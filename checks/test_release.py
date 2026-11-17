"""The release script must fail on every fault it claims to catch (ratchet.test-can-fail).

    python3 -m unittest discover -s checks -v

checks/release.py tags and releases a version from the release workflow. These tests
never reach the network: the GitHub API is a fake, given to the script as a function,
and the HTTP client is given a fake opener. Standard library only.
"""

import io
import json
import os
import re
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
TOKEN = "ghs_THISISNOTAREALTOKEN0123456789abcdef"
BODY_MARKER = "BODY-FROM-THE-RESPONSE"
PATH = "/repos/%s" % REPO
with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as _handle:
    NOW = json.load(_handle)["version"]
with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as _handle:
    # The older versions in today's changelog, read another way than the script reads them.
    OLDER = [v for v in re.findall(r"^## ([0-9]+\.[0-9]+) \(", _handle.read(), re.M) if v != NOW]
TAGGED = dict((v, ("commit", EARLIER)) for v in OLDER)


def changelog(*entries):
    """A changelog with one entry for each (version, text), newest first."""
    parts = ["# Changelog\n"]
    for version, text in entries:
        parts.append("\n## %s (2026-11-17)\n\n%s\n" % (version, text))
    return "".join(parts)


TWO = changelog(("0.4", "The entry for 0.4."), ("0.3", "The entry for 0.3."))


class FakeGitHub:
    """The part of the GitHub API that the script uses, in memory.

    tags: {version: (object type, sha)}. releases: [{"tag_name": ..., "draft": ...}].
    fail: {(method, path): status} answers that request with that status.
    """

    def __init__(self, tags=None, releases=None, fail=None, ancestors=(), moves_tag_to=None):
        self.tags = dict(tags or {})
        self.releases = [dict(r) for r in (releases or [])]
        self.fail = dict(fail or {})
        self.ancestors = set(ancestors)
        self.moves_tag_to = moves_tag_to
        self.calls = []

    @property
    def writes(self):
        return [(method, path) for method, path, _ in self.calls if method != "GET"]

    def ref(self, version):
        kind, sha = self.tags[version]
        return {"ref": "refs/tags/v%s" % version, "object": {"type": kind, "sha": sha}}

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
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
            return 200, {"status": "ahead" if base in self.ancestors and head == SHA else "diverged"}
        return 404, None


def publish(text, version="0.4", github=None):
    """Run the script's publish step on a changelog. Returns (error text or None, output, fake)."""
    github = github if github is not None else FakeGitHub()
    out = io.StringIO()
    try:
        release.publish(version, text, REPO, SHA, github, out)
    except release.ReleaseError as error:
        return str(error), out.getvalue(), github
    return None, out.getvalue(), github


class ChangelogEntries(unittest.TestCase):
    """The changelog is read strictly: only real top-level headings, never anything in a code block."""

    def fails(self, text, message):
        with self.assertRaises(release.ReleaseError) as caught:
            release.parse_changelog(text)
        self.assertIn(message, str(caught.exception))

    def test_a_fenced_heading_inside_an_entry_is_part_of_that_entry(self):
        text = changelog(("0.4", "Before.\n\n```\n## 0.3 (2026-11-17)\n\nTEXT FROM CODE EXAMPLE\n```\n\nAfter."), ("0.3", "Old."))
        entries = release.parse_changelog(text)
        self.assertEqual([e.version for e in entries], ["0.4", "0.3"])
        notes = release.release_text(entries[0], REPO)
        self.assertEqual(notes, "Before.\n\n```\n## 0.3 (2026-11-17)\n\nTEXT FROM CODE EXAMPLE\n```\n\nAfter.")

    def test_a_fenced_heading_before_the_first_entry_fails(self):
        text = "# Changelog\n\n```\n## 0.4 (2026-11-17)\n\nTEXT FROM CODE EXAMPLE\n```\n" + TWO[len("# Changelog\n"):]
        self.fails(text, "CHANGELOG.md:3: nothing but blank lines may stand before the first entry")

    def test_a_fence_that_is_not_three_backticks_alone_fails(self):
        for fence in ("~~~", "````", "   ```", "```python3 x"):
            with self.subTest(fence=fence):
                self.fails(changelog(("0.4", "%s\n## 0.3 (2026-11-17)\n%s" % (fence, fence))), "a code block here opens and closes with")

    def test_a_code_block_that_is_never_closed_fails(self):
        self.fails(changelog(("0.4", "```\n## 0.3 (2026-11-17)")), "a code block is opened and never closed")

    def test_a_duplicate_entry_fails(self):
        self.fails(changelog(("0.4", "One."), ("0.4", "Two.")), "CHANGELOG.md:7: a second entry for 0.4")

    def test_a_malformed_heading_fails(self):
        for heading in ("## 0.4 (2026-11-17", "## v0.4 (2026-11-17)", "## 0.4", "## 0.4.1 (2026-11-17)",
                        "## 0.4 (2026-11-17) ", "##  0.4 (2026-11-17)", " ## 0.4 (2026-11-17)",
                        "   ## 0.4 (2026-11-17)", "# 0.4 (2026-11-17)", "## 0.4 (17 November)", "##"):
            with self.subTest(heading=heading):
                text = "# Changelog\n\n%s\n\nThe entry.\n" % heading
                self.fails(text, 'CHANGELOG.md:3: a heading here is "## MAJOR.MINOR (YYYY-MM-DD)"')

    def test_a_heading_made_with_an_underline_fails(self):
        self.fails(changelog(("0.4", "Text.\n\n0.3 (2026-11-17)\n---")), "a heading made with an underline")

    def test_a_comment_or_html_that_could_hide_a_heading_fails(self):
        for line in ("<!--", "<details>", "<!-- generated:count --> text"):
            with self.subTest(line=line):
                self.fails(changelog(("0.4", "%s\n## 0.3 (2026-11-17)\n-->" % line)), "the only comments here are the markers")

    def test_a_link_definition_fails(self):
        self.fails(changelog(("0.4", "See [the guide][guide].\n\n[guide]: MIGRATING.md")), "a link definition")

    def test_entries_newest_first(self):
        self.fails(changelog(("0.3", "Old."), ("0.4", "New.")), "the entries must stand newest first")

    def test_an_empty_entry_fails(self):
        self.fails("# Changelog\n\n## 0.4 (2026-11-17)\n\n<!-- generated:count -->\n<!-- /generated -->\n", "the entry for 0.4 is empty")

    def test_the_first_line_is_the_title(self):
        self.fails("Changelog\n\n## 0.4 (2026-11-17)\n\nText.\n", 'CHANGELOG.md:1: the first line is "# Changelog"')

    def test_crlf_is_read_as_lf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "CHANGELOG.md")
            with open(path, "wb") as handle:
                handle.write(TWO.replace("\n", "\r\n").encode("utf-8"))
            entries = release.read_changelog(path)
        self.assertEqual(release.release_text(entries[0], REPO), "The entry for 0.4.")
        self.assertEqual([e.version for e in entries], ["0.4", "0.3"])

    def test_a_lone_carriage_return_in_a_heading_fails(self):
        self.fails(TWO.replace("## 0.4 (2026-11-17)", "## 0.4\r(2026-11-17)", 1), 'a heading here is "## MAJOR.MINOR (YYYY-MM-DD)"')

    def test_a_changelog_that_is_not_utf8_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "CHANGELOG.md")
            with open(path, "wb") as handle:
                handle.write(TWO.encode("utf-8").replace(b"for 0.4", b"for \xff0.4"))
            with self.assertRaises(release.ReleaseError) as caught:
                release.read_changelog(path)
        self.assertIn("is not valid UTF-8, at byte", str(caught.exception))

    def test_links_point_at_the_files_in_the_tag_and_code_is_left_alone(self):
        entry = release.parse_changelog(changelog(("0.4", "See [the guide](MIGRATING.md#start), `[x](y)` and [web](https://example.invalid/a).")))[0]
        self.assertEqual(
            release.release_text(entry, REPO),
            "See [the guide](https://github.com/%s/blob/v0.4/MIGRATING.md#start), `[x](y)` and [web](https://example.invalid/a)." % REPO,
        )

    def test_the_03_entry_gives_the_text_of_the_existing_release_for_v03(self):
        with open(os.path.join(HERE, "fixtures", "release", "v0.3.json"), encoding="utf-8") as handle:
            published = json.load(handle)
        entries = release.read_changelog(os.path.join(ROOT, "CHANGELOG.md"))
        entry = next(e for e in entries if e.version == "0.3")
        # GitHub keeps a release text written in its form with CRLF and two line endings at the end.
        self.assertEqual(release.release_text(entry, REPO), published["body"].replace("\r\n", "\n").rstrip("\n"))
        self.assertEqual(published["tag_name"], "v0.3")

    def test_todays_changelog_is_read_without_a_fault(self):
        entries = release.read_changelog(os.path.join(ROOT, "CHANGELOG.md"))
        self.assertEqual([e.version for e in entries], [NOW] + OLDER)
        self.assertEqual([e.version for e in entries][-3:], ["0.3", "0.2", "0.1"])


class Publish(unittest.TestCase):
    """Tag and release are created in order, checked, and never written over."""

    def test_a_new_version_is_tagged_at_this_commit_and_released(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER)}, releases=[{"tag_name": "v0.3", "draft": False}])
        error, out, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs"), ("POST", PATH + "/releases")])
        self.assertEqual(github.calls[-3][2], {"ref": "refs/tags/v0.4", "sha": SHA})
        self.assertEqual(github.calls[-2][2], {"tag_name": "v0.4", "name": "Ratchet 0.4", "body": "The entry for 0.4.",
                                               "draft": False, "prerelease": False})
        self.assertEqual(github.calls[-1][:2], ("GET", PATH + "/git/ref/tags/v0.4"))
        self.assertIn("Tagged v0.4 at %s and released Ratchet 0.4" % SHA, out)

    def test_an_older_version_without_a_tag_fails_and_is_named(self):
        text = changelog(("0.5", "Five."), ("0.4", "Four."), ("0.3", "Three."), ("0.2", "Two."))
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER)})
        error, _, github = publish(text, version="0.5", github=github)
        self.assertIn("0.2 and 0.4 have an entry in CHANGELOG.md and no tag", error)
        self.assertEqual(github.writes, [])

    def test_an_older_version_without_a_tag_fails_also_when_nothing_is_to_be_released(self):
        github = FakeGitHub(tags={"0.4": ("commit", EARLIER)}, releases=[{"tag_name": "v0.4", "draft": False}], ancestors=[EARLIER])
        error, _, github = publish(TWO, github=github)
        self.assertIn("0.3 has an entry in CHANGELOG.md and no tag", error)
        self.assertEqual(github.writes, [])

    def test_a_tag_without_an_entry_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.9": ("commit", EARLIER)})
        error, _, github = publish(TWO, github=github)
        self.assertIn("the tag v0.9 has no entry in CHANGELOG.md", error)
        self.assertEqual(github.writes, [])

    def test_a_tag_that_is_not_a_version_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4-rc": ("commit", EARLIER)})
        error, _, github = publish(TWO, github=github)
        self.assertIn("a tag under refs/tags/v is not of the form vMAJOR.MINOR", error)
        self.assertEqual(github.writes, [])

    def test_a_tag_at_this_commit_without_a_release_gets_only_its_release(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", SHA)})
        error, out, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/releases")])
        self.assertEqual(github.calls[-1][:2], ("GET", PATH + "/git/ref/tags/v0.4"))
        self.assertIn("The tag v0.4 was already at %s. Released Ratchet 0.4" % SHA, out)

    def test_a_tag_at_this_commit_with_a_draft_writes_nothing_and_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", SHA)}, releases=[{"tag_name": "v0.4", "draft": True}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("a draft release for v0.4 exists", error)
        self.assertEqual(github.writes, [])

    def test_a_tag_at_this_commit_with_a_published_release_is_done(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", SHA)}, releases=[{"tag_name": "v0.4", "draft": False}])
        error, out, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [])
        self.assertIn("v0.4 is tagged at this commit and released. Nothing to do", out)

    def test_a_draft_without_a_tag_writes_nothing_and_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER)}, releases=[{"tag_name": "v0.4", "draft": True}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("a release for v0.4 exists, and the tag does not", error)
        self.assertEqual(github.writes, [])

    def test_two_releases_for_one_tag_fail(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", SHA)},
                            releases=[{"tag_name": "v0.4", "draft": False}, {"tag_name": "v0.4", "draft": True}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("2 releases for v0.4", error)
        self.assertEqual(github.writes, [])

    def test_a_tag_at_another_commit_without_a_published_release_writes_nothing_and_fails(self):
        for releases in ([], [{"tag_name": "v0.4", "draft": True}]):
            with self.subTest(releases=releases):
                github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", OTHER)}, releases=releases, ancestors=[OTHER])
                error, _, github = publish(TWO, github=github)
                self.assertIn("the tag v0.4 points at another commit than this one", error)
                self.assertEqual(github.writes, [])

    def test_a_tag_at_another_commit_that_is_not_earlier_writes_nothing_and_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", OTHER)}, releases=[{"tag_name": "v0.4", "draft": False}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("the tag v0.4 points at a commit that is not an earlier commit of this one", error)
        self.assertEqual(github.writes, [])

    def test_an_annotated_tag_writes_nothing_and_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("tag", SHA)}, releases=[{"tag_name": "v0.4", "draft": False}])
        error, _, github = publish(TWO, github=github)
        self.assertIn("the tag v0.4 points at another commit than this one", error)
        self.assertEqual(github.writes, [])

    def test_a_version_released_at_an_earlier_commit_is_done(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER), "0.4": ("commit", OTHER)}, releases=[{"tag_name": "v0.4", "draft": False}],
                            ancestors=[OTHER])
        error, out, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [])
        self.assertIn("v0.4 is released at an earlier commit, and this commit does not raise the version. Nothing to do", out)

    def test_a_refused_ref_creation_writes_nothing_more(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER)}, fail={("POST", PATH + "/git/refs"): 422})
        error, _, github = publish(TWO, github=github)
        self.assertIn("POST %s/git/refs: HTTP 422" % PATH, error)
        self.assertIn("The tag v0.4 was not created, and nothing was written", error)
        self.assertEqual(github.writes, [("POST", PATH + "/git/refs")])

    def test_a_tag_whose_target_does_not_match_after_creation_fails(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER)}, moves_tag_to=OTHER)
        error, _, github = publish(TWO, github=github)
        self.assertIn("read back, the tag v0.4 does not point at %s" % SHA, error)

    def test_a_created_tag_that_the_answer_puts_elsewhere_gets_no_release(self):
        class Elsewhere(FakeGitHub):
            def __call__(self, method, path, body=None):
                status, data = FakeGitHub.__call__(self, method, path, body)
                if method == "POST" and path.endswith("/git/refs"):
                    data = dict(data, object={"type": "commit", "sha": OTHER})
                return status, data
        github = Elsewhere(tags={"0.3": ("commit", EARLIER)})
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
                github = FakeGitHub(tags={"0.3": ("commit", EARLIER)}, fail={(method, path): 500})
                error, _, github = publish(TWO, github=github)
                self.assertIn("%s %s: HTTP 500" % (method, path), error)
                self.assertEqual(github.writes, writes)
                self.assertEqual(github.calls[-1][:2], (method, path))

    def test_a_failed_release_after_the_tag_says_how_to_finish(self):
        github = FakeGitHub(tags={"0.3": ("commit", EARLIER)}, fail={("POST", PATH + "/releases"): 500})
        error, _, github = publish(TWO, github=github)
        self.assertIn("The tag v0.4 is at %s and has no release. Re-run this run" % SHA, error)
        # The re-run finds the tag at this commit and creates only the release.
        del github.fail[("POST", PATH + "/releases")]
        github.calls = []
        error, _, github = publish(TWO, github=github)
        self.assertIsNone(error)
        self.assertEqual(github.writes, [("POST", PATH + "/releases")])

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


class Token(unittest.TestCase):
    """The token comes from GITHUB_TOKEN, goes only to api.github.com, and is never printed."""

    def run_main(self, github, argv=("publish",), environ=None):
        opener = FakeOpener(github)
        environ = environ if environ is not None else {"GITHUB_TOKEN": TOKEN, "GITHUB_REPOSITORY": REPO, "GITHUB_SHA": SHA}
        out, err = io.StringIO(), io.StringIO()
        code = release.main(list(argv), environ=environ, opener=opener, out=out, err=err)
        return code, out.getvalue(), err.getvalue(), opener

    def test_the_token_never_appears_in_output(self):
        scenarios = [
            FakeGitHub(tags=TAGGED),
            FakeGitHub(tags=TAGGED, fail={("POST", PATH + "/git/refs"): 422}),
            FakeGitHub(tags=TAGGED, fail={("POST", PATH + "/releases"): 500}),
            FakeGitHub(fail={("GET", PATH + "/git/matching-refs/tags/v"): 401}),
            FakeGitHub(tags=dict(TAGGED, **{NOW: ("commit", OTHER)})),
        ]
        for github in scenarios:
            with self.subTest(fail=github.fail):
                code, out, err, opener = self.run_main(github)
                self.assertNotIn(TOKEN, out + err)
                self.assertNotIn(TOKEN[4:20], out + err)
                self.assertNotIn(BODY_MARKER, out + err)
                self.assertTrue(opener.requests)
                for request in opener.requests:
                    self.assertTrue(request.full_url.startswith("https://api.github.com/repos/%s/" % REPO))
                    self.assertEqual(request.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertEqual(code, 1)
        self.assertIn("the tag v%s points at another commit than this one" % NOW, err)

    def test_a_publish_reads_the_version_from_ratchet_json(self):
        github = FakeGitHub(tags=TAGGED)
        code, out, err, opener = self.run_main(github)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(github.calls[-2][2]["tag_name"], "v" + NOW)
        self.assertIn("Tagged v%s at %s and released Ratchet %s" % (NOW, SHA, NOW), out)

    def test_an_error_gives_the_method_the_path_and_the_status(self):
        github = FakeGitHub(fail={("GET", PATH + "/git/matching-refs/tags/v"): 403})
        code, out, err, _ = self.run_main(github)
        self.assertEqual(code, 1)
        self.assertEqual(err, "release: GET %s/git/matching-refs/tags/v: HTTP 403. Nothing was written.\n" % PATH)

    def test_no_token_no_run(self):
        for environ in ({"GITHUB_REPOSITORY": REPO, "GITHUB_SHA": SHA},
                        {"GITHUB_TOKEN": "", "GITHUB_REPOSITORY": REPO, "GITHUB_SHA": SHA}):
            with self.subTest(environ=environ):
                code, _, err, opener = self.run_main(FakeGitHub(), environ=environ)
                self.assertEqual(code, 1)
                self.assertIn("GITHUB_TOKEN is not set", err)
                self.assertEqual(opener.requests, [])

    def test_the_repository_and_the_commit_are_read_strictly(self):
        for name, value in (("GITHUB_REPOSITORY", "owner/repo/../other"), ("GITHUB_REPOSITORY", "https://example.invalid/x"),
                            ("GITHUB_SHA", "A" * 40), ("GITHUB_SHA", SHA[:39]), ("GITHUB_SHA", SHA + "\n")):
            with self.subTest(name=name, value=value):
                environ = {"GITHUB_TOKEN": TOKEN, "GITHUB_REPOSITORY": REPO, "GITHUB_SHA": SHA}
                environ[name] = value
                code, _, err, opener = self.run_main(FakeGitHub(), environ=environ)
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
        entry = release.read_changelog(os.path.join(ROOT, "CHANGELOG.md"))[0]
        self.assertEqual(entry.version, NOW)
        self.assertEqual(out.getvalue(), release.release_text(entry, REPO) + "\n")
        self.assertIn("https://github.com/%s/blob/v%s/" % (REPO, NOW), out.getvalue())


class Workflow(unittest.TestCase):
    """The release workflow is thin, and it is the copy that was read with this script."""

    COPY = os.path.join(HERE, "fixtures", "release", "release.yml")
    LIVE = os.path.join(ROOT, ".github", "workflows", "release.yml")

    def lines(self):
        with open(self.COPY, "rb") as handle:
            return handle.read().decode("utf-8", errors="strict").split("\n")

    def test_the_workflow_is_the_copy_read_with_this_script(self):
        with open(self.COPY, "rb") as copy, open(self.LIVE, "rb") as live:
            self.assertEqual(live.read(), copy.read(), ".github/workflows/release.yml differs from checks/fixtures/release/release.yml")

    def test_the_workflow_keeps_its_form(self):
        lines = self.lines()
        self.assertIn("permissions:\n  contents: read\n", "\n".join(lines))
        self.assertEqual([l for l in lines if "contents: write" in l], ["      contents: write"])
        self.assertEqual([l.strip() for l in lines if "runs-on:" in l], ["runs-on: ubuntu-24.04"])
        self.assertEqual([l.strip() for l in lines if "timeout-minutes:" in l], ["timeout-minutes: 5"])
        uses = [l.strip() for l in lines if "uses:" in l]
        self.assertEqual(len(uses), 1)
        self.assertRegex(uses[0], r"^- uses: actions/checkout@[0-9a-f]{40} # v[0-9.]+\Z")
        self.assertIn("          persist-credentials: false", lines)
        runs = [l.strip() for l in lines if l.strip().startswith("run:")]
        self.assertEqual(runs, [
            "run: python3 checks/generate.py --check",
            "run: python3 checks/check_register.py register.json --markdown REGISTER.md",
            "run: python3 -m unittest discover -s checks",
            "run: python3 checks/release.py publish",
        ])
        self.assertFalse([l for l in lines if "run:" in l and "${{" in l])
        self.assertEqual([l.strip() for l in lines if "${{" in l], ["GITHUB_TOKEN: ${{ github.token }}"])
        self.assertLess(lines.index("          GITHUB_TOKEN: ${{ github.token }}"), lines.index("        run: python3 checks/release.py publish"))
        self.assertGreater(lines.index("          GITHUB_TOKEN: ${{ github.token }}"), lines.index("        run: python3 -m unittest discover -s checks"))


if __name__ == "__main__":
    unittest.main()
