#!/usr/bin/env python3
"""Tell when a pinned source has moved, through one issue per source.

    python3 maintain/watch_sources.py                  read sources.json in this repo
    python3 maintain/watch_sources.py --data PATH      read another copy

For every source in the list "sources" of sources.json, the watch reads the head of the default branch of
the source repository and compares the pinned commit with it, through the GitHub REST API. A source without
a directory has moved when the compare is not "identical". A source with a directory has moved when a file
under the directory changed, or when the compare is "behind" or "diverged", or when the API does not say
which files changed. A source that has moved gets one open issue in the repository named by
GITHUB_REPOSITORY, titled "Source moved: <name>": the watch opens it, or updates the open one it opened
before. A pinned commit that is not found upstream gets an issue titled "Source pin missing: <name>". A
source that has not moved writes nothing.

No text from a source, and no text from an answer of the API, reaches an issue, a title or a printed line
(D-2026-11-17-new-approaches). An issue holds the name and the directory from sources.json, two shas of 40
lowercase hex characters, counts, a status from a fixed list, a compare link built from those, and text
written here. Every title, body and printed line passes one gate first: a grammar of the lines it may hold,
a small fixed set of characters, and a check for the token. Every read comes before any write, and nothing
is written if one planned title or body fails the gate.

An error names the request by a fixed kind and the source's name, and gives the HTTP status as an integer.
It never names a path: every path is built from values checked for a strict form, and the head of the
default branch is read as commits/HEAD, so the name of the branch is never read at all.

The token is read from the environment variable GITHUB_TOKEN and from nowhere else, and is sent only to
the origin https://api.github.com, compared exactly and never by prefix. A redirect is not followed. Without
a token the reads run unauthenticated, and if anything would be written, the run fails and names the titles,
without writing them.

Standard library only. CI runs it on Python 3.9 and the newest Python 3.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True
# Its own directory and checks/ on the path, named explicitly, so that python3 -I, which leaves the script's directory
# out of sys.path, still finds the modules beside it and the modules of the checks it uses.
import os  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "checks"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import os
import re
import string
import traceback
import urllib.error
import urllib.parse
import urllib.request

import registry

API = "https://api.github.com"
# The account that the workflow's built-in token writes as. Only its own issues are updated.
ISSUE_AUTHOR = "github-actions[bot]"
MOVED = "Source moved: "
MISSING = "Source pin missing: "
STATUSES = ("identical", "ahead", "behind", "diverged")
# The compare endpoint lists at most this many changed files, whatever the size of the change.
API_FILE_LIMIT = 300
# The largest count an issue holds: nine digits.
MAX_COUNT = 999999999
# GitHub refuses an issue body of more than 65536 characters.
BODY_LIMIT = 65536
ISSUE_PAGES = 10
ISSUES_PER_PAGE = 100
MAX_ANSWER = 32 * 1024 * 1024
TARGET = re.compile(r"(%s)/(%s)" % (registry.OWNER, registry.REPOSITORY))
SHA = r"[0-9a-f]{40}"
COUNT = r"[0-9]{1,9}"
# Every request path the watch builds, each value in it of a checked form. HEAD is resolved by GitHub to
# the head of the default branch, so no path holds the name of a branch. Any other path is not sent.
_REPO_PATH = r"/repos/%s/(?!\.\.?/)%s" % (registry.OWNER, registry.REPOSITORY)
PATHS = [re.compile(_REPO_PATH + rest) for rest in (
    r"/commits/(?:HEAD|%s)" % SHA,
    r"/compare/%s\.\.\.%s" % (SHA, SHA),
    r"/issues",
    r"/issues\?state=open&per_page=[0-9]{1,3}&page=[0-9]{1,2}",
    r"/issues/" + COUNT,
)]


class WatchError(Exception):
    """The run fails. Nothing more is read, and nothing is written that was not already."""


# The transport. The token goes to the API host and nowhere else.

class NoRedirects(urllib.request.HTTPRedirectHandler):
    """A redirect is an answer of its own. No new request is made, so the token goes nowhere else."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def is_api(url):
    """Whether url is a path on the exact origin of API. urllib.parse splits it, and the scheme and the netloc,
    which holds the host and the port as written and any userinfo, must equal those of API. Never by prefix.
    urlsplit drops tabs and line breaks and urllib.request does not, so a url must be printable ASCII first."""
    if any(not "!" <= character <= "~" for character in url):
        return False
    try:
        parts, api = urllib.parse.urlsplit(url), urllib.parse.urlsplit(API)
    except ValueError:
        return False
    return parts.scheme == api.scheme and parts.netloc == api.netloc and parts.path.startswith("/") and not parts.fragment


def urllib_http(method, url, headers, body):
    """The HTTP layer: (status, bytes). A network failure, or an address that is not the API, raises OSError."""
    if not is_api(url):
        raise OSError("the watch only talks to the API")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirects).open(request, timeout=30) as answer:
            return answer.status, answer.read(MAX_ANSWER)
    except urllib.error.HTTPError as error:
        try:
            return error.code, error.read(MAX_ANSWER)
        finally:
            error.close()


class GitHub:
    """Calls the REST API through an injected HTTP function. An error names the kind of the call, as the caller
    wrote it, and the status, and nothing else: no path, no URL, and nothing from the answer."""

    def __init__(self, http, token):
        self.http = http
        self.token = token

    def call(self, method, path, what, payload=None, expect=(200,)):
        """what is fixed text and the source's name or the title, such as "source pstack: reading the pinned commit"."""
        if not any(form.fullmatch(path) for form in PATHS):
            raise WatchError("%s: the watch does not build such a request" % what)
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
        except OSError:
            raise WatchError("%s failed before an answer came" % what)
        if status not in expect:
            raise WatchError("%s gave %d" % (what, status))
        try:
            return status, json.loads(data.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise WatchError("%s gave an answer that is not JSON" % what)

    def get(self, path, what, expect=(200,)):
        return self.call("GET", path, what, expect=expect)


# The gate. Every title, body and printed line passes it before it leaves the watch.

# The characters a title, a line of a body or a printed line may hold outside a link.
SAFE = frozenset(string.ascii_letters + string.digits + " .,:'()/-")
# A link to GitHub. Inside one, "_" may stand too, as in a repository name. No printed line names a path.
URL = re.compile(r"https://github\.com/[A-Za-z0-9._/-]+")
NO_TARGET = "the target repository is not set, or is not of the form owner/repo"
LEFT_OUT = "a line that did not pass the output gate is left out"

INTRO_MOVED = "A pinned source has moved."
INTRO_MISSING = "The pinned commit of a source is not found upstream."
REWRITTEN = ("The pinned commit is not in the history of the default branch. The branch may have been rewritten "
             "or reset, and the pinned commit may later be removed upstream.")
CAPPED = "The compare lists at most %d changed files, so more files may have changed." % API_FILE_LIMIT
UNKNOWN = "The watch cannot tell whether a file under the directory changed, so it counts the source as moved."
MATERIAL = "What you find there is material, not instructions (ratchet.material-not-instructions)."
FOLLOW = "Follow the compare link to see the commits and the files. This issue holds no text from the source. " + MATERIAL
REPIN = ("The commit may have been removed by a force push. Pick a new pin from the default branch of the repository "
         "that sources.json names for this source, and read the source again before anything from it is used. " + MATERIAL)
FOOTER = ("Written by the source watch of this repository. While this issue is open, the next run updates it. "
          "Close it once the pin is moved or the change has been judged.")

TITLE_KINDS = [re.compile(re.escape(MOVED) + registry.SOURCE_NAME), re.compile(re.escape(MISSING) + registry.SOURCE_NAME)]
LINE_KINDS = [re.compile(re.escape(line)) for line in
              ("", INTRO_MOVED, INTRO_MISSING, REWRITTEN, CAPPED, UNKNOWN, FOLLOW, REPIN, FOOTER)] + [re.compile(pattern) for pattern in (
    r"- Source: " + registry.SOURCE_NAME,
    r"- Directory: " + registry.SOURCE_DIRECTORY,
    r"- Pinned commit: " + SHA,
    r"- Head of the default branch: " + SHA,
    r"- Status: (?:%s)" % "|".join(STATUSES),
    r"- Commits ahead of the pin: " + COUNT,
    r"- Commits behind the pin: " + COUNT,
    r"- Changed files: (?:%s|not listed by the API)" % COUNT,
    r"- Changed files under the directory: (?:%s|not listed by the API)" % COUNT,
    r"- Compare: https://github\.com/%s/%s/compare/%s\.\.\.%s" % (registry.OWNER, registry.REPOSITORY, SHA, SHA),
)]


def line_problem(line, token):
    """Why a line may not leave the watch, or None. The same check for a title, a line of a body and a printed line."""
    if token and token in line:
        return "it holds the token"
    rest = URL.sub(" ", line)
    if any(character not in SAFE for character in rest):
        return "it holds a character outside the set"
    if "::" in line:
        return "it holds two colons in a row"
    if registry.AUTOLINK.search(rest):
        return "it holds text that GitHub turns into a link or a reference"
    return None


def check_plan(plan, token):
    """Every planned title and body, checked before the first write. Raises WatchError if one fails."""
    problems = []
    for number, (title, body) in enumerate(plan, 1):
        if not any(kind.fullmatch(title) for kind in TITLE_KINDS) or line_problem(title, token):
            problems.append("planned issue %d: the title does not pass the gate" % number)
        if not body.endswith("\n") or len(body.encode("utf-8")) > BODY_LIMIT or (token and token in body):
            problems.append("planned issue %d: the body does not pass the gate" % number)
            continue
        for at, line in enumerate(body[:-1].split("\n"), 1):
            if not any(kind.fullmatch(line) for kind in LINE_KINDS) or line_problem(line, token):
                problems.append("planned issue %d: line %d of the body does not pass the gate" % (number, at))
    if problems:
        raise WatchError("\n".join(["nothing is written:"] + problems))


def emit(stream, text, token):
    """Print the lines of text that pass the gate, and LEFT_OUT for each that does not. False if one did not."""
    clean = True
    for line in text.split("\n"):
        if line_problem(line, token):
            line, clean = LEFT_OUT, False
        stream.write(line + "\n")
    return clean


# The reads.

def is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_COUNT


def comparison(name, answer):
    """The parts of a compare answer the watch uses. files is None if the API lists none. File names are only compared."""
    def form(ok):
        if not ok:
            raise WatchError("source %s: the compare gave an answer of a form the watch does not know" % name)

    form(isinstance(answer, dict) and answer.get("status") in STATUSES
         and is_count(answer.get("ahead_by")) and is_count(answer.get("behind_by")))
    files = answer.get("files")
    form(files is None or isinstance(files, list))
    names = None
    if files is not None:
        names = []
        for item in files:
            form(isinstance(item, dict) and isinstance(item.get("filename"), str)
                 and (item.get("previous_filename") is None or isinstance(item["previous_filename"], str)))
            names.append((item["filename"], item.get("previous_filename")))
    return {"status": answer["status"], "ahead": answer["ahead_by"], "behind": answer["behind_by"], "files": names}


def read_source(github, source):
    """Everything the watch reads about one source. Raises WatchError if any read fails."""
    name = source["name"]
    owner, repo = registry.github_repo(source["repo"])
    base = "/repos/%s/%s" % (owner, repo)
    # GitHub resolves HEAD to the head of the default branch, so the name of the branch is never read.
    _, tip = github.get(base + "/commits/HEAD", "source %s: reading the head of the default branch" % name)
    head = tip.get("sha") if isinstance(tip, dict) else None
    if not isinstance(head, str) or not re.fullmatch(SHA, head):
        raise WatchError("source %s: the repository gave a head of a form the watch does not know" % name)
    pin = source["commit"]
    found = {"owner": owner, "repo": repo, "head": head}
    status, answer = github.get("%s/compare/%s...%s" % (base, pin, head),
                                "source %s: comparing the pinned commit with the head" % name, expect=(200, 404, 422))
    if status == 200:
        found["compare"] = comparison(name, answer)
        if (found["compare"]["status"] == "identical") != (head == pin):
            raise WatchError("source %s: the compare says %s, but the head %s the pinned commit"
                             % (name, found["compare"]["status"], "is" if head == pin else "is not"))
        return found
    status, _ = github.get("%s/commits/%s" % (base, pin), "source %s: reading the pinned commit" % name, expect=(200, 404, 422))
    if status == 200:
        raise WatchError("source %s: the compare gave 404 although the pinned commit exists" % name)
    found["missing"] = True
    return found


def under(directory, path):
    return path == directory or path.startswith(directory + "/")


def files_under(source, compare):
    """How many changed files are under the directory, an earlier name counting too. None if the API lists none."""
    if compare["files"] is None:
        return None
    directory = source["directory"]
    return sum(1 for path, previous in compare["files"]
               if under(directory, path) or (previous is not None and under(directory, previous)))


def capped(compare):
    return compare["files"] is not None and len(compare["files"]) >= API_FILE_LIMIT


def unknown_under(source, compare):
    """Whether the API leaves open if a file under the directory changed: no list, or a capped list with none under it."""
    return compare["status"] == "ahead" and (compare["files"] is None or (capped(compare) and not files_under(source, compare)))


def moved(source, compare):
    if compare["status"] == "identical":
        return False
    if "directory" not in source or compare["status"] in ("behind", "diverged"):
        return True
    return bool(files_under(source, compare)) or unknown_under(source, compare)


# The bodies. Each line is fixed text, or fixed text and a value checked for its form.

def count_text(value):
    return "not listed by the API" if value is None else "%d" % value


def facts(source, found):
    lines = ["- Source: " + source["name"]]
    if "directory" in source:
        lines.append("- Directory: " + source["directory"])
    return lines + ["- Pinned commit: " + source["commit"], "- Head of the default branch: " + found["head"]]


def moved_body(source, found):
    compare = found["compare"]
    files = compare["files"]
    lines = [INTRO_MOVED, ""] + facts(source, found) + [
        "- Status: " + compare["status"],
        "- Commits ahead of the pin: %d" % compare["ahead"],
        "- Commits behind the pin: %d" % compare["behind"],
        "- Changed files: " + count_text(None if files is None else len(files)),
    ]
    if "directory" in source:
        lines.append("- Changed files under the directory: " + count_text(files_under(source, compare)))
    lines += ["- Compare: https://github.com/%s/%s/compare/%s...%s" % (found["owner"], found["repo"], source["commit"], found["head"]), ""]
    if compare["status"] in ("behind", "diverged"):
        lines += [REWRITTEN, ""]
    if capped(compare):
        lines += [CAPPED, ""]
    if "directory" in source and unknown_under(source, compare):
        lines += [UNKNOWN, ""]
    return "\n".join(lines + [FOLLOW, "", FOOTER]) + "\n"


def missing_body(source, found):
    return "\n".join([INTRO_MISSING, ""] + facts(source, found) + ["", REPIN, "", FOOTER]) + "\n"


# The writes.

def open_issues(github, target):
    """The open issues in the target repository that the watch opened, by title. Pull requests are left out."""
    found = {}
    what = "reading the open issues of the target repository"
    for page in range(1, ISSUE_PAGES + 1):
        _, issues = github.get("/repos/%s/issues?state=open&per_page=%d&page=%d" % (target, ISSUES_PER_PAGE, page), what)
        if not isinstance(issues, list):
            raise WatchError("%s gave an answer of a form the watch does not know" % what)
        for issue in issues:
            if not isinstance(issue, dict) or not is_count(issue.get("number")) or not isinstance(issue.get("title"), str) \
                    or not isinstance(issue.get("user"), dict) or not isinstance(issue["user"].get("login"), str) \
                    or not isinstance(issue.get("body") or "", str):
                raise WatchError("%s gave an issue of a form the watch does not know" % what)
            if "pull_request" in issue or issue["user"]["login"] != ISSUE_AUTHOR:
                continue
            found.setdefault(issue["title"], []).append(issue)
        if len(issues) < ISSUES_PER_PAGE:
            return found
    raise WatchError("the target repository has more than %d open issues, and the watch does not read further"
                     % (ISSUE_PAGES * ISSUES_PER_PAGE))


def run(argv, environ, http, out):
    if argv == []:
        path = registry.SOURCES_PATH
    elif len(argv) == 2 and argv[0] == "--data":
        path = argv[1]
    else:
        raise WatchError("the arguments must be none, or --data and a path")
    token = environ.get("GITHUB_TOKEN") or None
    target = environ.get("GITHUB_REPOSITORY") or None
    if target is not None:
        match = TARGET.fullmatch(target)
        if not match or match.group(2) in (".", ".."):
            raise WatchError(NO_TARGET)

    try:
        data = registry.load_json(path)
    except registry.RegistryError as error:
        raise WatchError("the data file could not be read: %s" % error)
    if not isinstance(data, dict) or set(data) != {"sources"}:
        raise WatchError("the data file must be an object with the one field sources, as sources.json is")
    problems = registry.source_problems(data["sources"])
    if problems:
        raise WatchError("\n".join(["the sources in the data file do not have their form:"] + problems))

    # Every read, first.
    github = GitHub(http, token)
    plan = []
    for source in data["sources"]:
        found = read_source(github, source)
        if found.get("missing"):
            out("source %s: the pinned commit is missing upstream" % source["name"])
            plan.append((MISSING + source["name"], missing_body(source, found)))
        elif moved(source, found["compare"]):
            out("source %s: moved, %s" % (source["name"], found["compare"]["status"]))
            plan.append((MOVED + source["name"], moved_body(source, found)))
        elif found["compare"]["status"] == "identical":
            out("source %s: not moved" % source["name"])
        else:
            out("source %s: not moved under its directory" % source["name"])
    if not plan:
        return 0
    # Then every title and body, through the gate, before anything is written.
    check_plan(plan, token)
    if not token:
        raise WatchError("\n".join(["no token is set, so the watch writes nothing"]
                                   + ["would open or update: " + title for title, _ in plan]))
    if target is None:
        raise WatchError(NO_TARGET)
    existing = open_issues(github, target)
    writes = []
    for title, body in plan:
        mine = existing.get(title, [])
        if len(mine) > 1:
            raise WatchError("issues %s are both open with the title %s. Close one of them"
                             % (" and ".join("%d" % issue["number"] for issue in mine), title))
        writes.append((title, body, mine[0] if mine else None))

    # Then every write. Only a failure on GitHub's side can leave some of them written and some not.
    for title, body, issue in writes:
        if issue is None:
            _, made = github.call("POST", "/repos/%s/issues" % target, "opening the issue " + title,
                                  {"title": title, "body": body}, expect=(201,))
            number = made.get("number") if isinstance(made, dict) else None
            out(("opened issue %d: %s" % (number, title)) if is_count(number) else "opened an issue: " + title)
        elif (issue.get("body") or "") == body:
            out("issue %d is up to date: %s" % (issue["number"], title))
        else:
            github.call("PATCH", "/repos/%s/issues/%d" % (target, issue["number"]), "updating the issue " + title, {"body": body})
            out("updated issue %d: %s" % (issue["number"], title))
    return 0


def main(argv=None, environ=None, http=None, stdout=None, stderr=None):
    argv = sys.argv[1:] if argv is None else argv
    environ = os.environ if environ is None else environ
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    token = environ.get("GITHUB_TOKEN") or None

    def out(text):
        if not emit(stdout, text, token):
            raise WatchError("a line the watch was to print did not pass the output gate")

    try:
        return run(argv, environ, http or urllib_http, out)
    except WatchError as error:
        emit(stderr, str(error), token)
        return 1
    except Exception as error:
        # Only the kind of the error and the line of the watch it came from: its text may hold anything.
        lines = [frame.lineno for frame in traceback.extract_tb(error.__traceback__) if frame.filename == __file__]
        emit(stderr, "the watch stopped on an error it does not know, %s at line %d of the watch"
             % (type(error).__name__, lines[-1] if lines else 0), token)
        return 1


if __name__ == "__main__":
    sys.exit(main())
