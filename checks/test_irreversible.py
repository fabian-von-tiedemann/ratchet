"""The hook for ratchet.irreversible-waits: a step that cannot be undone waits for an approval that names it.

    python3 -m unittest discover -s checks -v

checks/irreversible.py is a PreToolUse hook for Claude Code. It reads the hook's JSON on stdin and exits 2, with
the reason on stderr, to deny a command; it exits 0 to let it run. The fixtures are under
checks/fixtures/irreversible/:

- deny/<step>-<case>.sh: one command each, which the hook must deny for that step. The prefix names the step:
  fp is force-push, tag is tag, release is release, del is delete-outside, set is settings, un is a command the
  hook cannot read with certainty, appr is a command that touches the approvals file.
- pass/ok-<case>.sh: one command each, which the hook must let run.
- approved/<step>/command.sh and approvals.json: a command that is denied, and the approvals file that lets it run.
- approvals/<case>.json: an approvals file that approves nothing for `git tag v2`.
- several/<case>/command.sh, one.json and both.json: a command that takes two steps, an approvals file with an
  entry for one of them, which does not let it run, and one with an entry for each, which does.

Each test runs the hook as Claude Code does, in a process of its own, on a scratch working tree that is a git
repository with a tag v1, and with a link inside it that points outside. Standard library only.
"""

import json
import os
import secrets
import subprocess
import sys
import tempfile
import unittest

from suite_runner import FixtureTest
from test_checks import ROOT, read

HOOK = os.path.join(ROOT, "checks", "irreversible.py")
APPROVALS = os.path.join(".claude", "ratchet-approvals.json")

STEPS = {
    "fp": "force-push",
    "tag": "tag",
    "release": "release",
    "del": "delete-outside",
    "set": "settings",
    "un": "unreadable",
    "appr": "approvals",
}

# approvals/<case>.json -> what the hook says about the file, or None when the file is valid and approves
# nothing for `git tag v2`.
BAD_APPROVALS = {
    "unknown-field": "unknown field 'by'",
    "unknown-top-field": "unknown field 'note'",
    "field-twice": "the field 'step' appears twice in one object",
    "not-json": "not valid JSON",
    "not-utf8": "not valid UTF-8, at byte",
    "not-a-list": "approvals must be a list",
    "top-not-object": "the top level must be an object",
    "step-unknown": "step must be one of",
    "step-other": "is not the step release",
    "until-form": "until must be a date",
    "until-impossible": "until must be a date",
    "until-number": "until must be a date",
    "command-operator": "one plain command",
    "command-substitution": "one plain command",
    "command-twice": "is approved twice",
    "reason-empty": "reason must not be empty",
    "not-ascii": "printable ASCII",
    "expired": None,
    "command-other": None,
    "command-extra-space": None,
}


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "init.defaultBranch=main",
                    "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"] + list(args),
                   cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Hook(FixtureTest):
    def setUp(self):
        scratch = self.scratch()
        self.tree = os.path.realpath(os.path.join(scratch, "tree"))
        self.outside = os.path.realpath(os.path.join(scratch, "outside"))
        for folder in (self.tree, self.outside, os.path.join(self.tree, "checks"), os.path.join(self.tree, "build"),
                       os.path.join(self.outside, "sub")):
            os.makedirs(folder, exist_ok=True)
        os.symlink(self.outside, os.path.join(self.tree, "link-out"))
        with open(os.path.join(self.tree, "README"), "w") as handle:
            handle.write("tree\n")
        git(self.tree, "init", "-q")
        git(self.tree, "add", "README")
        git(self.tree, "commit", "-q", "-m", "One")
        git(self.tree, "tag", "v1")
        git(self.tree, "branch", "personlig/x")

    def hook(self, payload, raw=None, root=None):
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = root or self.tree
        data = raw if raw is not None else json.dumps(payload).encode("utf-8")
        result = subprocess.run([sys.executable, HOOK], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, cwd=self.tree)
        return result.returncode, result.stdout.decode("utf-8"), result.stderr.decode("utf-8")

    def bash(self, command, cwd=None):
        return self.hook({"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "Bash",
                          "tool_input": {"command": command, "description": "x"}, "cwd": cwd or self.tree,
                          "tool_use_id": "t", "permission_mode": "default"})

    def command(self, name):
        text = self.fixture_text(name)
        self.assertTrue(text.endswith("\n"), name)
        return text[:-1]

    def approve(self, data):
        os.makedirs(os.path.join(self.tree, ".claude"), exist_ok=True)
        with open(os.path.join(self.tree, APPROVALS), "wb") as handle:
            handle.write(data)

    def assert_denied(self, result, step, command):
        code, out, err = result
        self.assertEqual(code, 2, "%r was not denied: %s%s" % (command, out, err))
        self.assertIn("\n- %s: " % step, err, "%r was denied, but not for %s: %s" % (command, step, err))
        self.assertNotIn("Traceback", err)

    def assert_passes(self, result, command):
        code, out, err = result
        self.assertEqual((code, err), (0, ""), "%r was not let through: %s" % (command, err))

    def test_every_fixture_that_must_be_denied_is_denied_for_its_step(self):
        names = sorted(os.listdir(os.path.join(self.fixtures, "irreversible", "deny")))
        self.assertGreater(len(names), 100)
        for name in names:
            prefix = name.split("-", 1)[0]
            self.assertIn(prefix, STEPS, name)
            with self.subTest(fixture=name):
                command = self.command("irreversible/deny/" + name)
                self.assert_denied(self.bash(command), STEPS[prefix], command)

    def test_every_fixture_that_must_pass_passes(self):
        names = sorted(os.listdir(os.path.join(self.fixtures, "irreversible", "pass")))
        self.assertGreater(len(names), 30)
        for name in names:
            with self.subTest(fixture=name):
                command = self.command("irreversible/pass/" + name)
                self.assert_passes(self.bash(command), command)

    def test_each_step_runs_with_an_approval_that_names_it_and_its_exact_command(self):
        steps = sorted(os.listdir(os.path.join(self.fixtures, "irreversible", "approved")))
        self.assertEqual(steps, sorted(set(STEPS.values()) - {"unreadable", "approvals"}))
        for step in steps:
            with self.subTest(step=step):
                command = self.command("irreversible/approved/%s/command.sh" % step)
                approvals = self.fixture_bytes("irreversible/approved/%s/approvals.json" % step)
                path = os.path.join(self.tree, APPROVALS)
                if os.path.exists(path):
                    os.remove(path)
                self.assert_denied(self.bash(command), step, command)
                self.approve(approvals)
                self.assert_passes(self.bash(command), command)
                # The same approval does not reach a command that differs, or the step chained to another command.
                self.assert_denied(self.bash(command + " "), step, command + " ")
                self.assert_denied(self.bash("true && " + command), step, "true && " + command)

    def test_a_command_with_several_steps_runs_when_each_step_has_an_entry(self):
        cases = sorted(os.listdir(os.path.join(self.fixtures, "irreversible", "several")))
        self.assertEqual(cases, ["force-tag", "mirror"])
        for case in cases:
            with self.subTest(case=case):
                command = self.command("irreversible/several/%s/command.sh" % case)
                path = os.path.join(self.tree, APPROVALS)
                if os.path.exists(path):
                    os.remove(path)
                result = self.bash(command)
                self.assert_denied(result, "force-push", command)
                self.assert_denied(result, "tag", command)
                # One entry is valid, and lets the command run only once the other step has an entry too.
                self.approve(self.fixture_bytes("irreversible/several/%s/one.json" % case))
                code, _, err = self.bash(command)
                self.assertEqual(code, 2, err)
                self.assertNotIn("ratchet-approvals.json: ", err)
                self.assertIn('"step": "tag"', err)
                self.assertNotIn('"step": "force-push"', err)
                self.approve(self.fixture_bytes("irreversible/several/%s/both.json" % case))
                self.assert_passes(self.bash(command), command)
                self.assert_denied(self.bash("true && " + command), "tag", "true && " + command)

    def test_an_approvals_file_that_is_not_valid_or_does_not_match_approves_nothing(self):
        names = sorted(name[:-len(".json")] for name in os.listdir(os.path.join(self.fixtures, "irreversible", "approvals")))
        self.assertEqual(names, sorted(BAD_APPROVALS))
        for name, message in sorted(BAD_APPROVALS.items()):
            with self.subTest(fixture=name):
                self.approve(self.fixture_bytes("irreversible/approvals/%s.json" % name))
                result = self.bash("git tag v2")
                self.assert_denied(result, "tag", "git tag v2")
                if message is None:
                    self.assertNotIn("ratchet-approvals.json:", result[2])
                else:
                    self.assertIn("ratchet-approvals.json: ", result[2])
                    self.assertIn(message, result[2])

    def test_a_command_that_cannot_be_read_is_never_approved(self):
        command = "sh -c 'git tag v2'"
        self.approve(json.dumps({"approvals": [{"step": "tag", "command": command, "until": "2999-12-31",
                                                "reason": "Asked."}]}).encode("utf-8"))
        result = self.bash(command)
        self.assert_denied(result, "unreadable", command)
        self.assertIn("ratchet-approvals.json: ", result[2])

    def test_a_directory_from_mktemp_may_be_deleted_by_its_path_in_a_later_command(self):
        made = subprocess.run(["mktemp", "-d"], stdout=subprocess.PIPE, check=True, universal_newlines=True).stdout.strip()
        self.addCleanup(lambda: os.path.isdir(made) and os.rmdir(made))
        self.assertRegex(os.path.basename(made), r"^tmp\.[A-Za-z0-9]+$")
        for command in ("rm -rf %s" % made, "rm -rf '%s'" % made, "rm -rf %s/a" % made):
            with self.subTest(command=command):
                self.assert_passes(self.bash(command), command)
        for command in ("rm -rf %s/.." % made, "rm -rf %s/../x" % made, "rm -rf %s" % os.path.dirname(made)):
            with self.subTest(command=command):
                self.assert_denied(self.bash(command), "delete-outside", command)
        # A directory in the same place that mktemp -d did not name, and a link that mktemp -d would have named.
        other = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(os.rmdir, other)
        self.assert_denied(self.bash("rm -rf %s" % other), "delete-outside", other)
        link = os.path.join(os.path.dirname(made), "tmp." + secrets.token_hex(5))
        os.symlink(self.outside, link)
        self.addCleanup(os.remove, link)
        self.assert_denied(self.bash("rm -rf %s/" % link), "delete-outside", link)
        self.assert_denied(self.bash("rm -rf %s/sub" % link), "delete-outside", link)

    def test_the_working_tree_is_the_project_directory_and_follows_cd(self):
        checks = os.path.join(self.tree, "checks")
        self.assert_passes(self.bash("rm -rf build", cwd=checks), "rm -rf build in checks")
        self.assert_passes(self.bash("rm -rf ../build", cwd=checks), "rm -rf ../build in checks")
        self.assert_denied(self.bash("rm -rf ../../x", cwd=checks), "delete-outside", "rm -rf ../../x in checks")
        self.assert_passes(self.bash("rm -rf %s/build" % self.tree), "an absolute path inside")
        self.assert_denied(self.bash("rm -rf %s" % self.outside), "delete-outside", "an absolute path outside")

    def test_the_approvals_file_cannot_be_written_with_the_file_tools(self):
        path = os.path.join(self.tree, APPROVALS)
        for tool, field in (("Write", "file_path"), ("Edit", "file_path"), ("MultiEdit", "file_path"), ("NotebookEdit", "notebook_path")):
            with self.subTest(tool=tool):
                result = self.hook({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {field: path}, "cwd": self.tree})
                self.assert_denied(result, "approvals", tool)
                elsewhere = self.hook({"hook_event_name": "PreToolUse", "tool_name": tool,
                                       "tool_input": {field: os.path.join(self.tree, "README")}, "cwd": self.tree})
                self.assert_passes(elsewhere, tool)
        template = os.path.join(self.tree, "templates", os.path.basename(APPROVALS))
        self.assert_passes(self.hook({"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": template},
                                      "cwd": self.tree}), "Write to a file of the same name elsewhere")
        self.assert_passes(self.hook({"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": path},
                                      "cwd": self.tree}), "Read")

    def test_input_the_hook_cannot_read_is_denied(self):
        cases = {
            "not JSON": b"{",
            "not UTF-8": b'{"tool_name": "Bash", "tool_input": {"command": "ls \xff"}, "cwd": "/"}',
            "a field twice": b'{"tool_name": "Bash", "tool_name": "Read", "tool_input": {"command": "git tag v2"}, "cwd": "/"}',
            "not an object": b"[]",
            "no tool name": json.dumps({"tool_input": {"command": "ls"}, "cwd": self.tree}).encode(),
            "no command": json.dumps({"tool_name": "Bash", "tool_input": {}, "cwd": self.tree}).encode(),
            "a command that is not text": json.dumps({"tool_name": "Bash", "tool_input": {"command": ["ls"]}, "cwd": self.tree}).encode(),
            "no cwd": json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}).encode(),
            "a relative cwd": json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": "tree"}).encode(),
            "no file path": json.dumps({"tool_name": "Write", "tool_input": {}, "cwd": self.tree}).encode(),
        }
        for name, raw in sorted(cases.items()):
            with self.subTest(case=name):
                code, _, err = self.hook(None, raw=raw)
                self.assertEqual(code, 2, err)
                self.assertIn("- input: ", err)
                self.assertNotIn("Traceback", err)

    def test_the_message_says_how_to_go_ahead(self):
        code, _, err = self.bash("git push --force origin main")
        self.assertEqual(code, 2)
        self.assertIn('"step": "force-push"', err)
        self.assertIn("git push --force origin main", err)
        self.assertIn(APPROVALS, err)


class Wiring(unittest.TestCase):
    """The settings that wire the hook, in the template and in this repo, and the approvals file of the template."""

    def settings(self, name):
        import registry
        return registry.parse_json(read(name).encode("utf-8"))

    def assert_wired(self, data, script):
        self.assertEqual(sorted(data), ["hooks"])
        self.assertEqual(sorted(data["hooks"]), ["PreToolUse"])
        self.assertEqual(data["hooks"]["PreToolUse"], [{
            "matcher": "Bash|Write|Edit|MultiEdit|NotebookEdit",
            "hooks": [{"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/" + script],
                       "onFailure": "block", "timeout": 30}],
        }])

    def test_the_template_wires_a_copy_of_the_hook_in_the_project(self):
        self.assert_wired(self.settings("templates/claude-settings.json"), ".claude/hooks/irreversible.py")

    def test_this_repo_wires_the_hook_from_checks(self):
        self.assert_wired(self.settings(".claude/settings.json"), "checks/irreversible.py")
        self.assertIn("/.claude/ratchet-approvals.json\n", read(".gitignore").splitlines(True))

    def test_the_template_approvals_file_is_valid_and_approves_nothing(self):
        sys.path.insert(0, os.path.join(ROOT, "checks"))
        import irreversible
        approvals, problems = irreversible.read_approvals(os.path.join(ROOT, "templates", "ratchet-approvals.json"))
        self.assertEqual((approvals, problems), ([], []))


if __name__ == "__main__":
    unittest.main()
