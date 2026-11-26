#!/usr/bin/env python3
"""Print what a project's register must do to move to a newer version of Ratchet.

    python3 .ratchet/checks/upgrade.py register.json [--to 0.12] [--no-fetch]
    python3 .ratchet/checks/upgrade.py register.json --from OLD/ratchet.json [--source NEW/ratchet.json]

The register is the project's register.json.

The one command, without --from (D-2026-11-22-second-redraw, step 6). The clone of
Ratchet this script stands in, .ratchet, must be a git clone. The script fetches its
tags from origin, with git and nothing else, unless --no-fetch is given. It reads the
version the register states, and takes ratchet.json from that version's tag. It
compares it with the release asked for with --to, or else the latest release tag by
number, and says how many releases behind the register is. When the register passes
against the version it states, it moves the clone to the release, detached, and runs
the upgrade.py there, which prints the steps below, the commands to run after, and
the commit to pin the workflow to. A register with rows by reference in a project
with no .github/workflows/ratchet.yml, which adopt mode never writes, is told instead
how to copy checks/run_pinned.py again from the new commit, with the line for a
local check script and for the CI step, as init.py prints them. It does not move a
clone with changes to files git tracks in it, or one on a branch, and it says how to move the clone back. A version
with no tag, a shallow clone that lacks the tag, a tag asked for that does not exist
and a fetch that fails each stop it, with what to do.

Offline, with --from: --from is ratchet.json of the version the register states, and
--source, by default the ratchet.json next to this script, is the newer Ratchet. It
reads those files and nothing else, and runs no git.

Either way the script compares the two versions, rule by rule, and prints:

- a step for each adopted rule that changed, with the entry to paste in place of
  the old one
- a step for each adopted rule that changed and carries a translation whose English
  text changed: the translation must be made again, and the entry is printed without
  it, with the sha256 of the new text
- for a changed rule that the register adopts by reference: whether its sha256 still
  matches, and when the rule or its ratchet changed, that it no longer does, the new
  sha256 in the entry, and that the project reads its own wording in the file the row
  names again, with the new rule and its ratchet printed to read it against. Nothing
  fails until the owner moves "ratchet_version"
- a step for each adopted rule that was removed: take it out of "adopted", and to
  keep it, add the printed entry to "own", which has the fields of an own rule only:
  its status and "where" are kept, and its translation is not. A rule adopted by
  reference gets Ratchet's text in that entry, and the step names its marker line to
  take out of the file. A rule adopted in part keeps its status and not its "where",
  and the step says so.
  A rule merged into another, or moved into Ratchet's own register, shows as removed:
  the step says that the changelog says why, and that the rule it was merged into may
  be adopted in its place
- when every adopted rule was removed, a step to adopt at least one rule
- the new rules, each with the entry to paste if the project adopts it
- the changed and removed rules that the register does not adopt, by key
- when the fields of ratchet.json differ between the two, at the top or in its rules,
  a field new or gone, a note for a project that keeps a copy of a Ratchet check, or a
  check of its own, that reads it.
- the commands that print REGISTER.md and the instruction file again and check them,
  with the options first and the register's path after "--". A register with rows by
  reference after the steps and no REGISTER.md beside it is not told to print one, and
  its check command has no --markdown REGISTER.md.

It writes no file of the project. Only the one command changes anything: the tags
and the checkout of .ratchet, through git. Before it prints a
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
run: a file is missing or is not a valid data file, or, in the one command, .ratchet
is not a git clone or cannot be moved, a tag is missing, or the fetch failed.
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
import copy
import json
import os
import re
import shlex
import subprocess

import check_register
import registry
import run_pinned

# The fields of a rule that the comparison reads, in the order a change names them.
COMPARED = (("status", "the status"), ("enforcement", "the enforcement"), ("rule", "the rule"),
            ("ratchet", "the ratchet"), ("source", "the source"))
# What the step for a removed rule that the register adopts adds. A rule may leave because it was merged into another,
# or moved into Ratchet's own register, which ratchet.json does not show: the changelog does.
MERGED = ("The changelog of Ratchet %s says why it was removed. When it was merged into another rule, the register may "
          "adopt that rule in its place.")
# The workflow init.py writes for a new repo. Adopt mode writes none, and runs the check with run_pinned.py instead.
WORKFLOW = ".github/workflows/ratchet.yml"
# A release: a major and a minor version, as a tag names it after its "v".
RELEASE = re.compile(r"\A(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")


class UpgradeError(Exception):
    """The upgrade cannot run."""


def version_key(version):
    major, minor = version.split(".")
    return int(major), int(minor)


def load_older(path, data=None):
    """ratchet.json of an older version, read as strictly as this one's, but for the parts named in registry.validate.

    With data, the bytes are those given, and path only names them.
    """
    try:
        data = registry.load_json(path) if data is None else registry.parse_json(data)
    except registry.RegistryError as error:
        raise UpgradeError("%s: %s" % (path, error))
    problems = registry.validate(data, None, older=True)
    if problems:
        raise UpgradeError("\n".join("%s: %s" % (path, problem) for problem in problems))
    return data


def entry(rule, old_entry=None):
    """A rule as it stands in a register, keeping the status, the place of the check and the translation that still hold.

    A translation is kept when the English text it is bound to did not change, and is left out when it did. A row
    adopted by reference stays one: its key, its file, and the sha256 of the rule and its ratchet in this version. A row
    adopted in part keeps its "where", the clauses its wording does not state, whether the rule names a check or not.
    """
    part = old_entry is not None and check_register.is_reference(old_entry) and check_register.holds_part(old_entry)
    if old_entry is not None and check_register.is_reference(old_entry):
        result = {"key": rule["key"], check_register.STANDS_IN: old_entry[check_register.STANDS_IN],
                  check_register.SHA: check_register.reference_sha256(rule)}
    else:
        result = dict((field, rule[field]) for field in check_register.RULE_FIELDS)
    if rule["enforcement"] == "enforced":
        if old_entry is not None and "status" in old_entry:
            result["status"] = old_entry["status"]
            if "where" in old_entry:
                result["where"] = old_entry["where"]
        else:
            result["status"] = "text only for now"
            if part:
                result["where"] = old_entry["where"]
    elif part:
        result["where"] = old_entry["where"]
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
        # Not the "where" of a row adopted in part: the own rule holds Ratchet's whole text, and is never in part.
        fields += [(field, before[field]) for field in check_register.STATUS_FIELDS
                   if field in before and not (field == "where" and check_register.holds_part(before))]
    return dict(fields)


def rule_fields(data):
    """Every field that at least one rule of a ratchet.json holds."""
    return set(field for rule in data["rules"] for field in rule)


def form_changes(old, new):
    """The fields that one version has and the other lacks, as text: first those at the top of ratchet.json, then those
    of its rules, each sorted by the field.

    The older file is read with registry.validate(older=True), which refuses a field it does not know, at the top as
    in a rule. So a field can be new, or gone, only when a later version changes the form. A field of a rule counts
    when some rule of one version holds it and no rule of the other does: "kept_by", which a rule may hold, is new only
    once a rule holds it.
    """
    changes = [(field, '"%s" is new' % field) for field in set(new) - set(old)]
    changes += [(field, '"%s" is gone' % field) for field in set(old) - set(new)]
    rules = [(field, '"%s" in a rule is new' % field) for field in rule_fields(new) - rule_fields(old)]
    rules += [(field, '"%s" in a rule is gone' % field) for field in rule_fields(old) - rule_fields(new)]
    return [text for _, text in sorted(changes)] + [text for _, text in sorted(rules)]


def changed_fields(old, new):
    return [name for field, name in COMPARED if old[field] != new[field]]


def reference_text(before, rule):
    """What the step for a changed rule says to a row adopted by reference: whether its sha256 still matches, and if not,
    the new one and that the project reads its own wording again."""
    new = check_register.reference_sha256(rule)
    if before[check_register.SHA] == new:
        return ("It is adopted by reference, and its rule and its ratchet did not change, so its sha256 still matches and the "
                "entry is as it was.")
    return ("It is adopted by reference, and its rule or its ratchet changed, so its sha256 no longer matches: the new sha256 "
            "is %s. Read the project's own wording in %s again against the new rule, and change it where it no longer says "
            "what the rule says. check_register.py fails from when \"ratchet_version\" is moved until sha256 is set to the "
            "new one, and not before.%s" % (new, before[check_register.STANDS_IN],
                                            " It is adopted in part: read the clauses its \"where\" lists against the new rule "
                                            "too." if check_register.holds_part(before) else ""))


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
                text.append('It is text only now, so the entry has no status%s.' % (
                    ', and keeps the "where" that lists the clauses its wording does not state' if "where" in step["entry"]
                    else ' and no "where"'))
            elif step["entry"].get("status") == "built" and old_by[key]["ratchet"] != rule["ratchet"]:
                text.append('It keeps the status "built". Its ratchet changed: check that the check in "where" still does what '
                            'the ratchet says, or set the status to "text only for now".')
            if check_register.is_reference(before):
                text.append(reference_text(before, rule))
                if before[check_register.SHA] != check_register.reference_sha256(rule):
                    # The new rule and its ratchet, so the project can read its wording against them (review of step 9a).
                    step["against"] = rule
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
                if "where" in step["entry"]:
                    text.append('An own rule may say where its check stands, so the entry keeps its status and its "where".')
                elif "status" in step["entry"]:
                    text.append('An own rule may say where its check stands, so the entry keeps its status.')
                clauses = check_register.part_clauses(adopted[key].get("where"))
                if check_register.holds_part(adopted[key]) and clauses:
                    text.append('It was adopted in part, and an own rule stands in the register in full, so the entry has no '
                                '"where": the clauses it listed as not stated, %s, stand in the rule of the entry like the rest '
                                'of it.' % check_register.PART_SEPARATOR.join(clauses))
                if check_register.TRANSLATION in adopted[key]:
                    text.append("An own rule has no translation, so the entry has none.")
                if check_register.is_reference(adopted[key]):
                    text.append("It was adopted by reference, and an own rule stands in the register in full, so the entry "
                                "holds Ratchet's text of it, which the project may replace with its own wording. Take the line "
                                "%s out of %s, since no row names it there." % (
                                    check_register.MARKER % key, adopted[key][check_register.STANDS_IN]))
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
    # The option stands first and the register's path after --, so a path that starts with - is not read as an option.
    return "rm -f -- %s && python3 %s %s -- %s > %s && rm -f -- %s && mv -- %s %s" % (
        new, shlex.quote(script), option, shlex.quote(path), new, shlex.quote(target), new, shlex.quote(target))


def passes(name, register, old, out):
    """Whether the register passes check_register.py against the version it states. Prints why when it does not."""
    problems, _ = check_register.check(register, old)
    if problems:
        for problem in problems:
            print("%s: %s" % (name, problem), file=out)
        print("FAIL: %s does not pass check_register.py against Ratchet %s, the version it states. Fix it first: an upgrade "
              "starts from a register that matches its Ratchet." % (name, old["version"]), file=out)
    return not problems


def report(path, register, old, new, out, script):
    """Print the steps for one register. Returns the exit code."""
    name = os.path.basename(path)
    if not passes(name, register, old, out):
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
        if step.get("against"):
            print("The rule in Ratchet %s, to read the wording in %s against: %s" % (
                new["version"], step["entry"][check_register.STANDS_IN], step["against"]["rule"]), file=out)
            print("Its ratchet: %s" % step["against"]["ratchet"], file=out)
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
    print("", file=out)
    instructions = None
    if check_register.INSTRUCTIONS in register:
        instructions = "/".join(part for part in (os.path.dirname(path).replace(os.sep, "/"), register[check_register.INSTRUCTIONS]) if part)
    # REGISTER.md is optional for a register with rows by reference. One that left it out is not told to print it
    # (review of step 9a). The register looked at is the one with the steps done.
    markdown = not check_register.references(after) or os.path.lexists(os.path.join(os.path.dirname(path), "REGISTER.md"))
    if not markdown:
        print("REGISTER.md is not there, which a register with rows adopted by reference may leave out, so it is not printed.",
              file=out)
    if markdown and instructions is not None:
        print("Then print REGISTER.md and %s again, put each in place, and check them:" % instructions, file=out)
    elif markdown:
        print("Then print REGISTER.md again, put it in place, and check it:", file=out)
    elif instructions is not None:
        print("Then print %s again, put it in place, and check it:" % instructions, file=out)
    else:
        print("Then check it:", file=out)
    print("", file=out)
    # The check writes nothing (round 3 of #100). Each file is printed to a new file in the directory the commands run in,
    # and moved into place. rm -f removes a link that stands at either name, never what it points at, so neither the
    # redirection nor mv follows one, and mv does not move the file into a directory that a link leads to.
    if markdown:
        print("    %s" % put_in_place(script, path, "--print-markdown", "REGISTER.md"), file=out)
    if instructions is not None:
        print("    %s" % put_in_place(script, path, "--print-instructions", instructions), file=out)
    # The check reads REGISTER.md only where the register has it or must have it: an adoption report on 0.12 found a
    # --markdown REGISTER.md printed for a file that was not there.
    print("    python3 %s%s -- %s" % (shlex.quote(script), " --markdown REGISTER.md" if markdown else "", shlex.quote(path)),
          file=out)
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


def git(root, *args, timeout=120):
    """(exit code, standard output as bytes, standard error as text) of git, run on the clone at root.

    No GIT_ variable of the caller is used, so that none leads git to another repo, git does not look for a repo above
    root, takes no lock it can do without, and never prompts.
    """
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.update(GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0", GIT_CEILING_DIRECTORIES=os.path.dirname(os.path.realpath(root)), LC_ALL="C")
    try:
        result = subprocess.run(["git", "-c", "advice.detachedHead=false", "-C", root] + list(args), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as error:
        raise UpgradeError("git %s could not be run: %s." % (args[0], error))
    return result.returncode, result.stdout, result.stderr.decode("utf-8", errors="replace")


def said(stderr):
    """The line of git's standard error that says what failed."""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    for line in lines:
        for start in ("fatal: ", "error: "):
            if line.startswith(start):
                return line[len(start):]
    return lines[-1] if lines else "git said nothing"


def git_text(root, *args):
    code, output, stderr = git(root, *args)
    if code != 0:
        raise UpgradeError("git %s failed: %s." % (args[0], said(stderr)))
    return output.decode("utf-8", errors="replace").strip()


def releases(root):
    """{version: tag} for every tag of the clone that names a release: v, a major and a minor version, and nothing else."""
    found = {}
    for name in git_text(root, "for-each-ref", "--format=%(refname:strip=2)", "refs/tags/").splitlines():
        if name.startswith("v") and RELEASE.match(name[1:]):
            found[name[1:]] = name
    return found


def tags(versions):
    return joined(["v" + version for version in sorted(versions, key=version_key)])


def one_command(args, out):
    """The upgrade in one command: fetch the tags of the clone this script stands in, compare the tag the register
    states with the latest release, or the one asked for, and print the steps. Returns the exit code."""
    here = os.path.abspath(__file__)
    root = os.path.dirname(os.path.dirname(here))
    typed = sys.argv[0] if os.path.isfile(sys.argv[0]) and os.path.samefile(sys.argv[0], here) else here
    shown = os.path.normpath(os.path.join(os.path.dirname(typed), os.pardir))
    quoted = shlex.quote(shown)
    code, output, _ = git(root, "rev-parse", "--show-toplevel")
    if code != 0 or os.path.realpath(output.decode("utf-8", errors="replace").strip()) != os.path.realpath(root):
        raise UpgradeError("%s is not a git clone of Ratchet, so it has no tags to compare. Clone Ratchet into it with git, "
                           "as README.md says, or compare two files with --from." % shown)
    name = os.path.basename(args.register)
    if not os.path.isfile(args.register):
        raise UpgradeError("no such file: %s" % args.register)
    try:
        register = registry.load_json(args.register)
    except registry.RegistryError as error:
        print("%s: %s" % (args.register, error), file=out)
        print("FAIL: the register cannot be read", file=out)
        return 1
    stated = register.get("ratchet_version") if isinstance(register, dict) else None
    if not isinstance(stated, str) or not RELEASE.match(stated):
        print('FAIL: %s states no "ratchet_version" of the form 0.11, so there is no tag to compare it with.' % name, file=out)
        return 1
    if git_text(root, "status", "--porcelain", "--untracked-files=no"):
        raise UpgradeError("%s has changes to files that git tracks in it, so it is not moved. Put them aside, or clone "
                           "Ratchet into it again." % shown)

    if not args.no_fetch:
        code, _, stderr = git(root, "fetch", "--tags", "--quiet", "--no-recurse-submodules", "origin", timeout=600)
        if code != 0:
            raise UpgradeError("the tags of %s could not be fetched from origin: %s. To use the tags already in %s, run "
                               "again with --no-fetch." % (shown, said(stderr), shown))
        print("Fetched the tags of %s from origin." % shown, file=out)
    known = releases(root)
    listed = " Its release tags are %s." % tags(known) if known else " It has no release tag."
    if args.to is not None:
        target = args.to[1:] if args.to.startswith("v") else args.to
        if not RELEASE.match(target):
            raise UpgradeError("--to takes a version such as 0.11, or its tag, v0.11, not %r." % args.to)
        if target not in known:
            raise UpgradeError("there is no release tag v%s in %s.%s%s" % (
                target, shown, listed, " Its tags were not fetched: run again without --no-fetch." if args.no_fetch else ""))
        which = "the release asked for"
    elif known:
        target, which = max(known, key=version_key), "the latest release"
    else:
        raise UpgradeError("%s has no release tag to compare with.%s" % (
            shown, " Its tags were not fetched: run again without --no-fetch." if args.no_fetch else ""))
    if version_key(target) < version_key(stated):
        print("FAIL: Ratchet %s, %s, is older than %s, the version %s states. An upgrade does not go back." % (
            target, which, stated, name), file=out)
        return 1
    if stated not in known:
        missing = "%s states Ratchet %s, and %s has no tag v%s to compare with." % (name, stated, shown, stated)
        if not args.no_fetch:
            missing += " origin has none either, so Ratchet %s was never released.%s" % (stated, listed)
        elif git_text(root, "rev-parse", "--is-shallow-repository") == "true":
            missing += (" %s is a shallow clone, which holds only the tags it was cloned with, and --no-fetch fetched no "
                        "other. Run again without --no-fetch, or fetch the tags: git -C %s fetch --tags origin" % (shown, quoted))
        else:
            missing += (" --no-fetch fetched no tag. Run again without --no-fetch, or fetch the tags: git -C %s fetch --tags "
                        "origin" % quoted)
        raise UpgradeError(missing)

    code, data, stderr = git(root, "cat-file", "blob", "refs/tags/%s:ratchet.json" % known[stated])
    if code != 0:
        raise UpgradeError("%s has no ratchet.json: %s." % (known[stated], said(stderr)))
    old = load_older("ratchet.json at %s" % known[stated], data)
    # The register must pass against the version it states before the clone is moved, so that a register to fix first
    # is fixed against the checks it was written for.
    if not passes(name, register, old, out):
        return 1
    commit = git_text(root, "rev-parse", "--verify", "refs/tags/%s^{commit}" % known[target])
    head = git_text(root, "rev-parse", "--verify", "HEAD")
    if head != commit:
        code, branch, _ = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
        if code == 0:
            # A clone on a branch may be someone's work on Ratchet, so it is not moved. A clone made at a tag is not on one.
            # It is told to move to the release itself, whose upgrade.py knows that release's forms, so that the same
            # command then runs there (Gemini's review of 0425ffe).
            branch = branch.decode("utf-8", errors="replace").strip()
            raise UpgradeError("%s is on the branch %s, so it is not moved. Move it to %s, the release to upgrade to, with "
                               "git -C %s checkout --detach %s, and run again. The branch stays where it is: git -C %s "
                               "checkout %s goes back to it." % (shown, branch, known[target], quoted, known[target], quoted,
                                                                 shlex.quote(branch)))
        code, _, stderr = git(root, "checkout", "--quiet", "--detach", commit)
        if code != 0 or git_text(root, "rev-parse", "--verify", "HEAD") != commit:
            raise UpgradeError("%s could not be moved to %s: %s." % (shown, known[target], said(stderr)))
        print("Moved %s to %s. It was at %s. To move it back: git -C %s checkout --detach %s" % (
            shown, known[target], head, quoted, head), file=out)
        # The steps are printed by the upgrade.py of the version moved to, which knows its own forms.
        # The register's path comes after --, so that one that starts with - is not read as an option there.
        again = (["--to", args.to] if args.to is not None else []) + ["--no-fetch", "--", args.register]
        result = subprocess.run([sys.executable, "-B", typed] + again,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        out.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode

    new = registry.load(os.path.join(root, "ratchet.json"))
    if new["version"] != target:
        raise UpgradeError("the ratchet.json of %s states %s, not %s." % (known[target], new["version"], target))
    behind = sorted((version for version in known if version_key(stated) < version_key(version) <= version_key(target)),
                    key=version_key)
    if behind:
        print("%s states Ratchet %s. %s is %s, %s after it: %s." % (
            name, stated, which[0].upper() + which[1:], target,
            "1 release" if len(behind) == 1 else "%d releases" % len(behind), joined(behind)), file=out)
    else:
        print("%s states Ratchet %s, %s. It is not behind." % (name, stated, which), file=out)
    print("", file=out)
    code = report(args.register, register, old, new, out, os.path.join(os.path.dirname(typed), "check_register.py"))
    if code == 0 and behind:
        print("", file=out)
        # The project's root is where this runs, as .ratchet/checks/upgrade.py, and where the printed commands run.
        project = os.getcwd()
        if check_register.references(register) and not os.path.lexists(os.path.join(project, WORKFLOW)):
            # REGISTER.md as the report decided it, on the register with the steps done: there, or required once no
            # row by reference is left (round 5 of #140).
            _, after = plan(register, old, new)
            markdown = (not check_register.references(after)
                        or os.path.lexists(os.path.join(project, "REGISTER.md")))
            for line in pinned_run(root, shown, project, known[target], commit, os.path.basename(args.register),
                                   markdown):
                print(line, file=out)
        else:
            print("Then pin %s to the commit of %s: %s." % (WORKFLOW, known[target], commit), file=out)
    return code


def pinned_run(root, shown, project, tag, commit, register="register.json", markdown=False):
    """What a register with rows by reference, in a project with no workflow of Ratchet's, is told to do with the commit:
    adopt mode wrote no workflow, and its check runs from checks/run_pinned.py, copied from the pinned commit. The same
    copy command and lines that init.py prints, with the new commit: the copy, the line of the local check script, and
    the CI step."""
    try:
        objects = run_pinned.objects_of(root)
        blob = run_pinned.stored_blob(root, commit, run_pinned.SELF)
    except (run_pinned.Refused, OSError) as error:
        raise UpgradeError("cannot read %s of %s from %s: %s" % (run_pinned.SELF, tag, shown, error))
    if not os.path.isabs(shown):
        objects = os.path.relpath(os.path.abspath(objects), project)
    # The register by its own name, as the project's root sees it: the commands run from there.
    run = run_pinned.run_command(commit, blob, run_pinned.COPY, register, markdown)
    return ["The check runs from the pinned commit with %s. To move it to the commit of %s, %s, run these from the "
            "project's root. Copy the runner again from that commit:" % (run_pinned.COPY, tag, commit),
            "",
            "    " + run_pinned.copy_command(objects, commit, blob, run_pinned.COPY),
            "",
            "Then put this line in the local check script, in place of the one there:",
            "",
            "    " + run_pinned.local_line(commit, blob, run_pinned.COPY, register, markdown),
            "",
            "or this in the step of the job that runs the check:",
            "",
            "    " + run]


def main(argv=None, out=None):
    out = out or sys.stdout
    parser = argparse.ArgumentParser(description="Print what a register must do to move to a newer Ratchet. Writes no file of "
                                                 "the project.")
    parser.add_argument("register", help="path to the project's register.json")
    parser.add_argument("--to", metavar="VERSION",
                        help="the release to compare with, such as 0.11 (default: the latest release tag)")
    parser.add_argument("--no-fetch", action="store_true", help="use the tags already in the clone, and fetch none")
    parser.add_argument("--from", dest="older", metavar="ratchet.json",
                        help="offline: ratchet.json of the version the register states, as it stood at its tag")
    parser.add_argument("--source", help="with --from: path to the newer ratchet.json (default: the one next to this script)")
    args = parser.parse_args(argv)
    if args.older is not None and (args.to is not None or args.no_fetch):
        parser.error("--from compares two files and fetches nothing: leave out --to and --no-fetch, or --from")
    if args.older is None and args.source is not None:
        parser.error("--source is the newer file of --from, and is given only with it")
    if args.older is None and os.path.dirname(args.register) not in ("", "."):
        # The one command names the register, REGISTER.md and the store from the folder it runs in, and prints commands
        # that run there: a register in another folder would be named one way here and another there (rounds 2 to 4 of
        # #140). So it takes a register named alone.
        parser.error("name the register alone, from the folder that holds it, such as: python3 .ratchet/checks/upgrade.py "
                     "register.json (not %s)" % args.register)
    try:
        if args.older is None:
            return one_command(args, out)
        script = os.path.join(os.path.dirname(sys.argv[0]), "check_register.py")
        new = registry.load(args.source or registry.SOURCE)
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
