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

    def run_copy(self, *args, commit=None):
        command = [sys.executable, "-I", COPY, commit or self.commit, "--repository", self.source] + list(args)
        if "--" not in args:
            command += ["--", "register.json"]
        result = subprocess.run(command, cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)
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
        with open(self.path(COPY), "a", encoding="utf-8") as handle:
            handle.write("# a line of the project's own\n")
        code, output = self.run_copy()
        self.assertEqual(code, 2, output)
        self.assertIn("is not checks/run_pinned.py of commit %s" % self.commit, output)
        self.assertIn("--no-replace-objects show %s:checks/run_pinned.py >" % self.commit, output)

    def test_a_store_that_is_not_a_repo_of_its_own_is_refused(self):
        # A plain folder at .ratchet inside the project's repo: never taken for the project's repo.
        os.mkdir(self.path(".ratchet"))
        code, output = self.run_copy()
        self.assertEqual(code, 2, output)
        self.assertIn(".ratchet exists and is not a git repo of its own", output)

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
        self.assertNotIn(self.INSERT, open(os.path.join(HERE, "run_pinned.py"), encoding="utf-8").read(),
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
