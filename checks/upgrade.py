#!/usr/bin/env python3
"""Print what a project's register must do to move to this version of Ratchet.

    python3 .ratchet/checks/upgrade.py register.json --from OLD/ratchet.json

The register is the project's register.json. --from is ratchet.json of the version
the register states, and --source, by default the ratchet.json next to this script,
is the newer Ratchet. The script compares the two, rule by rule, and prints:

- a step for each adopted rule that changed, with the entry to paste in place of
  the old one
- a step for each adopted rule that changed and carries a translation whose English
  text changed: the translation must be made again, and the entry is printed without
  it, with the sha256 of the new text
- a step for each adopted rule that was removed: take it out of "adopted", and to
  keep it, add the printed entry to "own", which has the fields of an own rule only:
  its status and "where" are kept, and its translation is not.
  A rule merged into another, or moved into Ratchet's own register, shows as removed:
  the step says that the changelog says why, and that the rule it was merged into may
  be adopted in its place
- when every adopted rule was removed, a step to adopt at least one rule
- the new rules, each with the entry to paste if the project adopts it
- the changed and removed rules that the register does not adopt, by key
- when the fields of ratchet.json differ between the two, at the top or in its rules,
  a field new or gone, a note for a project that keeps a copy of a Ratchet check, or a
  check of its own, that reads it.
- when the form of register.json changed between the two versions, what changed. Every
  field that came in 0.10 may be left out, so none of it is a step.

It writes nothing. It runs offline, on the files it is given. Before it prints a
step, it checks that the register passes check_register.py against the older
Ratchet, and that the register with every step done passes it against the newer
one: with each removed rule taken out, and with each also moved to "own". When the
register must adopt a rule, it is checked with all of those it is given adopted.
The data files are read strictly, as every check here reads them, and no rule is
read from Markdown. Where a version changed a rule, and why, is in the changelog
of the newer Ratchet.

Exit code 0: the steps are printed, or there is nothing to change. 1: the register
does not pass against the version it states, the newer Ratchet is older, or the
steps would not give a register that passes against it. 2: the script could not
run: a file is missing or is not a valid data file.
Standard library only. Run on Python 3.9 and 3.12.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True

import argparse
import copy
import json
import os
import re
import shlex

import check_register
import registry

# The fields of a rule that the comparison reads, in the order a change names them.
COMPARED = (("status", "the status"), ("enforcement", "the enforcement"), ("rule", "the rule"),
            ("ratchet", "the ratchet"), ("source", "the source"))
# What the step for a removed rule that the register adopts adds. A rule may leave because it was merged into another,
# or moved into Ratchet's own register, which ratchet.json does not show: the changelog does.
MERGED = ("The changelog of Ratchet %s says why it was removed. When it was merged into another rule, the register may "
          "adopt that rule in its place.")
# The versions that changed the form of register.json, and what changed. Told to a register that moves past the version.
REGISTER_FORMS = (
    ("0.10", 'The form of register.json grew in Ratchet 0.10 (D-2026-11-20-generated-block). It may name an instruction file in '
             '"instructions", and check_register.py then checks the block of rules it generates into that file. An adopted rule '
             'may carry a "translation", bound to its English rule by a sha256. An own rule may carry "status" and "where". A '
             'register without them stays valid, so none of this is a step.'),
)


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
    """A rule as it stands in a register, keeping the status, the place of the check and the translation that still hold.

    A translation is kept when the English text it is bound to did not change, and is left out when it did.
    """
    result = dict((field, rule[field]) for field in check_register.RULE_FIELDS)
    if rule["enforcement"] == "enforced":
        if old_entry is not None and "status" in old_entry:
            result["status"] = old_entry["status"]
            if "where" in old_entry:
                result["where"] = old_entry["where"]
        else:
            result["status"] = "text only for now"
    if old_entry is not None and check_register.TRANSLATION in old_entry and old_entry["rule"] == rule["rule"]:
        result[check_register.TRANSLATION] = copy.deepcopy(old_entry[check_register.TRANSLATION])
    return result


def own_prefix(register):
    """(prefix, why) for the project's own keys: that of its first own rule, or one made from the project's name.

    A name gives the lowercase letters and digits in it, in words joined by hyphens. A name that gives none, or gives
    Ratchet's own prefix, gives "project".
    """
    if register["own"]:
        return register["own"][0]["key"].split(".", 1)[0], "from the register's first own rule"
    prefix = "-".join(re.findall(r"[a-z0-9]+", register["project"].lower()))
    if prefix in ("", "ratchet"):
        prefix = "project"
    return prefix, "made from the project's name"


def own_entry(rule, before, prefix, taken):
    """A removed rule as a rule of the project's own: the fields key, rule, ratchet and source, and the status and the
    "where" of the entry it had in "adopted", which an own rule may have from 0.10. Not its translation, which is bound
    to a rule of Ratchet.

    The key is the prefix, a dot and the name of Ratchet's key, with -2, -3 and so on when that key is taken.
    """
    name = rule["key"].split(".", 1)[1]
    key, number = "%s.%s" % (prefix, name), 1
    while key in taken:
        number += 1
        key = "%s.%s-%d" % (prefix, name, number)
    fields = [("key", key)] + [(field, rule[field]) for field in check_register.RULE_FIELDS if field != "key"]
    if rule["ratchet"].startswith("Check: "):
        fields += [(field, before[field]) for field in check_register.STATUS_FIELDS if field in before]
    return dict(fields)


def rule_fields(data):
    """Every field that at least one rule of a ratchet.json holds."""
    return set(field for rule in data["rules"] for field in rule)


def form_changes(old, new):
    """The fields that one version has and the other lacks, as text: first those at the top of ratchet.json, then those
    of its rules, each sorted by the field.

    The older file is read with registry.validate(older=True), which allows it to lack the cap and to hold the date
    and the sources, which left ratchet.json in 0.9 (D-2026-11-19-batched-releases), allows its experimental rules
    to lack "since", which came in 0.10 (D-2026-11-19-one-point-oh), and refuses any other field it does not know.
    So a field can be new, or gone. A field of a rule counts when some rule of one version holds it and no rule of
    the other does: "kept_by", which a rule may hold, is new only once a rule holds it.
    """
    changes = [(field, '"%s" is new' % field) for field in set(new) - set(old)]
    changes += [(field, '"%s" is gone' % field) for field in set(old) - set(new)]
    rules = [(field, '"%s" in a rule is new' % field) for field in rule_fields(new) - rule_fields(old)]
    rules += [(field, '"%s" in a rule is gone' % field) for field in rule_fields(old) - rule_fields(new)]
    return [text for _, text in sorted(changes)] + [text for _, text in sorted(rules)]


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
            if check_register.TRANSLATION in before and check_register.TRANSLATION not in step["entry"]:
                text.append('Its rule changed, so its translation must be made again, and the entry has none. Translate the new '
                            'rule and add its "translation" with "sha256": "%s".' % check_register.rule_sha256(rule["rule"]))
            step["text"] = " ".join(text)
        steps.append(step)
    prefix, why = own_prefix(register)
    taken = set(item["key"] for item in register["own"])
    for rule in old["rules"]:
        key = rule["key"]
        if key not in new_by:
            step = {"key": key, "kind": "removed", "adopted": key in adopted, "text": "%s: removed." % key}
            if key in adopted:
                step["entry"] = own_entry(rule, adopted[key], prefix, taken)
                taken.add(step["entry"]["key"])
                text = ['%s: removed. Remove it from "adopted". To keep it as a rule of the project\'s own, also add this entry to "own".' % key]
                if register["own"]:
                    text.append('Its key has the prefix "%s", %s.' % (prefix, why))
                else:
                    text.append('The register has no own rule yet, so its key has a prefix %s, "%s". Any other prefix of the same '
                                'form will do, but not "ratchet".' % (why, prefix))
                if step["entry"]["key"] != "%s.%s" % (prefix, key.split(".", 1)[1]):
                    text.append('The key "%s.%s" is taken, so the entry has "%s".' % (prefix, key.split(".", 1)[1], step["entry"]["key"]))
                if "status" in step["entry"]:
                    text.append('An own rule may say where its check stands, so the entry keeps its status and its "where".')
                if check_register.TRANSLATION in adopted[key]:
                    text.append("An own rule has no translation, so the entry has none.")
                text.append(MERGED % new["version"])
                step["text"] = " ".join(text)
            steps.append(step)

    after = copy.deepcopy(register)
    after["ratchet_version"] = new["version"]
    by_step = dict((step["key"], step) for step in steps if step["adopted"])
    after["adopted"] = [
        copy.deepcopy(by_step[item["key"]]["entry"]) if item["key"] in by_step else item
        for item in after["adopted"]
        if not (item["key"] in by_step and by_step[item["key"]]["kind"] == "removed")
    ]
    return steps, after


def outcomes(steps, after, new):
    """(registers, kept, must_adopt): each register the printed steps can give, whether a removed rule can be kept in
    "own", and the entries of which the register must adopt at least one.

    A removed rule may be taken out or also moved to "own", so there are two registers when the register adopts one.
    When every rule the register adopts was removed, it must adopt at least one: the new rules, or, when there are
    none, the rules to start with, which templates/register.json adopts. Each register is then checked with all of them
    adopted.
    """
    kept = [step["entry"] for step in steps if step["adopted"] and step["kind"] == "removed"]
    registers = [after]
    if kept:
        moved = copy.deepcopy(after)
        moved["own"] = moved["own"] + copy.deepcopy(kept)
        registers.append(moved)
    must_adopt = []
    if not after["adopted"]:
        by_key = registry.rules_by_key(new)
        must_adopt = [step["entry"] for step in steps if step["kind"] == "new"] or [entry(by_key[key]) for key in new["start"]]
        for register in registers:
            register["adopted"] = copy.deepcopy(must_adopt)
    return registers, bool(kept), must_adopt


def paste(item):
    return json.dumps(item, indent=2, ensure_ascii=False)


def put_in_place(script, path, option, target):
    """The shell command that prints one file with check_register.py and puts it in place at target: a new file in the
    directory the command runs in, named after the target, then moved there. The target is a relative path."""
    new = shlex.quote(target.split("/")[-1] + ".new")
    return "rm -f %s && python3 %s %s %s > %s && rm -f %s && mv %s %s" % (
        new, script, path, option, new, shlex.quote(target), new, shlex.quote(target))


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
    registers, kept, must_adopt = outcomes(steps, after, new)
    failed = False
    for number, done in enumerate(registers):
        how = "" if number == 0 else ', with each removed rule moved to "own"'
        for problem in check_register.check(done, new)[0]:
            # The steps would not give a register that passes. That is a fault in this script, not in the register.
            print("%s after the steps%s: %s" % (name, how, problem), file=out)
            failed = True
    if failed:
        print("FAIL: the steps would not give a register that passes against Ratchet %s. Upgrade by hand, and report this." % new["version"], file=out)
        return 1
    new_rules = [step for step in steps if step["kind"] == "new"]

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
    if must_adopt:
        number += 1
        print("%d. Every rule the register adopts was removed, and a register that adopts no rule from Ratchet does not pass "
              "check_register.py. Adopt at least one rule of Ratchet %s: %s" % (number, new["version"], (
                  "the new rules below come with their entries." if new_rules else
                  "the rules to start with below come with their entries.")), file=out)
    if must_adopt and not new_rules:
        print("", file=out)
        print("Rules to start with, which templates/register.json of Ratchet %s adopts:" % new["version"], file=out)
        print("", file=out)
        for item in must_adopt:
            print(paste(item), file=out)
            print("", file=out)
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
    form = form_changes(old, new)
    if form:
        print("", file=out)
        print("The form of ratchet.json changed from Ratchet %s to %s: %s. This is for the project, not the register. Ratchet's "
              "checks read ratchet.json strictly, so the checks of Ratchet %s do not read the ratchet.json of %s. The checks in "
              ".ratchet come with their own version and need nothing. A copy of a Ratchet check kept in the project, or a check "
              "of the project's own, that reads ratchet.json must be updated: replace the copy with the one from Ratchet %s, or "
              "change the check." % (old["version"], new["version"], joined(form), old["version"], new["version"], new["version"]),
              file=out)
    for version, text in REGISTER_FORMS:
        if version_key(old["version"]) < version_key(version) <= version_key(new["version"]):
            print("", file=out)
            print(text, file=out)
    print("", file=out)
    instructions = None
    if check_register.INSTRUCTIONS in register:
        instructions = "/".join(part for part in (os.path.dirname(path).replace(os.sep, "/"), register[check_register.INSTRUCTIONS]) if part)
        print("Then print REGISTER.md and %s again, put each in place, and check them:" % instructions, file=out)
    else:
        print("Then print REGISTER.md again, put it in place, and check it:", file=out)
    print("", file=out)
    # The check writes nothing (round 3 of #100). Each file is printed to a new file in the directory the commands run in,
    # and moved into place. rm -f removes a link that stands at either name, never what it points at, so neither the
    # redirection nor mv follows one, and mv does not move the file into a directory that a link leads to.
    print("    %s" % put_in_place(script, path, "--print-markdown", "REGISTER.md"), file=out)
    if instructions is not None:
        print("    %s" % put_in_place(script, path, "--print-instructions", instructions), file=out)
    print("    python3 %s %s --markdown REGISTER.md" % (script, path), file=out)
    print("", file=out)
    if not must_adopt:
        adopting = "no new rule adopted"
    elif new_rules:
        adopting = "the new rules adopted"
    else:
        adopting = "the rules to start with adopted"
    either = ', whether each removed rule is taken out or also moved to "own" with the entry printed' if kept else ""
    print("Checked: with the steps above and %s, %s passes check_register.py against Ratchet %s%s." % (
        adopting, name, new["version"], either), file=out)
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
