"""The story and the values: one data file, values.json, read strictly, and generated into the files that show them.

    python3 -m unittest discover -s checks -v

values.json holds Ratchet's story, the line that leads to its four values, the values, the line that weighs them,
and the two lines around the principles (D-2026-11-23-values-and-principles). It is text, not rules: no rule stands
under a value, and nothing here checks what a value says. What is checked is that the file has its one form, read
as strictly as every data file (D-2026-11-16-strict-forms, D-2026-11-17-latin-strict-utf8), and that README.md and
RATCHET.md show it as generate.py writes it, so the text has one home. The landing page is tested in test_pages.py.
Standard library only.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# The scripts of Ratchet's own maintenance stand in maintain/, beside checks/ (D-2026-11-27-maintain-apart).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maintain"))
import generate  # noqa: E402
import registry  # noqa: E402
from test_checks import ROOT, RepoCopy, read  # noqa: E402

# What the generator writes for a small values.json, typed by hand.
SMALL = {"story": "One person, many agents.", "lead": "We value:", "values": [{"prefer": "Checks", "over": "warnings"}],
         "balance": "The left wins.", "production": "For production:", "aims": "These are aims."}
SMALL_TEXT = ("*One person\\, many agents\\.*\n\n**We value\\:**\n\n**Checks** over warnings\n\nThe left wins\\.")


class ValuesFile(RepoCopy, unittest.TestCase):
    def values_text(self):
        with open(os.path.join(self.copy, "values.json"), encoding="utf-8", newline="") as handle:
            return handle.read()

    def test_the_four_values_are_the_approved_text(self):
        # D-2026-11-23-values-and-principles: the text the maintainer approved word for word.
        values = registry.load_values(os.path.join(ROOT, "values.json"))
        self.assertEqual([(value["prefer"], value["over"]) for value in values["values"]], [
            ("Checks that catch mistakes", "instructions that warn about them"),
            ("Written decisions", "remembered conversations"),
            ("Shown results", "reported success"),
            ("Independent review", "self-review"),
        ])
        self.assertEqual(values["lead"], "We value:")
        self.assertEqual(values["story"], 'Agile was written for a team of people. Ratchet is for one person with a team of '
                                          'agents, who work fast, forget everything between sessions and say "done" with confidence.')
        self.assertEqual(values["balance"], "That is, while there is value in the items on the right, we value the items on the "
                                            "left more. The right is faster. It works while the agent remembers, obeys and "
                                            "judges itself well. The left is for when it doesn't.")
        self.assertEqual(values["production"], "For applications with users in production:")
        self.assertEqual(values["aims"], "These are aims. Ratchet's rules say which of them a check can see.")

    def test_values_json_is_read_strictly(self):
        valid = self.values_text()
        data = json.loads(valid)

        def changed(change):
            copy = json.loads(valid)
            change(copy)
            return json.dumps(copy, indent=2)

        cases = {
            "a field twice": (valid.replace('{\n  "story"', '{\n  "story": "x",\n  "story"', 1),
                              "values.json: not a valid data file: the field 'story' appears twice in one object"),
            "an unknown field": (changed(lambda d: d.update(rules=[])), "values.json: unknown field 'rules'"),
            "a field missing": (changed(lambda d: d.pop("aims")), "values.json: missing field 'aims'"),
            "not an object": ("[]\n", "values.json: the top level must be an object"),
            "NaN": ('{"story": NaN}\n', "values.json: not a valid data file: NaN is not allowed"),
            "not JSON": (valid[:-3], "values.json: not a valid data file"),
            "no values": (changed(lambda d: d.update(values=[])), "values.json: values must be a list of at least one value"),
            "values not a list": (changed(lambda d: d.update(values={})), "values.json: values must be a list of at least one value"),
            "a value with a field more": (changed(lambda d: d["values"][1].update(why="x")),
                                          "values.json: value 2 must be an object with exactly the fields prefer and over"),
            "a value with a field missing": (changed(lambda d: d["values"][0].pop("over")),
                                             "values.json: value 1 must be an object with exactly the fields prefer and over"),
            "a value not text": (changed(lambda d: d["values"][2].update(prefer=["Shown results"])), "values.json: value 3: prefer must be text"),
            "a story not text": (changed(lambda d: d.update(story=1)), "values.json: story must be text"),
            "a character outside the list": (changed(lambda d: d.update(lead="We value\u200b:")), "values.json: lead holds U+200B"),
            "two lines": (changed(lambda d: d.update(balance="The right is faster.\nThe left is not.")),
                          "values.json: balance must be one line"),
            "no words": (changed(lambda d: d.update(aims="...")), "values.json: aims holds no words"),
            "code": (changed(lambda d: d["values"][0].update(over="`instructions`")),
                     "values.json: value 1: over holds code. A value here is text only"),
        }
        self.assertEqual(len(data["values"]), 4)
        path = os.path.join(self.copy, "values.json")
        for case, (text, message) in cases.items():
            with self.subTest(case=case):
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(text)
                self.assert_check_fails(message)
        os.remove(path)
        self.assert_check_fails("values.json: not a valid data file")

    def test_values_json_that_is_not_utf8_fails(self):
        path = os.path.join(self.copy, "values.json")
        with open(path, "rb") as handle:
            original = handle.read()
        with open(path, "wb") as handle:
            handle.write(original.replace(b"e", b"\xff", 1))
        self.assert_check_fails("values.json: not a valid data file")


class GeneratedValues(RepoCopy, unittest.TestCase):
    def test_the_generator_writes_the_story_and_the_values_as_text(self):
        self.assertEqual(generate.values_text(SMALL), SMALL_TEXT)
        marked = dict(SMALL, values=[{"prefer": "[ok](https://example.invalid) <!-- x -->", "over": "*all*"}])
        self.assertIn("**\\[ok\\]\\(https\\:\\/\\/example\\.invalid\\) \\<\\!\\-\\- x \\-\\-\\>** over \\*all\\*",
                      generate.values_text(marked))

    def test_the_readme_and_ratchet_md_show_the_values_first(self):
        # The values stand above the principles, before the first heading of each file below its title.
        for name in ("README.md", "RATCHET.md"):
            with self.subTest(file=name):
                text = read(name)
                block = text.index("<!-- generated:values -->\n")
                self.assertLess(block, text.index("\n## "))
                self.assertIn("**Checks that catch mistakes** over instructions that warn about them\n", text[block:])

    def test_a_value_edited_by_hand_fails(self):
        for name in ("README.md", "RATCHET.md"):
            with self.subTest(file=name):
                self.setUp()
                self.edit(name, "**Shown results** over reported success\n", "**Shown results** over everything\n")
                self.assert_check_fails("%s: generated text is out of date or was edited by hand" % name)

    def test_the_block_of_the_values_must_stand_in_the_readme_and_ratchet_md(self):
        for name in ("README.md", "RATCHET.md"):
            with self.subTest(file=name):
                self.setUp()
                text = read(name)
                start = text.index("<!-- generated:values -->\n")
                end = text.index("<!-- /generated -->\n", start) + len("<!-- /generated -->\n")
                self.edit(name, text[start:end], "")
                self.assert_check_fails("Missing: values")


if __name__ == "__main__":
    unittest.main()
