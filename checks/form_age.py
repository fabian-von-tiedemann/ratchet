#!/usr/bin/env python3
"""Say whether the form has been unchanged for three tags and at least 30 days (issue #70).

    python3 checks/form_age.py [ROOT]

Criterion 1 of D-2026-11-19-one-point-oh. ROOT, by default the checkout this script
stands in, is the top of a git checkout that holds its tags. The script reads the last
three tags from v0.16 on, where D-2026-11-26-road-to-1-0 starts the count, and compares
the form at each with the form at the tag before it:

1. ratchet.json: the fields at the top and the fields that at least one rule holds,
   read with upgrade.load_older and compared with upgrade.form_changes.
2. register.json and templates/register.json: the field paths they use, at the top,
   in a row of "adopted", in its "translation" and in a row of "own", the union of the
   two files, each read strictly with registry.parse_json.
3. The changelog's own record: the entries of the two newer tags, as CHANGELOG.md at
   the newest tag holds them, have no line that is exactly "Changes of form:".

The date of a tag is the date in its heading in CHANGELOG.md at the newest tag. Every
release from v0.16 on that changelog dates must have its tag here, so that a tag not
fetched, or one git cannot read, never makes two other tags look like neighbours.

Exit 0: holds. The form is the same at all three tags, and the oldest is dated at
least 30 days before the newest.
Exit 1: does not hold, with each reason: a difference of form between two
neighbouring tags, an entry that lists a change of form, the days short, or fewer
than three tags from v0.16 on.
Exit 2: cannot tell. ROOT is not the top of a git checkout, it is a partial clone, git
warns while it lists the tags, there are no tags, a tag is not of the form
vMAJOR.MINOR, a release from v0.16 on that the changelog dates has no tag, or a file
at a counted tag is missing, not strict UTF-8, or does not read strictly, or a counted
tag has no dated heading.

It is a report for the maintainer's decision on 1.0, in no required job. It writes
nothing, reaches no network, and runs git only as rev-parse, config --get-regexp, tag --list
and show, with GIT_NO_LAZY_FETCH=1. A partial clone, which could fetch an object that
a read asks for, is refused before anything is read.

Standard library only. CI runs it on Python 3.9 and the newest Python 3.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True
# Its own directory on the path, named explicitly, so that python3 -I, which leaves the script's directory out of
# sys.path, still finds the modules beside it.
import os  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse  # noqa: E402
import datetime  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402

import registry  # noqa: E402
import released_text  # noqa: E402
import upgrade  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The count starts at this tag, by D-2026-11-26-road-to-1-0, which freezes the form from 0.16 on.
FIRST = (0, 16)
FIRST_TAG = "v0.16"
FIRST_WHY = "D-2026-11-26-road-to-1-0"
TAGS = 3
DAYS = 30
# A tag: "v", then a major and a minor version with no leading zero, as upgrade.RELEASE reads a release.
TAG = re.compile(r"\Av((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))\Z")
DATED = re.compile(r"\A## ([0-9]+\.[0-9]+) \(([0-9]{4}-[0-9]{2}-[0-9]{2})\)\Z")
MARKER = "Changes of form:"
REGISTERS = ("register.json", "templates/register.json")
NOTES = (
    "The count starts at %s, by %s: tags before it are not counted." % (FIRST_TAG, FIRST_WHY),
    "Parts 1 and 2 compare the fields the files use, not every field a reader at a tag allowed. A field allowed and "
    "unused, and a change in what a field means, are seen only through a line \"%s\" in the changelog, which shows a "
    "change that was recorded, not whether the record is complete." % MARKER,
)


class CannotTell(Exception):
    """The run cannot read what it needs."""


def run_git(root, *args):
    """(exit code, stdout bytes, stderr bytes) of a read-only git command. GIT_NO_LAZY_FETCH=1 keeps git from fetching
    an object it lacks, where the git in use honours it. Raises CannotTell when git cannot run."""
    try:
        result = subprocess.run(["git", "-C", root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))
    except OSError as error:
        raise CannotTell("cannot run git: %s" % error)
    return result.returncode, result.stdout, result.stderr


def git(root, *args):
    """The bytes git prints, or None when it fails."""
    code, out, _ = run_git(root, *args)
    return out if code == 0 else None


def counted_tags(root):
    """The tags from FIRST on, highest version first, as [(version, tag)]. Raises CannotTell."""
    toplevel = git(root, "rev-parse", "--show-toplevel")
    if toplevel is None or os.path.realpath(toplevel.decode("utf-8", "replace").strip()) != os.path.realpath(root):
        raise CannotTell("%s is not the top of a git checkout" % root)
    # A partial clone fetches an object it lacks when a read asks for it, on a git that does not honour
    # GIT_NO_LAZY_FETCH. The report reaches no network, so it reads none.
    # git marks one with extensions.partialClone, or, as newer versions write it, with remote.<name>.promisor.
    code, promisor, _ = run_git(root, "config", "--get-regexp", r"^(extensions\.partialclone|remote\..*\.promisor)$")
    if code == 0 and any(line.split(None, 1)[1:] != [b"false"] for line in promisor.splitlines() if line.strip()):
        raise CannotTell("%s is a partial clone, which may fetch the files a tag holds as they are read. Run the report on "
                         "a full clone with its tags" % root)
    code, listed, warned = run_git(root, "tag", "--list")
    if code != 0:
        raise CannotTell("cannot list the tags of %s" % root)
    if warned.strip():
        # git leaves out a tag it cannot read, and says so only here.
        raise CannotTell("git warned while it listed the tags of %s: %s" % (
            root, warned.decode("utf-8", "replace").strip().replace("\n", "; ")))
    found, wrong = [], []
    for tag in listed.decode("utf-8", "replace").split():
        match = TAG.match(tag)
        if match:
            found.append((upgrade.version_key(match.group(1)), match.group(1), tag))
        else:
            wrong.append(tag)
    if wrong:
        raise CannotTell("; ".join("the tag %r is not of the form vMAJOR.MINOR" % tag for tag in sorted(wrong)))
    if not found:
        raise CannotTell("there are no tags. Fetch them: git fetch --tags")
    return [(version, tag) for key, version, tag in sorted(found, reverse=True) if key >= FIRST]


def show(root, tag, path):
    data = git(root, "show", "%s:%s" % (tag, path))
    if data is None:
        raise CannotTell("%s at %s: the file is missing" % (path, tag))
    return data


def ratchet_at(root, tag):
    """ratchet.json at a tag, read with upgrade.load_older. Raises CannotTell."""
    name = "ratchet.json at %s" % tag
    try:
        return upgrade.load_older(name, show(root, tag, "ratchet.json"))
    except upgrade.UpgradeError as error:
        raise CannotTell(str(error))


def objects(value, name, where):
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise CannotTell("%s: %s must be a list of objects" % (name, where))
    return value


def register_paths(data, name):
    """The field paths that a register uses: the top fields, and the fields of a row of adopted, of its translation and
    of a row of own. Raises CannotTell when the parts it reads are not of their kind."""
    if not isinstance(data, dict):
        raise CannotTell("%s: the top level must be an object" % name)
    paths = set(data)
    for row in objects(data.get("adopted", []), name, "adopted"):
        paths |= set("adopted[]." + field for field in row)
        if "translation" in row:
            if not isinstance(row["translation"], dict):
                raise CannotTell("%s: a translation must be an object" % name)
            paths |= set("adopted[].translation." + field for field in row["translation"])
    for row in objects(data.get("own", []), name, "own"):
        paths |= set("own[]." + field for field in row)
    return paths


def register_at(root, tag):
    """The union of the field paths of register.json and templates/register.json at a tag. Raises CannotTell."""
    paths = set()
    for path in REGISTERS:
        name = "%s at %s" % (path, tag)
        try:
            data = registry.parse_json(show(root, tag, path))
        except registry.RegistryError as error:
            raise CannotTell("%s: %s" % (name, error))
        paths |= register_paths(data, name)
    return paths


def changelog_text(root, tag):
    """(name, text) of CHANGELOG.md at a tag. Raises CannotTell."""
    name = "CHANGELOG.md at %s" % tag
    try:
        return name, released_text.text(show(root, tag, "CHANGELOG.md"), name)
    except ValueError as error:
        raise CannotTell(str(error))


def untagged(root, tag, tagged):
    """Each release from FIRST on, up to the version of tag, that CHANGELOG.md at tag dates and that has no tag here, as
    a problem. It runs before any verdict, so that a tag not fetched never shortens the count nor makes two tags look
    like neighbours. Raises CannotTell."""
    name, text = changelog_text(root, tag)
    newest = upgrade.version_key(tag[1:])
    missing = []
    for heading, _ in released_text.entries(text):
        match = DATED.match(heading)
        if match and FIRST <= upgrade.version_key(match.group(1)) <= newest and match.group(1) not in tagged:
            missing.append(match.group(1))
    return ["%s: the release %s is dated there and has no tag v%s here, so the tags counted may not be all of them. "
            "Fetch the tags: git fetch --tags" % (name, version, version) for version in missing]


def changelog_at(root, tag, versions):
    """{version: (date, entry)} for each version, from CHANGELOG.md at a tag. Raises CannotTell."""
    name, text = changelog_text(root, tag)
    found = {}
    for heading, entry in released_text.entries(text):
        version = released_text.version_of(heading)
        if version in versions:
            found.setdefault(version, []).append((heading, entry))
    result, problems = {}, []
    for version in versions:
        held = found.get(version, [])
        if len(held) != 1:
            problems.append("%s: the entry of %s stands %d times, and one dated heading is needed" % (name, version, len(held))
                            if held else "%s: no entry of %s, so its date is not known" % (name, version))
            continue
        heading, entry = held[0]
        match = DATED.match(heading)
        if not match:
            problems.append("%s: %r has no date, so the date of %s is not known" % (name, heading, version))
            continue
        try:
            date = datetime.date(*(int(part) for part in match.group(2).split("-")))
        except ValueError:
            problems.append("%s: %r has a date that does not exist" % (name, heading))
            continue
        result[version] = (date, entry)
    if problems:
        raise CannotTell("; ".join(problems))
    return result


def judge(root):
    """(exit code, verdict, reasons)."""
    try:
        counted = counted_tags(root)
    except CannotTell as error:
        return 2, "cannot tell", [str(error)]
    tagged = set(version for version, _ in counted)
    if counted:
        try:
            missing = untagged(root, counted[0][1], tagged)
        except CannotTell as error:
            missing = str(error).split("\n")
        if missing:
            return 2, "cannot tell", missing
    if len(counted) < TAGS:
        return 1, "does not hold", ["%d tag(s) from %s on (%s), and %d are needed" % (
            len(counted), FIRST_TAG, ", ".join(tag for _, tag in reversed(counted)) or "none", TAGS)]
    counted = list(reversed(counted[:TAGS]))
    versions = [version for version, _ in counted]
    tags = [tag for _, tag in counted]
    problems, forms = [], {}
    for tag in tags:
        for part, read in (("ratchet", ratchet_at), ("register", register_at)):
            try:
                forms[(tag, part)] = read(root, tag)
            except CannotTell as error:
                problems += str(error).split("\n")
    try:
        dated = changelog_at(root, tags[-1], versions)
    except CannotTell as error:
        problems += str(error).split("\n")
    if problems:
        return 2, "cannot tell", problems

    reasons = []
    for older, newer in zip(tags, tags[1:]):
        changes = upgrade.form_changes(forms[(older, "ratchet")], forms[(newer, "ratchet")])
        reasons += ["ratchet.json from %s to %s: %s" % (older, newer, change) for change in changes]
        old, new = forms[(older, "register")], forms[(newer, "register")]
        reasons += ['register.json and templates/register.json from %s to %s: "%s" is new' % (older, newer, path)
                    for path in sorted(new - old)]
        reasons += ['register.json and templates/register.json from %s to %s: "%s" is gone' % (older, newer, path)
                    for path in sorted(old - new)]
    for version in versions[1:]:
        if MARKER in dated[version][1].split("\n"):
            reasons.append('CHANGELOG.md at %s: the entry of %s lists a change of form, under a line "%s"'
                           % (tags[-1], version, MARKER))
    days = (dated[versions[-1]][0] - dated[versions[0]][0]).days
    span = "%s (%s) to %s (%s): %d days" % (tags[0], dated[versions[0]][0], tags[-1], dated[versions[-1]][0], days)
    if days < DAYS:
        reasons.append("%s, %d short of %d" % (span, DAYS - days, DAYS))
    if reasons:
        return 1, "does not hold", reasons
    return 0, "holds", ["the form is the same at %s, and %s" % (", ".join(tags), span)]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Say whether the form has been unchanged for three tags and 30 days.")
    parser.add_argument("root", nargs="?", default=ROOT, help="the top of a git checkout that holds its tags")
    args = parser.parse_args(argv)
    code, verdict, reasons = judge(os.path.abspath(args.root))
    print("form_age: %s. Criterion 1 of D-2026-11-19-one-point-oh, the form unchanged for %d tags and at least %d days:"
          % (verdict, TAGS, DAYS))
    for reason in reasons:
        print("- " + reason)
    for note in NOTES:
        print(note)
    return code


if __name__ == "__main__":
    sys.exit(main())
