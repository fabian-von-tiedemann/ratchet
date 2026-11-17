"""The runner of the suite in the child process of checks/expected_tests.py.

    python3 checks/suite_runner.py --records FILE --start checks

It is started by checks/expected_tests.py, not by hand. It runs
`unittest discover` on the start directory with unittest's own text runner, and
writes one JSON record per line to FILE, which must not exist yet:

- "start", when a test starts, with a number that is new for each test instance
- "outcome", for each outcome that unittest gives: passed, failed, errored, skipped,
  expected failure or unexpected success. An outcome of a subtest is the outcome of
  its test. An outcome of a set-up or tear-down of a class or a module has an
  instance of its own, which never started.
- "loaded", when a FixtureTest loads a fixture: its name and the sha256 of the
  bytes it read, with the instance that was running, or null outside any test
- "complete", after unittest has printed its summary, with the counts.

The outcomes come from unittest's result object, here, and not from the tests. The
completion record is written only when the run returns. A run that exits early,
from anywhere, or is killed, leaves it out.

FixtureTest is how a test loads a fixture. It works the same in a run without this
runner, such as `python3 -m unittest discover -s checks`, and records nothing there.

Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import unittest

import expected_tests

FIXTURES = expected_tests.FIXTURES
# The recorder of this run, set by main(). None in a run without this runner.
RECORDER = None


class Recorder:
    """Writes the records of one run, one JSON object per line, each flushed when it is written."""

    def __init__(self, path):
        self.handle = open(path, "x", encoding="utf-8", newline="\n")
        self.instances = 0
        self.current = None
        self.outcomes = 0
        self.loads = 0

    def write(self, record):
        self.handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        self.handle.flush()

    def new_instance(self):
        self.instances += 1
        return self.instances

    def start(self, test):
        self.current = self.new_instance()
        test._suite_runner_instance = self.current
        self.write({"record": "start", "instance": self.current, "test": test.id()})

    def outcome(self, test, outcome):
        case = getattr(test, "test_case", test) if isinstance(test, unittest.case._SubTest) else test
        instance = getattr(case, "_suite_runner_instance", None)
        if instance is None:
            # A set-up or tear-down of a class or a module, which unittest gives as a holder, not as a test.
            instance = self.new_instance()
        self.outcomes += 1
        self.write({"record": "outcome", "instance": instance, "test": case.id(), "outcome": outcome})

    def loaded(self, name, sha):
        self.loads += 1
        self.write({"record": "loaded", "instance": self.current, "fixture": name, "sha256": sha})

    def complete(self, tests_run):
        self.write({"record": "complete", "tests_run": tests_run, "outcomes": self.outcomes, "loaded": self.loads})
        self.handle.close()


class RecordingResult(unittest.TextTestResult):
    """unittest's text result, which also gives every outcome to the recorder."""

    def startTest(self, test):
        RECORDER.start(test)
        super().startTest(test)

    def stopTest(self, test):
        super().stopTest(test)
        RECORDER.current = None

    def addSuccess(self, test):
        super().addSuccess(test)
        RECORDER.outcome(test, "passed")

    def addError(self, test, err):
        super().addError(test, err)
        RECORDER.outcome(test, "errored")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        RECORDER.outcome(test, "failed")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        RECORDER.outcome(test, "skipped")

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        RECORDER.outcome(test, "expected failure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        RECORDER.outcome(test, "unexpected success")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            RECORDER.outcome(test, "failed" if issubclass(err[0], test.failureException) else "errored")


def main(argv=None):
    global RECORDER
    parser = argparse.ArgumentParser(description="Run the suite and record every outcome. Started by checks/expected_tests.py.")
    parser.add_argument("--records", required=True, help="the file to write the records to. It must not exist")
    parser.add_argument("--start", required=True, help="the directory that discover starts from")
    args = parser.parse_args(argv)
    RECORDER = Recorder(args.records)
    suite = unittest.TestLoader().discover(args.start)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult).run(suite)
    RECORDER.complete(result.testsRun)
    return 0 if result.wasSuccessful() else 1


class FixtureTest(unittest.TestCase):
    """A test that loads fixtures, each by its name under the fixtures directory. Each load is recorded."""

    fixtures = FIXTURES

    def _record(self, name, sha):
        if RECORDER is not None:
            RECORDER.loaded(name, sha)

    def _path(self, name):
        if not isinstance(name, str) or not expected_tests.NAME.match(name):
            raise self.failureException("%r is not a fixture's name: its path under the fixtures directory, with / between the parts" % (name,))
        return os.path.join(self.fixtures, *name.split("/"))

    def fixture_bytes(self, name):
        """The bytes of one fixture, by its name under the fixtures directory."""
        path = self._path(name)
        if os.path.islink(path) or not os.path.isfile(path):
            self._record(name, None)
            raise self.failureException("there is no fixture named %s under %s" % (name, self.fixtures))
        with open(path, "rb") as handle:
            data = handle.read()
        self._record(name, expected_tests.digest(data))
        return data

    def fixture_text(self, name):
        """The text of one fixture, read as strict UTF-8."""
        return self.fixture_bytes(name).decode("utf-8", errors="strict")

    def scratch(self):
        directory = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, directory)
        return directory

    def fixture_file(self, name):
        """A copy of one fixture in a scratch directory, under its own name. Returns the copy's path."""
        data = self.fixture_bytes(name)
        path = os.path.join(self.scratch(), *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def fixture_directory(self, name):
        """A copy of every fixture in a directory, in a scratch directory. Returns the copy's path."""
        source = self._path(name)
        names = []
        if os.path.isdir(source) and not os.path.islink(source):
            for folder, folders, files in os.walk(source):
                folders.sort()
                names += [os.path.relpath(os.path.join(folder, file), self.fixtures).replace(os.sep, "/") for file in sorted(files)]
        if not names:
            raise self.failureException("there is no directory of fixtures named %s under %s" % (name, self.fixtures))
        target = os.path.join(self.scratch(), *name.split("/"))
        for each in names:
            data = self.fixture_bytes(each)
            path = os.path.join(target, *each[len(name) + 1:].split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(data)
        return target


if __name__ == "__main__":
    # The tests import this module as suite_runner. Run that module, so that there is one recorder, not two.
    import suite_runner
    sys.exit(suite_runner.main())
