"""Tests for checks/map.py, the check of a repo's own map of Ratchet's rules.

    python3 -m unittest discover -s checks -v

The fixtures are under checks/fixtures/map/: a checkout's ratchet.json with three rules under checkout/, a repo with a
valid map under repo/, and maps with one fault each under faults/. A fixture's name cannot start with a dot, so a part
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


if __name__ == "__main__":
    unittest.main()
