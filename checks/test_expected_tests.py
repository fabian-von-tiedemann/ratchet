"""The check that every expected test ran and passed (ratchet.expected-tests-ran).

    python3 -m unittest discover -s checks -v

checks/expected_tests.py runs a suite in a child process and reads the records that
the child's runner writes. Most cases here run the check, in a process of its own as
CI runs it, on a small suite in a scratch directory. Its fixtures are a copy of
checks/fixtures/tests-ran/tree/, loaded through FixtureTest. The other cases give the
reader of the records a file that no runner wrote. Standard library only.

Every way found in review to drop a test without failing the run is a case here, and
each case is turned red by one mutation: see the table in checks/README.md.
"""

import json
import os
import subprocess
import sys
import textwrap
import unittest

import expected_tests
from suite_runner import FixtureTest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "expected_tests.py")
TREE = "tests-ran/tree"
# The sha256 of each file in the fake tree, taken with `shasum -a 256` and not computed the way the check does.
ONE = "bcdb09da2ba2b9d2dbd01063f38105f2f9ec27b16b9210286ef01dc242a24436"
THREE = "f6936912184481f5edd4c304ce27c5a1a827804fc7f329f43d273b8621870776"
OK = "expected_tests: every expected test ran and passed"
FAIL = "expected_tests: FAIL"
NOT_FINISHED = "the suite did not finish: there is no completion record"
ONE_MISSING = "one.json: no test that passed loaded it as it stands"
THREE_MISSING = "two/three.txt: no test that passed loaded it as it stands"

# The start of every module of the small suite. FIXTURES is the copy of the fake tree.
PRELUDE = '''\
import os
import signal
import sys
import unittest

from suite_runner import FixtureTest

FIXTURES = %r


class Base(FixtureTest):
    fixtures = FIXTURES

'''

# Two tests that load both fixtures and pass. Indented as the sources in the tests are, so that the two can be joined.
BOTH = textwrap.indent('''\
class Loads(Base):
    def test_one(self):
        self.assertTrue(self.fixture_bytes("one.json"))

    def test_three(self):
        self.assertEqual(self.fixture_text("two/three.txt"), "three\\n")
''', " " * 12)


class Runs(FixtureTest):
    """The check, run as CI runs it, on a small suite."""

    def setUp(self):
        self.tree = self.fixture_directory(TREE)
        self.suite = os.path.join(self.scratch(), "suite")
        os.mkdir(self.suite)

    def check(self, source, **modules):
        """Run the check on a suite of test_inner.py, which holds source, and the other modules given."""
        modules["test_inner"] = source
        for name, text in modules.items():
            with open(os.path.join(self.suite, name + ".py"), "w", encoding="utf-8") as handle:
                handle.write(PRELUDE % self.tree + textwrap.dedent(text))
        result = subprocess.run(
            [sys.executable, CHECK, "--start", self.suite, "--fixtures", self.tree],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=300,
        )
        return result.returncode, result.stdout

    def assert_fails(self, source, *problems, **modules):
        code, output = self.check(source, **modules)
        self.assertEqual(code, 1, output)
        self.assertIn(FAIL, output)
        self.assertNotIn(OK, output)
        listed = [line[2:] for line in output.splitlines() if line.startswith("- ")]
        for problem in problems:
            self.assertTrue(any(problem in line for line in listed), "%r is not listed in:\n%s" % (problem, output))
        return output

    def test_a_complete_set_passes(self):
        code, output = self.check(BOTH)
        self.assertEqual(code, 0, output)
        self.assertIn(OK + ". 2 tests, each id once, and 2 fixtures, each loaded as it stands by a test that passed.", output)
        self.assertIn("Ran 2 tests", output, "the child's own output is shown")

    def test_every_way_of_loading_counts(self):
        code, output = self.check('''\
            class Loads(Base):
                def test_a_file(self):
                    with open(self.fixture_file("one.json"), encoding="utf-8") as handle:
                        self.assertIn("one", handle.read())

                def test_a_directory(self):
                    self.assertTrue(os.path.isfile(os.path.join(self.fixture_directory("two"), "three.txt")))
            ''')
        self.assertEqual(code, 0, output)

    def test_a_fixture_that_no_test_loads_fails(self):
        output = self.assert_fails('''\
            class Loads(Base):
                def test_one(self):
                    self.fixture_bytes("one.json")
            ''', THREE_MISSING)
        self.assertNotIn(ONE_MISSING, output)

    def test_a_skip_in_set_up_class_fails(self):
        self.assert_fails(BOTH + '''
            class Skipped(Base):
                @classmethod
                def setUpClass(cls):
                    raise unittest.SkipTest("class preparation unavailable")

                def test_one(self):
                    self.fixture_bytes("one.json")
            ''', "setUpClass (test_inner.Skipped): skipped, outside any test")

    def test_a_skip_in_a_set_up_class_that_every_fixture_test_shares_fails(self):
        # The probe of review round 1.
        self.assert_fails('''\
            class Shared(Base):
                @classmethod
                def setUpClass(cls):
                    raise unittest.SkipTest("class preparation unavailable")


            class Loads(Shared):
                def test_one(self):
                    self.fixture_bytes("one.json")
                    self.fixture_bytes("two/three.txt")
            ''', "setUpClass (test_inner.Loads): skipped, outside any test", ONE_MISSING, THREE_MISSING)

    def test_sys_exit_in_set_up_class_fails(self):
        # The probe of review round 2: unittest does not catch SystemExit here, and the run exits 0 with no summary.
        output = self.assert_fails('''\
            class Loads(Base):
                @classmethod
                def setUpClass(cls):
                    sys.exit(0)

                def test_one(self):
                    self.fixture_bytes("one.json")
                    self.fixture_bytes("two/three.txt")
            ''', NOT_FINISHED, ONE_MISSING, THREE_MISSING)
        self.assertNotIn("the suite exited with status", output, "the child exited 0")

    def test_sys_exit_in_load_tests_fails(self):
        output = self.assert_fails(BOTH + '''

            def load_tests(loader, tests, pattern):
                sys.exit(0)
            ''', NOT_FINISHED, ONE_MISSING, THREE_MISSING)
        self.assertNotIn("the suite exited with status", output, "the child exited 0")

    def test_an_exit_from_inside_a_test_fails(self):
        self.assert_fails(BOTH + '''
            class Leaves(Base):
                def test_leave(self):
                    os._exit(0)
            ''', NOT_FINISHED)

    def test_a_duplicate_id_through_a_class_alias_fails(self):
        # The probe of review round 2: a later pass under the same id hid an earlier skip.
        self.assert_fails('''\
            class Loads(Base):
                ran = []

                def test_one(self):
                    self.ran.append(1)
                    if len(self.ran) == 1:
                        self.skipTest("skipped the first time")
                    self.fixture_bytes("one.json")
                    self.fixture_bytes("two/three.txt")


            Alias = Loads
            ''', "test_inner.Loads.test_one: ran 2 times under one id", "test_inner.Loads.test_one: skipped")

    def test_a_duplicate_id_that_passes_both_times_fails(self):
        self.assert_fails(BOTH + "\n\n            Alias = Loads\n", "test_inner.Loads.test_one: ran 2 times under one id",
                          "test_inner.Loads.test_three: ran 2 times under one id")

    def test_an_expected_failure_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                @unittest.expectedFailure
                def test_one(self):
                    self.fixture_bytes("one.json")
                    self.fixture_bytes("two/three.txt")
                    self.fail("as expected")
            ''', "test_inner.Loads.test_one: expected failure", ONE_MISSING, THREE_MISSING)

    def test_an_unexpected_success_fails(self):
        self.assert_fails(BOTH + '''
            class Lucky(Base):
                @unittest.expectedFailure
                def test_lucky(self):
                    self.fixture_bytes("one.json")
            ''', "test_inner.Lucky.test_lucky: unexpected success")

    def test_a_skip_decorator_on_a_class_fails(self):
        self.assert_fails('''\
            @unittest.skip("not now")
            class Loads(Base):
                def test_one(self):
                    self.fixture_bytes("one.json")
                    self.fixture_bytes("two/three.txt")
            ''', "test_inner.Loads.test_one: skipped", ONE_MISSING, THREE_MISSING)

    def test_a_skipped_test_fails(self):
        self.assert_fails(BOTH + '''
            class Later(Base):
                def test_later(self):
                    self.skipTest("later")
            ''', "test_inner.Later.test_later: skipped")

    def test_a_test_skipped_after_it_loaded_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                def test_one(self):
                    self.fixture_bytes("one.json")
                    self.fixture_bytes("two/three.txt")
                    self.skipTest("after the load")
            ''', "test_inner.Loads.test_one: skipped", ONE_MISSING, THREE_MISSING)

    def test_a_failing_test_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                def test_one(self):
                    self.fixture_bytes("one.json")
                    self.fixture_bytes("two/three.txt")
                    self.fail("no")
            ''', "test_inner.Loads.test_one: failed", ONE_MISSING, THREE_MISSING, "the suite exited with status 1")

    def test_an_erroring_test_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                def test_one(self):
                    self.fixture_bytes("one.json")
                    self.fixture_bytes("two/three.txt")
                    raise RuntimeError("no")
            ''', "test_inner.Loads.test_one: errored", ONE_MISSING, THREE_MISSING)

    def test_a_test_that_could_not_be_prepared_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                def setUp(self):
                    self.fixture_bytes("one.json")
                    raise RuntimeError("cannot prepare")

                def test_one(self):
                    self.fixture_bytes("two/three.txt")
            ''', "test_inner.Loads.test_one: errored", ONE_MISSING, THREE_MISSING)

    def test_a_failing_subtest_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                def test_both(self):
                    for name in ("one.json", "two/three.txt"):
                        with self.subTest(name=name):
                            self.fixture_bytes(name)
                            self.assertNotEqual(name, "one.json")
            ''', "test_inner.Loads.test_both: failed", ONE_MISSING, THREE_MISSING)

    def test_a_skipped_subtest_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                def test_both(self):
                    for name in ("one.json", "two/three.txt"):
                        with self.subTest(name=name):
                            self.fixture_bytes(name)
                            if name == "one.json":
                                self.skipTest("one is skipped")
            ''', "test_inner.Loads.test_both: skipped", ONE_MISSING, THREE_MISSING)

    def test_an_error_in_tear_down_module_after_the_tests_passed_fails(self):
        self.assert_fails(BOTH + '''

            def tearDownModule():
                raise RuntimeError("cannot clean up")
            ''', "tearDownModule (test_inner): errored, outside any test")

    def test_a_module_that_fails_to_import_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                def test_one(self):
                    self.fixture_bytes("one.json")
            ''', "unittest.loader._FailedTest.test_broken: errored", THREE_MISSING,
            test_broken='''\
            import a_module_that_does_not_exist


            class Three(Base):
                def test_three(self):
                    self.fixture_bytes("two/three.txt")
            ''')

    def test_a_killed_child_fails(self):
        output = self.assert_fails(BOTH + '''
            class Killed(Base):
                def test_killed(self):
                    os.kill(os.getpid(), signal.SIGKILL)
            ''', "the suite was stopped by signal %d" % 9, NOT_FINISHED)
        self.assertIn("test_inner.Killed.test_killed: started and has no outcome", output)

    def test_a_fixture_loaded_outside_a_test_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                @classmethod
                def setUpClass(cls):
                    cls("test_three").fixture_bytes("one.json")

                def test_three(self):
                    self.fixture_bytes("two/three.txt")
            ''', "one.json: loaded outside any test, so no outcome counts for it", ONE_MISSING)

    def test_a_fixture_changed_before_it_was_loaded_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                def test_both(self):
                    with open(os.path.join(FIXTURES, "one.json"), "a", encoding="utf-8") as handle:
                        handle.write(" ")
                    self.fixture_bytes("one.json")
                    self.fixture_bytes("two/three.txt")
            ''', "one.json: loaded by test_inner.Loads.test_both with bytes that are not the fixture's as it stands", ONE_MISSING)

    def test_a_fixture_that_is_only_named_fails(self):
        self.assert_fails('''\
            class Loads(Base):
                def test_both(self):
                    with open(os.path.join(FIXTURES, "one.json"), encoding="utf-8") as handle:
                        self.assertTrue(handle.read())
                    self.fixture_bytes("two/three.txt")
            ''', ONE_MISSING)

    def test_a_name_that_is_not_a_fixture_fails_the_test(self):
        for name in ("missing.json", "two", "../tree/one.json", "/etc/hosts", ".hidden"):
            with self.subTest(name=name):
                self.assert_fails(BOTH + '''
            class Wrong(Base):
                def test_wrong(self):
                    self.fixture_bytes(%r)
            ''' % name, "test_inner.Wrong.test_wrong: failed")

    def test_a_tree_that_cannot_be_read_fails(self):
        os.symlink(os.path.join(self.tree, "one.json"), os.path.join(self.tree, "link.json"))
        with open(os.path.join(self.tree, ".hidden"), "w", encoding="utf-8") as handle:
            handle.write("hidden\n")
        self.assert_fails(BOTH, "link.json: is a link, not a fixture", "'.hidden': is not a name a test can load")

    def test_an_empty_fixtures_directory_fails(self):
        self.tree = self.scratch()
        self.assert_fails("", "holds no fixtures. A run that expects nothing has not shown that everything ran")

    def test_a_missing_fixtures_directory_fails(self):
        self.tree = os.path.join(self.scratch(), "nothing")
        self.assert_fails("", "there is no directory of fixtures at")


class Records(FixtureTest):
    """The reader of the records, given a file that no runner wrote."""

    def setUp(self):
        self.path = os.path.join(self.scratch(), "records")
        self.found = {"one.json": ONE, "two/three.txt": THREE}

    def lines(self):
        """The records of a complete run in which test_both loads both fixtures and passes."""
        return [
            {"record": "start", "instance": 1, "test": "test_inner.Loads.test_both"},
            {"record": "loaded", "instance": 1, "fixture": "one.json", "sha256": ONE},
            {"record": "loaded", "instance": 1, "fixture": "two/three.txt", "sha256": THREE},
            {"record": "outcome", "instance": 1, "test": "test_inner.Loads.test_both", "outcome": "passed"},
            {"record": "complete", "tests_run": 1, "outcomes": 1, "loaded": 2},
        ]

    def problems(self, lines=None, raw=None, status=0):
        if raw is None:
            raw = "".join(json.dumps(line) + "\n" for line in (self.lines() if lines is None else lines)).encode("utf-8")
        with open(self.path, "wb") as handle:
            handle.write(raw)
        records, problems = expected_tests.read_records(self.path)
        return expected_tests.status_problems(status) + problems + expected_tests.compare(records, self.found)

    def assert_problem(self, problem, lines=None, raw=None, status=0):
        found = self.problems(lines, raw, status)
        self.assertTrue(any(problem in each for each in found), "%r not in %r" % (problem, found))

    def test_a_complete_run_passes(self):
        self.assertEqual(self.problems(), [])

    def test_a_record_of_a_form_the_check_does_not_know_fails(self):
        base = self.lines()
        cases = {
            "an unknown kind": ({"record": "waived"}, "an unknown kind of record 'waived'"),
            "no kind": ({"instance": 1}, "a record without its kind"),
            "an unknown field": (dict(base[3], waived="yes"), "unknown field 'waived'"),
            "a missing field": ({"record": "outcome", "instance": 1, "outcome": "passed"}, "missing field 'test'"),
            "an instance that is true": (dict(base[3], instance=True), "instance must be a whole number from 1"),
            "an instance that is text": (dict(base[3], instance="1"), "instance must be a whole number from 1"),
            "an instance of zero": (dict(base[0], instance=0), "instance must be a whole number from 1"),
            "an instance with a fraction": (dict(base[1], instance=1.0), "instance must be a whole number from 1"),
            "an unknown outcome": (dict(base[3], outcome="waived"), "outcome must be one of"),
            "a short sha256": (dict(base[1], sha256=ONE[:-1]), "sha256 must be 64 lowercase hex digits"),
            "a sha256 in capitals": (dict(base[1], sha256=ONE.upper()), "sha256 must be 64 lowercase hex digits"),
            "a fixture outside the tree": (dict(base[1], fixture="../one.json"), "fixture must be a fixture's name"),
            "a test without a name": (dict(base[0], test=""), "test must be a name of one line"),
            "a count that is negative": (dict(base[4], loaded=-1), "loaded must be a whole number from 0"),
            "a list": ([1, 2], "a record is one JSON object"),
        }
        for case, (line, problem) in cases.items():
            with self.subTest(case=case):
                self.assert_problem("line 3: not a record the check knows: " + problem, base[:2] + [line] + base[2:])

    def test_a_line_that_is_not_json_fails(self):
        raw = b'{"record": "start", "instance": 1,\n'
        self.assert_problem("line 1: not a record the check knows: not one JSON object", raw=raw)

    def test_a_field_twice_in_one_record_fails(self):
        raw = b'{"record": "start", "instance": 1, "test": "a.b", "test": "c.d"}\n'
        self.assert_problem("line 1: not a record the check knows: the field 'test' twice", raw=raw)

    def test_a_record_cut_off_at_its_end_fails(self):
        raw = "".join(json.dumps(line) + "\n" for line in self.lines()).encode("utf-8")[:-1]
        self.assert_problem("line 5: the record has no line break at its end, so it was cut off", raw=raw)

    def test_an_empty_line_fails(self):
        raw = "".join(json.dumps(line) + "\n" for line in self.lines()).encode("utf-8").replace(b"\n", b"\n\n", 1)
        self.assert_problem("line 2: not a record the check knows: not one JSON object", raw=raw)

    def test_records_that_are_not_utf8_fail(self):
        raw = "".join(json.dumps(line) + "\n" for line in self.lines()).encode("utf-8").replace(b"test_both", b"test_\xffboth", 1)
        self.assert_problem("the records are not valid UTF-8", raw=raw)

    def test_no_record_file_fails(self):
        records, problems = expected_tests.read_records(os.path.join(self.scratch(), "none"))
        self.assertEqual(records, [])
        self.assertEqual(problems, ["the suite wrote no records"])

    def test_a_run_without_its_completion_record_fails(self):
        self.assert_problem(NOT_FINISHED, self.lines()[:-1])

    def test_a_record_after_the_completion_record_fails(self):
        lines = self.lines()
        self.assert_problem("line 5: a record follows the completion record", lines[:3] + lines[4:] + lines[3:4])

    def test_two_completion_records_fail(self):
        self.assert_problem("the suite wrote 2 completion records", self.lines() + self.lines()[-1:])

    def test_counts_that_disagree_with_the_records_fail(self):
        for field, label in (("tests_run", "tests run"), ("outcomes", "outcomes"), ("loaded", "fixtures loaded")):
            with self.subTest(field=field):
                lines = self.lines()
                lines[-1][field] += 1
                self.assert_problem("the completion record counts %d %s, and the records hold %d" % (lines[-1][field], label, lines[-1][field] - 1), lines)

    def test_an_exit_status_other_than_zero_fails(self):
        self.assert_problem("the suite exited with status 1", status=1)
        self.assert_problem("the suite was stopped by signal 15", status=-15)

    def test_an_instance_started_twice_fails(self):
        lines = self.lines()
        self.assert_problem("line 2: instance 1 started twice", lines[:1] + lines[:1] + lines[1:])

    def test_an_outcome_of_another_test_than_its_instance_fails(self):
        lines = self.lines()
        lines[3]["test"] = "test_inner.Loads.test_other"
        self.assert_problem("line 4: the outcome of instance 1 names test_inner.Loads.test_other, and that instance is test_inner.Loads.test_both", lines)

    def test_a_passing_outcome_outside_any_test_fails(self):
        lines = self.lines()
        lines.insert(4, {"record": "outcome", "instance": 2, "test": "setUpClass (test_inner.Loads)", "outcome": "passed"})
        lines[-1]["outcomes"] = 2
        self.assert_problem("setUpClass (test_inner.Loads): passed, outside any test", lines)

    def test_a_load_by_an_instance_that_never_started_fails(self):
        lines = self.lines()
        lines[1]["instance"] = 7
        self.assert_problem("line 2: one.json was loaded by instance 7, which never started", lines)

    def test_a_passing_test_does_not_cover_for_one_that_failed_on_the_same_fixture(self):
        lines = self.lines()
        lines[3]["outcome"] = "failed"
        lines[4:4] = [
            {"record": "start", "instance": 2, "test": "test_inner.Loads.test_again"},
            {"record": "loaded", "instance": 2, "fixture": "one.json", "sha256": ONE},
            {"record": "outcome", "instance": 2, "test": "test_inner.Loads.test_again", "outcome": "passed"},
        ]
        lines[-1].update(tests_run=2, outcomes=2, loaded=3)
        found = self.problems(lines)
        self.assertIn("test_inner.Loads.test_both: failed", found)
        self.assertIn(THREE_MISSING, found)
        self.assertNotIn(ONE_MISSING, found)

    def test_a_pass_and_another_outcome_of_one_instance_is_not_a_pass(self):
        lines = self.lines()
        lines.insert(4, {"record": "outcome", "instance": 1, "test": "test_inner.Loads.test_both", "outcome": "errored"})
        lines[-1]["outcomes"] = 2
        found = self.problems(lines)
        self.assertIn("test_inner.Loads.test_both: errored", found)
        self.assertIn(ONE_MISSING, found)

    def test_a_fixture_that_does_not_exist_fails(self):
        lines = self.lines()
        lines[1]["fixture"] = "gone.json"
        self.assert_problem("gone.json: loaded by test_inner.Loads.test_both, and there is no such fixture", lines)


if __name__ == "__main__":
    unittest.main()
