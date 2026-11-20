#!/usr/bin/env python3
"""Reference check for ratchet.register-on-top.

A project's register is a data file, register.json. This check compares it with
Ratchet at the version it states: every adopted rule must be Ratchet's own rule,
character for character. A project chooses which rules it adopts. It never
rewrites one.

    python3 checks/check_register.py register.json
    python3 checks/check_register.py register.json --write REGISTER.md
    python3 checks/check_register.py register.json --markdown REGISTER.md
    python3 checks/check_register.py register.json --markdown REGISTER.md --agents AGENTS.md

REGISTER.md is generated from the data file. With --markdown the check also fails
unless REGISTER.md is, byte for byte, what the data file generates. The check
never reads rules out of Markdown.

With --agents the check also fails while the file given still holds a placeholder
of templates/AGENTS.md, from the fixed list PLACEHOLDERS, and names each. It looks
for those exact texts and nothing else: it does not parse the file.

A value in the data file is text, never Markdown: one line of Latin letters,
digits, plain spaces and the marks on a fixed list in registry.py. Every other
character is refused, and so is a name between two colons. When a value is
written to REGISTER.md, every ASCII punctuation mark gets a backslash, so that
no value can become a link, an image, emphasis, HTML or a comment. The one form
besides text is code, a part between a pair of backticks in the data. Keys,
statuses and the version are not free text: each has its own exact form.

Every file is read as strict UTF-8. Bytes that are not UTF-8 fail the check.
Line endings: CRLF is read as LF. Generated files are written with LF.

Exit code 0: the register is valid. 1: at least one problem. 2: the check could not run.
Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import os
import re
import sys

import registry

TOP_FIELDS = ("project", "ratchet_version", "adopted", "own")
RULE_FIELDS = ("key", "rule", "ratchet", "source")
STATUS_FIELDS = ("status", "where")
STATUSES = ("built", "text only for now")
OWN_KEY = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.[a-z0-9]+(-[a-z0-9]+)*\Z")

INTRO = (
    "Every rule in force in this project. This file takes precedence over all other text in the repo. "
    "It is generated from `register.json`: change that file, never this one."
)
ADOPTED = (
    "Ratchet version: %s. The rows below are copied verbatim from Ratchet at that version. "
    "The project chooses which rows it adopts and never rewrites one."
)
STANDS = (
    'One row for each adopted rule whose ratchet starts with "Check:". The status is "built" or "text only for now". '
    "A built check says where it lives."
)
OWN = "Same form as Ratchet's. The keys use the project's own prefix, never `ratchet.`."
NO_OWN = "None yet."

# The placeholders of templates/AGENTS.md, exactly as they stand there and in the order they start. A placeholder
# inside another one is on the list on its own, after it, since an edit may take the outer one away and leave the
# inner one. test_init.py fails when the template holds a part in angle brackets, nested or not, that is not on this
# list, other than <name>, which stands for any skill.
PLACEHOLDERS = (
    "<project>",
    "<One to three sentences: what the project is for and for whom.>",
    "<`HANDOVER.md`, or the status issue (#<n>)>",
    "<n>",
    "<If the project has a glossary: The project's terms are defined in `GLOSSARY.md`.>",
    "<The current phase, what is in scope, and what needs the owner's approval first, such as experiments that cost money.>",
    "<the directory your agent tool reads skills from>",
    "<skills directory>",
)


def placeholders(text):
    """The placeholders of templates/AGENTS.md that text still holds, in the order of PLACEHOLDERS."""
    return [placeholder for placeholder in PLACEHOLDERS if placeholder in text]


def check(register, ratchet):
    """Return (problems, summary) for a parsed register.json."""
    version = ratchet["version"]
    if not isinstance(register, dict):
        return ["the register must be one object with the fields %s" % ", ".join(TOP_FIELDS)], None
    problems = ["missing field %r" % field for field in TOP_FIELDS if field not in register]
    problems += ["unknown field %r" % field for field in sorted(set(register) - set(TOP_FIELDS))]
    if problems:
        return problems, None

    if registry.text_problem(register["project"]) or not registry.WORD.search(register["project"]):
        problems.append("project must be the project's name: it %s" % (registry.text_problem(register["project"]) or "holds no letter or digit"))
    stated = register["ratchet_version"]
    if not isinstance(stated, str) or not registry.VERSION.match(stated):
        problems.append("ratchet_version must be exactly a version like %s, found %r" % (version, stated))
    elif stated != version:
        problems.append(
            "the register follows Ratchet %s, but this check is Ratchet %s. Run the check from Ratchet at the version the register states"
            % (stated, version)
        )
    for field in ("adopted", "own"):
        if not isinstance(register[field], list):
            problems.append("%s must be a list" % field)
    if problems:
        return problems, None

    by_key = registry.rules_by_key(ratchet)
    seen = set()
    built = needs = core = 0
    for number, entry in enumerate(register["adopted"], 1):
        name = "adopted rule %d" % number
        if not isinstance(entry, dict):
            problems.append("%s must be an object" % name)
            continue
        if isinstance(entry.get("key"), str):
            name = entry["key"]
        missing = [field for field in RULE_FIELDS if field not in entry]
        unknown = sorted(set(entry) - set(RULE_FIELDS) - set(STATUS_FIELDS))
        if missing or unknown:
            problems += ["%s: missing field %r" % (name, field) for field in missing]
            problems += ["%s: unknown field %r" % (name, field) for field in unknown]
            continue
        if not all(isinstance(value, str) for value in entry.values()):
            problems.append("%s: every field must be a string" % name)
            continue
        if entry["key"] not in by_key:
            problems.append("%s is not a rule in Ratchet %s" % (name, version))
            continue
        if name in seen:
            problems.append("%s is adopted twice" % name)
            continue
        seen.add(name)
        rule = by_key[name]
        differs = False
        for field in ("rule", "ratchet", "source"):
            if entry[field] != rule[field]:
                differs = True
                problems.append(
                    "the %s of %s differs from Ratchet %s\n  expected: %s\n  found:    %s" % (field, name, version, rule[field], entry[field])
                )
        if differs:
            continue
        core += rule["status"] == "core"
        if rule["enforcement"] != "enforced":
            if "status" in entry or "where" in entry:
                problems.append("%s is text only in Ratchet. It cannot have a status or a place where its check lives" % name)
            continue
        needs += 1
        if "status" not in entry:
            problems.append('%s names a check, so it needs a status: "built" or "text only for now"' % name)
        elif entry["status"] not in STATUSES:
            problems.append('the status of %s is "%s". It must be "built" or "text only for now"' % (name, entry["status"]))
        elif registry.text_problem(entry.get("where", "")):
            problems.append("%s: where %s" % (name, registry.text_problem(entry.get("where", ""))))
        elif entry["status"] == "built" and not entry.get("where"):
            problems.append("%s is marked built but does not say where the check lives" % name)
        else:
            built += entry["status"] == "built"

    own = set()
    for number, entry in enumerate(register["own"], 1):
        name = "own rule %d" % number
        if not isinstance(entry, dict):
            problems.append("%s must be an object" % name)
            continue
        if isinstance(entry.get("key"), str):
            name = entry["key"]
        if set(entry) != set(RULE_FIELDS):
            problems.append("%s: an own rule has exactly the fields %s" % (name, ", ".join(RULE_FIELDS)))
        elif any(registry.text_problem(value) for value in entry.values()):
            field = next(field for field in RULE_FIELDS if registry.text_problem(entry[field]))
            problems.append("%s: %s %s" % (name if field != "key" else "own rule %d" % number, field, registry.text_problem(entry[field])))
        elif name.startswith("ratchet."):
            problems.append("%s uses Ratchet's prefix. The project's own keys use the project's prefix" % name)
        elif not OWN_KEY.match(name):
            problems.append("%s: an own key is a prefix, a dot and a name, in lowercase words joined by hyphens" % name)
        elif name in own:
            problems.append("%s is listed twice" % name)
        elif not registry.WORD.search(entry["rule"]):
            problems.append("%s: the rule holds no words" % name)
        elif registry.ratchet_problem(entry["ratchet"]):
            problems.append("%s: %s" % (name, registry.ratchet_problem(entry["ratchet"])))
        own.add(name)

    if not register["adopted"] and not problems:
        problems.append("no rules from Ratchet. A register that adopts nothing has nothing to check")
    summary = "%d rules match Ratchet %s (%d core, %d experimental). %d name a check: %d built, %d text only for now. %d rules of the project's own." % (
        len(seen), version, core, len(seen) - core, needs, built, needs - built, len(own),
    )
    return problems, summary


def render(register):
    """The one REGISTER.md that a valid register.json generates."""
    rows = [registry.row(entry) for entry in register["adopted"]]
    stands = [
        "| %s | %s | %s |" % (entry["key"], entry["status"], registry.cell(entry.get("where", "")))
        for entry in register["adopted"] if "status" in entry
    ]
    lines = [
        "# Register for %s" % registry.cell(register["project"]), "", INTRO, "",
        "## Rules from Ratchet", "", ADOPTED % register["ratchet_version"], "",
        registry.TABLE_HEADER, registry.TABLE_RULE] + rows + [
        "", "## Where each check stands", "", STANDS, "",
        "| Key | Status | Where the check lives |", "|---|---|---|"] + stands + [
        "", "## The project's own rules", ""]
    if register["own"]:
        lines += [OWN, "", registry.TABLE_HEADER, registry.TABLE_RULE]
        lines += [registry.row(entry) for entry in register["own"]]
    else:
        lines.append(NO_OWN)
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a project's register.json against Ratchet.")
    parser.add_argument("register", help="path to the project's register.json")
    parser.add_argument("--markdown", metavar="REGISTER.md", help="also fail unless this file is what the register generates")
    parser.add_argument("--write", metavar="REGISTER.md", help="write the generated register to this file")
    parser.add_argument("--agents", metavar="AGENTS.md", help="also fail while this file holds a placeholder of templates/AGENTS.md")
    parser.add_argument("--source", default=registry.SOURCE, help="path to ratchet.json (default: the one next to this check)")
    args = parser.parse_args(argv)
    try:
        ratchet = registry.load(args.source)
        if not os.path.isfile(args.register):
            raise OSError("no such file: %s" % args.register)
    except (registry.RegistryError, OSError) as error:
        print("check_register: cannot run: %s" % error, file=sys.stderr)
        return 2
    try:
        register = registry.load_json(args.register)
    except registry.RegistryError as error:
        problems, summary = [str(error)], None
    else:
        problems, summary = check(register, ratchet)
    problems = ["%s: %s" % (args.register, problem) for problem in problems]
    if not problems:
        expected = render(register)
        if args.write:
            with open(args.write, "w", encoding="utf-8", newline="") as handle:
                handle.write(expected)
            print("wrote %s" % args.write)
        if args.markdown:
            try:
                problems += registry.compare(args.markdown, registry.read(args.markdown), expected, os.path.basename(args.register))
            except registry.RegistryError as error:
                problems.append(str(error))
    if args.agents:
        try:
            text = registry.read(args.agents)
        except registry.RegistryError as error:
            problems.append(str(error))
        else:
            if text is None:
                problems.append("%s: the file is missing" % args.agents)
            else:
                problems += ["%s: still holds the template's placeholder %s. Fill it in or delete it" % (args.agents, placeholder)
                             for placeholder in placeholders(text)]
    if problems:
        for problem in problems:
            print(problem)
        print("FAIL: %d problem(s)" % len(problems))
        return 1
    print("%s: %s" % (args.register, summary))
    if args.agents:
        print("%s: holds no placeholder of templates/AGENTS.md" % args.agents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
