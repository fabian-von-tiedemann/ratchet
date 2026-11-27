"""ratchet.decision-as-file: the form of the files in decisions/, and the status line that generate.py writes into each
decision that a later one replaces, amends or ends (D-2026-11-27-stale-text, point 2).

    python3 -m unittest discover -s checks -v

Each folder under checks/fixtures/decisions/ is a small decisions/ of its own. A case copies it into a scratch root and
reads it with decisions.expected, which generate.py calls, so a case fails when that gives a problem or a file whose
text is not what it generates. The cases of the grammar of a field are written in the test. The round trip runs
generate.py on a copy of this repo. Standard library only.
"""

import os
import shutil
import sys
import tempfile
import unittest

from suite_runner import FixtureTest
from test_checks import ROOT, RepoCopy, run

# The scripts of Ratchet's own maintenance stand in maintain/, beside checks/ (D-2026-11-27-maintain-apart).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maintain"))
import decisions  # noqa: E402

PASSING = ("old-without-fields", "new-with-fields", "same-day", "two-kinds")
# Each case that fails, with the words of its problem, or the decisions whose status is not what generate.py writes.
FAILING = {
    "new-without-fields": "a decision dated 2026-11-28 or later says what it replaces, amends and ends",
    "unknown-id": "Amends names D-2026-11-20-gone, which has no file in decisions/",
    "later-id": "Replaces names D-2026-11-28-a, which is dated after it",
    "own-id": "Ends names the decision itself",
    "one-id-two-fields": "names D-2026-11-27-old in more than one field",
    "cycle": "name each other in a cycle: D-2026-11-28-a -> D-2026-11-28-b -> D-2026-11-28-a",
    "status-missing": ["D-2026-11-28-b"],
    "status-stale": ["D-2026-11-28-b"],
    "status-edited": ["D-2026-11-28-b"],
    "status-unnamed": ["D-2026-11-28-a"],
    "status-misplaced": "a status block stands only just under the title, once",
    "title-id": "the title names D-2026-11-28-b, and the file is named for D-2026-11-28-a",
    "date": "Date is 2026-11-29, and the id's date is 2026-11-28",
    "no-question": "the lines ## Question and ## Answer stand once each, in that order",
    "no-answer": "the lines ## Question and ## Answer stand once each, in that order",
    "answer-first": "the lines ## Question and ## Answer stand once each, in that order",
    "field-twice": "the field Kind stands more than once",
    "field-unknown": "the field Supersedes is not one a decision has",
    "fields-in-part": "the header holds Date, Decided by, Kind, Replaces, Amends, Ends, in this order, or the first three alone",
}
GOOD = "# D-2026-11-28-a: a decision\n\n- Date: 2026-11-28\n- Decided by: the owner\n- Kind: decision (D)\n%s\n## Question\n\nq\n\n## Answer\n\na\n"
OLD = "# D-2026-11-20-old: a decision\n\n- Date: 2026-11-20\n- Decided by: the owner\n- Kind: decision (D)\n\n## Question\n\nq\n\n## Answer\n\na\n"


def stale(files):
    return sorted(os.path.basename(path)[:-3] for path, (current, expected) in files.items() if current != expected)


class Decisions(FixtureTest):
    def verdict(self, case):
        """(problems, the decisions whose text is not what generate.py writes) for one folder of fixtures."""
        root = self.scratch()
        os.rename(self.fixture_directory("decisions/" + case), os.path.join(root, "decisions"))
        files, problems = decisions.expected(root)
        return problems, stale(files)

    def folder(self, texts):
        """A scratch root whose decisions/ holds these texts, by id."""
        root = self.scratch()
        os.mkdir(os.path.join(root, "decisions"))
        for ident, text in texts.items():
            with open(os.path.join(root, "decisions", ident + ".md"), "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
        return root

    def test_every_folder_of_fixtures_is_a_case(self):
        self.assertEqual(sorted(PASSING + tuple(FAILING)), sorted(os.listdir(os.path.join(self.fixtures, "decisions"))))

    def test_the_passing_cases_pass(self):
        for case in PASSING:
            with self.subTest(case=case):
                self.assertEqual(self.verdict(case), ([], []))

    def test_each_failing_case_fails_for_its_reason(self):
        for case, reason in sorted(FAILING.items()):
            with self.subTest(case=case):
                problems, wrong = self.verdict(case)
                if isinstance(reason, list):
                    self.assertEqual((problems, wrong), ([], reason))
                else:
                    self.assertTrue(problems, case)
                    self.assertIn(reason, problems[0])

    def test_two_kinds_give_one_status_line_in_order(self):
        # Amended and then replaced, and a decision that Replaces one and Amends another, each in its own status line.
        root = self.scratch()
        os.rename(self.fixture_directory("decisions/two-kinds"), os.path.join(root, "decisions"))
        files, _ = decisions.expected(root)
        lines = dict((os.path.basename(path)[:-3], expected.split("\n")[3]) for path, (_, expected) in files.items()
                     if decisions.START in expected)
        self.assertEqual(lines, {
            "D-2026-11-28-c": "Status: amended by D-2026-11-28-a (its first point); replaced by D-2026-11-28-b",
            "D-2026-11-27-old": "Status: amended by D-2026-11-28-b (its order); amended by D-2026-11-28-d (its order)",
            "D-2026-11-20-older": "Status: replaced by D-2026-11-28-d",
        })

    def test_the_cut_over_is_the_28th(self):
        self.assertEqual(decisions.CUT_OVER.isoformat(), "2026-11-28")
        for date, passes in (("2026-11-27", True), ("2026-11-28", False), ("2027-01-01", False)):
            with self.subTest(date=date):
                ident = "D-%s-x" % date
                text = "# %s: x\n\n- Date: %s\n- Decided by: the owner\n- Kind: decision (D)\n\n## Question\n\n## Answer\n" % (ident, date)
                self.assertEqual(not decisions.expected(self.folder({ident: text}))[1], passes)

    def test_each_field_has_one_exact_form(self):
        # ratchet.one-exact-form: each form a field may take passes, and each other form named here fails.
        fields = "- Replaces: %s\n- Amends: %s\n- Ends: %s\n"
        good = {
            ("none", "none", "none"): [],
            ("D-2026-11-20-old", "none", "none"): [],
            ("none", "D-2026-11-20-old (one word)", "none"): [],
            ("none", "D-2026-11-20-old (%s)" % " ".join(["w"] * 15), "none"): [],
            ("none", "D-2026-11-20-old (point 2, and #78's order)", "none"): [],
            ("none", "none", "D-2026-11-20-old"): [],
            ("D-2026-11-20-old; D-2026-11-20-other", "none", "none"): [],
        }
        bad = {
            ("", "none", "none"): "names ''",
            ("None", "none", "none"): "names 'None'",
            ("D-2026-11-20-old, D-2026-11-20-other", "none", "none"): "which is not the id of a decision",
            ("D-2026-11-20-other; D-2026-11-20-old", "none", "none"): "names each decision once, in the order of their ids",
            ("D-2026-11-20-old; D-2026-11-20-old", "none", "none"): "names each decision once, in the order of their ids",
            ("D-2026-02-30-old", "none", "none"): "not the id of a decision with a date that exists",
            ("none", "D-2026-11-20-old", "none"): 'each item of Amends is "<id> (<what>)"',
            ("none", "D-2026-11-20-old ()", "none"): "one to 15 words",
            ("none", "D-2026-11-20-old (%s)" % " ".join(["w"] * 16), "none"): "one to 15 words",
            ("none", "D-2026-11-20-old (two  spaces)", "none"): "one to 15 words",
            ("none", "D-2026-11-20-old (a; b)", "none"): 'each item of Amends is "<id> (<what>)"',
            ("none", "D-2026-11-20-old (a <b>)", "none"): "one to 15 words",
            ("none", "D-2026-11-20-old (a | b)", "none"): "one to 15 words",
            ("none", "D-2026-11-20-old (café​)", "none"): "one to 15 words",
            ("none", "D-2026-11-20-old (x (y) z)", "none"): 'each item of Amends is "<id> (<what>)"',
            ("none", "none", "D-2026-11-20-old (why)"): "which is not the id of a decision",
        }
        texts = {"D-2026-11-20-old": OLD, "D-2026-11-20-other": OLD.replace("-old", "-other")}
        for value, words in list(good.items()) + list(bad.items()):
            with self.subTest(value=value):
                root = self.folder(dict(texts, **{"D-2026-11-28-a": GOOD % (fields % value)}))
                _, problems = decisions.expected(root)
                if value in good:
                    self.assertEqual(problems, [])
                else:
                    self.assertEqual(len(problems), 1, problems)
                    self.assertIn(words, problems[0])

    def test_the_top_of_the_file_has_one_form(self):
        fields = "- Replaces: none\n- Amends: none\n- Ends: none\n"
        cases = {
            "Kind": (GOOD % fields).replace("- Kind: decision (D)", "- Kind: proposal (P)"),
            "Decided by": (GOOD % fields).replace("- Decided by: the owner", "- Decided by: "),
            "an empty line follows the title": (GOOD % fields).replace("decision\n\n- Date", "decision\n- Date"),
            "each line of the header": (GOOD % fields).replace("- Kind: decision (D)\n", "- Kind: decision (D)\nKind\n"),
            'the first line is "# <id>: <title>"': (GOOD % fields).replace("# D-2026-11-28-a: ", "# D-2026-11-28-a "),
            "the status block is the line": (GOOD % fields).replace("decision\n\n", "decision\n\n<!-- generated:status -->\nStatus: x\n\n"),
        }
        for words, text in sorted(cases.items()):
            with self.subTest(words=words):
                problems = decisions.expected(self.folder({"D-2026-11-28-a": text}))[1]
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(words, problems[0])

    def test_any_line_between_the_markers_is_compared_with_the_status(self):
        # The line between the markers is generated text, so a line of another form is caught as not what is generated.
        fields = "- Replaces: none\n- Amends: none\n- Ends: D-2026-11-20-old\n"
        for line in ("Stat: ended by D-2026-11-28-a", "", "Status: ended by D-2026-11-28-a ", "<!-- x -->"):
            with self.subTest(line=line):
                old = OLD.replace("decision\n\n", "decision\n\n%s\n%s\n%s\n\n" % (decisions.START, line, decisions.END))
                files, problems = decisions.expected(self.folder({"D-2026-11-20-old": old, "D-2026-11-28-a": GOOD % fields}))
                self.assertEqual((problems, stale(files)), ([], ["D-2026-11-20-old"]))

    def test_an_entry_of_another_kind_fails(self):
        # Every entry that test_budget's test of the names fails on, and generate.py with it, beside one that passes.
        for name in ("notes.txt", "README", ".DS_Store", "D-2026-11-22-good.txt", "D-2026-11-22-good", "D-2026-02-30-bad.md",
                     "D-2026-11-22-.md", "d-2026-11-22-low.md", "x-D-2026-11-22-good.md", "D-2026-11-22-good.md.bak"):
            with self.subTest(name=name):
                root = self.folder({"D-2026-11-20-old": OLD})
                with open(os.path.join(root, "decisions", name), "w", encoding="utf-8") as handle:
                    handle.write("x\n")
                self.assertEqual([found for found, _ in decisions.entry_problems(os.path.join(root, "decisions"))], [name])
                self.assertEqual(len(decisions.expected(root)[1]), 1)
        root = self.folder({"D-2026-11-20-old": OLD})
        os.mkdir(os.path.join(root, "decisions", "D-2026-11-22-folder.md"))
        os.symlink("D-2026-11-20-old.md", os.path.join(root, "decisions", "D-2026-11-22-link.md"))
        self.assertEqual([found for found, _ in decisions.entry_problems(os.path.join(root, "decisions"))],
                         ["D-2026-11-22-folder.md", "D-2026-11-22-link.md"])
        self.assertEqual(len(decisions.expected(root)[1]), 2)
        self.assertEqual(decisions.expected(self.folder({"D-2026-11-20-old": OLD}))[1], [])

    def test_a_root_with_no_decisions_has_none(self):
        self.assertEqual(decisions.expected(self.scratch()), ({}, []))

    def test_a_wrong_name_writes_no_decision(self):
        # A field that names no decision leaves every file as it is, so generate.py writes no status from it.
        files, problems = decisions.expected(self.folder({
            "D-2026-11-20-old": OLD,
            "D-2026-11-28-a": GOOD % "- Replaces: D-2026-11-20-old\n- Amends: none\n- Ends: D-2026-11-20-gone\n"}))
        self.assertEqual((files, len(problems)), ({}, 1))


    def test_a_carriage_return_is_refused_and_no_decision_is_written(self):
        # Review of #202: a CRLF file read as LF and written back with its status changed the verbatim text's bytes.
        root = self.folder({"D-2026-11-20-old": OLD,
                            "D-2026-11-28-a": GOOD % "- Replaces: none\n- Amends: D-2026-11-20-old (a point)\n- Ends: none\n"})
        path = os.path.join(root, "decisions", "D-2026-11-20-old.md")
        with open(path, "rb") as handle:
            data = handle.read()
        for bad in (data.replace(b"\n", b"\r\n"), data.replace(b"## Answer", b"## Answer\r", 1)):
            with self.subTest(crlf=bad.count(b"\r\n")):
                with open(path, "wb") as handle:
                    handle.write(bad)
                files, problems = decisions.expected(root)
                self.assertEqual(files, {})
                self.assertEqual(problems, ["decisions/D-2026-11-20-old.md: holds a carriage return. A decision file has LF "
                                            "line endings only"])


    def test_a_decision_in_the_wrong_form_writes_no_decision(self):
        # Review of #202: a later decision with a broken field gave no status, and write mode then wrote the earlier file
        # without the status another later decision gives it. No decision file is written while any decision has a problem.
        root = self.folder({"D-2026-11-20-old": OLD,
                            "D-2026-11-28-a": GOOD % "- Replaces: none\n- Amends: D-2026-11-20-old (a point)\n- Ends: none\n",
                            "D-2026-11-28-b": GOOD.replace("D-2026-11-28-a", "D-2026-11-28-b")
                            % "- Replaces: none\n- Amends: D-2026-11-20-old (another point)\n- Ends: none\n- Other: x\n"})
        files, problems = decisions.expected(root)
        self.assertEqual(files, {})
        self.assertEqual(len(problems), 1)
        self.assertIn("D-2026-11-28-b", problems[0])


class ThisRepo(RepoCopy, unittest.TestCase):
    """The decisions of this repo, through generate.py itself."""

    def decision_texts(self, root):
        folder = os.path.join(root, "decisions")
        texts = {}
        for name in sorted(os.listdir(folder)):
            with open(os.path.join(folder, name), "rb") as handle:
                texts[name] = handle.read()
        return texts

    def test_the_repo_passes_and_names_what_the_backfill_found(self):
        files, problems = decisions.expected(ROOT)
        self.assertEqual((problems, stale(files)), ([], []))
        self.assertEqual(len(files), len(os.listdir(os.path.join(ROOT, "decisions"))))
        # A few of the relations the backfill wrote, each in the later decision, and the status it gives the earlier.
        heads = dict((os.path.basename(path)[:-3], text.split("\n## Question\n")[0]) for path, (text, _) in files.items())
        self.assertIn("- Ends: D-2026-11-22-standing-approval\n", heads["D-2026-11-27-stale-text"])
        self.assertIn("Status: amended by D-2026-11-22-owner-reads-outside-gates", heads["D-2026-11-22-standing-approval"])
        self.assertIn("ended by D-2026-11-27-stale-text\n", heads["D-2026-11-22-standing-approval"])
        self.assertIn("Status: amended by D-2026-11-27-no-sparse-fetch (point 2 is withdrawn)\n", heads["D-2026-11-27-maintain-apart"])
        self.assertIn("- Amends: D-2026-11-17-auto-merge (", heads["D-2026-11-17-agent-merges-after-approval"])
        self.assertNotIn("replaced by", heads["D-2026-11-17-auto-merge"])
        self.assertNotIn("replaced by", heads["D-2026-11-17-release-verbatim"])
        # Every relation in this repo is one of the 46 the inventory proved, all Amends but one Ends, none Replaces.
        count = dict((field, 0) for field in decisions.RELATIONS)
        for path, (text, _) in files.items():
            record, _ = decisions.parse(os.path.basename(path)[:-3], text)
            for field in decisions.RELATIONS:
                count[field] += len(record["relations"][field])
        self.assertEqual(count, {"Replaces": 0, "Amends": 45, "Ends": 1})

    def test_the_round_trip_changes_no_byte_from_the_question_on(self):
        decided = self.decision_texts(self.copy)
        # Take every status block out, and put one into a decision that no other one names.
        start, end = decisions.START.encode(), decisions.END.encode()
        for name, data in decided.items():
            if start in data:
                head, rest = data.split(start + b"\n", 1)
                data = head + rest.split(end + b"\n\n", 1)[1]
            else:
                title, rest = data.split(b"\n\n", 1)
                data = title + b"\n\n" + start + b"\nStatus: replaced by D-2026-11-16-scope\n" + end + b"\n\n" + rest
            with open(os.path.join(self.copy, "decisions", name), "wb") as handle:
                handle.write(data)
        broken = self.decision_texts(self.copy)
        # --check fails, names every decision, and writes nothing.
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        for name in decided:
            self.assertIn("decisions/%s: generated text is out of date or was edited by hand" % name, output)
        self.assertEqual(self.decision_texts(self.copy), broken)
        # generate.py writes each one back, byte for byte, and changes nothing from "## Question" on.
        code, output = run("generate.py", root=self.copy)
        self.assertEqual(code, 0, output)
        after = self.decision_texts(self.copy)
        self.assertEqual(after, decided)
        for name in decided:
            question = b"\n## Question\n"
            self.assertEqual(after[name][after[name].index(question):], broken[name][broken[name].index(question):])
        # And once more writes nothing.
        code, output = run("generate.py", root=self.copy)
        self.assertEqual(code, 0, output)
        self.assertNotIn("wrote ", output)
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)


if __name__ == "__main__":
    unittest.main()
