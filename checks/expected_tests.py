"""Stub, so that the tests can be shown red before the check exists: it loads fixtures and checks nothing."""

import os
import shutil
import tempfile
import unittest

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def problems(root, records):
    return []


class FixtureTest(unittest.TestCase):
    fixtures = FIXTURES

    def fixture_bytes(self, name):
        path = os.path.join(self.fixtures, *name.split("/"))
        if not os.path.isfile(path) or ".." in name.split("/"):
            raise self.failureException("no fixture named %r" % name)
        with open(path, "rb") as handle:
            return handle.read()

    def fixture_text(self, name):
        return self.fixture_bytes(name).decode("utf-8")

    def scratch(self):
        directory = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, directory)
        return directory

    def fixture_file(self, name):
        path = os.path.join(self.scratch(), *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(self.fixture_bytes(name))
        return path

    def fixture_directory(self, name):
        target = os.path.join(self.scratch(), *name.split("/"))
        source = os.path.join(self.fixtures, *name.split("/"))
        for folder, _, files in os.walk(source):
            for file in files:
                relative = os.path.relpath(os.path.join(folder, file), self.fixtures).replace(os.sep, "/")
                path = os.path.join(target, os.path.relpath(os.path.join(folder, file), source))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as handle:
                    handle.write(self.fixture_bytes(relative))
        return target
