"""checks/run_pinned.py runs the register check of the pinned commit, and never an edited or planted file.

    python3 -m unittest discover -s checks -v

Each test makes a project of its own: a git repo with a register.json, the copy of run_pinned.py taken from the
pinned commit, and a store, a clone of a copy of this checkout with one commit. Standard library only.
"""

import ast
import json
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
import testing  # noqa: E402
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

    def test_the_printed_local_line_stops_a_check_script_with_set_e_or_without(self):
        # An adoption report on 0.12: the line for a local check script assumed set -e, so in a script without it a
        # register that fails the check went on to the rest of the script, to "all green".
        self.clone_store()
        self.failing()
        blob = git(self.source, "rev-parse", "%s:checks/run_pinned.py" % self.commit)
        _, run = self.commands()
        local = run_pinned.local_line(self.commit, blob, COPY.replace(os.sep, "/"))
        for shell in self.shells():
            with self.subTest(shell=shell, line="the step's"):
                # The step's line alone does not stop a script without set -e: this is what the local line is for.
                code, output = self.shell(run + "\necho ALL GREEN\n", shell)
                self.assertEqual(code, 0, output)
                self.assertIn("ALL GREEN", output)
            for start in ("set -eu\n", "set -e\n", ""):
                with self.subTest(shell=shell, start=start):
                    code, output = self.shell(start + local + "\necho ALL GREEN\n", shell)
                    self.assertEqual(code, 1, output)
                    self.assertIn("no rules from Ratchet", output)
                    self.assertNotIn("ALL GREEN", output)
        # A runner that is not the pinned one stops it too, and a register that passes goes on.
        with open(self.path(COPY), "wb") as handle:
            handle.write(b"print('ANOTHER RUNNER RAN')\n")
        for shell in self.shells():
            with self.subTest(shell=shell, runner="another"):
                code, output = self.shell(local + "\necho ALL GREEN\n", shell)
                self.assertEqual(code, 1, output)
                self.assertNotIn("ANOTHER RUNNER RAN", output)
                self.assertNotIn("ALL GREEN", output)
        with open(self.path(COPY), "wb") as handle:
            handle.write(subprocess.run(["git", "-C", self.source, "show", "%s:checks/run_pinned.py" % self.commit],
                                        stdout=subprocess.PIPE, check=True).stdout)
        with open(os.path.join(ROOT, "templates", "register.json"), encoding="utf-8") as handle:
            register = json.load(handle)
        register["project"] = "demo"
        self.register(register)
        for shell in self.shells():
            for start in ("set -eu\n", ""):
                with self.subTest(shell=shell, start=start, register="passes"):
                    code, output = self.shell(start + local + "\necho ALL GREEN\n", shell)
                    self.assertEqual(code, 0, output)
                    self.assertIn("ALL GREEN", output)

    def later(self):
        """A copy of the source with a second commit on top, which changes no check: (its path, the new commit, its
        parent). The runner of the project is the same file in both."""
        later = os.path.join(os.path.dirname(self.project), "later")
        git(os.path.dirname(self.project), "clone", "-q", self.source, later)
        with open(os.path.join(later, "README.md"), "a", encoding="utf-8") as handle:
            handle.write("\nA second commit.\n")
        git(later, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-q", "-am", "Later")
        return later, git(later, "rev-parse", "HEAD"), git(later, "rev-parse", "HEAD^")

    def test_a_missing_store_gets_the_pinned_commit_alone(self):
        # An adoption report on 0.12: every run in CI cloned the whole history. Only the pinned commit and its tree are
        # fetched now, so the parent commit is not in the store.
        later, commit, parent = self.later()
        command = [sys.executable, "-I", COPY, commit, "--repository", later, "--", "register.json"]
        result = subprocess.run(command, cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        store = self.path(".ratchet")
        self.assertEqual(git(store, "cat-file", "-t", commit), "commit")
        missing = subprocess.run(["git", "-C", store, "cat-file", "-e", parent], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        self.assertNotEqual(missing.returncode, 0, "the parent of the pinned commit was fetched")
        self.assertFalse(os.path.exists(os.path.join(store, "checks")), "the store has no checkout")
        # A second run reads the store it made, with no fetch.
        result = subprocess.run(command[:4] + ["--repository", os.path.join(self.project, "nowhere")] + command[6:],
                                cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_host_that_does_not_give_a_commit_by_its_id_is_cloned_whole(self):
        # The fall back: when the shallow fetch by id fails, the branches and tags of the repository are fetched into the
        # store made for it, what a clone fetches, as 0.12 did. Nothing is removed.
        later, commit, parent = self.later()
        scratch = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, scratch)
        refused = []

        class NoFetchById(run_pinned.Git):
            def run(self, objects, *args, data=None):
                if "--depth=1" in args:
                    refused.append(args)
                    return 128, b"", "Server does not allow request for unadvertised object"
                return run_pinned.Git.run(self, objects, *args, data=data)

        store = self.path(".ratchet")
        objects = run_pinned.store_with(NoFetchById(scratch), store, commit, later)
        self.assertEqual(len(refused), 1)
        self.assertEqual(objects, os.path.abspath(os.path.join(store, ".git", "objects")))
        self.assertEqual(git(store, "cat-file", "-t", commit), "commit")
        self.assertEqual(git(store, "cat-file", "-t", parent), "commit", "the whole repository was fetched")

    def test_a_store_left_empty_by_an_outage_gets_the_commit_once_the_host_answers(self):
        # Round 2 of #140: a first run that could not reach the host left an empty store, and a retry against a host that
        # gives branches and tags but no commit by its id was refused, though a fresh store would have passed.
        later, commit, parent = self.later()
        scratch = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, scratch)

        class Outage(run_pinned.Git):
            def run(self, objects, *args, data=None):
                if "fetch" in args:
                    return 128, b"", "Could not resolve host"
                return run_pinned.Git.run(self, objects, *args, data=data)

        class NoFetchById(run_pinned.Git):
            def run(self, objects, *args, data=None):
                if "fetch" in args and args[-1] == commit:
                    return 128, b"", "Server does not allow request for unadvertised object"
                return run_pinned.Git.run(self, objects, *args, data=data)

        store = self.path(".ratchet")
        with self.assertRaises(run_pinned.Refused):
            run_pinned.store_with(Outage(scratch), store, commit, later)
        self.assertTrue(os.path.isdir(store), "the first run left its store")
        again = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, again)
        objects = run_pinned.store_with(NoFetchById(again), store, commit, later)
        self.assertEqual(git(store, "cat-file", "-t", commit), "commit")
        self.assertEqual(objects, os.path.abspath(os.path.join(store, ".git", "objects")))

    def test_a_repository_that_cannot_be_reached_never_passes(self):
        # With no store and no repository to fetch from, the check does not run, and a second run, with the store the
        # first one made, does not either.
        for name in ("no-such-repository", "file:///no/such/repository"):
            with self.subTest(repository=name):
                for run in ("first", "second"):
                    result = subprocess.run([sys.executable, "-I", COPY, self.commit, "--repository", name, "--",
                                             "register.json"], cwd=self.project, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, universal_newlines=True)
                    self.assertEqual(result.returncode, 2, (run, result.stdout))
                    self.assertIn("cannot be fetched" if run == "second" else "cannot fetch", result.stdout)
                    self.assertIn("run_pinned: the check did not run", result.stdout)
                self.assertNotIn("Ratchet at", result.stdout)
            shutil.rmtree(self.path(".ratchet"))

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

    def pinned_runner(self):
        return subprocess.run(["git", "-C", self.source, "show", "%s:checks/run_pinned.py" % self.commit],
                              stdout=subprocess.PIPE, check=True).stdout

    def outside(self):
        """A file outside the project, which the copy command must never write: (its path, its bytes)."""
        path = os.path.join(tempfile.mkdtemp(dir=os.path.dirname(self.project)), "sentinel")
        with open(path, "wb") as handle:
            handle.write(b"UNCHANGED\n")
        return path, b"UNCHANGED\n"

    def clear(self, path):
        """Remove what stands at path, a link, a file or a folder, so that the next case starts from nothing."""
        if os.path.islink(path) or os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)

    def test_the_copy_command_refuses_anything_at_the_temporary_name(self):
        # The assessment of checks/ (D-2026-11-26-checks-assessment, section 4): a link left at <target>.new was
        # written through, so the copy overwrote a file outside the project, and the target was left a link.
        self.clone_store()
        os.remove(self.path(COPY))
        copy, _ = self.commands()
        temporary = self.path(COPY) + ".new"
        sentinel, before = self.outside()
        for kind in ("link to a file outside", "link to nothing", "regular file", "folder"):
            for shell in self.shells():
                with self.subTest(kind=kind, shell=shell):
                    if kind == "link to a file outside":
                        os.symlink(sentinel, temporary)
                    elif kind == "link to nothing":
                        os.symlink(sentinel + ".missing", temporary)
                    elif kind == "regular file":
                        with open(temporary, "wb") as handle:
                            handle.write(b"LEFT OVER\n")
                    else:
                        os.mkdir(temporary)
                    try:
                        code, output = self.shell(copy, shell)
                        self.assertNotEqual(code, 0, output)
                        self.assertIn("run_pinned.py was not copied: %s.new is in the way" % COPY.replace(os.sep, "/"),
                                      output)
                        with open(sentinel, "rb") as handle:
                            self.assertEqual(handle.read(), before)
                        self.assertFalse(os.path.lexists(sentinel + ".missing"))
                        self.assertFalse(os.path.lexists(self.path(COPY)))
                        # What stood at the temporary name is left as it was, for the project to look at.
                        if kind == "regular file":
                            with open(temporary, "rb") as handle:
                                self.assertEqual(handle.read(), b"LEFT OVER\n")
                        elif kind == "folder":
                            self.assertTrue(os.path.isdir(temporary) and not os.path.islink(temporary))
                            self.assertEqual(os.listdir(temporary), [])
                        else:
                            self.assertTrue(os.path.islink(temporary))
                    finally:
                        for path in (temporary, self.path(COPY), sentinel + ".missing"):
                            self.clear(path)
                        with open(sentinel, "wb") as handle:
                            handle.write(before)

    def test_the_copy_command_refuses_a_target_that_is_not_a_regular_file(self):
        self.clone_store()
        os.remove(self.path(COPY))
        copy, _ = self.commands()
        sentinel, before = self.outside()
        folder = os.path.dirname(sentinel)
        for kind in ("link to a file outside", "link to a folder outside", "link to nothing", "folder"):
            for shell in self.shells():
                with self.subTest(kind=kind, shell=shell):
                    target = {"link to a file outside": sentinel, "link to a folder outside": folder,
                              "link to nothing": sentinel + ".missing"}.get(kind)
                    if target:
                        os.symlink(target, self.path(COPY))
                    else:
                        os.mkdir(self.path(COPY))
                    try:
                        code, output = self.shell(copy, shell)
                        self.assertNotEqual(code, 0, output)
                        self.assertIn("run_pinned.py was not copied: %s is not a regular file"
                                      % COPY.replace(os.sep, "/"), output)
                        with open(sentinel, "rb") as handle:
                            self.assertEqual(handle.read(), before)
                        self.assertEqual(sorted(os.listdir(folder)), ["sentinel"])
                        self.assertEqual(os.path.islink(self.path(COPY)), bool(target))
                        if not target:
                            self.assertEqual(os.listdir(self.path(COPY)), [])
                        self.assertEqual(os.listdir(self.path(".github", "ratchet")), ["run_pinned.py"])
                    finally:
                        for name in os.listdir(self.path(".github", "ratchet")):
                            self.clear(self.path(".github", "ratchet", name))
                        for name in os.listdir(folder):
                            if name != "sentinel":
                                self.clear(os.path.join(folder, name))
                        with open(sentinel, "wb") as handle:
                            handle.write(before)

    def test_the_copy_command_replaces_a_regular_file_at_the_target(self):
        # As after an earlier copy, or an upgrade that copies the runner of a new commit over the old one.
        self.clone_store()
        copy, _ = self.commands()
        for shell in self.shells():
            with self.subTest(shell=shell):
                with open(self.path(COPY), "wb") as handle:
                    handle.write(b"an older runner\n")
                code, output = self.shell(copy, shell)
                self.assertEqual(code, 0, output)
                self.assertFalse(os.path.islink(self.path(COPY)))
                with open(self.path(COPY), "rb") as handle:
                    self.assertEqual(handle.read(), self.pinned_runner())
                self.assertEqual(os.listdir(self.path(".github", "ratchet")), ["run_pinned.py"])

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
    """Every script in checks/ and in maintain/ runs under python3 -I, which leaves the script's directory out of
    sys.path: a project that runs a check isolated, as the finding from a real adoption did, got ModuleNotFoundError: No
    module named 'registry'."""

    INSERT = "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
    # A script in maintain/ also puts checks/ on the path, before its own directory (D-2026-11-27-maintain-apart).
    INSERT_CHECKS = 'sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "checks"))\n'

    def scripts(self):
        """(the directory, the name) of every script in checks/ and in maintain/ that is not a test."""
        found = sorted((folder, name) for folder in (HERE, testing.MAINTAIN) for name in os.listdir(folder)
                       if name.endswith(".py") and not name.startswith("test_"))
        self.assertIn((HERE, "check_register.py"), found)
        self.assertIn((testing.MAINTAIN, "generate.py"), found)
        return found

    @staticmethod
    def imports(text):
        """(the line, the top-level name) of every module that an import statement anywhere in the text imports, in a
        function or a block too, in the order of the lines. Read with ast, not by lines: an indented import got past a
        pattern that matched only the start of a line (review of #195)."""
        found = []
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                found += [(node.lineno, alias.name.split(".")[0]) for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                found.append((node.lineno, node.module.split(".")[0]))
        return sorted(found)

    @staticmethod
    def relative_imports(text):
        """The lines of every relative import in the text, such as `from . import x` or `from .x import y`. A script in
        checks/ or maintain/ is not a package, so it has none, and the guard above would not see where one points
        (review of #200)."""
        return sorted(node.lineno for node in ast.walk(ast.parse(text))
                      if isinstance(node, ast.ImportFrom) and node.level)

    def test_the_guard_finds_a_relative_import(self):
        text = "import os\nfrom . import generate\ndef f():\n    from .generate import main\nfrom ..x import y\n"
        self.assertEqual(self.relative_imports(text), [2, 4, 5])
        self.assertEqual(self.relative_imports("import os\nfrom json import loads\n"), [])

    def test_no_script_has_a_relative_import(self):
        for folder, name in self.scripts():
            with self.subTest(script=name):
                with open(os.path.join(folder, name), encoding="utf-8") as handle:
                    self.assertEqual(self.relative_imports(handle.read()), [])

    def test_the_guard_reads_every_import_statement(self):
        text = ("import os, sys\nfrom json import loads\nimport xml.dom\n'import docstring'\n"
                "def f():\n    import generate\n    if True:\n        from release import main\n")
        self.assertEqual(self.imports(text), [(1, "os"), (1, "sys"), (2, "json"), (3, "xml"), (6, "generate"), (8, "release")])

    def test_every_script_that_imports_one_beside_it_puts_its_own_directory_on_the_path_first(self):
        siblings = {name[:-3] for _, name in self.scripts()}
        maintained = {name[:-3] for folder, name in self.scripts() if folder == testing.MAINTAIN}
        for folder, name in self.scripts():
            with self.subTest(script=name):
                with open(os.path.join(folder, name), encoding="utf-8") as handle:
                    text = handle.read()
                imported = [(line, module) for line, module in self.imports(text) if module in siblings]
                if imported:
                    self.assertIn(self.INSERT, text)
                    self.assertLess(text[:text.index(self.INSERT)].count("\n") + 1, imported[0][0])
                if folder == testing.MAINTAIN and imported:
                    self.assertIn(self.INSERT_CHECKS, text)
                    self.assertLess(text.index(self.INSERT_CHECKS), text.index(self.INSERT))
                if folder == HERE:
                    # What a project runs never needs Ratchet's own maintenance.
                    self.assertEqual([module for _, module in imported if module in maintained], [])
        with open(os.path.join(HERE, "run_pinned.py"), encoding="utf-8") as handle:
            self.assertNotIn(self.INSERT, handle.read(),
                             "run_pinned.py imports nothing from beside it, so -I keeps a planted module out")

    def test_every_script_with_a_command_line_starts_under_python_minus_i(self):
        directory = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, directory)
        for folder, name in self.scripts():
            with open(os.path.join(folder, name), encoding="utf-8") as handle:
                text = handle.read()
            if "\nimport argparse\n" not in text or "__main__" not in text:
                continue
            with self.subTest(script=name):
                result = subprocess.run([sys.executable, "-I", os.path.join(folder, name), "--help"], cwd=directory,
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
