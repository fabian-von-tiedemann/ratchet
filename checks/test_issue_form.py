"""The issue form for proposals has the five fields of D-2026-11-17-pull-and-budget, each required.

    python3 -m unittest discover -s checks -v

The form is `.github/ISSUE_TEMPLATE/proposal.yml`. GitHub reads it as YAML, and the standard library has no YAML
parser, so this test does not parse YAML. It reads the file in one fixed form, line by line, and fails on every
line that is not in that form: a top with `name`, `description`, `labels` and `body`, then one block of seven
lines per field, in a fixed order and with fixed indentation. The labels line is exactly `labels: [proposal]`, a
list of the one label `proposal`. A value is one plain line that starts with a capital letter
and holds only letters, digits, spaces and `,.;()'?-`, so YAML reads it as that text and nothing else: it has no
colon, no `#`, no quote at its start and no mark that starts a block, an anchor or a tag, and it is not a word
that YAML 1.1 reads as true, false or null. A form this reader accepts is read the same way by any YAML parser.

The test claims that the form has exactly these fields, in this order, each a textarea marked required, and that
it gives the issues it opens the one label `proposal`. It does not claim that GitHub accepts the form or shows it,
or that the label exists in the repo: that is seen on GitHub once the form is on main. It does not
stop a person from opening an issue without the form. Standard library only.
"""

import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FORM = os.path.join(HERE, "..", ".github", "ISSUE_TEMPLATE", "proposal.yml")

# The five fields, from D-2026-11-17-pull-and-budget, item 3: id and label.
FIELDS = [
    ("what-happened", "What happened"),
    ("failure-class", "Failure class"),
    ("ratchet", "Ratchet"),
    ("other-projects", "Would it apply in other projects?"),
    ("primary-source", "Primary source"),
]

ID = re.compile(r"[a-z]+(?:-[a-z]+)*\Z")
VALUE = re.compile(r"[A-Z][A-Za-z0-9 ,.;()'?-]*[A-Za-z0-9.?)]\Z|[A-Z]\Z")
# Words that YAML 1.1 reads as true, false or null when they stand alone.
KEYWORDS = {"y", "yes", "n", "no", "true", "false", "on", "off", "null"}

# The one label an issue opened with the form gets. The line is read as this exact text.
LABELS = ["proposal"]
LABELS_LINE = "[%s]" % ", ".join(LABELS)

TOP = (("name: ", VALUE), ("description: ", VALUE), ("labels: ", LABELS_LINE), ("body:", None))
ITEM = (
    ("  - type: ", "textarea"),
    ("    id: ", ID),
    ("    attributes:", None),
    ("      label: ", VALUE),
    ("      description: ", VALUE),
    ("    validations:", None),
    ("      required: ", "true"),
)


class FormError(Exception):
    pass


def value(number, line, prefix, form):
    """The value on one line of the fixed form, or None for a line that holds only a key."""
    if form is None:
        if line != prefix:
            raise FormError("line %d: expected %r, found %r" % (number, prefix, line))
        return None
    if not line.startswith(prefix):
        raise FormError("line %d: expected a line that starts %r, found %r" % (number, prefix, line))
    found = line[len(prefix):]
    if isinstance(form, str):
        if found != form:
            raise FormError("line %d: expected %r, found %r" % (number, prefix + form, line))
    elif not form.match(found) or found.lower() in KEYWORDS:
        raise FormError("line %d: %r is not a value this reader knows" % (number, found))
    return found


def read_form(data):
    """Return (name, description, labels, [(id, label, description)]) from the bytes of the form, or raise FormError."""
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        raise FormError("byte %d is not ASCII" % error.start)
    if "\r" in text or "\t" in text:
        raise FormError("the form holds a carriage return or a tab")
    if not text.endswith("\n"):
        raise FormError("the form does not end with a newline")
    lines = [(number, line) for number, line in enumerate(text[:-1].split("\n"), 1) if line != ""]
    if len(lines) < len(TOP):
        raise FormError("the form is too short")
    head = [value(number, line, *TOP[k]) for k, (number, line) in enumerate(lines[: len(TOP)])]
    rest = lines[len(TOP):]
    fields = []
    for start in range(0, len(rest), len(ITEM)):
        block = rest[start:start + len(ITEM)]
        if len(block) < len(ITEM):
            raise FormError("line %d: a field that is not complete" % block[0][0])
        found = [value(number, line, *ITEM[k]) for k, (number, line) in enumerate(block)]
        fields.append((found[1], found[3], found[4]))
    return head[0], head[1], list(LABELS), fields


def form_problems(data):
    """Every way the form differs from the five required fields."""
    try:
        _, _, _, fields = read_form(data)
    except FormError as error:
        return [str(error)]
    found = [(field_id, label) for field_id, label, _ in fields]
    if found != FIELDS:
        return ["the fields are %r, not %r" % (found, FIELDS)]
    return []


def read_bytes():
    with open(FORM, "rb") as handle:
        return handle.read()


# Changes to the form that must fail: (what, old text, new text, part of the message).
MUTATIONS = [
    ("a field not required", "required: true", "required: false", "required: false"),
    ("a field with no validations", "    validations:\n      required: true\n", "", "expected '    validations:'"),
    ("a field of another type", "type: textarea", "type: input", "type: input"),
    ("a label with a colon", "label: What happened", "label: What happened: when", "not a value"),
    ("a label YAML reads as true", "label: Ratchet\n", "label: Yes\n", "not a value"),
    ("a block scalar", "description: ", "description: |\n        ", "not a value"),
    ("a quoted value", "label: Primary source", "label: 'Primary source'", "not a value"),
    ("a comment", "body:\n", "body:\n# a comment\n", "expected"),
    ("a key this reader does not know", "body:\n", "title: A proposal\nbody:\n", "expected 'body:'"),
    ("the labels line left out", "labels: [proposal]\n", "", "starts 'labels: '"),
    ("a different label", "labels: [proposal]", "labels: [question]", "expected 'labels: [proposal]'"),
    ("a second label", "labels: [proposal]", "labels: [proposal, question]", "expected 'labels: [proposal]'"),
    ("the labels as a block list", "labels: [proposal]\n", "labels:\n  - proposal\n", "starts 'labels: '"),
    ("the label quoted", "labels: [proposal]", "labels: [\"proposal\"]", "expected 'labels: [proposal]'"),
    ("the labels as a string", "labels: [proposal]", "labels: proposal", "expected 'labels: [proposal]'"),
    ("the labels key twice", "labels: [proposal]\n", "labels: [proposal]\nlabels: [proposal]\n", "expected 'body:'"),
    ("a line indented one more", "    id: ratchet", "     id: ratchet", "expected"),
    ("a trailing space", "required: true\n", "required: true \n", "expected"),
    ("a tab", "  - type", "\t- type", "tab"),
    ("a carriage return", "body:\n", "body:\r\n", "carriage return"),
    ("a letter that is not ASCII", "Failure class", "Failure cläss", "not ASCII"),
    ("a field renamed", "id: ratchet\n", "id: the-ratchet\n", "the fields are"),
    ("a field relabeled", "label: Primary source", "label: Source", "the fields are"),
]


class IssueForm(unittest.TestCase):
    def test_the_form_has_the_five_fields_each_required(self):
        self.assertEqual(form_problems(read_bytes()), [])

    def test_the_form_gives_its_issues_the_label_proposal(self):
        self.assertEqual(read_form(read_bytes())[2], ["proposal"])

    def test_the_form_fails_with_a_field_left_out(self):
        text = read_bytes().decode("ascii")
        last = text.rindex("  - type: textarea")
        self.assertIn("the fields are", form_problems(text[:last].encode("ascii"))[0])

    def test_the_form_fails_with_a_field_twice(self):
        text = read_bytes().decode("ascii")
        first = text.index("  - type: textarea")
        second = text.index("  - type: textarea", first + 1)
        doubled = text[:second] + text[first:second] + text[second:]
        self.assertIn("the fields are", form_problems(doubled.encode("ascii"))[0])

    def test_the_form_fails_with_the_last_field_cut_short(self):
        text = read_bytes().decode("ascii")
        self.assertTrue(text.endswith("    validations:\n      required: true\n"))
        cut = text[: -len("    validations:\n      required: true\n")]
        self.assertIn("not complete", form_problems(cut.encode("ascii"))[0])

    def test_the_form_fails_without_a_final_newline(self):
        self.assertIn("newline", form_problems(read_bytes().rstrip(b"\n"))[0])

    def test_every_change_in_the_list_fails(self):
        text = read_bytes().decode("ascii")
        for what, old, new, message in MUTATIONS:
            with self.subTest(case=what):
                changed = text.replace(old, new, 1)
                self.assertNotEqual(changed, text, what)
                problems = form_problems(changed.encode("utf-8"))
                self.assertEqual(len(problems), 1, what)
                self.assertIn(message, problems[0], what)


if __name__ == "__main__":
    unittest.main()
