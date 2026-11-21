"""No check writes through a symbolic link, and every write goes through one place (round 3 of #100).

    python3 -m unittest discover -s checks -v

generate.py, and check_register.py when it writes, refuse to run while git tracks a
symbolic link in the tree, or, outside a git work tree, while any entry is one. Each
writes only through registry.write_file, which refuses unless that gate passed in the
same process and refuses a link on any part of the path it writes. The sweep below
reads every script under checks/ with ast and fails on a call that writes anywhere
but in the places named in WRITERS. The trees with links, and the git work trees,
are made here, in a directory of their own, and never committed: a link in this repo
would make generate.py refuse to run on it. Standard library only.
"""

import ast
import json
import os
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
# generate.py and check_register.py write only through registry.write_file, so they are not named. The test files,
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
# Calls whose mode decides: open(path, mode) and its kin.
OPENERS = {("open",), ("io", "open"), ("builtins", "open"), ("codecs", "open"), ("os", "fdopen")}
# The flags of os.open that only read.
READ_FLAGS = {"O_RDONLY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK", "O_DIRECTORY", "O_BINARY", "O_NOCTTY", "O_NOINHERIT"}
# Modules whose functions write. Importing one under another name, or importing a function from it, would hide a call.
MODULES = set(WRITING_FUNCTIONS) | {"io", "builtins", "codecs", "pathlib"}


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


def writes(call):
    """What the call writes with, as text, or None if it only reads."""
    name = dotted(call.func)
    if isinstance(call.func, ast.Attribute) and call.func.attr in WRITING_METHODS:
        return call.func.attr
    if name and len(name) == 2 and name[1] in WRITING_FUNCTIONS.get(name[0], ()):
        return ".".join(name)
    if name in OPENERS:
        mode, given = argument(call, 1, "mode")
        if not given:
            return None
        if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and not set("wax+") & set(mode.value):
            return None
        return "%s with the mode %s" % (".".join(name), ast.unparse(mode) if hasattr(ast, "unparse") else "?")
    if name == ("os", "open"):
        flags, given = argument(call, 1, "flags")
        named = set()
        for node in ast.walk(flags) if given else ():
            if isinstance(node, ast.Attribute) and node.attr.startswith("O_"):
                named.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("O_"):
                named.add(node.value)
        if named and named <= READ_FLAGS:
            return None
        return "os.open with the flags %s" % ", ".join(sorted(named) or ["unknown"])
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
                    if alias.name in MODULES and alias.asname not in (None, alias.name):
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

    def test_generate_and_check_register_write_only_through_the_one_function(self):
        for name in ("generate.py", "check_register.py"):
            with self.subTest(script=name):
                self.assertEqual(sweep(os.path.join(HERE, name)), [])
        self.assertEqual(sorted(set(where for where, _, _ in sweep(os.path.join(HERE, "registry.py")))), ["write_file"])
        for name in ("generate.py", "check_register.py"):
            with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                self.assertIn("registry.write_file(", handle.read())

    def test_every_place_named_still_writes(self):
        # A name left in WRITERS after its write is gone would let a new write in there unseen.
        for name, allowed in sorted(WRITERS.items()):
            with self.subTest(script=name):
                self.assertEqual(sorted(set(where for where, _, _ in sweep(os.path.join(HERE, name)))), sorted(allowed))

    def test_the_sweep_finds_each_kind_of_write(self):
        source = "\n".join([
            "import os, shutil, tempfile, pathlib",
            "def a(p):",
            "    open(p, 'w')", "    open(p, mode='ab')", "    open(p, 'r+')", "    open(p, 'x')", "    open(p, m)",
            "    os.fdopen(d, 'wb')", "    os.open(p, os.O_WRONLY | os.O_CREAT)", "    os.open(p, flags)",
            "    os.open(p, os.O_RDONLY | getattr(os, 'O_APPEND', 0))",
            "    pathlib.Path(p).write_text('x')", "    q.write_bytes(b'')", "    os.replace(p, q)", "    os.rename(p, q)",
            "    shutil.copy(p, q)", "    shutil.copyfile(p, q)", "    shutil.move(p, q)", "    os.makedirs(p)", "    os.symlink(p, q)",
            "    tempfile.mkdtemp()",
            "import shutil as s", "from os import replace", "opener = open",
            "def b(p):",
            "    open(p)", "    open(p, 'rb')", "    os.open(p, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))", "    text.replace('a', 'b')",
            "    opener.open(request)", "    handle.write('x')",
        ])
        scratch = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, scratch)
        path = os.path.join(scratch, "sample.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(source + "\n")
        found = sweep(path)
        self.assertEqual(len([where for where, _, _ in found if where == "a"]), 19, found)
        self.assertEqual([where for where, _, _ in found if where == "b"], [], found)
        self.assertEqual(len([where for where, _, _ in found if where in ("<module>", "?")]), 3, found)


class WriteFile(unittest.TestCase):
    """registry.write_file, in this process."""

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, self.base)
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
        self.base = self.scratch()
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
        with open(path, "rb") as handle:
            data = handle.read()
        with open(path, "wb") as handle:
            handle.write(data.replace(b"| built |", b"| text only for now |", 1))

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


class LinksRefused(Trees):
    """Outside a git work tree the gate walks every entry and refuses every link."""

    def test_check_register_refuses_to_write_in_a_tree_with_a_link_to_a_file_outside(self):
        self.register_tree()
        with open(os.path.join(self.outside, "notes.md"), "wb") as handle:
            handle.write(b"Outside the repo.\n")
        os.mkdir(os.path.join(self.repo, "docs"))
        os.symlink(os.path.join(self.outside, "notes.md"), os.path.join(self.repo, "docs", "notes.md"))
        for args in (("--write-block",), ("--write", "REGISTER.md"), ("--write", "REGISTER.md", "--write-block")):
            with self.subTest(args=args):
                self.assert_refused("check_register.py", ("register.json",) + args, ["docs/notes.md"])

    def test_check_register_refuses_to_write_when_the_instruction_file_is_a_link_outside(self):
        self.register_tree()
        shutil.move(os.path.join(self.repo, "AGENTS.md"), os.path.join(self.outside, "AGENTS.md"))
        os.symlink(os.path.join(self.outside, "AGENTS.md"), os.path.join(self.repo, "AGENTS.md"))
        self.assert_refused("check_register.py", ("register.json", "--write-block"), ["AGENTS.md"])

    def test_check_register_refuses_to_write_under_a_linked_parent_directory(self):
        self.register_tree()
        shutil.copyfile(os.path.join(self.repo, "AGENTS.md"), os.path.join(self.outside, "AGENTS.md"))
        os.symlink(self.outside, os.path.join(self.repo, "link"))
        self.assert_refused("check_register.py", ("register.json", "--write", "link/REGISTER.md"), ["link"])
        self.set_instructions("link/AGENTS.md")
        self.assert_refused("check_register.py", ("register.json", "--write-block"), ["link"])

    def test_check_register_refuses_to_write_in_a_tree_with_a_link_inside_it(self):
        self.register_tree()
        os.symlink("AGENTS.md", os.path.join(self.repo, "CLAUDE.md"))
        for args in (("--write-block",), ("--write", "REGISTER.md")):
            with self.subTest(args=args):
                self.assert_refused("check_register.py", ("register.json",) + args, ["CLAUDE.md"])

    def test_the_refusal_comes_before_anything_else(self):
        # The register fails too, and the link is all that is said: nothing else was read or checked.
        self.register_tree()
        os.symlink("AGENTS.md", os.path.join(self.repo, "CLAUDE.md"))
        with open(os.path.join(self.repo, "register.json"), "wb") as handle:
            handle.write(b"not json")
        output = self.assert_refused("check_register.py", ("register.json", "--write-block"), ["CLAUDE.md"])
        self.assertNotIn("not a valid data file", output)

    def test_check_register_compares_in_a_tree_with_a_link_inside_it(self):
        # The compare mode writes nothing, so it does not walk: a project with CLAUDE.md -> AGENTS.md can run it.
        self.register_tree()
        with open(os.path.join(self.repo, "AGENTS.md"), "wb") as handle:
            handle.write(self.fixture_bytes("register/block-clean/AGENTS.md"))
        os.symlink("AGENTS.md", os.path.join(self.repo, "CLAUDE.md"))
        before = snapshot(self.base)
        code, output = run("check_register.py", "register.json", "--markdown", "REGISTER.md", cwd=self.repo)
        self.assertEqual(code, 0, output)
        self.assertIn("AGENTS.md: the block between the markers is what register.json generates", output)
        self.assertEqual(snapshot(self.base), before)

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

    def test_generate_runs_on_a_copy_without_links(self):
        self.repo_copy()
        code, output = run("generate.py", "--check", root=self.repo, cwd=self.repo)
        self.assertEqual(code, 0, output)

    def test_the_message_says_every_entry_was_walked_outside_a_git_work_tree(self):
        self.register_tree()
        os.makedirs(os.path.join(self.repo, ".venv", "bin"))
        os.symlink(sys.executable, os.path.join(self.repo, ".venv", "bin", "python"))
        output = self.assert_refused("check_register.py", ("register.json", "--write-block"), [".venv/bin/python"])
        self.assertIn("not a git work tree", output)


class GitLinks(Trees):
    """In a git work tree, the gate refuses only links that git tracks. Each tree is made with git init when the test
    runs. Links that the user's own tools make, untracked, pass the gate, and write_file refuses each on its own path."""

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

    def test_check_register_writes_past_untracked_links_of_tools(self):
        self.register_tree()
        commit_all(self.repo)
        self.tool_links()
        before = snapshot(self.base)
        code, output = run("check_register.py", "register.json", "--write", "REGISTER.md", "--write-block", cwd=self.repo)
        self.assertEqual(code, 0, output)
        self.assertIn("wrote the block in", output)
        self.assert_outside_unchanged(before)
        with open(os.path.join(self.repo, "AGENTS.md"), "rb") as handle:
            self.assertEqual(handle.read(), self.fixture_bytes("register/block-clean/AGENTS.md"))

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

    def test_a_tracked_link_anywhere_refuses(self):
        self.register_tree()
        os.makedirs(os.path.join(self.repo, "docs", "deep"))
        os.symlink("../../AGENTS.md", os.path.join(self.repo, "docs", "deep", "rules.md"))
        commit_all(self.repo)
        for args in (("--write-block",), ("--write", "REGISTER.md")):
            with self.subTest(args=args):
                output = self.assert_refused("check_register.py", ("register.json",) + args, ["docs/deep/rules.md"])
                self.assertIn("that git tracks", output)

    def test_a_tracked_link_refuses_generate(self):
        self.repo_copy()
        os.symlink("AGENTS.md", os.path.join(self.repo, "CLAUDE.md"))
        self.stale(os.path.join(self.repo, "AGENTS.md"))
        commit_all(self.repo)
        for args in ((), ("--check",)):
            with self.subTest(args=args):
                output = self.assert_refused("generate.py", args, ["CLAUDE.md"], root=self.repo)
                self.assertIn("that git tracks", output)

    def assert_not_written(self, script, args, root=None):
        before = snapshot(self.base)
        code, output = run(script, *args, root=root or ROOT, cwd=self.repo)
        self.assertNotEqual(code, 0, output)
        self.assertIn("is a symbolic link", output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(snapshot(self.base), before, "nothing in the repo or outside it was written")
        return output

    def test_an_untracked_link_as_a_parent_directory_of_a_write_target_is_not_written_through(self):
        self.register_tree()
        commit_all(self.repo)
        os.symlink(self.outside, os.path.join(self.repo, "link"))
        self.assert_not_written("check_register.py", ("register.json", "--write", "link/REGISTER.md"))
        self.set_instructions("link/AGENTS.md")
        shutil.copyfile(os.path.join(self.repo, "AGENTS.md"), os.path.join(self.outside, "AGENTS.md"))
        self.assert_not_written("check_register.py", ("register.json", "--write-block"))

    def test_an_untracked_link_as_the_write_target_is_not_written_through(self):
        self.register_tree()
        commit_all(self.repo)
        shutil.move(os.path.join(self.repo, "REGISTER.md"), os.path.join(self.outside, "REGISTER.md"))
        os.symlink(os.path.join(self.outside, "REGISTER.md"), os.path.join(self.repo, "REGISTER.md"))
        self.assert_not_written("check_register.py", ("register.json", "--write", "REGISTER.md"))
        shutil.move(os.path.join(self.repo, "AGENTS.md"), os.path.join(self.outside, "AGENTS.md"))
        os.symlink(os.path.join(self.outside, "AGENTS.md"), os.path.join(self.repo, "AGENTS.md"))
        self.assert_not_written("check_register.py", ("register.json", "--write-block"))

    def test_generate_does_not_write_through_an_untracked_link(self):
        # The parent directory of a file it writes, and the file itself: neither is written through.
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

    def test_without_git_every_entry_is_walked(self):
        # git cannot be run: the gate walks every entry, as outside a work tree, and refuses the untracked link too.
        self.register_tree()
        commit_all(self.repo)
        self.tool_links()
        empty = self.scratch()
        env = dict(os.environ, PATH=empty)
        before = snapshot(self.base)
        code, output = run("check_register.py", "register.json", "--write-block", cwd=self.repo, env=env)
        self.assertNotEqual(code, 0, output)
        self.assertIn(REFUSED, output)
        self.assertIn("not a git work tree", output)
        self.assertIn(".venv/bin/python", output)
        self.assertEqual(snapshot(self.base), before)

    def test_compare_mode_passes_with_a_tracked_link(self):
        self.register_tree()
        with open(os.path.join(self.repo, "AGENTS.md"), "wb") as handle:
            handle.write(self.fixture_bytes("register/block-clean/AGENTS.md"))
        os.symlink("AGENTS.md", os.path.join(self.repo, "CLAUDE.md"))
        commit_all(self.repo)
        before = snapshot(self.base)
        code, output = run("check_register.py", "register.json", "--markdown", "REGISTER.md", cwd=self.repo)
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.base), before)


if __name__ == "__main__":
    unittest.main()
