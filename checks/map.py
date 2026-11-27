#!/usr/bin/env python3
"""The map: check a repo's own map of Ratchet's rules, read only.

    python3 .ratchet/checks/map.py [ROOT] [--json] [--partial]

A repo with rules and checks of its own does not adopt Ratchet first. Its agent writes ratchet-map.json at the root of
ROOT (by default the folder it runs in), with every rule of the ratchet.json beside this script, each marked "covered"
or "gap", the paths in the repo that cover it, and a note. This check reads that file strictly and prints every
assessment, the gaps first, for the owner to review, each with the source its rule names in ratchet.json, if any.
Ratchet never writes the file.

It checks the form of the map and that every path it cites is a plain file under ROOT, reached through no link. It
does not check whether a path covers a rule: every row is the agent's proposal, and the owner judges it.

It writes nothing, reaches no network and runs no program. It reads the map through the guarded reader of
inventory.py, and looks at the kind of each path it cites, never at its content. ROOT itself may be reached through a
link, as inventory.py's root may; nothing below it is.

With --partial, a rule that has no entry in the map is not a problem: it is listed, by key, as not yet mapped, and
everything else is checked as without it. The first line says that the map is partial and not yet a map of the whole
Ratchet, and a partial run never prints the line of a full pass. It is for the map while it is written.

Exit code 0 when the map is of its form and every path exists as stated, 1 when not, with each problem named, and 2
when it could not run: no valid ratchet.json beside it, or a ROOT that is not a folder. Standard library only.
CI runs it on Python 3.9 and the newest Python 3.
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
import re

import inventory
import registry

# The map's name, at the root of the repo and only there. It ends in .json, so it can never be a register's
# instruction or reference file, which end in .md.
MAP_NAME = "ratchet-map.json"
# ratchet.json of the checkout this script runs from: the folder above checks/.
SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ratchet.json")

TOP_FIELDS = ("ratchet", "rules")
RULE_FIELDS = ("status", "by", "note")
STATUSES = ("covered", "gap")
NOTE_LENGTH = 300
PATH_LENGTH = 200
# The characters a path in "by" may hold: ASCII letters and digits, ".", "_", "-", "+", and "/" between the parts.
PATH_CHARACTERS = re.compile(r"^[A-Za-z0-9._+/-]+\Z")
REFUSED_IN_PATH = ("\\", ":", "#", "?")

PROPOSAL = ("This map is the agent's proposal, for the owner to review. map.py checks its form and that each path it "
            "cites is a plain file under the root, not whether a path covers a rule.")

# The line a partial run prints second, and gives as the field "partial" in --json, whether the map passes or not.
PARTIAL = ("This run is partial: a rule missing from the map is listed as not yet mapped, not named as a problem. Run "
           "map.py without --partial once every rule is mapped.")
# What the first line of a partial run says after the version, where a full run gives its counts or its problems.
PARTIAL_HEAD = "partial, not yet a map of the whole Ratchet"

KIND_NAMES = {type(None): "null", bool: "true or false", int: "a number", float: "a number", str: "text",
              list: "an array", dict: "an object"}


class CannotRun(Exception):
    """The check cannot start: no valid ratchet.json beside it, or a root that is not a folder."""


def kind_of(value):
    return KIND_NAMES.get(type(value), type(value).__name__)


def checkout():
    """The version and the rules, in order, of the ratchet.json beside this script: (version, [(key, status, source)]).
    A rule's source is the text it draws on, printed as it stands, or "" when it names none."""
    if not os.path.isfile(SOURCE):
        raise CannotRun("there is no ratchet.json beside map.py, at %s: run map.py from a checkout of Ratchet" % SOURCE)
    try:
        data = registry.load_json(SOURCE)
    except registry.RegistryError as error:
        raise CannotRun("%s: %s" % (SOURCE, error))
    version = data.get("version") if isinstance(data, dict) else None
    rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(version, str) or not registry.VERSION.match(version) or not isinstance(rules, list):
        raise CannotRun("%s has no version of the form MAJOR.MINOR and list of rules" % SOURCE)
    keys = []
    for rule in rules:
        key = rule.get("key") if isinstance(rule, dict) else None
        if not isinstance(key, str) or not registry.KEY.match(key) or key in [k for k, _, _ in keys]:
            raise CannotRun("%s has a rule without a key of its own" % SOURCE)
        keys.append((key, rule.get("status") if isinstance(rule.get("status"), str) else "?", rule.get("source", "")))
    return version, keys


def path_problem(value):
    """Why a path in "by" is not of its form, or None. The form is checked before anything is looked at."""
    if not isinstance(value, str):
        return "must be text, found %s" % kind_of(value)
    if value == "":
        return "is empty"
    if len(value) > PATH_LENGTH:
        return "is longer than %d characters" % PATH_LENGTH
    for character in REFUSED_IN_PATH:
        if character in value:
            return "holds %r, which a path here may not hold" % character
    if value.startswith("/"):
        return "starts with /: give the path from the root of the repo"
    if value.endswith("/"):
        return "ends with /: give a file, not a folder"
    if not PATH_CHARACTERS.match(value):
        return ("holds a character outside the list: ASCII letters and digits, '.', '_', '-', '+', "
                "and '/' between the parts")
    if any(part in ("", ".", "..") for part in value.split("/")):
        return "has an empty part, '.' or '..': give a plain path from the root"
    return None


def target_problem(root, value):
    """Why the path does not name a plain file under root, reached through no link, or None. Nothing is read."""
    kind, linked = inventory.guarded_look(root, value.split("/"))
    if kind == "file":
        return None
    if kind == "link":
        if linked == value:
            return "is a link, not followed: cite the file it points to"
        return "is under %s, which is a link, not followed: cite the file without the link" % linked
    if kind == "dir":
        return "is a folder, not a file"
    if kind == "missing":
        return "does not exist"
    return "is not a plain file: a FIFO, a socket or a device"


def read_map(root):
    """The parsed map at root, or (None, why it was not read)."""
    kind, linked = inventory.guarded_look(root, [MAP_NAME])
    if kind == "missing":
        return None, "there is no %s at the root: the agent writes it, with a status for every rule" % MAP_NAME
    if kind == "link":
        return None, "%s is a link, not followed: put the map itself at the root" % MAP_NAME
    if kind == "dir":
        return None, "%s is a folder, not a file" % MAP_NAME
    if kind == "other":
        return None, "%s is not a plain file: a FIFO, a socket or a device, not read" % MAP_NAME
    data, why = inventory.guarded_read(root, [MAP_NAME])
    if data is None:
        return None, "%s: %s" % (MAP_NAME, why)
    if data.startswith(b"\xef\xbb\xbf"):
        return None, "%s starts with a byte order mark: write it as UTF-8 without one" % MAP_NAME
    try:
        return registry.parse_json(data), None
    except registry.RegistryError as error:
        return None, "%s is %s" % (MAP_NAME, str(error))


def rule_problems(root, key, entry, problems):
    """Add each problem with one rule's entry; return the entry as facts, or None when it is not of its form."""
    where = "rules.%s" % key
    if not isinstance(entry, dict):
        problems.append("%s must be an object with status, by and note, found %s" % (where, kind_of(entry)))
        return None
    ok = True
    for field in RULE_FIELDS:
        if field not in entry:
            problems.append("%s has no field %r" % (where, field))
            ok = False
    for field in entry:
        if field not in RULE_FIELDS:
            problems.append("%s has the field %s, which a rule's entry does not have" % (where, json.dumps(field)))
            ok = False
    status, by, note = entry.get("status"), entry.get("by"), entry.get("note")
    if "status" in entry:
        if not isinstance(status, str):
            problems.append("%s.status must be text, found %s" % (where, kind_of(status)))
            ok = False
        elif status not in STATUSES:
            problems.append("%s.status is %s: it is \"covered\" or \"gap\"; whether a rule is wanted is the owner's "
                            "decision, not the map's" % (where, json.dumps(status)))
            ok = False
    if "note" in entry:
        if not isinstance(note, str):
            problems.append("%s.note must be text, found %s" % (where, kind_of(note)))
            ok = False
        elif not note:
            problems.append("%s.note is empty" % where)
            ok = False
        elif len(note) > NOTE_LENGTH:
            problems.append("%s.note is longer than %d characters" % (where, NOTE_LENGTH))
            ok = False
        else:
            why = registry.text_problem(note)
            if why:
                problems.append("%s.note %s" % (where, why))
                ok = False
    paths = []
    if "by" in entry:
        if not isinstance(by, list):
            problems.append("%s.by must be an array of paths, found %s" % (where, kind_of(by)))
            ok = False
        else:
            if status == "covered" and not by:
                problems.append("%s is covered and cites no path: give the file that covers it, or mark it a gap" % where)
                ok = False
            for value in by:
                why = path_problem(value)
                if why is None and value in paths:
                    why = "stands twice"
                if why is None:
                    why = target_problem(root, value)
                if why:
                    problems.append("%s.by: %s %s" % (where, json.dumps(value), why))
                    ok = False
                if isinstance(value, str):
                    paths.append(value)
    if not ok:
        return None
    return {"key": key, "status": status, "by": list(by), "note": note}


def check(root, partial=False):
    """The facts of the map at root: a dict with "ok", and the assessments or the problems. With partial, a rule with no
    entry is not a problem, the facts hold the field "partial", and on a pass the keys of those rules as "unmapped"."""
    version, rules = checkout()
    if inventory.guarded_look(root, [])[0] != "dir":
        raise CannotRun("%s is not a folder" % inventory.shown(root))
    facts = {"map": MAP_NAME, "ratchet": version, "proposal": PROPOSAL}
    if partial:
        facts["partial"] = PARTIAL
    data, why = read_map(root)
    if why:
        facts.update(ok=False, problems=[why])
        return facts
    problems = []
    if not isinstance(data, dict):
        facts.update(ok=False, problems=["the map must be an object with ratchet and rules, found %s" % kind_of(data)])
        return facts
    for field in TOP_FIELDS:
        if field not in data:
            problems.append("the map has no field %r" % field)
    for field in data:
        if field not in TOP_FIELDS:
            problems.append("the map has the field %s, which it does not have" % json.dumps(field))
    if "ratchet" in data:
        stated = data["ratchet"]
        if not isinstance(stated, str):
            problems.append("ratchet must be text of the form MAJOR.MINOR, found %s" % kind_of(stated))
        elif not registry.VERSION.match(stated):
            problems.append("ratchet is %s, not of the form MAJOR.MINOR" % json.dumps(stated))
        elif stated != version:
            problems.append("ratchet is %s, and the checkout map.py runs from is Ratchet %s: map the rules of the "
                            "version you run" % (json.dumps(stated), version))
    entries, unmapped = [], []
    if "rules" in data:
        given = data["rules"]
        if not isinstance(given, dict):
            problems.append("rules must be an object with one entry for each rule, found %s" % kind_of(given))
        else:
            known = [key for key, _, _ in rules]
            for key, part, source in rules:
                if key not in given:
                    if partial:
                        unmapped.append(key)
                    else:
                        problems.append("rules has no entry for %s, a rule of Ratchet %s" % (key, version))
                    continue
                entry = rule_problems(root, key, given[key], problems)
                if entry is not None:
                    entry["part"] = part
                    if source:
                        entry["source"] = source
                    entries.append(entry)
            for key in given:
                if key not in known:
                    problems.append("rules has an entry for %s, which is not a rule of Ratchet %s"
                                    % (json.dumps(key), version))
    if problems:
        facts.update(ok=False, problems=problems)
        return facts
    counts = dict((status, sum(1 for entry in entries if entry["status"] == status)) for status in STATUSES)
    facts.update(ok=True, counts=counts, rules=entries)
    if partial:
        facts["unmapped"] = unmapped
    return facts


def entry_lines(entry):
    lines = ["  %s (%s): %s%s" % (entry["key"], entry["part"], entry["status"], "  <-- GAP" if entry["status"] == "gap" else "")]
    lines.append("    by: %s" % (", ".join(entry["by"]) if entry["by"] else "(no path)"))
    lines.append("    note: %s" % entry["note"])
    if "source" in entry:
        lines.append("    source: %s" % entry["source"])
    return lines


def text_report(facts):
    """The facts as text. It is made from the same facts as --json, and from nothing else. The line that the map is
    the agent's proposal stands in both, whether the map passes or not."""
    out = []
    partial = "partial" in facts
    head = "%s, for Ratchet %s: " % (facts["map"], facts["ratchet"]) + (PARTIAL_HEAD + ": " if partial else "")
    if not facts["ok"]:
        out.append("%s%d problem%s" % (head, len(facts["problems"]), "" if len(facts["problems"]) == 1 else "s"))
        if partial:
            out.append(facts["partial"])
        out.append(facts["proposal"])
        for problem in facts["problems"]:
            out.append("  %s" % problem)
        return "\n".join(out) + "\n"
    counts, rules = facts["counts"], facts["rules"]
    if partial:
        unmapped = facts["unmapped"]
        out.append("%s%d rule%s given, %d covered, %d gap%s; %d rule%s not yet mapped%s" % (
            head, len(rules), "" if len(rules) == 1 else "s", counts["covered"], counts["gap"],
            "" if counts["gap"] == 1 else "s", len(unmapped), "" if len(unmapped) == 1 else "s",
            ": " + ", ".join(unmapped) if unmapped else ""))
        out.append(facts["partial"])
    else:
        out.append("%s%d rules, %d covered, %d gap%s" % (
            head, len(rules), counts["covered"], counts["gap"], "" if counts["gap"] == 1 else "s"))
    out.append(facts["proposal"])
    for status, title in (("gap", "Gaps"), ("covered", "Covered")):
        out.append("")
        out.append("%s (%d):" % (title, counts[status]))
        for entry in rules:
            if entry["status"] == status:
                out += entry_lines(entry)
        if not counts[status]:
            out.append("  none")
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a repo's ratchet-map.json against the rules of this Ratchet. "
                                                 "Reads only; writes nothing.")
    parser.add_argument("root", nargs="?", default=".", help="the root of the repo, by default the folder it runs in")
    parser.add_argument("--json", action="store_true", help="print JSON in place of text")
    parser.add_argument("--partial", action="store_true",
                        help="list a rule with no entry as not yet mapped, not as a problem, while the map is written")
    args = parser.parse_args(argv)
    try:
        facts = check(args.root, partial=args.partial)
    except CannotRun as error:
        print("map: cannot run: %s" % inventory.shown(str(error)), file=sys.stderr)
        if args.partial:
            print(PARTIAL, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(facts, indent=2, sort_keys=True))
    else:
        sys.stdout.write(text_report(facts))
    return 0 if facts["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
