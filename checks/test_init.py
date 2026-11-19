"""The one-command start: checks/init.py writes what README's "Start here" sets up, and never overwrites a file.

    python3 -m unittest discover -s checks -v

Each test makes a project of its own, a git repo in a directory from tempfile, with a clone of a copy of this
checkout as its .ratchet, and runs init.py from there, as README says. The copy is a git repo with one commit, so
that init.py reads a real commit to pin. Standard library only.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

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
         "-c", "tag.gpgsign=false", "-c", "init.defaultBranch=main"] + list(args),
        cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=environment())
    assert result.returncode == 0, result.stdout
    return result.stdout.strip()


def read_template(name):
    with open(os.path.join(ROOT, "templates", name), encoding="utf-8", newline="") as handle:
        return handle.read()


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
        result = subprocess.run([sys.executable, os.path.join(project, ".ratchet", "checks", "init.py")] + list(args),
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
        self.assertEqual(self.text("AGENTS.md").split("\n", 1)[1], read_template("AGENTS.md").split("\n", 1)[1])
        register = json.loads(self.text("register.json"))
        self.assertEqual(register["project"], "demo-project")
        template = json.loads(read_template("register.json"))
        template["project"] = "demo-project"
        self.assertEqual(register, template)
        self.assertEqual(self.text(".gitignore"), ".ratchet/\n")
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

    def test_every_step_in_the_workflow_runs_after_init(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        commands = re.findall(r"(?m)^\s+run: python3 (\.ratchet/\S.*)$", self.text(".github", "workflows", "ratchet.yml"))
        self.assertGreaterEqual(len(commands), 1)
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run([sys.executable] + command.split(" "), cwd=self.project, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, universal_newlines=True)
                self.assertEqual(result.returncode, 0, result.stdout)

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
                code, output = self.init("--name", name)
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
        self.assertEqual(self.text(".gitignore"), "node_modules\n.ratchet/\n")
        self.assertRegex(output, r"(?m)^add +\.ratchet/ to \.gitignore")

    def test_a_gitignore_that_holds_the_line_is_not_changed(self):
        for line in (".ratchet", ".ratchet/", "/.ratchet", "/.ratchet/"):
            with self.subTest(line=line):
                self.write(".gitignore", "build/\r\n%s\r\n" % line)
                code, output = self.init()
                self.assertEqual(code, 0, output)
                self.assertEqual(self.text(".gitignore"), "build/\r\n%s\r\n" % line)
                self.assertRegex(output, r"(?m)^unchanged +\.gitignore")

    def test_a_gitignore_with_crlf_gets_crlf(self):
        self.write(".gitignore", "build/\r\n")
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.text(".gitignore"), "build/\r\n.ratchet/\r\n")

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

    def test_outside_the_root_of_a_git_repo_it_does_not_run(self):
        shutil.rmtree(self.path(".git"))
        code, output = self.init()
        self.assertEqual(code, 2, output)
        self.assertIn("the root of a git repo", output)
        self.assertEqual(snapshot(self.project), {})

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


if __name__ == "__main__":
    unittest.main()
