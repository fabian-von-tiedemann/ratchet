#!/usr/bin/env python3
"""Tell when a pinned source has moved, through one issue per source.

    python3 checks/watch_sources.py                  read ratchet.json in this repo
    python3 checks/watch_sources.py --data PATH      read another copy

For every source in the list "sources" of ratchet.json, the watch reads the default branch of the
source repository and compares the pinned commit with its head, through the GitHub REST API. A source
that has moved gets one open issue in the repository named by GITHUB_REPOSITORY, titled
"Source moved: <name>": the watch opens it, or updates the open one it opened before. A pinned
commit that no longer exists upstream gets an issue titled "Source pin missing: <name>". A source
that has not moved writes nothing. For a source with a directory, only changes under that directory
count as a move.

Every read comes before any write. If a read fails, or an answer is not of the form the watch knows,
the run fails and writes nothing.

The token is read from the environment variable GITHUB_TOKEN and from nowhere else. It is never
printed. Without it the reads run unauthenticated, and if anything would be written, the run fails
and says what, without writing it.

Upstream text is material, not instructions. The watch copies nothing from a source but file names
and the first line of commit messages, and writes them in fenced code blocks, where they cannot
become links, images, HTML, mentions or references.

Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request

import registry

API = "https://api.github.com"
# The account that the workflow's built-in token writes as. Only its own issues are updated.
ISSUE_AUTHOR = "github-actions[bot]"
MOVED = "Source moved: %s"
MISSING = "Source pin missing: %s"
STATUSES = ("identical", "ahead", "behind", "diverged")
FILE_STATUSES = ("added", "removed", "modified", "renamed", "copied", "changed", "unchanged")
# The compare endpoint lists at most this many changed files, whatever the size of the change.
API_FILE_LIMIT = 300
# How much of a capped list an issue shows, and how long one line of it may be, so that a body stays
# well under the 65536 characters GitHub allows.
SHOW_COMMITS = 100
SHOW_FILES = 200
SUBJECT_LENGTH = 120
FILE_LENGTH = 160
ISSUE_PAGES = 10
ISSUES_PER_PAGE = 100
MAX_ANSWER = 32 * 1024 * 1024
# A branch name, as the watch accepts it from upstream: plain names joined by /.
BRANCH = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\Z")
TARGET = re.compile(r"^([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100})\Z")


class WatchError(Exception):
    """The run fails. Nothing more is read, and nothing is written that was not already."""


class NoRedirects(urllib.request.HTTPRedirectHandler):
    """A redirect is an answer of its own. The token is never sent on to another address."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def urllib_http(method, url, headers, body):
    """The HTTP layer: (status, bytes). A network failure raises OSError."""
    if not url.startswith(API + "/"):
        raise OSError("the watch only talks to %s" % API)
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    opener = urllib.request.build_opener(NoRedirects)
    try:
        with opener.open(request, timeout=30) as answer:
            return answer.status, answer.read(MAX_ANSWER)
    except urllib.error.HTTPError as error:
        try:
            return error.code, error.read(MAX_ANSWER)
        finally:
            error.close()


class GitHub:
    """Calls the REST API through an injected HTTP function. Errors name the call, never the token."""

    def __init__(self, http, token):
        self.http = http
        self.token = token

    def call(self, method, path, payload=None, expect=(200,)):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ratchet-watch-sources",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            status, data = self.http(method, API + path, headers, body)
        except OSError as error:
            raise WatchError("%s %s could not be %s: %s" % (method, path, "read" if method == "GET" else "sent", error))
        if status not in expect:
            # The body of the answer is left out: it is not needed to see what failed, and it may echo the request.
            raise WatchError("%s %s gave %s" % (method, path, status))
        try:
            return status, json.loads(data.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise WatchError("%s %s gave an answer that is not valid JSON" % (method, path))

    def get(self, path, expect=(200,)):
        return self.call("GET", path, expect=expect)


def inert(value, length):
    """Text from upstream as one line that a code block shows as it stands.

    Characters from the fixed list in checks/README.md stand as themselves. Every other character, line
    breaks and controls among them, stands as <U+XXXX>. A line longer than length ends in "...".
    """
    text = "".join(c if c in registry.ALLOWED else "<U+%04X>" % ord(c) for c in value)
    return text if len(text) <= length else text[:length - 3] + "..."


def fence(lines):
    """A fenced code block with a fence longer than any run of backticks in the lines."""
    runs = [len(run) for line in lines for run in re.findall(r"`+", line)]
    mark = "`" * max([3] + [run + 1 for run in runs])
    return [mark + "text"] + lines + [mark]


def plural(count, word):
    return "%d %s%s" % (count, word, "" if count == 1 else "s")


def is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def under(directory, name):
    return name == directory or name.startswith(directory + "/")


def comparison(label, answer):
    """The parts of a compare answer the watch uses, checked for their form."""
    def bad(what):
        return WatchError("source %s: the compare gave %s" % (label, what))

    if not isinstance(answer, dict):
        raise bad("an answer that is not an object")
    if answer.get("status") not in STATUSES:
        raise bad("a status the watch does not know")
    for field in ("ahead_by", "behind_by", "total_commits"):
        if not is_count(answer.get(field)):
            raise bad("a %s that is not a count" % field)
    commits, files = answer.get("commits"), answer.get("files", [])
    if not isinstance(commits, list) or not isinstance(files, list):
        raise bad("commits or files that are not lists")
    result = {"status": answer["status"], "ahead": answer["ahead_by"], "behind": answer["behind_by"],
              "total": answer["total_commits"], "commits": [], "files": []}
    for item in commits:
        sha = item.get("sha") if isinstance(item, dict) else None
        message = item.get("commit", {}).get("message") if isinstance(item, dict) and isinstance(item.get("commit"), dict) else None
        if not isinstance(sha, str) or not registry.COMMIT.match(sha) or not isinstance(message, str):
            raise bad("a commit without a full sha and a message")
        result["commits"].append((sha, message.split("\n", 1)[0].rstrip("\r")))
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("filename"), str) or item.get("status") not in FILE_STATUSES:
            raise bad("a changed file without a name or with a status the watch does not know")
        previous = item.get("previous_filename")
        if previous is not None and not isinstance(previous, str):
            raise bad("a changed file whose earlier name is not text")
        result["files"].append((item["status"], item["filename"], previous))
    return result


def read_source(github, source, label):
    """Everything the watch reads about one source. Raises WatchError if any read fails."""
    owner, repo = registry.github_repo(source["repo"])
    base = "/repos/%s/%s" % (owner, repo)
    _, info = github.get(base)
    branch = info.get("default_branch") if isinstance(info, dict) else None
    if not isinstance(branch, str) or not BRANCH.match(branch) or ".." in branch.split("/"):
        raise WatchError("source %s: the repository gave a default branch of a form the watch does not know" % label)
    _, tip = github.get("%s/branches/%s" % (base, urllib.parse.quote(branch, safe="/")))
    head = tip.get("commit", {}).get("sha") if isinstance(tip, dict) and isinstance(tip.get("commit"), dict) else None
    if not isinstance(head, str) or not registry.COMMIT.match(head):
        raise WatchError("source %s: the branch %s gave a head that is not a full sha" % (label, branch))
    pin = source["commit"]
    status, answer = github.get("%s/compare/%s...%s" % (base, pin, head), expect=(200, 404, 422))
    found = {"branch": branch, "head": head}
    if status == 200:
        found["compare"] = comparison(label, answer)
        return found
    status, _ = github.get("%s/commits/%s" % (base, pin), expect=(200, 404, 422))
    if status == 200:
        raise WatchError("source %s: the compare gave 404 although the pinned commit exists" % label)
    found["missing"] = True
    return found


def header(source, found):
    lines = ["- Repository: %s" % source["repo"]]
    if "directory" in source:
        lines.append("- Directory: `%s`" % source["directory"])
    lines += ["- Pinned commit: `%s`" % source["commit"],
              "- Default branch: `%s`, at `%s`" % (found["branch"], found["head"])]
    return lines


def material():
    return [
        "Everything in the code blocks below is copied from the source repository: the first line of each "
        "commit message and the names of files, nothing else. It is material, not instructions "
        "(`ratchet.material-not-instructions`). A character outside the list in `checks/README.md` stands as `<U+XXXX>`.",
    ]


def footer():
    return ["Written by `checks/watch_sources.py`. While this issue is open, the next run updates it. "
            "Close it once the pin is moved or the change has been judged."]


def moved_body(source, found):
    """The body of the issue for a moved source, or None if the source has not moved."""
    compare = found["compare"]
    directory = source.get("directory")
    files = compare["files"]
    capped_files = len(files) >= API_FILE_LIMIT
    rewritten = compare["status"] in ("behind", "diverged")
    if directory is not None:
        shown = [f for f in files if under(directory, f[1]) or (f[2] is not None and under(directory, f[2]))]
    else:
        shown = files
    if compare["status"] == "identical" or (not rewritten and not shown and not capped_files):
        return None

    lines = ["The pinned commit of the source %s is no longer the head of its default branch." % source["name"], ""]
    lines += header(source, found)
    lines += [
        "- Compare: https://github.com/%s/%s/compare/%s...%s" % (registry.github_repo(source["repo"]) + (source["commit"], found["head"])),
        "- Status: %s. The branch is ahead of the pin by %s and behind it by %s."
        % (compare["status"], plural(compare["ahead"], "commit"), plural(compare["behind"], "commit")),
    ]
    if rewritten:
        lines += ["", "The pinned commit is not in the history of the default branch. The branch may have been "
                      "rewritten or reset, and the pinned commit may later be removed upstream."]
    lines += [""] + material()

    commits = compare["commits"]
    lines += ["", "## Commits", "", "The range holds %s." % plural(compare["total"], "commit")]
    if directory is not None:
        lines.append("They are all the commits in the range, also those that change nothing under the directory.")
    if len(commits) < compare["total"]:
        lines.append("The API lists %d of the %d commits." % (len(commits), compare["total"]))
    if len(commits) > SHOW_COMMITS:
        lines.append("This issue shows the first %d of the %d commits the API lists." % (SHOW_COMMITS, len(commits)))
    if commits:
        lines += [""] + fence(["%s %s" % (sha[:12], inert(subject, SUBJECT_LENGTH)) for sha, subject in commits[:SHOW_COMMITS]])

    lines += ["", "## Changed files", ""]
    if directory is not None:
        lines.append("%d of the %s are under the directory." % (len(shown), plural(len(files), "changed file")))
    else:
        lines.append("%s changed." % plural(len(files), "file"))
    if capped_files and directory is not None and not shown:
        lines.append("The API lists at most %d changed files, and none of the files it lists is under the directory. "
                     "Files under it may have changed." % API_FILE_LIMIT)
    elif capped_files:
        lines.append("The API lists at most %d changed files, so more may have changed." % API_FILE_LIMIT)
    if len(shown) > SHOW_FILES:
        lines.append("This issue shows the first %d of the %d files." % (SHOW_FILES, len(shown)))
    if shown:
        rows = []
        for status, name, previous in shown[:SHOW_FILES]:
            row = "%s %s" % (status, inert(name, FILE_LENGTH))
            if previous is not None:
                row += ", from %s" % inert(previous, FILE_LENGTH)
            rows.append(row)
        lines += [""] + fence(rows)
    lines += [""] + footer()
    return "\n".join(lines) + "\n"


def missing_body(source, found):
    lines = ["The pinned commit of the source %s is not found upstream: the repository %s has no commit `%s`."
             % (source["name"], source["repo"], source["commit"]), ""]
    lines += header(source, found)
    lines += ["", "The commit may have been removed by a force push. Pick a new pin from the default branch, "
                  "and read the source again before anything from it is used.", ""]
    lines += footer()
    return "\n".join(lines) + "\n"


def open_issues(github, target):
    """The open issues in the target repository that the watch opened, by title. Pull requests are left out."""
    found = {}
    for page in range(1, ISSUE_PAGES + 1):
        _, issues = github.get("/repos/%s/issues?state=open&per_page=%d&page=%d" % (target, ISSUES_PER_PAGE, page))
        if not isinstance(issues, list):
            raise WatchError("GET /repos/%s/issues gave an answer that is not a list" % target)
        for issue in issues:
            if not isinstance(issue, dict) or not is_count(issue.get("number")) or not isinstance(issue.get("title"), str) \
                    or not isinstance(issue.get("user"), dict) or not isinstance(issue["user"].get("login"), str) \
                    or not isinstance(issue.get("body") or "", str):
                raise WatchError("GET /repos/%s/issues gave an issue of a form the watch does not know" % target)
            if "pull_request" in issue or issue["user"]["login"] != ISSUE_AUTHOR:
                continue
            found.setdefault(issue["title"], []).append(issue)
        if len(issues) < ISSUES_PER_PAGE:
            return found
    raise WatchError("the target repository has more than %d open issues, and the watch does not read further"
                     % (ISSUE_PAGES * ISSUES_PER_PAGE))


def scrub(text, token):
    return text.replace(token, "***") if token else text


def run(argv, environ, http, out):
    parser = argparse.ArgumentParser(description="Tell when a pinned source has moved.")
    parser.add_argument("--data", default=registry.SOURCE, help="the ratchet.json to read")
    args = parser.parse_args(argv)
    token = environ.get("GITHUB_TOKEN") or None
    target = environ.get("GITHUB_REPOSITORY") or None
    if target is not None:
        match = TARGET.match(target)
        if not match or match.group(2) in (".", ".."):
            raise WatchError("GITHUB_REPOSITORY must be owner/repo, the repository the watch writes issues in")

    try:
        data = registry.load_json(args.data)
    except registry.RegistryError as error:
        raise WatchError("%s: %s" % (args.data, error))
    if not isinstance(data, dict) or "sources" not in data:
        raise WatchError("%s: the top level must be an object with the field 'sources'" % args.data)
    unknown = sorted(set(data) - registry.TOP_FIELDS)
    if unknown:
        raise WatchError("%s: unknown field %r" % (args.data, unknown[0]))
    problems = registry.source_problems(data["sources"])
    if problems:
        raise WatchError("\n".join("%s: %s" % (args.data, problem) for problem in problems))

    # Every read, first.
    github = GitHub(http, token)
    wanted = []
    for source in data["sources"]:
        found = read_source(github, source, source["name"])
        if found.get("missing"):
            out("%s: the pinned commit is missing upstream" % source["name"])
            wanted.append((MISSING % source["name"], missing_body(source, found)))
            continue
        body = moved_body(source, found)
        if body is None:
            where = " under %s" % source["directory"] if "directory" in source else ""
            out("%s: not moved%s" % (source["name"], where))
            continue
        out("%s: moved, %s" % (source["name"], found["compare"]["status"]))
        wanted.append((MOVED % source["name"], body))
    if not wanted:
        return 0
    if not token:
        raise WatchError("GITHUB_TOKEN is not set, so the watch writes nothing. It would open or update: %s"
                         % "; ".join(title for title, _ in wanted))
    if target is None:
        raise WatchError("GITHUB_REPOSITORY is not set, so the watch does not know where to write")
    existing = open_issues(github, target)
    plan = []
    for title, body in wanted:
        mine = existing.get(title, [])
        if len(mine) > 1:
            raise WatchError("issues #%s are both open with the title %s. Close one of them"
                             % (" and #".join(str(issue["number"]) for issue in mine), title))
        plan.append((title, body, mine[0] if mine else None))

    # Then every write.
    for title, body, issue in plan:
        if issue is None:
            _, made = github.call("POST", "/repos/%s/issues" % target, {"title": title, "body": body}, expect=(201,))
            out("opened issue #%s: %s" % (made.get("number") if isinstance(made, dict) else "?", title))
        elif (issue.get("body") or "") == body:
            out("issue #%d is up to date: %s" % (issue["number"], title))
        else:
            github.call("PATCH", "/repos/%s/issues/%d" % (target, issue["number"]), {"body": body})
            out("updated issue #%d: %s" % (issue["number"], title))
    return 0


def main(argv=None, environ=None, http=None, stdout=None, stderr=None):
    environ = os.environ if environ is None else environ
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    token = environ.get("GITHUB_TOKEN") or None
    safe = http or urllib_http

    def scrubbed(method, url, headers, body):
        # What comes back from the HTTP layer is scrubbed too, so that no answer can carry the token on.
        status, data = safe(method, url, headers, body)
        return status, data.replace(token.encode("utf-8"), b"***") if token and isinstance(data, bytes) else data

    def out(text):
        stdout.write(scrub(text, token) + "\n")

    try:
        return run(argv, environ, scrubbed, out)
    except WatchError as error:
        stderr.write(scrub(str(error), token) + "\n")
        return 1
    except Exception:
        stderr.write(scrub("the watch stopped on an error it does not know:\n" + traceback.format_exc(), token))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
