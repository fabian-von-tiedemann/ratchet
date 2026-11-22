#!/usr/bin/env python3
"""Reference check for ratchet.register-on-top.

A project's register is a data file, register.json. This check compares it with
Ratchet at the version it states: every adopted rule that is copied must be
Ratchet's own rule, character for character. A project chooses which rules it
adopts. It never rewrites a copied one.

An adopted rule may instead be adopted by reference, the weaker mode
(D-2026-11-22-second-redraw). The row holds no rule text: it names the key, in
"stands_in" a Markdown file in the repo where the rule stands in the project's own
words, and in "sha256" the hash of the rule and its ratchet in Ratchet at the
version the register states. The check fails unless the key is a rule at that
version, the hash is that rule's and its ratchet's, and the file holds the line
"<!-- ratchet:rule <key> -->" exactly once. It reads nothing else in the file, and
labels each such row, as REGISTER.md does: the check sees a marker, not the words.
The label says the protection against a softened wording is built only when the
register itself adopts ratchet.owner-paths with the status "built". stands_in has the
path form of "instructions", is checked on its path the same way, and is never the
instruction file. A row by reference has no translation, and an own rule is never
one. REGISTER.md may be left out by a register with rows by reference: with
--markdown, a file that is not there is then not a failure. Where it is there, it is
what the register generates, and the rows by reference stand in a table of their own,
with their label and no rule text, there and in the block.

    python3 checks/check_register.py register.json
    python3 checks/check_register.py register.json --markdown REGISTER.md
    python3 checks/check_register.py register.json --markdown REGISTER.md --agents AGENTS.md
    python3 checks/check_register.py register.json --print-markdown
    python3 checks/check_register.py register.json --print-instructions

REGISTER.md is generated from the data file. With --markdown the check also fails
unless REGISTER.md is, byte for byte, what the data file generates. The check
never reads rules out of Markdown.

The register may name, in "instructions", the project's own instruction file, such as
AGENTS.md or CLAUDE.md, relative to the register. The check then generates a block of
the rules from the register and fails unless the file starts with the line
"<!-- ratchet:begin -->" and holds one line "<!-- ratchet:end -->", each alone on its
line and ending in LF, and between them, byte for byte, the block. Nothing stands
before the block, so no text can put it in a code block, a comment or an element that
hides it. "ratchet:begin" or "ratchet:end" in any other form, in any case or in
disguise, is a broken marker. Nothing else in the file is read: it must be UTF-8, and
the rest of it is the project's own (D-2026-11-20-generated-block). No part of the path
of the file may be a symbolic link, and the file stays inside the directory of the
register.

The check writes nothing (round 3 of #100). --print-markdown prints REGISTER.md as the
register generates it, and --print-instructions prints the instruction file with the
block brought up to date: between the markers, or at the start of a file that has none,
with no other byte of the file changed. Each prints to standard output and nothing else,
and prints nothing when there is a problem. The user puts the file in place with the
commands in checks/README.md. The register and every file named on the command line are
taken as given and refused when the path to them passes through a symbolic link, below
the working directory or the enclosing git root (registry.root_link). Neither print
mode reads or prints a file that a row by reference names, or a marker line: the
marker is the project's to put in its own file.

An adopted rule may carry a translation of its rule: a language code, the text, and
the sha256 of the English rule it translates. The check fails when the sha256 is not
that of the rule's text in Ratchet at the version the register states, so a rule
that changes fails until its translation is made again. The translation is text from
the same fixed list as every value: Latin script only.

An own rule may say where its check stands, with "status" and "where", on the same
terms as an adopted rule, but it does not have to.

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
Line endings: CRLF is read as LF. Generated files are printed with LF.

Exit code 0: the register is valid. 1: at least one problem. 2: the check could not run.
Standard library only. Run on Python 3.9 and 3.12.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True

import argparse
import hashlib
import os
import re

import registry

TOP_FIELDS = ("project", "ratchet_version", "adopted", "own")
RULE_FIELDS = ("key", "rule", "ratchet", "source")
STATUS_FIELDS = ("status", "where")
# The fields a register may leave out, from 0.10 (D-2026-11-20-generated-block). A register without them is as before.
INSTRUCTIONS = "instructions"
TRANSLATION = "translation"
TRANSLATION_FIELDS = ("language", "text", "sha256")
# A language code: two or three lowercase letters, and a region of two capitals after a hyphen if needed, such as sv or pt-BR.
LANGUAGE = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?\Z")
SHA256 = re.compile(r"^[0-9a-f]{64}\Z")
# One part of the path of the instruction file: letters, digits, ".", "_" and "-". The whole path ends in ".md".
PATH_PART = re.compile(r"^[A-Za-z0-9._-]+\Z")
PATH_LENGTH = 200
BEGIN = "<!-- ratchet:begin -->"
END = "<!-- ratchet:end -->"
# The words of the two markers, wherever they stand in the instruction file, in any case and in disguise. Each must
# stand once. A character outside printable ASCII, a control character such as NUL or DEL among them (round 3 of
# #100), may stand in place of each character of the word, and any number of them
# between two, so a letter of another script, an accented letter, a mark that shows as nothing or a soft hyphen does
# not hide the word. A full-width form of ASCII is read as its ASCII character first. At least SHARE of the characters
# of the word must be the word's own, so text in another script is not taken for it. No table of Unicode is asked, so
# the answer is the same on every version of Python (round 2 of #100).
MARKER_WORDS = (("ratchet:begin", re.compile("ratchet:begin", re.I)), ("ratchet:end", re.compile("ratchet:end", re.I)))
SHARE = 7
# The full-width forms of ASCII, U+FF01 to U+FF5E, each U+FEE0 above its ASCII character.
FULL_WIDTH = dict((code, code - 0xFEE0) for code in range(0xFF01, 0xFF5F))
STATUSES = ("built", "text only for now")
OWN_KEY = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.[a-z0-9]+(-[a-z0-9]+)*\Z")
# A row adopted by reference, the weaker mode, from 0.11 (D-2026-11-22-second-redraw). It holds no rule text: the key,
# the Markdown file where the project's own wording stands, and the sha256 of the rule and its ratchet at the version
# the register states. It may hold "status" and "where" on the same terms as a copied row, and nothing else.
STANDS_IN = "stands_in"
SHA = "sha256"
REFERENCE_FIELDS = ("key", STANDS_IN, SHA)
TEXT_FIELDS = ("rule", "ratchet", "source")
# The one line that stands for a rule adopted by reference in the file its row names, alone on its line. The word
# "ratchet:rule" anywhere else in that file, in any case and in disguise, is a broken marker.
MARKER = "<!-- ratchet:rule %s -->"
MARKER_LINE = re.compile(r"\A<!-- ratchet:rule (ratchet\.[a-z0-9]+(?:-[a-z0-9]+)*) -->\Z")
RULE_WORD = (("ratchet:rule", re.compile("ratchet:rule", re.I)),)
# The label of every row by reference, in the check's output and in REGISTER.md, word for word as the decision has
# it. The last word is "built" only when the register itself adopts OWNER_PATHS with the status "built": the check
# reads the register's own claim, not the host.
LABEL = ("Adopted by reference, the weaker mode. The wording in force is the project's own, in the file named. The check "
         "sees a marker, not the words. Protection against a softened wording: %s.")
OWNER_PATHS = "ratchet.owner-paths"

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
STANDS_OWN = " Then one row for each of the project's own rules that has a status."
TRANSLATIONS = (
    "A translation is there for the people who read the rules in that language. The English text above is the rule. "
    "Each translation is bound to the English text it translates by that text's sha256, so a rule that changes fails "
    "the check until its translation is made again."
)
REFERENCED = (
    "Ratchet version: %s. Each row below names a rule of Ratchet at that version and the file where the project's own "
    "wording of it stands, and its sha256 in `register.json` is that of the rule and its ratchet. Each file named holds "
    "one marker line for each of its rows. No rule text stands here."
)
BLOCK_INTRO = (
    "Generated from `register.json` by Ratchet's `check_register.py`. Never edit this block by hand: change `register.json` "
    "and print the file again with `check_register.py register.json --print-instructions`. The check fails on any other text "
    "between the two markers. `REGISTER.md` holds the same rules and takes precedence over all other text in the repo."
)

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
    problems += ["unknown field %r" % field for field in sorted(set(register) - set(TOP_FIELDS) - {INSTRUCTIONS})]
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
    if INSTRUCTIONS in register and instructions_problem(register[INSTRUCTIONS]):
        problems.append(instructions_problem(register[INSTRUCTIONS]))
    if problems:
        return problems, None

    by_key = registry.rules_by_key(ratchet)
    seen = set()
    built = needs = core = translated = referenced = referenced_core = 0
    for number, entry in enumerate(register["adopted"], 1):
        name = "adopted rule %d" % number
        if not isinstance(entry, dict):
            problems.append("%s must be an object" % name)
            continue
        if isinstance(entry.get("key"), str):
            name = entry["key"]
        if is_reference(entry):
            found = reference_problem(name, entry, register, by_key, version)
            if found:
                problems.append(found)
                continue
            if name in seen:
                problems.append("%s is adopted twice" % name)
                continue
            seen.add(name)
            rule = by_key[name]
            referenced += 1
            referenced_core += rule["status"] == "core"
        else:
            missing = [field for field in RULE_FIELDS if field not in entry]
            unknown = sorted(set(entry) - set(RULE_FIELDS) - set(STATUS_FIELDS) - {TRANSLATION})
            if missing or unknown:
                problems += ["%s: missing field %r" % (name, field) for field in missing]
                problems += ["%s: unknown field %r" % (name, field) for field in unknown]
                continue
            if not all(isinstance(value, str) for field, value in entry.items() if field != TRANSLATION):
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
            if TRANSLATION in entry:
                found = translation_problem(entry[TRANSLATION], rule["rule"], version)
                if found:
                    problems.append("%s: %s" % (name, found))
                    continue
                translated += 1
        core += rule["status"] == "core"
        if rule["enforcement"] != "enforced":
            if "status" in entry or "where" in entry:
                problems.append("%s is text only in Ratchet. It cannot have a status or a place where its check lives" % name)
            continue
        needs += 1
        if "status" not in entry:
            problems.append('%s names a check, so it needs a status: "built" or "text only for now"' % name)
        elif status_problem(name, entry):
            problems.append(status_problem(name, entry))
        else:
            built += entry["status"] == "built"

    own = set()
    own_status = own_built = 0
    for number, entry in enumerate(register["own"], 1):
        name = "own rule %d" % number
        if not isinstance(entry, dict):
            problems.append("%s must be an object" % name)
            continue
        if isinstance(entry.get("key"), str):
            name = entry["key"]
        missing = [field for field in RULE_FIELDS if field not in entry]
        unknown = sorted(set(entry) - set(RULE_FIELDS) - set(STATUS_FIELDS))
        if TRANSLATION in unknown:
            problems.append("%s: an own rule has no translation. A translation is bound to a rule of Ratchet; the project "
                            "writes its own rules in the language it chooses" % name)
        elif STANDS_IN in unknown or SHA in unknown:
            problems.append("%s: an own rule is not adopted by reference. stands_in and sha256 stand for a rule of Ratchet; "
                            "the project's own rules stand in the register in full" % name)
        elif missing or unknown:
            problems += ["%s: missing field %r" % (name, field) for field in missing]
            problems += ["%s: unknown field %r" % (name, field) for field in unknown]
        elif any(registry.text_problem(entry[field]) for field in RULE_FIELDS):
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
        elif not entry["ratchet"].startswith("Check: ") and ("status" in entry or "where" in entry):
            problems.append("%s is text only. It cannot have a status or a place where its check lives" % name)
        elif "where" in entry and "status" not in entry:
            problems.append('%s says where its check lives and has no status. Give it the status "built" or "text only for now"' % name)
        elif "status" in entry and status_problem(name, entry):
            problems.append(status_problem(name, entry))
        elif "status" in entry:
            own_status += 1
            own_built += entry["status"] == "built"
        own.add(name)

    if not register["adopted"] and not problems:
        problems.append("no rules from Ratchet. A register that adopts nothing has nothing to check")
    if INSTRUCTIONS in register and not problems:
        block = render_block(register)
        for (word, _), places in zip(MARKER_WORDS, marker_words(block)):
            if len(places) != 1:
                problems.append("a value holds %s in code, and the block of rules for %s would hold it outside its marker. "
                                "Write it another way" % (word, register[INSTRUCTIONS]))
    copied, copied_core = len(seen) - referenced, core - referenced_core
    summary = "%d rules match Ratchet %s (%d core, %d experimental)." % (copied, version, copied_core, copied - copied_core)
    if referenced:
        summary += (" %d rules are adopted by reference, the weaker mode (%d core, %d experimental): each names a rule of "
                    "Ratchet %s with the sha256 of its rule and ratchet, and the check sees a marker, not the words." % (
                        referenced, referenced_core, referenced - referenced_core, version))
    summary += " %d name a check: %d built, %d text only for now." % (needs, built, needs - built)
    if translated:
        summary += " %d translated." % translated
    if own_status:
        summary += " %d rules of the project's own, %d with a status: %d built, %d text only for now." % (
            len(own), own_status, own_built, own_status - own_built)
    else:
        summary += " %d rules of the project's own." % len(own)
    return problems, summary


def status_problem(name, entry):
    """Why the status and the "where" of a rule that names a check break their form, or None. The rule has a status."""
    if entry["status"] not in STATUSES:
        return 'the status of %s is "%s". It must be "built" or "text only for now"' % (name, entry["status"])
    if not isinstance(entry.get("where", ""), str) or registry.text_problem(entry.get("where", "")):
        return "%s: where %s" % (name, registry.text_problem(entry.get("where", "")))
    if entry["status"] == "built" and not entry.get("where"):
        return "%s is marked built but does not say where the check lives" % name
    return None


def instructions_problem(value, field=INSTRUCTIONS):
    """Why the path of the instruction file, or of the file a row by reference names in stands_in, breaks its form, or
    None.

    A path inside the repo, relative to the register: parts of letters, digits, ".", "_" and "-", joined by single "/",
    none of them "." or "..", none starting with "-", ending in ".md", at most PATH_LENGTH characters. So the block is
    put into a Markdown file of the project's own and nowhere else, and no part of the path reads as an option to the
    rm and mv of the printed commands (review of ef5cbaa).
    """
    form = ("%s must be the path of a Markdown file in the repo, relative to register.json, such as AGENTS.md: "
            "parts of letters, digits, '.', '_' and '-' joined by '/', none of them '.' or '..' and none starting with '-', "
            "ending in .md" % field)
    if not isinstance(value, str) or len(value) > PATH_LENGTH or not value.endswith(".md"):
        return form
    if any(not PATH_PART.match(part) or part in (".", "..") or part.startswith("-") for part in value.split("/")):
        return form
    return None


def is_reference(entry):
    """Whether an adopted row is meant to be adopted by reference: it has stands_in or sha256."""
    return STANDS_IN in entry or SHA in entry


def references(register):
    """The rows of a register that passes check() that are adopted by reference, in order."""
    return [entry for entry in register["adopted"] if is_reference(entry)]


def protection(register):
    """The last word of the label of a row by reference: "built" when the register adopts ratchet.owner-paths with the
    status "built", else "not built". It reads the register's own claim, not the host (D-2026-11-22-second-redraw)."""
    built = any(entry.get("key") == OWNER_PATHS and entry.get("status") == "built" for entry in register["adopted"])
    return "built" if built else "not built"


def label(register):
    """The label of every row by reference in this register, word for word as the decision has it."""
    return LABEL % protection(register)


def reference_sha256(rule):
    """The sha256 that a row by reference names: of the UTF-8 bytes of the rule, one line feed, and the ratchet, in
    lowercase hex. Neither holds a line feed, so the two are told apart. A change to either changes it."""
    return hashlib.sha256((rule["rule"] + "\n" + rule["ratchet"]).encode("utf-8")).hexdigest()


def reference_problem(name, entry, register, by_key, version):
    """Why an adopted row that has stands_in or sha256 is not a valid row by reference at this version, or None."""
    text = [field for field in TEXT_FIELDS if field in entry]
    if text:
        return ("%s: a row adopted by reference holds no rule text, and this one has stands_in or sha256 and %s. Copy the row "
                "whole, without stands_in and sha256, or adopt it by reference, without rule, ratchet and source" % (name, " and ".join(text)))
    if TRANSLATION in entry:
        return ("%s: a row adopted by reference has no translation. The project's own wording of it, in the file it names, "
                "is in the language the project chooses" % name)
    missing = [field for field in REFERENCE_FIELDS if field not in entry]
    unknown = sorted(set(entry) - set(REFERENCE_FIELDS) - set(STATUS_FIELDS))
    if missing or unknown:
        return "; ".join(["%s: missing field %r" % (name, field) for field in missing]
                         + ["%s: unknown field %r" % (name, field) for field in unknown])
    if not all(isinstance(value, str) for value in entry.values()):
        return "%s: every field must be a string" % name
    if entry["key"] not in by_key:
        return "%s is not a rule in Ratchet %s" % (name, version)
    if instructions_problem(entry[STANDS_IN], STANDS_IN):
        return "%s: %s" % (name, instructions_problem(entry[STANDS_IN], STANDS_IN))
    if INSTRUCTIONS in register and entry[STANDS_IN].lower() == register[INSTRUCTIONS].lower():
        return ("%s: stands_in names %s, the instruction file, which starts with the generated block. The project's own "
                "wording of a rule by reference stands in another file" % (name, entry[STANDS_IN]))
    if not SHA256.match(entry[SHA]):
        return "%s: sha256 must be 64 characters 0 to 9 and a to f: the sha256 of the rule and its ratchet" % name
    expected = reference_sha256(by_key[name])
    if entry[SHA] != expected:
        return ("%s: the sha256 is %s, and that of the rule and its ratchet in Ratchet %s is %s. The rule or its ratchet is "
                "not the one the project's wording was read against: read the wording in %s again, and when it says what "
                "the rule says, set sha256 to the new one" % (name, entry[SHA], version, expected, entry[STANDS_IN]))
    return None


def rule_sha256(text):
    """The sha256 of a rule's English text, its UTF-8 bytes, in lowercase hex. A translation names it."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def translation_problem(translation, rule, version):
    """Why a translation breaks its form or is not bound to the rule's text at this version, or None."""
    if not isinstance(translation, dict):
        return "translation must be an object with the fields language, text and sha256"
    missing = [field for field in TRANSLATION_FIELDS if field not in translation]
    unknown = sorted(set(translation) - set(TRANSLATION_FIELDS))
    if missing or unknown:
        return "; ".join(["translation: missing field %r" % field for field in missing]
                         + ["translation: unknown field %r" % field for field in unknown])
    if not all(isinstance(value, str) for value in translation.values()):
        return "translation: every field must be a string"
    if not LANGUAGE.match(translation["language"]):
        return ("translation language must be a language code: two or three lowercase letters, and a region of two capitals "
                "after a hyphen if needed, such as sv or pt-BR")
    if registry.text_problem(translation["text"]):
        return "translation text %s" % registry.text_problem(translation["text"])
    if not registry.WORD.search(translation["text"]):
        return "the translation holds no words"
    if not SHA256.match(translation["sha256"]):
        return "translation sha256 must be 64 characters 0 to 9 and a to f: the sha256 of the rule's English text"
    if translation["sha256"] != rule_sha256(rule):
        return ("the translation is bound to sha256 %s, and the rule's text in Ratchet %s has sha256 %s. The rule has changed "
                "since it was translated: translate it again, and set sha256 to the new one" % (translation["sha256"], version, rule_sha256(rule)))
    return None


def sections(register, level):
    """The sections of the rules, each headed at the level given: the rules from Ratchet, their translations if there
    are any, the rules adopted by reference if there are any, where each check stands, and the project's own rules.
    REGISTER.md and the block both hold them. A row by reference stands in a table of its own, with its label and no
    rule text."""
    copied = [entry for entry in register["adopted"] if not is_reference(entry)]
    referenced = references(register)
    rows = [registry.row(entry) for entry in copied]
    translations = [
        "| %s | %s | %s |" % (entry["key"], entry[TRANSLATION]["language"], registry.cell(entry[TRANSLATION]["text"]))
        for entry in register["adopted"] if TRANSLATION in entry
    ]
    stated = [entry for entry in register["adopted"] if "status" in entry]
    own_stated = [entry for entry in register["own"] if "status" in entry]
    stands = [
        "| %s | %s | %s |" % (entry["key"], entry["status"], registry.cell(entry.get("where", "")))
        for entry in stated + own_stated
    ]
    lines = []
    if copied or not referenced:
        lines += [
            level + " Rules from Ratchet", "", ADOPTED % register["ratchet_version"], "",
            registry.TABLE_HEADER, registry.TABLE_RULE] + rows + [""]
    if referenced:
        lines += [level + " Rules adopted by reference", "", REFERENCED % register["ratchet_version"], "",
                  "| Key | Stands in | Mode |", "|---|---|---|"]
        lines += ["| %s | `%s` | %s |" % (entry["key"], entry[STANDS_IN], registry.cell(label(register))) for entry in referenced]
        lines += [""]
    if translations:
        lines += [level + " Translations", "", TRANSLATIONS, "", "| Key | Language | Translation |", "|---|---|---|"]
        lines += translations + [""]
    lines += [
        level + " Where each check stands", "", STANDS + (STANDS_OWN if own_stated else ""), "",
        "| Key | Status | Where the check lives |", "|---|---|---|"] + stands + [
        "", level + " The project's own rules", ""]
    if register["own"]:
        lines += [OWN, "", registry.TABLE_HEADER, registry.TABLE_RULE]
        lines += [registry.row(entry) for entry in register["own"]]
    else:
        lines.append(NO_OWN)
    return lines


def render(register):
    """The one REGISTER.md that a valid register.json generates."""
    lines = ["# Register for %s" % registry.cell(register["project"]), "", INTRO, ""] + sections(register, "##")
    return "\n".join(lines) + "\n"


def render_block(register):
    """The one block, with its two markers, that a valid register.json generates into its instruction file."""
    lines = [BEGIN, "## Rules in force", "", BLOCK_INTRO, ""] + sections(register, "###") + [END]
    return "\n".join(lines) + "\n"


def disguised(line, word):
    """The places in a line that holds characters outside printable ASCII where the word stands in disguise, read in one
    pass. A control character of ASCII counts as one outside it.

    best[j] is, for a part of the line that ends here and stands for the first j characters of the word, the most of
    them that are the word's own, and where that part starts. A word found starts the search again after it.
    """
    none = (-1, 0)
    best, places = [(0, 0)] + [none] * len(word), []
    for at, char in enumerate(line):
        # A control character of ASCII, such as NUL or DEL, shows as nothing, and counts as a character outside ASCII.
        other = char >= "\x80" or char < "\x20" or char == "\x7f"
        step = [(0, at + 1)] + [none] * len(word)
        for j in range(len(word)):
            count, start = best[j] if j else (0, at)
            if count < 0:
                continue
            if not other and char.lower() == word[j] and count + 1 > step[j + 1][0]:
                step[j + 1] = (count + 1, start)
            elif other and count > step[j + 1][0]:
                step[j + 1] = (count, start)
            if other and 0 < j and count > step[j][0]:
                step[j] = (count, start)
        best = step
        if best[len(word)][0] >= SHARE:
            places.append(best[len(word)][1])
            best = [(0, at + 1)] + [none] * len(word)
    return places


def marker_words(text, words=MARKER_WORDS):
    """For each of the marker words, the two of the block by default, where it stands in the text, in any case and in
    disguise (see MARKER_WORDS).

    A line of printable ASCII alone is searched for the word as it is. A line with any other character, a control
    character of ASCII among them, is read by disguised().
    """
    folded = text.translate(FULL_WIDTH)
    found = [[] for _ in words]
    offset = 0
    for line in folded.split("\n"):
        for places, (word, pattern) in zip(found, words):
            if all("\x20" <= char < "\x7f" for char in line):
                places += [offset + match.start() for match in pattern.finditer(line)]
            else:
                places += [offset + start for start in disguised(line, word)]
        offset += len(line) + 1
    return found


def holds_marker_word(text):
    """Whether the text holds either marker word, in any case and in disguise."""
    return any(marker_words(text))


def find_block(text, name):
    """(start, end) of the block with its two markers in the text of an instruction file, or (None, problems).

    The file holds "ratchet:begin" and "ratchet:end" once each, in any case and in disguise, and each stands in its
    exact marker line, alone, ending in LF. The begin marker is the first line of the file, so nothing before it can
    put the block in a code block, a comment or an element that hides it. Nothing else of the file is read.
    """
    found = marker_words(text)
    begins, ends = len(found[0]), len(found[1])
    if begins == ends == 0:
        return None, ["%s: holds no generated block, and register.json names it in instructions. Print the file with the "
                      "block with check_register.py register.json --print-instructions and put it in place" % name]
    if begins != 1 or ends != 1:
        return None, ["%s: the markers of the generated block are broken: ratchet:begin stands %d times and ratchet:end %d "
                      "times. Each stands once, in its own line %s or %s" % (name, begins, ends, BEGIN, END)]
    places = []
    for (word, _), marker, at in zip(MARKER_WORDS, (BEGIN, END), (found[0][0], found[1][0])):
        start = text.rfind("\n", 0, at) + 1
        stop = text.find("\n", at)
        line = text[start:] if stop < 0 else text[start:stop + 1]
        if line != marker + "\n":
            return None, ["%s: the line that holds %s must be exactly %s, alone on its line and ending in LF, found %r"
                          % (name, word, marker, line)]
        places.append((start, start + len(line)))
    if places[1][0] < places[0][0]:
        return None, ["%s: the line %s stands before %s" % (name, END, BEGIN)]
    if places[0][0] != 0:
        return None, ["%s: the block must stand at the start of the file, its line %s the first, and it starts at line %d. "
                      "Nothing may stand before it, so that no text can put it in a code block, a comment or an element "
                      "that hides it. Move it there by hand" % (name, BEGIN, text.count("\n", 0, places[0][0]) + 1)]
    return (places[0][0], places[1][1]), []


def block_problems(name, data, register):
    """Every problem with the block in the bytes of an instruction file, or nothing."""
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        return ["%s: %s. Every file a check reads is UTF-8" % (name, registry.not_utf8(error))]
    place, problems = find_block(text, name)
    if problems:
        return problems
    found, expected = text[place[0]:place[1]], render_block(register)
    if found == expected:
        return []
    have, want = found.split("\n"), expected.split("\n")
    line = next((n for n, (a, b) in enumerate(zip(have, want), 1) if a != b), min(len(have), len(want)) + 1)
    def show(lines):
        each = lines[line - 1] if line <= len(lines) else "(the block ends)"
        return repr(each if len(each) <= 100 else each[:97] + "...")
    return ["%s: the block between the markers is not what register.json generates. It is generated: change register.json "
            "and print the file again with --print-instructions, never by hand. First difference at line %d of the file\n  expected: %s\n  found:    %s"
            % (name, text.count("\n", 0, place[0]) + line, show(want), show(have))]


def marker_problems(name, data, keys):
    """Every problem with the marker lines in the bytes of a file that rows by reference name, for the keys of those
    rows, or nothing.

    The word "ratchet:rule" is found wherever it stands, in any case and in disguise, as the words of the block are.
    Each line that holds it must be exactly "<!-- ratchet:rule <key> -->", alone on its line and ending in LF. When
    every such line is exact, the marker of each key given stands once, and no marker names a key that no row names
    this file for. Nothing else in the file is read.
    """
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        return ["%s: %s. Every file a check reads is UTF-8" % (name, registry.not_utf8(error))]
    problems, counts, lines = [], {}, set()
    for at in marker_words(text, RULE_WORD)[0]:
        start = text.rfind("\n", 0, at) + 1
        if start in lines:
            continue
        lines.add(start)
        stop = text.find("\n", at)
        line = text[start:] if stop < 0 else text[start:stop + 1]
        match = MARKER_LINE.match(line[:-1]) if line.endswith("\n") else None
        if match is None:
            problems.append("%s: the line that holds ratchet:rule, line %d, must be exactly %s, alone on its line and ending "
                            "in LF, found %r" % (name, text.count("\n", 0, start) + 1, MARKER % "<key>", line))
        else:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    if problems:
        return problems
    for key in keys:
        if key not in counts:
            problems.append("%s: holds no marker for %s, and register.json names it in stands_in for that rule. Put the line "
                            "%s where the project's own wording of the rule stands" % (name, key, MARKER % key))
        elif counts[key] != 1:
            problems.append("%s: the marker %s stands %d times. It stands once" % (name, MARKER % key, counts[key]))
    for key in sorted(set(counts) - set(keys)):
        problems.append("%s: holds the marker %s, and no row adopted by reference names this file for %s. Take the line "
                        "out, or adopt the rule by reference here" % (name, MARKER % key, key))
    return problems


def reference_files(register_path, register):
    """(every problem with the files that the rows by reference of a register that passes check() name, the paths
    read). Each file is checked on its path as the instruction file is, and read without following a link."""
    files = {}
    for entry in references(register):
        files.setdefault(entry[STANDS_IN], []).append(entry["key"])
    problems, read = [], []
    for value, keys in files.items():
        path, found = file_place(register_path, value, STANDS_IN)
        if found:
            problems += found
            continue
        if not os.path.isfile(path):
            problems.append("%s: the file is missing. register.json names it in stands_in for %s" % (path, ", ".join(keys)))
            continue
        try:
            data = registry.read_plain(path)
        except OSError as error:
            problems.append("%s: cannot be read as a plain file: %s" % (path, error.strerror))
            continue
        found = marker_problems(path, data, keys)
        problems += found
        if not found:
            read.append((path, keys))
    return problems, read


def with_block(text, register, name):
    """(the text of the instruction file with the block brought up to date, or None, problems).

    The block goes between the markers, or, in a file with no marker, at its start, followed by an empty line. No
    other character of the file changes. Where the markers are broken or the block is not at the start, there is no
    such text.
    """
    if text and not holds_marker_word(text):
        return render_block(register) + "\n" + text, []
    if not text:
        return render_block(register), []
    place, problems = find_block(text, name)
    if problems:
        return None, problems
    return text[:place[0]] + render_block(register) + text[place[1]:], []


def instruction_place(register_path, register):
    """(the path of the instruction file, or None, problems), before anything is read or written there.

    The path has the form instructions_problem allows: relative, no "." or "..", no empty part. Each part of it, from
    the directory of the register down, is not a symbolic link, each part before the last is a directory, and the
    file, resolved, stays inside that directory. So the file is read only inside the repo (round 2 of #100). The last
    part may be missing: --print-instructions then prints the block alone.
    """
    return file_place(register_path, register[INSTRUCTIONS], INSTRUCTIONS)


# How each field that names a file says what is done with it, when a part of its path is a link or a directory missing.
READ_AS = {
    INSTRUCTIONS: ("The instruction file is read and written only as a plain file in the repo",
                   "and the block is neither read nor written there"),
    STANDS_IN: ("The file a row by reference names is read only as a plain file in the repo",
                "and its marker is not read there"),
}


def file_place(register_path, value, field):
    """(the path of the file that value names in field, instructions or stands_in, or None, problems), as
    instruction_place says, before anything is read there."""
    root = os.path.dirname(register_path)
    if instructions_problem(value, field):
        return None, [instructions_problem(value, field)]
    plain, neither = READ_AS[field]
    parts = value.split("/")
    path = root
    for number, part in enumerate(parts, 1):
        path = os.path.join(path, part)
        shown = os.path.join(root, *parts[:number])
        if os.path.islink(path):
            return None, ["%s is a symbolic link. %s, and no part of its path may be a link" % (shown, plain)]
        if number < len(parts) and not os.path.isdir(path):
            return None, ["%s is missing or is not a directory. register.json names %s in %s, %s" % (shown, value, field, neither)]
    if os.path.exists(path) and not os.path.isfile(path):
        return None, ["%s: it is not a plain file" % path]
    inside = os.path.realpath(root or ".")
    if os.path.commonpath([inside, os.path.realpath(path)]) != inside:
        return None, ["%s resolves to a place outside the directory of register.json" % path]
    return path, []


def instruction_text(path, register):
    """(the instruction file at path, which instruction_place gave, with the block brought up to date, or None, problems).
    The file is read without following a link, and a file that is missing is read as empty."""
    try:
        data = registry.read_plain(path) or b""
    except OSError as error:
        return None, ["%s: the file is not printed: %s" % (path, error.strerror or error)]
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        return None, ["%s: the file is not printed: it %s. Every file a check reads is UTF-8" % (path, registry.not_utf8(error))]
    new, problems = with_block(text, register, path)
    if problems:
        return None, ["%s: the file is not printed, since the markers are broken. Mend them by hand first" % path] + problems
    return new, []


def generated_problems(register_path, register, markdown=None, planned=None):
    """(every problem with the files a register that passes check() generates, the path of the instruction file or None).

    The files are REGISTER.md at the path markdown, when it is given, and the instruction file that the register names in
    instructions. planned maps a path, relative as the paths given here are, to the bytes that a run would write there
    and that are not there yet: init.py --check passes what it would write, so that it reaches the same verdict as this
    check at the end of a real run (review of d86ff3e). Every other file is read from the disk.
    """
    planned = {os.path.normpath(path): data for path, data in (planned or {}).items()}
    problems = reference_files(register_path, register)[0]
    if markdown:
        try:
            if os.path.normpath(markdown) in planned:
                current = planned[os.path.normpath(markdown)].decode("utf-8", errors="strict").replace("\r\n", "\n")
            else:
                current = registry.read(markdown)
            # REGISTER.md is optional for a register with rows by reference (D-2026-11-22-second-redraw). Where it is
            # there, it is what the register generates.
            absent = os.path.normpath(markdown) not in planned and not os.path.lexists(markdown)
            if not (absent and references(register)):
                problems += registry.compare(markdown, current, render(register), os.path.basename(register_path))
        except registry.RegistryError as error:
            problems.append(str(error))
    block, found = instruction_place(register_path, register) if INSTRUCTIONS in register else (None, [])
    problems += found
    if block is None:
        return problems, None
    if os.path.normpath(block) in planned:
        return problems + block_problems(block, planned[os.path.normpath(block)], register), block
    if not os.path.isfile(block):
        problems.append("%s: the file is missing. register.json names it in instructions. Print it with the block with "
                        "check_register.py register.json --print-instructions and put it in place" % block)
        return problems, block
    try:
        data = registry.read_plain(block)
    except OSError as error:
        problems.append("%s: cannot be read as a plain file: %s" % (block, error.strerror))
        return problems, block
    return problems + block_problems(block, data, register), block


def printed(args, register, problems):
    """Print the one file a print mode asks for to standard output, and nothing else, or, if there is a problem, nothing
    there and the problems to standard error. The exit code."""
    text = None
    if not problems and args.print_markdown:
        text = render(register)
    elif not problems and INSTRUCTIONS not in register:
        problems.append("%s: register.json names no instruction file in instructions, so there is no file to print" % args.register)
    elif not problems:
        place, problems = instruction_place(args.register, register)
        if place is not None:
            text, problems = instruction_text(place, register)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print("FAIL: %d problem(s). Nothing was printed" % len(problems), file=sys.stderr)
        return 1
    sys.stdout.flush()
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a project's register.json against Ratchet. It writes nothing.")
    parser.add_argument("register", help="path to the project's register.json")
    parser.add_argument("--markdown", metavar="REGISTER.md", help="also fail unless this file is what the register generates")
    parser.add_argument("--agents", metavar="AGENTS.md", help="also fail while this file holds a placeholder of templates/AGENTS.md")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--print-markdown", action="store_true",
                       help="print REGISTER.md as the register generates it, and nothing else")
    group.add_argument("--print-instructions", action="store_true",
                       help="print the instruction file that the register names, with the block brought up to date, and nothing else")
    parser.add_argument("--source", default=registry.SOURCE, help="path to ratchet.json (default: the one next to this check)")
    args = parser.parse_args(argv)
    printing = args.print_markdown or args.print_instructions
    if printing and (args.markdown or args.agents):
        parser.error("--print-markdown and --print-instructions print one file, and take neither --markdown nor --agents")
    for path in [args.register] + [path for path in (args.markdown, args.agents) if path]:
        problem = registry.link_problem(path)
        if problem:
            print("check_register: cannot run: %s" % problem, file=sys.stderr)
            return 2
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
        register, problems, summary = None, [str(error)], None
    else:
        problems, summary = check(register, ratchet)
    problems = ["%s: %s" % (args.register, problem) for problem in problems]
    if printing:
        return printed(args, register, problems)
    block = None
    if not problems:
        found, block = generated_problems(args.register, register, args.markdown)
        problems += found
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
    for entry in references(register):
        print("%s: %s stands in %s. %s" % (args.register, entry["key"], entry[STANDS_IN], label(register)))
    for path, keys in reference_files(args.register, register)[1]:
        print("%s: holds the marker line of %s once each, and nothing else in it is read" % (path, ", ".join(keys)))
    if args.markdown and references(register) and not os.path.lexists(args.markdown):
        print("%s: not there, which a register with rows adopted by reference may leave out" % args.markdown)
    if block is not None:
        print("%s: the block between the markers is what register.json generates" % block)
    if args.agents:
        print("%s: holds no placeholder of templates/AGENTS.md" % args.agents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
