#!/usr/bin/env python3
"""A tripwire for ratchet.irreversible-waits: a PreToolUse hook for Claude Code.

It reads the tool call as JSON on stdin and exits 2, with the reason on stderr, when a Bash command takes one of
five steps that cannot be undone and no approval names that step and that exact command:

    force-push      git push --force, -f, --force-with-lease, --mirror, --prune, --delete, +refspec, :ref;
                    the API deleting a branch, or moving one with force=true
    tag             git tag creating, moving or deleting; git push of a tag, --tags, --follow-tags;
                    git update-ref on refs/tags/; the API on git/refs/tags or git/tags, or making a tag ref
    release         gh release create, edit, delete, upload, delete-asset; the API changing releases
    delete-outside  rm -r of a path outside the working tree, or of the tree itself
    settings        gh repo edit, delete, rename, archive, deploy-key; gh secret, gh variable set and delete;
                    gh workflow enable and disable; the API changing the repository or a settings path

It also denies, and no approval reaches, any command or file tool that names the approvals file.

It is a tripwire, not a lock. It catches the usual spellings, the cases listed in checks/README.md, and nothing
more: another spelling gets past it. Where the steps are locked, and where not, is in CONTROL-ROOM.md.

Approvals are in .claude/ratchet-approvals.json in the project, a file the owner writes and git ignores:

    {"approvals": [{"step": "tag", "command": "git tag v0.7", "until": "2026-11-30"}]}

It is read strictly. One defect anywhere and it approves nothing. It never exits other than 0 or 2.

Standard library only, in one file, so that a project can copy it. Run on Python 3.9 and 3.12.
"""

import datetime
import functools
import json
import os
import re
import stat
import subprocess
import sys
import tempfile

STEPS = ("force-push", "tag", "release", "delete-outside", "settings")
APPROVALS = os.path.join(".claude", "ratchet-approvals.json")
FILE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
# An approved command is one plain line: printable ASCII without the marks that chain, redirect or substitute.
PLAIN = re.compile(r"^[!-~](?:[ -~]*[!-~])?\Z")
NOT_PLAIN = set(";&|<>()$`\\")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SUB = "\x00"  # stands for a substitution, $(...) or `...`, inside a word
KEYWORDS = {"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "!", "{", "}", "time"}
WRAPPERS = {"env", "command", "builtin", "exec", "nohup", "nice", "timeout", "sudo", "xargs", "stdbuf"}
# Options of the wrappers that take the next word as their value.
WRAPPER_VALUES = {"env": {"-u", "-C", "-S"}, "exec": {"-a"}, "nice": {"-n"}, "sudo": {"-u", "-g", "-C", "-D", "-h", "-p", "-U"},
                  "xargs": {"-I", "-L", "-n", "-P", "-s", "-d", "-E", "-a"}, "stdbuf": {"-i", "-o", "-e"}, "timeout": {"-s", "-k"}}
GH_API_VALUES = {"-X", "--method", "-H", "--header", "-f", "--raw-field", "-F", "--field", "--input", "-q", "--jq", "-t",
                 "--template", "--cache", "-p", "--preview", "--hostname"}
# Paths under repos/{owner}/{repo}/ that are settings: a mutating call on one of them is the step settings.
SETTINGS = {"rulesets", "branches", "collaborators", "invitations", "hooks", "keys", "actions", "environments", "pages",
            "secrets", "variables", "topics", "vulnerability-alerts", "automated-security-fixes", "autolinks", "properties",
            "private-vulnerability-reporting", "transfer", "tags", "dependabot", "codespaces", "interaction-limits", "teams"}


class Denied(Exception):
    """Input the hook cannot read."""


# Reading the command line ---------------------------------------------------------------------------------------

def lex(text):
    """The simple commands of a line: [{"words": [...], "raw": [...], "targets": [...]}], with substitutions as commands too.

    Quotes and backslashes are taken away from a word, as the shell does. A word holds SUB where a substitution was.
    "raw" is each word as written. "targets" are the words after a redirection. A here-document's body is not read.
    """
    commands, subs = [], []
    _lex(text, 0, commands, subs, 0)
    return commands + subs


def _lex(text, i, commands, subs, depth):
    if depth > 50:
        raise Denied("the command nests too deeply to read")
    words, raw, targets, heredocs = [], [], [], []
    word, start, quoted, target = None, 0, False, False

    def end():
        nonlocal word, target
        if word is not None:
            (targets if target else words).append(word)
            if not target:
                raw.append(text[start:i])
            target = False
        word = None

    def finish():
        nonlocal words, raw, targets
        end()
        if words or targets:
            commands.append({"words": words, "raw": raw, "targets": targets})
        words, raw, targets = [], [], []

    def substitution(j, closing):
        """Lex text from j to its closing mark as commands of their own. Returns the index after it."""
        if closing == ")":
            inner = []
            j = _lex(text, j, inner, subs, depth + 1)
            subs.extend(inner)
            return j
        k = j
        while k < len(text) and text[k] != "`":
            k += 2 if text[k] == "\\" else 1
        inner = []
        _lex(text[j:k].replace("\\`", "`"), 0, inner, subs, depth + 1)
        subs.extend(inner)
        return k + 1

    while i < len(text):
        c = text[i]
        if word is None and c not in " \t\n;&|()<>":
            word, start = "", i
        if c in " \t":
            end()
            i += 1
        elif c == "\n":
            finish()
            i += 1
            for delimiter, strip in heredocs:
                while i < len(text):
                    line_end = text.find("\n", i)
                    line_end = len(text) if line_end < 0 else line_end
                    line = text[i:line_end]
                    i = line_end + 1
                    if (line.lstrip("\t") if strip else line) == delimiter:
                        break
            heredocs = []
        elif c in ";&|":
            if c == "&" and text[i + 1:i + 2] == ">":
                end()
                target = True
                i += 2 + (text[i + 2:i + 3] == ">")
                continue
            finish()
            i += 1
        elif c == "(":
            finish()
            i += 1
        elif c == ")":
            finish()
            if depth:
                return i + 1
            i += 1
        elif c in "<>":
            if word is not None and word.isdigit() and not quoted and text[start:i].isdigit():
                word = None
            end()
            if text.startswith("<<<", i):
                i += 3
            elif text.startswith("<<", i):
                i += 2
                strip = text[i:i + 1] == "-"
                i += strip
                while text[i:i + 1] in (" ", "\t"):
                    i += 1
                m = re.match(r"""(['"]?)([^\s;&|()<>'"]+)\1""", text[i:])
                if m:
                    heredocs.append((m.group(2), strip))
                    i += m.end()
                continue
            elif text.startswith("<(", i) or text.startswith(">(", i):
                i = substitution(i + 2, ")")
                continue
            else:
                i += 1
                if text[i:i + 1] in (">", "&", "|"):
                    i += 1
            target = True
        elif c == "'":
            k = text.find("'", i + 1)
            k = len(text) if k < 0 else k
            word += text[i + 1:k]
            quoted = True
            i = k + 1
        elif c == '"':
            i += 1
            quoted = True
            while i < len(text) and text[i] != '"':
                if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in '"\\$`\n':
                    word += text[i + 1] if text[i + 1] != "\n" else ""
                    i += 2
                elif text.startswith("$(", i) and not text.startswith("$((", i):
                    word += SUB
                    i = substitution(i + 2, ")")
                elif text[i] == "`":
                    word += SUB
                    i = substitution(i + 1, "`")
                else:
                    word += text[i]
                    i += 1
            i += 1
        elif c == "\\":
            word += text[i + 1:i + 2] if text[i + 1:i + 2] != "\n" else ""
            i += 2
        elif text.startswith("$((", i):
            k = text.find("))", i)
            k = len(text) if k < 0 else k
            word += text[i:k + 2]
            i = k + 2
        elif text.startswith("$(", i):
            word += SUB
            i = substitution(i + 2, ")")
        elif c == "`":
            word += SUB
            i = substitution(i + 1, "`")
        elif c == "#" and word == "":
            k = text.find("\n", i)
            i = len(text) if k < 0 else k
            word = None
        else:
            word += c
            i += 1
        if word is None:
            quoted = False
    finish()
    return i


def program(words):
    """(name, arguments) of a simple command, past assignments, keywords and wrappers such as env and sudo."""
    i = 0
    while i < len(words):
        word = words[i]
        if ASSIGNMENT.match(word) or word in KEYWORDS:
            i += 1
            continue
        name = os.path.basename(word)
        if name in ("for", "case", "select", "function"):
            return None, []
        if name in WRAPPERS:
            if name == "command" and any(w in ("-v", "-V") for w in words[i + 1:i + 2]):
                return None, []
            i += 1
            while i < len(words) and (words[i].startswith("-") or (name == "env" and ASSIGNMENT.match(words[i]))):
                i += 2 if words[i] in WRAPPER_VALUES.get(name, ()) else 1
            if name == "timeout" and i < len(words):
                i += 1
            continue
        return name, words[i + 1:]
    return None, []


# The five steps -------------------------------------------------------------------------------------------------

def git_steps(args, cwd):
    directory = cwd
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") and args:
            value = args.pop(0)
            if option == "-C" and directory is not None:
                directory = os.path.join(directory, value)
    if not args:
        return set()
    sub, rest = args[0], args[1:]
    if sub == "push":
        return push_steps(rest, directory)
    if sub == "tag":
        return tag_steps(rest)
    if sub in ("update-ref", "symbolic-ref") and any(w.lower().startswith("refs/tags/") for w in rest):
        return {"tag"}
    return set()


@functools.lru_cache(maxsize=256)
def is_tag(name, directory):
    """Whether a name in a refspec is a tag: refs/tags/..., or a short name that is a tag in the local repository."""
    if name.startswith("refs/tags/"):
        return True
    if name.startswith("refs/") or not name or directory is None:
        return False
    try:
        return subprocess.run(["git", "-C", directory, "show-ref", "--verify", "--quiet", "refs/tags/" + name],
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10).returncode == 0
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def push_steps(args, directory):
    steps, positional, delete = set(), [], False
    i = 0
    while i < len(args):
        word = args[i]
        i += 1
        if word in ("-o", "--push-option", "--repo", "--receive-pack", "--exec"):
            i += 1
        elif word.startswith("--"):
            option = word.split("=", 1)[0]
            if option.startswith("--force") or option in ("--mirror", "--prune"):
                steps.add("force-push")
            if option in ("--mirror", "--tags", "--follow-tags"):
                steps.add("tag")
            delete = delete or option == "--delete"
        elif word.startswith("-") and len(word) > 1:
            for letter in word[1:]:
                if letter == "o":
                    i += word.endswith("o")
                    break
                steps.update({"f": {"force-push"}}.get(letter, ()))
                delete = delete or letter == "d"
        else:
            positional.append(word)
    refspecs = positional[1:]
    j = 0
    while j < len(refspecs):
        spec = refspecs[j]
        if spec == "tag":
            steps.add("tag")
            j += 2
            continue
        j += 1
        source, _, destination = spec.lstrip("+").partition(":")
        if delete or (spec.startswith(":") and destination):
            ref = destination if spec.startswith(":") else source
            steps.add("tag" if is_tag(ref, directory) else "force-push")
            continue
        if spec.startswith("+"):
            steps.add("force-push")
        if is_tag(source, directory) or destination.startswith("refs/tags/"):
            steps.add("tag")
    return steps


def tag_steps(args):
    listing = {"-l", "--list", "-v", "--verify", "--contains", "--no-contains", "--points-at", "--merged", "--no-merged"}
    values = {"-m", "--message", "-F", "--file", "-u", "--local-user", "--sort", "--format", "--cleanup",
              "--contains", "--no-contains", "--points-at", "--merged", "--no-merged"}
    named, lists = False, False
    i = 0
    while i < len(args):
        word = args[i]
        i += 1
        option = word.split("=", 1)[0]
        if option in ("-d", "--delete"):
            return {"tag"}
        if option in listing or re.match(r"^-n[0-9]*\Z", word):
            lists = True
        elif word.startswith("-") and len(word) > 1:
            if "d" in word[1:] and not word.startswith("--"):
                return {"tag"}
            named = named or option in ("-a", "-s", "-f", "--force", "--annotate", "--sign", "-m", "-F", "-u")
            if option in values and "=" not in word:
                i += 1
        else:
            named = True
    return {"tag"} if named and not lists else set()


def gh_steps(args):
    words = [w for w in args if not w.startswith("-")]
    if not words:
        return set()
    group, action = words[0], (words[1] if len(words) > 1 else "")
    if group == "api":
        return api_steps(args[args.index("api") + 1:])
    if group == "release" and action in ("create", "edit", "delete", "upload", "delete-asset"):
        return {"release"}
    if group == "repo" and action in ("edit", "delete", "rename", "archive", "unarchive", "deploy-key"):
        return {"settings"}
    if group in ("secret", "variable") and action in ("set", "delete", "remove"):
        return {"settings"}
    if group == "workflow" and action in ("enable", "disable"):
        return {"settings"}
    return set()


def api_steps(args):
    method, endpoint, fields, body = None, None, [], False
    i = 0
    while i < len(args):
        word = args[i]
        i += 1
        option, has_value, value = word.partition("=") if word.startswith("--") else (word, False, "")
        if word.startswith("-X") and len(word) > 2:
            method = word[2:]
        elif option in GH_API_VALUES:
            if not has_value:
                value = args[i] if i < len(args) else ""
                i += 1
            if option in ("-X", "--method"):
                method = value
            elif option in ("-f", "--raw-field", "-F", "--field"):
                fields.append(value)
            elif option == "--input":
                body = True
        elif not word.startswith("-") and endpoint is None:
            endpoint = word
    method = (method or ("POST" if fields or body else "GET")).upper()
    if method in ("GET", "HEAD") or endpoint is None:
        return set()
    path = re.sub(r"^https?://[^/]+/", "", endpoint).split("?")[0].strip("/").split("/")
    if len(path) < 3 or path[0] != "repos":
        return set()
    rest = path[3:]
    if not rest:
        return {"settings"}
    joined = "/".join(rest)
    if rest[0] == "releases":
        return {"release"}
    if joined.startswith("git/refs/tags") or joined.startswith("git/tags"):
        return {"tag"}
    if joined == "git/refs" and (body or any(f.startswith("ref=refs/tags/") for f in fields)):
        return {"tag"}
    if joined.startswith("git/refs/heads/") and (method == "DELETE" or any(f in ("force=true", "force=1") for f in fields) or body):
        return {"force-push"}
    if rest[0] in SETTINGS:
        return {"settings"}
    return set()


def rm_steps(args, raws, cwd, tree, mktemp):
    if not any(w in ("-r", "-R", "--recursive") or (re.match(r"^-[A-Za-z]+\Z", w) and set(w[1:]) & set("rR")) for w in args):
        return set()
    operands, options = [], True
    for word, raw in zip(args, raws):
        if options and word == "--":
            options = False
        elif not (options and word.startswith("-") and len(word) > 1):
            operands.append((word, raw))
    for word, raw in operands:
        if raw in ['"$%s"' % name for name in mktemp] + ['"${%s}"' % name for name in mktemp]:
            continue
        path = resolve(cwd, word) if literal(word) else None
        if path is None or (outside(path, tree) and not own_temporary(path)):
            return {"delete-outside"}
    return set()


def own_temporary(path):
    """Whether a path is, or is inside, a directory that mktemp -d made: tmp. and at least six letters or digits,
    directly in the temporary directory or /tmp, a real directory and not a link, owned by this user."""
    roots = set(os.path.realpath(root) for root in (tempfile.gettempdir(), "/tmp"))
    for root in roots:
        if path != root and os.path.commonpath([path, root]) == root:
            top = os.path.join(root, os.path.relpath(path, root).split(os.sep)[0])
            try:
                info = os.lstat(top)
            except OSError:
                return False
            return (re.match(r"^tmp\.[A-Za-z0-9]{6,}\Z", os.path.basename(top)) is not None and stat.S_ISDIR(info.st_mode)
                    and info.st_uid == os.getuid())
    return False


def literal(word):
    """Whether a word means itself: no variable and no substitution in it."""
    return "$" not in word and SUB not in word


def resolve(cwd, path):
    """The real path of a word, from cwd, or None when it cannot be known."""
    if cwd is None:
        return None
    try:
        return os.path.realpath(os.path.join(cwd, os.path.expanduser(path)))
    except (OSError, ValueError):
        return None


def outside(path, tree):
    return path == tree or os.path.commonpath([path, tree]) != tree


def mktemp_names(commands):
    """Names assigned $(mktemp -d) in the line, and assigned nothing else: the one variable rm -r may name."""
    names = set()
    for command in commands:
        words = command["words"]
        for k, word in enumerate(words):
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=" + SUB + r"\Z", word)
            raw = command["raw"][k]
            if m and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\$\(mktemp -d(?: -t [A-Za-z0-9._-]+)?\)\Z", raw):
                names.add(m.group(1))
    for name in list(names):
        assigned = sum(1 for c in commands for w in c["words"] if w.startswith(name + "="))
        named = any(w == name for c in commands for w in c["words"] + c["targets"])
        if assigned != 1 or named:
            names.discard(name)
    return names


def command_steps(text, cwd, tree, approvals_path):
    """The steps a command line takes, and "approvals-file" when it names the approvals file."""
    commands = lex(text)
    mktemp = mktemp_names(commands)
    steps = set()
    for command in commands:
        words = command["words"]
        if any(resolve(cwd, word) == approvals_path for word in words + command["targets"] if literal(word)):
            steps.add("approvals-file")
        name, args = program(words)
        if name == "cd":
            target = [w for w in args if not w.startswith("-")]
            cwd = resolve(cwd, target[0]) if target and literal(target[0]) else None
        elif name == "git":
            steps |= git_steps(list(args), cwd)
        elif name == "gh":
            steps |= gh_steps(list(args))
        elif name == "rm":
            steps |= rm_steps(args, command["raw"][len(words) - len(args):], cwd, tree, mktemp)
    return steps


# The approvals --------------------------------------------------------------------------------------------------

def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("the field %r appears twice in one object" % key)
            result[key] = value
        return result

    def constant(name):
        raise ValueError("%s is not allowed" % name)

    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("not valid UTF-8, at byte %d" % error.start)
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except RecursionError:
        raise ValueError("nested too deeply")
    except ValueError as error:
        message = str(error)
        raise ValueError(message if "appears twice" in message or "not allowed" in message else "not valid JSON: %s" % message)


def approvals(path, today):
    """([(step, command)] that hold today, problem or None). One defect and nothing is approved."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except FileNotFoundError:
        return [], None
    except OSError as error:
        return [], "cannot be read: %s" % error.strerror
    try:
        top = strict_json(data)
    except ValueError as error:
        return [], str(error)
    if not isinstance(top, dict):
        return [], "the top level must be an object"
    if set(top) != {"approvals"}:
        return [], "; ".join(["unknown field %r" % f for f in sorted(set(top) - {"approvals"})] or ["missing field 'approvals'"])
    if not isinstance(top["approvals"], list):
        return [], "approvals must be a list"
    held = []
    for number, entry in enumerate(top["approvals"], 1):
        if not isinstance(entry, dict):
            return [], "entry %d must be an object" % number
        fields = {"step", "command", "until"}
        if set(entry) != fields:
            said = ["unknown field %r" % f for f in sorted(set(entry) - fields)] + ["missing field %r" % f for f in sorted(fields - set(entry))]
            return [], "entry %d: %s" % (number, "; ".join(said))
        if entry["step"] not in STEPS:
            return [], "entry %d: the step must be one of %s" % (number, ", ".join(STEPS))
        command = entry["command"]
        if not isinstance(command, str) or not PLAIN.match(command) or set(command) & NOT_PLAIN:
            return [], ("entry %d: the command must be one plain command: printable ASCII, no spaces at its ends, and none of "
                        "; & | < > ( ) $ ` \\" % number)
        until = entry["until"]
        try:
            last = datetime.date(*map(int, until.split("-"))) if isinstance(until, str) and DATE.match(until) else None
        except ValueError:
            last = None
        if last is None:
            return [], "entry %d: until must be a real date, written YYYY-MM-DD" % number
        if last >= today:
            held.append((entry["step"], command))
    return held, None


# The hook -------------------------------------------------------------------------------------------------------

def toplevel(cwd):
    try:
        result = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, ValueError, subprocess.SubprocessError):
        return os.path.realpath(cwd)
    found = result.stdout.decode("utf-8", errors="replace").strip()
    return os.path.realpath(found) if result.returncode == 0 and found else os.path.realpath(cwd)


def decide(call, environ, today):
    """None when the call goes ahead, or the message that denies it."""
    if not isinstance(call, dict) or not isinstance(call.get("tool_name"), str):
        raise Denied("the call names no tool")
    tool, given = call["tool_name"], call.get("tool_input")
    if tool != "Bash" and tool not in FILE_TOOLS:
        return None
    if not isinstance(given, dict):
        raise Denied("the call has no input")
    cwd = call.get("cwd") if isinstance(call.get("cwd"), str) and call.get("cwd") else os.getcwd()
    cwd = os.path.realpath(cwd)
    project = environ.get("CLAUDE_PROJECT_DIR") or toplevel(cwd)
    approvals_path = os.path.realpath(os.path.join(project, APPROVALS))
    if tool in FILE_TOOLS:
        path = given.get(FILE_TOOLS[tool])
        if not isinstance(path, str):
            raise Denied("the %s call has no path" % tool)
        if resolve(cwd, path) in (approvals_path, None):
            return "tripwire: approvals-file. Only the owner writes %s, and no approval covers it." % APPROVALS
        return None
    command = given.get("command")
    if not isinstance(command, str):
        raise Denied("the Bash call has no command")
    steps = command_steps(command, cwd, toplevel(cwd), approvals_path)
    if not steps:
        return None
    if "approvals-file" in steps:
        return "tripwire: approvals-file. The command names %s. Only the owner writes it, and no approval covers it." % APPROVALS
    held, problem = approvals(approvals_path, today)
    missing = sorted(step for step in steps if (step, command) not in held)
    if not missing:
        return None
    lines = ["tripwire: %s. This step cannot be undone, and no approval names it and this exact command." % step for step in missing]
    if problem:
        lines.append("The approvals file %s approves nothing: %s." % (APPROVALS, problem))
    if PLAIN.match(command) and not set(command) & NOT_PLAIN:
        lines.append("Ask the owner. To approve it, the owner adds to %s, with the last day it holds:" % APPROVALS)
        lines += ["  " + json.dumps({"step": step, "command": command, "until": "YYYY-MM-DD"}) for step in missing]
    else:
        lines.append("An approval names one plain command, so this one cannot be approved as written. Ask the owner, and run "
                     "the step on its own line.")
    lines.append("The tripwire catches the usual spellings only, and is not a lock: see checks/README.md.")
    return "\n".join(lines)


def main():
    try:
        data = sys.stdin.buffer.read()
        try:
            call = strict_json(data)
        except ValueError as error:
            raise Denied("the input is not a call it can read: %s" % error)
        message = decide(call, os.environ, datetime.date.today())
    except Denied as error:
        message = "tripwire: %s. Denied, because the tripwire cannot read the call." % error
    except BaseException as error:  # noqa: B902 - any failure denies; the hook exits 0 or 2 and nothing else
        message = "tripwire: denied, because the hook failed: %s" % type(error).__name__
    if message is None:
        return 0
    try:
        sys.stderr.write(message.encode("ascii", errors="backslashreplace").decode("ascii") + "\n")
        sys.stderr.flush()
    except BaseException:  # noqa: B902
        pass
    return 2


if __name__ == "__main__":
    code = 2
    try:
        code = main()
    finally:
        os._exit(code)
