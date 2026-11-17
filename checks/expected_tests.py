"""Fail the run when a test it expects did not run (ratchet.expected-tests-ran).

    python3 -m unittest discover -s checks -v

The expected tests are read from the fixtures themselves: every file under
checks/fixtures/ is one fixture, and the run must hold a test that loaded it and
passed. A test loads a fixture through FixtureTest, never by its path. Each load is
recorded in a ledger that belongs to the run, with the test and the sha256 of the
bytes it read, and each test's outcome is recorded when it ends. When the run stops,
the ledger is compared with the fixtures as they stand, and the run fails, naming
each one, on:

- a fixture that no test loaded
- a test that loaded a fixture and did not pass: it failed, errored, could not be
  prepared, was skipped, or was an expected failure or an unexpected success
- a name that a test gave and that is not a fixture
- a record whose bytes are not the fixture's own, so a name without its content
  does not count
- a fixtures directory that is missing or holds no fixtures, because a run that
  expects nothing has not shown that everything ran.

The failure is added to the run's result as one more failed test, before unittest
prints its summary and sets the exit status.

Standard library only. Run on Python 3.9 and 3.12.
"""

import functools
import hashlib
import os
import re
import shutil
import tempfile
import unittest

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
# A fixture's name: its path under the fixtures directory, with "/" between the parts. No part starts with a dot.
NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_][A-Za-z0-9_.-]*)*\Z")
PASSED = "passed"
# What the result holds after a test that did not pass, in the order an outcome is named.
OUTCOMES = (
    ("errors", "errored"),
    ("failures", "failed"),
    ("skipped", "skipped"),
    ("expectedFailures", "expected failure"),
    ("unexpectedSuccesses", "unexpected success"),
)
LEDGERS = "_expected_tests_ledgers"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fixtures(root):
    """Return ({name: sha256 of its bytes}, problems) for the fixtures under root."""
    if not os.path.isdir(root) or os.path.islink(root):
        return {}, ["there is no directory of fixtures at %s" % root]
    found, problems = {}, []
    for folder, folders, files in os.walk(root):
        folders.sort()
        for entry in sorted(folders + files):
            path = os.path.join(folder, entry)
            name = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.islink(path):
                problems.append("%s: is a link, not a fixture" % name)
                if entry in folders:
                    folders.remove(entry)
            elif not NAME.match(name):
                problems.append("%r: is not a name a test can load. A fixture is named by letters, digits, _ . and -, and does not start with a dot" % name)
            elif entry in files:
                with open(path, "rb") as handle:
                    found[name] = digest(handle.read())
    if not found and not problems:
        problems.append("%s holds no fixtures. A run that expects nothing has not shown that everything ran" % root)
    return found, problems


def problems(root, records):
    """Why the records of a run do not show every fixture under root loaded by a test that passed.

    records holds (name, test, outcome, sha256 of the bytes the test read, or None).
    """
    found, result = fixtures(root)
    for name, test, outcome, sha in records:
        if name not in found:
            result.append("%s: named by %s, and there is no such fixture" % (name, test))
        elif sha != found[name]:
            result.append("%s: named by %s, which did not load it as it stands" % (name, test))
        elif outcome != PASSED:
            result.append("%s: loaded by %s, which did not pass: %s" % (name, test, outcome))
    named = set(record[0] for record in records)
    for name in sorted(set(found) - named):
        result.append("%s: no test loads this fixture" % name)
    return result


class Ledger:
    """What the tests of one run loaded from one fixtures directory, and how each test ended."""

    def __init__(self, root):
        self.root = root
        self.loads = []
        self.outcomes = {}

    def records(self):
        return [(name, test, self.outcomes.get(test, "did not end"), sha) for name, test, sha in self.loads]


def ledger(result, root):
    """The ledger for root in this run. The first one installs the comparison at the end of the run."""
    ledgers = getattr(result, LEDGERS, None)
    if ledgers is None:
        ledgers = {}
        setattr(result, LEDGERS, ledgers)
        stop = result.stopTestRun

        @functools.wraps(stop)
        def stop_test_run():
            report(result, ledgers)
            stop()

        result.stopTestRun = stop_test_run
    return ledgers.setdefault(root, Ledger(root))


class _ExpectedTestsRan(unittest.TestCase):
    """The comparison, as it is shown in the run: one more test, which failed."""

    def test_every_expected_test_ran_and_passed(self):
        pass


def report(result, ledgers):
    found = []
    for root in sorted(ledgers):
        found += problems(root, ledgers[root].records())
    if not found:
        return
    test = _ExpectedTestsRan("test_every_expected_test_ran_and_passed")
    message = "\n".join(
        ["Not every expected test ran and passed (ratchet.expected-tests-ran). %d problem(s). "
         "Every fixture needs a test that loads it through FixtureTest and passes, in the same run:" % len(found)]
        + ["- " + problem for problem in found]
    )
    result.startTest(test)
    result.addFailure(test, (AssertionError, AssertionError(message), None))
    result.stopTest(test)


def tally(result):
    return tuple(len(getattr(result, field, ())) for field, _ in OUTCOMES)


class FixtureTest(unittest.TestCase):
    """A test that loads fixtures. Each load is recorded with the test, and counts only if the test passes."""

    fixtures = FIXTURES

    def run(self, result=None):
        if result is None:
            result = self.defaultTestResult()
            result.startTestRun()
            try:
                self.run(result)
            finally:
                result.stopTestRun()
            return result
        self._ledger = ledger(result, self.fixtures)
        self._started = False
        name = self._testMethodName
        method = getattr(self, name)

        @functools.wraps(method)
        def body(*args, **kwargs):
            self._started = True
            return method(*args, **kwargs)

        before = tally(result)
        setattr(self, name, body)
        try:
            return super().run(result)
        finally:
            delattr(self, name)
            grown = [outcome for (_, outcome), old, new in zip(OUTCOMES, before, tally(result)) if new > old]
            outcome = grown[0] if grown else PASSED
            if outcome == "errored" and not self._started:
                outcome = "could not be prepared"
            self._ledger.outcomes[self.id()] = outcome

    def _record(self, name, sha):
        ledger = getattr(self, "_ledger", None)
        if ledger is None:
            raise self.failureException("a fixture is loaded while the test runs, not before")
        ledger.loads.append((name, self.id(), sha))

    def _path(self, name):
        if not isinstance(name, str) or not NAME.match(name):
            self._record(str(name), None)
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
        self._record(name, digest(data))
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
            self._record(name, None)
            raise self.failureException("there is no directory of fixtures named %s under %s" % (name, self.fixtures))
        target = os.path.join(self.scratch(), *name.split("/"))
        for each in names:
            data = self.fixture_bytes(each)
            path = os.path.join(target, *each[len(name) + 1:].split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(data)
        return target
