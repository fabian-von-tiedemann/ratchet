"""The upgrade path: checks/upgrade.py prints what a register must do to move to a newer Ratchet.

    python3 -m unittest discover -s checks -v

The fixtures are under checks/fixtures/upgrade/: a Ratchet 9.8 and a 9.9 with every kind of change between them,
a project's register on 9.8, and data files with one fault each. Under upgrade/removed/ are a smaller 9.8 and 9.9, in
which two rules that registers on 9.8 adopt are removed. Each test loads what it uses through FixtureTest.
Standard library only.
"""

import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import unittest
from unittest import mock

from suite_runner import FixtureTest
from test_checks import ROOT, read, run

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import check_register  # noqa: E402
import registry  # noqa: E402
import upgrade  # noqa: E402

# Fixture under upgrade/faults/ -> what the upgrade must say when it is given that file as a Ratchet data file.
FAULTS = {
    "duplicate-field": "the field 'version' appears twice in one object",
    "not-json": "not a valid data file",
    "not-utf8": "is not valid UTF-8, at byte",
    "unknown-field": "unknown field 'waivers'",
    "missing-field": "missing field 'start'",
    "rule-unknown-field": "ratchet.reworded: unknown field waived",
    "rule-hidden-character": "ratchet.reworded: rule holds U+200B",
    "version-number": "version must look like 0.2",
    "key-twice": "ratchet.reworded: the key is used twice",
    "unknown-part": "ratchet.reworded: unknown part two",
}

# What the upgrade says when the fields at the top of ratchet.json differ between the two versions.
FORM = ("The form of ratchet.json changed from Ratchet %s to %s: %s. This is for the project, not the register. Ratchet's "
        "checks read ratchet.json strictly, so the checks of Ratchet %s do not read the ratchet.json of %s. The checks in "
        ".ratchet come with their own version and need nothing. A copy of a Ratchet check kept in the project, or a check "
        "of the project's own, that reads ratchet.json must be updated: replace the copy with the one from Ratchet %s, or "
        "change the check.")


def entries(output):
    """Every JSON object in the output that starts at the beginning of a line, in order."""
    decoder, found, at = json.JSONDecoder(), [], 0
    while True:
        at = output.find("\n{", at)
        if at < 0:
            return found
        value, end = decoder.raw_decode(output, at + 1)
        found.append(value)
        at = end


class Upgrade(FixtureTest):
    def files(self, register="register.json", old="old/ratchet.json", new="new/ratchet.json"):
        return [self.fixture_file("upgrade/" + register), "--from", self.fixture_file("upgrade/" + old),
                "--source", self.fixture_file("upgrade/" + new)]

    def upgrade(self, **files):
        return run("upgrade.py", *self.files(**files))

    def loaded(self, name):
        return registry.parse_json(self.fixture_bytes("upgrade/" + name))

    def test_every_change_is_listed_with_what_the_register_must_do(self):
        code, output = self.upgrade()
        self.assertEqual(code, 0, output)
        for line in (
            "register.json is on Ratchet 9.8. In Ratchet 9.9, 9 rules are new, changed or removed.",
            '1. Set "ratchet_version" to "9.9".',
            "ratchet.reworded: changed: the rule. The register adopts it: replace its entry with this one.",
            "ratchet.now-checked: changed: the enforcement and the ratchet. The register adopts it: replace its entry with this one. "
            'Its ratchet now names a check, so the entry has a status: "text only for now" until the project has built the check.',
            "ratchet.now-text: changed: the enforcement and the ratchet. The register adopts it: replace its entry with this one. "
            'It is text only now, so the entry has no status and no "where".',
            "ratchet.new-ratchet: changed: the ratchet and the source. The register adopts it: replace its entry with this one. "
            'It keeps the status "built". Its ratchet changed: check that the check in "where" still does what the ratchet says, '
            'or set the status to "text only for now".',
            'ratchet.dropped: removed. Remove it from "adopted". To keep it as a rule of the project\'s own, also add this entry '
            'to "own". Its key has the prefix "example", from the register\'s first own rule.',
            "ratchet.added: new. The register may adopt it. To adopt it, add this entry to \"adopted\".",
            "ratchet.added-text: new. The register may adopt it. To adopt it, add this entry to \"adopted\".",
            "Not adopted, so nothing to do: ratchet.changed-unadopted (changed), ratchet.dropped-unadopted (removed).",
            "Checked: with the steps above and no new rule adopted, register.json passes check_register.py against Ratchet 9.9, "
            'whether each removed rule is taken out or also moved to "own" with the entry printed.',
            "The reasons for each change are in CHANGELOG.md of Ratchet 9.9, in the entries after 9.8.",
        ):
            self.assertIn(line, output)
        self.assertNotIn("ratchet.keep", output, "a rule that did not change is not listed")
        self.assertNotIn("ratchet.left-out", output, "a rule that did not change is not listed, adopted or not")
        self.assertNotIn("The form of ratchet.json changed", output, "9.8 and 9.9 have the same fields")
        self.assertNotIn("Traceback", output)

    def test_each_printed_entry_is_the_rule_as_it_stands_in_the_newer_ratchet(self):
        code, output = self.upgrade()
        self.assertEqual(code, 0, output)
        new = registry.rules_by_key(self.loaded("new/ratchet.json"))
        printed = entries(output)
        self.assertEqual([entry["key"] for entry in printed],
                         ["ratchet.reworded", "ratchet.now-checked", "ratchet.now-text", "ratchet.new-ratchet", "example.dropped",
                          "ratchet.added", "ratchet.added-text"])
        self.assertEqual(printed[4], {"key": "example.dropped", "rule": "Write a status every day.",
                                      "ratchet": "Text only: a status is prose", "source": ""})
        printed = [entry for entry in printed if entry["key"].startswith("ratchet.")]
        for entry in printed:
            with self.subTest(key=entry["key"]):
                for field in check_register.RULE_FIELDS:
                    self.assertEqual(entry[field], new[entry["key"]][field])
        by_key = dict((entry["key"], entry) for entry in printed)
        self.assertEqual(by_key["ratchet.now-checked"]["status"], "text only for now")
        self.assertNotIn("status", by_key["ratchet.now-text"])
        self.assertNotIn("where", by_key["ratchet.now-text"])
        self.assertEqual((by_key["ratchet.new-ratchet"]["status"], by_key["ratchet.new-ratchet"]["where"]), ("built", "checks/secrets.sh"))
        self.assertEqual(by_key["ratchet.added"]["status"], "text only for now")
        self.assertNotIn("status", by_key["ratchet.added-text"])

    def test_the_register_with_the_steps_done_passes_against_the_newer_ratchet(self):
        register, old, new = self.loaded("register.json"), self.loaded("old/ratchet.json"), self.loaded("new/ratchet.json")
        steps, after = upgrade.plan(register, old, new)
        problems, summary = check_register.check(after, new)
        self.assertEqual(problems, [])
        self.assertEqual([entry["key"] for entry in after["adopted"]],
                         ["ratchet.keep", "ratchet.reworded", "ratchet.now-checked", "ratchet.now-text", "ratchet.new-ratchet"])
        self.assertEqual(after["own"], register["own"])
        self.assertEqual(after["adopted"][0], register["adopted"][0], "a rule that did not change keeps its entry, with its status")
        self.assertEqual(register["ratchet_version"], "9.8", "the register given is not changed")
        # Each entry that a step prints is the entry in the register after it.
        printed = dict((step["entry"]["key"], step["entry"]) for step in steps if step.get("entry"))
        for entry in after["adopted"][1:]:
            self.assertEqual(printed[entry["key"]], entry)

    def test_nothing_is_written(self):
        files = self.files()
        directories = sorted(set(os.path.dirname(os.path.dirname(path)) for path in files if path != "--from" and path != "--source"))
        def state():
            result = {}
            for directory in directories:
                for folder, _, names in os.walk(directory):
                    for name in names:
                        with open(os.path.join(folder, name), "rb") as handle:
                            result[os.path.join(folder, name)] = handle.read()
            return result
        before = state()
        code, output = run("upgrade.py", *files, cwd=directories[0])
        self.assertEqual(code, 0, output)
        self.assertEqual(state(), before)

    def test_a_register_on_the_newer_ratchet_has_nothing_to_change(self):
        code, output = self.upgrade(register="register-current.json", old="new/ratchet.json")
        self.assertEqual(code, 0, output)
        self.assertIn("register-current.json is on Ratchet 9.9, the version of this Ratchet. Nothing to change.", output)

    def test_a_register_that_has_drifted_from_its_ratchet_fails(self):
        code, output = self.upgrade(register="register-drifted.json")
        self.assertEqual(code, 1, output)
        self.assertIn("the rule of ratchet.reworded differs from Ratchet 9.8", output)
        self.assertIn("register-drifted.json does not pass check_register.py against Ratchet 9.8, the version it states. Fix it first", output)
        self.assertNotIn("ratchet_version", output.split("Fix it first")[1])

    def test_a_ratchet_that_is_not_the_one_the_register_states_fails(self):
        code, output = self.upgrade(register="register-other-version.json")
        self.assertEqual(code, 1, output)
        self.assertIn("the register follows Ratchet 9.7, but this check is Ratchet 9.8", output)

    def test_a_ratchet_older_than_the_register_fails(self):
        code, output = self.upgrade(register="register-current.json", old="new/ratchet.json", new="old/ratchet.json")
        self.assertEqual(code, 1, output)
        self.assertIn("this Ratchet is 9.8, which is older than 9.9, the version the register is on", output)

    def test_the_sources_of_an_older_ratchet_are_not_read(self):
        # Ratchet 0.3 wrote a source in a form that the reader of 0.4 and later refuses. The upgrade reads the
        # version, the parts and the rules, so a register on 0.3 can still be upgraded.
        with self.assertRaises(registry.RegistryError):
            registry.load(self.fixture_file("upgrade/old-source-form/ratchet.json"))
        code, output = self.upgrade(old="old-source-form/ratchet.json")
        self.assertEqual(code, 0, output)
        self.assertIn("In Ratchet 9.9, 9 rules are new, changed or removed.", output)
        # That older file has no cap, and has the date and the sources, which left ratchet.json in 0.9: the form changed.
        # Its rules lack "since", which every experimental rule has from 0.10.
        self.assertIn(FORM % ("9.8", "9.9", '"date" is gone, "experimental_cap" is new, "sources" is gone and "since" in a rule is new',
                              "9.8", "9.9", "9.9"), output)

    def test_a_change_of_form_is_told_to_a_project_with_a_copy_that_reads_ratchet_json(self):
        # The fields at the top of ratchet.json, which Ratchet's checks read strictly: a reader of the older version
        # fails on a field it does not know, so a copy of it, or a check of the project's own, must be updated.
        old, new = self.loaded("old/ratchet.json"), self.loaded("new/ratchet.json")
        self.assertEqual(upgrade.form_changes(old, new), [])
        del old["experimental_cap"]
        self.assertEqual(upgrade.form_changes(old, new), ['"experimental_cap" is new'])
        # A field can also be gone: 0.9 took the date and the sources out of ratchet.json (D-2026-11-19-batched-releases).
        older = dict(old, date="2026-01-01", sources=[])
        self.assertEqual(upgrade.form_changes(older, new), ['"date" is gone', '"experimental_cap" is new', '"sources" is gone'])
        self.assertEqual(upgrade.form_changes(dict(new, date="2026-01-01", sources=[]), new), ['"date" is gone', '"sources" is gone'])
        self.assertEqual(upgrade.load_older(self.fixture_file("upgrade/old-source-form/ratchet.json"))["sources"][0]["name"], "somewhere")
        out = io.StringIO()
        code = upgrade.report("register.json", self.loaded("register.json"), old, new, out, "check_register.py")
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn(FORM % ("9.8", "9.9", '"experimental_cap" is new', "9.8", "9.9", "9.9"), out.getvalue())
        # It is told after the steps for the register and before the command that writes REGISTER.md again.
        output = out.getvalue()
        self.assertLess(output.index("Steps for register.json:"), output.index("The form of ratchet.json changed"))
        self.assertLess(output.index("The form of ratchet.json changed"), output.index("Then write REGISTER.md again"))

    def test_a_field_of_a_rule_that_is_new_or_gone_is_a_change_of_form(self):
        # A field that some rule holds in one version and no rule holds in the other. 0.10 gives every experimental
        # rule "since" (D-2026-11-19-one-point-oh), and a reader of 0.9 refuses it as an unknown field.
        old, new = self.loaded("old/ratchet.json"), self.loaded("new/ratchet.json")
        for rule in old["rules"]:
            rule.pop("since", None)
        self.assertEqual(upgrade.form_changes(old, new), ['"since" in a rule is new'])
        self.assertEqual(upgrade.form_changes(new, old), ['"since" in a rule is gone'])
        del old["experimental_cap"]
        self.assertEqual(upgrade.form_changes(old, new), ['"experimental_cap" is new', '"since" in a rule is new'])
        new["rules"][0]["kept_by"] = "D-2026-01-15-keep"
        self.assertEqual(upgrade.form_changes(old, new), ['"experimental_cap" is new', '"kept_by" in a rule is new',
                                                          '"since" in a rule is new'])

    def test_a_ratchet_data_file_with_a_fault_fails_as_either_file(self):
        self.assertEqual(sorted(FAULTS), sorted(name[:-len(".json")] for name in os.listdir(os.path.join(self.fixtures, "upgrade", "faults"))))
        for name, message in sorted(FAULTS.items()):
            for role in ("old", "new"):
                with self.subTest(fixture=name, role=role):
                    code, output = self.upgrade(**{role: "faults/%s.json" % name})
                    self.assertEqual(code, 2, output)
                    self.assertIn("upgrade: cannot run:", output)
                    self.assertIn(message, output)
                    self.assertNotIn("Traceback", output)

    def test_a_file_that_is_missing_fails(self):
        register, _, old, _, new = self.files()
        missing = os.path.join(os.path.dirname(register), "nothing.json")
        for files in ([missing, "--from", old, "--source", new], [register, "--from", missing, "--source", new],
                      [register, "--from", old, "--source", missing]):
            with self.subTest(files=files):
                code, output = run("upgrade.py", *files)
                self.assertEqual(code, 2, output)
                self.assertIn("nothing.json", output)
                self.assertNotIn("Traceback", output)

    def test_this_repos_register_at_each_released_version_upgrades_to_this_ratchet(self):
        # Ratchet's own register.json and ratchet.json as they stood at the tags v0.3 to v0.9.
        new = registry.load(os.path.join(ROOT, "ratchet.json"))
        for version in ("0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"):
            with self.subTest(version=version):
                register = self.fixture_file("upgrade/released/%s/register.json" % version)
                old = self.fixture_file("upgrade/released/%s/ratchet.json" % version)
                code, output = run("upgrade.py", register, "--from", old)
                self.assertEqual(code, 0, output)
                self.assertIn("register.json is on Ratchet %s." % version, output)
                self.assertIn('Set "ratchet_version" to "%s".' % new["version"], output)
                self.assertIn("passes check_register.py against Ratchet %s" % new["version"], output)
                # ratchet.si-version, which this repo adopts, changed in 0.5 (D-2026-11-18-form-change-before-1-0) and in
                # 0.10, which states what 1.0 promises (D-2026-11-19-one-point-oh).
                self.assertIn("ratchet.si-version: changed: the rule. The register adopts it: replace its entry with this one.", output)
                # Every experimental rule has "since" from 0.10, a change of form in its rules (D-2026-11-19-one-point-oh).
                since = '"since" in a rule is new'
                if version in ("0.3", "0.4"):
                    # Neither has the cap, which came in 0.5 as a change of form. Every version before 0.9 has the date
                    # and the sources, which left ratchet.json in 0.9 (D-2026-11-19-batched-releases).
                    form = '"date" is gone, "experimental_cap" is new, "sources" is gone and ' + since
                elif version == "0.9":
                    form = since
                else:
                    form = '"date" is gone, "sources" is gone and ' + since
                self.assertIn(FORM % (version, new["version"], form, version, new["version"], new["version"]), output)
                # The rule that 0.6 adds is new to each register before it, and so is the rule that 0.7 adds. 0.8 adds none:
                # it moves two pins in "sources", which is not a field that the register holds. 0.9 adds none.
                for added, rule in (("0.6", "ratchet.phases"), ("0.7", "ratchet.irreversible-waits")):
                    line = "- %s: new. The register may adopt it." % rule
                    if tuple(map(int, version.split("."))) < tuple(map(int, added.split("."))):
                        self.assertIn(line, output)
                    else:
                        self.assertNotIn(line, output)
                if version == "0.9":
                    # 0.10 changes two rules, ratchet.si-version and ratchet.si-subtract, and adds none.
                    self.assertIn("In Ratchet %s, 2 rules are new, changed or removed." % new["version"], output)
                    self.assertIn("Not adopted, so nothing to do: ratchet.si-subtract (changed).", output)
                steps, after = upgrade.plan(registry.parse_json(self.fixture_bytes("upgrade/released/%s/register.json" % version)),
                                            upgrade.load_older(old), new)
                self.assertEqual(check_register.check(after, new)[0], [])

    def test_the_older_ratchet_is_required(self):
        code, output = run("upgrade.py", self.fixture_file("upgrade/register.json"))
        self.assertEqual(code, 2, output)
        self.assertIn("--from", output)


class RemovedRules(FixtureTest):
    """Rules that the register adopts and that the newer Ratchet removed. The fixtures are under upgrade/removed/:
    a Ratchet 9.8 with a rule that names a check and a rule that is text only, and a 9.9 that removes both and adds one."""

    def files(self, register):
        return [self.fixture_file("upgrade/removed/" + register), "--from", self.fixture_file("upgrade/removed/old.json"),
                "--source", self.fixture_file("upgrade/removed/new.json")]

    def loaded(self, name):
        return registry.parse_json(self.fixture_bytes("upgrade/removed/" + name))

    def done(self, register, own, adopt=()):
        """The register with the printed steps done: each removed rule taken out of "adopted" and, when own holds its
        printed entry, added to "own", and the printed entries in adopt added to "adopted"."""
        new = self.loaded("new.json")
        result = json.loads(json.dumps(register))
        result["ratchet_version"] = new["version"]
        result["adopted"] = [item for item in result["adopted"] if item["key"] in registry.rules_by_key(new)]
        result["adopted"] += list(adopt)
        result["own"] += list(own)
        return result

    def test_a_removed_rule_kept_in_own_comes_with_an_entry_that_passes(self):
        # The review of round 1: an adopted rule with the status "built" and a "where", moved to "own" as the steps
        # said, failed check_register.py with "an own rule has exactly the fields key, rule, ratchet, source".
        code, output = run("upgrade.py", *self.files("register.json"))
        self.assertEqual(code, 0, output)
        for line in (
            'ratchet.dropped-checked: removed. Remove it from "adopted". To keep it as a rule of the project\'s own, also add '
            'this entry to "own". Its key has the prefix "example", from the register\'s first own rule. An own rule has only '
            'the fields key, rule, ratchet and source, so the entry has no status and no "where".',
            'ratchet.dropped: removed. Remove it from "adopted". To keep it as a rule of the project\'s own, also add this entry '
            'to "own". Its key has the prefix "example", from the register\'s first own rule. The key "example.dropped" is '
            'taken, so the entry has "example.dropped-2".',
            'Checked: with the steps above and no new rule adopted, register.json passes check_register.py against Ratchet 9.9, '
            'whether each removed rule is taken out or also moved to "own" with the entry printed.',
        ):
            self.assertIn(line, output)
        old = registry.rules_by_key(self.loaded("old.json"))
        own = [entry for entry in entries(output) if not entry["key"].startswith("ratchet.")]
        self.assertEqual([entry["key"] for entry in own], ["example.dropped-checked", "example.dropped-2"])
        for entry, key in zip(own, ("ratchet.dropped-checked", "ratchet.dropped")):
            with self.subTest(key=key):
                self.assertEqual(list(entry), list(check_register.RULE_FIELDS))
                for field in ("rule", "ratchet", "source"):
                    self.assertEqual(entry[field], old[key][field])
        register = self.loaded("register.json")
        for after in (self.done(register, own), self.done(register, [])):
            self.assertEqual(check_register.check(after, self.loaded("new.json"))[0], [])

    def test_the_check_of_the_steps_covers_a_removed_rule_kept_in_own(self):
        # If the entry for "own" kept the status and the "where", the steps would give a register that fails. The
        # script must then fail too, not print the steps.
        def with_status(rule, before, prefix, taken):
            return before
        with mock.patch.object(upgrade, "own_entry", with_status):
            out = io.StringIO()
            code = upgrade.main(self.files("register.json"), out=out)
        self.assertEqual(code, 1, out.getvalue())
        self.assertIn("an own rule has exactly the fields key, rule, ratchet, source", out.getvalue())
        self.assertIn("FAIL: the steps would not give a register that passes against Ratchet 9.9.", out.getvalue())
        self.assertNotIn("Steps for", out.getvalue())

    def test_a_register_that_adopts_only_removed_rules_gets_its_steps(self):
        code, output = run("upgrade.py", *self.files("register-only-removed.json"))
        self.assertEqual(code, 0, output)
        for line in (
            '1. Set "ratchet_version" to "9.9".',
            'ratchet.dropped-checked: removed. Remove it from "adopted". To keep it as a rule of the project\'s own, also add '
            'this entry to "own". The register has no own rule yet, so its key has a prefix made from the project\'s name, '
            '"the-example-project". Any other prefix of the same form will do, but not "ratchet".',
            "Every rule the register adopts was removed, and a register that adopts no rule from Ratchet does not pass "
            "check_register.py. Adopt at least one rule of Ratchet 9.9: the new rules below come with their entries.",
            "New rules, which the register may adopt:",
            'ratchet.added: new. The register may adopt it. To adopt it, add this entry to "adopted".',
            "Checked: with the steps above and the new rules adopted, register-only-removed.json passes check_register.py "
            'against Ratchet 9.9, whether each removed rule is taken out or also moved to "own" with the entry printed.',
        ):
            self.assertIn(line, output)
        self.assertNotIn("no rules from Ratchet", output)
        printed = entries(output)
        self.assertEqual([entry["key"] for entry in printed],
                         ["the-example-project.dropped-checked", "the-example-project.dropped", "ratchet.added"])
        register, new = self.loaded("register-only-removed.json"), self.loaded("new.json")
        for own in (printed[:2], []):
            self.assertEqual(check_register.check(self.done(register, own, adopt=printed[2:]), new)[0], [])

    def test_with_no_new_rule_a_register_that_adopts_only_removed_rules_gets_the_rules_to_start_with(self):
        new = self.loaded("new.json")
        new["rules"] = [rule for rule in new["rules"] if rule["key"] == "ratchet.keep"]
        out = io.StringIO()
        code = upgrade.report("register-only-removed.json", self.loaded("register-only-removed.json"),
                              self.loaded("old.json"), new, out, "check_register.py")
        self.assertEqual(code, 0, out.getvalue())
        output = out.getvalue()
        for line in (
            "Adopt at least one rule of Ratchet 9.9: the rules to start with below come with their entries.",
            "Rules to start with, which templates/register.json of Ratchet 9.9 adopts:",
            "Checked: with the steps above and the rules to start with adopted, register-only-removed.json passes",
        ):
            self.assertIn(line, output)
        self.assertNotIn("New rules", output)
        printed = entries(output)
        self.assertEqual([entry["key"] for entry in printed],
                         ["the-example-project.dropped-checked", "the-example-project.dropped", "ratchet.keep"])
        self.assertEqual(printed[2], upgrade.entry(registry.rules_by_key(new)["ratchet.keep"]))
        register = self.loaded("register-only-removed.json")
        for own in (printed[:2], []):
            self.assertEqual(check_register.check(self.done(register, own, adopt=printed[2:]), new)[0], [])

    def test_a_name_that_gives_no_prefix_or_ratchets_own_gives_project(self):
        old, new = self.loaded("old.json"), self.loaded("new.json")
        for project in ("Ratchet", "ÅÄÖ"):
            with self.subTest(project=project):
                register = self.loaded("register-only-removed.json")
                register["project"] = project
                steps, after = upgrade.plan(register, old, new)
                own = [step["entry"] for step in steps if step["kind"] == "removed"]
                self.assertEqual([entry["key"] for entry in own], ["project.dropped-checked", "project.dropped"])
                registers, kept, must_adopt = upgrade.outcomes(steps, after, new)
                self.assertTrue(kept)
                for done in registers:
                    self.assertEqual(check_register.check(done, new)[0], [])

    def test_a_register_that_adopts_nothing_from_ratchet_fails(self):
        # Not a Ratchet register: it does not pass check_register.py against the version it states.
        code, output = run("upgrade.py", *self.files("register-adopts-nothing.json"))
        self.assertEqual(code, 1, output)
        self.assertIn("no rules from Ratchet. A register that adopts nothing has nothing to check", output)
        self.assertIn("register-adopts-nothing.json does not pass check_register.py against Ratchet 9.8, the version it states.", output)
        self.assertNotIn("Steps for", output)


class UpgradingSteps(FixtureTest):
    """The steps in UPGRADING.md, run from the root of a project whose register is this repo's own at 0.8."""

    def test_every_command_in_the_steps_runs_from_the_root_of_a_project(self):
        project = self.scratch()
        shutil.copytree(ROOT, os.path.join(project, ".ratchet"), ignore=shutil.ignore_patterns(".git", "__pycache__"))
        shutil.copyfile(self.fixture_file("upgrade/released/0.8/register.json"), os.path.join(project, "register.json"))
        shutil.copyfile(self.fixture_file("upgrade/released/0.8/ratchet.json"), os.path.join(project, ".ratchet", "from.json"))
        text = read("UPGRADING.md")
        new = registry.load(os.path.join(ROOT, "ratchet.json"))
        # The steps fetch a tag that exists: a version with a date in the changelog, never one that is unreleased
        # (D-2026-11-19-batched-releases). Their example moves from the version before it.
        dated = re.findall(r"(?m)^## ([0-9]+\.[0-9]+) \([0-9]{4}-[0-9]{2}-[0-9]{2}\)$", read("CHANGELOG.md"))
        fetched = re.findall(r"git clone --branch v([0-9.]+) https://github.com/fabian-von-tiedemann/ratchet \.ratchet", text)
        self.assertEqual(fetched, ["0.9"])
        self.assertIn(fetched[0], dated)
        self.assertEqual(dated[dated.index(fetched[0]) + 1], "0.8")
        self.assertIn("git -C .ratchet show v0.8:ratchet.json > .ratchet/from.json", text)
        commands = re.findall(r"(?m)^\s*(python3 \.ratchet/\S.*)$", text)
        self.assertEqual([command.split()[1] for command in commands],
                         [".ratchet/checks/upgrade.py", ".ratchet/checks/check_register.py", ".ratchet/checks/check_register.py"])
        for number, command in enumerate(commands):
            with self.subTest(command=command):
                if number == 1:
                    # Step 3: the steps that upgrade.py printed, done in register.json.
                    path = os.path.join(project, "register.json")
                    with open(path, "rb") as handle:
                        register = registry.parse_json(handle.read())
                    _, after = upgrade.plan(register, upgrade.load_older(os.path.join(project, ".ratchet", "from.json")), new)
                    with open(path, "w", encoding="utf-8", newline="") as handle:
                        handle.write(json.dumps(after, indent=2, ensure_ascii=False) + "\n")
                result = subprocess.run([sys.executable] + shlex.split(command)[1:], cwd=project,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                self.assertEqual(result.returncode, 0, result.stdout)
                if number == 0:
                    self.assertIn('Set "ratchet_version" to "%s".' % new["version"], result.stdout)


if __name__ == "__main__":
    unittest.main()
