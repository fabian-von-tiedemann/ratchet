"""The report on the age of the form, checks/form_age.py (issue #70).

    python3 -m unittest discover -s checks -v

Each case makes a git repo of its own in a scratch directory, with its own tags, and runs the script there in a child
process, as test_released_text.py does. Standard library only.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

import form_age
import released_text
import test_released_text
from test_released_text import git, run

SCRIPT = "form_age.py"
TAGS = ("v0.16", "v0.17", "v0.18")
DAYS_30 = ("2026-11-26", "2026-12-10", "2026-12-26")
DAYS_29 = ("2026-11-26", "2026-12-10", "2026-12-25")
RULE = {"key": "ratchet.new", "part": "core", "principle": "principle.new", "status": "core", "enforcement": "enforced",
        "rule": "A new rule.", "ratchet": "Check: a test.", "source": "", "reference_check": "checks/new.py"}
RATCHET = {"version": None, "experimental_cap": 0, "start": ["ratchet.new"],
           "principles": [{"key": "principle.new", "title": "New", "text": "A new principle."}],
           "parts": [{"id": "core", "file": "RATCHET.md", "title": "The core"}], "rules": [RULE]}
REGISTER = {"project": "test", "ratchet_version": None, "instructions": "AGENTS.md",
            "adopted": [{"key": "ratchet.new", "rule": "A new rule.", "ratchet": "Check: a test.", "source": "",
                         "status": "built", "where": "In a test.",
                         "translation": {"language": "sv", "text": "En ny regel.", "sha256": "0" * 64}}],
            "own": [{"key": "repo.own", "rule": "An own rule.", "ratchet": "Text only, as a test.", "source": ""}]}
TEMPLATE = {"project": "", "ratchet_version": None,
            "adopted": [{"key": "ratchet.new", "rule": "A new rule.", "ratchet": "Check: a test.", "source": ""}], "own": []}
FORM = "\nChanges of form:\n\n- A field is new.\n"
NOTES = ("The count starts at v0.16, by D-2026-11-26-road-to-1-0", "not whether the record is complete")


def files_at(version, entries):
    """The files of one tag: ratchet.json and the two registers at version, and a changelog of entries, newest first."""
    files = {"ratchet.json": copy.deepcopy(RATCHET), "register.json": copy.deepcopy(REGISTER),
             "templates/register.json": copy.deepcopy(TEMPLATE)}
    for name in files:
        files[name]["version" if name == "ratchet.json" else "ratchet_version"] = version
    files["CHANGELOG.md"] = "# Changelog\n\n" + "".join(
        "## %s (%s)\n\nIn short: version %s.\n%s\n" % (v, date, v, FORM if form else "") for v, date, form in entries)
    return files


def put(root, name, value):
    """Write a file of the seeded repo: JSON from a dict, text or bytes as given, and None removes it."""
    path = os.path.join(root, *name.split("/"))
    if value is None:
        if os.path.exists(path):
            os.remove(path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, indent=2) + "\n"
    with open(path, "wb") as handle:
        handle.write(value if isinstance(value, bytes) else value.encode("utf-8"))


class Seeded(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, self.root)
        git(self.root, "init", "-q")

    def seed(self, tags=TAGS, dates=DAYS_30, change=None, form=()):
        """Commit and tag each tag in turn. change(tag, files) may change the files of a tag before it is committed.
        form names the versions whose changelog entry lists a change of form."""
        entries = []
        for tag, date in zip(tags, dates):
            version = tag[1:]
            entries.insert(0, (version, date, version in form))
            files = files_at(version, entries)
            if change:
                change(tag, files)
            for name, value in files.items():
                put(self.root, name, value)
            test_released_text.commit_and_tag(self.root, tag)

    def run_here(self, root=None):
        return run(SCRIPT, root or self.root, cwd=self.root)

    def assertReport(self, code, *says, root=None):
        found, out = self.run_here(root)
        self.assertEqual(found, code, out)
        for said in says:
            self.assertIn(said, out)
        self.assertNotIn("Traceback", out)
        return out


class Holds(Seeded):
    def test_same_form_30_days_holds(self):
        """Case 1."""
        self.seed()
        out = self.assertReport(0, "form_age: holds.", "the form is the same at v0.16, v0.17, v0.18",
                                "v0.16 (2026-11-26) to v0.18 (2026-12-26): 30 days", *NOTES)
        self.assertNotIn("short", out)

    def test_29_days_does_not_hold(self):
        """Case 2."""
        self.seed(dates=DAYS_29)
        self.assertReport(1, "form_age: does not hold.", "29 days, 1 short of 30", *NOTES)

    def test_form_line_in_oldest_entry_only_holds(self):
        """Case 9: the change that started the count."""
        self.seed(form=("0.16",))
        self.assertReport(0, "form_age: holds.")

    def test_writes_nothing_and_runs_only_read_only_git(self):
        """The run leaves the repo as it was, and runs git only as rev-parse, tag --list and show."""
        self.seed()
        self.assertReport(0)
        self.assertEqual(git(self.root, "status", "--porcelain", "--ignored"), "")
        commands, real = [], subprocess.run

        def recorded(args, **kwargs):
            commands.append(args[3:5])
            return real(args, **kwargs)

        with unittest.mock.patch.object(released_text.subprocess, "run", recorded), \
                unittest.mock.patch.dict(os.environ, test_released_text.git_environment(self.root)):
            self.assertEqual(form_age.judge(self.root)[0], 0)
        self.assertEqual(set(command[0] for command in commands), {"rev-parse", "config", "tag", "show"})
        self.assertIn(["tag", "--list"], commands)
        self.assertTrue(all(command == ["tag", "--list"] for command in commands if command[0] == "tag"))
        self.assertTrue(all(command == ["config", "--get-regexp"] for command in commands if command[0] == "config"))

    def test_writes_no_bytecode_beside_the_script(self):
        """The script, run from a copy of the checks with bytecode allowed, leaves that copy as it was."""
        self.seed()
        here = os.path.dirname(os.path.abspath(__file__))
        copied = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, copied)
        for name in os.listdir(here):
            if name.endswith(".py"):
                shutil.copy(os.path.join(here, name), copied)
        before = sorted(os.listdir(copied))
        environment = test_released_text.git_environment(self.root)
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        result = subprocess.run([sys.executable, os.path.join(copied, SCRIPT), self.root], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True, cwd=self.root, env=environment)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(sorted(os.listdir(copied)), before)


class TagsNotAllRead(Seeded):
    FOUR = ("v0.16", "v0.17", "v0.18", "v0.19")
    DATES = ("2026-11-26", "2026-12-10", "2026-12-20", "2026-12-30")

    def test_a_tag_git_cannot_read_cannot_tell(self):
        """A middle tag whose ref is broken: git leaves it out of the list and warns, and the two tags around it are
        never compared as neighbours."""
        self.seed(tags=self.FOUR, dates=self.DATES, form=("0.18",))
        self.assertReport(1, "form_age: does not hold.", "the entry of 0.18 lists a change of form")
        with open(os.path.join(self.root, ".git", "refs", "tags", "v0.18"), "w"):
            pass
        self.assertReport(2, "form_age: cannot tell.", "git warned while it listed the tags")

    def test_a_dated_release_with_no_tag_cannot_tell(self):
        """A tag not fetched: the newest changelog dates 0.18, and v0.18 is not here."""
        self.seed(tags=self.FOUR, dates=self.DATES, form=("0.18",))
        git(self.root, "tag", "-d", "v0.18")
        self.assertReport(2, "form_age: cannot tell.", "the release 0.18 is dated there and has no tag v0.18 here")

    def test_a_dated_release_with_no_tag_among_three_cannot_tell(self):
        """A tag not fetched when only three releases exist: two tags are left, and the answer is "cannot tell", not
        "does not hold" for too few tags."""
        self.seed()
        git(self.root, "tag", "-d", "v0.17")
        self.assertReport(2, "form_age: cannot tell.", "the release 0.17 is dated there and has no tag v0.17 here")

    def test_a_partial_clone_cannot_tell_and_fetches_nothing(self):
        """A partial clone could fetch each file the report asks for. It is refused before anything is read."""
        self.seed()
        git(self.root, "config", "uploadpack.allowFilter", "true")
        clone = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, clone)
        git(clone, "clone", "-q", "--no-checkout", "--filter=blob:none", "file://" + self.root, "partial")
        partial = os.path.join(clone, "partial")
        packs = os.path.join(partial, ".git", "objects", "pack")
        before = sorted(os.listdir(packs))
        found, out = run(SCRIPT, partial, cwd=partial)
        self.assertEqual(found, 2, out)
        self.assertIn("is a partial clone", out)
        self.assertEqual(sorted(os.listdir(packs)), before)


class FormDiffers(Seeded):
    def test_top_field_new_or_missing_at_middle_cannot_tell(self):
        """Case 3: upgrade.load_older refuses it, so it is never "holds"."""
        for name, change, said in (
                ("new", lambda files: files["ratchet.json"].update(date="2026-12-10"), "unknown field 'date'"),
                ("missing", lambda files: files["ratchet.json"].pop("start"), "missing field 'start'")):
            with self.subTest(name):
                self.setUp()
                self.seed(change=lambda tag, files: change(files) if tag == "v0.17" else None)
                self.assertReport(2, "form_age: cannot tell.", "ratchet.json at v0.17: " + said)

    def test_rule_field_gone_at_newest_does_not_hold(self):
        """Case 4."""
        self.seed(change=lambda tag, files: files["ratchet.json"]["rules"][0].pop("reference_check") if tag == "v0.18" else None)
        self.assertReport(1, "form_age: does not hold.", 'ratchet.json from v0.17 to v0.18: "reference_check" in a rule is gone')

    def test_new_field_in_adopted_row_of_template_does_not_hold(self):
        """Case 5: templates/register.json only."""
        self.seed(change=lambda tag, files: files["templates/register.json"]["adopted"][0].update(since="0.17")
                  if tag != "v0.16" else None)
        self.assertReport(1, "form_age: does not hold.",
                          'register.json and templates/register.json from v0.16 to v0.17: "adopted[].since" is new')

    def test_new_field_in_translation_does_not_hold(self):
        """Case 6."""
        self.seed(change=lambda tag, files: files["register.json"]["adopted"][0]["translation"].update(date="2026-12-26")
                  if tag == "v0.18" else None)
        self.assertReport(1, "form_age: does not hold.", '"adopted[].translation.date" is new')

    def test_new_field_in_own_row_of_register_does_not_hold(self):
        """Case 7: register.json only."""
        self.seed(change=lambda tag, files: files["register.json"]["own"][0].update(status="built") if tag == "v0.17" else None)
        self.assertReport(1, "form_age: does not hold.", 'from v0.16 to v0.17: "own[].status" is new',
                          'from v0.17 to v0.18: "own[].status" is gone')

    def test_form_line_in_newest_entry_does_not_hold(self):
        """Case 8: field sets equal."""
        self.seed(form=("0.18",))
        self.assertReport(1, "form_age: does not hold.",
                          'CHANGELOG.md at v0.18: the entry of 0.18 lists a change of form, under a line "Changes of form:"')

    def test_form_line_in_middle_entry_does_not_hold(self):
        """Case 8b: field sets equal."""
        self.seed(form=("0.17",))
        self.assertReport(1, "form_age: does not hold.", "CHANGELOG.md at v0.18: the entry of 0.17 lists a change of form")

    def test_form_line_must_stand_alone(self):
        """Only a line that is exactly the marker counts, as AGENTS.md writes it."""
        self.seed(change=lambda tag, files: files.update({"CHANGELOG.md": files["CHANGELOG.md"].replace(
            "In short: version 0.18.", "In short: version 0.18. No Changes of form: none.")}) if tag == "v0.18" else None)
        self.assertReport(0, "form_age: holds.")


class Tags(Seeded):
    def test_fewer_than_three_from_v0_16_does_not_hold(self):
        """Case 10: older tags present, and the answer is known."""
        self.seed(tags=("v0.14", "v0.15", "v0.16", "v0.17"), dates=("2026-10-01", "2026-10-15", "2026-11-26", "2026-12-26"))
        self.assertReport(1, "form_age: does not hold.", "2 tag(s) from v0.16 on (v0.16, v0.17), and 3 are needed", *NOTES)

    def test_no_tag_cannot_tell(self):
        """Case 10: no tag at all."""
        put(self.root, "CHANGELOG.md", "# Changelog\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "No tag")
        self.assertReport(2, "form_age: cannot tell.", "there are no tags")

    def test_tag_of_another_form_cannot_tell(self):
        """Case 11."""
        for tag in ("v0.19-rc1", "latest", "v0.016", "v1"):
            with self.subTest(tag):
                self.setUp()
                self.seed()
                git(self.root, "tag", tag)
                self.assertReport(2, "form_age: cannot tell.", "the tag %r is not of the form vMAJOR.MINOR" % tag)

    def test_three_highest_by_number(self):
        """Case 12: v0.100 is above v0.20 and v0.19, and v0.16 and v0.15, of other forms, are not among the three."""
        def change(tag, files):
            if tag == "v0.15":
                files["ratchet.json"]["date"] = "2026-10-01"
            if tag == "v0.16":
                files["register.json"]["own"][0]["status"] = "built"
        self.seed(tags=("v0.15", "v0.16", "v0.19", "v0.20", "v0.100"),
                  dates=("2026-10-01", "2026-11-26", "2026-12-01", "2026-12-15", "2026-12-31"), change=change)
        self.assertReport(0, "form_age: holds.", "the form is the same at v0.19, v0.20, v0.100",
                          "v0.19 (2026-12-01) to v0.100 (2026-12-31): 30 days")


class Unreadable(Seeded):
    def test_heading_missing_or_unreleased_cannot_tell(self):
        """Case 13."""
        for name, old, new, said in (
                ("missing", "## 0.17 (2026-12-10)\n\nIn short: version 0.17.\n\n", "", "no entry of 0.17"),
                ("unreleased", "## 0.18 (2026-12-26)", "## 0.18 (unreleased)", "'## 0.18 (unreleased)' has no date"),
                ("no such date", "## 0.17 (2026-12-10)", "## 0.17 (2026-02-30)", "'## 0.17 (2026-02-30)' has a date that does not exist"),
                ("twice", "## 0.17 (2026-12-10)\n", "## 0.17 (2026-12-10)\n\n## 0.17 (2026-12-10)\n",
                 "the entry of 0.17 stands 2 times")):
            with self.subTest(name):
                self.setUp()

                def change(tag, files):
                    if tag == "v0.18":
                        self.assertIn(old, files["CHANGELOG.md"])
                        files["CHANGELOG.md"] = files["CHANGELOG.md"].replace(old, new)
                self.seed(change=change)
                self.assertReport(2, "form_age: cannot tell.", "CHANGELOG.md at v0.18: " + said)

    def test_ratchet_json_unreadable_cannot_tell(self):
        """Case 14: a key twice, a byte order mark, a field load_older does not know, bytes that are not UTF-8."""
        for name, value, said in (
                ("twice", '{"version": "0.17", "version": "0.17"}', "appears twice"),
                ("bom", "\ufeff" + json.dumps(dict(RATCHET, version="0.17")), "BOM"),
                ("rule field", dict(RATCHET, version="0.17", rules=[dict(RULE, note="x")]), "unknown field note"),
                ("utf-8", b'{"version": "\xff"}', "not valid UTF-8"),
                ("missing", None, "ratchet.json at v0.17: the file is missing")):
            with self.subTest(name):
                self.setUp()

                def change(tag, files):
                    if tag == "v0.17":
                        files["ratchet.json"] = value
                self.seed(change=change)
                self.assertReport(2, "form_age: cannot tell.", "ratchet.json at v0.17", said)

    def test_register_unreadable_cannot_tell(self):
        """A register at a tag with a key twice, a byte order mark, NaN, or a list where the rows are objects."""
        for name, path, value, said in (
                ("twice", "register.json", '{"own": [], "own": []}', "appears twice"),
                ("bom", "templates/register.json", "\ufeff{}", "BOM"),
                ("nan", "register.json", '{"own": NaN}', "NaN is not allowed"),
                ("rows", "templates/register.json", '{"adopted": ["ratchet.new"]}', "adopted must be a list of objects")):
            with self.subTest(name):
                self.setUp()
                self.seed(change=lambda tag, files: files.update({path: value}) if tag == "v0.18" else None)
                self.assertReport(2, "form_age: cannot tell.", "%s at v0.18" % path, said)

    def test_root_not_top_of_checkout_cannot_tell(self):
        """Case 15: a folder inside a checkout, and one outside any."""
        self.seed()
        self.assertReport(2, "form_age: cannot tell.", "is not the top of a git checkout", root=os.path.join(self.root, "templates"))
        outside = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, outside)
        self.assertReport(2, "form_age: cannot tell.", "is not the top of a git checkout", root=outside)


if __name__ == "__main__":
    sys.exit(unittest.main())
