#!/usr/bin/env python3
"""Tag and release the version in ratchet.json, from the release workflow.

    python3 checks/release.py notes --repo OWNER/NAME   print the release text, with no token and no network
    python3 checks/release.py publish                   tag and release, in the release workflow

D-2026-11-17-release-on-merge, D-2026-11-17-release-verbatim and D-2026-11-17-release-links.
The release text is one fixed line written here, with the version and links to CHANGELOG.md
and to the files at the tag. Nothing from the changelog is copied. From CHANGELOG.md the script
reads only which versions have an entry. The versions that must already be released are read
with git from the history of main, which a pull request cannot edit: every value that version
in ratchet.json has had on the first-parent history of the commit. An older one that is not
finished fails the run, and the run writes nothing: the message names the commit whose run the
maintainer reruns.

publish reads GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_SHA and GITHUB_REF from the
environment. The token is sent only to https://api.github.com and is never printed. It
never moves, deletes or edits a tag (repo.tags-stay). See checks/README.md for what it claims.

Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

import registry

API = "https://api.github.com"
# The one form of the heading of a version, matched against a whole line and nothing else. [0-9] and not \d,
# which in Python matches the digits of every script. \Z and not $, which also matches before a final LF.
HEADING = re.compile(r"^## ([0-9]+\.[0-9]+) \(([0-9]{4}-[0-9]{2}-[0-9]{2})\)\Z")
# The one line of a release, written here. Nothing from CHANGELOG.md is copied into it. The links name
# the file and the tree at the tag, with no anchor, so they do not depend on how GitHub makes the anchor of a heading.
RELEASE_LINE = ("Ratchet %(version)s: see [the changelog entry](https://github.com/%(repo)s/blob/v%(version)s/CHANGELOG.md) "
                "and [the files at this tag](https://github.com/%(repo)s/tree/v%(version)s)")
# Versions tagged before Ratchet published releases. Each needs its tag and no release.
BEFORE_RELEASES = ("0.1",)
MAIN = "refs/heads/main"
TAG_REF = re.compile(r"^refs/tags/v([0-9]+\.[0-9]+)\Z")
SHA = re.compile(r"^[0-9a-f]{40}\Z")
REPOSITORY = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z")
# Every path the script sends a request to: under one repository, and nothing that leaves it.
API_PATH = re.compile(r"^/repos/[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_./?=&-]*\Z")
PAGES = 100
HISTORY_FILE = "ratchet.json"
# A line of git cat-file --batch-check for a file that is there: object, type and size.
BLOB = re.compile(r"^([0-9a-f]{40}) blob ([0-9]+)\Z")


class ReleaseError(Exception):
    """The release cannot be made, or was not finished. The message says what was written."""


def version_key(version):
    major, minor = version.split(".")
    return int(major), int(minor)


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


def changelog_versions(text):
    """The versions that have an entry in a changelog, in the order they stand.

    This reads no Markdown. CRLF is read as LF, the text is split at LF, and a line is the heading
    of a version only when the whole line is "## MAJOR.MINOR (YYYY-MM-DD)". Every other line is
    passed over, whatever a reader makes of it. Nothing else in the file is read, and nothing of it
    reaches the release.
    """
    versions = []
    for line in text.replace("\r\n", "\n").split("\n"):
        match = HEADING.match(line)
        if match:
            versions.append(match.group(1))
    return versions


def git(root, args, data=None):
    """What git prints for args, run on the checkout at root, as bytes. ReleaseError when it fails.

    No GIT_ variable of the environment and no system or global config is used, replace refs are
    not read, and git does not look for a repository above root.
    """
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0",
               GIT_CEILING_DIRECTORIES=os.path.dirname(os.path.realpath(root)), LC_ALL="C")
    try:
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
    if not (isinstance(value, dict) and isinstance(value.get("version"), str) and registry.VERSION.match(value["version"])):
        raise ReleaseError("ratchet.json at commit %s on main has no version of the form MAJOR.MINOR. Nothing was written." % commit)
    return value["version"]


def main_history(root, sha):
    """[(commit, version)] for every commit on the first-parent history of sha whose tree holds ratchet.json, newest first.

    That history is main's as it was when sha was pushed. A pull request adds commits on top of it and cannot
    change one in it: the ruleset on main refuses a force-push and a deletion. Every commit is read, not only
    those that git reports as changing the file. The checkout must be at sha and must not be shallow.
    """
    if git(root, ["rev-parse", "--is-shallow-repository"]) != b"false\n":
        raise ReleaseError("the checkout is shallow: the release reads the whole history of main, "
                           "so the workflow checks out with fetch-depth: 0. Nothing was written.")
    if git(root, ["rev-parse", "--verify", "HEAD^{commit}"]) != (sha + "\n").encode("ascii"):
        raise ReleaseError("the checkout is not at GITHUB_SHA %s. Nothing was written." % sha)
    commits = git(root, ["rev-list", "--first-parent", sha]).decode("ascii", errors="replace").split("\n")
    if commits[-1] != "" or not all(SHA.match(c) for c in commits[:-1]) or commits[0] != sha:
        raise ReleaseError("git rev-list: the answer is not a list of commits from %s. Nothing was written." % sha)
    commits = commits[:-1]
    answer = git(root, ["cat-file", "--batch-check"], "".join("%s:%s\n" % (c, HISTORY_FILE) for c in commits).encode("ascii"))
    lines = answer.decode("ascii", errors="replace").split("\n")
    if len(lines) != len(commits) + 1 or lines[-1] != "":
        raise ReleaseError("git cat-file: the answer does not have one line for each commit. Nothing was written.")
    blobs = []
    for commit, line in zip(commits, lines):
        match = BLOB.match(line)
        if match:
            blobs.append((commit, match.group(1), int(match.group(2))))
        elif line == "%s:%s missing" % (commit, HISTORY_FILE):
            blobs.append((commit, None, None))
        else:
            raise ReleaseError("ratchet.json at commit %s on main is not a file. Nothing was written." % commit)
    missing = None
    for commit, blob, _ in blobs:
        if blob is None:
            missing = missing or commit
        elif missing:
            raise ReleaseError("ratchet.json is missing at commit %s on main, and the earlier commit %s holds it. "
                               "Nothing was written." % (missing, commit))
    unique = []
    for _, blob, size in blobs:
        if blob is not None and (blob, size) not in unique:
            unique.append((blob, size))
    answer = git(root, ["cat-file", "--batch"], "".join("%s\n" % blob for blob, _ in unique).encode("ascii"))
    contents = {}
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
    versions = {}
    history = []
    for commit, blob, _ in blobs:
        if blob is not None:
            if blob not in versions:
                versions[blob] = version_at(commit, contents[blob])
            history.append((commit, versions[blob]))
    return history


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


def first_commits(history, version, sha):
    """{version: the first commit on main whose ratchet.json names it}, after checking the history against this run."""
    if not history or history[0][0] != sha:
        raise ReleaseError("ratchet.json is not in commit %s. Nothing was written." % sha)
    if history[0][1] != version:
        raise ReleaseError("ratchet.json in the checkout names %s, and at commit %s it names %s. Nothing was written."
                           % (version, sha, history[0][1]))
    first = {}
    for commit, named in history:
        if version_key(named) > version_key(version):
            raise ReleaseError("ratchet.json at commit %s on main names %s, newer than %s. Nothing was written." % (commit, named, version))
        first[named] = commit
    return first


def unfinished(first, version, tags, releases):
    """Every older version that main has named and that is not finished, with what it lacks and which run to rerun."""
    problems = []
    for older in sorted(first, key=version_key):
        if version_key(older) >= version_key(version):
            continue
        if older not in tags:
            problems.append("%s: no tag. Rerun the release run of commit %s, the first commit on main whose ratchet.json names %s."
                            % (older, first[older], older))
        elif older not in BEFORE_RELEASES and False not in releases.get("v" + older, []):
            kind, target = tags[older]
            if kind == "commit":
                problems.append("%s: a tag and no published release. Rerun the release run of commit %s, which the tag points at."
                                % (older, target))
            else:
                problems.append("%s: a tag and no published release. The tag is not a plain tag of a commit: look at it by hand." % older)
    return problems


def publish(version, text, history, repo, sha, api, out):
    """Tag sha as v<version> and release it, or find that it is done. ReleaseError on every fault.

    history is main_history() of sha. Only versions up to this one are looked at. Nothing is
    written before every check has passed, and nothing is written for an older version. A tag
    is created and never moved, deleted or edited.
    """
    versions = changelog_versions(text)
    if version not in versions:
        raise ReleaseError("CHANGELOG.md has no entry for %s, the version in ratchet.json" % version)
    newest = max(versions, key=version_key)
    if newest != version:
        raise ReleaseError("the newest entry in CHANGELOG.md is %s, and ratchet.json says %s" % (newest, version))
    first = first_commits(history, version, sha)
    body = release_text(version, repo)
    tag = "v%s" % version

    tags = dict((v, target) for v, target in list_tags(api, repo).items() if version_key(v) <= version_key(version))
    releases = {}
    for name, draft in list_releases(api, repo):
        releases.setdefault(name, []).append(draft)

    for name in sorted(tags, key=version_key):
        if name not in versions:
            raise ReleaseError("the tag v%s has no entry in CHANGELOG.md. Nothing was written." % name)
    problems = unfinished(first, version, tags, releases)
    if problems:
        raise ReleaseError("an older version is not finished. %s Then rerun this run. Nothing was written." % " ".join(problems))
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
        # the fixed line for this version. Only the release is created.
        create_release(api, repo, tag, version, body, sha)
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
            if version not in changelog_versions(read_text(path)):
                raise ReleaseError("CHANGELOG.md has no entry for %s, the version in ratchet.json" % version)
            out.write(release_text(version, args.repo) + "\n")
            return 0
        if not environ.get("GITHUB_TOKEN"):
            raise ReleaseError("GITHUB_TOKEN is not set")
        repo = environment(environ, "GITHUB_REPOSITORY", REPOSITORY)
        sha = environment(environ, "GITHUB_SHA", SHA)
        if environ.get("GITHUB_REF") != MAIN:
            raise ReleaseError("GITHUB_REF is not %s: a release is made only from main" % MAIN)
        text = read_text(path)
        publish(version, text, main_history(root, sha), repo, sha, github(environ["GITHUB_TOKEN"], opener), out)
        return 0
    except ReleaseError as error:
        err.write("release: %s\n" % error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
