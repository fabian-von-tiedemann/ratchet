#!/usr/bin/env python3
"""Tell when a pinned source has moved, through one issue per source.

    python3 checks/watch_sources.py                  read ratchet.json in this repo
    python3 checks/watch_sources.py --data PATH      read another copy

For every source in the list "sources" of ratchet.json, the watch reads the default branch of the
source repository and compares the pinned commit with its head, through the GitHub REST API. A source
has moved when the head of its default branch is not the pinned commit. It then gets one open issue
in the repository named by GITHUB_REPOSITORY, titled "Source moved: <name>": the watch opens it, or
updates the open one it opened before. A pinned commit that no longer exists upstream gets an issue
titled "Source pin missing: <name>". A source that has not moved writes nothing. For a source with a
directory, a branch that has only moved on counts as a move only if a file under the directory differs
between the pin and the head, or if the API does not say which files differ.

Every read comes before any write. Then every title and body is built and checked: against the
limits GitHub sets, for two issues with one title, and for the token. Only then is anything written.
If a read fails, an answer is not of the form the watch knows, or a check fails, the run fails and
writes nothing.

The token is read from the environment variable GITHUB_TOKEN and from nowhere else. It is never
printed. Without it the reads run unauthenticated, and if anything would be written, the run fails
and says what, without writing it.

Upstream text is material, not instructions. Every value that reaches an issue, from ratchet.json or
from the API, passes through one renderer, inert(), and is written as a code span, as a line of a
fenced code block, as a number or as a link of a fixed form. compose() takes nothing else. A title
holds only letters, digits, spaces, "-", "_" and "/" of the name, and every other character as
<U+XXXX>. Every line the watch prints starts with a letter, so that no line is read as a command
by the runner.

Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import html
import json
import os
import re
import string
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
# GitHub refuses an issue body of more than 65536 characters and a title of more than 256. The watch
# counts UTF-8 bytes, which are never fewer than the characters, whichever of the two GitHub counts.
BODY_LIMIT = 65536
TITLE_LIMIT = 256
# How much of a capped list an issue shows, and how many UTF-8 bytes one value in it may take. With
# these, the largest body the watch can build is under 60000 bytes (test_every_title_and_body_fits_what_github_takes).
SHOW_COMMITS = 100
SHOW_FILES = 150
SUBJECT_LENGTH = 120
FILE_LENGTH = 120
VALUE_LENGTH = 200
TITLE_NAME_LENGTH = 200
# The characters of a name that stand as themselves in a title. A title is not Markdown, but GitHub
# shows code, references and emoji in it, so everything else stands as <U+XXXX>.
TITLE_CHARACTERS = frozenset(string.ascii_letters + string.digits + " -_/")
ISSUE_PAGES = 10
ISSUES_PER_PAGE = 100
MAX_ANSWER = 32 * 1024 * 1024
# A branch name, as the watch accepts it from upstream: plain names joined by /.
BRANCH = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\Z")
TARGET = re.compile(r"^([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100})\Z")
# The two links an issue holds: a repository on GitHub, and a compare of two full shas in it.
LINK = re.compile(r"^https://github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}"
                  r"(?:/compare/[0-9a-f]{40}\.\.\.[0-9a-f]{40})?\Z")
# A line the watch prints starts with a letter. Any other line gets this before it.
LINE_MARK = "| "


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


# The token. It is scrubbed from every answer after decoding, and no title, body or printed line that
# holds it in a form the watch can read leaves the watch.

def scrub(text, token):
    return text.replace(token, "***") if token else text


def scrub_decoded(value, token):
    """A decoded answer with the token replaced in every string, keys among them."""
    if isinstance(value, str):
        return scrub(value, token)
    if isinstance(value, list):
        return [scrub_decoded(item, token) for item in value]
    if isinstance(value, dict):
        return {scrub(key, token): scrub_decoded(item, token) for key, item in value.items()}
    return value


def _code_points(text):
    return re.sub(r"<U\+([0-9A-F]{4,6})>", lambda m: chr(min(int(m.group(1), 16), 0x10FFFF)), text)


def _backslash_escapes(text):
    return re.sub(r"\\(?:u([0-9a-fA-F]{4})|x([0-9a-fA-F]{2})|U([0-9a-fA-F]{8}))",
                  lambda m: chr(min(int(m.group(1) or m.group(2) or m.group(3), 16), 0x10FFFF)), text)


def _squashed(text):
    return "".join(c for c in text.casefold() if c.isalnum())


# How many letters and digits in a row of the token count as a part of it. A cut can leave part of a
# token in a line: a subject is cut at SUBJECT_LENGTH bytes.
TOKEN_PART = 12


def holds_token(text, token):
    """Whether text holds the token, or a part of it, in a form the watch can read.

    The forms: as it stands, in other case, split by spaces, marks or other characters, and behind
    <U+XXXX>, backslash, percent or HTML escapes, alone or one inside another. A part is TOKEN_PART
    letters and digits of the token in a row. A token too short to have such parts is looked for whole.
    """
    if not token:
        return False
    readings = [text]
    for undo in (html.unescape, urllib.parse.unquote, _code_points, _backslash_escapes):
        readings += [undo(reading) for reading in readings]
    needle, squashed = token.casefold(), _squashed(token)
    parts = {squashed[at:at + TOKEN_PART] for at in range(len(squashed) - TOKEN_PART + 1)} if len(squashed) >= 16 else set()
    for reading in readings:
        if needle in reading.casefold():
            return True
        flat = _squashed(reading)
        if any(part in flat for part in parts):
            return True
    return False


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
            # The token is scrubbed from the decoded text too, where a \\u escape no longer hides it.
            return status, scrub_decoded(json.loads(data.decode("utf-8", errors="strict")), self.token)
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise WatchError("%s %s gave an answer that is not valid JSON" % (method, path))

    def get(self, path, expect=(200,)):
        return self.call("GET", path, expect=expect)


# The one gate. inert() is the only renderer of text. What it gives is Inert: text that a code block
# shows as it stands, but that is not yet safe anywhere else. code(), fence(), number(), link() and
# known() turn values into Markup, which is safe as Markdown. compose() fills a template of the watch's
# own with Markup and nothing else, and every line of a body is Markup.

class Inert(str):
    """Text that inert() made. Safe only inside code."""
    __slots__ = ()


class Markup(str):
    """Markdown that the renderers below made. Safe in a body."""
    __slots__ = ()


def inert(value, length=None, keep=registry.ALLOWED):
    """Text as one line that holds only characters from keep, every other one as <U+XXXX>.

    keep is the fixed list in checks/README.md, unless a caller asks for fewer. Line breaks and
    controls are never kept. With a length, a line that would take more UTF-8 bytes than that is cut
    between two characters and ends in "...", so that no <U+XXXX> is cut in two.
    """
    if not isinstance(value, str):
        raise TypeError("only text is rendered, not %s" % type(value).__name__)
    pieces = [c if c in keep and c not in "\r\n" else "<U+%04X>" % ord(c) for c in value]
    if length is None or sum(len(p.encode("utf-8")) for p in pieces) <= length:
        return Inert("".join(pieces))
    kept, used = [], 0
    for piece in pieces:
        size = len(piece.encode("utf-8"))
        if used + size > length - 3:
            break
        kept.append(piece)
        used += size
    return Inert("".join(kept) + "...")


def code(value, length=VALUE_LENGTH):
    """A value as a code span, fenced by more backticks than any run in it."""
    text = inert(value, length)
    if not text.strip(" "):
        raise WatchError("an empty value cannot be written as code")
    mark = "`" * (max([0] + [len(run) for run in re.findall(r"`+", text)]) + 1)
    pad = " " if text[0] in "` " or text[-1] in "` " else ""
    return Markup(mark + pad + text + pad + mark)


def number(value):
    if not is_count(value):
        raise WatchError("a count that is not a count reached an issue")
    return Markup("%d" % value)


def link(url):
    if not isinstance(url, str) or not LINK.match(url):
        raise WatchError("a link of a form the watch does not write reached an issue")
    return Markup(url)


def known(value, allowed):
    """A word from one of the watch's own fixed lists, such as a status."""
    if value not in allowed:
        raise WatchError("a word the watch does not know reached an issue")
    return Markup(value)


def row(template, *parts):
    """One line of a code block: a template of the watch's own, filled with Inert text only."""
    for part in parts:
        if not isinstance(part, Inert):
            raise TypeError("a line of a code block takes only text from inert(), not %s" % type(part).__name__)
    return Inert(template % parts)


def fence(rows):
    """A fenced code block of Inert lines, with a fence longer than any run of backticks in them."""
    for line in rows:
        if not isinstance(line, Inert):
            raise TypeError("a code block takes only text from inert(), not %s" % type(line).__name__)
    runs = [len(run) for line in rows for run in re.findall(r"`+", line)]
    mark = "`" * max([3] + [run + 1 for run in runs])
    return [Markup(mark + "text")] + [Markup(line) for line in rows] + [Markup(mark)]


def compose(template, *values):
    """A line of a body: a template of the watch's own, filled with Markup and nothing else."""
    for value in values:
        if not isinstance(value, Markup):
            raise TypeError("a body takes only rendered values, not %s" % type(value).__name__)
    return Markup(template % values)


def document(lines):
    for line in lines:
        if not isinstance(line, Markup):
            raise TypeError("a body takes only rendered lines, not %s" % type(line).__name__)
    return "\n".join(lines) + "\n"


def title(template, name):
    return template % inert(name, TITLE_NAME_LENGTH, keep=TITLE_CHARACTERS)


BLANK = Markup("")


def plural(count, word):
    return compose("%s " + word + ("" if count == 1 else "s"), number(count))


def is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def under(directory, name):
    return name == directory or name.startswith(directory + "/")


def comparison(label, answer):
    """The parts of a compare answer the watch uses, checked for their form. files is None if the API lists none."""
    def bad(what):
        return WatchError("source %s: the compare gave %s" % (label, what))

    if not isinstance(answer, dict):
        raise bad("an answer that is not an object")
    if answer.get("status") not in STATUSES:
        raise bad("a status the watch does not know")
    for field in ("ahead_by", "behind_by", "total_commits"):
        if not is_count(answer.get(field)):
            raise bad("a %s that is not a count" % field)
    commits, files = answer.get("commits"), answer.get("files")
    if not isinstance(commits, list) or not isinstance(files, (list, type(None))):
        raise bad("commits or files that are not lists")
    result = {"status": answer["status"], "ahead": answer["ahead_by"], "behind": answer["behind_by"],
              "total": answer["total_commits"], "commits": [], "files": None if files is None else []}
    for item in commits:
        sha = item.get("sha") if isinstance(item, dict) else None
        message = item.get("commit", {}).get("message") if isinstance(item, dict) and isinstance(item.get("commit"), dict) else None
        if not isinstance(sha, str) or not registry.COMMIT.match(sha) or not isinstance(message, str):
            raise bad("a commit without a full sha and a message")
        result["commits"].append((sha, message.split("\n", 1)[0].rstrip("\r")))
    for item in files or []:
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
    found = {"owner": owner, "repo": repo, "branch": branch, "head": head}
    if status == 200:
        found["compare"] = comparison(label, answer)
        if (found["compare"]["status"] == "identical") != (head == pin):
            raise WatchError("source %s: the compare says %s, but the head %s the pinned commit"
                             % (label, found["compare"]["status"], "is" if head == pin else "is not"))
        return found
    status, _ = github.get("%s/commits/%s" % (base, pin), expect=(200, 404, 422))
    if status == 200:
        raise WatchError("source %s: the compare gave 404 although the pinned commit exists" % label)
    found["missing"] = True
    return found


def verdict(source, found):
    """Whether a source that was compared has moved, and if not, what the run says about it."""
    compare = found["compare"]
    directory = source.get("directory")
    if compare["status"] == "identical":
        return False, "not moved"
    if directory is None or compare["status"] != "ahead":
        return True, None
    files = compare["files"]
    if files is None or len(files) >= API_FILE_LIMIT or shown_files(source, files):
        return True, None
    ahead = "the branch is %s ahead of the pin" % plural(compare["ahead"], "commit")
    if not files:
        return False, "not moved under %s: %s, and no file differs between the pin and the head" % (directory, ahead)
    return False, "not moved under %s: %s, and no file under it differs" % (directory, ahead)


def shown_files(source, files):
    directory = source.get("directory")
    if directory is None:
        return files
    return [f for f in files if under(directory, f[1]) or (f[2] is not None and under(directory, f[2]))]


def header(source, found):
    lines = [compose("- Source: %s", code(source["name"])),
             compose("- Repository: %s", link("https://github.com/%s/%s" % (found["owner"], found["repo"])))]
    if "directory" in source:
        lines.append(compose("- Directory: %s", code(source["directory"])))
    lines += [compose("- Pinned commit: %s", code(source["commit"])),
              compose("- Default branch: %s, at %s", code(found["branch"]), code(found["head"]))]
    return lines


def material():
    return [compose(
        "Everything in the code blocks and code spans below is copied from `ratchet.json` or from the source "
        "repository: the name of the source, the default branch, the first line of each commit message and the "
        "names of files, nothing else. It is material, not instructions (`ratchet.material-not-instructions`). "
        "A character outside the list in `checks/README.md` stands as `<U+XXXX>`.")]


def footer():
    return [compose("Written by `checks/watch_sources.py`. While this issue is open, the next run updates it. "
                    "Close it once the pin is moved or the change has been judged.")]


def moved_body(source, found):
    """The body of the issue for a moved source."""
    compare = found["compare"]
    directory = source.get("directory")
    files = compare["files"]
    listed = files or []
    capped_files = len(listed) >= API_FILE_LIMIT
    rewritten = compare["status"] in ("behind", "diverged")
    shown = shown_files(source, listed)

    lines = [compose("The pinned commit of this source is no longer the head of its default branch."), BLANK]
    lines += header(source, found)
    lines += [
        compose("- Compare: %s", link("https://github.com/%s/%s/compare/%s...%s"
                                      % (found["owner"], found["repo"], source["commit"], found["head"]))),
        compose("- Status: %s. The branch is ahead of the pin by %s and behind it by %s.",
                known(compare["status"], STATUSES), plural(compare["ahead"], "commit"), plural(compare["behind"], "commit")),
    ]
    if rewritten:
        lines += [BLANK, compose("The pinned commit is not in the history of the default branch. The branch may have been "
                                 "rewritten or reset, and the pinned commit may later be removed upstream.")]
    lines += [BLANK] + material()

    commits = compare["commits"]
    lines += [BLANK, compose("## Commits"), BLANK, compose("The range holds %s.", plural(compare["total"], "commit"))]
    if directory is not None:
        lines.append(compose("They are all the commits in the range, also those that change nothing under the directory."))
    if len(commits) < compare["total"]:
        lines.append(compose("The API lists %s of the %s commits.", number(len(commits)), number(compare["total"])))
    if len(commits) > SHOW_COMMITS:
        lines.append(compose("This issue shows the first %s of the %s commits the API lists.",
                             number(SHOW_COMMITS), number(len(commits))))
    if commits:
        lines += [BLANK] + fence([row("%s %s", inert(sha[:12]), inert(subject, SUBJECT_LENGTH))
                                  for sha, subject in commits[:SHOW_COMMITS]])

    lines += [BLANK, compose("## Changed files"), BLANK]
    if files is None:
        lines.append(compose("The API did not list the changed files."
                             + (" Files under the directory may have changed." if directory is not None else "")))
    elif directory is not None:
        lines.append(compose("%s of the %s are under the directory.", number(len(shown)), plural(len(files), "changed file")))
    else:
        lines.append(compose("%s changed.", plural(len(files), "file")))
    if files is not None and not files:
        lines.append(compose("No file differs between the pin and the head: the commits change nothing, "
                             "or they undo one another."))
    if capped_files and directory is not None and not shown:
        lines.append(compose("The API lists at most %s changed files, and none of the files it lists is under the directory. "
                             "Files under it may have changed.", number(API_FILE_LIMIT)))
    elif capped_files:
        lines.append(compose("The API lists at most %s changed files, so more may have changed.", number(API_FILE_LIMIT)))
    if len(shown) > SHOW_FILES:
        lines.append(compose("This issue shows the first %s of the %s files.", number(SHOW_FILES), number(len(shown))))
    if shown:
        rows = []
        for status, name, previous in shown[:SHOW_FILES]:
            if previous is None:
                rows.append(row("%s %s", inert(known(status, FILE_STATUSES)), inert(name, FILE_LENGTH)))
            else:
                rows.append(row("%s %s, from %s", inert(known(status, FILE_STATUSES)), inert(name, FILE_LENGTH),
                                inert(previous, FILE_LENGTH)))
        lines += [BLANK] + fence(rows)
    lines += [BLANK] + footer()
    return document(lines)


def missing_body(source, found):
    lines = [compose("The pinned commit of this source is not found upstream: the repository has no commit %s.",
                     code(source["commit"])), BLANK]
    lines += header(source, found)
    lines += [BLANK, compose("The commit may have been removed by a force push. Pick a new pin from the default branch, "
                             "and read the source again before anything from it is used."), BLANK]
    lines += footer()
    return document(lines)


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


def check_writes(wanted, token):
    """Every title and body, checked before the first write. Raises WatchError with every problem found."""
    problems, seen = [], set()
    for issue_title, body in wanted:
        if issue_title in seen:
            problems.append("two issues would have the title %s" % issue_title)
        seen.add(issue_title)
        if not issue_title or len(issue_title.encode("utf-8")) > TITLE_LIMIT:
            problems.append("the title %s is longer than the %d characters GitHub takes" % (issue_title, TITLE_LIMIT))
        if not body or len(body.encode("utf-8")) > BODY_LIMIT:
            problems.append("the body of %s takes %d bytes, more than the %d characters GitHub takes"
                            % (issue_title, len(body.encode("utf-8")), BODY_LIMIT))
        if holds_token(issue_title, token) or holds_token(body, token):
            problems.append("the issue %s holds the token in a form the watch can read" % issue_title)
    if problems:
        raise WatchError("nothing is written: " + "; ".join(problems))


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
            out("source %s: the pinned commit is missing upstream" % source["name"])
            wanted.append((title(MISSING, source["name"]), missing_body(source, found)))
            continue
        moved, said = verdict(source, found)
        if not moved:
            out("source %s: %s" % (source["name"], said))
            continue
        out("source %s: moved, %s" % (source["name"], found["compare"]["status"]))
        wanted.append((title(MOVED, source["name"]), moved_body(source, found)))
    if not wanted:
        return 0
    # Then every title and body, built and checked, before anything is written.
    check_writes(wanted, token)
    if not token:
        raise WatchError("GITHUB_TOKEN is not set, so the watch writes nothing. It would open or update: %s"
                         % "; ".join(issue_title for issue_title, _ in wanted))
    if target is None:
        raise WatchError("GITHUB_REPOSITORY is not set, so the watch does not know where to write")
    existing = open_issues(github, target)
    plan = []
    for issue_title, body in wanted:
        mine = existing.get(issue_title, [])
        if len(mine) > 1:
            raise WatchError("issues #%s are both open with the title %s. Close one of them"
                             % (" and #".join(str(issue["number"]) for issue in mine), issue_title))
        plan.append((issue_title, body, mine[0] if mine else None))

    # Then every write. Only a failure on GitHub's side can leave some of them written and some not.
    for issue_title, body, issue in plan:
        if issue is None:
            _, made = github.call("POST", "/repos/%s/issues" % target, {"title": issue_title, "body": body}, expect=(201,))
            made = made.get("number") if isinstance(made, dict) else None
            out("opened issue #%s: %s" % ("%d" % made if is_count(made) else "?", issue_title))
        elif (issue.get("body") or "") == body:
            out("issue #%d is up to date: %s" % (issue["number"], issue_title))
        else:
            github.call("PATCH", "/repos/%s/issues/%d" % (target, issue["number"]), {"body": body})
            out("updated issue #%d: %s" % (issue["number"], issue_title))
    return 0


def printed(text, token):
    """The lines of text as the watch prints them: scrubbed, through inert(), each starting with a letter."""
    lines = []
    for line in text.split("\n"):
        line = scrub(line, token)
        if holds_token(line, token):
            line = "a line that held the token is left out"
        line = inert(line)
        lines.append(line if line[:1] in string.ascii_letters else LINE_MARK + line)
    return "".join(line + "\n" for line in lines)


def main(argv=None, environ=None, http=None, stdout=None, stderr=None):
    environ = os.environ if environ is None else environ
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    token = environ.get("GITHUB_TOKEN") or None
    safe = http or urllib_http

    def scrubbed(method, url, headers, body):
        # The raw answer is scrubbed here, and the decoded answer again in GitHub.call.
        status, data = safe(method, url, headers, body)
        return status, data.replace(token.encode("utf-8"), b"***") if token and isinstance(data, bytes) else data

    def out(text):
        stdout.write(printed(text, token))

    try:
        return run(argv, environ, scrubbed, out)
    except WatchError as error:
        stderr.write(printed(str(error), token))
        return 1
    except Exception:
        stderr.write(printed("the watch stopped on an error it does not know:\n" + traceback.format_exc().rstrip("\n"), token))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
