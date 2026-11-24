"""The job `base`: the base branch's checks judge a pull request (checks/from_base.py).

    python3 -m unittest discover -s checks -v

Each case makes a small git repo of its own in a scratch directory, a dry run of the job: a base commit with checks
of its own, a pull request's commit, and the merge commit that GitHub makes of the two, which the job checks out. Then
it runs from_base.py as the workflow does, with python3 -I, on that merge. The checks of the small repo stand in for
Ratchet's own under the same names: its generate.py fails when the value in data.json is above a limit, its
check_register.py and released_text.py pass, and its expected_tests.py runs its tests with unittest. So no case runs
this repo's suite, and the suite does not run itself. Standard library only.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import from_base

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "from_base.py")

# The base's rule: the value in data.json, or in the file it is given, is at most LIMIT.
GENERATE = '''import json, sys
LIMIT = 3
path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "data.json"
with open(path) as handle:
    value = json.load(handle)["value"]
if value > LIMIT:
    print("generate: %d is above %d" % (value, LIMIT))
    sys.exit(1)
print("generate: %d is at most %d" % (value, LIMIT))
'''
# The base's test of its rule: it fails on the fixture big.json and passes on small.json.
TEST = '''import os, subprocess, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
def run(name):
    return subprocess.call([sys.executable, "-B", os.path.join(HERE, "generate.py"), os.path.join(HERE, "fixtures", name)],
                           stdout=subprocess.DEVNULL)
class Rule(unittest.TestCase):
    def test_fails_on_a_value_above_the_limit(self):
        self.assertEqual(run("big.json"), 1)
    def test_passes_on_a_value_at_the_limit(self):
        self.assertEqual(run("small.json"), 0)
'''
# The base's runner of the suite.
RUNNER = '''import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.exit(subprocess.call([sys.executable, "-B", "-m", "unittest", "discover", "-q", "-s", HERE]))
'''
PASS = "import sys\nsys.exit(0)\n"
# The base's run of its suite on a released copy, a stand-in for test_released_text.py --released-copy: it runs the
# base's runner once more, with RELEASED set as a copy after the release steps would be. It holds no test of its own.
RELEASED = '''import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
if __name__ == "__main__" and sys.argv[1:] == ["--released-copy"]:
    sys.exit(subprocess.call([sys.executable, "-B", os.path.join(HERE, "expected_tests.py")], env=dict(os.environ, RELEASED="1")))
'''
WORKFLOW = "name: checks\non: [pull_request]\njobs: {}\n"
BASE = {
    ".github/workflows/checks.yml": WORKFLOW,
    "data.json": '{"value": 2}\n',
    "REGISTER.md": "# Register\n",
    "register.json": "{}\n",
    "checks/README.md": "The checks.\n",
    "checks/generate.py": GENERATE,
    "checks/check_register.py": PASS,
    "checks/released_text.py": PASS,
    "checks/expected_tests.py": RUNNER,
    "checks/test_generate.py": TEST,
    "checks/test_released_text.py": RELEASED,
    "checks/fixtures/big.json": '{"value": 5}\n',
    "checks/fixtures/small.json": '{"value": 3}\n',
}
OK = "from_base: the base branch's checks pass this pull request"
FAIL = "from_base: FAIL: the base branch's checks do not pass this pull request:"


def environment(home):
    """git with no configuration of the user's, and a fixed name for the commits."""
    env = dict(os.environ, HOME=home, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, LC_ALL="C",
               GIT_AUTHOR_NAME="Ratchet test", GIT_AUTHOR_EMAIL="test@example.invalid",
               GIT_COMMITTER_NAME="Ratchet test", GIT_COMMITTER_EMAIL="test@example.invalid", PYTHONDONTWRITEBYTECODE="1")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    return env


class DryRun(unittest.TestCase):
    """A base commit, a pull request's commit and their merge, judged by from_base.py as the workflow runs it."""

    def setUp(self):
        self.scratch = os.path.realpath(tempfile.mkdtemp(prefix="ratchet-test-"))
        self.addCleanup(shutil.rmtree, self.scratch)
        self.repo = os.path.join(self.scratch, "repo")
        self.env = environment(self.scratch)
        os.makedirs(self.repo)
        self.git("init", "-q", "-b", "main")
        self.git("config", "commit.gpgsign", "false")
        self.write(BASE)
        self.base = self.commit("the base")

    def git(self, *args):
        result = subprocess.run(["git", "-C", self.repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, env=self.env)
        self.assertEqual(result.returncode, 0, result.stdout)
        return result.stdout.strip()

    def write(self, files):
        for path, text in files.items():
            full = os.path.join(self.repo, *path.split("/"))
            if text is None:
                os.remove(full)
                continue
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def pull_request(self, files, base_moves=None):
        """The pull request's commit on a branch from the base, and HEAD at the merge that GitHub makes of it."""
        self.git("switch", "-q", "-c", "pr", self.base)
        self.write(files)
        head = self.commit("the pull request")
        self.git("switch", "-q", "main")
        if base_moves:
            self.write(base_moves)
            self.commit("the base moves on")
        self.git("merge", "-q", "--no-ff", "-m", "the merge", head)
        return head

    def own(self, *command):
        """A command of the pull request's own, run on the merge, as the job `own` runs it."""
        return subprocess.call([sys.executable, "-B"] + list(command), cwd=self.repo, env=self.env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def judge(self, head, base=None):
        result = subprocess.run([sys.executable, "-I", SCRIPT, "--base-sha", base or self.base, "--head-sha", head],
                                cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                                env=self.env)
        return result.returncode, result.stdout

    def assertPasses(self, head):
        status, output = self.judge(head)
        self.assertEqual(status, 0, output)
        self.assertIn(OK, output)
        return output

    def assertFails(self, head, *words):
        status, output = self.judge(head)
        self.assertEqual(status, 1, output)
        self.assertIn(FAIL, output)
        for each in words:
            self.assertIn(each, output)
        self.assertIn("merges it as an administrator", output)
        return output

    def test_a_change_of_data_within_the_rules_passes(self):
        head = self.pull_request({"data.json": '{"value": 3}\n'})
        output = self.assertPasses(head)
        self.assertIn("in the tree of the data: python3 checks/generate.py --check", output)
        self.assertIn("in the tree of the code: python3 checks/expected_tests.py", output)
        self.assertIn("in the tree of the code: python3 checks/test_released_text.py --released-copy", output)
        # The work trees are gone after the run.
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)

    def test_a_check_softened_with_the_data_it_judges_fails_in_the_tree_of_the_data(self):
        # The threat: the pull request raises the limit and the value together, by less than the base's fixtures would
        # catch. Its own checks and the base's tests pass it. The base's rule, reading the pull request's data, does not.
        head = self.pull_request({"checks/generate.py": GENERATE.replace("LIMIT = 3", "LIMIT = 4"), "data.json": '{"value": 4}\n'})
        self.assertEqual(self.own("checks/generate.py", "--check"), 0)
        self.assertEqual(self.own("checks/expected_tests.py"), 0)
        output = self.assertFails(head, "the base's `python3 checks/generate.py --check` failed in the tree of the data",
                                  "generate: 4 is above 3", "paths this pull request changes that the base judges by: checks/generate.py")
        self.assertNotIn("in the tree of the code, with exit status", output)

    def test_a_check_softened_with_its_test_fails_in_the_tree_of_the_code(self):
        # The pull request softens the check and drops the test that would catch it. The data does not change.
        test = TEST.replace('self.assertEqual(run("big.json"), 1)', 'pass')
        head = self.pull_request({"checks/generate.py": GENERATE.replace("LIMIT = 3", "LIMIT = 10"), "checks/test_generate.py": test})
        self.assertEqual(self.own("checks/expected_tests.py"), 0)
        output = self.assertFails(head, "the base's `python3 checks/expected_tests.py` failed in the tree of the code")
        self.assertIn("test_fails_on_a_value_above_the_limit", output)
        self.assertNotIn("in the tree of the data, with exit status", output)

    def test_a_check_that_fails_only_after_a_release_fails_in_the_tree_of_the_code(self):
        # Round 1 of #147: a fault in the pull request's code of the checks that shows only on a released copy. The base's
        # tests pass it in the tree as it is, and fail it in the base's run of the suite on a released copy of that tree.
        softened = GENERATE.replace("LIMIT = 3", "import os\nLIMIT = 9 if os.environ.get('RELEASED') else 3")
        head = self.pull_request({"checks/generate.py": softened})
        self.assertEqual(self.own("checks/expected_tests.py"), 0)
        output = self.assertFails(head, "the base's `python3 checks/test_released_text.py --released-copy` failed in the tree of the code",
                                  "the base judges by: checks/generate.py")
        self.assertIn("test_fails_on_a_value_above_the_limit", output)
        self.assertNotIn("the base's `python3 checks/expected_tests.py` failed", output)

    def test_a_check_softened_with_its_runner_fails_in_the_tree_of_the_code(self):
        # The pull request softens the check and makes its runner pass whatever happens. The base's runner runs.
        head = self.pull_request({"checks/generate.py": GENERATE.replace("LIMIT = 3", "LIMIT = 10"), "checks/expected_tests.py": PASS})
        self.assertEqual(self.own("checks/expected_tests.py"), 0)
        self.assertFails(head, "the base's `python3 checks/expected_tests.py` failed in the tree of the code")

    def test_a_check_removed_fails_in_the_tree_of_the_code(self):
        head = self.pull_request({"checks/generate.py": None, "checks/test_generate.py": None})
        self.assertFails(head, "failed in the tree of the code", "checks/generate.py, checks/test_generate.py")

    def test_a_module_added_beside_the_checks_is_empty_in_the_tree_of_the_data(self):
        # A json.py beside the checks would be imported by the base's generate.py in place of the standard library's. In
        # the tree of the data it is there, empty, so the base's script fails on it and never passes on what it says.
        shadow = "def load(handle):\n    return {'value': 0}\n"
        head = self.pull_request({"checks/json.py": shadow, "data.json": '{"value": 9}\n'})
        self.assertEqual(self.own("checks/generate.py", "--check"), 0)
        output = self.assertFails(head, "the base's `python3 checks/generate.py --check` failed in the tree of the data",
                                  "the base judges by: checks/json.py")
        self.assertIn("AttributeError", output)
        self.assertNotIn("is at most", output)

    def test_a_new_check_that_the_data_links_to_is_there_in_the_tree_of_the_data(self):
        # The base's generate.py fails on a link in the data that leads nowhere. A new check, linked from the data, is there.
        linking = GENERATE.replace("LIMIT = 3", "LIMIT = 3\nimport os\nif not os.path.exists(open('checks/README.md').read().strip()):\n"
                                   "    sys.exit('the link leads nowhere')")
        self.write({"checks/generate.py": linking, "checks/README.md": "checks/generate.py\n"})
        self.base = self.commit("the base checks its link")
        head = self.pull_request({"checks/new.py": "print('new')\n", "checks/README.md": "checks/new.py\n"})
        self.assertPasses(head)

    def test_a_script_the_base_lacks_fails_even_when_the_pull_request_adds_it(self):
        # Without the check, the pull request's released_text.py would run, or the empty file in its place, and pass.
        self.write({"checks/released_text.py": None})
        self.base = self.commit("the base without released_text.py")
        head = self.pull_request({"checks/released_text.py": PASS})
        output = self.assertFails(head, "the base has no checks/released_text.py, so its `python3 checks/released_text.py` "
                                  "cannot judge the tree of the data", "the base judges by: checks/released_text.py")
        self.assertNotIn("in the tree of the data: python3 checks/released_text.py", output)

    def test_a_tightened_check_passes(self):
        tighter = GENERATE.replace("if value > LIMIT:", "if not isinstance(value, int) or value > LIMIT:")
        head = self.pull_request({"checks/generate.py": tighter, "data.json": '{"value": 1}\n'})
        self.assertPasses(head)

    def test_a_new_test_and_a_new_fixture_pass(self):
        head = self.pull_request({"checks/test_more.py": "import unittest\nclass More(unittest.TestCase):\n    def test_more(self):\n        pass\n",
                                  "checks/fixtures/more.json": '{"value": 1}\n'})
        self.assertPasses(head)

    def test_a_change_of_form_fails_closed_and_says_why(self):
        # The field is renamed in the data, the check and its fixtures together. The base cannot read the new form.
        renamed = GENERATE.replace('["value"]', '["amount"]')
        head = self.pull_request({"checks/generate.py": renamed, "data.json": '{"amount": 2}\n',
                                  "checks/fixtures/big.json": '{"amount": 5}\n', "checks/fixtures/small.json": '{"amount": 3}\n'})
        self.assertEqual(self.own("checks/generate.py", "--check"), 0)
        self.assertEqual(self.own("checks/expected_tests.py"), 0)
        output = self.assertFails(head, "failed in the tree of the data", "failed in the tree of the code",
                                  "the base judges by: checks/generate.py")
        self.assertIn("the form of a data file on purpose is one the base branch cannot judge", output)

    def test_a_change_to_the_workflow_fails_and_names_it(self):
        head = self.pull_request({".github/workflows/checks.yml": WORKFLOW + "# skip the base\n"})
        self.assertFails(head, "changes .github/workflows/checks.yml, the job that runs these checks",
                         "the base judges by: .github/workflows/checks.yml")

    def test_a_change_to_the_runner_fails_and_names_it(self):
        # A softened runner is never judged by the base, which runs its own, and would be the base's runner once merged.
        head = self.pull_request({"checks/expected_tests.py": RUNNER + "# skip nothing\n"})
        self.assertFails(head, "changes checks/expected_tests.py, the runner of the suite",
                         "the base judges by: checks/expected_tests.py")

    def test_a_base_that_moved_on_is_judged_by_its_newest_commit(self):
        # The base gains a stricter limit after the pull request branched. The merge is judged by the newer base.
        head = self.pull_request({"data.json": '{"value": 3}\n'}, base_moves={"checks/generate.py": GENERATE.replace("LIMIT = 3", "LIMIT = 2"),
                                                                           "checks/fixtures/small.json": '{"value": 2}\n'})
        self.assertFails(head, "generate: 3 is above 2")

    def test_a_checkout_that_is_not_the_merge_of_the_pull_request_fails(self):
        head = self.pull_request({"data.json": '{"value": 1}\n'})
        other = self.git("rev-parse", "HEAD^1")
        status, output = self.judge(other)
        self.assertEqual(status, 1, output)
        self.assertIn("the second parent of HEAD is %s, not the pull request's head %s" % (head, other), output)
        status, output = self.judge(head, base=head)
        self.assertEqual(status, 1, output)
        self.assertIn("is not the base %s or a later commit of it" % head, output)
        status, output = self.judge("HEAD")
        self.assertEqual(status, 1, output)
        self.assertIn("--head-sha must be a full commit id", output)
        self.git("switch", "-q", "--detach", head)
        status, output = self.judge(head)
        self.assertEqual(status, 1, output)
        self.assertIn("HEAD is not the merge commit of a pull request: it has 1 parent(s), not 2", output)


class Paths(unittest.TestCase):
    def test_what_is_code_of_the_checks(self):
        for path in ("checks/generate.py", "checks/test_checks.py", "checks/json.py", "checks/tool/__init__.py", "checks/tool/data.txt"):
            self.assertTrue(from_base.is_code(path), path)
        for path in ("checks/README.md", "checks/fixtures/register/register.json", "checks/fixtures/tests-ran/tree/test_a.py",
                     "register.json", "checks.py", "templates/checks/x.py", ".github/workflows/checks.yml"):
            self.assertFalse(from_base.is_code(path), path)
        self.assertTrue(from_base.is_test("checks/test_checks.py"))
        self.assertFalse(from_base.is_test("checks/tool/test_x.py"))
        self.assertTrue(from_base.judged_by(".github/workflows/checks.yml"))

    def test_the_commands_are_the_ones_the_jobs_own_and_released_run(self):
        with open(os.path.join(os.path.dirname(HERE), ".github", "workflows", "checks.yml"), encoding="utf-8") as handle:
            workflow = handle.read()
        for command in from_base.DATA_COMMANDS + from_base.CODE_COMMANDS:
            self.assertIn("run: python3 %s\n" % " ".join(command), workflow)

    def test_the_suite_on_a_released_copy_runs_in_the_tree_of_the_code_after_the_suite(self):
        # Round 1 of #147: the base's tests judge the pull request's checks after a release too, as ReleaseSteps did.
        released = ("checks/test_released_text.py", "--released-copy")
        self.assertEqual(from_base.CODE_COMMANDS, (("checks/expected_tests.py",), released))
        self.assertNotIn(released, from_base.DATA_COMMANDS)


if __name__ == "__main__":
    unittest.main()
