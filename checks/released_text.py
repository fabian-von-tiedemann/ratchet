#!/usr/bin/env python3
"""Fail when released text is not as it stood at its tag (repo.version, repo.tags-stay).

    python3 checks/released_text.py

Reads the tags of this checkout, so the checkout must hold them: in CI,
actions/checkout with fetch-depth: 0. Every tag is of the form vMAJOR.MINOR. Then it
fails, naming each problem, when:

- an entry of CHANGELOG.md that a tag holds is not, byte for byte, as it stood at
  that tag, or is gone. Every tag that holds a changelog is compared with every entry
  it holds.
- a tag has no entry in CHANGELOG.md, or an entry after the first has no tag. Only
  the first entry may be a version that is not yet released.
- ratchet.json names a version that has a tag, and is not as it stood at that tag.
  A change to the rules raises the version (D-2026-11-17-new-approaches).
- an entry is headed in any way but "## <version> (<date>)", or stands twice. The first
  entry may also be headed "## <version> (unreleased)", while its changes are being
  collected (D-2026-11-19-batched-releases); an entry after the first may not, and
  neither may a version that has a tag. An entry with a date is released by the next
  push to main, and from its tag on it is compared as every released entry is.
- there are no tags, or a tag of another form, or the tags cannot be listed.

- ratchet.json is not a valid data file, read as every check reads it: strict JSON,
  with no field twice, no NaN or Infinity, and no field it does not know
  (registry.strict_loads and registry.validate).

sources.json is not read: it is not part of what is released, so a pin that moves
needs no new version.

A file is read as strict UTF-8, and CRLF is read as LF, as every check here reads it.

Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import os
import re
import subprocess
import sys

import registry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = re.compile(r"^v([0-9]+\.[0-9]+)\Z")
HEADING = re.compile(r"^## ([0-9]+\.[0-9]+) \([0-9]{4}-[0-9]{2}-[0-9]{2}\)\Z")
UNRELEASED = re.compile(r"^## ([0-9]+\.[0-9]+) \(unreleased\)\Z")


class GitError(Exception):
    pass


def git(root, *args):
    """The bytes git prints, or None when it fails with "does not exist" or the like. Raises GitError when git cannot run."""
    try:
        result = subprocess.run(["git", "-C", root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as error:
        raise GitError(str(error))
    if result.returncode != 0:
        return None
    return result.stdout


def text(data, name):
    """The text of a file's bytes, as strict UTF-8 with CRLF read as LF."""
    try:
        return data.decode("utf-8", errors="strict").replace("\r\n", "\n")
    except UnicodeDecodeError as error:
        raise ValueError("%s: is not valid UTF-8, at byte %d" % (name, error.start))


def entries(changelog):
    """[(heading, text of the entry)], in order. An entry runs from a line that starts with "## " to the next one, or to the end."""
    starts = [match.start() for match in re.finditer(r"^## ", changelog, re.M)]
    return [(changelog[a:].split("\n", 1)[0], changelog[a:b]) for a, b in zip(starts, starts[1:] + [len(changelog)])]


def version_of(heading):
    match = HEADING.match(heading) or UNRELEASED.match(heading)
    return match.group(1) if match else None


def tags(root):
    """Return ({version: tag}, problems)."""
    toplevel = git(root, "rev-parse", "--show-toplevel")
    if toplevel is None or os.path.realpath(toplevel.decode("utf-8", "replace").strip()) != os.path.realpath(root):
        return {}, ["cannot list the tags: %s is not the top of a git checkout" % root]
    listed = git(root, "tag", "--list")
    if listed is None:
        return {}, ["cannot list the tags of %s" % root]
    found, problems = {}, []
    for tag in listed.decode("utf-8", "replace").split():
        match = TAG.match(tag)
        if match:
            found[match.group(1)] = tag
        else:
            problems.append("the tag %r is not of the form vMAJOR.MINOR, so the check does not know what it releases" % tag)
    if not found and not problems:
        problems.append("there are no tags, so nothing released can be compared. Fetch them: in CI the checkout needs fetch-depth: 0")
    return found, problems


def check(root):
    """Return (problems, summary)."""
    released, problems = tags(root)
    path = os.path.join(root, "CHANGELOG.md")
    if not os.path.isfile(path):
        return problems + ["CHANGELOG.md: the file is missing"], None
    with open(path, "rb") as handle:
        try:
            current = entries(text(handle.read(), "CHANGELOG.md"))
        except ValueError as error:
            return problems + [str(error)], None
    by_version, counted = {}, {}
    for heading, entry in current:
        version = version_of(heading)
        if version is None:
            problems.append('CHANGELOG.md: %r is not the heading of an entry. An entry is headed "## <version> (<date>)", and the '
                            'first may be headed "## <version> (unreleased)"' % heading)
            continue
        counted[version] = counted.get(version, 0) + 1
        by_version.setdefault(version, (heading, entry))
    problems += ["CHANGELOG.md: the entry of %s stands %d times" % (v, n) for v, n in sorted(counted.items()) if n > 1]

    compared = 0
    for version, tag in sorted(released.items(), key=lambda item: tuple(int(p) for p in item[0].split("."))):
        if version not in by_version:
            problems.append("the tag %s has no entry in CHANGELOG.md" % tag)
        data = git(root, "show", "%s:CHANGELOG.md" % tag)
        if data is None:
            continue
        try:
            then = entries(text(data, "CHANGELOG.md at %s" % tag))
        except ValueError as error:
            problems.append(str(error))
            continue
        for heading, entry in then:
            compared += 1
            now = by_version.get(version_of(heading))
            if now is None:
                problems.append("CHANGELOG.md has no entry %s, which the tag %s holds" % (heading, tag))
            elif now != (heading, entry):
                problems.append("CHANGELOG.md: the entry %s is not as it stood at the tag %s" % (now[0], tag))
    pending = None
    for number, (heading, _) in enumerate(current):
        version = version_of(heading)
        if UNRELEASED.match(heading):
            if number > 0:
                problems.append('CHANGELOG.md: the entry %s is headed "(unreleased)", and only the first entry may be. '
                                "An entry is released from the moment it has a date" % heading)
            elif version in released:
                problems.append('CHANGELOG.md: the entry %s is headed "(unreleased)", and the tag %s exists. '
                                "A released version stays released" % (heading, released[version]))
            else:
                pending = version
        elif number > 0 and version is not None and version not in released:
            problems.append("CHANGELOG.md: the entry %s has no tag v%s. Only the first entry may be a version that is not yet released" % (heading, version))

    path = os.path.join(root, "ratchet.json")
    state = None
    if not os.path.isfile(path):
        problems.append("ratchet.json: the file is missing")
    else:
        with open(path, "rb") as handle:
            data = handle.read()
        source, version = None, None
        try:
            source = text(data, "ratchet.json")
            parsed = registry.strict_loads(source)
        except RecursionError:
            problems.append("ratchet.json: not a valid data file: it is nested too deeply")
        except ValueError as error:
            problems.append(str(error) if source is None else "ratchet.json: not a valid data file: %s" % error)
        else:
            invalid = registry.validate(parsed, root)
            problems += ["ratchet.json: %s" % problem for problem in invalid]
            if not invalid:
                version = parsed["version"]
        if version is not None:
            if version in released:
                then = git(root, "show", "%s:ratchet.json" % released[version])
                if then is None:
                    problems.append("ratchet.json: names %s, which is released, and the tag %s holds no ratchet.json" % (version, released[version]))
                else:
                    try:
                        same = text(then, "ratchet.json at %s" % released[version]) == source
                    except ValueError as error:
                        problems.append(str(error))
                        same = True
                    if not same:
                        problems.append("ratchet.json: names %s, which is released, and is not as it stood at the tag %s. "
                                        "A change to the rules raises the version" % (version, released[version]))
                    state = "ratchet.json is as it stood at the tag %s." % released[version]
            else:
                state = "ratchet.json names %s, which has no tag yet." % version
    if pending is not None:
        state = ((state or "") + " The first entry, %s, is unreleased." % pending).strip()
    summary = "%d entries in %d tags, each as it stood there. Every tag has an entry. %s" % (compared, len(released), state or "")
    return problems, summary.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fail when released text is not as it stood at its tag.")
    parser.add_argument("--root", default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        problems, summary = check(os.path.abspath(args.root))
    except GitError as error:
        problems, summary = ["cannot run git: %s" % error], None
    if problems:
        print("released_text: FAIL: %d problem(s). Released text must stay as it stood at its tag (repo.tags-stay):" % len(problems))
        for problem in problems:
            print("- " + problem)
        return 1
    print("released_text: released text matches its tags: " + summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
