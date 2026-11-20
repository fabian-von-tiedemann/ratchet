"""The budget: ratchet.json caps the number of experimental rules, and generate.py --check fails above the cap.

    python3 -m unittest discover -s checks -v

The cap is the field "experimental_cap" in ratchet.json (D-2026-11-17-pull-and-budget). The fixtures under
checks/fixtures/budget/ are small data files with one core rule and two experimental ones. Each test loads what
it uses through FixtureTest. Also the bookkeeping of D-2026-11-20-proposal-triage, choices 4 and 5: an experimental
rule that enters in this version is adopted in this repo's register or says why Ratchet cannot use it, the rules
that were merged, removed and moved are gone, and ratchet.root-cause names a check. Standard library only.
"""

import json
import os
import shutil
import sys
import unittest

from suite_runner import FixtureTest
from test_checks import ROOT, RepoCopy, read, run

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import check_register  # noqa: E402
import registry  # noqa: E402

# The cap was 25 on the day of D-2026-11-17-pull-and-budget: 20 experimental rules in ratchet.json at the commit on
# main that added that decision, plus five. D-2026-11-20-proposal-triage, choice 5, moved two rules that apply only to
# Ratchet into this repo's own rules and lowered the cap by two, so that the move frees no place.
CAP = 23
# The experimental rules after D-2026-11-20-proposal-triage: 24, one added, one merged into another, three removed and
# two moved into this repo's own rules.
EXPERIMENTAL = 24 + 1 - 1 - 3 - 2
# The rules that D-2026-11-20-proposal-triage, choice 5, takes out of ratchet.json, and where each went.
GONE = {
    "ratchet.cr-background-wait": "merged into ratchet.cr-wake",
    "ratchet.cr-lead-with-ask": "removed",
    "ratchet.cr-reads-first": "removed",
    "ratchet.cr-review": "removed",
    "ratchet.si-version": "repo.version",
    "ratchet.si-maintainer-approves": "repo.maintainer-approves",
}
NOT_USED = "not_used_because"
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
    def test_the_cap_is_lowered_by_the_two_rules_moved_out(self):
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        self.assertEqual(data["experimental_cap"], CAP, "raising the cap is a decision")
        self.assertEqual(registry.counts(data)["experimental"]["rules"], EXPERIMENTAL)
        self.assertLessEqual(EXPERIMENTAL, CAP)

    def test_one_experimental_rule_over_the_cap_fails_the_check(self):
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        count = registry.counts(data)["experimental"]["rules"]
        self.edit("ratchet.json", '"experimental_cap": %d,' % CAP, '"experimental_cap": %d,' % (count - 1))
        self.assert_check_fails("%d experimental rules, which is more than the cap of %d" % (count, count - 1))

    def test_the_phases_are_one_experimental_rule_that_is_text_only(self):
        # D-2026-11-19-locks-not-parsing, item 5: explore, build and run are one rule, outside the core.
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        parts = dict((part["id"], part["file"]) for part in data["parts"])
        self.assertEqual(parts.get("phases"), "CONTROL-ROOM.md")
        rules = [(rule["key"], rule["status"], rule["enforcement"]) for rule in data["rules"] if rule["part"] == "phases"]
        self.assertEqual(rules, [("ratchet.phases", "experimental", "text-only")])
        self.assertFalse([rule["key"] for rule in data["rules"] if rule["key"].startswith("ratchet.phase-")])

    def test_review_by_risk_is_one_experimental_rule_of_the_control_room_that_is_text_only(self):
        # D-2026-11-19-review-by-risk, choices 1 and 3: one rule outside the core, counted against the cap.
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        rules = [(rule["key"], rule["part"], rule["status"], rule["enforcement"]) for rule in data["rules"] if "review-by-risk" in rule["key"]]
        self.assertEqual(rules, [("ratchet.review-by-risk", "control-room", "experimental", "text-only")])
        keys = [rule["key"] for rule in data["rules"]]
        self.assertEqual(keys.index("ratchet.review-by-risk"), keys.index("ratchet.cr-workspace") + 1, "it stands after the rule on workspaces")
        self.assertIn("ratchet.review-by-risk", read("CONTROL-ROOM.md"))

    def test_the_count_text_states_the_cap(self):
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        count = registry.counts(data)["experimental"]["rules"]
        for name in ("README.md", "RATCHET.md", "SELF-IMPROVEMENT.md", "CHANGELOG.md"):
            with self.subTest(file=name):
                self.assertIn("Outside the core there are %d experimental rules, under a cap of %d" % (count, CAP), read(name))


class Triage(RepoCopy, unittest.TestCase):
    """D-2026-11-20-proposal-triage, choices 4 and 5, as they stand in ratchet.json and in this repo's register."""

    def setUp(self):
        super().setUp()
        self.data = registry.load(os.path.join(ROOT, "ratchet.json"))
        self.by_key = registry.rules_by_key(self.data)
        self.register = registry.load_json(os.path.join(ROOT, "register.json"))

    def test_the_merged_removed_and_moved_rules_are_gone_from_ratchet(self):
        for key in GONE:
            with self.subTest(key=key):
                self.assertNotIn(key, self.by_key)
                self.assertNotIn(key, [item["key"] for item in self.register["adopted"]])
                for name in ("CONTROL-ROOM.md", "SELF-IMPROVEMENT.md", "RATCHET.md", "README.md", "REGISTER.md", "UPGRADING.md"):
                    self.assertNotIn(key, read(name), name)

    def test_the_rules_moved_out_stand_in_this_repos_own_rules_with_their_text(self):
        own = dict((item["key"], item) for item in self.register["own"])
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        # ratchet.si-maintainer-approves is as it stood at v0.9. ratchet.si-version changed in 0.10, before it moved, and
        # moves with what 1.0 promises (D-2026-11-19-one-point-oh, choice 1).
        self.assertEqual(own["repo.maintainer-approves"]["rule"], old["ratchet.si-maintainer-approves"]["rule"])
        for words in ("Ratchet is versioned `MAJOR.MINOR`", "Only a major version changes the form of `ratchet.json` or `register.json`",
                      "Before 1.0, a minor version may do these too"):
            self.assertIn(words, own["repo.version"]["rule"])
        self.assertTrue(own["repo.version"]["ratchet"].startswith("Check: `checks/released_text.py`"))

    def released(self, version):
        """The bytes of ratchet.json as it stood at the tag of version, from the fixtures of upgrade.py."""
        with open(os.path.join(ROOT, "checks", "fixtures", "upgrade", "released", version, "ratchet.json"), "rb") as handle:
            return handle.read()

    def test_background_wait_is_merged_into_wake_which_keeps_its_key_and_since(self):
        wake = self.by_key["ratchet.cr-wake"]
        self.assertEqual((wake["since"], wake["status"], wake["part"]), ("0.2", "experimental", "control-room"))
        self.assertIn("A scheduled wake-up reads the feed of new PRs", wake["rule"])
        self.assertIn("keeps its thread alive until the run is done", wake["rule"])

    def test_root_cause_names_a_check_and_this_repo_adopts_it_as_text_only_for_now(self):
        rule = self.by_key["ratchet.root-cause"]
        self.assertEqual((rule["status"], rule["enforcement"]), ("core", "enforced"))
        self.assertTrue(rule["ratchet"].startswith("Check: "))
        self.assertNotIn("reference_check", rule, "Ratchet ships no reference check for it")
        adopted = dict((item["key"], item) for item in self.register["adopted"])
        self.assertEqual(adopted["ratchet.root-cause"]["status"], "text only for now")
        core = registry.counts(self.data)["core"]
        self.assertEqual((core["rules"], core["enforced"], core["text_only"]), (35, 17, 18))

    def test_one_exact_form_enters_as_experimental_and_this_repo_adopts_it(self):
        rule = self.by_key["ratchet.one-exact-form"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["since"]),
                         ("experimental", "text-only", "promoted", self.data["version"]))
        self.assertIn("ratchet.one-exact-form", [item["key"] for item in self.register["adopted"]])

    def rewrite_register(self, change):
        """Change this copy's register.json with change(register), and write its REGISTER.md and the block in AGENTS.md again."""
        path = os.path.join(self.copy, "register.json")
        register = registry.load_json(path)
        change(register)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(register, indent=2, ensure_ascii=False) + "\n")
        with open(os.path.join(self.copy, "REGISTER.md"), "w", encoding="utf-8", newline="") as handle:
            handle.write(check_register.render(register))
        place, problems = check_register.instruction_place(path, register)
        self.assertEqual(problems, [])
        self.assertEqual(check_register.write_block(place, register), [])

    def unadopt(self, key):
        self.rewrite_register(lambda register: register.update(adopted=[item for item in register["adopted"] if item["key"] != key]))

    def give_reason(self, key, reason='"Ratchet runs no such step"'):
        self.edit("ratchet.json", '      "key": "%s",\n' % key, '      "key": "%s",\n      "%s": %s,\n' % (key, NOT_USED, reason))

    def test_a_rule_that_enters_in_this_version_and_is_not_adopted_here_fails(self):
        for key in ("ratchet.review-by-risk", "ratchet.one-exact-form"):
            self.assertEqual(self.by_key[key]["since"], self.data["version"])
        self.unadopt("ratchet.review-by-risk")
        self.assert_check_fails("ratchet.review-by-risk enters Ratchet in %s, and register.json does not adopt it. A rule "
                                "that enters is used by Ratchet itself, or says in %s why Ratchet cannot use it"
                                % (self.data["version"], NOT_USED))

    def test_a_rule_that_enters_and_says_why_ratchet_cannot_use_it_passes(self):
        self.unadopt("ratchet.review-by-risk")
        self.give_reason("ratchet.review-by-risk")
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def test_a_rule_that_this_repo_adopts_and_that_says_ratchet_cannot_use_it_fails(self):
        self.give_reason("ratchet.one-exact-form")
        self.assert_check_fails("ratchet.one-exact-form: register.json adopts it, and %s says Ratchet cannot use it. "
                                "Remove one of the two" % NOT_USED)

    def test_an_older_rule_that_this_repo_does_not_adopt_passes(self):
        self.assertNotEqual(self.by_key["ratchet.cr-handover"]["since"], self.data["version"])
        self.assertNotIn("ratchet.cr-handover", [item["key"] for item in self.register["adopted"]])
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def test_the_reason_is_text_of_its_form_on_an_experimental_rule_only(self):
        for key, reason, message in (
                ("ratchet.root-cause", '"Ratchet runs no such step"', "ratchet.root-cause: only an experimental rule has %s" % NOT_USED),
                ("ratchet.review-by-risk", '"."', "ratchet.review-by-risk: %s must say why, in words" % NOT_USED),
                ("ratchet.review-by-risk", '""', "ratchet.review-by-risk: %s must say why, in words" % NOT_USED),
                ("ratchet.review-by-risk", '"Ratchet runs\u200b no such step"', "ratchet.review-by-risk: %s holds U+200B" % NOT_USED),
                ("ratchet.review-by-risk", "true", "ratchet.review-by-risk: every field must be a string")):
            with self.subTest(reason=reason):
                self.give_reason(key, reason)
                self.assert_check_fails(message)
                self.edit("ratchet.json", '      "%s": %s,\n' % (NOT_USED, reason), "")

    def test_a_misspelled_reason_is_an_unknown_field(self):
        self.edit("ratchet.json", '      "key": "ratchet.review-by-risk",\n',
                  '      "key": "ratchet.review-by-risk",\n      "not_used_becuase": "Ratchet runs no such step",\n')
        self.assert_check_fails("ratchet.review-by-risk: unknown field not_used_becuase")


if __name__ == "__main__":
    unittest.main()
