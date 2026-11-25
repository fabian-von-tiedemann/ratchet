"""The one-command start: checks/init.py writes what README's "Start here" sets up, and never overwrites a file.

    python3 -m unittest discover -s checks -v

Each test makes a project of its own, a git repo in a directory from tempfile, with a clone of a copy of this
checkout as its .ratchet, and runs init.py from there, as README says. The copy is a git repo with one commit, so
that init.py reads a real commit to pin. Standard library only.
"""

import builtins
import contextlib
import errno
import html
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

import generate  # noqa: E402
import init  # noqa: E402
import run_pinned  # noqa: E402

WRITTEN = ("AGENTS.md", "register.json", "REGISTER.md", os.path.join(".github", "workflows", "ratchet.yml"), ".gitignore",
           "CLAUDE.md")
PLACEHOLDER = "<40-character commit sha>"


def environment():
    """git with no configuration of the person who runs the tests, and no repo named from outside."""
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", LC_ALL="C")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    return env


QUIET = (("gc.auto", "0"), ("maintenance.auto", "false"))


def git(cwd, *args):
    result = subprocess.run(
        ["git", "-c", "user.name=Ratchet test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
         "-c", "tag.gpgsign=false", "-c", "init.defaultBranch=main", "-c", "gc.auto=0", "-c", "maintenance.auto=false"] + list(args),
        cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=environment())
    assert result.returncode == 0, result.stdout
    # No automatic gc or maintenance in a repo a test makes, not for this call alone but in the new repo's own config, so
    # that init.py, or anything else that runs git there, starts none either.
    if args[:1] in (("init",), ("clone",)):
        repo = cwd if args[0] == "init" else os.path.join(cwd, args[-1])
        for name, value in QUIET:
            git(repo, "config", name, value)
    return result.stdout.strip()


def read_template(name):
    with open(os.path.join(ROOT, "templates", name), encoding="utf-8", newline="") as handle:
        return handle.read()


def without_markers(text):
    """The template's text with the lines that mark what --solo leaves out taken away, as init.py writes it."""
    return "".join(line for line in text.splitlines(True) if line not in ("<!-- team -->\n", "<!-- /team -->\n"))


def filled_in(text):
    """AGENTS.md with every placeholder of the template filled in, as step 1 of "A new repo" in STARTING.md asks."""
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


# The sample of the dry run on the landing page, and the command on the page that fetches Ratchet, with its version.
SAMPLE = re.compile(r'<pre class="sample">([^<>]*)</pre>')
SAMPLE_COMMAND = "$ python3 .ratchet/checks/init.py --check"
PAGE_FETCH = re.compile(r"(?m)^<pre><code>git clone --branch v([0-9]+\.[0-9]+) "
                        r"https://github\.com/fabian-von-tiedemann/ratchet \.ratchet</code></pre>$")


def dry_run(source, branch=None):
    """(exit code, lines) of init.py --check in a new empty git repo, with source cloned into its .ratchet, at the tag
    branch, or at the HEAD of source when branch is None, as README's command fetches Ratchet."""
    project = os.path.join(tempfile.mkdtemp(prefix="ratchet-test-"), "demo-project")
    try:
        os.mkdir(project)
        git(project, "init", "-q")
        git(project, "clone", "-q", *(["--branch", branch] if branch else []), source, ".ratchet")
        result = subprocess.run([sys.executable, os.path.join(project, ".ratchet", "checks", "init.py"), "--check"],
                                cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                                env=dict(environment(), PWD=project))
        return result.returncode, result.stdout.split("\n")
    finally:
        shutil.rmtree(os.path.dirname(project))


def sample_problems(root, head):
    """Why the sample on root's landing page is not what init.py --check prints in an empty repo at the version that the
    page's clone command fetches, as messages, or nothing.

    The page fetches the tag vX.Y that its clone command names, so the sample is compared with that tag's own init.py,
    cloned from root, which must hold the tag. Only in the release of vX.Y, where ratchet.json names X.Y and the first
    entry of CHANGELOG.md is X.Y with a date, does the tag not exist yet, and the sample is compared with head, a git
    repo whose HEAD holds root as it stands. A tag that is missing anywhere else is a problem: the head is never taken in
    its place. After its first line, the command, each line of the sample is a line that the run prints, so the lines
    that differ between runs, the commit and the project's name, need not stand in it.
    """
    with open(os.path.join(root, "docs", "index.html"), encoding="utf-8") as handle:
        page = handle.read()
    samples, fetched = SAMPLE.findall(page), PAGE_FETCH.findall(page)
    if len(samples) != 1 or len(fetched) != 1:
        return ["the page holds %d samples of the dry run and %d clone commands, and must hold one of each"
                % (len(samples), len(fetched))]
    sample, version = html.unescape(samples[0]).split("\n"), fetched[0]
    if sample[0] != SAMPLE_COMMAND or len(sample) < 2:
        return ["the sample must start with the line %r and show what it prints" % SAMPLE_COMMAND]
    with open(os.path.join(root, "ratchet.json"), encoding="utf-8") as handle:
        current = json.load(handle)["version"]
    date, newest = generate.changelog_context(root)
    tag = "v" + version
    if version == current and date is not None and newest == current:
        source, branch, which = head, None, "the head, the release of %s, whose tag %s does not exist yet" % (version, tag)
    else:
        found = subprocess.run(["git", "-C", root, "rev-parse", "-q", "--verify", "refs/tags/%s^{commit}" % tag],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=environment())
        if found.returncode != 0:
            return ["the page fetches %s with its clone command, and this checkout has no tag %s, so the sample cannot be "
                    "compared with what that version prints. Fetch the tags, with git fetch --tags, or in CI with "
                    "fetch-depth: 0 in actions/checkout. The head is not compared in its place" % (tag, tag)]
        source, branch, which = root, tag, "the tag %s, which the page's clone command fetches" % tag
    code, printed = dry_run(source, branch)
    if code != 0:
        return ["init.py --check exits %d in an empty repo at %s:\n%s" % (code, which, "\n".join(printed))]
    missing = [line for line in sample[1:] if line not in printed]
    if missing:
        return ["the sample on the page holds lines that init.py --check does not print in an empty repo at %s: %s"
                % (which, missing)]
    return []


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
        cls.runner = git(cls.source, "rev-parse", "HEAD:checks/run_pinned.py")
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
        # PWD as a shell gives it after cd into the project, so the paths init.py prints are the ones the test spelled,
        # whether or not the temporary directory is reached through a link, such as /var to /private/var on macOS.
        result = subprocess.run([sys.executable, script] + list(args),
                                cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                                env=dict(environment(), PWD=project))
        return result.returncode, result.stdout

    def path(self, *parts):
        return os.path.join(self.project, *parts)

    def text(self, *parts):
        with open(self.path(*parts), encoding="utf-8", newline="") as handle:
            return handle.read()

    def write(self, name, text):
        with open(self.path(name), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def test_a_file_where_a_directory_of_a_path_should_be_refuses_the_run_cleanly(self):
        # Review of 3219bf4: .github, or .github/workflows, is a regular file. Both modes refuse with exit 2, write
        # nothing, and show no traceback.
        for name in (".github", os.path.join(".github", "workflows")):
            with self.subTest(file=name):
                os.makedirs(os.path.dirname(self.path(name)) or self.project, exist_ok=True)
                with open(self.path(name), "w", encoding="utf-8") as handle:
                    handle.write("not a directory\n")
                before = sorted(os.listdir(self.project))
                for args in (("--check",), ()):
                    code, output = self.init(*args)
                    self.assertEqual(code, 2, output)
                    self.assertNotIn("Traceback", output)
                    self.assertIn("init: nothing was written", output)
                    self.assertNotIn("would write", output)
                    self.assertEqual(sorted(os.listdir(self.project)), before)
                shutil.rmtree(self.path(".github")) if os.path.isdir(self.path(".github")) else os.remove(self.path(".github"))

    def test_a_link_on_a_path_it_writes_refuses_the_run_before_anything_is_written(self):
        # Review of ef5cbaa: .github is a link that git tracks, to a directory outside. --check and a real run both find
        # the link while they plan, refuse, and write nothing: never "would write", and never some files before the run
        # stops at the workflow.
        outside = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, outside)
        os.symlink(outside, self.path(".github"))
        git(self.project, "add", ".github")
        git(self.project, "commit", "-q", "-m", "a link")
        before = sorted(os.listdir(self.project))
        for args in (("--check",), ()):
            with self.subTest(args=args):
                code, output = self.init(*args)
                self.assertEqual(code, 2, output)
                self.assertIn(".github is a symbolic link", output)
                self.assertNotIn("would write", output)
                self.assertIn("init: nothing was written", output)
                self.assertEqual(sorted(os.listdir(self.project)), before)
                self.assertEqual(os.listdir(outside), [])

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
        self.assertEqual(self.text("CLAUDE.md"), read_template("CLAUDE.md"))
        self.assertIn("@AGENTS.md", self.text("CLAUDE.md").split("\n"))
        self.assert_ratchet_ignored()
        self.assertIn("10 rules match Ratchet %s" % self.version, output)
        self.assertNotIn("adopt mode", output)

    def test_a_start_says_which_path_it_takes_and_why_and_adopt_mode_does_not(self):
        # STARTING.md says init.py takes one of two paths and says which. Adopt mode says so in its line; a start says so
        # in one line too, in --check and in a real run, with the reason that adopt_mode has for not adopting.
        start = "init: a new start: %s, so init.py writes %s, and adds /.ratchet/ to .gitignore. It never overwrites a file\n"
        every = ".github/workflows/ratchet.yml, AGENTS.md, CLAUDE.md, register.json and REGISTER.md"
        for args in (("--check",), ()):
            with self.subTest(args=args):
                code, output = self.init(*args)
                self.assertEqual(code, 0, output)
                self.assertIn(start % ("the project has no instruction file of its own", every), output)
                self.assertEqual(output.count("init: a new start"), 1)
                self.assertNotIn("adopt mode", output)
        code, output = self.init("--check")
        self.assertEqual(code, 0, output)
        self.assertIn(start % (".github/workflows/ratchet.yml is there, which init.py writes first in a start",
                               ".github/workflows/ratchet.yml, AGENTS.md, register.json and REGISTER.md"), output)
        # A register that names an instruction file keeps a repo with its own AGENTS.md out of adopt mode.
        self.project = self.make_project("named")
        self.write("AGENTS.md", "# Our own rules\n")
        register = json.loads(init.register_text("named", init.registry.load(os.path.join(ROOT, "ratchet.json"))))
        register["instructions"] = "AGENTS.md"
        self.write("register.json", json.dumps(register, indent=2) + "\n")
        code, output = self.init("--check")
        self.assertIn(start % ("register.json names an instruction file in instructions",
                               ".github/workflows/ratchet.yml, AGENTS.md, register.json and REGISTER.md"), output)
        # Adopt mode prints its own line and never this one.
        self.project = self.make_project("adopted")
        self.write("CLAUDE.md", "# Our own rules\n")
        for args in (("--check",), ()):
            with self.subTest(adopt=args):
                code, output = self.init(*args)
                self.assertIn("init: adopt mode: CLAUDE.md is the project's own instruction file", output)
                self.assertNotIn("init: a new start", output)

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
                for name in ("AGENTS.md", "CLAUDE.md", "register.json", "REGISTER.md",
                             os.path.join(".github", "workflows", "ratchet.yml")):
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
        self.assertEqual(code, 0, output)
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
        # ratchet.owner-paths, like ratchet.protected-main, is checked by a setting of the host (the review of step 8).
        waiting = ("ratchet.register-on-top", "ratchet.protected-main", "ratchet.owner-paths", "ratchet.no-secrets",
                   "ratchet.lesson-names-check")
        self.assertEqual(list(init.WAIT_FOR_REMOTE), list(waiting))
        for args in ((), ("--check",)):
            with self.subTest(args=args):
                code, output = self.init(*args)
                self.assertEqual(code, 0, output)
                self.assertIn("names no remote", output)
                for key in waiting:
                    self.assertIn(key, output)
                    self.assertIn("  %s: %s\n" % (key, init.WAIT_FOR_REMOTE[key]), output)
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
        self.assertEqual(code, 0, output)
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

    def test_the_sample_on_the_landing_page_is_what_the_dry_run_prints_at_the_version_the_page_fetches(self):
        # The landing page shows the dry run: after its first line, the command, each line is one that --check prints in
        # an empty repo, at the tag the page's clone command fetches, or at the head in that version's release. The
        # cases are the tests of Sample.
        self.assertEqual(sample_problems(ROOT, self.source), [])

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
        # Step 5 of D-2026-11-22-second-redraw: a file that exists and that init.py will not write is reported, not a
        # failure. The run exits 0 when the register passes. The project was started with init.py, so its workflow
        # stands, and the AGENTS.md of its own does not switch the run to adopt mode (step 9b).
        os.makedirs(self.path(".github", "workflows"))
        self.write(WRITTEN[3], read_template("ratchet-checks.yml").replace(PLACEHOLDER, self.commit))
        self.write("AGENTS.md", "# Our own rules\n")
        code, output = self.init()
        self.assertNotIn("adopt mode", output)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.text("AGENTS.md"), "# Our own rules\n")
        self.assertRegex(output, r"(?m)^skip +AGENTS\.md: it exists and differs")
        for name in WRITTEN[1:]:
            with self.subTest(file=name):
                self.assertTrue(os.path.isfile(self.path(name)), output)
        self.assertIn("1 file left as it is", output)

    def test_paths_are_printed_as_typed_from_a_folder_reached_through_a_link(self):
        # Step 5 of D-2026-11-22-second-redraw: the folder is reached through a link above the repo, as /var is on macOS,
        # and init.py is run as README says, with the shell's PWD. The paths it prints are the ones the user typed, not
        # the ones the system resolves, which once came out as ../../../../private/var/... A link below the repo is
        # still refused (test_a_link_on_a_path_it_writes_refuses_the_run_before_anything_is_written).
        real = os.path.join(self.directory, "real")
        os.mkdir(real)
        os.rename(self.project, os.path.join(real, "demo-project"))
        os.symlink(real, os.path.join(self.directory, "alias"))
        project = os.path.join(self.directory, "alias", "demo-project")
        for args in (("--check",), ()):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, os.path.join(".ratchet", "checks", "init.py")] + list(args),
                                        cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        universal_newlines=True, env=dict(environment(), PWD=project))
                output = result.stdout
                self.assertEqual(result.returncode, 0, output)
                self.assertIn("init: Ratchet %s from .ratchet, at commit" % self.version, output)
                self.assertNotIn(real, output)
                self.assertNotIn(os.path.realpath(real), output)
                self.assertNotIn("..", output.replace("...", ""))
        self.assertIn("init: python3 .ratchet/checks/check_register.py register.json --markdown REGISTER.md\n", output)

    def test_a_second_run_changes_nothing(self):
        code, output = self.init()
        self.assertEqual(code, 0, output)
        before = snapshot(self.project)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.project), before)
        self.assertIn("Nothing changed", output)
        self.assertNotRegex(output, r"(?m)^(write|add) ")
        # Every file but CLAUDE.md, which a run names only when it writes it (review round 2 of #158).
        self.assertEqual(len(re.findall(r"(?m)^unchanged ", output)), len(WRITTEN) - 1, output)
        self.assertNotIn("CLAUDE.md", output)

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
        # Step 5 of D-2026-11-22-second-redraw: a dry run on a project that has its own workflow reports the file and
        # exits 0, since the plan can be carried out. One that has its own instruction file is in adopt mode (step 9b),
        # which test_adopt_check_and_a_real_run_agree covers.
        for name, text in ((WRITTEN[3], "name: our own\n"),):
            with self.subTest(file=name):
                os.makedirs(os.path.dirname(self.path(name)) or self.project, exist_ok=True)
                self.write(name, text)
                before = snapshot(self.project)
                code, output = self.init("--check")
                self.assertEqual(code, 0, output)
                self.assertEqual(snapshot(self.project), before)
                self.assertRegex(output, r"(?m)^skip +%s: it exists and differs" % re.escape(name.replace(os.sep, "/")))
                self.assertIn("1 file left as it is", output)
                self.assertIn("the register it would leave passes", output)
                code, output = self.init()
                self.assertEqual(code, 0, output)
                self.assertEqual(self.text(name), text)
                self.assertIn("1 file left as it is", output)
                self.assertNotIn("register check failed", output)
                for written in WRITTEN:
                    os.remove(self.path(written))

    def test_a_register_that_would_not_pass_exits_1_with_and_without_check(self):
        # A register.json of the project's own that does not pass, and a REGISTER.md that is not what register.json
        # generates, each fail the register check at the end of a real run, so --check says so and exits 1 too.
        code, output = self.init()
        self.assertEqual(code, 0, output)
        register, markdown = self.text("register.json"), self.text("REGISTER.md")
        cases = (("register.json", '{"project": "demo-project"}\n', "does not pass"),
                 ("REGISTER.md", markdown + "\nOur own line.\n", "is not what register.json generates"))
        for name, text, said in cases:
            with self.subTest(file=name):
                self.write(name, text)
                before = snapshot(self.project)
                code, output = self.init("--check")
                self.assertEqual(code, 1, output)
                self.assertEqual(snapshot(self.project), before)
                self.assertIn("the register it would leave does not pass", output)
                self.assertIn(said, output)
                code, output = self.init()
                self.assertEqual(code, 1, output)
                self.assertEqual(snapshot(self.project), before)
                self.assertIn("register check failed", output)
                self.write("register.json", register)
                self.write("REGISTER.md", markdown)

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
        init.add_line(self.project, path, b"build/\n", b"build/\n/.ratchet/\n")
        self.assertEqual(self.text(".gitignore"), "build/\n/.ratchet/\n")
        with self.assertRaises(init.Changed):
            init.add_line(self.project, path, b"build/\n", b"build/\n/.ratchet/\n")
        self.assertEqual(self.text(".gitignore"), "build/\n/.ratchet/\n")
        self.assertEqual(sorted(os.listdir(self.project)), [".git", ".gitignore", ".ratchet"])

    def instructions_case(self, value, prepare):
        """A new project whose own register.json names value in instructions, prepared by prepare(project, register), with
        no REGISTER.md. (the exit code of --check, the exit code of a real run, the output of each)."""
        import check_register
        self.project = self.make_project("case-%d" % len(os.listdir(self.directory)))
        register = json.loads(init.register_text("demo-project", init.registry.load(os.path.join(ROOT, "ratchet.json"))))
        register["instructions"] = value
        self.write("register.json", json.dumps(register, indent=2) + "\n")
        prepare(self.project, register, check_register.render_block(register))
        before = snapshot(self.project)
        checked, check_output = self.init("--check")
        self.assertEqual(snapshot(self.project), before)
        code, output = self.init()
        return checked, code, check_output, output

    def test_check_and_a_real_run_agree_on_the_instruction_file_the_register_names(self):
        # Review of d86ff3e (Gemini, proven by run): the check at the end of a real run also reads the instruction file
        # that register.json names in instructions, and --check said nothing of it, so it exited 0 where a real run exits
        # 1. Both now reach the verdict with check_register.generated_problems, --check with the bytes it would write.
        def nothing(project, register, block):
            pass

        def write(name, text):
            def prepare(project, register, block):
                os.makedirs(os.path.dirname(os.path.join(project, name)) or project, exist_ok=True)
                with open(os.path.join(project, name), "w", encoding="utf-8", newline="") as handle:
                    handle.write(text(block))
            return prepare

        def linked(project, register, block):
            os.mkdir(os.path.join(project, "real"))
            with open(os.path.join(project, "real", "AGENTS.md"), "w", encoding="utf-8", newline="") as handle:
                handle.write(block + "\n# Our own rules\n")
            os.symlink("real", os.path.join(project, "link"))

        failing = (
            ("AGENTS.md", nothing, "AGENTS.md: holds no generated block"),
            ("AGENTS.md", write("AGENTS.md", lambda block: "# Our own rules\n"), "AGENTS.md: holds no generated block"),
            ("AGENTS.md", write("AGENTS.md", lambda block: block.replace("## Rules in force", "## Rules once") + "\n# Ours\n"),
             "is not what register.json generates"),
            ("AGENTS.md", write("AGENTS.md", lambda block: block + block), "the markers of the generated block are broken"),
            ("CLAUDE.md", nothing, "CLAUDE.md: the file is missing"),
            ("link/AGENTS.md", linked, "link is a symbolic link"),
            ("REGISTER.md", nothing, "REGISTER.md: holds no generated block"),
        )
        for value, prepare, said in failing:
            with self.subTest(instructions=value, said=said):
                checked, code, check_output, output = self.instructions_case(value, prepare)
                self.assertEqual((checked, code), (1, 1), check_output + output)
                self.assertIn(said, check_output)
                self.assertIn(said, output)
                self.assertIn("the register it would leave does not pass", check_output)
                # A register that names an instruction file is in the copied mode with the block, never in adopt mode.
                self.assertNotIn("adopt mode", check_output + output)
        for value, prepare in (("AGENTS.md", write("AGENTS.md", lambda block: block + "\n# Our own rules\n")),
                               ("docs/RULES.md", write(os.path.join("docs", "RULES.md"), lambda block: block))):
            with self.subTest(instructions=value, passes=True):
                checked, code, check_output, output = self.instructions_case(value, prepare)
                self.assertEqual((checked, code), (0, 0), check_output + output)
                self.assertIn("the register it would leave passes", check_output)

    def test_a_register_md_that_is_not_a_plain_file_is_named_so_and_fails_both_ways(self):
        # Review of d86ff3e: a directory or a link at REGISTER.md is "not a plain file", not "not what register.json
        # generates", and both --check and a real run exit 1.
        code, output = self.init()
        self.assertEqual(code, 0, output)
        markdown = self.text("REGISTER.md")
        os.remove(self.path("REGISTER.md"))
        with open(self.path("ours.md"), "w", encoding="utf-8", newline="") as handle:
            handle.write(markdown)
        for make in (lambda path: os.mkdir(path), lambda path: os.symlink("ours.md", path)):
            make(self.path("REGISTER.md"))
            with self.subTest(link=os.path.islink(self.path("REGISTER.md"))):
                checked, check_output = self.init("--check")
                real, output = self.init()
                self.assertEqual((checked, real), (1, 1), check_output + output)
                self.assertRegex(check_output, r"(?m)^skip +REGISTER\.md: it exists and is not a plain file")
                self.assertRegex(output, r"(?m)^skip +REGISTER\.md: it exists and is not a plain file")
            if os.path.islink(self.path("REGISTER.md")):
                os.remove(self.path("REGISTER.md"))
            else:
                os.rmdir(self.path("REGISTER.md"))

    def test_the_last_line_says_only_what_applies(self):
        # Review of d86ff3e: with nothing written, or with the project's own AGENTS.md kept, the last line does not ask
        # to fill in AGENTS.md or name files that were not written.
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertIn("init: done. Fill in AGENTS.md, and commit .github/workflows/ratchet.yml, AGENTS.md, CLAUDE.md, "
                      "register.json, REGISTER.md and .gitignore\n", output)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertIn("init: done. Nothing to commit\n", output)
        for name in WRITTEN:
            os.remove(self.path(name))
        # A workflow of the project's own keeps the run out of adopt mode, so its own AGENTS.md is left as it is.
        self.write(WRITTEN[3], "name: our own\n")
        self.write("AGENTS.md", "# Our own rules\n")
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertIn("init: done. Compare each file left as it is with what init.py would write, by hand, and commit "
                      "CLAUDE.md, register.json, REGISTER.md and .gitignore\n", output)
        self.assertNotIn("Fill in AGENTS.md", output)

    def run_patched(self, patch, *args):
        """Run init.py as the README does, with a change to it or to os made first, in the same process."""
        code = "\n".join(["import errno, os, sys",
                          "sys.path.insert(0, os.path.join('.ratchet', 'checks'))",
                          "import init", patch, "sys.exit(init.main(sys.argv[1:]))"])
        result = subprocess.run([sys.executable, "-B", "-c", code] + list(args), cwd=self.project, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True, env=environment())
        return result.returncode, result.stdout

    def test_an_existing_register_is_kept_and_its_register_md_generated_from_it(self):
        code, output = self.init("--name", "first")
        self.assertEqual(code, 0, output)
        os.remove(self.path("REGISTER.md"))
        code, output = self.init("--name", "second")
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads(self.text("register.json"))["project"], "first")
        self.assertIn("# Register for first\n", self.text("REGISTER.md"))
        self.assertRegex(output, r"(?m)^skip +register\.json: it exists and differs")
        self.assertRegex(output, r"(?m)^write +REGISTER\.md")

    def test_a_file_in_the_way_that_is_not_a_plain_file_is_skipped(self):
        os.mkdir(self.path("AGENTS.md"))
        code, output = self.init()
        self.assertEqual(code, 0, output)
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
        # The workflow is the first file written (step 9b), so it is the one it stops at.
        self.assertIn("cannot write .github/workflows/ratchet.yml", output)
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
                        init.write_new(self.project, path, b"x" * 4096)
                self.assertFalse(os.path.lexists(path))
                self.assertEqual(sorted(os.listdir(self.project)), [".git", ".ratchet"])

    def test_without_hard_links_write_new_creates_nothing(self):
        path = self.path("AGENTS.md")
        with unittest.mock.patch.object(os, "link", no_link):
            with self.assertRaises(OSError):
                init.write_new(self.project, path, b"whole\n")
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
            self.assertTrue(init.write_new(self.project, path, data))
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
            self.assertFalse(init.write_new(self.project, path, b"ours\n"))
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

    def test_the_reasons_for_waiting_and_the_case_table_are_pinned(self):
        # The review at 18d1ce8: the small texts of the fix that named ratchet.owner-paths among the rules that wait for
        # a remote. Each reason word for word, and checks/README.md counts and names the five.
        self.assertEqual(init.WAIT_FOR_REMOTE, {
            "ratchet.register-on-top": "its check runs in CI on the host",
            "ratchet.protected-main": "the protection of main is a setting of the host",
            "ratchet.owner-paths": "the owner's required review on the owner's paths is a setting of the host",
            "ratchet.no-secrets": "its scan runs in CI on the host",
            "ratchet.lesson-names-check": "the lesson template is an issue template of the host",
        })
        with open(os.path.join(ROOT, "checks", "README.md"), encoding="utf-8") as handle:
            readme = handle.read()
        self.assertEqual(len(init.WAIT_FOR_REMOTE), 5)
        self.assertIn("| No remote in the git config, with and without `--check` | The five rules that wait for one are "
                      "named, and no other; after `git remote add`, none |\n", readme)
        self.assertIn("the adopted rules whose check cannot run before it has one, with why: `ratchet.register-on-top`, "
                      "`ratchet.protected-main`, `ratchet.owner-paths`, `ratchet.no-secrets` and "
                      "`ratchet.lesson-names-check`, as far as the register that stands after the run adopts them.", readme)

    # Adopt mode, step 9b of D-2026-11-22-second-redraw: a repo that already has an instruction file of its own gets only
    # register.json, once it names with --adopt the rules its file states, with those rows by reference and no copied
    # row, and is told the rows by reference and the marker lines to add.

    SWEDISH = "# Arbetsregler\n\nVi gör ändringar via PR, och main är skyddad. Inga hemligheter i repot.\n"

    def adopt_entries(self, output):
        """The rows by reference that an adopt run printed, by key, each parsed from its one line of JSON."""
        return {entry["key"]: entry for entry in (json.loads(line.strip()) for line in output.split("\n")
                                                    if line.strip().startswith('{"key": "ratchet.'))}

    def assertStepParses(self, output, run):
        """The printed step is YAML that a workflow can hold: a block scalar, not "run: { ... }", which YAML reads as a
        flow mapping and refuses. The standard library has no YAML parser, so the shape is pinned exactly, and Ruby's or
        PyYAML's parser reads it where one is installed."""
        lines = output.split("\n")
        at = lines.index("  - name: Ratchet's register check")
        step = lines[at:at + 3]
        self.assertEqual(step, ["  - name: Ratchet's register check", "    run: |", "      " + run])
        self.assertTrue(lines[at + 3].startswith("init:"), lines[at + 3])
        document = "steps:\n" + "\n".join(step) + "\n"
        expected = {"steps": [{"name": "Ratchet's register check", "run": run + "\n"}]}
        parsers = []
        if shutil.which("ruby"):
            parsers.append(["ruby", "-ryaml", "-rjson", "-e", "print JSON.generate(YAML.safe_load(STDIN.read))"])
        if subprocess.run([sys.executable, "-c", "import yaml"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            parsers.append([sys.executable, "-c", "import json, sys, yaml; print(json.dumps(yaml.safe_load(sys.stdin)))"])
        for parser in parsers:
            with self.subTest(parser=parser[0]):
                result = subprocess.run(parser, input=document, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        universal_newlines=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected)

    def test_a_repo_with_its_own_instruction_file_is_adopted_and_the_file_is_never_written(self):
        import check_register
        ratchet = init.registry.load(os.path.join(ROOT, "ratchet.json"))
        by_key = init.registry.rules_by_key(ratchet)
        # A file in Swedish, and one that is not UTF-8 at all: adopt mode never reads what the file holds. The first run
        # writes nothing: no register.json until the project names the rules its file states.
        for data in (self.SWEDISH.encode("utf-8"), "# R\u00e8gles\n".encode("latin-1")):
            with self.subTest(data=data[:12]):
                self.project = self.make_project("adopt-%d" % len(os.listdir(self.directory)))
                with open(self.path("AGENTS.md"), "wb") as handle:
                    handle.write(data)
                code, output = self.init()
                self.assertEqual(code, 0, output)
                self.assertIn("init: adopt mode: AGENTS.md is the project's own instruction file", output)
                self.assertEqual(snapshot(self.project), {"AGENTS.md": data})
                self.assertRegex(output, r"(?m)^not yet +register\.json: it is written once you name with --adopt")
                self.assertIn("init: there is no register.json yet, so there is no register to check", output)
                # The rows by reference and their marker lines, for every rule to start with, pointing at AGENTS.md.
                entries = self.adopt_entries(output)
                self.assertEqual(sorted(entries), sorted(ratchet["start"]))
                for key, entry in entries.items():
                    self.assertEqual(entry["stands_in"], "AGENTS.md")
                    self.assertEqual(entry["sha256"], check_register.reference_sha256(by_key[key]))
                    self.assertIn("\n<!-- ratchet:rule %s -->\n" % key, output)
                # The copy of run_pinned.py and the one step that runs it, pinned to the commit, and no workflow or admin.
                # The copy is kept only when it hashes to the blob the pinned tree names, and the step hashes it again.
                self.assertIn("\n  %s\n" % run_pinned.copy_command(".ratchet/.git/objects", self.commit, self.runner,
                                                                     ".github/ratchet/run_pinned.py"), output)
                self.assertIn("it keeps the copy only when its bytes are blob %s" % self.runner, output)
                run = run_pinned.run_command(self.commit, self.runner, ".github/ratchet/run_pinned.py")
                self.assertNotIn("\n", run)
                self.assertIn("\n  - name: Ratchet's register check\n    run: |\n      %s\n" % run, output)
                self.assertStepParses(output, run)
                self.assertIn("No workflow and no required job are added", output)
                # One line names adoption in part, and its exact form.
                self.assertEqual(output.count("adopted in part"), 1, output)
                self.assertIn('may be adopted in part: in its row in register.json, give "where": "Not stated here: <clause>; '
                              '<clause>."', output)
                self.assertIn("python3 .ratchet/checks/inventory.py", output)
                self.assertNotIn("..", output.replace("...", ""))
                self.assertNotIn("would write", output)
        # With the marker of a rule in the file, --adopt writes register.json with that row by reference and no other:
        # no copied row, and no instructions.
        self.project = self.make_project("adopt-with-marker")
        self.write("AGENTS.md", self.SWEDISH + "<!-- ratchet:rule ratchet.protected-main -->\n")
        code, output = self.init("--adopt", "ratchet.protected-main")
        self.assertEqual(code, 0, output)
        self.assertRegex(output, r"(?m)^write +register\.json$")
        register = json.loads(self.text("register.json"))
        self.assertEqual(register["project"], self.project.rsplit(os.sep, 1)[1])
        self.assertNotIn("instructions", register)
        self.assertEqual(register["adopted"], [self.adopt_entries(output).get("ratchet.protected-main") or
                                               init.reference_row("ratchet.protected-main", "AGENTS.md", ratchet)])
        self.assertEqual(check_register.check(register, ratchet)[0], [])
        self.assertIn("init: python3 .ratchet/checks/check_register.py register.json\n", output)
        self.assertNotIn(":rule ratchet.protected-main -->", output)

    def test_adopt_check_and_a_real_run_agree(self):
        self.write("AGENTS.md", self.SWEDISH)
        before = snapshot(self.project)
        code, output = self.init("--check")
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.project), before)
        self.assertIn("adopt mode", output)
        self.assertRegex(output, r"(?m)^not yet +register\.json")
        checked = output
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.project), before)
        self.assertEqual(self.adopt_entries(checked), self.adopt_entries(output))
        # --adopt a rule whose marker is not in AGENTS.md: both exit 1, write nothing and name the missing marker.
        checked, check_output = self.init("--check", "--adopt", "ratchet.no-secrets")
        code, output = self.init("--adopt", "ratchet.no-secrets")
        self.assertEqual((checked, code), (1, 1), check_output + output)
        self.assertEqual(snapshot(self.project), before)
        for said in (check_output, output):
            self.assertIn("AGENTS.md: holds no marker for ratchet.no-secrets", said)
            self.assertRegex(said, r"(?m)^skip +register\.json: the register would not pass check_register\.py, so it "
                                   r"is not written")
        self.assertIn("init: register.json would be not written", check_output)
        self.assertIn("init: register.json was not written", output)
        # With the marker: --check says it would write it and that it passes, and the real run writes it.
        with open(self.path("AGENTS.md"), "a", encoding="utf-8") as handle:
            handle.write("<!-- ratchet:rule ratchet.no-secrets -->\n")
        checked, check_output = self.init("--check", "--adopt", "ratchet.no-secrets")
        self.assertEqual(checked, 0, check_output)
        self.assertRegex(check_output, r"(?m)^would write +register\.json$")
        self.assertIn("the register it would leave passes", check_output)
        self.assertFalse(os.path.lexists(self.path("register.json")))
        code, output = self.init("--adopt", "ratchet.no-secrets")
        self.assertEqual(code, 0, output)
        register = json.loads(self.text("register.json"))
        # A register.json that is a link: not a plain file, so both exit 1.
        os.remove(self.path("register.json"))
        self.write("ours.json", json.dumps(register, indent=2) + "\n")
        os.symlink("ours.json", self.path("register.json"))
        for args in (("--check",), (), ("--adopt", "ratchet.no-secrets")):
            code, output = self.init(*args)
            self.assertEqual(code, 1, output)
            self.assertRegex(output, r"(?m)^skip +register\.json: it exists and is not a plain file")
        # A run that cannot run, cannot in both: a bad name, a rule that is not Ratchet's, a rule named twice.
        os.remove(self.path("register.json"))
        for bad in (("--name", "not a name!"), ("--adopt", "ratchet.no-such-rule"),
                    ("--adopt", "ratchet.no-secrets", "--adopt", "ratchet.no-secrets")):
            for args in (("--check",), ()):
                code, output = self.init(*(bad + args))
                self.assertEqual(code, 2, output)
        self.assertFalse(os.path.lexists(self.path("register.json")))

    def test_adopt_is_refused_in_a_start(self):
        for args in (("--check",), ()):
            code, output = self.init("--adopt", "ratchet.no-secrets", *args)
            self.assertEqual(code, 2, output)
            self.assertIn("--adopt is for adopt mode", output)
            self.assertEqual(snapshot(self.project), {})

    def test_a_second_adopt_run_changes_nothing(self):
        self.write("CLAUDE.md", self.SWEDISH + "<!-- ratchet:rule ratchet.no-secrets -->\n")
        code, output = self.init("--adopt", "ratchet.no-secrets")
        self.assertEqual(code, 0, output)
        before = snapshot(self.project)
        code, output = self.init("--adopt", "ratchet.no-secrets")
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.project), before)
        self.assertIn("adopt mode", output)
        self.assertRegex(output, r"(?m)^unchanged +register\.json$")
        self.assertIn("Nothing changed", output)
        self.assertIn("init: done. Nothing to commit", output)
        # Without --adopt, the register that stands is the project's, and is checked as it stands.
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.project), before)
        self.assertRegex(output, r"(?m)^skip +register\.json: it is the project's own\. It was left as it is, and is "
                                 r"checked as it stands$")
        self.assertIn("init: done. Nothing to commit", output)

    def check_register(self):
        result = subprocess.run([sys.executable, self.path(".ratchet", "checks", "check_register.py"), "register.json"],
                                cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        return result.returncode, result.stdout

    def test_an_adoption_end_to_end_add_the_markers_and_the_check_passes(self):
        # What README says to do after an adopt run: put a marker line by the project's own wording of a rule, and name
        # it with --adopt. The check passes, labeling each row as the weaker mode. A run after it stays in adopt mode,
        # keeps the register and no longer prints those rows.
        self.write("AGENTS.md", self.SWEDISH)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        with open(self.path("AGENTS.md"), "a", encoding="utf-8") as handle:
            for key in ("ratchet.protected-main", "ratchet.no-secrets"):
                handle.write("<!-- ratchet:rule %s -->\n" % key)
        code, output = self.init("--adopt", "ratchet.protected-main", "--adopt", "ratchet.no-secrets")
        self.assertEqual(code, 0, output)
        code, said = self.check_register()
        self.assertEqual(code, 0, said)
        self.assertIn("2 rules are adopted by reference", said)
        self.assertIn("0 rules match Ratchet", said)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertIn("adopt mode", output)
        self.assertRegex(output, r"(?m)^skip +register\.json: it is the project's own")
        self.assertNotIn("ratchet:rule ratchet.no-secrets", output)
        self.assertIn("ratchet:rule ratchet.decision-as-file", output)
        self.assertIn("init: paste the row of each rule whose marker you put in AGENTS.md into adopted", output)

    def test_an_adoption_pasted_verbatim_from_what_init_prints_passes(self):
        # Review of 58ca014: the marker lines, taken from the printed output as they stand and pasted unchanged, every
        # one of them, make check_register.py pass once --adopt names them, and the rows it writes are the rows printed.
        # A marker starts at column zero, so one printed with an indent fails. A finished adoption run again changes
        # nothing and says only what applies.
        self.write("AGENTS.md", self.SWEDISH)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        lines = output.split("\n")
        markers = [line for line in lines if "<!-- ratchet:rule " in line]
        rows = self.adopt_entries(output)
        ratchet = init.registry.load(os.path.join(ROOT, "ratchet.json"))
        self.assertEqual(len(markers), len(ratchet["start"]), output)
        self.assertEqual(len(rows), len(markers), output)
        with open(self.path("AGENTS.md"), "a", encoding="utf-8", newline="") as handle:
            handle.write("\n" + "\n".join(markers) + "\n")
        adopt = []
        for key in ratchet["start"]:
            adopt += ["--adopt", key]
        code, output = self.init(*adopt)
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads(self.text("register.json"))["adopted"], [rows[key] for key in ratchet["start"]])
        code, said = self.check_register()
        self.assertEqual(code, 0, said)
        self.assertIn("%d rules are adopted by reference" % len(rows), said)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertNotIn("<!-- ratchet:rule ", output)
        self.assertIn("init: done. Nothing to commit\n", output)
        self.assertNotIn("Compare each file", output)

    def test_printed_rows_carry_a_status_only_where_the_rule_names_a_check(self):
        # Review of 58ca014: check_register.py refuses a status on a rule that is text only, such as
        # ratchet.evidence-before-done, and needs one on a rule that names a check.
        self.write("AGENTS.md", self.SWEDISH)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        by_key = init.registry.rules_by_key(init.registry.load(os.path.join(ROOT, "ratchet.json")))
        entries = self.adopt_entries(output)
        kinds = set()
        for key, entry in entries.items():
            with self.subTest(key=key):
                if by_key[key]["ratchet"].startswith("Check: "):
                    kinds.add("check")
                    self.assertEqual(entry.get("status"), "text only for now")
                else:
                    kinds.add("text")
                    self.assertNotIn("status", entry)
        self.assertEqual(kinds, {"check", "text"})
        self.assertNotIn("status", entries["ratchet.evidence-before-done"])

    def test_adopt_mode_never_reads_register_md(self):
        # Review of 58ca014: adopt mode leaves REGISTER.md out of its verdict, as check_register.py register.json does,
        # so it does not read it. One that cannot be read, a link or a directory: register.json is written, exit 0 both ways.
        def unreadable():
            self.write("REGISTER.md", "# ours\n")
            os.chmod(self.path("REGISTER.md"), 0)
            self.addCleanup(os.chmod, self.path("REGISTER.md"), 0o644)

        def linked():
            self.write("elsewhere.md", "# ours\n")
            os.symlink("elsewhere.md", self.path("REGISTER.md"))

        for kind, prepare in (("unreadable", unreadable), ("link", linked),
                              ("directory", lambda: os.mkdir(self.path("REGISTER.md")))):
            with self.subTest(kind=kind):
                self.project = self.make_project("register-md-%s" % kind)
                self.write("AGENTS.md", self.SWEDISH + "<!-- ratchet:rule ratchet.no-secrets -->\n")
                prepare()
                checked, check_output = self.init("--check", "--adopt", "ratchet.no-secrets")
                self.assertFalse(os.path.lexists(self.path("register.json")), check_output)
                code, output = self.init("--adopt", "ratchet.no-secrets")
                self.assertEqual((checked, code), (0, 0), check_output + output)
                for said in (check_output, output):
                    self.assertIn("init: REGISTER.md is left as it is and not checked in adopt mode", said)
                    self.assertNotIn("Traceback", said)
                self.assertTrue(os.path.isfile(self.path("register.json")), output)

    def test_an_empty_adopted_list_is_offered_register_on_top(self):
        # Review of 58ca014: a register.json of the project's own that adopts nothing does not pass, and the rule that is
        # the floor is offered with the rest.
        self.write("AGENTS.md", self.SWEDISH)
        register = json.loads(read_template("register.json"))
        register["adopted"] = []
        self.write("register.json", json.dumps(register, indent=2) + "\n")
        for args in (("--check",), ()):
            code, output = self.init(*args)
            self.assertEqual(code, 1, output)
            self.assertIn("ratchet.register-on-top", self.adopt_entries(output))

    def test_the_register_of_adopt_mode_holds_only_the_rows_named_and_no_copied_row(self):
        # Finding from a real adoption: a copied ratchet.register-on-top says the register lists every rule in force and
        # takes precedence, which is false where the project's own instruction file governs. Adopt mode copies no row.
        ratchet = init.registry.load(os.path.join(ROOT, "ratchet.json"))
        register = json.loads(init.adopt_register_text("demo", ratchet, ["ratchet.protected-main"], "CLAUDE.md"))
        self.assertEqual(register["adopted"], [init.reference_row("ratchet.protected-main", "CLAUDE.md", ratchet)])
        self.assertFalse(any("rule" in row for row in register["adopted"]))
        for keys, said in ((["ratchet.no-such-rule"], "there is no rule ratchet.no-such-rule in Ratchet"),
                           (["ratchet.no-secrets", "ratchet.no-secrets"], "--adopt names a rule twice")):
            with self.assertRaisesRegex(init.InitError, said):
                init.adopt_register_text("demo", ratchet, keys, "AGENTS.md")
        real = init.check_register.check

        def check(register, ratchet):
            if any("stands_in" in row for row in register["adopted"]):
                return ["a problem"], ""
            return real(register, ratchet)

        with unittest.mock.patch.object(init.check_register, "check", check):
            with self.assertRaisesRegex(init.InitError, "the register for adopt mode does not pass: a problem"):
                init.adopt_register_text("demo", ratchet, ["ratchet.no-secrets"], "AGENTS.md")
        self.assertFalse(hasattr(init, "ADOPT_COPIED"))

    def test_what_adopt_mode_prints_around_the_rows(self):
        # Review of 58ca014, and the findings from a real adoption: each line adopt mode prints beside the rows, pinned.
        self.write("AGENTS.md", self.SWEDISH + "<!-- ratchet:rule ratchet.protected-main -->\n")
        code, output = self.init("--check", "--adopt", "ratchet.protected-main")
        self.assertEqual(code, 0, output)
        self.assertNotIn("--solo changes nothing", output)
        # No .gitignore: the advice to add the line, and no .gitignore written.
        self.assertIn("init: .gitignore does not ignore .ratchet. Add the line /.ratchet/ to it", output)
        # The markers need a file in UTF-8 with LF line endings, said every time.
        self.assertIn("A marker line counts only in a file in UTF-8 with LF line endings", output)
        # The inventory names the required jobs, given the exported ruleset.
        self.assertIn("python3 .ratchet/checks/inventory.py --ruleset <file>", output)
        # No remote: the rule adopted waits for one.
        self.assertIn("init: the repo's git config names no remote, so these adopted rules wait for one:\n"
                      "  ratchet.protected-main: the protection of main is a setting of the host\n", output)
        # The job's token only reads, the checkout leaves no token, each with why; the line for a local check script.
        run = run_pinned.run_command(self.commit, self.runner, ".github/ratchet/run_pinned.py")
        self.assertIn("init: and give that job these, if it does not have them:\n  permissions:\n    contents: read\n"
                      "init:   the job's token can then only read the repo, so no step in the job can push or approve "
                      "with it\n", output)
        self.assertIn("    with:\n      persist-credentials: false\ninit:   the checkout then leaves no token in "
                      ".git/config, where a later step could read it\n", output)
        # An adoption report on 0.12: the line assumed set -e, so a script without it went on after a failing check.
        local = run_pinned.local_line(self.commit, self.runner, ".github/ratchet/run_pinned.py")
        self.assertEqual(local, "( %s ) || exit 1" % run)
        self.assertIn("a local check script that CI runs, put this line in it, in place of the step. It stops the script "
                      "when the check fails, with set -e or without it:\n  %s\n" % local, output)
        # How to record a rule as built, by where it is enforced, without saying that it is.
        self.assertIn('"status": "built", with "where" naming the enforcement point and when it was read back: for '
                      "ratchet.protected-main, the ruleset or branch protection of main at the host", output)
        self.assertIn("init.py cannot see what the host enforces, and does not say", output)
        self.assertIn('"key": "ratchet.decision-as-file", "stands_in": "AGENTS.md", "sha256": ', output)
        self.assertNotIn('"status": "built"}', output)
        # ratchet.register-on-top is offered with the caution that it fits only a register that governs.
        self.assertIn("init: ratchet.register-on-top fits only where the register, not AGENTS.md, lists every rule in "
                      "force and takes precedence", output)
        code, output = self.init("--solo")
        self.assertEqual(code, 0, output)
        self.assertIn("init: --solo changes nothing in adopt mode, which writes no instruction file", output)
        self.assertIn("such as python3 .ratchet/checks/init.py --adopt ratchet.protected-main.", output)
        self.assertFalse(os.path.lexists(self.path(".gitignore")))
        self.write(".gitignore", "/.ratchet/\n")
        git(self.project, "remote", "add", "origin", "https://example.invalid/demo.git")
        code, output = self.init("--adopt", "ratchet.protected-main")
        self.assertEqual(code, 0, output)
        self.assertNotIn(".gitignore does not ignore", output)
        self.assertNotIn("wait for one", output)

    def test_the_project_name_comes_from_the_git_remote_and_says_where_from(self):
        # Finding from a real adoption: in a worktree whose folder a tool named, the name was the folder's. The repo's
        # name in the url of the remote origin, or else the first remote, comes first, and the run says which it took.
        code, output = self.init("--check")
        self.assertIn('init: project name "demo-project", the folder\'s name, since the repo\'s git config names no '
                      "remote with a url\n", output)
        git(self.project, "remote", "add", "upstream", "https://example.invalid/team/upstream-name")
        git(self.project, "remote", "add", "origin", "git@example.invalid:team/my-app.git")
        code, output = self.init("--check")
        self.assertEqual(code, 0, output)
        self.assertIn('init: project name "my-app", the repo\'s name in the url of the git remote origin\n', output)
        code, output = self.init("--check", "--name", "Given")
        self.assertIn('init: project name "Given", given with --name\n', output)
        git(self.project, "remote", "remove", "origin")
        self.assertEqual(init.remote_repo(self.project), ("upstream", "upstream-name"))
        git(self.project, "remote", "set-url", "upstream", "https://example.invalid/team/www.bad")
        code, output = self.init("--check")
        self.assertEqual(code, 0, output)
        self.assertIn('init: project name "demo-project", the folder\'s name, since the repo\'s name in the url of the '
                      'git remote upstream, "www.bad", cannot be one: it would be shown as a link\n', output)

    def test_the_instruction_files_that_switch_to_adopt_mode(self):
        # .claude/CLAUDE.md alone counts; AGENTS.md is named before CLAUDE.md; a file reached through a link in a parent
        # folder does not count; a workflow that is a dangling link keeps the run out of adopt mode.
        os.makedirs(self.path(".claude"))
        self.write(os.path.join(".claude", "CLAUDE.md"), self.SWEDISH)
        code, output = self.init("--check")
        self.assertEqual(code, 0, output)
        self.assertIn("init: adopt mode: .claude/CLAUDE.md is the project's own instruction file", output)
        self.project = self.make_project("agents-and-claude")
        self.write("CLAUDE.md", self.SWEDISH)
        self.write("AGENTS.md", self.SWEDISH)
        code, output = self.init("--check")
        self.assertEqual(code, 0, output)
        self.assertIn("init: adopt mode: AGENTS.md is the project's own instruction file", output)
        self.assertIn("init: the project also has CLAUDE.md", output)
        self.assertEqual({entry["stands_in"] for entry in self.adopt_entries(output).values()}, {"AGENTS.md"})
        self.project = self.make_project("linked-parent")
        os.makedirs(self.path("real-github"))
        with open(self.path("real-github", "copilot-instructions.md"), "w", encoding="utf-8") as handle:
            handle.write(self.SWEDISH)
        os.symlink("real-github", self.path(".github"))
        self.assertEqual(init.own_instructions(self.project), [])
        self.project = self.make_project("dangling-workflow")
        self.write("AGENTS.md", self.SWEDISH)
        os.makedirs(self.path(".github", "workflows"))
        os.symlink("missing.yml", self.path(".github", "workflows", "ratchet.yml"))
        code, output = self.init("--check")
        self.assertNotIn("adopt mode", output)

    def test_adopt_mode_names_the_first_instruction_file_and_the_others(self):
        # AGENTS.md as a link to CLAUDE.md, a common layout: the link is not a plain file, so CLAUDE.md is the one named.
        self.write("CLAUDE.md", self.SWEDISH)
        os.symlink("CLAUDE.md", self.path("AGENTS.md"))
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertIn("init: adopt mode: CLAUDE.md is the project's own instruction file", output)
        self.assertEqual({entry["stands_in"] for entry in self.adopt_entries(output).values()}, {"CLAUDE.md"})
        self.assertTrue(os.path.islink(self.path("AGENTS.md")))
        # Two plain files: the first in the fixed order is named, and the other is named as one a row may point at.
        self.project = self.make_project("two-files")
        self.write("GEMINI.md", self.SWEDISH)
        os.makedirs(self.path(".github"))
        self.write(os.path.join(".github", "copilot-instructions.md"), self.SWEDISH)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertIn("init: adopt mode: GEMINI.md is the project's own instruction file", output)
        self.assertIn("init: the project also has .github/copilot-instructions.md", output)
        self.assertEqual({entry["stands_in"] for entry in self.adopt_entries(output).values()}, {"GEMINI.md"})

    def test_a_project_started_with_init_is_never_in_adopt_mode(self):
        # The workflow that init.py writes is written first, so a start that stopped halfway, with AGENTS.md written
        # and register.json not, is not taken for a project of its own on the next run, which writes the rest.
        code, output = self.run_patched("""
real = init.write_new
def write_new(root, path, data):
    if path.endswith("register.json"):
        raise OSError(errno.ENOSPC, "cut off")
    return real(root, path, data)
init.write_new = write_new""")
        self.assertEqual(code, 2, output)
        self.assertTrue(os.path.isfile(self.path("AGENTS.md")), output)
        self.assertTrue(os.path.isfile(self.path("CLAUDE.md")), output)
        self.assertTrue(os.path.isfile(self.path(WRITTEN[3])), output)
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertNotIn("adopt mode", output)
        for name in WRITTEN:
            self.assertTrue(os.path.isfile(self.path(name)), output)

    def test_a_start_stopped_at_any_file_is_never_taken_for_adopt_mode(self):
        # The CLAUDE.md that a start writes is an instruction file that switches a run to adopt mode, as AGENTS.md is.
        # A start stopped at each file in turn leaves an instruction file only when it also left the workflow, which keeps
        # the next run a start: that run is not in adopt mode, writes the rest, and leaves CLAUDE.md as it was written.
        for stop in WRITTEN:
            with self.subTest(stop=stop):
                self.project = self.make_project("stop-%d" % len(os.listdir(self.directory)))
                code, output = self.run_patched("""
real = init.write_new
def write_new(root, path, data):
    if os.path.relpath(path, root) == %r:
        raise OSError(errno.ENOSPC, "cut off")
    return real(root, path, data)
init.write_new = write_new
real_add = init.add_line
def add_line(root, path, before, after):
    if os.path.relpath(path, root) == %r:
        raise OSError(errno.ENOSPC, "cut off")
    return real_add(root, path, before, after)
init.add_line = add_line""" % (stop, stop))
                self.assertEqual(code, 2, output)
                if init.own_instructions(self.project):
                    self.assertTrue(os.path.isfile(self.path(WRITTEN[3])), output)
                self.assertEqual(init.adopt_mode(self.project), [], output)
                written = snapshot(self.project)
                code, output = self.init()
                self.assertEqual(code, 0, output)
                self.assertNotIn("adopt mode", output)
                self.assertEqual(sorted(snapshot(self.project)), sorted(WRITTEN))
                for name, data in written.items():
                    self.assertEqual(snapshot(self.project)[name], data, name)
                self.assertEqual(self.text("CLAUDE.md"), read_template("CLAUDE.md"))

    def test_a_second_start_with_the_claude_md_it_wrote_is_not_adopt_mode(self):
        # A repo init.py started has CLAUDE.md, an instruction file. The workflow it wrote keeps a second run a start:
        # with --check and without, every file unchanged, CLAUDE.md among them, and no adopt mode.
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.assertEqual(init.own_instructions(self.project), ["AGENTS.md", "CLAUDE.md"])
        before = snapshot(self.project)
        for args in (("--check",), ()):
            with self.subTest(args=args):
                code, output = self.init(*args)
                self.assertEqual(code, 0, output)
                self.assertNotIn("adopt mode", output)
                self.assertNotIn("CLAUDE.md", output)
                self.assertEqual(snapshot(self.project), before)
        # Without the workflow, the same CLAUDE.md and AGENTS.md are a repo's own, and the run is in adopt mode: what
        # recognizes a start is the workflow, and the test fails if init.py stops writing it first.
        os.remove(self.path(WRITTEN[3]))
        code, output = self.init("--check")
        self.assertIn("init: adopt mode: AGENTS.md is the project's own instruction file", output)

    def test_an_existing_claude_md_is_never_touched(self):
        # A CLAUDE.md of the project's own: in a repo init.py has not started, adopt mode, as before; in one it started,
        # neither read nor named (review round 2 of #158). Either way its bytes stay as they were.
        data = b"# Our rules for Claude\r\nKeep it short.\r\n"
        with open(self.path("CLAUDE.md"), "wb") as handle:
            handle.write(data)
        for args in (("--check",), ()):
            with self.subTest(args=args, started=False):
                code, output = self.init(*args)
                self.assertEqual(code, 0, output)
                self.assertIn("init: adopt mode: CLAUDE.md is the project's own instruction file", output)
                self.assertEqual(snapshot(self.project), {"CLAUDE.md": data})
        os.makedirs(self.path(".github", "workflows"))
        self.write(WRITTEN[3], read_template("ratchet-checks.yml").replace(PLACEHOLDER, self.commit))
        for args in (("--check",), ()):
            with self.subTest(args=args, started=True):
                code, output = self.init(*args)
                self.assertEqual(code, 0, output)
                self.assertNotIn("adopt mode", output)
                self.assertNotIn("CLAUDE.md", output)
                with open(self.path("CLAUDE.md"), "rb") as handle:
                    self.assertEqual(handle.read(), data)

    def test_claude_md_is_written_only_beside_a_register_of_init_s_own(self):
        # Review round 2 of #158: CLAUDE.md is written only when register.json is missing or holds the bytes init.py
        # writes, so a register that names CLAUDE.md, in any spelling and in any field, never gets the template there.
        # Byte for byte the register of init.py: CLAUDE.md written. One that differs, by its name alone: not written and
        # not named. One that names claude.md in lowercase, in instructions or in stands_in, on a volume that may not
        # tell case apart: no file of that name in any case written, and CLAUDE.md not named by init.py itself.
        ratchet = init.registry.load(os.path.join(ROOT, "ratchet.json"))

        def changed(change):
            def make(name):
                register = json.loads(init.register_text(name, ratchet))
                change(register)
                return json.dumps(register, indent=2) + "\n"
            return make

        cases = (("init.py's own", lambda name: init.register_text(name, ratchet), True),
                 ("another name", lambda name: init.register_text("other", ratchet), False),
                 ("claude.md in instructions", changed(lambda register: register.update(instructions="claude.md")), False),
                 ("claude.md in stands_in", changed(lambda register: register.update(
                     adopted=[init.reference_row("ratchet.no-secrets", "claude.md", ratchet)])), False))
        for case, register, written in cases:
            with self.subTest(register=case):
                self.project = self.make_project("claude-%d" % len(os.listdir(self.directory)))
                self.write("register.json", register(os.path.basename(self.project)))
                for args in (("--check",), ()):
                    code, output = self.init(*args)
                    self.assertNotIn("Traceback", output)
                    self.assertNotIn("adopt mode", output)
                    plan = re.findall(r"(?m)^(?:would write|write|unchanged|skip) +(\S+)", output)
                    self.assertEqual("CLAUDE.md" in plan, written, output)
                    if not written:
                        self.assertNotRegex(output, r"(?m)^\S.*CLAUDE\.md")
                names = [name.lower() for name in os.listdir(self.project)]
                self.assertEqual("claude.md" in names, written, names)
                if written:
                    self.assertEqual(self.text("CLAUDE.md"), read_template("CLAUDE.md"))
                    self.assertEqual(code, 0, output)
                elif case == "another name":
                    self.assertEqual(code, 0, output)

    def test_an_unreadable_claude_md_in_a_started_repo_is_never_read(self):
        # Review round 2 of #158: a CLAUDE.md in a repo init.py started is not read, so one that cannot be read is no
        # new way to stop the run. (An AGENTS.md that cannot be read stops a run with a traceback, on main as here.)
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root reads a file with mode 000")
        code, output = self.init()
        self.assertEqual(code, 0, output)
        with open(self.path("CLAUDE.md"), "rb") as handle:
            data = handle.read()
        os.chmod(self.path("CLAUDE.md"), 0)
        self.addCleanup(os.chmod, self.path("CLAUDE.md"), 0o644)
        for args in (("--check",), ()):
            with self.subTest(args=args):
                code, output = self.init(*args)
                self.assertEqual(code, 0, output)
                self.assertNotIn("Traceback", output)
                self.assertNotIn("CLAUDE.md", output)
        os.chmod(self.path("CLAUDE.md"), 0o644)
        with open(self.path("CLAUDE.md"), "rb") as handle:
            self.assertEqual(handle.read(), data)

    def test_a_claude_md_that_appears_after_the_choice_is_skipped_and_named(self):
        # Review round 3 of #158: a CLAUDE.md that stands there by the time the plan reads it, though writes_claude saw
        # none, is skipped and named like any file in the way, with no KeyError, and its bytes are left as they are.
        code, output = self.init()
        self.assertEqual(code, 0, output)
        self.write("CLAUDE.md", "# Our own\n")
        for args in (("--check",), ()):
            with self.subTest(args=args):
                code, output = self.run_patched("init.writes_claude = lambda root, planned: True", *args)
                self.assertEqual(code, 0, output)
                self.assertNotIn("Traceback", output)
                self.assertRegex(output, r"(?m)^skip +CLAUDE\.md: it exists and differs from what init\.py writes\. "
                                         r"It was left as it is: compare it with .*templates/CLAUDE\.md by hand")
                self.assertEqual(self.text("CLAUDE.md"), "# Our own\n")

    def test_a_claude_md_template_without_the_import_is_refused(self):
        self.assertIn(init.CLAUDE_IMPORT, read_template("CLAUDE.md").split("\n"))
        code, output = self.run_patched("init.template = (lambda real: lambda name: real(name).replace('@AGENTS.md', "
                                        "'AGENTS.md') if name == 'CLAUDE.md' else real(name))(init.template)")
        self.assertEqual(code, 2, output)
        self.assertIn("templates/CLAUDE.md must hold the line @AGENTS.md", output)
        self.assertEqual(snapshot(self.project), {})

    def test_adopt_mode_writes_nothing_through_a_link(self):
        # register.json is the one file adopt mode writes, and a link on its path, here the root's parent being fine
        # and the file itself a dangling link, is refused before anything is written.
        self.write("AGENTS.md", self.SWEDISH)
        outside = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, outside)
        os.symlink(os.path.join(outside, "register.json"), self.path("register.json"))
        for args in (("--check",), ()):
            code, output = self.init(*args)
            self.assertNotEqual(code, 0, output)
            self.assertEqual(os.listdir(outside), [])
            self.assertRegex(output, r"(?m)^skip +register\.json: it exists and is not a plain file")

    def test_the_repository_of_the_printed_step_is_the_one_the_template_fetches(self):
        self.assertIn("repository: %s\n" % init.REPOSITORY.split("github.com/", 1)[1], read_template("ratchet-checks.yml"))

    def test_the_workflow_template_reads_only_and_leaves_no_token(self):
        # Finding from a real adoption: every job's token only reads, and no checkout leaves the token in .git/config.
        text = read_template("ratchet-checks.yml")
        self.assertIn("\npermissions:\n  contents: read\n", text)
        jobs = "\n" + text.split("\njobs:\n", 1)[1]
        for job in init.JOBS:
            with self.subTest(job=job):
                block = jobs.split("\n  %s:\n" % job, 1)[1].split("\n  project-checks:\n", 1)[0]
                self.assertIn("\n    permissions:\n      contents: read\n    steps:\n", "\n" + block)
        checkouts = re.findall(r"uses: actions/checkout@[0-9a-f]{40} # v[0-9.]+\n(?: +#.*\n)*?((?: +\S.*\n)*?) +with:\n((?: {10}.*\n)+)",
                               text)
        self.assertEqual(len(checkouts), text.count("uses: actions/checkout@"))
        for _, options in checkouts:
            self.assertIn("persist-credentials: false\n", options)

    def test_the_rules_that_wait_for_a_remote_are_rules_of_the_starter_register(self):
        keys = [rule["key"] for rule in json.loads(read_template("register.json"))["adopted"]]
        for key in init.WAIT_FOR_REMOTE:
            with self.subTest(key=key):
                self.assertIn(key, keys)


class Sample(unittest.TestCase):
    """sample_problems on a repo of its own: a copy of this checkout, tagged v9.0 as the version the page fetches, and a
    head after the tag whose init.py prints "would draft" where the tag prints "would write". So a sample of the tag's
    lines passes only when the tag is what it is compared with, and a sample of the head's only when the head is.
    ratchet.json keeps this checkout's version, which the template's register must name for init.py to run: the
    release is that version with a date, and the page fetching it."""

    TAG_LINE, HEAD_LINE = "would write AGENTS.md", "would draft AGENTS.md"

    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="ratchet-test-")
        cls.origin = os.path.join(cls.base, "ratchet")
        shutil.copytree(ROOT, cls.origin, ignore=shutil.ignore_patterns(".git", "__pycache__", "fixtures", ".claude"))
        git(cls.origin, "init", "-q")
        with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as handle:
            cls.version = json.load(handle)["version"]
        cls.unreleased = dict(fetched="9.0", heading="## %s (unreleased)" % cls.version)
        cls.release = dict(fetched=cls.version, heading="## %s (2026-11-26)" % cls.version)
        cls.state(cls.origin, **cls.unreleased)
        git(cls.origin, "add", "-A")
        git(cls.origin, "commit", "-q", "-m", "Ratchet 9.0")
        git(cls.origin, "tag", "v9.0")
        path = os.path.join(cls.origin, "checks", "init.py")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        shown = '{"write": "would write"'
        assert text.count(shown) == 1, "init.py no longer holds %s once" % shown
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(shown, '{"write": "would draft"'))
        git(cls.origin, "commit", "-q", "-am", "The head after v9.0")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base)

    @staticmethod
    def state(root, fetched, heading, sample=None):
        """Make the page fetch vfetched and the first heading of CHANGELOG.md be heading, and, with sample, the sample on
        the page be the command and that one line."""
        def edit(name, pattern, replacement):
            path = os.path.join(root, *name.split("/"))
            with open(path, encoding="utf-8", newline="") as handle:
                text, count = re.subn(pattern, replacement, handle.read(), count=1, flags=re.M)
            assert count == 1, "%s holds no %s" % (name, pattern)
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
        edit("docs/index.html", r"(<pre><code>git clone --branch v)[0-9]+\.[0-9]+", r"\g<1>" + fetched)
        edit("CHANGELOG.md", r"^## .*$", heading)
        if sample is not None:
            edit("docs/index.html", r'<pre class="sample">[^<>]*</pre>',
                 '<pre class="sample">%s\n%s</pre>' % (SAMPLE_COMMAND, sample))

    def repo(self, sample, state=None):
        """A clone of the origin, with its tags, the state given committed at its head."""
        directory = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, directory)
        git(directory, "clone", "-q", self.origin, "ratchet")
        root = os.path.join(directory, "ratchet")
        self.state(root, sample=sample, **(state or self.unreleased))
        git(root, "commit", "-q", "-am", "The state of the case")
        return root

    def problems(self, root):
        return sample_problems(root, root)

    def test_a_sample_of_what_the_tag_prints_passes_while_the_head_prints_otherwise(self):
        self.assertEqual(self.problems(self.repo(self.TAG_LINE)), [])

    def test_a_sample_of_what_the_head_prints_fails_while_the_head_is_not_the_tag(self):
        problems = self.problems(self.repo(self.HEAD_LINE))
        self.assertEqual(problems, ["the sample on the page holds lines that init.py --check does not print in an empty "
                                    "repo at the tag v9.0, which the page's clone command fetches: ['%s']" % self.HEAD_LINE])

    def test_in_a_release_the_sample_is_what_the_head_prints(self):
        self.assertEqual(self.problems(self.repo(self.HEAD_LINE, self.release)), [])
        self.assertEqual(self.problems(self.repo(self.TAG_LINE, self.release)),
                         ["the sample on the page holds lines that init.py --check does not print in an empty repo at "
                          "the head, the release of %s, whose tag v%s does not exist yet: ['%s']"
                          % (self.version, self.version, self.TAG_LINE)])

    def test_a_release_entry_without_a_date_is_not_a_release_and_needs_the_tag(self):
        # The page fetches the version of ratchet.json while its entry is unreleased: there is no tag for it, and the
        # head is not taken.
        problems = self.problems(self.repo(self.HEAD_LINE, dict(self.unreleased, fetched=self.version)))
        self.assertEqual(len(problems), 1)
        self.assertIn("this checkout has no tag v%s" % self.version, problems[0])

    def test_a_missing_tag_fails_clearly_and_the_head_is_not_taken_in_its_place(self):
        for sample in (self.TAG_LINE, self.HEAD_LINE):
            with self.subTest(sample=sample):
                root = self.repo(sample)
                git(root, "tag", "-d", "v9.0")
                self.assertEqual(self.problems(root), [
                    "the page fetches v9.0 with its clone command, and this checkout has no tag v9.0, so the sample cannot "
                    "be compared with what that version prints. Fetch the tags, with git fetch --tags, or in CI with "
                    "fetch-depth: 0 in actions/checkout. The head is not compared in its place"])


if __name__ == "__main__":
    unittest.main()
