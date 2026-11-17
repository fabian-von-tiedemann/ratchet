#!/usr/bin/env python3
"""Tag and release the version in ratchet.json, from the release workflow.

    python3 checks/release.py notes --repo OWNER/NAME   print the release text, with no token and no network
    python3 checks/release.py publish                   tag and release, in the release workflow

D-2026-11-17-release-on-merge, D-2026-11-17-release-verbatim and D-2026-11-17-release-links.
The release text is one fixed line written here, with the version and links to CHANGELOG.md
and to the files at the tag. Nothing from the changelog is copied. From CHANGELOG.md the script
reads only which versions have an entry. An older version that is not finished fails the run,
and the run writes nothing: the maintainer reruns the run of that version.

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


def unfinished(versions, version, tags, releases):
    """Every older version in the changelog that is not finished, with what it lacks."""
    problems = []
    for older in sorted(set(versions), key=version_key):
        if version_key(older) >= version_key(version):
            continue
        if older not in tags:
            problems.append("%s: no tag" % older)
        elif older not in BEFORE_RELEASES and False not in releases.get("v" + older, []):
            problems.append("%s: a tag and no published release" % older)
    return problems


def publish(version, text, repo, sha, api, out):
    """Tag sha as v<version> and release it, or find that it is done. ReleaseError on every fault.

    Only versions up to this one are looked at. Nothing is written before every check has
    passed, and nothing is written for an older version. A tag is created and never moved,
    deleted or edited.
    """
    versions = changelog_versions(text)
    if version not in versions:
        raise ReleaseError("CHANGELOG.md has no entry for %s, the version in ratchet.json" % version)
    newest = max(versions, key=version_key)
    if newest != version:
        raise ReleaseError("the newest entry in CHANGELOG.md is %s, and ratchet.json says %s" % (newest, version))
    body = release_text(version, repo)
    tag = "v%s" % version

    tags = dict((v, target) for v, target in list_tags(api, repo).items() if version_key(v) <= version_key(version))
    releases = {}
    for name, draft in list_releases(api, repo):
        releases.setdefault(name, []).append(draft)

    for name in sorted(tags, key=version_key):
        if name not in versions:
            raise ReleaseError("the tag v%s has no entry in CHANGELOG.md. Nothing was written." % name)
    problems = unfinished(versions, version, tags, releases)
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
        # the fixed line for this version. Only the release is created.
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
        publish(version, read_text(path), repo, sha, github(environ["GITHUB_TOKEN"], opener), out)
        return 0
    except ReleaseError as error:
        err.write("release: %s\n" % error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
