"""The budget: ratchet.json caps the number of experimental rules, and generate.py --check fails above the cap.

    python3 -m unittest discover -s checks -v

The cap is the field "experimental_cap" in ratchet.json (D-2026-11-17-pull-and-budget). The fixtures under
checks/fixtures/budget/ are small data files with one core rule and two experimental ones. Each test loads what
it uses through FixtureTest. Also the bookkeeping of D-2026-11-20-proposal-triage, choices 4 and 5: an experimental
rule that enters in this version is adopted in this repo's register or says why Ratchet cannot use it, the rules
that were merged, removed and moved are gone, and ratchet.root-cause names a check. Standard library only.
"""

import copy
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

from suite_runner import FixtureTest
from test_checks import ROOT, RepoCopy, read, run

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import check_register  # noqa: E402
# The scripts of Ratchet's own maintenance stand in maintain/, beside checks/ (D-2026-11-27-maintain-apart).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maintain"))
import from_base  # noqa: E402
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
# Step 12 adds the seven rules of the product module, which brings the count to the cap.
EXPERIMENTAL = 24 + 1 - 1 - 3 - 2 - 6 - 3 + 7
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
# The rules that step 8 of D-2026-11-22-second-redraw, core batch A, takes out of ratchet.json, and where each went.
CORE_BATCH_A_OUT = {
    "ratchet.one-approver": "into ratchet.owner-paths, whole",
    "ratchet.checks-owner-read": "into ratchet.owner-paths, whole, tightened by T4",
    "ratchet.one-channel": "into ratchet.ask-the-owner, whole",
    "ratchet.five-choices": "into ratchet.ask-the-owner, whole",
    "ratchet.look-up-facts": "into ratchet.ask-the-owner, whole",
    "ratchet.experiment-plan": "R9, the spending approval and the backstop into ratchet.ask-the-owner word for word",
    "ratchet.glossary": "L3, the own rule repo.glossary with the same text",
    "ratchet.grill-first": "R1, a line of the handbook template, and its number leaves ratchet.si-measure",
    "ratchet.kinds-apart": "M5, a line of the handbook template and the own rule repo.kinds-apart",
}
# The rules that step 10 of D-2026-11-22-second-redraw, core batch B, takes out of ratchet.json, and where each went.
CORE_BATCH_B_OUT = {
    "ratchet.once-per-version": "into ratchet.fresh-context, with its lock per PR, head and model",
    "ratchet.register-review-first": "into ratchet.fresh-context, whole",
    "ratchet.findings-marked": "into ratchet.evidence-before-done, without the marks of R2",
    "ratchet.verify-findings": "into ratchet.evidence-before-done, whole",
    "ratchet.run-early": "R3, a line of the handbook template",
}
# The rules that step 11 of D-2026-11-22-second-redraw, core batch C, takes out of ratchet.json, and where each went.
CORE_BATCH_C_OUT = {
    "ratchet.reuse-first": "into ratchet.simplest, whole",
    "ratchet.slices": "into ratchet.simplest, whole",
    "ratchet.test-first": "into ratchet.test-can-fail, whole",
    "ratchet.lesson-loop": "into ratchet.lesson-names-check, without \"at most three\" (R10)",
    "ratchet.nightly-visible": "renamed ratchet.silence-is-red and widened (T1)",
}
# Where a rule of core batch A, B or C could still be cited. The changelog and the decisions keep the old keys as history.
CITING = ("AGENTS.md", "CONTRIBUTING.md", "CONTROL-ROOM.md", "GLOSSARY.md", "HANDOVER.md", "PRODUCT.md", "RATCHET.md",
          "README.md", "REGISTER.md", "SELF-IMPROVEMENT.md", "STARTING.md", "UPGRADING.md",
          os.path.join("checks", "README.md"),
          os.path.join("docs", "index.html"), os.path.join("templates", "AGENTS.md"),
          os.path.join("templates", "CONTROL-ROOM-HANDBOOK.md"), os.path.join("templates", "GLOSSARY.md"))
# The sentence D-2026-11-22-owner-reads-outside-gates puts back into ratchet.owner-paths, as the maintainer's second answer
# has it: it covers a setting outside the repo that a check depends on, such as a variable of the host.
OUTSIDE_GATES = ("Checks, gates and automated reviewers, and the settings outside the repo they depend on, such as the host's "
                 "rules, its variables or the brief and model of an automated reviewer, change only after the owner has read "
                 "the change.")
# The first wording, which the second answer replaced. The decision quotes it in the second question.
FIRST_WORDING = ("Checks, gates and automated reviewers that act outside the repo, such as the host's rules or the brief and "
                 "model of an automated reviewer, change only after the owner has read the change.")
NOT_USED = "not_used_because"
OVER = "experimental rules, which is more than the cap of"
FORM = "experimental_cap must be a whole number from 0"

# Every entry of this repo's register that is built, with the command of maintain/from_base.py that the base branch runs
# for it (D-2026-11-22-second-redraw, built by enforcement point). An entry marked built that is not here fails.
ENFORCED = {
    "ratchet.register-on-top": ("checks/check_register.py", "register.json", "--markdown", "REGISTER.md"),
    "ratchet.expected-tests-ran": ("checks/expected_tests.py",),
    "repo.rules-as-data": ("maintain/generate.py", "--check"),
    "repo.checks-fail-on-fixtures": ("checks/expected_tests.py",),
    "repo.version": ("maintain/released_text.py",),
    "repo.new-rule-used": ("maintain/generate.py", "--check"),
    "repo.short-pages": ("maintain/generate.py", "--check"),
    "ratchet.decision-as-file": ("maintain/generate.py", "--check"),
}
# What every such `where` says: the enforcement point, when it was read back, and that the base branch's script runs.
POINT = ("Enforced at the merge: the ruleset on `main` requires the job `checks` of `.github/workflows/checks.yml`, read back on ",
         "and on a pull request that job passes only when the job `base` passes. The job `base` takes `maintain/from_base.py` "
         "from the base commit, never from the pull request, and it runs the base branch's ")
# What the workflow must hold for that to be so: the job base takes from_base.py from the base commit and runs it in
# isolation, and the job checks waits for it, runs whatever it did, and fails on a pull request unless it passed.
SHOWN = (
    "  base:\n    if: github.event_name == 'pull_request'\n",
    'git show "HEAD^1:maintain/from_base.py" > "$judge/from_base.py"',
    'python3 -I "$judge/from_base.py" --base-sha "$BASE_SHA" --head-sha "$HEAD_SHA"',
    "  checks:\n    needs: [own, base, released]\n    if: always()\n",
    'if [ "$EVENT" = pull_request ] && [ "$BASE" != success ]; then',
)


def register_where(register, key):
    return {entry["key"]: entry for entry in register["adopted"] + register["own"]}[key]["where"]


def enforcement_problems(register, workflow, commands):
    """Why the entries marked built in a register are not shown to be enforced where they can refuse, each as a line."""
    problems = []
    missing = [text for text in SHOWN if text not in workflow]
    if missing:
        problems.append("the workflow does not show the job base and the job checks that waits for it: %r is missing" % missing[0])
    if "pull_request_target" in workflow:
        problems.append("the workflow names pull_request_target, which runs the base's workflow with the base's rights")
    for entry in register["adopted"] + register["own"]:
        if entry.get("status") != "built":
            continue
        key, where = entry["key"], entry.get("where", "")
        if key not in ENFORCED:
            problems.append("%s is built, and no enforcement point is stated for it in ENFORCED" % key)
            continue
        command = ENFORCED[key]
        if not all(part in where for part in POINT):
            problems.append("%s: its where does not say where it is enforced and when that was read back" % key)
        if "`%s" % command[0] not in where:
            problems.append("%s: its where does not name `%s`" % (key, command[0]))
        if tuple(command) not in [tuple(each) for each in commands]:
            problems.append("%s: the base branch does not run %s" % (key, " ".join(command)))
    return problems


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


def decision_name_problems(folder):
    """Every entry of a folder of decisions that is not a plain file, not through a link, named D-YYYY-MM-DD-<slug>.md
    with a date that exists, sorted."""
    problems = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if (os.path.islink(path) or not os.path.isfile(path) or not name.endswith(".md")
                or registry.decision_date(name[:-3]) is None):
            problems.append(name)
    return problems


def sole_owner(text):
    """The owner, when a CODEOWNERS file is exactly one line, "*", one space, one owner and a line feed. Else None."""
    if text.count("\n") != 1 or not text.endswith("\n"):
        return None
    parts = text[:-1].split(" ")
    if len(parts) != 2 or parts[0] != "*" or not parts[1].startswith("@") or len(parts[1]) < 2:
        return None
    if not all(character.isascii() and (character.isalnum() or character in "-_/") for character in parts[1][1:]):
        return None
    return parts[1]


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
        for name in ("RATCHET.md", "SELF-IMPROVEMENT.md", "CHANGELOG.md"):
            with self.subTest(file=name):
                self.assertIn("Outside the core there are %d experimental rules, under a cap of %d" % (count, CAP), read(name))


class Triage(RepoCopy, FixtureTest):
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
                for name in ("CONTROL-ROOM.md", "SELF-IMPROVEMENT.md", "RATCHET.md", "README.md", "STARTING.md", "REGISTER.md", "UPGRADING.md"):
                    self.assertNotIn(key, read(name), name)

    def test_the_rules_moved_out_stand_in_this_repos_own_rules_with_their_text(self):
        own = dict((item["key"], item) for item in self.register["own"])
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        # ratchet.si-maintainer-approves is as it stood at v0.9. ratchet.si-version changed in 0.10, before it moved, and
        # moves with what 1.0 promises (D-2026-11-19-one-point-oh, choice 1).
        # The key it cites, ratchet.checks-owner-read, merged into ratchet.owner-paths in step 8 of D-2026-11-22-second-redraw.
        self.assertEqual(own["repo.maintainer-approves"]["rule"],
                         old["ratchet.si-maintainer-approves"]["rule"].replace("`ratchet.checks-owner-read`", "`ratchet.owner-paths`"))
        for words in ("Ratchet is versioned `MAJOR.MINOR`", "Only a major version changes the form of `ratchet.json` or `register.json`",
                      "Before 1.0, a minor version may do these too"):
            self.assertIn(words, own["repo.version"]["rule"])
        self.assertTrue(own["repo.version"]["ratchet"].startswith("Check: `maintain/released_text.py`"))

    def released(self, version):
        """The bytes of ratchet.json as it stood at the tag of version, 0.3 or 0.9, kept under the fixtures of upgrade.py
        for these tests when its registers of 0.3 to 0.9 left (D-2026-11-23-support-from-0-12). Loaded as a fixture, so
        that expected_tests.py sees that a test uses it."""
        return self.fixture_bytes("upgrade/released/%s/ratchet.json" % version)

    def test_the_control_rooms_cleaned_out_rules_are_gone_and_their_lines_stand_in_the_handbook(self):
        # D-2026-11-22-second-redraw, step 2 of the migration: a handbook line is added in the PR in which its rule leaves.
        for key in CLEANED_OUT:
            with self.subTest(key=key):
                self.assertNotIn(key, self.by_key)
                self.assertNotIn(key, [item["key"] for item in self.register["adopted"]])
                for name in ("CONTROL-ROOM.md", "SELF-IMPROVEMENT.md", "RATCHET.md", "README.md", "STARTING.md", "REGISTER.md", "AGENTS.md"):
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
                for name in ("CONTROL-ROOM.md", "SELF-IMPROVEMENT.md", "RATCHET.md", "README.md", "STARTING.md", "REGISTER.md", "AGENTS.md",
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
                      "Strengthen the ratchet.", "Rewording the rule does not count.",
                      # D-2026-11-24-recurring-finding-is-a-failure-class: the clause, word for word as approved.
                      "A review finding that recurs is a failure class: it becomes a check, for code usually a rule of the "
                      "project's linter in the required job, with a fixture it fails on."):
            self.assertIn(words, harden["rule"])
        for words in ("Check: the periodic count of rules by kind of ratchet", "and of repeated failure classes", "a convention"):
            self.assertIn(words, harden["ratchet"])
        self.assertEqual(harden["source"], "pstack `principle-encode-lessons-in-structure`; "
                                           "sprocketlab/slop-code-bench, which measures how agent-written code erodes across iterations")
        glossary = read("GLOSSARY.md")
        self.assertIn("| built | ", glossary)
        for words in ("required for the merge and reads its rules from the base branch", "runs in every harness the project uses",
                      "is red when the post is late", "no deploy can run without it", "This is a convention, not something a check verifies"):
            self.assertIn(words, glossary)

    def test_every_built_entry_names_an_enforcement_point_that_the_repo_shows(self):
        # D-2026-11-22-second-redraw, built by enforcement point: a merge check is built only when it is required for the
        # merge and reads its rules from the base branch. Each entry marked built is in ENFORCED, with the command the
        # base branch runs for it, its `where` names that enforcement point, and the workflow and maintain/from_base.py
        # show it. What is required for the merge is a setting of the host, which no check here can read: the `where`
        # says when it was read back.
        register = json.loads(read("register.json"))
        problems = enforcement_problems(register, read(".github", "workflows", "checks.yml"), from_base.DATA_COMMANDS + from_base.CODE_COMMANDS)
        self.assertEqual(problems, [])
        built = sorted(entry["key"] for entry in register["adopted"] + register["own"] if entry.get("status") == "built")
        self.assertEqual(built, sorted(ENFORCED))

    def test_a_claim_of_built_that_the_repo_does_not_show_fails(self):
        register = json.loads(read("register.json"))
        workflow = read(".github", "workflows", "checks.yml")
        commands = from_base.DATA_COMMANDS + from_base.CODE_COMMANDS

        def with_entry(key, **change):
            changed = copy.deepcopy(register)
            for entry in changed["adopted"] + changed["own"]:
                if entry["key"] == key:
                    entry.update(change)
            return changed

        cases = {
            "a built entry with no enforcement point": (with_entry("ratchet.root-cause", status="built", where="In CI"), workflow, commands,
                                                        "ratchet.root-cause is built, and no enforcement point is stated for it"),
            "a where that does not name the point": (with_entry("repo.version", where="`maintain/released_text.py` runs in CI"), workflow, commands,
                                                     "repo.version: its where does not say"),
            "a where that names another check": (with_entry("repo.version", where=register_where(register, "repo.rules-as-data")), workflow, commands,
                                                 "repo.version: its where does not name `maintain/released_text.py`"),
            "a workflow with no job base": (register, workflow.replace('git show "HEAD^1:maintain/from_base.py"', 'cat maintain/from_base.py'), commands,
                                            "the workflow does not show"),
            "a job checks that does not wait for base": (register, workflow.replace("needs: [own, base, released]", "needs: [own, released]"), commands,
                                                         "the workflow does not show"),
            "a base that runs on pull_request_target": (register, workflow + "\n# pull_request_target\n", commands,
                                                        "pull_request_target"),
            "a command the base does not run": (register, workflow, [c for c in commands if c[0] != "maintain/released_text.py"],
                                                "repo.version: the base branch does not run maintain/released_text.py"),
        }
        for name, (changed, text, given, words) in cases.items():
            with self.subTest(name):
                problems = enforcement_problems(changed, text, given)
                self.assertTrue(any(words in problem for problem in problems), problems)

    def test_the_tripwire_is_not_built_since_it_runs_in_one_harness(self):
        # A hook is built only when it runs in every harness the project uses. The tripwire of ratchet.irreversible-waits
        # runs as a hook only in Claude Code, and Codex also works on this repo.
        register = json.loads(read("register.json"))
        waits = {entry["key"]: entry for entry in register["adopted"]}["ratchet.irreversible-waits"]
        self.assertEqual(waits["status"], "text only for now")
        self.assertTrue(waits["where"].startswith("Not built. "), waits["where"])
        for words in ("runs as a hook only in Claude Code", "`.claude/settings.json`",
                      "Codex and the other harnesses that work on this repo do not run it",
                      "the hook does not run in every harness this repo uses"):
            self.assertIn(words, waits["where"])

    def test_core_batch_a_rules_are_gone_and_stand_where_the_decision_put_them(self):
        # D-2026-11-22-second-redraw, step 8 of the migration: each rule that leaves is gone from ratchet.json, from this
        # repo's register and from every file that cites rules, and a handbook line is added in the PR in which its rule
        # leaves.
        for key in CORE_BATCH_A_OUT:
            with self.subTest(key=key):
                self.assertNotIn(key, self.by_key)
                self.assertNotIn(key, [item["key"] for item in self.register["adopted"]])
                for name in CITING:
                    self.assertNotIn(key, read(name), name)
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        own = dict((item["key"], item) for item in self.register["own"])
        # L3 and M5: the glossary and the four letters are rules of Ratchet's own, with the text they had in the core.
        for key, was in (("repo.glossary", "ratchet.glossary"), ("repo.kinds-apart", "ratchet.kinds-apart")):
            self.assertEqual((own[key]["rule"], own[key]["ratchet"]), (old[was]["rule"], old[was]["ratchet"]), key)
        handbook = read(os.path.join("templates", "CONTROL-ROOM-HANDBOOK.md"))
        # R1: the interview before the work, with what the rule asked of it.
        for words in ("Before a new project or a large work package: interview the owner with `grilling`",
                      "with a recommended answer for each question, until no decision is left as an unstated assumption."):
            self.assertIn(words, handbook)
        # M5: the four letters.
        self.assertIn("Keep four kinds of statement apart and label them: decision (D), proposal (P), outside observation (O) "
                      "and open question (Q).", handbook)
        # R1: the number of ratchet.grill-first leaves ratchet.si-measure, and the overhead takes its place (M4). Word for
        # word, the rule and its ratchet, as for ratchet.owner-paths, ratchet.ask-the-owner and ratchet.decision-as-file
        # (the review at 18d1ce8).
        self.assertEqual(self.by_key["ratchet.si-measure"]["rule"],
                         "Every two weeks, the project reports four numbers: review rounds before approval, the steps and "
                         "minutes its last upgrade of Ratchet took, repeated failure classes, and the share of rules enforced by "
                         "a check. The trend goes in the status issue. With each release of Ratchet, the steps and minutes to "
                         "adopt it in an empty repo and to upgrade it by one version are recorded in its changelog.")
        self.assertEqual(self.by_key["ratchet.si-measure"]["ratchet"],
                         "Check: the report is a scheduled job, and the status issue shows the date of the last one. No check "
                         "sees the record with a release")
        measure = self.by_key["ratchet.si-measure"]["rule"]
        self.assertNotIn("decisions that came up after work started", measure)
        self.assertIn("four numbers", measure)
        self.assertIn("the steps and minutes its last upgrade of Ratchet took", measure)
        self.assertNotIn("decisions come up after work has started", read("SELF-IMPROVEMENT.md"))
        # M4, "stays as decided" (the review of step 8): D-2026-11-21-inventory-and-easy-upgrade records the steps and
        # minutes to adopt Ratchet in an empty repo and to upgrade by one version with each release, and the two-weekly
        # report keeps the adopter's own number beside it.
        self.assertIn("With each release of Ratchet, the steps and minutes to adopt it in an empty repo and to upgrade it by "
                      "one version are recorded in its changelog.", measure)
        self.assertIn("No check sees the record with a release", self.by_key["ratchet.si-measure"]["ratchet"])
        self.assertIn("records in the new version's entry of the changelog the steps and minutes to adopt Ratchet in an empty "
                      "repo and to upgrade by one version (`ratchet.si-measure`, ", read("AGENTS.md"))

    def test_every_rule_of_0_2_that_is_no_longer_in_ratchet_left_in_a_named_step(self):
        # Read from v0.2's tables, which the fixture of 0.3 holds key for key, and from ratchet.json as it stands, six left
        # in 0.10 and, after step 11, 27 in 0.11. A rule of 0.2 that leaves outside the steps named here makes this fail.
        then = set(registry.rules_by_key(registry.parse_json(self.released("0.3"))))
        tenth = then - set(GONE)
        gone = sorted(tenth - set(self.by_key))
        self.assertEqual(sorted(then - set(self.by_key) - set(gone)), sorted(GONE))
        self.assertEqual(len(gone), 27)
        # Step 2 took out six, of which ratchet.phases entered in 0.6, step 3 three, step 8 nine, step 10 five and step
        # 11 five.
        self.assertEqual(gone, sorted(set(CLEANED_OUT) - {"ratchet.phases"} | set(LOOP_CLEANED_OUT) | set(CORE_BATCH_A_OUT)
                                      | set(CORE_BATCH_B_OUT) | set(CORE_BATCH_C_OUT)))

    def test_core_batch_b_rules_are_gone_and_stand_where_the_decision_put_them(self):
        # D-2026-11-22-second-redraw, step 10 of the migration: each rule that leaves is gone from ratchet.json, from this
        # repo's register and from every file that cites rules, and the handbook line of ratchet.run-early is added in
        # the PR in which it leaves (R3).
        for key in CORE_BATCH_B_OUT:
            with self.subTest(key=key):
                self.assertNotIn(key, self.by_key)
                self.assertNotIn(key, [item["key"] for item in self.register["adopted"]])
                for name in CITING:
                    self.assertNotIn(key, read(name), name)
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        handbook = read(os.path.join("templates", "CONTROL-ROOM-HANDBOOK.md"))
        # R3: the rule of ratchet.run-early, whole, and from its ratchet the standing approval for local experiments.
        self.assertIn("- %s A standing approval for local experiments at no cost removes the excuse.\n"
                      % old["ratchet.run-early"]["rule"], handbook)
        self.assertIn("A standing approval for local experiments at no cost removes the excuse", old["ratchet.run-early"]["ratchet"])
        # The review script leans on two rules of the core now, not three.
        for name in ("RATCHET.md", "CONTROL-ROOM.md"):
            self.assertIn("`ratchet.fresh-context` and `ratchet.two-rounds`", read(name), name)

    def test_fresh_context_holds_once_per_version_and_register_review_first_whole(self):
        # D-2026-11-22-second-redraw: ratchet.fresh-context is kept and takes ratchet.once-per-version, with its lock per
        # PR, head and model, and ratchet.register-review-first, whole. One check, the review script's, stands under it,
        # and the ratchet says in words that the review before the merge of a change to the register is text only.
        rule = self.by_key["ratchet.fresh-context"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["principle"], rule["source"]),
                         ("core", "enforced", "review", "principle.independent-gate",
                          "google/elephant-goldfish-model (the fresh context)"))
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        for key in ("ratchet.fresh-context", "ratchet.once-per-version", "ratchet.register-review-first"):
            with self.subTest(key=key):
                self.assertIn(old[key]["rule"], rule["rule"])
        self.assertEqual(rule["rule"], " ".join(old[key]["rule"] for key in (
            "ratchet.fresh-context", "ratchet.once-per-version", "ratchet.register-review-first")))
        self.assertTrue(rule["ratchet"].startswith(old["ratchet.fresh-context"]["ratchet"] + ", and keeps a lock file per PR, head and model."))
        self.assertEqual(old["ratchet.once-per-version"]["ratchet"], "Check: the review script keeps a lock file per PR, head and model")
        self.assertIn("is text only until the project's merge check can see review outcomes", rule["ratchet"])
        self.assertEqual(old["ratchet.register-review-first"]["ratchet"], "Text only until the project's merge check can see review outcomes")
        self.assertIn("ratchet.fresh-context", self.data["start"])

    def test_evidence_before_done_holds_the_findings_rules_and_t3_and_drops_only_the_marks_of_r2(self):
        # D-2026-11-22-second-redraw: ratchet.evidence-before-done is kept, with T3, and takes ratchet.findings-marked
        # without the marks "standards" and "spec" (R2) and ratchet.verify-findings, whole. It stays text only.
        rule = self.by_key["ratchet.evidence-before-done"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["principle"]),
                         ("core", "text-only", "building", "principle.show-the-run"))
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        was = old["ratchet.evidence-before-done"]["rule"]
        first = "No claim that something is done without a check run just now, shown with the command and its result."
        self.assertTrue(was.startswith(first + " "))
        # T3, the decision's two clauses, in its words.
        t3 = "A claim shows the head it ran on, and for a change a user sees, the run shows what the user sees."
        self.assertIn(first + " " + t3 + " " + was[len(first) + 1:], rule["rule"])
        self.assertIn('A subagent\'s "done" is checked independently.', rule["rule"])
        self.assertIn(old["ratchet.verify-findings"]["rule"], rule["rule"])
        marked = old["ratchet.findings-marked"]["rule"]
        r2 = ('It is also marked "standards" (breaks the repo\'s documented rules) or "spec" (does not do what the issue '
              'asked). ')
        self.assertIn(r2, marked)
        self.assertIn(marked.replace(r2, ""), rule["rule"])
        for mark in ('"standards"', '"spec"'):
            self.assertNotIn(mark, rule["rule"])
        for words in ("Text only: a check cannot see a claim made in a message", "whether a finding was verified",
                      "a script can see that a finding's marks are there, not that they are true",
                      "Required checks on the PR head cover the claims they run"):
            self.assertIn(words, rule["ratchet"])
        self.assertEqual(registry.cited_names(rule), ["obra/superpowers", "pstack", "mattpocock/skills"])
        for key in ("ratchet.evidence-before-done", "ratchet.verify-findings", "ratchet.findings-marked"):
            for part in old[key]["source"].split("; "):
                with self.subTest(source=part):
                    name, what = part.split(" ", 1)
                    self.assertIn(what.split(",")[0], rule["source"])
        self.assertIn("ratchet.evidence-before-done", self.data["start"])
        # This repo adopts the new entry, which is text only and so has no status.
        adopted = dict((item["key"], item) for item in self.register["adopted"])
        self.assertEqual(adopted["ratchet.evidence-before-done"],
                         {"key": "ratchet.evidence-before-done", "rule": rule["rule"], "ratchet": rule["ratchet"], "source": rule["source"]})

    def test_core_batch_c_rules_are_gone_and_stand_where_the_decision_put_them(self):
        # D-2026-11-22-second-redraw, step 11 of the migration: each rule that leaves is gone from ratchet.json, from this
        # repo's register and from every file that cites rules. "At most three" lessons is gone from the rule and from the
        # handbook template's checklist too (R10).
        for key in CORE_BATCH_C_OUT:
            with self.subTest(key=key):
                self.assertNotIn(key, self.by_key)
                self.assertNotIn(key, [item["key"] for item in self.register["adopted"]])
                for name in CITING:
                    self.assertNotIn(key, read(name), name)
        handbook = read(os.path.join("templates", "CONTROL-ROOM-HANDBOOK.md"))
        self.assertIn("- [ ] After a failed review or a failed experiment: propose lessons with the lesson template.\n", handbook)
        for name in CITING:
            self.assertNotIn("at most three lessons", read(name), name)
        self.assertIn("The project's owner approves the lesson (`ratchet.lesson-names-check`).", read("SELF-IMPROVEMENT.md"))

    def test_simplest_holds_reuse_first_and_slices_whole(self):
        # D-2026-11-22-second-redraw: ratchet.simplest is kept and takes ratchet.reuse-first and ratchet.slices, whole. All
        # three are text only (merge rule 1), so the ratchet keeps each reason.
        rule = self.by_key["ratchet.simplest"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["principle"]),
                         ("core", "text-only", "building", "principle.subtract-first"))
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        self.assertEqual(rule["rule"], " ".join(old[key]["rule"] for key in ("ratchet.simplest", "ratchet.reuse-first", "ratchet.slices")))
        self.assertIn("New code is justified against a requirement and a simpler alternative.", rule["rule"])
        self.assertIn("with dependencies and acceptance criteria", rule["rule"])
        self.assertTrue(rule["ratchet"].startswith(old["ratchet.simplest"]["ratchet"] + ", "))
        for key in ("ratchet.reuse-first", "ratchet.slices"):
            self.assertIn(old[key]["ratchet"][len("Text only: "):], rule["ratchet"], key)
        self.assertEqual(rule["source"], old["ratchet.simplest"]["source"] + "; " + old["ratchet.slices"]["source"])

    def test_test_can_fail_holds_test_first_whole_and_the_schedule_of_l4(self):
        # D-2026-11-22-second-redraw: ratchet.test-can-fail is kept and takes ratchet.test-first, whole. Both name mutation
        # testing, one mechanism. L4 lets mutations run on a schedule the project sets, and a scheduled run names the
        # revision it tested, posts its result, and is red when a mutation survives or when its last run is too old.
        rule = self.by_key["ratchet.test-can-fail"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["principle"]),
                         ("core", "enforced", "building", "principle.checks-that-fail"))
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        self.assertEqual(rule["rule"], old["ratchet.test-can-fail"]["rule"] + " " + old["ratchet.test-first"]["rule"])
        self.assertEqual(old["ratchet.test-first"]["ratchet"], "Check: mutations of the changed code that the new tests must kill")
        self.assertTrue(rule["ratchet"].startswith(old["ratchet.test-can-fail"]["ratchet"]
                                                   + ", and mutations of the changed code that the new tests must kill. "))
        for words in ("Mutations may run on a schedule the project sets, not in every PR.",
                      "A scheduled run names the revision it tested and posts its result.",
                      "It is red when a mutation survives or when the last run is older than the age the project sets"):
            self.assertIn(words, rule["ratchet"])
        self.assertEqual(rule["source"], old["ratchet.test-first"]["source"])

    def test_silence_is_red_is_nightly_visible_widened_by_t1_and_still_names_the_nightly_scan(self):
        # D-2026-11-22-second-redraw, T1: ratchet.nightly-visible is kept, widened and renamed, because the old name would
        # be false. Every scheduled job posts its result, a late post is red, and the nightly security scan is still named.
        rule = self.by_key["ratchet.silence-is-red"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["principle"], rule["source"]),
                         ("core", "enforced", "security", "principle.show-the-run", ""))
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        self.assertEqual(rule["rule"], "Every scheduled job posts its result, and a late post is red. " + old["ratchet.nightly-visible"]["rule"])
        self.assertIn("nightly security scan", rule["rule"])
        # T1 adds that every job posts and that a late post is red, and names no destination for the other jobs, so the
        # status issue stays the destination of the nightly job alone, in the words of the old ratchet.
        self.assertEqual(old["ratchet.nightly-visible"]["ratchet"],
                         "Check: the nightly job posts its own result, pass or fail, to the status issue")
        self.assertEqual(rule["ratchet"], "Check: every scheduled job posts its own result, pass or fail, and a late post is red. "
                                          "The nightly job posts its own result, pass or fail, to the status issue")
        self.assertEqual(rule["ratchet"].count("status issue"), 1)
        keys = [item["key"] for item in self.data["rules"]]
        self.assertEqual(keys.index("ratchet.silence-is-red"), keys.index("ratchet.skills-pinned") + 1, "it stands where the old key stood")
        self.assertIn("`ratchet.silence-is-red`", read("RATCHET.md"))

    def test_agents_without_keys_takes_the_two_clauses_of_t2(self):
        # D-2026-11-22-second-redraw, T2: the agents' forge account has no admin role, and agents use a temporary directory
        # of their own. It stays text only.
        rule = self.by_key["ratchet.agents-without-keys"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["principle"]),
                         ("core", "text-only", "security", "principle.guard-the-boundaries"))
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        self.assertEqual(rule["rule"], old["ratchet.agents-without-keys"]["rule"] + " The agents' forge account has no admin role, "
                         "and agents use a temporary directory of their own.")
        self.assertTrue(rule["ratchet"].startswith(old["ratchet.agents-without-keys"]["ratchet"]))

    def test_lesson_names_check_holds_lesson_loop_without_at_most_three(self):
        # D-2026-11-22-second-redraw, R10: "at most three" lessons is gone. Lessons are proposed, and apply only after the
        # owner approves them. The check of the lesson template stands, and the ratchet says what it does not see.
        rule = self.by_key["ratchet.lesson-names-check"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["principle"]),
                         ("core", "enforced", "lessons", "principle.checks-that-fail"))
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        loop = old["ratchet.lesson-loop"]["rule"]
        self.assertIn("at most three lessons are proposed", loop)
        self.assertEqual(rule["rule"], old["ratchet.lesson-names-check"]["rule"] + " " + loop.replace("at most three lessons", "lessons"))
        self.assertNotIn("three", rule["rule"])
        self.assertIn("They apply only after the owner approves them.", rule["rule"])
        self.assertTrue(rule["ratchet"].startswith(old["ratchet.lesson-names-check"]["ratchet"] + ". "))
        self.assertIn("whether a lesson was proposed", rule["ratchet"])
        self.assertIn("ratchet.lesson-names-check", self.data["start"])

    def test_register_on_top_holds_the_clause_l1_word_for_word(self):
        # D-2026-11-22-second-redraw, L1 (review of step 9a): register-on-top as it stood at v0.9, then the clause on
        # adoption by reference word for word as the table of losses in the decision has it. Its ratchet names both modes.
        rule = self.by_key["ratchet.register-on-top"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["reference_check"]), ("core", "enforced", "checks/check_register.py"))
        clause = "A Ratchet row may point at the project's own wording, and the check then sees a marker, not the rule's text."
        self.assertIn("\n| L1 | %s | register-on-top |" % clause, read(os.path.join("decisions", "D-2026-11-22-second-redraw.md")))
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))["ratchet.register-on-top"]
        self.assertEqual(rule["rule"], old["rule"] + " " + clause)
        self.assertEqual(rule["rule"],
                         "One file, the register, lists every rule in force and takes precedence over all other text in the repo. "
                         "Where a text and the register differ, the register wins. A Ratchet row may point at the project's own "
                         "wording, and the check then sees a marker, not the rule's text.")
        self.assertEqual(rule["ratchet"],
                         old["ratchet"] + ": a copied row character for character, and a row by reference by the sha256 of the "
                         "rule and its ratchet and by one marker line in the file it names, not by the words there")

    def test_owner_paths_holds_one_approver_and_checks_owner_read_and_names_the_register_and_every_file_it_names(self):
        # D-2026-11-22-second-redraw: ratchet.owner-paths as decided, word for word, with T4: the owner's paths include the
        # register and every file it names, the review is dismissed on a new push, and the agents cannot bypass it.
        rule = self.by_key["ratchet.owner-paths"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["principle"], rule["source"]),
                         ("core", "enforced", "truth", "principle.independent-gate", ""))
        self.assertEqual(rule["rule"],
                         "Only the owner approves decisions. Agents write proposals and mark them as proposals. The project "
                         "lists the paths that are the owner's: the decisions, the register and every file it names, the checks, "
                         "the gates and the automated reviewers. A change to any of them merges only after the owner has read it "
                         "and approved its head. A work package that changes a check, a gate or an automated reviewer states, "
                         "before review, what it claims and against which threat, with a finite list of cases. "
                         + OUTSIDE_GATES)
        self.assertEqual(rule["ratchet"],
                         "Check: the host requires the owner's review on the listed paths and dismisses it on a new push, and "
                         "agents work under an account of their own that cannot approve and cannot bypass the requirement. It does "
                         "not see whether the claim and the threat were stated, whether a proposal is marked as one, or whether "
                         "the owner read a change to a check, gate or automated reviewer, or to a setting outside the repo they "
                         "depend on")
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        # ratchet.one-approver, whole. M5 keeps exactly this in the core.
        self.assertIn(old["ratchet.one-approver"]["rule"], rule["rule"])
        # ratchet.checks-owner-read: what a work package that changes a check states, and that the check does not see it.
        self.assertIn("states, before review, what it claims and against which threat, with a finite list of cases.", rule["rule"])
        self.assertIn("It does not see whether the claim and the threat were stated", rule["ratchet"])
        # This repo adopts it as text only for now: owner coverage stays not built until there is evidence from the host.
        adopted = dict((item["key"], item) for item in self.register["adopted"])
        self.assertEqual(adopted["ratchet.owner-paths"]["status"], "text only for now")
        where = adopted["ratchet.owner-paths"]["where"]
        self.assertTrue(where.startswith("Pending setup, not built."))
        # The review of step 8: on its way to built it names the gates and automated reviewers outside .github/CODEOWNERS,
        # and it says plainly that the control room can submit the owner's approval. The second answer of
        # D-2026-11-22-owner-reads-outside-gates: it names the settings outside the repo that the checks depend on too.
        for words in ("the gates and automated reviewers outside the repo, and the settings outside the repo that the checks "
                      "depend on, are listed among the owner's paths too",
                      "the variables and secrets of Actions, which the agents' account may change",
                      "are not in `.github/CODEOWNERS`", "The control room can submit the code owner's approval itself"):
            self.assertIn(words, where)
        self.assertNotIn("when that the", where)
        self.assertNotIn("that act outside the repo", where)

    def test_owner_paths_holds_the_sentence_on_gates_outside_the_repo_by_the_maintainers_decision(self):
        # D-2026-11-22-owner-reads-outside-gates: the old ratchet.checks-owner-read said that checks, gates and automated
        # reviewers change only after the owner has read the change. ratchet.owner-paths covered only what merges in the
        # repo, so a gate or a reviewer changed outside it fell out. The maintainer put the sentence back in the core.
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        self.assertIn("Checks, gates and automated reviewers change only after the owner has read the change.",
                      old["ratchet.checks-owner-read"]["rule"])
        self.assertTrue(self.by_key["ratchet.owner-paths"]["rule"].endswith(" " + OUTSIDE_GATES))
        self.assertNotIn("that act outside the repo", self.by_key["ratchet.owner-paths"]["rule"])
        decision = read(os.path.join("decisions", "D-2026-11-22-owner-reads-outside-gates.md"))
        for words in ("# D-2026-11-22-owner-reads-outside-gates: ", "- Decided by: Ratchet's maintainer",
                      "> 1. **Fables fråga om kärnan.**", "> Ja\n", OUTSIDE_GATES, "GPT-6 Astra", "Claude Fable",
                      "The mark `[…]` shows where this file leaves out part of a message.\n"):
            self.assertIn(words, decision)
        # The second exchange, after the reviews of #125 at 18d1ce8: the maintainer saw the exact sentence, Fable's gap,
        # and chose to close it, in Swedish first and then in English. Each exchange is answered "Ja".
        question, answer, follows = (decision.split("\n## Question\n")[1].split("\n## Answer\n")[0],
                                     decision.split("\n## Answer\n")[1].split("\n## What follows\n")[0],
                                     decision.split("\n## What follows\n")[1])
        second = question.split("The second question")[1]
        for words in ("> Alla tre granskarna godkänner nu #125. Fable påpekar två saker som gäller just dig.",
                      "> > *\"" + FIRST_WORDING + "\"*", "> Fable hittade dessutom en lucka i formuleringen.",
                      "> 1. **Täpp till luckan först** (mitt råd). Meningen blir:", ">    > *\"" + OUTSIDE_GATES + "\"*",
                      "> 2. **Slå ihop som den är**, vid head `18d1ce8`, och ta luckan i en senare PR.", "> […]\n",
                      "> All three reviewers now approve #125.", "> 1. **Close the gap first** (my recommendation).",
                      "> Vad rekommenderar du?\n", "> What do you recommend?\n"):
            self.assertIn(words, second)
        self.assertLess(second.index("> Alla tre granskarna"), second.index("> All three reviewers"))
        self.assertLess(second.index("> Vad rekommenderar du?"), second.index("> What do you recommend?"))
        self.assertEqual(answer.count("> Ja\n"), 2)
        self.assertLess(answer.index("To the first question."), answer.index("To the second question."))
        # What follows records the sentence of the second answer, not the first, and says who found the gap.
        self.assertIn(OUTSIDE_GATES, follows)
        self.assertNotIn(FIRST_WORDING, follows)
        for words in ("Claude Fable found the gap", "a variable of Actions that the agents' account may change"):
            self.assertIn(words, follows)

    def test_this_repos_code_owner_owns_the_register_and_every_file_it_names(self):
        # ratchet.owner-paths: the owner's paths are the decisions, the register and every file it names, and the checks.
        # The host matches CODEOWNERS like gitignore, and the last matching line wins, so a later line such as
        # "CODEOWNERS @x", "checks @x" or "/decisions @x" takes a path from the maintainer. This reads no pattern: the
        # file must be exactly the one line this repo has, which gives every path to the maintainer, and there is no
        # other CODEOWNERS file where the host looks. It does not see whether the host requires the review: the register
        # says that is not built.
        self.assertEqual(sole_owner(read(os.path.join(".github", "CODEOWNERS"))), "@fabian-von-tiedemann")
        for other in ("CODEOWNERS", os.path.join("docs", "CODEOWNERS")):
            self.assertFalse(os.path.lexists(os.path.join(ROOT, other)), other)
        paths = ["register.json", "REGISTER.md", self.register["instructions"], "decisions/D-2026-11-22-second-redraw.md",
                 "checks/check_register.py", ".github/workflows/checks.yml", "ratchet.json", ".github/CODEOWNERS"]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(os.path.isfile(os.path.join(ROOT, path)), path)

    def test_a_codeowners_file_with_any_line_but_the_one_fails(self):
        # The counterexamples of the review of step 8: each would leave a path with another owner, the last match winning.
        self.assertEqual(sole_owner("* @fabian-von-tiedemann\n"), "@fabian-von-tiedemann")
        for text in ("* @fabian-von-tiedemann\nCODEOWNERS @someone\n", "* @fabian-von-tiedemann\nchecks @someone\n",
                     "* @fabian-von-tiedemann\n/decisions @someone\n", "* @fabian-von-tiedemann\n/decisions/ @someone\n",
                     "* @fabian-von-tiedemann\nregister.json @someone\n", "* @fabian-von-tiedemann\n*.md @someone\n",
                     "* @fabian-von-tiedemann\n**/checks/** @someone\n", "* @fabian-von-tiedemann\nAGENTS.md\n",
                     "* @fabian-von-tiedemann @someone\n", "* @fabian-von-tiedemann # note\n",
                     "# owners\n* @fabian-von-tiedemann\n", "* @fabian-von-tiedemann\n\n", "* @fabian-von-tiedemann",
                     "*  @fabian-von-tiedemann\n", "* @fabian-von-tiedemann\r\n", "/* @fabian-von-tiedemann\n",
                     "\ufeff* @fabian-von-tiedemann\n", "", "\n"):
            with self.subTest(text=text):
                self.assertIsNone(sole_owner(text))

    def test_the_start_set_has_ten_rules_with_owner_paths(self):
        # D-2026-11-22-second-redraw: the start set grows from nine rules to ten, since the protection of a row by
        # reference depends on ratchet.owner-paths. Eight of the ten name a check.
        start = self.data["start"]
        self.assertEqual(len(start), 10)
        self.assertEqual(len(set(start)), 10)
        self.assertIn("ratchet.owner-paths", start)
        self.assertEqual(sum(self.by_key[key]["enforcement"] == "enforced" for key in start), 8)
        template = registry.load_json(os.path.join(ROOT, "templates", "register.json"))
        self.assertEqual([item["key"] for item in template["adopted"]], start)
        self.assertIn("The ten rules to start with:", read("STARTING.md"))
        self.assertIn("| Ratchet uses all ten of its start rules. |", read("SELF-IMPROVEMENT.md"))

    def test_ask_the_owner_holds_the_three_rules_and_the_spending_clause_word_for_word(self):
        # D-2026-11-22-second-redraw: ratchet.ask-the-owner as decided, holding ratchet.look-up-facts,
        # ratchet.one-channel and ratchet.five-choices whole, and from ratchet.experiment-plan the owner's approval of
        # spending and the spending limit as the backstop, word for word (R9). The design checklist is gone.
        rule = self.by_key["ratchet.ask-the-owner"]
        self.assertEqual((rule["status"], rule["enforcement"], rule["part"], rule["principle"], rule["source"]),
                         ("core", "text-only", "questions", "principle.wait-for-the-owner", "mattpocock/skills `grilling`"))
        # Word for word as the decision has it, as for ratchet.owner-paths (the review of step 8).
        self.assertEqual(rule["rule"],
                         "The agent looks up facts itself. Decisions belong to the owner. Questions to the owner come through one "
                         "channel, the control room, never directly from the workspaces, and so do manual steps only the owner can "
                         "do. The owner gets at most five decisions at a time, each in one sentence with a recommendation, so the "
                         "answer can be \"yes\" or \"yes except 2\". Housekeeping and technical choices are made by the control room "
                         "and shown in PRs. An experiment that costs money needs the owner's approval of scope, cost cap, account "
                         "and timing before anything is created.")
        self.assertEqual(rule["ratchet"],
                         "Text only: messages pass no check, a check cannot tell a fact from a decision, and a check cannot see "
                         "spending before it happens. A spending limit on the account is the backstop")
        old = registry.rules_by_key(registry.parse_json(self.released("0.9")))
        for whole in (old["ratchet.look-up-facts"]["rule"], old["ratchet.five-choices"]["rule"],
                      "Questions to the owner come through one channel, the control room, never directly from the workspaces",
                      "and so do manual steps only the owner can do.",
                      "An experiment that costs money needs the owner's approval of scope, cost cap, account and timing before "
                      "anything is created."):
            self.assertIn(whole, rule["rule"])
        self.assertIn("An experiment that costs money", old["ratchet.experiment-plan"]["rule"])
        for words in ("Text only: messages pass no check", "a check cannot tell a fact from a decision",
                      "a check cannot see spending before it happens. A spending limit on the account is the backstop"):
            self.assertIn(words, rule["ratchet"])
        self.assertNotIn("hypothesis", rule["rule"])

    def test_decision_as_file_allows_one_log_and_keeps_the_id_the_verbatim_answer_and_a_strict_lint(self):
        # D-2026-11-22-second-redraw, L2: a decision may be a record in one log the project names. The id form, the
        # verbatim question and answer, and a strict lint of the form chosen all stay. This repo keeps one file each.
        rule = self.by_key["ratchet.decision-as-file"]
        self.assertEqual((rule["status"], rule["enforcement"]), ("core", "enforced"))
        # Word for word, the rule as step 8 wrote it under L2, and the ratchet naming what the lint reads of a log's record.
        self.assertEqual(rule["rule"],
                         "Each decision by the owner is written with the question and the answer verbatim and an id of the form "
                         "`D-YYYY-MM-DD-<slug>`, as a file of its own or as a record in one log the project names.")
        self.assertEqual(rule["ratchet"],
                         "Check: a strict lint of the form chosen, each decision file's name and format or each record's id and "
                         "format in the log")
        adopted = dict((item["key"], item) for item in self.register["adopted"])
        # D-2026-11-27-stale-text, point 2: the base's generate.py --check reads the names and the format of every
        # decision, from the pull request after the one that built it, and fails on the seeded folders of test_decisions.
        self.assertEqual(adopted["ratchet.decision-as-file"]["status"], "built")
        where = adopted["ratchet.decision-as-file"]["where"]
        self.assertIn("one file per decision there", where)
        for words in ("on the pull request's `decisions/`, from the pull request after the one that built it on.",
                      "it runs the base branch's `maintain/generate.py --check`, with its `maintain/decisions.py`, on the pull "
                      "request's `decisions/`",
                      "an entry that is not a plain file named `D-YYYY-MM-DD-<slug>.md` with a date that exists",
                      "the headings `## Question` and `## Answer`", "dated 2026-11-28 or later",
                      "a status line that is missing, stale or edited by hand", "`checks/fixtures/decisions/`",
                      "It does not see a relation that nobody writes down"):
            self.assertIn(words, where)
        # Every entry of decisions/, not only the .md files (the review at 18d1ce8), as the where says.
        self.assertTrue(os.listdir(os.path.join(ROOT, "decisions")))
        self.assertEqual(decision_name_problems(os.path.join(ROOT, "decisions")), [])

    def test_a_file_in_decisions_whose_name_is_not_an_id_fails(self):
        # Each entry that the test of ratchet.decision-as-file must fail on, beside one that passes.
        good = "D-2026-11-22-good.md"
        for name in ("notes.txt", "README", ".DS_Store", "D-2026-11-22-good.txt", "D-2026-11-22-good", "D-2026-02-30-bad.md",
                     "D-2026-11-22-.md", "d-2026-11-22-low.md", "x-D-2026-11-22-good.md", "D-2026-11-22-good.md.bak"):
            with self.subTest(name=name):
                folder = self.fresh_decisions(good)
                with open(os.path.join(folder, name), "w", encoding="utf-8") as handle:
                    handle.write("x\n")
                self.assertEqual(decision_name_problems(folder), [name])
        folder = self.fresh_decisions(good)
        os.mkdir(os.path.join(folder, "D-2026-11-22-folder.md"))
        self.assertEqual(decision_name_problems(folder), ["D-2026-11-22-folder.md"])
        folder = self.fresh_decisions(good)
        os.symlink(good, os.path.join(folder, "D-2026-11-22-link.md"))
        self.assertEqual(decision_name_problems(folder), ["D-2026-11-22-link.md"])
        self.assertEqual(decision_name_problems(self.fresh_decisions(good)), [])

    def fresh_decisions(self, good):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        with open(os.path.join(folder, good), "w", encoding="utf-8") as handle:
            handle.write("x\n")
        return folder

    def test_expected_tests_ran_cites_owner_paths(self):
        # D-2026-11-22-second-redraw: expected-tests-ran is unchanged but for the key it cites.
        self.assertIn("so a change to the checks is read by the owner (`ratchet.owner-paths`)",
                      self.by_key["ratchet.expected-tests-ran"]["ratchet"])

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
        # Step 8 of D-2026-11-22-second-redraw: 35 core rules less the nine of core batch A, and the two new ones, is 28.
        # Step 10, core batch B, takes out five more: one that names a check (ratchet.once-per-version, whose check is
        # the review script's, which ratchet.fresh-context names) and four that are text only.
        # Step 11, core batch C, takes out five more and adds one: ratchet.test-first, which names a check and goes into
        # ratchet.test-can-fail, three that are text only, and ratchet.nightly-visible, which names a check and is renamed
        # ratchet.silence-is-red. That is the 19 of the decision, 6 of them text only.
        self.assertEqual((core["rules"], core["enforced"], core["text_only"]), (28 - 5 - 5 + 1, 15 - 1 - 2 + 1, 13 - 4 - 3))
        self.assertEqual((core["rules"], core["text_only"]), (19, 6))

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
