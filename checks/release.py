#!/usr/bin/env python3
"""Tag and release the version in ratchet.json, from the release workflow.

    python3 checks/release.py notes --repo OWNER/NAME   print the release text, with no token and no network
    python3 checks/release.py publish                   tag and release, in the release workflow

D-2026-11-17-release-on-merge and D-2026-11-17-release-verbatim. The release text is the
changelog entry as it stands, then one fixed line. An older version that is not finished
fails the run, and the run writes nothing: the maintainer reruns the run of that version.

publish reads GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_SHA and GITHUB_REF from the
environment. The token is sent only to https://api.github.com and is never printed. It
never moves, deletes or edits a tag (repo.tags-stay). See checks/README.md for what it claims.

Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

import registry

API = "https://api.github.com"
TITLE = "# Changelog"
HEADING = re.compile(r"^## ([0-9]+\.[0-9]+) \(([0-9]{4}-[0-9]{2}-[0-9]{2})\)\Z")
# A line ends with LF or CRLF. Every other character that a reader could take for the end of a line
# fails, and so does every other control character than a tab: C0, DEL and C1, U+2028 and U+2029.
CONTROL = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029]")
CONTROL_NAMES = {"\r": "a carriage return without LF", "\x0b": "a vertical tab", "\x0c": "a form feed",
                 "\x85": "a next line", "\u2028": "a line separator", "\u2029": "a paragraph separator"}
# What can stand before a block on a line: any spaces and tabs, the > of a block quote, and the marker of
# a list item. A heading, a code block, HTML or a link definition after any of these is refused.
CONTAINER = r"(?:[ \t>]|[*+-](?=[ \t]|\Z)|[0-9]{1,9}[.)](?=[ \t]|\Z))*"
# What a reader takes for a heading of level one or two, anywhere a block can start.
HEADING_LIKE = re.compile(r"^" + CONTAINER + r"#{1,2}(?:[ \t]|\Z)")
# What a reader takes for the underline of a heading after a line of text, of any length and in a block quote or a list item.
UNDERLINE = re.compile(r"^[ \t>]*(?:=+|-+)[ \t]*\Z")
# An HTML heading of level one or two, anywhere outside a code block, also in a code span.
HTML_HEADING = re.compile(r"<h[12](?:[\s/>]|\Z)", re.IGNORECASE)
HTML_LIKE = re.compile(r"^" + CONTAINER + r"<")
# A blank line holds nothing but spaces and tabs. A no-break space or another space that is not ASCII is text.
BLANK = " \t"
FENCE_LIKE = re.compile(r"^ {0,3}(?:```|~~~)")
FENCE_ANYWHERE = re.compile(r"^" + CONTAINER + r"(?:```|~~~)")
FENCE_OPEN = re.compile(r"^```[a-z]*\Z")
LINK_DEFINITION = re.compile(r"^" + CONTAINER + r"\[[^\]]+\]:")
MARKER = re.compile(r"^<!-- generated:[a-z-]+(?: [a-z0-9-]+)? -->\Z")
END = "<!-- /generated -->"
# The one line the script adds to an entry, last, after a blank line.
FILES_LINE = "The files of this version: [v%(version)s](https://github.com/%(repo)s/tree/v%(version)s)"
# Versions tagged before Ratchet published releases. Each needs its tag and no release.
BEFORE_RELEASES = ("0.1",)
MAIN = "refs/heads/main"
TAG_REF = re.compile(r"^refs/tags/v([0-9]+\.[0-9]+)\Z")
SHA = re.compile(r"^[0-9a-f]{40}\Z")
REPOSITORY = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z")
# Every path the script sends a request to: under one repository, and nothing that leaves it.
API_PATH = re.compile(r"^/repos/[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_./?=&-]*\Z")
PAGES = 100


class ReleaseError(Exception):
    """The release cannot be made, or was not finished. The message says what was written."""


class Entry:
    def __init__(self, version, date, line, lines):
        self.version = version
        self.date = date
        self.line = line
        self.lines = lines


def version_key(version):
    major, minor = version.split(".")
    return int(major), int(minor)


def read_changelog(path):
    """The entries of a changelog file. Strict UTF-8, and CRLF read as LF."""
    return parse_changelog(read_text(path))


def read_text(path):
    """The text of a file, read as strict UTF-8."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        raise ReleaseError("%s: the file cannot be read" % os.path.basename(path))
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ReleaseError("CHANGELOG.md: it %s. Every file a check reads is UTF-8" % registry.not_utf8(error))
    return text


def parse_changelog(text):
    """The entries of a changelog, newest first, or ReleaseError with the first fault.

    CRLF is read as LF. Any other character that could end a line, and any other control
    character than a tab, fails with its line, before anything else is read. Only a line
    "## MAJOR.MINOR (YYYY-MM-DD)" at the start of a line and outside a code block starts an
    entry. Anything else a reader could take for a heading of level one or two fails: after
    spaces or a tab, in a list item or a block quote, made with an underline, or in HTML. So
    does anything that could hide one: a code block opened in another way than three
    backticks at the start of a line, a comment, HTML, a link definition, text before the
    first entry.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    for number, line in enumerate(lines, 1):
        found = CONTROL.search(line)
        if found:
            character = found.group(0)
            raise ReleaseError("CHANGELOG.md:%d: %s (U+%04X). A line here ends with LF or CRLF, and the only control character "
                               "in the text is a tab" % (number, CONTROL_NAMES.get(character, "a control character"), ord(character)))
    if lines[0] != TITLE:
        raise ReleaseError('CHANGELOG.md:1: the first line is "%s"' % TITLE)
    entries = []
    fence = False
    previous = ""
    for number, line in enumerate(lines[1:], 2):
        where = "CHANGELOG.md:%d" % number
        if fence:
            if FENCE_LIKE.match(line):
                if line != "```":
                    raise ReleaseError("%s: a code block here opens and closes with ``` at the start of the line, closes with ``` alone" % where)
                fence = False
            if entries:
                entries[-1].lines.append(line)
            previous = ""
            continue
        if FENCE_ANYWHERE.match(line):
            if not FENCE_OPEN.match(line):
                raise ReleaseError("%s: a code block here opens and closes with ``` at the start of the line, closes with ``` alone" % where)
            fence = True
        elif HEADING_LIKE.match(line):
            match = HEADING.match(line)
            if not match:
                raise ReleaseError('%s: a heading here is "## MAJOR.MINOR (YYYY-MM-DD)", found %r' % (where, line))
            version = match.group(1)
            if any(e.version == version for e in entries):
                raise ReleaseError("%s: a second entry for %s" % (where, version))
            if entries and version_key(version) >= version_key(entries[-1].version):
                raise ReleaseError("%s: the entries must stand newest first, and %s comes after %s" % (where, version, entries[-1].version))
            entries.append(Entry(version, match.group(2), number, []))
            previous = ""
            continue
        elif UNDERLINE.match(line) and previous.strip(BLANK):
            raise ReleaseError("%s: a heading made with an underline. Headings here start with ##" % where)
        elif HTML_HEADING.search(line):
            raise ReleaseError("%s: an HTML heading. Headings here start with ##, and there is no HTML" % where)
        elif (HTML_LIKE.match(line) or line.lstrip().startswith("<")) and not (MARKER.match(line) or line == END):
            raise ReleaseError("%s: the only comments here are the markers of generated blocks, each alone on its line, and there is no HTML" % where)
        elif LINK_DEFINITION.match(line):
            raise ReleaseError("%s: a link definition. Links here are written inline, so that each entry holds its own" % where)
        if not entries:
            if line.strip(BLANK):
                raise ReleaseError("%s: nothing but blank lines may stand before the first entry" % where)
        else:
            entries[-1].lines.append(line)
        previous = line
    if fence:
        raise ReleaseError("CHANGELOG.md: a code block is opened and never closed")
    if not entries:
        raise ReleaseError("CHANGELOG.md: there is no entry")
    for entry in entries:
        if not any(line.strip() for line in entry.lines if not (MARKER.match(line) or line == END)):
            raise ReleaseError("CHANGELOG.md:%d: the entry for %s is empty" % (entry.line, entry.version))
    return entries


def release_text(entry, repo):
    """The text of the release: the lines of the entry as they stand, without the blank lines
    around them, then a blank line and FILES_LINE. Nothing in the entry is changed."""
    lines = list(entry.lines)
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n\n" + FILES_LINE % {"version": entry.version, "repo": repo}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is never followed, so the token is never sent to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def default_opener():
    return urllib.request.build_opener(NoRedirect)


def github(token, opener=None):
    """A function (method, path, body) -> (status, data) for the GitHub API.

    data is the parsed answer for a status below 400, else None. Nothing from the body of
    an answer with an error is read. The token goes in one header, to api.github.com only.
    """
    opener = opener or default_opener()

    def call(method, path, body=None):
        if not API_PATH.match(path) or "/../" in path or "/./" in path:
            raise ReleaseError("%s: a request goes to a path under /repos/OWNER/NAME/ on %s, and to nothing else" % (method, API))
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(API + path, data=data, method=method, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "ratchet-release",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with opener.open(request, timeout=30) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as error:
            error.close()
            return error.code, None
        except (urllib.error.URLError, OSError, ValueError):
            raise ReleaseError("%s %s: no answer" % (method, path))
        if status >= 300:
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            raise ReleaseError("%s %s: HTTP %d, and the answer is not JSON" % (method, path, status))

    return call


def request(api, method, path, body, expected, after):
    """Make one request. On any other status than the expected one, fail and say what was written."""
    status, data = api(method, path, body)
    if status != expected:
        raise ReleaseError("%s %s: HTTP %d. %s" % (method, path, status, after))
    return data


def malformed(method, path):
    return ReleaseError("%s %s: the answer is not of the form expected. Nothing was written." % (method, path))


def list_tags(api, repo):
    """{version: (object type, sha)} for every tag under refs/tags/v."""
    path = "/repos/%s/git/matching-refs/tags/v" % repo
    data = request(api, "GET", path, None, 200, "Nothing was written.")
    if not isinstance(data, list):
        raise malformed("GET", path)
    tags = {}
    for ref in data:
        if not (isinstance(ref, dict) and isinstance(ref.get("ref"), str) and isinstance(ref.get("object"), dict)
                and isinstance(ref["object"].get("type"), str) and isinstance(ref["object"].get("sha"), str)):
            raise malformed("GET", path)
        match = TAG_REF.match(ref["ref"])
        if not match:
            raise ReleaseError("GET %s: a tag under refs/tags/v is not of the form vMAJOR.MINOR. Nothing was written." % path)
        tags[match.group(1)] = (ref["object"]["type"], ref["object"]["sha"])
    return tags


def list_releases(api, repo):
    """Every release, drafts too: [(tag name, draft)]."""
    releases = []
    for page in range(1, PAGES + 1):
        path = "/repos/%s/releases?per_page=100&page=%d" % (repo, page)
        data = request(api, "GET", path, None, 200, "Nothing was written.")
        if not isinstance(data, list):
            raise malformed("GET", path)
        for item in data:
            if not (isinstance(item, dict) and isinstance(item.get("tag_name"), str) and isinstance(item.get("draft"), bool)):
                raise malformed("GET", path)
            releases.append((item["tag_name"], item["draft"]))
        if len(data) < 100:
            return releases
    raise ReleaseError("GET /repos/%s/releases: more than %d pages. Nothing was written." % (repo, PAGES))


def points_at(data, ref, sha):
    return (isinstance(data, dict) and data.get("ref") == ref and isinstance(data.get("object"), dict)
            and data["object"].get("type") == "commit" and data["object"].get("sha") == sha)


def create_release(api, repo, tag, version, body, sha):
    """Create the release for a tag that is at sha, then read the tag back."""
    path = "/repos/%s/releases" % repo
    data = request(api, "POST", path, {"tag_name": tag, "name": "Ratchet %s" % version, "body": body,
                                       "draft": False, "prerelease": False}, 201,
                   "The tag %s is at %s and has no release. Rerun this run: it finds the tag at this commit and creates only the release." % (tag, sha))
    if not (isinstance(data, dict) and data.get("tag_name") == tag and data.get("draft") is False):
        raise ReleaseError("POST %s: the answer is not a published release for %s. Look at the releases by hand." % (path, tag))
    ref = "refs/tags/%s" % tag
    path = "/repos/%s/git/ref/tags/%s" % (repo, tag)
    data = request(api, "GET", path, None, 200, "The release for %s was created, and its tag could not be read back." % tag)
    if not points_at(data, ref, sha):
        raise ReleaseError("GET %s: read back, the tag %s does not point at %s. The release was created. Look at it by hand." % (path, tag, sha))


def unfinished(entries, version, tags, releases):
    """Every older version in the changelog that is not finished, with what it lacks."""
    problems = []
    for entry in sorted(entries, key=lambda e: version_key(e.version)):
        if version_key(entry.version) >= version_key(version):
            continue
        if entry.version not in tags:
            problems.append("%s: no tag" % entry.version)
        elif entry.version not in BEFORE_RELEASES and False not in releases.get("v" + entry.version, []):
            problems.append("%s: a tag and no published release" % entry.version)
    return problems


def publish(version, text, repo, sha, api, out):
    """Tag sha as v<version> and release it, or find that it is done. ReleaseError on every fault.

    Only versions up to this one are looked at. Nothing is written before every check has
    passed, and nothing is written for an older version. A tag is created and never moved,
    deleted or edited.
    """
    entries = parse_changelog(text)
    entry = next((e for e in entries if e.version == version), None)
    if entry is None:
        raise ReleaseError("CHANGELOG.md has no entry for %s, the version in ratchet.json" % version)
    if entries[0].version != version:
        raise ReleaseError("the newest entry in CHANGELOG.md is %s, and ratchet.json says %s" % (entries[0].version, version))
    body = release_text(entry, repo)
    tag = "v%s" % version

    tags = dict((v, target) for v, target in list_tags(api, repo).items() if version_key(v) <= version_key(version))
    releases = {}
    for name, draft in list_releases(api, repo):
        releases.setdefault(name, []).append(draft)

    known = set(e.version for e in entries)
    for name in sorted(tags, key=version_key):
        if name not in known:
            raise ReleaseError("the tag v%s has no entry in CHANGELOG.md. Nothing was written." % name)
    problems = unfinished(entries, version, tags, releases)
    if problems:
        raise ReleaseError("an older version is not finished (%s). Rerun the release run of the commit that raised the version "
                           "to it, then this run. Nothing was written." % "; ".join(problems))
    mine = releases.get(tag, [])
    if len(mine) > 1:
        raise ReleaseError("there are %d releases for %s. Nothing was written." % (len(mine), tag))

    if version not in tags:
        if mine:
            raise ReleaseError("a release for %s exists, and the tag does not. Publish or remove it by hand. Nothing was written." % tag)
        ref = "refs/tags/%s" % tag
        path = "/repos/%s/git/refs" % repo
        data = request(api, "POST", path, {"ref": ref, "sha": sha}, 201,
                       "The tag %s was not created, and nothing was written." % tag)
        if not points_at(data, ref, sha):
            raise ReleaseError("POST %s: the answer says that the tag %s points at another commit than %s. "
                               "No release was created. Look at the tag by hand." % (path, tag, sha))
        create_release(api, repo, tag, version, body, sha)
        out.write("Tagged %s at %s and released Ratchet %s.\n" % (tag, sha, version))
        return

    kind, target = tags[version]
    if kind == "commit" and target == sha:
        if mine and mine[0]:
            raise ReleaseError("a draft release for %s exists. Publish it by hand. Nothing was written." % tag)
        if mine:
            out.write("%s is tagged at this commit and released. Nothing to do.\n" % tag)
            return
        # A rerun of this version's own run: the tag is at the approved commit, and the text is
        # the entry at that commit. Only the release is created.
        create_release(api, repo, tag, version, body, sha)
        out.write("The tag %s was already at %s. Released Ratchet %s.\n" % (tag, sha, version))
        return

    if kind != "commit":
        raise ReleaseError("the tag %s points at another commit than this one: it is not a plain tag of a commit. "
                           "The tag is not moved. Nothing was written." % tag)
    if not mine or mine[0]:
        raise ReleaseError("the tag %s points at another commit than this one, and has no published release. The tag is not moved. "
                           "Rerun the release run of the commit it points at. Nothing was written." % tag)
    path = "/repos/%s/compare/%s...%s" % (repo, target, sha)
    data = request(api, "GET", path, None, 200, "Nothing was written.")
    if not (isinstance(data, dict) and data.get("status") == "ahead"):
        raise ReleaseError("the tag %s points at a commit that is not an earlier commit of this one. "
                           "The tag is not moved. Nothing was written." % tag)
    out.write("%s is released at an earlier commit, and this commit does not raise the version. Nothing to do.\n" % tag)


def environment(environ, name, form):
    value = environ.get(name, "")
    if not form.match(value):
        raise ReleaseError("%s is not set, or is not of its form" % name)
    return value


def main(argv=None, environ=None, opener=None, out=None, err=None, root=None):
    environ = os.environ if environ is None else environ
    root = root or registry.ROOT
    out = out or sys.stdout
    err = err or sys.stderr
    parser = argparse.ArgumentParser(description="Tag and release the version in ratchet.json.")
    commands = parser.add_subparsers(dest="command", required=True)
    notes = commands.add_parser("notes", help="print the release text for the version in ratchet.json")
    notes.add_argument("--repo", required=True, help="OWNER/NAME, for the links in the text")
    commands.add_parser("publish", help="tag and release, in the release workflow")
    args = parser.parse_args(argv)
    try:
        try:
            version = registry.load(os.path.join(root, "ratchet.json"))["version"]
        except registry.RegistryError as error:
            raise ReleaseError(str(error))
        path = os.path.join(root, "CHANGELOG.md")
        if args.command == "notes":
            if not REPOSITORY.match(args.repo):
                raise ReleaseError("--repo is not of the form OWNER/NAME")
            entries = read_changelog(path)
            entry = next((e for e in entries if e.version == version), None)
            if entry is None:
                raise ReleaseError("CHANGELOG.md has no entry for %s, the version in ratchet.json" % version)
            out.write(release_text(entry, args.repo) + "\n")
            return 0
        if not environ.get("GITHUB_TOKEN"):
            raise ReleaseError("GITHUB_TOKEN is not set")
        repo = environment(environ, "GITHUB_REPOSITORY", REPOSITORY)
        sha = environment(environ, "GITHUB_SHA", SHA)
        if environ.get("GITHUB_REF") != MAIN:
            raise ReleaseError("GITHUB_REF is not %s: a release is made only from main" % MAIN)
        publish(version, read_text(path), repo, sha, github(environ["GITHUB_TOKEN"], opener), out)
        return 0
    except ReleaseError as error:
        err.write("release: %s\n" % error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
