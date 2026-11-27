"""The decision files in decisions/: their form, and the status line that generate.py writes into each one that a later
decision replaces, amends or ends (D-2026-11-27-stale-text, point 2).

generate.py calls expected(root). It returns ({path: (current text, expected text)}, problems), as its own
expected_files does, and generate.py --check fails on each problem and on each file whose text is not the expected text.

The one form of the top of a decision file, line by line:

    # D-YYYY-MM-DD-<slug>: <title>
    <empty line>
    <!-- generated:status -->                     only when a later decision names this one,
    Status: <part>; <part>                         and then all four lines, exactly here
    <!-- /generated:status -->
    <empty line>
    - Date: YYYY-MM-DD                             the date of the id
    - Decided by: <text>
    - Kind: decision (D)
    - Replaces: none | <id>; <id>                  these three, in this order, on every decision dated
    - Amends: none | <id> (<what>); <id> (<what>)  CUT_OVER or later; an older one has all three or none
    - Ends: none | <id>; <id>
    <empty line>

The rest of the file is never read but for two lines, "## Question" and then "## Answer", each once, and is never
written. The ids in one field are each named once, in the order of their text, and one decision names another in one
field only. <what> is one to 15 words of text from the fixed list, with no "(", ")", ";", "<" or ">". A named id is a
decision in decisions/, not the file itself, and not dated after it. Two decisions of the same day may name each other's
way, so the date does not order them: a cycle of names is refused instead.

A part of the status line is "replaced by <id>", "amended by <id> (<what>)" or "ended by <id>", one for each field of a
later decision that names this one, ordered by that decision's id and then in the order of the fields. generate.py
writes the block, removes it from a decision that no other one names, and changes no other byte of the file.

The entries of decisions/ are refused, each by its name, when one is not a plain file, is a link, or is not named
D-YYYY-MM-DD-<slug>.md with a date that exists. A root with no decisions/ has no decisions.

Standard library only.
"""

import datetime
import os
import re

import registry

FOLDER = "decisions"
# The first date on which a decision must name what it replaces, amends or ends: the day after the pull request that
# built this check, so that every decision filed after it has the three fields, and none filed before it needs them.
CUT_OVER = datetime.date(2026, 11, 28)
START = "<!-- generated:status -->"
END = "<!-- /generated:status -->"
MARK = "generated:status"
TITLE = re.compile(r"# (D-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9]+(?:-[a-z0-9]+)*): (\S.*)\Z")
FIELD = re.compile(r"- ([A-Z][a-z]*(?: [a-z]+)*): (.*)\Z")
FIELDS = ("Date", "Decided by", "Kind")
RELATIONS = ("Replaces", "Amends", "Ends")
KIND = "decision (D)"
WORDS = {"Replaces": "replaced by", "Amends": "amended by", "Ends": "ended by"}
NOTE_WORDS = 15
NOTE = re.compile(r"(D-[^ ()]*) \(([^()]*)\)\Z")
NOT_IN_NOTE = "();<>"
QUESTION = "## Question"
ANSWER = "## Answer"


def entry_problems(folder):
    """Each entry of decisions/ that is not a plain file, is a link, or is not named D-YYYY-MM-DD-<slug>.md with a date
    that exists, as (name, problem), sorted."""
    problems = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if (os.path.islink(path) or not os.path.isfile(path) or not name.endswith(".md")
                or registry.decision_date(name[:-3]) is None):
            problems.append((name, "decisions/%s: every entry here is a plain file named D-YYYY-MM-DD-<slug>.md, with a "
                                   "date that exists" % name))
    return problems


def relation_items(field, value):
    """The (id, note) pairs of one relation field's value, or a problem. The note is None but in Amends."""
    if value == "none":
        return [], None
    items = []
    for part in value.split("; "):
        if field == "Amends":
            match = NOTE.match(part)
            if not match:
                return None, 'each item of Amends is "<id> (<what>)", the items separated by "; ", or the field is "none"'
            ident, note = match.group(1), match.group(2)
            words = note.split(" ")
            if (registry.text_problem(note) is not None or any(character in note for character in NOT_IN_NOTE)
                    or "" in words or len(words) > NOTE_WORDS):
                return None, ("what %s amends is one to %d words of text, with no %s"
                              % (ident, NOTE_WORDS, ", ".join('"%s"' % c for c in NOT_IN_NOTE)))
        else:
            ident, note = part, None
        if registry.decision_date(ident) is None:
            return None, "%s names %r, which is not the id of a decision with a date that exists" % (field, ident)
        items.append((ident, note))
    idents = [ident for ident, _ in items]
    if idents != sorted(set(idents)):
        return None, "%s names each decision once, in the order of their ids" % field
    return items, None


def parse(ident, text):
    """(record, problems) for one decision file. The record is None when the file breaks its form."""
    name = "decisions/%s.md" % ident
    problems = []
    lines = text.split("\n")
    match = TITLE.match(lines[0])
    if not match:
        return None, ["%s: the first line is \"# <id>: <title>\"" % name]
    if match.group(1) != ident:
        return None, ["%s: the title names %s, and the file is named for %s" % (name, match.group(1), ident)]
    if len(lines) < 3 or lines[1] != "":
        return None, ["%s: an empty line follows the title" % name]
    start = 2
    block = None
    if lines[2] == START:
        # The line between the markers is generated text: whatever it holds, it is compared with what is generated.
        if len(lines) < 6 or lines[4] != END or lines[5] != "":
            return None, ["%s: the status block is the line %s, one line of status, the line %s and an empty line"
                          % (name, START, END)]
        block, start = lines[3], 6
    if text.count(MARK) != (2 if block is not None else 0):
        return None, ["%s: a status block stands only just under the title, once" % name]
    fields, names = {}, []
    end = start
    while end < len(lines) and lines[end] != "":
        found = FIELD.match(lines[end])
        if not found:
            return None, ["%s: line %d: each line of the header is \"- <Field>: <value>\"" % (name, end + 1)]
        names.append(found.group(1))
        fields[found.group(1)] = found.group(2)
        end += 1
    if end >= len(lines):
        return None, ["%s: an empty line follows the header" % name]
    for field in sorted(set(names)):
        if field not in FIELDS + RELATIONS:
            problems.append("%s: the field %s is not one a decision has" % (name, field))
        elif names.count(field) > 1:
            problems.append("%s: the field %s stands more than once" % (name, field))
    date = registry.decision_date(ident)
    if not problems and date >= CUT_OVER and tuple(names) == FIELDS:
        problems.append("%s: a decision dated %s or later says what it replaces, amends and ends, each \"none\" or the ids"
                        % (name, CUT_OVER.isoformat()))
    elif not problems and tuple(names) not in (FIELDS, FIELDS + RELATIONS):
        problems.append("%s: the header holds %s, in this order%s" % (
            name, ", ".join(FIELDS + RELATIONS), "" if date >= CUT_OVER else ", or the first three alone"))
    if problems:
        return None, problems
    if fields["Date"] != date.isoformat():
        problems.append("%s: Date is %s, and the id's date is %s" % (name, fields["Date"], date.isoformat()))
    if fields["Decided by"] == "" or registry.text_problem(fields["Decided by"]) is not None:
        problems.append("%s: Decided by names who decided, as text" % name)
    if fields["Kind"] != KIND:
        problems.append("%s: Kind is %s" % (name, KIND))
    relations = {}
    for field in RELATIONS:
        items, problem = relation_items(field, fields.get(field, "none"))
        if problem:
            problems.append("%s: %s" % (name, problem))
        relations[field] = items or []
    named = [ident for items in relations.values() for ident, _ in items]
    for other in sorted(set(named)):
        if named.count(other) > 1:
            problems.append("%s: names %s in more than one field" % (name, other))
    body = lines[end:]
    if body.count(QUESTION) != 1 or body.count(ANSWER) != 1 or body.index(QUESTION) > body.index(ANSWER):
        problems.append("%s: the lines %s and %s stand once each, in that order" % (name, QUESTION, ANSWER))
    if problems:
        return None, problems
    head = "\n".join(lines[start:])
    return {"id": ident, "date": date, "title": lines[0], "block": block, "head": head, "relations": relations}, []


def status_lines(records):
    """{id: the status line} for each decision that a later one names."""
    parts = {}
    for ident in sorted(records):
        for field in RELATIONS:
            for other, note in records[ident]["relations"][field]:
                part = "%s %s" % (WORDS[field], ident) + (" (%s)" % note if note is not None else "")
                parts.setdefault(other, []).append(part)
    return dict((ident, "Status: " + "; ".join(items)) for ident, items in parts.items())


def cycles(records):
    """Each cycle of names among the decisions, as a list of ids starting from its smallest, sorted."""
    edges = dict((ident, sorted(set(other for items in record["relations"].values() for other, _ in items
                                    if other in records and other != ident)))
                 for ident, record in records.items())
    found = set()

    def walk(path):
        for other in edges[path[-1]]:
            if other == path[0]:
                low = path.index(min(path))
                found.add(tuple(path[low:] + path[:low]))
            elif other not in path and other > path[0]:
                walk(path + [other])

    for ident in sorted(edges):
        walk([ident])
    return sorted(list(cycle) for cycle in found)


def expected(root):
    """({path: (current text, expected text)}, problems) for decisions/ under root."""
    folder = os.path.join(root, FOLDER)
    if not os.path.isdir(folder) or os.path.islink(folder):
        return {}, []
    entries = entry_problems(folder)
    problems = [problem for _, problem in entries]
    bad = set(name for name, _ in entries)
    texts, records = {}, {}
    for name in sorted(os.listdir(folder)):
        if name in bad:
            continue
        ident = name[:-3]
        path = os.path.join(folder, name)
        text = registry.read(path)
        texts[ident] = (path, text)
        record, found = parse(ident, text)
        problems += found
        if record is not None:
            records[ident] = record
    known = set(texts)
    before = len(problems)
    for ident in sorted(records):
        for field in RELATIONS:
            for other, _ in records[ident]["relations"][field]:
                if other == ident:
                    problems.append("decisions/%s.md: %s names the decision itself" % (ident, field))
                elif other not in known:
                    problems.append("decisions/%s.md: %s names %s, which has no file in decisions/" % (ident, field, other))
                elif registry.decision_date(other) > records[ident]["date"]:
                    problems.append("decisions/%s.md: %s names %s, which is dated after it" % (ident, field, other))
    for cycle in cycles(records):
        problems.append("decisions/: these decisions name each other in a cycle: %s" % " -> ".join(cycle + cycle[:1]))
    if len(problems) > before:
        # A name that is wrong gives no status to write, so no decision file is written until the names are right.
        return {}, problems
    lines = status_lines(records)
    result = {}
    for ident, record in sorted(records.items()):
        path, current = texts[ident]
        block = "%s\n%s\n%s\n\n" % (START, lines[ident], END) if ident in lines else ""
        result[path] = (current, record["title"] + "\n\n" + block + record["head"])
    for ident in sorted(set(lines) - set(records)):
        if ident in texts:
            problems.append("decisions/%s.md: a later decision names it, and its status cannot be written until its form "
                            "is right" % ident)
    return result, problems
