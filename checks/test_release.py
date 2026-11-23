"""The release script must fail on every fault it claims to catch (ratchet.test-can-fail).

    python3 -m unittest discover -s checks -v

checks/release.py tags and releases a version from the release workflow
(D-2026-11-17-release-on-merge, D-2026-11-17-release-links). These tests never reach
the network: the GitHub API is a fake, given to the script as a function, and the HTTP
client is given a fake opener. The history of main is read from git repositories that the
tests build in temporary directories. The real repository is never written to. Standard library only.
"""

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import urllib.error
import urllib.request
import zlib
from unittest import mock

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


class Cancelled(BaseException):
    """The run is cancelled: the fake stops answering at a chosen request.

    A BaseException, as KeyboardInterrupt is: GitHub stops a cancelled run, and the script cannot catch that.
    """


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


def commit_of(version):
    """A made-up commit at which ratchet.json first named a version, in the histories made up below."""
    return hashlib.sha1(("the commit that raised the version to " + version).encode("ascii")).hexdigest()


def made_up_history(text, version, sha):
    """A stand-in for the history of main, for the tests of the logic that are not about git.

    This commit names the version, and before it one commit for each older version that has a line
    in the changelog. The script never builds a history this way: it reads it with git (see MainHistory).
    """
    older = set(v for v in re.findall(r"^## ([0-9]+\.[0-9]+) \(", text, re.M)
                if release.version_key(v) < release.version_key(version))
    return [(sha, version)] + [(commit_of(v), v) for v in sorted(older, key=release.version_key, reverse=True)]


def publish(text, version="0.4", github=None, sha=SHA, history=None, report=False, pending=None):
    """Run the script's publish step on a changelog. Returns (error text or None, output, fake).

    pending is the set of commits on main whose changelog heads the version they name "(unreleased)".
    """
    github = github if github is not None else FakeGitHub()
    history = history if history is not None else made_up_history(text, version, sha)
    out = io.StringIO()
    options = {"report": True} if report else {}
    if pending is not None:
        options["pending"] = frozenset(pending)
    try:
        release.publish(version, text, history, REPO, sha, github, out, **options)
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
        self.assertIn('the tag "refs/tags/v0.4-rc": the version "0.4-rc" ' + FORM, error)
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
        self.assertEqual(error, tag_unconfirmed("GET %s/git/ref/tags/v0.4: read back, the tag v0.4 does not point at %s" % (PATH, SHA), SHA)[9:-1])

    def test_a_created_tag_that_the_answer_puts_elsewhere_gets_no_release(self):
        class Elsewhere(FakeGitHub):
            def __call__(self, method, path, body=None):
                status, data = FakeGitHub.__call__(self, method, path, body)
                if method == "POST" and path.endswith("/git/refs"):
                    data = dict(data, object={"type": "commit", "sha": OTHER})
                return status, data
        github = Elsewhere(**DONE_03)
        error, _, github = publish(TWO, github=github)
        self.assertEqual(error, "POST %s/git/refs: the answer does not say that the tag v0.4 points at %s. Ratchet 0.4 is not finished: "
                                "the tag v0.4 was created, and there is no release. Look at the tag by hand. If it points at commit %s, "
                                "rerun the release run of that commit: it creates only the release." % (PATH, SHA, SHA))
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

    # Round 1 of release-links, finding 3: the answer to the publication is checked, and the list of releases is read to its end.

    def test_an_answer_to_the_publication_that_is_not_a_published_release_fails(self):
        answers = (
            lambda data: dict(data, draft=True),
            lambda data: dict(data, draft=None),
            lambda data: dict(data, tag_name="v0.5"),
            lambda data: dict((k, v) for k, v in data.items() if k != "tag_name"),
            lambda data: [data],
            lambda data: None,
        )
        for index, change in enumerate(answers):
            class Changed(FakeGitHub):
                def __call__(self, method, path, body=None):
                    status, data = FakeGitHub.__call__(self, method, path, body)
                    if method == "POST" and path == PATH + "/releases":
                        data = change(data)
                    return status, data
            with self.subTest(answer=index):
                error, out, github = publish(TWO, github=Changed(**DONE_03))
                self.assertEqual(error, release_missing("POST %s/releases: the answer is not a published release for v0.4" % PATH, SHA)[9:-1])
                self.assertEqual(out, "")
                self.assertNotIn(("GET", PATH + "/git/ref/tags/v0.4"), [call[:2] for call in github.calls])

    def test_the_list_of_releases_is_read_past_its_first_page(self):
        # 100 releases of newer versions fill the first page. The release of 0.3 is on the second.
        newer = [{"tag_name": "v1.%d" % n, "draft": False} for n in range(100)]
        for releases, pages in ((newer + DONE_03["releases"], 2), (newer[:98] + DONE_03["releases"], 1),
                                (newer[:99] + DONE_03["releases"], 2),
                                (newer + newer + DONE_03["releases"], 3), (newer[:50] + DONE_03["releases"] + newer[:50], 2)):
            with self.subTest(releases=len(releases)):
                error, _, github = publish(TWO, github=FakeGitHub(tags=DONE_03["tags"], releases=releases))
                self.assertIsNone(error)
                read = [path for method, path, _ in github.calls if path.startswith(PATH + "/releases?")]
                self.assertEqual(read, [PATH + "/releases?per_page=100&page=%d" % n for n in range(1, pages + 1)])
        # A release for this version on the second page is found, and no second one is made.
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", SHA)},
                            releases=newer + DONE_03["releases"] + [{"tag_name": "v0.4", "draft": False}])
        error, out, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [])
        self.assertIn("v0.4 is tagged at this commit and released. Nothing to do", out)

    def test_a_list_of_releases_with_no_end_fails_and_writes_nothing(self):
        class Endless(FakeGitHub):
            def __call__(self, method, path, body=None):
                if method == "GET" and path.startswith(PATH + "/releases?"):
                    self.calls.append((method, path, body))
                    return 200, [{"tag_name": "v9.%d" % n, "draft": False} for n in range(100)]
                return FakeGitHub.__call__(self, method, path, body)
        error, _, github = publish(TWO, github=Endless(**DONE_03))
        self.assertEqual(error, "GET %s/releases: more than 100 pages. Nothing was written." % PATH)
        self.assertEqual(github.writes, [])

    # Round 1 of release-links, finding 4: the message names the commit whose run to rerun.

    def test_an_older_version_without_a_tag_names_the_first_commit_that_raised_the_version(self):
        first, then = commit_of("0.4"), "e" * 40
        history = [(LATER, "0.5"), (then, "0.4"), (first, "0.4"), (EARLIER, "0.3")]
        error, _, github = publish(THREE, version="0.5", github=FakeGitHub(**DONE_03), sha=LATER, history=history)
        self.assertEqual(error, "an older version is not finished. 0.4: no tag. Rerun the release run of commit %s, "
                                "the first commit on main whose ratchet.json names 0.4. Then rerun this run. Nothing was written." % first)
        self.assertEqual(github.writes, [])

    def test_an_older_version_with_a_tag_names_the_commit_the_tag_points_at(self):
        # The run of the first commit with 0.4 was replaced, and a later commit with 0.4 made the tag.
        first, tagged = commit_of("0.4"), "e" * 40
        history = [(LATER, "0.5"), (tagged, "0.4"), (first, "0.4"), (EARLIER, "0.3")]
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", tagged)}, releases=DONE_03["releases"])
        error, _, github = publish(THREE, version="0.5", github=github, sha=LATER, history=history)
        self.assertEqual(error, "an older version is not finished. 0.4: a tag and no published release. Rerun the release run of commit %s, "
                                "which the tag points at. Then rerun this run. Nothing was written." % tagged)
        self.assertNotIn(first, error)
        # That rerun finishes 0.4, and then the run of 0.5 releases 0.5.
        github.calls = []
        error, out, github = publish(TWO, github=github, sha=tagged, history=history[1:])
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/releases")])
        github.calls = []
        error, out, github = publish(THREE, version="0.5", github=github, sha=LATER, history=history)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs"), ("POST", PATH + "/releases")])

    def test_an_older_version_whose_tag_is_not_a_plain_tag_is_looked_at_by_hand(self):
        github = FakeGitHub(tags={"0.3": ("tag", EARLIER)})
        error, _, github = publish(TWO, github=github)
        self.assertIn("0.3: a tag and no published release. The tag is not a plain tag of a commit: look at it by hand.", error)
        self.assertEqual(github.writes, [])

    def test_this_version_tagged_at_another_commit_names_that_commit(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", OTHER)}, releases=DONE_03["releases"])
        error, _, github = publish(TWO, github=github)
        self.assertEqual(error, "the tag v0.4 points at another commit than this one, and has no published release. The tag is not moved. "
                                "Rerun the release run of commit %s, which the tag points at. Nothing was written." % OTHER)
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
    environ = {"GITHUB_TOKEN": TOKEN, "GITHUB_REPOSITORY": REPO, "GITHUB_SHA": SHA, "GITHUB_REF": MAIN, "GITHUB_EVENT_NAME": "push"}
    environ.update(changes)
    return dict((k, v) for k, v in environ.items() if v is not None)


def run_main(github, argv=("publish",), environ=None, root=None):
    opener = FakeOpener(github)
    out, err = io.StringIO(), io.StringIO()
    code = release.main(list(argv), environ=environ if environ is not None else environment(), opener=opener, out=out, err=err, root=root)
    return code, out.getvalue(), err.getvalue(), opener


# No automatic gc or maintenance in a repository a test makes. git starts them in the background after a commit or a
# fetch, and one still writing in .git is a likely, not a proven, cause of an intermittent "could not parse HEAD" and
# of a removal that finds .git/objects/pack not empty. For this call, and, for init and clone, in the new repository's
# own config, so that a script under test that runs git there starts none either.
QUIET = (("gc.auto", "0"), ("maintenance.auto", "false"))


def git(directory, *args, **kwargs):
    """Run git in a repository that a test made, with no config of the user and no GIT_ variable of the environment."""
    args = quiet_args(args)
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CEILING_DIRECTORIES=os.path.dirname(os.path.realpath(directory)),
               GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.invalid", GIT_COMMITTER_NAME="Test",
               GIT_COMMITTER_EMAIL="test@example.invalid", LC_ALL="C")
    result = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"] + quiet_options() + ["-C", directory]
                            + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, universal_newlines=True, **kwargs)
    if result.returncode:
        raise AssertionError("git %s: %s" % (" ".join(args), result.stderr))
    if args[:1] == ("init",):
        for name, value in QUIET:
            git(directory, "config", name, value)
    return result.stdout.strip()


def quiet_options():
    """-c for each setting of QUIET, for one call of git."""
    return [part for name, value in QUIET for part in ("-c", "%s=%s" % (name, value))]


def quiet_args(args):
    """args, with each setting of QUIET written into the config of the repository that a clone makes."""
    args = tuple(args)
    if args[:1] == ("clone",):
        return args[:1] + tuple(part for name, value in QUIET for part in ("--config", "%s=%s" % (name, value))) + args[1:]
    return args


class Checkout:
    """A git repository in a temporary directory, made by a test, that stands in for a checkout of main.

    Each commit writes ratchet.json, today's with another version, and CHANGELOG.md.
    """

    def __init__(self):
        self.directory = tempfile.mkdtemp()
        with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as handle:
            self.data = json.load(handle)
        for rule in self.data["rules"]:
            if "reference_check" in rule:
                target = os.path.join(self.directory, rule["reference_check"])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                open(target, "w").close()
        git(self.directory, "init", "-q")

    def write(self, name, data):
        with open(os.path.join(self.directory, name), "wb") as handle:
            handle.write(data)

    def ratchet_json(self, version):
        return (json.dumps(dict(self.data, version=version), indent=2) + "\n").encode("utf-8")

    def commit(self, version=None, text=None, raw=None, remove=False, message="A commit"):
        """Commit ratchet.json with this version (or these bytes, or without it) and this changelog. Returns the commit."""
        if remove:
            os.remove(os.path.join(self.directory, "ratchet.json"))
        elif raw is not None:
            self.write("ratchet.json", raw)
        elif version is not None:
            self.write("ratchet.json", self.ratchet_json(version))
        if text is not None:
            self.write("CHANGELOG.md", text.encode("utf-8"))
        git(self.directory, "add", "-A")
        git(self.directory, "commit", "-q", "--allow-empty", "-m", message)
        return git(self.directory, "rev-parse", "HEAD")

    def history(self, sha=None):
        return release.main_history(self.directory, sha or git(self.directory, "rev-parse", "HEAD"))

    def run(self, github, sha=None):
        return run_main(github, environ=environment(GITHUB_SHA=sha or git(self.directory, "rev-parse", "HEAD")), root=self.directory)

    def close(self):
        shutil.rmtree(self.directory)


class MainHistory(unittest.TestCase):
    """Round 1 of release-links, finding 1: the versions that must be released come from the history of main, not from the changelog.

    A pull request can edit CHANGELOG.md. It cannot edit a commit that is already on main, because the ruleset
    on main refuses a force-push and a deletion. So every version that ratchet.json has named on main is read
    with git from the first-parent history of the commit being released, and each older one needs its tag and its release.
    """

    def setUp(self):
        self.checkout = Checkout()

    def tearDown(self):
        self.checkout.close()

    def test_a_version_on_main_that_was_never_released_fails_although_the_changelog_no_longer_shows_it(self):
        # 0.4 was merged and never tagged. The pull request of 0.5 takes 0.4's heading out of the exact form, or the entry out.
        five = "# Changelog\n\n## 0.5 (2026-11-17)\n\nFive.\n\n%s\n\n## 0.3 (2026-11-16)\n\nThree.\n"
        for hidden in (" ## 0.4 (2026-11-17)\n\nFour.", "- ## 0.4 (2026-11-17)\n\nFour.", "## 0.4  (2026-11-17)\n\nFour.", "Four."):
            with self.subTest(hidden=hidden):
                checkout = Checkout()
                self.addCleanup(checkout.close)
                checkout.commit("0.3", changelog(("0.3", "Three.")))
                four = checkout.commit("0.4", changelog(("0.4", "Four."), ("0.3", "Three.")))
                head = checkout.commit("0.5", five % hidden)
                github = FakeGitHub(**DONE_03)
                code, out, err, _ = checkout.run(github, head)
                self.assertEqual(code, 1)
                self.assertEqual(err, "release: an older version is not finished. 0.4: no tag. Rerun the release run of commit %s, "
                                      "the first commit on main whose ratchet.json names 0.4. Then rerun this run. Nothing was written.\n" % four)
                self.assertEqual(github.writes, [])
                self.assertNotIn("0.5", github.tags)

    def test_the_same_history_releases_05_once_04_is_released(self):
        self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        four = self.checkout.commit("0.4", changelog(("0.4", "Four."), ("0.3", "Three.")))
        head = self.checkout.commit("0.5", THREE)
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", four)},
                            releases=DONE_03["releases"] + [{"tag_name": "v0.4", "draft": False}])
        code, out, err, _ = self.checkout.run(github, head)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.tags["0.5"], ("commit", head))

    def test_the_history_is_every_commit_on_the_first_parent_line_that_holds_ratchet_json(self):
        self.checkout.write("README.md", b"Before ratchet.json.\n")
        self.checkout.commit(message="No ratchet.json yet")
        three = self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        again = self.checkout.commit(text=changelog(("0.3", "Three, again.")))
        four = self.checkout.commit("0.4", TWO)
        self.assertEqual(self.checkout.history(), [(four, "0.4"), (again, "0.3"), (three, "0.3")])

    def test_a_version_only_on_a_branch_merged_into_main_is_not_counted(self):
        self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        git(self.checkout.directory, "checkout", "-q", "-b", "side")
        side = self.checkout.commit("0.9", changelog(("0.9", "Nine.")))
        git(self.checkout.directory, "checkout", "-q", "main")
        four = self.checkout.commit("0.4", TWO)
        git(self.checkout.directory, "merge", "-q", "-s", "ours", "--no-ff", "-m", "Merge side, keeping main", "side")
        merge = git(self.checkout.directory, "rev-parse", "HEAD")
        history = self.checkout.history()
        self.assertEqual([v for _, v in history], ["0.4", "0.4", "0.3"])
        self.assertEqual(history[:2], [(merge, "0.4"), (four, "0.4")])
        self.assertNotIn(side, [c for c, _ in history])

    def test_a_merge_commit_that_raises_the_version_is_the_first_commit_on_main_with_it(self):
        three = self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        git(self.checkout.directory, "checkout", "-q", "-b", "side")
        self.checkout.commit("0.4", TWO)
        git(self.checkout.directory, "checkout", "-q", "main")
        git(self.checkout.directory, "merge", "-q", "--no-ff", "-m", "Merge the pull request of 0.4", "side")
        merge = git(self.checkout.directory, "rev-parse", "HEAD")
        head = self.checkout.commit("0.5", THREE)
        self.assertEqual(self.checkout.history(), [(head, "0.5"), (merge, "0.4"), (three, "0.3")])
        code, _, err, _ = self.checkout.run(FakeGitHub(**DONE_03))
        self.assertEqual(code, 1)
        self.assertIn("0.4: no tag. Rerun the release run of commit %s," % merge, err)

    def test_a_shallow_checkout_fails(self):
        self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        self.checkout.commit("0.4", TWO)
        shallow = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, shallow)
        git(shallow, "clone", "-q", "--depth", "1", "file://" + self.checkout.directory, "copy")
        copy = os.path.join(shallow, "copy")
        with self.assertRaises(release.ReleaseError) as caught:
            release.main_history(copy, git(copy, "rev-parse", "HEAD"))
        self.assertEqual(str(caught.exception), "the checkout is shallow: the release reads the whole history of main, "
                                                "so the workflow checks out with fetch-depth: 0. Nothing was written.")

    def test_a_directory_that_is_not_a_repository_fails(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        with self.assertRaises(release.ReleaseError) as caught:
            release.main_history(directory, SHA)
        self.assertIn("git rev-parse: exit", str(caught.exception))

    def test_the_checkout_must_be_at_the_commit_being_released(self):
        three = self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        self.checkout.commit("0.4", TWO)
        for sha in (three, SHA):
            with self.subTest(sha=sha):
                with self.assertRaises(release.ReleaseError) as caught:
                    self.checkout.history(sha)
                self.assertEqual(str(caught.exception), "the checkout is not at GITHUB_SHA %s. Nothing was written." % sha)

    def test_ratchet_json_at_an_earlier_commit_is_read_strictly(self):
        good = self.checkout.ratchet_json("0.3")
        cases = (
            (good.replace(b'"version": "0.3"', b'"version": "0.3", "version": "0.2"'), "appears twice"),
            (good.replace(b'"version": "0.3"', b'"version": NaN'), "NaN is not allowed"),
            (good.replace(b"0.3", b"\xff0.3", 1), "is not valid UTF-8"),
            (b"\xef\xbb\xbf" + good, "not a valid data file"),
            (good[:-10], "not a valid data file"),
            (good.replace(b'"version": "0.3"', b'"version": "0.3.1"'), 'the version "0.3.1" ' + FORM),
            (good.replace(b'"version": "0.3"', b'"version": "\xd9\xa0.3"'), 'the version "\\u0660.3" ' + FORM),
            (good.replace(b'"version": "0.3"', b'"version": 0.3'), "the version 0.3 " + FORM),
            (good.replace(b'"version": "0.3"', b'"release": "0.3"'), "has no version"),
            (b'["0.3"]\n', "has no version"),
        )
        for raw, problem in cases:
            with self.subTest(problem=problem, raw=raw[:40]):
                checkout = Checkout()
                self.addCleanup(checkout.close)
                bad = checkout.commit(raw=raw)
                checkout.commit("0.4", TWO)
                with self.assertRaises(release.ReleaseError) as caught:
                    checkout.history()
                self.assertIn("ratchet.json at commit %s on main" % bad, str(caught.exception))
                self.assertIn(problem, str(caught.exception))
                self.assertIn("Nothing was written", str(caught.exception))

    def test_ratchet_json_removed_from_main_and_added_again_fails(self):
        three = self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        gone = self.checkout.commit(remove=True)
        self.checkout.commit("0.4", TWO)
        with self.assertRaises(release.ReleaseError) as caught:
            self.checkout.history()
        self.assertEqual(str(caught.exception), "ratchet.json is missing at commit %s on main, and the earlier commit %s holds it. "
                                                "Nothing was written." % (gone, three))

    def test_a_version_on_main_newer_than_the_one_being_released_fails(self):
        self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        five = self.checkout.commit("0.5", THREE)
        self.checkout.commit("0.4", TWO)
        github = FakeGitHub(**DONE_03)
        code, _, err, _ = self.checkout.run(github)
        self.assertEqual(code, 1)
        self.assertEqual(err, "release: ratchet.json at commit %s on main names 0.5, newer than 0.4. Nothing was written.\n" % five)
        self.assertEqual(github.calls, [])

    def test_the_checkout_must_name_the_version_that_its_commit_names(self):
        self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        head = self.checkout.commit("0.4", TWO)
        self.checkout.write("ratchet.json", self.checkout.ratchet_json("0.5"))
        self.checkout.write("CHANGELOG.md", THREE.encode("utf-8"))
        github = FakeGitHub(**DONE_03)
        code, _, err, _ = self.checkout.run(github)
        self.assertEqual(code, 1)
        self.assertEqual(err, "release: ratchet.json in the checkout names 0.5, and at commit %s it names 0.4. Nothing was written.\n" % head)
        self.assertEqual(github.calls, [])

    def test_git_variables_of_the_environment_do_not_change_what_is_read(self):
        self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        four = self.checkout.commit("0.4", TWO)
        other = Checkout()
        self.addCleanup(other.close)
        other.commit("0.9", changelog(("0.9", "Nine.")))
        variables = {"GIT_DIR": os.path.join(other.directory, ".git"), "GIT_WORK_TREE": other.directory,
                     "GIT_INDEX_FILE": os.path.join(other.directory, ".git", "index"), "GIT_REPLACE_REF_BASE": "refs/other/"}
        with mock.patch.dict(os.environ, variables):
            self.assertEqual([v for _, v in self.checkout.history(four)], ["0.4", "0.3"])


# D-2026-11-17-release-narrow-claim: the six spellings of 0.4 that review round 2 of release-links and the decision name.
NOT_A_VERSION = ("00.4", "0.04", "+0.4", " 0.4", "0.4 ", "٠.٤")
FORM = "is not of the form MAJOR.MINOR, in ASCII digits with no leading zero. Nothing was written."


def not_a_version(where, value):
    """The message for a version of another form, written out here and not taken from the script."""
    return "%s: the version %s %s" % (where, json.dumps(value), FORM)


class StrictVersions(unittest.TestCase):
    """Round 2 of release-links, finding 2, and D-2026-11-17-release-narrow-claim: every version has one form.

    A version is read from ratchet.json in the checkout, from ratchet.json at each commit on main, from the tags and
    from the headings of the changelog. Each must match ^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$, or the run fails and names
    the value and where it came from. Versions are compared as pairs of integers.
    """

    def checkout(self):
        checkout = Checkout()
        self.addCleanup(checkout.close)
        return checkout

    def test_a_version_of_another_form_in_the_checkout_fails_before_any_request(self):
        for value in NOT_A_VERSION:
            with self.subTest(value=value):
                checkout = self.checkout()
                checkout.commit("0.3", changelog(("0.3", "Three.")))
                checkout.write("ratchet.json", checkout.ratchet_json(value))
                github = FakeGitHub(**DONE_03)
                code, _, err, _ = checkout.run(github)
                self.assertEqual((code, err), (1, "release: %s\n" % not_a_version("ratchet.json in the checkout", value)))
                self.assertEqual(github.calls, [])
                out, err = io.StringIO(), io.StringIO()
                code = release.main(["notes", "--repo", REPO], environ={}, opener=None, out=out, err=err, root=checkout.directory)
                self.assertEqual((code, out.getvalue()), (1, ""))
                self.assertEqual(err.getvalue(), "release: %s\n" % not_a_version("ratchet.json in the checkout", value))

    def test_a_version_of_another_form_at_a_commit_on_main_fails_and_names_the_commit(self):
        for value in NOT_A_VERSION:
            with self.subTest(value=value):
                checkout = self.checkout()
                checkout.commit("0.3", changelog(("0.3", "Three.")))
                odd = checkout.commit(value, TWO)
                checkout.commit("0.4", TWO)
                with self.assertRaises(release.ReleaseError) as caught:
                    checkout.history()
                self.assertEqual(str(caught.exception), not_a_version("ratchet.json at commit %s on main" % odd, value))

    def test_the_history_03_04_004_fails_on_004_and_writes_nothing(self):
        # The reviewer's history: 0.4 is merged and never tagged, then 00.4. It released v00.4 and named nothing.
        checkout = self.checkout()
        checkout.commit("0.3", changelog(("0.3", "Three.")))
        checkout.commit("0.4", TWO)
        head = checkout.commit("00.4", changelog(("00.4", "Alias."), ("0.4", "Four."), ("0.3", "Three.")))
        github = FakeGitHub(**DONE_03)
        code, out, err, _ = checkout.run(github, head)
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(err, "release: %s\n" % not_a_version("ratchet.json in the checkout", "00.4"))
        self.assertEqual(github.writes, [])
        self.assertEqual(sorted(github.tags), ["0.3"])

    def test_a_tag_of_another_form_fails_and_is_named(self):
        for value in NOT_A_VERSION + ("0.4-rc",):
            with self.subTest(value=value):
                github = FakeGitHub(tags={"0.3": ("commit", EARLIER), value: ("commit", EARLIER)}, releases=DONE_03["releases"])
                error, _, github = publish(TWO, github=github)
                where = "GET %s/git/matching-refs/tags/v, the tag %s" % (PATH, json.dumps("refs/tags/v" + value))
                self.assertEqual(error, not_a_version(where, value))
                self.assertEqual(github.writes, [])

    def test_a_heading_with_a_leading_zero_fails_and_names_its_line(self):
        for value in ("00.4", "0.04"):
            with self.subTest(value=value):
                text = changelog(("0.4", "Four."), (value, "Alias."), ("0.3", "Three."))
                with self.assertRaises(release.ReleaseError) as caught:
                    release.changelog_versions(text)
                self.assertEqual(str(caught.exception), not_a_version("CHANGELOG.md, line 7", value))
                error, _, github = publish(text, github=FakeGitHub(**DONE_03), history=[(SHA, "0.4"), (commit_of("0.3"), "0.3")])
                self.assertEqual(error, not_a_version("CHANGELOG.md, line 7", value))
                self.assertEqual(github.calls, [])

    def test_versions_are_compared_as_pairs_of_integers(self):
        self.assertEqual(release.version_key("0.10"), (0, 10))
        self.assertGreater(release.version_key("0.10"), release.version_key("0.9"))
        self.assertGreater(release.version_key("10.0"), release.version_key("9.12"))

    def test_09_then_010_releases_010(self):
        checkout = self.checkout()
        checkout.commit("0.3", changelog(("0.3", "Three.")))
        nine = checkout.commit("0.9", changelog(("0.9", "Nine."), ("0.3", "Three.")))
        head = checkout.commit("0.10", changelog(("0.10", "Ten."), ("0.9", "Nine."), ("0.3", "Three.")))
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.9": ("commit", nine)},
                            releases=DONE_03["releases"] + [{"tag_name": "v0.9", "draft": False}])
        code, out, err, _ = checkout.run(github, head)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.tags["0.10"], ("commit", head))
        self.assertEqual(github.releases[-1]["body"], release_line("0.10"))

    def test_09_unfinished_stops_010(self):
        checkout = self.checkout()
        checkout.commit("0.3", changelog(("0.3", "Three.")))
        nine = checkout.commit("0.9", changelog(("0.9", "Nine."), ("0.3", "Three.")))
        head = checkout.commit("0.10", changelog(("0.10", "Ten."), ("0.9", "Nine."), ("0.3", "Three.")))
        github = FakeGitHub(**DONE_03)
        code, _, err, _ = checkout.run(github, head)
        self.assertEqual(code, 1)
        self.assertIn("0.9: no tag. Rerun the release run of commit %s," % nine, err)
        self.assertEqual(github.writes, [])

    def test_a_tag_named_with_the_token_is_not_printed(self):
        # A tag name comes from an answer of the API and is now named in a message. The token is taken out of every message.
        checkout = self.checkout()
        checkout.commit("0.3", changelog(("0.3", "Three.")))
        checkout.commit("0.4", TWO)
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), TOKEN: ("commit", EARLIER)}, releases=DONE_03["releases"])
        code, out, err, _ = checkout.run(github)
        self.assertEqual(code, 1)
        self.assertNotIn(TOKEN, out + err)
        self.assertNotIn(TOKEN[4:20], out + err)
        self.assertIn("the tag \"refs/tags/v[the token]\"", err)


class Substitutes(unittest.TestCase):
    """Round 2 of release-links, finding 1, and D-2026-11-17-release-narrow-claim: a checkout that swaps objects is refused.

    Before any history is read, the run fails when the checkout has .git/info/grafts, a ref under refs/replace/,
    .git/shallow or .git/objects/info/alternates. Each test shows first that the file or the ref changes what git
    reads, or that the reading ignores it, and then that the run refuses it.
    """

    def setUp(self):
        self.checkout = Checkout()
        self.git_dir = os.path.join(self.checkout.directory, ".git")
        self.three = self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        self.four = self.checkout.commit("0.4", TWO)
        self.head = self.checkout.commit("0.5", THREE)

    def tearDown(self):
        self.checkout.close()

    def refused(self, message):
        with self.assertRaises(release.ReleaseError) as caught:
            self.checkout.history(self.head)
        self.assertEqual(str(caught.exception), message)
        github = FakeGitHub(**DONE_03)
        code, _, err, _ = self.checkout.run(github, self.head)
        self.assertEqual((code, err), (1, "release: %s\n" % message))
        self.assertEqual(github.calls, [])

    def test_a_graft_file_is_refused(self):
        # The reviewer's probe: a graft makes 0.3 the parent of 0.5, and 0.4 is gone from the history.
        with open(os.path.join(self.git_dir, "info", "grafts"), "w") as handle:
            handle.write("%s %s\n" % (self.head, self.three))
        self.assertEqual(git(self.checkout.directory, "rev-list", "--first-parent", self.head).split(), [self.head, self.three])
        self.refused("the checkout has .git/info/grafts, which changes the parents git reads. Nothing was written.")

    def test_the_reading_ignores_a_graft_file_and_graft_variables(self):
        with open(os.path.join(self.git_dir, "info", "grafts"), "w") as handle:
            handle.write("%s %s\n" % (self.head, self.three))
        other = os.path.join(self.checkout.directory, "other-grafts")
        with open(other, "w") as handle:
            handle.write("%s %s\n" % (self.head, self.three))
        with mock.patch.dict(os.environ, {"GIT_GRAFT_FILE": other}):
            self.assertEqual(release.read_history(self.checkout.directory, self.head),
                             [(self.head, "0.5"), (self.four, "0.4"), (self.three, "0.3")])

    def test_a_replace_ref_is_refused(self):
        # A replace ref swaps the commit of 0.4 for one that names 0.3.
        git(self.checkout.directory, "checkout", "-q", "--detach", self.three)
        fake = self.checkout.commit("0.3", TWO, message="Not on main")
        git(self.checkout.directory, "checkout", "-q", "main")
        git(self.checkout.directory, "replace", self.four, fake)
        self.assertEqual(release.read_history(self.checkout.directory, self.head),
                         [(self.head, "0.5"), (self.four, "0.4"), (self.three, "0.3")])
        self.refused("the checkout has the replace ref %s, which swaps one object for another. Nothing was written."
                     % json.dumps("refs/replace/" + self.four))

    def test_a_packed_replace_ref_is_refused(self):
        git(self.checkout.directory, "replace", self.four, self.three)
        git(self.checkout.directory, "pack-refs", "--all")
        self.assertFalse(os.path.exists(os.path.join(self.git_dir, "refs", "replace", self.four)))
        self.refused("the checkout has the replace ref %s, which swaps one object for another. Nothing was written."
                     % json.dumps("refs/replace/" + self.four))

    def test_a_shallow_file_is_refused_also_when_empty(self):
        # .git/shallow cuts the history at the commits it names, in a clone that holds the whole history.
        shallow = os.path.join(self.git_dir, "shallow")
        with open(shallow, "w") as handle:
            handle.write("%s\n" % self.four)
        self.assertEqual(release.read_history(self.checkout.directory, self.head), [(self.head, "0.5"), (self.four, "0.4")])
        message = ("the checkout is shallow: the release reads the whole history of main, "
                   "so the workflow checks out with fetch-depth: 0. Nothing was written.")
        self.refused(message)
        open(shallow, "w").close()
        self.refused(message)

    def test_an_alternates_file_is_refused(self):
        # An object store named in alternates stands in for an object the checkout lacks, and git does not check its hash
        # when it reads it. The blob of ratchet.json at 0.4 is taken out of the checkout, and another store holds, under
        # its name, the bytes of a ratchet.json that names 0.3. Then 0.4 is gone from the history.
        blob = git(self.checkout.directory, "rev-parse", "%s:ratchet.json" % self.four)
        os.remove(os.path.join(self.git_dir, "objects", blob[:2], blob[2:]))
        store = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, store)
        data = self.checkout.ratchet_json("0.3")
        os.makedirs(os.path.join(store, blob[:2]))
        with open(os.path.join(store, blob[:2], blob[2:]), "wb") as handle:
            handle.write(zlib.compress(b"blob %d\0" % len(data) + data))
        with open(os.path.join(self.git_dir, "objects", "info", "alternates"), "w") as handle:
            handle.write(store + "\n")
        self.assertEqual(release.read_history(self.checkout.directory, self.head),
                         [(self.head, "0.5"), (self.four, "0.3"), (self.three, "0.3")])
        self.refused("the checkout has .git/objects/info/alternates, which reads objects from another store. Nothing was written.")

    def test_an_empty_alternates_file_is_refused(self):
        open(os.path.join(self.git_dir, "objects", "info", "alternates"), "w").close()
        self.refused("the checkout has .git/objects/info/alternates, which reads objects from another store. Nothing was written.")


API_URL = "https://api.github.com"
KINDS = ("transport", "exception", "http", "not-json", "form")


class Failing(FakeOpener):
    """Fails one request in one way, and answers every other from the fake.

    transport: no answer (urllib's URLError). exception: an error the script does not expect (RuntimeError).
    http: HTTP 500. not-json: an answer that is not JSON. form: JSON of the wrong form.
    lost: the request reaches the fake, and then its answer is lost. not-json and form always reach it.
    """

    def __init__(self, github, method, path, kind, lost=False):
        FakeOpener.__init__(self, github)
        self.target, self.kind, self.lost = (method, path), kind, lost

    def open(self, request, timeout=None):
        method, path = request.get_method(), request.full_url[len(API_URL):]
        if (method, path) != self.target:
            return FakeOpener.open(self, request, timeout)
        self.requests.append(request)
        body = json.loads(request.data.decode("utf-8")) if request.data else None
        if self.lost or self.kind in ("not-json", "form"):
            status, _ = self.github(method, path, body)
        else:
            self.github.calls.append((method, path, body))
            status = 201 if method == "POST" else 200
        if self.kind == "transport":
            raise urllib.error.URLError("synthetic: no answer")
        if self.kind == "exception":
            raise RuntimeError("synthetic: an error the script does not expect")
        if self.kind == "http":
            raise urllib.error.HTTPError(request.full_url, 500, "error", {}, io.BytesIO(TOKEN.encode()))
        answer = Response(status, None)
        answer.raw = b"<html>not JSON</html>" if self.kind == "not-json" else b'["not", "an", "object"]'
        return answer


def main_with(opener, sha, root, event="push"):
    out, err = io.StringIO(), io.StringIO()
    code = release.main(["publish"], environ=environment(GITHUB_SHA=sha, GITHUB_EVENT_NAME=event), opener=opener,
                        out=out, err=err, root=root)
    return code, out.getvalue(), err.getvalue()


def release_missing(cause, sha, version="0.4"):
    """The one message of a failure after the tag is at sha and before its release is confirmed."""
    return ("release: %s. Ratchet %s is not finished: the tag v%s points at commit %s, and its release is missing or was not confirmed. "
            "Rerun the release run of commit %s, which the tag points at: it creates the release if it is missing, and writes nothing else.\n"
            % (cause, version, version, sha, sha))


def tag_unconfirmed(cause, sha, version="0.4"):
    """The one message of a failure after the release is created and before its tag is read back."""
    return ("release: %s. Ratchet %s is not finished: its release was created, and the tag v%s was not confirmed at commit %s. "
            "Rerun the release run of commit %s: it writes nothing if the release is there, and it is green only if the tag points at that commit.\n"
            % (cause, version, version, sha, sha))


def tag_maybe(cause, sha, version="0.4"):
    """The one message of a failure of the creation of the tag that may have created it."""
    return ("release: %s. Ratchet %s is not finished: the tag v%s may have been created at commit %s, and there is no release. "
            "Rerun the release run of commit %s: it creates the tag if it is missing, then the release.\n" % (cause, version, version, sha, sha))


class AfterTheTag(unittest.TestCase):
    """Round 1 of the narrowed claim, finding 2: every failure after the tag is created ends in one message.

    It names the version and the commit the tag points at, says what is missing, and gives the rerun.
    Each kind of failure is tried at each request after the tag: no answer, an error the script does not
    expect, an HTTP error, an answer that is not JSON, and an answer of the wrong form.
    """

    def setUp(self):
        self.checkout = Checkout()
        self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        self.four = self.checkout.commit("0.4", TWO)

    def tearDown(self):
        self.checkout.close()

    def run_failing(self, github, method, path, kind, lost=False):
        return main_with(Failing(github, method, path, kind, lost), self.four, self.checkout.directory)

    def schedule(self, github):
        return main_with(FakeOpener(github), self.four, self.checkout.directory, event="schedule")

    def test_a_failure_of_the_publication_names_the_version_the_commit_and_the_rerun(self):
        path = PATH + "/releases"
        causes = {
            "transport": "POST %s: no answer" % path,
            "exception": "POST %s: an unexpected error (RuntimeError)" % path,
            "http": "POST %s: HTTP 500" % path,
            "not-json": "POST %s: HTTP 201, and the answer is not JSON" % path,
            "form": "POST %s: the answer is not a published release for v0.4" % path,
        }
        for kind in KINDS:
            for tagged in (False, True):
                with self.subTest(kind=kind, tagged_before=tagged):
                    github = FakeGitHub(**DONE_03)
                    if tagged:
                        github.tags["0.4"] = ("commit", self.four)
                    code, out, err = self.run_failing(github, "POST", path, kind)
                    self.assertEqual((code, out), (1, ""))
                    self.assertEqual(err, release_missing(causes[kind], self.four))
                    self.assertEqual(github.tags["0.4"], ("commit", self.four))
                    self.assertNotIn(TOKEN, err)
                    if kind in ("not-json", "form"):
                        continue  # The release reached the fake; the rerun below is for those that did not.
                    # The next scheduled run names the version, and writes nothing. The rerun finishes it.
                    github.calls = []
                    code, out, err = self.schedule(github)
                    self.assertEqual(code, 1)
                    self.assertIn("Ratchet 0.4 is not finished: the tag v0.4 points at commit %s" % self.four, err)
                    self.assertEqual(github.writes, [])
                    code, out, err, _ = self.checkout.run(github, self.four)
                    self.assertEqual((code, err), (0, ""))
                    self.assertEqual(github.writes, [("POST", path)])

    def test_a_publication_whose_answer_is_lost_is_found_by_the_rerun(self):
        path = PATH + "/releases"
        for kind in ("transport", "exception", "http"):
            with self.subTest(kind=kind):
                github = FakeGitHub(**DONE_03)
                code, out, err = self.run_failing(github, "POST", path, kind, lost=True)
                self.assertEqual(code, 1)
                self.assertIn("Ratchet 0.4 is not finished: the tag v0.4 points at commit %s, and its release is missing or was not confirmed"
                              % self.four, err)
                self.assertEqual(len([r for r in github.releases if r["tag_name"] == "v0.4"]), 1)
                github.calls = []
                code, out, err = self.schedule(github)
                self.assertEqual((code, err), (0, ""))
                code, out, err, _ = self.checkout.run(github, self.four)
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(github.writes, [])
                self.assertIn("v0.4 is tagged at this commit and released. Nothing to do", out)

    def test_a_failure_of_the_read_back_says_that_the_release_was_created(self):
        path = PATH + "/git/ref/tags/v0.4"
        causes = {
            "transport": "GET %s: no answer" % path,
            "exception": "GET %s: an unexpected error (RuntimeError)" % path,
            "http": "GET %s: HTTP 500" % path,
            "not-json": "GET %s: HTTP 200, and the answer is not JSON" % path,
            "form": "GET %s: read back, the tag v0.4 does not point at %s" % (path, self.four),
        }
        for kind in KINDS:
            with self.subTest(kind=kind):
                github = FakeGitHub(**DONE_03)
                code, out, err = self.run_failing(github, "GET", path, kind)
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(err, tag_unconfirmed(causes[kind], self.four))
                github.calls = []
                code, out, err, _ = self.checkout.run(github, self.four)
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(github.writes, [])

    def test_a_creation_of_the_tag_that_may_have_written_it_says_so(self):
        path = PATH + "/git/refs"
        causes = {
            "transport": "POST %s: no answer" % path,
            "exception": "POST %s: an unexpected error (RuntimeError)" % path,
            "http": "POST %s: HTTP 500" % path,
            "not-json": "POST %s: HTTP 201, and the answer is not JSON" % path,
        }
        for kind, lost in (("transport", False), ("transport", True), ("exception", True), ("http", False), ("not-json", False)):
            with self.subTest(kind=kind, lost=lost):
                github = FakeGitHub(**DONE_03)
                code, out, err = self.run_failing(github, "POST", path, kind, lost)
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(err, tag_maybe(causes[kind], self.four))
                github.calls = []
                code, out, err, _ = self.checkout.run(github, self.four)
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(github.tags["0.4"], ("commit", self.four))
                self.assertEqual(github.releases[-1]["tag_name"], "v0.4")

    def test_an_answer_to_the_creation_of_the_tag_of_the_wrong_form_says_the_tag_was_created(self):
        github = FakeGitHub(**DONE_03)
        code, out, err = self.run_failing(github, "POST", PATH + "/git/refs", "form")
        self.assertEqual(code, 1)
        self.assertEqual(err, (
            "release: POST %s/git/refs: the answer does not say that the tag v0.4 points at %s. Ratchet 0.4 is not finished: "
            "the tag v0.4 was created, and there is no release. Look at the tag by hand. If it points at commit %s, "
            "rerun the release run of that commit: it creates only the release.\n" % (PATH, self.four, self.four)))
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs")])

    def test_any_error_raised_after_the_tag_ends_in_the_one_message(self):
        # The API itself raises, at each request after the tag, an error of each kind the script does not expect.
        for target in (("POST", PATH + "/releases"), ("GET", PATH + "/git/ref/tags/v0.4")):
            for exception in (KeyError, TypeError, ValueError, AttributeError, IndexError, OSError, release.ReleaseError):
                class Raising(FakeGitHub):
                    def __call__(self, method, path, body=None):
                        if (method, path) == target:
                            self.calls.append((method, path, body))
                            raise exception("synthetic %s" % TOKEN)
                        return FakeGitHub.__call__(self, method, path, body)
                with self.subTest(target=target, exception=exception.__name__):
                    error, out, github = publish(TWO, github=Raising(**DONE_03), sha=SHA)
                    expected = release_missing if target[0] == "POST" else tag_unconfirmed
                    # A ReleaseError keeps its own text as the cause. main() takes the token out of it (see Token).
                    cause = ("synthetic %s" % TOKEN if exception is release.ReleaseError
                             else "%s %s: an unexpected error (%s)" % (target[0], target[1], exception.__name__))
                    self.assertEqual(error, expected(cause, SHA)[len("release: "):-1])
                    self.assertEqual(out, "")

    def test_a_transport_error_before_the_tag_says_that_nothing_was_written(self):
        # The reviewer's mutation turned the "no answer" of the transport into an exception that is not caught.
        for method, path in (("GET", PATH + "/git/matching-refs/tags/v"), ("GET", PATH + "/releases?per_page=100&page=1")):
            with self.subTest(path=path):
                github = FakeGitHub(**DONE_03)
                code, out, err = self.run_failing(github, method, path, "transport")
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(err, "release: %s %s: no answer. Nothing was written.\n" % (method, path))
                self.assertEqual(github.writes, [])


class Scheduled(unittest.TestCase):
    """Round 1 of the narrowed claim, finding 1: a scheduled run comes even when nothing is merged.

    It runs on the head of main, writes nothing, and fails and names the version when the version
    in ratchet.json there, or an older one, is not finished. On a finished state it passes.
    """

    def setUp(self):
        self.checkout = Checkout()
        self.three = self.checkout.commit("0.3", changelog(("0.3", "Three.")))
        self.four = self.checkout.commit("0.4", TWO)

    def tearDown(self):
        self.checkout.close()

    def schedule(self, github, sha=None):
        sha = sha or self.four
        git(self.checkout.directory, "checkout", "-q", "--detach", sha)
        opener = FakeOpener(github)
        code, out, err = main_with(opener, sha, self.checkout.directory, event="schedule")
        return code, out, err, opener

    def test_a_run_cancelled_after_its_tag_is_named_by_the_next_scheduled_run(self):
        github = FakeGitHub(cancel=("POST", PATH + "/releases"), **DONE_03)
        with self.assertRaises(Cancelled):
            self.checkout.run(github, self.four)
        github.cancel = None
        github.calls = []
        code, out, err, opener = self.schedule(github)
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(err, "release: Ratchet 0.4 is not finished: the tag v0.4 points at commit %s, the head of main, and there is no "
                              "published release. A scheduled run writes nothing. Rerun the release run of commit %s, which the tag "
                              "points at: it creates only the release.\n" % (self.four, self.four))
        self.assertEqual(github.writes, [])
        self.assertEqual(set(r.get_method() for r in opener.requests), {"GET"})
        # The rerun finishes it, and the next scheduled run passes and writes nothing.
        code, out, err, _ = self.checkout.run(github, self.four)
        self.assertEqual((code, err), (0, ""))
        github.calls = []
        code, out, err, _ = self.schedule(github)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.writes, [])
        self.assertIn("v0.4 is tagged at this commit and released. Nothing to do", out)

    def test_a_version_with_no_tag_is_named_and_not_tagged(self):
        # The run of 0.4 never ran, or was replaced. Later commits keep 0.4. The scheduled run is on the head.
        head = self.checkout.commit(text=TWO + "\nA later change.\n")
        for sha in (self.four, head):
            with self.subTest(head=sha):
                github = FakeGitHub(**DONE_03)
                code, out, err, opener = self.schedule(github, sha)
                self.assertEqual(code, 1)
                self.assertEqual(err, "release: Ratchet 0.4 is not finished: there is no tag v0.4 and no release, and ratchet.json at the "
                                      "head of main, commit %s, names 0.4. A scheduled run writes nothing. Rerun the release run of commit "
                                      "%s, the first commit on main whose ratchet.json names 0.4, or start the workflow by hand on main.\n"
                                      % (sha, self.four))
                self.assertEqual(github.writes, [])
                self.assertNotIn("0.4", github.tags)

    def test_a_finished_state_passes_and_writes_nothing(self):
        head = self.checkout.commit(text=TWO + "\nA later change.\n")
        done = dict(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", self.four)},
                    releases=DONE_03["releases"] + [{"tag_name": "v0.4", "draft": False}], ancestors=[self.four])
        for sha, said in ((self.four, "v0.4 is tagged at this commit and released. Nothing to do"),
                          (head, "v0.4 is released at an earlier commit, and this commit does not raise the version. Nothing to do")):
            with self.subTest(head=sha):
                github = FakeGitHub(**done)
                code, out, err, opener = self.schedule(github, sha)
                self.assertEqual((code, err), (0, ""))
                self.assertIn(said, out)
                self.assertEqual(github.writes, [])

    def test_an_unfinished_older_version_is_named(self):
        five = self.checkout.commit("0.5", THREE)
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", self.four), "0.5": ("commit", five)},
                            releases=DONE_03["releases"] + [{"tag_name": "v0.5", "draft": False}])
        code, out, err, _ = self.schedule(github, five)
        self.assertEqual(code, 1)
        self.assertIn("0.4: a tag and no published release. Rerun the release run of commit %s, which the tag points at." % self.four, err)
        self.assertEqual(github.writes, [])

    def test_a_draft_or_a_tag_elsewhere_is_named_and_nothing_written(self):
        cases = (
            ({"0.4": ("commit", self.four)}, [{"tag_name": "v0.4", "draft": True}], "a draft release for v0.4 exists"),
            ({"0.4": ("commit", OTHER)}, [], "the tag v0.4 points at another commit than this one, and has no published release"),
            ({}, [{"tag_name": "v0.4", "draft": False}], "a release for v0.4 exists, and the tag does not"),
        )
        for tags, releases, said in cases:
            with self.subTest(said=said):
                github = FakeGitHub(tags=dict(DONE_03["tags"], **tags), releases=DONE_03["releases"] + releases)
                code, out, err, _ = self.schedule(github)
                self.assertEqual(code, 1)
                self.assertIn(said, err)
                self.assertEqual(github.writes, [])

    def test_a_scheduled_run_that_cannot_read_is_red_and_writes_nothing(self):
        # D-2026-11-17-release-fail-closed: a run that cannot confirm that every version is released is red and writes
        # nothing. Naming the version is best effort: it needs an answer. Round 2 of the narrowed claim found that a
        # scheduled run with HTTP 503 on the tag list was red, wrote nothing, and did not name 0.4.
        tag_list = PATH + "/git/matching-refs/tags/v"
        page = PATH + "/releases?per_page=100&page=1"
        head = self.checkout.commit(text=TWO + "\nA later change.\n")
        released = DONE_03["releases"] + [{"tag_name": "v0.4", "draft": False}]
        states = (
            ("cancelled after its tag", self.four, {"0.4": ("commit", self.four)}, DONE_03["releases"], (tag_list, page),
             "Ratchet 0.4 is not finished: the tag v0.4 points at commit %s" % self.four),
            ("never tagged", self.four, {}, DONE_03["releases"], (tag_list, page),
             "Ratchet 0.4 is not finished: there is no tag v0.4 and no release"),
            ("released at an earlier commit", head, {"0.4": ("commit", self.four)}, released,
             (tag_list, page, PATH + "/compare/%s...%s" % (self.four, head)), None),
        )
        for state, sha, tags, releases, reads, named in states:
            def fake():
                return FakeGitHub(tags=dict(DONE_03["tags"], **tags), releases=releases, ancestors=[self.four])
            for path in reads:
                for kind in (503, 500, 502, "transport", "not-json", "form", "exception"):
                    with self.subTest(state=state, path=path, kind=kind):
                        github = fake()
                        if isinstance(kind, int):
                            github.fail[("GET", path)] = kind
                            opener = FakeOpener(github)
                        else:
                            opener = Failing(github, "GET", path, kind)
                        git(self.checkout.directory, "checkout", "-q", "--detach", sha)
                        if kind == "exception":
                            # An error the script does not expect, before any write, is not caught: Python exits with 1.
                            with self.assertRaises(RuntimeError):
                                main_with(opener, sha, self.checkout.directory, event="schedule")
                        else:
                            code, out, err = main_with(opener, sha, self.checkout.directory, event="schedule")
                            self.assertEqual((code, out), (1, ""))
                            self.assertTrue(err.endswith(" Nothing was written.\n"), err)
                            if isinstance(kind, int):
                                self.assertTrue(err.startswith("release: GET %s: HTTP %d" % (path, kind)), err)
                            self.assertNotIn(TOKEN, err)
                        self.assertEqual(github.writes, [])
                        self.assertEqual(set(r.get_method() for r in opener.requests), {"GET"})
            # When the API answers again, the scheduled run names what is unfinished, or passes on a finished state.
            with self.subTest(state=state, answered=True):
                github = fake()
                code, out, err, _ = self.schedule(github, sha)
                if named is None:
                    self.assertEqual((code, err), (0, ""))
                else:
                    self.assertEqual(code, 1)
                    self.assertIn(named, err)
                self.assertEqual(github.writes, [])

    def test_a_scheduled_run_sends_no_write_even_if_the_logic_asked_for_one(self):
        github = FakeGitHub(**DONE_03)
        api = release.read_only(github)
        self.assertEqual(api("GET", PATH + "/git/matching-refs/tags/v")[0], 200)
        for method in ("POST", "PATCH", "PUT", "DELETE", "get"):
            with self.subTest(method=method):
                with self.assertRaises(release.ReleaseError) as caught:
                    api(method, PATH + "/git/refs", {"ref": "refs/tags/v0.4", "sha": SHA})
                self.assertEqual(str(caught.exception), "%s %s/git/refs: a scheduled run writes nothing, and the request was not sent"
                                 % (method, PATH))
        self.assertEqual(github.calls, [("GET", PATH + "/git/matching-refs/tags/v", None)])
        # The logic of publish, told to report, raises before any write in each case that would write in a push run.
        for tags, releases in (({}, []), ({"0.4": ("commit", SHA)}, [])):
            with self.subTest(tags=tags):
                github = FakeGitHub(tags=dict(DONE_03["tags"], **tags), releases=DONE_03["releases"] + releases)
                error, _, github = publish(TWO, github=github, report=True)
                self.assertIn("A scheduled run writes nothing", error)
                self.assertEqual(github.writes, [])

    def test_main_gives_a_scheduled_run_only_the_read_only_api(self):
        # Whatever publish asks for in a scheduled run, a write is not sent.
        def writes_anyway(version, text, history, repo, sha, api, out, report=False, pending=frozenset()):
            api("POST", PATH + "/git/refs", {"ref": "refs/tags/v0.4", "sha": sha})
        github = FakeGitHub(**DONE_03)
        opener = FakeOpener(github)
        with mock.patch.object(release, "publish", writes_anyway):
            code, out, err = main_with(opener, self.four, self.checkout.directory, event="schedule")
        self.assertEqual(code, 1)
        self.assertEqual(err, "release: POST %s/git/refs: a scheduled run writes nothing, and the request was not sent\n" % PATH)
        self.assertEqual(opener.requests, [])

    def test_a_push_and_a_run_by_hand_still_write(self):
        for event in ("push", "workflow_dispatch"):
            with self.subTest(event=event):
                github = FakeGitHub(**DONE_03)
                code, out, err = main_with(FakeOpener(github), self.four, self.checkout.directory, event=event)
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(github.writes, [("POST", PATH + "/git/refs"), ("POST", PATH + "/releases")])

    def test_the_event_is_read_strictly_and_a_scheduled_run_is_only_on_main(self):
        for changes in ({"GITHUB_EVENT_NAME": None}, {"GITHUB_EVENT_NAME": ""}, {"GITHUB_EVENT_NAME": "pull_request"},
                        {"GITHUB_EVENT_NAME": "pull_request_target"}, {"GITHUB_EVENT_NAME": "Schedule"},
                        {"GITHUB_EVENT_NAME": "schedule\n"}, {"GITHUB_EVENT_NAME": "release"}):
            with self.subTest(changes=changes):
                code, _, err, opener = run_main(FakeGitHub(), environ=environment(**changes))
                self.assertEqual(code, 1)
                self.assertEqual(err, "release: GITHUB_EVENT_NAME is not push, workflow_dispatch or schedule\n")
                self.assertEqual(opener.requests, [])
        for ref in ("refs/heads/personlig/x", "refs/tags/v0.4", None):
            with self.subTest(ref=ref):
                code, _, err, opener = run_main(FakeGitHub(), environ=environment(GITHUB_EVENT_NAME="schedule", GITHUB_REF=ref))
                self.assertEqual(code, 1)
                self.assertIn("GITHUB_REF is not refs/heads/main", err)
                self.assertEqual(opener.requests, [])


def unreleased(version, text, *older):
    """A changelog whose first entry, of version, is headed "(unreleased)", with the dated entries (version, text) after it."""
    return changelog(*older).replace("# Changelog\n", "# Changelog\n\n## %s (unreleased)\n\n%s\n" % (version, text), 1)


UNRELEASED_TWO = unreleased("0.4", "Four, collected.", ("0.3", "Three."))
NOT_RELEASED = ('Ratchet 0.4 is not released: its entry in CHANGELOG.md is headed "(unreleased)". Every older version is finished. '
                "Nothing was written.\n")


def dated_again(dated, head, version="0.4"):
    """The message of a run at head, whose changelog heads version "(unreleased)" after commit dated on main gave it a date."""
    return ('Ratchet %s is not finished: commit %s on main gave its entry in CHANGELOG.md a date, and at commit %s it is headed '
            '"(unreleased)" again. A version dated on main must be released. Give the entry its date again, so that the run of '
            "that push releases it, or rerun the release run of commit %s, the first commit on main that dated it. "
            "Nothing was written." % (version, dated, head, dated))


class Unreleased(unittest.TestCase):
    """D-2026-11-19-batched-releases, choice 1: the first entry may be headed "## <version> (unreleased)".

    While it is, no run publishes that version: a run of a push or by hand passes and says so, and a scheduled run
    passes too. Every older version must still be finished, as before. Every other place or form of the heading fails.
    """

    def test_an_unreleased_first_entry_publishes_nothing_and_passes(self):
        for report in (False, True):
            with self.subTest(scheduled=report):
                error, out, github = publish(UNRELEASED_TWO, github=FakeGitHub(**DONE_03), report=report, pending={SHA})
                self.assertIsNone(error)
                self.assertEqual(out, NOT_RELEASED)
                self.assertEqual(github.writes, [])
                self.assertNotIn("0.4", github.tags)

    def test_an_unreleased_first_entry_still_needs_every_older_version_finished(self):
        for report in (False, True):
            with self.subTest(scheduled=report):
                github = FakeGitHub(tags={"0.3": ("commit", EARLIER)})
                error, out, github = publish(UNRELEASED_TWO, github=github, report=report, pending={SHA})
                self.assertIn("an older version is not finished. 0.3: a tag and no published release", error)
                self.assertIn("Nothing was written", error)
                self.assertEqual(github.writes, [])

    def test_an_unreleased_entry_of_a_version_that_has_a_tag_fails(self):
        for tags, releases in (({"0.4": ("commit", EARLIER)}, []), ({"0.4": ("commit", SHA)}, [{"tag_name": "v0.4", "draft": False}])):
            with self.subTest(tags=tags):
                github = FakeGitHub(tags=dict(DONE_03["tags"], **tags), releases=DONE_03["releases"] + releases)
                error, _, github = publish(UNRELEASED_TWO, github=github, pending={SHA})
                self.assertEqual(error, 'the tag v0.4 exists, and the entry of 0.4 in CHANGELOG.md is headed "(unreleased)". '
                                        "A released version stays released. Nothing was written.")
                self.assertEqual(github.writes, [])

    def test_an_unreleased_entry_with_a_release_and_no_tag_fails(self):
        github = FakeGitHub(tags=DONE_03["tags"], releases=DONE_03["releases"] + [{"tag_name": "v0.4", "draft": True}])
        error, _, github = publish(UNRELEASED_TWO, github=github, pending={SHA})
        self.assertEqual(error, "a release for v0.4 exists, and the tag does not. Publish or remove it by hand. Nothing was written.")
        self.assertEqual(github.writes, [])

    def test_an_unreleased_heading_that_is_not_first_or_stands_twice_fails_before_any_request(self):
        cases = (
            (changelog(("0.4", "Four.")).replace("# Changelog\n", "# Changelog\n\n## 0.5 (unreleased)\n\nFive.\n\n## 0.3 (unreleased)\n\nThree.\n"),
             "0.5", "CHANGELOG.md, line 7: the entry of 0.3 is headed (unreleased), and only the first entry may be. Nothing was written."),
            (unreleased("0.4", "Four.", ("0.3", "Three.")).replace("## 0.3 (2026-11-17)", "## 0.3 (unreleased)"),
             "0.4", "CHANGELOG.md, line 7: the entry of 0.3 is headed (unreleased), and only the first entry may be. Nothing was written."),
            (unreleased("0.4", "Four.", ("0.4", "Four, dated."), ("0.3", "Three.")),
             "0.4", "CHANGELOG.md: the version 0.4 has 2 headings. Nothing was written."),
        )
        for text, version, message in cases:
            with self.subTest(message=message):
                error, _, github = publish(text, version=version, github=FakeGitHub(**DONE_03), pending={SHA})
                self.assertEqual(error, message)
                self.assertEqual(github.calls, [])

    def test_an_unreleased_heading_of_another_form_is_no_entry(self):
        for heading in ("## 0.4 (Unreleased)", "## 0.4 (unreleased) ", "## 0.4 unreleased", "## 0.4(unreleased)", "## 0.4 (unreleased",
                        "## Unreleased", "## 0.4 (unreleased)\u00a0", "##  0.4 (unreleased)", "## 0.4 (unreleased, soon)"):
            with self.subTest(heading=heading):
                text = UNRELEASED_TWO.replace("## 0.4 (unreleased)", heading)
                self.assertEqual(release.changelog_versions(text), ["0.3"])
                error, _, github = publish(text, github=FakeGitHub(**DONE_03), pending={SHA})
                self.assertEqual(error, "CHANGELOG.md has no entry for 0.4, the version in ratchet.json")
                self.assertEqual(github.calls, [])

    def test_the_checkout_and_its_commit_must_agree_on_whether_the_version_is_released(self):
        error, _, github = publish(UNRELEASED_TWO, github=FakeGitHub(**DONE_03), pending=set())
        self.assertEqual(error, 'CHANGELOG.md in the checkout heads 0.4 "(unreleased)", and at commit %s it does not. Nothing was written.' % SHA)
        self.assertEqual(github.calls, [])
        error, _, github = publish(TWO, github=FakeGitHub(**DONE_03), pending={SHA})
        self.assertEqual(error, 'CHANGELOG.md at commit %s heads 0.4 "(unreleased)", and in the checkout it does not. Nothing was written.' % SHA)
        self.assertEqual(github.calls, [])

    def test_a_dated_entry_is_released_as_before(self):
        error, out, github = publish(TWO, github=FakeGitHub(**DONE_03), pending=set())
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs"), ("POST", PATH + "/releases")])


class UnreleasedOnMain(unittest.TestCase):
    """The history of main, read with git, with commits whose changelog heads the version "(unreleased)".

    A version must be released once a commit on main names it with a dated entry. A version that main only ever named
    as unreleased needs nothing. The rerun that a message names is the first commit on main that names the version
    with a date, since a rerun of an unreleased commit publishes nothing.
    """

    def setUp(self):
        self.checkout = Checkout()
        self.addCleanup(self.checkout.close)
        self.three = self.checkout.commit("0.3", changelog(("0.3", "Three.")))

    def schedule(self, github, sha):
        return main_with(FakeOpener(github), sha, self.checkout.directory, event="schedule")

    def test_the_commits_that_head_their_version_unreleased_are_read_from_main(self):
        first = self.checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")))
        second = self.checkout.commit(text=unreleased("0.4", "Four, and more.", ("0.3", "Three.")))
        dated = self.checkout.commit(text=TWO)
        history = self.checkout.history()
        self.assertEqual(history, [(dated, "0.4"), (second, "0.4"), (first, "0.4"), (self.three, "0.3")])
        self.assertEqual(release.read_pending(self.checkout.directory, history), {first, second})

    def test_a_push_of_an_unreleased_version_passes_and_writes_nothing(self):
        head = self.checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")))
        github = FakeGitHub(**DONE_03)
        code, out, err, opener = self.checkout.run(github, head)
        self.assertEqual((code, out, err), (0, NOT_RELEASED, ""))
        self.assertEqual(github.writes, [])
        self.assertEqual(set(r.get_method() for r in opener.requests), {"GET"})
        code, out, err = self.schedule(github, head)
        self.assertEqual((code, out, err), (0, NOT_RELEASED, ""))

    def test_the_release_is_the_push_that_dates_the_entry(self):
        self.checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")))
        self.checkout.commit(text=unreleased("0.4", "Four, and more.", ("0.3", "Three.")))
        dated = self.checkout.commit(text=TWO)
        github = FakeGitHub(**DONE_03)
        code, out, err, _ = self.checkout.run(github, dated)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.tags["0.4"], ("commit", dated))
        self.assertEqual(github.releases[-1]["body"], release_line("0.4"))

    def test_a_dated_entry_left_without_its_tag_is_named_by_the_scheduled_run_with_the_commit_that_dated_it(self):
        self.checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")))
        dated = self.checkout.commit(text=TWO)
        head = self.checkout.commit(text=TWO + "\nA later change.\n")
        github = FakeGitHub(**DONE_03)
        code, out, err = self.schedule(github, head)
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(err, "release: Ratchet 0.4 is not finished: there is no tag v0.4 and no release, and ratchet.json at the "
                              "head of main, commit %s, names 0.4. A scheduled run writes nothing. Rerun the release run of commit "
                              "%s, the first commit on main whose ratchet.json names 0.4, or start the workflow by hand on main.\n"
                              % (head, dated))
        self.assertEqual(github.writes, [])

    def test_a_dated_version_left_unreleased_stops_the_next_unreleased_one_and_names_the_commit_that_dated_it(self):
        self.checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")))
        dated = self.checkout.commit(text=TWO)
        head = self.checkout.commit("0.5", unreleased("0.5", "Five.", ("0.4", "Four."), ("0.3", "Three.")))
        for event in ("push", "schedule"):
            with self.subTest(event=event):
                github = FakeGitHub(**DONE_03)
                code, out, err = main_with(FakeOpener(github), head, self.checkout.directory, event=event)
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(err, "release: an older version is not finished. 0.4: no tag. Rerun the release run of commit %s, "
                                      "the first commit on main whose ratchet.json names 0.4. Then rerun this run. Nothing was written.\n" % dated)
                self.assertEqual(github.writes, [])

    def cancelled_before_the_tag(self, github, sha):
        """The run of the push of sha, cancelled before it creates the tag: it writes nothing."""
        github.cancel = ("POST", PATH + "/git/refs")
        with self.assertRaises(Cancelled):
            main_with(FakeOpener(github), sha, self.checkout.directory)
        github.cancel = None
        self.assertNotIn("0.4", github.tags)

    def late_run(self, github, sha):
        """The run of an earlier commit on main, rerun or started late, on a checkout of that commit."""
        git(self.checkout.directory, "checkout", "-q", "--detach", sha)
        try:
            return main_with(FakeOpener(github), sha, self.checkout.directory)
        finally:
            git(self.checkout.directory, "checkout", "-q", "main")

    def test_a_dated_version_headed_unreleased_again_must_still_be_released(self):
        # Round 2 of PR #50, finding 1: the run of the dated commit was cancelled before it tagged, and a later commit
        # put "(unreleased)" back. Every run passed with no v0.4. Once main has dated a version, it must be released.
        self.checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")))
        dated = self.checkout.commit(text=TWO)
        github = FakeGitHub(ancestors=[dated], **DONE_03)
        self.cancelled_before_the_tag(github, dated)
        head = self.checkout.commit(text=UNRELEASED_TWO)
        for event in ("push", "schedule"):
            with self.subTest(event=event):
                code, out, err = main_with(FakeOpener(github), head, self.checkout.directory, event=event)
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(err, "release: %s\n" % dated_again(dated, head))
                self.assertNotIn("0.4", github.tags)
                self.assertEqual(github.writes, [("POST", PATH + "/git/refs")])
        # The late run of the dated commit, after the revert: 0.4 was dated on main, so it is released there.
        code, out, err = self.late_run(github, dated)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.tags["0.4"], ("commit", dated))
        self.assertEqual(github.releases[-1]["body"], release_line("0.4"))
        # main stays red while its changelog heads the released 0.4 "(unreleased)", and is green once the date is back.
        self.assert_red_while_unreleased(github, head)
        redated = self.checkout.commit(text=TWO)
        code, out, err, _ = self.checkout.run(github, redated)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "v0.4 is released at an earlier commit, and this commit does not raise the version. Nothing to do.\n")

    def test_a_dated_version_released_late_and_then_headed_unreleased_again_keeps_main_red(self):
        # The other order: the late run of the dated commit releases 0.4 before the revert reaches main.
        self.checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")))
        dated = self.checkout.commit(text=TWO)
        github = FakeGitHub(ancestors=[dated], **DONE_03)
        self.cancelled_before_the_tag(github, dated)
        code, out, err, _ = self.checkout.run(github, dated)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.tags["0.4"], ("commit", dated))
        head = self.checkout.commit(text=UNRELEASED_TWO)
        self.assert_red_while_unreleased(github, head)

    def test_a_dated_version_headed_unreleased_again_names_the_first_commit_that_dated_it(self):
        self.checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")))
        dated = self.checkout.commit(text=TWO)
        self.checkout.commit(text=UNRELEASED_TWO)
        self.checkout.commit(text=TWO + "\nDated again.\n")
        head = self.checkout.commit(text=UNRELEASED_TWO + "\nAnd unreleased again.\n")
        github = FakeGitHub(**DONE_03)
        code, out, err, _ = self.checkout.run(github, head)
        self.assertEqual((code, out, err), (1, "", "release: %s\n" % dated_again(dated, head)))
        self.assertEqual(github.writes, [])

    def assert_red_while_unreleased(self, github, head):
        for event in ("push", "schedule"):
            with self.subTest(event=event):
                before = list(github.writes)
                code, out, err = main_with(FakeOpener(github), head, self.checkout.directory, event=event)
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(err, 'release: the tag v0.4 exists, and the entry of 0.4 in CHANGELOG.md is headed "(unreleased)". '
                                      "A released version stays released. Nothing was written.\n")
                self.assertEqual(github.writes, before)

    def test_a_version_main_only_named_as_unreleased_needs_no_release(self):
        self.checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")))
        head = self.checkout.commit("0.5", changelog(("0.5", "Five, which took the place of 0.4."), ("0.3", "Three.")))
        github = FakeGitHub(**DONE_03)
        code, out, err, _ = self.checkout.run(github, head)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(sorted(github.tags), ["0.3", "0.5"])

    def test_a_commit_whose_changelog_heads_the_version_in_another_form_counts_as_released(self):
        # Fail closed: only the one exact form "## <version> (unreleased)", as the first entry, takes a commit out.
        for heading in ("## 0.4 (Unreleased)", "## 0.4 (unreleased) ", "## 0.4"):
            with self.subTest(heading=heading):
                checkout = Checkout()
                self.addCleanup(checkout.close)
                checkout.commit("0.3", changelog(("0.3", "Three.")))
                odd = checkout.commit("0.4", unreleased("0.4", "Four.", ("0.3", "Three.")).replace("## 0.4 (unreleased)", heading))
                head = checkout.commit("0.5", unreleased("0.5", "Five.", ("0.3", "Three.")))
                self.assertEqual(release.read_pending(checkout.directory, checkout.history()), {head})
                github = FakeGitHub(**DONE_03)
                code, out, err, _ = checkout.run(github, head)
                self.assertEqual(code, 1)
                self.assertIn("0.4: no tag. Rerun the release run of commit %s," % odd, err)
                self.assertEqual(github.writes, [])

    def test_a_changelog_on_main_that_is_not_utf8_fails(self):
        data = unreleased("0.4", "F\xffour.", ("0.3", "Three.")).encode("latin-1")
        self.checkout.write("CHANGELOG.md", data)
        bad = self.checkout.commit("0.4")
        head = self.checkout.commit(text=UNRELEASED_TWO)
        with self.assertRaises(release.ReleaseError) as caught:
            release.read_pending(self.checkout.directory, self.checkout.history(head))
        self.assertEqual(str(caught.exception), "CHANGELOG.md at commit %s on main: it is not valid UTF-8, at byte %d (0xFF). "
                                                "Nothing was written." % (bad, data.index(b"\xff")))


class Token(unittest.TestCase):
    """The token comes from GITHUB_TOKEN, goes only to api.github.com, and is never printed."""

    @classmethod
    def setUpClass(cls):
        # A checkout with today's ratchet.json and CHANGELOG.md, at one commit, with the first entry given a date if it
        # is unreleased, so that the run comes to its writes.
        cls.checkout = Checkout()
        with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as handle:
            cls.checkout.commit(NOW, handle.read().replace("## %s (unreleased)\n" % NOW, "## %s (2026-11-26)\n" % NOW, 1))

    @classmethod
    def tearDownClass(cls):
        cls.checkout.close()

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
                code, out, err, opener = self.checkout.run(github)
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
        code, out, err, _ = self.checkout.run(github)
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
        self.checkout = Checkout()
        self.directory = self.checkout.directory
        self.checkout.commit("0.3", changelog(("0.3", "The entry for 0.3.")))
        self.head = self.checkout.commit(self.VERSION, changelog((self.VERSION, "The entry for %s." % self.VERSION), ("0.3", "The entry for 0.3.")))

    def tearDown(self):
        self.checkout.close()

    def test_publish_tags_the_version_in_ratchet_json(self):
        github = FakeGitHub(**DONE_03)
        code, out, err, _ = self.checkout.run(github)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.tags[self.VERSION], ("commit", self.head))
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
        code, out, err, _ = self.checkout.run(github)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.releases[-1]["body"], release_line(self.VERSION))
        out, err = io.StringIO(), io.StringIO()
        code = release.main(["notes", "--repo", REPO], environ={}, opener=None, out=out, err=err, root=self.directory)
        self.assertEqual((code, err.getvalue(), out.getvalue()), (0, "", release_line(self.VERSION) + "\n"))


# After CRLF is read as LF: every control character but the tab and LF, and the two line separators of Unicode.
# A YAML parser may break a line at a lone CR, at NEL (U+0085, among the C1 controls), at U+2028 or at U+2029,
# where the comparison below does not. Then a line it takes for a comment can hold code.
WORKFLOW_REFUSED = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029]")


def workflow_text(data):
    """The text of a workflow file, read as strict UTF-8, with CRLF read as LF. ValueError on any other line break or control character."""
    text = data.decode("utf-8", errors="strict").replace("\r\n", "\n")
    match = WORKFLOW_REFUSED.search(text)
    if match:
        raise ValueError("the workflow holds U+%04X at character %d: a control character or a line break other than LF and CRLF"
                         % (ord(match.group()), match.start()))
    return text


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

    def data(self):
        with open(self.LIVE, "rb") as handle:
            return handle.read()

    def lines(self):
        return workflow_text(self.data()).split("\n")

    # Round 1 of release-links, finding 2: a lone CR in a comment hid "if: false" from the comparison.

    def test_a_line_break_or_control_character_that_is_not_lf_or_crlf_fails_the_reading(self):
        live = self.data()
        self.assertEqual(workflow_text(live), live.decode("utf-8"))
        anchor = b"jobs:\n  release:\n"
        self.assertEqual(live.count(anchor), 1)
        for character in ("\r", "\x00", "\x08", "\x0b", "\x0c", "\x1b", "\x1f", "\x7f", "\x85", "\x9f", "\u2028", "\u2029"):
            with self.subTest(character=character):
                hidden = anchor + ("    # review marker%s    if: false\n" % character).encode("utf-8")
                with self.assertRaises(ValueError) as caught:
                    workflow_text(live.replace(anchor, hidden))
                self.assertIn("U+%04X" % ord(character), str(caught.exception))
        # The reviewer's file, byte for byte: "# review marker", a lone CR, then "if: false" on the job.
        with self.assertRaises(ValueError):
            workflow_text(live.replace(b"    timeout-minutes: 30\n", b"    timeout-minutes: 30\n    # review marker\r    if: false\n"))
        with self.assertRaises(UnicodeDecodeError):
            workflow_text(live.replace(b"name: release", b"name: release\xff"))

    def test_the_reading_that_the_comparison_uses_refuses_the_reviewers_file(self):
        # The same lines() that every test of the workflow reads, given the reviewer's file instead of the live one.
        live = self.data()
        hostile = live.replace(b"    timeout-minutes: 30\n", b"    timeout-minutes: 30\n    # review marker\r    if: false\n")
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        path = os.path.join(directory, "release.yml")
        with open(path, "wb") as handle:
            handle.write(hostile)
        with mock.patch.object(self, "LIVE", path):
            with self.assertRaises(ValueError):
                self.code()

    def test_crlf_and_the_tab_are_read_and_then_compared(self):
        live = self.data()
        self.assertEqual(workflow_text(live.replace(b"\n", b"\r\n")), live.decode("utf-8"))
        # A tab passes the reading. It is no indentation for the comparison, so the reviewed form does not match.
        tabbed = workflow_text(live.replace(b"  group: release", b"\tgroup: release"))
        self.assertIn("\tgroup: release", workflow_code(tabbed))

    def test_the_workflow_keeps_its_form(self):
        lines = self.lines()
        text = "\n".join(lines)
        self.assertIn("on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n  schedule:\n    - cron: \"23 4 * * *\"\n\n"
                      "permissions:\n  contents: read\n", text)
        self.assertFalse([l for l in lines if "inputs:" in l])
        self.assertEqual([l for l in lines if "contents: write" in l], ["      contents: write"])
        self.assertEqual([l.strip(" ") for l in lines if "runs-on:" in l], ["runs-on: ubuntu-24.04"])
        self.assertEqual([l.strip(" ") for l in lines if "timeout-minutes:" in l], ["timeout-minutes: 30"])
        uses = [l.strip(" ") for l in lines if "uses:" in l]
        self.assertEqual(len(uses), 1)
        self.assertRegex(uses[0], r"^- uses: actions/checkout@[0-9a-f]{40} # v[0-9.]+\Z")
        self.assertIn("          persist-credentials: false", lines)
        self.assertIn("          fetch-depth: 0", lines)
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

    def test_it_runs_only_on_a_push_to_main_by_hand_with_no_input_and_every_day(self):
        self.assertEqual(self.block("on:"), ["on:", "  push:", "    branches: [main]", "  workflow_dispatch:",
                                             "  schedule:", '    - cron: "23 4 * * *"'])
        self.assertFalse([l for l in self.code() if l.strip(" ").startswith(("if:", "- if:"))])

    def test_the_schedule_runs_at_least_once_a_day(self):
        # Round 1 of the narrowed claim, finding 1: a run comes even when nothing is merged. One cron line, with a fixed
        # minute and hour and every day of the month, every month and every day of the week, so no day is left out.
        crons = [l.strip(" ") for l in self.code() if "cron" in l]
        self.assertEqual(len(crons), 1)
        self.assertRegex(crons[0], r'^- cron: "([0-5]?[0-9]) ([01]?[0-9]|2[0-3]) \* \* \*"\Z')
        self.assertEqual([l for l in self.code() if "schedule" in l], ["  schedule:"])

    def test_the_checkout_holds_the_whole_history_of_main(self):
        # Round 1 of release-links, finding 1: the script reads every version that main has had, so the clone is not shallow.
        self.assertEqual(self.block("        with:"), ["        with:", "          fetch-depth: 0", "          persist-credentials: false"])
        self.assertEqual([l for l in self.code() if "fetch-depth" in l or "filter:" in l or "sparse" in l], ["          fetch-depth: 0"])

    def test_a_run_has_a_time_limit(self):
        self.assertEqual([l for l in self.code() if "timeout-minutes" in l], ["    timeout-minutes: 30"])

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
            "  schedule:",
            '    - cron: "23 4 * * *"',
            "permissions:",
            "  contents: read",
            "concurrency:",
            "  group: release",
            "  cancel-in-progress: false",
            "jobs:",
            "  release:",
            "    runs-on: ubuntu-24.04",
            "    timeout-minutes: 30",
            "    permissions:",
            "      contents: write",
            "    env:",
            '      PYTHONDONTWRITEBYTECODE: "1"',
            "    steps:",
            "      - uses: actions/checkout@<commit> # v<version>",
            "        with:",
            "          fetch-depth: 0",
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
