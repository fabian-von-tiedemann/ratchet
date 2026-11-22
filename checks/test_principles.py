"""The principles: every rule in ratchet.json stands under one principle, and the generator shows them first.

    python3 -m unittest discover -s checks -v

ratchet.json holds a list "principles", each with a key of the form principle.<slug>, a short title and a text of at
most three sentences, and every rule names one of them in "principle" (D-2026-11-20-principles-and-obligations). A
principle names no check of its own: each rule keeps its own ratchet, and a register keeps the status of each rule it
adopts. The reader is as strict as for every other field (D-2026-11-16-strict-forms, D-2026-11-17-latin-strict-utf8).
The ratchet.json of a version before 0.10 has neither field, and checks/upgrade.py reads it.

The fixtures are under checks/fixtures/principles/: clean.json, a small data file that passes, older.json, the same
in the form before principles, and one file per fault, each clean.json with one change. Each test loads what it
uses through FixtureTest. Standard library only.
"""

import os
import re
import shutil
import sys
import unittest

from suite_runner import FixtureTest
from test_checks import ROOT, RepoCopy, read, run

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import generate  # noqa: E402
import registry  # noqa: E402

KEY_FORM = "a key is principle. followed by lowercase words joined by hyphens"
SAME_TITLE = "principle.name-it: its title is the title of principle.test-everything, compared without regard to case"
# Two titles that differ only in their spaces look the same in HTML, so a title has single spaces between words.
SPACED = "principle.keep-it-simple: the title has two spaces in a row, and HTML shows them as one"

# Fixture under principles/ -> what generate.py --check must say when that file is ratchet.json.
FAILING = {
    "missing-principles": "missing field 'principles'",
    "principles-not-list": "principles must be a list",
    "principle-not-object": "a principle must be an object",
    "principle-missing-field": "principle.keep-it-simple: missing text",
    "principle-unknown-field": ("principle.test-everything: unknown field check. A principle has exactly key, title and "
                                "text, and names no check of its own"),
    "principle-not-text": "principle.test-everything: every field must be a string",
    "key-form": "principle.Test_Everything: " + KEY_FORM,
    "key-rule-prefix": "ratchet.test-everything: " + KEY_FORM,
    "key-twice": "principle.test-everything: the key is used twice",
    "title-twice": SAME_TITLE,
    "title-twice-case": SAME_TITLE,
    "title-outside-list": "principle.test-everything: title holds U+200B",
    "title-no-words": "principle.test-everything: the title holds no words",
    "title-too-long": "principle.test-everything: the title is 65 characters long, and a title is at most 60",
    "title-repeated-space": SPACED,
    "title-padded": "principle.keep-it-simple: title must be one line, without | and without spaces at the ends",
    "text-outside-list": "principle.test-everything: text holds U+202E",
    "text-no-words": "principle.test-everything: the text holds no words",
    "text-four-sentences": "principle.test-everything: the text has 4 sentences, and a principle has at most 3",
    "text-no-full-stop": ("principle.test-everything: the text must end with a full stop, a question mark or an "
                          "exclamation mark, so that its sentences can be counted"),
    "rule-without-principle": "ratchet.keep: has no principle. Every rule names the key of one principle in principles",
    "rule-unknown-principle": "ratchet.now-checked: names principle.nowhere, which is not a principle in principles",
    "rule-principle-misspelled": "ratchet.keep: unknown field principal",
    "rule-principle-not-text": "ratchet.keep: every field must be a string",
    "principle-without-rule": "principle.name-it has no rule under it. A principle stands over at least one rule",
}
PASSING = ("clean", "older")

# What the generator writes for clean.json, typed by hand.
SECTION = (
    "### Test everything\n"
    "\n"
    "Every change is tested before it is merged\\. A test that never failed proves nothing\\.\n"
    "\n"
    "Guidance, text only. Rules under it: `ratchet.keep` (names a check)\n"
    "\n"
    "### Keep it simple\n"
    "\n"
    "Choose the simple solution\\, and name what you decide\\.\n"
    "\n"
    "Guidance, text only. Rules under it: `ratchet.reworded` (experimental, text only), `ratchet.now-checked` (experimental, text only)"
)
TITLES = "- Test everything\n- Keep it simple"


class PrincipleForm(FixtureTest):
    def generate_check(self, name):
        """generate.py --check on a directory that holds only this fixture, as ratchet.json."""
        root = self.scratch()
        shutil.copyfile(self.fixture_file("principles/%s.json" % name), os.path.join(root, "ratchet.json"))
        return run("generate.py", "--check", "--root", root)

    def test_a_fault_in_the_principles_fails_the_check(self):
        self.assertEqual(sorted(list(FAILING) + list(PASSING)),
                         sorted(name[:-len(".json")] for name in os.listdir(os.path.join(self.fixtures, "principles"))))
        for name, message in sorted(FAILING.items()):
            with self.subTest(fixture=name):
                code, output = self.generate_check(name)
                self.assertEqual(code, 1, output)
                self.assertIn(message, output)
                self.assertTrue(output.startswith("generate: "), "the data file fails before anything is generated: %s" % output)
                self.assertNotIn("Traceback", output)

    def test_the_clean_file_passes(self):
        data = registry.parse_json(self.fixture_bytes("principles/clean.json"))
        self.assertEqual(registry.validate(data, ROOT), [])

    def test_an_older_ratchet_json_may_lack_the_principles_and_this_one_may_not(self):
        data = registry.parse_json(self.fixture_bytes("principles/older.json"))
        self.assertEqual(registry.validate(data, None, older=True), [])
        self.assertIn("missing field 'principles'", registry.validate(data, None))

    def test_an_older_ratchet_json_with_principles_is_read_as_strictly(self):
        for name in ("rule-without-principle", "rule-unknown-principle", "principle-without-rule", "title-twice", "text-four-sentences"):
            with self.subTest(fixture=name):
                data = registry.parse_json(self.fixture_bytes("principles/%s.json" % name))
                self.assertIn(FAILING[name], registry.validate(data, None, older=True))

    def test_a_rule_in_an_older_ratchet_json_names_no_principle_it_lacks(self):
        data = registry.parse_json(self.fixture_bytes("principles/older.json"))
        data["rules"][0]["principle"] = "principle.test-everything"
        self.assertEqual(registry.validate(data, None, older=True),
                         ["ratchet.keep: names principle.test-everything, which is not a principle in principles"])

    def test_the_generator_writes_each_principle_with_its_rules_and_a_list_of_the_titles(self):
        data = registry.parse_json(self.fixture_bytes("principles/clean.json"))
        self.assertEqual(generate.render(data, "principles", None, "", {}), SECTION)
        self.assertEqual(generate.render(data, "principle-list", None, "", {}), TITLES)

    def test_a_title_and_a_text_are_written_as_text(self):
        data = registry.parse_json(self.fixture_bytes("principles/clean.json"))
        data["principles"][0].update(title="Test *all* <b>", text="Read [this](https://example.invalid) <!-- hidden -->.")
        section = generate.render(data, "principles", None, "", {})
        self.assertIn("### Test \\*all\\* \\<b\\>\n", section)
        self.assertIn("Read \\[this\\]\\(https\\:\\/\\/example\\.invalid\\) \\<\\!\\-\\- hidden \\-\\-\\>\\.\n", section)
        self.assertEqual(generate.render(data, "principle-list", None, "", {}).split("\n")[0], "- Test \\*all\\* \\<b\\>")


class ThisRatchet(unittest.TestCase):
    def test_seven_principles_each_over_at_least_one_rule_and_every_rule_under_one(self):
        # D-2026-11-22-second-redraw, step 4: the seven principles of the core on top, today's rules under them.
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        self.assertEqual(len(data["principles"]), 7)
        keys = [principle["key"] for principle in data["principles"]]
        self.assertEqual(sorted(set(rule["principle"] for rule in data["rules"])), sorted(keys))

    def test_ratchet_md_shows_the_principles_first(self):
        text = read("RATCHET.md")
        headings = [line for line in text.split("\n") if line.startswith("## ")]
        self.assertEqual(headings[0], "## The principles")
        section = text[text.index("## The principles"):text.index(headings[1])]
        self.assertIn("<!-- generated:principles -->\n", section)

    def test_readme_lists_the_principles_before_anything_else(self):
        text = read("README.md")
        headings = [line for line in text.split("\n") if line.startswith("## ")]
        self.assertEqual(headings[0], "## The principles")
        section = text[text.index("## The principles"):text.index(headings[1])]
        self.assertIn("<!-- generated:principle-list -->\n", section)
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        self.assertEqual(re.findall(r"^- (.*)$", section, re.M), [registry.cell(p["title"]) for p in data["principles"]])


class GeneratedPrinciples(RepoCopy, unittest.TestCase):
    def test_a_principle_edited_by_hand_in_ratchet_md_fails(self):
        self.edit("RATCHET.md", "### Keep one place\n", "### Keep one place, where practical\n")
        self.assert_check_fails("RATCHET.md: generated text is out of date or was edited by hand")

    def test_a_rule_moved_to_another_principle_without_generating_fails(self):
        self.edit("ratchet.json", '"principle": "principle.keep-one-place"', '"principle": "principle.independent-gate"')
        self.assert_check_fails("RATCHET.md: generated text is out of date or was edited by hand")

    def test_the_list_of_titles_must_stand_in_the_readme(self):
        text = read("README.md")
        block = re.search(r"<!-- generated:principle-list -->\n.*?<!-- /generated -->\n", text, re.S).group(0)
        self.edit("README.md", block, "")
        self.assert_check_fails("Missing: principle-list")

    def test_a_principle_mentioned_that_does_not_exist_fails(self):
        self.append("README.md", "\nSee `principle.nowhere`.\n")
        self.assert_check_fails("principle.nowhere is not a principle in ratchet.json")


if __name__ == "__main__":
    unittest.main()
