"""The guard on released text, checks/released_text.py, and the steps of a release.

    python3 -m unittest discover -s checks -v

Each case makes a git repo of its own in a scratch directory, with its own tags, so no
case needs the tags of this repo and none is skipped where they are missing. The
guard runs on this repo's own tags in a step of its own in CI. Standard library only.
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

import release
import test_checks
import test_release

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GUARD = "released_text.py"
OK = "released_text: released text matches its tags"
# A changelog of three released versions and one that is not yet released, newest first.
ENTRIES = {
    "0.1": "## 0.1 (2026-01-01)\n\n- The first rules.\n",
    "0.2": "## 0.2 (2026-02-01)\n\nAdded:\n\n- The icon.\n\n",
    "0.3": "## 0.3 (2026-03-01)\n\n<!-- generated:count -->\nThree rules.\n<!-- /generated -->\n\n",
    "0.4": "## 0.4 (2026-04-01)\n\n<!-- generated:count -->\nFour rules.\n<!-- /generated -->\n\n",
}
TITLE = "# Changelog\n\n"
# A ratchet.json that registry.validate accepts: the guard reads it as strictly as every other check does.
RATCHET = '{\n  "version": "%s",\n  "experimental_cap": 0,\n  "start": [],\n  "principles": [],\n  "parts": [],\n  "rules": []\n}\n'
EMPTY = '"principles": [],\n  "parts": [],\n  "rules": []'
# One rule, with the principle and the part it is in, in place of the empty lists.
A_RULE = ('"principles": [{"key": "principle.new", "title": "New", "text": "A new principle."}],\n  '
          '"parts": [{"id": "core", "file": "RATCHET.md", "title": "The core"}],\n  "rules": [{"key": "ratchet.new", '
          '"part": "core", "principle": "principle.new", "status": "core", "enforcement": "text-only", "rule": "A new rule.", '
          '"ratchet": "Text only, as a test.", "source": ""}]')


def changelog(*versions):
    return TITLE + "".join(ENTRIES[version] for version in versions)


# No automatic gc or maintenance in a repository a test makes. git starts them in the background after a commit or a
# fetch, and one still writing in .git is a likely, not a proven, cause of an intermittent "could not parse HEAD" and
# of a removal that finds .git/objects/pack not empty. For this call, and, for init and clone, in the new repository's
# own config, so that a script under test that runs git there starts none either.
QUIET = (("gc.auto", "0"), ("maintenance.auto", "false"))


def git_environment(home):
    """git with no configuration but its own, so that a person's settings, such as signing, change nothing."""
    environment = dict(os.environ, HOME=home, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, LC_ALL="C",
                       GIT_CONFIG_COUNT=str(len(QUIET)))
    for number, (name, value) in enumerate(QUIET):
        environment["GIT_CONFIG_KEY_%d" % number], environment["GIT_CONFIG_VALUE_%d" % number] = name, value
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        environment.pop(name, None)
    return environment


def git(root, *args):
    result = subprocess.run(
        ["git", "-c", "user.name=Ratchet test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
         "-c", "tag.gpgsign=false", "-c", "init.defaultBranch=main"] + list(args),
        cwd=root, env=git_environment(root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
    )
    if result.returncode != 0:
        raise AssertionError("git %s: %s" % (" ".join(args), result.stdout))
    if args[:1] == ("init",):
        for name, value in QUIET:
            git(root, "config", name, value)
    return result.stdout


# How long one script may run before the test fails it as hung. A script on its own takes seconds. The run of the whole
# suite in released_copy_case takes as long as the suite, which grows with every check and fixture: it took more than 600
# seconds on a loaded machine in November 2026. The limit for that run guards against a hang, not against a slow suite,
# so it is well above the suite's time. In CI the job's own timeout-minutes in .github/workflows/checks.yml ends it sooner.
SCRIPT_TIMEOUT = 600
SUITE_TIMEOUT = 3600


def run(script, *args, root=ROOT, cwd=None, timeout=SCRIPT_TIMEOUT):
    result = subprocess.run(
        [sys.executable, os.path.join(root, "checks", script)] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, cwd=cwd, timeout=timeout,
        env=git_environment(cwd or root),
    )
    return result.returncode, result.stdout


def write(root, name, text):
    path = os.path.join(root, *name.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def commit_and_tag(root, tag):
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", "Release " + tag)
    git(root, "tag", tag)


class Guard(unittest.TestCase):
    """The guard on a repo with the tags v0.1, v0.2 and v0.3, and 0.4 not yet released."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, self.root)
        git(self.root, "init", "-q")
        # As in this repo, the first tag holds no changelog: 0.1 is first written down in 0.2.
        write(self.root, "README.md", "Ratchet.\n")
        commit_and_tag(self.root, "v0.1")
        write(self.root, "CHANGELOG.md", changelog("0.2", "0.1"))
        commit_and_tag(self.root, "v0.2")
        write(self.root, "CHANGELOG.md", changelog("0.3", "0.2", "0.1"))
        write(self.root, "ratchet.json", RATCHET % "0.3")
        commit_and_tag(self.root, "v0.3")
        write(self.root, "CHANGELOG.md", changelog("0.4", "0.3", "0.2", "0.1"))
        write(self.root, "ratchet.json", RATCHET % "0.4")

    def guard(self):
        result = subprocess.run(
            [sys.executable, os.path.join(HERE, GUARD), "--root", self.root],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=git_environment(self.root),
        )
        return result.returncode, result.stdout

    def edit(self, old, new):
        with open(os.path.join(self.root, "CHANGELOG.md"), encoding="utf-8", newline="") as handle:
            text = handle.read()
        self.assertIn(old, text)
        write(self.root, "CHANGELOG.md", text.replace(old, new, 1))

    def assert_fails(self, *problems):
        code, output = self.guard()
        self.assertEqual(code, 1, output)
        self.assertNotIn(OK, output)
        self.assertNotIn("Traceback", output)
        listed = [line[2:] for line in output.splitlines() if line.startswith("- ")]
        for problem in problems:
            self.assertTrue(any(problem in line for line in listed), "%r is not listed in:\n%s" % (problem, output))

    def test_released_text_as_it_stood_at_its_tags_passes(self):
        code, output = self.guard()
        self.assertEqual(code, 0, output)
        self.assertIn(OK + ": 5 entries in 3 tags, each as it stood there. Every tag has an entry.", output)

    def test_the_version_not_yet_released_may_change(self):
        self.edit("Four rules.", "Five rules.")
        code, output = self.guard()
        self.assertEqual(code, 0, output)

    def test_an_unreleased_first_entry_passes_and_ratchet_json_may_change_under_it(self):
        # D-2026-11-19-batched-releases: changes are collected under the first entry until a PR gives it a date.
        self.edit("## 0.4 (2026-04-01)", "## 0.4 (unreleased)")
        code, output = self.guard()
        self.assertEqual(code, 0, output)
        self.assertIn("ratchet.json names 0.4, which has no tag yet. The first entry, 0.4, is unreleased.", output)
        write(self.root, "ratchet.json", RATCHET.replace(EMPTY, A_RULE) % "0.4")
        self.edit("Four rules.", "Four rules, and one more.")
        code, output = self.guard()
        self.assertEqual(code, 0, output)

    def test_the_release_is_the_entry_given_a_date(self):
        self.edit("## 0.4 (2026-04-01)", "## 0.4 (unreleased)")
        self.assertEqual(self.guard()[0], 0)
        self.edit("## 0.4 (unreleased)", "## 0.4 (2026-04-02)")
        code, output = self.guard()
        self.assertEqual(code, 0, output)
        self.assertNotIn("unreleased", output)
        commit_and_tag(self.root, "v0.4")
        code, output = self.guard()
        self.assertEqual(code, 0, output)
        self.assertIn("ratchet.json is as it stood at the tag v0.4.", output)
        # From its tag on, the entry and ratchet.json are frozen as before.
        self.edit("## 0.4 (2026-04-02)", "## 0.4 (unreleased)")
        self.assert_fails('CHANGELOG.md: the entry ## 0.4 (unreleased) is headed "(unreleased)", and the tag v0.4 exists. '
                          "A released version stays released",
                          "CHANGELOG.md: the entry ## 0.4 (unreleased) is not as it stood at the tag v0.4")

    def test_an_unreleased_entry_that_is_not_first_fails(self):
        self.edit("## 0.4 (2026-04-01)", "## 0.5 (2026-05-01)\n\n- Five.\n\n## 0.4 (unreleased)")
        self.assert_fails('CHANGELOG.md: the entry ## 0.4 (unreleased) is headed "(unreleased)", and only the first entry may be. '
                          "An entry is released from the moment it has a date")

    def test_two_unreleased_entries_fail(self):
        self.edit("## 0.4 (2026-04-01)", "## 0.5 (unreleased)\n\n- Five.\n\n## 0.4 (unreleased)")
        self.assert_fails('CHANGELOG.md: the entry ## 0.4 (unreleased) is headed "(unreleased)", and only the first entry may be')

    def test_an_unreleased_heading_for_a_released_version_fails(self):
        write(self.root, "CHANGELOG.md", changelog("0.3", "0.2", "0.1").replace("## 0.3 (2026-03-01)", "## 0.3 (unreleased)"))
        write(self.root, "ratchet.json", RATCHET % "0.3")
        self.assert_fails('CHANGELOG.md: the entry ## 0.3 (unreleased) is headed "(unreleased)", and the tag v0.3 exists')

    def test_an_unreleased_heading_of_another_form_fails(self):
        for heading in ("## 0.4 (Unreleased)", "## 0.4 (unreleased) ", "## 0.4 unreleased", "## 0.4(unreleased)",
                        "## 0.4 (unreleased", "## 0.4 (unreleased)\u00a0", "## Unreleased (unreleased)"):
            with self.subTest(heading=heading):
                write(self.root, "CHANGELOG.md", changelog("0.4", "0.3", "0.2", "0.1").replace("## 0.4 (2026-04-01)", heading))
                self.assert_fails("CHANGELOG.md: %r is not the heading of an entry" % heading)

    def test_ratchet_json_with_the_fields_that_moved_out_fails(self):
        # D-2026-11-19-batched-releases, choice 3: the sources are in sources.json, and the date is in the changelog.
        valid = RATCHET % "0.4"
        for field, value in (("sources", "[]"), ("date", '"2026-01-01"')):
            with self.subTest(field=field):
                write(self.root, "ratchet.json", valid.replace('"start"', '"%s": %s,\n  "start"' % (field, value)))
                self.assert_fails("ratchet.json: unknown field %r" % field)

    def test_a_word_changed_in_a_released_entry_fails(self):
        self.edit("- The icon.", "- The icons.")
        self.assert_fails("CHANGELOG.md: the entry ## 0.2 (2026-02-01) is not as it stood at the tag v0.2",
                          "CHANGELOG.md: the entry ## 0.2 (2026-02-01) is not as it stood at the tag v0.3")

    def test_the_count_of_a_released_entry_regenerated_fails(self):
        # What the generator did to the entry of 0.3 before only the first entry was generated.
        self.edit("Three rules.", "Four rules.")
        self.assert_fails("CHANGELOG.md: the entry ## 0.3 (2026-03-01) is not as it stood at the tag v0.3")

    def test_a_line_added_to_the_end_of_the_last_entry_fails(self):
        with open(os.path.join(self.root, "CHANGELOG.md"), "a", encoding="utf-8") as handle:
            handle.write("- Also this.\n")
        self.assert_fails("CHANGELOG.md: the entry ## 0.1 (2026-01-01) is not as it stood at the tag v0.2")

    def test_a_released_entry_removed_fails(self):
        self.edit(ENTRIES["0.2"], "")
        self.assert_fails("CHANGELOG.md has no entry ## 0.2 (2026-02-01), which the tag v0.2 holds",
                          "the tag v0.2 has no entry in CHANGELOG.md")

    def test_the_date_of_a_released_entry_changed_fails(self):
        self.edit("## 0.3 (2026-03-01)", "## 0.3 (2026-03-02)")
        self.assert_fails("CHANGELOG.md: the entry ## 0.3 (2026-03-02) is not as it stood at the tag v0.3")

    def test_a_tag_without_a_changelog_still_needs_an_entry(self):
        self.edit(ENTRIES["0.1"], "")
        self.assert_fails("the tag v0.1 has no entry in CHANGELOG.md")

    def test_an_entry_after_the_first_without_a_tag_fails(self):
        self.edit("## 0.3 (2026-03-01)", "## 0.35 (2026-03-15)\n\n- Never released.\n\n## 0.3 (2026-03-01)")
        self.assert_fails("CHANGELOG.md: the entry ## 0.35 (2026-03-15) has no tag v0.35. Only the first entry may be a version that is not yet released")

    def test_a_heading_of_another_form_fails(self):
        for heading in ("## Unreleased", "## 0.4", "## 0.4 (soon)", "## 0.4  (2026-04-01)", "##  0.4 (2026-04-01)", "## v0.4 (2026-04-01)"):
            with self.subTest(heading=heading):
                write(self.root, "CHANGELOG.md", changelog("0.4", "0.3", "0.2", "0.1").replace("## 0.4 (2026-04-01)", heading))
                self.assert_fails("CHANGELOG.md: %r is not the heading of an entry" % heading)

    def test_an_entry_twice_fails(self):
        write(self.root, "CHANGELOG.md", changelog("0.4", "0.3", "0.3", "0.2", "0.1"))
        self.assert_fails("CHANGELOG.md: the entry of 0.3 stands 2 times")

    def test_a_changelog_that_is_not_utf8_fails(self):
        with open(os.path.join(self.root, "CHANGELOG.md"), "wb") as handle:
            handle.write(changelog("0.4", "0.3", "0.2", "0.1").encode("utf-8").replace(b"Four", b"F\xffour"))
        self.assert_fails("CHANGELOG.md: is not valid UTF-8")

    def test_a_missing_changelog_fails(self):
        os.remove(os.path.join(self.root, "CHANGELOG.md"))
        self.assert_fails("CHANGELOG.md: the file is missing")

    def test_the_released_version_as_it_stood_at_its_tag_passes(self):
        git(self.root, "checkout", "-q", "--", ".")
        code, output = self.guard()
        self.assertEqual(code, 0, output)
        self.assertIn("ratchet.json is as it stood at the tag v0.3.", output)

    def test_the_rules_of_a_released_version_changed_fails(self):
        write(self.root, "CHANGELOG.md", changelog("0.3", "0.2", "0.1"))
        write(self.root, "ratchet.json", RATCHET.replace(EMPTY, A_RULE) % "0.3")
        with open(os.path.join(self.root, "ratchet.json"), encoding="utf-8") as handle:
            self.assertIn("ratchet.new", handle.read())
        self.assert_fails("ratchet.json: names 0.3, which is released, and is not as it stood at the tag v0.3. A change to the rules raises the version")

    def test_a_released_version_whose_tag_holds_no_ratchet_json_fails(self):
        write(self.root, "CHANGELOG.md", changelog("0.2", "0.1"))
        write(self.root, "ratchet.json", RATCHET % "0.2")
        self.assert_fails("ratchet.json: names 0.2, which is released, and the tag v0.2 holds no ratchet.json")

    def test_a_ratchet_json_that_cannot_be_read_fails(self):
        for text, problem in (("{", "ratchet.json: not a valid data file"), (RATCHET.replace('"%s"', "4"), "ratchet.json: version must look like 0.2")):
            with self.subTest(text=text):
                write(self.root, "ratchet.json", text)
                self.assert_fails(problem)

    def test_a_ratchet_json_that_is_not_strict_fails(self):
        # Finding 4 of review round 1 of the new approach: plain json.loads took a field twice, an unknown field and NaN.
        valid = RATCHET % "0.4"
        cases = {
            # The parser meets NaN before it closes the object, so NaN is the problem it names.
            "the probe of the review": ('{"version":"0.3","version":"0.4","unknown":true,"rules":NaN}\n',
                                        "ratchet.json: not a valid data file: NaN is not allowed"),
            "the probe of the review, without NaN": ('{"version":"0.3","version":"0.4","unknown":true,"rules":[]}\n',
                                                     "ratchet.json: not a valid data file: the field 'version' appears twice in one object"),
            "a field twice": (valid.replace('"start"', '"version": "0.4",\n  "start"'),
                              "ratchet.json: not a valid data file: the field 'version' appears twice in one object"),
            "an unknown field": (valid.replace('"start"', '"unknown": true,\n  "start"'), "ratchet.json: unknown field 'unknown'"),
            "a missing field": (valid.replace('  "start": [],\n', ""), "ratchet.json: missing field 'start'"),
            "NaN": (valid.replace('"rules": []', '"rules": NaN'), "ratchet.json: not a valid data file: NaN is not allowed"),
            "Infinity": (valid.replace('"rules": []', '"rules": Infinity'), "ratchet.json: not a valid data file: Infinity is not allowed"),
            "nested too deeply": (valid.replace('"rules": []', '"rules": ' + "[" * 100000 + "]" * 100000),
                                  "ratchet.json: not a valid data file: it is nested too deeply"),
            "a list at the top": ("[]\n", "ratchet.json: the top level must be an object"),
        }
        for case, (text, problem) in cases.items():
            with self.subTest(case=case):
                write(self.root, "ratchet.json", text)
                self.assert_fails(problem)

    def test_a_ratchet_json_that_is_not_utf8_fails(self):
        with open(os.path.join(self.root, "ratchet.json"), "wb") as handle:
            handle.write((RATCHET % "0.4").encode("utf-8").replace(b"0.4", b"0.\xff4", 1))
        self.assert_fails("ratchet.json: is not valid UTF-8")

    def test_a_tag_of_another_form_fails(self):
        for tag in ("v0.4-rc1", "latest", "0.3", "v0.3.1"):
            with self.subTest(tag=tag):
                git(self.root, "tag", tag, "v0.3")
                self.assert_fails("the tag %r is not of the form vMAJOR.MINOR, so the check does not know what it releases" % tag)
                git(self.root, "tag", "-d", tag)

    def test_an_annotated_tag_is_read_like_any_other(self):
        git(self.root, "tag", "-d", "v0.3")
        git(self.root, "tag", "-a", "-m", "Ratchet 0.3", "v0.3", "HEAD")
        code, output = self.guard()
        self.assertEqual(code, 0, output)

    def test_a_checkout_without_tags_fails(self):
        for tag in ("v0.1", "v0.2", "v0.3"):
            git(self.root, "tag", "-d", tag)
        self.assert_fails("there are no tags, so nothing released can be compared. Fetch them: in CI the checkout needs fetch-depth: 0")

    def test_a_directory_that_is_not_a_git_checkout_fails(self):
        shutil.rmtree(os.path.join(self.root, ".git"))
        self.assert_fails("cannot list the tags")


class ReleaseSteps(unittest.TestCase):
    """The version that ratchet.json names, unreleased, on a copy of this repo, its release, and the state after it.

    D-2026-11-19-batched-releases. Whichever state the repo is in, each test first heads the first entry of the
    changelog "(unreleased)", or gives it a date, as test_checks.first_entry does. While it is unreleased, a merge
    publishes nothing. The release is a pull request that gives the entry its date and moves the command in the README that
    fetches Ratchet to the new tag; checks/generate.py writes the rest. Every step is release.py's own code, never a
    copy of it. The copy gets tags that hold the changelog of each released version as it stands in the copy, which
    the guard in CI shows to be the changelog at the real tags, and a ratchet.json as main had it: none at v0.1 and
    v0.2, and one from v0.3 on.
    """

    DATE = "2026-11-26"

    def setUp(self):
        self.copy = os.path.join(tempfile.mkdtemp(prefix="ratchet-test-"), "ratchet")
        self.addCleanup(shutil.rmtree, os.path.dirname(self.copy))
        shutil.copytree(ROOT, self.copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        with open(os.path.join(self.copy, "ratchet.json"), encoding="utf-8") as handle:
            self.version = json.load(handle)["version"]
        self.changelog = self.read("CHANGELOG.md")

    def read(self, name):
        with open(os.path.join(self.copy, name), encoding="utf-8", newline="") as handle:
            return handle.read()

    def entries(self):
        """[(version, text of the entry)], newest first."""
        starts = [match.start() for match in re.finditer(r"^## ", self.changelog, re.M)]
        texts = [self.changelog[a:b] for a, b in zip(starts, starts[1:] + [len(self.changelog)])]
        return [(text.split(" ", 2)[1], text) for text in texts]

    def tag_the_releases_before(self):
        """Tags for every version before the one not yet released, oldest first, each with the changelog up to its own entry.

        ratchet.json is first on main in 0.3, as in this repo, so the history that release.py reads names 0.3 and every later version.
        """
        git(self.copy, "init", "-q")
        entries = self.entries()
        self.assertEqual(entries[0][0], self.version)
        title = self.changelog[:self.changelog.index("## ")]
        data = self.read("ratchet.json")
        named = '"version": "%s",' % self.version
        self.assertEqual(data.count(named), 1)
        released = entries[1:]
        for number in range(len(released) - 1, -1, -1):
            version = released[number][0]
            if number == len(released) - 1:
                # The tag v0.1 of this repo holds no changelog: 0.1 is first written down in 0.2.
                os.remove(os.path.join(self.copy, "CHANGELOG.md"))
            else:
                write(self.copy, "CHANGELOG.md", title + "".join(text for _, text in released[number:]))
            if version in ("0.1", "0.2"):
                if os.path.exists(os.path.join(self.copy, "ratchet.json")):
                    os.remove(os.path.join(self.copy, "ratchet.json"))
            else:
                write(self.copy, "ratchet.json", data.replace(named, '"version": "%s",' % version))
            commit_and_tag(self.copy, "v" + version)
        write(self.copy, "CHANGELOG.md", self.changelog)
        write(self.copy, "ratchet.json", data)

    def github(self):
        """GitHub as it stands before this version: a tag for each older version, and a published release for each but 0.1."""
        tags = dict((version, ("commit", git(self.copy, "rev-parse", "v%s^{commit}" % version).strip()))
                    for version, _ in self.entries()[1:])
        releases = [{"tag_name": "v" + version, "draft": False} for version in tags if version not in release.BEFORE_RELEASES]
        return test_release.FakeGitHub(tags=tags, releases=releases)

    def merge(self, message):
        git(self.copy, "add", "-A")
        git(self.copy, "commit", "-q", "--allow-empty", "-m", message)
        return git(self.copy, "rev-parse", "HEAD").strip()

    def publish(self, github, sha, **report):
        """release.py's publish, on the history of main in the copy, read with git as the release workflow reads it."""
        out = io.StringIO()
        history = release.main_history(self.copy, sha)
        release.publish(self.version, self.read("CHANGELOG.md"), history, test_release.REPO, sha, github, out,
                        pending=release.read_pending(self.copy, history), **report)
        return out.getvalue()

    def checks_pass(self):
        """The checks that the job checks runs, and that the release workflow runs before it tags."""
        for script, args in (("generate.py", ["--check"]), ("check_register.py", ["register.json", "--markdown", "REGISTER.md"]), (GUARD, [])):
            with self.subTest(step=script):
                code, output = run(script, *args, root=self.copy, cwd=self.copy)
                self.assertEqual(code, 0, output)

    def hold(self, date=None):
        """Head the first entry "(unreleased)", or with date, as test_checks.first_entry does, and read the changelog again."""
        version, fetched = test_checks.first_entry(self.copy, date)
        self.assertEqual(version, self.version)
        self.changelog = self.read("CHANGELOG.md")
        return fetched

    def test_the_entry_of_0_9_says_what_changes(self):
        entry = dict(self.entries())["0.9"]
        for words in ("Ratchet 0.9, computed from `ratchet.json`", "Outside the core there are 23 experimental rules, under a cap of 25",
                      "No rule is added, changed or removed in this version.", "Changes of form:", "`date` is gone", "`sources` is gone",
                      "`sources.json`", "D-2026-11-19-batched-releases"):
            self.assertIn(words, entry)

    def test_an_unreleased_entry_publishes_nothing_and_the_entry_given_its_date_releases_it(self):
        fetched = self.hold()
        self.assertTrue(self.changelog.startswith("# Changelog\n\n## %s (unreleased)\n" % self.version))
        self.assertIn("Ratchet %s, computed from `ratchet.json`" % self.version, self.entries()[0][1])
        # RATCHET.md says the version is not yet released, and the README fetches the latest release.
        self.assertIn("Version %s, not yet released." % self.version, self.read("RATCHET.md"))
        self.assertEqual(fetched, self.entries()[1][0])
        self.assertIn("git clone --branch v%s https://github.com/fabian-von-tiedemann/ratchet .ratchet" % fetched, self.read("README.md"))
        self.tag_the_releases_before()
        self.checks_pass()
        # A merge while the entry is unreleased: the release workflow writes nothing, on a push and on its schedule.
        sha = self.merge("Merge a change to %s" % self.version)
        github = self.github()
        said = ('Ratchet %s is not released: its entry in CHANGELOG.md is headed "(unreleased)". Every older version is finished. '
                "Nothing was written.\n" % self.version)
        self.assertEqual(self.publish(github, sha), said)
        self.assertEqual(self.publish(github, sha, report=True), said)
        self.assertEqual(github.writes, [])
        # The release: the entry gets its date and the README fetches its tag. Then the checks pass, and the merge is
        # tagged and released.
        self.assertEqual(self.hold(self.DATE), self.version)
        self.assertIn("Version %s, %s." % (self.version, self.DATE), self.read("RATCHET.md"))
        self.checks_pass()
        sha = self.merge("Release %s" % self.version)
        self.assertEqual(self.publish(github, sha), "Tagged v%s at %s and released Ratchet %s.\n" % (self.version, sha, self.version))
        path = "/repos/%s" % test_release.REPO
        self.assertEqual(github.writes, [("POST", path + "/git/refs"), ("POST", path + "/releases")])
        self.assertEqual(github.releases[-1]["body"], release.release_text(self.version, test_release.REPO))
        git(self.copy, "tag", "v" + self.version)
        # The next scheduled run of the release workflow finds every version finished, and writes nothing.
        writes = list(github.writes)
        self.assertEqual(self.publish(github, sha, report=True), "v%s is tagged at this commit and released. Nothing to do.\n" % self.version)
        self.assertEqual(github.writes, writes)
        code, output = run(GUARD, root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("in %d tags" % len(self.entries()), output)
        # That the full suite passes in the copy after it is the case of released_copy_case, which the job released of
        # .github/workflows/checks.yml runs once, out of this suite (D-2026-11-24-faster-suite).

    def test_while_unreleased_a_rule_may_change_and_after_its_release_only_with_a_new_version(self):
        self.hold()
        self.tag_the_releases_before()
        rule = "Only the owner approves decisions."

        def change_the_rule(old, new):
            for name in ("ratchet.json", "register.json"):
                text = self.read(name)
                self.assertIn(old, text)
                write(self.copy, name, text.replace(old, new))
            code, output = run("generate.py", root=self.copy, cwd=self.copy)
            self.assertEqual(code, 0, output)

        change_the_rule(rule, "Only the owner approves every decision.")
        self.checks_pass()
        self.hold(self.DATE)
        self.merge("Release %s" % self.version)
        git(self.copy, "tag", "v" + self.version)
        self.checks_pass()
        change_the_rule("Only the owner approves every decision.", rule)
        code, output = run("generate.py", "--check", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        code, output = run(GUARD, root=self.copy, cwd=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("ratchet.json: names %s, which is released, and is not as it stood at the tag v%s. A change to the rules raises "
                      "the version" % (self.version, self.version), output)

    def test_after_the_release_a_pin_moves_in_sources_json_with_no_new_version(self):
        # D-2026-11-19-batched-releases, choice 3: the list of sources is not part of what is released.
        self.hold(self.DATE)
        self.tag_the_releases_before()
        self.merge("Release %s" % self.version)
        git(self.copy, "tag", "v" + self.version)
        before = dict((name, self.read(name)) for name in ("ratchet.json", "CHANGELOG.md", "README.md", "REGISTER.md"))
        sources = self.read("sources.json")
        pin = json.loads(sources)["sources"][0]["commit"]
        moved = "0123456789abcdef0123456789abcdef01234567"
        write(self.copy, "sources.json", sources.replace(pin, moved))
        code, output = run("generate.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertEqual([line for line in output.splitlines() if line.startswith("wrote ")], ["wrote RATCHET.md"])
        self.assertIn("`%s`" % moved, self.read("RATCHET.md"))
        self.assertEqual(dict((name, self.read(name)) for name in before), before)
        self.checks_pass()


RELEASE_STEPS = "test_an_unreleased_entry_publishes_nothing_and_the_entry_given_its_date_releases_it"
RELEASED_COPY = "python3 checks/test_released_text.py --released-copy"
SUITE_PASSED = "expected_tests: every expected test ran and passed"


def released_copy_case():
    """The full suite on a released copy of this repo, as one test that the suite does not collect (D-2026-11-24-faster-suite).

    The test takes every release step of ReleaseSteps, with each of its assertions, on a copy, and then runs
    checks/expected_tests.py in that copy, which runs the whole suite there, this module among it. The class is made
    here and not at the top of the module, so that discover does not collect it and the suite does not run itself
    again. The job released of .github/workflows/checks.yml runs it once per pull request and push to main, with
    RELEASED_COPY, and the job checks needs that job; the release workflow runs it before it tags.
    """

    class ReleasedCopy(ReleaseSteps):
        def test_the_full_suite_passes_after_the_release(self):
            getattr(self, RELEASE_STEPS)()
            code, output = run("expected_tests.py", root=self.copy, cwd=self.copy, timeout=SUITE_TIMEOUT)
            self.assertEqual(code, 0, output)
            self.assertIn(SUITE_PASSED, output)

    return ReleasedCopy("test_the_full_suite_passes_after_the_release")


def released_copy(stream=None):
    """Run released_copy_case and give 0 only when its one test ran and passed: a skip, an error or a failure is 1."""
    stream = stream or sys.stderr
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite([released_copy_case()]))
    if (result.testsRun == 1 and result.wasSuccessful() and not result.skipped and not result.expectedFailures
            and not result.unexpectedSuccesses):
        stream.write("released copy: the full suite passed on a released copy of this repo\n")
        return 0
    stream.write("released copy: the full suite did not pass on a released copy of this repo, or did not run\n")
    return 1


def job_block(lines, start):
    """The line start and the lines under it up to the next line indented no deeper, or None unless start stands once."""
    if lines.count(start) != 1:
        return None
    index = lines.index(start)
    depth = len(start) - len(start.lstrip(" "))
    block = [start]
    for line in lines[index + 1:]:
        if line.strip(" ") and not line.strip(" ").startswith("#") and len(line) - len(line.lstrip(" ")) <= depth:
            break
        block.append(line)
    return block


# What the job checks must hold so that it is red unless the job released passed, whatever the event.
RELEASED_GATE = ("      RELEASED: ${{ needs.released.result }}\n",
                 '          if [ "$RELEASED" != success ]; then\n'
                 '            echo "The full suite on a released copy of this repo, the job released, did not pass."\n'
                 "            exit 1\n"
                 "          fi\n")


def released_job_problems(workflow):
    """Why checks.yml does not run the suite on a released copy in a job of its own that the job checks needs, each as a line."""
    lines = workflow.split("\n")
    problems = []
    job = job_block(lines, "  released:")
    if job is None:
        problems.append("the workflow has no job released, once")
    else:
        if job.count("        run: %s" % RELEASED_COPY) != 1:
            problems.append("the job released does not run %s once" % RELEASED_COPY)
        if [line for line in job if line.strip(" ").startswith(("if:", "- if:")) or "continue-on-error" in line]:
            problems.append("the job released has a condition, so it may not run or not fail")
    checks = job_block(lines, "  checks:")
    if checks is None:
        problems.append("the workflow has no job checks, once")
    else:
        text = "\n".join(checks) + "\n"
        if "    needs: [own, base, released]\n" not in text:
            problems.append("the job checks does not need the job released")
        if not all(part in text for part in RELEASED_GATE):
            problems.append("the job checks does not fail unless the job released passed")
    return problems


class ReleasedCopyJob(unittest.TestCase):
    """The case that runs the full suite on a released copy, and the job of checks.yml that runs it (D-2026-11-24-faster-suite)."""

    def workflow(self):
        with open(os.path.join(ROOT, ".github", "workflows", "checks.yml"), encoding="utf-8") as handle:
            return handle.read()

    def test_the_job_released_runs_the_case_and_the_job_checks_needs_it(self):
        self.assertEqual(released_job_problems(self.workflow()), [])

    def test_a_workflow_where_checks_does_not_need_released_or_released_does_not_run_the_case_fails(self):
        workflow = self.workflow()
        cases = {
            "checks does not need released": (("needs: [own, base, released]", "needs: [own, base]"), "does not need the job released"),
            "checks does not read its result": (('if [ "$RELEASED" != success ]', 'if [ "$RELEASED" = nothing ]'), "does not fail unless"),
            "checks does not fail on it": (('the job released, did not pass."\n            exit 1', 'the job released, did not pass."\n            true'), "does not fail unless"),
            "released runs something else": ((RELEASED_COPY, "python3 checks/expected_tests.py"), "does not run"),
            "released runs only on a push": (("  released:\n", "  released:\n    if: github.event_name == 'push'\n"), "has a condition"),
            "released may fail and pass": (("  released:\n", "  released:\n    continue-on-error: true\n"), "has a condition"),
            "no job released": (("  released:\n", "  other:\n"), "no job released"),
        }
        for name, ((old, new), problem) in sorted(cases.items()):
            with self.subTest(case=name):
                self.assertEqual(workflow.count(old), 1, old)
                problems = released_job_problems(workflow.replace(old, new))
                self.assertTrue([line for line in problems if problem in line], problems)

    def test_the_release_workflow_runs_the_case_before_it_tags(self):
        with open(os.path.join(ROOT, ".github", "workflows", "release.yml"), encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        self.assertEqual(lines.count("        run: %s" % RELEASED_COPY), 1)
        self.assertLess(lines.index("        run: %s" % RELEASED_COPY), lines.index("        run: python3 checks/release.py publish"))

    def run_the_case(self, suite):
        """released_copy with the release steps and the run of the suite in the copy replaced: [what was called], exit status."""
        called = []
        module = sys.modules[__name__]

        def steps(case):
            called.append("steps")

        def fake_run(script, *args, **options):
            called.append((script, args, options["root"] == options["cwd"] and options["root"] != ROOT))
            return suite()

        with unittest.mock.patch.object(module.ReleaseSteps, RELEASE_STEPS, steps), unittest.mock.patch.object(module, "run", fake_run):
            stream = io.StringIO()
            code = module.released_copy(stream)
        return called, code, stream.getvalue()

    def test_the_case_takes_the_release_steps_and_then_runs_the_suite_in_the_copy(self):
        called, code, output = self.run_the_case(lambda: (0, SUITE_PASSED + ": 3 tests\n"))
        self.assertEqual(called, ["steps", ("expected_tests.py", (), True)])
        self.assertEqual(code, 0, output)
        self.assertIn("released copy: the full suite passed", output)

    def test_a_released_copy_whose_suite_fails_or_does_not_run_fails(self):
        def skip():
            raise unittest.SkipTest("skipped")

        for name, suite in (("fails", lambda: (1, "expected_tests: 1 problem\n")), ("says nothing", lambda: (0, "")), ("skipped", skip)):
            with self.subTest(suite=name):
                called, code, output = self.run_the_case(suite)
                self.assertEqual(code, 1, output)
                self.assertIn("released copy: the full suite did not pass", output)


if __name__ == "__main__":
    if sys.argv[1:] == ["--released-copy"]:
        sys.exit(released_copy())
    unittest.main()
