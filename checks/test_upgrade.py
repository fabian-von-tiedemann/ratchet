"""The upgrade path: checks/upgrade.py prints what a register must do to move to a newer Ratchet.

    python3 -m unittest discover -s checks -v

The fixtures are under checks/fixtures/upgrade/: a Ratchet 9.8 and a 9.9 with every kind of change between them,
a project's register on 9.8, and data files with one fault each. Under upgrade/removed/ are a smaller 9.8 and 9.9, in
which two rules that registers on 9.8 adopt are removed. Each test loads what it uses through FixtureTest.
Standard library only.
"""

import hashlib
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

# What the upgrade says to a register that moves from a version before 0.10 to 0.10 or later.
REGISTER_FORM = ('The form of register.json grew in Ratchet 0.10 (D-2026-11-20-generated-block). It may name an instruction '
                 'file in "instructions", and check_register.py then checks the block of rules it generates into that file. '
                 'An adopted rule may carry a "translation", bound to its English rule by a sha256. An own rule may carry '
                 '"status" and "where". A register without them stays valid, so none of this is a step.')


# What a copy of this repo leaves out when a test makes a clone of Ratchet from it: git's own files, bytecode, and what
# the checks do not read, so that each test copies little.
COPY_IGNORED = (".git", "__pycache__", "fixtures", "docs", "assets")


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git(directory, *args):
    """What git prints for args in directory, as text. No GIT_ variable, and no global or system config, is used."""
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    result = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "advice.detachedHead=false",
                             "-C", directory] + list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True)
    if result.returncode != 0:
        raise AssertionError("git %s: %s" % (" ".join(args), result.stdout))
    return result.stdout.strip()


def make_origin(directory, releases):
    """A git repo at directory that stands in for Ratchet on GitHub: this repo's files, then one commit and one annotated
    tag per release, each with its own ratchet.json. releases is [(version, the bytes of ratchet.json), ...], or
    [(version, the bytes of ratchet.json, {path: bytes}), ...] for a release whose other files differ from this repo's.
    Those files are this repo's again in the next release."""
    shutil.copytree(ROOT, directory, ignore=shutil.ignore_patterns(*COPY_IGNORED))
    git(directory, "init", "-q")
    for name, value in (("user.name", "Test"), ("user.email", "test@example.invalid"), ("gc.auto", "0"),
                        ("maintenance.auto", "false")):
        git(directory, "config", name, value)
    for release in releases:
        version, data, others = release if len(release) == 3 else release + ({},)
        for path, content in dict(others, **{"ratchet.json": data}).items():
            with open(os.path.join(directory, path), "wb") as handle:
                handle.write(content)
        git(directory, "add", "-A")
        git(directory, "commit", "-q", "-m", "Release %s" % version)
        git(directory, "tag", "-a", "-m", "Ratchet %s" % version, "v" + version)
        for path in others:
            shutil.copyfile(os.path.join(ROOT, path), os.path.join(directory, path))


def snapshot(top, skip=()):
    """Every file under top, as its bytes, and every directory, without following a link, but for the paths in skip."""
    state = {}
    for folder, folders, files in os.walk(top):
        folders[:] = [name for name in folders if os.path.relpath(os.path.join(folder, name), top) not in skip]
        for name in folders + files:
            path = os.path.join(folder, name)
            key = os.path.relpath(path, top)
            if os.path.islink(path):
                state[key] = ("link", os.readlink(path))
            elif os.path.isdir(path):
                state[key] = ("directory",)
            else:
                with open(path, "rb") as handle:
                    state[key] = ("file", handle.read())
    return state


def in_project(project, *args, env=None):
    """Run python3 with args from the root of a project, as an adopter does: (exit code, standard output and error)."""
    result = subprocess.run([sys.executable, "-B"] + list(args), cwd=project, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True)
    return result.returncode, result.stdout


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
        self.assertNotIn("The form of register.json", output, "the change of form of 0.10 is not between 9.8 and 9.9")
        self.assertNotIn("--print-instructions", output, "the register names no instruction file")
        self.assertNotIn("Traceback", output)

    def test_a_translation_of_a_rule_whose_text_changed_must_be_made_again(self):
        # #77: a translation is bound to the English rule by its sha256. An upgrade that changes the rule names the
        # translation that must be made again, and prints the entry without it, so that the steps give a register that
        # passes. A translation of a rule whose text did not change stays.
        register, old, new = self.loaded("register.json"), self.loaded("old/ratchet.json"), self.loaded("new/ratchet.json")
        old_by, new_by = registry.rules_by_key(old), registry.rules_by_key(new)
        for item in register["adopted"]:
            item["translation"] = {"language": "sv", "text": "En regel p\u00e5 svenska.", "sha256": sha256(old_by[item["key"]]["rule"])}
        self.assertEqual(check_register.check(register, old)[0], [])
        out = io.StringIO()
        code = upgrade.report("register.json", register, old, new, out, "check_register.py")
        output = out.getvalue()
        self.assertEqual(code, 0, output)
        self.assertIn('ratchet.reworded: changed: the rule. The register adopts it: replace its entry with this one. Its rule '
                      'changed, so its translation must be made again, and the entry has none. Translate the new rule and add '
                      'its "translation" with "sha256": "%s".' % sha256(new_by["ratchet.reworded"]["rule"]), output)
        self.assertIn('ratchet.dropped: removed. Remove it from "adopted".', output)
        self.assertIn("An own rule has no translation, so the entry has none.", output)
        printed = dict((entry["key"], entry) for entry in entries(output))
        self.assertNotIn("translation", printed["ratchet.reworded"])
        self.assertNotIn("translation", printed["example.dropped"])
        self.assertEqual(printed["ratchet.new-ratchet"]["translation"]["sha256"], sha256(new_by["ratchet.new-ratchet"]["rule"]),
                         "the rule did not change, only its ratchet, so the translation stays")
        self.assertNotIn("ratchet.new-ratchet: changed: the ratchet and the source. The register adopts it: replace its entry with "
                         "this one. Its rule changed", output)
        steps, after = upgrade.plan(register, old, new)
        self.assertEqual(after["adopted"][0]["translation"], register["adopted"][0]["translation"], "ratchet.keep keeps it")
        self.assertEqual(check_register.check(after, new)[0], [])

    def test_a_register_that_names_an_instruction_file_is_told_to_put_its_block_in_again(self):
        register, old, new = self.loaded("register.json"), self.loaded("old/ratchet.json"), self.loaded("new/ratchet.json")
        register["instructions"] = "docs/AGENTS.md"
        out = io.StringIO()
        code = upgrade.report("register.json", register, old, new, out, "check_register.py")
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("Then print REGISTER.md and docs/AGENTS.md again, put each in place, and check them:", out.getvalue())
        self.assertIn("    rm -f -- REGISTER.md.new && python3 check_register.py register.json --print-markdown > REGISTER.md.new && "
                      "rm -f -- REGISTER.md && mv -- REGISTER.md.new REGISTER.md\n", out.getvalue())
        # The .new file stands in the directory the commands run in, so nothing is removed or written through a directory
        # of the path before the check has refused a link there.
        self.assertIn("    rm -f -- AGENTS.md.new && python3 check_register.py register.json --print-instructions > AGENTS.md.new && "
                      "rm -f -- docs/AGENTS.md && mv -- AGENTS.md.new docs/AGENTS.md\n", out.getvalue())
        # The script and the register's path are quoted for the shell, on each of the three lines (review of 3219bf4).
        out = io.StringIO()
        upgrade.report("my project/register.json", register, old, new, out, "my checks/check_register.py")
        lines = [line for line in out.getvalue().split("\n") if line.startswith("    ") and "python3 " in line]
        self.assertEqual(len(lines), 3, out.getvalue())
        for line in lines:
            with self.subTest(line=line):
                self.assertIn("python3 'my checks/check_register.py' 'my project/register.json' ", line)
        self.assertNotIn("--write", out.getvalue())

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
        # Its rules lack "since", which every experimental rule has from 0.10, and it has no principles, which came in 0.10
        # with a principle for every rule (D-2026-11-20-principles-and-obligations).
        self.assertIn(FORM % ("9.8", "9.9", '"date" is gone, "experimental_cap" is new, "principles" is new, "sources" is gone, '
                              '"principle" in a rule is new and "since" in a rule is new', "9.8", "9.9", "9.9"), output)

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
        self.assertLess(output.index("The form of ratchet.json changed"), output.index("Then print REGISTER.md again"))

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
                # ratchet.si-version and ratchet.si-maintainer-approves, which this repo adopted, left in 0.10 for its own
                # rules (D-2026-11-20-proposal-triage, choice 5). The steps say to keep each in "own".
                for key in ("ratchet.si-version", "ratchet.si-maintainer-approves"):
                    self.assertIn('%s: removed. Remove it from "adopted". To keep it as a rule of the project\'s own, also add '
                                  'this entry to "own".' % key, output)
                # Every experimental rule has "since" from 0.10, a change of form in its rules (D-2026-11-19-one-point-oh).
                # 0.10 adds the principles, and every rule names one (D-2026-11-20-principles-and-obligations).
                since = '"principle" in a rule is new and "since" in a rule is new'
                if version in ("0.3", "0.4"):
                    # Neither has the cap, which came in 0.5 as a change of form. Every version before 0.9 has the date
                    # and the sources, which left ratchet.json in 0.9 (D-2026-11-19-batched-releases).
                    form = '"date" is gone, "experimental_cap" is new, "principles" is new, "sources" is gone, ' + since
                elif version == "0.9":
                    form = '"principles" is new, ' + since
                else:
                    form = '"date" is gone, "principles" is new, "sources" is gone, ' + since
                self.assertIn(FORM % (version, new["version"], form, version, new["version"], new["version"]), output)
                # 0.10 also changes the form of register.json, and every new field is optional (D-2026-11-20-generated-block).
                self.assertIn(REGISTER_FORM, output)
                # The rules that 0.7 and 0.10 add are new to each register before them. 0.8 adds none: it moves two pins
                # in "sources", which is not a field that the register holds. 0.9 adds none. ratchet.phases, which 0.6
                # added, leaves in 0.11 (D-2026-11-22-second-redraw, R8), so it is new to no register.
                self.assertNotIn("- ratchet.phases: new.", output)
                for added, rule in (("0.7", "ratchet.irreversible-waits"), ("0.10", "ratchet.review-by-risk"),
                                    ("0.10", "ratchet.one-exact-form")):
                    line = "- %s: new. The register may adopt it." % rule
                    if tuple(map(int, version.split("."))) < tuple(map(int, added.split("."))):
                        self.assertIn(line, output)
                    else:
                        self.assertNotIn(line, output)
                if version == "0.9":
                    # 0.10 adds two rules, ratchet.review-by-risk and ratchet.one-exact-form, changes three, ratchet.root-cause,
                    # ratchet.cr-wake and ratchet.si-subtract, and removes six: ratchet.cr-background-wait, merged into
                    # ratchet.cr-wake, three more and the two this repo moved to its own rules (D-2026-11-20-proposal-triage).
                    # 0.11 removes six more and changes ratchet.cr-workspace, and changes ratchet.cr-wake and
                    # ratchet.review-by-risk again (D-2026-11-22-second-redraw, step 2): 11 + 6 + 1 = 18. Step 3 changes
                    # ratchet.si-harden, removes ratchet.si-repeat-is-signal and ratchet.si-promote, and removes
                    # ratchet.si-subtract, which 0.10 changed: 18 + 3 = 21. Step 8, core batch A, adds ratchet.owner-paths
                    # and ratchet.ask-the-owner, removes the nine rules that go into them or leave the core, and changes
                    # ratchet.decision-as-file, ratchet.si-measure and ratchet.expected-tests-ran: 21 + 2 + 9 + 3 = 35.
                    # Step 10, core batch B, removes the five rules that go into ratchet.fresh-context and
                    # ratchet.evidence-before-done or leave the core, and changes those two: 35 + 5 + 2 = 42.
                    self.assertIn("In Ratchet %s, 42 rules are new, changed or removed." % new["version"], output)
                    for key in ("ratchet.owner-paths", "ratchet.ask-the-owner"):
                        self.assertIn("- %s: new. The register may adopt it." % key, output)
                    for key in ("ratchet.one-approver", "ratchet.kinds-apart", "ratchet.glossary", "ratchet.checks-owner-read"):
                        self.assertIn('%s: removed. Remove it from "adopted".' % key, output)
                    for key in ("ratchet.decision-as-file", "ratchet.expected-tests-ran"):
                        self.assertIn("%s: changed: " % key, output)
                    self.assertIn("ratchet.evidence-before-done: changed: the rule, the ratchet and the source.", output)
                    self.assertIn("Not adopted, so nothing to do: ratchet.cr-analysis-model (removed), ratchet.cr-background-wait "
                                  "(removed), ratchet.cr-does-not-build (removed), ratchet.cr-lead-with-ask (removed), "
                                  "ratchet.cr-next-task (removed), ratchet.cr-quiet-hours (removed), ratchet.cr-reads-first "
                                  "(removed), ratchet.cr-review (removed), ratchet.cr-verify-reports (removed), ratchet.cr-wake "
                                  "(changed), ratchet.cr-workspace (changed), ratchet.experiment-plan (removed), "
                                  "ratchet.findings-marked (removed), ratchet.five-choices (removed), ratchet.fresh-context (changed), "
                                  "ratchet.grill-first (removed), ratchet.look-up-facts (removed), ratchet.once-per-version (removed), "
                                  "ratchet.one-channel (removed), ratchet.phases (removed), ratchet.register-review-first (removed), "
                                  "ratchet.root-cause (changed), ratchet.run-early (removed), ratchet.si-harden (changed), "
                                  "ratchet.si-measure (changed), ratchet.si-promote (removed), ratchet.si-repeat-is-signal (removed), "
                                  "ratchet.si-subtract (removed), ratchet.verify-findings (removed).", output)
                steps, after = upgrade.plan(registry.parse_json(self.fixture_bytes("upgrade/released/%s/register.json" % version)),
                                            upgrade.load_older(old), new)
                self.assertEqual(check_register.check(after, new)[0], [])

    def test_without_from_a_copy_that_is_not_a_git_clone_cannot_run(self):
        # Without --from, the script fetches the tags of the clone it stands in. A copy of the checks outside any git work
        # tree has no tags: it says so, names --from, and writes nothing.
        project = self.scratch()
        shutil.copytree(ROOT, os.path.join(project, ".ratchet"), ignore=shutil.ignore_patterns(*COPY_IGNORED))
        with open(os.path.join(project, "register.json"), "wb") as handle:
            handle.write(self.fixture_bytes("upgrade/register.json"))
        before = snapshot(project)
        code, output = in_project(project, ".ratchet/checks/upgrade.py", "register.json")
        self.assertEqual(code, 2, output)
        self.assertIn("upgrade: cannot run: .ratchet is not a git clone of Ratchet", output)
        self.assertIn("--from", output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(snapshot(project), before)

    def test_from_and_the_options_of_the_one_command_are_not_mixed(self):
        register = self.fixture_file("upgrade/register.json")
        old = self.fixture_file("upgrade/old/ratchet.json")
        for args in (["--to", "9.9"], ["--no-fetch"]):
            with self.subTest(args=args):
                code, output = run("upgrade.py", register, "--from", old, *args)
                self.assertEqual(code, 2, output)
                self.assertIn("--from compares two files and fetches nothing", output)
        code, output = run("upgrade.py", register, "--source", old)
        self.assertEqual(code, 2, output)
        self.assertIn("--source is the newer file of --from", output)


# What the upgrade.py of v9.10 in the origin of OneCommand prints first, and no other release's does: a test that moves
# the clone to v9.10 sees it only when the upgrade.py there runs.
MARKER = "This is the upgrade.py of the test's v9.10."

# The upgrade.py of v0.10 in the origin of OneCommand: as Ratchet 0.10's, it compares two files given with --from, and
# without it fails as argparse does.
UPGRADE_0_10 = b"""import argparse
parser = argparse.ArgumentParser()
parser.add_argument("register")
parser.add_argument("--from", dest="older", required=True)
parser.parse_args()
print("This is the upgrade.py of the test's v0.10, which compares two files.")
"""


class OneCommand(FixtureTest):
    """The upgrade in one command (D-2026-11-22-second-redraw, step 6): without --from, upgrade.py fetches the tags of the
    clone of Ratchet it stands in, compares the tag the register states with the latest release, or the one asked for,
    and says how far behind the register is. A git repo made in a scratch directory stands in for Ratchet on GitHub, with
    this repo's checks and the ratchet.json of upgrade/old/ at v9.8 and of upgrade/new/ at v9.9. v9.10 has the rules of
    9.9, so that the latest release is found by number and not by text, and an upgrade.py that prints MARKER first.
    v0.10 has the rules of 9.8, comes before the first version whose upgrade.py does this, and has an upgrade.py that
    only compares two files. Two tags are not releases: v9.11-rc1 and v09.10. No test reaches the network."""

    def setUp(self):
        old, new = self.fixture_bytes("upgrade/old/ratchet.json"), self.fixture_bytes("upgrade/new/ratchet.json")
        newest = new.replace(b'"version": "9.9"', b'"version": "9.10"', 1)
        self.assertNotEqual(newest, new)
        script = read("checks/upgrade.py").encode("utf-8")
        start = b"    out = out or sys.stdout\n"
        marked = script.replace(start, start + b"    print(%r, file=out)\n" % MARKER.encode("utf-8"), 1)
        self.assertNotEqual(marked, script)
        self.origin = os.path.join(self.scratch(), "ratchet")
        make_origin(self.origin, [("0.10", old.replace(b'"version": "9.8"', b'"version": "0.10"', 1),
                                   {"checks/upgrade.py": UPGRADE_0_10}),
                                  ("9.8", old), ("9.9", new), ("9.10", newest, {"checks/upgrade.py": marked})])
        # Tags that are not releases: a release candidate after the latest, and the latest with a leading zero.
        git(self.origin, "tag", "v9.11-rc1", "v9.10^{commit}")
        git(self.origin, "tag", "-a", "-m", "Not a release", "v09.10", "v9.10^{commit}")

    def project(self, register="register.json", at="v9.8", shallow=False, version=None):
        """A project with a register from upgrade/ and Ratchet cloned into .ratchet at a tag. Returns its path. With version,
        the register states that version in place of its own."""
        project = self.scratch()
        data = self.fixture_bytes("upgrade/" + register)
        if version is not None:
            data = re.sub(rb'"ratchet_version": "[0-9.]+"', b'"ratchet_version": "' + version.encode("ascii") + b'"', data, 1)
            self.assertEqual(registry.parse_json(data)["ratchet_version"], version)
        with open(os.path.join(project, "register.json"), "wb") as handle:
            handle.write(data)
        if shallow:
            git(project, "clone", "-q", "--depth", "1", "--branch", at, "file://" + self.origin, ".ratchet")
        else:
            git(project, "clone", "-q", "--branch", at, self.origin, ".ratchet")
        return project

    def upgrade(self, project, *args):
        """Run the one command in the project. The files of the project, and those that git tracks in .ratchet, must be
        as they were, but for .ratchet moved to another tag, which a test checks itself."""
        before = snapshot(project, skip=(".ratchet",))
        code, output = in_project(project, ".ratchet/checks/upgrade.py", "register.json", *args)
        self.assertEqual(snapshot(project, skip=(".ratchet",)), before, "no file of the project changed")
        self.assertEqual(git(os.path.join(project, ".ratchet"), "status", "--porcelain", "--untracked-files=no"), "",
                         "no file that git tracks in .ratchet changed")
        self.assertNotIn("Traceback", output)
        return code, output

    def head(self, project):
        return git(os.path.join(project, ".ratchet"), "rev-parse", "HEAD")

    def tag(self, name):
        return git(self.origin, "rev-parse", name + "^{commit}")

    def offline(self, register="register.json", new="new/ratchet.json"):
        """What the offline mode prints for the same register and the same two versions, from the root of a project."""
        project = self.scratch()
        shutil.copytree(ROOT, os.path.join(project, ".ratchet"), ignore=shutil.ignore_patterns(*COPY_IGNORED))
        for name, fixture in (("register.json", register), ("old.json", "old/ratchet.json"), ("new.json", new)):
            with open(os.path.join(project, name), "wb") as handle:
                handle.write(self.fixture_bytes("upgrade/" + fixture))
        code, output = in_project(project, ".ratchet/checks/upgrade.py", "register.json", "--from", "old.json", "--source", "new.json")
        self.assertEqual(code, 0, output)
        return output

    def test_the_latest_release_is_fetched_compared_and_counted(self):
        # .ratchet is a shallow clone at v9.8, the version the register states, and has no other tag. The command fetches
        # the tags, finds v9.10 the latest by number, moves .ratchet there, and prints the steps from 9.8 to 9.10, which
        # are those of the offline mode with the same files, with the commands at the end naming .ratchet as typed.
        project = self.project(shallow=True)
        was = self.head(project)
        code, output = self.upgrade(project)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.head(project), self.tag("v9.10"))
        self.assertIn("Fetched the tags of .ratchet from origin.", output)
        self.assertIn("Moved .ratchet to v9.10. It was at %s. To move it back: git -C .ratchet checkout --detach %s" % (was, was), output)
        self.assertIn("register.json states Ratchet 9.8. The latest release is 9.10, 2 releases after it: 9.9 and 9.10.", output)
        self.assertIn("Then pin .github/workflows/ratchet.yml to the commit of v9.10: %s." % self.tag("v9.10"), output)
        # The steps come from the upgrade.py of v9.10, which the command runs once .ratchet is there: it prints MARKER,
        # and v9.8's, which the command was started with, does not.
        self.assertEqual(output.count(MARKER), 1, output)
        self.assertLess(output.index("Moved .ratchet to v9.10."), output.index(MARKER))
        self.assertLess(output.index(MARKER), output.index("register.json states Ratchet 9.8."))
        offline = self.offline().replace("Ratchet 9.9", "Ratchet 9.10").replace('"9.9"', '"9.10"')
        self.assertIn("In Ratchet 9.10, 9 rules are new, changed or removed.", output)
        self.assertIn(offline, output)
        self.assertIn("python3 .ratchet/checks/check_register.py register.json --markdown REGISTER.md", output)

    def test_the_release_asked_for_is_compared(self):
        project = self.project()
        for asked in ("9.9", "v9.9"):
            with self.subTest(asked=asked):
                code, output = self.upgrade(project, "--to", asked)
                self.assertEqual(code, 0, output)
                self.assertEqual(self.head(project), self.tag("v9.9"))
                self.assertIn("register.json states Ratchet 9.8. The release asked for is 9.9, 1 release after it: 9.9.", output)
                self.assertIn(self.offline(), output)
                self.assertIn("Then pin .github/workflows/ratchet.yml to the commit of v9.9: %s." % self.tag("v9.9"), output)
                self.assertNotIn(MARKER, output)

    def test_a_clone_already_at_the_release_is_not_moved(self):
        project = self.project(at="v9.10")
        code, output = self.upgrade(project, "--no-fetch")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.head(project), self.tag("v9.10"))
        self.assertNotIn("Fetched", output)
        self.assertNotIn("Moved", output)
        self.assertIn("register.json states Ratchet 9.8. The latest release is 9.10, 2 releases after it: 9.9 and 9.10.", output)

    def test_a_register_on_the_latest_release_is_already_current(self):
        project = self.project(register="register-current.json", at="v9.9")
        code, output = self.upgrade(project, "--to", "9.9")
        self.assertEqual(code, 0, output)
        self.assertIn("register.json states Ratchet 9.9, the release asked for. It is not behind.", output)
        self.assertIn("register.json is on Ratchet 9.9, the version of this Ratchet. Nothing to change.", output)
        self.assertNotIn("Then pin", output)
        self.assertEqual(self.head(project), self.tag("v9.9"))

    def test_a_release_that_is_not_a_tag_is_refused(self):
        # The release tags are listed, and the two tags of the origin that are not releases are not among them.
        project = self.project()
        was = self.head(project)
        tags = git(os.path.join(project, ".ratchet"), "tag", "--list").split()
        self.assertIn("v9.11-rc1", tags)
        self.assertIn("v09.10", tags)
        listed = " Its release tags are v0.10, v9.8, v9.9 and v9.10."
        for asked, said in (("9.7", "there is no release tag v9.7 in .ratchet." + listed),
                            ("v12.0", "there is no release tag v12.0 in .ratchet." + listed),
                            ("9.11", "there is no release tag v9.11 in .ratchet." + listed),
                            ("v9.11-rc1", "--to takes a version such as 0.11, or its tag, v0.11, not 'v9.11-rc1'."),
                            ("v09.10", "--to takes a version such as 0.11, or its tag, v0.11, not 'v09.10'."),
                            ("09.10", "--to takes a version such as 0.11, or its tag, v0.11, not '09.10'."),
                            ("latest", "--to takes a version such as 0.11, or its tag, v0.11, not 'latest'."),
                            ("9.9.1", "--to takes a version such as 0.11, or its tag, v0.11, not '9.9.1'.")):
            with self.subTest(asked=asked):
                code, output = self.upgrade(project, "--to", asked)
                self.assertEqual(code, 2, output)
                self.assertIn("upgrade: cannot run: " + said, output)
                self.assertEqual(self.head(project), was, ".ratchet is not moved")

    def test_a_tag_that_is_not_a_release_is_not_the_latest(self):
        # v9.11-rc1 comes after v9.10 if read as text or by its first numbers, and v09.10 names 9.10 with a leading zero.
        # Neither is a release, so the latest is v9.10, and .ratchet moves to its commit by the tag v9.10.
        project = self.project()
        code, output = self.upgrade(project, "--no-fetch")
        self.assertEqual(code, 0, output)
        self.assertIn("Moved .ratchet to v9.10.", output)
        self.assertIn("The latest release is 9.10, 2 releases after it: 9.9 and 9.10.", output)
        self.assertNotIn("9.11", output)
        self.assertNotIn("v09.10", output)

    def test_a_release_before_the_first_that_fetches_is_refused(self):
        # A register before 0.10, asked to move to 0.10, is told to compare two files: 0.10's upgrade.py does not fetch.
        project = self.project(version="0.9")
        was = self.head(project)
        code, output = self.upgrade(project, "--to", "0.10")
        self.assertEqual(code, 2, output)
        self.assertIn("upgrade: cannot run: Ratchet 0.10 comes before 0.11, the first version whose upgrade.py fetches and "
                      "compares the tags itself. Compare two files with --from, as the UPGRADING.md of v0.10 says.", output)
        self.assertEqual(self.head(project), was, ".ratchet is not moved")

    def test_a_release_older_than_the_register_fails(self):
        # Also a release before 0.11: that it goes back is what is wrong, not that its upgrade.py does not fetch.
        project = self.project(register="register-current.json", at="v9.9")
        for asked, said in (("9.8", "9.8"), ("0.10", "0.10")):
            with self.subTest(asked=asked):
                code, output = self.upgrade(project, "--to", asked)
                self.assertEqual(code, 1, output)
                self.assertIn("FAIL: Ratchet %s, the release asked for, is older than 9.9, the version register.json states. An "
                              "upgrade does not go back." % said, output)
                self.assertNotIn("cannot run", output)
                self.assertEqual(self.head(project), self.tag("v9.9"))

    def test_missing_history_in_a_shallow_clone_is_named(self):
        # A shallow clone at v9.9 holds only that tag. With --no-fetch the tag the register states is not there, and the
        # command says how to get it. Without --no-fetch it fetches it.
        project = self.project(at="v9.9", shallow=True)
        code, output = self.upgrade(project, "--no-fetch")
        self.assertEqual(code, 2, output)
        self.assertIn("upgrade: cannot run: register.json states Ratchet 9.8, and .ratchet has no tag v9.8 to compare with. "
                      ".ratchet is a shallow clone, which holds only the tags it was cloned with, and --no-fetch fetched no "
                      "other. Run again without --no-fetch, or fetch the tags: git -C .ratchet fetch --tags origin", output)
        self.assertEqual(self.head(project), self.tag("v9.9"))
        code, output = self.upgrade(project, "--to", "9.9")
        self.assertEqual(code, 0, output)
        self.assertIn("register.json states Ratchet 9.8. The release asked for is 9.9, 1 release after it: 9.9.", output)

    def test_a_version_that_was_never_released_has_no_history(self):
        project = self.project(register="register-other-version.json")
        was = self.head(project)
        code, output = self.upgrade(project)
        self.assertEqual(code, 2, output)
        self.assertIn("upgrade: cannot run: register.json states Ratchet 9.7, and .ratchet has no tag v9.7 to compare with. "
                      "origin has none either, so Ratchet 9.7 was never released. Its release tags are v0.10, v9.8, v9.9 and "
                      "v9.10.", output)
        self.assertEqual(self.head(project), was)

    def test_a_fetch_that_fails_is_named_and_no_fetch_uses_the_tags_there_are(self):
        project = self.project()
        clone = os.path.join(project, ".ratchet")
        git(clone, "remote", "set-url", "origin", os.path.join(project, "nowhere"))
        was = self.head(project)
        code, output = self.upgrade(project)
        self.assertEqual(code, 2, output)
        self.assertIn("upgrade: cannot run: the tags of .ratchet could not be fetched from origin:", output)
        self.assertIn("To use the tags already in .ratchet, run again with --no-fetch.", output)
        self.assertEqual(self.head(project), was)
        code, output = self.upgrade(project, "--no-fetch")
        self.assertEqual(code, 0, output)
        self.assertIn("The latest release is 9.10", output)

    def test_a_register_that_does_not_pass_against_its_version_leaves_the_clone_where_it_was(self):
        project = self.project(register="register-drifted.json")
        was = self.head(project)
        code, output = self.upgrade(project)
        self.assertEqual(code, 1, output)
        self.assertIn("the rule of ratchet.reworded differs from Ratchet 9.8", output)
        self.assertIn("register.json does not pass check_register.py against Ratchet 9.8, the version it states. Fix it first", output)
        self.assertNotIn("Moved", output)
        self.assertEqual(self.head(project), was)

    def test_a_clone_with_changes_of_its_own_is_not_moved(self):
        project = self.project()
        was = self.head(project)
        path = os.path.join(project, ".ratchet", "README.md")
        with open(path, "ab") as handle:
            handle.write(b"\nA line of the project's own.\n")
        before = snapshot(project)
        code, output = in_project(project, ".ratchet/checks/upgrade.py", "register.json", "--no-fetch")
        self.assertEqual(code, 2, output)
        self.assertIn("upgrade: cannot run: .ratchet has changes to files that git tracks in it, so it is not moved.", output)
        inside = os.path.join(".ratchet", ".git")
        self.assertEqual(snapshot(project, skip=(inside,)),
                         dict((k, v) for k, v in before.items() if k != inside and not k.startswith(inside + os.sep)))
        self.assertEqual(self.head(project), was)

    def on_branch(self, version, at):
        """A project whose register states version, with .ratchet on a branch work at the tag at. Returns its path."""
        project = self.project(version=version)
        git(os.path.join(project, ".ratchet"), "checkout", "-q", "-b", "work", at)
        return project

    def run_printed(self, project, output):
        """Run, through /bin/sh from the root of the project, the one command the refusal printed to move .ratchet."""
        commands = re.findall(r"git -C \S+ checkout --detach \S+?(?=,| and|$)", output)
        self.assertEqual(len(commands), 1, output)
        env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        result = subprocess.run(["/bin/sh", "-c", commands[0]], cwd=project, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        return commands[0]

    def test_a_clone_on_a_branch_is_not_moved(self):
        # A clone on a branch, such as a checkout someone works on Ratchet in, is not moved. It is told to leave the branch
        # at the release, and the same command then runs. A clone already at the release is used where it stands.
        project = self.on_branch("9.8", "v9.9")
        clone = os.path.join(project, ".ratchet")
        code, output = self.upgrade(project, "--no-fetch")
        self.assertEqual(code, 2, output)
        self.assertIn("upgrade: cannot run: .ratchet is on the branch work, so it is not moved. Move it to v9.10, the release "
                      "to upgrade to, with git -C .ratchet checkout --detach v9.10, and run again. The branch stays where it "
                      "is: git -C .ratchet checkout work goes back to it.", output)
        self.assertEqual(git(clone, "symbolic-ref", "--short", "HEAD"), "work")
        self.assertEqual(self.head(project), self.tag("v9.9"))
        git(clone, "checkout", "-q", "-B", "work", "v9.10")
        code, output = self.upgrade(project, "--no-fetch")
        self.assertEqual(code, 0, output)
        self.assertEqual(git(clone, "symbolic-ref", "--short", "HEAD"), "work")

    def test_the_command_printed_for_a_clone_on_a_branch_lets_the_upgrade_run(self):
        # Gemini's review of 0425ffe: the command printed moved .ratchet to the tag of the version the register states.
        # For a register on 0.10 or earlier, the upgrade.py there does not do the one command, so running again failed.
        # The command printed is run as printed, then the upgrade again, as typed the first time: it passes, from a
        # register on a release before 0.11 and from one after, with --to and without.
        for version, args, release in (("0.10", ("--no-fetch",), "v9.10"), ("9.8", ("--no-fetch",), "v9.10"),
                                       ("0.10", ("--no-fetch", "--to", "9.9"), "v9.9"), ("9.8", (), "v9.10")):
            with self.subTest(version=version, args=args):
                project = self.on_branch(version, "v9.9" if release == "v9.10" else "v9.8")
                code, output = self.upgrade(project, *args)
                self.assertEqual(code, 2, output)
                self.assertIn("is on the branch work, so it is not moved.", output)
                printed = self.run_printed(project, output)
                code, output = self.upgrade(project, *args)
                self.assertEqual(code, 0, output)
                self.assertEqual(printed, "git -C .ratchet checkout --detach %s" % release)
                self.assertIn("register.json states Ratchet %s." % version, output)
                self.assertIn('1. Set "ratchet_version" to "%s".' % release[1:], output)
                self.assertIn("Then pin .github/workflows/ratchet.yml to the commit of %s: %s." % (release, self.tag(release)),
                              output)
                self.assertNotIn("--from", output)
                self.assertEqual(self.head(project), self.tag(release))
                self.assertEqual(git(os.path.join(project, ".ratchet"), "rev-parse", "--verify", "refs/heads/work"),
                                 self.tag("v9.9" if release == "v9.10" else "v9.8"), "the branch stays where it was")

    def test_a_register_whose_path_starts_with_a_dash_is_read_as_a_path(self):
        # The command runs the upgrade.py of the release with the register's path after --, so that a path that starts
        # with - is not read as an option there.
        project = self.project()
        os.rename(os.path.join(project, "register.json"), os.path.join(project, "-register.json"))
        before = snapshot(project, skip=(".ratchet",))
        code, output = in_project(project, ".ratchet/checks/upgrade.py", "--no-fetch", "--", "-register.json")
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(project, skip=(".ratchet",)), before)
        self.assertEqual(self.head(project), self.tag("v9.10"))
        self.assertIn(MARKER, output)
        self.assertIn("-register.json states Ratchet 9.8. The latest release is 9.10", output)
        self.assertIn("Steps for -register.json:", output)

    def test_a_git_variable_of_the_caller_does_not_lead_git_to_another_repo(self):
        # Run from a git hook, GIT_DIR names the project's repo. The command still reads .ratchet, and nothing else.
        project = self.project()
        other = os.path.join(self.scratch(), "other")
        os.mkdir(other)
        git(other, "init", "-q")
        env = dict(os.environ, GIT_DIR=os.path.join(other, ".git"), GIT_WORK_TREE=other)
        before = snapshot(other)
        code, output = in_project(project, ".ratchet/checks/upgrade.py", "register.json", "--no-fetch", env=env)
        self.assertEqual(code, 0, output)
        self.assertIn("The latest release is 9.10", output)
        self.assertEqual(snapshot(other), before)


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
            'this entry to "own". Its key has the prefix "example", from the register\'s first own rule. An own rule may say '
            'where its check stands, so the entry keeps its status and its "where".',
            'ratchet.dropped: removed. Remove it from "adopted". To keep it as a rule of the project\'s own, also add this entry '
            'to "own". Its key has the prefix "example", from the register\'s first own rule. The key "example.dropped" is '
            'taken, so the entry has "example.dropped-2". The changelog of Ratchet 9.9 says why it was removed. When it was '
            'merged into another rule, the register may adopt that rule in its place.',
            'Checked: with the steps above and no new rule adopted, register.json passes check_register.py against Ratchet 9.9, '
            'whether each removed rule is taken out or also moved to "own" with the entry printed.',
        ):
            self.assertIn(line, output)
        old = registry.rules_by_key(self.loaded("old.json"))
        own = [entry for entry in entries(output) if not entry["key"].startswith("ratchet.")]
        self.assertEqual([entry["key"] for entry in own], ["example.dropped-checked", "example.dropped-2"])
        for entry, key, fields in zip(own, ("ratchet.dropped-checked", "ratchet.dropped"),
                                      (check_register.RULE_FIELDS + check_register.STATUS_FIELDS, check_register.RULE_FIELDS)):
            with self.subTest(key=key):
                self.assertEqual(list(entry), list(fields))
                for field in ("rule", "ratchet", "source"):
                    self.assertEqual(entry[field], old[key][field])
        self.assertEqual((own[0]["status"], own[0]["where"]), ("built", "checks/status.sh"))
        register = self.loaded("register.json")
        for after in (self.done(register, own), self.done(register, [])):
            self.assertEqual(check_register.check(after, self.loaded("new.json"))[0], [])

    def test_the_check_of_the_steps_covers_a_removed_rule_kept_in_own(self):
        # If the entry for "own" gave a rule that is text only a status, the steps would give a register that fails. The
        # script must then fail too, not print the steps.
        own_entry = upgrade.own_entry
        def with_status(rule, before, prefix, taken):
            return dict(own_entry(rule, before, prefix, taken), status="built", where="checks/status.sh")
        with mock.patch.object(upgrade, "own_entry", with_status):
            out = io.StringIO()
            code = upgrade.main(self.files("register.json"), out=out)
        self.assertEqual(code, 1, out.getvalue())
        self.assertIn("example.dropped-2 is text only. It cannot have a status or a place where its check lives", out.getvalue())
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
    """The steps in UPGRADING.md, run from the root of a project whose register is this repo's own at 0.9."""

    def test_every_command_in_the_steps_runs_from_the_root_of_a_project(self):
        # UPGRADING.md gives one command. A git repo made here stands in for Ratchet on GitHub, with the ratchet.json of
        # v0.9 at its tag, and this repo as it is at the tag of its own version. The project's .ratchet is a clone at v0.9.
        # The command is run as written, the steps it prints are done in register.json, and then each command it printed
        # is run as printed. Each must pass.
        new = registry.load(os.path.join(ROOT, "ratchet.json"))
        origin = os.path.join(self.scratch(), "ratchet")
        make_origin(origin, [("0.9", self.fixture_bytes("upgrade/released/0.9/ratchet.json")),
                             (new["version"], read("ratchet.json").encode("utf-8"))])
        project = self.scratch()
        with open(os.path.join(project, "register.json"), "wb") as handle:
            handle.write(self.fixture_bytes("upgrade/released/0.9/register.json"))
        git(project, "clone", "-q", "--branch", "v0.9", origin, ".ratchet")
        text = read("UPGRADING.md")
        self.assertIsNone(re.search(r"git clone (-|http)", text), "the README clones Ratchet the first time, and the command fetches")
        # A clone on 0.10 or earlier has an upgrade.py that does not fetch: it is moved once, to the first that does.
        self.assertIn("git -C .ratchet fetch --tags origin\ngit -C .ratchet checkout --detach v%s\n" % upgrade.FIRST, text)
        commands = re.findall(r"(?m)^\s*((?:rm -f \S+ && )?python3 \.ratchet/\S.*)$", text)
        self.assertEqual(commands, ["python3 .ratchet/checks/upgrade.py register.json"])
        code, output = in_project(project, *shlex.split(commands[0])[1:])
        self.assertEqual(code, 0, output)
        self.assertIn("register.json states Ratchet 0.9. The latest release is %s" % new["version"], output)
        self.assertIn('Set "ratchet_version" to "%s".' % new["version"], output)
        self.assertEqual(git(os.path.join(project, ".ratchet"), "rev-parse", "HEAD"),
                         git(origin, "rev-parse", "v%s^{commit}" % new["version"]))
        # The steps that upgrade.py printed, done in register.json.
        path = os.path.join(project, "register.json")
        with open(path, "rb") as handle:
            register = registry.parse_json(handle.read())
        _, after = upgrade.plan(register, upgrade.load_older(self.fixture_file("upgrade/released/0.9/ratchet.json")), new)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(after, indent=2, ensure_ascii=False) + "\n")
        printed = re.findall(r"(?m)^    ((?:rm -f |python3 )\S.*)$", output)
        self.assertEqual(len(printed), 2, output)
        for command in printed:
            with self.subTest(command=command):
                result = subprocess.run(["/bin/sh", "-c", command.replace("python3 ", shlex.quote(sys.executable) + " -B ")],
                                        cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                self.assertEqual(result.returncode, 0, result.stdout)

    def test_the_printed_commands_run_in_order_for_a_register_that_names_an_instruction_file(self):
        # Round 2 of #100: the commands that upgrade.py prints are run as printed, one after the other, on a register
        # that names AGENTS.md, whose block the older register generated. Each must pass.
        project = self.scratch()
        shutil.copytree(ROOT, os.path.join(project, ".ratchet"), ignore=shutil.ignore_patterns(".git", "__pycache__"))
        shutil.copyfile(self.fixture_file("upgrade/released/0.9/ratchet.json"), os.path.join(project, ".ratchet", "from.json"))
        register = registry.parse_json(self.fixture_bytes("upgrade/released/0.9/register.json"))
        register["instructions"] = "AGENTS.md"
        path = os.path.join(project, "register.json")
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(register, indent=2, ensure_ascii=False) + "\n")
        with open(os.path.join(project, "AGENTS.md"), "w", encoding="utf-8", newline="") as handle:
            handle.write(check_register.render_block(register) + "\n# The project's own text\n")
        with open(os.path.join(project, "REGISTER.md"), "w", encoding="utf-8", newline="") as handle:
            handle.write(check_register.render(register))
        result = subprocess.run([sys.executable, ".ratchet/checks/upgrade.py", "register.json", "--from", ".ratchet/from.json"],
                                cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        commands = re.findall(r"(?m)^    ((?:rm -f |python3 )\S.*)$", result.stdout)
        self.assertEqual(len(commands), 3, result.stdout)
        # The steps, done in register.json.
        new = registry.load(os.path.join(ROOT, "ratchet.json"))
        _, after = upgrade.plan(register, upgrade.load_older(os.path.join(project, ".ratchet", "from.json")), new)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(after, indent=2, ensure_ascii=False) + "\n")
        for command in commands:
            with self.subTest(command=command):
                ran = subprocess.run(["/bin/sh", "-c", command.replace("python3 ", shlex.quote(sys.executable) + " ")],
                                     cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                self.assertEqual(ran.returncode, 0, ran.stdout)
        with open(os.path.join(project, "AGENTS.md"), encoding="utf-8", newline="") as handle:
            self.assertEqual(handle.read(), check_register.render_block(after) + "\n# The project's own text\n")


if __name__ == "__main__":
    unittest.main()
