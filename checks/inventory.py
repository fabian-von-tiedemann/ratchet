#!/usr/bin/env python3
"""The inventory: list a repo's agent layer as it stands, read only.

    python3 checks/inventory.py [ROOT] [--global] [--home DIR] [--uses claude,codex] [--ruleset FILE]... [--json]

It lists the files that make up the agent layer under ROOT (by default the folder it runs in), and, with --global,
the user's own layer under the home folder: instruction files at any depth, skills, commands, agents, hooks,
settings, MCP config, workflows, pull request and issue templates, the code owners file and the register. For each
it names the kind and the harnesses that load it, from the table KINDS below. It then lists facts, never a judgment:

- files with the same content, and skills, commands and agents with the same name
- with --uses, the files that no harness in use loads, such as a session prompt for a harness the project left
- files that look unused: a hook no settings file names, a skill folder without SKILL.md, an empty file, a file in
  a harness's folder of a kind this inventory does not know
- the paths an instruction file names that do not exist
- the jobs of each workflow, and, given the exported ruleset or branch protection with --ruleset, the jobs that run
  on a pull request and are not required, the required checks no job names, and what the export says of required
  review and bypass
- the lines of the code owners file beside the files the register names, for the owner to compare

It writes nothing, reaches no network and runs no program. It reads only under the paths it is given, follows no
link and reports each one, and does not read a file whose name looks like a credential: it names it as skipped. It
prints names and short facts, never what a file holds: from settings and MCP config only the names of hook events
and servers. Judging what each part means is the agent's job, on this output, and its result is a proposal to the
owner (D-2026-11-21-inventory-and-easy-upgrade, D-2026-11-22-second-redraw).

Exit code 0 when it ran, 2 when it could not. Standard library only. Run on Python 3.9 and 3.12.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True

import argparse
import fnmatch
import hashlib
import json
import os
import re
import stat
import unicodedata

import registry

# The harnesses whose files this inventory knows. "github" and "ratchet" are not harnesses: their files are read by
# the host and by Ratchet's checks, whichever harness is in use.
HARNESSES = ("claude", "codex", "gemini", "cursor", "copilot", "windsurf", "cline")
HOSTS = ("github", "ratchet")

# Instruction files by name, at any depth of the repo: the harnesses that load each, as of 2026-11.
INSTRUCTION_NAMES = {
    "CLAUDE.md": ("claude",),
    "CLAUDE.local.md": ("claude",),
    "AGENTS.md": ("codex", "copilot", "cursor", "windsurf"),
    "AGENTS.override.md": ("codex",),
    "GEMINI.md": ("gemini",),
}

# The rest of the repo's layer: (pattern of the path from the root, kind, harnesses). "**" stands for any number of
# folders, "*" for one part of a name. The first pattern that matches gives the kind.
KINDS = (
    (".claude/CLAUDE.md", "instructions", ("claude",)),
    (".claude/rules/**/*.md", "instructions", ("claude",)),
    (".claude/settings.json", "settings", ("claude",)),
    (".claude/settings.local.json", "settings", ("claude",)),
    (".claude/skills/*/SKILL.md", "skill", ("claude",)),
    (".claude/skills/*/**/*", "skill file", ("claude",)),
    (".claude/commands/**/*.md", "command", ("claude",)),
    (".claude/agents/**/*.md", "agent", ("claude",)),
    (".claude/hooks/**/*", "hook", ("claude",)),
    (".claude/output-styles/**/*.md", "output style", ("claude",)),
    (".claude/ratchet-approvals.json", "approvals", ("ratchet",)),
    (".mcp.json", "mcp", ("claude",)),
    (".agents/skills/*/SKILL.md", "skill", ("codex",)),
    (".agents/skills/*/**/*", "skill file", ("codex",)),
    (".codex/config.toml", "settings", ("codex",)),
    (".gemini/settings.json", "settings", ("gemini",)),
    (".gemini/commands/**/*.toml", "command", ("gemini",)),
    (".cursorrules", "instructions", ("cursor",)),
    (".cursor/rules/**/*.mdc", "instructions", ("cursor",)),
    (".cursor/rules/**/*.md", "instructions", ("cursor",)),
    (".cursor/commands/**/*.md", "command", ("cursor",)),
    (".cursor/mcp.json", "mcp", ("cursor",)),
    (".cursor/hooks.json", "hooks", ("cursor",)),
    (".windsurfrules", "instructions", ("windsurf",)),
    (".windsurf/rules/**/*.md", "instructions", ("windsurf",)),
    (".clinerules", "instructions", ("cline",)),
    (".clinerules/**/*", "instructions", ("cline",)),
    (".github/copilot-instructions.md", "instructions", ("copilot",)),
    (".github/instructions/**/*.instructions.md", "instructions", ("copilot",)),
    (".github/prompts/**/*.prompt.md", "command", ("copilot",)),
    (".github/agents/**/*.md", "agent", ("copilot",)),
    (".vscode/mcp.json", "mcp", ("copilot",)),
    (".github/workflows/*.yml", "workflow", ("github",)),
    (".github/workflows/*.yaml", "workflow", ("github",)),
    (".github/pull_request_template.md", "pr template", ("github",)),
    (".github/PULL_REQUEST_TEMPLATE.md", "pr template", ("github",)),
    (".github/PULL_REQUEST_TEMPLATE/**/*", "pr template", ("github",)),
    ("pull_request_template.md", "pr template", ("github",)),
    ("PULL_REQUEST_TEMPLATE.md", "pr template", ("github",)),
    ("docs/pull_request_template.md", "pr template", ("github",)),
    ("docs/PULL_REQUEST_TEMPLATE.md", "pr template", ("github",)),
    (".github/ISSUE_TEMPLATE/**/*", "issue template", ("github",)),
    (".github/CODEOWNERS", "code owners", ("github",)),
    ("CODEOWNERS", "code owners", ("github",)),
    ("docs/CODEOWNERS", "code owners", ("github",)),
    ("register.json", "register", ("ratchet",)),
    ("REGISTER.md", "register", ("ratchet",)),
)

# The user's global layer, under the home folder, with --global.
GLOBAL_KINDS = (
    (".claude/CLAUDE.md", "instructions", ("claude",)),
    (".claude/rules/**/*.md", "instructions", ("claude",)),
    (".claude/settings.json", "settings", ("claude",)),
    (".claude/skills/*/SKILL.md", "skill", ("claude",)),
    (".claude/skills/*/**/*", "skill file", ("claude",)),
    (".claude/commands/**/*.md", "command", ("claude",)),
    (".claude/agents/**/*.md", "agent", ("claude",)),
    (".claude/hooks/**/*", "hook", ("claude",)),
    (".claude/output-styles/**/*.md", "output style", ("claude",)),
    (".codex/AGENTS.md", "instructions", ("codex",)),
    (".codex/AGENTS.override.md", "instructions", ("codex",)),
    (".codex/config.toml", "settings", ("codex",)),
    (".codex/prompts/**/*.md", "command", ("codex",)),
    (".codex/skills/*/SKILL.md", "skill", ("codex",)),
    (".codex/skills/*/**/*", "skill file", ("codex",)),
    (".agents/skills/*/SKILL.md", "skill", ("codex",)),
    (".agents/skills/*/**/*", "skill file", ("codex",)),
    (".gemini/GEMINI.md", "instructions", ("gemini",)),
    (".gemini/settings.json", "settings", ("gemini",)),
    (".gemini/commands/**/*.toml", "command", ("gemini",)),
)

# The folders of the repo that belong to a harness: every file in them is listed, of a kind it knows or not. The
# folder of the host, .github, is walked for the kinds above only.
HARNESS_FOLDERS = {".claude": "claude", ".agents": "codex", ".codex": "codex", ".gemini": "gemini", ".cursor": "cursor",
                   ".windsurf": "windsurf", ".clinerules": "cline"}
# The folders of the global layer that are walked, each in full, and the folders whose own entries are only looked
# at, for the files of a kind above and the names that look like a credential. Nothing else under home is read.
GLOBAL_WALKED = (".claude/rules", ".claude/skills", ".claude/commands", ".claude/agents", ".claude/hooks",
                 ".claude/output-styles", ".codex/prompts", ".codex/skills", ".agents/skills", ".gemini/commands")
GLOBAL_LOOKED_AT = (".claude", ".codex", ".gemini")
GLOBAL_FILES = (".claude.json",)
# Folders the walk of the repo does not enter.
NOT_ENTERED = {".git", "node_modules"}
NOT_ENTERED_PATHS = {".claude/worktrees"}

# A name that looks like a credential. Such a file is named and never read.
CREDENTIAL_NAMES = ("*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.jks", ".env", ".env.*", "*.env", ".netrc",
                    ".npmrc", ".pypirc", "id_rsa*", "id_ecdsa*", "id_ed25519*", "id_dsa*", "*credential*", "*secret*",
                    "*token*", "auth.json", "oauth_creds.json", ".claude.json", "*.kdbx")

MAX_BYTES = 1000000

# A path named in an instruction file: the target of a Markdown link, a span in backticks, or an import @path.
LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SPAN = re.compile(r"`([^`\s]+)`")
IMPORT = re.compile(r"(?:^|\s)@([A-Za-z0-9_.~/-]+)")
EXTENSIONS = {"md", "mdc", "json", "py", "sh", "yml", "yaml", "toml", "txt", "js", "mjs", "ts", "html", "cfg", "ini",
              "lock", "xml", "csv", "sql", "rb", "go", "rs", "java"}
PATH_CHARACTERS = re.compile(r"^[A-Za-z0-9_.~/@+-]+\Z")
URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
LINE_SUFFIX = re.compile(r":[0-9]+(?:[:-][0-9]+)?\Z")

PULL_REQUEST_EVENTS = {"pull_request", "pull_request_target", "merge_group"}


class Fault(Exception):
    """The inventory cannot run."""


def shown(value):
    """A name as text on one line: a backslash, a control character and a character that is not text escaped."""
    out = []
    for char in value:
        if char == "\\":
            out.append("\\\\")
        elif char == "\n":
            out.append("\\n")
        elif char == "\t":
            out.append("\\t")
        elif unicodedata.category(char)[0] in ("C", "Z") and char != " ":
            point = ord(char)
            out.append("\\x%02x" % point if point < 0x100 else "\\u%04x" % point if point < 0x10000 else "\\U%08x" % point)
        else:
            out.append(char)
    return "".join(out)


def matches(pattern, path):
    """Whether a path, with / between its parts, matches a pattern of KINDS."""
    return _match(pattern.split("/"), path.split("/"))


def _match(pattern, parts):
    if not pattern:
        return not parts
    if pattern[0] == "**":
        return any(_match(pattern[1:], parts[skip:]) for skip in range(len(parts) + 1))
    return bool(parts) and fnmatch.fnmatchcase(parts[0], pattern[0]) and _match(pattern[1:], parts[1:])


def classify(rel, kinds, by_name):
    """(kind, harnesses) for a path from the root of its layer, or None for a file of no kind this inventory knows."""
    for pattern, kind, harnesses in kinds:
        if matches(pattern, rel):
            return kind, harnesses
    if by_name:
        name = rel.rsplit("/", 1)[-1]
        if name in INSTRUCTION_NAMES:
            return "instructions", INSTRUCTION_NAMES[name]
    return None


def looks_like_credential(name):
    lowered = name.lower()
    return any(fnmatch.fnmatchcase(lowered, pattern) for pattern in CREDENTIAL_NAMES)


def read_file(path):
    """The bytes of a regular file, never through a link: (data, None), or (None, why it was not read)."""
    try:
        handle = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError as error:
        return None, "could not be read: %s" % (error.strerror or error)
    try:
        status = os.fstat(handle)
        if not stat.S_ISREG(status.st_mode):
            return None, "not a regular file, not read"
        if status.st_size > MAX_BYTES:
            return None, "larger than %d bytes, not read" % MAX_BYTES
        chunks, total = [], 0
        while True:
            chunk = os.read(handle, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                return None, "larger than %d bytes, not read" % MAX_BYTES
            chunks.append(chunk)
        return b"".join(chunks), None
    finally:
        os.close(handle)


class Layer:
    """One root that is walked: the repo, or the home folder for the global layer."""

    def __init__(self, name, top, prefix):
        self.name = name
        self.top = os.path.abspath(top)
        self.prefix = prefix

    def shown_path(self, rel):
        return self.prefix + rel


class Inventory:
    def __init__(self):
        self.files = []
        self.skipped = []
        self.links = []
        self.data = {}

    def add_link(self, layer, rel, full):
        if any(link["path"] == layer.shown_path(rel) for link in self.links):
            return
        try:
            target = os.readlink(full)
        except OSError as error:
            self.skipped.append({"path": layer.shown_path(rel), "why": "a link that could not be read: %s" % error})
            return
        resolved = os.path.normpath(os.path.join(os.path.dirname(full), target))
        inside = resolved == layer.top or resolved.startswith(layer.top.rstrip(os.sep) + os.sep)
        self.links.append({"path": layer.shown_path(rel), "target": target, "inside": inside})

    def add_file(self, layer, rel, full, kind, harnesses):
        name = rel.rsplit("/", 1)[-1]
        path = layer.shown_path(rel)
        if looks_like_credential(name):
            self.skipped.append({"path": path, "why": "looks like a credential, not read"})
            return
        entry = {"path": path, "layer": layer.name, "kind": kind, "harnesses": list(harnesses), "rel": rel, "facts": []}
        data, why = read_file(full)
        if why is not None:
            # A file too large or that could not be read stays in the layer, unread. Anything else is not a file.
            self.skipped.append({"path": path, "why": why})
            if why == "not a regular file, not read":
                return
            entry["bytes"] = None
            entry["sha256"] = None
        else:
            entry["bytes"] = len(data)
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            self.data[path] = data
        self.files.append(entry)

    def walk_repo(self, layer):
        for folder, folders, names in os.walk(layer.top, topdown=True, followlinks=False):
            rel_folder = os.path.relpath(folder, layer.top).replace(os.sep, "/")
            rel_folder = "" if rel_folder == "." else rel_folder + "/"
            kept = []
            for name in sorted(folders):
                rel = rel_folder + name
                full = os.path.join(folder, name)
                if os.path.islink(full):
                    if self.in_layer(rel):
                        self.add_link(layer, rel, full)
                    continue
                if name in NOT_ENTERED or rel in NOT_ENTERED_PATHS:
                    if rel in NOT_ENTERED_PATHS:
                        self.skipped.append({"path": layer.shown_path(rel), "why": "a folder of worktrees, not walked"})
                    continue
                kept.append(name)
            folders[:] = kept
            for name in sorted(names):
                rel = rel_folder + name
                full = os.path.join(folder, name)
                if os.path.islink(full):
                    if self.in_layer(rel):
                        self.add_link(layer, rel, full)
                    continue
                found = classify(rel, KINDS, by_name=True)
                harness_folder = HARNESS_FOLDERS.get(rel.split("/", 1)[0]) if "/" in rel else None
                if found is None and harness_folder is None:
                    continue
                kind, harnesses = found if found is not None else ("unknown", (harness_folder,))
                self.add_file(layer, rel, full, kind, harnesses)

    def in_layer(self, rel):
        """Whether a link at rel stands where the repo's layer is: in a harness's folder, or where a kind is."""
        first = rel.split("/", 1)[0]
        return first in HARNESS_FOLDERS or first == ".github" or classify(rel, KINDS, by_name=True) is not None

    def walk_global(self, layer):
        for rel in GLOBAL_FILES:
            full = os.path.join(layer.top, rel)
            if os.path.lexists(full):
                self.skipped.append({"path": layer.shown_path(rel), "why": "looks like a credential, not read"})
        for top in GLOBAL_LOOKED_AT:
            full_top = os.path.join(layer.top, top)
            if os.path.islink(full_top):
                self.add_link(layer, top, full_top)
                continue
            try:
                names = sorted(os.listdir(full_top))
            except OSError:
                continue
            for name in names:
                rel = top + "/" + name
                full = os.path.join(full_top, name)
                if os.path.islink(full):
                    if classify(rel, GLOBAL_KINDS, by_name=False) is not None or rel in GLOBAL_WALKED:
                        self.add_link(layer, rel, full)
                    continue
                if os.path.isdir(full):
                    continue
                found = classify(rel, GLOBAL_KINDS, by_name=False)
                if found is not None:
                    self.add_file(layer, rel, full, *found)
                elif looks_like_credential(name):
                    self.skipped.append({"path": layer.shown_path(rel), "why": "looks like a credential, not read"})
        for top in GLOBAL_WALKED:
            full_top = os.path.join(layer.top, *top.split("/"))
            if os.path.islink(full_top):
                self.add_link(layer, top, full_top)
                continue
            if not os.path.isdir(full_top):
                continue
            for folder, folders, names in os.walk(full_top, topdown=True, followlinks=False):
                rel_folder = os.path.relpath(folder, layer.top).replace(os.sep, "/") + "/"
                kept = []
                for name in sorted(folders):
                    full = os.path.join(folder, name)
                    if os.path.islink(full):
                        self.add_link(layer, rel_folder + name, full)
                    else:
                        kept.append(name)
                folders[:] = kept
                for name in sorted(names):
                    rel = rel_folder + name
                    full = os.path.join(folder, name)
                    if os.path.islink(full):
                        self.add_link(layer, rel, full)
                        continue
                    found = classify(rel, GLOBAL_KINDS, by_name=False)
                    if found is None:
                        if looks_like_credential(name):
                            self.skipped.append({"path": layer.shown_path(rel), "why": "looks like a credential, not read"})
                        continue
                    self.add_file(layer, rel, full, *found)


def json_facts(data, kind):
    """The names of hook events and of MCP servers in a settings or MCP file: short facts, never a value."""
    try:
        value = registry.parse_json(data)
    except registry.RegistryError as error:
        return [str(error)]
    if not isinstance(value, dict):
        return ["not a JSON object"]
    facts = []
    hooks = value.get("hooks")
    if isinstance(hooks, dict) and hooks:
        counts = []
        for event in sorted(hooks):
            groups = hooks[event]
            number = 0
            if isinstance(groups, list):
                for group in groups:
                    inner = group.get("hooks") if isinstance(group, dict) else None
                    number += len(inner) if isinstance(inner, list) else 1
            counts.append("%s (%d)" % (shown(event), number))
        facts.append("hooks on " + ", ".join(counts))
    for field in ("mcpServers", "servers"):
        servers = value.get(field)
        if isinstance(servers, dict) and servers:
            facts.append("servers: " + ", ".join(shown(name) for name in sorted(servers)))
    if kind == "settings" and isinstance(value.get("contextFileName"), (str, list)):
        names = value["contextFileName"]
        names = [names] if isinstance(names, str) else [name for name in names if isinstance(name, str)]
        facts.append("context file names: " + ", ".join(shown(name) for name in names))
    return facts


def candidate(raw, kind):
    """The path a token names, or None when it does not look like a path of the repo."""
    value = raw.strip()
    if not value or URL.match(value) or value.startswith(("#", "<", "$", "/", "~", "-")):
        return None
    value = value.split("#", 1)[0].split("?", 1)[0]
    value = LINE_SUFFIX.sub("", value)
    if not value or not PATH_CHARACTERS.match(value) or "@" in value:
        return None
    last = value.rstrip("/").rsplit("/", 1)[-1]
    extension = last.rsplit(".", 1)[-1].lower() if "." in last.strip(".") else ""
    if kind == "link":
        return value
    if "/" not in value:
        # A bare name in backticks, such as `generate.py`, is a name: a path only in a link or an import.
        return value if kind == "import" else None
    if extension in EXTENSIONS or value.endswith("/"):
        return value
    return "?" + value


def named_paths(text):
    """Each (line, kind, path) an instruction file names."""
    found = []
    for number, line in enumerate(text.split("\n"), 1):
        for kind, pattern in (("link", LINK), ("span", SPAN), ("import", IMPORT)):
            for match in pattern.finditer(line):
                value = candidate(match.group(1), kind)
                if value is not None:
                    found.append((number, kind, value))
    return found


def within(top, path):
    path = os.path.normpath(path)
    return path == top or path.startswith(top.rstrip(os.sep) + os.sep)


def resolve_named(layer, rel, kind, value):
    """(exists, [full paths it may mean]) for a path an instruction file names, or None when it is not looked at."""
    tentative = value.startswith("?")
    value = value.lstrip("?")
    folder = os.path.dirname(os.path.join(layer.top, *rel.split("/")))
    # A link is read from the file's folder. Any other name may be from the file's folder or from the root.
    bases = [folder] if kind == "link" else [folder, layer.top]
    if tentative:
        # A word with a / and no extension, such as owner/repo, counts as a path only when its first part exists.
        first = value.split("/", 1)[0]
        bases = [base for base in bases if os.path.lexists(os.path.join(base, first))]
    places = [os.path.normpath(os.path.join(base, *value.split("/"))) for base in bases]
    places = [place for place in places if within(layer.top, place)]
    if not places:
        return None
    return any(os.path.lexists(place) for place in places), places


def inspect(inventory, layers):
    """Facts read from the files: names in settings, paths in instruction files, which files instruction files name."""
    missing = []
    named_by = {}
    for entry in inventory.files:
        data = inventory.data.get(entry["path"])
        if data is None:
            continue
        layer = layers[entry["layer"]]
        if entry["kind"] in ("settings", "mcp") and entry["rel"].endswith(".json"):
            entry["facts"] += json_facts(data, entry["kind"])
        if entry["kind"] != "instructions":
            continue
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            entry["facts"].append("not UTF-8 at byte %d: the paths it names are not read" % error.start)
            continue
        seen = set()
        for number, kind, value in named_paths(text):
            result = resolve_named(layer, entry["rel"], kind, value)
            if result is None:
                continue
            exists, places = result
            for place in places:
                named_by.setdefault(os.path.normpath(place), set()).add(entry["path"])
            if not exists and (number, value.lstrip("?")) not in seen:
                seen.add((number, value.lstrip("?")))
                missing.append({"file": entry["path"], "line": number, "path": value.lstrip("?")})
        count = len([item for item in missing if item["file"] == entry["path"]])
        if count:
            entry["facts"].append("names %d path%s that do%s not exist" % (count, "" if count == 1 else "s", "es" if count == 1 else ""))
    return missing, named_by


def same_content(inventory):
    groups = {}
    for entry in inventory.files:
        if entry.get("sha256") and entry["bytes"]:
            groups.setdefault(entry["sha256"], []).append(entry["path"])
    return sorted(sorted(paths) for paths in groups.values() if len(paths) > 1)


def name_of(entry):
    rel = entry["rel"]
    if entry["kind"] == "skill":
        return rel.split("/")[-2]
    if entry["kind"] == "command":
        parts = rel.split("/")
        under = parts[2:] if parts[1] in ("commands", "prompts") else parts[-1:]
        name = "/".join(under)
        for ending in (".prompt.md", ".md", ".toml"):
            if name.endswith(ending):
                return name[:-len(ending)]
        return name
    if entry["kind"] == "agent":
        name = rel.rsplit("/", 1)[-1]
        for ending in (".agent.md", ".md"):
            if name.endswith(ending):
                return name[:-len(ending)]
    return None


def same_name(inventory):
    groups = {}
    for entry in inventory.files:
        name = name_of(entry)
        if name is not None:
            groups.setdefault((entry["kind"], name), []).append(entry)
    result = []
    for (kind, name), entries in sorted(groups.items()):
        if len(entries) < 2:
            continue
        hashes = {entry.get("sha256") for entry in entries}
        result.append({"kind": kind, "name": name, "paths": sorted(entry["path"] for entry in entries),
                       "same_content": len(hashes) == 1 and None not in hashes})
    return result


def look_unused(inventory):
    unused = []
    settings_text = {}
    for entry in inventory.files:
        if entry["kind"] == "settings" and entry["path"] in inventory.data:
            settings_text.setdefault(entry["layer"], []).append(inventory.data[entry["path"]].decode("utf-8", errors="replace"))
    skill_folders = {}
    for entry in inventory.files:
        rel = entry["rel"]
        if entry["kind"] == "hook" and rel.startswith(".claude/hooks/"):
            texts = settings_text.get(entry["layer"], [])
            if not any(rel in text for text in texts):
                unused.append({"path": entry["path"], "why": "a hook that no settings file names"})
        if entry["kind"] in ("skill", "skill file"):
            parts = rel.split("/")
            folder = entry["path"][:len(entry["path"]) - len(rel)] + "/".join(parts[:3])
            skill_folders.setdefault(folder, False)
            if entry["kind"] == "skill":
                skill_folders[folder] = True
        if entry["bytes"] == 0:
            unused.append({"path": entry["path"], "why": "empty"})
        if entry["kind"] == "unknown":
            unused.append({"path": entry["path"], "why": "not a kind this inventory knows"})
    for folder, has_skill in sorted(skill_folders.items()):
        if not has_skill:
            unused.append({"path": folder, "why": "a skill folder without SKILL.md"})
    return sorted(unused, key=lambda item: item["path"])


def not_loaded(inventory, uses, named_by, layers):
    result = []
    for entry in inventory.files:
        harnesses = [name for name in entry["harnesses"] if name not in HOSTS]
        if not harnesses or set(harnesses) & set(uses):
            continue
        full = os.path.normpath(os.path.join(layers[entry["layer"]].top, *entry["rel"].split("/")))
        result.append({"path": entry["path"], "harnesses": harnesses,
                       "named_by": sorted(named_by.get(full, set()) - {entry["path"]})})
    return sorted(result, key=lambda item: item["path"])


# --- Workflows, read as far as their top-level keys, their jobs and each job's name. ---

KEY = re.compile(r"^( *)(\"[^\"]*\"|'[^']*'|[A-Za-z0-9_-]+)\s*:(.*)\Z")


def without_comment(line):
    """A line without a comment that starts at the line or after a space, outside quotes."""
    quote = None
    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or line[index - 1] in " \t"):
            return line[:index].rstrip()
    return line.rstrip()


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def workflow_facts(text):
    """{"on": [...], "jobs": [{"id", "name", "pull_request"}], "unread": why or None} for a workflow's text."""
    lines = [without_comment(line) for line in text.split("\n")]
    if any(line.startswith("\t") or "\t" in line[:len(line) - len(line.lstrip())] for line in lines):
        return {"on": [], "jobs": [], "unread": "indented with tabs, which this reader does not read"}
    triggers, jobs, unread = [], [], None
    index = 0
    while index < len(lines):
        match = KEY.match(lines[index])
        if not match or match.group(1):
            index += 1
            continue
        key, rest = unquote(match.group(2)), match.group(3).strip()
        children, index = block(lines, index + 1)
        if key == "on":
            if rest.startswith("["):
                triggers = [unquote(item) for item in rest.strip("[]").split(",") if item.strip()]
            elif rest:
                triggers = [unquote(rest)]
            else:
                triggers = [unquote(KEY.match(line).group(2)) for line in direct(children) if KEY.match(line)]
        elif key == "jobs":
            if rest:
                unread = "its jobs are in a form this reader does not read"
                continue
            for job_line, job_block in entries(children):
                job = {"id": unquote(KEY.match(job_line).group(2)), "name": None, "calls": False}
                for line in direct(job_block):
                    inner = KEY.match(line)
                    if inner and unquote(inner.group(2)) == "name":
                        job["name"] = unquote(inner.group(3))
                    if inner and unquote(inner.group(2)) == "uses":
                        job["calls"] = True
                jobs.append(job)
    return {"on": triggers, "jobs": jobs, "unread": unread}


def indent(line):
    return len(line) - len(line.lstrip(" "))


def block(lines, start):
    """The lines indented under the key before start, and the index after them."""
    end = start
    while end < len(lines) and (not lines[end].strip() or indent(lines[end]) > 0):
        end += 1
    return lines[start:end], end


def direct(lines):
    """The lines of a block at its first indent: the keys directly under its parent."""
    filled = [line for line in lines if line.strip()]
    if not filled:
        return []
    first = indent(filled[0])
    return [line[first:] for line in filled if indent(line) == first]


def entries(lines):
    """Each key directly under a block, with the lines under it, each moved left to the key's indent."""
    filled = [line for line in lines if line.strip()]
    if not filled:
        return []
    first = indent(filled[0])
    result = []
    for line in lines:
        if not line.strip():
            continue
        if indent(line) == first and KEY.match(line[first:]):
            result.append((line[first:], []))
        elif result and indent(line) > first:
            result[-1][1].append(line[first:])
    return result


# --- The exported ruleset or branch protection. ---

def expect(value, kinds, what):
    if not isinstance(value, kinds):
        names = {list: "a list", dict: "an object", str: "text", bool: "true or false", int: "a number"}
        kind = kinds[0] if isinstance(kinds, tuple) else kinds
        raise Fault("%s must be %s" % (what, names.get(kind, kind.__name__)))
    return value


def read_ruleset(path):
    """The facts of each ruleset or branch protection in an exported file."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_BYTES + 1)
    except OSError as error:
        raise Fault("%s: cannot read: %s" % (path, error.strerror or error))
    if len(data) > MAX_BYTES:
        raise Fault("%s: larger than %d bytes" % (path, MAX_BYTES))
    try:
        value = registry.parse_json(data)
    except registry.RegistryError as error:
        raise Fault("%s: %s" % (path, error))
    items = value if isinstance(value, list) else [value]
    result = []
    for item in items:
        try:
            if isinstance(item, dict) and "rules" in item:
                result.append(ruleset_facts(item))
            elif isinstance(item, dict) and set(item) & {"required_status_checks", "required_pull_request_reviews", "enforce_admins"}:
                result.append(protection_facts(item))
            else:
                raise Fault("neither a ruleset nor a branch protection, as GitHub exports them")
        except Fault as error:
            raise Fault("%s: %s" % (path, error))
    return result


def ruleset_facts(item):
    facts = {"form": "ruleset", "name": expect(item.get("name", ""), str, "name"),
             "target": expect(item.get("target", "branch"), str, "target"),
             "enforcement": expect(item.get("enforcement", "active"), str, "enforcement"),
             "include": [], "exclude": [], "required_checks": [], "up_to_date": None, "review": None,
             "bypass": [], "other_rules": [], "not_read": []}
    conditions = expect(item.get("conditions") or {}, dict, "conditions")
    ref_name = expect(conditions.get("ref_name") or {}, dict, "conditions.ref_name")
    for field in ("include", "exclude"):
        facts[field] = [expect(name, str, "conditions.ref_name.%s" % field) for name in expect(ref_name.get(field, []), list, "conditions.ref_name.%s" % field)]
    for rule in expect(item["rules"], list, "rules"):
        rule = expect(rule, dict, "a rule")
        if "type" not in rule:
            raise Fault("a rule without a type")
        kind = expect(rule["type"], str, "type")
        parameters = expect(rule.get("parameters") or {}, dict, "parameters of %s" % kind)
        if kind == "required_status_checks":
            for check in expect(parameters.get("required_status_checks", []), list, "required_status_checks"):
                facts["required_checks"].append(expect(expect(check, dict, "a required status check").get("context"), str, "context"))
            if "strict_required_status_checks_policy" in parameters:
                facts["up_to_date"] = expect(parameters["strict_required_status_checks_policy"], bool, "strict_required_status_checks_policy")
        elif kind == "pull_request":
            facts["review"] = {
                "approvals": expect(parameters.get("required_approving_review_count", 0), int, "required_approving_review_count"),
                "code_owner": expect(parameters.get("require_code_owner_review", False), bool, "require_code_owner_review"),
                "dismiss_stale": expect(parameters.get("dismiss_stale_reviews_on_push", False), bool, "dismiss_stale_reviews_on_push"),
                "last_push": expect(parameters.get("require_last_push_approval", False), bool, "require_last_push_approval"),
            }
        elif kind in ("deletion", "non_fast_forward", "creation", "update", "required_linear_history", "required_signatures"):
            facts["other_rules"].append(kind)
        else:
            facts["not_read"].append(kind)
    for actor in expect(item.get("bypass_actors") or [], list, "bypass_actors"):
        actor = expect(actor, dict, "a bypass actor")
        facts["bypass"].append("%s %s (%s)" % (expect(actor.get("actor_type", "?"), str, "actor_type"),
                                               actor.get("actor_id") if isinstance(actor.get("actor_id"), int) else "-",
                                               expect(actor.get("bypass_mode", "always"), str, "bypass_mode")))
    return facts


def protection_facts(item):
    facts = {"form": "branch protection", "name": "", "target": "branch", "enforcement": "active", "include": [],
             "exclude": [], "required_checks": [], "up_to_date": None, "review": None, "bypass": [], "other_rules": [],
             "not_read": []}
    checks = item.get("required_status_checks")
    if checks is not None:
        checks = expect(checks, dict, "required_status_checks")
        names = [expect(name, str, "contexts") for name in expect(checks.get("contexts", []), list, "contexts")]
        for check in expect(checks.get("checks", []), list, "checks"):
            name = expect(expect(check, dict, "a check").get("context"), str, "context")
            if name not in names:
                names.append(name)
        facts["required_checks"] = names
        if "strict" in checks:
            facts["up_to_date"] = expect(checks["strict"], bool, "strict")
    reviews = item.get("required_pull_request_reviews")
    if reviews is not None:
        reviews = expect(reviews, dict, "required_pull_request_reviews")
        facts["review"] = {
            "approvals": expect(reviews.get("required_approving_review_count", 0), int, "required_approving_review_count"),
            "code_owner": expect(reviews.get("require_code_owner_reviews", False), bool, "require_code_owner_reviews"),
            "dismiss_stale": expect(reviews.get("dismiss_stale_reviews", False), bool, "dismiss_stale_reviews"),
            "last_push": expect(reviews.get("require_last_push_approval", False), bool, "require_last_push_approval"),
        }
        allowances = expect(reviews.get("bypass_pull_request_allowances") or {}, dict, "bypass_pull_request_allowances")
        for field, key, label in (("users", "login", "user"), ("teams", "slug", "team"), ("apps", "slug", "app")):
            for actor in expect(allowances.get(field, []), list, field):
                name = expect(expect(actor, dict, "an allowance").get(key), str, key)
                facts["bypass"].append("%s %s (pull requests)" % (label, name))
    admins = item.get("enforce_admins")
    if admins is not None:
        enabled = expect(expect(admins, dict, "enforce_admins").get("enabled"), bool, "enforce_admins.enabled")
        if not enabled:
            facts["bypass"].append("administrators (enforce_admins is off)")
    for field in ("allow_force_pushes", "allow_deletions", "required_linear_history", "required_signatures", "lock_branch"):
        value = item.get(field)
        if isinstance(value, dict) and isinstance(value.get("enabled"), bool):
            facts["other_rules"].append("%s %s" % (field, "on" if value["enabled"] else "off"))
    return facts


def required_names(rulesets):
    """The checks required by the exports that GitHub enforces on branches."""
    names = []
    for facts in rulesets:
        if facts["enforcement"] == "active" and facts["target"] == "branch":
            for name in facts["required_checks"]:
                if name not in names:
                    names.append(name)
    return names


def contexts_of(job, required):
    """The required checks a job reports as: its id or its name, alone, with a matrix "(...)" or a called " / job".

    A name that is an expression is known only when the job runs, so only the id is compared."""
    names = [job["id"]] + ([job["name"]] if job["name"] and "${{" not in job["name"] else [])
    return [context for context in required
            if any(context == name or context.startswith(name + " (") or context.startswith(name + " / ") for name in names)]


def code_owners(inventory, layer):
    """The lines of the code owners file GitHub reads, and the files the register names."""
    owners_file, lines = None, []
    for rel in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        path = rel
        if path in inventory.data:
            owners_file = path
            text = inventory.data[path].decode("utf-8", errors="replace")
            for number, line in enumerate(text.split("\n"), 1):
                line = line.strip()
                if line and not line.startswith("#"):
                    lines.append([number, line])
            break
    names = []
    data = inventory.data.get("register.json")
    note = None
    if data is not None:
        try:
            register = registry.parse_json(data)
        except registry.RegistryError as error:
            register, note = None, "register.json: %s" % error
        if isinstance(register, dict):
            values = []
            if isinstance(register.get("instructions"), str):
                values.append(register["instructions"])
            for part in ("adopted", "own"):
                for row in register.get(part) or []:
                    if not isinstance(row, dict):
                        continue
                    if isinstance(row.get("stands_in"), str):
                        values.append(row["stands_in"])
                    if isinstance(row.get("where"), str):
                        for match in SPAN.finditer(row["where"]):
                            value = candidate(match.group(1), "span")
                            if value is not None:
                                values.append(value.lstrip("?"))
            for value in values:
                full = os.path.join(layer.top, *value.split("/"))
                if within(layer.top, full) and value not in [name for name, _ in names]:
                    names.append([value, os.path.lexists(full)])
    if owners_file is None and data is None:
        return None
    return {"file": owners_file, "lines": lines, "register_names": names, "note": note}


def build(args):
    root = args.root
    if not os.path.isdir(root):
        raise Fault("%s is not a directory" % root)
    uses = None
    if args.uses is not None:
        uses = [name.strip() for name in args.uses.split(",") if name.strip()]
        for name in uses:
            if name not in HARNESSES:
                raise Fault("unknown harness %r: the harnesses this inventory knows are %s" % (name, ", ".join(HARNESSES)))
        uses = sorted(set(uses))
    rulesets = []
    for path in args.ruleset or []:
        rulesets += read_ruleset(path)

    inventory = Inventory()
    layers = {"repo": Layer("repo", root, "")}
    inventory.walk_repo(layers["repo"])
    if args.use_global:
        home = args.home or os.path.expanduser("~")
        if not os.path.isdir(home):
            raise Fault("%s is not a directory" % home)
        layers["global"] = Layer("global", home, "~/")
        inventory.walk_global(layers["global"])
    inventory.files.sort(key=lambda entry: (entry["layer"] != "repo", entry["path"]))

    missing, named_by = inspect(inventory, layers)
    workflows = []
    required = required_names(rulesets)
    not_required = [] if rulesets else None
    produced = set()
    for entry in inventory.files:
        if entry["kind"] != "workflow" or entry["path"] not in inventory.data:
            continue
        try:
            text = inventory.data[entry["path"]].decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            workflows.append({"path": entry["path"], "on": [], "jobs": [], "unread": "not UTF-8 at byte %d" % error.start})
            continue
        facts = workflow_facts(text)
        on_pull_request = bool(set(facts["on"]) & PULL_REQUEST_EVENTS)
        jobs = []
        for job in facts["jobs"]:
            state = None
            if rulesets:
                matched = contexts_of(job, required)
                produced.update(matched)
                state = bool(matched)
                if not state and on_pull_request:
                    not_required.append({"path": entry["path"], "job": job["id"], "name": job["name"]})
            jobs.append({"id": job["id"], "name": job["name"], "required": state, "calls": job["calls"]})
        workflows.append({"path": entry["path"], "on": facts["on"], "jobs": jobs, "unread": facts["unread"]})

    harnesses_here = sorted({name for entry in inventory.files for name in entry["harnesses"] if name not in HOSTS})
    return {
        "root": root,
        "global": bool(args.use_global),
        "uses": uses,
        "harnesses_here": harnesses_here,
        "files": [{key: entry[key] for key in ("path", "layer", "kind", "harnesses", "bytes", "sha256", "facts")}
                  for entry in inventory.files],
        "skipped": sorted(inventory.skipped, key=lambda item: item["path"]),
        "links": sorted(inventory.links, key=lambda item: item["path"]),
        "same_content": same_content(inventory),
        "same_name": same_name(inventory),
        "not_loaded": None if uses is None else not_loaded(inventory, uses, named_by, layers),
        "look_unused": look_unused(inventory),
        "missing_paths": missing,
        "workflows": workflows,
        "rulesets": rulesets,
        "not_required": not_required,
        "required_without_job": None if not rulesets else [name for name in required if name not in produced],
        "code_owners": code_owners(inventory, layers["repo"]),
    }


def yes(value):
    return "yes" if value else "no"


def text_report(facts):
    out = []
    add = out.append
    add("inventory of %s" % shown(facts["root"]) + (", with the global layer" if facts["global"] else ""))
    add("")
    add("The agent layer: %d files" % len(facts["files"]))
    for entry in facts["files"]:
        line = "  %s  %s  %s" % (shown(entry["path"]), entry["kind"], ", ".join(entry["harnesses"]))
        if entry["facts"]:
            line += "  (" + "; ".join(entry["facts"]) + ")"
        add(line)
    add("Harnesses with files here: %s" % (", ".join(facts["harnesses_here"]) or "none"))

    def section(title, items):
        add("")
        add(title)
        if not items:
            add("  none")
        for item in items:
            add("  " + item)

    section("Skipped, not read", ["%s: %s" % (shown(item["path"]), item["why"]) for item in facts["skipped"]] +
            ["%s: a link to %s, %s the root, not followed" % (shown(item["path"]), shown(item["target"]),
                                                              "inside" if item["inside"] else "outside")
             for item in facts["links"]])
    section("Same content", [", ".join(shown(path) for path in group) for group in facts["same_content"]])
    section("Same name", ["%s %s: %s (%s content)" % (item["kind"], shown(item["name"]), ", ".join(shown(path) for path in item["paths"]),
                                                       "same" if item["same_content"] else "different")
                          for item in facts["same_name"]])
    if facts["uses"] is None:
        add("")
        add("Not loaded by a harness in use: give --uses with the harnesses the project uses to list them")
    else:
        section("Not loaded by a harness in use (--uses %s)" % ", ".join(facts["uses"]),
                ["%s: loaded by %s%s" % (shown(item["path"]), ", ".join(item["harnesses"]),
                                          "; named by " + ", ".join(shown(name) for name in item["named_by"]) if item["named_by"] else "")
                 for item in facts["not_loaded"]])
    section("Look unused", ["%s: %s" % (shown(item["path"]), item["why"]) for item in facts["look_unused"]])
    section("Paths named that do not exist", ["%s:%d names %s" % (shown(item["file"]), item["line"], shown(item["path"]))
                                              for item in facts["missing_paths"]])
    add("")
    add("Workflows")
    if not facts["workflows"]:
        add("  none")
    for workflow in facts["workflows"]:
        add("  %s, on %s" % (shown(workflow["path"]), ", ".join(shown(name) for name in workflow["on"]) or "nothing this reader found"))
        if workflow["unread"]:
            add("    %s" % workflow["unread"])
        for job in workflow["jobs"]:
            label = shown(job["id"]) + (' ("%s")' % shown(job["name"]) if job["name"] else "")
            state = {None: "", True: ": required", False: ": not required"}[job["required"]]
            add("    %s%s%s" % (label, state, ", calls a reusable workflow" if job["calls"] else ""))
    if facts["not_required"] is None:
        add("")
        add("Required checks: give --ruleset with the exported ruleset or branch protection of the default branch to see which jobs are required")
    else:
        section("Jobs that run on a pull request and are not required: they look like a gate and are not",
                ["%s: %s" % (shown(item["path"]), shown(item["job"]) + (' ("%s")' % shown(item["name"]) if item["name"] else ""))
                 for item in facts["not_required"]])
        section("Required checks that no job here names", [shown(name) for name in facts["required_without_job"]])
        add("")
        add("The exported rules")
        for item in facts["rulesets"]:
            title = "  %s%s, target %s, enforcement %s" % (item["form"], " " + shown(item["name"]) if item["name"] else "",
                                                          shown(item["target"]), shown(item["enforcement"]))
            if item["include"]:
                title += ", on " + ", ".join(shown(name) for name in item["include"])
            if item["exclude"]:
                title += ", not on " + ", ".join(shown(name) for name in item["exclude"])
            add(title)
            if item["enforcement"] != "active":
                add("    enforcement %s: GitHub does not enforce it" % shown(item["enforcement"]))
            review = item["review"]
            if review is None:
                add("    required review: none")
            else:
                add("    required review: %d approval%s, code owner review %s, stale reviews dismissed on push %s, last push approval %s"
                    % (review["approvals"], "" if review["approvals"] == 1 else "s", yes(review["code_owner"]),
                       yes(review["dismiss_stale"]), yes(review["last_push"])))
            add("    required checks: %s%s" % (", ".join(shown(name) for name in item["required_checks"]) or "none",
                                               "" if item["up_to_date"] is None else "; branch up to date: %s" % yes(item["up_to_date"])))
            add("    bypass: %s" % (", ".join(shown(name) for name in item["bypass"]) or "none"))
            if item["other_rules"]:
                add("    other rules: %s" % ", ".join(shown(name) for name in item["other_rules"]))
            if item["not_read"]:
                add("    rules not read: %s" % ", ".join(shown(name) for name in item["not_read"]))
    owners = facts["code_owners"]
    add("")
    add("Code owners, beside the files the register names")
    if owners is None:
        add("  no code owners file and no register.json")
    else:
        add("  %s" % (shown(owners["file"]) if owners["file"] else "no code owners file"))
        for number, line in owners["lines"]:
            add("    %d: %s" % (number, shown(line)))
        if owners["note"]:
            add("  %s" % shown(owners["note"]))
        add("  register.json names" if owners["register_names"] else "  register.json names no file")
        for name, exists in owners["register_names"]:
            add("    %s%s" % (shown(name), "" if exists else " (does not exist)"))
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="List a repo's agent layer as it stands. Reads only; writes nothing.")
    parser.add_argument("root", nargs="?", default=".", help="the root of the repo, by default the folder it runs in")
    parser.add_argument("--global", dest="use_global", action="store_true", help="also list the user's global layer under the home folder")
    parser.add_argument("--home", help="the home folder for --global, in place of HOME")
    parser.add_argument("--uses", help="the harnesses the project uses, separated by commas: %s" % ", ".join(HARNESSES))
    parser.add_argument("--ruleset", action="append", help="a ruleset or branch protection exported from the host, as JSON; may be given more than once")
    parser.add_argument("--json", action="store_true", help="print JSON in place of text")
    args = parser.parse_args(argv)
    try:
        facts = build(args)
    except Fault as error:
        print("inventory: cannot run: %s" % shown(str(error)), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(facts, indent=2, sort_keys=True))
    else:
        sys.stdout.write(text_report(facts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
