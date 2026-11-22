"""The inventory: checks/inventory.py lists a repo's agent layer as it stands, and writes nothing.

    python3 -m unittest discover -s checks -v

The fixtures are under checks/fixtures/inventory/: a repo with an agent layer, a user's global layer under home/,
exported rulesets and branch protection under ruleset/, and exports with one fault each under faults/. A fixture's
name cannot start with a dot, so a part of a name that starts with "dot-" stands for one that starts with ".": the
test copies the fixture and renames it. This repo holds no link, so the links are made in the copy. Each test loads
what it uses through FixtureTest. Standard library only.
"""

import ast
import json
import os
import subprocess
import sys
import unittest

from suite_runner import FixtureTest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(HERE, "inventory.py")

# Every value in the fixtures that stands for a secret. None may appear in what the inventory prints.
SECRETS = ("FIXTURE-SECRET-SETTINGS", "FIXTURE-SECRET-CREDENTIALS", "FIXTURE-SECRET-ENV", "FIXTURE-SECRET-MCP",
           "FIXTURE-SECRET-CLAUDE-JSON", "FIXTURE-SECRET-AUTH", "FIXTURE-SECRET-OUTSIDE")

# Fixture under inventory/faults/ -> what the inventory says when it is given that file as an exported ruleset.
FAULTS = {
    "not-json": "not a valid data file",
    "field-twice": "the field 'name' appears twice in one object",
    "not-utf8": "is not valid UTF-8, at byte",
    "wrong-type": "required_status_checks must be a list",
    "rule-without-type": "a rule without a type",
    "not-an-object": "neither a ruleset nor a branch protection",
    "neither-form": "neither a ruleset nor a branch protection",
    "empty-list": "holds no ruleset and no branch protection",
    "no-enforcement": "a ruleset without enforcement",
    "no-target": "a ruleset without target",
    "count-is-bool": "required_approving_review_count must be a number",
    "actor-id-text": "actor_id must be a number",
    "conditions-false": "conditions must be an object",
    "conditions-list": "conditions must be an object",
    "bypass-text": "bypass_actors must be a list",
    "parameters-list": "parameters of pull_request must be an object",
    "allowances-false": "bypass_pull_request_allowances must be an object",
    "toggle-text": "allow_force_pushes must be an object",
}

# The modules through which a script could reach the network or run another program.
NETWORK = {"socket", "ssl", "urllib", "http", "ftplib", "smtplib", "poplib", "imaplib", "telnetlib", "xmlrpc",
           "asyncio", "subprocess", "multiprocessing", "webbrowser"}


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
            if os.path.isfile(path) and not os.path.islink(path):
                with open(path, "rb") as handle:
                    data = handle.read()
            seen[os.path.relpath(path, top)] = (status.st_mode, status.st_size, status.st_mtime_ns, data)
    return seen


class Inventory(FixtureTest):
    def setUp(self):
        self.repo = self.fixture_directory("inventory/repo")
        undot(self.repo)
        self.home = self.fixture_directory("inventory/home")
        undot(self.home)

    def run_inventory(self, *args, home=None, timeout=120, cwd=None):
        environment = dict(os.environ)
        environment["HOME"] = home or self.home
        result = subprocess.run([sys.executable, SCRIPT] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, env=environment, timeout=timeout, cwd=cwd)
        return result.returncode, result.stdout, result.stderr

    def facts(self, *args):
        code, out, err = self.run_inventory(self.repo, "--json", *args)
        self.assertEqual(code, 0, out + err)
        for secret in SECRETS:
            self.assertNotIn(secret, out + err)
        return json.loads(out)

    def text(self, *args):
        code, out, err = self.run_inventory(self.repo, *args)
        self.assertEqual(code, 0, out + err)
        for secret in SECRETS:
            self.assertNotIn(secret, out + err)
        return out

    def ruleset(self, name):
        # An export is read through no link on its whole path, and a scratch folder may lie under one, such as /tmp on
        # macOS: the tests give the path without it.
        return os.path.realpath(self.fixture_file("inventory/ruleset/%s.json" % name))

    def write(self, rel, data, top=None):
        """Write a file into the copy of the repo, or under top, making its folders."""
        path = os.path.join(top or self.repo, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data.encode("utf-8") if isinstance(data, str) else data)
        return path

    def export(self, value, name="export.json"):
        """An export written as JSON into a scratch folder of its own."""
        return self.write(name, json.dumps(value), top=os.path.realpath(self.scratch()))

    def files(self, facts):
        return {entry["path"]: entry for entry in facts["files"]}

    def test_lists_the_agent_layer_with_the_harnesses_that_load_each(self):
        files = self.files(self.facts())
        expected = {
            "AGENTS.md": ("instructions", ["codex", "copilot", "cursor", "windsurf"]),
            "CLAUDE.md": ("instructions", ["claude"]),
            "sub/AGENTS.md": ("instructions", ["codex", "copilot", "cursor", "windsurf"]),
            ".cursorrules": ("instructions", ["cursor"]),
            ".claude/settings.json": ("settings", ["claude"]),
            ".claude/hooks/guard.py": ("hook", ["claude"]),
            ".claude/hooks/old.sh": ("hook", ["claude"]),
            ".claude/skills/deploy/SKILL.md": ("skill", ["claude"]),
            ".claude/skills/empty/notes.md": ("skill file", ["claude"]),
            ".agents/skills/deploy/SKILL.md": ("skill", ["codex"]),
            ".claude/commands/review.md": ("command", ["claude"]),
            ".github/prompts/review.prompt.md": ("command", ["copilot"]),
            ".claude/agents/reviewer.md": ("agent", ["claude"]),
            ".claude/agents/blank.md": ("agent", ["claude"]),
            ".claude/notes.txt": ("unknown", ["claude"]),
            ".mcp.json": ("mcp", ["claude"]),
            ".github/workflows/checks.yml": ("workflow", ["github"]),
            ".github/workflows/nightly.yaml": ("workflow", ["github"]),
            ".github/pull_request_template.md": ("pr template", ["github"]),
            ".github/ISSUE_TEMPLATE/bug.yml": ("issue template", ["github"]),
            ".github/CODEOWNERS": ("code owners", ["github"]),
            "register.json": ("register", ["ratchet"]),
        }
        self.assertEqual(sorted(files), sorted(expected))
        for path, (kind, harnesses) in expected.items():
            with self.subTest(path=path):
                self.assertEqual((files[path]["kind"], files[path]["harnesses"]), (kind, harnesses))
                self.assertEqual(files[path]["layer"], "repo")
        # docs/guide.md is named by an instruction file, but is no part of the agent layer.
        self.assertNotIn("docs/guide.md", files)

    def test_settings_and_mcp_give_names_and_counts_and_never_values(self):
        files = self.files(self.facts())
        self.assertIn("hooks on PreToolUse (1), Stop (1)", files[".claude/settings.json"]["facts"])
        self.assertIn("servers: files, search", files[".mcp.json"]["facts"])
        out = self.text()
        self.assertIn("hooks on PreToolUse (1), Stop (1)", out)
        with open(os.path.join(self.repo, ".mcp.json"), encoding="utf-8") as handle:
            self.assertIn("API_KEY", handle.read())
        self.assertNotIn("API_KEY", out)
        self.assertNotIn("files-server", out)

    def test_skips_files_that_look_like_credentials_and_says_so(self):
        facts = self.facts("--global")
        skipped = {entry["path"]: entry["why"] for entry in facts["skipped"]}
        for path in (".claude/.credentials.json", ".claude/.env", "~/.claude.json", "~/.codex/auth.json"):
            with self.subTest(path=path):
                self.assertEqual(skipped[path], "looks like a credential, not read")
                self.assertNotIn(path, self.files(facts))
        self.assertIn(".claude/.credentials.json: looks like a credential, not read", self.text("--global"))

    def test_reports_links_and_never_follows_one(self):
        outside = os.path.join(self.scratch(), "outside")
        os.makedirs(outside)
        with open(os.path.join(outside, "SKILL.md"), "w") as handle:
            handle.write("FIXTURE-SECRET-OUTSIDE\n")
        os.symlink(outside, os.path.join(self.repo, ".claude", "skills", "outside"))
        os.symlink(os.path.join("..", "..", "AGENTS.md"), os.path.join(self.repo, ".claude", "commands", "linked.md"))
        os.symlink("AGENTS.md", os.path.join(self.repo, "GEMINI.md"))
        facts = self.facts()
        links = {entry["path"]: entry for entry in facts["links"]}
        self.assertEqual(sorted(links), [".claude/commands/linked.md", ".claude/skills/outside", "GEMINI.md"])
        self.assertEqual(links[".claude/skills/outside"]["target"], outside)
        self.assertFalse(links[".claude/skills/outside"]["inside"])
        self.assertTrue(links[".claude/commands/linked.md"]["inside"])
        self.assertTrue(links["GEMINI.md"]["inside"])
        files = self.files(facts)
        for path in links:
            self.assertNotIn(path, files)
        self.assertFalse([path for path in files if path.startswith(".claude/skills/outside")])
        out = self.text()
        self.assertIn(".claude/skills/outside: a link to %s, outside the root, not followed" % outside, out)
        self.assertIn("GEMINI.md: a link to AGENTS.md, inside the root, not followed", out)

    def test_same_content_and_same_name(self):
        facts = self.facts()
        self.assertIn([".claude/commands/review.md", ".github/prompts/review.prompt.md"], facts["same_content"])
        names = {(entry["kind"], entry["name"]): entry for entry in facts["same_name"]}
        self.assertEqual(sorted(names), [("command", "review"), ("skill", "deploy")])
        self.assertEqual(names[("skill", "deploy")]["paths"], [".agents/skills/deploy/SKILL.md", ".claude/skills/deploy/SKILL.md"])
        self.assertFalse(names[("skill", "deploy")]["same_content"])
        self.assertTrue(names[("command", "review")]["same_content"])
        # The empty file is not the same content as anything: it is listed as unused.
        self.assertFalse([group for group in facts["same_content"] if ".claude/agents/blank.md" in group])

    def test_the_global_layer_only_when_asked(self):
        self.assertFalse([path for path in self.files(self.facts()) if path.startswith("~")])
        facts = self.facts("--global")
        files = self.files(facts)
        self.assertEqual(sorted(path for path in files if path.startswith("~")),
                         ["~/.claude/CLAUDE.md", "~/.claude/skills/deploy/SKILL.md", "~/.codex/AGENTS.md", "~/.codex/prompts/review.md"])
        self.assertEqual(files["~/.codex/prompts/review.md"]["kind"], "command")
        self.assertEqual(files["~/.codex/prompts/review.md"]["layer"], "global")
        names = {(entry["kind"], entry["name"]): entry["paths"] for entry in facts["same_name"]}
        self.assertEqual(names[("skill", "deploy")],
                         [".agents/skills/deploy/SKILL.md", ".claude/skills/deploy/SKILL.md", "~/.claude/skills/deploy/SKILL.md"])
        self.assertIn([".claude/skills/deploy/SKILL.md", "~/.claude/skills/deploy/SKILL.md"], facts["same_content"])
        # A link in the global layer is named and not followed, once, wherever it stands.
        outside = os.path.join(self.scratch(), "shared-skills")
        os.makedirs(os.path.join(outside, "deploy"))
        with open(os.path.join(outside, "deploy", "SKILL.md"), "w") as handle:
            handle.write("FIXTURE-SECRET-OUTSIDE\n")
        os.makedirs(os.path.join(self.home, ".agents"))
        os.symlink(outside, os.path.join(self.home, ".agents", "skills"))
        os.symlink(outside, os.path.join(self.home, ".codex", "skills"))
        facts = self.facts("--global")
        self.assertEqual([(link["path"], link["inside"]) for link in facts["links"]],
                         [("~/.agents/skills", False), ("~/.codex/skills", False)])
        self.assertFalse([path for path in self.files(facts) if "deploy" in path and path.startswith(("~/.agents", "~/.codex"))])
        # --home names the directory in place of HOME.
        code, out, err = self.run_inventory(self.repo, "--json", "--global", "--home", self.home, home=self.scratch())
        self.assertEqual(code, 0, out + err)
        self.assertIn("~/.codex/AGENTS.md", self.files(json.loads(out)))

    def test_files_no_harness_in_use_loads(self):
        facts = self.facts()
        self.assertIsNone(facts["not_loaded"])
        self.assertIn("give --uses", self.text())
        facts = self.facts("--uses", "claude,codex")
        self.assertEqual(facts["uses"], ["claude", "codex"])
        not_loaded = {entry["path"]: entry for entry in facts["not_loaded"]}
        self.assertEqual(sorted(not_loaded), [".cursorrules", ".github/prompts/review.prompt.md"])
        self.assertEqual(not_loaded[".cursorrules"]["harnesses"], ["cursor"])
        facts = self.facts("--uses", "claude")
        not_loaded = {entry["path"]: entry for entry in facts["not_loaded"]}
        self.assertEqual(sorted(not_loaded), [".agents/skills/deploy/SKILL.md", ".cursorrules", ".github/prompts/review.prompt.md",
                                              "AGENTS.md", "sub/AGENTS.md"])
        self.assertEqual(not_loaded["AGENTS.md"]["named_by"], ["CLAUDE.md"])
        self.assertEqual(not_loaded["sub/AGENTS.md"]["named_by"], [])
        out = self.text("--uses", "claude")
        self.assertIn("AGENTS.md: loaded by codex, copilot, cursor, windsurf; named by CLAUDE.md", out)
        self.assertEqual(facts["harnesses_here"], ["claude", "codex", "copilot", "cursor", "windsurf"])

    def test_files_that_look_unused(self):
        unused = {entry["path"]: entry["why"] for entry in self.facts()["look_unused"]}
        self.assertEqual(unused, {
            ".claude/hooks/old.sh": "a hook that no settings file names",
            ".claude/skills/empty": "a skill folder without SKILL.md",
            ".claude/agents/blank.md": "empty",
            ".claude/notes.txt": "not a kind this inventory knows",
        })

    def test_paths_an_instruction_file_names_that_do_not_exist(self):
        missing = [(entry["file"], entry["line"], entry["path"]) for entry in self.facts()["missing_paths"]]
        self.assertEqual(missing, [("AGENTS.md", 3, "missing-link.md"), ("AGENTS.md", 5, "docs/missing.md"),
                                   ("AGENTS.md", 5, "scripts/run.sh"), ("sub/AGENTS.md", 3, "old/notes.md")])
        # A bare name in backticks, such as `gone.md` or `register.json`, is a name and not looked at.
        self.assertIn("AGENTS.md:5 names docs/missing.md", self.text())

    def test_workflows_without_a_ruleset(self):
        facts = self.facts()
        workflows = {entry["path"]: entry for entry in facts["workflows"]}
        checks = workflows[".github/workflows/checks.yml"]
        self.assertEqual(checks["on"], ["pull_request", "push"])
        self.assertEqual([(job["id"], job["name"], job["required"]) for job in checks["jobs"]],
                         [("checks", None, None), ("lint", "Lint the docs", None), ("test", None, None)])
        nightly = workflows[".github/workflows/nightly.yaml"]
        self.assertEqual(nightly["on"], ["schedule", "workflow_dispatch"])
        self.assertEqual([(job["id"], job["name"]) for job in nightly["jobs"]], [("sweep", "${{ github.workflow }} sweep")])
        self.assertIsNone(facts["not_required"])
        self.assertIn("give --ruleset", self.text())

    def test_jobs_that_run_and_are_not_required(self):
        facts = self.facts("--ruleset", self.ruleset("ruleset"))
        workflows = {entry["path"]: entry for entry in facts["workflows"]}
        self.assertEqual([(job["id"], job["required"]) for job in workflows[".github/workflows/checks.yml"]["jobs"]],
                         [("checks", True), ("lint", False), ("test", True)])
        self.assertEqual([(entry["path"], entry["job"]) for entry in facts["not_required"]],
                         [(".github/workflows/checks.yml", "lint")])
        self.assertEqual(facts["required_without_job"], ["deploy/preview"])
        ruleset = facts["rulesets"][0]
        self.assertEqual(ruleset["form"], "ruleset")
        self.assertEqual(ruleset["enforcement"], "active")
        self.assertEqual(ruleset["include"], ["~DEFAULT_BRANCH"])
        self.assertEqual(ruleset["required_checks"], ["checks", "test (3.9)", "deploy/preview"])
        self.assertEqual(ruleset["review"], {"approvals": 1, "code_owner": True, "dismiss_stale": True, "last_push": False,
                                             "thread_resolution": False})
        self.assertEqual(ruleset["bypass"], ["RepositoryRole 5 (always)"])
        self.assertEqual(ruleset["other_rules"], ["deletion", "non_fast_forward"])
        self.assertEqual(ruleset["not_read"], ["code_scanning"])
        out = self.text("--ruleset", self.ruleset("ruleset"))
        self.assertIn("Jobs that run on a pull request and are not required: they look like a gate and are not", out)
        self.assertIn('.github/workflows/checks.yml: lint ("Lint the docs")', out)
        self.assertIn("bypass: RepositoryRole 5 (always)", out)

    def test_classic_branch_protection(self):
        facts = self.facts("--ruleset", self.ruleset("protection"))
        self.assertEqual([entry["job"] for entry in facts["not_required"]], ["lint", "test"])
        protection = facts["rulesets"][0]
        self.assertEqual(protection["form"], "branch protection")
        self.assertEqual(protection["required_checks"], ["checks"])
        self.assertEqual(protection["review"], {"approvals": 2, "code_owner": False, "dismiss_stale": True, "last_push": False,
                                                "thread_resolution": None})
        self.assertEqual(protection["bypass"], ["user fixture-admin (pull requests)", "administrators (enforce_admins is off)"])

    def test_a_ruleset_that_is_not_enforced_requires_nothing(self):
        facts = self.facts("--ruleset", self.ruleset("evaluate"))
        self.assertEqual([entry["job"] for entry in facts["not_required"]], ["checks", "lint", "test"])
        self.assertEqual(facts["rulesets"][0]["enforcement"], "evaluate")
        self.assertIn("enforcement evaluate: GitHub does not enforce it", self.text("--ruleset", self.ruleset("evaluate")))
        # Two exports together: what one requires is required.
        facts = self.facts("--ruleset", self.ruleset("evaluate"), "--ruleset", self.ruleset("protection"))
        self.assertEqual([entry["job"] for entry in facts["not_required"]], ["lint", "test"])

    def test_a_ruleset_with_a_fault_cannot_run(self):
        self.assertEqual(sorted(FAULTS), sorted(name[:-len(".json")] for name in os.listdir(os.path.join(self.fixtures, "inventory", "faults"))))
        for name, message in FAULTS.items():
            with self.subTest(fault=name):
                path = os.path.realpath(self.fixture_file("inventory/faults/%s.json" % name))
                code, out, err = self.run_inventory(self.repo, "--ruleset", path)
                self.assertEqual(code, 2)
                self.assertIn(message, out + err)
                self.assertEqual(out, "")

    def test_code_owners_beside_the_files_the_register_names(self):
        facts = self.facts()
        owners = facts["code_owners"]
        self.assertEqual(owners["file"], ".github/CODEOWNERS")
        self.assertEqual(owners["lines"], [[2, "* @fixture-owner"], [4, "/.github/ @fixture-owner"],
                                           [5, "/checks/ @fixture-owner @fixture-second"]])
        self.assertEqual(owners["register_names"], [["AGENTS.md", True], ["checks/check_register.py", False],
                                                    [".github/workflows/checks.yml", True]])
        out = self.text()
        self.assertIn("    5: /checks/ @fixture-owner @fixture-second", out)
        self.assertIn("    checks/check_register.py (does not exist)", out)

    def test_writes_nothing(self):
        before = (snapshot(self.repo), snapshot(self.home))
        for args in ([], ["--json"], ["--global", "--uses", "claude", "--ruleset", self.ruleset("ruleset")]):
            with self.subTest(args=args):
                code, out, err = self.run_inventory(self.repo, *args)
                self.assertEqual(code, 0, out + err)
                self.assertEqual((snapshot(self.repo), snapshot(self.home)), before)

    def test_reaches_no_network_and_runs_no_program(self):
        with open(SCRIPT, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertFalse(imported & NETWORK)
        # From registry, which runs git elsewhere, it takes only the strict reader of JSON.
        used = {node.attr for node in ast.walk(tree)
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "registry"}
        self.assertEqual(used, {"parse_json", "RegistryError"})
        calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and isinstance(node.func.value, ast.Name) and node.func.value.id == "os"}
        self.assertFalse(calls & {"system", "popen", "execv", "execvp", "spawnv", "fork", "startfile"})

    def test_a_name_with_a_line_break_is_shown_escaped(self):
        with open(os.path.join(self.repo, ".claude", "commands", "a\nb.md"), "w") as handle:
            handle.write("A command.\n")
        out = self.text()
        self.assertIn(".claude/commands/a\\nb.md", out)
        self.assertFalse([line for line in out.splitlines() if line.startswith("b.md")])
        self.assertIn(".claude/commands/a\nb.md", self.files(self.facts()))

    def test_a_file_too_large_is_not_read(self):
        path = os.path.join(self.repo, ".claude", "rules", "big.md")
        os.makedirs(os.path.dirname(path))
        with open(path, "w") as handle:
            handle.write("`docs/none.md`\n" + "x" * 1000000)
        facts = self.facts()
        self.assertIn({"path": ".claude/rules/big.md", "why": "larger than 1000000 bytes, not read"}, facts["skipped"])
        self.assertEqual(self.files(facts)[".claude/rules/big.md"]["kind"], "instructions")
        self.assertNotIn("docs/none.md", [entry["path"] for entry in facts["missing_paths"]])

    def test_an_instruction_file_that_is_not_utf8(self):
        path = os.path.join(self.repo, ".claude", "rules", "latin.md")
        os.makedirs(os.path.dirname(path))
        with open(path, "wb") as handle:
            handle.write(b"caf\xe9 `docs/none.md`\n")
        facts = self.facts()
        self.assertIn("not UTF-8 at byte 3: the paths it names are not read", self.files(facts)[".claude/rules/latin.md"]["facts"])
        self.assertNotIn("docs/none.md", [entry["path"] for entry in facts["missing_paths"]])

    def test_cannot_run(self):
        for args in (["--uses", "vim"], ["--ruleset", os.path.join(self.scratch(), "none.json")], ["--bogus"]):
            with self.subTest(args=args):
                code, out, err = self.run_inventory(self.repo, *args)
                self.assertEqual(code, 2, out + err)
        code, out, err = self.run_inventory(os.path.join(self.repo, "no-such-folder"))
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)

    # --- Each finding of the review of #119 at 237bb13, one test each. ---

    def test_global_a_linked_harness_folder_is_named_and_nothing_under_it_is_read(self):
        home = self.scratch()
        outside = self.scratch()
        self.write("claude/skills/hidden/SKILL.md", "FIXTURE-SECRET-OUTSIDE\n", top=outside)
        self.write("claude/CLAUDE.md", "FIXTURE-SECRET-OUTSIDE\n", top=outside)
        self.write("claude/rules/rule.md", "FIXTURE-SECRET-OUTSIDE\n", top=outside)
        self.write("agents/skills/shared/SKILL.md", "FIXTURE-SECRET-OUTSIDE\n", top=outside)
        self.write(".codex/AGENTS.md", "Codex.\n", top=home)
        os.symlink(os.path.join(outside, "claude"), os.path.join(home, ".claude"))
        os.symlink(os.path.join(outside, "agents"), os.path.join(home, ".agents"))
        code, out, err = self.run_inventory(self.repo, "--json", "--global", home=home)
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("FIXTURE-SECRET-OUTSIDE", out + err)
        facts = json.loads(out)
        self.assertEqual([(link["path"], link["inside"]) for link in facts["links"]], [("~/.agents", False), ("~/.claude", False)])
        self.assertEqual(sorted(path for path in self.files(facts) if path.startswith("~")), ["~/.codex/AGENTS.md"])
        # A link deeper down, at ~/.codex/prompts/team, is named at that place, once.
        self.write("prompts/review.md", "FIXTURE-SECRET-OUTSIDE\n", top=outside)
        os.makedirs(os.path.join(home, ".codex", "prompts"))
        os.symlink(os.path.join(outside, "prompts"), os.path.join(home, ".codex", "prompts", "team"))
        code, out, err = self.run_inventory(self.repo, "--json", "--global", home=home)
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("FIXTURE-SECRET-OUTSIDE", out + err)
        self.assertEqual([link["path"] for link in json.loads(out)["links"]], ["~/.agents", "~/.claude", "~/.codex/prompts/team"])

    def test_an_export_is_read_through_the_guarded_reader(self):
        data = self.fixture_bytes("inventory/ruleset/ruleset.json").replace(b"protect-main", b"FIXTURE-SECRET-OUTSIDE")
        folder = os.path.realpath(self.scratch())
        secret = self.write("secret-token.json", data, top=folder)
        plain = self.write("plain.json", data, top=folder)
        link = os.path.join(folder, "linked.json")
        os.symlink(plain, link)
        fifo = os.path.join(folder, "pipe.json")
        os.mkfifo(fifo)
        for path, message in ((secret, "looks like a credential, not read"), (link, "a link, not followed"),
                              (fifo, "not a regular file, not read")):
            with self.subTest(path=os.path.basename(path)):
                code, out, err = self.run_inventory(self.repo, "--ruleset", path, timeout=20)
                self.assertEqual(code, 2, out + err)
                self.assertIn(message, err)
                self.assertEqual(out, "")
                self.assertNotIn("FIXTURE-SECRET-OUTSIDE", out + err)

    def test_a_job_with_a_name_is_required_by_its_name_only(self):
        self.write(".github/workflows/gate.yml", "on: pull_request\njobs:\n  checks:\n    name: Run Checks\n    runs-on: x\n"
                   "  build:\n    name: ${{ matrix.os }} build\n    runs-on: x\n")
        export = self.export({"name": "main", "target": "branch", "enforcement": "active", "rules": [
            {"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "checks"}, {"context": "build"}]}}]})
        facts = self.facts("--ruleset", export)
        gate = {entry["path"]: entry for entry in facts["workflows"]}[".github/workflows/gate.yml"]
        self.assertEqual([(job["id"], job["required"]) for job in gate["jobs"]], [("checks", False), ("build", True)])
        self.assertIn({"path": ".github/workflows/gate.yml", "job": "checks", "name": "Run Checks"}, facts["not_required"])
        # The job checks in checks.yml has no name, so it still reports as checks.
        checks = {entry["path"]: entry for entry in facts["workflows"]}[".github/workflows/checks.yml"]
        self.assertEqual(checks["jobs"][0]["required"], True)

    def test_bypass_actors_left_out_of_an_export_are_not_shown_as_none(self):
        base = {"name": "main", "target": "branch", "enforcement": "active", "rules": []}
        for value, expected, line in ((None, None, "bypass: not shown in the export"), ([], [], "bypass: none")):
            with self.subTest(value=value):
                item = dict(base)
                if value is not None:
                    item["bypass_actors"] = value
                facts = self.facts("--ruleset", self.export(item))
                self.assertEqual(facts["rulesets"][0]["bypass"], expected)
                self.assertIn(line, self.text("--ruleset", self.export(item)))
        item = dict(base, bypass_actors=None)
        self.assertIsNone(self.facts("--ruleset", self.export(item))["rulesets"][0]["bypass"])
        # An actor_id that is null, as for a deploy key, is shown as "-".
        item = dict(base, bypass_actors=[{"actor_id": None, "actor_type": "DeployKey", "bypass_mode": "always"}])
        self.assertEqual(self.facts("--ruleset", self.export(item))["rulesets"][0]["bypass"], ["DeployKey - (always)"])

    def test_review_parameters_it_does_not_know_or_that_are_left_out(self):
        facts = self.facts("--ruleset", self.ruleset("ruleset"))
        ruleset = facts["rulesets"][0]
        self.assertEqual(ruleset["review"]["thread_resolution"], False)
        export = self.export({"name": "main", "target": "branch", "enforcement": "active", "rules": [
            {"type": "pull_request", "parameters": {"required_approving_review_count": 1, "automatic_copilot_code_review_enabled": True}}]})
        ruleset = self.facts("--ruleset", export)["rulesets"][0]
        self.assertEqual(ruleset["review"]["approvals"], 1)
        self.assertIsNone(ruleset["review"]["code_owner"])
        self.assertIn("pull_request.automatic_copilot_code_review_enabled", ruleset["not_read"])
        out = self.text("--ruleset", export)
        self.assertIn("code owner review not in the export", out)
        self.assertIn("rules not read: pull_request.automatic_copilot_code_review_enabled", out)

    def test_a_trigger_list_in_block_form_is_read(self):
        self.write(".github/workflows/listed.yml", "on:\n  - pull_request\n  - push\njobs:\n  extra:\n    runs-on: x\n")
        self.write(".github/workflows/odd.yml", "on:\n  [pull_request,\n   push]\njobs:\n  other:\n    runs-on: x\n")
        facts = self.facts("--ruleset", self.ruleset("ruleset"))
        workflows = {entry["path"]: entry for entry in facts["workflows"]}
        self.assertEqual(workflows[".github/workflows/listed.yml"]["on"], ["pull_request", "push"])
        self.assertIn({"path": ".github/workflows/listed.yml", "job": "extra", "name": None}, facts["not_required"])
        # A list over two lines leaves a bracket open: the workflow is not read, and its jobs are listed as such.
        self.assertEqual(workflows[".github/workflows/odd.yml"]["unread"],
                         "line 2 leaves a quote or a bracket open, a value over more than one line, which this reader does not read")
        self.assertIn({"path": ".github/workflows/odd.yml", "job": None, "name": None, "required": None}, facts["not_known"])
        self.assertIn("not read: line 2 leaves a quote or a bracket open", self.text())

    def test_ratchets_own_copy_is_not_walked(self):
        self.write(".ratchet/AGENTS.md", "Ratchet.\n")
        self.write(".ratchet/checks/fixtures/inventory/repo/CLAUDE.md", "A fixture.\n")
        self.write("sub/.ratchet/AGENTS.md", "Not the root.\n")
        facts = self.facts()
        self.assertFalse([path for path in self.files(facts) if path.startswith(".ratchet")])
        self.assertIn("sub/.ratchet/AGENTS.md", self.files(facts))
        self.assertIn({"path": ".ratchet", "why": "Ratchet's own copy, not walked"}, facts["skipped"])

    def test_a_register_whose_parts_are_not_lists(self):
        self.write("register.json", '{"instructions": "AGENTS.md", "adopted": "all", "own": {"key": "x"}}\n')
        owners = self.facts()["code_owners"]
        self.assertEqual(owners["register_names"], [["AGENTS.md", True]])
        self.assertEqual(owners["note"], "register.json: adopted is not a list, not read; register.json: own is not a list, not read")
        self.assertIn("register.json: adopted is not a list, not read", self.text())

    def test_a_word_after_an_at_sign_is_not_an_import(self):
        self.write("CLAUDE.md", "Ask @alice, or see @pytest.mark.skip and email@example.com.\n"
                   "Read @AGENTS.md. Then @docs/gone.md, and @notes.md!\n")
        missing = [(entry["file"], entry["path"]) for entry in self.facts()["missing_paths"]]
        self.assertIn(("CLAUDE.md", "docs/gone.md"), missing)
        self.assertIn(("CLAUDE.md", "notes.md"), missing)
        self.assertFalse([path for file, path in missing if file == "CLAUDE.md" and path not in ("docs/gone.md", "notes.md")])

    def test_an_apostrophe_inside_a_plain_value(self):
        self.write(".github/workflows/gate.yml", "on: pull_request  # comment\njobs:\n  gate:\n    name: Project's Gate  # comment\n"
                   "    runs-on: x\n  quoted:\n    name: 'it''s # here'  # comment\n    runs-on: x\n")
        gate = {entry["path"]: entry for entry in self.facts()["workflows"]}[".github/workflows/gate.yml"]
        self.assertEqual(gate["on"], ["pull_request"])
        self.assertEqual([(job["id"], job["name"]) for job in gate["jobs"]], [("gate", "Project's Gate"), ("quoted", "it's # here")])

    def test_a_markdown_rule_named_after_secrets_is_read(self):
        self.write(".claude/rules/no-secrets.md", "Keep `docs/none.md` out.\n")
        self.write(".claude/commands/rotate-token.md", "Rotate.\n")
        self.write(".claude/rules/secret-token.json", "FIXTURE-SECRET-OUTSIDE\n")
        self.write(".claude/rules/.env.md", "FIXTURE-SECRET-OUTSIDE\n")
        facts = self.facts()
        files = self.files(facts)
        self.assertEqual(files[".claude/rules/no-secrets.md"]["kind"], "instructions")
        self.assertEqual(files[".claude/commands/rotate-token.md"]["kind"], "command")
        skipped = {entry["path"]: entry["why"] for entry in facts["skipped"]}
        self.assertEqual(skipped[".claude/rules/secret-token.json"], "looks like a credential, not read")
        self.assertEqual(skipped[".claude/rules/.env.md"], "looks like a credential, not read")

    def test_code_owners_not_utf8_and_names_in_where_that_are_not_paths(self):
        self.write(".github/CODEOWNERS", b"* @fixture-owner\n/caf\xe9/ @fixture-owner\n")
        self.write("register.json", json.dumps({"instructions": "AGENTS.md", "adopted": [
            {"key": "a", "where": "`python3 checks/generate.py --check`, run in `owner/repo`, and `checks/gone.py`"}], "own": []}))
        owners = self.facts()["code_owners"]
        self.assertEqual(owners["lines"], [])
        self.assertEqual(owners["note"], ".github/CODEOWNERS: not UTF-8 at byte 21, its lines are not read")
        self.assertEqual(owners["register_names"], [["AGENTS.md", True], ["checks/gone.py", False]])

    def test_options_that_say_nothing(self):
        for args in (["--uses", ""], ["--uses", " , "], ["--home", self.home]):
            with self.subTest(args=args):
                code, out, err = self.run_inventory(self.repo, *args)
                self.assertEqual(code, 2, out + err)
                self.assertEqual(out, "")
        only = self.scratch()
        self.write("CLAUDE.md", "One.\n", top=only)
        code, out, err = self.run_inventory(only)
        self.assertEqual(code, 0, out + err)
        self.assertIn("The agent layer: 1 file\n", out)

    # --- The review of #119 at d2d3677: one guarded reader for every file, and a workflow reader that fails closed. ---

    def test_an_export_through_a_linked_folder_is_refused(self):
        data = self.fixture_bytes("inventory/ruleset/ruleset.json").replace(b"protect-main", b"FIXTURE-SECRET-OUTSIDE")
        outside = os.path.realpath(self.scratch())
        self.write("export.json", data, top=outside)
        here = os.path.realpath(self.scratch())
        os.symlink(outside, os.path.join(here, "linked-directory"))
        os.makedirs(os.path.join(here, "real"))
        os.symlink(outside, os.path.join(here, "real", "deeper"))
        for path, cwd, part in (("linked-directory/export.json", here, "linked-directory"),
                                (os.path.join(here, "linked-directory", "export.json"), None, "linked-directory"),
                                ("./real/deeper/export.json", here, "real/deeper"),
                                ("real/../linked-directory/export.json", here, "linked-directory")):
            with self.subTest(path=path):
                code, out, err = self.run_inventory(self.repo, "--ruleset", path, cwd=cwd)
                self.assertEqual(code, 2, out + err)
                self.assertEqual(out, "")
                self.assertIn("%s on its path is a link, not followed" % part, err)
                self.assertNotIn("FIXTURE-SECRET-OUTSIDE", out + err)
        # The same file, given without a link on its path, is read.
        code, out, err = self.run_inventory(self.repo, "--json", "--ruleset", "export.json", cwd=outside)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(json.loads(out)["rulesets"][0]["name"], "FIXTURE-SECRET-OUTSIDE")

    def test_a_path_named_through_a_link_is_not_looked_at(self):
        outside = self.scratch()
        self.write("present.md", "FIXTURE-SECRET-OUTSIDE\n", top=outside)
        os.symlink(outside, os.path.join(self.repo, "linked"))
        self.write("CLAUDE.md", "See `linked/present.md`, `linked/absent.md` and [x](linked/also.md).\n")
        self.write("register.json", json.dumps({"instructions": "linked/present.md", "adopted": [], "own": []}))
        facts = self.facts()
        self.assertFalse([entry for entry in facts["missing_paths"] if entry["path"].startswith("linked/")])
        self.assertEqual(facts["code_owners"]["register_names"], [["linked/present.md", None]])
        self.assertIn("linked/present.md (through a link, not looked at)", self.text())

    def test_every_open_walk_and_listing_goes_through_the_guarded_reader(self):
        with open(SCRIPT, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        forbidden_os = {"open", "fdopen", "walk", "fwalk", "listdir", "scandir", "readlink", "stat", "lstat", "access",
                        "chdir"}
        forbidden_path = {"exists", "lexists", "isdir", "isfile", "islink", "realpath", "getsize", "samefile", "getmtime"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
                # A name imported from a module could be called without "os." in front: none is.
                self.assertNotIn(node.module, ("os", "os.path", "io", "builtins"))
        self.assertFalse(imported & {"glob", "pathlib", "shutil", "io", "codecs", "fileinput", "tempfile", "mmap"})

        def offending(node):
            func = node.func
            if isinstance(func, ast.Name) and func.id in ("open", "exec", "eval", "compile", "__import__"):
                return func.id
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name) and func.value.id == "os" and func.attr in forbidden_os:
                    return "os." + func.attr
                if (isinstance(func.value, ast.Attribute) and func.value.attr == "path" and isinstance(func.value.value, ast.Name)
                        and func.value.value.id == "os" and func.attr in forbidden_path):
                    return "os.path." + func.attr
            return None

        found = []

        def visit(node, function):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function = node.name
            if isinstance(node, ast.Call):
                name = offending(node)
                if name is not None and not (function or "").startswith("guarded_"):
                    found.append("%s at line %d in %s" % (name, node.lineno, function or "the module"))
            for child in ast.iter_child_nodes(node):
                visit(child, function)

        visit(tree, None)
        self.assertEqual(found, [])
        # The guarded helpers exist and use what they guard: the sweep is not empty by accident.
        helpers = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("guarded_")}
        self.assertTrue({"guarded_read", "guarded_walk", "guarded_entries", "guarded_look", "guarded_read_link"} <= helpers, helpers)

    def workflow(self, text, name="odd.yml", *args):
        self.write(".github/workflows/" + name, text)
        facts = self.facts(*args)
        return {entry["path"]: entry for entry in facts["workflows"]}[".github/workflows/" + name], facts

    def test_a_trigger_list_at_column_zero_is_read(self):
        text = "on:\n- pull_request\n- push\njobs:\n  extra:\n    runs-on: x\n"
        workflow, facts = self.workflow(text, "listed.yml", "--ruleset", self.ruleset("ruleset"))
        self.assertEqual((workflow["on"], workflow["unread"]), (["pull_request", "push"], None))
        self.assertIn({"path": ".github/workflows/listed.yml", "job": "extra", "name": None}, facts["not_required"])
        # As PyYAML writes it, with the key quoted.
        workflow, _ = self.workflow("'on':\n- pull_request\njobs:\n  extra:\n    runs-on: x\n", "dumped.yml")
        self.assertEqual((workflow["on"], workflow["unread"]), (["pull_request"], None))

    def test_odd_but_valid_trigger_forms_are_read_or_named_as_not_read(self):
        jobs = "jobs:\n  extra:\n    runs-on: x\n"
        read = {
            "on:  # the events\n  pull_request:\n  push:\n": ["pull_request", "push"],
            "on:\n  - pull_request  # one\n  # a comment between items\n\n  - push\n": ["pull_request", "push"],
            "on:\n- pull_request\n# a comment\n- 'push'\n": ["pull_request", "push"],
            "---\non: [pull_request, push]  # trailing\n": ["pull_request", "push"],
            "on: \"pull_request\"\n": ["pull_request"],
            "on:\n  pull_request:\n    branches: [main]\n  workflow_dispatch:\n": ["pull_request", "workflow_dispatch"],
        }
        not_read = (
            "on: &triggers\n  pull_request:\n",
            "on:\n  - &event pull_request\n",
            "on: *triggers\n",
            "on:\n  <<: *triggers\n",
            "on:\n",
            "on: {pull_request: {}}\n",
            "on: [pull_request, {push: {}}]\n",
            "on:\n  - pull_request:\n      branches: [main]\n",
            "on:\n  - pull_request\n  push:\n",
            "on:\n    pull_request:\n  push:\n",
            "on:\n  - pull\n    request\n",
            "on: !!str pull_request\n",
            "on: pull request\n",
            "? on\n: pull_request\n",
            "on: pull_request\non: push\n",
            "on: pull_request\n  stray: line\n",
            "{\"on\": \"pull_request\"}\n",
        )
        for number, (text, events) in enumerate(sorted(read.items())):
            with self.subTest(text=text):
                workflow, _ = self.workflow(text + jobs, "read-%d.yml" % number)
                self.assertEqual((workflow["on"], workflow["unread"]), (events, None))
        for number, text in enumerate(not_read):
            with self.subTest(text=text):
                workflow, facts = self.workflow(text + jobs, "unread-%d.yml" % number, "--ruleset", self.ruleset("ruleset"))
                self.assertTrue(workflow["unread"], workflow)
                path = ".github/workflows/unread-%d.yml" % number
                self.assertFalse([entry for entry in facts["not_required"] if entry["path"] == path])
                # Its jobs are listed under their own heading, or, when the whole file was not read, the file is.
                known = [entry for entry in facts["not_known"] if entry["path"] == path]
                self.assertIn(known, ([{"path": path, "job": "extra", "name": None, "required": False}],
                                      [{"path": path, "job": None, "name": None, "required": None}]))

    def test_jobs_in_a_form_it_does_not_read_are_named_as_not_read(self):
        cases = (
            "on: pull_request\njobs:\n- extra\n",
            "on: pull_request\njobs:\n  extra:\n    <<: *base\n    runs-on: x\n",
            "on: pull_request\njobs:\n  extra: {runs-on: x}\n",
            "on: pull_request\njobs:\n  extra:\n    name: >-\n      Run checks\n    runs-on: x\n",
            "on: pull_request\njobs:\n  extra:\n    name: Run\n      checks\n    runs-on: x\n",
            "on: pull_request\njobs:\n    extra:\n      runs-on: x\n  other:\n    runs-on: x\n",
            "on: pull_request\njobs:\n",
            "on: pull_request\n",
        )
        for number, text in enumerate(cases):
            with self.subTest(text=text):
                workflow, facts = self.workflow(text, "jobs-%d.yml" % number, "--ruleset", self.ruleset("ruleset"))
                self.assertTrue(workflow["unread"], workflow)
                path = ".github/workflows/jobs-%d.yml" % number
                self.assertFalse([entry for entry in facts["not_required"] if entry["path"] == path])
                self.assertTrue([entry for entry in facts["not_known"] if entry["path"] == path], facts["not_known"])

    def test_a_workflow_not_read_lists_its_jobs_under_their_own_heading(self):
        self.write(".github/workflows/anchored.yml", "on: &t\n  pull_request:\njobs:\n  gate:\n    name: Gate\n    runs-on: x\n")
        self.write(".github/workflows/latin.yml", b"on: pull_request\nname: caf\xe9\njobs:\n  gate:\n    runs-on: x\n")
        self.write(".github/workflows/big.yml", "on: pull_request\n" + "#" * 1000001 + "\n")
        facts = self.facts("--ruleset", self.ruleset("ruleset"))
        known = sorted((entry["path"], entry["job"]) for entry in facts["not_known"])
        self.assertEqual(known, [(".github/workflows/anchored.yml", "gate"), (".github/workflows/big.yml", None),
                                 (".github/workflows/latin.yml", None)])
        workflows = {entry["path"]: entry for entry in facts["workflows"]}
        self.assertEqual(workflows[".github/workflows/big.yml"]["unread"], "larger than 1000000 bytes, not read")
        out = self.text("--ruleset", self.ruleset("ruleset"))
        self.assertIn("Jobs of workflows this reader could not read: it cannot tell whether they run on a pull request", out)
        self.assertIn('.github/workflows/anchored.yml: gate ("Gate"), not required', out)
        self.assertIn(".github/workflows/big.yml: its jobs were not read", out)
        # Without an export, the heading is there too.
        self.assertIn('.github/workflows/anchored.yml: gate ("Gate")\n', self.text())

    def test_settings_not_utf8_is_named_and_not_read_for_hooks(self):
        self.write(".claude/settings.local.json", b'{"note": "caf\xe9 .claude/hooks/old.sh"}\n')
        unused = {entry["path"]: entry["why"] for entry in self.facts()["look_unused"]}
        self.assertEqual(unused[".claude/hooks/old.sh"],
                         "a hook that no settings file names; .claude/settings.local.json is not UTF-8 at byte 13 and was not read for hooks")

    def test_this_repo(self):
        code, out, err = self.run_inventory(ROOT, "--json", "--uses", "claude,codex", home=self.scratch())
        self.assertEqual(code, 0, out + err)
        facts = json.loads(out)
        files = self.files(facts)
        self.assertEqual(files["AGENTS.md"]["kind"], "instructions")
        workflows = {entry["path"]: entry for entry in facts["workflows"]}
        self.assertEqual([job["id"] for job in workflows[".github/workflows/checks.yml"]["jobs"]], ["checks"])
        # The fixture repos under checks/fixtures/ hold AGENTS.md and CLAUDE.md too, as instruction files at depth.
        self.assertEqual(files["checks/fixtures/inventory/repo/AGENTS.md"]["kind"], "instructions")


if __name__ == "__main__":
    unittest.main()
