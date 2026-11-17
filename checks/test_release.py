"""The release script must fail on every fault it claims to catch (ratchet.test-can-fail).

    python3 -m unittest discover -s checks -v

checks/release.py tags and releases a version from the release workflow
(D-2026-11-17-release-on-merge, D-2026-11-17-release-links). These tests never reach
the network: the GitHub API is a fake, given to the script as a function, and the HTTP
client is given a fake opener. Standard library only.
"""

import io
import json
import os
import re
import shutil
import tempfile
import unittest
import urllib.error
import urllib.request

import release

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = "fabian-von-tiedemann/ratchet"
SHA = "a" * 40
OTHER = "b" * 40
EARLIER = "c" * 40
LATER = "d" * 40
TOKEN = "ghs_THISISNOTAREALTOKEN0123456789abcdef"
BODY_MARKER = "BODY-FROM-THE-RESPONSE"
PATH = "/repos/%s" % REPO
MAIN = "refs/heads/main"
with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as _handle:
    NOW = json.load(_handle)["version"]
with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as _handle:
    # The older versions in today's changelog, read another way than the script reads them.
    OLDER = [v for v in re.findall(r"^## ([0-9]+\.[0-9]+) \(", _handle.read(), re.M) if v != NOW]
TAGGED = dict((v, ("commit", EARLIER)) for v in OLDER)
RELEASED = [{"tag_name": "v" + v, "draft": False} for v in OLDER]


def release_line(version, repo=REPO):
    """The one line of a release, written out here and not taken from the script."""
    return ("Ratchet %s: see [the changelog entry](https://github.com/%s/blob/v%s/CHANGELOG.md) "
            "and [the files at this tag](https://github.com/%s/tree/v%s)" % (version, repo, version, repo, version))


def changelog(*entries):
    """A changelog with one entry for each (version, text), newest first."""
    parts = ["# Changelog\n"]
    for version, text in entries:
        parts.append("\n## %s (2026-11-17)\n\n%s\n" % (version, text))
    return "".join(parts)


TWO = changelog(("0.4", "The entry for 0.4."), ("0.3", "The entry for 0.3."))
THREE = changelog(("0.5", "The entry for 0.5."), ("0.4", "The entry for 0.4."), ("0.3", "The entry for 0.3."))
# Lines that a reader may take for the heading of 0.4, and that are not of the one exact form.
NOT_A_HEADING = (
    "## 0.4 (2026-11-17) ", " ## 0.4 (2026-11-17)", "##  0.4 (2026-11-17)", "## 0.4  (2026-11-17)", "##\t0.4 (2026-11-17)",
    "## v0.4 (2026-11-17)", "## 0.4", "### 0.4 (2026-11-17)", "# 0.4 (2026-11-17)", "> ## 0.4 (2026-11-17)",
    "- ## 0.4 (2026-11-17)", "\r## 0.4 (2026-11-17)", "\u00a0## 0.4 (2026-11-17)",
    "## 0.4 (2026-11-17)\u00a0", "## \u0660.\u0664 (2026-11-17)", "## 0.4 (\uff12026-11-17)", "## 0.4 (2026-11-17)\u2028",
)
# A changelog with a lone carriage return, lines of spaces that are not ASCII, a link definition and a comment.
HOSTILE = "\n".join([
    "# Changelog", "", "## 0.4 (2026-11-17)", "\u00a0", "\u2003",
    "Text with a lone carriage return\r## 0.3 (2026-11-17) HIDDEN", "", "[x]: https://example.invalid/HIDDEN",
    "<!-- HIDDEN -->", "\u3000", "", "## 0.3 (2026-11-16)", "", "Old.", "\u00a0", "",
])
DONE_03 = {"tags": {"0.3": ("commit", EARLIER)}, "releases": [{"tag_name": "v0.3", "draft": False}]}


class Cancelled(Exception):
    """The run is cancelled: the fake stops answering at a chosen request."""


class FakeGitHub:
    """The part of the GitHub API that the script uses, in memory.

    tags: {version: (object type, sha)}. releases: [{"tag_name": ..., "draft": ...}].
    fail: {(method, path): status} answers that request with that status.
    cancel: a (method, path) at which the run is cancelled before the request is answered.
    ancestors: the commits that are earlier commits of every head.
    """

    def __init__(self, tags=None, releases=None, fail=None, ancestors=(), moves_tag_to=None, cancel=None):
        self.tags = dict(tags or {})
        self.releases = [dict(r) for r in (releases or [])]
        self.fail = dict(fail or {})
        self.ancestors = set(ancestors)
        self.moves_tag_to = moves_tag_to
        self.cancel = cancel
        self.calls = []

    @property
    def writes(self):
        return [(method, path) for method, path, _ in self.calls if method != "GET"]

    def ref(self, version):
        kind, sha = self.tags[version]
        return {"ref": "refs/tags/v%s" % version, "object": {"type": kind, "sha": sha}}

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if (method, path) == self.cancel:
            raise Cancelled()
        if (method, path) in self.fail:
            return self.fail[(method, path)], None
        if method == "GET" and path == PATH + "/git/matching-refs/tags/v":
            return 200, [self.ref(v) for v in sorted(self.tags)]
        if method == "GET" and path.startswith(PATH + "/releases?per_page=100&page="):
            page = int(path.rsplit("=", 1)[1])
            return 200, self.releases[(page - 1) * 100:page * 100]
        if method == "POST" and path == PATH + "/git/refs":
            version = body["ref"][len("refs/tags/v"):]
            if version in self.tags:
                return 422, None
            self.tags[version] = ("commit", body["sha"])
            created = self.ref(version)
            if self.moves_tag_to:
                self.tags[version] = ("commit", self.moves_tag_to)
            return 201, created
        if method == "POST" and path == PATH + "/releases":
            created = {"tag_name": body["tag_name"], "name": body["name"], "draft": body["draft"], "body": body["body"]}
            self.releases.append(created)
            return 201, created
        if method == "GET" and path.startswith(PATH + "/git/ref/tags/v"):
            version = path[len(PATH + "/git/ref/tags/v"):]
            return (200, self.ref(version)) if version in self.tags else (404, None)
        if method == "GET" and path.startswith(PATH + "/compare/"):
            base, head = path[len(PATH + "/compare/"):].split("...")
            return 200, {"status": "ahead" if base in self.ancestors and base != head else "diverged"}
        return 404, None


def publish(text, version="0.4", github=None, sha=SHA):
    """Run the script's publish step on a changelog. Returns (error text or None, output, fake)."""
    github = github if github is not None else FakeGitHub()
    out = io.StringIO()
    try:
        release.publish(version, text, REPO, sha, github, out)
    except release.ReleaseError as error:
        return str(error), out.getvalue(), github
    return None, out.getvalue(), github


class ReleaseText(unittest.TestCase):
    """The release text is one fixed line written in the script, and nothing from the changelog (D-2026-11-17-release-links)."""

    def test_the_release_text_is_exactly_the_fixed_line_for_the_version_and_the_repo(self):
        self.assertEqual(release.release_text("0.4", "owner/name"),
                         "Ratchet 0.4: see [the changelog entry](https://github.com/owner/name/blob/v0.4/CHANGELOG.md) "
                         "and [the files at this tag](https://github.com/owner/name/tree/v0.4)")
        self.assertEqual(release.release_text("12.30", REPO), release_line("12.30"))
        # No anchor: the link does not depend on how GitHub makes the anchor of a heading.
        self.assertNotIn("#", release.release_text("0.4", REPO))

    def test_no_byte_of_the_changelog_reaches_the_release(self):
        error, _, github = publish(HOSTILE, github=FakeGitHub(**DONE_03))
        self.assertIsNone(error)
        body = github.releases[-1]["body"]
        self.assertEqual(body, release_line("0.4"))
        for fragment in ("\r", " ", " ", "　", "example.invalid", "HIDDEN", "Old.", "<!--"):
            self.assertNotIn(fragment, body)


class ChangelogVersions(unittest.TestCase):
    """The script reads from the changelog only which versions have an entry, from one exact line."""

    def test_only_a_line_of_the_exact_form_is_the_heading_of_a_version(self):
        self.assertEqual(release.changelog_versions(TWO), ["0.4", "0.3"])
        for line in NOT_A_HEADING:
            with self.subTest(line=line):
                self.assertEqual(release.changelog_versions(changelog(("0.3", "Three.")) + line + "\n"), ["0.3"])

    def test_crlf_is_read_as_lf(self):
        self.assertEqual(release.changelog_versions(TWO.replace("\n", "\r\n")), ["0.4", "0.3"])

    def test_a_line_of_the_form_counts_wherever_it_stands(self):
        # A known limit: in a code block a renderer shows the line as code, and the script counts it.
        # No text is copied, so the most it can do is make the script take a version for one with an entry.
        text = changelog(("0.4", "```\n## 0.2 (2026-11-16)\n```"), ("0.3", "Three."))
        self.assertEqual(release.changelog_versions(text), ["0.4", "0.2", "0.3"])

    def test_a_missing_entry_for_the_version_fails_before_any_request(self):
        for line in ("",) + NOT_A_HEADING:
            with self.subTest(line=line):
                text = "# Changelog\n\n%s\n\nThe entry for 0.4.\n\n## 0.3 (2026-11-16)\n\nThree.\n" % line
                error, _, github = publish(text, github=FakeGitHub(**DONE_03))
                self.assertEqual(error, "CHANGELOG.md has no entry for 0.4, the version in ratchet.json")
                self.assertEqual(github.calls, [])

    def test_an_older_tag_without_an_entry_fails_and_writes_nothing(self):
        for line in ("",) + tuple(l.replace("0.4", "0.2") for l in NOT_A_HEADING):
            with self.subTest(line=line):
                text = TWO + "\n%s\n\nThe entry for 0.2.\n" % line
                github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.2": ("commit", EARLIER)},
                                    releases=[{"tag_name": "v0.3", "draft": False}, {"tag_name": "v0.2", "draft": False}])
                error, _, github = publish(text, github=github)
                self.assertEqual(error, "the tag v0.2 has no entry in CHANGELOG.md. Nothing was written.")
                self.assertEqual(github.writes, [])

    def test_a_changelog_that_is_not_utf8_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "CHANGELOG.md")
            with open(path, "wb") as handle:
                handle.write(TWO.encode("utf-8").replace(b"for 0.4", b"for \xff0.4"))
            with self.assertRaises(release.ReleaseError) as caught:
                release.read_text(path)
        self.assertIn("is not valid UTF-8, at byte", str(caught.exception))

    def test_todays_changelog_is_read_without_a_fault(self):
        with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as handle:
            versions = release.changelog_versions(handle.read())
        self.assertEqual(versions, [NOW] + OLDER)
        self.assertEqual(versions[-3:], ["0.3", "0.2", "0.1"])


class Publish(unittest.TestCase):
    """Tag and release are created in order, checked, and never written over."""

    def test_a_new_version_is_tagged_at_this_commit_and_released(self):
        error, out, github = publish(TWO, github=FakeGitHub(**DONE_03))
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs"), ("POST", PATH + "/releases")])
        self.assertEqual(github.calls[-3][2], {"ref": "refs/tags/v0.4", "sha": SHA})
        self.assertEqual(github.calls[-2][2], {"tag_name": "v0.4", "name": "Ratchet 0.4",
                                               "body": release_line("0.4"),
                                               "draft": False, "prerelease": False})
        self.assertEqual(github.calls[-1][:2], ("GET", PATH + "/git/ref/tags/v0.4"))
        self.assertIn("Tagged v0.4 at %s and released Ratchet 0.4" % SHA, out)

    def test_an_older_version_without_a_tag_fails_and_is_named(self):
        text = changelog(("0.5", "Five."), ("0.4", "Four."), ("0.3", "Three."), ("0.2", "Two."))
        github = FakeGitHub(**DONE_03)
        error, _, github = publish(text, version="0.5", github=github)
        self.assertIn("0.2: no tag", error)
        self.assertIn("0.4: no tag", error)
        self.assertIn("Nothing was written", error)
        self.assertEqual(github.writes, [])

    def test_an_older_version_with_a_tag_and_no_release_fails_and_is_named(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER)})
        error, _, github = publish(TWO, github=github)
        self.assertIn("0.3: a tag and no published release", error)
        self.assertEqual(github.writes, [])

    def test_an_older_version_with_only_a_draft_fails_and_is_named(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER)}, releases=[{"tag_name": "v0.3", "draft": True}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("0.3: a tag and no published release", error)
        self.assertEqual(github.writes, [])

    def test_an_unfinished_older_version_fails_also_when_nothing_is_to_be_released(self):
        github = FakeGitHub(tags={"0.4": ("commit", EARLIER), "0.3": ("commit", EARLIER)},
                            releases=[{"tag_name": "v0.4", "draft": False}], ancestors=[EARLIER])
        error, _, github = publish(TWO, github=github)
        self.assertIn("0.3: a tag and no published release", error)
        self.assertEqual(github.writes, [])

    def test_a_version_from_before_releases_needs_only_its_tag(self):
        self.assertEqual(release.BEFORE_RELEASES, ("0.1",))
        text = changelog(("0.4", "Four."), ("0.3", "Three."), ("0.1", "One."))
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.1": ("commit", EARLIER)}, releases=[{"tag_name": "v0.3", "draft": False}])
        error, _, github = publish(text, github=github)
        self.assertIsNone(error)
        github = FakeGitHub(**DONE_03)
        error, _, github = publish(text, github=github)
        self.assertIn("0.1: no tag", error)
        self.assertEqual(github.writes, [])

    def test_newer_tags_and_releases_are_ignored(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.5": ("commit", LATER), "0.9": ("tag", LATER)},
                            releases=[{"tag_name": "v0.3", "draft": False}, {"tag_name": "v0.5", "draft": True}])
        error, out, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs"), ("POST", PATH + "/releases")])

    def test_a_tag_without_an_entry_fails_up_to_this_version(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.2": ("commit", EARLIER)}, releases=[{"tag_name": "v0.3", "draft": False}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("the tag v0.2 has no entry in CHANGELOG.md", error)
        self.assertEqual(github.writes, [])

    def test_a_tag_that_is_not_a_version_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4-rc": ("commit", EARLIER)}, releases=[{"tag_name": "v0.3", "draft": False}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("a tag under refs/tags/v is not of the form vMAJOR.MINOR", error)
        self.assertEqual(github.writes, [])

    def test_a_tag_at_this_commit_without_a_release_gets_only_its_release(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", SHA)}, releases=[{"tag_name": "v0.3", "draft": False}])
        error, out, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/releases")])
        self.assertEqual(github.calls[-1][:2], ("GET", PATH + "/git/ref/tags/v0.4"))
        self.assertIn("The tag v0.4 was already at %s. Released Ratchet 0.4" % SHA, out)

    def test_a_tag_at_this_commit_with_a_draft_writes_nothing_and_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", SHA)},
                            releases=[{"tag_name": "v0.3", "draft": False}, {"tag_name": "v0.4", "draft": True}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("a draft release for v0.4 exists", error)
        self.assertEqual(github.writes, [])

    def test_a_tag_at_this_commit_with_a_published_release_is_done(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", SHA)},
                            releases=[{"tag_name": "v0.3", "draft": False}, {"tag_name": "v0.4", "draft": False}])
        error, out, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [])
        self.assertIn("v0.4 is tagged at this commit and released. Nothing to do", out)

    def test_a_draft_without_a_tag_writes_nothing_and_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER)}, releases=[{"tag_name": "v0.3", "draft": False}, {"tag_name": "v0.4", "draft": True}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("a release for v0.4 exists, and the tag does not", error)
        self.assertEqual(github.writes, [])

    def test_two_releases_for_one_tag_fail(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", SHA)},
                            releases=[{"tag_name": "v0.3", "draft": False}, {"tag_name": "v0.4", "draft": False}, {"tag_name": "v0.4", "draft": True}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("2 releases for v0.4", error)
        self.assertEqual(github.writes, [])

    def test_a_tag_at_another_commit_without_a_published_release_writes_nothing_and_fails(self):
        for releases in ([], [{"tag_name": "v0.4", "draft": True}]):
            with self.subTest(releases=releases):
                github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", OTHER)},
                                    releases=[{"tag_name": "v0.3", "draft": False}] + releases, ancestors=[OTHER])
                error, _, github = publish(TWO, github=github)
                self.assertIn("the tag v0.4 points at another commit than this one", error)
                self.assertEqual(github.writes, [])

    def test_a_tag_at_another_commit_that_is_not_earlier_writes_nothing_and_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", OTHER)},
                            releases=[{"tag_name": "v0.3", "draft": False}, {"tag_name": "v0.4", "draft": False}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("the tag v0.4 points at a commit that is not an earlier commit of this one", error)
        self.assertEqual(github.writes, [])

    def test_an_annotated_tag_writes_nothing_and_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("tag", SHA)},
                            releases=[{"tag_name": "v0.3", "draft": False}, {"tag_name": "v0.4", "draft": False}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("the tag v0.4 points at another commit than this one", error)
        self.assertEqual(github.writes, [])

    def test_a_version_released_at_an_earlier_commit_is_done(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", OTHER)},
                            releases=[{"tag_name": "v0.3", "draft": False}, {"tag_name": "v0.4", "draft": False}], ancestors=[OTHER])
        error, out, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [])
        self.assertIn("v0.4 is released at an earlier commit, and this commit does not raise the version. Nothing to do", out)

    def test_a_refused_ref_creation_writes_nothing_more(self):
        github = FakeGitHub(fail={("POST", PATH + "/git/refs"): 422}, **DONE_03)
        error, _, github = publish(TWO, github=github)
        self.assertIn("POST %s/git/refs: HTTP 422" % PATH, error)
        self.assertIn("The tag v0.4 was not created, and nothing was written", error)
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs")])

    def test_a_tag_whose_target_does_not_match_after_creation_fails(self):
        github = FakeGitHub(moves_tag_to=OTHER, **DONE_03)
        error, _, github = publish(TWO, github=github)
        self.assertIn("read back, the tag v0.4 does not point at %s" % SHA, error)

    def test_a_created_tag_that_the_answer_puts_elsewhere_gets_no_release(self):
        class Elsewhere(FakeGitHub):
            def __call__(self, method, path, body=None):
                status, data = FakeGitHub.__call__(self, method, path, body)
                if method == "POST" and path.endswith("/git/refs"):
                    data = dict(data, object={"type": "commit", "sha": OTHER})
                return status, data
        github = Elsewhere(**DONE_03)
        error, _, github = publish(TWO, github=github)
        self.assertIn("the answer says that the tag v0.4 points at another commit", error)
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs")])

    def test_an_api_error_writes_nothing_more(self):
        cases = {
            ("GET", PATH + "/git/matching-refs/tags/v"): [],
            ("GET", PATH + "/releases?per_page=100&page=1"): [],
            ("POST", PATH + "/git/refs"): [("POST", PATH + "/git/refs")],
            ("POST", PATH + "/releases"): [("POST", PATH + "/git/refs"), ("POST", PATH + "/releases")],
        }
        for (method, path), writes in cases.items():
            with self.subTest(method=method, path=path):
                github = FakeGitHub(fail={(method, path): 500}, **DONE_03)
                error, _, github = publish(TWO, github=github)
                self.assertIn("%s %s: HTTP 500" % (method, path), error)
                self.assertEqual(github.writes, writes)
                self.assertEqual(github.calls[-1][:2], (method, path))

    def test_an_answer_of_the_wrong_form_fails(self):
        class Odd(FakeGitHub):
            def __call__(self, method, path, body=None):
                self.calls.append((method, path, body))
                return 200, {"not": "a list"}
        error, _, github = publish(TWO, github=Odd())
        self.assertIn("GET %s/git/matching-refs/tags/v: the answer is not of the form expected" % PATH, error)
        self.assertEqual(github.writes, [])

    def test_the_version_must_be_the_newest_entry(self):
        error, _, github = publish(TWO, version="0.3")
        self.assertIn("the newest entry in CHANGELOG.md is 0.4, and ratchet.json says 0.3", error)
        self.assertEqual(github.calls, [])

    def test_a_version_without_an_entry_fails_before_any_call(self):
        error, _, github = publish(changelog(("0.3", "Three.")))
        self.assertIn("CHANGELOG.md has no entry for 0.4", error)
        self.assertEqual(github.calls, [])


class Unfinished(unittest.TestCase):
    """Round 2, finding 1: an unfinished version stops every later run, and its own rerun finishes it."""

    SHA4 = SHA
    SHA5 = LATER

    def test_a_failed_publication_of_04_stops_05_and_a_rerun_of_04_finishes(self):
        github = FakeGitHub(fail={("POST", PATH + "/releases"): 500}, **DONE_03)
        error, _, github = publish(TWO, github=github, sha=self.SHA4)
        self.assertIn("POST %s/releases: HTTP 500" % PATH, error)
        self.assertEqual(github.tags["0.4"], ("commit", self.SHA4))
        del github.fail[("POST", PATH + "/releases")]
        # 0.5 is merged. Its run fails, names 0.4, and writes nothing.
        github.calls = []
        error, _, github = publish(THREE, version="0.5", github=github, sha=self.SHA5)
        self.assertIn("0.4: a tag and no published release", error)
        self.assertIn("Nothing was written", error)
        self.assertEqual(github.writes, [])
        self.assertNotIn("0.5", github.tags)
        # The maintainer reruns the run of 0.4. It finishes 0.4 and only 0.4.
        github.calls = []
        error, out, github = publish(TWO, github=github, sha=self.SHA4)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/releases")])
        self.assertEqual(github.releases[-1]["tag_name"], "v0.4")
        # Then the run of 0.5 is rerun, and releases 0.5.
        github.calls = []
        error, out, github = publish(THREE, version="0.5", github=github, sha=self.SHA5)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs"), ("POST", PATH + "/releases")])

    def test_a_rerun_of_04_is_not_stopped_by_a_tag_for_05(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", self.SHA4), "0.5": ("commit", self.SHA5)},
                            releases=[{"tag_name": "v0.3", "draft": False}])
        error, _, github = publish(TWO, github=github, sha=self.SHA4)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/releases")])

    def test_a_run_cancelled_right_after_tagging_stops_every_later_run(self):
        github = FakeGitHub(cancel=("POST", PATH + "/releases"), **DONE_03)
        with self.assertRaises(Cancelled):
            publish(TWO, github=github, sha=self.SHA4)
        self.assertEqual(github.tags["0.4"], ("commit", self.SHA4))
        github.cancel = None
        # A later merge that keeps 0.4 fails, and so does the merge of 0.5. Neither writes.
        for text, version in ((TWO, "0.4"), (THREE, "0.5")):
            with self.subTest(version=version):
                github.calls = []
                error, _, github = publish(text, version=version, github=github, sha=self.SHA5)
                self.assertIsNotNone(error)
                self.assertIn("Nothing was written", error)
                self.assertEqual(github.writes, [])
        self.assertIn("0.4: a tag and no published release", error)
        # The rerun of the cancelled run finishes it.
        github.calls = []
        error, _, github = publish(TWO, github=github, sha=self.SHA4)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/releases")])


class Response:
    def __init__(self, status, data):
        self.status = status
        self.raw = json.dumps(data).encode("utf-8")

    def read(self):
        return self.raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    """Stands in for urllib's opener. Records every request, and answers from a FakeGitHub."""

    def __init__(self, github):
        self.github = github
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        path = request.full_url[len("https://api.github.com"):]
        body = json.loads(request.data.decode("utf-8")) if request.data else None
        status, data = self.github(request.get_method(), path, body)
        if status >= 400:
            # The body holds the token and text that must never be shown.
            raise urllib.error.HTTPError(request.full_url, status, "error", {}, io.BytesIO(("%s %s" % (BODY_MARKER, TOKEN)).encode()))
        return Response(status, data)


def environment(**changes):
    environ = {"GITHUB_TOKEN": TOKEN, "GITHUB_REPOSITORY": REPO, "GITHUB_SHA": SHA, "GITHUB_REF": MAIN}
    environ.update(changes)
    return dict((k, v) for k, v in environ.items() if v is not None)


def run_main(github, argv=("publish",), environ=None, root=None):
    opener = FakeOpener(github)
    out, err = io.StringIO(), io.StringIO()
    code = release.main(list(argv), environ=environ if environ is not None else environment(), opener=opener, out=out, err=err, root=root)
    return code, out.getvalue(), err.getvalue(), opener


class Token(unittest.TestCase):
    """The token comes from GITHUB_TOKEN, goes only to api.github.com, and is never printed."""

    def test_the_token_never_appears_in_output(self):
        scenarios = [
            FakeGitHub(tags=TAGGED, releases=RELEASED),
            FakeGitHub(tags=TAGGED, releases=RELEASED, fail={("POST", PATH + "/git/refs"): 422}),
            FakeGitHub(tags=TAGGED, releases=RELEASED, fail={("POST", PATH + "/releases"): 500}),
            FakeGitHub(fail={("GET", PATH + "/git/matching-refs/tags/v"): 401}),
            FakeGitHub(tags=dict(TAGGED, **{NOW: ("commit", OTHER)}), releases=RELEASED),
        ]
        for github in scenarios:
            with self.subTest(fail=github.fail):
                code, out, err, opener = run_main(github)
                self.assertNotIn(TOKEN, out + err)
                self.assertNotIn(TOKEN[4:20], out + err)
                self.assertNotIn(BODY_MARKER, out + err)
                self.assertTrue(opener.requests)
                for request in opener.requests:
                    self.assertTrue(request.full_url.startswith("https://api.github.com/repos/%s/" % REPO))
                    self.assertEqual(request.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertEqual(code, 1)
        self.assertIn("the tag v%s points at another commit than this one" % NOW, err)

    def test_an_error_gives_the_method_the_path_and_the_status(self):
        github = FakeGitHub(fail={("GET", PATH + "/git/matching-refs/tags/v"): 403})
        code, out, err, _ = run_main(github)
        self.assertEqual(code, 1)
        self.assertEqual(err, "release: GET %s/git/matching-refs/tags/v: HTTP 403. Nothing was written.\n" % PATH)

    def test_no_token_no_run(self):
        for token in (None, ""):
            with self.subTest(token=token):
                code, _, err, opener = run_main(FakeGitHub(), environ=environment(GITHUB_TOKEN=token))
                self.assertEqual(code, 1)
                self.assertIn("GITHUB_TOKEN is not set", err)
                self.assertEqual(opener.requests, [])

    def test_the_repository_the_commit_and_the_branch_are_read_strictly(self):
        for name, value in (("GITHUB_REPOSITORY", "owner/repo/../other"), ("GITHUB_REPOSITORY", "https://example.invalid/x"),
                            ("GITHUB_SHA", "A" * 40), ("GITHUB_SHA", SHA[:39]), ("GITHUB_SHA", SHA + "\n"),
                            ("GITHUB_REF", None), ("GITHUB_REF", "refs/heads/personlig/x"), ("GITHUB_REF", "refs/tags/v0.4"),
                            ("GITHUB_REF", MAIN + "\n")):
            with self.subTest(name=name, value=value):
                code, _, err, opener = run_main(FakeGitHub(), environ=environment(**{name: value}))
                self.assertEqual(code, 1)
                self.assertIn("%s is not" % name, err)
                self.assertEqual(opener.requests, [])

    def test_only_paths_under_the_repository_api_are_sent(self):
        opener = FakeOpener(FakeGitHub())
        api = release.github(TOKEN, opener)
        for path in ("https://example.invalid/repos/x", "//example.invalid/repos/x", "/repos/a/b/../../x", "/user", "/repos/a/b/x y"):
            with self.subTest(path=path):
                with self.assertRaises(release.ReleaseError) as caught:
                    api("GET", path)
                self.assertNotIn(TOKEN, str(caught.exception))
        self.assertEqual(opener.requests, [])

    def test_a_redirect_is_not_followed(self):
        handler = release.NoRedirect()
        request = urllib.request.Request("https://api.github.com/repos/a/b/x", headers={"Authorization": "Bearer " + TOKEN})
        self.assertIsNone(handler.redirect_request(request, None, 302, "Found", {}, "https://example.invalid/"))
        default = release.default_opener()
        self.assertTrue(any(isinstance(h, release.NoRedirect) for h in default.handlers))
        self.assertFalse(any(type(h) is urllib.request.HTTPRedirectHandler for h in default.handlers))

    def test_notes_need_no_token_and_no_network(self):
        out, err = io.StringIO(), io.StringIO()
        code = release.main(["notes", "--repo", REPO], environ={}, opener=None, out=out, err=err)
        self.assertEqual((code, err.getvalue()), (0, ""))
        self.assertEqual(out.getvalue(), release_line(NOW) + "\n")


class VersionSource(unittest.TestCase):
    """Round 2, finding 3: the version is read from ratchet.json at the checked-out commit, never written in the code."""

    VERSION = "9.7"

    def setUp(self):
        self.directory = tempfile.mkdtemp()
        with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as handle:
            data = json.load(handle)
        data["version"] = self.VERSION
        with open(os.path.join(self.directory, "ratchet.json"), "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        for rule in data["rules"]:
            if "reference_check" in rule:
                target = os.path.join(self.directory, rule["reference_check"])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                open(target, "w").close()
        with open(os.path.join(self.directory, "CHANGELOG.md"), "w", encoding="utf-8") as handle:
            handle.write(changelog((self.VERSION, "The entry for %s." % self.VERSION), ("0.3", "The entry for 0.3.")))

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_publish_tags_the_version_in_ratchet_json(self):
        github = FakeGitHub(**DONE_03)
        code, out, err, _ = run_main(github, root=self.directory)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.tags[self.VERSION], ("commit", SHA))
        self.assertEqual(github.releases[-1]["tag_name"], "v" + self.VERSION)
        self.assertEqual(github.releases[-1]["body"], release_line(self.VERSION))

    def test_notes_give_the_entry_for_the_version_in_ratchet_json(self):
        out, err = io.StringIO(), io.StringIO()
        code = release.main(["notes", "--repo", REPO], environ={}, opener=None, out=out, err=err, root=self.directory)
        self.assertEqual((code, err.getvalue()), (0, ""))
        self.assertEqual(out.getvalue(), release_line(self.VERSION) + "\n")

    def test_no_byte_of_the_changelog_reaches_publish_or_notes(self):
        with open(os.path.join(self.directory, "CHANGELOG.md"), "w", encoding="utf-8", newline="") as handle:
            handle.write(HOSTILE.replace("0.4", self.VERSION))
        github = FakeGitHub(**DONE_03)
        code, out, err, _ = run_main(github, root=self.directory)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.releases[-1]["body"], release_line(self.VERSION))
        out, err = io.StringIO(), io.StringIO()
        code = release.main(["notes", "--repo", REPO], environ={}, opener=None, out=out, err=err, root=self.directory)
        self.assertEqual((code, err.getvalue(), out.getvalue()), (0, "", release_line(self.VERSION) + "\n"))


def workflow_code(text):
    """The lines of a workflow that are not blank and not a comment, by ASCII rules only.

    A line is blank when it holds nothing but the ASCII space, and a comment when its first
    character other than the ASCII space is #. A tab or a space that is not ASCII is neither
    indentation nor blank here, so such a line is kept, and the comparison with the reviewed
    form fails on it.
    """
    return [line for line in text.split("\n") if line.strip(" ") and not line.lstrip(" ").startswith("#")]


class Workflow(unittest.TestCase):
    """The release workflow is thin, and keeps the form that was reviewed."""

    LIVE = os.path.join(ROOT, ".github", "workflows", "release.yml")

    def lines(self):
        with open(self.LIVE, "rb") as handle:
            return handle.read().decode("utf-8", errors="strict").split("\n")

    def test_the_workflow_keeps_its_form(self):
        lines = self.lines()
        text = "\n".join(lines)
        self.assertIn("on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n\npermissions:\n  contents: read\n", text)
        self.assertFalse([l for l in lines if "inputs:" in l])
        self.assertEqual([l for l in lines if "contents: write" in l], ["      contents: write"])
        self.assertEqual([l.strip(" ") for l in lines if "runs-on:" in l], ["runs-on: ubuntu-24.04"])
        self.assertEqual([l.strip(" ") for l in lines if "timeout-minutes:" in l], ["timeout-minutes: 5"])
        uses = [l.strip(" ") for l in lines if "uses:" in l]
        self.assertEqual(len(uses), 1)
        self.assertRegex(uses[0], r"^- uses: actions/checkout@[0-9a-f]{40} # v[0-9.]+\Z")
        self.assertIn("          persist-credentials: false", lines)
        runs = [l.strip(" ") for l in lines if l.strip(" ").startswith("run:")]
        self.assertEqual(runs, [
            "run: python3 checks/generate.py --check",
            "run: python3 checks/check_register.py register.json --markdown REGISTER.md",
            "run: python3 -m unittest discover -s checks",
            "run: python3 checks/release.py publish",
        ])
        self.assertFalse([l for l in lines if "run:" in l and "${{" in l])
        self.assertEqual([l.strip(" ") for l in lines if "${{" in l], ["GITHUB_TOKEN: ${{ github.token }}"])
        self.assertLess(lines.index("          GITHUB_TOKEN: ${{ github.token }}"), lines.index("        run: python3 checks/release.py publish"))
        self.assertGreater(lines.index("          GITHUB_TOKEN: ${{ github.token }}"), lines.index("        run: python3 -m unittest discover -s checks"))

    # Round 1 of the new approach, finding 2: each part of the workflow that the design leans on has a test of
    # its own, and the whole file, without its comments, is the reviewed form and holds nothing else.

    def code(self):
        """The lines of the workflow that are not blank and not a comment, each as it stands."""
        return workflow_code("\n".join(self.lines()))

    def test_a_space_that_is_not_ascii_or_a_tab_before_a_hash_is_no_comment(self):
        # Last round, finding 3: a no-break space before # was read as the indentation of a comment.
        for space in ("\u00a0", "\u2003", "\u3000", "\u2028", "\t", " \u00a0"):
            with self.subTest(space=space):
                line = space + "# not a comment here"
                self.assertEqual(workflow_code("name: release\n%s\n" % line), ["name: release", line])
                self.assertEqual(workflow_code("name: release\n%s\n" % space), ["name: release", space])
        self.assertEqual(workflow_code("name: release\n  # a comment\n#\n\n   \n"), ["name: release"])

    def block(self, start):
        """The line start and the lines indented under it."""
        code = self.code()
        self.assertEqual(code.count(start), 1, start)
        index = code.index(start)
        depth = len(start) - len(start.lstrip(" "))
        lines = [start]
        for line in code[index + 1:]:
            if len(line) - len(line.lstrip(" ")) <= depth:
                break
            lines.append(line)
        return lines

    def test_one_release_run_at_a_time_and_a_running_one_is_never_cancelled(self):
        self.assertEqual(self.block("concurrency:"), ["concurrency:", "  group: release", "  cancel-in-progress: false"])
        self.assertEqual([l for l in self.code() if "concurrency" in l or "cancel-in-progress" in l],
                         ["concurrency:", "  cancel-in-progress: false"])

    def test_the_token_is_read_only_but_in_the_job_that_writes_tags_and_releases(self):
        self.assertEqual(self.block("permissions:"), ["permissions:", "  contents: read"])
        self.assertEqual(self.block("    permissions:"), ["    permissions:", "      contents: write"])
        self.assertEqual([l.strip(" ") for l in self.code() if "permissions" in l or "write" in l or "read-all" in l],
                         ["permissions:", "permissions:", "contents: write"])

    def test_it_runs_only_on_a_push_to_main_and_by_hand_with_no_input(self):
        self.assertEqual(self.block("on:"), ["on:", "  push:", "    branches: [main]", "  workflow_dispatch:"])
        self.assertFalse([l for l in self.code() if l.strip(" ").startswith(("if:", "- if:"))])

    def test_a_run_has_a_time_limit(self):
        self.assertEqual([l for l in self.code() if "timeout-minutes" in l], ["    timeout-minutes: 5"])

    def test_the_three_checks_run_in_order_before_the_one_step_that_writes(self):
        steps = self.block("    steps:")
        runs = [l.strip(" ") for l in steps if l.strip(" ").startswith(("run:", "- run:"))]
        self.assertEqual(runs, [
            "run: python3 checks/generate.py --check",
            "run: python3 checks/check_register.py register.json --markdown REGISTER.md",
            "run: python3 -m unittest discover -s checks",
            "run: python3 checks/release.py publish",
        ])
        self.assertFalse([l for l in self.code() if "continue-on-error" in l or "always()" in l or "failure()" in l])

    def test_the_workflow_is_the_reviewed_form_and_holds_nothing_else(self):
        # The checkout may be moved to another pinned commit. Everything else is as reviewed.
        code = [re.sub(r"@[0-9a-f]{40} # v[0-9]+(?:\.[0-9]+)*\Z", "@<commit> # v<version>", line) for line in self.code()]
        self.assertEqual(code, [
            "name: release",
            "on:",
            "  push:",
            "    branches: [main]",
            "  workflow_dispatch:",
            "permissions:",
            "  contents: read",
            "concurrency:",
            "  group: release",
            "  cancel-in-progress: false",
            "jobs:",
            "  release:",
            "    runs-on: ubuntu-24.04",
            "    timeout-minutes: 5",
            "    permissions:",
            "      contents: write",
            "    steps:",
            "      - uses: actions/checkout@<commit> # v<version>",
            "        with:",
            "          persist-credentials: false",
            "      - name: Generated text matches the data files",
            "        run: python3 checks/generate.py --check",
            "      - name: This repo's own register has not drifted",
            "        run: python3 checks/check_register.py register.json --markdown REGISTER.md",
            "      - name: Every check fails on the fixtures it claims to catch",
            "        run: python3 -m unittest discover -s checks",
            "      - name: Tag and release the version in ratchet.json, if it is new",
            "        env:",
            "          GITHUB_TOKEN: ${{ github.token }}",
            "        run: python3 checks/release.py publish",
        ])


if __name__ == "__main__":
    unittest.main()
