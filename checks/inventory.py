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

It writes nothing, reaches no network and runs no program. It reads only under the paths it is given, through one
guarded reader that refuses a link at any part of a path below its starting point, follows no link and reports each
one, and does not read a file whose name looks like a credential: it names it as skipped. Its workflow reader reads a
subset of YAML and names a workflow outside it as not read, with its jobs under a heading of their own. It
prints names and short facts, never what a file holds: from settings and MCP config only the names of hook events
and servers. Judging what each part means is the agent's job, on this output, and its result is a proposal to the
owner (D-2026-11-21-inventory-and-easy-upgrade, D-2026-11-22-second-redraw).

Exit code 0 when it ran, 2 when it could not. Standard library only. Run on Python 3.9 and 3.12.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True

import argparse
import errno
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
GLOBAL_LOOKED_AT = (".claude", ".codex", ".gemini", ".agents")
GLOBAL_FILES = (".claude.json",)
# Folders the walk of the repo does not enter.
NOT_ENTERED = {".git", "node_modules"}
# The folders not entered at the root, each with why: worktrees, and Ratchet's own copy in a repo that adopted it.
NOT_ENTERED_PATHS = {".claude/worktrees": "a folder of worktrees, not walked", ".ratchet": "Ratchet's own copy, not walked"}

# A name that looks like a credential. Such a file is named and never read.
CREDENTIAL_NAMES = ("*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.jks", ".env", ".env.*", "*.env", ".netrc",
                    ".npmrc", ".pypirc", "id_rsa*", "id_ecdsa*", "id_ed25519*", "id_dsa*", "*credential*", "*secret*",
                    "*token*", "auth.json", "oauth_creds.json", ".claude.json", "*.kdbx")

MAX_BYTES = 1000000

# A path named in an instruction file: the target of a Markdown link, a span in backticks, or an import @path.
LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
# A span is the text between two backticks, paired from the left. One with a space in it is a command, not a path.
SPAN = re.compile(r"`([^`]*)`")
# An import is a word of its own that starts with @. Punctuation at its end, as at the end of a sentence, is not part.
IMPORT = re.compile(r"(?:^|(?<=\s))@(\S+)")
TRAILING = ".,;:!?)]}\"'"
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


# The patterns that are a word in a name, such as no-secrets.md. A Markdown file of a kind a harness loads as text
# into the session, under such a name, names a rule and is read; any other file under it is not.
CREDENTIAL_WORDS = ("*credential*", "*secret*", "*token*")
MARKDOWN_KINDS = ("instructions", "skill", "skill file", "command", "agent", "output style")


def looks_like_credential(name, kind=None):
    lowered = name.lower()
    hits = [pattern for pattern in CREDENTIAL_NAMES if fnmatch.fnmatchcase(lowered, pattern)]
    if hits and kind in MARKDOWN_KINDS and lowered.endswith((".md", ".mdc")) and set(hits) <= set(CREDENTIAL_WORDS):
        return False
    return bool(hits)


# --- The guarded reader: the only place that opens, lists or looks at a file. ---
#
# Every path is read from a starting point, the root, the home folder, or for --ruleset the current folder or / , one
# part at a time: each part is looked at without following it, refused when it is a link, and opened under the folder
# before it with O_NOFOLLOW. A file is opened with O_NOFOLLOW and O_NONBLOCK and read only when it is a regular file.
# The starting point itself is the one path that may pass through a link, as /tmp does on macOS. test_inventory.py
# fails on any open, walk, listing or look at a path outside the functions named guarded_.

NOT_REGULAR = "not a regular file, not read"


class Refused(Exception):
    """A path the guarded reader does not go through: why, the part that is a link if one is, and whether it is gone."""

    def __init__(self, why, linked=None, missing=False):
        Exception.__init__(self, why)
        self.why = why
        self.linked = linked
        self.missing = missing


def guarded_start(start):
    """A descriptor of the folder a path starts from. It may itself be reached through a link."""
    try:
        return os.open(start, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError as error:
        raise Refused("could not be read: %s" % (error.strerror or error), missing=True)


def guarded_step(folder, part, shown_part, last, directory):
    """A descriptor of one part under the descriptor of its folder, refused when the part is a link."""
    try:
        status = os.stat(part, dir_fd=folder, follow_symlinks=False)
    except OSError as error:
        raise Refused("could not be read: %s" % (error.strerror or error), missing=True)
    if stat.S_ISLNK(status.st_mode):
        raise Refused("a link, not followed" if last else "%s on its path is a link, not followed" % shown_part,
                      linked=shown_part)
    if directory and not stat.S_ISDIR(status.st_mode):
        raise Refused("could not be read: %s is not a folder" % shown_part, missing=True)
    try:
        if directory:
            return os.open(part, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0), dir_fd=folder)
        return os.open(part, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), dir_fd=folder)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.EMLINK):
            raise Refused("%s on its path is a link, not followed" % shown_part, linked=shown_part)
        raise Refused("could not be read: %s" % (error.strerror or error))


def guarded_open(start, parts, directory, prefix=""):
    """A descriptor of start/parts, each part opened under the one before it, never through a link."""
    handle = guarded_start(start)
    try:
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            following = guarded_step(handle, part, prefix + "/".join(parts[:index + 1]), last, directory or not last)
            os.close(handle)
            handle = following
    except BaseException:
        os.close(handle)
        raise
    return handle


def guarded_read(start, parts, prefix=""):
    """The bytes of the regular file at start/parts: (data, None), or (None, why it was not read)."""
    try:
        handle = guarded_open(start, parts, directory=False, prefix=prefix)
    except Refused as refused:
        return None, refused.why
    try:
        status = os.fstat(handle)
        if not stat.S_ISREG(status.st_mode):
            return None, NOT_REGULAR
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
    except OSError as error:
        return None, "could not be read: %s" % (error.strerror or error)
    finally:
        os.close(handle)


def guarded_look(start, parts):
    """What stands at start/parts, without following a link: ("missing" | "dir" | "file" | "other", None), or
    ("link", the part from start that is a link), whether that is the last part or one above it."""
    try:
        handle = guarded_open(start, parts[:-1], directory=True)
    except Refused as refused:
        return ("link", refused.linked) if refused.linked else ("missing", None)
    try:
        if not parts:
            return "dir", None
        status = os.stat(parts[-1], dir_fd=handle, follow_symlinks=False)
    except OSError:
        return "missing", None
    finally:
        os.close(handle)
    if stat.S_ISLNK(status.st_mode):
        return "link", "/".join(parts)
    if stat.S_ISDIR(status.st_mode):
        return "dir", None
    return ("file" if stat.S_ISREG(status.st_mode) else "other"), None


def guarded_read_link(start, parts):
    """The target of the link at start/parts, read from its folder, reached through no link: (target, None) or (None, why)."""
    try:
        handle = guarded_open(start, parts[:-1], directory=True)
    except Refused as refused:
        return None, refused.why
    try:
        return os.readlink(parts[-1], dir_fd=handle), None
    except OSError as error:
        return None, "a link that could not be read: %s" % (error.strerror or error)
    finally:
        os.close(handle)


def guarded_list(handle):
    """The entries of an open folder, sorted, each (name, "link" | "dir" | "file" | "other"), none followed."""
    entries = []
    with os.scandir(handle) as listing:
        for entry in listing:
            if entry.is_symlink():
                kind = "link"
            elif entry.is_dir(follow_symlinks=False):
                kind = "dir"
            elif entry.is_file(follow_symlinks=False):
                kind = "file"
            else:
                kind = "other"
            entries.append((entry.name, kind))
    return sorted(entries)


def guarded_entries(start, parts):
    """The entries of the folder start/parts, reached through no link: (entries, None) or ([], why)."""
    try:
        handle = guarded_open(start, parts, directory=True)
    except Refused as refused:
        return [], refused.why
    try:
        return guarded_list(handle), None
    except OSError as error:
        return [], "could not be read: %s" % (error.strerror or error)
    finally:
        os.close(handle)


def guarded_walk(start, parts, on_error):
    """Each folder under start/parts, from the top down: (its parts, its entries, a list the caller fills with the
    names of the folders to enter). A folder is entered only by its descriptor, never through a link."""
    try:
        handle = guarded_open(start, parts, directory=True)
    except Refused as refused:
        on_error(list(parts), refused.why)
        return
    for found in guarded_walk_under(handle, list(parts), on_error):
        yield found


def guarded_walk_under(handle, parts, on_error):
    try:
        try:
            entries = guarded_list(handle)
        except OSError as error:
            on_error(parts, "could not be read: %s" % (error.strerror or error))
            return
        enter = []
        yield parts, entries, enter
        for name in enter:
            try:
                inner = guarded_step(handle, name, "/".join(parts + [name]), True, True)
            except Refused as refused:
                on_error(parts + [name], refused.why)
                continue
            for found in guarded_walk_under(inner, parts + [name], on_error):
                yield found
    finally:
        os.close(handle)


def parts_of(rel):
    return [part for part in rel.split("/") if part]


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

    def add_link(self, layer, rel):
        if any(link["path"] == layer.shown_path(rel) for link in self.links):
            return
        target, why = guarded_read_link(layer.top, parts_of(rel))
        if why is not None:
            self.skipped.append({"path": layer.shown_path(rel), "why": why})
            return
        full = os.path.join(layer.top, *parts_of(rel))
        resolved = os.path.normpath(os.path.join(os.path.dirname(full), target))
        inside = resolved == layer.top or resolved.startswith(layer.top.rstrip(os.sep) + os.sep)
        self.links.append({"path": layer.shown_path(rel), "target": target, "inside": inside})

    def add_file(self, layer, rel, kind, harnesses):
        name = rel.rsplit("/", 1)[-1]
        path = layer.shown_path(rel)
        if looks_like_credential(name, kind):
            self.skipped.append({"path": path, "why": "looks like a credential, not read"})
            return
        entry = {"path": path, "layer": layer.name, "kind": kind, "harnesses": list(harnesses), "rel": rel, "facts": []}
        data, why = guarded_read(layer.top, parts_of(rel))
        entry["why"] = why
        if why is not None:
            # A file too large or that could not be read stays in the layer, unread. Anything else is not a file.
            self.skipped.append({"path": path, "why": why})
            if why == NOT_REGULAR:
                return
            entry["bytes"] = None
            entry["sha256"] = None
        else:
            entry["bytes"] = len(data)
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            self.data[path] = data
        self.files.append(entry)

    def folder_not_read(self, layer):
        def note(parts, why):
            self.skipped.append({"path": layer.shown_path("/".join(parts)) or layer.prefix + ".", "why": why})
        return note

    def walk_repo(self, layer):
        for parts, entries, enter in guarded_walk(layer.top, [], self.folder_not_read(layer)):
            rel_folder = "".join(part + "/" for part in parts)
            for name, kind in entries:
                rel = rel_folder + name
                if kind == "link":
                    if self.in_layer(rel):
                        self.add_link(layer, rel)
                    continue
                if kind == "dir":
                    if rel in NOT_ENTERED_PATHS:
                        self.skipped.append({"path": layer.shown_path(rel), "why": NOT_ENTERED_PATHS[rel]})
                    elif name not in NOT_ENTERED:
                        enter.append(name)
                    continue
                found = classify(rel, KINDS, by_name=True)
                harness_folder = HARNESS_FOLDERS.get(rel.split("/", 1)[0]) if "/" in rel else None
                if found is None and harness_folder is None:
                    continue
                kind_found, harnesses = found if found is not None else ("unknown", (harness_folder,))
                self.add_file(layer, rel, kind_found, harnesses)

    def in_layer(self, rel):
        """Whether a link at rel stands where the repo's layer is: in a harness's folder, or where a kind is."""
        first = rel.split("/", 1)[0]
        return first in HARNESS_FOLDERS or first == ".github" or classify(rel, KINDS, by_name=True) is not None

    def walk_global(self, layer):
        for rel in GLOBAL_FILES:
            if guarded_look(layer.top, parts_of(rel))[0] != "missing":
                self.skipped.append({"path": layer.shown_path(rel), "why": "looks like a credential, not read"})
        for top in GLOBAL_LOOKED_AT:
            kind, linked = guarded_look(layer.top, parts_of(top))
            if kind == "link":
                self.add_link(layer, linked)
                continue
            if kind != "dir":
                continue
            entries, why = guarded_entries(layer.top, parts_of(top))
            if why is not None:
                self.skipped.append({"path": layer.shown_path(top), "why": why})
            for name, kind in entries:
                rel = top + "/" + name
                if kind == "link":
                    if classify(rel, GLOBAL_KINDS, by_name=False) is not None or rel in GLOBAL_WALKED:
                        self.add_link(layer, rel)
                    continue
                if kind == "dir":
                    continue
                found = classify(rel, GLOBAL_KINDS, by_name=False)
                if found is not None:
                    self.add_file(layer, rel, *found)
                elif looks_like_credential(name):
                    self.skipped.append({"path": layer.shown_path(rel), "why": "looks like a credential, not read"})
        for top in GLOBAL_WALKED:
            # Every part from the home folder down is looked at before anything under it is walked: a link at
            # ~/.claude is named there, and ~/.claude/skills behind it is not read.
            kind, linked = guarded_look(layer.top, parts_of(top))
            if kind == "link":
                self.add_link(layer, linked)
                continue
            if kind != "dir":
                continue
            for parts, entries, enter in guarded_walk(layer.top, parts_of(top), self.folder_not_read(layer)):
                rel_folder = "/".join(parts) + "/"
                for name, kind in entries:
                    rel = rel_folder + name
                    if kind == "link":
                        self.add_link(layer, rel)
                        continue
                    if kind == "dir":
                        enter.append(name)
                        continue
                    found = classify(rel, GLOBAL_KINDS, by_name=False)
                    if found is None:
                        if looks_like_credential(name):
                            self.skipped.append({"path": layer.shown_path(rel), "why": "looks like a credential, not read"})
                        continue
                    self.add_file(layer, rel, *found)


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
    if kind == "span" and any(char.isspace() for char in raw.strip()):
        return None
    value = raw.strip()
    if kind == "import":
        value = value.rstrip(TRAILING)
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
    if kind == "import":
        # @alice or @pytest.mark.skip is a word: an import has a / or an extension this inventory knows.
        return value if "/" in value or extension in EXTENSIONS else None
    if "/" not in value:
        # A bare name in backticks, such as `generate.py`, is a name: a path only in a link or an import.
        return None
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
        bases = [base for base in bases if within(layer.top, os.path.join(base, first))
                 and exists_in(layer, os.path.join(base, first)) is True]
    places = [os.path.normpath(os.path.join(base, *value.split("/"))) for base in bases]
    places = [place for place in places if within(layer.top, place)]
    if not places:
        return None
    found = [exists_in(layer, place) for place in places]
    if True in found:
        return True, places
    if None in found:
        # Through a link: what is behind it is not looked at, so whether the path exists is not said.
        return None
    return False, places


def exists_in(layer, place):
    """Whether a path under the top of a layer exists, looked at through no link: True, False, or None when a part
    above it is a link. A link that is the last part exists."""
    rel = os.path.relpath(os.path.normpath(place), layer.top)
    parts = [] if rel == "." else rel.split(os.sep)
    kind, linked = guarded_look(layer.top, parts)
    if kind == "link":
        return True if linked == "/".join(parts) else None
    return kind != "missing"


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
    settings_text, settings_unread = {}, {}
    for entry in inventory.files:
        if entry["kind"] == "settings" and entry["path"] in inventory.data:
            try:
                text = inventory.data[entry["path"]].decode("utf-8", errors="strict")
            except UnicodeDecodeError as error:
                settings_unread.setdefault(entry["layer"], []).append(
                    "%s is not UTF-8 at byte %d and was not read for hooks" % (shown(entry["path"]), error.start))
                continue
            settings_text.setdefault(entry["layer"], []).append(text)
    skill_folders = {}
    for entry in inventory.files:
        rel = entry["rel"]
        if entry["kind"] == "hook" and rel.startswith(".claude/hooks/"):
            texts = settings_text.get(entry["layer"], [])
            if not any(rel in text for text in texts):
                why = "; ".join(["a hook that no settings file names"] + settings_unread.get(entry["layer"], []))
                unused.append({"path": entry["path"], "why": why})
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


# --- Workflows, read as far as their top-level keys, their events, their jobs and each job's name. ---
#
# The reader reads a subset of YAML and fails closed: what it does not place is "not read", never left out. It reads
# block mappings indented with spaces, keys that are plain, or quoted without an escape; comments; a block scalar,
# whose text it skips; and under on: one event name, a list of names on one line, a block sequence of names at any
# indent, or a block mapping of names. A line that leaves a quote or a flow collection open, an anchor, alias, tag or
# merge key where it reads, a key given twice, a second document, a tab in the indent, or any line it cannot place
# makes the workflow, or the part of it, not read.

KEY = re.compile(r"^( *)(\"[^\"\\]*\"|'(?:[^']|'')*'|[A-Za-z0-9_-]+) *:(?: +(.*))?\Z")
EVENT = re.compile(r"^[a-z][a-z_]*\Z")
ITEM = re.compile(r"^-(?: +(.*))?\Z")
# The rest of a line that starts a block scalar: "|" or ">", with its indicators.
BLOCK_SCALAR = re.compile(r"(?:^|[:-] +)[|>][0-9+-]*\Z")
# The characters a plain scalar cannot start with.
INDICATORS = "-?:,[]{}#&*!|>'\"%@`"


class Unread(Exception):
    """A workflow, or a part of it, in a form this reader does not read."""


def without_comment(line):
    """(the line without a comment that starts at the line or after a space, outside quotes; whether it leaves a quote
    or a flow collection open).

    A quote or a bracket opens only where a scalar starts: at the start of the line, or after ":", "-", "[", "{" or ","
    and spaces, or anywhere inside a flow collection. An apostrophe inside a plain value, as in Project's Gate, and the
    braces of ${{ }}, are characters of the value."""
    quote = None
    depth = 0
    index = 0
    while index < len(line):
        char = line[index]
        if quote == "'":
            if char == "'":
                if line[index + 1:index + 2] == "'":
                    index += 1
                else:
                    quote = None
        elif quote == '"':
            if char == "\\":
                index += 1
            elif char == '"':
                quote = None
        elif char == "#" and (index == 0 or line[index - 1] in " \t"):
            return line[:index].rstrip(), depth > 0
        else:
            before = line[:index].rstrip(" ")
            starts = not before or before[-1] in ":-[{,"
            if char in "\"'" and (starts or depth > 0):
                quote = char
            elif char in "[{" and (starts or depth > 0):
                depth += 1
            elif char in "]}" and depth > 0:
                depth -= 1
        index += 1
    return line.rstrip(), quote is not None or depth > 0


def key_name(raw):
    """The key a KEY match names, unquoted."""
    if raw[0] == "'":
        return raw[1:-1].replace("''", "'")
    if raw[0] == '"':
        return raw[1:-1]
    return raw


def scalar(value):
    """The text of a scalar on one line, plain or quoted without an escape, or None for anything else."""
    value = (value or "").strip()
    if not value:
        return None
    if value[0] == "'":
        inner = value[1:-1]
        if len(value) < 2 or value[-1] != "'" or "'" in inner.replace("''", ""):
            return None
        return inner.replace("''", "'")
    if value[0] == '"':
        inner = value[1:-1]
        if len(value) < 2 or value[-1] != '"' or '"' in inner or "\\" in inner:
            return None
        return inner
    if value[0] in INDICATORS or ": " in value or value.endswith(":"):
        return None
    return value


def event(value):
    name = scalar(value)
    if name is None or not EVENT.match(name):
        raise Unread()
    return name


def indent(line):
    return len(line) - len(line.lstrip(" "))


def structure(text):
    """The lines that carry structure, without comments and blank lines, and without the text of block scalars."""
    lines = []
    block_indent = None
    for number, raw in enumerate(text.split("\n"), 1):
        if block_indent is not None:
            if not raw.strip() or indent(raw) > block_indent:
                continue
            block_indent = None
        line, still_open = without_comment(raw)
        if not line.strip():
            continue
        if "\t" in line[:len(line) - len(line.lstrip(" \t"))]:
            raise Unread("indented with tabs, which this reader does not read")
        if still_open:
            raise Unread("line %d leaves a quote or a bracket open, a value over more than one line, which this reader "
                         "does not read" % number)
        if BLOCK_SCALAR.search(line.strip()):
            block_indent = indent(line)
        lines.append((number, line))
    return lines


def mapping(lines):
    """[(key, rest, [lines under it])] of a block mapping whose keys stand at the indent of its first line, which is
    more than 0. A block sequence may stand at the indent of a key with nothing after it, as YAML allows."""
    if not lines or indent(lines[0]) == 0:
        raise Unread()
    first = indent(lines[0])
    result, seen = [], set()
    for line in lines:
        here = indent(line)
        if here > first and result:
            result[-1][2].append(line)
        elif here == first and ITEM.match(line[first:]) and result and not result[-1][1]:
            result[-1][2].append(line)
        elif here == first:
            match = KEY.match(line[first:])
            if not match:
                raise Unread()
            key = key_name(match.group(2))
            if key in seen:
                raise Unread()
            seen.add(key)
            result.append((key, match.group(3) or "", []))
        else:
            raise Unread()
    return result


def read_on(rest, under):
    """The events a workflow runs on, from the rest of its on: line and the lines under it."""
    if rest:
        if under:
            raise Unread()
        if rest.startswith("["):
            if not rest.endswith("]"):
                raise Unread()
            return [event(item) for item in rest[1:-1].split(",")]
        return [event(rest)]
    if not under:
        raise Unread()
    first = indent(under[0])
    if ITEM.match(under[0][first:]):
        events = []
        for line in under:
            item = ITEM.match(line[first:]) if indent(line) == first else None
            if item is None:
                raise Unread()
            events.append(event(item.group(1)))
        return events
    events = []
    for key, _, _ in mapping(under):
        if not EVENT.match(key):
            raise Unread()
        events.append(key)
    return events


def read_jobs(rest, under):
    """Each job, with its id, its name and whether it calls a reusable workflow."""
    if rest or not under:
        raise Unread()
    jobs = []
    for job_id, job_rest, body in mapping(under):
        if job_rest or not body:
            raise Unread()
        job = {"id": job_id, "name": None, "calls": False}
        for key, value, deeper in mapping(body):
            if key == "name":
                job["name"] = scalar(value)
                if job["name"] is None or deeper:
                    raise Unread()
            elif key == "uses":
                job["calls"] = True
        jobs.append(job)
    return jobs


def workflow_facts(text):
    """{"on": [...] or None, "jobs": [...] or None, "unread": why or None} for a workflow's text. None is not read."""
    try:
        lines = structure(text)
        top, current = {}, None
        for number, line in lines:
            if indent(line) > 0 or (ITEM.match(line) and current is not None and not current[0]):
                if current is None:
                    raise Unread("line %d is indented before the first key, which this reader does not read" % number)
                current[1].append(line)
                continue
            if line == "---" and not top:
                continue
            match = KEY.match(line)
            if not match:
                raise Unread("line %d is in a form this reader does not read" % number)
            key = key_name(match.group(2))
            if key in top:
                raise Unread("the key %s is given twice" % shown(key))
            current = (match.group(3) or "", [])
            top[key] = current
    except Unread as error:
        return {"on": None, "jobs": None, "unread": str(error)}
    triggers, jobs, unread = None, None, []
    if "on" not in top:
        unread.append("it has no on: that this reader found")
    else:
        try:
            triggers = read_on(*top["on"])
        except Unread:
            unread.append("its triggers are in a form this reader does not read")
    if "jobs" not in top:
        unread.append("it has no jobs: that this reader found")
    else:
        try:
            jobs = read_jobs(*top["jobs"])
        except Unread:
            unread.append("its jobs are in a form this reader does not read")
    return {"on": triggers, "jobs": jobs, "unread": "; ".join(unread) or None}


# --- The exported ruleset or branch protection. ---

KIND_NAMES = {list: "a list", dict: "an object", str: "text", bool: "true or false", int: "a number"}


def expect(value, kinds, what):
    """The value, when it is of its kind. true and false are not numbers, though Python counts them as such."""
    kinds = kinds if isinstance(kinds, tuple) else (kinds,)
    if not isinstance(value, kinds) or (isinstance(value, bool) and bool not in kinds):
        raise Fault("%s must be %s" % (what, KIND_NAMES.get(kinds[0], kinds[0].__name__)))
    return value


def optional(item, key, kinds, what=None):
    """A field that may be left out: None when it is absent or null, else the value, of its kind."""
    value = item.get(key)
    return None if value is None else expect(value, kinds, what or key)


def needed(item, key, kinds, form, what=None):
    """A field the export always holds: a fault when it is absent or null."""
    if item.get(key) is None:
        raise Fault("a %s without %s" % (form, what or key))
    return expect(item[key], kinds, what or key)


# What a refusal for a link on the path of an export adds: how to give it without one (review of #119).
NO_LINK = ("Give the path with no link on it: as realpath prints it, or relative from a folder below the link, such as "
           "/private/tmp on macOS in place of /tmp")


def read_ruleset(path):
    """The facts of each ruleset or branch protection in an exported file, read as every other file is."""
    # Read from the current folder, or from / for an absolute path, one part at a time, refused at any part that is a
    # link: a folder given through a link is refused as a file that is one.
    absolute = path.startswith("/")
    parts = [part for part in path.split("/") if part not in ("", ".")]
    # The name is the last part that names something, so secret-token.json/ or secret-token.json/. is a credential too,
    # and the name after normalizing, so x/secret-token.json/.. is (review of #119).
    names = [name for name in (parts[-1] if parts else "", os.path.basename(os.path.normpath(path))) if name not in ("", ".", "..")]
    if any(looks_like_credential(name) for name in names):
        raise Fault("%s: looks like a credential, not read" % path)
    # A path that ends in "/", "/." or "/.." names a folder.
    if not parts or path.split("/")[-1] in ("", ".", ".."):
        raise Fault("%s: names a folder, not a file" % path)
    data, why = guarded_read("/" if absolute else ".", parts, prefix="/" if absolute else "")
    if why is not None:
        if "is a link, not followed" in why or why == "a link, not followed":
            why += ". " + NO_LINK
        raise Fault("%s: %s" % (path, why))
    try:
        value = registry.parse_json(data)
    except registry.RegistryError as error:
        raise Fault("%s: %s" % (path, error))
    items = value if isinstance(value, list) else [value]
    if not items:
        raise Fault("%s: the export holds no ruleset and no branch protection" % path)
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


def empty_facts(form):
    return {"form": form, "name": "", "target": "branch", "enforcement": "active", "include": [], "exclude": [],
            "required_checks": [], "up_to_date": None, "review": None, "bypass": [], "other_rules": [], "not_read": []}


# The parameters of a rule, or fields of a branch protection's review, that are read: field -> (fact, kind).
RULESET_REVIEW = {"required_approving_review_count": ("approvals", int), "require_code_owner_review": ("code_owner", bool),
                  "dismiss_stale_reviews_on_push": ("dismiss_stale", bool), "require_last_push_approval": ("last_push", bool),
                  "required_review_thread_resolution": ("thread_resolution", bool)}
PROTECTION_REVIEW = {"required_approving_review_count": ("approvals", int), "require_code_owner_reviews": ("code_owner", bool),
                     "dismiss_stale_reviews": ("dismiss_stale", bool), "require_last_push_approval": ("last_push", bool)}
REVIEW_FACTS = ("approvals", "code_owner", "dismiss_stale", "last_push", "thread_resolution")
OTHER_RULES = ("deletion", "non_fast_forward", "creation", "update", "required_linear_history", "required_signatures")
PROTECTION_TOGGLES = ("allow_force_pushes", "allow_deletions", "required_linear_history", "required_signatures",
                      "lock_branch", "block_creations", "required_conversation_resolution", "allow_fork_syncing")


def review_facts(values, known, prefix, facts):
    """Each review fact a field gives, None where the export leaves it out; a field it does not know is named."""
    review = dict.fromkeys(REVIEW_FACTS)
    for field in sorted(values):
        if field in known:
            fact, kind = known[field]
            review[fact] = optional(values, field, kind)
        elif field not in ("url", "bypass_pull_request_allowances"):
            facts["not_read"].append("%s.%s" % (prefix, field))
    return review


def ruleset_facts(item):
    facts = empty_facts("ruleset")
    facts["name"] = optional(item, "name", str) or ""
    facts["target"] = needed(item, "target", str, "ruleset")
    facts["enforcement"] = needed(item, "enforcement", str, "ruleset")
    conditions = optional(item, "conditions", dict)
    ref_name = None if conditions is None else optional(conditions, "ref_name", dict, "conditions.ref_name")
    for field in ("include", "exclude"):
        if ref_name is None:
            facts[field] = None
        else:
            names = optional(ref_name, field, list, "conditions.ref_name.%s" % field) or []
            facts[field] = [expect(name, str, "conditions.ref_name.%s" % field) for name in names]
    for rule in expect(item["rules"], list, "rules"):
        rule = expect(rule, dict, "a rule")
        if rule.get("type") is None:
            raise Fault("a rule without a type")
        kind = expect(rule["type"], str, "type")
        parameters = optional(rule, "parameters", dict, "parameters of %s" % kind) or {}
        if kind == "required_status_checks":
            if parameters.get("required_status_checks") is None:
                raise Fault("a rule required_status_checks without required_status_checks")
            for check in expect(parameters["required_status_checks"], list, "required_status_checks"):
                facts["required_checks"].append(needed(expect(check, dict, "a required status check"), "context", str,
                                                       "required status check"))
            facts["up_to_date"] = optional(parameters, "strict_required_status_checks_policy", bool)
            for field in sorted(set(parameters) - {"required_status_checks", "strict_required_status_checks_policy"}):
                facts["not_read"].append("required_status_checks.%s" % field)
        elif kind == "pull_request":
            facts["review"] = review_facts(parameters, RULESET_REVIEW, "pull_request", facts)
        elif kind in OTHER_RULES:
            facts["other_rules"].append(kind)
        else:
            facts["not_read"].append(kind)
    actors = optional(item, "bypass_actors", list)
    # GitHub leaves bypass_actors out of what it shows an account without admin rights: then it is not known.
    facts["bypass"] = None if actors is None else []
    for actor in actors or []:
        actor = expect(actor, dict, "a bypass actor")
        actor_id = optional(actor, "actor_id", int)
        facts["bypass"].append("%s %s (%s)" % (needed(actor, "actor_type", str, "bypass actor"),
                                               "-" if actor_id is None else actor_id,
                                               needed(actor, "bypass_mode", str, "bypass actor")))
    return facts


def protection_facts(item):
    facts = empty_facts("branch protection")
    checks = optional(item, "required_status_checks", dict)
    if checks is not None:
        if checks.get("contexts") is None and checks.get("checks") is None:
            raise Fault("required_status_checks without contexts or checks")
        names = [expect(name, str, "contexts") for name in optional(checks, "contexts", list) or []]
        for check in optional(checks, "checks", list) or []:
            name = needed(expect(check, dict, "a check"), "context", str, "check")
            if name not in names:
                names.append(name)
        facts["required_checks"] = names
        facts["up_to_date"] = optional(checks, "strict", bool)
    reviews = optional(item, "required_pull_request_reviews", dict)
    if reviews is not None:
        facts["review"] = review_facts(reviews, PROTECTION_REVIEW, "required_pull_request_reviews", facts)
        allowances = optional(reviews, "bypass_pull_request_allowances", dict) or {}
        for field, key, label in (("users", "login", "user"), ("teams", "slug", "team"), ("apps", "slug", "app")):
            for actor in optional(allowances, field, list, "bypass_pull_request_allowances.%s" % field) or []:
                name = needed(expect(actor, dict, "an allowance"), key, str, "allowance")
                facts["bypass"].append("%s %s (pull requests)" % (label, name))
    admins = optional(item, "enforce_admins", dict)
    if admins is None:
        facts["bypass"].append("administrators: enforce_admins not in the export")
    elif not needed(admins, "enabled", bool, "enforce_admins", "enabled"):
        facts["bypass"].append("administrators (enforce_admins is off)")
    for field in PROTECTION_TOGGLES:
        toggle = optional(item, field, dict)
        if toggle is not None:
            enabled = needed(toggle, "enabled", bool, field, "enabled")
            facts["other_rules"].append("%s %s" % (field, "on" if enabled else "off"))
    for field in sorted(set(item) - set(PROTECTION_TOGGLES) - {"url", "required_status_checks", "required_pull_request_reviews",
                                                               "enforce_admins"}):
        facts["not_read"].append(field)
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
    """The required checks a job reports as: its name, alone, with a matrix "(...)" or a called " / job".

    GitHub reports a job by its literal name when it has one, and by its id only when it has none. A name that is an
    expression is known only when the job runs, so the id is compared in its place."""
    name = job["name"] if job["name"] and "${{" not in job["name"] else job["id"]
    return [context for context in required
            if context == name or context.startswith(name + " (") or context.startswith(name + " / ")]


def code_owners(inventory, layer):
    """The lines of the code owners file GitHub reads, and the files the register names."""
    owners_file, lines, notes = None, [], []
    for rel in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        path = rel
        if path in inventory.data:
            owners_file = path
            try:
                text = inventory.data[path].decode("utf-8", errors="strict")
            except UnicodeDecodeError as error:
                notes.append("%s: not UTF-8 at byte %d, its lines are not read" % (path, error.start))
                break
            for number, line in enumerate(text.split("\n"), 1):
                line = line.strip()
                if line and not line.startswith("#"):
                    lines.append([number, line])
            break
    names = []
    data = inventory.data.get("register.json")
    if data is not None:
        try:
            register = registry.parse_json(data)
        except registry.RegistryError as error:
            register = None
            notes.append("register.json: %s" % error)
        if register is not None and not isinstance(register, dict):
            notes.append("register.json: not a JSON object, not read")
        if isinstance(register, dict):
            values = []
            if isinstance(register.get("instructions"), str):
                values.append(register["instructions"])
            for part in ("adopted", "own"):
                rows = register.get(part)
                if rows is None:
                    continue
                if not isinstance(rows, list):
                    notes.append("register.json: %s is not a list, not read" % part)
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if isinstance(row.get("stands_in"), str):
                        values.append(row["stands_in"])
                    if isinstance(row.get("where"), str):
                        for match in SPAN.finditer(row["where"]):
                            value = candidate(match.group(1), "span")
                            if value is None:
                                continue
                            # A word such as owner/repo is a path only when its first part exists, as in a file.
                            if value.startswith("?"):
                                value = value[1:]
                                # Its first part is looked at only inside the root, as resolve_named does (review of #119).
                                first = os.path.join(layer.top, value.split("/", 1)[0])
                                if not within(layer.top, first) or exists_in(layer, first) is not True:
                                    continue
                            values.append(value)
            for value in values:
                full = os.path.join(layer.top, *value.split("/"))
                if within(layer.top, full) and value not in [name for name, _ in names]:
                    names.append([value, exists_in(layer, full)])
    if owners_file is None and data is None:
        return None
    return {"file": owners_file, "lines": lines, "register_names": names, "note": "; ".join(notes) or None}


def build(args):
    root = args.root
    if guarded_look(root, [])[0] != "dir":
        raise Fault("%s is not a directory" % root)
    uses = None
    if args.uses is not None:
        uses = [name.strip() for name in args.uses.split(",") if name.strip()]
        if not uses:
            raise Fault("--uses names no harness: give the harnesses the project uses, such as --uses claude,codex")
        for name in uses:
            if name not in HARNESSES:
                raise Fault("unknown harness %r: the harnesses this inventory knows are %s" % (name, ", ".join(HARNESSES)))
        uses = sorted(set(uses))
    if args.home is not None and not args.use_global:
        raise Fault("--home names the home folder for --global, and --global was not given")
    if args.home == "":
        raise Fault("--home is empty: give the home folder for --global, or leave --home out to use HOME")
    rulesets = []
    for path in args.ruleset or []:
        rulesets += read_ruleset(path)

    inventory = Inventory()
    layers = {"repo": Layer("repo", root, "")}
    inventory.walk_repo(layers["repo"])
    if args.use_global:
        home = args.home or os.path.expanduser("~")
        if guarded_look(home, [])[0] != "dir":
            raise Fault("%s is not a directory" % home)
        layers["global"] = Layer("global", home, "~/")
        inventory.walk_global(layers["global"])
    inventory.files.sort(key=lambda entry: (entry["layer"] != "repo", entry["path"]))

    missing, named_by = inspect(inventory, layers)
    workflows = []
    required = required_names(rulesets)
    not_required = [] if rulesets else None
    # The jobs of a workflow whose events or jobs were not read: whether they run on a pull request is not known, and
    # they are listed under a heading of their own, never left out.
    not_known = []
    produced = set()
    for entry in inventory.files:
        if entry["kind"] != "workflow":
            continue
        data = inventory.data.get(entry["path"])
        if data is None:
            facts = {"on": None, "jobs": None, "unread": entry.get("why") or "not read"}
        else:
            try:
                facts = workflow_facts(data.decode("utf-8", errors="strict"))
            except UnicodeDecodeError as error:
                facts = {"on": None, "jobs": None, "unread": "not UTF-8 at byte %d" % error.start}
        on_pull_request = facts["on"] is not None and bool(set(facts["on"]) & PULL_REQUEST_EVENTS)
        jobs = None if facts["jobs"] is None else []
        for job in facts["jobs"] or []:
            state = None
            if rulesets:
                matched = contexts_of(job, required)
                produced.update(matched)
                state = bool(matched)
            if facts["on"] is None:
                not_known.append({"path": entry["path"], "job": job["id"], "name": job["name"], "required": state})
            elif rulesets and not state and on_pull_request:
                not_required.append({"path": entry["path"], "job": job["id"], "name": job["name"]})
            jobs.append({"id": job["id"], "name": job["name"], "required": state, "calls": job["calls"]})
        if facts["jobs"] is None:
            not_known.append({"path": entry["path"], "job": None, "name": None, "required": None})
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
        "not_known": not_known,
        "required_without_job": None if not rulesets else [name for name in required if name not in produced],
        "code_owners": code_owners(inventory, layers["repo"]),
    }


def yes(value):
    return "yes" if value else "no"


def review_line(review):
    """The facts of a required review, each "not in the export" where the export leaves it out."""
    parts = []
    if review["approvals"] is None:
        parts.append("approvals not in the export")
    else:
        parts.append("%d approval%s" % (review["approvals"], "" if review["approvals"] == 1 else "s"))
    for fact, label in (("code_owner", "code owner review"), ("dismiss_stale", "stale reviews dismissed on push"),
                        ("last_push", "last push approval"), ("thread_resolution", "conversations resolved")):
        if review[fact] is not None:
            parts.append("%s %s" % (label, yes(review[fact])))
        elif fact != "thread_resolution":
            parts.append("%s not in the export" % label)
    return ", ".join(parts)


def text_report(facts):
    out = []
    add = out.append
    add("inventory of %s" % shown(facts["root"]) + (", with the global layer" if facts["global"] else ""))
    add("")
    add("The agent layer: %d file%s" % (len(facts["files"]), "" if len(facts["files"]) == 1 else "s"))
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
        events = "events not read" if workflow["on"] is None else ", ".join(shown(name) for name in workflow["on"])
        add("  %s, on %s" % (shown(workflow["path"]), events))
        if workflow["unread"]:
            add("    not read: %s" % shown(workflow["unread"]))
        if workflow["jobs"] is None:
            add("    jobs not read")
        for job in workflow["jobs"] or []:
            label = shown(job["id"]) + (' ("%s")' % shown(job["name"]) if job["name"] else "")
            state = {None: "", True: ": required", False: ": not required"}[job["required"]]
            add("    %s%s%s" % (label, state, ", calls a reusable workflow" if job["calls"] else ""))
    known = {None: "", True: ", required", False: ", not required"}
    section("Jobs of workflows this reader could not read: it cannot tell whether they run on a pull request",
            ["%s: its jobs were not read" % shown(item["path"]) if item["job"] is None else
             "%s: %s%s%s" % (shown(item["path"]), shown(item["job"]), ' ("%s")' % shown(item["name"]) if item["name"] else "",
                             known[item["required"]])
             for item in facts["not_known"]])
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
            if item["include"] is None:
                title += ", branches not in the export"
            elif item["include"]:
                title += ", on " + ", ".join(shown(name) for name in item["include"])
            if item["exclude"]:
                title += ", not on " + ", ".join(shown(name) for name in item["exclude"])
            add(title)
            if item["enforcement"] != "active":
                add("    enforcement %s: GitHub does not enforce it" % shown(item["enforcement"]))
            review = item["review"]
            add("    required review: %s" % ("none" if review is None else review_line(review)))
            add("    required checks: %s%s" % (", ".join(shown(name) for name in item["required_checks"]) or "none",
                                               "" if item["up_to_date"] is None else "; branch up to date: %s" % yes(item["up_to_date"])))
            if item["bypass"] is None:
                add("    bypass: not shown in the export (GitHub shows it only to an account with admin rights)")
            else:
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
            add("    %s%s" % (shown(name), {True: "", False: " (does not exist)", None: " (through a link, not looked at)"}[exists]))
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
