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

    def run_inventory(self, *args, home=None):
        environment = dict(os.environ)
        environment["HOME"] = home or self.home
        result = subprocess.run([sys.executable, SCRIPT] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, env=environment)
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
        return self.fixture_file("inventory/ruleset/%s.json" % name)

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
        self.assertEqual(ruleset["review"], {"approvals": 1, "code_owner": True, "dismiss_stale": True, "last_push": False})
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
        self.assertEqual(protection["review"], {"approvals": 2, "code_owner": False, "dismiss_stale": True, "last_push": False})
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
                code, out, err = self.run_inventory(self.repo, "--ruleset", self.fixture_file("inventory/faults/%s.json" % name))
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
