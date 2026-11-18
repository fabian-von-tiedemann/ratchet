"""The upgrade path: checks/upgrade.py prints what a register must do to move to a newer Ratchet.

    python3 -m unittest discover -s checks -v

The fixtures are under checks/fixtures/upgrade/: a Ratchet 9.8 and a 9.9 with every kind of change between them,
a project's register on 9.8, and data files with one fault each. Each test loads what it uses through FixtureTest.
Standard library only.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import unittest

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
    "missing-field": "missing field 'sources'",
    "rule-unknown-field": "ratchet.reworded: unknown field waived",
    "rule-hidden-character": "ratchet.reworded: rule holds U+200B",
    "version-number": "version must look like 0.2",
    "key-twice": "ratchet.reworded: the key is used twice",
    "unknown-part": "ratchet.reworded: unknown part two",
}


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
            'ratchet.dropped: removed. Remove it from "adopted". To keep it, move it to "own" under the project\'s own prefix.',
            "ratchet.added: new. The register may adopt it. To adopt it, add this entry to \"adopted\".",
            "ratchet.added-text: new. The register may adopt it. To adopt it, add this entry to \"adopted\".",
            "Not adopted, so nothing to do: ratchet.changed-unadopted (changed), ratchet.dropped-unadopted (removed).",
            "Checked: with the steps above and no new rule adopted, register.json passes check_register.py against Ratchet 9.9.",
            "The reasons for each change are in CHANGELOG.md of Ratchet 9.9, in the entries after 9.8.",
        ):
            self.assertIn(line, output)
        self.assertNotIn("ratchet.keep", output, "a rule that did not change is not listed")
        self.assertNotIn("ratchet.left-out", output, "a rule that did not change is not listed, adopted or not")
        self.assertNotIn("Traceback", output)

    def test_each_printed_entry_is_the_rule_as_it_stands_in_the_newer_ratchet(self):
        code, output = self.upgrade()
        self.assertEqual(code, 0, output)
        new = registry.rules_by_key(self.loaded("new/ratchet.json"))
        printed = entries(output)
        self.assertEqual([entry["key"] for entry in printed],
                         ["ratchet.reworded", "ratchet.now-checked", "ratchet.now-text", "ratchet.new-ratchet", "ratchet.added", "ratchet.added-text"])
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
        # Ratchet's own register.json and ratchet.json as they stood at the tags v0.3 and v0.4.
        new = registry.load(os.path.join(ROOT, "ratchet.json"))
        for version in ("0.3", "0.4"):
            with self.subTest(version=version):
                register = self.fixture_file("upgrade/released/%s/register.json" % version)
                old = self.fixture_file("upgrade/released/%s/ratchet.json" % version)
                code, output = run("upgrade.py", register, "--from", old)
                self.assertEqual(code, 0, output)
                self.assertIn("register.json is on Ratchet %s." % version, output)
                self.assertIn('Set "ratchet_version" to "%s".' % new["version"], output)
                self.assertIn("passes check_register.py against Ratchet %s" % new["version"], output)
                steps, after = upgrade.plan(registry.parse_json(self.fixture_bytes("upgrade/released/%s/register.json" % version)),
                                            upgrade.load_older(old), new)
                self.assertEqual(check_register.check(after, new)[0], [])

    def test_the_older_ratchet_is_required(self):
        code, output = run("upgrade.py", self.fixture_file("upgrade/register.json"))
        self.assertEqual(code, 2, output)
        self.assertIn("--from", output)


class UpgradingSteps(FixtureTest):
    """The steps in UPGRADING.md, run from the root of a project whose register is this repo's own at 0.4."""

    def test_every_command_in_the_steps_runs_from_the_root_of_a_project(self):
        project = self.scratch()
        shutil.copytree(ROOT, os.path.join(project, ".ratchet"), ignore=shutil.ignore_patterns(".git", "__pycache__"))
        shutil.copyfile(self.fixture_file("upgrade/released/0.4/register.json"), os.path.join(project, "register.json"))
        shutil.copyfile(self.fixture_file("upgrade/released/0.4/ratchet.json"), os.path.join(project, ".ratchet", "from.json"))
        text = read("UPGRADING.md")
        new = registry.load(os.path.join(ROOT, "ratchet.json"))
        self.assertIn("git clone --branch v%s https://github.com/fabian-von-tiedemann/ratchet .ratchet" % new["version"], text)
        self.assertIn("git -C .ratchet show v0.4:ratchet.json > .ratchet/from.json", text)
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
