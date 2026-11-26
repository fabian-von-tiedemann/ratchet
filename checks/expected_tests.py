#!/usr/bin/env python3
"""Fail when a test the suite expects did not run and pass (ratchet.expected-tests-ran).

    python3 checks/expected_tests.py

Runs the suite in a child process, `checks/suite_runner.py`, which runs
`unittest discover -s checks` and writes a record of the run to a file in a
directory that this process makes. Then reads that file strictly, and fails, naming
each problem, when:

- the child's exit status is not 0, or it was stopped by a signal
- there is no completion record, because the child exited early, from anywhere, or
  was killed; or the completion record's counts disagree with the records
- a test that was collected did not run, because the run was interrupted, told to
  stop or stopped at the first failure; or a test ran that was not collected
- a test did not pass: it failed, errored, was skipped, was an expected failure or
  an unexpected success, or started and has no outcome
- a test has a second outcome record: each instance has exactly one
- a set-up or tear-down of a class or a module had an outcome of its own
- a test id ran more than once
- a fixture under checks/fixtures/ was not loaded, with the bytes it held before the
  run, by a test that passed; or a fixture changed while the suite ran
- a record has a form this check does not know.

The expected tests are the tests that discover collects, and the expected fixtures
are the files under checks/fixtures/. The check catches tests dropped by mistake. It
does not stop test code that defeats it on purpose: that code runs with the same
rights as the check, and a change to checks/ is read by the maintainer
(ratchet.owner-paths).

Standard library only. CI runs it on Python 3.9 and the newest Python 3.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True
# Its own directory on the path, named explicitly, so that python3 -I, which leaves the script's directory out of
# sys.path, still finds the modules beside it.
import os  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import tempfile

import registry

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
RUNNER = os.path.join(HERE, "suite_runner.py")
# A fixture's name: its path under the fixtures directory, with "/" between the parts. No part starts with a dot.
NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_][A-Za-z0-9_.-]*)*\Z")
SHA256 = re.compile(r"^[0-9a-f]{64}\Z")
PASSED = "passed"
OUTCOMES = (PASSED, "failed", "errored", "skipped", "expected failure", "unexpected success")
# Every form of record, with its fields. Nothing else is read.
FORMS = {
    "collected": ("instance", "test"),
    "start": ("instance", "test"),
    "outcome": ("instance", "test", "outcomes"),
    "loaded": ("instance", "fixture", "sha256"),
    "complete": ("collected", "tests_run", "outcomes", "loaded"),
}
COUNTS = (("collected", "tests collected", "collected"), ("tests_run", "tests run", "start"), ("outcomes", "outcomes", "outcome"),
          ("loaded", "fixtures loaded", "loaded"))


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


def whole(value, least):
    return isinstance(value, int) and not isinstance(value, bool) and value >= least


def json_type(value):
    """What kind of JSON value a parsed value is, in words."""
    if isinstance(value, bool):
        return "true or false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "an object"
    return "text"


def form_problem(record):
    """Why a parsed line is not a record of a form this check knows, or None."""
    if not isinstance(record, dict):
        return "a record is one JSON object"
    if "record" not in record:
        return "a record without its kind"
    kind = record["record"]
    # The type comes first: a list or an object is not a key that FORMS can be asked about.
    if not isinstance(kind, str):
        return "the kind of a record must be text, and it is %s" % json_type(kind)
    if kind not in FORMS:
        return "an unknown kind of record %r" % (kind,)
    fields = FORMS[kind]
    unknown = sorted(set(record) - set(fields) - {"record"})
    if unknown:
        return "unknown field %r in a record %s" % (unknown[0], kind)
    missing = [field for field in fields if field not in record]
    if missing:
        return "missing field %r in a record %s" % (missing[0], kind)
    if "instance" in fields and not whole(record["instance"], 1) and not (kind == "loaded" and record["instance"] is None):
        return "instance must be a whole number from 1" + (", or null for a load outside any test" if kind == "loaded" else "")
    if "test" in fields:
        test = record["test"]
        if not isinstance(test, str) or not test or any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in test):
            return "test must be a name of one line"
    if kind == "outcome":
        outcomes = record["outcomes"]
        if not isinstance(outcomes, list) or not outcomes or any(not isinstance(each, str) or each not in OUTCOMES for each in outcomes):
            return "outcomes must be a list of one or more of %s" % ", ".join(OUTCOMES)
    if kind == "loaded":
        if not isinstance(record["fixture"], str) or not NAME.match(record["fixture"]):
            return "fixture must be a fixture's name, its path under the fixtures directory"
        if record["sha256"] is not None and not (isinstance(record["sha256"], str) and SHA256.match(record["sha256"])):
            return "sha256 must be 64 lowercase hex digits, or null for a fixture that is not there"
    if kind == "complete":
        for field in fields:
            if not whole(record[field], 0):
                return "%s must be a whole number from 0" % field
    return None


def read_records(path):
    """Return ([(line number, record)], problems) for the records in path, read strictly."""
    if not os.path.isfile(path):
        return [], ["the suite wrote no records"]
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        return [], ["the records are not valid UTF-8, at byte %d" % error.start]
    records, problems = [], []
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    elif lines:
        problems.append("the records, line %d: the record has no line break at its end, so it was cut off" % len(lines))
    for number, line in enumerate(lines, 1):
        try:
            record = registry.strict_loads(line)
        except RecursionError:
            problems.append("the records, line %d: not a record the check knows: it is nested too deeply" % number)
            continue
        except ValueError as error:
            # The strict reader's own problems name what is wrong. Any other is a line that is not JSON.
            message = str(error) if str(error).startswith("the field ") or str(error).endswith(" is not allowed") else "not one JSON object"
            problems.append("the records, line %d: not a record the check knows: %s" % (number, message))
            continue
        problem = form_problem(record)
        if problem:
            problems.append("the records, line %d: not a record the check knows: %s" % (number, problem))
            continue
        records.append((number, record))
    return records, problems


def status_problems(status):
    if status == 0:
        return []
    if status < 0:
        return ["the suite was stopped by signal %d" % -status]
    return ["the suite exited with status %d" % status]


def compare(records, found):
    """Why the records of a run do not show every test passed once and every fixture loaded by a test that passed.

    found is {name: sha256} of the fixtures as they stood before the run.
    """
    problems = []
    completes = [(number, record) for number, record in records if record["record"] == "complete"]
    if not completes:
        problems.append("the suite did not finish: there is no completion record. It exited early, or was stopped")
    elif len(completes) > 1:
        problems.append("the suite wrote %d completion records" % len(completes))
    if completes:
        first = completes[0][0]
        for number, record in records:
            if number > first and record["record"] != "complete":
                problems.append("the records, line %d: a record follows the completion record" % number)
        complete = completes[0][1]
        for field, label, kind in COUNTS:
            held = sum(1 for _, record in records if record["record"] == kind)
            if complete[field] != held:
                problems.append("the completion record counts %d %s, and the records hold %d" % (complete[field], label, held))
        if complete["tests_run"] == 0:
            problems.append("the suite ran no tests")

    # collected: instance -> test, before the run. tests: instance -> test, for each that started.
    # outcomes: instance -> the outcomes of its one outcome record. seen: every instance that has a start or an outcome.
    # answered: every instance that has an outcome record. doubled: every instance that has more than one.
    collected, tests, outcomes, seen, answered, doubled, ids = {}, {}, {}, set(), set(), set(), {}
    loads = []
    for number, record in records:
        kind = record["record"]
        if kind == "collected":
            instance = record["instance"]
            if seen or loads:
                problems.append("the records, line %d: a test collected after the run started" % number)
            elif instance in collected:
                problems.append("the records, line %d: instance %d collected twice" % (number, instance))
            else:
                collected[instance] = record["test"]
        elif kind == "start":
            instance = record["instance"]
            if instance in tests:
                problems.append("the records, line %d: instance %d started twice" % (number, instance))
                continue
            if instance in seen:
                problems.append("the records, line %d: instance %d starts after a record of it" % (number, instance))
                continue
            seen.add(instance)
            if instance in collected and collected[instance] != record["test"]:
                problems.append("the records, line %d: the start of instance %d names %s, and that instance is %s"
                                % (number, instance, record["test"], collected[instance]))
                continue
            if instance not in collected:
                problems.append("%s: ran and was not collected" % record["test"])
            tests[instance] = record["test"]
            ids.setdefault(record["test"], []).append(instance)
        elif kind == "outcome":
            instance = record["instance"]
            if instance in answered:
                problems.append("the records, line %d: a second outcome of %s, instance %d. A test has exactly one" % (number, record["test"], instance))
                doubled.add(instance)
                continue
            answered.add(instance)
            seen.add(instance)
            if instance not in tests:
                problems.append("%s: %s, outside any test" % (record["test"], ", ".join(record["outcomes"])))
            elif record["test"] != tests[instance]:
                problems.append("the records, line %d: the outcome of instance %d names %s, and that instance is %s"
                                % (number, instance, record["test"], tests[instance]))
            else:
                outcomes[instance] = record["outcomes"]
        elif kind == "loaded":
            if record["instance"] is not None and record["instance"] not in tests:
                problems.append("the records, line %d: %s was loaded by instance %d, which never started" % (number, record["fixture"], record["instance"]))
                continue
            loads.append(record)

    for instance in sorted(set(collected) - set(tests)):
        problems.append("%s: collected and did not run" % collected[instance])
    passed = set()
    for instance in sorted(tests):
        got = outcomes.get(instance)
        if got is None:
            problems.append("%s: started and has no outcome" % tests[instance])
        elif got == [PASSED]:
            if instance in collected and instance not in doubled:
                passed.add(instance)
        elif set(got) == {PASSED}:
            problems.append("%s: passed %d times in one run of the test" % (tests[instance], len(got)))
        else:
            problems.append("%s: %s" % (tests[instance], ", ".join(sorted(set(got) - {PASSED}))))
    for test, instances in sorted(ids.items()):
        if len(instances) > 1:
            problems.append("%s: ran %d times under one id" % (test, len(instances)))

    covered = set()
    for record in loads:
        name, instance, sha = record["fixture"], record["instance"], record["sha256"]
        if instance is None:
            problems.append("%s: loaded outside any test, so no outcome counts for it" % name)
        elif name not in found:
            problems.append("%s: loaded by %s, and there is no such fixture" % (name, tests[instance]))
        elif sha != found[name]:
            problems.append("%s: loaded by %s with bytes that are not the fixture's as it stands" % (name, tests[instance]))
        elif instance in passed:
            covered.add(name)
    for name in sorted(set(found) - covered):
        problems.append("%s: no test that passed loaded it as it stands" % name)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the suite in a process of its own and fail when a test it expects did not run and pass.")
    parser.add_argument("--start", default=HERE, help=argparse.SUPPRESS)
    parser.add_argument("--fixtures", default=FIXTURES, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    before, problems = fixtures(args.fixtures)
    directory = tempfile.mkdtemp(prefix="ratchet-records-")
    try:
        path = os.path.join(directory, "records.jsonl")
        sys.stdout.flush()
        # No bytecode in the runner, or in any Python its tests start (review of 3219bf4).
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        status = subprocess.call([sys.executable, "-B", RUNNER, "--records", path, "--start", os.path.abspath(args.start)], env=env)
        after, _ = fixtures(args.fixtures)
        for name in sorted(set(before) | set(after)):
            if before.get(name) != after.get(name):
                problems.append("%s: changed while the suite ran" % name)
        records, found = read_records(path)
    finally:
        shutil.rmtree(directory)
    problems = status_problems(status) + problems + found + compare(records, before)
    if problems:
        print("expected_tests: FAIL: %d problem(s). Not every expected test ran and passed (ratchet.expected-tests-ran):" % len(problems))
        for problem in problems:
            print("- " + problem)
        return 1
    starts = sum(1 for _, record in records if record["record"] == "start")
    print("expected_tests: every expected test ran and passed. %d tests, each id once, and %d fixtures, each loaded as it stands by a test that passed."
          % (starts, len(before)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
