"""The tripwire for ratchet.irreversible-waits, and the tag ruleset that locks moving and deleting a tag.

    python3 -m unittest discover -s checks -v

checks/tripwire.py is a PreToolUse hook for Claude Code. These tests run it as Claude Code does: a child process
that gets the call as JSON on stdin, in a scratch git work tree with a tag v1 and a branch feature. The cases are
under checks/fixtures/tripwire/: deny.json holds every case the hook claims, each with the steps it must name,
pass.json holds the normal work of the control room, which must pass, and approvals/ holds approvals files with one
defect each. In a command, {tree} stands for the scratch work tree. Each test loads what it uses through FixtureTest.
Standard library only.
"""

import datetime
import json
import os
import random
import re
import shutil
import string
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from suite_runner import FixtureTest
from test_checks import ROOT, read

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import registry  # noqa: E402
import testing  # noqa: E402
import tripwire  # noqa: E402

HOOK = os.path.join(HERE, "tripwire.py")
APPROVALS = os.path.join(".claude", "ratchet-approvals.json")
STEPS = ("force-push", "tag", "release", "delete-outside", "settings")
MATCHER = "Bash|Write|Edit|MultiEdit|NotebookEdit"
# Approvals files with one defect -> what the denial must say about the file. A file that is valid but holds no
# entry for the command says nothing about the file.
DEFECTS = {
    "unknown-field": "unknown field 'note'",
    "entry-unknown-field": "unknown field 'reason'",
    "entry-missing-field": "missing field 'until'",
    "duplicate-field": "the field 'step' appears twice",
    "not-json": "not valid JSON",
    "not-utf8": "not valid UTF-8",
    "top-not-object": "must be an object",
    "approvals-not-list": "must be a list",
    "unknown-step": "the step must be one of",
    "date-form": "a real date",
    "date-impossible": "a real date",
    "date-number": "a real date",
    "command-chain": "one plain command",
    "command-substitution": "one plain command",
    "command-empty": "one plain command",
    "command-spaces": "one plain command",
    "trailing-space": "one plain command",
    "command-not-ascii": "one plain command",
}
VALID_BUT_NO_MATCH = ("expired", "other-command", "other-step")


def git(cwd, *args):
    testing.git(cwd, *args, env=testing.environment(drop=(), **testing.identity("Test")),
                options=testing.quiet_options())


def fresh(root, length, make):
    """A new entry directly in root, tmp. and length random letters and digits, made by make(path), which fails when
    the path exists. Never a fixed name, so that runs at the same time never share one."""
    choose = random.SystemRandom().choice
    for _ in range(100):
        path = os.path.join(root, "tmp." + "".join(choose(string.ascii_letters + string.digits) for _ in range(length)))
        try:
            make(path)
            return path
        except FileExistsError:
            continue
    raise AssertionError("no free name of %d characters in %s" % (length, root))


def strict(data, fields):
    """A fixture's object, with exactly these fields."""
    if not isinstance(data, dict) or set(data) != set(fields):
        raise AssertionError("expected exactly the fields %s, found %r" % (sorted(fields), data))
    return data


class Tripwire(FixtureTest):

    def setUp(self):
        self.tree = os.path.realpath(os.path.join(self.scratch(), "tree"))
        os.makedirs(os.path.join(self.tree, ".claude"))
        os.makedirs(os.path.join(self.tree, "sub"))
        git(self.tree, "init", "-q")
        git(self.tree, "commit", "-q", "--allow-empty", "-m", "first")
        git(self.tree, "tag", "v1")
        git(self.tree, "branch", "feature")

    def hook(self, payload, raw=None, environ=None):
        """(exit status, stderr) of the hook given this call, in this environment or the test's own."""
        data = raw if raw is not None else json.dumps(payload).encode("utf-8")
        result = subprocess.run([sys.executable, HOOK], input=data, cwd=self.tree, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=dict(os.environ if environ is None else environ, CLAUDE_PROJECT_DIR=self.tree), timeout=60)
        return result.returncode, result.stderr.decode("utf-8", errors="replace")

    def bash(self, command, environ=None):
        return self.hook({"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": self.tree,
                          "tool_input": {"command": command.replace("{tree}", self.tree)}}, environ=environ)

    def approve(self, entries):
        with open(os.path.join(self.tree, APPROVALS), "w", encoding="utf-8") as handle:
            json.dump({"approvals": entries}, handle)

    def entry(self, step, command, days=1):
        until = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
        return {"step": step, "command": command.replace("{tree}", self.tree), "until": until}

    def deny_cases(self):
        data = strict(registry.parse_json(self.fixture_bytes("tripwire/deny.json")), ["cases"])
        cases = [strict(case, ["steps", "command", "approvable"]) for case in data["cases"]]
        self.assertGreater(len(cases), 100)
        return cases

    def pass_commands(self):
        data = strict(registry.parse_json(self.fixture_bytes("tripwire/pass.json")), ["commands"])
        self.assertGreater(len(data["commands"]), 40)
        return data["commands"]

    def test_every_claimed_case_is_denied_and_names_its_steps(self):
        for case in self.deny_cases():
            with self.subTest(command=case["command"]):
                code, message = self.bash(case["command"])
                self.assertEqual(code, 2, message)
                for step in case["steps"]:
                    self.assertIn("tripwire: %s" % step, message)
                for step in set(STEPS + ("approvals-file",)) - set(case["steps"]):
                    self.assertNotIn("tripwire: %s" % step, message)

    def test_every_step_has_claimed_cases(self):
        steps = set(step for case in self.deny_cases() for step in case["steps"])
        self.assertEqual(steps, set(STEPS + ("approvals-file",)))

    def test_the_normal_work_of_the_control_room_passes(self):
        for command in self.pass_commands():
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), (0, ""))

    def test_an_approval_that_names_each_step_and_the_exact_command_lets_it_pass(self):
        for case in self.deny_cases():
            if not case["approvable"]:
                continue
            with self.subTest(command=case["command"]):
                self.approve([self.entry(step, case["command"]) for step in case["steps"]])
                self.assertEqual(self.bash(case["command"]), (0, ""))
                # The approval names the exact command, and nothing else.
                for other in (case["command"] + " ", "true && " + case["command"], case["command"] + "; true"):
                    self.assertEqual(self.bash(other)[0], 2, other)

    def test_a_case_that_is_not_approvable_stays_denied_with_an_entry(self):
        for case in self.deny_cases():
            if case["approvable"]:
                continue
            with self.subTest(command=case["command"]):
                self.approve([self.entry(step, case["command"]) for step in case["steps"] if step in STEPS])
                code, message = self.bash(case["command"])
                self.assertEqual(code, 2, message)

    def test_a_directory_from_mktemp_may_be_deleted_by_its_path_in_a_later_call(self):
        # Shell state does not last from one Bash call to the next, so a workspace often removes its temporary
        # directory by path. Only a real directory named tmp. and six or more letters or digits, directly in the
        # temporary directory, and owned by this user, passes, with what is inside it.
        made = subprocess.run(["mktemp", "-d"], stdout=subprocess.PIPE, universal_newlines=True, check=True).stdout.strip()
        self.addCleanup(lambda: os.path.isdir(made) and os.rmdir(made))
        self.assertRegex(os.path.basename(made), r"^tmp\.[A-Za-z0-9]{6,}$")
        for command in ("rm -rf %s" % made, "rm -r %s/sub" % made):
            self.assertEqual(self.bash(command), (0, ""), command)
        root = os.path.dirname(made)
        other = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(os.rmdir, other)
        short = fresh(root, 5, os.mkdir)
        self.addCleanup(os.rmdir, short)
        link = fresh(root, 10, lambda path: os.symlink(self.tree, path))
        self.addCleanup(os.remove, link)
        for command in ("rm -rf %s" % root, "rm -rf %s/.." % made, "rm -rf %s" % other, "rm -rf %s" % short,
                        "rm -rf %s" % link, "rm -rf %s/" % link):
            code, message = self.bash(command)
            self.assertEqual(code, 2, command)
            self.assertIn("tripwire: delete-outside", message)

    def test_a_link_to_or_inside_a_directory_from_mktemp_is_never_followed(self):
        # The entry in the temporary directory, and every part after it, is read as written: a link there, "." or
        # "..", and the path is denied, even where the link or the ".." leads to another directory from mktemp -d.
        made, made2 = (subprocess.run(["mktemp", "-d"], stdout=subprocess.PIPE, universal_newlines=True,
                                      check=True).stdout.strip() for _ in range(2))
        for directory in (made, made2):
            self.addCleanup(shutil.rmtree, directory, True)
        root = os.path.dirname(made)
        outside = self.scratch()
        sibling = fresh(root, 10, lambda path: os.symlink(made, path))
        self.addCleanup(os.remove, sibling)
        os.symlink(outside, os.path.join(made, "out"))
        os.symlink(made2, os.path.join(made, "in"))
        os.mkdir(os.path.join(made, "sub"))
        for command in ("rm -rf %s/" % made, "rm -rf %s//sub" % made, "rm -rf %s" % os.path.realpath(made)):
            self.assertEqual(self.bash(command), (0, ""), command)
        for command in ("rm -rf %s" % sibling, "rm -rf %s/" % sibling, "rm -rf %s/sub" % sibling,
                        "rm -rf %s/out/" % made, "rm -rf %s/out/x" % made, "rm -rf %s/out" % made,
                        "rm -rf %s/in/" % made, "rm -rf %s/in/x" % made,
                        "rm -rf %s/.." % made, "rm -rf %s/../.." % made, "rm -rf %s/sub/../.." % made,
                        "rm -rf %s/../%s" % (made, os.path.basename(made2)), "rm -rf %s/./sub" % made):
            code, message = self.bash(command)
            self.assertEqual(code, 2, command)
            self.assertIn("tripwire: delete-outside", message)

    def test_the_temporary_directory_is_where_mktemp_writes_whatever_TMPDIR_says(self):
        # Claude Code's sandbox sets TMPDIR to a directory of its own, and on macOS mktemp -d ignores TMPDIR and
        # writes to the per-user temporary directory that the system gives it. The hook looks where mktemp -d
        # writes: a directory from mktemp -d may be deleted by its path, and a directory of the same form in TMPDIR,
        # where mktemp -d did not write, is denied, so that setting TMPDIR does not widen the exception. Where
        # mktemp -d writes where TMPDIR says, as on Linux, the two are the same place.
        unrelated = os.path.realpath(self.scratch())
        environ = dict(os.environ, TMPDIR=unrelated)
        made = subprocess.run(["mktemp", "-d"], stdout=subprocess.PIPE, universal_newlines=True, check=True,
                              env=environ).stdout.strip()
        self.addCleanup(shutil.rmtree, made, True)
        for command in ("rm -rf %s" % made, "rm -r %s/sub" % made):
            self.assertEqual(self.bash(command, environ), (0, ""), command)
        if os.path.realpath(os.path.dirname(made)) != unrelated:
            planted = fresh(unrelated, 10, os.mkdir)
            for command in ("rm -rf %s" % planted, "rm -r %s/sub" % planted):
                code, message = self.bash(command, environ)
                self.assertEqual(code, 2, command)
                self.assertIn("tripwire: delete-outside", message)

    def decide(self, command):
        """The hook's decision on a Bash call, made in this process so that a test can mock what the hook reads."""
        call = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": self.tree, "tool_input": {"command": command}}
        return tripwire.decide(call, {"CLAUDE_PROJECT_DIR": self.tree}, datetime.date.today())

    def mktemp_in_tmp(self):
        """A real directory that mktemp -d makes directly in the second root, of mktemp -d's own form, removed after
        the test. The second root is /tmp in the hook. Here it is a fresh directory from mktemp -d, put in place of
        /tmp for this test only, so that the test needs no write to /tmp and runs in a sandbox that refuses one."""
        root = os.path.realpath(subprocess.run(["mktemp", "-d"], stdout=subprocess.PIPE, universal_newlines=True,
                                               check=True).stdout.strip())
        self.addCleanup(shutil.rmtree, root, True)
        replaced = mock.patch.object(tripwire, "SECOND_ROOT", root)
        replaced.start()
        self.addCleanup(replaced.stop)
        made = subprocess.run(["mktemp", "-d", os.path.join(root, "tmp.XXXXXXXXXX")], stdout=subprocess.PIPE,
                              universal_newlines=True, check=True).stdout.strip()
        self.assertRegex(made, r"^%s/tmp\.[A-Za-z0-9]{10}$" % re.escape(root))
        return made

    def test_the_second_root_is_tmp(self):
        # The tests above put a directory of their own in place of /tmp. The hook itself trusts /tmp, a constant that
        # nothing in the call, its JSON or its environment, can change.
        self.assertEqual(tripwire.SECOND_ROOT, "/tmp")

    def test_on_macOS_a_system_temporary_directory_it_cannot_establish_is_not_trusted(self):
        # On macOS the hook reads where mktemp -d writes from confstr(_CS_DARWIN_USER_TEMP_DIR). When that fails, or
        # gives no absolute path of an existing directory, no directory takes its place: not TMPDIR, which the harness
        # sets, and not a default. /tmp stays the second root, here the stand-in from mktemp_in_tmp. Elsewhere the
        # temporary directory is TMPDIR's, as before.
        unrelated = os.path.realpath(self.scratch())
        planted = fresh(unrelated, 10, os.mkdir)
        in_tmp = self.mktemp_in_tmp()
        failures = {"OSError": {"side_effect": OSError(22, "Invalid argument")}, "ValueError": {"side_effect": ValueError("unknown")},
                    "None": {"return_value": None}, "empty": {"return_value": ""}, "relative": {"return_value": "var/T"},
                    "missing": {"return_value": os.path.join(unrelated, "missing") + "/"}}

        def on(platform, **confstr):
            return (mock.patch.object(tripwire.sys, "platform", platform), mock.patch.object(tripwire.os, "confstr", **confstr),
                    mock.patch.object(tripwire.tempfile, "gettempdir", return_value=unrelated))

        for name, confstr in sorted(failures.items()):
            with self.subTest(confstr=name):
                first, second, third = on("darwin", **confstr)
                with first, second, third:
                    for command in ("rm -rf %s" % planted, "rm -r %s/sub" % planted):
                        message = self.decide(command)
                        self.assertIsNotNone(message, command)
                        self.assertIn("tripwire: delete-outside", message)
                    for command in ("rm -rf %s" % in_tmp, "rm -r %s/sub" % in_tmp):
                        self.assertIsNone(self.decide(command), command)
        for platform, confstr in (("darwin", {"return_value": unrelated + "/"}), ("linux", failures["OSError"])):
            with self.subTest(platform=platform):
                first, second, third = on(platform, **confstr)
                with first, second, third:
                    for command in ("rm -rf %s" % planted, "rm -r %s/sub" % planted, "rm -rf %s" % in_tmp):
                        self.assertIsNone(self.decide(command), command)

    def test_a_directory_from_mktemp_in_tmp_may_be_deleted_by_its_path_in_a_later_call(self):
        # /tmp is the second root, whatever TMPDIR says and wherever the system's temporary directory is: a real
        # directory of mktemp -d's form, made directly in /tmp, and a path inside it, pass. The stand-in for /tmp is
        # from mktemp_in_tmp, and the first root is an unrelated directory, so that only the second root lets it pass.
        unrelated = os.path.realpath(self.scratch())
        made = self.mktemp_in_tmp()
        with mock.patch.dict(tripwire.os.environ, TMPDIR=unrelated), \
                mock.patch.object(tripwire, "mktemp_directory", return_value=unrelated):
            for command in ("rm -rf %s" % made, "rm -r %s/sub" % made, "rm -rf %s/" % made):
                self.assertIsNone(self.decide(command), command)

    def test_a_directory_of_another_owner_is_never_deleted(self):
        # The entry from mktemp -d must be owned by the user the hook runs as. With the hook running as another uid,
        # the same directory, and a path inside it, are denied, in the temporary directory and in /tmp. The stand-in
        # for /tmp is from mktemp_in_tmp, and the temporary directory is another fresh directory from mktemp -d, so
        # that each path is judged by its own root alone.
        first = os.path.realpath(subprocess.run(["mktemp", "-d"], stdout=subprocess.PIPE, universal_newlines=True,
                                                check=True).stdout.strip())
        self.addCleanup(shutil.rmtree, first, True)
        made = subprocess.run(["mktemp", "-d", os.path.join(first, "tmp.XXXXXXXXXX")], stdout=subprocess.PIPE,
                              universal_newlines=True, check=True).stdout.strip()
        in_tmp = self.mktemp_in_tmp()
        commands = ["rm -rf %s" % path for path in (made, in_tmp)] + ["rm -r %s/sub" % path for path in (made, in_tmp)]
        with mock.patch.object(tripwire, "mktemp_directory", return_value=first):
            for command in commands:
                self.assertIsNone(self.decide(command), command)
            with mock.patch.object(tripwire.os, "getuid", return_value=os.getuid() + 1):
                for command in commands:
                    message = self.decide(command)
                    self.assertIsNotNone(message, command)
                    self.assertIn("tripwire: delete-outside", message)

    def test_a_command_with_two_steps_needs_an_entry_for_each(self):
        command = "git push --mirror origin"
        self.approve([self.entry("force-push", command)])
        code, message = self.bash(command)
        self.assertEqual(code, 2, message)
        self.assertIn("tripwire: tag", message)
        self.assertNotIn("tripwire: force-push", message)
        self.approve([self.entry("force-push", command), self.entry("tag", command)])
        self.assertEqual(self.bash(command), (0, ""))

    def test_an_approval_holds_through_its_last_day_and_not_after(self):
        self.approve([self.entry("tag", "git tag v9", days=0)])
        self.assertEqual(self.bash("git tag v9"), (0, ""))
        self.approve([self.entry("tag", "git tag v9", days=-1)])
        self.assertEqual(self.bash("git tag v9")[0], 2)

    def test_an_approvals_file_with_a_defect_approves_nothing(self):
        names = sorted(name[:-len(".json")] for name in os.listdir(os.path.join(self.fixtures, "tripwire", "approvals")))
        self.assertEqual(names, sorted(list(DEFECTS) + list(VALID_BUT_NO_MATCH)))
        for name in names:
            with self.subTest(file=name):
                with open(os.path.join(self.tree, APPROVALS), "wb") as handle:
                    handle.write(self.fixture_bytes("tripwire/approvals/%s.json" % name))
                code, message = self.bash("git tag v9")
                self.assertEqual(code, 2, message)
                self.assertIn("tripwire: tag", message)
                if name in DEFECTS:
                    self.assertIn("approvals file", message)
                    self.assertIn(DEFECTS[name], message)
                else:
                    self.assertNotIn("approvals file", message)

    def test_the_message_says_what_the_owner_writes(self):
        code, message = self.bash("git tag v9")
        self.assertEqual(code, 2)
        self.assertIn('{"step": "tag", "command": "git tag v9", "until": "YYYY-MM-DD"}', message)
        self.assertIn(APPROVALS, message)

    def test_no_file_tool_writes_the_approvals_file(self):
        target = os.path.join(self.tree, APPROVALS)
        for tool, field in (("Write", "file_path"), ("Edit", "file_path"), ("MultiEdit", "file_path"), ("NotebookEdit", "notebook_path")):
            with self.subTest(tool=tool):
                for path in (target, os.path.join(self.tree, "sub", "..", APPROVALS)):
                    code, message = self.hook({"tool_name": tool, "cwd": self.tree, "tool_input": {field: path}})
                    self.assertEqual(code, 2, message)
                    self.assertIn("tripwire: approvals-file", message)
                # A file of the same name elsewhere, such as the template, is not the approvals file.
                other = os.path.join(self.tree, "templates", "ratchet-approvals.json")
                self.assertEqual(self.hook({"tool_name": tool, "cwd": self.tree, "tool_input": {field: other}}), (0, ""))
        # Not even an approval lets an agent write the approvals file.
        self.approve([self.entry(step, "cat .claude/ratchet-approvals.json") for step in STEPS])
        self.assertEqual(self.bash("cat .claude/ratchet-approvals.json")[0], 2)

    def test_other_tools_pass(self):
        for tool in ("Read", "Glob", "Grep", "WebFetch"):
            with self.subTest(tool=tool):
                self.assertEqual(self.hook({"tool_name": tool, "cwd": self.tree, "tool_input": {"file_path": "/etc/x"}}), (0, ""))

    def test_input_it_cannot_read_is_denied(self):
        cases = {
            "empty": b"",
            "not JSON": b"{",
            "not UTF-8": b'{"tool_name": "Bash", "tool_input": {"command": "ls \xff"}}',
            "a list": b"[]",
            "no tool": b'{"tool_input": {"command": "ls"}}',
            "a tool that is not text": b'{"tool_name": 1, "tool_input": {}}',
            "no input": b'{"tool_name": "Bash"}',
            "no command": b'{"tool_name": "Bash", "tool_input": {}}',
            "a command that is not text": b'{"tool_name": "Bash", "tool_input": {"command": ["git"]}}',
            "a path that is not text": b'{"tool_name": "Write", "tool_input": {"file_path": 1}}',
            "a field twice": b'{"tool_name": "Read", "tool_name": "Bash", "tool_input": {"command": "git push -f"}}',
        }
        for name, raw in cases.items():
            with self.subTest(case=name):
                code, message = self.hook(None, raw=raw)
                self.assertEqual(code, 2, message)
                self.assertIn("tripwire:", message)

    def test_it_never_exits_other_than_0_or_2(self):
        odd = ["", " ", "'", '"', "\\", "$(", "`", "((", "))", "$((1+", "<<", "<<EOF", "a <<EOF\nb", "|", "&&", ";;", "{", "}",
               "git", "git push", "git push -", "git tag -", "gh api", "gh api -X", "gh api -X PATCH", "rm -rf", "rm -rf ''",
               "rm -rf \"\"", "cd", "cd -", "d=$(mktemp -d", "$(git push -f", "echo `git tag v2", "\x00", "git\x00push -f",
               "x" * 100000, "(" * 2000, "$(" * 500, "git push " + "+a " * 2000, "é\u202e", "rm -rf /\udc80"]
        for command in odd:
            with self.subTest(command=command[:40]):
                code, message = self.hook({"tool_name": "Bash", "cwd": self.tree, "tool_input": {"command": command}})
                self.assertIn(code, (0, 2), message)
                self.assertNotIn("Traceback", message)


class Settings(FixtureTest):
    """The settings that run the hook, in the template and in this repo, and the empty approvals file."""

    def settings(self, *path):
        hooks = strict(registry.parse_json(read(*path).encode("utf-8")), ["hooks"])["hooks"]
        groups = strict(hooks, ["PreToolUse"])["PreToolUse"]
        self.assertEqual(len(groups), 1)
        group = strict(groups[0], ["matcher", "hooks"])
        self.assertEqual(group["matcher"], MATCHER)
        self.assertEqual(len(group["hooks"]), 1)
        return strict(group["hooks"][0], ["type", "command", "args", "onFailure", "timeout"])

    def test_the_template_runs_the_copied_hook_and_blocks_when_it_fails(self):
        hook = self.settings("templates", "claude-settings.json")
        self.assertEqual(hook, {"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/tripwire.py"],
                                "onFailure": "block", "timeout": 30})

    def test_this_repo_runs_its_own_hook_and_blocks_when_it_fails(self):
        hook = self.settings(".claude", "settings.json")
        self.assertEqual(hook, {"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/checks/tripwire.py"],
                                "onFailure": "block", "timeout": 30})

    def test_the_approvals_template_is_empty_and_the_approvals_file_is_ignored_by_git(self):
        self.assertEqual(registry.parse_json(read("templates", "ratchet-approvals.json").encode("utf-8")), {"approvals": []})
        self.assertIn("/.claude/ratchet-approvals.json", read(".gitignore").split("\n"))


class Rule(FixtureTest):
    """ratchet.irreversible-waits in ratchet.json and in this repo's register (D-2026-11-19-locks-not-parsing)."""

    def test_the_rule_is_experimental_outside_the_core_with_the_tripwire_as_its_reference_check(self):
        data = registry.load(os.path.join(ROOT, "ratchet.json"))
        parts = dict((part["id"], part["file"]) for part in data["parts"])
        rules = [rule for rule in data["rules"] if rule["key"] == "ratchet.irreversible-waits"]
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual((rule["status"], rule["enforcement"], rule.get("reference_check")), ("experimental", "enforced", "checks/tripwire.py"))
        self.assertEqual(parts[rule["part"]], "CONTROL-ROOM.md")
        for words in ("tripwire", "not a lock", "tag ruleset", "role", "main branch", "sandbox", "only an admin",
                      "secrets and variables that the role Write may change are caught by the hook alone"):
            self.assertIn(words, rule["ratchet"])
        # 23 when it was added in 0.7. 0.10 adds ratchet.review-by-risk (D-2026-11-19-review-by-risk) and
        # ratchet.one-exact-form, and takes six out (D-2026-11-20-proposal-triage): 19. 0.11 takes six more out, step 2
        # of D-2026-11-22-second-redraw: 13. Step 3 takes three more out: 10. Step 12 adds the seven rules of the
        # product module: 17.
        self.assertEqual(registry.counts(data)["experimental"]["rules"], 17)

    def test_this_repo_adopts_it_as_not_built_and_says_what_is_locked_and_what_only_the_tripwire_catches(self):
        # Built from 2026-11-19, when the maintainer applied the tag ruleset and the control room read it back
        # (D-2026-11-19-tripwire-and-settings), until D-2026-11-22-second-redraw defined "built" by where a check is
        # enforced: a hook is built only when it runs in every harness the project uses, and Codex, which also works on
        # this repo, does not run it. The tripwire is the check the rule names, and the place where it lives says which
        # steps a lock refuses and which the tripwire alone catches.
        register = registry.parse_json(read("register.json").encode("utf-8"))
        entries = [entry for entry in register["adopted"] if entry["key"] == "ratchet.irreversible-waits"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "text only for now")
        where = entries[0]["where"]
        self.assertTrue(where.startswith("Not built. "), where)
        for words in ("runs as a hook only in Claude Code", "Codex and the other harnesses that work on this repo do not run it",
                      "D-2026-11-22-second-redraw"):
            self.assertIn(words, where)
        for words in ("`checks/tripwire.py`", "`.claude/settings.json`", "not every spelling", "`templates/tag-ruleset.json`",
                      "`tags-stay`", "read back on 2026-11-19", "D-2026-11-19-tag-ruleset-scope", "role Write", "only an admin",
                      "`main`", "caught by the tripwire alone", "creating a tag or a release", "a force push to another branch",
                      "Actions secrets and variables", "sandbox", "D-2026-11-19-tripwire-and-settings"):
            self.assertIn(words, where)
        locked, alone = where.split("caught by the tripwire alone", 1)
        for words in ("creating a tag or a release", "a force push to another branch", "Actions secrets and variables"):
            self.assertNotIn(words, locked)

    def test_checks_readme_lists_every_claimed_case(self):
        text = read("checks", "README.md")
        cases = registry.parse_json(self.fixture_bytes("tripwire/deny.json"))["cases"]
        for case in cases:
            with self.subTest(command=case["command"]):
                self.assertIn("`%s`" % case["command"].replace("\n", " "), text)


class Parallel(unittest.TestCase):
    """The tests that make entries in the shared temporary directory, run in several processes at once."""

    TESTS = ("test_tripwire.Tripwire.test_a_directory_from_mktemp_may_be_deleted_by_its_path_in_a_later_call",
             "test_tripwire.Tripwire.test_a_link_to_or_inside_a_directory_from_mktemp_is_never_followed")

    def test_runs_at_the_same_time_do_not_touch_each_other(self):
        children = [subprocess.Popen([sys.executable, "-B", "-m", "unittest"] + list(self.TESTS), cwd=HERE, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT) for _ in range(4)]
        outputs = [child.communicate(timeout=600)[0].decode("utf-8", errors="replace") for child in children]
        for number, (child, output) in enumerate(zip(children, outputs), 1):
            self.assertEqual(child.returncode, 0, "run %d of 4:\n%s" % (number, output))


class TagRuleset(unittest.TestCase):
    """templates/tag-ruleset.json: what the maintainer applies, read strictly (D-2026-11-19-tag-ruleset-scope)."""

    def test_the_ruleset_locks_moving_and_deleting_every_tag_but_not_creating_one(self):
        data = registry.parse_json(read("templates", "tag-ruleset.json").encode("utf-8"))
        strict(data, ["name", "target", "enforcement", "conditions", "rules", "bypass_actors"])
        self.assertEqual(data["target"], "tag")
        self.assertEqual(data["enforcement"], "active")
        self.assertIsInstance(data["name"], str)
        self.assertEqual(data["conditions"], {"ref_name": {"include": ["~ALL"], "exclude": []}})
        self.assertEqual([strict(rule, ["type"])["type"] for rule in data["rules"]], ["deletion", "update", "non_fast_forward"])
        self.assertNotIn("creation", json.dumps(data))
        self.assertEqual(data["bypass_actors"], [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}])

    def test_the_release_only_creates_a_tag_and_never_moves_or_deletes_one(self):
        # What the ruleset leaves open is what the release workflow needs: release.py writes a tag with one POST to
        # git/refs, and no PATCH or DELETE.
        text = read("checks", "release.py")
        self.assertIn('api("POST", path, {"ref": ref, "sha": sha})', text)
        for method in ('"PATCH"', '"DELETE"', '"PUT"'):
            self.assertNotIn(method, text)


if __name__ == "__main__":
    unittest.main()
