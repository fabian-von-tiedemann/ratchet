"""The budget: ratchet.json caps the number of experimental rules, and generate.py --check fails above the cap.

    python3 -m unittest discover -s checks -v

The cap is the field "experimental_cap" in ratchet.json (D-2026-11-17-pull-and-budget). The fixtures under
checks/fixtures/budget/ are small data files with one core rule and two experimental ones. Each test loads what
it uses through FixtureTest. Standard library only.
"""

import os
import shutil
import sys
import unittest

from suite_runner import FixtureTest
from test_checks import ROOT, RepoCopy, read, run

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import registry  # noqa: E402

# The cap on the day of the decision: 20 experimental rules in ratchet.json at the commit on main that added
# decisions/D-2026-11-17-pull-and-budget.md, plus five.
CAP = 25
OVER = "experimental rules, which is more than the cap of"
FORM = "experimental_cap must be a whole number from 0"

# Fixture under budget/ -> what generate.py --check must say when that file is ratchet.json.
FAILING = {
    "over-cap": "2 experimental rules, which is more than the cap of 1",
    "no-cap": "missing field 'experimental_cap'",
    "cap-text": FORM,
    "cap-true": FORM,
    "cap-fraction": FORM,
    "cap-negative": FORM,
    "cap-twice": "the field 'experimental_cap' appears twice in one object",
}


class Budget(FixtureTest):
    def generate_check(self, name):
        """generate.py --check on a directory that holds only this fixture, as ratchet.json."""
        root = self.scratch()
        shutil.copyfile(self.fixture_file("budget/%s.json" % name), os.path.join(root, "ratchet.json"))
        return run("generate.py", "--check", "--root", root)

    def test_a_cap_that_is_exceeded_or_not_of_its_form_fails_the_check(self):
        self.assertEqual(sorted(list(FAILING) + ["at-cap"]), sorted(name[:-len(".json")] for name in os.listdir(os.path.join(self.fixtures, "budget"))))
        for name, message in sorted(FAILING.items()):
            with self.subTest(fixture=name):
                code, output = self.generate_check(name)
                self.assertEqual(code, 1, output)
                self.assertIn(message, output)
                self.assertTrue(output.startswith("generate: "), "the data file fails before anything is generated: %s" % output)
                self.assertNotIn("Traceback", output)

    def test_experimental_rules_at_the_cap_pass(self):
        data = registry.load(self.fixture_file("budget/at-cap.json"))
        self.assertEqual((data["experimental_cap"], registry.counts(data)["experimental"]["rules"]), (2, 2))
        self.assertEqual(registry.validate(registry.parse_json(self.fixture_bytes("budget/at-cap.json")), ROOT), [])


class RepoBudget(RepoCopy, unittest.TestCase):
    def test_the_cap_is_the_count_on_the_day_of_the_decision_plus_five(self):
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        self.assertEqual(data["experimental_cap"], CAP, "raising the cap is a decision")
        self.assertLessEqual(registry.counts(data)["experimental"]["rules"], CAP)

    def test_one_experimental_rule_over_the_cap_fails_the_check(self):
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        count = registry.counts(data)["experimental"]["rules"]
        self.edit("ratchet.json", '"experimental_cap": %d,' % CAP, '"experimental_cap": %d,' % (count - 1))
        self.assert_check_fails("%d experimental rules, which is more than the cap of %d" % (count, count - 1))

    def test_the_count_text_states_the_cap(self):
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        count = registry.counts(data)["experimental"]["rules"]
        for name in ("README.md", "RATCHET.md", "SELF-IMPROVEMENT.md", "CHANGELOG.md"):
            with self.subTest(file=name):
                self.assertIn("Outside the core there are %d experimental rules, under a cap of %d" % (count, CAP), read(name))


if __name__ == "__main__":
    unittest.main()
