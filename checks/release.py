#!/usr/bin/env python3
"""Tag and release the version in ratchet.json, from the release workflow.

    python3 checks/release.py notes --repo OWNER/NAME   print the release text, with no token and no network
    python3 checks/release.py publish                   tag and release, in the release workflow

D-2026-11-17-release-on-merge, D-2026-11-17-release-verbatim, D-2026-11-17-release-links and
D-2026-11-17-release-narrow-claim.
The release text is one fixed line written here, with the version and links to CHANGELOG.md
and to the files at the tag. Nothing from the changelog is copied. From CHANGELOG.md the script
reads only which versions have an entry. The versions that must already be released are read
with git from the history of main, which a pull request cannot edit: every value that version
in ratchet.json has had on the first-parent history of the commit. An older one that is not
finished fails the run, and the run writes nothing: the message names the commit whose run the
maintainer reruns.

It claims to catch mistakes in normal operation: a run that was cancelled or failed, a publication
that failed, a changelog that was edited. It does not stand against someone who changes the git
data of the runner or deliberately writes a version in an unusual form. Two cheap barriers stand
anyway: every version has one strict form, and a checkout with grafts, replace refs, a shallow file
or alternates is refused before any history is read.

Every failure after the tag is created, of any kind, ends in one message that names the version and
the commit of the tag, says what is missing, and gives the rerun (finish_release).

The first entry of the changelog may be headed "## <version> (unreleased)" (D-2026-11-19-batched-releases).
While it is, no run publishes that version: it reads the tags and the releases, fails as before when an older
version is not finished, and otherwise passes, says so and writes nothing. That holds for a push, a run by hand
and a scheduled run. The release is the push of a commit that gives the entry its date. A version must be
released once a commit on main names it in ratchet.json with an entry that has a date: the changelog at each
commit is read with git beside ratchet.json, and only the one exact unreleased heading, as the first entry,
takes a commit out. A version that main only ever named as unreleased needs nothing. A version that a commit on main
dated must be released whatever the head says: a head that heads it "(unreleased)" again fails and names that commit.

publish reads GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_SHA, GITHUB_REF and GITHUB_EVENT_NAME from the
environment. A scheduled run (GITHUB_EVENT_NAME schedule) writes nothing: it fails and names the version
when the version at the head of main, or an older one, is not finished, and passes when all are.
The token is sent only to https://api.github.com and is never printed. It never moves,
deletes or edits a tag (repo.tags-stay). See checks/README.md for what it claims.

Standard library only. CI runs it on Python 3.9 and the newest Python 3.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True
# Its own directory on the path, named explicitly, so that python3 -I, which leaves the script's directory out of
# sys.path, still finds the modules beside it.
import os  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request

import registry

API = "https://api.github.com"
# The one form of a version (D-2026-11-17-release-narrow-claim): ASCII digits, no leading zero, nothing before or after.
# Every version the script reads must match it, and versions are compared only as pairs of integers (version_key).
VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
FORM = "is not of the form MAJOR.MINOR, in ASCII digits with no leading zero. Nothing was written."
# The one form of the heading of a version, matched against a whole line and nothing else. [0-9] and not \d,
# which in Python matches the digits of every script. \Z and not $, which also matches before a final LF.
HEADING = re.compile(r"^## ([0-9]+\.[0-9]+) \(([0-9]{4}-[0-9]{2}-[0-9]{2})\)\Z")
# The one form of the heading of a version that is not yet released, matched the same way (D-2026-11-19-batched-releases).
UNRELEASED = re.compile(r"^## ([0-9]+\.[0-9]+) \(unreleased\)\Z")
# The one line of a release, written here. Nothing from CHANGELOG.md is copied into it. The links name
# the file and the tree at the tag, with no anchor, so they do not depend on how GitHub makes the anchor of a heading.
RELEASE_LINE = ("Ratchet %(version)s: see [the changelog entry](https://github.com/%(repo)s/blob/v%(version)s/CHANGELOG.md) "
                "and [the files at this tag](https://github.com/%(repo)s/tree/v%(version)s)")
# Versions tagged before Ratchet published releases. Each needs its tag and no release.
BEFORE_RELEASES = ("0.1",)
MAIN = "refs/heads/main"
# The events the workflow runs on. A scheduled run only reads (D-2026-11-17-release-narrow-claim, round 1, finding 1).
EVENTS = ("push", "workflow_dispatch", "schedule")
TAG_PREFIX = "refs/tags/v"
SHA = re.compile(r"^[0-9a-f]{40}\Z")
REPOSITORY = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z")
# Every path the script sends a request to: under one repository, and nothing that leaves it.
API_PATH = re.compile(r"^/repos/[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_./?=&-]*\Z")
PAGES = 100
HISTORY_FILE = "ratchet.json"
CHANGELOG = "CHANGELOG.md"
# A line of git cat-file --batch-check for a file that is there: object, type and size.
BLOB = re.compile(r"^([0-9a-f]{40}) blob ([0-9]+)\Z")


class ReleaseError(Exception):
    """The release cannot be made, or was not finished. The message says what was written."""


def version_key(version):
    """(major, minor) as integers, the one form in which versions are compared. The version has matched VERSION."""
    major, minor = version.split(".")
    return int(major), int(minor)


def name(key):
    """The version of a key, in the one form."""
    return "%s.%s" % key


def shown(value):
    """A value read from a file or an answer, as JSON in ASCII, cut short: text for a message, never Markdown."""
    text = json.dumps(value, ensure_ascii=True)
    return text if len(text) <= 60 else text[:60] + "..."


def checked(value, where):
    """The version, if it is a string of the one form. Else ReleaseError, which names the value and where it came from."""
    if isinstance(value, str) and VERSION.match(value):
        return value
    raise ReleaseError("%s: the version %s %s" % (where, shown(value), FORM))


def read_text(path):
    """The text of a file, read as strict UTF-8."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        raise ReleaseError("%s: the file cannot be read" % os.path.basename(path))
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ReleaseError("CHANGELOG.md: it %s. Every file a check reads is UTF-8" % registry.not_utf8(error))


def changelog_entries(text):
    """[(version, whether it has a date, line number)] for the headings of a changelog, in the order they stand.

    This reads no Markdown. CRLF is read as LF, the text is split at LF, and a line is the heading
    of a version only when the whole line is "## MAJOR.MINOR (YYYY-MM-DD)", or "## MAJOR.MINOR (unreleased)".
    Every other line is passed over, whatever a reader makes of it. Nothing else in the file is read, and
    nothing of it reaches the release. A heading whose version has a leading zero fails.
    """
    entries = []
    for number, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        for form, dated in ((HEADING, True), (UNRELEASED, False)):
            match = form.match(line)
            if match:
                entries.append((checked(match.group(1), "CHANGELOG.md, line %d" % number), dated, number))
    return entries


def changelog_versions(text):
    """The versions that have an entry in a changelog, released or not, in the order they stand."""
    return [version for version, _, _ in changelog_entries(text)]


def unreleased_first(text):
    """The version of the first entry if it is headed "(unreleased)", else None. ReleaseError on any other place of that heading.

    Only the first entry may be unreleased, and a version has one heading.
    """
    entries = changelog_entries(text)
    for position, (version, dated, number) in enumerate(entries):
        if not dated and position > 0:
            raise ReleaseError("CHANGELOG.md, line %d: the entry of %s is headed (unreleased), and only the first entry may be. "
                               "Nothing was written." % (number, version))
    keys = [version_key(version) for version, _, _ in entries]
    for key in sorted(set(keys)):
        if keys.count(key) > 1:
            raise ReleaseError("CHANGELOG.md: the version %s has %d headings. Nothing was written." % (name(key), keys.count(key)))
    return entries[0][0] if entries and not entries[0][1] else None


def git(root, args, data=None):
    """What git prints for args, run on the checkout at root, as bytes. ReleaseError when it fails.

    No GIT_ variable of the environment and no system or global config is used, replace refs are
    not read, the graft file is an empty file in a directory made for this call and not .git/info/grafts,
    and git does not look for a repository above root.
    """
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0",
               GIT_CEILING_DIRECTORIES=os.path.dirname(os.path.realpath(root)), LC_ALL="C")
    try:
        with tempfile.TemporaryDirectory(prefix="ratchet-release-") as scratch:
            env["GIT_GRAFT_FILE"] = os.path.join(scratch, "grafts")
            open(env["GIT_GRAFT_FILE"], "wb").close()
            result = subprocess.run(["git", "--no-replace-objects", "-C", root] + list(args), input=data,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=120)
    except (OSError, subprocess.SubprocessError):
        raise ReleaseError("git %s: it could not be run. Nothing was written." % args[0])
    if result.returncode != 0:
        raise ReleaseError("git %s: exit %d. Nothing was written." % (args[0], result.returncode))
    return result.stdout


def version_at(commit, data):
    """The version in the bytes of ratchet.json at a commit, read strictly."""
    try:
        value = registry.parse_json(data)
    except registry.RegistryError as error:
        raise ReleaseError("ratchet.json at commit %s on main: %s. Nothing was written." % (commit, error))
    if not (isinstance(value, dict) and "version" in value):
        raise ReleaseError("ratchet.json at commit %s on main has no version. Nothing was written." % commit)
    return checked(value["version"], "ratchet.json at commit %s on main" % commit)


def refuse_substitutes(root):
    """Fail if the checkout has anything that makes git read other objects or other parents than the commits hold.

    Run before any history is read. .git/info/grafts and a ref under refs/replace/ change the parents or the objects
    git reads; the reading ignores both, and they are refused anyway. .git/shallow, even empty, makes git stop the
    history at the commits it names. objects/info/alternates makes git read objects that the checkout lacks from
    another store, without checking their hash. A fresh checkout on GitHub has none of them.
    """
    if git(root, ["rev-parse", "--is-shallow-repository"]) != b"false\n":
        raise ReleaseError("the checkout is shallow: the release reads the whole history of main, "
                           "so the workflow checks out with fetch-depth: 0. Nothing was written.")
    answer = git(root, ["rev-parse", "--git-common-dir"])
    if not answer.endswith(b"\n") or b"\n" in answer[:-1]:
        raise ReleaseError("git rev-parse: the answer is not one path. Nothing was written.")
    common = os.path.join(root, os.fsdecode(answer[:-1]))
    for parts, what in ((("info", "grafts"), "changes the parents git reads"),
                        (("objects", "info", "alternates"), "reads objects from another store")):
        if os.path.lexists(os.path.join(common, *parts)):
            raise ReleaseError("the checkout has .git/%s, which %s. Nothing was written." % ("/".join(parts), what))
    refs = git(root, ["for-each-ref", "--format=%(refname)", "refs/replace/"])
    if refs:
        raise ReleaseError("the checkout has the replace ref %s, which swaps one object for another. Nothing was written."
                           % shown(os.fsdecode(refs.split(b"\n")[0])))


def main_history(root, sha):
    """[(commit, version)] for every commit on the first-parent history of sha whose tree holds ratchet.json, newest first.

    That history is main's as it was when sha was pushed. A pull request adds commits on top of it and cannot
    change one in it: the ruleset on main refuses a force-push and a deletion. Every commit is read, not only
    those that git reports as changing the file. The checkout must be at sha, and must have nothing that
    refuse_substitutes refuses.
    """
    refuse_substitutes(root)
    return read_history(root, sha)


def read_history(root, sha):
    """main_history without refuse_substitutes: what git reads, with replace refs and .git/info/grafts ignored."""
    if git(root, ["rev-parse", "--verify", "HEAD^{commit}"]) != (sha + "\n").encode("ascii"):
        raise ReleaseError("the checkout is not at GITHUB_SHA %s. Nothing was written." % sha)
    commits = git(root, ["rev-list", "--first-parent", sha]).decode("ascii", errors="replace").split("\n")
    if commits[-1] != "" or not all(SHA.match(c) for c in commits[:-1]) or commits[0] != sha:
        raise ReleaseError("git rev-list: the answer is not a list of commits from %s. Nothing was written." % sha)
    commits = commits[:-1]
    blobs, contents = read_files(root, commits, HISTORY_FILE)
    missing = None
    for commit, blob in blobs:
        if blob is None:
            missing = missing or commit
        elif missing:
            raise ReleaseError("ratchet.json is missing at commit %s on main, and the earlier commit %s holds it. "
                               "Nothing was written." % (missing, commit))
    versions = {}
    history = []
    for commit, blob in blobs:
        if blob is not None:
            if blob not in versions:
                versions[blob] = version_at(commit, contents[blob])
            history.append((commit, versions[blob]))
    return history


def read_files(root, commits, path):
    """([(commit, object or None)], {object: bytes}): the file at path in each commit, with git, None where it is missing."""
    answer = git(root, ["cat-file", "--batch-check"], "".join("%s:%s\n" % (c, path) for c in commits).encode("ascii"))
    lines = answer.decode("ascii", errors="replace").split("\n")
    if len(lines) != len(commits) + 1 or lines[-1] != "":
        raise ReleaseError("git cat-file: the answer does not have one line for each commit. Nothing was written.")
    blobs = []
    for commit, line in zip(commits, lines):
        match = BLOB.match(line)
        if match:
            blobs.append((commit, match.group(1), int(match.group(2))))
        elif line == "%s:%s missing" % (commit, path):
            blobs.append((commit, None, None))
        else:
            raise ReleaseError("%s at commit %s on main is not a file. Nothing was written." % (path, commit))
    unique = []
    for _, blob, size in blobs:
        if blob is not None and (blob, size) not in unique:
            unique.append((blob, size))
    contents = {}
    if unique:
        answer = git(root, ["cat-file", "--batch"], "".join("%s\n" % blob for blob, _ in unique).encode("ascii"))
        at = 0
        for blob, size in unique:
            header = ("%s blob %d\n" % (blob, size)).encode("ascii")
            end = at + len(header) + size
            if answer[at:at + len(header)] != header or answer[end:end + 1] != b"\n":
                raise ReleaseError("git cat-file: the answer is not of the form expected. Nothing was written.")
            contents[blob] = answer[at + len(header):end]
            at = end + 1
        if at != len(answer):
            raise ReleaseError("git cat-file: the answer is not of the form expected. Nothing was written.")
    return [(commit, blob) for commit, blob, _ in blobs], contents


def read_pending(root, history):
    """The commits of history whose CHANGELOG.md heads the version they name "(unreleased)", as its first entry.

    history is main_history(). The changelog at each commit is read with git, as strict UTF-8 with CRLF read as LF,
    and only its headings, as changelog_entries reads them. A commit whose changelog is missing, or does not have the
    one exact unreleased heading for its version as the first entry, is not pending: its version must be released.
    """
    blobs, contents = read_files(root, [commit for commit, _ in history], CHANGELOG)
    named = dict(history)
    pending = set()
    for commit, blob in blobs:
        if blob is None:
            continue
        try:
            text = contents[blob].decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ReleaseError("CHANGELOG.md at commit %s on main: it %s. Nothing was written." % (commit, registry.not_utf8(error)))
        try:
            entries = changelog_entries(text)
        except ReleaseError as error:
            raise ReleaseError("CHANGELOG.md at commit %s on main: %s" % (commit, error))
        if entries and not entries[0][1] and version_key(entries[0][0]) == version_key(named[commit]):
            pending.add(commit)
    return pending


def release_text(version, repo):
    """The text of the release: RELEASE_LINE for the version and the repository, and nothing else."""
    return RELEASE_LINE % {"version": version, "repo": repo}


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
    """Make one request. On no answer, or any other status than the expected one, fail and say what was written.

    With after None, the failure says only the method, the path and what went wrong: finish_release says the rest.
    """
    try:
        status, data = api(method, path, body)
    except ReleaseError as error:
        if after is None:
            raise
        raise ReleaseError("%s. %s" % (str(error).rstrip("."), after))
    if status != expected:
        raise ReleaseError("%s %s: HTTP %d%s" % (method, path, status, "" if after is None else ". " + after))
    return data


def read_only(api):
    """The api of a scheduled run: it sends a GET and refuses every other request, which is not sent."""

    def call(method, path, body=None):
        if method != "GET":
            raise ReleaseError("%s %s: a scheduled run writes nothing, and the request was not sent" % (method, path))
        return api(method, path, body)

    return call


def malformed(method, path):
    return ReleaseError("%s %s: the answer is not of the form expected. Nothing was written." % (method, path))


def list_tags(api, repo):
    """{version_key: (object type, sha)} for every tag under refs/tags/v, each of the one form."""
    path = "/repos/%s/git/matching-refs/tags/v" % repo
    data = request(api, "GET", path, None, 200, "Nothing was written.")
    if not isinstance(data, list):
        raise malformed("GET", path)
    tags = {}
    for ref in data:
        if not (isinstance(ref, dict) and isinstance(ref.get("ref"), str) and isinstance(ref.get("object"), dict)
                and isinstance(ref["object"].get("type"), str) and isinstance(ref["object"].get("sha"), str)):
            raise malformed("GET", path)
        if not ref["ref"].startswith(TAG_PREFIX):
            raise malformed("GET", path)
        version = checked(ref["ref"][len(TAG_PREFIX):], "GET %s, the tag %s" % (path, shown(ref["ref"])))
        key = version_key(version)
        if key in tags:
            raise malformed("GET", path)
        tags[key] = (ref["object"]["type"], ref["object"]["sha"])
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


# What is not finished after a failure once the tag may exist, and the rerun that finishes it. One form for each
# state, filled with the version, the tag and the commit. A failure after the tag ends in one of these, and in nothing else.
TAG_MAYBE = ("Ratchet %(version)s is not finished: the tag %(tag)s may have been created at commit %(sha)s, and there is no release. "
             "Rerun the release run of commit %(sha)s: it creates the tag if it is missing, then the release.")
TAG_ELSEWHERE = ("Ratchet %(version)s is not finished: the tag %(tag)s was created, and there is no release. Look at the tag by hand. "
                 "If it points at commit %(sha)s, rerun the release run of that commit: it creates only the release.")
RELEASE_MISSING = ("Ratchet %(version)s is not finished: the tag %(tag)s points at commit %(sha)s, and its release is missing or was "
                   "not confirmed. Rerun the release run of commit %(sha)s, which the tag points at: it creates the release if it is "
                   "missing, and writes nothing else.")
TAG_UNCONFIRMED = ("Ratchet %(version)s is not finished: its release was created, and the tag %(tag)s was not confirmed at commit "
                   "%(sha)s. Rerun the release run of commit %(sha)s: it writes nothing if the release is there, and it is green only "
                   "if the tag points at that commit.")


def after_tag(state, error, method, path, version, tag, sha):
    """The one message of a failure once the tag may exist: what failed, then what is not finished and the rerun.

    error is any exception. A ReleaseError says what failed. Any other is named by its type and the request,
    and its text is not shown.
    """
    if isinstance(error, ReleaseError):
        cause = str(error).rstrip(".")
    else:
        cause = "%s %s: an unexpected error (%s)" % (method, path, type(error).__name__)
    return "%s. %s" % (cause, state % {"version": version, "tag": tag, "sha": sha})


def create_tag(api, repo, tag, version, sha):
    """Create the tag at sha. A refusal writes nothing. Every other failure may have written the tag, and says so."""
    ref = "refs/tags/%s" % tag
    path = "/repos/%s/git/refs" % repo
    try:
        status, data = api("POST", path, {"ref": ref, "sha": sha})
    except Exception as error:
        raise ReleaseError(after_tag(TAG_MAYBE, error, "POST", path, version, tag, sha))
    if status == 422:
        raise ReleaseError("POST %s: HTTP 422. The tag %s was not created, and nothing was written." % (path, tag))
    if status != 201:
        raise ReleaseError(after_tag(TAG_MAYBE, ReleaseError("POST %s: HTTP %d" % (path, status)), "POST", path, version, tag, sha))
    if not points_at(data, ref, sha):
        raise ReleaseError(after_tag(TAG_ELSEWHERE, ReleaseError("POST %s: the answer does not say that the tag %s points at %s"
                                                                 % (path, tag, sha)), "POST", path, version, tag, sha))


def finish_release(api, repo, tag, version, body, sha):
    """Create the release for a tag that is at sha, then read the tag back.

    Every failure here, of any kind, ends in one message (after_tag): no answer, an error the script does not
    expect, an HTTP error, an answer that is not JSON or not of the form expected. Nothing after the tag exits without it.
    """
    state, method, path = RELEASE_MISSING, "POST", "/repos/%s/releases" % repo
    try:
        data = request(api, method, path, {"tag_name": tag, "name": "Ratchet %s" % version, "body": body,
                                           "draft": False, "prerelease": False}, 201, None)
        if not (isinstance(data, dict) and data.get("tag_name") == tag and data.get("draft") is False):
            raise ReleaseError("POST %s: the answer is not a published release for %s" % (path, tag))
        state, method, path = TAG_UNCONFIRMED, "GET", "/repos/%s/git/ref/tags/%s" % (repo, tag)
        data = request(api, method, path, None, 200, None)
        if not points_at(data, "refs/tags/%s" % tag, sha):
            raise ReleaseError("GET %s: read back, the tag %s does not point at %s" % (path, tag, sha))
    except Exception as error:
        raise ReleaseError(after_tag(state, error, method, path, version, tag, sha))


def first_commits(history, version, sha, pending=frozenset()):
    """{version_key: the first commit on main whose ratchet.json names it with a dated entry}, after checking the history.

    A commit in pending heads its version "(unreleased)", so it does not count: a rerun of its run publishes nothing.
    A version that only pending commits name is not in the answer.
    """
    if not history or history[0][0] != sha:
        raise ReleaseError("ratchet.json is not in commit %s. Nothing was written." % sha)
    if version_key(history[0][1]) != version_key(version):
        raise ReleaseError("ratchet.json in the checkout names %s, and at commit %s it names %s. Nothing was written."
                           % (version, sha, history[0][1]))
    first = {}
    for commit, named in history:
        if version_key(named) > version_key(version):
            raise ReleaseError("ratchet.json at commit %s on main names %s, newer than %s. Nothing was written." % (commit, named, version))
        if commit not in pending:
            first[version_key(named)] = commit
    return first


def unfinished(first, version, tags, releases):
    """Every older version that main has named and that is not finished, with what it lacks and which run to rerun.

    first and tags are keyed by version_key, releases by tag name.
    """
    problems = []
    for key in sorted(first):
        if key >= version_key(version):
            continue
        older = name(key)
        if key not in tags:
            problems.append("%s: no tag. Rerun the release run of commit %s, the first commit on main whose ratchet.json names %s."
                            % (older, first[key], older))
        elif older not in BEFORE_RELEASES and False not in releases.get("v" + older, []):
            kind, target = tags[key]
            if kind == "commit":
                problems.append("%s: a tag and no published release. Rerun the release run of commit %s, which the tag points at."
                                % (older, target))
            else:
                problems.append("%s: a tag and no published release. The tag is not a plain tag of a commit: look at it by hand." % older)
    return problems


def publish(version, text, history, repo, sha, api, out, report=False, pending=frozenset()):
    """Tag sha as v<version> and release it, or find that it is done. ReleaseError on every fault.

    history is main_history() of sha. Only versions up to this one are looked at. Nothing is
    written before every check has passed, and nothing is written for an older version. A tag
    is created and never moved, deleted or edited. Versions are compared as version_key, pairs of integers.
    With report, the run of a schedule, it writes nothing: where a run of a push would write, it fails and names
    the version, the commit and what is missing. pending is read_pending() of history. When the first entry is
    headed "(unreleased)", nothing is written for this version, and the run passes once every older one is finished.
    """
    this = version_key(checked(version, "ratchet.json in the checkout"))
    entries = [version_key(v) for v in changelog_versions(text)]
    if this not in entries:
        raise ReleaseError("CHANGELOG.md has no entry for %s, the version in ratchet.json" % version)
    newest = max(entries)
    if newest != this:
        raise ReleaseError("the newest entry in CHANGELOG.md is %s, and ratchet.json says %s" % (name(newest), version))
    held = unreleased_first(text) is not None
    if held and sha not in pending:
        raise ReleaseError('CHANGELOG.md in the checkout heads %s "(unreleased)", and at commit %s it does not. Nothing was written.'
                           % (version, sha))
    if sha in pending and not held:
        raise ReleaseError('CHANGELOG.md at commit %s heads %s "(unreleased)", and in the checkout it does not. Nothing was written.'
                           % (sha, version))
    first = first_commits(history, version, sha, pending)
    body = release_text(version, repo)
    tag = "v%s" % version

    tags = dict((key, target) for key, target in list_tags(api, repo).items() if key <= this)
    releases = {}
    for tag_name, draft in list_releases(api, repo):
        releases.setdefault(tag_name, []).append(draft)

    for key in sorted(tags):
        if key not in entries:
            raise ReleaseError("the tag v%s has no entry in CHANGELOG.md. Nothing was written." % name(key))
    problems = unfinished(first, version, tags, releases)
    if problems:
        raise ReleaseError("an older version is not finished. %s Then rerun this run. Nothing was written." % " ".join(problems))
    mine = releases.get(tag, [])
    if len(mine) > 1:
        raise ReleaseError("there are %d releases for %s. Nothing was written." % (len(mine), tag))

    if held:
        if this in tags:
            raise ReleaseError('the tag %s exists, and the entry of %s in CHANGELOG.md is headed "(unreleased)". '
                               "A released version stays released. Nothing was written." % (tag, version))
        if mine:
            raise ReleaseError("a release for %s exists, and the tag does not. Publish or remove it by hand. Nothing was written." % tag)
        if this in first:
            # A commit on main dated this version, and its run did not release it. The heading that came back does not
            # take the duty away (PR #50, round 2, finding 1).
            raise ReleaseError('Ratchet %s is not finished: commit %s on main gave its entry in CHANGELOG.md a date, and at commit %s '
                               'it is headed "(unreleased)" again. A version dated on main must be released. Give the entry its date '
                               "again, so that the run of that push releases it, or rerun the release run of commit %s, the first "
                               "commit on main that dated it. Nothing was written." % (version, first[this], sha, first[this]))
        out.write('Ratchet %s is not released: its entry in CHANGELOG.md is headed "(unreleased)". Every older version is finished. '
                  "Nothing was written.\n" % version)
        return

    if this not in tags:
        if mine:
            raise ReleaseError("a release for %s exists, and the tag does not. Publish or remove it by hand. Nothing was written." % tag)
        if report:
            raise ReleaseError("Ratchet %s is not finished: there is no tag %s and no release, and ratchet.json at the head of main, "
                               "commit %s, names %s. A scheduled run writes nothing. Rerun the release run of commit %s, the first "
                               "commit on main whose ratchet.json names %s, or start the workflow by hand on main."
                               % (version, tag, sha, version, first[this], version))
        create_tag(api, repo, tag, version, sha)
        finish_release(api, repo, tag, version, body, sha)
        out.write("Tagged %s at %s and released Ratchet %s.\n" % (tag, sha, version))
        return

    kind, target = tags[this]
    if kind == "commit" and target == sha:
        if mine and mine[0]:
            raise ReleaseError("a draft release for %s exists. Publish it by hand. Nothing was written." % tag)
        if mine:
            out.write("%s is tagged at this commit and released. Nothing to do.\n" % tag)
            return
        if report:
            raise ReleaseError("Ratchet %s is not finished: the tag %s points at commit %s, the head of main, and there is no published "
                               "release. A scheduled run writes nothing. Rerun the release run of commit %s, which the tag points at: "
                               "it creates only the release." % (version, tag, sha, sha))
        # A rerun of this version's own run: the tag is at the approved commit, and the text is
        # the fixed line for this version. Only the release is created.
        finish_release(api, repo, tag, version, body, sha)
        out.write("The tag %s was already at %s. Released Ratchet %s.\n" % (tag, sha, version))
        return

    if kind != "commit":
        raise ReleaseError("the tag %s points at another commit than this one: it is not a plain tag of a commit. "
                           "The tag is not moved. Nothing was written." % tag)
    if not mine or mine[0]:
        raise ReleaseError("the tag %s points at another commit than this one, and has no published release. The tag is not moved. "
                           "Rerun the release run of commit %s, which the tag points at. Nothing was written." % (tag, target))
    path = "/repos/%s/compare/%s...%s" % (repo, target, sha)
    data = request(api, "GET", path, None, 200, "Nothing was written.")
    if not (isinstance(data, dict) and data.get("status") == "ahead"):
        raise ReleaseError("the tag %s points at a commit that is not an earlier commit of this one. "
                           "The tag is not moved. Nothing was written." % tag)
    out.write("%s is released at an earlier commit, and this commit does not raise the version. Nothing to do.\n" % tag)


def checkout_version(root):
    """The version in ratchet.json in the checkout, of the one form, in a file that registry.py reads without a fault."""
    path = os.path.join(root, "ratchet.json")
    try:
        data = registry.load_json(path)
    except registry.RegistryError:
        data = None  # registry.load says what is wrong, with the path.
    if isinstance(data, dict) and "version" in data:
        checked(data["version"], "ratchet.json in the checkout")
    try:
        return checked(registry.load(path)["version"], "ratchet.json in the checkout")
    except registry.RegistryError as error:
        raise ReleaseError(str(error))


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
        version = checkout_version(root)
        path = os.path.join(root, "CHANGELOG.md")
        if args.command == "notes":
            if not REPOSITORY.match(args.repo):
                raise ReleaseError("--repo is not of the form OWNER/NAME")
            if version_key(version) not in [version_key(v) for v in changelog_versions(read_text(path))]:
                raise ReleaseError("CHANGELOG.md has no entry for %s, the version in ratchet.json" % version)
            out.write(release_text(version, args.repo) + "\n")
            return 0
        if not environ.get("GITHUB_TOKEN"):
            raise ReleaseError("GITHUB_TOKEN is not set")
        repo = environment(environ, "GITHUB_REPOSITORY", REPOSITORY)
        sha = environment(environ, "GITHUB_SHA", SHA)
        if environ.get("GITHUB_REF") != MAIN:
            raise ReleaseError("GITHUB_REF is not %s: a release is made only from main" % MAIN)
        event = environ.get("GITHUB_EVENT_NAME")
        if event not in EVENTS:
            raise ReleaseError("GITHUB_EVENT_NAME is not push, workflow_dispatch or schedule")
        report = event == "schedule"
        api = github(environ["GITHUB_TOKEN"], opener)
        text = read_text(path)
        history = main_history(root, sha)
        publish(version, text, history, repo, sha, read_only(api) if report else api, out, report=report,
                pending=read_pending(root, history))
        return 0
    except ReleaseError as error:
        message = str(error)
        # A message may name a value from an answer of the API, such as a tag. The token is never in one.
        if environ.get("GITHUB_TOKEN"):
            message = message.replace(environ["GITHUB_TOKEN"], "[the token]")
        err.write("release: %s\n" % message)
        return 1


if __name__ == "__main__":
    sys.exit(main())
