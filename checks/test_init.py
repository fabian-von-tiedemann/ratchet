"""The one-command start: checks/init.py writes what README's "Start here" sets up, and never overwrites a file.

    python3 -m unittest discover -s checks -v

Each test makes a project of its own, a git repo in a directory from tempfile, with a clone of a copy of this
checkout as its .ratchet, and runs init.py from there, as README says. The copy is a git repo with one commit, so
that init.py reads a real commit to pin. Standard library only.
"""

import builtins
import contextlib
import errno
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import init  # noqa: E402

WRITTEN = ("AGENTS.md", "register.json", "REGISTER.md", os.path.join(".github", "workflows", "ratchet.yml"), ".gitignore")
PLACEHOLDER = "<40-character commit sha>"


def environment():
    """git with no configuration of the person who runs the tests, and no repo named from outside."""
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", LC_ALL="C")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    return env


def git(cwd, *args):
    result = subprocess.run(
        ["git", "-c", "user.name=Ratchet test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
         "-c", "tag.gpgsign=false", "-c", "init.defaultBranch=main", "-c", "gc.auto=0", "-c", "maintenance.auto=false"] + list(args),
        cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=environment())
    assert result.returncode == 0, result.stdout
    return result.stdout.strip()


def read_template(name):
    with open(os.path.join(ROOT, "templates", name), encoding="utf-8", newline="") as handle:
        return handle.read()


def without_markers(text):
    """The template's text with the lines that mark what --solo leaves out taken away, as init.py writes it."""
    return "".join(line for line in text.splitlines(True) if line not in ("<!-- team -->\n", "<!-- /team -->\n"))


def filled_in(text):
    """AGENTS.md with every placeholder of the template filled in, as step 4 of "Start here" asks."""
    import check_register
    for placeholder in check_register.PLACEHOLDERS:
        text = text.replace(placeholder, "Filled in.")
    return text


def bracketed(text):
    """Every part of text in angle brackets, in the order the parts start, a part nested in another one included.
    Each ">" closes the "<" last opened. A bracket with no partner fails."""
    parts, opened = [], []
    for index, character in enumerate(text):
        if character == "<":
            opened.append((index, len(parts)))
            parts.append(None)
        elif character == ">":
            assert opened, "a > with no < before it at %d" % index
            start, slot = opened.pop()
            parts[slot] = text[start:index + 1]
    assert not opened, "a < with no > after it at %s" % [start for start, slot in opened]
    return parts


def no_link(*args, **kwargs):
    raise OSError(errno.EPERM, "no hard links here")


class CutOff:
    """A file opened for writing whose first write stops halfway, as when the disk fills or the run is stopped."""

    def __init__(self, handle):
        self.handle = handle

    def write(self, data):
        self.handle.write(data[:len(data) // 2])
        self.handle.flush()
        raise OSError(errno.ENOSPC, "cut off halfway")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.handle.close()
        return False

    def __getattr__(self, name):
        return getattr(self.handle, name)


@contextlib.contextmanager
def cut_off_writes():
    """Every file opened for writing, with open or os.fdopen, is cut off halfway through its first write."""
    real_open, real_fdopen = builtins.open, os.fdopen

    def wrap(opener):
        def opened(file, mode="r", *args, **kwargs):
            handle = opener(file, mode, *args, **kwargs)
            return CutOff(handle) if set(mode) & set("wxa+") else handle
        return opened

    with unittest.mock.patch.object(builtins, "open", wrap(real_open)), \
            unittest.mock.patch.object(os, "fdopen", wrap(real_fdopen)):
        yield


def snapshot(directory):
    """Every file under directory, outside .git and .ratchet, with its bytes."""
    found = {}
    for base, directories, files in os.walk(directory):
        directories[:] = [name for name in directories if not (base == directory and name in (".git", ".ratchet"))]
        for name in files:
            path = os.path.join(base, name)
            with open(path, "rb") as handle:
                found[os.path.relpath(path, directory)] = handle.read()
    return found


class Init(unittest.TestCase):
    """init.py, run from the root of a new project with this checkout cloned into .ratchet."""

    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="ratchet-test-")
        cls.source = os.path.join(cls.base, "ratchet")
        shutil.copytree(ROOT, cls.source, ignore=shutil.ignore_patterns(".git", "__pycache__", "fixtures", ".claude"))
        git(cls.source, "init", "-q")
        git(cls.source, "add", "-A")
        git(cls.source, "commit", "-q", "-m", "Ratchet as it stands")
        cls.commit = git(cls.source, "rev-parse", "HEAD")
        with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as handle:
            cls.version = json.load(handle)["version"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base)

    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, self.directory)
        self.project = self.make_project("demo-project")

    def make_project(self, name):
        project = os.path.join(self.directory, name)
        os.mkdir(project)
        git(project, "init", "-q")
        git(project, "clone", "-q", self.source, ".ratchet")
        return project

    def init(self, *args, project=None):
        project = project or self.project
        script = os.path.join(self.project if project == self.path(".ratchet") else project, ".ratchet", "checks", "init.py")
        result = subprocess.run([sys.executable, script] + list(args),
                                cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                                env=environment())
        return result.returncode, result.stdout

    def path(self, *parts):
        return os.path.join(self.project, *parts)

    def text(self, *parts):
        with open(self.path(*parts), encoding="utf-8", newline="") as handle:
            return handle.read()

    def write(self, name, text):
        with open(self.path(name), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def test_an_empty_repo_gets_every_file(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        for name in WRITTEN:
            with self.subTest(file=name):
                self.assertTrue(os.path.isfile(self.path(name)), output)
                self.assertIn(name.replace(os.sep, "/"), output)
        self.assertEqual(self.text("AGENTS.md").split("\n", 1)[0], "# Working rules for demo-project")
        self.assertEqual(self.text("AGENTS.md").split("\n", 1)[1], without_markers(read_template("AGENTS.md")).split("\n", 1)[1])
        register = json.loads(self.text("register.json"))
        self.assertEqual(register["project"], "demo-project")
        template = json.loads(read_template("register.json"))
        template["project"] = "demo-project"
        self.assertEqual(register, template)
        self.assertEqual(self.text(".gitignore"), "/.ratchet/\n")
        self.assert_ratchet_ignored()
        self.assertIn("9 rules match Ratchet %s" % self.version, output)

    def test_the_pinned_commit_is_in_the_workflow(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        workflow = self.text(".github", "workflows", "ratchet.yml")
        self.assertRegex(self.commit, r"^[0-9a-f]{40}$")
        self.assertIn("ref: %s\n" % self.commit, workflow)
        self.assertNotIn(PLACEHOLDER, workflow)
        self.assertEqual(workflow, read_template("ratchet-checks.yml").replace(PLACEHOLDER, self.commit))
        self.assertIn(self.commit, output)

    def test_the_generated_register_passes_check_register(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        result = subprocess.run([sys.executable, self.path(".ratchet", "checks", "check_register.py"), "register.json",
                                 "--markdown", "REGISTER.md"], cwd=self.project, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("# Register for demo\\-project\n", self.text("REGISTER.md"))
        self.assertIn("check_register.py register.json --markdown REGISTER.md", output)

    def run_the_workflow(self):
        """(exit code, output) of each step of the written workflow that runs a check of Ratchet, run here."""
        commands = re.findall(r"(?m)^\s+run: python3 (\.ratchet/\S.*)$", self.text(".github", "workflows", "ratchet.yml"))
        self.assertGreaterEqual(len(commands), 1)
        results = []
        for command in commands:
            result = subprocess.run([sys.executable] + command.split(" "), cwd=self.project, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, universal_newlines=True)
            results.append((result.returncode, result.stdout))
        return results

    def test_every_step_in_the_workflow_runs_after_init_once_agents_md_is_filled_in(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.write("AGENTS.md", filled_in(self.text("AGENTS.md")))
        for code, output in self.run_the_workflow():
            self.assertEqual(code, 0, output)

    def test_the_workflow_fails_while_agents_md_holds_a_placeholder_and_names_each(self):
        import check_register
        for solo in (False, True):
            with self.subTest(solo=solo):
                for name in ("AGENTS.md", "register.json", "REGISTER.md", os.path.join(".github", "workflows", "ratchet.yml")):
                    if os.path.lexists(self.path(name)):
                        os.remove(self.path(name))
                code, output = self.init(*(["--solo"] if solo else []))
                self.assertEqual(code, 0, output)
                agents = self.text("AGENTS.md")
                left = [placeholder for placeholder in check_register.PLACEHOLDERS if placeholder in agents]
                self.assertGreaterEqual(len(left), 4)
                for placeholder in left:
                    self.assertIn(placeholder, output)
                failed = [output for code, output in self.run_the_workflow() if code != 0]
                self.assertEqual(len(failed), 1, failed)
                for placeholder in left:
                    self.assertIn("AGENTS.md: still holds the template's placeholder %s" % placeholder, failed[0])
                # One left, the rest filled in: that one alone is named.
                self.write("AGENTS.md", filled_in(agents).replace("Filled in.", left[-1], 1))
                failed = [output for code, output in self.run_the_workflow() if code != 0]
                self.assertEqual(len(failed), 1, failed)
                self.assertIn(left[-1], failed[0])
                self.assertIn("FAIL: 1 problem(s)", failed[0])

    def test_solo_leaves_out_the_control_room_and_the_skills(self):
        code, output = self.init("--solo")
        self.assertEqual(code, 0, output)
        agents = self.text("AGENTS.md")
        self.assertEqual(agents.split("\n", 1)[0], "# Working rules for demo-project")
        for text in ("control room", "Control room", "## Skills", "skills directory", "| Situation |", "<!--"):
            self.assertNotIn(text, agents)
        for heading in ("## Purpose", "## Read first", "## What this project is and is not doing now"):
            self.assertIn("\n%s\n" % heading, agents)
        self.assertNotIn("\n\n\n", agents)
        self.assertTrue(agents.endswith(".>\n"), agents[-80:])
        code, output = self.init("--solo")
        self.assertEqual(code, 0, output)
        self.assertRegex(output, r"(?m)^unchanged +AGENTS\.md")
        code, output = self.init()
        self.assertEqual(code, 1, output)
        self.assertRegex(output, r"(?m)^skip +AGENTS\.md: it exists and differs")

    def test_without_solo_the_control_room_and_the_skills_stay(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        agents = self.text("AGENTS.md")
        self.assertIn("\n\nThe control room also reads its handbook, after the register.\n\n## What", agents)
        self.assertIn("\n\n## Skills\n", agents)
        self.assertNotIn("<!--", agents)

    def test_team_markers_that_are_not_in_pairs_are_refused(self):
        for text in ("a\n<!-- team -->\nb\n", "a\n<!-- /team -->\nb\n", "<!-- team -->\n<!-- team -->\n<!-- /team -->\n",
                     "<!-- team -->\na\n<!-- /team -->\n<!-- /team -->\n", "a\n"):
            for solo in (False, True):
                with self.subTest(text=text, solo=solo):
                    with self.assertRaises(init.InitError):
                        init.team_parts(text, solo)
        self.assertEqual(init.team_parts("a\n<!-- team -->\nb\n<!-- /team -->\nc\n", False), "a\nb\nc\n")
        self.assertEqual(init.team_parts("a\n<!-- team -->\nb\n<!-- /team -->\nc\n", True), "a\nc\n")

    def test_without_a_remote_it_names_the_rules_that_wait_for_one(self):
        waiting = ("ratchet.register-on-top", "ratchet.protected-main", "ratchet.no-secrets", "ratchet.lesson-names-check")
        for args in ((), ("--check",)):
            with self.subTest(args=args):
                code, output = self.init(*args)
                self.assertEqual(code, 0, output)
                self.assertIn("names no remote", output)
                for key in waiting:
                    self.assertIn(key, output)
                for key in ("ratchet.decision-as-file", "ratchet.root-cause"):
                    self.assertNotIn(key, output)
        git(self.project, "remote", "add", "origin", "https://example.invalid/demo.git")
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertNotIn("names no remote", output)
        for key in waiting:
            self.assertNotIn(key, output)

    def test_only_adopted_rules_are_named_as_waiting_for_a_remote(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        register = json.loads(self.text("register.json"))
        register["adopted"] = [rule for rule in register["adopted"] if rule["key"] != "ratchet.no-secrets"]
        self.write("register.json", json.dumps(register, indent=2) + "\n")
        os.remove(self.path("REGISTER.md"))
        code, output = self.init()
        self.assertEqual(code, 1, output)
        waiting = output.split("wait for one:\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn("ratchet.protected-main", waiting)
        self.assertNotIn("ratchet.no-secrets", waiting)

    def test_a_worktree_whose_repo_has_a_remote_names_none_waiting(self):
        main = os.path.join(self.directory, "main")
        os.mkdir(main)
        git(main, "init", "-q")
        git(main, "commit", "-q", "--allow-empty", "-m", "start")
        git(main, "remote", "add", "origin", "https://example.invalid/demo.git")
        worktree = os.path.join(self.directory, "worktree-project")
        git(main, "worktree", "add", "-q", worktree)
        git(worktree, "clone", "-q", self.source, ".ratchet")
        code, output = self.init("--name", "demo", project=worktree)
        self.assertEqual(code, 0, output)
        self.assertNotIn("names no remote", output)

    def test_the_workflow_has_a_job_for_the_projects_own_checks_and_init_names_the_jobs_to_require(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        workflow = self.text(".github", "workflows", "ratchet.yml")
        jobs = re.findall(r"(?m)^  ([a-z][a-z-]*):$", workflow.split("\njobs:\n", 1)[1])
        self.assertEqual(jobs, ["ratchet", "project-checks"])
        own = workflow.split("\n  project-checks:\n", 1)[1]
        self.assertIn("runs-on:", own)
        self.assertIn("The project's own checks", own)
        self.assertIn("require the jobs ratchet and project-checks", output)
        code, output = self.init("--check")
        self.assertIn("require the jobs ratchet and project-checks", output)

    def test_a_workflow_template_without_the_jobs_is_refused(self):
        text = read_template("ratchet-checks.yml")
        self.assertEqual(init.workflow_text_from(text, "a" * 40).count("\n  project-checks:\n"), 1)
        for broken in (text.replace("\n  project-checks:\n", "\n  own:\n"), text.replace("\n  ratchet:\n", "\n  register:\n"),
                       text + "\n  ratchet:\n"):
            with self.subTest(broken=broken[-40:]):
                with self.assertRaises(init.InitError):
                    init.workflow_text_from(broken, "a" * 40)

    def test_an_existing_agents_md_is_skipped_and_reported(self):
        self.write("AGENTS.md", "# Our own rules\n")
        code, output = self.init()
        self.assertEqual(code, 1, output)
        self.assertEqual(self.text("AGENTS.md"), "# Our own rules\n")
        self.assertRegex(output, r"(?m)^skip +AGENTS\.md: it exists and differs")
        for name in WRITTEN[1:]:
            with self.subTest(file=name):
                self.assertTrue(os.path.isfile(self.path(name)), output)
        self.assertIn("1 file left as it is", output)

    def test_a_second_run_changes_nothing(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        before = snapshot(self.project)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.project), before)
        self.assertIn("Nothing changed", output)
        self.assertNotRegex(output, r"(?m)^(write|add) ")
        self.assertEqual(len(re.findall(r"(?m)^unchanged ", output)), len(WRITTEN), output)

    def test_check_writes_nothing(self):
        before = snapshot(self.project)
        code, output = self.init("--check")
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.project), before)
        self.assertEqual(before, {})
        for name in WRITTEN:
            with self.subTest(file=name):
                self.assertRegex(output, r"(?m)^would (write|add) .*%s" % re.escape(name.replace(os.sep, "/")))
        self.assertIn("Nothing was written", output)

    def test_check_reports_a_file_that_exists_and_writes_nothing(self):
        self.write("AGENTS.md", "# Our own rules\n")
        before = snapshot(self.project)
        code, output = self.init("--check")
        self.assertEqual(code, 1, output)
        self.assertEqual(snapshot(self.project), before)
        self.assertRegex(output, r"(?m)^skip +AGENTS\.md: it exists and differs")

    def test_a_bad_project_name_is_refused(self):
        for name in ("", " demo", "demo ", "two  spaces", "bad|name", "a@b", "-demo", "demo-", "a_b_", "demo!",
                     "www.example.com", "Proj\u00e9t", "\u540d\u524d", "demo\u200b", "x" * 101, "<project>"):
            with self.subTest(name=name):
                code, output = self.init("--name=" + name)
                self.assertEqual(code, 2, output)
                self.assertIn("project name", output)
                self.assertEqual(snapshot(self.project), {})

    def test_a_bad_folder_name_is_refused_unless_a_name_is_given(self):
        project = self.make_project("not a name!")
        code, output = self.init(project=project)
        self.assertEqual(code, 2, output)
        self.assertIn("--name", output)
        self.assertEqual(snapshot(project), {})
        code, output = self.init("--name", "Demo Project 2", project=project)
        self.assertEqual(code, 0, output)
        with open(os.path.join(project, "AGENTS.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.readline(), "# Working rules for Demo Project 2\n")

    def test_good_names_pass(self):
        for name in ("demo", "Demo Project 2", "my_project", "web.app", "a-b.c_d e", "X"):
            with self.subTest(name=name):
                self.assertIsNone(init.name_problem(name))

    def test_a_gitignore_that_exists_gets_one_line(self):
        self.write(".gitignore", "node_modules")
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.text(".gitignore"), "node_modules\n/.ratchet/\n")
        self.assertRegex(output, r"(?m)^add +/\.ratchet/ to \.gitignore")
        self.assert_ratchet_ignored()

    def assert_ratchet_ignored(self):
        """git itself, run here by the test and never by init.py, says that .ratchet is ignored."""
        git(self.project, "-c", "core.fsmonitor=false", "check-ignore", "-q", ".ratchet")

    def test_a_gitignore_that_holds_the_line_is_not_changed(self):
        for line in (".ratchet/", "/.ratchet/"):
            for newline in ("\n", "\r\n"):
                with self.subTest(line=line, newline=newline):
                    text = "build/%s!.ratchet/%s%s%s" % (newline, newline, line, newline)
                    self.write(".gitignore", text)
                    code, output = self.init()
                    self.assertEqual(code, 0, output)
                    self.assertEqual(self.text(".gitignore"), text)
                    self.assertRegex(output, r"(?m)^unchanged +\.gitignore")
                    self.assert_ratchet_ignored()

    def test_a_gitignore_whose_last_line_on_ratchet_is_not_the_line_gets_it(self):
        # The last line that mentions .ratchet decides, and only .ratchet/ or /.ratchet/, exactly, with no
        # negation after it, counts. A leading space is part of the pattern in gitignore.
        for text in (" .ratchet/\n", "\t.ratchet/\n", ".ratchet/\n!.ratchet/\n", ".ratchet/\n!*\n", "!.ratchet/\n",
                     "# .ratchet/\n", ".ratchet\n", "/.ratchet\n", ".ratchet/ \n", ".ratchet/*\n", "build/\n"):
            with self.subTest(text=text):
                self.write(".gitignore", text)
                code, output = self.init()
                self.assertEqual(code, 0, output)
                self.assertEqual(self.text(".gitignore"), text + "/.ratchet/\n")
                self.assertRegex(output, r"(?m)^add +/\.ratchet/ to \.gitignore")
                self.assert_ratchet_ignored()
                code, output = self.init()
                self.assertEqual(code, 0, output)
                self.assertRegex(output, r"(?m)^unchanged +\.gitignore")

    def test_a_gitignore_with_crlf_gets_crlf(self):
        self.write(".gitignore", "build/\r\n")
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.text(".gitignore"), "build/\r\n/.ratchet/\r\n")
        self.assert_ratchet_ignored()

    def test_a_gitignore_changed_after_the_plan_is_left_as_it_is(self):
        # Another edit lands between the plan and the write: init.py stops, and the edit is kept.
        self.write(".gitignore", "build/\n")
        code, output = self.run_patched("""
plan = init.gitignore_plan
def gitignore_plan(path):
    result = plan(path)
    with open(path, "a") as handle:
        handle.write("dist/\\n")
    return result
init.gitignore_plan = gitignore_plan
""")
        self.assertEqual(code, 2, output)
        self.assertEqual(self.text(".gitignore"), "build/\ndist/\n")
        self.assertIn(".gitignore changed while init.py ran", output)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.text(".gitignore"), "build/\ndist/\n/.ratchet/\n")

    def test_the_line_is_added_only_to_the_gitignore_that_was_read(self):
        path = self.path(".gitignore")
        self.write(".gitignore", "build/\n")
        init.add_line(path, b"build/\n", b"build/\n/.ratchet/\n")
        self.assertEqual(self.text(".gitignore"), "build/\n/.ratchet/\n")
        with self.assertRaises(init.Changed):
            init.add_line(path, b"build/\n", b"build/\n/.ratchet/\n")
        self.assertEqual(self.text(".gitignore"), "build/\n/.ratchet/\n")
        self.assertEqual(sorted(os.listdir(self.project)), [".git", ".gitignore", ".ratchet"])

    def run_patched(self, patch, *args):
        """Run init.py as the README does, with a change to it or to os made first, in the same process."""
        code = "\n".join(["import errno, os, sys",
                          "sys.path.insert(0, os.path.join('.ratchet', 'checks'))",
                          "import init", patch, "sys.exit(init.main(sys.argv[1:]))"])
        result = subprocess.run([sys.executable, "-c", code] + list(args), cwd=self.project, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True, env=environment())
        return result.returncode, result.stdout

    def test_an_existing_register_is_kept_and_its_register_md_generated_from_it(self):
        code, output = self.init("--name", "first")
        self.assertEqual(code, 0, output)
        os.remove(self.path("REGISTER.md"))
        code, output = self.init("--name", "second")
        self.assertEqual(code, 1, output)
        self.assertEqual(json.loads(self.text("register.json"))["project"], "first")
        self.assertIn("# Register for first\n", self.text("REGISTER.md"))
        self.assertRegex(output, r"(?m)^skip +register\.json: it exists and differs")
        self.assertRegex(output, r"(?m)^write +REGISTER\.md")

    def test_a_file_in_the_way_that_is_not_a_plain_file_is_skipped(self):
        os.mkdir(self.path("AGENTS.md"))
        code, output = self.init()
        self.assertEqual(code, 1, output)
        self.assertTrue(os.path.isdir(self.path("AGENTS.md")))
        self.assertRegex(output, r"(?m)^skip +AGENTS\.md: it exists and is not a plain file")

    def test_no_temporary_file_is_left_behind(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(sorted(snapshot(self.project)), sorted(WRITTEN))

    def test_without_hard_links_no_file_is_written(self):
        # A file system with no hard links: a file cannot be put in place whole without the risk of overwriting
        # one, so init.py stops and writes none, rather than writing a file directly.
        code, output = self.run_patched("""
def link(*args, **kwargs):
    raise OSError(errno.EPERM, "no hard links here")
os.link = link
""")
        self.assertEqual(code, 2, output)
        self.assertIn("cannot write AGENTS.md", output)
        self.assertEqual(snapshot(self.project), {})
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(sorted(snapshot(self.project)), sorted(WRITTEN))

    def test_a_write_cut_off_leaves_no_file(self):
        # The disk fills or the run is stopped in the middle of a write: the file that was being written does
        # not exist, so a second run writes it, rather than skipping a file that is half written.
        for links in (True, False):
            with self.subTest(links=links):
                path = self.path("AGENTS.md")
                with cut_off_writes(), unittest.mock.patch.object(os, "link", os.link if links else no_link):
                    with self.assertRaises(OSError):
                        init.write_new(path, b"x" * 4096)
                self.assertFalse(os.path.lexists(path))
                self.assertEqual(sorted(os.listdir(self.project)), [".git", ".ratchet"])

    def test_without_hard_links_write_new_creates_nothing(self):
        path = self.path("AGENTS.md")
        with unittest.mock.patch.object(os, "link", no_link):
            with self.assertRaises(OSError):
                init.write_new(path, b"whole\n")
        self.assertFalse(os.path.lexists(path))
        self.assertEqual(sorted(os.listdir(self.project)), [".git", ".ratchet"])

    def test_a_file_is_linked_into_place_whole(self):
        path = self.path("AGENTS.md")
        data = b"whole\n" * 1000
        calls = []
        real = os.link

        def link(source, destination, **kwargs):
            self.assertFalse(os.path.lexists(destination))
            with open(source, "rb") as handle:
                self.assertEqual(handle.read(), data)
            calls.append(destination)
            return real(source, destination, **kwargs)

        with unittest.mock.patch.object(os, "link", link):
            self.assertTrue(init.write_new(path, data))
        self.assertEqual(calls, [path])
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), data)
        self.assertEqual(sorted(os.listdir(self.project)), [".git", ".ratchet", "AGENTS.md"])

    def test_a_file_that_appears_meanwhile_is_not_overwritten(self):
        path = self.path("AGENTS.md")
        real = os.link

        def link(source, destination, **kwargs):
            with open(destination, "wb") as handle:
                handle.write(b"theirs\n")
            return real(source, destination, **kwargs)

        with unittest.mock.patch.object(os, "link", link):
            self.assertFalse(init.write_new(path, b"ours\n"))
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"theirs\n")
        self.assertEqual(sorted(os.listdir(self.project)), [".git", ".ratchet", "AGENTS.md"])

    def test_outside_the_root_of_a_git_repo_it_does_not_run(self):
        shutil.rmtree(self.path(".git"))
        code, output = self.init()
        self.assertEqual(code, 2, output)
        self.assertIn("the root of a git repo", output)
        self.assertEqual(snapshot(self.project), {})

    def assert_not_a_repo(self):
        before = snapshot(self.project)
        code, output = self.init()
        self.assertEqual(code, 2, output)
        self.assertIn("the root of a git repo", output)
        self.assertIn("nothing was written", output)
        self.assertEqual(snapshot(self.project), before)

    def test_a_git_that_is_not_a_repo_does_not_run(self):
        store = os.path.join(self.directory, "store")
        os.mkdir(store)
        cases = (
            ("an empty .git directory", None),
            ("a .git directory without objects", "HEAD"),
            ("a stale .git file", "gitdir: %s\n" % os.path.join(self.directory, "gone")),
            ("a .git file naming a directory that is no repo", "gitdir: %s\n" % store),
            ("a .git file of two lines", "gitdir: %s\ngitdir: %s\n" % (store, store)),
            ("a .git file with no gitdir", "%s\n" % store),
            ("an empty .git file", ""),
        )
        for case, content in cases:
            with self.subTest(case=case):
                shutil.rmtree(self.path(".git"), ignore_errors=True)
                if os.path.lexists(self.path(".git")):
                    os.remove(self.path(".git"))
                if content is None or content == "HEAD":
                    os.mkdir(self.path(".git"))
                    if content == "HEAD":
                        self.write(os.path.join(".git", "HEAD"), "ref: refs/heads/main\n")
                else:
                    self.write(".git", content)
                self.assert_not_a_repo()

    def test_a_worktree_runs(self):
        main = os.path.join(self.directory, "main")
        os.mkdir(main)
        git(main, "init", "-q")
        git(main, "commit", "-q", "--allow-empty", "-m", "start")
        worktree = os.path.join(self.directory, "worktree-project")
        git(main, "worktree", "add", "-q", worktree)
        with open(os.path.join(worktree, ".git"), encoding="utf-8") as handle:
            self.assertRegex(handle.read(), r"^gitdir: .*worktrees")
        git(worktree, "clone", "-q", self.source, ".ratchet")
        code, output = self.init("--name", "demo", project=worktree)
        self.assertEqual(code, 0, output)
        self.assertTrue(os.path.isfile(os.path.join(worktree, "AGENTS.md")))

    def test_a_git_file_naming_a_repo_elsewhere_runs(self):
        # As git init --separate-git-dir and a submodule leave it: an absolute path, and one relative to the
        # folder of the .git file.
        for relative in (False, True):
            with self.subTest(relative=relative):
                store = os.path.join(self.directory, "store-%s" % relative)
                shutil.move(self.path(".git"), store)
                self.write(".git", "gitdir: %s\n" % (os.path.relpath(store, self.project) if relative else store))
                code, output = self.init()
                self.assertEqual(code, 0, output)
                os.remove(self.path(".git"))
                shutil.move(store, self.path(".git"))

    def test_a_ratchet_that_is_not_a_git_checkout_does_not_run(self):
        shutil.rmtree(self.path(".ratchet", ".git"))
        code, output = self.init()
        self.assertEqual(code, 2, output)
        self.assertIn("commit", output)
        self.assertEqual(snapshot(self.project), {})

    def test_a_ratchet_checkout_with_changes_does_not_run(self):
        with open(self.path(".ratchet", "templates", "AGENTS.md"), "a", encoding="utf-8") as handle:
            handle.write("\nA change that is not committed.\n")
        code, output = self.init()
        self.assertEqual(code, 2, output)
        self.assertIn("not committed", output)
        self.assertEqual(snapshot(self.project), {})

    def test_it_does_not_run_in_ratchet_itself(self):
        code, output = self.init(project=self.path(".ratchet"))
        self.assertEqual(code, 2, output)
        self.assertIn("your own repo", output)

    def test_a_commit_that_is_not_40_hex_characters_is_refused(self):
        for text in ("", "HEAD", "abc123", "A" * 40, "g" * 40, "a" * 39, "a" * 41, "a" * 40 + "\n" + "b" * 40):
            with self.subTest(text=text):
                self.assertIsNotNone(init.commit_problem(text))
        self.assertIsNone(init.commit_problem(self.commit))

    def test_the_tag_is_named_when_the_commit_is_a_release(self):
        code, output = self.init("--check")
        self.assertEqual(code, 0, output)
        self.assertIn("not the commit of the tag v%s" % self.version, output)
        git(self.path(".ratchet"), "tag", "v" + self.version)
        code, output = self.init("--check")
        self.assertEqual(code, 0, output)
        self.assertIn("the commit of the tag v%s" % self.version, output)
        self.assertNotIn("not the commit of the tag", output)

    def test_the_templates_hold_what_init_fills_in(self):
        self.assertEqual(read_template("AGENTS.md").split("\n", 1)[0], init.AGENTS_TITLE % "<project>")
        self.assertEqual(json.loads(read_template("register.json"))["project"], "<project>")
        self.assertEqual(read_template("ratchet-checks.yml").count(PLACEHOLDER), 1)
        self.assertEqual(init.PLACEHOLDER, PLACEHOLDER)

    def test_the_list_of_placeholders_is_the_templates(self):
        # Every part of templates/AGENTS.md in angle brackets, a part nested in another one included, is on the fixed
        # list that check_register.py --agents fails on, in the order the parts start in the template. The exceptions
        # are <name>, which stands for any skill's name, and the lines that mark what --solo leaves out. The parts are
        # found by pairing each ">" with the "<" before it, so a placeholder inside another one is found on its own.
        import check_register
        text = read_template("AGENTS.md")
        for placeholder in check_register.PLACEHOLDERS:
            with self.subTest(placeholder=placeholder):
                self.assertEqual(text.count(placeholder), 1)
        parts = [part for part in bracketed(without_markers(text)) if part != "<name>"]
        self.assertIn("<n>", parts)
        self.assertEqual(parts, list(check_register.PLACEHOLDERS))
        self.assertEqual(check_register.placeholders(filled_in(text)), [])
        self.assertEqual(check_register.placeholders(text), list(check_register.PLACEHOLDERS))

    def test_bracketed_finds_nested_parts_and_refuses_unpaired_brackets(self):
        self.assertEqual(bracketed("a <b (#<n>)> c <d>"), ["<b (#<n>)>", "<n>", "<d>"])
        for text in ("a <b", "a b>", "<a <b>", "<a>>"):
            with self.subTest(text=text):
                with self.assertRaises(AssertionError):
                    bracketed(text)

    def test_a_placeholder_left_inside_a_filled_in_one_is_named(self):
        # A partial edit: the outer placeholder chosen and its brackets taken away, the one inside it left, everything
        # else filled in. For the handover that is "3. The latest handover: status issue #<n>.".
        import check_register
        text = read_template("AGENTS.md")
        handover = "<`HANDOVER.md`, or the status issue (#<n>)>"
        self.assertEqual(text.count(handover), 1)
        edited = filled_in(text.replace(handover, "status issue #N-LEFT")).replace("N-LEFT", "<n>")
        self.assertIn("\n3. The latest handover: status issue #<n>.\n", edited)
        self.assertEqual(check_register.placeholders(edited), ["<n>"])
        # The same for every placeholder that holds another one: its brackets taken away, the inner one kept.
        nested = [(outer, inner) for outer in check_register.PLACEHOLDERS for inner in check_register.PLACEHOLDERS
                  if inner != outer and inner in outer]
        self.assertIn((handover, "<n>"), nested)
        for outer, inner in nested:
            with self.subTest(outer=outer):
                edited = filled_in(text.replace(outer, outer[1:-1].replace(inner, "INNER-LEFT"))).replace("INNER-LEFT", inner)
                self.assertEqual(check_register.placeholders(edited), [inner])

    def test_the_rules_that_wait_for_a_remote_are_rules_of_the_starter_register(self):
        keys = [rule["key"] for rule in json.loads(read_template("register.json"))["adopted"]]
        for key in init.WAIT_FOR_REMOTE:
            with self.subTest(key=key):
                self.assertIn(key, keys)


if __name__ == "__main__":
    unittest.main()
