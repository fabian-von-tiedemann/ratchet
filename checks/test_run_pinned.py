"""checks/run_pinned.py runs the register check of the pinned commit, and never an edited or planted file.

    python3 -m unittest discover -s checks -v

Each test makes a project of its own: a git repo with a register.json, the copy of run_pinned.py taken from the
pinned commit, and a store, a clone of a copy of this checkout with one commit. Standard library only.
"""

import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import run_pinned  # noqa: E402
from test_init import git  # noqa: E402

EDITED = "import sys\nprint('EDITED CHECK RAN')\nsys.exit(0)\n"
PLANTED = "print('PLANTED MODULE RAN')\nraise SystemExit(0)\n"
COPY = os.path.join(".github", "ratchet", "run_pinned.py")


class RunPinned(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="ratchet-test-")
        cls.source = os.path.join(cls.base, "ratchet")
        shutil.copytree(ROOT, cls.source, ignore=shutil.ignore_patterns(".git", "__pycache__", "fixtures", ".claude"))
        git(cls.source, "init", "-q")
        git(cls.source, "add", "-A")
        git(cls.source, "commit", "-q", "-m", "Ratchet as it stands")
        cls.commit = git(cls.source, "rev-parse", "HEAD")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base)

    def setUp(self):
        directory = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, directory)
        self.project = os.path.join(directory, "project")
        os.mkdir(self.project)
        git(self.project, "init", "-q")
        with open(os.path.join(ROOT, "templates", "register.json"), encoding="utf-8") as handle:
            register = json.load(handle)
        register["project"] = "demo"
        self.register(register)
        os.makedirs(self.path(".github", "ratchet"))
        with open(self.path(COPY), "wb") as handle:
            handle.write(subprocess.run(["git", "-C", self.source, "show", "%s:checks/run_pinned.py" % self.commit],
                                        stdout=subprocess.PIPE, check=True).stdout)

    def path(self, *parts):
        return os.path.join(self.project, *parts)

    def register(self, register):
        with open(self.path("register.json"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps(register, indent=2) + "\n")

    def failing(self):
        """A register that the honest check refuses: it adopts nothing."""
        with open(self.path("register.json"), encoding="utf-8") as handle:
            register = json.load(handle)
        register["adopted"] = []
        self.register(register)

    def run_copy(self, *args, commit=None, env=None):
        command = [sys.executable, "-I", COPY, commit or self.commit, "--repository", self.source] + list(args)
        if "--" not in args:
            command += ["--", "register.json"]
        result = subprocess.run(command, cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, env=env)
        return result.returncode, result.stdout

    def clone_store(self):
        git(self.project, "clone", "-q", self.source, ".ratchet")

    def test_the_honest_path_passes_and_a_register_that_fails_fails(self):
        self.clone_store()
        code, output = self.run_copy()
        self.assertEqual(code, 0, output)
        self.assertIn("run_pinned: Ratchet at %s, every object hashed" % self.commit, output)
        self.failing()
        code, output = self.run_copy()
        self.assertEqual(code, 1, output)
        self.assertIn("no rules from Ratchet", output)

    def test_an_edited_check_hidden_by_assume_unchanged_is_never_run(self):
        # The finding from a real adoption: the edit is invisible to git status, and HEAD still matches the pin, so the
        # old step ran it. The store is read as objects only.
        self.clone_store()
        self.failing()
        check = self.path(".ratchet", "checks", "check_register.py")
        with open(check, "w", encoding="utf-8") as handle:
            handle.write(EDITED)
        git(self.path(".ratchet"), "update-index", "--assume-unchanged", "checks/check_register.py")
        self.assertEqual(git(self.path(".ratchet"), "status", "--porcelain"), "")
        self.assertEqual(git(self.path(".ratchet"), "rev-parse", "HEAD"), self.commit)
        direct = subprocess.run([sys.executable, "-E", "-s", check, "register.json"], cwd=self.project,
                                stdout=subprocess.PIPE, universal_newlines=True)
        self.assertEqual((direct.returncode, direct.stdout), (0, "EDITED CHECK RAN\n"))
        code, output = self.run_copy()
        self.assertEqual(code, 1, output)
        self.assertNotIn("EDITED", output)
        self.assertIn("no rules from Ratchet", output)

    def test_a_module_planted_beside_the_check_or_beside_the_copy_is_never_imported(self):
        self.clone_store()
        self.failing()
        with open(self.path(".ratchet", ".git", "info", "exclude"), "a", encoding="utf-8") as handle:
            handle.write("checks/argparse.py\n")
        for path in (self.path(".ratchet", "checks", "argparse.py"), self.path(".ratchet", "checks", "registry.py"),
                     self.path(".github", "ratchet", "hashlib.py"), self.path(".github", "ratchet", "subprocess.py"),
                     self.path("argparse.py")):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(PLANTED)
        code, output = self.run_copy()
        self.assertEqual(code, 1, output)
        self.assertNotIn("PLANTED", output)
        self.assertIn("no rules from Ratchet", output)

    def test_a_missing_store_is_cloned_and_a_store_without_the_commit_fetches_it(self):
        code, output = self.run_copy()
        self.assertEqual(code, 0, output)
        self.assertTrue(os.path.isdir(self.path(".ratchet", ".git")))
        self.assertFalse(os.path.exists(self.path(".ratchet", "checks")), "the clone has no checkout")
        other = os.path.join(self.project, "empty-store")
        os.mkdir(other)
        git(other, "init", "-q")
        code, output = self.run_copy("--store", "empty-store")
        self.assertEqual(code, 0, output)

    def test_a_wrong_or_missing_commit_is_refused(self):
        self.clone_store()
        tree = git(self.source, "rev-parse", self.commit + "^{tree}")
        for commit, said in (("abc", "is not a commit: a commit is 40 characters"),
                             (self.commit.upper(), "is not a commit: a commit is 40 characters"),
                             ("0" * 40, "is not in .ratchet, and cannot be fetched"),
                             (tree, "is not a commit in .ratchet, it is a tree")):
            with self.subTest(commit=commit):
                code, output = self.run_copy(commit=commit)
                self.assertEqual(code, 2, output)
                self.assertIn(said, output)
                self.assertIn("run_pinned: the check did not run", output)

    def test_a_corrupt_object_is_refused(self):
        # A copy of the source repo, whose objects are loose: the blob of the check is swapped for other bytes under its
        # name. git cat-file reads it as it is, and run_pinned hashes it and refuses.
        shutil.copytree(self.source, self.path(".ratchet"))
        self.failing()
        blob = git(self.source, "rev-parse", "%s:checks/check_register.py" % self.commit)
        loose = self.path(".ratchet", ".git", "objects", blob[:2], blob[2:])
        self.assertTrue(os.path.isfile(loose))
        os.chmod(loose, 0o644)
        data = EDITED.encode("utf-8")
        with open(loose, "wb") as handle:
            handle.write(zlib.compress(b"blob %d\0" % len(data) + data))
        code, output = self.run_copy()
        self.assertEqual(code, 2, output)
        self.assertIn("object %s is corrupt in the store" % blob, output)
        self.assertNotIn("EDITED", output)

    def test_a_replace_ref_is_not_followed(self):
        self.clone_store()
        self.failing()
        store = self.path(".ratchet")
        blob = git(store, "rev-parse", "%s:checks/check_register.py" % self.commit)
        with open(os.path.join(self.project, "edited.py"), "w", encoding="utf-8") as handle:
            handle.write(EDITED)
        other = git(store, "hash-object", "-w", os.path.join(self.project, "edited.py"))
        git(store, "replace", blob, other)
        code, output = self.run_copy()
        self.assertEqual(code, 1, output)
        self.assertNotIn("EDITED", output)

    def test_a_copy_that_is_not_the_pinned_commits_is_refused(self):
        self.clone_store()
        with open(self.path(COPY), "rb") as handle:
            whole = handle.read()
        with open(self.path(COPY), "wb") as handle:
            handle.write(whole.replace(b"\nimport sys\n", b"\n# a line of the project's own\nimport sys\n", 1))
        code, output = self.run_copy()
        self.assertEqual(code, 2, output)
        self.assertIn("is not checks/run_pinned.py of commit %s" % self.commit, output)
        self.assertIn("Copy it again, from the project's root: " + self.commands()[0], output)

    def test_a_store_that_is_not_a_repo_of_its_own_is_refused(self):
        # A plain folder at .ratchet inside the project's repo: never taken for the project's repo.
        os.mkdir(self.path(".ratchet"))
        code, output = self.run_copy()
        self.assertEqual(code, 2, output)
        self.assertIn(".ratchet exists and is not a git repo of its own", output)

    def marker_program(self):
        """A program that writes a line to a marker file each time it runs, and fails. Returns (program, marker)."""
        marker = os.path.join(self.project, "MARKER")
        program = os.path.join(os.path.dirname(self.project), "marker.sh")
        with open(program, "w", encoding="utf-8") as handle:
            handle.write('#!/bin/sh\necho "ran: $0 $*" >> %s\nexit 1\n' % marker)
        os.chmod(program, 0o755)
        return program, marker

    def hostile(self, git_config, program, url):
        """Config in the file git_config that runs program at every point git offers one, and sends url elsewhere."""
        hooks = os.path.join(os.path.dirname(git_config), "hooks-of-" + os.path.basename(git_config))
        os.makedirs(hooks)
        for hook in ("reference-transaction", "post-checkout", "post-merge", "pre-auto-gc", "post-index-change"):
            os.symlink(program, os.path.join(hooks, hook))
        for key, value in (("core.sshCommand", program), ("core.fsmonitor", program), ("core.hooksPath", hooks),
                           ("credential.helper", program), ("core.askPass", program), ("core.pager", program),
                           ("core.alternateRefsCommand", program), ("protocol.allow", "always"),
                           ("remote.origin.uploadpack", program), ("uploadpack.packObjectsHook", program),
                           ("url.ext::%s %%S.insteadOf" % program, url), ("gc.auto", "1"),
                           ("filter.evil.smudge", program), ("filter.evil.process", program)):
            subprocess.run(["git", "config", "--file", git_config, "--add", key, value], check=True)

    def test_the_store_config_never_runs_a_program_even_when_an_object_is_missing_from_a_promisor_store(self):
        # Codex's case: the commit is in the store, a blob is not, and the store is a partial clone. Before, git cat-file
        # started a lazy fetch, and the store's core.sshCommand ran before the verification refused.
        program, marker = self.marker_program()
        self.clone_store()
        store = self.path(".ratchet")
        blob = git(store, "rev-parse", "%s:checks/check_register.py" % self.commit)
        os.remove(os.path.join(store, ".git", "objects", blob[:2], blob[2:]))
        config = os.path.join(store, ".git", "config")
        for key, value in (("core.repositoryformatversion", "1"), ("extensions.partialClone", "origin"),
                           ("remote.origin.url", "ssh://git@example.invalid/ratchet"), ("remote.origin.promisor", "true"),
                           ("remote.origin.partialclonefilter", "blob:none")):
            subprocess.run(["git", "config", "--file", config, key, value], check=True)
        self.hostile(config, program, self.source)
        code, output = self.run_copy()
        self.assertEqual(code, 2, output)
        self.assertIn("object %s is missing from the store" % blob, output)
        self.assertFalse(os.path.exists(marker), open(marker).read() if os.path.exists(marker) else "")

    def test_no_config_of_the_store_the_user_or_the_system_runs_a_program_on_read_or_fetch(self):
        # A store without the commit, so that it is fetched, and every place git takes a program from, set in the
        # store's config, in the user's, through HOME, XDG_CONFIG_HOME, GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM, and
        # through GIT_CONFIG_PARAMETERS: none runs, and the fetch is from the repository named, not a rewritten url.
        program, marker = self.marker_program()
        store = self.path("empty-store")
        os.mkdir(store)
        git(store, "init", "-q")
        self.hostile(os.path.join(store, ".git", "config"), program, self.source)
        home = os.path.join(os.path.dirname(self.project), "home")
        os.makedirs(os.path.join(home, "git"))
        for name in (".gitconfig", os.path.join("git", "config"), "global", "system"):
            self.hostile(os.path.join(home, name), program, self.source)
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home, GIT_CONFIG_GLOBAL=os.path.join(home, "global"),
                   GIT_CONFIG_SYSTEM=os.path.join(home, "system"), GIT_CONFIG_NOSYSTEM="0",
                   GIT_CONFIG_PARAMETERS="'core.sshcommand'='%s'" % program)
        self.failing()
        code, output = self.run_copy("--store", "empty-store", env=env)
        self.assertEqual(code, 1, output)
        self.assertIn("no rules from Ratchet", output)
        self.assertFalse(os.path.exists(marker), open(marker).read() if os.path.exists(marker) else "")
        # The commit is now in the store, so a second run reads it without a fetch, with the same config in place.
        code, output = self.run_copy("--store", "empty-store", env=env)
        self.assertEqual(code, 1, output)
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(git(store, "cat-file", "-t", self.commit), "commit")

    def test_a_missing_store_is_cloned_with_no_config_of_the_users(self):
        program, marker = self.marker_program()
        home = os.path.join(os.path.dirname(self.project), "home")
        os.mkdir(home)
        self.hostile(os.path.join(home, ".gitconfig"), program, self.source)
        code, output = self.run_copy(env=dict(os.environ, HOME=home))
        self.assertEqual(code, 0, output)
        self.assertFalse(os.path.exists(marker), open(marker).read() if os.path.exists(marker) else "")

    def commands(self, store=".ratchet"):
        """(the copy command and the run command adopt mode prints), for the blob of run_pinned.py in the commit."""
        blob = git(self.source, "rev-parse", "%s:checks/run_pinned.py" % self.commit)
        objects = os.path.join(store, ".git", "objects")
        return (run_pinned.copy_command(objects, self.commit, blob, COPY.replace(os.sep, "/")),
                run_pinned.run_command(self.commit, blob, COPY.replace(os.sep, "/")))

    def shell(self, command, shell="sh", env=None):
        result = subprocess.run([shell, "-c", command], cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, env=env)
        return result.returncode, result.stdout

    def shells(self):
        """sh, and bash and dash where they are installed: a local check script may run under any of them."""
        return ["sh"] + [name for name in ("bash", "dash") if shutil.which(name)]

    def test_the_printed_run_line_stops_a_check_script_on_a_runner_that_is_not_the_pinned_one(self):
        # Codex's and Astra's case: with "<hash check> && <run>" a failing hash check is the left side of &&, which set -e
        # does not stop on, so a script with set -eu went on and exited 0 with an empty runner.
        self.clone_store()
        with open(self.path(COPY), "rb") as handle:
            whole = handle.read()
        _, run = self.commands()
        for name, data in (("empty", b""), ("cut short", whole[:len(whole) // 2]),
                           ("another", b"print('ANOTHER RUNNER RAN')\n")):
            with open(self.path(COPY), "wb") as handle:
                handle.write(data)
            for shell in self.shells():
                for start in ("set -eu\n", "set -e\n", ""):
                    with self.subTest(runner=name, shell=shell, start=start):
                        code, output = self.shell(start + run + "\necho LATER CHECK PASSED\n", shell)
                        self.assertNotEqual(code, 0, output)
                        self.assertNotIn("LATER CHECK PASSED", output)
                        self.assertNotIn("ANOTHER RUNNER RAN", output)
                        self.assertIn("is not checks/run_pinned.py of commit %s" % self.commit, output)
        # The pinned runner passes the line, and the script goes on.
        with open(self.path(COPY), "wb") as handle:
            handle.write(whole)
        for shell in self.shells():
            with self.subTest(shell=shell):
                code, output = self.shell("set -eu\n" + run + "\necho LATER CHECK PASSED\n", shell)
                self.assertEqual(code, 0, output)
                self.assertIn("LATER CHECK PASSED", output)

    def test_the_copy_command_reads_no_git_variable_of_the_environment(self):
        # Codex's and Astra's case: GIT_COMMON_DIR was left in effect, so git read the config of a repo it was never
        # given, here one that no git can read.
        self.clone_store()
        os.remove(self.path(COPY))
        other = os.path.join(os.path.dirname(self.project), "other")
        subprocess.run(["git", "init", "-q", "--bare", other], check=True)
        subprocess.run(["git", "config", "--file", os.path.join(other, "config"), "core.repositoryformatversion", "999"],
                       check=True)
        # Before the fix, the copy command fails on this store: git refuses a repository format it does not know.
        failing = subprocess.run(["git", "--git-dir", other, "rev-parse", "--git-dir"], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertNotEqual(failing.returncode, 0, failing.stdout)
        copy, _ = self.commands()
        hostile = {"GIT_COMMON_DIR": other, "GIT_DIR": other, "GIT_WORK_TREE": other,
                   "GIT_OBJECT_DIRECTORY": os.path.join(other, "objects"),
                   "GIT_ALTERNATE_OBJECT_DIRECTORIES": os.path.join(other, "objects"),
                   "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.repositoryformatversion",
                   "GIT_CONFIG_VALUE_0": "999", "GIT_CONFIG_PARAMETERS": "'core.repositoryformatversion'='999'",
                   "GIT_INDEX_FILE": os.path.join(other, "index"), "GIT_NAMESPACE": "other"}
        for shell in self.shells():
            for name, value in sorted(hostile.items()) + [("all", None)]:
                with self.subTest(shell=shell, variable=name):
                    env = dict(os.environ, **(hostile if value is None else {name: value}))
                    code, output = self.shell(copy, shell, env)
                    self.assertEqual(code, 0, output)
                    with open(self.path(COPY), "rb") as handle:
                        copied = handle.read()
                    self.assertEqual(copied, subprocess.run(
                        ["git", "-C", self.source, "show", "%s:checks/run_pinned.py" % self.commit],
                        stdout=subprocess.PIPE, check=True).stdout)
                    os.remove(self.path(COPY))

    def test_the_printed_copy_command_copies_the_pinned_runner_and_the_printed_step_runs_it(self):
        self.clone_store()
        os.remove(self.path(COPY))
        copy, run = self.commands()
        code, output = self.shell(copy)
        self.assertEqual(code, 0, output)
        with open(self.path(COPY), "rb") as handle:
            copied = handle.read()
        self.assertEqual(copied, subprocess.run(["git", "-C", self.source, "show", "%s:checks/run_pinned.py" % self.commit],
                                                stdout=subprocess.PIPE, check=True).stdout)
        self.assertEqual(os.listdir(self.path(".github", "ratchet")), ["run_pinned.py"])
        code, output = self.shell(run)
        self.assertEqual(code, 0, output)
        self.assertIn("run_pinned: Ratchet at %s, every object hashed" % self.commit, output)
        self.failing()
        code, output = self.shell(run)
        self.assertEqual(code, 1, output)

    def test_the_copy_command_refuses_a_runner_swapped_in_the_store_for_an_empty_blob(self):
        # Astra's case: the runner's loose object replaced by a validly compressed empty blob. Before, the copy made an
        # empty runner, and running it exited 0 for an invalid register.
        shutil.copytree(self.source, self.path(".ratchet"))
        self.failing()
        os.remove(self.path(COPY))
        blob = git(self.source, "rev-parse", "%s:checks/run_pinned.py" % self.commit)
        loose = self.path(".ratchet", ".git", "objects", blob[:2], blob[2:])
        os.chmod(loose, 0o644)
        with open(loose, "wb") as handle:
            handle.write(zlib.compress(b"blob 0\0"))
        copy, run = self.commands()
        code, output = self.shell(copy)
        self.assertNotEqual(code, 0, output)
        self.assertIn("run_pinned.py was not copied", output)
        self.assertFalse(os.path.lexists(self.path(COPY)))
        self.assertEqual(os.listdir(self.path(".github", "ratchet")), [])
        # And a runner that is missing, empty, or cut short, fails the step: it never passes a register that fails.
        code, output = self.shell(run)
        self.assertNotEqual(code, 0, output)
        self.assertIn("is not checks/run_pinned.py of commit %s" % self.commit, output)
        with open(self.path(COPY), "wb"):
            pass
        code, output = self.shell(run)
        self.assertNotEqual(code, 0, output)
        self.assertIn("is not checks/run_pinned.py of commit %s" % self.commit, output)

    def test_a_runner_cut_short_refuses_and_the_step_refuses_it(self):
        self.clone_store()
        self.failing()
        with open(self.path(COPY), "rb") as handle:
            whole = handle.read()
        _, run = self.commands()
        # Cut after its own guard and before main runs, and cut before the guard: only the step catches the second.
        guard = whole.index(b"\ndef parse(")
        for cut, direct in ((guard, 2), (whole.index(b"\nimport sys\n"), 0)):
            with self.subTest(cut=cut):
                with open(self.path(COPY), "wb") as handle:
                    handle.write(whole[:cut + 1])
                code, output = self.run_copy()
                self.assertEqual(code, direct, output)
                if direct:
                    self.assertIn("is cut short", output)
                code, output = self.shell(run)
                self.assertNotEqual(code, 0, output)
                self.assertNotIn("no rules from Ratchet", output)

    def test_the_command_line(self):
        for argv in ([], [self.commit], ["--", "register.json"], [self.commit, "--store", "--"],
                     [self.commit, "extra", "--", "register.json"]):
            with self.subTest(argv=argv):
                with self.assertRaises(run_pinned.Refused):
                    run_pinned.parse(argv)
        self.assertEqual(run_pinned.parse([self.commit, "--", "register.json", "--markdown", "REGISTER.md"]),
                         (self.commit, ".ratchet", run_pinned.REPOSITORY, ["register.json", "--markdown", "REGISTER.md"]))

    def test_the_repository_is_the_one_init_prints(self):
        import init
        self.assertEqual(run_pinned.REPOSITORY, init.REPOSITORY)


class Isolated(unittest.TestCase):
    """Every script in checks/ runs under python3 -I, which leaves the script's directory out of sys.path: a project that
    runs a check isolated, as the finding from a real adoption did, got ModuleNotFoundError: No module named 'registry'."""

    INSERT = "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"

    def scripts(self):
        names = sorted(name for name in os.listdir(HERE) if name.endswith(".py") and not name.startswith("test_"))
        self.assertIn("check_register.py", names)
        return names

    def test_every_script_that_imports_one_beside_it_puts_its_own_directory_on_the_path_first(self):
        siblings = {name[:-3] for name in self.scripts()}
        for name in self.scripts():
            with self.subTest(script=name):
                with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                    text = handle.read()
                imports = [match.start() for match in re.finditer(r"(?m)^(?:import|from) (\w+)", text)
                           if match.group(1) in siblings]
                if imports:
                    self.assertIn(self.INSERT, text)
                    self.assertLess(text.index(self.INSERT), imports[0])
        with open(os.path.join(HERE, "run_pinned.py"), encoding="utf-8") as handle:
            self.assertNotIn(self.INSERT, handle.read(),
                             "run_pinned.py imports nothing from beside it, so -I keeps a planted module out")

    def test_every_script_with_a_command_line_starts_under_python_minus_i(self):
        directory = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, directory)
        for name in self.scripts():
            with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                text = handle.read()
            if "\nimport argparse\n" not in text or "__main__" not in text:
                continue
            with self.subTest(script=name):
                result = subprocess.run([sys.executable, "-I", os.path.join(HERE, name), "--help"], cwd=directory,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                                        timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertNotIn("ModuleNotFoundError", result.stdout)

    def test_the_register_check_runs_under_python_minus_i(self):
        result = subprocess.run([sys.executable, "-I", os.path.join(HERE, "check_register.py"), "register.json",
                                 "--markdown", "REGISTER.md"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
