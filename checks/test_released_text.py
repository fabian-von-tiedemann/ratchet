"""The guard on released text, checks/released_text.py, and the steps of a release.

    python3 -m unittest discover -s checks -v

Each case makes a git repo of its own in a scratch directory, with its own tags, so no
case needs the tags of this repo and none is skipped where they are missing. The
guard runs on this repo's own tags in a step of its own in CI. Standard library only.
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
GUARD = "released_text.py"
OK = "released_text: released text matches its tags"
# How the release workflow finds the entry of a version (D-2026-11-17-release-on-merge, .github/workflows/release.yml in PR #9).
RELEASE_ENTRY = r"^## %s \([^)]*\)\n(.*?)(?=^## |\Z)"
# A changelog of three released versions and one that is not yet released, newest first.
ENTRIES = {
    "0.1": "## 0.1 (2026-01-01)\n\n- The first rules.\n",
    "0.2": "## 0.2 (2026-02-01)\n\nAdded:\n\n- The icon.\n\n",
    "0.3": "## 0.3 (2026-03-01)\n\n<!-- generated:count -->\nThree rules.\n<!-- /generated -->\n\n",
    "0.4": "## 0.4 (2026-04-01)\n\n<!-- generated:count -->\nFour rules.\n<!-- /generated -->\n\n",
}
TITLE = "# Changelog\n\n"
RATCHET = '{\n  "version": "%s",\n  "rules": []\n}\n'


def changelog(*versions):
    return TITLE + "".join(ENTRIES[version] for version in versions)


def git_environment(home):
    """git with no configuration but its own, so that a person's settings, such as signing, change nothing."""
    environment = dict(os.environ, HOME=home, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, LC_ALL="C")
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
    return result.stdout


def run(script, *args, root=ROOT, cwd=None):
    result = subprocess.run(
        [sys.executable, os.path.join(root, "checks", script)] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, cwd=cwd, timeout=600,
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
        write(self.root, "ratchet.json", RATCHET.replace("[]", '[{"key": "ratchet.new"}]') % "0.3")
        self.assert_fails("ratchet.json: names 0.3, which is released, and is not as it stood at the tag v0.3. A change to the rules raises the version")

    def test_a_released_version_whose_tag_holds_no_ratchet_json_fails(self):
        write(self.root, "CHANGELOG.md", changelog("0.2", "0.1"))
        write(self.root, "ratchet.json", RATCHET % "0.2")
        self.assert_fails("ratchet.json: names 0.2, which is released, and the tag v0.2 holds no ratchet.json")

    def test_a_ratchet_json_that_cannot_be_read_fails(self):
        for text, problem in (("{", "ratchet.json: not a valid data file"), ('{"version": 4}\n', "ratchet.json: the version must look like 0.4")):
            with self.subTest(text=text):
                write(self.root, "ratchet.json", text)
                self.assert_fails(problem)

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
    """The steps of the release of 0.4 on a copy of this repo, and the state after it.

    The version is already 0.4 in ratchet.json, so a release renames nothing: the release workflow tags the
    merge and writes the release text from the changelog. The copy gets tags that hold the changelog of each
    released version as it stands in the copy, which the guard in CI shows to be the changelog at the real tags.
    """

    def setUp(self):
        self.copy = os.path.join(tempfile.mkdtemp(prefix="ratchet-test-"), "ratchet")
        self.addCleanup(shutil.rmtree, os.path.dirname(self.copy))
        shutil.copytree(ROOT, self.copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        with open(os.path.join(self.copy, "ratchet.json"), encoding="utf-8") as handle:
            self.version = json.load(handle)["version"]
        with open(os.path.join(self.copy, "CHANGELOG.md"), encoding="utf-8", newline="") as handle:
            self.changelog = handle.read()

    def entries(self):
        """[(version, text of the entry)], newest first."""
        starts = [match.start() for match in re.finditer(r"^## ", self.changelog, re.M)]
        texts = [self.changelog[a:b] for a, b in zip(starts, starts[1:] + [len(self.changelog)])]
        return [(text.split(" ", 2)[1], text) for text in texts]

    def tag_the_releases_before(self):
        """Tags for every version before the one being released, oldest first, each with the changelog up to its own entry."""
        git(self.copy, "init", "-q")
        entries = self.entries()
        self.assertEqual(entries[0][0], self.version)
        title = self.changelog[:self.changelog.index("## ")]
        released = entries[1:]
        for number in range(len(released) - 1, -1, -1):
            if number == len(released) - 1:
                # The tag v0.1 of this repo holds no changelog: 0.1 is first written down in 0.2.
                os.remove(os.path.join(self.copy, "CHANGELOG.md"))
            else:
                write(self.copy, "CHANGELOG.md", title + "".join(text for _, text in released[number:]))
            commit_and_tag(self.copy, "v" + released[number][0])
        write(self.copy, "CHANGELOG.md", self.changelog)

    def test_the_release_of_0_4_finds_its_entry_and_everything_passes_after_it(self):
        self.assertEqual(self.version, "0.4")
        # The checks that the release workflow runs before it tags.
        for script, args in (("generate.py", ["--check"]), ("check_register.py", ["register.json", "--markdown", "REGISTER.md"])):
            with self.subTest(step=script):
                code, output = run(script, *args, root=self.copy, cwd=self.copy)
                self.assertEqual(code, 0, output)
        # The release text, found as the workflow finds it.
        found = re.search(RELEASE_ENTRY % re.escape(self.version), self.changelog, re.S | re.M)
        self.assertIsNotNone(found, "the release workflow finds no entry for %s" % self.version)
        body = found.group(1)
        self.assertIn("Ratchet 0.4, computed from `ratchet.json`", body)
        self.assertIn("ratchet.expected-tests-ran", body)
        self.assertIn("Added:", body)
        self.assertNotIn("## ", body)
        self.assertNotIn("nreleased", self.changelog[:found.end()])
        # The release: the workflow tags the merge.
        self.tag_the_releases_before()
        code, output = run(GUARD, root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        commit_and_tag(self.copy, "v0.4")
        code, output = run(GUARD, root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("in 4 tags", output)
        # After it, the full suite passes in the copy, run by the check that every expected test ran. This module
        # holds no test in that run, so that it does not run itself again.
        write(self.copy, "checks/test_released_text.py", '"""Left out of the run inside ReleaseSteps, which runs this module."""\n')
        code, output = run("expected_tests.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("expected_tests: every expected test ran and passed", output)

    def test_after_the_release_a_rule_changed_without_a_new_version_fails_the_guard(self):
        self.tag_the_releases_before()
        commit_and_tag(self.copy, "v0.4")
        rule = "Only the owner approves decisions."
        for name in ("ratchet.json", "register.json"):
            path = os.path.join(self.copy, name)
            with open(path, encoding="utf-8", newline="") as handle:
                text = handle.read()
            self.assertIn(rule, text)
            write(self.copy, name, text.replace(rule, "Only the owner approves every decision."))
        code, output = run("generate.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        code, output = run("generate.py", "--check", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        code, output = run(GUARD, root=self.copy, cwd=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("ratchet.json: names 0.4, which is released, and is not as it stood at the tag v0.4. A change to the rules raises the version", output)


if __name__ == "__main__":
    unittest.main()
