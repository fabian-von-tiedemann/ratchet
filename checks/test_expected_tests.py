"""The check that every expected test ran and passed (ratchet.expected-tests-ran).

    python3 -m unittest discover -s checks -v

The cases use a fake tree of fixtures, checks/fixtures/tests-ran/tree/, copied into a
scratch directory through this run's own ledger. Some give the check fake results. The
others run small suites with unittest's own runner, and one runs `unittest discover` in a
process of its own, which is how CI runs the suite. Standard library only.
"""

import io
import os
import shutil
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

    def run_suite(self, **methods):
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite_for(self.root, **methods))
        return result, stream.getvalue()

    def assert_run_fails(self, problem, **methods):
        result, output = self.run_suite(**methods)
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

    def test_an_empty_fixtures_directory_fails(self):
        self.root = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, self.root)

        def nothing(self):
            pass

        self.assert_run_fails("holds no fixtures", test_nothing=nothing)


class Discover(FixtureTest):
    """The check in `python3 -m unittest discover`, in a process of its own, as CI runs it."""

    def project(self, test_module, **others):
        directory = os.path.join(tempfile.mkdtemp(prefix="ratchet-test-"), "checks")
        self.addCleanup(shutil.rmtree, os.path.dirname(directory))
        os.mkdir(directory)
        shutil.copyfile(os.path.join(HERE, "expected_tests.py"), os.path.join(directory, "expected_tests.py"))
        shutil.copytree(self.fixture_directory(TREE), os.path.join(directory, "fixtures"))
        others["test_inner"] = test_module
        for name, text in others.items():
            with open(os.path.join(directory, name + ".py"), "w", encoding="utf-8") as handle:
                handle.write(text)
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", directory, "-v"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        return result.returncode, result.stdout

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


if __name__ == "__main__":
    unittest.main()
