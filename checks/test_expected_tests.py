"""The check that every expected test ran and passed (ratchet.expected-tests-ran).

    python3 -m unittest discover -s checks -v

The cases use a fake tree of fixtures, checks/fixtures/tests-ran/tree/, copied into a
scratch directory through this run's own ledger. Some give the check fake results. The
others run small suites with unittest's own runner, and some run `unittest discover` in a
process of its own, which is how CI runs the suite. Standard library only.

Every outcome that unittest can give a test has a case here, and each case is turned red
by the mutation that handles that outcome wrongly: see the table in checks/README.md.
"""

import io
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

import expected_tests
from expected_tests import FixtureTest

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = "tests-ran/tree"
# The sha256 of each file in the fake tree, taken with `shasum -a 256` and not computed the way the check does.
ONE = "bcdb09da2ba2b9d2dbd01063f38105f2f9ec27b16b9210286ef01dc242a24436"
THREE = "f6936912184481f5edd4c304ce27c5a1a827804fc7f329f43d273b8621870776"
SUMMARY = "Not every expected test ran and passed (ratchet.expected-tests-ran)"
COMPARISON = "test_0_expected_tests_ran"


def suite_for(root, **methods):
    """A suite of one test class whose fixtures are root, with the given test methods."""
    attributes = {"fixtures": root}
    attributes.update(methods)
    case = type("Inner", (FixtureTest,), attributes)
    return unittest.TestLoader().loadTestsFromTestCase(case)


def load(name):
    def test(self):
        self.assertTrue(self.fixture_bytes(name))
    return test


class FakeResults(FixtureTest):
    """The check given the fake tree and results that no test produced."""

    def setUp(self):
        self.root = self.fixture_directory(TREE)

    def problems(self, *records):
        return expected_tests.problems(self.root, list(records))

    def test_a_complete_set_passes(self):
        self.assertEqual(self.problems(("one.json", "fake.a", "passed", ONE), ("two/three.txt", "fake.b", "passed", THREE)), [])

    def test_a_missing_test_fails(self):
        self.assertEqual(self.problems(("one.json", "fake.a", "passed", ONE)), ["two/three.txt: no test loads this fixture"])

    def test_a_skipped_test_fails(self):
        self.assertEqual(
            self.problems(("one.json", "fake.a", "passed", ONE), ("two/three.txt", "fake.b", "skipped", THREE)),
            ["two/three.txt: loaded by fake.b, which did not pass: skipped"],
        )

    def test_an_erroring_test_fails(self):
        self.assertEqual(
            self.problems(("one.json", "fake.a", "errored", ONE), ("two/three.txt", "fake.b", "passed", THREE)),
            ["one.json: loaded by fake.a, which did not pass: errored"],
        )

    def test_a_test_that_could_not_be_prepared_fails(self):
        self.assertEqual(
            self.problems(("one.json", "fake.a", "could not be prepared", ONE), ("two/three.txt", "fake.b", "passed", THREE)),
            ["one.json: loaded by fake.a, which did not pass: could not be prepared"],
        )

    def test_a_passing_test_does_not_cover_for_one_that_failed_on_the_same_fixture(self):
        self.assertEqual(
            self.problems(("one.json", "fake.a", "passed", ONE), ("one.json", "fake.c", "failed", ONE), ("two/three.txt", "fake.b", "passed", THREE)),
            ["one.json: loaded by fake.c, which did not pass: failed"],
        )

    def test_a_fixture_that_is_named_and_never_loaded_fails(self):
        for digest in (None, THREE, ONE.upper(), ""):
            with self.subTest(digest=digest):
                self.assertEqual(
                    self.problems(("one.json", "fake.a", "passed", digest), ("two/three.txt", "fake.b", "passed", THREE)),
                    ["one.json: named by fake.a, which did not load it as it stands"],
                )

    def test_a_test_naming_a_fixture_that_does_not_exist_fails(self):
        for name in ("missing.json", "two", "two/", "./one.json", "../tree/one.json", "/one.json", ""):
            with self.subTest(name=name):
                self.assertEqual(
                    self.problems(("one.json", "fake.a", "passed", ONE), ("two/three.txt", "fake.b", "passed", THREE), (name, "fake.c", "passed", None)),
                    ["%s: named by fake.c, and there is no such fixture" % name],
                )

    def test_an_empty_fixtures_directory_fails(self):
        empty = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, empty)
        os.mkdir(os.path.join(empty, "only-a-directory"))
        self.assertEqual(
            expected_tests.problems(empty, []),
            ["%s holds no fixtures. A run that expects nothing has not shown that everything ran" % empty],
        )

    def test_a_missing_fixtures_directory_fails(self):
        missing = os.path.join(self.root, "does-not-exist")
        self.assertEqual(expected_tests.problems(missing, []), ["there is no directory of fixtures at %s" % missing])

    def test_a_file_in_the_tree_that_no_test_can_name_fails(self):
        with open(os.path.join(self.root, "two", ".hidden"), "w") as handle:
            handle.write("x")
        self.assertEqual(
            self.problems(("one.json", "fake.a", "passed", ONE), ("two/three.txt", "fake.b", "passed", THREE)),
            ["'two/.hidden': is not a name a test can load. A fixture is named by letters, digits, _ . and -, and does not start with a dot"],
        )

    def test_an_outcome_of_a_class_or_module_is_placed_and_one_the_check_does_not_know_fails(self):
        result = unittest.TestResult()
        holder = unittest.suite._ErrorHolder
        result.errors.append((holder("tearDownClass (fake.Inner)"), "boom"))
        result.skipped.append((holder("tearDownModule (fake)"), "not today"))
        result.errors.append((holder("something else (fake)"), "boom"))
        found, unknown = expected_tests.fixture_outcomes(result)
        self.assertEqual(found, [("fake.Inner", "tearDownClass (fake.Inner) errored"), ("fake", "tearDownModule (fake) skipped")])
        self.assertEqual(unknown, ["the run holds an outcome that the check cannot place: 'something else (fake)', errored"])
        records = [("one.json", "fake.Inner.test_a", "passed", ONE), ("two/three.txt", "fake.Other.test_b", "passed", THREE),
                   ("one.json", "fake.Innermost.test_c", "passed", ONE)]
        self.assertEqual(expected_tests.placed(records, found[:1]), [records[0][:2] + ("tearDownClass (fake.Inner) errored", ONE)] + records[1:])

    @unittest.skipUnless(hasattr(os, "symlink"), "the system has no links")
    def test_a_link_in_the_tree_fails(self):
        os.symlink(os.path.join(self.root, "one.json"), os.path.join(self.root, "link.json"))
        self.assertEqual(
            self.problems(("one.json", "fake.a", "passed", ONE), ("two/three.txt", "fake.b", "passed", THREE)),
            ["link.json: is a link, not a fixture"],
        )


class RealRuns(FixtureTest):
    """The check inside small suites run by unittest's own runner."""

    def setUp(self):
        self.root = self.fixture_directory(TREE)

    def run_suite(self, comparison=True, **methods):
        """Run one class of the given methods. With comparison, the run starts with the comparison, as discover runs it."""
        suite = suite_for(self.root, **methods)
        if comparison:
            suite = unittest.TestSuite([expected_tests.Comparison(self.root), suite])
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        return result, stream.getvalue()

    def assert_run_fails(self, problem, comparison=True, **methods):
        result, output = self.run_suite(comparison, **methods)
        self.assertFalse(result.wasSuccessful(), output)
        self.assertIn(problem, output)
        self.assertIn(SUMMARY, output)
        return output

    def test_a_complete_set_passes(self):
        result, output = self.run_suite(test_one=load("one.json"), test_three=load("two/three.txt"))
        self.assertTrue(result.wasSuccessful(), output)
        self.assertEqual(result.testsRun, 2, output)
        self.assertNotIn(SUMMARY, output)

    def test_every_way_of_loading_counts(self):
        def text(self):
            self.assertEqual(self.fixture_text("one.json"), '{"case": "one"}\n')

        def path(self):
            with open(self.fixture_file("two/three.txt"), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "three\n")

        result, output = self.run_suite(test_text=text, test_path=path)
        self.assertTrue(result.wasSuccessful(), output)

    def test_a_directory_loads_every_file_in_it(self):
        def directory(self):
            copy = self.fixture_directory("two")
            self.assertEqual(os.listdir(copy), ["three.txt"])

        output = self.assert_run_fails("one.json: no test loads this fixture", test_directory=directory)
        self.assertNotIn("two/three.txt:", output)

    def test_a_missing_test_fails(self):
        self.assert_run_fails("two/three.txt: no test loads this fixture", test_one=load("one.json"))

    def test_a_skipped_test_fails(self):
        self.assert_run_fails(
            "two/three.txt: no test loads this fixture",
            test_one=load("one.json"), test_three=unittest.skip("not today")(load("two/three.txt")),
        )

    def test_a_test_skipped_after_it_loaded_fails(self):
        def skipped(self):
            self.fixture_bytes("two/three.txt")
            self.skipTest("not today")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_three, which did not pass: skipped" % __name__,
                              test_one=load("one.json"), test_three=skipped)

    def test_an_erroring_test_fails(self):
        def erroring(self):
            self.fixture_bytes("two/three.txt")
            raise RuntimeError("broken")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_three, which did not pass: errored" % __name__,
                              test_one=load("one.json"), test_three=erroring)

    def test_a_test_that_could_not_be_prepared_fails(self):
        def set_up(self):
            self.fixture_bytes("two/three.txt")
            raise RuntimeError("cannot prepare")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_one, which did not pass: could not be prepared" % __name__,
                              setUp=set_up, test_one=load("one.json"))

    def test_a_fixture_that_is_only_named_fails(self):
        def named(self):
            # The name in the test, and the file opened by its path: neither is a load through FixtureTest.
            name = "two/three.txt"
            with open(os.path.join(self.fixtures, *name.split("/")), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "three\n")

        self.assert_run_fails("two/three.txt: no test loads this fixture", test_one=load("one.json"), test_three=named)

    def test_a_fixture_changed_after_it_was_loaded_fails(self):
        def changed(self):
            self.fixture_bytes("two/three.txt")
            with open(os.path.join(self.fixtures, "two", "three.txt"), "w") as handle:
                handle.write("changed\n")

        self.assert_run_fails("two/three.txt: named by %s.Inner.test_three, which did not load it as it stands" % __name__,
                              test_one=load("one.json"), test_three=changed)

    def test_a_test_naming_a_fixture_that_does_not_exist_fails_even_if_it_passes(self):
        def swallowed(self):
            with self.assertRaises(AssertionError):
                self.fixture_bytes("missing.json")

        self.assert_run_fails("missing.json: named by %s.Inner.test_missing, and there is no such fixture" % __name__,
                              test_one=load("one.json"), test_three=load("two/three.txt"), test_missing=swallowed)

    def test_a_name_outside_the_tree_is_not_read(self):
        def outside(self):
            with self.assertRaises(AssertionError):
                self.fixture_bytes("../tree/one.json")

        self.assert_run_fails("../tree/one.json: named by %s.Inner.test_outside, and there is no such fixture" % __name__,
                              test_one=load("one.json"), test_three=load("two/three.txt"), test_outside=outside)

    def test_a_failing_test_fails(self):
        def failing(self):
            self.fixture_bytes("two/three.txt")
            self.fail("broken")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_three, which did not pass: failed" % __name__,
                              test_one=load("one.json"), test_three=failing)

    def test_an_expected_failure_fails(self):
        # Without the check, this run is successful: an expected failure does not fail a run.
        @unittest.expectedFailure
        def expected(self):
            self.fixture_bytes("two/three.txt")
            self.fail("the check under test is broken")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_three, which did not pass: expected failure" % __name__,
                              test_one=load("one.json"), test_three=expected)

    def test_an_unexpected_success_fails_and_names_the_fixture(self):
        @unittest.expectedFailure
        def unexpected(self):
            self.fixture_bytes("two/three.txt")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_three, which did not pass: unexpected success" % __name__,
                              test_one=load("one.json"), test_three=unexpected)

    def test_a_failing_subtest_fails_every_fixture_of_its_test(self):
        def subtests(self):
            for name in ("one.json", "two/three.txt"):
                with self.subTest(name=name):
                    self.fixture_bytes(name)
                    self.assertNotEqual(name, "two/three.txt")

        output = self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_both, which did not pass: failed" % __name__,
                                       test_both=subtests)
        self.assertIn("one.json: loaded by %s.Inner.test_both, which did not pass: failed" % __name__, output)

    def test_an_erroring_subtest_fails(self):
        def subtests(self):
            for name in ("one.json", "two/three.txt"):
                with self.subTest(name=name):
                    self.fixture_bytes(name)
                    if name == "two/three.txt":
                        raise RuntimeError("broken")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_both, which did not pass: errored" % __name__,
                              test_both=subtests)

    def test_a_skipped_subtest_fails(self):
        def subtests(self):
            for name in ("one.json", "two/three.txt"):
                with self.subTest(name=name):
                    self.fixture_bytes(name)
                    if name == "two/three.txt":
                        self.skipTest("not today")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_both, which did not pass: skipped" % __name__,
                              test_both=subtests)

    def test_an_error_in_tear_down_fails(self):
        def tear_down(self):
            raise RuntimeError("cannot tear down")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_three, which did not pass: errored" % __name__,
                              tearDown=tear_down, test_one=load("one.json"), test_three=load("two/three.txt"))

    def test_an_error_in_a_cleanup_fails(self):
        def cleaned(self):
            self.addCleanup(self.fail, "cannot clean up")
            self.fixture_bytes("two/three.txt")

        self.assert_run_fails("two/three.txt: loaded by %s.Inner.test_three, which did not pass: " % __name__,
                              test_one=load("one.json"), test_three=cleaned)

    def test_a_class_set_up_that_skips_fails(self):
        def set_up_class(cls):
            raise unittest.SkipTest("class preparation unavailable")

        output = self.assert_run_fails("one.json: no test loads this fixture",
                                       setUpClass=classmethod(set_up_class), test_one=load("one.json"), test_three=load("two/three.txt"))
        self.assertIn("two/three.txt: no test loads this fixture", output)

    def test_a_class_set_up_that_errors_fails(self):
        def set_up_class(cls):
            raise RuntimeError("cannot prepare the class")

        self.assert_run_fails("two/three.txt: no test loads this fixture",
                              setUpClass=classmethod(set_up_class), test_one=load("one.json"), test_three=load("two/three.txt"))

    def test_a_skipped_class_fails(self):
        result, output = self.run_suite(
            __unittest_skip__=True, __unittest_skip_why__="not today", test_one=load("one.json"), test_three=load("two/three.txt"))
        self.assertFalse(result.wasSuccessful(), output)
        self.assertIn("one.json: no test loads this fixture", output)
        self.assertIn("two/three.txt: no test loads this fixture", output)

    def test_an_error_in_tear_down_class_fails_the_tests_of_the_class(self):
        def tear_down_class(cls):
            raise RuntimeError("cannot tear down the class")

        output = self.assert_run_fails(
            "one.json: loaded by %s.Inner.test_one, which did not pass: tearDownClass (%s.Inner) errored" % (__name__, __name__),
            tearDownClass=classmethod(tear_down_class), test_one=load("one.json"), test_three=load("two/three.txt"))
        self.assertIn("two/three.txt: loaded by %s.Inner.test_three, which did not pass: tearDownClass" % __name__, output)

    def test_a_skip_in_tear_down_class_fails_the_tests_of_the_class(self):
        # Without the check, this run is successful: a skip does not fail a run.
        def tear_down_class(cls):
            raise unittest.SkipTest("not today")

        self.assert_run_fails(
            "one.json: loaded by %s.Inner.test_one, which did not pass: tearDownClass (%s.Inner) skipped" % (__name__, __name__),
            tearDownClass=classmethod(tear_down_class), test_one=load("one.json"), test_three=load("two/three.txt"))

    def test_without_the_comparison_a_fixture_test_still_installs_it(self):
        # A run of one module, without discover, holds no comparison of its own.
        self.assert_run_fails("two/three.txt: no test loads this fixture", comparison=False, test_one=load("one.json"))

    def test_the_comparison_alone_names_every_fixture(self):
        result, output = self.run_suite()
        self.assertFalse(result.wasSuccessful(), output)
        self.assertIn("one.json: no test loads this fixture", output)
        self.assertIn("two/three.txt: no test loads this fixture", output)

    def test_an_empty_fixtures_directory_fails(self):
        self.root = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, self.root)

        def nothing(self):
            pass

        self.assert_run_fails("holds no fixtures", test_nothing=nothing)


class Discover(FixtureTest):
    """The check in `python3 -m unittest discover`, in a process of its own, as CI runs it."""

    def project(self, test_module, *arguments, patch=None, **others):
        """Run discover on a project of expected_tests.py, the comparison module, the fake tree and the given modules."""
        directory = os.path.join(tempfile.mkdtemp(prefix="ratchet-test-"), "checks")
        self.addCleanup(shutil.rmtree, os.path.dirname(directory))
        os.mkdir(directory)
        for name in ("expected_tests.py", COMPARISON + ".py"):
            shutil.copyfile(os.path.join(HERE, name), os.path.join(directory, name))
        if patch:
            with open(os.path.join(directory, "expected_tests.py"), encoding="utf-8") as handle:
                text = handle.read()
            self.assertEqual(text.count(patch[0]), 1, patch[0])
            with open(os.path.join(directory, "expected_tests.py"), "w", encoding="utf-8") as handle:
                handle.write(text.replace(patch[0], patch[1]))
        shutil.copytree(self.fixture_directory(TREE), os.path.join(directory, "fixtures"))
        others["test_inner"] = test_module
        for name, text in others.items():
            with open(os.path.join(directory, name + ".py"), "w", encoding="utf-8") as handle:
                handle.write(text)
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", directory, "-v"] + list(arguments),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        return result.returncode, result.stdout

    def assert_both_named(self, code, output):
        self.assertEqual(code, 1, output)
        self.assertIn(SUMMARY, output)
        self.assertIn("one.json: no test loads this fixture", output)
        self.assertIn("two/three.txt: no test loads this fixture", output)

    MODULE = (
        "from expected_tests import FixtureTest\n\n"
        "class Inner(FixtureTest):\n"
        "    def test_one(self):\n"
        "        self.assertTrue(self.fixture_bytes('one.json'))\n"
    )

    def test_a_complete_set_exits_zero(self):
        code, output = self.project(self.MODULE + "\n    def test_three(self):\n        self.assertTrue(self.fixture_bytes('two/three.txt'))\n")
        self.assertEqual(code, 0, output)
        self.assertIn("Ran 2 tests", output)

    def test_a_missing_test_exits_nonzero(self):
        code, output = self.project(self.MODULE)
        self.assertEqual(code, 1, output)
        self.assertIn("two/three.txt: no test loads this fixture", output)
        self.assertIn("FAILED (failures=1)", output)

    def test_a_module_that_cannot_be_imported_exits_nonzero_and_its_fixtures_are_named(self):
        broken = "import a_module_that_does_not_exist\n" + self.MODULE.replace("one.json", "two/three.txt")
        code, output = self.project(self.MODULE, test_broken=broken)
        self.assertEqual(code, 1, output)
        self.assertIn("No module named 'a_module_that_does_not_exist'", output)
        self.assertIn("two/three.txt: no test loads this fixture", output)
        self.assertNotIn("one.json: no test loads this fixture", output)


    # Every way found to keep the tests that load fixtures from running. The comparison must run anyway.
    BOTH = (
        "import unittest\nfrom expected_tests import FixtureTest\n\n"
        "class Inner(FixtureTest):\n"
        "    def test_one(self):\n"
        "        self.assertTrue(self.fixture_bytes('one.json'))\n\n"
        "    def test_three(self):\n"
        "        self.assertTrue(self.fixture_bytes('two/three.txt'))\n"
    )

    def test_a_set_up_shared_by_every_fixture_test_that_skips_exits_nonzero(self):
        # The reviewer's probe: every class that loads fixtures is skipped, and so was the check.
        code, output = self.project(self.BOTH, patch=(
            "    fixtures = FIXTURES\n",
            "    fixtures = FIXTURES\n\n    @classmethod\n    def setUpClass(cls):\n        raise unittest.SkipTest('class preparation unavailable')\n"))
        self.assert_both_named(code, output)

    def test_a_class_set_up_that_skips_exits_nonzero(self):
        code, output = self.project(self.BOTH + "\n    @classmethod\n    def setUpClass(cls):\n        raise unittest.SkipTest('not today')\n")
        self.assert_both_named(code, output)

    def test_a_class_set_up_that_errors_names_the_fixtures(self):
        code, output = self.project(self.BOTH + "\n    @classmethod\n    def setUpClass(cls):\n        raise RuntimeError('broken')\n")
        self.assert_both_named(code, output)

    def test_a_module_set_up_that_skips_exits_nonzero(self):
        code, output = self.project(self.BOTH + "\n\ndef setUpModule():\n    raise unittest.SkipTest('not today')\n")
        self.assert_both_named(code, output)

    def test_a_module_set_up_that_errors_names_the_fixtures(self):
        code, output = self.project(self.BOTH + "\n\ndef setUpModule():\n    raise RuntimeError('broken')\n")
        self.assert_both_named(code, output)

    def test_a_class_skip_decorator_exits_nonzero(self):
        code, output = self.project(self.BOTH.replace("class Inner(", "@unittest.skip('not today')\nclass Inner("))
        self.assert_both_named(code, output)

    def test_a_load_tests_hook_that_drops_the_tests_exits_nonzero(self):
        code, output = self.project(self.BOTH + "\n\ndef load_tests(loader, tests, pattern):\n    return unittest.TestSuite()\n")
        self.assert_both_named(code, output)

    def test_the_only_module_that_loads_fixtures_cannot_be_imported(self):
        code, output = self.project("import a_module_that_does_not_exist\n" + self.BOTH)
        self.assert_both_named(code, output)
        self.assertIn("No module named 'a_module_that_does_not_exist'", output)

    def test_a_module_that_discover_does_not_collect_exits_nonzero(self):
        code, output = self.project("", inner_tests=self.BOTH)
        self.assert_both_named(code, output)

    def test_a_filter_that_selects_no_test_that_loads_fixtures_exits_nonzero(self):
        code, output = self.project(self.BOTH, "-k", "test_nothing_by_this_name")
        self.assert_both_named(code, output)

    def test_a_filter_that_selects_some_of_them_names_the_rest(self):
        code, output = self.project(self.BOTH, "-k", "test_one")
        self.assertEqual(code, 1, output)
        self.assertIn("two/three.txt: no test loads this fixture", output)
        self.assertNotIn("one.json: no test loads this fixture", output)

    def test_a_run_that_stops_at_the_first_failure_names_the_rest(self):
        code, output = self.project(self.BOTH, "-f", test_a_first="import unittest\n\nclass First(unittest.TestCase):\n    def test_fails(self):\n        self.fail('first')\n")
        self.assert_both_named(code, output)

    @unittest.skipUnless(hasattr(signal, "SIGINT") and hasattr(os, "kill"), "the system cannot interrupt a process")
    def test_a_run_interrupted_before_any_fixture_test_names_every_fixture(self):
        # With -c, the first interrupt stops the run, and the run is not failed for it.
        first = "import os, signal, unittest\n\nclass First(unittest.TestCase):\n    def test_interrupts(self):\n        os.kill(os.getpid(), signal.SIGINT)\n"
        code, output = self.project(self.BOTH, "-c", test_a_first=first)
        self.assert_both_named(code, output)

    def test_a_tear_down_module_that_errors_names_the_fixtures_of_the_module(self):
        code, output = self.project(self.BOTH + "\n\ndef tearDownModule():\n    raise RuntimeError('broken')\n")
        self.assertEqual(code, 1, output)
        self.assertIn("one.json: loaded by test_inner.Inner.test_one, which did not pass: tearDownModule (test_inner) errored", output)

    def test_a_tear_down_module_that_skips_exits_nonzero(self):
        code, output = self.project(self.BOTH + "\n\ndef tearDownModule():\n    raise unittest.SkipTest('not today')\n")
        self.assertEqual(code, 1, output)
        self.assertIn("two/three.txt: loaded by test_inner.Inner.test_three, which did not pass: tearDownModule (test_inner) skipped", output)

    def test_the_comparison_alone_exits_nonzero(self):
        code, output = self.project("")
        self.assert_both_named(code, output)


class Collected(unittest.TestCase):
    """The comparison is part of this repo's own suite. Not a FixtureTest, so that it runs whatever FixtureTest does."""

    def test_the_comparison_is_the_first_thing_discover_runs(self):
        suite = unittest.TestLoader().discover(HERE)
        first = next(iter(suite))
        self.assertIsInstance(first, expected_tests.Comparison)
        self.assertEqual(first.root, expected_tests.FIXTURES)
        found = [test for test in suite if isinstance(test, expected_tests.Comparison)]
        self.assertEqual(len(found), 1)

    def test_a_filter_does_not_remove_the_comparison(self):
        loader = unittest.TestLoader()
        loader.testNamePatterns = ["*test_nothing_by_this_name*"]
        self.assertIsInstance(next(iter(loader.discover(HERE))), expected_tests.Comparison)


if __name__ == "__main__":
    unittest.main()
