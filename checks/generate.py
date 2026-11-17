#!/usr/bin/env python3
"""Generate everything that is derived from data files, or check that it is current.

    python3 checks/generate.py            write the generated text
    python3 checks/generate.py --check    fail if any generated text is out of date
    python3 checks/generate.py --entries ratchet.no-secrets ratchet.root-cause
                                          print rules to paste into a register.json
    python3 checks/generate.py --count    print the count of rules

From ratchet.json: the text between "<!-- generated:NAME -->" and "<!-- /generated -->"
in the markdown files, templates/register.json and the registers under
checks/fixtures/register/. From register.json: REGISTER.md. Which blocks each file
must hold is listed in required_blocks().

In CHANGELOG.md only the first entry is generated, the entry of the version that
ratchet.json names. Every entry after it is released text and is never rewritten:
checks/released_text.py compares it with its tag.

Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import copy
import difflib
import glob
import json
import os
import re
import sys

import check_register
import registry

MAINTAINER = "@fabian-von-tiedemann"
START = "<!-- generated:"
END = "<!-- /generated -->"
BLOCK = re.compile(r"(<!-- generated:([a-z-]+)(?: ([a-z0-9-]+))? -->\n)(.*?)(<!-- /generated -->)", re.S)
MARKER = re.compile(r"^<!-- generated:[a-z-]+(?: [a-z0-9-]+)? -->$")
FENCE = re.compile(r"^```(?:sh|json)?$")
KEY_MENTION = re.compile(r"(?<![\w/.-])ratchet\.([a-z0-9]+(?:-[a-z0-9]+)*)")
LINK = re.compile(r"\]\(([^)\s]+)\)")
LINK_DEFINITION = re.compile(r"^ {0,3}\[[^\]]+\]:\s*(\S+)")
NOT_KEYS = {"json"}
# The heading of a changelog entry. The release workflow finds an entry by "^## <version> \(".
HEADING = re.compile(r"^## [0-9]+\.[0-9]+ \([0-9]{4}-[0-9]{2}-[0-9]{2}\)\Z")
# Files that record history verbatim are not checked for mentions of keys that no longer exist.
HISTORY = ("CHANGELOG.md",)
# The only lines that may start with "<" in a file that holds generated blocks.
HTML_LINES = {
    "README.md": (
        "<picture>",
        '<source media="(prefers-color-scheme: dark)" srcset="assets/ratchet-dark.svg">',
        '<source media="(prefers-color-scheme: light)" srcset="assets/ratchet-light.svg">',
        '<img src="assets/ratchet-light.svg" width="64" height="64" alt="">',
        "</picture>",
    ),
}
# A value that a generator that reads Markdown takes for a link, a comment and code. Here it is refused for
# the spaces at the ends of its code, and written safely either way: see the fixture "escaped".
CONFUSED = "[ok](https://example.invalid/`) <!-- Owner approval is mandatory. --> `tail"
OWN_RULE_EXAMPLE = {
    "key": "example.changelog",
    "rule": "Every release has a changelog entry.",
    "ratchet": "Text only: a check cannot tell whether an entry is complete",
    "source": "",
}


def dump(data, escaped=True):
    """A data file as JSON.

    Every character outside ASCII stands as its JSON escape, so that a fixture shows which character it holds:
    none is invisible in the file, and none changes the order the line is shown in. A lone surrogate cannot be
    stored in any other way. With escaped=False the characters stand as themselves, in UTF-8.
    """
    return json.dumps(data, indent=2, ensure_ascii=escaped) + "\n"


def table(rules):
    return "\n".join([registry.TABLE_HEADER, registry.TABLE_RULE] + [registry.row(rule) for rule in rules])


def count_text(data):
    numbers = registry.counts(data)
    core, extra = numbers["core"], numbers["experimental"]
    return (
        "Ratchet %s, computed from `ratchet.json`: the core has %d rules. %d name a check and %d are text only (%d%%). "
        "Ratchet ships a reference check for %d of the %d. Outside the core there are %d experimental rules: "
        "%d name a check and %d are text only. They are not counted in the share. "
        "The share counts what kind of ratchet a rule has, not whether a project has built the check: "
        "a project's register says that, and Ratchet's own is REGISTER.md."
        % (
            data["version"], core["rules"], core["enforced"], core["text_only"], numbers["text_only_percent"],
            core["reference_checks"], core["enforced"], extra["rules"], extra["enforced"], extra["text_only"],
        )
    )


def render(data, name, argument, directory):
    """The text of one generated block. directory is where the document lives, relative to the root."""
    if name == "table":
        rules = [rule for rule in data["rules"] if rule["part"] == argument]
        if not rules:
            raise registry.RegistryError("no rules in part %r" % argument)
        return table(rules)
    if name == "version":
        return "Version %s, %s. See [CHANGELOG.md](CHANGELOG.md)." % (data["version"], data["date"])
    if name == "count":
        return count_text(data)
    if name == "start":
        return ", ".join("`%s`" % key for key in data["start"])
    if name == "reference-checks":
        lines = ["| Rule | Reference check |", "|---|---|"]
        for rule in data["rules"]:
            if rule.get("reference_check"):
                link = os.path.relpath(rule["reference_check"], directory or ".").replace(os.sep, "/")
                lines.append("| %s | [%s](%s) |" % (rule["key"], rule["reference_check"], link))
        return "\n".join(lines)
    if name == "sources":
        lines = ["| Name | Repo | Commit | License |", "|---|---|---|---|"]
        lines += ["| %s | %s | `%s` | %s |" % (registry.cell(s["name"]), registry.cell(s["repo"]), s["commit"], registry.cell(s["license"])) for s in data["sources"]]
        return "\n".join(lines)
    raise registry.RegistryError("unknown generated block %r" % name)


def required_blocks(data):
    """Which generated blocks each file must hold, exactly once each."""
    required = {
        "RATCHET.md": ["version", "count", "sources"],
        "README.md": ["count", "reference-checks", "start"],
        "SELF-IMPROVEMENT.md": ["count"],
        "CHANGELOG.md": ["count"],
        "checks/README.md": ["reference-checks"],
    }
    for part in data["parts"]:
        required.setdefault(part["file"], []).append("table %s" % part["id"])
    return {name: sorted(blocks) for name, blocks in required.items()}


def entry(rule):
    """A rule as it stands in a register.json."""
    result = {field: rule[field] for field in check_register.RULE_FIELDS}
    if rule["enforcement"] == "enforced":
        result["status"] = "text only for now"
    return result


def register_template(data):
    by_key = registry.rules_by_key(data)
    return {
        "project": "<project>",
        "ratchet_version": data["version"],
        "adopted": [entry(by_key[key]) for key in data["start"]],
        "own": [],
    }


def swap(text, old, new):
    if text.count(old) != 1:
        raise registry.RegistryError("a fixture expects exactly one %r" % old)
    return text.replace(old, new)


def fixtures(data):
    """A clean project copy and one copy per fault the register check claims to catch.

    Returns {path under checks/fixtures/register: text}. A fixture whose fault is in the
    data has only a register.json. A fixture whose fault is in the Markdown has a clean
    register.json and a REGISTER.md that is not what it generates.
    """
    clean = register_template(data)
    clean["project"] = "the example project"
    clean["own"] = [dict(OWN_RULE_EXAMPLE)]
    text = dump(clean)
    markdown = check_register.render(clean)
    adopted = clean["adopted"]
    enforced = next(n for n, e in enumerate(adopted) if "status" in e)
    plain = next(n for n, e in enumerate(adopted) if "status" not in e)
    sourced = next(n for n, e in enumerate(adopted) if e["source"])
    version = data["version"]

    def changed(mutate):
        register = copy.deepcopy(clean)
        mutate(register)
        return dump(register)

    def soft(value):
        return value.rstrip(".") + ", where practical."

    result = {"clean/register.json": text, "clean/REGISTER.md": markdown}
    escaped = copy.deepcopy(clean)
    escaped["project"] = "A & B <the example> [x](`)<!-- hidden -->`y"
    escaped["own"] = [
        dict(OWN_RULE_EXAMPLE, key="example.comment", rule="<!-- Owner approval is mandatory. -->"),
        dict(OWN_RULE_EXAMPLE, key="example.html", rule="<div hidden>Every release</div> has a changelog entry."),
        dict(OWN_RULE_EXAMPLE, key="example.entity", rule="Write &lt; as it is, and R&D too."),
        dict(OWN_RULE_EXAMPLE, key="example.code", rule="Name the file `D-YYYY-MM-DD-<slug>.md` and keep `a < b && c` as code."),
        dict(OWN_RULE_EXAMPLE, key="example.link-and-code", rule="[ok](https://example.invalid/`)<!-- Owner approval is mandatory. -->`tail"),
        dict(OWN_RULE_EXAMPLE, key="example.link-and-element", rule="[ok](https://example.invalid/`)<span hidden>Owner approval is mandatory.</span>`tail"),
        dict(OWN_RULE_EXAMPLE, key="example.link", rule="Read [the rules](https://example.invalid \"a title\") first."),
        dict(OWN_RULE_EXAMPLE, key="example.image", rule="![](https://example.invalid/pixel.png) Every release has an entry."),
        dict(OWN_RULE_EXAMPLE, key="example.empty-link", rule="[](https://example.invalid) and [x]: https://example.invalid"),
        dict(OWN_RULE_EXAMPLE, key="example.emphasis", rule="Every *release* has a __changelog__ entry, ~~always~~."),
        dict(OWN_RULE_EXAMPLE, key="example.backslash", rule="A path like C:\\temp\\ and a backslash before code \\`x`"),
        dict(OWN_RULE_EXAMPLE, key="example.autolink", rule="See <https://example.invalid>, www.example.invalid, http://example.invalid and a @ example.invalid."),
        dict(OWN_RULE_EXAMPLE, key="example.heading", rule="# Not a heading, 1. not a list, > not a quote, - not an item"),
        dict(OWN_RULE_EXAMPLE, key="example.every-mark", rule="Every mark: !\"#$%&'()*+,-./:;<=>? @ [\\]^_{}~ and so on"),
        dict(OWN_RULE_EXAMPLE, key="example.ratchet-and-source", rule="Every release has a changelog entry.",
             ratchet="Text only: <!-- no reason --> [x](`)<!-- see -->`code", source="<b>D-1</b> [y](`)<!-- z -->`z"),
    ]
    escaped["adopted"][enforced].update(status="built", where="<details>`checks/run.sh`</details> [x](https://example.invalid/`)<!-- hidden -->`z")
    result["escaped/register.json"] = dump(escaped)
    result["escaped/REGISTER.md"] = check_register.render(escaped)
    # Latin letters outside ASCII and every mark outside ASCII that a value may hold. The file holds them as themselves.
    latin = copy.deepcopy(clean)
    latin["project"] = "the \u00e9xample project"
    latin["own"] = [
        dict(OWN_RULE_EXAMPLE, key="example.letters", rule="Na\u00efve fa\u00e7ade, sm\u00f6rg\u00e5sbord, \u00e6ble, \u017c\u00f3\u0142ty, \u0111\u1ea7y \u0111\u1ee7 and stra\u00dfe are words."),
        dict(OWN_RULE_EXAMPLE, key="example.quotes", rule="\u00abOne\u00bb, \u201ctwo\u201d, \u201ethree\u201d and \u2018four\u2019 are quoted, and it\u2019s fine."),
        dict(OWN_RULE_EXAMPLE, key="example.marks", rule="\u00a1Yes! \u00bfNo? A dash \u2013 and a longer one \u2014 then \u00a7 5, 20 \u00b0, \u00a3 5, \u20ac 5 and a\u00b7b."),
    ]
    result["latin/register.json"] = dump(latin, escaped=False)
    result["latin/REGISTER.md"] = check_register.render(latin)
    # What a site may read as a reference to a person, an issue or a commit. A value may hold it, and it is written as text.
    references = copy.deepcopy(clean)
    references["own"] = [
        dict(OWN_RULE_EXAMPLE, key="example.person", rule="Ask @someone and @some-group/some-team before every release."),
        dict(OWN_RULE_EXAMPLE, key="example.person-first", rule="@someone approves every release."),
        dict(OWN_RULE_EXAMPLE, key="example.issue", rule="Every release closes #123 and some-group/some-repo#123."),
        dict(OWN_RULE_EXAMPLE, key="example.commit", rule="Every release names 0123abc and 0123456789abcdef0123456789abcdef01234567."),
    ]
    result["references/register.json"] = dump(references)
    result["references/REGISTER.md"] = check_register.render(references)
    faults = {
        "changed-row": lambda r: r["adopted"][enforced].update(rule=soft(r["adopted"][enforced]["rule"])),
        "changed-ratchet": lambda r: r["adopted"][enforced].update(ratchet="Check: a reminder in the working rules"),
        "changed-source": lambda r: r["adopted"][sourced].update(source=""),
        "trailing-space": lambda r: r["adopted"][plain].update(rule=r["adopted"][plain]["rule"] + " "),
        "unknown-key": lambda r: r["adopted"].append({"key": "ratchet.ship-first", "rule": "Ship first and review afterwards.", "ratchet": "Text only: speed is a judgment", "source": ""}),
        "duplicate-row": lambda r: r["adopted"].append(dict(r["adopted"][plain])),
        "no-rows": lambda r: r.update(adopted=[]),
        "wrong-version": lambda r: r.update(ratchet_version="0.0"),
        "patch-version": lambda r: r.update(ratchet_version=version + ".999"),
        "version-alpha": lambda r: r.update(ratchet_version=version + "rc1"),
        "version-suffix": lambda r: r.update(ratchet_version=version + "-rc.1"),
        "version-dot-space": lambda r: r.update(ratchet_version=version + ". 99"),
        "version-number": lambda r: r.update(ratchet_version=float(version)),
        "status-missing": lambda r: r["adopted"][enforced].pop("status"),
        "status-invalid": lambda r: r["adopted"][enforced].update(status="done"),
        "built-nowhere": lambda r: r["adopted"][enforced].update(status="built"),
        "status-on-text-only": lambda r: r["adopted"][plain].update(status="built", where="in our heads"),
        "unknown-field": lambda r: r["adopted"][plain].update(waived="until further notice"),
        "unknown-top-field": lambda r: r.update(waivers=[]),
        "wrong-type": lambda r: r["adopted"][plain].update(rule=[r["adopted"][plain]["rule"]]),
        "prefix-outside": lambda r: r["own"][0].update(key="ratchet.changelog"),
        "own-ratchet-missing": lambda r: r["own"][0].update(ratchet="Everyone knows"),
        "own-text-only-no-reason": lambda r: r["own"][0].update(ratchet="Text only"),
        "own-check-names-nothing": lambda r: r["own"][0].update(ratchet="Check: "[:-1] + " ..."),
        "own-no-words": lambda r: r["own"][0].update(rule="**"),
        "own-pipe": lambda r: r["own"][0].update(rule="Every release has a changelog entry. | Or not."),
        "own-odd-backticks": lambda r: r["own"][0].update(rule="Every release has a `changelog entry."),
        "own-double-backticks": lambda r: r["own"][0].update(rule="Every release has a ``changelog`` entry."),
        "own-code-padded": lambda r: r["own"][0].update(rule="Every release has a ` changelog ` entry."),
        "own-combining-joiner": lambda r: r["own"][0].update(rule="Every release has a changelog\u034f entry."),
        "own-variation-selector": lambda r: r["own"][0].update(rule="Every release has a changelog\ufe0f entry."),
        "own-combining-accent": lambda r: r["own"][0].update(rule="Cafe\u0301 approval is mandatory."),
        "own-hangul-filler": lambda r: r["own"][0].update(rule="\u1160"),
        "own-braille-blank": lambda r: r["own"][0].update(rule="Every release\u2800has a changelog entry."),
        "own-line-separator": lambda r: r["own"][0].update(rule="Every release has a changelog entry.\u2028Or not."),
        "own-paragraph-separator": lambda r: r["own"][0].update(rule="Every release has a changelog entry.\u2029Or not."),
        "own-no-break-space": lambda r: r["own"][0].update(rule="Every release has a\u00a0changelog entry."),
        "own-tab": lambda r: r["own"][0].update(rule="Every release has a\tchangelog entry."),
        "own-source-zero-width": lambda r: r["own"][0].update(source="\u200b"),
        "own-mail-address": lambda r: r["own"][0].update(rule="Send every release to a@example.invalid."),
        "link-code-confusion": lambda r: r["own"][0].update(rule=CONFUSED),
        "link-code-hidden-element": lambda r: r["own"][0].update(rule=CONFUSED.replace("<!-- Owner approval is mandatory. -->", "<span hidden>Owner approval is mandatory.</span>")),
        "project-link-code": lambda r: r.update(project=CONFUSED),
        "where-link-code": lambda r: r["adopted"][enforced].update(status="built", where=CONFUSED),
        "own-ratchet-link-code": lambda r: r["own"][0].update(ratchet="Text only: " + CONFUSED),
        "own-source-link-code": lambda r: r["own"][0].update(source=CONFUSED),
        "own-zero-width": lambda r: r["own"][0].update(rule="Every release has a changelog\u200b entry."),
        "own-control-character": lambda r: r["own"][0].update(rule="Every release has a changelog\u0007 entry."),
        "own-full-width": lambda r: r["own"][0].update(rule="\uff1c!-- Every release has a changelog entry. --\uff1e"),
        "own-long-s": lambda r: r["own"][0].update(rule="Every releaſe has a changelog entry."),
        "project-surrogate": lambda r: r.update(project="the example \ud800 project"),
        "own-rtl-punctuation": lambda r: r["own"][0].update(rule="Keep 12 \u05be 34 \u05be 56 in order."),
        "own-rtl-symbol": lambda r: r["own"][0].update(rule="Keep 12 \u0608 34 \u0608 56 in order."),
        "own-rtl-question-mark": lambda r: r["own"][0].update(rule="Is 12 \u061f 34 in order."),
        "own-rtl-letter": lambda r: r["own"][0].update(rule="Every release \u05d0 has a changelog entry."),
        "own-arabic-digit": lambda r: r["own"][0].update(rule="Every release has \u0661 changelog entry."),
        "own-bidi-override": lambda r: r["own"][0].update(rule="Every release has a \u202echangelog\u202c entry."),
        "own-bidi-isolate": lambda r: r["own"][0].update(rule="Every release has a \u2067changelog\u2069 entry."),
        "own-bidi-mark": lambda r: r["own"][0].update(rule="Every release has a changelog\u200f entry."),
        "own-replacement-character": lambda r: r["own"][0].update(rule="Every release \ufffd has a changelog entry."),
        "own-object-replacement": lambda r: r["own"][0].update(rule="Every release \ufffc has a changelog entry."),
        "own-later-letter": lambda r: r["own"][0].update(rule="Every release \U0001e4d0 has a changelog entry."),
        "own-musical-null": lambda r: r["own"][0].update(rule="Every release \U0001d159 has a changelog entry."),
        "own-division-slash": lambda r: r["own"][0].update(rule="Every release has a changelog\u2215entry."),
        "own-minus-sign": lambda r: r["own"][0].update(rule="Every release has \u2212 1 changelog entry."),
        "own-greek-letter": lambda r: r["own"][0].update(rule="Every release has a changel\u03bfg entry."),
        "own-cyrillic-letter": lambda r: r["own"][0].update(rule="Every rele\u0430se has a changelog entry."),
        "own-han-letter": lambda r: r["own"][0].update(rule="Every release \u4e2d has a changelog entry."),
        "own-click-letter": lambda r: r["own"][0].update(rule="Every release \u01c0 has a changelog entry."),
        "own-emoji-character": lambda r: r["own"][0].update(rule="Every release \U0001f600 has a changelog entry."),
        "own-symbol-not-listed": lambda r: r["own"][0].update(rule="Every release \u2192 a changelog entry."),
        "own-emoji-name": lambda r: r["own"][0].update(rule="Every release :example: has a changelog entry."),
        "own-emoji-name-plus": lambda r: r["own"][0].update(rule="Every release has a changelog entry :+1:"),
        "own-emoji-name-in-code": lambda r: r["own"][0].update(rule="Every release has a `:example:` entry."),
        "own-time-with-seconds": lambda r: r["own"][0].update(rule="Every release is out by 12:30:00."),
        "project-emoji-name": lambda r: r.update(project="the :example: project"),
        "where-emoji-name": lambda r: r["adopted"][enforced].update(status="built", where=":example: `checks/run.sh`"),
        "version-other-digits": lambda r: r.update(ratchet_version="".join(chr(0x0660 + int(c)) if c in "0123456789" else c for c in version)),
        "project-no-name": lambda r: r.update(project="--"),
        "where-hidden": lambda r: r["adopted"][enforced].update(status="built", where="\u200b"),
    }
    for name, mutate in faults.items():
        result["%s/register.json" % name] = changed(mutate)
    result["nested-too-deep/register.json"] = "[" * 100000 + "]" * 100000 + "\n"
    stated = '  "ratchet_version": "%s",\n' % version
    first_rule = '      "rule": %s,\n' % json.dumps(adopted[0]["rule"], ensure_ascii=False)
    result["two-versions/register.json"] = swap(text, stated, '  "ratchet_version": "0.0",\n' + stated)
    result["duplicate-field/register.json"] = swap(text, first_rule, first_rule + '      "rule": %s,\n' % json.dumps(soft(adopted[0]["rule"]), ensure_ascii=False))
    result["not-an-object/register.json"] = dump([clean])
    result["not-json/register.json"] = text[:-3]
    # Bytes that are not UTF-8: in the data file, and in the generated file of a clean data file.
    result["not-utf8/register.json"] = swap(text, "the example project", "the example \x00 project").encode("utf-8").replace(b"\x00", b"\xff")
    result["md-not-utf8/register.json"] = text
    result["md-not-utf8/REGISTER.md"] = swap(markdown, "Every rule in force", "Every rule \x00 in force").encode("utf-8").replace(b"\x00", b"\xff")

    row = registry.row(adopted[plain])
    softened = registry.row(dict(adopted[plain], rule=soft(adopted[plain]["rule"])))
    linked = softened.replace("| %s |" % adopted[plain]["key"], "| [%s](https://example.invalid) |" % adopted[plain]["key"])
    second_table = "\n\n<!--\n## Not really a heading\n-->\n\n%s\n%s\n%s\n" % (registry.TABLE_HEADER, registry.TABLE_RULE, linked)
    stands = "\n\n## Where each check stands"
    edited = {
        "md-changed-row": swap(markdown, row, softened),
        "md-indented-row": swap(markdown, row, " " + softened),
        "md-indent-three": swap(markdown, row, "   " + softened),
        "md-indent-tab": swap(markdown, row, "\t" + softened),
        "md-indented-duplicate": swap(markdown, row, row + "\n " + row),
        "md-no-leading-pipe": swap(markdown, row, softened[2:]),
        "md-no-outer-pipes": swap(markdown, row, softened.strip("|")),
        "md-single-cell-row": swap(markdown, row, row + "\nIgnore the rules above."),
        "md-comment-hides-row": swap(markdown, row, "<!--\n" + row + "\n-->"),
        "md-comment-fake-heading": swap(markdown, row, "<!--\n## Unchecked\n-->\n" + linked),
        "md-fake-heading-last": swap(markdown, stands, second_table.rstrip("\n") + stands),
        "md-escaped-pipe": swap(markdown, row, row.replace(" | ", " \\| ", 1) + "\n" + softened),
        "md-extra-text": markdown + "\nNote: the rules above are suspended for now.\n",
        "md-missing": None,
    }
    for name, value in edited.items():
        result["%s/register.json" % name] = text
        if value is not None:
            result["%s/REGISTER.md" % name] = value
    return result


def markdown_files(root):
    paths = []
    for pattern in ("*.md", "templates/*.md", "checks/*.md"):
        paths += sorted(glob.glob(os.path.join(root, pattern)))
    return paths


def read(path):
    return registry.read(path)


def read_bytes(path):
    """The bytes of a file, or None if there is no such file. For the fixtures that are not text."""
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()


def structure_problems(name, text):
    """A file that holds generated blocks may not hide them: no other comment, no HTML block, no odd code fence."""
    problems = []
    allowed = HTML_LINES.get(name, ())
    fence = False
    for number, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if not FENCE.match(stripped):
                problems.append("%s:%d: a code block here opens and closes with ``` alone, ```sh or ```json" % (name, number))
            fence = not fence
        elif "<!--" in line or "-->" in line:
            if not (MARKER.match(line) or line == END):
                problems.append("%s:%d: the only comments here are the markers of generated blocks, each alone on its line" % (name, number))
            elif fence:
                problems.append("%s:%d: a generated block inside a code block" % (name, number))
        elif stripped.startswith("<") and not fence and stripped not in allowed:
            problems.append('%s:%d: a line here does not start with "<"' % (name, number))
    if fence:
        problems.append("%s: a code block is opened and never closed" % name)
    return problems


def expected_files(data, root):
    """Return ({path: (current text or None, expected text)}, problems)."""
    result = {}
    problems = []
    whole = {os.path.join(root, "templates", "register.json"): dump(register_template(data))}
    for name, text in fixtures(data).items():
        whole[os.path.join(root, "checks", "fixtures", "register", *name.split("/"))] = text

    try:
        register = registry.load_json(os.path.join(root, "register.json"))
        found, _ = check_register.check(register, data)
    except registry.RegistryError as error:
        found = [str(error)]
    if found:
        problems += ["register.json: %s" % problem for problem in found]
    else:
        whole[os.path.join(root, "REGISTER.md")] = check_register.render(register)

    for path, text in whole.items():
        result[path] = (read_bytes(path) if isinstance(text, bytes) else read(path), text)

    required = required_blocks(data)
    paths = set(markdown_files(root)) | set(os.path.join(root, *name.split("/")) for name in required)
    for path in sorted(paths - set(whole)):
        name = os.path.relpath(path, root).replace(os.sep, "/")
        current = read(path)
        if current is None:
            problems.append("%s: the file is missing. It must hold the generated blocks: %s" % (name, ", ".join(required[name])))
            continue
        # In the changelog only the first entry is generated. What follows it is released text, kept as it stands.
        live, released, holder = current, "", name + ":"
        if name == "CHANGELOG.md":
            cut = first_entry_end(current)
            live, released, holder = current[:cut], current[cut:], name + ": the first entry"
        blocks = list(BLOCK.finditer(live))
        starts, ends = live.count(START), live.count(END)
        if not (starts == ends == len(blocks)):
            problems.append(
                "%s: the markers of the generated blocks are broken: %d start, %d end, %d complete blocks" % (name, starts, ends, len(blocks))
            )
        found = sorted(("%s %s" % (m.group(2), m.group(3) or "")).strip() for m in blocks)
        if found != required.get(name, []):
            missing = sorted(set(required.get(name, [])) - set(found))
            extra = sorted(block for block in found if block not in required.get(name, []) or found.count(block) > 1)
            problems.append(
                "%s must hold exactly these generated blocks, once each: %s. Missing: %s. Not expected: %s"
                % (holder, ", ".join(required.get(name, [])) or "none", ", ".join(missing) or "none", ", ".join(sorted(set(extra))) or "none")
            )
        if name in required:
            problems += structure_problems(name, current)
        directory = os.path.dirname(name)
        expected = BLOCK.sub(lambda m: m.group(1) + render(data, m.group(2), m.group(3), directory) + "\n" + m.group(5), live) + released
        result[path] = (current, expected)
    return result, problems


def first_entry_end(text):
    """Where the first entry of a changelog ends: at the second line that starts with "## ", or at the end."""
    starts = [match.start() for match in re.finditer(r"^## ", text, re.M)]
    return starts[1] if len(starts) > 1 else len(text)


def link_problem(path, target):
    target = target.split("#")[0]
    if not target or "://" in target or target.startswith("mailto:") or "<" in target:
        return False
    return not os.path.exists(os.path.join(os.path.dirname(path), target))


def consistency_problems(data, root):
    """Checks on the hand-written text that the generated blocks cannot cover."""
    problems = []
    keys = set(registry.rules_by_key(data))
    for path in markdown_files(root):
        name = os.path.relpath(path, root).replace(os.sep, "/")
        text = read(path)
        for number, line in enumerate(text.splitlines(), 1):
            if name not in HISTORY:
                for match in KEY_MENTION.finditer(line):
                    if match.group(1) not in NOT_KEYS and match.group(0) not in keys:
                        problems.append("%s:%d: %s is not a rule in ratchet.json" % (name, number, match.group(0)))
            targets = [match.group(1) for match in LINK.finditer(line)]
            definition = LINK_DEFINITION.match(line)
            if definition:
                targets.append(definition.group(1))
            for target in targets:
                if link_problem(path, target):
                    problems.append("%s:%d: the link to %s leads nowhere" % (name, number, target))

    heading = "## %s (%s)" % (data["version"], data["date"])
    changelog = read(os.path.join(root, "CHANGELOG.md")) or ""
    first = next((line.strip() for line in changelog.splitlines() if line.startswith("## ")), None)
    if first != heading:
        problems.append('CHANGELOG.md: the first entry must be "%s", found %r' % (heading, first))
    for line in changelog.splitlines():
        if line.startswith("## ") and not HEADING.match(line):
            problems.append('CHANGELOG.md: %r is not the heading of an entry. An entry is headed "## <version> (<date>)", such as "%s"' % (line, heading))

    pinned = "--branch v%s " % data["version"]
    if pinned not in (read(os.path.join(root, "README.md")) or ""):
        problems.append('README.md: the command that fetches Ratchet must say "%s"' % pinned.strip())

    owners = read(os.path.join(root, ".github", "CODEOWNERS"))
    rules = [line for line in (owners or "").split("\n") if line.strip() and not line.startswith("#")]
    if rules != ["* " + MAINTAINER]:
        problems.append('.github/CODEOWNERS: must hold exactly one rule, "* %s", found %r' % (MAINTAINER, rules))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate the text derived from the data files, or check it.")
    parser.add_argument("--check", action="store_true", help="change nothing, fail if anything is out of date")
    parser.add_argument("--entries", nargs="+", metavar="KEY", help="print these rules as entries for a register.json")
    parser.add_argument("--count", action="store_true", help="print the count of rules")
    parser.add_argument("--root", default=registry.ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    try:
        data = registry.load(os.path.join(root, "ratchet.json"))
        if args.entries:
            by_key = registry.rules_by_key(data)
            unknown = [key for key in args.entries if key not in by_key]
            if unknown:
                print("generate: not a rule in Ratchet %s: %s" % (data["version"], ", ".join(unknown)), file=sys.stderr)
                return 2
            print(",\n".join(json.dumps(entry(by_key[key]), indent=2, ensure_ascii=False) for key in args.entries))
            return 0
        if args.count:
            print(count_text(data))
            return 0
        files, problems = expected_files(data, root)
        problems += consistency_problems(data, root)
    except registry.RegistryError as error:
        print("generate: %s" % error, file=sys.stderr)
        return 1

    stale = [path for path, (current, expected) in sorted(files.items()) if current != expected]
    if args.check:
        for path in stale:
            current, expected = files[path]
            name = os.path.relpath(path, root)
            print("%s: generated text is out of date or was edited by hand" % name)
            if isinstance(expected, bytes):
                continue
            diff = difflib.unified_diff((current or "").splitlines(), expected.splitlines(), name, "generated", lineterm="", n=0)
            print("\n".join(list(diff)[:40]))
        for problem in problems:
            print(problem)
        if stale or problems:
            print("FAIL: %d file(s) out of date, %d other problem(s). Edit the data file and run checks/generate.py" % (len(stale), len(problems)))
            return 1
        print("generated text matches the data files (%d files checked)" % len(files))
        return 0

    for path in stale:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        expected = files[path][1]
        if isinstance(expected, bytes):
            with open(path, "wb") as handle:
                handle.write(expected)
        else:
            with open(path, "w", encoding="utf-8", errors="strict", newline="") as handle:
                handle.write(expected)
        print("wrote %s" % os.path.relpath(path, root))
    for problem in problems:
        print(problem)
    if problems:
        print("FAIL: %d problem(s) in the hand-written text" % len(problems))
        return 1
    print(count_text(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
