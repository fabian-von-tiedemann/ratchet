"""The age of an experimental rule: generate.py --check fails when one has stood too long with no decision.

    python3 -m unittest discover -s checks -v

Every experimental rule in ratchet.json names "since", the version it entered Ratchet, and may name "kept_by", the
decision that kept it once more (D-2026-11-19-one-point-oh, choice 4). A rule that has stood through three releases
and 60 days with no decision fails the check, measured at the newest version with a date in CHANGELOG.md, so it is
caught in the clean-out at a release. A rule kept by a decision in "kept_by" stands one age more, counted from the
release at which it first stood too long, not from the decision: so it is kept once, and naming another decision in
"kept_by" keeps it no longer. The dates of the releases must not go back as the versions rise, or a mistyped year
would hide every rule.

The fixtures are under checks/fixtures/age/: a ratchet.json with a rule for each case, second-keep.json with a rule
kept by a second, later decision, changelogs whose newest release is 60 and 59 days after the first, one with three
releases more, and one with a year mistyped, the decisions that rules name in "kept_by", and under form/ data files
with one fault each in the new fields. Each test loads what it uses through FixtureTest. Standard library only.
"""

import datetime
import os
import shutil
import sys
import unittest

from suite_runner import FixtureTest
from test_checks import ROOT, RepoCopy, run

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import generate  # noqa: E402
import registry  # noqa: E402

OVERDUE = ("ratchet.overdue is experimental since 9.1 and has stood through 3 releases and 60 days, up to 9.4 (2026-03-02), "
           "with no decision to keep it")
CHOOSE = ("In the clean-out of this release, move it into the core, merge it with another rule, remove it, or keep it once "
          "more by a decision named in kept_by (D-2026-11-19-one-point-oh)")
KEPT_OUT = ("%s was kept by %s and has stood through 3 releases and 60 days more since it first stood too long, at 9.4 "
            "(2026-03-02), up to 9.7 (2026-05-01). It has had its one keep, and another decision in kept_by keeps it no "
            "longer. In the clean-out of this release, move it into the core, merge it with another rule, or remove it "
            "(D-2026-11-19-one-point-oh)")
BACKWARDS = ("CHANGELOG.md: '## 9.4 (2025-03-02)' is dated before '## 9.3 (2026-01-20)', the entry of the version before it. "
             "The dates of the entries must not go back as the versions rise")

# Fixture under age/form/ -> what generate.py --check must say when that file is ratchet.json.
FAILING = {
    "since-missing": "ratchet.reworded: an experimental rule has since, the version it entered Ratchet",
    "since-on-core": "ratchet.keep: only an experimental rule has since",
    "kept-by-on-core": "ratchet.keep: only an experimental rule has kept_by",
    "since-not-a-version": "ratchet.reworded: since must look like 0.2",
    "since-number": "ratchet.reworded: every field must be a string",
    "kept-by-not-an-id": "ratchet.reworded: kept_by must be the id of a decision, D-YYYY-MM-DD-<slug>, with a date that exists",
    "kept-by-no-such-date": "ratchet.reworded: kept_by must be the id of a decision, D-YYYY-MM-DD-<slug>, with a date that exists",
    "kept-by-no-file": "ratchet.reworded: kept_by names D-2026-01-15-keep, and decisions/D-2026-01-15-keep.md does not exist",
    "kept-by-misspelled": "ratchet.reworded: unknown field keptby",
    "since-twice": "the field 'since' appears twice in one object",
}


class AgeForm(FixtureTest):
    def test_a_fault_in_since_or_kept_by_fails_the_check(self):
        self.assertEqual(sorted(FAILING), sorted(name[:-len(".json")] for name in os.listdir(os.path.join(self.fixtures, "age", "form"))))
        for name, message in sorted(FAILING.items()):
            with self.subTest(fixture=name):
                root = self.scratch()
                shutil.copyfile(self.fixture_file("age/form/%s.json" % name), os.path.join(root, "ratchet.json"))
                code, output = run("generate.py", "--check", "--root", root)
                self.assertEqual(code, 1, output)
                self.assertIn(message, output)
                self.assertTrue(output.startswith("generate: "), "the data file fails before anything is generated: %s" % output)
                self.assertNotIn("Traceback", output)

    def test_an_older_ratchet_json_must_have_since(self):
        # Every version from 0.12 on gives each experimental rule since, so the reader of an older ratchet.json, which
        # checks/upgrade.py reads, fails without it as this one does (D-2026-11-23-support-from-0-12).
        data = registry.parse_json(self.fixture_bytes("age/form/since-missing.json"))
        self.assertIn(FAILING["since-missing"], registry.validate(data, None, older=True))


class Age(FixtureTest):
    def project(self, changelog="CHANGELOG.md", ratchet="ratchet.json"):
        """A scratch root with the fixture's ratchet.json, the two decisions, and the changelog given."""
        root = self.scratch()
        os.makedirs(os.path.join(root, "decisions"))
        for name in ("D-2026-01-15-keep.md", "D-2025-12-31-keep-early.md", "D-2026-05-01-keep-again.md"):
            with open(os.path.join(root, "decisions", name), "wb") as handle:
                handle.write(self.fixture_bytes("age/decisions/" + name))
        with open(os.path.join(root, "ratchet.json"), "wb") as handle:
            handle.write(self.fixture_bytes("age/" + ratchet))
        data = registry.load(os.path.join(root, "ratchet.json"))
        releases, problems = generate.release_dates(self.fixture_text("age/" + changelog))
        self.assertEqual(problems, [])
        return data, releases

    def test_the_dates_of_the_releases_are_read_from_the_headings(self):
        _, releases = self.project()
        day = datetime.date
        self.assertEqual(releases, {"9.1": day(2026, 1, 1), "9.2": day(2026, 1, 1), "9.3": day(2026, 1, 20), "9.4": day(2026, 3, 2)})

    def test_three_releases_and_60_days_with_no_decision_fail_and_name_the_rule(self):
        # ratchet.kept and ratchet.kept-early entered in 9.1 too, and were kept: they stand one age more from 9.4.
        data, releases = self.project()
        self.assertEqual(registry.age_problems(data, releases), ["%s. %s" % (OVERDUE, CHOOSE)])

    def test_59_days_are_not_yet_too_old(self):
        # The same releases, the newest a day earlier: ratchet.overdue has 3 releases and 59 days.
        data, releases = self.project(changelog="CHANGELOG-day-59.md")
        self.assertEqual(registry.age_problems(data, releases), [])

    def test_two_releases_are_not_yet_too_old_whatever_the_days(self):
        # ratchet.two-releases entered in 9.2, 60 days before 9.4, and has stood through two releases since.
        data, releases = self.project()
        self.assertNotIn("ratchet.two-releases", " ".join(registry.age_problems(data, releases)))

    def test_a_decision_in_kept_by_keeps_the_rule_once_more(self):
        # ratchet.kept entered in 9.1 with ratchet.overdue, and was kept: it passes at 9.4, where ratchet.overdue fails.
        data, releases = self.project()
        self.assertNotIn("ratchet.kept ", " ".join(registry.age_problems(data, releases)))
        rule = registry.rules_by_key(data)["ratchet.kept"]
        del rule["kept_by"]
        self.assertIn("ratchet.kept is experimental since 9.1", " ".join(registry.age_problems(data, releases)))

    def test_a_kept_rule_fails_after_one_age_more_and_is_not_offered_another_keep(self):
        # Three releases more, 9.5 to 9.7, and 9.7 is 60 days after 9.4, where the rules since 9.1 first stood too long.
        # Both kept rules fail, whatever the date of their decision: one is from before 9.1, the other from before 9.4.
        data, releases = self.project(changelog="CHANGELOG-kept-out.md")
        overdue = ("ratchet.overdue is experimental since 9.1 and has stood through 6 releases and 120 days, up to 9.7 "
                   "(2026-05-01), with no decision to keep it")
        two = ("ratchet.two-releases is experimental since 9.2 and has stood through 5 releases and 120 days, up to 9.7 "
               "(2026-05-01), with no decision to keep it")
        self.assertEqual(registry.age_problems(data, releases), [
            "%s. %s" % (overdue, CHOOSE),
            "%s. %s" % (two, CHOOSE),
            KEPT_OUT % ("ratchet.kept", "D-2026-01-15-keep"),
            KEPT_OUT % ("ratchet.kept-early", "D-2025-12-31-keep-early"),
        ])
        self.assertNotIn("keep it once more", " ".join(registry.age_problems(data, releases)[2:]))

    def test_a_second_keep_fails(self):
        # The keep of ratchet.kept has run out, and a second decision, dated the day of 9.7, is named in its place.
        data, releases = self.project(ratchet="second-keep.json", changelog="CHANGELOG-kept-out.md")
        self.assertIn(KEPT_OUT % ("ratchet.kept", "D-2026-05-01-keep-again"), registry.age_problems(data, releases))
        # The same with the decision of ratchet.kept named for ratchet.kept-early, which is later than its own.
        registry.rules_by_key(data)["ratchet.kept-early"]["kept_by"] = "D-2026-01-15-keep"
        self.assertIn(KEPT_OUT % ("ratchet.kept-early", "D-2026-01-15-keep"), registry.age_problems(data, releases))

    def test_the_age_more_of_a_kept_rule_needs_three_releases_and_60_days(self):
        data, releases = self.project(changelog="CHANGELOG-kept-out.md")
        two = dict(releases)
        del two["9.7"]
        self.assertNotIn(" was kept by ", " ".join(registry.age_problems(data, two)))
        day_59 = dict(releases, **{"9.7": datetime.date(2026, 4, 30)})
        self.assertNotIn(" was kept by ", " ".join(registry.age_problems(data, day_59)))

    def test_a_rule_that_entered_in_the_version_not_yet_released_has_no_age(self):
        data, releases = self.project()
        self.assertNotIn("ratchet.unreleased", " ".join(registry.age_problems(data, releases)))

    def test_since_must_name_a_version_with_an_entry_in_the_changelog(self):
        data, releases = self.project(ratchet="no-entry.json")
        self.assertIn("ratchet.two-releases: since is 9.0, which has no entry with a date in CHANGELOG.md and is not this "
                      "version, 9.5", registry.age_problems(data, releases))

    def test_since_later_than_this_version_fails(self):
        # A later version cannot have an entry: the first entry of the changelog is this version.
        data, releases = self.project()
        registry.rules_by_key(data)["ratchet.two-releases"]["since"] = "9.10"
        self.assertIn("ratchet.two-releases: since is 9.10, which has no entry with a date in CHANGELOG.md and is not this "
                      "version, 9.5", registry.age_problems(data, releases))

    def test_a_release_dated_before_the_version_before_it_fails(self):
        # 9.4 with its year mistyped, 2025 for 2026. The age is measured at the newest version, so the mistake would
        # hide ratchet.overdue, and every other rule, if the date were not refused.
        releases, problems = generate.release_dates(self.fixture_text("age/CHANGELOG-date-backwards.md"))
        self.assertEqual(problems, [BACKWARDS])
        data, _ = self.project()
        self.assertEqual(registry.age_problems(data, releases), [])

    def test_a_date_in_a_heading_that_does_not_exist_fails(self):
        releases, problems = generate.release_dates("# Changelog\n\n## 9.2 (2026-02-30)\n\nTwo.\n\n## 9.1 (2026-01-01)\n\nOne.\n")
        self.assertEqual(releases, {"9.1": datetime.date(2026, 1, 1)})
        self.assertEqual(problems, ["CHANGELOG.md: '## 9.2 (2026-02-30)' has a date that does not exist"])


class RepoAge(RepoCopy, unittest.TestCase):
    def test_every_experimental_rule_names_since_and_no_core_rule_does(self):
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        for rule in data["rules"]:
            with self.subTest(rule=rule["key"]):
                self.assertEqual("since" in rule, rule["status"] == "experimental")
                self.assertNotIn("kept_by", rule)

    def test_since_is_the_first_tag_that_holds_the_rule(self):
        # Read from the tags by hand on 2026-11-19, with git show and git grep: ratchet.json came in 0.3, and 0.2 held
        # the rules of CONTROL-ROOM.md and SELF-IMPROVEMENT.md in their Markdown tables (D-2026-11-19-one-point-oh).
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        since = dict((rule["key"], rule["since"]) for rule in data["rules"] if rule["status"] == "experimental")
        # ratchet.review-by-risk entered in 0.10, and the tag v0.10 is the first that holds it.
        later = {"ratchet.expected-tests-ran": "0.4", "ratchet.irreversible-waits": "0.7",
                 "ratchet.review-by-risk": "0.10"}
        # ratchet.one-exact-form entered in 0.10 too. Six rules since 0.2 left in 0.10 (D-2026-11-20-proposal-triage).
        # In 0.11 five rules since 0.2 and ratchet.phases left (D-2026-11-22-second-redraw, step 2), and three more
        # rules since 0.2 left (step 3).
        later["ratchet.one-exact-form"] = "0.10"
        # The seven rules of the product module enter in 0.12, which has no tag yet (D-2026-11-22-second-redraw, step 12).
        for key in ("ratchet.release-what-was-tested", "ratchet.accepted-by-who-can-judge", "ratchet.boundaries-have-tests",
                    "ratchet.production-health", "ratchet.measure-real-use", "ratchet.platform-lifecycle",
                    "ratchet.dependencies-pinned"):
            later[key] = "0.12"
        self.assertEqual(len(since), 17)
        for key, version in sorted(since.items()):
            with self.subTest(rule=key):
                self.assertEqual(version, later.get(key, "0.2"))

    def test_no_rule_is_too_old_today(self):
        # The releases up to 0.10 are dated from 2026-11-16 to 2026-11-21, so no rule has stood 60 days.
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def newest_release(self):
        """(the heading of the newest entry with a date in the copy's changelog, its version, the versions dated after 0.2)."""
        with open(os.path.join(self.copy, "CHANGELOG.md"), encoding="utf-8") as handle:
            text = handle.read()
        releases, _ = generate.release_dates(text)
        newest = max(releases, key=registry.version_key)
        after = [version for version in releases if registry.version_key(version) > (0, 2)]
        return "## %s (%s)" % (newest, releases[newest].isoformat()), newest, len(after)

    def test_a_release_60_days_on_fails_the_check_and_names_the_rules(self):
        # The newest release dated 60 days after 0.2: the six rules since 0.2 have stood through every release since.
        # There were twenty until 0.10 merged, removed and moved six of them (D-2026-11-20-proposal-triage), and 0.11
        # took five more out (D-2026-11-22-second-redraw, step 2) and three more (step 3).
        # It is the newest release in this repo, and the version being released in the copy that test_released_text.py dates.
        heading, newest, after = self.newest_release()
        self.edit("CHANGELOG.md", heading, "## %s (2027-01-15)" % newest)
        # The date of the first entry stands in RATCHET.md too, so the generated text is written again first.
        run("generate.py", root=self.copy)
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("ratchet.json: ratchet.cr-wake is experimental since 0.2 and has stood through %d releases and 60 days, "
                      "up to %s (2027-01-15), with no decision to keep it" % (after, newest), output)
        self.assertEqual(output.count("with no decision to keep it"), 6)
        # 0.7 came on 2026-11-19, 57 days before. 0.4 came on 2026-11-17, a day after 0.2: 59 days.
        self.assertNotIn("ratchet.irreversible-waits is", output)
        self.assertNotIn("ratchet.expected-tests-ran is", output)

    def test_a_release_dated_before_the_one_before_fails_the_check(self):
        # The newest release with its year mistyped, 2026-01-16 for 2027-01-16: before the release before it, and the age check silent.
        heading, newest, _ = self.newest_release()
        with open(os.path.join(self.copy, "CHANGELOG.md"), encoding="utf-8") as handle:
            releases, _ = generate.release_dates(handle.read())
        before = max((version for version in releases if registry.version_key(version) < registry.version_key(newest)),
                     key=registry.version_key)
        self.edit("CHANGELOG.md", heading, "## %s (2026-01-16)" % newest)
        run("generate.py", root=self.copy)
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("CHANGELOG.md: '## %s (2026-01-16)' is dated before '## %s (%s)', the entry of the version before it"
                      % (newest, before, releases[before].isoformat()), output)
        self.assertNotIn("ratchet.json:", output)

    def test_59_days_on_pass(self):
        heading, newest, _ = self.newest_release()
        self.edit("CHANGELOG.md", heading, "## %s (2027-01-14)" % newest)
        run("generate.py", root=self.copy)
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)


if __name__ == "__main__":
    unittest.main()
