"""Tests for checks/map.py, the check of a repo's own map of Ratchet's rules.

    python3 -m unittest discover -s checks -v

The fixtures are under checks/fixtures/map/: a checkout's ratchet.json with three rules, one with a source, under
checkout/, a repo with a valid map under repo/, and maps with one fault each under faults/. A fixture's name cannot start with a dot, so a part
that starts with dot- is renamed to start with . in the copy the test makes. Links, FIFOs and files that cannot be read
are made in scratch directories at test time, never committed. Each case of checks/README.md#mappy is a test here.
Standard library only.
"""

import ast
import contextlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import unittest
from unittest import mock

from suite_runner import FixtureTest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import map as map_check  # noqa: E402

# The modules map.py runs with: itself and the two it imports from beside it.
SCRIPTS = ("map.py", "inventory.py", "registry.py")

# Fixture under map/faults/ -> what map.py says of it, given as the repo's ratchet-map.json. Each exits 1.
FAULTS = {
    "key-missing": "rules has no entry for ratchet.gamma, a rule of Ratchet 0.9",
    "key-extra": 'rules has an entry for "ratchet.delta", which is not a rule of Ratchet 0.9',
    "key-misspelled": 'rules has an entry for "ratchet.gama", which is not a rule of Ratchet 0.9',
    "key-twice": "the field 'ratchet.gamma' appears twice in one object",
    "status-other": 'rules.ratchet.beta.status is "partly": it is "covered" or "gap"',
    "status-not-wanted": 'rules.ratchet.beta.status is "not-wanted": it is "covered" or "gap"',
    "covered-without-path": "rules.ratchet.alpha is covered and cites no path",
    "path-empty": 'rules.ratchet.alpha.by: "" is empty',
    "path-dot": 'rules.ratchet.alpha.by: "." has an empty part',
    "path-dot-dot": 'rules.ratchet.alpha.by: "../AGENTS.md" has an empty part',
    "path-empty-part": 'rules.ratchet.alpha.by: "docs//rules.md" has an empty part',
    "path-dot-part": 'rules.ratchet.alpha.by: "docs/./rules.md" has an empty part',
    "path-absolute": 'rules.ratchet.alpha.by: "/etc/passwd" starts with /',
    "path-trailing-slash": 'rules.ratchet.alpha.by: "docs/" ends with /',
    "path-backslash": "holds '\\\\', which a path here may not hold",
    "path-colon": "holds ':', which a path here may not hold",
    "path-hash": "holds '#', which a path here may not hold",
    "path-question": "holds '?', which a path here may not hold",
    "path-long": "is longer than 200 characters",
    "path-space": 'rules.ratchet.alpha.by: "docs/the rules.md" holds a character outside the list',
    "path-not-ascii": 'rules.ratchet.alpha.by: "docs/r\\u00e9gles.md" holds a character outside the list',
    "path-missing": 'rules.ratchet.alpha.by: "docs/gone.md" does not exist',
    "path-folder": 'rules.ratchet.alpha.by: "docs" is a folder, not a file',
    "path-twice": 'rules.ratchet.alpha.by: "AGENTS.md" stands twice',
    "path-number": "rules.ratchet.alpha.by: 7 must be text, found a number",
    "path-array": 'rules.ratchet.alpha.by: ["AGENTS.md"] must be text, found an array',
    "version-other": 'ratchet is "0.8", and the checkout map.py runs from is Ratchet 0.9',
    "version-form": 'ratchet is "0.9.1", not of the form MAJOR.MINOR',
    "version-number": "ratchet must be text of the form MAJOR.MINOR, found a number",
    "version-null": "ratchet must be text of the form MAJOR.MINOR, found null",
    "top-without-rules": "the map has no field 'rules'",
    "top-without-ratchet": "the map has no field 'ratchet'",
    "top-unknown-field": 'the map has the field "owner", which it does not have',
    "top-array": "the map must be an object with ratchet and rules, found an array",
    "rules-array": "rules must be an object with one entry for each rule, found an array",
    "rules-null": "rules must be an object with one entry for each rule, found null",
    "rule-without-note": "rules.ratchet.beta has no field 'note'",
    "rule-unknown-field": 'rules.ratchet.beta has the field "wanted", which a rule\'s entry does not have',
    "rule-text": "rules.ratchet.beta must be an object with status, by and note, found text",
    "rule-null": "rules.ratchet.beta must be an object with status, by and note, found null",
    "status-null": "rules.ratchet.beta.status must be text, found null",
    "status-boolean": "rules.ratchet.beta.status must be text, found true or false",
    "by-text": "rules.ratchet.beta.by must be an array of paths, found text",
    "by-object": "rules.ratchet.beta.by must be an array of paths, found an object",
    "note-number": "rules.ratchet.beta.note must be text, found a number",
    "note-object": "rules.ratchet.beta.note must be text, found an object",
    "note-empty": "rules.ratchet.beta.note is empty",
    "note-long": "rules.ratchet.beta.note is longer than 300 characters",
    "note-pipe": "rules.ratchet.beta.note must be one line, without |",
    "note-line-break": "rules.ratchet.beta.note must be one line, without |",
    "note-right-to-left": "rules.ratchet.beta.note holds U+202E",
    "not-utf8": "is not valid UTF-8, at byte",
    "byte-order-mark": "ratchet-map.json starts with a byte order mark",
    "not-json": "ratchet-map.json is not a valid data file",
    "nan": "NaN is not allowed",
    "infinity": "Infinity is not allowed",
    "nested-too-deeply": "ratchet-map.json is not a valid data file: it is nested too deeply",
}


def undot(top):
    """Rename every part under top whose name starts with dot- to one that starts with a dot, deepest first."""
    for folder, folders, files in os.walk(top, topdown=False):
        for name in folders + files:
            if name.startswith("dot-"):
                os.rename(os.path.join(folder, name), os.path.join(folder, "." + name[len("dot-"):]))


def snapshot(top):
    """Every entry under top, with its kind, size, time of change and bytes, to compare before and after a run."""
    seen = {}
    for folder, folders, files in os.walk(top):
        for name in folders + files:
            path = os.path.join(folder, name)
            status = os.lstat(path)
            data = None
            if stat.S_ISREG(status.st_mode):
                with open(path, "rb") as handle:
                    data = handle.read()
            seen[os.path.relpath(path, top)] = (status.st_mode, status.st_size, status.st_mtime_ns, data)
    return seen


def blocks(text):
    """The lines under each rule's key in the text report: {key: [lines]}."""
    found, key = {}, None
    for line in text.split("\n"):
        if re.match(r"^  ratchet\.[a-z-]+ \(", line):
            key = line.split()[0]
            found[key] = []
        elif line.startswith("    ") and key:
            found[key].append(line)
        else:
            key = None
    return found


def versions():
    """(the version of the first entry of CHANGELOG.md that is not released, the latest released version)."""
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as handle:
        headings = re.findall(r"(?m)^## ([0-9]+\.[0-9]+) \(([^)]*)\)$", handle.read())
    released = next(version for version, when in headings if re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\Z", when))
    unreleased = next((version for version, when in headings if when == "unreleased"), None)
    if unreleased is None:
        major, minor = released.split(".")
        unreleased = "%s.%d" % (major, int(minor) + 1)
    return unreleased, released


class Map(FixtureTest):
    def setUp(self):
        self.repo = self.fixture_directory("map/repo")
        undot(self.repo)
        self.checkout = self.make_checkout(self.fixture_bytes("map/checkout/ratchet.json"))

    def make_checkout(self, source):
        """A checkout of Ratchet in a scratch directory: the three scripts, and ratchet.json beside checks/ unless None."""
        top = self.scratch()
        os.makedirs(os.path.join(top, "checks"))
        for name in SCRIPTS:
            shutil.copyfile(os.path.join(HERE, name), os.path.join(top, "checks", name))
        if source is not None:
            with open(os.path.join(top, "ratchet.json"), "wb") as handle:
                handle.write(source)
        return top

    def run_map(self, *args, checkout=None, cwd=None, env=None, bytecode=False):
        script = os.path.join(checkout or self.checkout, "checks", "map.py")
        command = [sys.executable] + ([] if bytecode else ["-B"]) + [script] + list(args)
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                                cwd=cwd, env=env, timeout=120)
        return result.returncode, result.stdout, result.stderr

    def write_map(self, data, top=None):
        path = os.path.join(top or self.repo, map_check.MAP_NAME)
        if os.path.lexists(path):
            os.remove(path)
        with open(path, "wb") as handle:
            handle.write(data.encode("utf-8") if isinstance(data, str) else data)

    def problems(self, *args):
        code, out, err = self.run_map(self.repo, *args)
        self.assertEqual(code, 1, out + err)
        self.assertEqual(err, "")
        return out

    def valid_map(self):
        return json.loads(self.fixture_text("map/repo/ratchet-map.json"))

    # 1. A complete, valid map passes, against a checkout whose version is unreleased and one whose is released.

    def test_the_valid_map_passes(self):
        code, out, err = self.run_map(self.repo)
        self.assertEqual((code, err), (0, ""), out + err)
        self.assertIn("ratchet-map.json, for Ratchet 0.9: 3 rules, 1 covered, 2 gaps", out)

    def full_map_for(self, version):
        """A checkout whose ratchet.json is this repo's with the version given, and a repo with a map of all its rules."""
        with open(os.path.join(ROOT, "ratchet.json"), "rb") as handle:
            data = json.loads(handle.read().decode("utf-8"))
        data["version"] = version
        checkout = self.make_checkout((json.dumps(data, indent=2) + "\n").encode("utf-8"))
        repo = self.scratch()
        with open(os.path.join(repo, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("# Rules\n")
        rules = dict((rule["key"], {"status": "covered" if number % 2 else "gap", "by": ["AGENTS.md"] if number % 2 else [],
                                    "note": "Assessed for the test."}) for number, rule in enumerate(data["rules"]))
        self.write_map(json.dumps({"ratchet": version, "rules": rules}), top=repo)
        return checkout, repo, data

    def test_a_full_map_passes_against_an_unreleased_and_a_released_version(self):
        unreleased, released = versions()
        self.assertNotEqual(unreleased, released)
        for version in (unreleased, released):
            with self.subTest(version=version):
                checkout, repo, data = self.full_map_for(version)
                code, out, err = self.run_map(repo, "--json", checkout=checkout)
                self.assertEqual((code, err), (0, ""), out + err)
                facts = json.loads(out)
                self.assertEqual(facts["ratchet"], version)
                self.assertEqual([entry["key"] for entry in facts["rules"]], [rule["key"] for rule in data["rules"]])

    def test_this_checkout_s_own_map_py_reads_this_checkout_s_ratchet_json(self):
        with open(os.path.join(ROOT, "ratchet.json"), "rb") as handle:
            data = json.loads(handle.read().decode("utf-8"))
        repo = self.scratch()
        with open(os.path.join(repo, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("# Rules\n")
        rules = dict((rule["key"], {"status": "covered", "by": ["AGENTS.md"], "note": "Assessed."}) for rule in data["rules"])
        self.write_map(json.dumps({"ratchet": data["version"], "rules": rules}), top=repo)
        code, out, err = self.run_map(repo, checkout=ROOT)
        self.assertEqual((code, err), (0, ""), out + err)
        self.assertIn("for Ratchet %s: %d rules, %d covered, 0 gaps" % (data["version"], len(rules), len(rules)), out)

    # 2 to 5 and 7 to 10. Each fault fixture fails, with its problem named.

    def test_every_fault_fixture_fails_with_its_problem_named(self):
        for name, expected in sorted(FAULTS.items()):
            with self.subTest(fault=name):
                self.write_map(self.fixture_bytes("map/faults/%s.json" % name))
                for args in ([], ["--json"]):
                    out = self.problems(*args)
                    if args:
                        facts = json.loads(out)
                        self.assertFalse(facts["ok"])
                        self.assertTrue(any(expected in problem for problem in facts["problems"]), facts["problems"])
                    else:
                        self.assertIn(expected, out)
                        self.assertNotIn("Covered (", out)

    def test_every_fault_fixture_has_its_case(self):
        names = sorted(name[:-len(".json")] for name in os.listdir(os.path.join(HERE, "fixtures", "map", "faults")))
        self.assertEqual(names, sorted(FAULTS))

    def test_a_gap_with_paths_and_a_gap_with_none_pass(self):
        facts = json.loads(self.run_map(self.repo, "--json")[1])
        by = dict((entry["key"], (entry["status"], entry["by"])) for entry in facts["rules"])
        self.assertEqual(by["ratchet.beta"], ("gap", ["docs/rules.md"]))
        self.assertEqual(by["ratchet.gamma"], ("gap", []))

    def test_every_problem_is_named_not_only_the_first(self):
        value = self.valid_map()
        value["ratchet"] = "0.8"
        value["rules"].pop("ratchet.gamma")
        value["rules"]["ratchet.beta"]["status"] = "partly"
        self.write_map(json.dumps(value))
        out = self.problems()
        self.assertIn("3 problems", out)
        for expected in ('ratchet is "0.8"', "no entry for ratchet.gamma", 'status is "partly"'):
            self.assertIn(expected, out)

    def test_a_path_of_200_characters_passes_its_form(self):
        self.assertIsNone(map_check.path_problem("a" * 200))
        self.assertIn("longer than 200", map_check.path_problem("a" * 201))
        self.assertIsNone(map_check.path_problem(".github/workflows/c++-ci_1.yml"))

    def test_a_note_of_300_characters_passes(self):
        value = self.valid_map()
        value["rules"]["ratchet.beta"]["note"] = "x" * 300
        self.write_map(json.dumps(value))
        self.assertEqual(self.run_map(self.repo)[0], 0)

    # 6. A path's target: missing, a folder, a link, under a linked folder or a FIFO fails.

    def test_a_path_that_is_a_link_under_a_link_or_a_fifo_fails(self):
        os.symlink("AGENTS.md", os.path.join(self.repo, "LINK.md"))
        os.symlink("docs", os.path.join(self.repo, "linked"))
        outside = self.scratch()
        with open(os.path.join(outside, "x.md"), "w", encoding="utf-8") as handle:
            handle.write("x\n")
        os.symlink(outside, os.path.join(self.repo, "outside"))
        os.mkfifo(os.path.join(self.repo, "pipe"))
        cases = {
            "LINK.md": '"LINK.md" is a link, not followed',
            "linked/rules.md": '"linked/rules.md" is under linked, which is a link, not followed',
            "outside/x.md": '"outside/x.md" is under outside, which is a link, not followed',
            "pipe": '"pipe" is not a plain file: a FIFO',
        }
        for path, expected in sorted(cases.items()):
            with self.subTest(path=path):
                value = self.valid_map()
                value["rules"]["ratchet.alpha"]["by"] = [path]
                self.write_map(json.dumps(value))
                self.assertIn(expected, self.problems())

    def test_map_py_looks_under_the_root_only_through_inventory_s_guarded_functions(self):
        with open(os.path.join(HERE, "map.py"), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id in ("open", "exec", "eval", "compile", "__import__"):
                found.append(func.id)
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                name = "%s.%s" % (func.value.id, func.attr)
                if func.value.id == "os" and func.attr in ("open", "stat", "lstat", "listdir", "scandir", "walk", "readlink"):
                    found.append(name)
                if func.value.id == "inventory" and func.attr not in ("guarded_look", "guarded_read", "shown"):
                    found.append(name)
            # os.path.isfile is called once, on ratchet.json beside the script, which is Ratchet's own file and not
            # under the root. abspath, dirname and join only build paths.
            if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute) and func.value.attr == "path"
                    and isinstance(func.value.value, ast.Name) and func.value.value.id == "os"):
                if func.attr != "isfile" or [ast.dump(arg) for arg in node.args] != [ast.dump(ast.Name("SOURCE", ast.Load()))]:
                    found.append("os.path.%s" % func.attr)
        self.assertEqual(sorted(set(found)), ["os.path.abspath", "os.path.dirname", "os.path.join"])

    # 10. The map file itself: a link, a folder, a FIFO, unreadable, or not there.

    def test_the_map_file_as_a_link_a_folder_a_fifo_unreadable_or_missing_is_named(self):
        path = os.path.join(self.repo, map_check.MAP_NAME)
        real = os.path.join(self.repo, "real.json")
        os.rename(path, real)
        os.symlink("real.json", path)
        self.assertIn("ratchet-map.json is a link, not followed", self.problems())
        os.remove(path)
        os.mkdir(path)
        self.assertIn("ratchet-map.json is a folder, not a file", self.problems())
        os.rmdir(path)
        os.mkfifo(path)
        self.assertIn("ratchet-map.json is not a plain file: a FIFO", self.problems())
        os.remove(path)
        self.assertIn("there is no ratchet-map.json at the root", self.problems())
        if os.geteuid() != 0:
            os.rename(real, path)
            os.chmod(path, 0)
            self.addCleanup(os.chmod, path, 0o600)
            self.assertIn("ratchet-map.json: could not be read", self.problems())

    def test_a_map_over_a_million_bytes_is_named(self):
        self.write_map(b" " * 1000001)
        self.assertIn("ratchet-map.json: larger than 1000000 bytes, not read", self.problems())

    def test_no_ratchet_json_beside_it_or_one_that_is_not_valid_cannot_run(self):
        for source, expected in ((None, "there is no ratchet.json beside map.py"), (b"{", "not a valid data file"),
                                 (b'{"version": "0.9"}', "no version of the form MAJOR.MINOR and list of rules"),
                                 (b'{"version": "0.9", "rules": [{"key": "ratchet.a"}, {"key": "ratchet.a"}]}',
                                  "a rule without a key of its own")):
            with self.subTest(source=source):
                code, out, err = self.run_map(self.repo, checkout=self.make_checkout(source))
                self.assertEqual((code, out), (2, ""))
                self.assertIn("map: cannot run: ", err)
                self.assertIn(expected, err)

    # 11. ROOT: an invalid one cannot run; the root itself may be reached through a link, as inventory.py's may.

    def test_an_invalid_root_cannot_run(self):
        for root in (os.path.join(self.repo, "gone"), os.path.join(self.repo, "AGENTS.md")):
            with self.subTest(root=root):
                code, out, err = self.run_map(root)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("is not a folder", err)

    def test_the_root_may_be_reached_through_a_link_and_defaults_to_the_folder_it_runs_in(self):
        expected = self.run_map(self.repo)
        link = os.path.join(self.scratch(), "repo-link")
        os.symlink(self.repo, link)
        self.assertEqual(self.run_map(link), expected)
        self.assertEqual(self.run_map(cwd=self.repo), expected)
        self.assertEqual(expected[0], 0)

    # 12. Purity: nothing changes, no bytecode is written, no program runs.

    def test_a_run_changes_nothing_under_the_repo_or_the_checkout(self):
        before = (snapshot(self.repo), snapshot(self.checkout))
        for name in (None, "path-missing", "not-utf8"):
            if name:
                self.write_map(self.fixture_bytes("map/faults/%s.json" % name))
                before = (snapshot(self.repo), snapshot(self.checkout))
            for args in ([], ["--json"]):
                with self.subTest(fault=name, args=args):
                    self.run_map(self.repo, *args)
                    self.assertEqual((snapshot(self.repo), snapshot(self.checkout)), before)

    def test_no_bytecode_is_written_beside_the_checks(self):
        env = dict((key, value) for key, value in os.environ.items() if key not in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX"))
        code, out, err = self.run_map(self.repo, env=env, bytecode=True)
        self.assertEqual(code, 0, out + err)
        caches = [folder for folder, folders, _ in os.walk(self.checkout) if "__pycache__" in folders]
        self.assertEqual(caches, [])

    def test_no_program_runs(self):
        def refuse(*args, **kwargs):
            raise AssertionError("map.py ran a program")
        patches = [mock.patch.object(subprocess, name, refuse) for name in ("Popen", "run", "call", "check_call", "check_output")]
        patches += [mock.patch.object(os, name, refuse) for name in ("system", "popen", "fork", "execv", "execve", "execvp",
                                                                      "spawnv", "posix_spawn", "posix_spawnp")
                    if hasattr(os, name)]
        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            stack.enter_context(mock.patch.object(map_check, "SOURCE", os.path.join(self.checkout, "ratchet.json")))
            stack.enter_context(contextlib.redirect_stdout(out))
            code = map_check.main([self.repo, "--json"])
        self.assertEqual(code, 0, out.getvalue())
        self.assertTrue(json.loads(out.getvalue())["ok"])

    def test_map_py_imports_no_module_that_reaches_the_network_or_runs_a_program(self):
        with open(os.path.join(HERE, "map.py"), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertEqual(imported, {"sys", "os", "argparse", "json", "re", "inventory", "registry"})

    # 13. --json gives the same facts as the text.

    def test_the_text_is_made_from_the_same_facts_as_json(self):
        for name in (None, "key-missing", "path-missing"):
            with self.subTest(fault=name):
                if name:
                    self.write_map(self.fixture_bytes("map/faults/%s.json" % name))
                code, text, _ = self.run_map(self.repo)
                json_code, data, _ = self.run_map(self.repo, "--json")
                self.assertEqual(code, json_code)
                self.assertEqual(map_check.text_report(json.loads(data)), text)

    def test_the_text_lists_every_assessment_with_the_gaps_first_and_marked(self):
        code, out, _ = self.run_map(self.repo)
        self.assertEqual(code, 0)
        self.assertIn(map_check.PROPOSAL, out)
        self.assertLess(out.index("Gaps (2):"), out.index("Covered (1):"))
        self.assertEqual(out.count("<-- GAP"), 2)
        for key, entry in self.valid_map()["rules"].items():
            self.assertIn(entry["note"], out)
            for path in entry["by"]:
                self.assertIn(path, out)
            self.assertIn("%s (" % key, out)
        facts = json.loads(self.run_map(self.repo, "--json")[1])
        self.assertEqual(facts["counts"], {"covered": 1, "gap": 2})
        self.assertEqual(facts["proposal"], map_check.PROPOSAL)

    def test_the_notice_that_the_map_is_a_proposal_stands_in_both_formats_whether_it_passes_or_not(self):
        # Spelled out here, not read from map.PROPOSAL, so that a notice emptied or reworded in map.py fails (round 1
        # of the review of #167).
        notice = ("This map is the agent's proposal, for the owner to review. map.py checks its form and that each path "
                  "it cites is a plain file under the root, not whether a path covers a rule.")
        self.assertIn("the agent's proposal", notice)
        self.assertIn("map.py checks its form and that each path it cites is a plain file", notice)
        self.assertIn("not whether a path covers a rule", notice)
        for name, expected in ((None, 0), ("key-missing", 1)):
            if name:
                self.write_map(self.fixture_bytes("map/faults/%s.json" % name))
            with self.subTest(fault=name, format="text"):
                code, out, _ = self.run_map(self.repo)
                self.assertEqual(code, expected, out)
                self.assertIn("\n%s\n" % notice, out)
            with self.subTest(fault=name, format="json"):
                code, out, _ = self.run_map(self.repo, "--json")
                self.assertEqual(code, expected, out)
                self.assertEqual(json.loads(out)["proposal"], notice)

    # 14. A rule's source from the checkout's ratchet.json, printed as it stands, on gaps and covered rules alike.

    def test_the_source_stands_under_its_own_rule_only_whether_covered_or_a_gap(self):
        source = "example/skills `tdd`"
        for status in ("covered", "gap"):
            with self.subTest(status=status):
                value = self.valid_map()
                value["rules"]["ratchet.alpha"]["status"] = status
                self.write_map(json.dumps(value))
                code, out, err = self.run_map(self.repo)
                self.assertEqual((code, err), (0, ""), out + err)
                found = blocks(out)
                self.assertEqual(sorted(found), ["ratchet.alpha", "ratchet.beta", "ratchet.gamma"])
                self.assertIn("    source: %s" % source, found["ratchet.alpha"])
                for key in ("ratchet.beta", "ratchet.gamma"):
                    self.assertFalse([line for line in found[key] if line.startswith("    source:")], found[key])
                self.assertEqual(out.count("source:"), 1)
                facts = json.loads(self.run_map(self.repo, "--json")[1])
                by_key = dict((entry["key"], entry) for entry in facts["rules"])
                self.assertEqual(by_key["ratchet.alpha"]["status"], status)
                self.assertEqual(by_key["ratchet.alpha"]["source"], source)
                self.assertNotIn("source", by_key["ratchet.beta"])
                self.assertNotIn("source", by_key["ratchet.gamma"])

    def test_a_source_that_looks_like_markdown_is_printed_as_it_stands(self):
        source = "a/skills `one`; b `two-three`, which goes further; c/d (the e)"
        self.assertIsNone(map_check.registry.text_problem(source))
        data = json.loads(self.fixture_text("map/checkout/ratchet.json"))
        data["rules"][1]["source"] = source
        checkout = self.make_checkout(json.dumps(data).encode("utf-8"))
        code, out, err = self.run_map(self.repo, checkout=checkout)
        self.assertEqual((code, err), (0, ""), out + err)
        self.assertIn("    source: %s" % source, blocks(out)["ratchet.beta"])
        facts = json.loads(self.run_map(self.repo, "--json", checkout=checkout)[1])
        self.assertEqual([entry["source"] for entry in facts["rules"] if entry["key"] == "ratchet.beta"], [source])

    def test_a_map_that_fails_prints_its_problems_and_no_rule_or_source(self):
        self.write_map(self.fixture_bytes("map/faults/path-missing.json"))
        out = self.problems()
        self.assertNotIn("source", out)
        self.assertEqual(blocks(out), {})
        facts = json.loads(self.problems("--json"))
        self.assertEqual(sorted(facts), ["map", "ok", "problems", "proposal", "ratchet"])
        self.assertNotIn("source", json.dumps(facts))

    # 6. A path it cites is looked at for its kind and never read.

    def test_only_the_map_is_read_never_a_path_it_cites(self):
        value = self.valid_map()
        value["rules"]["ratchet.gamma"]["by"] = ["docs/rules.md", "AGENTS.md", ".github/workflows/ci.yml"]
        self.write_map(json.dumps(value))
        inventory = map_check.inventory
        reads, looks = [], []
        real_read, real_look = inventory.guarded_read, inventory.guarded_look

        def read(start, parts, prefix=""):
            reads.append(list(parts))
            return real_read(start, parts, prefix)

        def look(start, parts):
            looks.append(list(parts))
            return real_look(start, parts)

        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(inventory, "guarded_read", read))
            stack.enter_context(mock.patch.object(inventory, "guarded_look", look))
            stack.enter_context(mock.patch.object(map_check, "SOURCE", os.path.join(self.checkout, "ratchet.json")))
            stack.enter_context(contextlib.redirect_stdout(out))
            code = map_check.main([self.repo, "--json"])
        self.assertEqual(code, 0, out.getvalue())
        self.assertEqual(reads, [["ratchet-map.json"]])
        # Every path it cites was looked at, so the run did reach them.
        for path in (".github/workflows/ci.yml", "AGENTS.md", "docs/rules.md"):
            self.assertIn(path.split("/"), looks)

    # 15. --partial: a rule with no entry is listed as not yet mapped, not named as a problem; all else as without it.

    # Spelled out here, not read from map.py, so that a notice emptied or reworded there fails.
    PARTIAL_NOTICE = ("This run is partial: a rule missing from the map is listed as not yet mapped, not named as a "
                      "problem. Run map.py without --partial once every rule is mapped.")
    PARTIAL_HEAD = "ratchet-map.json, for Ratchet %s: partial, not yet a map of the whole Ratchet: "
    # The first line of a full pass, which a partial run never prints.
    FULL_PASS = re.compile(r"(?m)^ratchet-map\.json, for Ratchet [0-9]+\.[0-9]+: [0-9]+ rules, [0-9]+ covered, ")
    FULL_KEYS = ["counts", "map", "ok", "proposal", "ratchet", "rules"]

    def this_checkout(self):
        """A checkout whose ratchet.json is this repo's, a repo with AGENTS.md, and the keys of its rules in order."""
        with open(os.path.join(ROOT, "ratchet.json"), "rb") as handle:
            data = json.loads(handle.read().decode("utf-8"))
        repo = self.scratch()
        with open(os.path.join(repo, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("# Rules\n")
        return self.make_checkout(json.dumps(data).encode("utf-8")), repo, data["version"], [r["key"] for r in data["rules"]]

    def assert_partial_text(self, out, version="0.9"):
        """The first line of a partial run says it is partial, the notice follows, and no line of a full pass stands."""
        first, second = out.split("\n")[:2]
        self.assertTrue(first.startswith(self.PARTIAL_HEAD % version), first)
        self.assertEqual(second, self.PARTIAL_NOTICE)
        self.assertIsNone(self.FULL_PASS.search(out), out)

    def test_partial_one_rule_given_passes_and_lists_every_other_rule_as_not_yet_mapped(self):
        checkout, repo, version, keys = self.this_checkout()
        rest = keys[1:]
        self.write_map(json.dumps({"ratchet": version, "rules": {
            keys[0]: {"status": "covered", "by": ["AGENTS.md"], "note": "Assessed."}}}), top=repo)
        code, out, err = self.run_map(repo, "--partial", checkout=checkout)
        self.assertEqual((code, err), (0, ""), out + err)
        self.assert_partial_text(out, version)
        self.assertIn("1 rule given, 1 covered, 0 gaps; %d rules not yet mapped: %s\n" % (len(rest), ", ".join(rest)), out)
        self.assertEqual(len(rest), len(keys) - 1)
        facts = json.loads(self.run_map(repo, "--partial", "--json", checkout=checkout)[1])
        self.assertEqual(facts["unmapped"], rest)
        self.assertEqual(facts["counts"], {"covered": 1, "gap": 0})
        self.assertEqual([entry["key"] for entry in facts["rules"]], keys[:1])
        # Without --partial: exit 1, each missing rule named, and nothing of a partial run.
        code, out, err = self.run_map(repo, checkout=checkout)
        self.assertEqual((code, err), (1, ""), out + err)
        self.assertTrue(out.startswith("ratchet-map.json, for Ratchet %s: %d problems\n" % (version, len(rest))), out)
        for key in rest:
            self.assertIn("  rules has no entry for %s, a rule of Ratchet %s\n" % (key, version), out)
        self.assertNotIn("partial", out)
        self.assertNotIn("not yet mapped", out)

    def test_partial_one_rule_given_with_a_bad_path_fails(self):
        self.write_map(json.dumps({"ratchet": "0.9", "rules": {
            "ratchet.alpha": {"status": "covered", "by": ["docs/gone.md"], "note": "Assessed."}}}))
        code, out, err = self.run_map(self.repo, "--partial")
        self.assertEqual((code, err), (1, ""), out + err)
        self.assert_partial_text(out)
        self.assertIn("1 problem\n", out.split("\n")[0] + "\n")
        self.assertIn('rules.ratchet.alpha.by: "docs/gone.md" does not exist', out)
        self.assertNotIn("no entry", out)

    def test_partial_an_unknown_key_fails(self):
        value = self.valid_map()
        value["rules"] = {"ratchet.delta": value["rules"]["ratchet.alpha"]}
        self.write_map(json.dumps(value))
        code, out, err = self.run_map(self.repo, "--partial")
        self.assertEqual((code, err), (1, ""), out + err)
        self.assert_partial_text(out)
        self.assertIn('rules has an entry for "ratchet.delta", which is not a rule of Ratchet 0.9', out)

    def test_partial_with_every_rule_given_is_the_full_result_with_none_not_yet_mapped(self):
        full_code, full_out, _ = self.run_map(self.repo, "--json")
        code, out, err = self.run_map(self.repo, "--partial", "--json")
        self.assertEqual((code, err), (full_code, ""))
        self.assertEqual(code, 0)
        full, partial = json.loads(full_out), json.loads(out)
        self.assertEqual(partial.pop("unmapped"), [])
        self.assertEqual(partial.pop("partial"), self.PARTIAL_NOTICE)
        self.assertEqual(partial, full)
        code, text, _ = self.run_map(self.repo, "--partial")
        self.assertEqual(code, 0)
        self.assert_partial_text(text)
        self.assertEqual(text.split("\n")[0], self.PARTIAL_HEAD % "0.9" + "3 rules given, 1 covered, 2 gaps; 0 rules not yet mapped")
        # Under the two notices, the same rules as a full run: the gaps first, then the covered.
        self.assertEqual(text.split("\n")[2:], self.run_map(self.repo)[1].split("\n")[1:])

    def test_partial_an_empty_rules_passes_with_every_rule_not_yet_mapped(self):
        self.write_map(json.dumps({"ratchet": "0.9", "rules": {}}))
        code, out, err = self.run_map(self.repo, "--partial")
        self.assertEqual((code, err), (0, ""), out + err)
        self.assert_partial_text(out)
        self.assertIn("0 rules given, 0 covered, 0 gaps; 3 rules not yet mapped: ratchet.alpha, ratchet.beta, "
                      "ratchet.gamma\n", out)
        self.assertEqual(blocks(out), {})
        facts = json.loads(self.run_map(self.repo, "--partial", "--json")[1])
        self.assertEqual((facts["ok"], facts["unmapped"], facts["rules"]), (True, ["ratchet.alpha", "ratchet.beta", "ratchet.gamma"], []))
        self.assertEqual(self.run_map(self.repo)[0], 1)

    def test_json_holds_unmapped_and_partial_only_with_partial(self):
        self.write_map(self.fixture_bytes("map/faults/key-missing.json"))
        facts = json.loads(self.run_map(self.repo, "--partial", "--json")[1])
        self.assertEqual(sorted(facts), sorted(self.FULL_KEYS + ["partial", "unmapped"]))
        self.assertEqual(facts["unmapped"], ["ratchet.gamma"])
        self.write_map(self.fixture_bytes("map/repo/ratchet-map.json"))
        code, out, _ = self.run_map(self.repo, "--json")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(json.loads(out)), self.FULL_KEYS)
        self.assertNotIn("partial", out)
        self.assertNotIn("unmapped", out)

    def test_without_partial_the_text_is_as_before_byte_for_byte(self):
        # The text of the valid map and of key-missing as map.py printed it before --partial, spelled out in full.
        proposal = ("This map is the agent's proposal, for the owner to review. map.py checks its form and that each "
                    "path it cites is a plain file under the root, not whether a path covers a rule.")
        valid = "\n".join([
            "ratchet-map.json, for Ratchet 0.9: 3 rules, 1 covered, 2 gaps", proposal, "", "Gaps (2):",
            "  ratchet.beta (core): gap  <-- GAP", "    by: docs/rules.md",
            "    note: Covered in part: docs/rules.md names decisions, with no id and no check.",
            "  ratchet.gamma (experimental): gap  <-- GAP", "    by: (no path)", "    note: Nothing in the repo covers it.",
            "", "Covered (1):", "  ratchet.alpha (core): covered", "    by: .github/workflows/ci.yml, AGENTS.md",
            "    note: The job `test` runs on every pull request, and AGENTS.md says so.",
            "    source: example/skills `tdd`", ""])
        self.assertEqual(self.run_map(self.repo), (0, valid, ""))
        self.write_map(self.fixture_bytes("map/faults/key-missing.json"))
        missing = "\n".join(["ratchet-map.json, for Ratchet 0.9: 1 problem", proposal,
                             "  rules has no entry for ratchet.gamma, a rule of Ratchet 0.9", ""])
        self.assertEqual(self.run_map(self.repo), (1, missing, ""))

    def test_every_fault_fixture_fails_with_partial_as_without_it_but_for_a_missing_rule(self):
        passed = []
        for name, expected in sorted(FAULTS.items()):
            with self.subTest(fault=name):
                self.write_map(self.fixture_bytes("map/faults/%s.json" % name))
                full = json.loads(self.problems("--json"))
                code, out, err = self.run_map(self.repo, "--partial", "--json")
                self.assertEqual(err, "")
                partial = json.loads(out)
                self.assertEqual(partial["partial"], self.PARTIAL_NOTICE)
                left = [problem for problem in full["problems"] if not problem.startswith("rules has no entry for ")]
                if not left:
                    passed.append(name)
                    self.assertEqual((code, partial["ok"]), (0, True))
                    continue
                self.assertEqual(code, 1, out)
                self.assertEqual(partial["problems"], left)
                self.assertEqual(sorted(partial), ["map", "ok", "partial", "problems", "proposal", "ratchet"])
                code, text, _ = self.run_map(self.repo, "--partial")
                self.assertEqual(code, 1)
                self.assert_partial_text(text)
                self.assertIn(expected, text)
                self.assertNotIn("Covered (", text)
        self.assertEqual(passed, ["key-missing"])

    def test_the_partial_notice_stands_on_a_pass_a_failure_with_none_unmapped_and_when_it_cannot_run(self):
        cases = (("key-missing", 0), ("path-missing", 1), (None, 0))
        for name, expected in cases:
            self.write_map(self.fixture_bytes("map/faults/%s.json" % name if name else "map/repo/ratchet-map.json"))
            with self.subTest(fault=name, format="text"):
                code, out, _ = self.run_map(self.repo, "--partial")
                self.assertEqual(code, expected, out)
                self.assert_partial_text(out)
            with self.subTest(fault=name, format="json"):
                code, out, _ = self.run_map(self.repo, "--partial", "--json")
                self.assertEqual(code, expected, out)
                self.assertEqual(json.loads(out)["partial"], self.PARTIAL_NOTICE)
        for args in (["--partial"], ["--partial", "--json"]):
            with self.subTest(cannot_run=args):
                code, out, err = self.run_map(os.path.join(self.repo, "gone"), *args)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("map: cannot run: ", err)
                self.assertIn("\n%s\n" % self.PARTIAL_NOTICE, err)
                code, out, err = self.run_map(self.repo, *args, checkout=self.make_checkout(None))
                self.assertEqual((code, out), (2, ""))
                self.assertIn("\n%s\n" % self.PARTIAL_NOTICE, err)
        code, out, err = self.run_map(os.path.join(self.repo, "gone"))
        self.assertEqual((code, out), (2, ""))
        self.assertNotIn("partial", err)

    def test_partial_text_is_made_from_the_same_facts_as_json(self):
        for name in (None, "key-missing", "path-missing"):
            with self.subTest(fault=name):
                if name:
                    self.write_map(self.fixture_bytes("map/faults/%s.json" % name))
                code, text, _ = self.run_map(self.repo, "--partial")
                json_code, data, _ = self.run_map(self.repo, "--partial", "--json")
                self.assertEqual(code, json_code)
                self.assertEqual(map_check.text_report(json.loads(data)), text)


if __name__ == "__main__":
    unittest.main()
