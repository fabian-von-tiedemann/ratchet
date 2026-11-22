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
# Ratchet into this repo's own rules and lowered the cap by two, so that the move frees no place. D-2026-11-22-second-redraw
# set it to 17: the ten experimental rules left after steps 2 and 3 of its migration, and the seven product rules.
CAP = 17
# The experimental rules after D-2026-11-20-proposal-triage: 24, one added, one merged into another, three removed and
# two moved into this repo's own rules. Step 2 of D-2026-11-22-second-redraw takes out six more: one merged into
# ratchet.cr-wake, and five that leave as a handbook line, as a sentence of another rule, or as a duplicate. Step 3 takes
# out three: one merged into ratchet.si-harden, one moved to CONTRIBUTING.md and one moved into this repo's own rules.
EXPERIMENTAL = 24 + 1 - 1 - 3 - 2 - 6 - 3
# The rules that D-2026-11-20-proposal-triage, choice 5, takes out of ratchet.json, and where each went.
GONE = {
    "ratchet.cr-background-wait": "merged into ratchet.cr-wake",
    "ratchet.cr-lead-with-ask": "removed",
    "ratchet.cr-reads-first": "removed",
    "ratchet.cr-review": "removed",
    "ratchet.si-version": "repo.version",
    "ratchet.si-maintainer-approves": "repo.maintainer-approves",
}
# The rules that step 2 of D-2026-11-22-second-redraw takes out of ratchet.json, with the row of its table of losses.
CLEANED_OUT = {
    "ratchet.cr-does-not-build": "R4, a line of the handbook template",
    "ratchet.cr-analysis-model": "R5, two clauses into ratchet.review-by-risk and a line of the handbook template",
    "ratchet.cr-next-task": "merged into ratchet.cr-wake, whole",
    "ratchet.cr-quiet-hours": "R7, a line of the handbook template",
    "ratchet.cr-verify-reports": "R11, a duplicate of ratchet.evidence-before-done",
    "ratchet.phases": "R8, one sentence into ratchet.cr-workspace and a section of the handbook template",
}
# The rules that step 3 of D-2026-11-22-second-redraw takes out of ratchet.json, and where each went.
LOOP_CLEANED_OUT = {
    "ratchet.si-repeat-is-signal": "merged into ratchet.si-harden, the rule and its count together",
    "ratchet.si-promote": "M1, the same text in CONTRIBUTING.md",
    "ratchet.si-subtract": "M2, the own rule repo.subtract with the same text",
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

    def test_the_phases_are_a_section_of_the_handbook_and_one_sentence_of_cr_workspace(self):
        # D-2026-11-22-second-redraw, R8: the part and the rule are gone, one sentence stands in ratchet.cr-workspace,
        # and the three phases are a section of the handbook template.
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        self.assertNotIn("phases", [part["id"] for part in data["parts"]])
        self.assertFalse([rule["key"] for rule in data["rules"] if rule["key"].startswith("ratchet.phase")])
        workspace = registry.rules_by_key(data)["ratchet.cr-workspace"]
        self.assertIn("Building starts only on a work package the owner approved, and changes only the files it names.", workspace["rule"])
        handbook = read(os.path.join("templates", "CONTROL-ROOM-HANDBOOK.md"))
        for words in ("## Phases", "**Explore.**", "**Build.**", "**Run.**"):
            self.assertIn(words, handbook)
        self.assertNotIn("## The phases", read("CONTROL-ROOM.md"))

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

    def test_the_control_rooms_cleaned_out_rules_are_gone_and_their_lines_stand_in_the_handbook(self):
        # D-2026-11-22-second-redraw, step 2 of the migration: a handbook line is added in the PR in which its rule leaves.
        for key in CLEANED_OUT:
            with self.subTest(key=key):
                self.assertNotIn(key, self.by_key)
                self.assertNotIn(key, [item["key"] for item in self.register["adopted"]])
                for name in ("CONTROL-ROOM.md", "SELF-IMPROVEMENT.md", "RATCHET.md", "README.md", "REGISTER.md", "AGENTS.md"):
                    self.assertNotIn(key, read(name), name)
        handbook = read(os.path.join("templates", "CONTROL-ROOM-HANDBOOK.md"))
        for words in ("The control room does not build the product.",
                      "Overall, scope and architecture assessments run on the strongest model the project has.",
                      "Hourly is a good default for the wake-up, with a full status update every second time.",
                      "During the owner's quiet hours"):
            self.assertIn(words, handbook)
        wake = self.by_key["ratchet.cr-wake"]["rule"]
        self.assertIn("When nobody asks anything, the control room takes the next permitted task.", wake)
        self.assertNotIn("Hourly", wake)
        review = self.by_key["ratchet.review-by-risk"]["rule"]
        self.assertIn("Overall, scope and architecture assessments run in a fresh context.", review)
        self.assertIn("There is no silent switch to another model.", review)
        self.assertIn("A test is in the full class even when it is only added to", review)

    def test_this_repos_review_classes_are_an_own_rule_and_no_longer_in_the_rule_of_ratchet(self):
        # D-2026-11-22-second-redraw, M3: the paths of Ratchet's own classes move word for word into an own rule.
        own = dict((item["key"], item) for item in self.register["own"])
        classes = own["repo.review-classes"]["rule"]
        for words in ("The light class is the directory `docs/`, the landing page, and `CHANGELOG.md`",
                      "a release also changes `RATCHET.md` and gets the full review",
                      "`sources.json` and `decisions/`. A mixed PR gets the full review."):
            self.assertIn(words, classes)
        for path in ("`docs/`", "`CHANGELOG.md`", "`decisions/`", "`templates/`"):
            self.assertNotIn(path, self.by_key["ratchet.review-by-risk"]["rule"])

    def test_the_loops_cleaned_out_rules_are_gone_and_stand_where_the_decision_put_them(self):
        # D-2026-11-22-second-redraw, step 3 of the migration, and the rows M1 and M2 of its table of losses.
        for key in LOOP_CLEANED_OUT:
            with self.subTest(key=key):
                self.assertNotIn(key, self.by_key)
                self.assertNotIn(key, [item["key"] for item in self.register["adopted"]])
                for name in ("CONTROL-ROOM.md", "SELF-IMPROVEMENT.md", "RATCHET.md", "README.md", "REGISTER.md", "AGENTS.md",
                             "CONTRIBUTING.md", os.path.join("templates", "LESSON.md")):
                    self.assertNotIn(key, read(name), name)
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        # M1: the text of ratchet.si-promote, unchanged since 0.9, stands in CONTRIBUTING.md.
        self.assertIn("> " + old["ratchet.si-promote"]["rule"] + "\n", read("CONTRIBUTING.md"))
        # M2: the own rule has the rule and the ratchet of ratchet.si-subtract as 0.10 left it.
        own = dict((item["key"], item) for item in self.register["own"])
        self.assertEqual(own["repo.subtract"]["rule"],
                         "A core rule may be removed only when a check covers it completely, or when a stronger or simpler rule "
                         "replaces it. A core rule that has never been triggered is a candidate for review, not for removal. An "
                         "experimental rule may also be removed in the clean-out at a release, once it has stood through three "
                         "releases and 60 days with no decision to keep it.")
        self.assertEqual(own["repo.subtract"]["ratchet"], "Text only: a check cannot judge whether a check covers a rule completely")

    def test_si_harden_holds_the_repeat_and_its_count_and_says_what_makes_a_check_built(self):
        # D-2026-11-22-second-redraw: si-harden takes ratchet.si-repeat-is-signal, the rule and its count together, and the
        # definition of "built" by enforcement point (T6), which is a convention, text only for the enforcement half.
        harden = self.by_key["ratchet.si-harden"]
        self.assertEqual((harden["status"], harden["enforcement"], harden["since"], harden["part"]),
                         ("experimental", "enforced", "0.2", "tightening"))
        for words in ('A rule whose ratchet is "text only" is turned into a check as soon as a check can see it.',
                      "failed at least once on a real or seeded violation", "only where it can refuse",
                      "a merge check is required for the merge and reads its rules from the base branch",
                      "a hook runs in every harness the project uses",
                      "a scheduled check posts its result and is red when the post is late",
                      "no deploy can run without a deploy check",
                      "When a failure class comes back after a lesson, the lesson's ratchet was too weak.",
                      "Strengthen the ratchet.", "Rewording the rule does not count."):
            self.assertIn(words, harden["rule"])
        for words in ("Check: the periodic count of rules by kind of ratchet", "and of repeated failure classes", "a convention"):
            self.assertIn(words, harden["ratchet"])
        self.assertEqual(harden["source"], "pstack `principle-encode-lessons-in-structure`")
        glossary = read("GLOSSARY.md")
        self.assertIn("| built | ", glossary)
        for words in ("required for the merge and reads its rules from the base branch", "runs in every harness the project uses",
                      "is red when the post is late", "no deploy can run without it", "This is a convention, not something a check verifies"):
            self.assertIn(words, glossary)

    def test_the_six_merge_checks_that_run_the_prs_own_checks_are_not_built(self):
        # D-2026-11-22-second-redraw, built by enforcement point: a merge check is built only when it reads its rules from
        # the base branch. The job `checks` runs the PR's own checks and rule data, so these six stay text only for now
        # until it runs the base branch's, and each `where` says what is missing.
        register = json.loads(read("register.json"))
        entries = {entry["key"]: entry for entry in register["adopted"] + register["own"]}
        for key in ("ratchet.register-on-top", "ratchet.expected-tests-ran", "repo.rules-as-data",
                    "repo.checks-fail-on-fixtures", "repo.version", "repo.new-rule-used"):
            self.assertEqual(entries[key]["status"], "text only for now", key)
            for words in ("Not built.", "required for the merge", "the PR's own checks and rule data, not the base branch's"):
                self.assertIn(words, entries[key]["where"], key)

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
                         ("experimental", "text-only", "promoted", "0.10"))
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
        with open(place, encoding="utf-8", newline="") as handle:
            text, problems = check_register.with_block(handle.read(), register, place)
        self.assertEqual(problems, [])
        with open(place, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def unadopt(self, key):
        self.rewrite_register(lambda register: register.update(adopted=[item for item in register["adopted"] if item["key"] != key]))

    def enter_now(self, key):
        """Make key, in this copy's ratchet.json, a rule that enters in the version of the file."""
        rule = self.by_key[key]
        fields = '      "key": "%s",\n      "part": "%s",\n      "principle": "%s",\n      "status": "experimental",\n      "since": ' % (
            key, rule["part"], rule["principle"])
        self.edit("ratchet.json", fields + '"%s"' % rule["since"], fields + '"%s"' % self.data["version"])

    def give_reason(self, key, reason='"Ratchet runs no such step"'):
        self.edit("ratchet.json", '      "key": "%s",\n' % key, '      "key": "%s",\n      "%s": %s,\n' % (key, NOT_USED, reason))

    def test_a_rule_that_enters_in_this_version_and_is_not_adopted_here_fails(self):
        # No rule enters in 0.11, so the copy makes ratchet.review-by-risk enter in the version of the file.
        self.enter_now("ratchet.review-by-risk")
        self.unadopt("ratchet.review-by-risk")
        self.assert_check_fails("ratchet.review-by-risk enters Ratchet in %s, and register.json does not adopt it. A rule "
                                "that enters is used by Ratchet itself, or says in %s why Ratchet cannot use it"
                                % (self.data["version"], NOT_USED))

    def test_a_rule_that_enters_and_says_why_ratchet_cannot_use_it_passes(self):
        self.enter_now("ratchet.review-by-risk")
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
