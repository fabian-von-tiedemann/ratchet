"""The check that projects run writes nothing, the scripts that write do so through one guarded place, and no
script writes bytecode (round 3 of #100).

    python3 -m unittest discover -s checks -v

check_register.py, the check that projects run, writes nothing: it prints REGISTER.md
or the instruction file to standard output. generate.py writes only through
registry.write_file, behind a gate that refuses while git tracks a symbolic link in the
tree, or, outside a git work tree, while any entry is one, and refuses a root that
passes through a link. init.py writes with its own functions, each of which refuses a
link on the path it writes. Every script that runs as a program sets
sys.dont_write_bytecode before it imports a module from checks/. The sweep below reads
every script under checks/ with ast and fails on a call that writes anywhere but in
the places named in WRITERS. The trees with links, and the git work trees, are made
here, in a directory of their own, and never committed: a link in this repo would make
generate.py refuse to run on it. Standard library only.
"""

import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

from suite_runner import FixtureTest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import registry  # noqa: E402

REFUSED = "Replace each link with a regular file"

# The places each script under checks/ may write, by the name of the function that holds the call: a class's method
# as Class.method, a function inside another as outer.inner. A script that is not named here may not write at all.
# check_register.py writes nothing, and generate.py writes only through registry.write_file, so neither is named. The test files,
# test_*.py, are not swept: they are the suite, not the checks, they write only into directories they make with
# tempfile, and neither CI nor an agent runs them on a project's tree.
WRITERS = {
    "registry.py": {"write_file"},
    "init.py": {"temporary", "write_new", "add_line"},
    "release.py": {"git"},
    "expected_tests.py": {"main"},
    "suite_runner.py": {"Recorder.__init__", "FixtureTest.scratch", "FixtureTest.fixture_file", "FixtureTest.fixture_directory"},
}

# Calls that write, whatever the object they are called on: the methods of pathlib that change a file.
WRITING_METHODS = {"write_text", "write_bytes", "touch", "symlink_to", "hardlink_to", "mkdir", "unlink", "rmdir", "rmtree"}
# Calls that write when called on one of these modules.
WRITING_FUNCTIONS = {
    "os": {"replace", "rename", "renames", "remove", "unlink", "rmdir", "removedirs", "mkdir", "makedirs", "symlink", "link",
           "chmod", "lchmod", "chown", "lchown", "truncate", "ftruncate", "utime", "mkfifo", "mknod", "write", "pwrite",
           "writev", "sendfile", "copy_file_range"},
    "shutil": {"copy", "copy2", "copyfile", "copyfileobj", "copymode", "copystat", "copytree", "move", "rmtree", "chown",
               "make_archive", "unpack_archive"},
    "tempfile": {"mkdtemp", "mkstemp", "NamedTemporaryFile", "TemporaryFile", "SpooledTemporaryFile", "TemporaryDirectory"},
}
# Calls whose mode decides: open(path, mode) and its kin. Each only reads when its mode is left out or is a literal string
# with none of w, a, x and +, and its arguments are spelled out, with no * or **. Anything else counts as a write: the
# sweep fails closed (round 3 of #100, review of c71187f).
OPENERS = {("open",), ("io", "open"), ("io", "FileIO"), ("builtins", "open"), ("codecs", "open"), ("os", "fdopen")}
# The flags of os.open that only read.
READ_FLAGS = {"O_RDONLY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK", "O_DIRECTORY", "O_BINARY", "O_NOCTTY", "O_NOINHERIT"}
# Modules whose functions write. Importing one under another name, or importing a function from it, would hide a call.
MODULES = set(WRITING_FUNCTIONS) | {"io", "builtins", "codecs", "pathlib", "importlib"}
# Modules that are not imported at all in checks/: a Path writes through methods such as open, rename, replace and chmod
# whose names the sweep cannot tell from those of a string or a URL opener, and importlib imports a module by name.
BANNED = {"pathlib", "importlib"}


def dotted(node):
    """("os", "replace") for os.replace, ("open",) for open, None for anything else."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return tuple([node.id] + parts[::-1])
    return None


def argument(call, position, name):
    if len(call.args) > position:
        return call.args[position], True
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value, True
    return None, False


def read_flags(node):
    """Whether the flags of os.open only read: os.O_ names from READ_FLAGS, or getattr(os, "O_NAME", 0) of one, joined
    by |. A number, a name, any other call or any other operator is not known to only read."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return read_flags(node.left) and read_flags(node.right)
    if isinstance(node, ast.Attribute) and dotted(node) is not None and len(dotted(node)) == 2 and dotted(node)[0] == "os":
        return node.attr in READ_FLAGS
    if (isinstance(node, ast.Call) and dotted(node.func) == ("getattr",) and len(node.args) == 3 and not node.keywords
            and dotted(node.args[0]) == ("os",) and isinstance(node.args[1], ast.Constant) and node.args[1].value in READ_FLAGS
            and isinstance(node.args[2], ast.Constant) and node.args[2].value == 0 and not isinstance(node.args[2].value, bool)):
        return True
    return False


def spelled_out(call):
    """Whether every argument of the call is written out, with no * and no **."""
    return not any(isinstance(arg, ast.Starred) for arg in call.args) and all(keyword.arg is not None for keyword in call.keywords)


def writes(call):
    """What the call writes with, as text, or None if it only reads."""
    name = dotted(call.func)
    shown = ast.unparse(call) if hasattr(ast, "unparse") else ".".join(name or ("?",))
    if isinstance(call.func, ast.Attribute) and call.func.attr in WRITING_METHODS:
        return call.func.attr
    if name and len(name) == 2 and name[1] in WRITING_FUNCTIONS.get(name[0], ()):
        return ".".join(name)
    if name == ("__import__",):
        return "__import__, which imports a module by name"
    if name in OPENERS:
        if not spelled_out(call):
            return "%s with arguments that are not spelled out" % shown
        mode, given = argument(call, 1, "mode")
        if not given:
            return None
        if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and not set("wax+") & set(mode.value):
            return None
        return "%s, whose mode is not a literal that only reads" % shown
    if name == ("os", "open"):
        flags, given = argument(call, 1, "flags")
        if spelled_out(call) and given and read_flags(flags):
            return None
        return "%s, whose flags are not known to only read" % shown
    return None


def sweep(path):
    """[(the function that holds it, line, what), ...] for every call in the file that writes, and every import or name
    that would hide one."""
    with open(path, "rb") as handle:
        tree = ast.parse(handle.read(), filename=path)
    found = []

    def visit(node, where):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(child, where + [child.name])
                continue
            here = ".".join(where) or "<module>"
            if isinstance(child, ast.Call):
                what = writes(child)
                if what:
                    found.append((here, child.lineno, what))
            elif isinstance(child, ast.Import):
                for alias in child.names:
                    if alias.name.split(".")[0] in BANNED:
                        found.append((here, child.lineno, "import %s, which checks/ does not use" % alias.name))
                    elif alias.name in MODULES and alias.asname not in (None, alias.name):
                        found.append((here, child.lineno, "import %s as %s" % (alias.name, alias.asname)))
            elif isinstance(child, ast.ImportFrom) and child.module in MODULES:
                found.append((here, child.lineno, "from %s import ..." % child.module))
            elif isinstance(child, ast.Name) and child.id == "open" and not isinstance(child.ctx, ast.Load):
                found.append((here, child.lineno, "open is rebound"))
            visit(child, where)

    visit(tree, [])
    # open used as a value and not called, such as opener = open, could be called with any mode.
    called = set(id(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "open" and isinstance(node.ctx, ast.Load) and id(node) not in called:
            found.append(("?", node.lineno, "open is used without being called"))
    return found


def scripts():
    return sorted(name for name in os.listdir(HERE) if name.endswith(".py") and not name.startswith("test_"))


def scratch_dir(case):
    """A new directory for one test, by its path with no link in it, since generate.py refuses a root that passes
    through a link, and the temporary directory may (/tmp on macOS)."""
    directory = os.path.realpath(tempfile.mkdtemp(prefix="ratchet-test-"))
    case.addCleanup(shutil.rmtree, directory)
    return directory


def checks_modules():
    return set(name[:-3] for name in os.listdir(HERE) if name.endswith(".py"))


def no_bytecode_problem(path):
    """None if the script sets sys.dont_write_bytecode = True at its top level, after import sys and before it imports a
    module from checks/, or what is wrong."""
    with open(path, "rb") as handle:
        body = ast.parse(handle.read(), filename=path).body
    local = checks_modules()

    def imports_local(node):
        if isinstance(node, ast.Import):
            return any(alias.name.split(".")[0] in local for alias in node.names)
        return isinstance(node, ast.ImportFrom) and (node.level or (node.module or "").split(".")[0] in local)

    def imports_sys(node):
        return isinstance(node, ast.Import) and any(alias.name == "sys" for alias in node.names)

    def sets_flag(node):
        return (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute)
                and node.targets[0].attr == "dont_write_bytecode" and isinstance(node.targets[0].value, ast.Name)
                and node.targets[0].value.id == "sys" and isinstance(node.value, ast.Constant) and node.value.value is True)

    flag = next((number for number, node in enumerate(body) if sets_flag(node)), None)
    if flag is None:
        return "it does not set sys.dont_write_bytecode = True at its top level"
    if not any(imports_sys(node) for node in body[:flag]):
        return "it sets sys.dont_write_bytecode before it imports sys"
    first = next((number for number, node in enumerate(body) if imports_local(node)), None)
    if first is not None and first < flag:
        return "it imports a module from checks/ on line %d, before it sets sys.dont_write_bytecode" % body[first].lineno
    return None


def runnable():
    """The scripts under checks/ that run as programs: each holds if __name__ == "__main__". The tests are not among them."""
    found = []
    for name in scripts():
        with open(os.path.join(HERE, name), encoding="utf-8") as handle:
            if 'if __name__ == "__main__":' in handle.read():
                found.append(name)
    return found


def run(script, *args, root=ROOT, cwd=None, env=None):
    result = subprocess.run(
        [sys.executable, "-B", os.path.join(root, "checks", script)] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, cwd=cwd, env=env,
    )
    return result.returncode, result.stdout


def git(repo, *args):
    """Run git in repo, with no global or system config, so that nothing of the user's own is used."""
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    subprocess.run(["git", "-c", "commit.gpgsign=false"] + list(args), cwd=repo, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def commit_all(repo):
    """Make repo a git work tree and commit every file in it, with a name and mail set in that repo only."""
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    # No gc in the background after the commit: it would change .git while a test compares the tree before and after.
    git(repo, "config", "gc.auto", "0")
    git(repo, "config", "maintenance.auto", "false")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture")


def snapshot(top):
    """Every entry under top, without following a link: a link as its target, a file as its bytes, a directory as such."""
    state = {}
    for folder, folders, files in os.walk(top):
        for name in folders + files:
            path = os.path.join(folder, name)
            key = os.path.relpath(path, top)
            if os.path.islink(path):
                state[key] = ("link", os.readlink(path))
            elif os.path.isdir(path):
                state[key] = ("directory",)
            else:
                with open(path, "rb") as handle:
                    state[key] = ("file", handle.read())
    return state


class WriteSweep(unittest.TestCase):
    def test_no_script_writes_outside_the_places_named(self):
        for name in scripts():
            with self.subTest(script=name):
                allowed = WRITERS.get(name, set())
                outside = [(where, line, what) for where, line, what in sweep(os.path.join(HERE, name)) if where not in allowed]
                self.assertEqual(outside, [], "%s writes outside %s" % (name, ", ".join(sorted(allowed)) or "any place"))

    def test_check_register_writes_nothing(self):
        # The check that projects run prints what it generates and never writes, so no link can lead a write of it.
        self.assertEqual(sweep(os.path.join(HERE, "check_register.py")), [])
        with open(os.path.join(HERE, "check_register.py"), encoding="utf-8") as handle:
            text = handle.read()
        for name in ("write_file", "refuse_links", "guard_path"):
            self.assertNotIn(name, text)

    def test_generate_writes_only_through_the_one_function(self):
        self.assertEqual(sweep(os.path.join(HERE, "generate.py")), [])
        self.assertEqual(sorted(set(where for where, _, _ in sweep(os.path.join(HERE, "registry.py")))), ["write_file"])
        with open(os.path.join(HERE, "generate.py"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("registry.write_file(", text)
        self.assertIn("registry.refuse_links(", text)

    def test_each_write_of_init_is_guarded(self):
        # init.py keeps its own writes, which never overwrite a file and put each in place whole. Each function that
        # writes a file there refuses a link on its path first, with registry.guard_path.
        with open(os.path.join(HERE, "init.py"), "rb") as handle:
            tree = ast.parse(handle.read())
        functions = dict((node.name, node) for node in tree.body if isinstance(node, ast.FunctionDef))
        for name in ("write_new", "add_line"):
            with self.subTest(function=name):
                calls = [dotted(node.func) for node in ast.walk(functions[name]) if isinstance(node, ast.Call)]
                self.assertIn(("registry", "guard_path"), calls)
                self.assertLess(calls.index(("registry", "guard_path")), calls.index(("temporary",)))
        callers = [node.name for node in functions.values()
                   if any(isinstance(call, ast.Call) and dotted(call.func) == ("temporary",) for call in ast.walk(node))]
        self.assertEqual(sorted(callers), ["add_line", "write_new"])

    def test_every_place_named_still_writes(self):
        # A name left in WRITERS after its write is gone would let a new write in there unseen.
        for name, allowed in sorted(WRITERS.items()):
            with self.subTest(script=name):
                self.assertEqual(sorted(set(where for where, _, _ in sweep(os.path.join(HERE, name)))), sorted(allowed))

    def test_the_sweep_finds_each_kind_of_write(self):
        source = "\n".join([
            "import io, os, shutil, tempfile, pathlib",
            "def a(p):",
            "    open(p, 'w')", "    open(p, mode='ab')", "    open(p, 'r+')", "    open(p, 'x')", "    open(p, m)",
            "    os.fdopen(d, 'wb')", "    os.open(p, os.O_WRONLY | os.O_CREAT)", "    os.open(p, flags)",
            "    os.open(p, os.O_RDONLY | getattr(os, 'O_APPEND', 0))",
            "    pathlib.Path(p).write_text('x')", "    q.write_bytes(b'')", "    os.replace(p, q)", "    os.rename(p, q)",
            "    shutil.copy(p, q)", "    shutil.copyfile(p, q)", "    shutil.move(p, q)", "    os.makedirs(p)", "    os.symlink(p, q)",
            "    tempfile.mkdtemp()",
            # Round 3 of #100, review of c71187f: each of these passed the sweep before it failed closed.
            "    os.open(p, os.O_RDONLY | 1)", "    open(p, **{'mode': 'w'})", "    open(*(p, 'w'))", "    io.FileIO(p, 'w')",
            "    io.FileIO(p, m)", "    os.open(p, *flags)", "    os.fdopen(d, **kw)", "    open(p, 'r', **kw)",
            "    os.open(p, getattr(os, 'O_WRONLY', 0))", "    os.open(p, getattr(os, 'O_NOFOLLOW', 1))",
            "import shutil as s", "from os import replace", "opener = open", "import importlib", "x = __import__('os')",
            "def b(p):",
            "    open(p)", "    open(p, 'rb')", "    os.open(p, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))", "    text.replace('a', 'b')",
            "    opener.open(request)", "    handle.write('x')", "    io.FileIO(p)", "    io.FileIO(p, 'rb')", "    open(p, mode='r')",
            "    os.fdopen(d)",
        ])
        scratch = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, scratch)
        path = os.path.join(scratch, "sample.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(source + "\n")
        found = sweep(path)
        self.assertEqual(len([where for where, _, _ in found if where == "a"]), 29, found)
        self.assertEqual([where for where, _, _ in found if where == "b"], [], found)
        # import pathlib, import shutil as s, from os import replace, opener = open, import importlib, __import__.
        self.assertEqual(len([where for where, _, _ in found if where in ("<module>", "?")]), 6, found)


class PartFiles(unittest.TestCase):
    def test_the_file_of_a_part_is_a_plain_path_inside_the_repo(self):
        # generate.py reads and writes the file of each part. Like a reference check, it is a plain relative path.
        with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as handle:
            data = json.load(handle)
        scratch = scratch_dir(self)
        for bad in ("../RATCHET.md", "/RATCHET.md", "docs/../../x.md", ".hidden.md", "a//b.md", "RATCHET.md\n"):
            with self.subTest(file=bad):
                changed = json.loads(json.dumps(data))
                changed["parts"][0]["file"] = bad
                path = os.path.join(scratch, "ratchet.json")
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(changed, handle)
                with self.assertRaises(registry.RegistryError) as raised:
                    registry.load(path)
                self.assertIn("the file of a part must be a plain path inside the repo", str(raised.exception))


def bytecode_env(prefix):
    """os.environ for a run whose bytecode is looked for: without PYTHONDONTWRITEBYTECODE, so only what the scripts set
    keeps it out, without PYTHONPATH, so nothing is imported from the real checks (review of #106), and with the cache
    prefix in the scratch tree, so bytecode that goes there instead of to __pycache__ is seen too."""
    env = dict((k, v) for k, v in os.environ.items() if k not in ("PYTHONDONTWRITEBYTECODE", "PYTHONPATH", "PYTHONPYCACHEPREFIX"))
    env["PYTHONPYCACHEPREFIX"] = prefix
    return env


def startup_bytecode(case):
    """The .pyc, relative to a cache prefix, that this interpreter writes under it before the first line of a script
    runs. They are modules of the standard library, such as site and encodings, which it imports at its start, and only
    -B from the caller would stop them. The script sets sys.dont_write_bytecode, as the checks do, and nothing else."""
    scratch = scratch_dir(case)
    prefix = os.path.join(scratch, "prefix")
    script = os.path.join(scratch, "start.py")
    with open(script, "w", encoding="utf-8") as handle:
        handle.write("import sys\nsys.dont_write_bytecode = True\n")
    result = subprocess.run([sys.executable, script], cwd=scratch, env=bytecode_env(prefix), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True)
    case.assertEqual(result.returncode, 0, result.stdout)
    return set(os.path.relpath(os.path.join(folder, name), prefix)
               for folder, _, names in os.walk(prefix) for name in names if name.endswith(".pyc"))


def bytecode_written(scratch, prefix, baseline):
    """Every .pyc in scratch that is not under prefix, and every .pyc under prefix that is not in baseline."""
    found = []
    for folder, _, names in os.walk(scratch):
        for name in (name for name in names if name.endswith(".pyc")):
            path = os.path.join(folder, name)
            if os.path.commonpath([path, prefix]) != prefix or os.path.relpath(path, prefix) not in baseline:
                found.append(os.path.relpath(path, scratch))
    return sorted(found)


class NoBytecode(unittest.TestCase):
    def test_every_script_that_runs_as_a_program_sets_no_bytecode_first(self):
        names = runnable()
        self.assertIn("generate.py", names)
        self.assertIn("check_register.py", names)
        self.assertIn("init.py", names)
        for name in names:
            with self.subTest(script=name):
                self.assertIsNone(no_bytecode_problem(os.path.join(HERE, name)))

    def test_the_sweep_for_bytecode_fails_on_each_wrong_order(self):
        scratch = scratch_dir(self)
        cases = {
            "import sys\nsys.dont_write_bytecode = True\nimport registry\n": None,
            '"""Doc."""\nimport os\nimport sys\n\nsys.dont_write_bytecode = True\nimport registry\n': None,
            "import sys\nimport registry\nsys.dont_write_bytecode = True\n": "before it sets",
            "import registry\n": "does not set",
            "import sys\nif True:\n    sys.dont_write_bytecode = True\n": "does not set",
            "sys.dont_write_bytecode = True\nimport sys\n": "before it imports sys",
            "import sys\nsys.dont_write_bytecode = 1\n": "does not set",
            "import sys\nfrom check_register import check\nsys.dont_write_bytecode = True\n": "before it sets",
        }
        for number, (source, expected) in enumerate(sorted(cases.items())):
            with self.subTest(source=source):
                path = os.path.join(scratch, "case%d.py" % number)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(source)
                problem = no_bytecode_problem(path)
                if expected is None:
                    self.assertIsNone(problem)
                else:
                    self.assertIn(expected, problem or "")

    def test_scripts_run_as_programs_write_no_bytecode(self):
        # Run without -B and without PYTHONDONTWRITEBYTECODE: only the flag each script sets keeps the bytecode out.
        # Review of #106: the cache prefix is in the scratch tree, so bytecode that goes there is seen too.
        scratch = scratch_dir(self)
        copy, prefix = os.path.join(scratch, "ratchet"), os.path.join(scratch, "prefix")
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        env, baseline = bytecode_env(prefix), startup_bytecode(self)
        for args in ((os.path.join(copy, "checks", "generate.py"), "--check"),
                     (os.path.join(copy, "checks", "check_register.py"), "register.json", "--markdown", "REGISTER.md"),
                     (os.path.join(copy, "checks", "check_register.py"), "register.json", "--print-markdown")):
            with self.subTest(args=args[1:]):
                result = subprocess.run([sys.executable] + list(args), cwd=copy, env=env, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, universal_newlines=True)
                self.assertEqual(result.returncode, 0, result.stdout)
                caches = [folder for folder, folders, _ in os.walk(copy) if "__pycache__" in folders]
                self.assertEqual(caches, [], "no __pycache__ was written")
                self.assertEqual(bytecode_written(scratch, prefix, baseline), [],
                                 "no bytecode beyond what the interpreter writes at its start")


class NoBytecodeFromTheSuite(unittest.TestCase):
    def test_expected_tests_and_the_processes_under_it_write_no_bytecode(self):
        # Review of 3219bf4: expected_tests.py runs suite_runner.py, whose tests spawn more Python, such as
        # python -m unittest in test_tripwire. A copy of the three scripts runs a reduced suite of one test, whose child
        # imports a module of its own, without -B and without PYTHONDONTWRITEBYTECODE. No __pycache__ appears anywhere.
        scratch = scratch_dir(self)
        copy, start = os.path.join(scratch, "checks"), os.path.join(scratch, "start")
        fixtures = os.path.join(copy, "fixtures")
        for folder in (copy, start, fixtures):
            os.mkdir(folder)
        for name in ("expected_tests.py", "suite_runner.py", "registry.py"):
            shutil.copyfile(os.path.join(HERE, name), os.path.join(copy, name))
        with open(os.path.join(fixtures, "one.txt"), "w", encoding="utf-8") as handle:
            handle.write("one\n")
        with open(os.path.join(start, "probe_helper.py"), "w", encoding="utf-8") as handle:
            handle.write("VALUE = 1\n")
        with open(os.path.join(start, "test_probe.py"), "w", encoding="utf-8") as handle:
            handle.write("\n".join([
                "import os, subprocess, sys, unittest",
                "import probe_helper",
                "from suite_runner import FixtureTest",
                "HERE = os.path.dirname(os.path.abspath(__file__))",
                "class Probe(FixtureTest):",
                "    def test_a_child_imports_a_module(self):",
                "        self.fixture_bytes('one.txt')",
                "        subprocess.run([sys.executable, '-c', 'import probe_helper'], cwd=HERE, check=True)",
                "        subprocess.run([sys.executable, '-m', 'unittest', 'probe_helper'], cwd=HERE,",
                "                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)",
                ""]))
        # Review of #100 and #106: the cache prefix is in the scratch tree, PYTHONPATH is not passed, and what the
        # interpreter writes under a prefix at its start is read from a run of its own, not allowed by its path.
        prefix = os.path.join(scratch, "prefix")
        baseline = startup_bytecode(self)
        result = subprocess.run([sys.executable, os.path.join(copy, "expected_tests.py"), "--start", start, "--fixtures", fixtures],
                                cwd=scratch, env=bytecode_env(prefix), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("every expected test ran and passed", result.stdout)
        caches = [folder for folder, folders, _ in os.walk(scratch) if "__pycache__" in folders]
        self.assertEqual(caches, [], "no __pycache__ was written")
        self.assertEqual(bytecode_written(scratch, prefix, baseline), [],
                         "no bytecode beyond what the interpreter writes at its start")

    def test_the_suite_passes_the_variable_to_the_python_it_spawns(self):
        # The tests that spawn python -m unittest or python -c pass -B as well.
        for name, needle in (("test_tripwire.py", '[sys.executable, "-B", "-m", "unittest"]'),
                             ("test_init.py", '[sys.executable, "-B", "-c", code]')):
            with self.subTest(test=name):
                with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                    self.assertIn(needle, handle.read())
        with open(os.path.join(HERE, "suite_runner.py"), "rb") as handle:
            body = ast.parse(handle.read()).body
        sets = [node for node in body if isinstance(node, ast.Assign) and ast.dump(node.targets[0]).find("PYTHONDONTWRITEBYTECODE") >= 0]
        self.assertEqual(len(sets), 1, "suite_runner.py sets os.environ[\"PYTHONDONTWRITEBYTECODE\"] at its top level")


class WriteFile(unittest.TestCase):
    """registry.write_file, in this process."""

    def setUp(self):
        self.base = scratch_dir(self)
        self.repo = os.path.join(self.base, "repo")
        os.mkdir(self.repo)
        self.addCleanup(registry.forget_walks)

    def test_nothing_is_written_before_the_walk(self):
        registry.forget_walks()
        with self.assertRaises(registry.RegistryError) as raised:
            registry.write_file(os.path.join(self.repo, "a.md"), "text")
        self.assertIn("no tree was checked for links", str(raised.exception))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "a.md")))

    def test_a_file_outside_the_tree_walked_is_not_written(self):
        self.assertIsNone(registry.refuse_links(self.repo))
        for target in (os.path.join(self.base, "a.md"), os.path.join(self.repo, "..", "a.md")):
            with self.subTest(target=target):
                with self.assertRaises(registry.RegistryError) as raised:
                    registry.write_file(target, "text")
                self.assertIn("outside the tree that was checked for links", str(raised.exception))
        self.assertEqual(sorted(os.listdir(self.base)), ["repo"])

    def test_a_file_in_the_tree_walked_is_written(self):
        self.assertIsNone(registry.refuse_links(self.repo))
        registry.write_file(os.path.join(self.repo, "a.md"), "tå\n")
        registry.write_file(os.path.join(self.repo, "new", "b.md"), b"\xff", parents=True)
        with open(os.path.join(self.repo, "a.md"), "rb") as handle:
            self.assertEqual(handle.read(), "tå\n".encode("utf-8"))
        with open(os.path.join(self.repo, "new", "b.md"), "rb") as handle:
            self.assertEqual(handle.read(), b"\xff")

    def test_a_tree_with_a_link_is_not_recorded_as_walked(self):
        os.symlink(self.base, os.path.join(self.repo, "up"))
        self.assertIn("up", registry.refuse_links(self.repo))
        with self.assertRaises(registry.RegistryError):
            registry.write_file(os.path.join(self.repo, "a.md"), "text")

    def test_a_link_made_after_the_walk_on_the_path_is_not_followed(self):
        # The gate may pass a link that git does not track. write_file checks every part of its own path.
        outside = os.path.join(self.base, "outside")
        os.mkdir(outside)
        with open(os.path.join(outside, "a.md"), "wb") as handle:
            handle.write(b"before\n")
        self.assertIsNone(registry.refuse_links(self.repo))
        os.symlink(outside, os.path.join(self.repo, "dir"))
        os.symlink(os.path.join(outside, "a.md"), os.path.join(self.repo, "a.md"))
        os.mkdir(os.path.join(self.repo, "real"))
        os.symlink(outside, os.path.join(self.repo, "real", "deeper"))
        for target, parents in (("dir/a.md", False), ("dir/new.md", False), ("dir/sub/new.md", True), ("a.md", False),
                                ("real/deeper/new.md", True)):
            with self.subTest(target=target):
                with self.assertRaises(registry.RegistryError) as raised:
                    registry.write_file(os.path.join(self.repo, *target.split("/")), "after\n", parents=parents)
                self.assertIn("is a symbolic link", str(raised.exception))
        self.assertEqual(sorted(os.listdir(outside)), ["a.md"])
        with open(os.path.join(outside, "a.md"), "rb") as handle:
            self.assertEqual(handle.read(), b"before\n")

    def test_a_root_that_passes_through_a_link_is_refused(self):
        # The root is taken as given, with os.path.abspath, and never resolved: a root through a link below the enclosing
        # git root is refused.
        os.mkdir(os.path.join(self.base, ".git"))
        os.symlink(self.repo, os.path.join(self.base, "linked"))
        for root in (os.path.join(self.base, "linked"), os.path.join(self.base, "linked", "sub")):
            with self.subTest(root=root):
                os.makedirs(os.path.join(self.repo, "sub"), exist_ok=True)
                problem = registry.refuse_links(root)
                self.assertIn("passes through a symbolic link", problem or "")
                self.assertIn(os.path.join(self.base, "linked"), problem)
                with self.assertRaises(registry.RegistryError):
                    registry.write_file(os.path.join(root, "a.md"), "text")
        self.assertEqual(sorted(os.listdir(self.repo)), ["sub"])
        self.assertIsNone(registry.root_link(self.repo))

    def test_a_root_that_is_missing_a_link_or_not_a_directory_is_refused(self):
        os.mkdir(os.path.join(self.repo, ".git"))
        os.symlink(self.base, os.path.join(self.repo, "up"))
        with open(os.path.join(self.repo, "file"), "wb") as handle:
            handle.write(b"x")
        for name, message in (("missing", "does not exist"), ("up", "passes through a symbolic link"),
                              ("up/missing", "passes through a symbolic link"), ("file", "is not a directory")):
            with self.subTest(root=name):
                root = os.path.join(self.repo, *name.split("/"))
                self.assertIn(message, registry.refuse_links(root) or "")
                with self.assertRaises(registry.RegistryError):
                    registry.write_file(os.path.join(root, "a.md"), "text", parents=True)
        self.assertEqual(sorted(os.listdir(self.base)), ["repo"])

    def test_a_link_between_the_enclosing_git_root_and_the_root_is_refused(self):
        # The enclosing git root is found by the path as given, without resolving it: a/ is a link in the repo, and the
        # root is a/b below it.
        os.mkdir(os.path.join(self.repo, ".git"))
        outside = os.path.join(self.base, "outside")
        os.makedirs(os.path.join(outside, "b"))
        os.symlink(outside, os.path.join(self.repo, "a"))
        problem = registry.refuse_links(os.path.join(self.repo, "a", "b"))
        self.assertIn("passes through a symbolic link", problem or "")
        self.assertIn(os.path.join(self.repo, "a"), problem)

    def test_a_link_above_the_workspace_is_not_refused(self):
        # A link of the system above the repo, such as /tmp or /var on macOS, is neither between the working directory
        # and the root nor below an enclosing git root, and is not refused.
        os.symlink(self.base, os.path.join(self.base, "system"))
        try:
            os.mkdir(os.path.join(self.repo, ".git"))
            self.assertIsNone(registry.root_link(os.path.join(self.base, "system", "repo")))
        finally:
            os.rmdir(os.path.join(self.repo, ".git"))
        unresolved = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, unresolved)
        self.assertIsNone(registry.refuse_links(unresolved))

    def test_a_path_with_dot_dot_is_refused_by_link_problem(self):
        for path in ("a/../b", "../b", os.path.join(self.repo, "x", "..", "y"), "a/b/.."):
            with self.subTest(path=path):
                self.assertIn('".."', registry.link_problem(path) or "")
        self.assertIsNone(registry.link_problem(os.path.join(self.repo, "a..b")))

    def test_guard_path_refuses_a_link_on_the_path_and_a_path_outside(self):
        os.mkdir(os.path.join(self.repo, "real"))
        os.symlink(self.base, os.path.join(self.repo, "real", "up"))
        os.symlink(os.path.join(self.base, "x"), os.path.join(self.repo, "file.md"))
        for target, message in (("real/up/a.md", "real/up is a symbolic link"), ("file.md", "file.md is a symbolic link"),
                                ("../a.md", "outside")):
            with self.subTest(target=target):
                with self.assertRaises(registry.RegistryError) as raised:
                    registry.guard_path(self.repo, os.path.join(self.repo, *target.split("/")))
                self.assertIn(message, str(raised.exception))
        registry.guard_path(self.repo, os.path.join(self.repo, "real", "new", "a.md"))

    def test_a_file_with_a_second_hard_link_is_not_written(self):
        outside = os.path.join(self.base, "outside.md")
        with open(outside, "wb") as handle:
            handle.write(b"before\n")
        try:
            os.link(outside, os.path.join(self.repo, "a.md"))
        except OSError:
            self.skipTest("no hard links here")
        self.assertIsNone(registry.refuse_links(self.repo))
        with self.assertRaises(registry.RegistryError) as raised:
            registry.write_file(os.path.join(self.repo, "a.md"), "after\n")
        self.assertIn("hard link", str(raised.exception))
        with open(outside, "rb") as handle:
            self.assertEqual(handle.read(), b"before\n")


class Trees(FixtureTest):
    """Trees with links, made in a directory of their own: the repo under repo/, what the links lead to under outside/."""

    def tree(self):
        self.base = scratch_dir(self)
        self.repo = os.path.join(self.base, "repo")
        self.outside = os.path.join(self.base, "outside")
        os.mkdir(self.outside)

    def register_tree(self):
        """A copy of block-clean, with its block made stale, so that a write mode has something to write."""
        self.tree()
        os.mkdir(self.repo)
        for name in ("register.json", "REGISTER.md", "AGENTS.md"):
            with open(os.path.join(self.repo, name), "wb") as handle:
                handle.write(self.fixture_bytes("register/block-clean/" + name))
        self.stale(os.path.join(self.repo, "AGENTS.md"))

    def stale(self, path):
        # Swap the first status in the file, whichever there is: since step 3 of D-2026-11-22-second-redraw this repo's
        # register has no entry that is built. A file left unchanged would let the tests pass for the wrong reason.
        with open(path, "rb") as handle:
            data = handle.read()
        for old, new in ((b"| built |", b"| text only for now |"), (b"| text only for now |", b"| built |")):
            if old in data:
                changed = data.replace(old, new, 1)
                break
        else:
            self.fail("%s holds no status to make stale" % path)
        with open(path, "wb") as handle:
            handle.write(changed)

    def repo_copy(self):
        self.tree()
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))

    def set_instructions(self, value):
        path = os.path.join(self.repo, "register.json")
        with open(path, encoding="utf-8") as handle:
            register = json.load(handle)
        register["instructions"] = value
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(register, handle)

    def assert_refused(self, script, args, links, root=None):
        before = snapshot(self.base)
        code, output = run(script, *args, root=root or ROOT, cwd=self.repo)
        self.assertNotEqual(code, 0, output)
        self.assertIn(REFUSED, output)
        for link in links:
            self.assertIn(link, output)
        self.assertNotIn("wrote", output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(snapshot(self.base), before, "nothing in the repo or outside it was written")
        return output


class CheckRegisterWritesNothing(Trees):
    """check_register.py prints and never writes, whatever links the tree holds, tracked or not."""

    def printed(self, *args, cwd=None):
        result = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "checks", "check_register.py")] + list(args),
                                cwd=cwd or self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stdout, result.stderr.decode("utf-8", errors="replace")

    def linked_tree(self, git_tracks):
        """block-clean with a stale block, and links of every kind: a file outside, a directory outside, and CLAUDE.md
        to AGENTS.md. With git_tracks, a git work tree that tracks them all."""
        self.register_tree()
        with open(os.path.join(self.outside, "notes.md"), "wb") as handle:
            handle.write(b"Outside the repo.\n")
        os.mkdir(os.path.join(self.repo, "docs"))
        os.symlink(os.path.join(self.outside, "notes.md"), os.path.join(self.repo, "docs", "notes.md"))
        os.symlink(self.outside, os.path.join(self.repo, "link"))
        os.symlink("AGENTS.md", os.path.join(self.repo, "CLAUDE.md"))
        for name in ("REGISTER.md.new", "AGENTS.md.new"):
            os.symlink(os.path.join(self.outside, name), os.path.join(self.repo, name))
        if git_tracks:
            commit_all(self.repo)

    def test_the_print_modes_write_nothing_in_a_tree_with_links(self):
        for git_tracks in (False, True):
            with self.subTest(git_tracks=git_tracks):
                self.linked_tree(git_tracks)
                before = snapshot(self.base)
                code, out, err = self.printed("register.json", "--print-markdown")
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(out, self.fixture_bytes("register/block-clean/REGISTER.md"))
                code, out, err = self.printed("register.json", "--print-instructions")
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(out, self.fixture_bytes("register/block-clean/AGENTS.md"))
                self.assertEqual(snapshot(self.base), before, "nothing in the repo or outside it was written")

    def test_the_documented_commands_replace_links_and_write_nothing_through_them(self):
        # The command for each file removes the .new file and the target first, so that neither the redirection nor mv
        # follows a link that stood at either name, and mv then puts a regular file in place.
        self.linked_tree(True)
        os.remove(os.path.join(self.repo, "REGISTER.md"))
        os.symlink(self.outside, os.path.join(self.repo, "REGISTER.md"))
        outside = dict((k, v) for k, v in snapshot(self.base).items() if k.startswith("outside"))
        with open(os.path.join(ROOT, "checks", "README.md"), encoding="utf-8") as handle:
            readme = handle.read()
        commands = [line.strip() for line in readme.split("\n") if line.strip().startswith("rm -f ") and "check_register.py" in line]
        self.assertEqual(len(commands), 2, commands)
        for command in commands:
            command = command.replace("python3 checks/check_register.py", "%s -B %s" % (
                shlex.quote(sys.executable), shlex.quote(os.path.join(ROOT, "checks", "check_register.py"))))
            result = subprocess.run(["/bin/sh", "-c", command], cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(dict((k, v) for k, v in snapshot(self.base).items() if k.startswith("outside")), outside)
        for name, fixture in (("REGISTER.md", "REGISTER.md"), ("AGENTS.md", "AGENTS.md")):
            path = os.path.join(self.repo, name)
            self.assertFalse(os.path.islink(path))
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), self.fixture_bytes("register/block-clean/" + fixture))
        self.assertFalse(os.path.lexists(os.path.join(self.repo, "REGISTER.md.new")))

    def test_the_documented_command_for_a_nested_instruction_file_writes_nothing_through_a_tracked_link(self):
        # Review of 7787374, P1: the .new file stands in the directory the command runs in, under a plain name, and only
        # rm -f and mv name the nested path, after the check has refused a link there. docs is a link that git tracks,
        # to a directory outside that holds AGENTS.md and AGENTS.md.new.
        self.register_tree()
        for name in ("AGENTS.md", "AGENTS.md.new"):
            with open(os.path.join(self.outside, name), "wb") as handle:
                handle.write(b"Outside the repo.\n")
        os.symlink(self.outside, os.path.join(self.repo, "docs"))
        self.set_instructions("docs/AGENTS.md")
        commit_all(self.repo)
        documented = []
        for name in ("UPGRADING.md", os.path.join("checks", "README.md")):
            with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
                documented += [(name, command) for command in re.findall(r"`(rm -f [^`]*--print-instructions[^`]*docs/AGENTS\.md)`", handle.read())]
        self.assertEqual(sorted(name for name, _ in documented), sorted([os.path.join("checks", "README.md"), "UPGRADING.md"]), documented)
        for name, command in documented:
            with self.subTest(document=name):
                self.assertIn("> AGENTS.md.new &&", command, "the new file has a plain name in the current directory")
                self.assertNotIn("docs/AGENTS.md.new", command)
                command = re.sub(r"python3 \S*checks/check_register\.py", "%s -B %s" % (
                    shlex.quote(sys.executable), shlex.quote(os.path.join(ROOT, "checks", "check_register.py"))), command)
                outside = dict((k, v) for k, v in snapshot(self.base).items() if k.startswith("outside"))
                result = subprocess.run(["/bin/sh", "-c", command], cwd=self.repo, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, universal_newlines=True)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("is a symbolic link", result.stdout)
                self.assertEqual(dict((k, v) for k, v in snapshot(self.base).items() if k.startswith("outside")), outside,
                                 "nothing outside was emptied, removed or written")

    def test_a_path_with_dot_dot_is_refused(self):
        # Review of 7787374, P2: os.path.abspath folds jump/.. away, but the file is opened by the path as given, through
        # jump, a link that git tracks, to a directory under the one outside.
        self.tree()
        os.mkdir(self.repo)
        sub = os.path.join(self.outside, "subdir")
        os.mkdir(sub)
        for name in ("register.json", "REGISTER.md", "AGENTS.md"):
            for where in (self.repo, self.outside):
                with open(os.path.join(where, name), "wb") as handle:
                    handle.write(self.fixture_bytes("register/block-clean/" + name))
        os.symlink(sub, os.path.join(self.repo, "jump"))
        commit_all(self.repo)
        for args in (("jump/../register.json",), ("register.json", "--markdown", "jump/../REGISTER.md"),
                     ("register.json", "--agents", "jump/../AGENTS.md"), ("jump/../register.json", "--print-markdown")):
            with self.subTest(args=args):
                code, out, err = self.printed(*args)
                self.assertEqual((code, out), (2, b""), err)
                self.assertIn("..", err)
                self.assertIn("refused", err)

    def test_the_print_modes_report_a_register_that_cannot_be_read(self):
        # Review of 7787374, P3: a register that is not JSON, or not UTF-8, is reported, not a traceback.
        self.register_tree()
        for data, message in ((b"{not json", "not a valid data file"), (b'{"project": "\xff"}', "not valid UTF-8")):
            with open(os.path.join(self.repo, "register.json"), "wb") as handle:
                handle.write(data)
            for flag in ("--print-markdown", "--print-instructions"):
                with self.subTest(data=data, flag=flag):
                    code, out, err = self.printed("register.json", flag)
                    self.assertEqual((code, out), (1, b""), err)
                    self.assertIn(message, err)
                    self.assertNotIn("Traceback", err)

    def test_the_instruction_file_is_not_printed_through_a_link(self):
        self.register_tree()
        shutil.copyfile(os.path.join(self.repo, "AGENTS.md"), os.path.join(self.outside, "AGENTS.md"))
        os.symlink(self.outside, os.path.join(self.repo, "link"))
        for instructions in ("link/AGENTS.md", "CLAUDE.md"):
            with self.subTest(instructions=instructions):
                if instructions == "CLAUDE.md":
                    os.symlink(os.path.join(self.outside, "AGENTS.md"), os.path.join(self.repo, "CLAUDE.md"))
                self.set_instructions(instructions)
                before = snapshot(self.base)
                code, out, err = self.printed("register.json", "--print-instructions")
                self.assertEqual(code, 1, err)
                self.assertEqual(out, b"")
                self.assertIn("is a symbolic link", err)
                self.assertEqual(snapshot(self.base), before)

    def test_a_register_reached_through_a_tracked_link_is_refused(self):
        # The register's directory, or a directory above it, is a link that git tracks, to a project outside. The check
        # refuses to read there in every mode, rather than check the file outside, and writes nothing.
        for linked, register in (("project", "project/register.json"), ("a", "a/b/register.json")):
            with self.subTest(register=register):
                self.tree()
                os.mkdir(self.repo)
                project = os.path.join(self.outside, *register.split("/")[1:-1]) if "/b/" in register else self.outside
                os.makedirs(project, exist_ok=True)
                for name in ("register.json", "REGISTER.md", "AGENTS.md"):
                    with open(os.path.join(project, name), "wb") as handle:
                        handle.write(self.fixture_bytes("register/block-clean/" + name))
                os.symlink(self.outside, os.path.join(self.repo, linked))
                commit_all(self.repo)
                before = snapshot(self.base)
                markdown = register.replace("register.json", "REGISTER.md")
                for args in (("--print-instructions",), ("--print-markdown",), ("--markdown", markdown), ()):
                    with self.subTest(args=args):
                        code, out, err = self.printed(register, *args)
                        self.assertNotEqual(code, 0, err)
                        self.assertEqual(out if args[:1] != ("--markdown",) and args else b"", b"")
                        self.assertIn("passes through a symbolic link", (out.decode("utf-8") + err))
                        self.assertEqual(snapshot(self.base), before)

    def test_compare_mode_passes_with_a_link_inside_the_tree(self):
        for git_tracks in (False, True):
            with self.subTest(git_tracks=git_tracks):
                self.register_tree()
                with open(os.path.join(self.repo, "AGENTS.md"), "wb") as handle:
                    handle.write(self.fixture_bytes("register/block-clean/AGENTS.md"))
                os.symlink("AGENTS.md", os.path.join(self.repo, "CLAUDE.md"))
                if git_tracks:
                    commit_all(self.repo)
                before = snapshot(self.base)
                code, output = run("check_register.py", "register.json", "--markdown", "REGISTER.md", cwd=self.repo)
                self.assertEqual(code, 0, output)
                self.assertIn("AGENTS.md: the block between the markers is what register.json generates", output)
                self.assertEqual(snapshot(self.base), before)


class LinksRefused(Trees):
    """Outside a git work tree the gate of generate.py walks every entry and refuses every link."""

    def test_generate_refuses_a_tree_with_a_link_to_a_file_outside_in_a_directory_it_scans(self):
        self.repo_copy()
        stale = b"<!-- generated:version -->\nstale\n<!-- /generated -->\n"
        with open(os.path.join(self.outside, "LINKED.md"), "wb") as handle:
            handle.write(stale)
        os.symlink(os.path.join(self.outside, "LINKED.md"), os.path.join(self.repo, "templates", "LINKED.md"))
        for args in ((), ("--check",)):
            with self.subTest(args=args):
                self.assert_refused("generate.py", args, ["templates/LINKED.md"], root=self.repo)

    def test_generate_refuses_a_tree_with_a_linked_parent_directory(self):
        self.repo_copy()
        fixtures = os.path.join(self.repo, "checks", "fixtures", "register")
        shutil.move(fixtures, os.path.join(self.outside, "register"))
        os.remove(os.path.join(self.outside, "register", "clean", "REGISTER.md"))
        os.symlink(os.path.join(self.outside, "register"), fixtures)
        for args in ((), ("--check",)):
            with self.subTest(args=args):
                self.assert_refused("generate.py", args, ["checks/fixtures/register"], root=self.repo)

    def test_generate_refuses_a_tree_with_a_link_inside_it(self):
        self.repo_copy()
        os.symlink("AGENTS.md", os.path.join(self.repo, "CLAUDE.md"))
        self.stale(os.path.join(self.repo, "AGENTS.md"))
        for args in ((), ("--check",)):
            with self.subTest(args=args):
                output = self.assert_refused("generate.py", args, ["CLAUDE.md"], root=self.repo)
                self.assertNotIn("out of date", output, "nothing was read before the refusal")
                self.assertIn("not a git work tree", output)

    def test_generate_runs_on_a_copy_without_links(self):
        self.repo_copy()
        code, output = run("generate.py", "--check", root=self.repo, cwd=self.repo)
        self.assertEqual(code, 0, output)


class GitLinks(Trees):
    """In a git work tree, the gate of generate.py refuses only links that git tracks. Each tree is made with git init
    when the test runs. Links that the user's own tools make, untracked, pass the gate, and write_file refuses each on
    its own path."""

    def tool_links(self):
        """An untracked .venv/bin/python and node_modules/.bin/x, each a link to a file outside the repo."""
        for name in ("python", "x"):
            with open(os.path.join(self.outside, name), "wb") as handle:
                handle.write(b"outside\n")
        os.makedirs(os.path.join(self.repo, ".venv", "bin"))
        os.makedirs(os.path.join(self.repo, "node_modules", ".bin"))
        os.symlink(os.path.join(self.outside, "python"), os.path.join(self.repo, ".venv", "bin", "python"))
        os.symlink(os.path.join(self.outside, "x"), os.path.join(self.repo, "node_modules", ".bin", "x"))

    def assert_outside_unchanged(self, before):
        self.assertEqual(dict((k, v) for k, v in snapshot(self.base).items() if k.startswith("outside")),
                         dict((k, v) for k, v in before.items() if k.startswith("outside")))

    def test_generate_writes_past_untracked_links_of_tools(self):
        self.repo_copy()
        self.stale(os.path.join(self.repo, "AGENTS.md"))
        commit_all(self.repo)
        self.tool_links()
        before = snapshot(self.base)
        code, output = run("generate.py", root=self.repo, cwd=self.repo)
        self.assertEqual(code, 0, output)
        self.assertIn("wrote AGENTS.md", output)
        self.assert_outside_unchanged(before)
        code, output = run("generate.py", "--check", root=self.repo, cwd=self.repo)
        self.assertEqual(code, 0, output)

    def test_a_tracked_link_refuses_generate(self):
        self.repo_copy()
        os.makedirs(os.path.join(self.repo, "docs", "deep"))
        os.symlink("../../AGENTS.md", os.path.join(self.repo, "docs", "deep", "rules.md"))
        os.symlink("AGENTS.md", os.path.join(self.repo, "CLAUDE.md"))
        self.stale(os.path.join(self.repo, "AGENTS.md"))
        commit_all(self.repo)
        for args in ((), ("--check",)):
            with self.subTest(args=args):
                output = self.assert_refused("generate.py", args, ["CLAUDE.md", "docs/deep/rules.md"], root=self.repo)
                self.assertIn("that git tracks", output)

    def test_generate_refuses_a_root_given_with_dot_dot(self):
        # Review of 7787374, P2: --root jump/.. through a link that git tracks is refused, not folded away.
        # Review of #100: the link is made before the commit, so git tracks it. The gate would then refuse the tree for
        # the link as well, so the test asks for the message of the refusal of "..", which comes first.
        self.repo_copy()
        os.mkdir(os.path.join(self.outside, "subdir"))
        os.symlink(os.path.join(self.outside, "subdir"), os.path.join(self.repo, "jump"))
        commit_all(self.repo)
        before = snapshot(self.base)
        for root in (os.path.join(self.repo, "jump", ".."), os.path.join(self.repo, "checks", "..")):
            with self.subTest(root=root):
                code, output = run("generate.py", "--check", "--root", root, cwd=self.repo)
                self.assertNotEqual(code, 0, output)
                self.assertIn('%s holds "..", which is refused' % root, output)
                self.assertNotIn("that git tracks", output)
                self.assertEqual(snapshot(self.base), before)

    def test_generate_refuses_a_root_that_is_a_tracked_link(self):
        # The register's directory, the root of generate.py, is a link that git tracks in another repo, to a copy of
        # Ratchet outside it with a stale block. Run by that path, with or without --root, generate.py refuses, and
        # writes nothing outside.
        self.tree()
        os.mkdir(self.repo)
        copy = os.path.join(self.outside, "ratchet")
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.stale(os.path.join(copy, "AGENTS.md"))
        os.symlink(copy, os.path.join(self.repo, "ratchet"))
        commit_all(self.repo)
        linked = os.path.join(self.repo, "ratchet")
        for root, args in ((linked, ()), (linked, ("--check",)), (ROOT, ("--root", linked))):
            with self.subTest(root=root, args=args):
                before = snapshot(self.base)
                code, output = run("generate.py", *args, root=root, cwd=self.repo)
                self.assertNotEqual(code, 0, output)
                self.assertIn("passes through a symbolic link", output)
                self.assertNotIn("Traceback", output)
                self.assertEqual(snapshot(self.base), before, "nothing in the repo or outside it was written")

    def assert_not_written(self, script, args, root=None):
        before = snapshot(self.base)
        code, output = run(script, *args, root=root or ROOT, cwd=self.repo)
        self.assertNotEqual(code, 0, output)
        self.assertIn("symbolic link", output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(snapshot(self.base), before, "nothing in the repo or outside it was written")
        return output

    def test_generate_does_not_write_through_an_untracked_link(self):
        # The parent directory of a file it writes, the file itself, and the register: none is written through.
        self.repo_copy()
        commit_all(self.repo)
        fixtures = os.path.join(self.repo, "checks", "fixtures", "register")
        shutil.move(fixtures, os.path.join(self.outside, "register"))
        os.remove(os.path.join(self.outside, "register", "clean", "REGISTER.md"))
        os.symlink(os.path.join(self.outside, "register"), fixtures)
        self.assert_not_written("generate.py", (), root=self.repo)
        os.remove(fixtures)
        shutil.move(os.path.join(self.outside, "register"), fixtures)
        git(self.repo, "checkout", "--", "checks/fixtures/register")
        shutil.move(os.path.join(self.repo, "REGISTER.md"), os.path.join(self.outside, "REGISTER.md"))
        self.stale(os.path.join(self.outside, "REGISTER.md"))
        os.symlink(os.path.join(self.outside, "REGISTER.md"), os.path.join(self.repo, "REGISTER.md"))
        self.assert_not_written("generate.py", (), root=self.repo)
        os.remove(os.path.join(self.repo, "REGISTER.md"))
        git(self.repo, "checkout", "--", "REGISTER.md")
        shutil.move(os.path.join(self.repo, "register.json"), os.path.join(self.outside, "register.json"))
        os.symlink(os.path.join(self.outside, "register.json"), os.path.join(self.repo, "register.json"))
        output = self.assert_not_written("generate.py", (), root=self.repo)
        self.assertIn("register.json passes through a symbolic link", output)

    def test_generate_does_not_scan_an_untracked_link(self):
        # templates/LINKED.md leads to a file outside with a stale generated block. The scan of Markdown files does not
        # take it in, so it is neither read nor written.
        self.repo_copy()
        commit_all(self.repo)
        with open(os.path.join(self.outside, "LINKED.md"), "wb") as handle:
            handle.write(b"<!-- generated:version -->\nstale\n<!-- /generated -->\n")
        os.symlink(os.path.join(self.outside, "LINKED.md"), os.path.join(self.repo, "templates", "LINKED.md"))
        os.symlink(self.outside, os.path.join(self.repo, "checks", "linked"))
        before = snapshot(self.base)
        for args in (("--check",), ()):
            with self.subTest(args=args):
                code, output = run("generate.py", *args, root=self.repo, cwd=self.repo)
                self.assertEqual(code, 0, output)
                self.assertNotIn("LINKED", output)
                self.assertEqual(snapshot(self.base), before)

    def test_a_folder_that_git_does_not_track_in_a_parent_repo_is_walked(self):
        # The root is a folder inside another git work tree that git does not track, or that it ignores: git lists
        # nothing there, so every entry is walked, and a link in it refuses.
        for ignored in (False, True):
            with self.subTest(ignored=ignored):
                self.tree()
                os.mkdir(self.repo)
                with open(os.path.join(self.repo, ".gitignore"), "w", encoding="utf-8") as handle:
                    handle.write("ratchet/\n" if ignored else "\n")
                commit_all(self.repo)
                copy = os.path.join(self.repo, "ratchet")
                shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
                self.stale(os.path.join(copy, "AGENTS.md"))
                os.symlink("AGENTS.md", os.path.join(copy, "CLAUDE.md"))
                before = snapshot(self.base)
                code, output = run("generate.py", root=copy, cwd=self.repo)
                self.assertNotEqual(code, 0, output)
                self.assertIn(REFUSED, output)
                self.assertIn("CLAUDE.md", output)
                self.assertIn("every entry was walked", output)
                self.assertEqual(snapshot(self.base), before)

    def test_generate_does_not_scan_a_directory_that_is_an_untracked_link(self):
        # templates/ itself is a link that git does not track, to a copy outside that also holds a stale LINKED.md.
        self.repo_copy()
        commit_all(self.repo)
        templates = os.path.join(self.repo, "templates")
        shutil.move(templates, os.path.join(self.outside, "templates"))
        with open(os.path.join(self.outside, "templates", "LINKED.md"), "wb") as handle:
            handle.write(b"<!-- generated:version -->\nstale\n<!-- /generated -->\n")
        os.symlink(os.path.join(self.outside, "templates"), templates)
        before = snapshot(self.base)
        code, output = run("generate.py", "--check", root=self.repo, cwd=self.repo)
        self.assertNotIn("LINKED", output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(snapshot(self.base), before)
        sys.path.insert(0, HERE)
        import generate
        self.assertNotIn(os.path.join(templates, "LINKED.md"), generate.markdown_files(self.repo))
        self.assertEqual([path for path in generate.markdown_files(self.repo) if path.startswith(templates + os.sep)], [])

    def test_without_git_every_entry_is_walked(self):
        # git cannot be run: the gate walks every entry, as outside a work tree, and refuses the untracked link too.
        self.repo_copy()
        commit_all(self.repo)
        self.tool_links()
        env = dict(os.environ, PATH=scratch_dir(self))
        before = snapshot(self.base)
        code, output = run("generate.py", root=self.repo, cwd=self.repo, env=env)
        self.assertNotEqual(code, 0, output)
        self.assertIn(REFUSED, output)
        self.assertIn("not a git work tree", output)
        self.assertIn(".venv/bin/python", output)
        self.assertEqual(snapshot(self.base), before)


class InitRoot(Trees):
    """init.py takes the root from the directory it runs in as the shell gives it, and refuses one through a link."""

    def test_init_refuses_a_project_whose_directory_is_a_tracked_link(self):
        self.tree()
        os.mkdir(self.repo)
        project = os.path.join(self.outside, "project")
        os.mkdir(project)
        git(project, "init", "-q")
        os.symlink(project, os.path.join(self.repo, "project"))
        commit_all(self.repo)
        linked = os.path.join(self.repo, "project")
        before = snapshot(self.base)
        code, output = run("init.py", cwd=linked, env=dict(os.environ, PWD=linked))
        self.assertEqual(code, 2, output)
        self.assertIn("passes through a symbolic link", output)
        self.assertIn("nothing was written", output)
        self.assertEqual(snapshot(self.base), before, "nothing in the repo or outside it was written")


if __name__ == "__main__":
    unittest.main()
