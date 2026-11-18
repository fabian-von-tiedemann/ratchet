#!/usr/bin/env python3
"""A PreToolUse hook for Claude Code: a step that cannot be undone waits for an approval that names it.

The reference check for ratchet.irreversible-waits. Claude Code runs it before each tool call that its matcher
names, with the call as JSON on stdin. It exits 0 to let the call run, and 2, with the reason on stderr, to deny
it. It denies a Bash command that takes one of five steps, unless an approval names the step and the exact
command:

- force-push: a push that rewrites or removes a ref on the remote (--force, --force-with-lease, a refspec with
  +, --mirror, --prune, --delete, a refspec with no source), or the same through gh
- tag: creating, moving or deleting a tag, locally or on the remote, or pushing one
- release: creating, changing or deleting a release
- delete-outside: deleting a path outside the working tree, the working tree itself, or its .git
- settings: changing the repository's settings, through gh or the GitHub API

It also denies, and never lets an approval reach, a command it cannot read with certainty: eval, sh -c, an
alias, a program or an argument that only a substitution names, and the like. And it denies a command, or a
file tool, that touches the approvals file, which the owner writes.

The approvals are in .claude/ratchet-approvals.json in the project directory, read strictly. See checks/README.md.

What it stands against is an agent's mistake. It does not stand against an agent that means to get round it:
such an agent can write the approvals file another way, run the step from a script or another language, or
change the settings that run the hook.

One file, standard library only, so that a project can copy it. Run on Python 3.9 and 3.12.
"""

import datetime
import json
import os
import re
import stat
import subprocess
import sys
import tempfile

APPROVALS = os.path.join(".claude", "ratchet-approvals.json")
APPROVALS_NAME = "ratchet-approvals.json"
STEPS = ("force-push", "tag", "release", "delete-outside", "settings")
UNREADABLE = "unreadable"
FILE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
APPROVAL_FIELDS = ("step", "command", "until", "reason")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
# What an approved command may hold: printable ASCII, and none of the marks that join, redirect or expand.
PLAIN_COMMAND = re.compile(r"^[ !\"%+,\-./0-9:=?@A-Z\[\]^_a-z{}~']+\Z")
PRINTABLE = re.compile(r"^[ -~]*\Z")
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\+?=")
REF_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._/-]*\Z")
# A directory that mktemp -d makes in the temporary directory, by its default template.
MKTEMP_NAME = re.compile(r"^tmp\.[A-Za-z0-9]{6,}\Z")
# Characters an unquoted path to delete may hold. Anything else unquoted is refused.
SAFE_UNQUOTED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._/+-,@%:=~*?")
MAX_CWDS = 32

SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "mksh", "ash", "fish", "csh", "tcsh", "yash", "posh"}
DELETERS = {"rm", "rmdir", "unlink", "shred", "srm"}
# Programs that only print or test what they are given: an argument of theirs is never run.
QUIET = {"echo", "printf", "true", "false", ":", "test", "[", "cat", "ls", "grep", "egrep", "fgrep", "rg", "head",
         "tail", "wc", "sort", "uniq", "which", "type", "basename", "dirname", "realpath", "readlink", "stat",
         "file", "date", "sleep", "pwd", "mkdir", "touch", "jq", "diff", "less", "more", "man"}
# Programs that run a string, or their arguments, as commands, in a way this hook does not follow.
RUNS_STRINGS = {"eval", "watch", "parallel", "su", "chroot", "nsenter", "unshare", "script", "expect", "coproc",
                "osascript"}
VARIABLE_BUILTINS = {"export", "declare", "local", "readonly", "typeset", "read", "unset", "getopts", "mapfile",
                     "readarray", "printf", "let", "vared", "zparseopts"}
SAFE_GIT_ENV = {"GIT_EDITOR", "GIT_SEQUENCE_EDITOR", "GIT_PAGER", "GIT_TERMINAL_PROMPT", "GIT_AUTHOR_NAME",
                "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
                "GIT_COMMITTER_DATE", "GIT_OPTIONAL_LOCKS", "GIT_TRACE", "GIT_ADVICE"}
# Configuration that `git -c` may set for one command: none of it changes what a push, a tag or a clean does.
SAFE_GIT_CONFIG = ("user.", "color.", "core.pager", "core.quotepath", "core.editor", "advice.", "commit.gpgsign",
                   "tag.gpgsign", "init.defaultbranch", "safe.directory", "log.", "diff.", "pager.", "format.",
                   "column.", "i18n.", "merge.conflictstyle", "pull.rebase", "pull.ff", "gc.auto",
                   "maintenance.auto", "credential.helper")
# Configuration whose change makes a later git command do something else: an alias, where and how a push goes.
RISKY_GIT_CONFIG = ("alias.", "remote.", "push.", "include.", "includeif.", "url.", "branch.", "core.hookspath",
                    "core.sshcommand", "core.worktree", "core.bare")
GIT_COMMANDS = {
    "add", "am", "annotate", "apply", "archive", "bisect", "blame", "branch", "bundle", "cat-file", "check-attr",
    "check-ignore", "check-mailmap", "check-ref-format", "checkout", "cherry", "cherry-pick", "citool", "clean",
    "clone", "commit", "commit-graph", "commit-tree", "config", "count-objects", "describe", "diff", "diff-files",
    "diff-index", "diff-tree", "difftool", "fetch", "for-each-ref", "format-patch", "fsck", "gc", "grep",
    "hash-object", "help", "init", "interpret-trailers", "log", "ls-files", "ls-remote", "ls-tree", "maintenance",
    "merge", "merge-base", "merge-file", "merge-tree", "mergetool", "mktag", "mktree", "mv", "name-rev", "notes",
    "pull", "push", "range-diff", "read-tree", "rebase", "reflog", "remote", "repack", "replace", "rerere", "reset",
    "restore", "rev-list", "rev-parse", "revert", "rm", "shortlog", "show", "show-branch", "show-ref",
    "sparse-checkout", "stash", "status", "stripspace", "submodule", "switch", "symbolic-ref", "tag",
    "update-index", "update-ref", "var", "verify-commit", "verify-pack", "verify-tag", "version", "whatchanged",
    "worktree", "write-tree",
}
GH_QUIET = {"pr", "issue", "run", "label", "cache", "gist", "auth", "config", "org", "codespace", "cs", "project",
            "search", "status", "browse", "attestation", "completion", "help", "version", "ruleset", "ssh-key",
            "gpg-key", "co"}
# Parts of a repository's path in the API under which a change is a change of the repository's settings.
SETTINGS_PATHS = {"rulesets", "collaborators", "invitations", "hooks", "keys", "environments", "pages", "topics",
                  "vulnerability-alerts", "automated-security-fixes", "private-vulnerability-reporting", "transfer",
                  "properties", "autolinks", "interaction-limits", "dispatches", "immutable-releases", "lfs",
                  "secret-scanning", "code-security-configuration", "tags", "teams", "subscription"}


class Unreadable(Exception):
    """The command cannot be read with certainty."""


# ---------------------------------------------------------------- reading a command line

class Word:
    """One word of a command line, as parts: ("lit", text, quoted), ("var", name, quoted), ("dyn", why, quoted),
    ("sub", program, quoted) for $(...) and `...`, and ("proc", program, False) for <(...) and >(...)."""

    def __init__(self, parts, raw):
        self.parts = [part for part in parts if not (part[0] == "lit" and part[1] == "")] or parts[:1]
        self.raw = raw

    def programs(self):
        return [part[1] for part in self.parts if part[0] in ("sub", "proc")]

    def plain(self):
        """The text of a word that is one unquoted literal, or None."""
        if len(self.parts) == 1 and self.parts[0][0] == "lit" and not self.parts[0][2]:
            return self.parts[0][1]
        return None

    def braces(self):
        shape = "".join(part[1] if part[0] == "lit" and not part[2] else "x" for part in self.parts)
        return re.search(r"\{[^{}]*(,|\.\.)[^{}]*\}", shape) is not None

    def value(self):
        """The text the shell makes of the word, when it is plain text, or None."""
        if any(part[0] != "lit" for part in self.parts) or self.braces():
            return None
        first = self.parts[0] if self.parts else ("lit", "", True)
        text = "".join(part[1] for part in self.parts)
        if not first[2] and first[1].startswith("="):
            return None
        if not first[2] and first[1].startswith("~"):
            head = first[1].split("/", 1)[0]
            if head != "~":
                return None
            return os.path.expanduser("~") + text[1:]
        return text

    def glob(self):
        return any(part[0] == "lit" and not part[2] and re.search(r"[*?\[]", part[1]) for part in self.parts)

    def unquoted(self):
        return "".join(part[1] for part in self.parts if part[0] == "lit" and not part[2])

    def exact_variable(self):
        """(name, quoted) when the word is one variable and nothing else."""
        if len(self.parts) == 1 and self.parts[0][0] == "var":
            return self.parts[0][1], self.parts[0][2]
        return None

    def assignment(self):
        """(name, the value as a Word) when the word assigns a variable."""
        if not self.parts or self.parts[0][0] != "lit" or self.parts[0][2]:
            return None
        match = ASSIGNMENT.match(self.parts[0][1])
        if not match:
            return None
        rest = [("lit", self.parts[0][1][match.end():], False)] + self.parts[1:]
        return match.group(1), Word(rest, self.raw[match.end():])


def dynamic(why):
    return Word([("dyn", why, False)], "<%s>" % why)


class Command:
    def __init__(self, depth, first):
        self.words = []
        self.assigns = []
        self.redirects = []
        self.depth = depth
        self.first = first
        self.pipeline = False
        self.background = False
        self.data = False

    def all_words(self):
        return self.words + [value for _, value in self.assigns] + [target for _, target in self.redirects]


class Program:
    def __init__(self):
        self.commands = []


class Context:
    """What one command line holds as a whole."""

    def __init__(self):
        self.arith = False
        self.functions = False
        self.loop_names = set()
        self.expansion_names = set()


class Lexer:
    OPERATORS = ("&&", "||", ";;", ";&", "|&", "&>>", "&>", "<<<", "<<-", "<<", "<>", "<&", ">&", ">>", ">|",
                 "((", "|", "&", ";", "(", ")", "<", ">")

    def __init__(self, text, context):
        self.s = text
        self.i = 0
        self.context = context
        self.heredocs = []

    def peek(self, offset=0):
        index = self.i + offset
        return self.s[index] if index < len(self.s) else ""

    def token(self):
        """("word", Word), ("op", text), ("newline", None) or ("end", None)."""
        while True:
            c = self.peek()
            if c in (" ", "\t"):
                self.i += 1
            elif c == "\\" and self.peek(1) == "\n":
                self.i += 2
            elif c == "#":
                while self.peek() not in ("", "\n"):
                    self.i += 1
            else:
                break
        c = self.peek()
        if c == "":
            if self.heredocs:
                raise Unreadable("a here-document is not closed")
            return ("end", None)
        if c == "\n":
            self.i += 1
            self.read_heredocs()
            return ("newline", None)
        if c in "<>" and self.peek(1) == "(":
            return ("word", self.word())
        match = re.match(r"[0-9]+(?=[<>])", self.s[self.i:])
        if match:
            self.i += match.end()
        for operator in self.OPERATORS:
            if self.s.startswith(operator, self.i):
                self.i += len(operator)
                return ("op", operator)
        if match:
            raise Unreadable("a redirection this hook cannot read")
        return ("word", self.word())

    def read_heredocs(self):
        pending, self.heredocs = self.heredocs, []
        for delimiter, strip, quoted in pending:
            lines = []
            while True:
                if self.i >= len(self.s):
                    raise Unreadable("a here-document is not closed")
                end = self.s.find("\n", self.i)
                end = len(self.s) if end < 0 else end
                line = self.s[self.i:end]
                self.i = min(end + 1, len(self.s))
                if (line.lstrip("\t") if strip else line) == delimiter:
                    break
                lines.append(line)
            body = "\n".join(lines)
            if not quoted and ("$(" in body or "`" in body):
                raise Unreadable("a here-document runs a command substitution")

    def word(self):
        start = self.i
        parts = []
        if self.peek() in "<>" and self.peek(1) == "(":
            self.i += 2
            parts.append(("proc", Parser(self, closer=")").parse(), False))
        while True:
            c = self.peek()
            if c == "" or c in " \t\n|&;()<>":
                break
            if c == "\\":
                if self.peek(1) == "\n":
                    self.i += 2
                    continue
                if self.peek(1) == "":
                    raise Unreadable("a backslash at the end")
                parts.append(("lit", self.peek(1), True))
                self.i += 2
            elif c == "'":
                end = self.s.find("'", self.i + 1)
                if end < 0:
                    raise Unreadable("a quotation mark is not closed")
                parts.append(("lit", self.s[self.i + 1:end], True))
                self.i = end + 1
            elif c == '"':
                self.i += 1
                self.double_quoted(parts)
            elif c == "$":
                self.dollar(parts, False)
            elif c == "`":
                parts.append(("sub", self.backticks(False), False))
            else:
                parts.append(("lit", c, False))
                self.i += 1
        if self.i == start:
            raise Unreadable("an empty word")
        return Word(merge(parts), self.s[start:self.i])

    def double_quoted(self, parts):
        while True:
            c = self.peek()
            if c == "":
                raise Unreadable("a quotation mark is not closed")
            if c == '"':
                self.i += 1
                return
            if c == "\\":
                following = self.peek(1)
                if following == "\n":
                    self.i += 2
                elif following in ('$', '`', '"', "\\"):
                    parts.append(("lit", following, True))
                    self.i += 2
                else:
                    parts.append(("lit", "\\", True))
                    self.i += 1
            elif c == "$":
                self.dollar(parts, True)
            elif c == "`":
                parts.append(("sub", self.backticks(True), True))
            else:
                parts.append(("lit", c, True))
                self.i += 1

    def dollar(self, parts, quoted):
        following = self.peek(1)
        if following == "'" and not quoted:
            end = self.i + 2
            while end < len(self.s) and self.s[end] != "'":
                end += 2 if self.s[end] == "\\" else 1
            if end >= len(self.s):
                raise Unreadable("a quotation mark is not closed")
            body = self.s[self.i + 2:end]
            parts.append(("dyn", "an escape in $'...'", True) if "\\" in body else ("lit", body, True))
            self.i = end + 1
        elif following == '"' and not quoted:
            self.i += 2
            self.double_quoted(parts)
        elif following == "(" and self.peek(2) == "(":
            depth, index = 0, self.i + 1
            while index < len(self.s):
                if self.s[index] == "(":
                    depth += 1
                elif self.s[index] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                index += 1
            if index >= len(self.s):
                raise Unreadable("an arithmetic expansion is not closed")
            body = self.s[self.i + 3:index - 1]
            if "$(" in body or "`" in body:
                raise Unreadable("a command substitution in an arithmetic expansion")
            self.context.arith = True
            parts.append(("dyn", "an arithmetic expansion", quoted))
            self.i = index + 1
        elif following == "(":
            self.i += 2
            parts.append(("sub", Parser(self, closer=")").parse(), quoted))
        elif following == "{":
            depth, index = 0, self.i + 1
            while index < len(self.s):
                if self.s[index] == "{":
                    depth += 1
                elif self.s[index] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                index += 1
            if index >= len(self.s):
                raise Unreadable("a parameter expansion is not closed")
            body = self.s[self.i + 2:index]
            self.i = index + 1
            if IDENTIFIER.match(body):
                parts.append(("var", body, quoted))
                return
            if "$(" in body or "`" in body:
                raise Unreadable("a command substitution in a parameter expansion")
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):?=", body)
            if match:
                self.context.expansion_names.add(match.group(1))
            parts.append(("dyn", "${%s}" % body, quoted))
        elif re.match(r"[A-Za-z_]", following):
            match = re.match(r"[A-Za-z_][A-Za-z0-9_]*", self.s[self.i + 1:])
            parts.append(("var", match.group(0), quoted))
            self.i += 1 + match.end()
        elif following and following in "0123456789@*#?$!-_":
            parts.append(("dyn", "$" + following, quoted))
            self.i += 2
        else:
            parts.append(("lit", "$", quoted))
            self.i += 1

    def backticks(self, quoted):
        index = self.i + 1
        inner = []
        while True:
            if index >= len(self.s):
                raise Unreadable("a backtick is not closed")
            c = self.s[index]
            if c == "\\" and index + 1 < len(self.s) and self.s[index + 1] in ("\\", "`", "$") + (('"',) if quoted else ()):
                inner.append(self.s[index + 1])
                index += 2
            elif c == "`":
                break
            else:
                inner.append(c)
                index += 1
        self.i = index + 1
        return parse("".join(inner), self.context)


def merge(parts):
    merged = []
    for part in parts:
        if merged and part[0] == "lit" and merged[-1][0] == "lit" and merged[-1][2] == part[2]:
            merged[-1] = ("lit", merged[-1][1] + part[1], part[2])
        else:
            merged.append(part)
    return merged


class Parser:
    OPENERS = {"(": "(", "{": "{", "if": "if", "while": "loop", "until": "loop", "for": "loop", "select": "loop"}
    CLOSERS = {")": "(", "}": "{", "fi": "if", "done": "loop"}

    def __init__(self, lexer, closer=None):
        self.lexer = lexer
        self.closer = closer
        self.program = Program()
        self.stack = []
        self.command = None
        self.first = True
        self.andor = []
        self.pipe_next = False

    def start(self):
        command = Command(len(self.stack), self.first)
        command.pipeline = self.pipe_next
        self.pipe_next = False
        self.first = False
        self.program.commands.append(command)
        self.andor.append(command)
        self.command = command
        return command

    def end_command(self):
        self.command = None

    def end_list(self, background):
        if background:
            for command in self.andor:
                command.background = True
        self.andor = []
        self.first = True
        self.command = None

    def parse(self):
        lexer = self.lexer
        while True:
            kind, value = lexer.token()
            if kind == "end":
                if self.closer:
                    raise Unreadable("a command substitution is not closed")
                if self.stack:
                    raise Unreadable("a compound command is not closed")
                return self.program
            if kind == "newline":
                self.end_list(False)
            elif kind == "op":
                if self.operator(value):
                    return self.program
            else:
                self.add_word(value)

    def operator(self, op):
        if op in (";", "&"):
            self.end_list(op == "&")
        elif op in ("&&", "||"):
            self.end_command()
        elif op in ("|", "|&"):
            if self.command is not None:
                self.command.pipeline = True
            self.pipe_next = True
            self.end_command()
        elif op == "(":
            if self.command is not None:
                if len(self.command.words) == 1 and not self.command.assigns:
                    kind, value = self.lexer.token()
                    if (kind, value) != ("op", ")"):
                        raise Unreadable("a parenthesis inside a command")
                    self.program.commands.remove(self.command)
                    self.lexer.context.functions = True
                    self.end_command()
                    return False
                raise Unreadable("a parenthesis inside a command")
            self.stack.append("(")
        elif op == ")":
            if not self.stack:
                if self.closer == ")":
                    return True
                raise Unreadable("a parenthesis that closes nothing")
            if self.stack.pop() != "(":
                raise Unreadable("a parenthesis that closes something else")
            self.end_command()
        elif op == "((":
            if self.command is not None:
                raise Unreadable("a parenthesis inside a command")
            depth, s, begin = 2, self.lexer.s, self.lexer.i
            while self.lexer.i < len(s) and depth:
                depth += {"(": 1, ")": -1}.get(s[self.lexer.i], 0)
                self.lexer.i += 1
            if depth:
                raise Unreadable("an arithmetic command is not closed")
            if "$(" in s[begin:self.lexer.i] or "`" in s[begin:self.lexer.i]:
                raise Unreadable("a command substitution in an arithmetic command")
            self.lexer.context.arith = True
        elif op in (";;", ";&"):
            raise Unreadable("a case statement")
        else:
            kind, target = self.lexer.token()
            if kind != "word":
                raise Unreadable("a redirection with no target")
            command = self.command if self.command is not None else self.start()
            if op in ("<<", "<<-"):
                delimiter = target.value()
                if delimiter is None and not all(part[0] == "lit" for part in target.parts):
                    raise Unreadable("a here-document whose delimiter is not plain")
                delimiter = "".join(part[1] for part in target.parts)
                quoted = any(part[2] for part in target.parts)
                self.lexer.heredocs.append((delimiter, op == "<<-", quoted))
            else:
                command.redirects.append((op, target))
        return False

    def add_word(self, word):
        if self.command is None:
            reserved = word.plain()
            if reserved in ("then", "do", "else", "elif", "!"):
                return
            if reserved in ("if", "while", "until", "{"):
                self.stack.append(self.OPENERS[reserved])
                return
            if reserved in self.CLOSERS and reserved != ")":
                if not self.stack or self.stack.pop() != self.CLOSERS[reserved]:
                    raise Unreadable("%s closes nothing" % reserved)
                return
            if reserved in ("for", "select"):
                self.loop()
                return
            if reserved == "case":
                raise Unreadable("a case statement")
            if reserved == "function":
                kind, name = self.lexer.token()
                if kind != "word":
                    raise Unreadable("a function with no name")
                self.lexer.context.functions = True
                return
            if reserved == "[[":
                self.condition()
                return
            command = self.start()
            assignment = word.assignment()
            if assignment:
                command.assigns.append(assignment)
                return
            command.words.append(word)
            return
        assignment = word.assignment()
        if not self.command.words and assignment:
            self.command.assigns.append(assignment)
        else:
            self.command.words.append(word)

    def loop(self):
        kind, name = self.lexer.token()
        if kind != "word" or not name.plain() or not IDENTIFIER.match(name.plain()):
            raise Unreadable("a for loop this hook cannot read")
        self.lexer.context.loop_names.add(name.plain())
        data = self.start()
        data.data = True
        kind, value = self.lexer.token()
        while kind == "newline" or (kind, value) == ("op", ";"):
            kind, value = self.lexer.token()
        if kind == "word" and value.plain() == "in":
            while True:
                kind, value = self.lexer.token()
                if kind == "word":
                    data.words.append(value)
                elif kind == "newline" or (kind, value) == ("op", ";"):
                    break
                else:
                    raise Unreadable("a for loop this hook cannot read")
        elif kind == "word" and value.plain() == "do":
            pass
        else:
            raise Unreadable("a for loop this hook cannot read")
        self.end_list(False)
        self.stack.append("loop")

    def condition(self):
        data = self.start()
        data.data = True
        while True:
            kind, value = self.lexer.token()
            if kind == "word":
                if value.plain() == "]]":
                    return
                data.words.append(value)
            elif kind in ("end", "newline"):
                raise Unreadable("a [[ that is not closed")


def parse(text, context):
    return Parser(Lexer(text, context)).parse()


# ---------------------------------------------------------------- what a command does

class Finding:
    def __init__(self, step, why):
        self.step = step
        self.why = why


class State:
    def __init__(self, root, cwd, context):
        self.root = os.path.realpath(root)
        self.cwds = {os.path.realpath(cwd)}
        self.context = context
        self.findings = []
        self.temps = set()
        self.live = set()
        self.git_taint = False
        self.deletes = False
        self.links = False

    def child(self):
        child = State.__new__(State)
        child.__dict__.update(self.__dict__)
        child.cwds = set(self.cwds)
        child.live = set(self.live)
        return child

    def finish(self, child):
        self.deletes = self.deletes or child.deletes
        self.links = self.links or child.links

    def add(self, step, why):
        self.findings.append(Finding(step, why))

    def unreadable(self, why):
        self.add(UNREADABLE, why)


def analyze(command, cwd, root):
    """Every finding for a Bash command: the steps it takes, and why it cannot be read."""
    findings = []
    context = Context()
    try:
        program = parse(command, context)
    except Unreadable as error:
        return findings + [Finding(UNREADABLE, str(error))]
    except RecursionError:
        return findings + [Finding(UNREADABLE, "it is nested too deeply")]
    state = State(root, cwd, context)
    state.temps = temporary_names(program, context)
    run_program(program, state, top=True)
    if state.links and state.deletes:
        state.unreadable("it makes a link and deletes, and a link it makes could lead outside the working tree")
    return findings + state.findings


def program_name(word):
    value = word.value()
    return None if value is None else os.path.basename(value.rstrip("/")) or value


def is_mktemp(word):
    if len(word.parts) != 1 or word.parts[0][0] != "sub":
        return False
    commands = word.parts[0][1].commands
    if len(commands) != 1 or commands[0].assigns or commands[0].redirects or not commands[0].words:
        return False
    values = [w.value() for w in commands[0].words]
    if None in values or os.path.basename(values[0]) != "mktemp":
        return False
    directory, index, templates = False, 1, 0
    while index < len(values):
        value = values[index]
        if value in ("-d", "--directory"):
            directory = True
        elif value in ("-q", "--quiet") or value.startswith("--tmpdir=") or value.startswith("--suffix="):
            pass
        elif value in ("-t", "-p", "--tmpdir"):
            index += 1
        elif re.match(r"^-[dqt]+\Z", value):
            directory = directory or "d" in value
            if value.endswith("t"):
                index += 1
        elif value.startswith("-"):
            return False
        else:
            templates += 1
        index += 1
    return directory and templates <= 1


def temporary_names(program, context):
    """The variables that only ever hold a directory from mktemp -d, assigned at the top of the line."""
    if context.arith or context.functions:
        return set()
    good, bad = set(), set(context.loop_names) | set(context.expansion_names)
    blocked = [False]

    def collect(program, top):
        for command in program.commands:
            for word in command.all_words():
                for inner in word.programs():
                    collect(inner, False)
            if command.data:
                continue
            for name, value in command.assigns:
                if (top and not command.words and command.depth == 0 and command.first and not command.pipeline
                        and not command.background and is_mktemp(value)):
                    good.add(name)
                else:
                    bad.add(name)
            if not command.words:
                continue
            name = program_name(command.words[0])
            if name in ("source", ".", "eval"):
                blocked[0] = True
            if name == "printf":
                values = [word.value() for word in command.words]
                for index, value in enumerate(values[:-1]):
                    if value == "-v":
                        if values[index + 1] is None:
                            blocked[0] = True
                        else:
                            bad.add(values[index + 1])
            elif name in VARIABLE_BUILTINS:
                for word in command.words[1:]:
                    value = word.value()
                    if value is None:
                        blocked[0] = True
                        continue
                    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)", value)
                    if match:
                        bad.add(match.group(1))
            if name == "trap":
                action = trap_action(command.words)
                if action is not None and action.value() is not None:
                    try:
                        collect(parse(action.value(), context), False)
                    except Unreadable:
                        blocked[0] = True

    collect(program, True)
    return set() if blocked[0] or context.arith or context.functions else good - bad


def trap_action(words):
    index = 1
    if index < len(words) and words[index].value() == "--":
        index += 1
    if index >= len(words) or index + 1 >= len(words):
        return None
    value = words[index].value()
    if value in ("-p", "-l", "-"):
        return None
    return words[index]


def touches_approvals(word, state):
    """Whether a word may lead to the approvals file. A word with a space in it is text, such as a message."""
    text = "".join(part[1] for part in word.parts if part[0] == "lit")
    if APPROVALS_NAME not in text or re.search(r"\s", text):
        return False
    value = word.value()
    if value is None or (".claude/" + APPROVALS_NAME) in value:
        return True
    target = os.path.realpath(os.path.join(state.root, APPROVALS))
    for base in ({"/"} if os.path.isabs(value) else state.cwds):
        if base is None or os.path.realpath(os.path.join(base, value)) == target:
            return True
    return False


def run_program(program, state, top=False):
    for command in program.commands:
        for word in command.all_words():
            if touches_approvals(word, state):
                state.add("approvals", "%s may lead to the approvals file, which only the owner writes" % word.raw)
            for inner in word.programs():
                child = state.child()
                run_program(inner, child)
                state.finish(child)
        if command.data:
            continue
        env_taint = False
        for name, value in command.assigns:
            if name.startswith("GIT_") and name not in SAFE_GIT_ENV:
                if command.words:
                    env_taint = True
                else:
                    state.git_taint = True
            if top and not command.words and name in state.temps and is_mktemp(value) and command.depth == 0:
                state.live.add(name)
        if command.words:
            run_words(command.words, state, env_taint, None)


def bases_for(state, override):
    return override if override is not None else set(state.cwds)


def resolve_dir(bases, word):
    value = word.value()
    if value is None:
        return {None}
    result = set()
    for base in bases:
        if base is None and not os.path.isabs(value):
            result.add(None)
            continue
        joined = os.path.join(base or "/", value)
        result.add(os.path.realpath(joined))
        result.add(os.path.normpath(joined))
    return result


def run_words(words, state, env_taint, override):
    """A simple command, from its program on."""
    if not words:
        return
    name = program_name(words[0])
    if name is None:
        state.unreadable("the program %s is not plain text" % words[0].raw)
        return
    args = words[1:]
    if name in ("cd", "pushd"):
        targets = [w for w in args if not (w.value() or "").startswith("-") or w.value() == "-"]
        if not targets:
            new = {os.path.expanduser("~")}
        elif targets[0].value() == "-":
            new = {None}
        else:
            new = resolve_dir(state.cwds, targets[0])
        state.cwds |= new
        if len(state.cwds) > MAX_CWDS:
            state.cwds.add(None)
        return
    if name == "popd":
        state.cwds.add(None)
        return
    if name == "ln":
        state.links = True
        return
    if name in QUIET:
        return
    if name in ("source", "."):
        return
    if name in RUNS_STRINGS:
        state.unreadable("%s runs a string or its arguments as commands" % name)
        return
    if name == "alias":
        if any((w.value() or "=") .find("=") >= 0 for w in args):
            state.unreadable("it defines an alias, which can stand for any command")
        return
    if name == "trap":
        action = trap_action(words)
        if action is None:
            return
        if action.value() is None:
            state.unreadable("the action of trap is not plain text")
            return
        try:
            inner = parse(action.value(), state.context)
        except Unreadable as error:
            state.unreadable("the action of trap: %s" % error)
            return
        child = state.child()
        run_program(inner, child)
        state.finish(child)
        return
    if name in SHELLS:
        run_shell(name, args, state)
        return
    if name == "busybox":
        run_words(args, state, env_taint, override)
        return
    if name in WRAPPERS:
        WRAPPERS[name](args, state, env_taint, override)
        return
    if name in DELETERS:
        run_delete(name, args, state, override)
        return
    if name == "find":
        run_find(args, state, override)
        return
    if name == "rsync":
        run_rsync(args, state, override)
        return
    if name == "git":
        run_git(args, state, env_taint or state.git_taint, override)
        return
    if name == "gh":
        run_gh(args, state)
        return
    if name == "ssh":
        run_ssh(args, state)
        return
    if name in VARIABLE_BUILTINS:
        for word in args:
            match = re.match(r"^(GIT_[A-Za-z0-9_]*)", word.value() or "")
            if match and match.group(1) not in SAFE_GIT_ENV:
                state.git_taint = True
        return
    # Any other program: an argument that would take a step if it were a command may be run by it.
    triggers = {"git", "gh", "find", "rsync", "busybox", "env", "sudo", "doas", "xargs", "nohup", "timeout", "eval"} | DELETERS | SHELLS
    for index in range(1, len(words)):
        if program_name(words[index]) in triggers:
            child = state.child()
            child.findings = []
            child.cwds = {None}
            run_words(words[index:], child, env_taint, None)
            state.finish(child)
            for finding in child.findings:
                state.add(finding.step, "%s may run its arguments: %s" % (name, finding.why))
            if child.findings:
                return


def run_shell(name, args, state):
    index = 0
    while index < len(args):
        value = args[index].value()
        if value is None:
            state.unreadable("an option of %s is not plain text" % name)
            return
        if value in ("--version", "--help"):
            return
        if value == "-" or value == "--":
            index += 1
            break
        if value.startswith("--"):
            index += 1
            continue
        if re.match(r"^[-+][A-Za-z]+\Z", value):
            if "c" in value[1:] and value[0] == "-":
                state.unreadable("%s -c runs a string as commands" % name)
                return
            if "s" in value[1:] and value[0] == "-":
                state.unreadable("%s -s reads its commands from standard input" % name)
                return
            index += 2 if value[-1] in "oO" else 1
            continue
        break
    if index >= len(args):
        state.unreadable("%s reads its commands from standard input" % name)
        return
    script = args[index].value()
    if script is None or script.startswith("/dev/") or script == "-":
        state.unreadable("the script %s runs is not a plain file name" % name)


def run_ssh(args, state):
    index, positional = 0, []
    with_value = set("BbcDEeFIiJLlmOoPpQRSWw")
    while index < len(args):
        value = args[index].value()
        if value is None:
            positional.append(None)
        elif positional:
            positional.append(value)
        elif value.startswith("-") and len(value) > 1:
            if value[-1] in with_value and len(value) == 2:
                index += 1
        else:
            positional.append(value)
        index += 1
    if len(positional) > 1:
        state.unreadable("ssh runs a command on another machine")


# Wrappers: each strips its own options and runs the rest as a command.

def wrapper(no_value, with_value, after=None):
    def run(args, state, env_taint, override):
        index = 0
        while index < len(args):
            value = args[index].value()
            if value is None:
                state.unreadable("an option of a wrapper is not plain text")
                return
            if value == "--":
                index += 1
                break
            if not value.startswith("-") or value == "-":
                break
            option = value.split("=", 1)[0]
            if option in with_value:
                index += 1 if "=" in value or (len(option) == 2 and len(value) > 2) else 2
            elif option in no_value or (len(value) > 2 and value[1] != "-" and value[:2] in with_value):
                index += 1
            else:
                state.unreadable("a wrapper option %s this hook does not know" % value)
                return
        if after:
            index = after(args, index, state)
            if index is None:
                return
        if index < len(args):
            run_words(args[index:], state, env_taint, override)
    return run


def run_env(args, state, env_taint, override):
    index = 0
    while index < len(args):
        word = args[index]
        value = word.value()
        assignment = word.assignment()
        if assignment:
            if assignment[0].startswith("GIT_") and assignment[0] not in SAFE_GIT_ENV:
                env_taint = True
            index += 1
            continue
        if value is None:
            state.unreadable("an argument of env is not plain text")
            return
        if value in ("-i", "-0", "-v", "--ignore-environment", "--null", "--debug", "-"):
            index += 1
        elif value in ("-u", "--unset"):
            index += 2
        elif value.startswith("--unset=") or (value.startswith("-u") and len(value) > 2):
            index += 1
        elif value in ("-C", "--chdir") or value.startswith("--chdir=") or (value.startswith("-C") and len(value) > 2):
            if value in ("-C", "--chdir"):
                target = args[index + 1] if index + 1 < len(args) else dynamic("no directory")
                index += 2
            else:
                target = Word([("lit", value.split("=", 1)[1] if "=" in value else value[2:], True)], value)
                index += 1
            override = resolve_dir(bases_for(state, override), target)
        elif value == "--":
            index += 1
            break
        elif value.startswith("-"):
            state.unreadable("env %s is an option this hook does not follow" % value)
            return
        else:
            break
    if index < len(args):
        run_words(args[index:], state, env_taint, override)


def command_lookup(args, index, state):
    for word in args[:index]:
        if word.value() in ("-v", "-V"):
            return None
    return index


def sudo_dir(args, index, state):
    for position, word in enumerate(args[:index]):
        if word.value() in ("-D", "--chdir") or (word.value() or "").startswith("--chdir="):
            state.cwds = state.cwds | {None}
    return index


def timeout_duration(args, index, state):
    return index + 1


def xargs_run(args, state, env_taint, override):
    no_value = {"-0", "-r", "-t", "-p", "-x", "-o", "--null", "--no-run-if-empty", "--verbose", "--interactive",
                "--exit", "--open-tty"}
    with_value = {"-I", "-L", "-n", "-P", "-s", "-d", "-E", "-a", "--arg-file", "--delimiter", "--max-args",
                  "--max-procs", "--max-lines", "--replace", "--eof", "--max-chars"}
    index = 0
    while index < len(args):
        value = args[index].value()
        if value is None:
            state.unreadable("an option of xargs is not plain text")
            return
        if value == "--":
            index += 1
            break
        if not value.startswith("-"):
            break
        option = value.split("=", 1)[0]
        if option in no_value:
            index += 1
        elif option in with_value:
            index += 1 if "=" in value else 2
        elif value[:2] in with_value:
            index += 1
        else:
            state.unreadable("xargs %s is an option this hook does not know" % value)
            return
    if index >= len(args):
        return
    run_words(args[index:] + [dynamic("the arguments xargs reads")], state, env_taint, override)


WRAPPERS = {
    "env": run_env,
    "command": wrapper({"-p", "-v", "-V"}, set(), command_lookup),
    "builtin": wrapper(set(), set()),
    "exec": wrapper({"-c", "-l"}, {"-a"}),
    "nohup": wrapper(set(), set()),
    "nice": wrapper({"-N"}, {"-n", "--adjustment"}),
    "time": wrapper({"-p", "-l", "-h", "-v"}, {"-o"}),
    "timeout": wrapper({"--foreground", "--preserve-status", "-v", "--verbose", "-f", "-p"}, {"-s", "-k", "--signal", "--kill-after"}, timeout_duration),
    "sudo": wrapper({"-A", "-b", "-E", "-H", "-K", "-k", "-n", "-P", "-S", "-s", "-i", "--preserve-env", "--login", "--shell", "--non-interactive"},
                    {"-u", "-g", "-p", "-C", "-h", "-r", "-t", "-T", "-U", "-D", "--user", "--group", "--chdir"}, sudo_dir),
    "doas": wrapper({"-n", "-s", "-L"}, {"-u", "-C"}),
    "stdbuf": wrapper(set(), {"-i", "-o", "-e", "--input", "--output", "--error"}),
    "caffeinate": wrapper({"-d", "-i", "-m", "-s", "-u"}, {"-t", "-w"}),
    "xargs": xargs_run,
}


# Deleting.

def temp_roots():
    roots = set()
    for candidate in (os.environ.get("TMPDIR"), tempfile.gettempdir(), "/tmp"):
        if candidate and os.path.isabs(candidate):
            roots.add(os.path.realpath(candidate))
    return roots


def inside(state, path, allow_root=False):
    root = state.root
    path = os.path.realpath(path)
    if path == root:
        return allow_root
    try:
        if os.path.commonpath([root, path]) != root:
            return False
    except ValueError:
        return False
    git_dir = os.path.join(root, ".git")
    return not (path == git_dir or path.startswith(git_dir + os.sep))


def temporary(path):
    for root in temp_roots():
        if path == root or not path.startswith(root + os.sep):
            continue
        name = path[len(root) + 1:].split(os.sep, 1)[0]
        directory = os.path.join(root, name)
        if not MKTEMP_NAME.match(name):
            continue
        try:
            info = os.lstat(directory)
        except OSError:
            continue
        if stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid():
            return True
    return False


def resolve_target(base, value):
    """Where a path to delete leads: the last part is the entry itself, unless the path ends in / or is . or .."""
    joined = value if os.path.isabs(value) else os.path.join(base, value)
    last = os.path.basename(joined)
    if value.endswith("/") or last in (".", "..", ""):
        return os.path.realpath(joined)
    return os.path.join(os.path.realpath(os.path.dirname(joined)), last)


def check_delete(word, state, override, contents=False):
    """Whether deleting what a word names stays inside the working tree. With contents=True, what is deleted is
    inside the named directory, which may be the working tree itself."""
    state.deletes = True
    variable = word.exact_variable()
    if variable and variable[1] and variable[0] in state.temps and variable[0] in state.live:
        return
    value = word.value()
    if value is None:
        state.unreadable("the path %s to delete is not plain text" % word.raw)
        return
    if set(word.unquoted()) - SAFE_UNQUOTED:
        state.unreadable("the path %s to delete holds a character this hook does not read unquoted" % word.raw)
        return
    if value == "":
        return
    parts = value.split("/")
    if word.glob():
        globbed = [i for i, part in enumerate(parts) if re.search(r"[*?\[]", part)]
        first = globbed[0]
        if "[" in value:
            state.unreadable("the path %s to delete has a pattern with [" % word.raw)
            return
        if any(parts[i].startswith(".") for i in globbed):
            state.add("delete-outside", "the pattern %s may match .." % word.raw)
            return
        if first != len(parts) - 1:
            state.unreadable("the path %s to delete has a pattern before its last part" % word.raw)
            return
        value = "/".join(parts[:first]) or ("/" if value.startswith("/") else ".")
        contents = True
    bases = {None} if os.path.isabs(value) else bases_for(state, override)
    for base in bases:
        if base is None and not os.path.isabs(value):
            state.unreadable("the directory %s is deleted from is not known" % word.raw)
            return
        target = os.path.realpath(value if os.path.isabs(value) else os.path.join(base, value)) if contents \
            else resolve_target(base or "/", value)
        if inside(state, target, allow_root=contents) or temporary(target):
            continue
        state.add("delete-outside", "%s is outside the working tree" % word.raw)
        return


def run_delete(name, args, state, override):
    operands, options_done, index = [], False, 0
    while index < len(args):
        word = args[index]
        value = word.value()
        if not options_done and value == "--":
            options_done = True
        elif not options_done and value is not None and value.startswith("-") and len(value) > 1:
            if name == "shred" and value in ("-n", "-s"):
                index += 1
        else:
            operands.append(word)
        index += 1
    for word in operands:
        check_delete(word, state, override)


def run_find(args, state, override):
    starts, index = [], 0
    follows = False
    while index < len(args) and (args[index].value() or "") in ("-H", "-L", "-P", "-E", "-X", "-s", "-x", "-d", "-f"):
        if args[index].value() == "-L":
            follows = True
        if args[index].value() == "-f":
            index += 1
            if index < len(args):
                starts.append(args[index])
        index += 1
    while index < len(args):
        value = args[index].value()
        if value is not None and (value.startswith("-") or value in ("(", "!", ",")):
            break
        starts.append(args[index])
        index += 1
    expression = args[index:]
    deletes, position = False, 0
    while position < len(expression):
        value = expression[position].value()
        if value == "-follow":
            follows = True
        if value == "-delete":
            deletes = True
        if value in ("-exec", "-execdir", "-ok", "-okdir"):
            inner = []
            position += 1
            while position < len(expression) and expression[position].value() not in (";", "+"):
                inner.append(expression[position])
                position += 1
            program = program_name(inner[0]) if inner else None
            if program is None:
                state.unreadable("find runs a program that is not plain text")
                return
            if program in DELETERS:
                deletes = True
            elif program in SHELLS or program in ("git", "gh", "find", "rsync") or program in WRAPPERS or program in RUNS_STRINGS:
                state.unreadable("find runs %s for each file it finds" % program)
                return
        position += 1
    if not deletes:
        return
    if follows:
        state.unreadable("find follows links while it deletes")
        return
    for word in starts or [Word([("lit", ".", True)], ".")]:
        check_delete(word, state, override, contents=True)


def run_rsync(args, state, override):
    values = [word.value() for word in args]
    if not any(value is not None and (value.startswith("--del") or value == "--remove-source-files") for value in values):
        return
    for word, value in zip(args, values):
        if value is not None and value.startswith("-"):
            continue
        if value is not None and re.match(r"^[^/]*:", value):
            state.add("delete-outside", "rsync deletes on %s, which is another machine" % word.raw)
            return
        check_delete(word, state, override, contents=True)


# git.

def is_local_tag(name, bases):
    """Whether a short name is a tag in the repository at every base. When that cannot be told, it counts as one."""
    if not REF_NAME.match(name):
        return True
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    for base in bases:
        if base is None:
            return True
        try:
            result = subprocess.run(["git", "-C", base, "show-ref", "--verify", "--quiet", "refs/tags/" + name],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return True
        if result.returncode == 0:
            return True
        if result.returncode != 1:
            return True
    return False


def run_git(args, state, env_taint, override):
    bases = bases_for(state, override)
    index = 0
    while index < len(args):
        word = args[index]
        value = word.value()
        if value is None:
            state.unreadable("an option of git is not plain text")
            return
        if value in ("-C",):
            if index + 1 >= len(args):
                return
            bases = resolve_dir(bases, args[index + 1])
            index += 2
        elif value == "-c":
            setting = args[index + 1].value() if index + 1 < len(args) else None
            if setting is None:
                state.unreadable("git -c sets something that is not plain text")
                return
            key = setting.split("=", 1)[0].lower()
            if not key.startswith(SAFE_GIT_CONFIG):
                state.unreadable("git -c %s changes what this git command does" % key)
                return
            index += 2
        elif value in ("--no-pager", "-P", "-p", "--paginate", "--no-optional-locks", "--literal-pathspecs",
                       "--no-replace-objects", "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs",
                       "--no-advice"):
            index += 1
        elif value in ("--version", "--help", "-h", "--exec-path", "--html-path", "--man-path", "--info-path"):
            return
        elif value.startswith("-"):
            state.unreadable("git %s is an option this hook does not follow" % value)
            return
        else:
            break
    if index >= len(args):
        return
    if env_taint:
        state.unreadable("a GIT_ variable in the environment changes what git does")
        return
    sub = args[index].value()
    rest = args[index + 1:]
    if sub == "push":
        run_push(rest, state, bases)
    elif sub == "tag":
        run_tag(rest, state)
    elif sub == "update-ref":
        values = [word.value() for word in rest]
        if None in values or "--stdin" in values:
            state.unreadable("git update-ref with arguments this hook cannot read")
            return
        refs = [value for value in values if not value.startswith("-")]
        if refs and refs[0].startswith("refs/tags/"):
            state.add("tag", "git update-ref changes the tag %s" % refs[0])
    elif sub == "clean":
        run_clean(rest, state, bases)
    elif sub == "worktree":
        if rest and rest[0].value() == "remove":
            for word in rest[1:]:
                if not (word.value() or "x").startswith("-"):
                    check_delete(word, state, bases)
    elif sub == "config":
        run_config(rest, state)
    elif sub == "submodule" and any(word.value() == "foreach" for word in rest):
        state.unreadable("git submodule foreach runs a string as commands")
    elif sub == "rebase" and any((word.value() or "-x") in ("-x", "--exec") or (word.value() or "").startswith("--exec=") for word in rest):
        state.unreadable("git rebase --exec runs a string as commands")
    elif sub == "bisect" and rest and rest[0].value() == "run":
        state.unreadable("git bisect run runs a command")
    elif sub not in GIT_COMMANDS:
        state.unreadable("git %s is not a git command this hook knows, and may be an alias" % sub)


def run_push(args, state, bases):
    words, force, tags, mirror, prune, delete, dry = [], [], False, False, False, False, False
    index, options_done = 0, False
    no_ops = {"--set-upstream", "--quiet", "--verbose", "--progress", "--no-progress", "--porcelain", "--atomic",
              "--no-atomic", "--no-verify", "--verify", "--thin", "--no-thin", "--ipv4", "--ipv6", "--all",
              "--branches", "--signed", "--no-signed", "--no-force-with-lease", "--no-recurse-submodules",
              "--no-force-if-includes", "--no-follow-tags", "--no-tags"}
    while index < len(args):
        word = args[index]
        value = word.value()
        if value is None:
            state.unreadable("an argument of git push, %s, is not plain text" % word.raw)
            return
        index += 1
        if options_done or not value.startswith("-") or value == "-":
            words.append(value)
            continue
        if value == "--":
            options_done = True
        elif value in no_ops or value.startswith("--signed=") or value.startswith("--recurse-submodules=") \
                or value.startswith("--push-option=") or value.startswith("--repo="):
            pass
        elif value in ("--push-option", "--repo"):
            index += 1
        elif value in ("--dry-run",):
            dry = True
        elif value in ("--force", "--force-if-includes") or value == "--force-with-lease" or value.startswith("--force-with-lease="):
            force.append(value)
        elif value == "--mirror":
            mirror = True
        elif value == "--prune":
            prune = True
        elif value == "--delete":
            delete = True
        elif value in ("--tags", "--follow-tags"):
            tags = True
        elif value.startswith("--"):
            state.unreadable("git push %s is an option this hook does not follow" % value)
            return
        else:
            for letter in value[1:]:
                if letter == "f":
                    force.append("-f")
                elif letter == "n":
                    dry = True
                elif letter == "d":
                    delete = True
                elif letter in "uqv46":
                    pass
                elif letter == "o":
                    index += 1
                else:
                    state.unreadable("git push -%s is an option this hook does not follow" % letter)
                    return
    if dry:
        return
    if force:
        state.add("force-push", "git push %s may overwrite a ref on the remote" % force[0])
    if mirror:
        state.add("force-push", "git push --mirror overwrites and removes refs on the remote")
        state.add("tag", "git push --mirror pushes and removes tags")
    if prune:
        state.add("force-push", "git push --prune removes refs from the remote")
    if tags:
        state.add("tag", "git push --tags or --follow-tags pushes tags")
    refspecs = words[1:]
    index = 0
    while index < len(refspecs):
        spec = refspecs[index]
        index += 1
        if spec == "tag" and index < len(refspecs):
            state.add("tag", "git push tag %s pushes a tag" % refspecs[index])
            index += 1
            continue
        if spec.startswith("+"):
            state.add("force-push", "the refspec %s overwrites a ref on the remote" % spec)
            spec = spec[1:]
        source, _, target = spec.partition(":") if ":" in spec else (spec, "", spec)
        if delete:
            source, target = "", spec
        if source == "":
            state.add("force-push", "it removes %s from the remote" % target)
            if target.startswith("refs/tags/") or (not target.startswith("refs/") and is_local_tag(target, bases)):
                state.add("tag", "it removes the tag %s from the remote" % target)
            continue
        if source.startswith("refs/tags/") or target.startswith("refs/tags/"):
            state.add("tag", "the refspec %s pushes a tag" % spec)
        elif source not in ("HEAD", "@") and not source.startswith("refs/") and re.match(r"^[A-Za-z0-9_./-]+\Z", source) \
                and is_local_tag(source, bases):
            state.add("tag", "%s is a tag" % source)


def run_tag(args, state):
    values = [word.value() for word in args]
    if None in values:
        state.unreadable("an argument of git tag is not plain text")
        return
    listing = {"-l", "--list", "-v", "--verify", "--column", "--no-column", "-i", "--ignore-case"}
    listing_prefixes = ("--contains", "--no-contains", "--merged", "--no-merged", "--points-at", "--sort", "--format",
                        "--color", "-n")
    creating = {"-a", "--annotate", "-s", "--sign", "-f", "--force", "-e", "--edit", "--create-reflog", "--no-sign"}
    with_value = {"-m", "-F", "-u", "--message", "--file", "--local-user", "--cleanup", "--trailer"}
    lists = create = delete = False
    positional, index = [], 0
    while index < len(values):
        value = values[index]
        index += 1
        if value in ("-d", "--delete"):
            delete = True
        elif value in listing or value.startswith(listing_prefixes):
            lists = True
        elif value in creating:
            create = True
        elif value.split("=", 1)[0] in with_value:
            create = True
            if "=" not in value:
                index += 1
        elif value.startswith("-") and len(value) > 1:
            create = True
        else:
            positional.append(value)
    if delete:
        state.add("tag", "git tag --delete deletes a tag")
    elif create or (positional and not lists):
        state.add("tag", "git tag creates or moves a tag")


def run_clean(args, state, bases):
    values = [word.value() for word in args]
    if None in values:
        state.unreadable("an argument of git clean is not plain text")
        return
    for value in values:
        if value in ("-n", "--dry-run") or (re.match(r"^-[a-zA-Z]+\Z", value) and "n" in value):
            return
    for base in bases:
        if base is None:
            state.unreadable("the directory git clean runs in is not known")
            return
        if not inside(state, base, allow_root=True):
            state.add("delete-outside", "git clean deletes in %s, outside the working tree" % base)
            return
    paths = [word for word, value in zip(args, values) if not value.startswith("-")]
    for word in paths:
        check_delete(word, state, bases, contents=True)
    state.deletes = True


def run_config(args, state):
    values = [word.value() for word in args]
    if None in values:
        state.unreadable("an argument of git config is not plain text")
        return
    reads = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l", "--get-color", "--get-colorbool"}
    writes = {"--add", "--replace-all", "--unset", "--unset-all", "--rename-section", "--remove-section"}
    with_value = {"--file", "-f", "--blob", "--type", "--default", "--comment"}
    mode, positional, index = None, [], 0
    while index < len(values):
        value = values[index]
        index += 1
        if value in ("--edit", "-e"):
            state.unreadable("git config --edit lets any setting change")
            return
        if value in reads:
            mode = "read"
        elif value in writes:
            mode = "write"
        elif value in with_value:
            index += 1
        elif value.startswith("-"):
            pass
        else:
            positional.append(value)
    if positional and positional[0] in ("get", "list"):
        return
    if positional and positional[0] in ("set", "unset", "rename-section", "remove-section", "edit"):
        if positional[0] == "edit":
            state.unreadable("git config edit lets any setting change")
            return
        mode, positional = "write", positional[1:]
    if mode == "read" or (mode is None and len(positional) < 2):
        return
    key = positional[0].lower() if positional else ""
    if key.startswith(RISKY_GIT_CONFIG) or not key:
        state.unreadable("git config %s changes what a later git command does" % key)


# gh.

def run_gh(args, state):
    values = [word.value() for word in args]
    index = 0
    while index < len(values) and values[index] is not None and values[index].startswith("-"):
        if values[index] in ("--help", "--version", "-h"):
            return
        state.unreadable("gh %s is an option this hook does not follow" % values[index])
        return
    if index >= len(values):
        return
    sub = values[index]
    if sub is None:
        state.unreadable("the gh command is not plain text")
        return
    rest = args[index + 1:]
    if sub == "api":
        run_api(rest, state)
        return
    if sub in GH_QUIET:
        return
    action = None
    position = 0
    while position < len(rest):
        value = rest[position].value()
        if value in ("-R", "--repo"):
            position += 2
            continue
        if value is not None and value.startswith("-"):
            position += 1
            continue
        action = value if value is not None else False
        break
    if action is False:
        state.unreadable("what gh %s does is not plain text" % sub)
        return
    later = [word.value() for word in rest[position + 1:]]
    if sub == "release":
        if action in ("create", "new", "delete", "edit", "upload", "delete-asset"):
            state.add("release", "gh release %s changes a release" % action)
        elif action not in ("view", "list", "ls", "download", "verify", "verify-asset", None):
            state.unreadable("gh release %s is not one this hook knows" % action)
    elif sub == "repo":
        if action in ("edit", "delete", "rename", "archive", "unarchive"):
            state.add("settings", "gh repo %s changes the repository" % action)
        elif action in ("deploy-key", "autolink"):
            if later and later[0] in ("add", "delete", "create"):
                state.add("settings", "gh repo %s %s changes the repository's settings" % (action, later[0]))
        elif action == "sync":
            if any(value is None or value in ("--force", "-f") for value in later):
                state.add("force-push", "gh repo sync --force overwrites a branch")
        elif action not in ("create", "new", "fork", "clone", "view", "list", "ls", "set-default", "gitignore", "license", None):
            state.unreadable("gh repo %s is not one this hook knows" % action)
    elif sub in ("secret", "variable"):
        if action in ("set", "delete", "remove"):
            state.add("settings", "gh %s %s changes the repository's settings" % (sub, action))
        elif action not in ("list", "ls", "get", None):
            state.unreadable("gh %s %s is not one this hook knows" % (sub, action))
    elif sub == "workflow":
        if action in ("enable", "disable", "run"):
            state.add("settings", "gh workflow %s changes which workflows run, and a workflow may take any step" % action)
        elif action not in ("list", "ls", "view", None):
            state.unreadable("gh workflow %s is not one this hook knows" % action)
    elif sub in ("alias", "extension", "ext", "extensions"):
        if action not in ("list", "ls", "search", "browse", None):
            state.unreadable("gh %s %s defines or runs a command this hook does not see" % (sub, action))
    else:
        state.unreadable("gh %s is not a gh command this hook knows, and may be an alias or an extension" % sub)


def run_api(args, state):
    method = endpoint = None
    fields, has_input = [], False
    skip_value = {"-q", "--jq", "-t", "--template", "--cache", "-p", "--preview", "--hostname"}
    flags = {"-i", "--include", "--paginate", "--silent", "--slurp", "--verbose"}
    index = 0
    while index < len(args):
        word = args[index]
        value = word.value()
        index += 1
        if value is not None and value.startswith("-") and len(value) > 1:
            option, attached = (value.split("=", 1) + [None])[:2] if value.startswith("--") else (value[:2], value[2:] or None)
            take = (lambda: (attached_word(word, value, attached) if attached is not None else (args[index] if index < len(args) else dynamic("no value"))))
            if option in ("-X", "--method"):
                method = take()
            elif option in ("-H", "--header"):
                header = take().value()
                if header is None:
                    state.unreadable("gh api sends a header that is not plain text")
                    return
                if header.lower().replace(" ", "").startswith("x-http-method-override"):
                    state.unreadable("gh api overrides its method with a header")
                    return
            elif option in ("-f", "--raw-field", "-F", "--field"):
                fields.append((option, take()))
            elif option == "--input":
                has_input = True
                take()
            elif option in skip_value:
                take()
            elif option in flags:
                continue
            else:
                state.unreadable("gh api %s is an option this hook does not follow" % value)
                return
            if attached is None:
                index += 1
        elif endpoint is not None:
            state.unreadable("gh api is given two endpoints")
            return
        else:
            endpoint = word
    if endpoint is None:
        return
    if method is not None:
        verb = method.value()
        if verb is None:
            state.unreadable("the method of gh api is not plain text")
            return
        verb = verb.upper()
    else:
        verb = "POST" if fields or has_input else "GET"
    if verb not in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"):
        state.unreadable("gh api with the method %s" % verb)
        return
    path = endpoint.value()
    if path is None:
        if verb not in ("GET", "HEAD"):
            state.unreadable("gh api %s to an endpoint that is not plain text" % verb)
        return
    if path.startswith("https://api.github.com/"):
        path = path[len("https://api.github.com/"):]
    elif re.match(r"^[a-z]+://", path):
        state.unreadable("gh api to another host")
        return
    path = re.split(r"[?#]", path.lstrip("/"), 1)[0]
    segments = [segment for segment in path.lower().split("/") if segment]

    def field(name):
        for option, word in fields:
            text = word.parts[0][1] if word.parts and word.parts[0][0] == "lit" else ""
            if text.startswith(name + "="):
                full = word.value()
                if full is None or (option in ("-F", "--field") and full[len(name) + 1:].startswith("@")):
                    return False
                return full[len(name) + 1:]
        return None

    if segments == ["graphql"]:
        query = field("query")
        if not query or has_input:
            state.unreadable("gh api graphql with a query this hook cannot read")
        elif re.search(r"\bmutation\b", query):
            state.unreadable("gh api graphql with a mutation, which may change anything")
        return
    if verb in ("GET", "HEAD"):
        return
    step, why = classify_api(verb, segments, field)
    if step:
        state.add(step, "gh api %s %s %s" % (verb, path, why))


def attached_word(word, value, attached):
    if word.value() is not None:
        return Word([("lit", attached, True)], attached)
    return dynamic("an attached value")


def classify_api(verb, segments, field):
    if segments[:1] in (["orgs"], ["enterprises"], ["teams"]):
        return "settings", "changes the settings of an organization"
    if segments[:1] != ["repos"] or len(segments) < 3:
        return None, ""
    rest = segments[3:]
    if not rest:
        return "settings", "changes or deletes the repository"
    head = rest[0]
    if head == "releases":
        return "release", "changes a release"
    if head == "git":
        if len(rest) >= 2 and rest[1] == "refs":
            if len(rest) == 2:
                ref = field("ref")
                if ref is None or ref is False:
                    return UNREADABLE, "makes a ref this hook cannot read"
                if ref.startswith("refs/tags/"):
                    return "tag", "makes a tag"
                if ref.startswith("refs/heads/"):
                    return None, ""
                return UNREADABLE, "makes a ref this hook cannot read"
            if rest[2] == "tags":
                return "tag", "changes a tag"
            if rest[2] == "heads":
                if verb == "DELETE":
                    return "force-push", "removes a branch"
                force = field("force")
                if force is False:
                    return UNREADABLE, "with a force this hook cannot read"
                if force in ("true",):
                    return "force-push", "overwrites a branch"
                if force in (None, "false"):
                    return None, ""
                return UNREADABLE, "with a force this hook cannot read"
            return UNREADABLE, "changes a ref this hook cannot read"
        if len(rest) >= 2 and rest[1] == "tags":
            return "tag", "makes a tag"
        return None, ""
    if head == "branches":
        if "protection" in rest or rest[-1] == "rename":
            return "settings", "changes the protection or the name of a branch"
        return None, ""
    if head == "actions":
        if len(rest) > 1 and rest[1] in ("runs", "jobs", "artifacts", "caches"):
            return None, ""
        return "settings", "changes the settings of Actions, or starts a workflow"
    if head in SETTINGS_PATHS:
        return "settings", "changes the repository's settings"
    return None, ""


# ---------------------------------------------------------------- the approvals

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
        raise ValueError("not valid UTF-8, at byte %d (0x%02X)" % (error.start, error.object[error.start]))
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except RecursionError:
        raise ValueError("nested too deeply")
    except json.JSONDecodeError as error:
        raise ValueError("not valid JSON: %s" % error)


def read_approvals(path, cwd=None, root=None):
    """(approvals, problems). A file with any problem approves nothing. A missing file approves nothing."""
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(path)))
    cwd = cwd or root
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except FileNotFoundError:
        return [], []
    except OSError as error:
        return [], ["cannot be read: %s" % error]
    try:
        top = strict_json(data)
    except ValueError as error:
        return [], [str(error)]
    if not isinstance(top, dict):
        return [], ["the top level must be an object"]
    problems = ["unknown field %r" % key for key in sorted(top) if key != "approvals"]
    if "approvals" not in top:
        problems.append("missing field 'approvals'")
    elif not isinstance(top["approvals"], list):
        problems.append("approvals must be a list")
    if problems:
        return [], problems
    approvals, seen = [], set()
    for number, entry in enumerate(top["approvals"], 1):
        where = "approval %d" % number
        if not isinstance(entry, dict):
            problems.append("%s: an approval must be an object" % where)
            continue
        unknown = sorted(set(entry) - set(APPROVAL_FIELDS))
        missing = [field for field in APPROVAL_FIELDS if field not in entry]
        problems.extend("%s: unknown field %r" % (where, field) for field in unknown)
        problems.extend("%s: missing field %r" % (where, field) for field in missing)
        if unknown or missing:
            continue
        if not all(isinstance(entry[field], str) for field in APPROVAL_FIELDS):
            for field in APPROVAL_FIELDS:
                if not isinstance(entry[field], str):
                    problems.append("%s: %s must be text" % (where, field) if field != "until"
                                    else "%s: until must be a date of the form 2026-01-31" % where)
            continue
        step, command, until, reason = (entry[field] for field in APPROVAL_FIELDS)
        if step not in STEPS:
            problems.append("%s: step must be one of %s" % (where, ", ".join(STEPS)))
            continue
        date = None
        if DATE.match(until):
            try:
                date = datetime.date(int(until[:4]), int(until[5:7]), int(until[8:]))
            except ValueError:
                date = None
        if date is None:
            problems.append("%s: until must be a date of the form 2026-01-31" % where)
        if not PRINTABLE.match(reason) or not PRINTABLE.match(command):
            problems.append("%s: the command and the reason must be printable ASCII" % where)
            continue
        if not reason.strip():
            problems.append("%s: the reason must not be empty" % where)
        if not PLAIN_COMMAND.match(command) or command != command.strip():
            problems.append("%s: the command must be one plain command, with no ; & | < > ( ) $ ` \\ # * or space at its ends" % where)
            continue
        if (step, command) in seen:
            problems.append("%s: the step %s is approved twice for one command" % (where, step))
        seen.add((step, command))
        findings = analyze(command, cwd, root)
        found = sorted(set(finding.step for finding in findings))
        if found != [step]:
            problems.append("%s: the command %s is not the step %s: it is %s" % (where, command, step, ", ".join(found) or "no step"))
            continue
        if date is not None:
            approvals.append({"step": step, "command": command, "until": date})
    if problems:
        return [], problems
    return approvals, []


# ---------------------------------------------------------------- the hook

def input_problem(why):
    return 2, "irreversible.py: denied, the hook cannot read its input (ratchet.irreversible-waits).\n- input: %s\n" % why


def decide(raw, env):
    try:
        data = strict_json(raw)
    except ValueError as error:
        return input_problem(str(error))
    if not isinstance(data, dict):
        return input_problem("the top level must be an object")
    tool, tool_input, cwd = data.get("tool_name"), data.get("tool_input"), data.get("cwd")
    if not isinstance(tool, str) or not isinstance(tool_input, dict):
        return input_problem("tool_name must be text and tool_input an object")
    if not isinstance(cwd, str) or not os.path.isabs(cwd):
        return input_problem("cwd must be an absolute path")
    root = env.get("CLAUDE_PROJECT_DIR") or cwd
    if not os.path.isabs(root):
        return input_problem("CLAUDE_PROJECT_DIR must be an absolute path")
    approvals_path = os.path.join(root, APPROVALS)
    if tool in FILE_TOOLS:
        path = tool_input.get(FILE_TOOLS[tool])
        if not isinstance(path, str) or not path:
            return input_problem("%s must be a path" % FILE_TOOLS[tool])
        full = os.path.realpath(os.path.join(cwd, path))
        if full == os.path.realpath(approvals_path) or full.endswith(os.sep + os.path.join(".claude", APPROVALS_NAME)):
            return 2, ("irreversible.py: denied (ratchet.irreversible-waits).\n"
                       "- approvals: %s writes the approvals file, which only the owner writes\n" % tool)
        return 0, ""
    if tool != "Bash":
        return 0, ""
    command = tool_input.get("command")
    if not isinstance(command, str):
        return input_problem("tool_input.command must be text")
    findings = analyze(command, cwd, root)
    if not findings:
        return 0, ""
    approvals, problems = read_approvals(approvals_path, cwd, root)
    today = datetime.date.today()
    granted = set(approval["step"] for approval in approvals if approval["command"] == command and approval["until"] >= today)
    blocking = [finding for finding in findings if finding.step in (UNREADABLE, "approvals") or finding.step not in granted]
    if not blocking:
        return 0, ""
    lines = ["irreversible.py: denied. A step that cannot be undone waits for an approval that names it, and a "
             "command this hook cannot read is never approved (ratchet.irreversible-waits)."]
    shown = set()
    for finding in findings:
        if (finding.step, finding.why) not in shown:
            shown.add((finding.step, finding.why))
            lines.append("- %s: %s" % (finding.step, finding.why))
    for problem in problems:
        lines.append("%s: %s, so it approves nothing" % (APPROVALS, problem))
    steps = sorted(set(finding.step for finding in blocking if finding.step in STEPS))
    if steps:
        lines.append("To go ahead, the owner adds to the list approvals in %s one entry for each step, with this "
                     "exact command, a last day and a reason:" % APPROVALS)
        for step in steps:
            lines.append("  " + json.dumps({"step": step, "command": command, "until": "YYYY-MM-DD", "reason": "..."}))
    if any(finding.step == UNREADABLE for finding in findings):
        lines.append("Write the command as plain commands: no eval, sh -c or alias, and no program, git argument or "
                     "path to delete that only a variable or a substitution names.")
    return 2, "\n".join(lines) + "\n"


def main():
    try:
        code, message = decide(sys.stdin.buffer.read(), os.environ)
    except Exception as error:  # A hook that crashes would let the call through: deny instead.
        code, message = 2, "irreversible.py: denied, the hook failed (ratchet.irreversible-waits).\n- error: %r\n" % (error,)
    if message:
        sys.stderr.write(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
