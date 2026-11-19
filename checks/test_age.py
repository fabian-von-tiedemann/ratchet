"""The age of an experimental rule: generate.py --check fails when one has stood too long with no decision.

    python3 -m unittest discover -s checks -v

Every experimental rule in ratchet.json names "since", the version it entered Ratchet, and may name "kept_by", the
decision that kept it once more (D-2026-11-19-one-point-oh, choice 4). A rule that has stood through three releases
and 60 days with no decision fails the check, measured at the newest version with a date in CHANGELOG.md, so it is
caught in the clean-out at a release. A decision in "kept_by" starts the count again from its date.

The fixtures are under checks/fixtures/age/: a ratchet.json with a rule for each case, two changelogs whose newest
release is 60 and 59 days after the first, the two decisions that rules name in "kept_by", and under form/ data files
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
KEPT_EARLY = "ratchet.kept-early was kept by D-2025-12-31-keep-early and has stood through 4 releases and %d days since then, up to 9.4 (%s)"
CHOOSE = ("In the clean-out of this release, move it into the core, merge it with another rule, remove it, or keep it once "
          "more by a decision named in kept_by (D-2026-11-19-one-point-oh)")

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

    def test_an_older_ratchet_json_may_lack_since(self):
        # The ratchet.json of a version before 0.10, which checks/upgrade.py reads, has no since.
        data = registry.parse_json(self.fixture_bytes("age/form/since-missing.json"))
        self.assertEqual(registry.validate(data, None, older=True), [])
        self.assertTrue(registry.validate(data, None))


class Age(FixtureTest):
    def project(self, changelog="CHANGELOG.md", ratchet="ratchet.json"):
        """A scratch root with the fixture's ratchet.json, the two decisions, and the changelog given."""
        root = self.scratch()
        os.makedirs(os.path.join(root, "decisions"))
        for name in ("D-2026-01-15-keep.md", "D-2025-12-31-keep-early.md"):
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
        data, releases = self.project()
        self.assertEqual(registry.age_problems(data, releases), [
            "%s. %s" % (OVERDUE, CHOOSE),
            "%s. %s" % (KEPT_EARLY % (61, "2026-03-02"), CHOOSE),
        ])

    def test_59_days_are_not_yet_too_old(self):
        # The same releases, the newest a day earlier: ratchet.overdue has 3 releases and 59 days. A rule kept by a
        # decision is counted from the decision, which is 60 days before the newest release, so it still fails.
        data, releases = self.project(changelog="CHANGELOG-day-59.md")
        self.assertEqual(registry.age_problems(data, releases), ["%s. %s" % (KEPT_EARLY % (60, "2026-03-01"), CHOOSE)])

    def test_two_releases_are_not_yet_too_old_whatever_the_days(self):
        # ratchet.two-releases entered in 9.2, 60 days before 9.4, and has stood through two releases since.
        data, releases = self.project()
        self.assertNotIn("ratchet.two-releases", " ".join(registry.age_problems(data, releases)))

    def test_a_decision_in_kept_by_starts_the_count_again(self):
        # ratchet.kept entered in 9.1 with ratchet.overdue, and was kept on 2026-01-15: two releases since then.
        data, releases = self.project()
        self.assertNotIn("ratchet.kept ", " ".join(registry.age_problems(data, releases)))
        rule = registry.rules_by_key(data)["ratchet.kept"]
        del rule["kept_by"]
        self.assertIn("ratchet.kept is experimental since 9.1", " ".join(registry.age_problems(data, releases)))

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
        later = {"ratchet.expected-tests-ran": "0.4", "ratchet.phases": "0.6", "ratchet.irreversible-waits": "0.7"}
        self.assertEqual(len(since), 23)
        for key, version in sorted(since.items()):
            with self.subTest(rule=key):
                self.assertEqual(version, later.get(key, "0.2"))

    def test_no_rule_is_too_old_today(self):
        # Every tag is from 2026-11-16 to 2026-11-19, so no rule has stood 60 days.
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
        # The newest release dated 60 days after 0.2: the twenty rules since 0.2 have stood through every release since.
        # It is 0.9 in this repo, and the version being released in the copy that test_released_text.py dates.
        heading, newest, after = self.newest_release()
        self.edit("CHANGELOG.md", heading, "## %s (2027-01-15)" % newest)
        # The date of the first entry stands in RATCHET.md too, so the generated text is written again first.
        run("generate.py", root=self.copy)
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("ratchet.json: ratchet.cr-wake is experimental since 0.2 and has stood through %d releases and 60 days, "
                      "up to %s (2027-01-15), with no decision to keep it" % (after, newest), output)
        self.assertEqual(output.count("with no decision to keep it"), 20)
        # 0.6 and 0.7 came on 2026-11-19, 57 days before. 0.4 came on 2026-11-17, a day after 0.2: 59 days.
        self.assertNotIn("ratchet.phases is", output)
        self.assertNotIn("ratchet.irreversible-waits is", output)
        self.assertNotIn("ratchet.expected-tests-ran is", output)

    def test_59_days_on_pass(self):
        heading, newest, _ = self.newest_release()
        self.edit("CHANGELOG.md", heading, "## %s (2027-01-14)" % newest)
        run("generate.py", root=self.copy)
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)


if __name__ == "__main__":
    unittest.main()
