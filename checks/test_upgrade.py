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
import run_pinned  # noqa: E402
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

# What a copy of this repo leaves out when a test makes a clone of Ratchet from it: git's own files, bytecode, and what
# the checks do not read, so that each test copies little.
COPY_IGNORED = (".git", "__pycache__", "fixtures", "docs", "assets")


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# No automatic gc or maintenance in a repository a test makes. git starts them in the background after a commit or a
# fetch, and one still writing in .git is a likely, not a proven, cause of an intermittent "could not parse HEAD" and
# of a removal that finds .git/objects/pack not empty. For this call, and, for init and clone, in the new repository's
# own config, so that a script under test that runs git there starts none either.
QUIET = (("gc.auto", "0"), ("maintenance.auto", "false"))


def git(directory, *args):
    """What git prints for args in directory, as text. No GIT_ variable, and no global or system config, is used."""
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    if args[:1] == ("clone",):
        args = args[:1] + tuple(part for name, value in QUIET for part in ("--config", "%s=%s" % (name, value))) + args[1:]
    quiet = [part for name, value in QUIET for part in ("-c", "%s=%s" % (name, value))]
    result = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "advice.detachedHead=false"]
                            + quiet + ["-C", directory] + list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True)
    if result.returncode != 0:
        raise AssertionError("git %s: %s" % (" ".join(args), result.stdout))
    if args[:1] == ("init",):
        for name, value in QUIET:
            git(directory, "config", name, value)
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

    def upgrade(self, *args, **files):
        return run("upgrade.py", *(self.files(**files) + list(args)))

    def loaded(self, name):
        return registry.parse_json(self.fixture_bytes("upgrade/" + name))

    def test_every_change_is_listed_with_what_the_register_must_do(self):
        # With --new-rules full, the new rules come with their entries, as before #181.
        code, output = self.upgrade("--new-rules", "full")
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
        self.assertIn("    rm -f -- REGISTER.md.new && python3 check_register.py --print-markdown -- register.json > REGISTER.md.new && "
                      "rm -f -- REGISTER.md && mv -- REGISTER.md.new REGISTER.md\n", out.getvalue())
        # The .new file stands in the directory the commands run in, so nothing is removed or written through a directory
        # of the path before the check has refused a link there.
        self.assertIn("    rm -f -- AGENTS.md.new && python3 check_register.py --print-instructions -- register.json > AGENTS.md.new && "
                      "rm -f -- docs/AGENTS.md && mv -- AGENTS.md.new docs/AGENTS.md\n", out.getvalue())
        self.assertIn("    python3 check_register.py --markdown REGISTER.md -- register.json\n", out.getvalue())
        # The script and the register's path are quoted for the shell, on each of the three lines (review of 3219bf4).
        out = io.StringIO()
        upgrade.report("my project/register.json", register, old, new, out, "my checks/check_register.py")
        lines = [line for line in out.getvalue().split("\n") if line.startswith("    ") and "python3 " in line]
        self.assertEqual(len(lines), 3, out.getvalue())
        for line in lines:
            with self.subTest(line=line):
                self.assertIn("python3 'my checks/check_register.py' --", line)
                self.assertIn(" -- 'my project/register.json'", line)
        self.assertNotIn("--write", out.getvalue())

    def test_a_row_by_reference_whose_rule_or_ratchet_changed_is_told_its_new_sha256(self):
        # D-2026-11-22-second-redraw, step 9a: the sha256 of a row by reference covers the rule and its ratchet, so an
        # upgrade that changes either says that it no longer matches, prints the new one, and asks the project to read its
        # own wording again. The register passes against the version it states until the owner moves the version.
        register, old, new = self.loaded("register.json"), self.loaded("old/ratchet.json"), self.loaded("new/ratchet.json")
        old_by, new_by = registry.rules_by_key(old), registry.rules_by_key(new)
        def reference(rule):
            return sha256(rule["rule"] + "\n" + rule["ratchet"])
        for item in register["adopted"]:
            if item["key"] in ("ratchet.keep", "ratchet.reworded", "ratchet.new-ratchet", "ratchet.dropped"):
                for field in ("rule", "ratchet", "source"):
                    del item[field]
                item.update(stands_in="RULES.md", sha256=reference(old_by[item["key"]]))
        self.assertEqual(check_register.check(register, old)[0], [], "it passes against the version it states")
        moved = dict(register, ratchet_version=new["version"])
        self.assertIn("ratchet.reworded: the sha256 is ", "\n".join(check_register.check(moved, new)[0]),
                      "it fails once the version is moved and the sha256 is not")
        out = io.StringIO()
        code = upgrade.report("register.json", register, old, new, out, "check_register.py")
        output = out.getvalue()
        self.assertEqual(code, 0, output)
        for key in ("ratchet.reworded", "ratchet.new-ratchet"):
            self.assertIn("It is adopted by reference, and its rule or its ratchet changed, so its sha256 no longer matches: the "
                          "new sha256 is %s. Read the project's own wording in RULES.md again against the new rule, and change "
                          "it where it no longer says what the rule says." % reference(new_by[key]), output)
            # The new rule and its ratchet are printed, so the wording can be read against them (review of step 9a).
            self.assertIn("\nThe rule in Ratchet 9.9, to read the wording in RULES.md against: %s\nIts ratchet: %s\n"
                          % (new_by[key]["rule"], new_by[key]["ratchet"]), output)
        self.assertEqual(output.count("to read the wording in RULES.md against"), 2, "not for a copied row or one removed")
        self.assertNotIn("ratchet.keep:", output, "a rule that did not change is not listed")
        self.assertIn("It was adopted by reference, and an own rule stands in the register in full, so the entry holds Ratchet's "
                      "text of it, which the project may replace with its own wording. Take the line "
                      "<!-- ratchet:rule ratchet.dropped --> out of RULES.md, since no row names it there.", output)
        printed = dict((entry["key"], entry) for entry in entries(output))
        self.assertEqual(printed["ratchet.reworded"], {"key": "ratchet.reworded", "stands_in": "RULES.md",
                                                       "sha256": reference(new_by["ratchet.reworded"])})
        self.assertEqual(printed["ratchet.new-ratchet"]["status"], "built", "the status and where stay")
        self.assertNotIn("rule", printed["ratchet.new-ratchet"])
        self.assertEqual(printed["example.dropped"]["rule"], old_by["ratchet.dropped"]["rule"])
        steps, after = upgrade.plan(register, old, new)
        self.assertEqual(check_register.check(after, new)[0], [])
        # A rule whose rule and ratchet did not change keeps its sha256.
        self.assertIn("its sha256 still matches", upgrade.reference_text({"stands_in": "RULES.md", "sha256": reference(old_by["ratchet.keep"])},
                                                                         old_by["ratchet.keep"]))

    def test_a_register_with_rows_by_reference_and_no_register_md_is_not_told_to_print_one(self):
        # Review of step 9a: REGISTER.md is optional for a register with rows by reference. One that left it out is told
        # to check the register, not to print REGISTER.md. One that has it is told to print it again, as before.
        register, old, new = self.loaded("register.json"), self.loaded("old/ratchet.json"), self.loaded("new/ratchet.json")
        old_by = registry.rules_by_key(old)
        item = next(item for item in register["adopted"] if item["key"] == "ratchet.keep")
        for field in ("rule", "ratchet", "source"):
            del item[field]
        item.update(stands_in="RULES.md", sha256=check_register.reference_sha256(old_by["ratchet.keep"]))
        project = self.scratch()
        path = os.path.join(project, "register.json")
        for instructions in (None, "AGENTS.md"):
            with self.subTest(instructions=instructions):
                given = dict(register, instructions=instructions) if instructions else register
                out = io.StringIO()
                self.assertEqual(upgrade.report(path, given, old, new, out, "check_register.py"), 0, out.getvalue())
                output = out.getvalue()
                self.assertNotIn("--print-markdown", output)
                self.assertNotIn("print REGISTER.md", output)
                self.assertIn("REGISTER.md is not there, which a register with rows adopted by reference may leave out, so it "
                              "is not printed.", output)
                # An adoption report on 0.12: the check command named a REGISTER.md that is not there.
                self.assertIn("    python3 check_register.py -- %s\n" % shlex.quote(path), output)
                self.assertNotIn("--markdown", output)
                self.assertEqual("--print-instructions" in output, bool(instructions))
                if instructions:
                    self.assertIn("Then print %s again, put it in place, and check it:" % os.path.join(project, "AGENTS.md"), output)
                else:
                    self.assertIn("Then check it:", output)
        with open(os.path.join(project, "REGISTER.md"), "w", encoding="utf-8") as handle:
            handle.write(check_register.render(register))
        out = io.StringIO()
        self.assertEqual(upgrade.report(path, register, old, new, out, "check_register.py"), 0, out.getvalue())
        self.assertIn("Then print REGISTER.md again, put it in place, and check it:", out.getvalue())
        self.assertIn("--print-markdown", out.getvalue())
        self.assertIn("    python3 check_register.py --markdown REGISTER.md -- %s\n" % shlex.quote(path), out.getvalue())
        # A register with no row by reference is told to print it, there or not.
        out = io.StringIO()
        self.assertEqual(upgrade.report(os.path.join(self.scratch(), "register.json"), self.loaded("register.json"), old, new, out,
                                        "check_register.py"), 0, out.getvalue())
        self.assertIn("--print-markdown", out.getvalue())

    def test_each_printed_entry_is_the_rule_as_it_stands_in_the_newer_ratchet(self):
        code, output = self.upgrade("--new-rules", "full")
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

    def test_a_change_of_form_is_told_to_a_project_with_a_copy_that_reads_ratchet_json(self):
        # The fields at the top of ratchet.json, which Ratchet's checks read strictly: a reader of the older version
        # fails on a field it does not know, so a copy of it, or a check of the project's own, must be updated.
        old, new = self.loaded("old/ratchet.json"), self.loaded("new/ratchet.json")
        self.assertEqual(upgrade.form_changes(old, new), [])
        del old["experimental_cap"]
        self.assertEqual(upgrade.form_changes(old, new), ['"experimental_cap" is new'])
        self.assertEqual(upgrade.form_changes(new, old), ['"experimental_cap" is gone'])
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

class OneCommand(FixtureTest):
    """The upgrade in one command (D-2026-11-22-second-redraw, step 6): without --from, upgrade.py fetches the tags of the
    clone of Ratchet it stands in, compares the tag the register states with the latest release, or the one asked for,
    and says how far behind the register is. A git repo made in a scratch directory stands in for Ratchet on GitHub, with
    this repo's checks and the ratchet.json of upgrade/old/ at v9.8 and of upgrade/new/ at v9.9. v9.10 has the rules of
    9.9, so that the latest release is found by number and not by text, and an upgrade.py that prints MARKER first.
    Two tags are not releases: v9.11-rc1 and v09.10. No test reaches the network."""

    def setUp(self):
        old, new = self.fixture_bytes("upgrade/old/ratchet.json"), self.fixture_bytes("upgrade/new/ratchet.json")
        newest = new.replace(b'"version": "9.9"', b'"version": "9.10"', 1)
        self.assertNotEqual(newest, new)
        script = read("checks/upgrade.py").encode("utf-8")
        start = b"    out = out or sys.stdout\n"
        marked = script.replace(start, start + b"    print(%r, file=out)\n" % MARKER.encode("utf-8"), 1)
        self.assertNotEqual(marked, script)
        self.origin = os.path.join(self.scratch(), "ratchet")
        make_origin(self.origin, [("9.8", old), ("9.9", new), ("9.10", newest, {"checks/upgrade.py": marked})])
        # Tags that are not releases: a release candidate after the latest, and the latest with a leading zero.
        git(self.origin, "tag", "v9.11-rc1", "v9.10^{commit}")
        git(self.origin, "tag", "-a", "-m", "Not a release", "v09.10", "v9.10^{commit}")

    def project(self, register="register.json", at="v9.8", shallow=False, version=None):
        """A project with a register from upgrade/ and Ratchet cloned into .ratchet at a tag. Returns its path. With version,
        the register states that version in place of its own."""
        project = self.scratch()
        data = self.fixture_bytes("upgrade/" + register)
        if version is not None:
            data = re.sub(rb'"ratchet_version": "[0-9.]+"', b'"ratchet_version": "' + version.encode("ascii") + b'"', data, count=1)
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

    def test_new_rules_full_goes_on_to_the_upgrade_py_of_the_release(self):
        # Case 9: the one command moves .ratchet to v9.10 and runs the upgrade.py there, which gets --new-rules full.
        for args, full in (((), False), (("--new-rules", "full"), True)):
            with self.subTest(args=args):
                code, output = self.upgrade(self.project(), *args)
                self.assertEqual(code, 0, output)
                self.assertEqual(output.count(MARKER), 1, output)
                self.assertEqual('"key": "ratchet.added"' in output, full, output)
                self.assertEqual("\nOne:\n- ratchet.added\n- ratchet.added-text\n" in output, not full, output)

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
        self.assertIn("python3 .ratchet/checks/check_register.py --markdown REGISTER.md -- register.json", output)

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

    def by_reference(self, project, key="ratchet.keep"):
        """Make one row of the project's register a row by reference, with its marker in RULES.md, as adopt mode leaves
        it: no workflow of Ratchet's."""
        path = os.path.join(project, "register.json")
        register = registry.load_json(path)
        old_by = registry.rules_by_key(registry.parse_json(self.fixture_bytes("upgrade/old/ratchet.json")))
        item = next(item for item in register["adopted"] if item["key"] == key)
        for field in ("rule", "ratchet", "source"):
            del item[field]
        item.update(stands_in="RULES.md", sha256=check_register.reference_sha256(old_by[key]))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(register, indent=2) + "\n")
        with open(os.path.join(project, "RULES.md"), "w", encoding="utf-8") as handle:
            handle.write("# Rules\n\nKeep it.\n\n%s\n" % check_register.MARKER % key)

    def test_a_register_by_reference_with_no_workflow_is_told_how_to_run_the_new_commit(self):
        # An adoption report on 0.12: the one command ended with "Then pin .github/workflows/ratchet.yml", a file adopt
        # mode never writes, and the copy command and the line for the check script came only from init.py --check.
        project = self.project()
        self.by_reference(project)
        code, output = self.upgrade(project, "--to", "9.9")
        self.assertEqual(code, 0, output)
        commit = self.tag("v9.9")
        blob = git(self.origin, "rev-parse", "v9.9:checks/run_pinned.py")
        self.assertNotIn("Then pin", output)
        self.assertNotIn("--markdown", output)
        self.assertIn("The check runs from the pinned commit with .github/ratchet/run_pinned.py. To move it to the commit "
                      "of v9.9, %s, run these from the project's root." % commit, output)
        copy = run_pinned.copy_command(os.path.join(".ratchet", ".git", "objects"), commit, blob, run_pinned.COPY)
        local = run_pinned.local_line(commit, blob, run_pinned.COPY)
        step = run_pinned.run_command(commit, blob, run_pinned.COPY)
        for line in (copy, local, step):
            self.assertIn("\n    %s\n" % line, output + "\n")
        # The printed copy command copies the runner of v9.9, and the printed line runs it: on the register as it is,
        # still on 9.8, the check of 9.9 fails, and a script without set -e stops there.
        result = subprocess.run(["sh", "-c", copy], cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        with open(os.path.join(project, run_pinned.COPY), "rb") as handle:
            self.assertEqual(run_pinned.blob_hash(handle.read()), blob)
        result = subprocess.run(["sh", "-c", local + "\necho ALL GREEN\n"], cwd=project, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("run_pinned: Ratchet at %s" % commit, result.stdout)
        self.assertNotIn("ALL GREEN", result.stdout)

    def test_a_register_by_reference_under_another_name_is_checked_by_that_name(self):
        # Round 1 of #140: the printed commands named register.json, so they checked a neighbouring register.json and
        # passed while the register that was upgraded failed.
        project = self.project()
        self.by_reference(project)
        os.rename(os.path.join(project, "register.json"), os.path.join(project, "adoption.json"))
        before = snapshot(project, skip=(".ratchet",))
        code, output = in_project(project, ".ratchet/checks/upgrade.py", "adoption.json", "--to", "9.9")
        self.assertEqual(snapshot(project, skip=(".ratchet",)), before, "no file of the project changed")
        self.assertEqual(code, 0, output)
        commit = self.tag("v9.9")
        blob = git(self.origin, "rev-parse", "v9.9:checks/run_pinned.py")
        for line in (run_pinned.local_line(commit, blob, run_pinned.COPY, "adoption.json"),
                     run_pinned.run_command(commit, blob, run_pinned.COPY, "adoption.json")):
            self.assertIn("\n    %s\n" % line, output + "\n")
        self.assertNotIn("-- register.json", output)

    def test_the_one_command_refuses_a_register_in_another_folder_before_it_runs(self):
        # Rounds 2 to 4 of #140: for policy/adoption.json, policy/../register.json and a REGISTER.md beside such a
        # register, printed commands named another file than the one upgraded. The one command takes a register named
        # alone, and refuses any other before it moves .ratchet or prints a command.
        project = self.project()
        self.by_reference(project)
        os.makedirs(os.path.join(project, "policy"))
        os.rename(os.path.join(project, "register.json"), os.path.join(project, "policy", "adoption.json"))
        before = self.head(project)
        for name in ("policy/adoption.json", "policy/../policy/adoption.json"):
            with self.subTest(register=name):
                code, output = in_project(project, ".ratchet/checks/upgrade.py", name, "--to", "9.9")
                self.assertEqual(code, 2, output)
                self.assertIn("name the register alone, from the folder that holds it", output)
                self.assertNotIn("check_register.py", output)
                self.assertEqual(self.head(project), before, ".ratchet did not move")

    def test_a_register_md_beside_the_register_is_checked_by_the_printed_commands(self):
        # Round 4 of #140: with a REGISTER.md beside the register, the pinned commands checked the register alone, so a
        # stale REGISTER.md passed them.
        project = self.project()
        self.by_reference(project)
        with open(os.path.join(project, "REGISTER.md"), "w", encoding="utf-8") as handle:
            handle.write("# stale\n")
        code, output = self.upgrade(project, "--to", "9.9")
        self.assertEqual(code, 0, output)
        commit = self.tag("v9.9")
        blob = git(self.origin, "rev-parse", "v9.9:checks/run_pinned.py")
        for line in (run_pinned.local_line(commit, blob, run_pinned.COPY, "register.json", True),
                     run_pinned.run_command(commit, blob, run_pinned.COPY, "register.json", True)):
            self.assertIn("\n    %s\n" % line, output + "\n")
            self.assertTrue(line.replace(" ) || exit 1", "").endswith("-- register.json --markdown REGISTER.md"), line)

    def test_a_register_whose_last_row_by_reference_is_removed_has_register_md_checked(self):
        # Round 5 of #140: once the upgrade removes the last row by reference, REGISTER.md is required, as the report
        # says, but the pinned commands left it out.
        project = self.project()
        self.by_reference(project, "ratchet.dropped")
        code, output = self.upgrade(project, "--to", "9.9")
        self.assertEqual(code, 0, output)
        commit = self.tag("v9.9")
        blob = git(self.origin, "rev-parse", "v9.9:checks/run_pinned.py")
        self.assertIn("\n    %s\n" % run_pinned.run_command(commit, blob, run_pinned.COPY, "register.json", True),
                      output + "\n")

    def test_a_register_whose_name_starts_with_a_dash_is_not_read_as_an_option(self):
        step = run_pinned.run_command("0" * 40, "1" * 40, run_pinned.COPY, "-register.json")
        self.assertTrue(step.endswith(" -- ./-register.json"), step)
        self.assertTrue(run_pinned.run_command("0" * 40, "1" * 40, run_pinned.COPY).endswith(" -- register.json"))

    def test_a_register_by_reference_with_the_workflow_is_told_to_pin_it(self):
        project = self.project()
        self.by_reference(project)
        os.makedirs(os.path.join(project, ".github", "workflows"))
        with open(os.path.join(project, ".github", "workflows", "ratchet.yml"), "w", encoding="utf-8") as handle:
            handle.write("name: ratchet\n")
        code, output = self.upgrade(project, "--to", "9.9")
        self.assertEqual(code, 0, output)
        self.assertIn("Then pin .github/workflows/ratchet.yml to the commit of v9.9: %s." % self.tag("v9.9"), output)
        self.assertNotIn("run_pinned", output)

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
        listed = " Its release tags are v9.8, v9.9 and v9.10."
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

    def test_a_release_older_than_the_register_fails(self):
        project = self.project(register="register-current.json", at="v9.9")
        code, output = self.upgrade(project, "--to", "9.8")
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL: Ratchet 9.8, the release asked for, is older than 9.9, the version register.json states. An "
                      "upgrade does not go back.", output)
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
                      "origin has none either, so Ratchet 9.7 was never released. Its release tags are v9.8, v9.9 and v9.10.", output)
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
        # Gemini's review of 0425ffe: the command printed moved .ratchet to the tag of the version the register states,
        # whose upgrade.py may not know the forms of the release. It moves .ratchet to the release. The command printed
        # is run as printed, then the upgrade again, as typed the first time: it passes, with --to and without.
        for version, args, release in (("9.8", ("--no-fetch",), "v9.10"), ("9.8", ("--no-fetch", "--to", "9.9"), "v9.9"),
                                       ("9.8", (), "v9.10")):
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

    def test_a_removed_rule_adopted_in_part_is_told_that_its_entry_drops_the_where(self):
        # The review of 4b29449: the step said that the entry for "own" kept its status and its "where", while the entry,
        # rightly, holds Ratchet's whole text and no "where" that lists clauses not stated.
        old, new = self.loaded("old.json"), self.loaded("new.json")
        register = self.loaded("register.json")
        rule = registry.rules_by_key(old)["ratchet.dropped-checked"]
        row = {"key": rule["key"], "stands_in": "RULES.md", "sha256": check_register.reference_sha256(rule),
               "status": "text only for now", "where": "Not stated here: one; two."}
        register["adopted"] = [row if item["key"] == rule["key"] else item for item in register["adopted"]]
        steps, _ = upgrade.plan(register, old, new)
        step = next(step for step in steps if step["key"] == rule["key"])
        self.assertEqual(step["entry"]["status"], "text only for now")
        self.assertNotIn("where", step["entry"])
        self.assertNotIn('keeps its status and its "where"', step["text"])
        self.assertIn('An own rule may say where its check stands, so the entry keeps its status.', step["text"])
        self.assertIn('It was adopted in part, and an own rule stands in the register in full, so the entry has no "where": '
                      'the clauses it listed as not stated, one; two, stand in the rule of the entry like the rest of it.',
                      step["text"])
        # A row that is not in part still keeps both.
        steps, _ = upgrade.plan(self.loaded("register.json"), old, new)
        step = next(step for step in steps if step["key"] == rule["key"])
        self.assertIn('so the entry keeps its status and its "where".', step["text"])

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


# The files under upgrade/released/0.12/: the ratchet.json of the tag v0.12, the register.json that the init.py of v0.12
# wrote in adopt mode with --adopt ratchet.no-secrets --adopt ratchet.review-by-risk, two rows by reference, and the
# AGENTS.md that holds their marker lines. 0.12 is the version the one project that follows Ratchet is on, and the first
# that this upgrade reads (D-2026-11-23-support-from-0-12).
RELEASED = "upgrade/released/0.12/"


class FromReleased(FixtureTest):
    """A register by reference on 0.12, as adopt mode left it, upgraded to this version with the real released data."""

    def project(self, register="register.json"):
        """A project with the register and AGENTS.md of 0.12, and the ratchet.json of v0.12 as from.json. Returns its path."""
        project = self.scratch()
        for name, fixture in ((register, "register.json"), ("AGENTS.md", "AGENTS.md"), ("from.json", "ratchet.json")):
            with open(os.path.join(project, name), "wb") as handle:
                handle.write(self.fixture_bytes(RELEASED + fixture))
        return project

    def test_the_ratchet_json_of_0_12_and_of_this_version_are_read_as_older(self):
        # The reader of an older ratchet.json is as strict as this version's, but for the files it does not look for and
        # the budget. The ratchet.json of v0.12 and this one pass it. A form before 0.12 fails it.
        older = registry.parse_json(self.fixture_bytes(RELEASED + "ratchet.json"))
        self.assertEqual(older["version"], "0.12")
        self.assertEqual(registry.validate(older, None, older=True), [])
        self.assertEqual(upgrade.load_older("ratchet.json", self.fixture_bytes(RELEASED + "ratchet.json"))["version"], "0.12")
        current = registry.parse_json(read("ratchet.json").encode("utf-8"))
        self.assertEqual(registry.validate(current, None, older=True), [])
        for change, problem in ((lambda data: data.pop("experimental_cap"), "missing field 'experimental_cap'"),
                                (lambda data: data.pop("principles"), "missing field 'principles'"),
                                (lambda data: data.update(date="2026-01-01"), "unknown field 'date'"),
                                (lambda data: data.update(sources=[]), "unknown field 'sources'")):
            with self.subTest(problem=problem):
                data = json.loads(json.dumps(older))
                change(data)
                self.assertIn(problem, registry.validate(data, None, older=True))
        data = json.loads(json.dumps(older))
        rule = next(rule for rule in data["rules"] if rule["status"] == "experimental")
        del rule["since"]
        self.assertIn("%s: an experimental rule has since, the version it entered Ratchet" % rule["key"],
                      registry.validate(data, None, older=True))

    def test_a_register_by_reference_on_0_12_upgrades_to_this_version(self):
        # The register passes against 0.12. The offline mode prints a step for each row whose rule or ratchet changed, with
        # its new sha256, and none for a row that did not change. With the steps done, the command it prints passes.
        project = self.project()
        old = upgrade.load_older(os.path.join(project, "from.json"))
        new = registry.load(os.path.join(ROOT, "ratchet.json"))
        register = registry.load_json(os.path.join(project, "register.json"))
        self.assertEqual(check_register.check(register, old)[0], [])
        self.assertTrue(all(check_register.is_reference(item) for item in register["adopted"]))
        code, output = in_project(project, os.path.join(HERE, "upgrade.py"), "register.json", "--from", "from.json")
        self.assertEqual(code, 0, output)
        self.assertNotIn("Traceback", output)
        self.assertIn("register.json is on Ratchet 0.12.", output)
        self.assertIn('1. Set "ratchet_version" to "%s".' % new["version"], output)
        self.assertIn("passes check_register.py against Ratchet %s." % new["version"], output)
        self.assertIn("REGISTER.md is not there, which a register with rows adopted by reference may leave out", output)
        old_by, new_by = registry.rules_by_key(old), registry.rules_by_key(new)
        changed = [item["key"] for item in register["adopted"]
                   if check_register.reference_sha256(old_by[item["key"]]) != check_register.reference_sha256(new_by[item["key"]])]
        # ratchet.review-by-risk got a clause in 0.13, so at least one row has a step (D-2026-11-23-two-reviewers-for-check-code).
        self.assertIn("ratchet.review-by-risk", changed)
        for item in register["adopted"]:
            with self.subTest(key=item["key"]):
                if item["key"] in changed:
                    self.assertIn("%s: changed: " % item["key"], output)
                    self.assertIn("its sha256 no longer matches: the new sha256 is %s. Read the project's own wording in "
                                  "AGENTS.md again" % check_register.reference_sha256(new_by[item["key"]]), output)
                else:
                    self.assertNotIn("%s: changed" % item["key"], output)
        # The steps done in register.json, then the one command printed, run as printed.
        _, after = upgrade.plan(register, old, new)
        with open(os.path.join(project, "register.json"), "w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(after, indent=2, ensure_ascii=False) + "\n")
        printed = re.findall(r"(?m)^    ((?:rm -f |python3 )\S.*)$", output)
        self.assertEqual(printed, ["python3 %s -- register.json" % shlex.quote(os.path.join(HERE, "check_register.py"))])
        result = subprocess.run(["/bin/sh", "-c", printed[0].replace("python3 ", shlex.quote(sys.executable) + " -B ", 1)],
                                cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)


class UpgradingSteps(FixtureTest):
    """The steps in UPGRADING.md, run from the root of a project whose register is the one of 0.12 under RELEASED."""

    def test_every_command_in_the_steps_runs_from_the_root_of_a_project(self):
        # UPGRADING.md gives one command. A git repo made here stands in for Ratchet on GitHub, with the ratchet.json of
        # v0.12 at its tag, and this repo as it is at the tag of its own version. The project's .ratchet is a clone at
        # v0.12, and it has no .github/workflows/ratchet.yml, as adopt mode leaves it. The command is run as written, the
        # steps it prints are done in register.json, and then each command it printed is run as printed: the check, the
        # copy of run_pinned.py from the new commit, and the line for the local check script. Each must pass.
        new = registry.load(os.path.join(ROOT, "ratchet.json"))
        origin = os.path.join(self.scratch(), "ratchet")
        make_origin(origin, [("0.12", self.fixture_bytes(RELEASED + "ratchet.json")),
                             (new["version"], read("ratchet.json").encode("utf-8"))])
        project = self.scratch()
        for name in ("register.json", "AGENTS.md"):
            with open(os.path.join(project, name), "wb") as handle:
                handle.write(self.fixture_bytes(RELEASED + name))
        git(project, "clone", "-q", "--branch", "v0.12", origin, ".ratchet")
        text = read("UPGRADING.md")
        self.assertIsNone(re.search(r"git clone (-|http)", text), "the README clones Ratchet the first time, and the command fetches")
        commands = re.findall(r"(?m)^\s*((?:rm -f \S+ && )?python3 \.ratchet/\S.*)$", text)
        self.assertEqual(commands, ["python3 .ratchet/checks/upgrade.py register.json"])
        code, output = in_project(project, *shlex.split(commands[0])[1:])
        self.assertEqual(code, 0, output)
        self.assertIn("register.json states Ratchet 0.12. The latest release is %s" % new["version"], output)
        self.assertIn('Set "ratchet_version" to "%s".' % new["version"], output)
        commit = git(origin, "rev-parse", "v%s^{commit}" % new["version"])
        self.assertEqual(git(os.path.join(project, ".ratchet"), "rev-parse", "HEAD"), commit)
        self.assertNotIn("Then pin", output)
        # The steps that upgrade.py printed, done in register.json.
        path = os.path.join(project, "register.json")
        with open(path, "rb") as handle:
            register = registry.parse_json(handle.read())
        _, after = upgrade.plan(register, upgrade.load_older("ratchet.json", self.fixture_bytes(RELEASED + "ratchet.json")), new)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(after, indent=2, ensure_ascii=False) + "\n")
        printed = re.findall(r"(?m)^    ((?:rm -f |python3 )\S.*)$", output)
        self.assertEqual(printed, ["python3 .ratchet/checks/check_register.py -- register.json"], output)
        blob = git(origin, "rev-parse", "v%s:checks/run_pinned.py" % new["version"])
        copy = run_pinned.copy_command(os.path.join(".ratchet", ".git", "objects"), commit, blob, run_pinned.COPY)
        local = run_pinned.local_line(commit, blob, run_pinned.COPY)
        for line in (copy, local):
            self.assertIn("\n    %s\n" % line, output + "\n")
        for command in printed + [copy, local + "\necho ALL GREEN"]:
            with self.subTest(command=command[:40]):
                result = subprocess.run(["/bin/sh", "-c", command.replace("python3 ", shlex.quote(sys.executable) + " -B ")],
                                        cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("ALL GREEN", result.stdout)

    def with_instructions(self, register_name):
        """A project with a copy of this repo in .ratchet, the ratchet.json of v0.12 as .ratchet/from.json, the register of
        0.12 under register_name naming CLAUDE.md as its instruction file, whose block it generated, and AGENTS.md with the
        marker lines, since a row by reference names a file other than the instruction file. REGISTER.md is there.
        Returns (project, register)."""
        project = self.scratch()
        shutil.copytree(ROOT, os.path.join(project, ".ratchet"), ignore=shutil.ignore_patterns(".git", "__pycache__", "fixtures"))
        with open(os.path.join(project, ".ratchet", "from.json"), "wb") as handle:
            handle.write(self.fixture_bytes(RELEASED + "ratchet.json"))
        with open(os.path.join(project, "AGENTS.md"), "wb") as handle:
            handle.write(self.fixture_bytes(RELEASED + "AGENTS.md"))
        register = registry.parse_json(self.fixture_bytes(RELEASED + "register.json"))
        register["instructions"] = "CLAUDE.md"
        with open(os.path.join(project, register_name), "w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(register, indent=2, ensure_ascii=False) + "\n")
        with open(os.path.join(project, "CLAUDE.md"), "w", encoding="utf-8", newline="") as handle:
            handle.write(check_register.render_block(register) + "\n# The project's own text\n")
        with open(os.path.join(project, "REGISTER.md"), "w", encoding="utf-8", newline="") as handle:
            handle.write(check_register.render(register))
        return project, register

    def test_the_printed_commands_run_in_order_for_a_register_that_names_an_instruction_file(self):
        # Round 2 of #100: the commands that upgrade.py prints are run as printed, one after the other, on a register
        # that names an instruction file, whose block the older register generated. Each must pass.
        project, register = self.with_instructions("register.json")
        path = os.path.join(project, "register.json")
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
        with open(os.path.join(project, "CLAUDE.md"), encoding="utf-8", newline="") as handle:
            self.assertEqual(handle.read(), check_register.render_block(after) + "\n# The project's own text\n")

    def test_the_printed_commands_run_for_a_register_whose_path_starts_with_a_dash(self):
        # Review of step 9a: the commands put the options first and the register's path after --, so that a path that
        # starts with - is not read as an option by check_register.py.
        project, register = self.with_instructions("-register.json")
        path = os.path.join(project, "-register.json")
        result = subprocess.run([sys.executable, ".ratchet/checks/upgrade.py", "--from", ".ratchet/from.json", "--", "-register.json"],
                                cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        commands = re.findall(r"(?m)^    ((?:rm -f |python3 )\S.*)$", result.stdout)
        self.assertEqual(len(commands), 3, result.stdout)
        for command in commands:
            self.assertIn(" -- -register.json", command)
        new = registry.load(os.path.join(ROOT, "ratchet.json"))
        _, after = upgrade.plan(register, upgrade.load_older(os.path.join(project, ".ratchet", "from.json")), new)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(after, indent=2, ensure_ascii=False) + "\n")
        for command in commands:
            with self.subTest(command=command):
                ran = subprocess.run(["/bin/sh", "-c", command.replace("python3 ", shlex.quote(sys.executable) + " ")],
                                     cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                self.assertEqual(ran.returncode, 0, ran.stdout)
        with open(os.path.join(project, "REGISTER.md"), encoding="utf-8", newline="") as handle:
            self.assertEqual(handle.read(), check_register.render(after))



def release_data(version):
    """This repo's ratchet.json with another version, so that each release of an origin is a commit of its own."""
    data = read("ratchet.json").encode("utf-8")
    current = registry.parse_json(data)["version"]
    changed = data.replace(b'"version": "%s"' % current.encode("ascii"), b'"version": "%s"' % version.encode("ascii"), 1)
    assert changed != data or version == current
    return changed


class Behind(FixtureTest):
    """--behind (#180): one line that says how many releases, by number, come after the version the register states.
    An origin made here has the release tags v0.2, v0.9, v0.10 and v0.16, so that text order and number order differ."""

    LINE = "register.json states Ratchet 0.9. The latest release is 0.16, 2 releases after it: 0.10 and 0.16.\n"

    def setUp(self):
        self.origin = os.path.join(self.scratch(), "ratchet")
        make_origin(self.origin, [(version, release_data(version)) for version in ("0.2", "0.9", "0.10", "0.16")])

    def project(self, data, at="v0.16", depth=None):
        """A project with register.json holding data, and Ratchet cloned into .ratchet at a tag. Returns its path."""
        project = self.scratch()
        with open(os.path.join(project, "register.json"), "wb") as handle:
            handle.write(data)
        if depth:
            git(project, "clone", "-q", "--depth", str(depth), "--branch", at, "file://" + self.origin, ".ratchet")
        else:
            git(project, "clone", "-q", "--branch", at, self.origin, ".ratchet")
        return project

    def register(self, version="0.9"):
        """The register that the init.py of v0.9 wrote, stating version."""
        data = self.fixture_bytes("upgrade/released/0.9/register.json")
        return data.replace(b'"ratchet_version": "0.9"', b'"ratchet_version": "%s"' % version.encode("ascii"), 1)

    def behind(self, project, *args):
        """Run --behind in the project. Nothing in the project or in .ratchet, its files or its checkout, may change."""
        ratchet = os.path.join(project, ".ratchet")
        before, head = snapshot(project, skip=(".ratchet/.git",)), git(ratchet, "rev-parse", "HEAD")
        code, output = in_project(project, ".ratchet/checks/upgrade.py", "register.json", "--behind", *args)
        self.assertEqual(snapshot(project, skip=(".ratchet/.git",)), before, "no file changed")
        self.assertEqual(git(ratchet, "rev-parse", "HEAD"), head, ".ratchet did not move")
        self.assertNotIn("Traceback", output)
        return code, output

    def test_the_releases_after_the_register_are_counted_by_number(self):
        # Case 1. By text, v0.9 sorts after v0.16 and v0.10, and would be taken for the latest.
        code, output = self.behind(self.project(self.register()))
        self.assertEqual((code, output), (1, self.LINE))

    def test_a_register_on_the_latest_release_is_not_behind(self):
        # Case 2.
        code, output = self.behind(self.project(self.register("0.16")))
        self.assertEqual((code, output), (0, "register.json states Ratchet 0.16, the latest release. It is not behind.\n"))

    def test_a_version_it_cannot_read_or_place_cannot_tell(self):
        # Case 3: newer than every tag, no field, and a version of three numbers.
        missing = registry.parse_json(self.register())
        del missing["ratchet_version"]
        for data, said in ((self.register("0.17"), "states Ratchet 0.17, which is newer than the latest release in .ratchet, 0.16"),
                           (json.dumps(missing).encode("utf-8"), 'register.json has no field "ratchet_version"'),
                           (self.register("0.9.1"), 'the "ratchet_version" of register.json, "0.9.1", is not a version')):
            with self.subTest(said=said):
                code, output = self.behind(self.project(data))
                self.assertEqual(code, 2, output)
                self.assertIn(said, output)

    def test_a_register_of_an_older_form_is_read_for_its_version_alone(self):
        # Case 4: the register of 0.9, with a field at the top and one in a rule that the current reader refuses.
        register = registry.parse_json(self.register())
        register["waivers"] = []
        register["adopted"][0]["waived"] = "no"
        problems = "\n".join(check_register.check(dict(register, ratchet_version=registry.load(registry.SOURCE)["version"]),
                                                  registry.load(registry.SOURCE))[0])
        self.assertIn("unknown field 'waivers'", problems)
        code, output = self.behind(self.project(json.dumps(register, indent=2).encode("utf-8")))
        self.assertEqual((code, output), (1, self.LINE))

    def test_no_fetch_uses_only_the_tags_in_the_clone(self):
        # Case 6. A shallow clone at v0.9 holds that tag alone, so with --no-fetch the register is not behind. Without it,
        # the fetch finds the rest. With origin gone, --no-fetch still runs.
        project = self.project(self.register(), at="v0.9", depth=1)
        self.assertEqual(self.behind(project, "--no-fetch"),
                         (0, "register.json states Ratchet 0.9, the latest release. It is not behind.\n"))
        git(os.path.join(project, ".ratchet"), "remote", "set-url", "origin", os.path.join(self.scratch(), "gone"))
        self.assertEqual(self.behind(project, "--no-fetch")[0], 0)
        git(os.path.join(project, ".ratchet"), "remote", "set-url", "origin", "file://" + self.origin)
        self.assertEqual(self.behind(project), (1, self.LINE))

    def test_no_release_tag_a_failed_fetch_or_a_register_that_is_not_strict_json_cannot_tell(self):
        # Case 10, and a register of 0.2, which was Markdown.
        project = self.project(self.register())
        ratchet = os.path.join(project, ".ratchet")
        git(ratchet, "remote", "set-url", "origin", os.path.join(self.scratch(), "gone"))
        code, output = self.behind(project)
        self.assertEqual(code, 2, output)
        self.assertIn("could not be fetched from origin", output)
        self.assertIn("--no-fetch", output)
        for tag in git(ratchet, "tag").split():
            git(ratchet, "tag", "-d", tag)
        code, output = self.behind(project, "--no-fetch")
        self.assertEqual(code, 2, output)
        self.assertIn(".ratchet has no release tag to compare with.", output)
        for data in (b'{"ratchet_version": "0.9", "ratchet_version": "0.9"}', b"# Register\n\n| Key | Rule |\n",
                     b'{"ratchet_version": "0.2", "adopted": []}'):
            with self.subTest(data=data):
                code, output = self.behind(self.project(data))
                self.assertEqual(code, 2, output)
                self.assertIn("MIGRATING.md at the tag v0.12", output)

    def test_behind_takes_no_option_of_the_steps(self):
        project = self.project(self.register())
        # An explicit --new-rules line too, which is the default (round 1 of #183).
        for args in (("--to", "0.10"), ("--from", "old.json"), ("--new-rules", "full"), ("--new-rules", "line")):
            with self.subTest(args=args):
                code, output = self.behind(project, *args)
                self.assertEqual(code, 2, output)
                self.assertIn("--behind compares the register with the latest release", output)


class FirstLeg(FixtureTest):
    """A register before 0.12 is told the commands of the first leg (#181, part 1). An origin made here has the release
    tags of the leg, v0.11 and v0.13, the register's own and v0.16, the latest. That the chain these commands start runs
    through the real v0.11 and v0.13 is shown by a run in the pull request: the tag ruleset locks those tags, so only the
    printed text can break it (D-2026-11-26-checks-assessment)."""

    def first_leg(self, version, *args):
        """(exit code, output, project) of the one command on a register of version, in a clone at v0.16."""
        origin = os.path.join(self.scratch(), "ratchet")
        make_origin(origin, [(name, release_data(name)) for name in sorted(set([version, "0.11", "0.13", "0.16"]),
                                                                                key=upgrade.version_key)])
        project = self.scratch()
        with open(os.path.join(project, "register.json"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"project": "example", "ratchet_version": version, "adopted": [], "own": []}))
        git(project, "clone", "-q", "--branch", "v0.16", origin, ".ratchet")
        head = git(os.path.join(project, ".ratchet"), "rev-parse", "HEAD")
        code, output = in_project(project, ".ratchet/checks/upgrade.py", "register.json", *args)
        self.assertEqual(git(os.path.join(project, ".ratchet"), "rev-parse", "HEAD"), head, ".ratchet did not move")
        return code, output

    def test_a_register_before_0_12_is_told_the_four_commands_of_the_first_leg(self):
        # Case 8: exactly the four commands of the plan, in order. The only checkout is to v0.11, and no --to is before
        # 0.13.
        for version in ("0.3", "0.9", "0.11"):
            with self.subTest(version=version):
                code, output = self.first_leg(version, "--no-fetch")
                self.assertEqual(code, 2, output)
                self.assertEqual(output, (
                    "register.json states Ratchet %s. This upgrade.py reads the forms of 0.12 and later, so a register "
                    "before 0.12 takes two legs: to 0.13 with the upgrade.py of v0.11, then to 0.16. Run these from the "
                    "project's root, in order. After each upgrade.py, do the steps it prints in register.json and run the "
                    "commands it prints:\n"
                    "\n"
                    "    git -C .ratchet fetch --tags origin\n"
                    "    git -C .ratchet checkout --detach v0.11\n"
                    "    python3 .ratchet/checks/upgrade.py --to 0.13 --no-fetch -- register.json\n"
                    "    python3 .ratchet/checks/upgrade.py --to 0.16 --no-fetch -- register.json\n") % version)

    def test_a_target_before_the_first_leg_or_a_register_of_0_2_is_refused(self):
        code, output = self.first_leg("0.9", "--to", "0.11")
        self.assertEqual(code, 2, output)
        self.assertIn("A register before 0.12 upgrades to 0.13 first, and 0.11 is before that.", output)
        code, output = self.first_leg("0.2")
        self.assertEqual(code, 2, output)
        self.assertIn("MIGRATING.md at the tag v0.12", output)


class NewRulesByPart(FixtureTest):
    """New rules on one line each, grouped under the title of their part (#181, part 3)."""

    def report(self, *form):
        old, new = (registry.parse_json(self.fixture_bytes("upgrade/%s/ratchet.json" % name)) for name in ("old", "new"))
        # A second part, so that the grouping shows: ratchet.added-text moves there.
        new["parts"].append({"id": "two", "file": "RATCHET.md", "title": "Two"})
        next(rule for rule in new["rules"] if rule["key"] == "ratchet.added-text")["part"] = "two"
        out = io.StringIO()
        register = registry.parse_json(self.fixture_bytes("upgrade/register.json"))
        self.assertEqual(upgrade.report("register.json", register, old, new, out, "check_register.py", *form), 0, out.getvalue())
        return out.getvalue()

    def test_new_rules_are_one_line_each_under_their_part(self):
        # Case 9, the default.
        output = self.report()
        self.assertIn("\nNew rules, which the register may adopt, by part. To print the entry of each, run again with "
                      "--new-rules full:\n\nOne:\n- ratchet.added\n\nTwo:\n- ratchet.added-text\n\n", output)
        self.assertNotIn('"key": "ratchet.added', output)
        self.assertNotIn("ratchet.added: new.", output)

    def test_with_full_the_entries_are_as_before(self):
        # Case 9, --new-rules full.
        output = self.report("full")
        self.assertIn("\nNew rules, which the register may adopt:\n\n- ratchet.added: new.", output)
        self.assertEqual([entry["key"] for entry in entries(output)][-2:], ["ratchet.added", "ratchet.added-text"])
        self.assertNotIn("by part", output)


if __name__ == "__main__":
    unittest.main()
