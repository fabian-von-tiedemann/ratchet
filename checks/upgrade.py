#!/usr/bin/env python3
"""Print what a project's register must do to move to this version of Ratchet.

    python3 .ratchet/checks/upgrade.py register.json --from OLD/ratchet.json

The register is the project's register.json. --from is ratchet.json of the version
the register states, and --source, by default the ratchet.json next to this script,
is the newer Ratchet. The script compares the two, rule by rule, and prints:

- a step for each adopted rule that changed or was removed, with the entry to
  paste in place of the old one, or the reason to remove it
- the new rules, each with the entry to paste if the project adopts it
- the changed and removed rules that the register does not adopt, by key.

It writes nothing. It runs offline, on the files it is given. Before it prints a
step, it checks that the register passes check_register.py against the older
Ratchet, and that the register with every step done passes it against the newer
one. The data files are read strictly, as every check here reads them, and no rule
is read from Markdown. Where a version changed a rule, and why, is in the changelog
of the newer Ratchet.

Exit code 0: the steps are printed, or there is nothing to change. 1: the register
does not pass against the version it states, or the newer Ratchet is older. 2: the
script could not run: a file is missing or is not a valid data file.
Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import copy
import json
import os
import sys

import check_register
import registry

# The fields of a rule that the comparison reads, in the order a change names them.
COMPARED = (("status", "the status"), ("enforcement", "the enforcement"), ("rule", "the rule"),
            ("ratchet", "the ratchet"), ("source", "the source"))


class UpgradeError(Exception):
    """The upgrade cannot run."""


def version_key(version):
    major, minor = version.split(".")
    return int(major), int(minor)


def load_older(path):
    """ratchet.json of an older version, read as strictly as this one's, but for the parts named in registry.validate."""
    try:
        data = registry.load_json(path)
    except registry.RegistryError as error:
        raise UpgradeError("%s: %s" % (path, error))
    problems = registry.validate(data, None, older=True)
    if problems:
        raise UpgradeError("\n".join("%s: %s" % (path, problem) for problem in problems))
    return data


def entry(rule, old_entry=None):
    """A rule as it stands in a register, keeping the status and the place of the check that still hold."""
    result = dict((field, rule[field]) for field in check_register.RULE_FIELDS)
    if rule["enforcement"] != "enforced":
        return result
    if old_entry is not None and "status" in old_entry:
        result["status"] = old_entry["status"]
        if "where" in old_entry:
            result["where"] = old_entry["where"]
    else:
        result["status"] = "text only for now"
    return result


def changed_fields(old, new):
    return [name for field, name in COMPARED if old[field] != new[field]]


def joined(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def plan(register, old, new):
    """Return (steps, the register with every step done) for a register that passes against old.

    A step is a dict: "key", "kind" (changed, removed or new), "adopted", "text", and "entry" when there is one to
    paste. The register given is not changed.
    """
    old_by, new_by = registry.rules_by_key(old), registry.rules_by_key(new)
    adopted = dict((item["key"], item) for item in register["adopted"])
    steps = []
    for rule in new["rules"]:
        key = rule["key"]
        if key not in old_by:
            steps.append({"key": key, "kind": "new", "adopted": False, "entry": entry(rule),
                          "text": '%s: new. The register may adopt it. To adopt it, add this entry to "adopted".' % key})
            continue
        fields = changed_fields(old_by[key], rule)
        if not fields:
            continue
        step = {"key": key, "kind": "changed", "adopted": key in adopted}
        if key in adopted:
            before = adopted[key]
            step["entry"] = entry(rule, before)
            text = ["%s: changed: %s. The register adopts it: replace its entry with this one." % (key, joined(fields))]
            if rule["enforcement"] == "enforced" and "status" not in before:
                text.append('Its ratchet now names a check, so the entry has a status: "text only for now" until the project has built the check.')
            elif rule["enforcement"] != "enforced" and "status" in before:
                text.append('It is text only now, so the entry has no status and no "where".')
            elif step["entry"].get("status") == "built" and old_by[key]["ratchet"] != rule["ratchet"]:
                text.append('It keeps the status "built". Its ratchet changed: check that the check in "where" still does what '
                            'the ratchet says, or set the status to "text only for now".')
            step["text"] = " ".join(text)
        steps.append(step)
    for rule in old["rules"]:
        key = rule["key"]
        if key not in new_by:
            steps.append({"key": key, "kind": "removed", "adopted": key in adopted,
                          "text": '%s: removed. Remove it from "adopted". To keep it, move it to "own" under the project\'s own prefix.' % key})

    after = copy.deepcopy(register)
    after["ratchet_version"] = new["version"]
    by_step = dict((step["key"], step) for step in steps if step["adopted"])
    after["adopted"] = [
        copy.deepcopy(by_step[item["key"]]["entry"]) if item["key"] in by_step else item
        for item in after["adopted"]
        if not (item["key"] in by_step and by_step[item["key"]]["kind"] == "removed")
    ]
    return steps, after


def paste(item):
    return json.dumps(item, indent=2, ensure_ascii=False)


def report(path, register, old, new, out, script):
    """Print the steps for one register. Returns the exit code."""
    name = os.path.basename(path)
    problems, _ = check_register.check(register, old)
    if problems:
        for problem in problems:
            print("%s: %s" % (name, problem), file=out)
        print("FAIL: %s does not pass check_register.py against Ratchet %s, the version it states. Fix it first: an upgrade "
              "starts from a register that matches its Ratchet." % (name, old["version"]), file=out)
        return 1
    if version_key(new["version"]) < version_key(old["version"]):
        print("FAIL: this Ratchet is %s, which is older than %s, the version the register is on. Run the upgrade from the "
              "newer Ratchet." % (new["version"], old["version"]), file=out)
        return 1
    if new["version"] == old["version"]:
        if old["rules"] != new["rules"]:
            raise UpgradeError("both files name Ratchet %s, and their rules differ. Give --from the ratchet.json of the version "
                               "the register states, as it stood at its tag" % new["version"])
        print("%s is on Ratchet %s, the version of this Ratchet. Nothing to change." % (name, new["version"]), file=out)
        return 0

    steps, after = plan(register, old, new)
    problems, _ = check_register.check(after, new)
    if problems:
        # The steps would not give a register that passes. That is a fault in this script, not in the register.
        for problem in problems:
            print("%s after the steps: %s" % (name, problem), file=out)
        print("FAIL: the steps would not give a register that passes against Ratchet %s. Upgrade by hand, and report this." % new["version"], file=out)
        return 1

    told = {0: "no rule is", 1: "1 rule is"}.get(len(steps), "%d rules are" % len(steps))
    print("%s is on Ratchet %s. In Ratchet %s, %s new, changed or removed." % (name, old["version"], new["version"], told), file=out)
    print("", file=out)
    print("Steps for %s:" % name, file=out)
    print("", file=out)
    print('1. Set "ratchet_version" to "%s".' % new["version"], file=out)
    number = 1
    for step in steps:
        if not step["adopted"]:
            continue
        number += 1
        print("%d. %s" % (number, step["text"]), file=out)
        if step.get("entry"):
            print("", file=out)
            print(paste(step["entry"]), file=out)
            print("", file=out)
    new_rules = [step for step in steps if step["kind"] == "new"]
    if new_rules:
        print("", file=out)
        print("New rules, which the register may adopt:", file=out)
        print("", file=out)
        for step in new_rules:
            print("- %s" % step["text"], file=out)
            print("", file=out)
            print(paste(step["entry"]), file=out)
            print("", file=out)
    others = sorted("%s (%s)" % (step["key"], step["kind"]) for step in steps if not step["adopted"] and step["kind"] != "new")
    if others:
        print("", file=out)
        print("Not adopted, so nothing to do: %s." % ", ".join(others), file=out)
    print("", file=out)
    print("Then write REGISTER.md again and check it:", file=out)
    print("", file=out)
    print("    python3 %s %s --write REGISTER.md" % (script, path), file=out)
    print("    python3 %s %s --markdown REGISTER.md" % (script, path), file=out)
    print("", file=out)
    print("Checked: with the steps above and no new rule adopted, %s passes check_register.py against Ratchet %s." % (name, new["version"]), file=out)
    print("The reasons for each change are in CHANGELOG.md of Ratchet %s, in the entries after %s." % (new["version"], old["version"]), file=out)
    return 0


def main(argv=None, out=None):
    out = out or sys.stdout
    parser = argparse.ArgumentParser(description="Print what a register must do to move to this version of Ratchet. Writes nothing.")
    parser.add_argument("register", help="path to the project's register.json")
    parser.add_argument("--from", dest="older", required=True, metavar="ratchet.json",
                        help="ratchet.json of the version the register states, as it stood at its tag")
    parser.add_argument("--source", default=registry.SOURCE, help="path to the newer ratchet.json (default: the one next to this script)")
    args = parser.parse_args(argv)
    script = os.path.join(os.path.dirname(sys.argv[0]), "check_register.py")
    try:
        new = registry.load(args.source)
        old = load_older(args.older)
        if not os.path.isfile(args.register):
            raise UpgradeError("no such file: %s" % args.register)
        try:
            register = registry.load_json(args.register)
        except registry.RegistryError as error:
            print("%s: %s" % (args.register, error), file=out)
            print("FAIL: the register cannot be read", file=out)
            return 1
        return report(args.register, register, old, new, out, script)
    except (registry.RegistryError, UpgradeError) as error:
        print("upgrade: cannot run: %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
