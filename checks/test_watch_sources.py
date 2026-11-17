"""The watch on pinned sources must fail, write and stay quiet exactly where it claims to.

    python3 -m unittest discover -s checks -v

The HTTP layer is a fake that answers like the GitHub REST API and records every call.
No test reaches the network. Standard library only.
"""

import io
import json
import os
import re
import shutil
import tempfile
import unittest

import watch_sources

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCES = os.path.join(HERE, "fixtures", "sources")
API = "https://api.github.com"
TARGET = "example/ratchet"
BOT = "github-actions[bot]"
TOKEN = "ghs_FAKE-test-token-0123456789"

PIN = "0123456789abcdef0123456789abcdef01234567"
HEAD = "89abcdef0123456789abcdef0123456789abcdef"
NEWER = "fedcba9876543210fedcba9876543210fedcba98"

PLAIN = {"name": "example/plain", "repo": "https://github.com/example/plain", "commit": PIN, "license": "MIT"}
TOOLS = {
    "name": "example tools", "repo": "https://github.com/example/tools", "directory": "skills/one",
    "author": "A. Person", "commit": PIN, "license": "MIT",
}

# Fixture name -> the text the watch must print for it. Every message names the source.
MALFORMED = {
    "unknown-field": "source example/plain: unknown field 'pinned_by'",
    "missing-commit": "source example/plain: missing field 'commit'",
    "missing-name": "source 1: missing field 'name'",
    "short-commit": "source example/plain: the commit must be a full 40-character sha, in lowercase hex",
    "uppercase-commit": "source example/plain: the commit must be a full 40-character sha, in lowercase hex",
    "commit-line-break": "source example/plain: the commit must be a full 40-character sha, in lowercase hex",
    "commit-wrong-type": "source example/plain: the commit must be a full 40-character sha, in lowercase hex",
    "repo-with-text": "source pstack: the repo must be https://github.com/ and an owner and a repository, and nothing else",
    "repo-not-github": "source example/plain: the repo must be https://github.com/ and an owner and a repository",
    "repo-http": "source example/plain: the repo must be https://github.com/ and an owner and a repository",
    "repo-trailing-slash": "source example/plain: the repo must be https://github.com/ and an owner and a repository",
    "repo-dot-git": "source example/plain: the repo must be https://github.com/ and an owner and a repository",
    "repo-dots": "source example/plain: the repo must be https://github.com/ and an owner and a repository",
    "repo-query": "source example/plain: the repo must be https://github.com/ and an owner and a repository",
    "repo-line-break": "source example/plain: the repo must be https://github.com/ and an owner and a repository",
    "directory-parent": "source example tools: the directory must be a plain relative path inside the repository",
    "directory-inner-parent": "source example tools: the directory must be a plain relative path inside the repository",
    "directory-absolute": "source example tools: the directory must be a plain relative path inside the repository",
    "directory-trailing-slash": "source example tools: the directory must be a plain relative path inside the repository",
    "directory-empty": "source example tools: the directory must be a plain relative path inside the repository",
    "directory-backtick": "source example tools: the directory must be a plain relative path inside the repository",
    "name-twice": "source example/plain: the name is used twice",
    "name-empty": "source 1: the name holds no words",
    "author-not-on-the-list": "source example tools: author holds U+202E, which is not among the characters a value may hold",
    "license-pipe": "source example/plain: license must be one line, without |",
    "not-an-object": "source 1: a source must be an object",
    "not-a-list": "sources must be a list",
}


class FakeGitHub:
    """Answers like the GitHub REST API from a table of routes, and keeps the issues of the target repo."""

    def __init__(self):
        self.routes = {}
        self.calls = []
        self.unknown = []
        self.issues = []
        self.fail = None
        # The repository the watch writes in, and the number its first issue gets. Tests change both,
        # so that a watch that hard-codes either one fails.
        self.target = TARGET
        self.first_number = 100

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, dict(headers), body))
        if self.fail is not None:
            outcome = self.fail(method, url)
            if outcome is not None:
                return outcome
        if not url.startswith(API + "/"):
            self.unknown.append((method, url))
            return 404, b'{"message": "Not Found"}'
        path = url[len(API):]
        issues = "/repos/%s/issues" % self.target
        if method == "GET" and path.startswith(issues + "?"):
            return 200, json.dumps([i for i in self.issues if i["state"] == "open"]).encode("utf-8")
        if method == "POST" and path == issues:
            payload = json.loads(body.decode("utf-8"))
            issue = {"number": self.first_number + len(self.issues), "title": payload["title"], "body": payload["body"],
                     "state": "open", "user": {"login": BOT, "type": "Bot"}}
            self.issues.append(issue)
            return 201, json.dumps(issue).encode("utf-8")
        if method == "PATCH" and path.startswith(issues + "/"):
            number = int(path[len(issues) + 1:])
            issue = next(i for i in self.issues if i["number"] == number)
            issue.update(json.loads(body.decode("utf-8")))
            return 200, json.dumps(issue).encode("utf-8")
        if (method, path) in self.routes:
            status, answer = self.routes[(method, path)]
            return status, answer if isinstance(answer, bytes) else json.dumps(answer).encode("utf-8")
        self.unknown.append((method, url))
        return 404, b'{"message": "Not Found"}'

    def writes(self):
        return [call for call in self.calls if call[0] != "GET"]

    def gets(self):
        return [call[1][len(API):] for call in self.calls if call[0] == "GET"]

    def upstream(self, source, head, compare, branch="main"):
        """The answers of one source repository."""
        repo = source["repo"][len("https://github.com/"):]
        self.routes[("GET", "/repos/%s" % repo)] = (200, {"full_name": repo, "default_branch": branch})
        self.routes[("GET", "/repos/%s/branches/%s" % (repo, branch))] = (200, {"name": branch, "commit": {"sha": head}})
        if compare is not None:
            self.routes[("GET", "/repos/%s/compare/%s...%s" % (repo, source["commit"], head))] = (200, compare)

    def unchanged(self, source):
        self.upstream(source, source["commit"], comparison("identical", [], []))

    def add_issue(self, title, body, login=BOT, pull_request=False):
        issue = {"number": self.first_number + len(self.issues), "title": title, "body": body, "state": "open",
                 "user": {"login": login, "type": "Bot" if login == BOT else "User"}}
        if pull_request:
            issue["pull_request"] = {"url": "https://api.github.com/repos/%s/pulls/1" % TARGET}
        self.issues.append(issue)
        return issue


def commit(sha, message):
    return {"sha": sha, "commit": {"message": message}}


def changed(filename, status="modified", previous=None):
    entry = {"filename": filename, "status": status}
    if previous is not None:
        entry["previous_filename"] = previous
    return entry


def comparison(status, commits, files, ahead=None, behind=0, total=None):
    return {
        "status": status,
        "ahead_by": len(commits) if ahead is None else ahead,
        "behind_by": behind,
        "total_commits": len(commits) if total is None else total,
        "commits": commits,
        "files": files,
    }


def two_commits():
    return comparison("ahead", [commit(NEWER, "Add a step\n\nLonger text that is never copied."), commit(HEAD, "Fix a typo")],
                      [changed("README.md"), changed("docs/guide.md", "added")])


def fences(body):
    """The lines of the body outside fenced code blocks, and the lines inside them, as two lists."""
    outside, inside, fence = [], [], None
    for line in body.split("\n"):
        if fence is None:
            match = re.match(r"^(`{3,})text$", line)
            if match:
                fence = match.group(1)
            else:
                outside.append(line)
        elif line == fence:
            fence = None
        else:
            self_check = re.match(r"^ {0,3}(`{3,})\s*$", line)
            if self_check and len(self_check.group(1)) >= len(fence):
                raise AssertionError("a line inside a code block closes it: %r" % line)
            inside.append(line)
    if fence is not None:
        raise AssertionError("a code block is not closed")
    return outside, inside


def outside_code(body):
    """The text of a body outside fenced code blocks and outside code spans, as GitHub reads Markdown.

    A run of backticks opens a code span that the next run of exactly as many backticks closes. A run
    that is never closed stands as text.
    """
    text = "\n".join(fences(body)[0])
    kept, at = [], 0
    while at < len(text):
        if text[at] != "`":
            kept.append(text[at])
            at += 1
            continue
        run = re.match(r"`+", text[at:]).group(0)
        close = re.search(r"(?<!`)%s(?!`)" % run, text[at + len(run):])
        if close is None:
            kept.append(run)
            at += len(run)
        else:
            at += len(run) + close.end()
    return "".join(kept)


def limited(github, refused):
    """An HTTP layer that refuses, as GitHub does, an issue whose title or body is too long, and records it."""
    def call(method, url, headers, body):
        if method in ("POST", "PATCH"):
            payload = json.loads(body.decode("utf-8"))
            if len(payload.get("body", "")) > 65536 or len(payload.get("title", "")) > 256:
                refused.append((method, len(payload.get("title", "")), len(payload.get("body", ""))))
                return 422, b'{"message": "Validation Failed"}'
        return github(method, url, headers, body)
    return call


class Watch(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, self.directory)
        self.github = FakeGitHub()

    def data(self, sources):
        """A copy of ratchet.json with these sources, and its path."""
        with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as handle:
            data = json.load(handle)
        data["sources"] = sources
        path = os.path.join(self.directory, "ratchet.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2, ensure_ascii=True) + "\n")
        return path

    def watch(self, sources, token=TOKEN, target=TARGET, http=None):
        environ = {}
        if token is not None:
            environ["GITHUB_TOKEN"] = token
        if target is not None:
            environ["GITHUB_REPOSITORY"] = target
        out, err = io.StringIO(), io.StringIO()
        code = watch_sources.main(["--data", self.data(sources)], environ=environ,
                                  http=http or self.github, stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def assert_no_writes(self):
        self.assertEqual(self.github.writes(), [])

    def assert_no_unknown_calls(self):
        self.assertEqual(self.github.unknown, [])

    def only_issue(self):
        self.assertEqual(len(self.github.issues), 1, self.github.issues)
        return self.github.issues[0]

    # The cases the issue asks for.

    def test_an_unchanged_source_writes_nothing(self):
        self.github.unchanged(PLAIN)
        self.github.unchanged(TOOLS)
        code, out, err = self.watch([PLAIN, TOOLS])
        self.assertEqual(code, 0, err)
        self.assertEqual(self.github.gets(), [
            "/repos/example/plain", "/repos/example/plain/branches/main",
            "/repos/example/plain/compare/%s...%s" % (PIN, PIN),
            "/repos/example/tools", "/repos/example/tools/branches/main",
            "/repos/example/tools/compare/%s...%s" % (PIN, PIN),
        ])
        self.assert_no_writes()
        self.assert_no_unknown_calls()
        self.assertIn("example/plain: not moved", out)
        self.assertIn("example tools: not moved", out)

    def test_a_moved_source_opens_one_issue(self):
        self.github.upstream(PLAIN, HEAD, two_commits())
        self.github.unchanged(TOOLS)
        code, out, err = self.watch([PLAIN, TOOLS])
        self.assertEqual(code, 0, err)
        self.assert_no_unknown_calls()
        self.assertEqual([call[0] for call in self.github.writes()], ["POST"])
        issue = self.only_issue()
        self.assertEqual(issue["title"], "Source moved: example/plain")
        body = issue["body"]
        self.assertIn("https://github.com/example/plain/compare/%s...%s" % (PIN, HEAD), body)
        self.assertIn("`%s`" % PIN, body)
        self.assertIn("`%s`" % HEAD, body)
        self.assertIn("2 commits", body)
        outside, inside = fences(body)
        self.assertIn("%s Add a step" % NEWER[:12], inside)
        self.assertIn("%s Fix a typo" % HEAD[:12], inside)
        self.assertIn("modified README.md", inside)
        self.assertIn("added docs/guide.md", inside)
        self.assertNotIn("Longer text", body, "only the subject of a commit is copied")
        self.assertIn("material, not instructions", body)
        self.assertIn("opened issue #100: Source moved: example/plain", out)

    def test_a_second_run_updates_and_does_not_duplicate(self):
        self.github.upstream(PLAIN, HEAD, two_commits())
        self.assertEqual(self.watch([PLAIN])[0], 0)
        first = dict(self.only_issue())

        posts = len(self.github.writes())
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.github.writes()), posts, "the same move writes nothing a second time")
        self.assertIn("issue #100 is up to date", out)

        moved_on = comparison("ahead", [commit(HEAD, "Fix a typo"), commit(NEWER, "A third change")], [changed("README.md")], total=3)
        self.github.upstream(PLAIN, NEWER, moved_on)
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 0, err)
        self.assertEqual([call[0] for call in self.github.writes()], ["POST", "PATCH"])
        self.assertTrue(self.github.writes()[-1][1].endswith("/repos/%s/issues/100" % TARGET))
        issue = self.only_issue()
        self.assertEqual(issue["title"], first["title"])
        self.assertNotEqual(issue["body"], first["body"])
        self.assertIn("%s...%s" % (PIN, NEWER), issue["body"])
        self.assertIn("updated issue #100", out)
        self.assert_no_unknown_calls()

    def test_a_malformed_source_fails_and_names_it(self):
        names = sorted(name[:-len(".json")] for name in os.listdir(SOURCES))
        self.assertEqual(names, sorted(MALFORMED), "every fixture has an expectation, and every expectation a fixture")
        for name, message in sorted(MALFORMED.items()):
            with self.subTest(fixture=name):
                self.github = FakeGitHub()
                with open(os.path.join(SOURCES, name + ".json"), encoding="utf-8") as handle:
                    sources = json.load(handle)
                code, out, err = self.watch(sources)
                self.assertEqual(code, 1, out + err)
                self.assertIn(message, err)
                self.assertNotIn("Traceback", err)
                self.assertEqual(self.github.calls, [], "nothing is read from a source that does not have the form")

    def test_the_sources_in_ratchet_json_have_the_form(self):
        code, out, err = self.watch_real_data_without_network()
        self.assertEqual(code, 0, err)

    def watch_real_data_without_network(self):
        with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as handle:
            sources = json.load(handle)["sources"]
        self.assertTrue(any("directory" in source for source in sources))
        for source in sources:
            self.github.unchanged(source)
        return self.watch(sources)

    def test_an_api_error_fails_without_writing(self):
        def status(code, text):
            return lambda method, url: (code, text) if url.endswith("/repos/example/tools") else None

        def unreadable(method, url):
            return (200, b"{not json") if "/compare/" in url and "example/tools" in url else None

        def unreachable(method, url):
            if url.endswith("/repos/example/tools"):
                raise OSError("connection refused")
            return None

        def issues_fail(method, url):
            return (502, b"Bad gateway") if "/repos/%s/issues" % TARGET in url else None

        cases = {
            "server error": (status(500, b'{"message": "Server Error"}'), "GET /repos/example/tools gave 500"),
            "rate limit": (status(403, b'{"message": "API rate limit exceeded"}'), "GET /repos/example/tools gave 403"),
            "missing repo": (status(404, b'{"message": "Not Found"}'), "GET /repos/example/tools gave 404"),
            "not json": (unreadable, "is not valid JSON"),
            "network": (unreachable, "GET /repos/example/tools could not be read: connection refused"),
            "issue list": (issues_fail, "GET /repos/%s/issues" % TARGET),
        }
        for name, (fail, message) in cases.items():
            with self.subTest(case=name):
                self.github = FakeGitHub()
                self.github.upstream(PLAIN, HEAD, two_commits())
                self.github.upstream(TOOLS, HEAD, comparison("ahead", [commit(HEAD, "Change")], [changed("skills/one/a.md")]))
                self.github.fail = fail
                code, out, err = self.watch([PLAIN, TOOLS])
                self.assertEqual(code, 1, out + err)
                self.assertIn(message, err)
                self.assertNotIn("Traceback", err)
                self.assert_no_writes()
                self.assertEqual(self.github.issues, [])

    def test_a_missing_pin_gets_its_own_issue(self):
        self.github.upstream(PLAIN, HEAD, None)
        self.github.routes[("GET", "/repos/example/plain/commits/%s" % PIN)] = (422, {"message": "No commit found for SHA"})
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 0, err)
        issue = self.only_issue()
        self.assertEqual(issue["title"], "Source pin missing: example/plain")
        self.assertIn("`%s`" % PIN, issue["body"])
        self.assertIn("has no commit", issue["body"])
        self.assertIn("/repos/example/plain/commits/%s" % PIN, self.github.gets())
        self.assertIn("example/plain: the pinned commit is missing upstream", out)

    def test_a_missing_pin_and_a_move_are_different_issues(self):
        self.github.add_issue("Source moved: example/plain", "an earlier move")
        self.github.upstream(PLAIN, HEAD, None)
        self.github.routes[("GET", "/repos/example/plain/commits/%s" % PIN)] = (404, {"message": "Not Found"})
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 0, err)
        self.assertEqual([call[0] for call in self.github.writes()], ["POST"])
        self.assertEqual(self.github.issues[0]["body"], "an earlier move")

    def test_a_compare_that_fails_while_the_pin_exists_fails_the_run(self):
        self.github.upstream(PLAIN, HEAD, None)
        self.github.routes[("GET", "/repos/example/plain/commits/%s" % PIN)] = (200, commit(PIN, "The pin"))
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 1, out + err)
        self.assertIn("source example/plain: the compare gave 404 although the pinned commit exists", err)
        self.assert_no_writes()

    def test_a_directory_source_with_changes_only_outside_its_directory_writes_nothing(self):
        outside = comparison("ahead", [commit(HEAD, "Change other skills")], [
            changed("README.md"), changed("skills/one-more/a.md"), changed("skills/onex"),
            changed("skills/two/one/a.md"), changed("other/skills/one/a.md"),
        ])
        self.github.upstream(TOOLS, HEAD, outside)
        code, out, err = self.watch([TOOLS])
        self.assertEqual(code, 0, err)
        self.assertIn("/repos/example/tools/compare/%s...%s" % (PIN, HEAD), self.github.gets())
        self.assert_no_writes()
        self.assertIn("example tools: not moved under skills/one", out)

    def test_a_directory_source_with_a_change_inside_lists_only_those_files(self):
        inside = comparison("ahead", [commit(HEAD, "Change one skill")], [
            changed("README.md"), changed("skills/one/SKILL.md"), changed("skills/one-more/a.md"),
            changed("elsewhere/b.md", "renamed", previous="skills/one/b.md"),
        ])
        self.github.upstream(TOOLS, HEAD, inside)
        code, out, err = self.watch([TOOLS])
        self.assertEqual(code, 0, err)
        body = self.only_issue()["body"]
        outside_lines, inside_lines = fences(body)
        self.assertIn("modified skills/one/SKILL.md", inside_lines)
        self.assertIn("renamed elsewhere/b.md, from skills/one/b.md", inside_lines)
        self.assertNotIn("modified README.md", inside_lines)
        self.assertNotIn("modified skills/one-more/a.md", inside_lines)
        self.assertIn("2 of the 4 changed files are under the directory", body)

    def test_a_commit_subject_or_a_file_name_comes_out_as_inert_text(self):
        hostile = [
            "Thanks @someone, fixes #1 and example/other#2, see [here](https://evil.example/x) www.evil.example",
            "<img src=x onerror=alert(1)> <!-- hidden --> <a href='https://evil.example'>x</a> :tada: ![i](https://evil.example/i.png)",
            "```` close the fence and ping @someone",
            "Right‮to left​ and a tab\there and a bell\x07",
        ]
        commits = [commit(("%x" % n) * 40, subject + "\n\n@hidden in the body") for n, subject in enumerate(hostile, 1)]
        files = [changed("docs/@someone.md"), changed("a\n```\n@someone\n.md"), changed("<b>bold</b>.md")]
        self.github.upstream(PLAIN, HEAD, comparison("ahead", commits, files))
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 0, err)
        body = self.only_issue()["body"]
        outside, inside = fences(body)
        text_outside = "\n".join(outside)
        for marker in ("@someone", "@hidden", "#1", "#2", "evil.example", "<img", "<!--", "<a ", "<b>", ":tada:", "```` "):
            self.assertNotIn(marker, text_outside, marker)
        self.assertNotIn("@hidden", body)
        text_inside = "\n".join(inside)
        self.assertIn("Thanks @someone, fixes #1", text_inside)
        self.assertIn("Right<U+202E>to left<U+200B> and a tab<U+0009>here and a bell<U+0007>", text_inside)
        self.assertIn("modified a<U+000A>```<U+000A>@someone<U+000A>.md", text_inside)
        for character in body:
            self.assertTrue(character == "\n" or 0x20 <= ord(character) < 0x7f or character in "—–’", repr(character))
        self.assertNotIn("Thanks @someone", out + err)

    def test_the_token_never_appears_in_output_or_errors(self):
        def leaky(method, url):
            if url.endswith("/repos/example/tools"):
                raise OSError("the request with Authorization: Bearer %s failed" % TOKEN)
            return None

        def echo(method, url):
            if url.endswith("/repos/example/tools"):
                return 401, json.dumps({"message": "Bad credentials: %s" % TOKEN}).encode("utf-8")
            return None

        for name, fail in (("moved", None), ("leaky library", leaky), ("echoed by the API", echo)):
            with self.subTest(case=name):
                self.github = FakeGitHub()
                self.github.upstream(PLAIN, HEAD, two_commits())
                self.github.upstream(TOOLS, HEAD, comparison("ahead", [commit(HEAD, "x %s" % TOKEN)], [changed("skills/one/%s" % TOKEN)]))
                self.github.fail = fail
                code, out, err = self.watch([PLAIN, TOOLS])
                self.assertTrue(self.github.calls)
                self.assertTrue(all(call[2].get("Authorization") == "Bearer " + TOKEN for call in self.github.calls),
                                "the token is sent, so the test can see it if it leaks")
                self.assertNotIn(TOKEN, out)
                self.assertNotIn(TOKEN, err)
                self.assertNotIn(TOKEN[4:], out + err)
                for issue in self.github.issues:
                    self.assertNotIn(TOKEN, issue["title"] + issue["body"])
                if fail is None:
                    self.assertEqual(code, 0, err)
                    self.assertEqual(len(self.github.issues), 2)
                else:
                    self.assertEqual(code, 1, out + err)

    # What the watch does besides, as its documentation says.

    def test_without_a_token_the_reads_run_and_the_writes_are_refused(self):
        self.github.upstream(PLAIN, HEAD, two_commits())
        code, out, err = self.watch([PLAIN], token=None)
        self.assertEqual(code, 1, out + err)
        self.assertIn("GITHUB_TOKEN is not set", err)
        self.assertIn("Source moved: example/plain", err)
        self.assertIn("/repos/example/plain/compare/%s...%s" % (PIN, HEAD), self.github.gets())
        self.assertTrue(all("Authorization" not in call[2] for call in self.github.calls))
        self.assert_no_writes()

    def test_without_a_token_and_nothing_moved_the_run_passes(self):
        self.github.unchanged(PLAIN)
        code, out, err = self.watch([PLAIN], token=None, target=None)
        self.assertEqual(code, 0, err)
        self.assertIn("example/plain: not moved", out)
        self.assert_no_writes()

    def test_an_empty_token_counts_as_no_token(self):
        self.github.upstream(PLAIN, HEAD, two_commits())
        code, out, err = self.watch([PLAIN], token="")
        self.assertEqual(code, 1, out + err)
        self.assertIn("GITHUB_TOKEN is not set", err)
        self.assertTrue(all("Authorization" not in call[2] for call in self.github.calls))
        self.assert_no_writes()

    def test_a_target_that_is_not_owner_and_repo_fails_without_writing(self):
        for target in (None, "", "example", "example/ratchet/extra", "example/../x", "exa mple/ratchet"):
            with self.subTest(target=target):
                self.github = FakeGitHub()
                self.github.upstream(PLAIN, HEAD, two_commits())
                code, out, err = self.watch([PLAIN], target=target)
                self.assertEqual(code, 1, out + err)
                self.assertIn("GITHUB_REPOSITORY", err)
                self.assert_no_writes()

    def test_a_diverged_or_behind_branch_opens_an_issue(self):
        cases = {
            "diverged": (comparison("diverged", [commit(HEAD, "Rewritten")], [changed("README.md")], behind=2),
                         "ahead of the pin by 1 commit and behind it by 2 commits"),
            "behind": (comparison("behind", [], [changed("README.md", "removed")], behind=3),
                       "ahead of the pin by 0 commits and behind it by 3 commits"),
        }
        for name, (answer, words) in cases.items():
            with self.subTest(status=name):
                self.github = FakeGitHub()
                self.github.upstream(TOOLS, HEAD, answer)
                code, out, err = self.watch([TOOLS])
                self.assertEqual(code, 0, err)
                body = self.only_issue()["body"]
                self.assertIn("Status: %s" % name, body)
                self.assertIn(words, body)
                self.assertIn("The pinned commit is not in the history of the default branch", body)

    def test_lists_that_the_api_caps_say_so(self):
        commits = [commit("%040x" % n, "Change %d" % n) for n in range(250)]
        files = [changed("file-%d.md" % n) for n in range(300)]
        self.github.upstream(PLAIN, HEAD, comparison("ahead", commits, files, total=400))
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 0, err)
        body = self.only_issue()["body"]
        self.assertIn("400 commits", body)
        self.assertIn("The API lists 250 of the 400 commits", body)
        self.assertIn("The API lists at most 300 changed files", body)
        outside, inside = fences(body)
        self.assertIn("Change 99", "\n".join(inside))
        self.assertNotIn("Change 100", "\n".join(inside))
        self.assertIn("This issue shows the first 100 of the 250 commits", body)
        self.assertIn("This issue shows the first 200 of the 300 files", body)
        self.assertLess(len(body), 65536)

    def test_a_directory_source_whose_file_list_is_capped_opens_an_issue(self):
        files = [changed("other/file-%d.md" % n) for n in range(300)]
        self.github.upstream(TOOLS, HEAD, comparison("ahead", [commit(HEAD, "Many changes")], files))
        code, out, err = self.watch([TOOLS])
        self.assertEqual(code, 0, err)
        body = self.only_issue()["body"]
        self.assertIn("none of the files it lists is under the directory", body)

    def test_an_issue_by_someone_else_with_the_same_title_is_not_edited(self):
        self.github.add_issue("Source moved: example/plain", "a stranger's text", login="stranger")
        self.github.add_issue("Source moved: example/plain", "a pull request", pull_request=True)
        self.github.upstream(PLAIN, HEAD, two_commits())
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 0, err)
        self.assertEqual([call[0] for call in self.github.writes()], ["POST"])
        self.assertEqual(self.github.issues[0]["body"], "a stranger's text")
        self.assertEqual(self.github.issues[1]["body"], "a pull request")

    def test_two_open_issues_of_its_own_with_one_title_fail_without_writing(self):
        self.github.add_issue("Source moved: example/plain", "one")
        self.github.add_issue("Source moved: example/plain", "two")
        self.github.upstream(PLAIN, HEAD, two_commits())
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 1, out + err)
        self.assertIn("issues #100 and #101 are both open", err)
        self.assert_no_writes()

    def test_an_answer_of_an_unknown_form_fails_without_writing(self):
        good = two_commits()
        cases = {
            "unknown status": dict(good, status="sideways"),
            "short sha": dict(good, commits=[commit("abc123", "Short")]),
            "message not text": dict(good, commits=[commit(HEAD, ["list"])]),
            "unknown file status": dict(good, files=[changed("README.md", "teleported")]),
            "count not a number": dict(good, total_commits="2"),
            "count is a boolean": dict(good, ahead_by=True),
            "file name not text": dict(good, files=[{"filename": 3, "status": "added"}]),
        }
        for name, answer in cases.items():
            with self.subTest(case=name):
                self.github = FakeGitHub()
                self.github.upstream(PLAIN, HEAD, answer)
                code, out, err = self.watch([PLAIN])
                self.assertEqual(code, 1, out + err)
                self.assertIn("source example/plain:", err)
                self.assertNotIn("Traceback", err)
                self.assert_no_writes()

    def test_a_branch_or_a_head_of_an_unknown_form_fails_without_writing(self):
        for branch, head in (("main\n", HEAD), ("../main", HEAD), ("ma`in", HEAD), ("main", "HEAD"), ("main", HEAD.upper())):
            with self.subTest(branch=branch, head=head):
                self.github = FakeGitHub()
                self.github.upstream(PLAIN, head, two_commits(), branch=branch)
                code, out, err = self.watch([PLAIN])
                self.assertEqual(code, 1, out + err)
                self.assertIn("source example/plain:", err)
                self.assert_no_writes()

    def test_every_read_comes_before_any_write(self):
        self.github.upstream(PLAIN, HEAD, two_commits())
        self.github.upstream(TOOLS, HEAD, comparison("ahead", [commit(HEAD, "Change")], [changed("skills/one/a.md")]))
        code, out, err = self.watch([PLAIN, TOOLS])
        self.assertEqual(code, 0, err)
        methods = [call[0] for call in self.github.calls]
        self.assertEqual(methods.count("POST"), 2)
        first_write = methods.index("POST")
        self.assertEqual(set(methods[:first_write]), {"GET"})
        self.assertEqual(set(methods[first_write:]), {"POST"})

    def test_the_pinned_directory_is_written_as_before_in_ratchet_md(self):
        import registry
        with open(os.path.join(ROOT, "ratchet.json"), encoding="utf-8") as handle:
            sources = json.load(handle)["sources"]
        pstack = next(source for source in sources if source["name"] == "pstack")
        self.assertEqual(registry.source_repo_text(pstack), "https://github.com/cursor/plugins, directory `pstack` (by Lauren Tan)")
        plain = next(source for source in sources if source["name"] == "obra/superpowers")
        self.assertEqual(registry.source_repo_text(plain), "https://github.com/obra/superpowers")


    # Round 1 of the review. Finding 1: moved means that the head is not the pin.

    def test_an_ahead_compare_with_no_changed_file_is_a_move(self):
        self.github.upstream(PLAIN, HEAD, comparison("ahead", [commit(HEAD, "An empty commit")], []))
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 0, err)
        body = self.only_issue()["body"]
        self.assertIn("0 files changed", body)
        self.assertIn("No file differs between the pin and the head", body)
        self.assertIn("source example/plain: moved, ahead", out)

    def test_a_directory_source_whose_branch_moved_without_a_changed_file_says_so(self):
        self.github.upstream(TOOLS, HEAD, comparison("ahead", [commit(HEAD, "An empty commit")], []))
        code, out, err = self.watch([TOOLS])
        self.assertEqual(code, 0, err)
        self.assert_no_writes()
        self.assertIn("source example tools: not moved under skills/one: the branch is 1 commit ahead of the pin, "
                      "and no file differs between the pin and the head", out)

    def test_a_directory_source_whose_compare_lists_no_files_opens_an_issue(self):
        answer = comparison("ahead", [commit(HEAD, "A change")], [])
        del answer["files"]
        self.github.upstream(TOOLS, HEAD, answer)
        code, out, err = self.watch([TOOLS])
        self.assertEqual(code, 0, err)
        body = self.only_issue()["body"]
        self.assertIn("The API did not list the changed files. Files under the directory may have changed.", body)

    def test_a_compare_that_disagrees_with_the_head_fails_without_writing(self):
        cases = {
            "identical, but the head is not the pin": (HEAD, comparison("identical", [], [])),
            "ahead, but the head is the pin": (PIN, two_commits()),
        }
        for name, (head, answer) in cases.items():
            with self.subTest(case=name):
                self.github = FakeGitHub()
                self.github.upstream(PLAIN, head, answer)
                code, out, err = self.watch([PLAIN])
                self.assertEqual(code, 1, out + err)
                self.assertIn("source example/plain: the compare says", err)
                self.assert_no_writes()

    # Finding 2: every title and body is built and checked before the first write.

    def worst_case(self):
        """A plain source and a directory source, each at every cap, with the longest lines the watch writes."""
        wide = "é€\u0007@`<" * 100
        commits = [commit("%040x" % n, wide) for n in range(250)]
        files = [changed("skills/one/" + wide + "%04d" % n, "unchanged", "skills/one/" + wide + "%04d-old" % n)
                 for n in range(300)]
        answer = comparison("diverged", commits, files, ahead=250, behind=9, total=4000)
        plain = dict(PLAIN, name="P" * 4000)
        tools = dict(TOOLS, name="T" * 4000, directory="skills/one")
        self.github.upstream(plain, HEAD, answer, branch="b" * 250)
        self.github.upstream(tools, HEAD, answer, branch="b" * 250)
        return [plain, tools]

    def test_every_title_and_body_fits_what_github_takes(self):
        sources = self.worst_case()
        refused = []
        code, out, err = self.watch(sources, http=limited(self.github, refused))
        self.assertEqual(refused, [])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.github.issues), 2)
        for issue in self.github.issues:
            self.assertLessEqual(len(issue["body"].encode("utf-8")), 65536)
            self.assertLessEqual(len(issue["title"].encode("utf-8")), 256)
            fences(issue["body"])

    def test_a_plan_that_breaks_a_limit_writes_nothing(self):
        self.github.upstream(PLAIN, HEAD, two_commits())
        files = [changed("skills/one/%s-%04d.md" % ("x" * 300, n)) for n in range(300)]
        self.github.upstream(TOOLS, HEAD, comparison("ahead", [commit(HEAD, "Many")], files))
        refused = []
        saved = watch_sources.SHOW_FILES, watch_sources.FILE_LENGTH
        watch_sources.SHOW_FILES, watch_sources.FILE_LENGTH = 300, 1000
        try:
            code, out, err = self.watch([PLAIN, TOOLS], http=limited(self.github, refused))
        finally:
            watch_sources.SHOW_FILES, watch_sources.FILE_LENGTH = saved
        self.assertEqual(code, 1, out + err)
        self.assertIn("nothing is written", err)
        self.assertIn("Source moved: example tools", err)
        self.assertIn("65536", err)
        self.assertEqual(refused, [])
        self.assert_no_writes()

    def test_two_sources_whose_titles_come_out_the_same_write_nothing(self):
        one = dict(PLAIN, name="N" * 300 + " one")
        two = dict(TOOLS, name="N" * 300 + " two")
        self.github.upstream(one, HEAD, two_commits())
        self.github.upstream(two, HEAD, comparison("ahead", [commit(HEAD, "A change")], [changed("skills/one/a.md")]))
        code, out, err = self.watch([one, two])
        self.assertEqual(code, 1, out + err)
        self.assertIn("two issues would have the title", err)
        self.assert_no_writes()

    # Finding 3: every value that reaches GitHub or a log passes through one renderer.

    HOSTILE_NAME = ("@someone [click](https://evil.example/x) <img src=x> ![i](https://evil.example/i.png) "
                    "<!-- c --> fixes #1 and example/other#2 www.evil.example **bold** `code` ::warning file=a::x")
    MARKERS = ("@someone", "#1", "#2", "evil.example", "<img", "<!--", "](", "**", "::warning")

    def test_a_source_name_is_inert_in_the_title_the_body_and_the_output(self):
        import registry
        moved = dict(PLAIN, name=self.HOSTILE_NAME)
        gone = dict(TOOLS, name=self.HOSTILE_NAME + " gone")
        self.assertEqual(registry.source_problems([moved, gone]), [], "the names pass the form of a source")
        self.github.upstream(moved, HEAD, two_commits())
        self.github.upstream(gone, HEAD, None)
        self.github.routes[("GET", "/repos/example/tools/commits/%s" % PIN)] = (404, {"message": "Not Found"})
        code, out, err = self.watch([moved, gone])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.github.issues), 2)
        for issue in self.github.issues:
            text = outside_code(issue["body"])
            for marker in self.MARKERS:
                self.assertNotIn(marker, text, marker)
            self.assertIn(self.HOSTILE_NAME, issue["body"], "the name is there, inside a code span")
            for marker in self.MARKERS + ("[", "`", "!", "*", "@", "#", ":warning"):
                self.assertNotIn(marker, issue["title"][issue["title"].index(":") + 1:], marker)
        for line in (out + err).splitlines():
            self.assertRegex(line, r"^[A-Za-z]", "a line the watch prints starts with its own text")

    def test_a_line_the_watch_prints_never_starts_with_upstream_text(self):
        def leaky(method, url):
            if url.endswith("/repos/example/plain"):
                raise OSError("refused\n::warning file=a::injected\n##[error]old form")
            return None
        self.github.fail = leaky
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 1, out + err)
        self.assertIn("injected", err)
        for line in (out + err).splitlines():
            self.assertRegex(line, r"^[A-Za-z|]", line)
            self.assertFalse(line.startswith("::") or line.startswith("##"), line)

    def test_only_rendered_values_reach_a_body(self):
        with self.assertRaises(TypeError):
            watch_sources.compose("- Source: %s", "@someone")
        with self.assertRaises(TypeError):
            watch_sources.compose("- Source: %s", watch_sources.inert("@someone", 100))
        self.assertEqual(watch_sources.compose("- Source: %s", watch_sources.code("@someone")), "- Source: `@someone`")
        self.assertEqual(watch_sources.code("a `b` c"), "``a `b` c``")
        self.assertEqual(watch_sources.code("`b`"), "`` `b` ``")
        with self.assertRaises(TypeError):
            watch_sources.fence(["not rendered"])

    # Finding 4: the token is scrubbed from decoded text, and no body that holds it is written.

    def test_an_escaped_token_in_an_answer_is_scrubbed_after_decoding(self):
        escaped = "".join("\\u%04x" % ord(c) for c in TOKEN)
        raw = json.dumps(comparison("ahead", [commit(HEAD, "Echo TOKEN")], [changed("README.md")])).replace("TOKEN", escaped)
        self.github.upstream(PLAIN, HEAD, raw.encode("ascii"))
        code, out, err = self.watch([PLAIN])
        self.assertEqual(code, 0, err)
        body = self.only_issue()["body"]
        self.assertNotIn(TOKEN, body)
        self.assertIn("Echo ***", body)

    def test_a_body_that_holds_the_token_in_a_readable_form_is_not_written(self):
        forms = {
            "split by a character off the list": TOKEN[:8] + "​" + TOKEN[8:],
            "in capitals": TOKEN.upper(),
            "percent-encoded": "".join("%%%02X" % ord(c) for c in TOKEN),
            "as HTML entities": "".join("&#%d;" % ord(c) for c in TOKEN),
            "split by spaces": " ".join(TOKEN),
        }
        for name, form in forms.items():
            with self.subTest(form=name):
                self.github = FakeGitHub()
                self.github.upstream(PLAIN, HEAD, two_commits())
                self.github.upstream(TOOLS, HEAD, comparison("ahead", [commit(HEAD, "Echo " + form)], [changed("skills/one/a.md")]))
                code, out, err = self.watch([PLAIN, TOOLS])
                self.assertEqual(code, 1, out + err)
                self.assertIn("holds the token", err)
                self.assertIn("Source moved: example tools", err)
                self.assert_no_writes()
                self.assertNotIn(TOKEN, out + err)

    # Finding 5: every value read from the API is tried with a value a hard-coded constant would get wrong.

    def test_values_read_from_the_api_are_used_and_not_assumed(self):
        other = {"name": "other", "repo": "https://github.com/someone-else/thing", "commit": NEWER, "license": "MIT"}
        tip = "%040x" % 0xabc
        self.github.target = "another-owner/another-repo"
        self.github.first_number = 4242
        self.github.add_issue("an issue by someone else", "theirs", login="stranger")
        self.github.add_issue("Source moved: other", "an earlier report")
        answer = comparison("diverged", [commit(tip, "Rewrite")], [changed("a.md", "renamed", "b.md")],
                            ahead=7, behind=3, total=11)
        self.github.upstream(other, tip, answer, branch="trunk/next")
        self.github.upstream(PLAIN, HEAD, comparison("ahead", [commit(HEAD, "One")], [changed("c.md", "removed")]))
        code, out, err = self.watch([other, PLAIN], target="another-owner/another-repo")
        self.assertEqual(code, 0, err)
        self.assert_no_unknown_calls()
        self.assertIn("/repos/someone-else/thing/branches/trunk/next", self.github.gets())
        self.assertIn("/repos/someone-else/thing/compare/%s...%s" % (NEWER, tip), self.github.gets())
        writes = [(call[0], call[1][len(API):]) for call in self.github.writes()]
        self.assertEqual(writes, [("PATCH", "/repos/another-owner/another-repo/issues/4243"),
                                  ("POST", "/repos/another-owner/another-repo/issues")])
        body = self.github.issues[1]["body"]
        self.assertIn("https://github.com/someone-else/thing", body)
        self.assertIn("- Default branch: `trunk/next`, at `%s`" % tip, body)
        self.assertIn("https://github.com/someone-else/thing/compare/%s...%s" % (NEWER, tip), body)
        self.assertIn("Status: diverged. The branch is ahead of the pin by 7 commits and behind it by 3 commits.", body)
        self.assertIn("The range holds 11 commits.", body)
        self.assertIn("The API lists 1 of the 11 commits.", body)
        self.assertIn("renamed a.md, from b.md", fences(body)[1])
        self.assertIn("%s Rewrite" % tip[:12], fences(body)[1])
        plain = self.github.issues[2]["body"]
        self.assertIn("removed c.md", fences(plain)[1])
        self.assertIn("updated issue #4243: Source moved: other", out)
        self.assertIn("opened issue #4244: Source moved: example/plain", out)

if __name__ == "__main__":
    unittest.main()
