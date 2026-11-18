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
import fnmatch
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
# Characters an unquoted path to delete may hold. Anything else unquoted is refused. A pattern is never expanded.
SAFE_UNQUOTED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._/+-,@%:=~")
# What may follow "$d" in a path to delete, for a directory from mktemp -d: parts below it, none of them . or ..
BELOW = re.compile(r"^(/[A-Za-z0-9_][A-Za-z0-9._-]*)*/?\Z")
# Words in front of a command that run it in the shell itself, so that a builtin after them can assign a variable.
PRECOMMANDS = {"command", "builtin", "time", "noglob", "nocorrect", "-", "exec"}
# Programs that cannot assign a variable of the shell that runs the line: programs of their own, and builtins
# that assign none. Any other command may assign every name it is given, and is read that way. The list says what
# is known to be safe; what is not on it counts as a builtin that assigns.
NO_ASSIGN = {"git", "gh", "rm", "rmdir", "unlink", "mkdir", "touch", "cp", "mv", "ln", "cat", "ls", "echo", "test", "[",
             "true", "false", ":", "cd", "pushd", "popd", "trap", "tar", "zip", "unzip", "curl", "jq", "python3",
             "python", "sed", "awk", "grep", "rg", "head", "tail", "wc", "sort", "uniq", "diff", "cmp", "find", "xargs",
             "open", "chmod", "du", "basename", "dirname", "realpath", "sleep", "date", "env", "sudo", "nohup",
             "timeout", "make", "mktemp", "ffmpeg", "ffprobe", "tee"}
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
GH_QUIET = {"pr", "issue", "label", "cache", "gist", "auth", "config", "org", "codespace", "cs", "project",
            "search", "status", "browse", "attestation", "completion", "help", "version", "ruleset", "ssh-key",
            "gpg-key", "co"}


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

    def ambiguity(self):
        """Why the shell may make of the word something other than its text, or None. The hook does not expand a
        pattern (* ? [ and zsh's ^ and #), a brace expansion, a tilde other than a leading ~ or ~/ that no quote
        touches, or zsh's leading =. It names them, so that a word that holds one is never read as plain text."""
        if self.braces():
            return "a brace expansion"
        for index, part in enumerate(self.parts):
            if part[0] != "lit" or part[2]:
                continue
            text = part[1]
            for offset, c in enumerate(text):
                start = index == 0 and offset == 0
                later = text[offset + 1:] + "".join(other[1] for other in self.parts[index + 1:] if other[0] == "lit")
                # [ opens a pattern only when a ] follows it in the word; [ alone, as in [ -x f ], is a program.
                if c in "*?^#" or (c == "[" and "]" in later):
                    return "a pattern"
                if c == "=" and start:
                    return "a leading ="
                if c == "~":
                    alone = len(text) == 1 and len(self.parts) == 1
                    if not (start and (alone or text[1:2] == "/")):
                        return "a tilde this hook does not expand"
        return None

    def value(self):
        """The text the shell makes of the word, when it is plain text, or None."""
        if any(part[0] != "lit" for part in self.parts) or self.ambiguity():
            return None
        first = self.parts[0] if self.parts else ("lit", "", True)
        text = "".join(part[1] for part in self.parts)
        if not first[2] and first[1].startswith("~"):
            return os.path.expanduser("~") + text[1:]
        return text

    def why_not_plain(self):
        why = self.ambiguity()
        return "not plain text" if why is None else "%s, which this hook does not expand" % why

    def unquoted(self):
        return "".join(part[1] for part in self.parts if part[0] == "lit" and not part[2])

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
        self.indirect = False


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
        if re.match(r"<[0-9]*-[0-9]*>", self.s[self.i:]):
            raise Unreadable("zsh's pattern <...>, which this hook does not expand")
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
            parts.append(("dyn", '$"...", which the locale may translate', True))
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
            # Any operator may assign, as ${d=x}, ${d:=x} and zsh's ${d::=x} do; zsh's flags, as in ${(P)x::=y},
            # may assign a variable that another names.
            if body.startswith("("):
                self.context.indirect = True
            match = re.match(r"^[#!]?([A-Za-z_][A-Za-z0-9_]*)", body)
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
        elif following in ("", " ", "\t", "\n") or following in "|&;<>()" or (quoted and following == '"'):
            parts.append(("lit", "$", quoted))
            self.i += 1
        else:
            # $[...], zsh's $=name and $~name, and the like: a form of $ this hook does not read.
            parts.append(("dyn", "a form of $ this hook does not read", quoted))
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
    found = assigned(program, context)
    state.temps = temporary_names(found, context)
    # A command that may assign, given a GIT_ name or a name this hook cannot read, may change what git does.
    for text in found.texts:
        for match in re.finditer(r"(?<![A-Za-z0-9_$])(?<!\$\{)(GIT_[A-Za-z0-9_]*)", text):
            if match.group(1) not in SAFE_GIT_ENV:
                state.git_taint = True
    if found.opaque:
        state.git_taint = True
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


def effective_words(words):
    """The words of a command from the program it runs, past command, builtin, time, noglob, nocorrect, - and exec,
    with their options."""
    index = 0
    while index < len(words) and program_name(words[index]) in PRECOMMANDS:
        index += 1
        while index < len(words):
            value = words[index].value()
            if value == "--":
                index += 1
                break
            if value is None or not value.startswith("-") or value == "-":
                break
            index += 2 if value == "-a" else 1
    return words[index:]


def mentions(text, name):
    """Whether literal text may name a variable: the name as a word of its own, not after $ or ${, or at the end of
    a cluster of short options, as in printf -vd."""
    if re.search(r"(?<![A-Za-z0-9_$])(?<!\$\{)%s(?![A-Za-z0-9_])" % re.escape(name), text):
        return True
    return re.match(r"^-[A-Za-z0-9_]*%s\Z" % re.escape(name), text) is not None


class Assigned:
    """What a line may assign, beyond its plain assignments: the literal text that commands which may assign are
    given, and whether one of them is given a name this hook cannot read."""

    def __init__(self):
        self.texts = []
        self.opaque = False
        self.blocked = False
        self.good = set()
        self.bad = set()

    def may_assign(self, name):
        return self.opaque or any(mentions(text, name) for text in self.texts)


def assigned(program, context):
    """Read the whole line for what it may assign. A variable from mktemp -d is trusted only when nothing else in
    the line may assign it: no plain assignment, no loop, no ${name=...}, and no command that may assign, such as
    read, printf -v, declare, set -A or a builtin behind command or builtin, that is given its name or a word this
    hook cannot read."""
    found = Assigned()
    found.bad |= set(context.loop_names) | set(context.expansion_names)

    def collect(program, top):
        for command in program.commands:
            for name, value in command.assigns:
                if (top and not command.words and command.depth == 0 and command.first and not command.pipeline
                        and not command.background and is_mktemp(value)):
                    found.good.add(name)
                else:
                    found.bad.add(name)
                    found.texts.extend(part[1] for part in value.parts if part[0] == "lit")
            for word in command.all_words():
                if is_mktemp(word):
                    continue
                for inner in word.programs():
                    collect(inner, False)
            if command.data:
                continue
            words = effective_words(command.words)
            if not words:
                if command.words:
                    found.opaque = True
                continue
            name = program_name(words[0])
            if name in ("source", ".", "eval"):
                found.blocked = True
            if name == "trap":
                action = trap_action(words)
                if action is not None and action.value() is not None:
                    try:
                        collect(parse(action.value(), context), False)
                    except Unreadable:
                        found.blocked = True
            if name in NO_ASSIGN:
                continue
            # printf assigns only with -v, which comes first: a first argument that is literal and is no option
            # leaves nothing to assign.
            if name == "printf" and len(words) > 1 and words[1].value() is not None \
                    and (not words[1].value().startswith("-") or words[1].value() == "--"):
                continue
            for word in words:
                for part in word.parts:
                    if part[0] == "lit":
                        found.texts.append(part[1])
                    elif not (part[0] == "var" and part[1] in found.good):
                        found.opaque = True

    collect(program, True)
    return found


def temporary_names(found, context):
    """The variables that only ever hold a directory from mktemp -d, assigned at the top of the line."""
    if found.blocked or context.arith or context.functions or context.indirect:
        return set()
    return set(name for name in found.good - found.bad if not found.may_assign(name))


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
    target = os.path.realpath(os.path.join(state.root, APPROVALS))
    if word.ambiguity() and not re.search(r"\s", text) and all(part[0] == "lit" for part in word.parts):
        # A pattern the shell may expand to the approvals file, part by part.
        pattern = [part for part in text.split("/") if part not in ("", ".")]
        for base in state.cwds:
            if base is None:
                return True
            whole = [part for part in (target if text.startswith("/") else os.path.relpath(target, base)).split("/") if part]
            if len(whole) == len(pattern) and all(fnmatch.fnmatchcase(a, b) for a, b in zip(whole, pattern)):
                return True
        return False
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
        state.unreadable("the program %s is %s" % (words[0].raw, words[0].why_not_plain()))
        return
    args = words[1:]
    if name in ("hash", "enable") and args:
        state.unreadable("%s with arguments can make a name run another program" % name)
        return
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
        if pattern_may_name(words[index], triggers):
            state.unreadable("%s is given %s, a pattern that may name a program it runs" % (name, words[index].raw))
            return
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


def pattern_may_name(word, names):
    """Whether a word that the shell may expand, such as g[i]t or ~user/bin/rm, may name one of the programs."""
    if any(part[0] != "lit" for part in word.parts) or word.ambiguity() is None:
        return False
    text = "".join(part[1] for part in word.parts).rstrip("/")
    pattern = re.sub(r"\{[^{}]*\}", "*", text.rsplit("/", 1)[-1])
    pattern = re.sub(r"[\^#]", "*", pattern)
    return any(fnmatch.fnmatchcase(name, pattern) for name in names)


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


def temporary_word(word, state):
    """Whether a word is "$d", or "$d" and parts below it such as "$d/wt", for a variable d that holds a directory
    from mktemp -d in this line. The variable is quoted, and what follows is literal and holds no . or .. part."""
    if not word.parts or word.parts[0][0] != "var" or not word.parts[0][2]:
        return False
    name = word.parts[0][1]
    if name not in state.temps or name not in state.live:
        return False
    rest = word.parts[1:]
    if any(part[0] != "lit" for part in rest):
        return False
    return BELOW.match("".join(part[1] for part in rest)) is not None


def check_delete(word, state, override, contents=False):
    """Whether deleting what a word names stays inside the working tree. With contents=True, what is deleted is
    inside the named directory, which may be the working tree itself."""
    state.deletes = True
    if temporary_word(word, state):
        return
    value = word.value()
    if value is None:
        state.unreadable("the path %s to delete is %s" % (word.raw, word.why_not_plain()))
        return
    if set(word.unquoted()) - SAFE_UNQUOTED:
        state.unreadable("the path %s to delete holds a character this hook does not read unquoted" % word.raw)
        return
    if value == "":
        return
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


# Options of find before its starting points, and primaries of its expression that take one value.
FIND_LEADING = {"-H", "-L", "-P", "-E", "-X", "-s", "-x", "-d"}
FIND_ONE = {"-name", "-iname", "-path", "-ipath", "-wholename", "-iwholename", "-regex", "-iregex", "-lname",
            "-ilname", "-type", "-xtype", "-user", "-group", "-uid", "-gid", "-perm", "-size", "-mtime", "-mmin",
            "-atime", "-amin", "-ctime", "-cmin", "-newer", "-anewer", "-cnewer", "-maxdepth", "-mindepth", "-links",
            "-inum", "-samefile", "-used", "-fstype", "-printf", "-fprint", "-fprint0", "-fls", "-context",
            "-regextype", "-flags", "-Btime", "-Bmin", "-Bnewer"}


def run_find(args, state, override):
    starts, index = [], 0
    follows = starts_unknown = False
    while index < len(args):
        value = args[index].value()
        if value in FIND_LEADING:
            follows = follows or value == "-L"
            index += 1
        elif value == "-f":
            if index + 1 < len(args):
                starts.append(args[index + 1])
            index += 2
        elif value == "-D":
            index += 2
        elif value is not None and re.match(r"^-O[0-9]\Z", value):
            index += 1
        else:
            break
    while index < len(args):
        word = args[index]
        value = word.value()
        if value is None and not temporary_word(word, state):
            state.unreadable("find is given %s, which may be a starting point or an action" % word.raw)
            return
        if value is not None and (value.startswith("-") or value in ("(", "!", ",")):
            break
        starts.append(word)
        index += 1
    expression = args[index:]
    deletes, position = False, 0
    while position < len(expression):
        word = expression[position]
        value = word.value()
        position += 1
        if value is None:
            state.unreadable("find is given %s, which may be an action" % word.raw)
            return
        if value == "-follow":
            follows = True
        elif value == "-delete":
            deletes = True
        elif value == "-files0-from":
            starts_unknown = True
            position += 1
        elif value in FIND_ONE or re.match(r"^-newer[a-zA-Z]{2}\Z", value):
            position += 1
        elif value == "-fprintf":
            position += 2
        elif value in ("-exec", "-execdir", "-ok", "-okdir"):
            inner, closed = [], False
            while position < len(expression):
                following = expression[position]
                position += 1
                if following.value() == ";" or (following.value() == "+" and inner and inner[-1].value() == "{}"):
                    closed = True
                    break
                inner.append(following)
            if not closed:
                state.unreadable("find %s is not closed with ; or +" % value)
                return
            result = run_find_exec(value, inner, state, override)
            if result is None:
                return
            deletes = deletes or result
    if not deletes:
        return
    if follows:
        state.unreadable("find follows links while it deletes")
        return
    if starts_unknown:
        state.unreadable("find reads where it starts from a file while it deletes")
        return
    for word in starts or [Word([("lit", ".", True)], ".")]:
        check_delete(word, state, override, contents=True)


def run_find_exec(kind, inner, state, override):
    """The command of find -exec, -execdir, -ok or -okdir, read as if it ran directly. {} stands for each file
    find finds, which a deletion reaches through the starting points. With -execdir and -okdir, the command runs
    in a directory this hook does not know. True when it deletes what find finds, False when not, None when the
    command cannot be read."""
    if not inner:
        state.unreadable("find %s runs nothing" % kind)
        return None
    name = program_name(inner[0])
    if name is None:
        state.unreadable("find runs a program that is %s" % inner[0].why_not_plain())
        return None
    if name in SHELLS or name in RUNS_STRINGS:
        state.unreadable("find runs %s for each file it finds" % name)
        return None
    base = {None} if kind in ("-execdir", "-okdir") else override
    words = []
    for word in inner:
        if word.value() == "{}":
            words.append(None)
        elif "{}" in word.raw:
            words.append(dynamic("a word that holds {}"))
        else:
            words.append(word)
    if name in DELETERS:
        run_delete(name, [word for word in words[1:] if word is not None], state, base)
        return True
    found = Word([("dyn", "a file that find finds", True)], "{}")
    run_words([found if word is None else word for word in words], state, False, base)
    return False


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
        state.unreadable("a GIT_ variable, or a variable this hook cannot name, may change what git does")
        return
    sub = args[index].value()
    rest = args[index + 1:]
    if sub == "push":
        run_push(rest, state, bases)
    elif sub == "tag":
        run_tag(rest, state)
    elif sub == "update-ref":
        run_update_ref(rest, state)
    elif sub == "symbolic-ref":
        run_symbolic_ref(rest, state)
    elif sub == "clean":
        run_clean(rest, state, bases)
    elif sub == "worktree":
        if rest and rest[0].value() == "remove":
            run_worktree_remove(rest[1:], state, bases)
    elif sub == "remote" and any(word.value() is None or (word.value() or "").startswith("--mirror") for word in rest):
        state.unreadable("git remote with --mirror, or with a word that is not plain text, changes what a later push does")
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


def git_options(args, state, what, flags, values=(), optional=(), numbers=(), paths=False):
    """Read the options of a git subcommand strictly. flags take no value; values take one, after = or as the next
    word; optional are long options that take a value only after =; numbers are short options with digits attached,
    as in -n5. Short options may be clustered, as in -fdx, and a short option that takes a value takes the rest of
    the cluster or the next word, as git does. Any other option, and an abbreviation of a long one, is an option
    this hook does not know, and the command is unreadable: its arity is not guessed. With paths, a positional word
    may be "$d" for a directory from mktemp -d. Returns ([(option, value)], [positional Word]) or None."""
    found, positional, index, done = [], [], 0, False
    while index < len(args):
        word = args[index]
        value = word.value()
        index += 1
        if value is None:
            if paths and temporary_word(word, state):
                positional.append(word)
                continue
            state.unreadable("%s is given %s, which is %s" % (what, word.raw, word.why_not_plain()))
            return None
        if done or not value.startswith("-") or value == "-":
            positional.append(word)
            continue
        if value == "--":
            done = True
            continue
        if value.startswith("--"):
            name, equals, attached = value.partition("=")
            if name in flags and not equals:
                found.append((name, None))
            elif name in values:
                if equals:
                    found.append((name, attached))
                elif index < len(args):
                    found.append((name, args[index].value()))
                    index += 1
                else:
                    found.append((name, None))
            elif name in optional and equals:
                found.append((name, attached))
            else:
                state.unreadable("%s %s is an option this hook does not know" % (what, value))
                return None
            continue
        letters = value[1:]
        for position, letter in enumerate(letters):
            short = "-" + letter
            rest = letters[position + 1:]
            if short in flags:
                found.append((short, None))
            elif short in values:
                if rest:
                    found.append((short, rest))
                elif index < len(args):
                    found.append((short, args[index].value()))
                    index += 1
                else:
                    found.append((short, None))
                break
            elif short in numbers and re.match(r"^[0-9]*\Z", rest):
                found.append((short, rest))
                break
            else:
                state.unreadable("%s -%s is an option this hook does not know" % (what, letter))
                return None
    return found, positional


PUSH_FLAGS = {"--all", "--branches", "--mirror", "-d", "--delete", "--tags", "-n", "--dry-run", "--porcelain", "-f",
              "--force", "--force-with-lease", "--force-if-includes", "--thin", "--no-thin", "-u", "--set-upstream",
              "--progress", "--no-progress", "--prune", "--no-verify", "--verify", "--follow-tags", "--no-follow-tags",
              "--no-tags", "--atomic", "--no-atomic", "-v", "--verbose", "-q", "--quiet", "-4", "--ipv4", "-6",
              "--ipv6", "--no-force-with-lease", "--no-force-if-includes", "--no-recurse-submodules", "--signed",
              "--no-signed"}
PUSH_VALUES = {"--repo", "-o", "--push-option", "--recurse-submodules"}
PUSH_OPTIONAL = {"--force-with-lease", "--signed"}


def run_push(args, state, bases):
    parsed = git_options(args, state, "git push", PUSH_FLAGS, PUSH_VALUES, PUSH_OPTIONAL)
    if parsed is None:
        return
    found, positional = parsed
    names = set(name for name, _ in found)
    if names & {"-n", "--dry-run"}:
        return
    force = [name for name, _ in found if name in ("-f", "--force", "--force-with-lease", "--force-if-includes")]
    if force:
        state.add("force-push", "git push %s may overwrite a ref on the remote" % force[0])
    if "--mirror" in names:
        state.add("force-push", "git push --mirror overwrites and removes refs on the remote")
        state.add("tag", "git push --mirror pushes and removes tags")
    if "--prune" in names:
        state.add("force-push", "git push --prune removes refs from the remote")
    if names & {"--tags", "--follow-tags"}:
        state.add("tag", "git push --tags or --follow-tags pushes tags")
    delete = bool(names & {"-d", "--delete"})
    words = [word.value() for word in positional]
    # The first word is the repository. With --repo, git still reads it so; the hook also reads it as a refspec,
    # so that neither reading lets a refspec through.
    refspecs = words if "--repo" in names else words[1:]
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
            if is_tag_ref(target) or (not target.lower().startswith("refs/") and is_local_tag(target, bases)):
                state.add("tag", "it removes the tag %s from the remote" % target)
            continue
        if is_tag_ref(source) or is_tag_ref(target):
            state.add("tag", "the refspec %s pushes a tag" % spec)
        elif source not in ("HEAD", "@") and not source.lower().startswith("refs/") \
                and re.match(r"^[A-Za-z0-9_./-]+\Z", source) and is_local_tag(source, bases):
            state.add("tag", "%s is a tag" % source)


def is_tag_ref(ref):
    """A ref under refs/tags/, in any case, since a file system that ignores case makes refs/TAGS/x a tag."""
    return ref.lower().startswith("refs/tags/")


TAG_FLAGS = {"-a", "--annotate", "-s", "--sign", "--no-sign", "-f", "--force", "-e", "--edit", "--no-edit",
             "--create-reflog", "-l", "--list", "-d", "--delete", "-v", "--verify", "-i", "--ignore-case",
             "--omit-empty", "--column", "--no-column", "--color", "--no-color"}
TAG_VALUES = {"-m", "--message", "-F", "--file", "-u", "--local-user", "--cleanup", "--trailer", "--sort", "--format",
              "--contains", "--no-contains", "--merged", "--no-merged", "--points-at"}
# What makes git tag list tags: -l, and the options that git documents as implying it. --column, --sort, --format
# and -i do not: with a name, git tag creates the tag.
TAG_LISTING = {"-l", "--list", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at", "-n"}
TAG_CREATING = {"-a", "--annotate", "-s", "--sign", "-f", "--force", "-e", "--edit", "-m", "--message", "-F", "--file",
                "-u", "--local-user", "--trailer"}


def run_tag(args, state):
    parsed = git_options(args, state, "git tag", TAG_FLAGS, TAG_VALUES, {"--column", "--color"}, {"-n"})
    if parsed is None:
        return
    found, positional = parsed
    names = set(name for name, _ in found)
    if names & {"-d", "--delete"}:
        state.add("tag", "git tag --delete deletes a tag")
    elif names & {"-v", "--verify"} or names & TAG_LISTING:
        return
    elif positional or names & TAG_CREATING:
        state.add("tag", "git tag creates or moves a tag")


def run_update_ref(args, state):
    parsed = git_options(args, state, "git update-ref", {"--no-deref", "-d", "--create-reflog", "-z", "--batch-updates"},
                         {"-m"})
    if parsed is None or not parsed[1]:
        return
    ref = parsed[1][0].value()
    if is_tag_ref(ref):
        state.add("tag", "git update-ref changes the tag %s" % ref)
    elif not ref.lower().startswith("refs/") and ref != "HEAD":
        state.unreadable("git update-ref changes %s, a ref outside refs/" % ref)


def run_symbolic_ref(args, state):
    parsed = git_options(args, state, "git symbolic-ref", {"-q", "--quiet", "-d", "--delete", "--short", "--recurse",
                                                           "--no-recurse"}, {"-m"})
    if parsed is None:
        return
    names = set(name for name, _ in parsed[0])
    refs = [word.value() for word in parsed[1]]
    if (len(refs) >= 2 or names & {"-d", "--delete"}) and any(is_tag_ref(ref) for ref in refs):
        state.add("tag", "git symbolic-ref makes or removes a ref that leads to a tag")


def run_worktree_remove(args, state, bases):
    parsed = git_options(args, state, "git worktree remove", {"-f", "--force"}, paths=True)
    if parsed is None:
        return
    for word in parsed[1]:
        check_delete(word, state, bases)


def run_clean(args, state, bases):
    parsed = git_options(args, state, "git clean", {"-d", "-f", "--force", "-i", "--interactive", "-n", "--dry-run",
                                                    "-q", "--quiet", "-x", "-X"}, {"-e", "--exclude"}, paths=True)
    if parsed is None:
        return
    found, paths = parsed
    if set(name for name, _ in found) & {"-n", "--dry-run"}:
        return
    for base in bases:
        if base is None:
            state.unreadable("the directory git clean runs in is not known")
            return
        if not inside(state, base, allow_root=True):
            state.add("delete-outside", "git clean deletes in %s, outside the working tree" % base)
            return
    for word in paths:
        check_delete(word, state, bases, contents=True)
    state.deletes = True


CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l", "--get-color",
                "--get-colorbool"}
CONFIG_WRITES = {"--add", "--replace-all", "--unset", "--unset-all", "--rename-section", "--remove-section"}
CONFIG_FLAGS = CONFIG_READS | CONFIG_WRITES | {"--global", "--system", "--local", "--worktree", "--includes",
                                               "--no-includes", "--null", "-z", "--name-only", "--show-origin",
                                               "--show-scope", "--bool", "--int", "--bool-or-int", "--bool-or-str",
                                               "--path", "--expiry-date", "--no-type", "--fixed-value", "--all",
                                               "--append", "--regexp", "-e", "--edit"}
CONFIG_VALUES = {"--file", "-f", "--blob", "--type", "--default", "--comment", "--value", "--url"}


def run_config(args, state):
    parsed = git_options(args, state, "git config", CONFIG_FLAGS, CONFIG_VALUES)
    if parsed is None:
        return
    found, words = parsed
    names = set(name for name, _ in found)
    positional = [word.value() for word in words]
    if names & {"-e", "--edit"} or positional[:1] == ["edit"]:
        state.unreadable("git config --edit lets any setting change")
        return
    mode = "read" if names & CONFIG_READS else "write" if names & CONFIG_WRITES else None
    if positional and positional[0] in ("get", "list"):
        return
    if positional and positional[0] in ("set", "unset", "rename-section", "remove-section"):
        mode, positional = "write", positional[1:]
    if mode == "read" or (mode is None and len(positional) < 2):
        return
    key = positional[0].lower() if positional else ""
    if key.startswith(RISKY_GIT_CONFIG) or not key:
        state.unreadable("git config %s changes what a later git command does" % key)


# gh.

def gh_action(args, state, what):
    """(index, action): where the first word that is not an option is, and that word, past -R or --repo and its
    value. The action is None when there is none, or when the call asks for help. The result is None when the
    call cannot be read: any other option before the action is one this hook does not know."""
    index = 0
    while index < len(args):
        value = args[index].value()
        if value is None:
            state.unreadable("what %s does is %s" % (what, args[index].why_not_plain()))
            return None
        if value in ("-R", "--repo"):
            index += 2
        elif value.startswith("--repo=") or (value.startswith("-R") and len(value) > 2):
            index += 1
        elif value in ("-h", "--help"):
            return index, None
        elif value.startswith("-"):
            state.unreadable("%s %s is an option this hook does not know" % (what, value))
            return None
        else:
            return index, value
    return index, None


def run_gh(args, state):
    values = [word.value() for word in args]
    if not values:
        return
    if values[0] is not None and values[0].startswith("-"):
        if values[0] in ("--help", "--version", "-h"):
            return
        state.unreadable("gh %s is an option this hook does not follow" % values[0])
        return
    sub = values[0]
    if sub is None:
        state.unreadable("the gh command is %s" % args[0].why_not_plain())
        return
    rest = args[1:]
    if sub == "api":
        run_api(rest, state)
        return
    if sub in GH_QUIET:
        return
    if sub not in ("release", "repo", "secret", "variable", "workflow", "run", "alias", "extension", "ext", "extensions"):
        state.unreadable("gh %s is not a gh command this hook knows, and may be an alias or an extension" % sub)
        return
    found = gh_action(rest, state, "gh " + sub)
    if found is None:
        return
    position, action = found
    if action is None:
        return
    later = rest[position + 1:]
    if sub == "release":
        if action in ("create", "new", "delete", "edit", "upload", "delete-asset"):
            state.add("release", "gh release %s changes a release" % action)
        elif action not in ("view", "list", "ls", "download", "verify", "verify-asset"):
            state.unreadable("gh release %s is not one this hook knows" % action)
    elif sub == "repo":
        if action in ("edit", "delete", "rename", "archive", "unarchive"):
            state.add("settings", "gh repo %s changes the repository" % action)
        elif action in ("deploy-key", "autolink"):
            inner = gh_action(later, state, "gh repo " + action)
            if inner is not None and inner[1] not in (None, "list", "ls"):
                state.add("settings", "gh repo %s %s changes the repository's settings" % (action, inner[1]))
        elif action == "sync":
            run_repo_sync(later, state)
        elif action not in ("create", "new", "fork", "clone", "view", "list", "ls", "set-default", "gitignore", "license"):
            state.unreadable("gh repo %s is not one this hook knows" % action)
    elif sub in ("secret", "variable"):
        if action in ("set", "delete", "remove"):
            state.add("settings", "gh %s %s changes the repository's settings" % (sub, action))
        elif action not in ("list", "ls", "get"):
            state.unreadable("gh %s %s is not one this hook knows" % (sub, action))
    elif sub == "workflow":
        if action in ("enable", "disable", "run"):
            state.add("settings", "gh workflow %s changes which workflows run, and a workflow may take any step" % action)
        elif action not in ("list", "ls", "view"):
            state.unreadable("gh workflow %s is not one this hook knows" % action)
    elif sub == "run":
        if action == "rerun":
            state.add("settings", "gh run rerun starts a workflow again, and a workflow may take any step")
        elif action not in ("list", "ls", "view", "watch", "download", "cancel", "delete"):
            state.unreadable("gh run %s is not one this hook knows" % action)
    elif action not in ("list", "ls", "search", "browse"):
        state.unreadable("gh %s %s defines or runs a command this hook does not see" % (sub, action))


# pflag's false values for a flag such as --force=false.
FALSE = ("false", "0", "f", "F", "FALSE", "False")


def run_repo_sync(args, state):
    index, force = 0, False
    while index < len(args):
        value = args[index].value()
        index += 1
        if value is None:
            state.unreadable("gh repo sync is given %s, which is %s" % (args[index - 1].raw, args[index - 1].why_not_plain()))
            return
        if value == "--":
            break
        if not value.startswith("-") or value == "-":
            continue
        if value == "--force":
            force = True
        elif value.startswith("--force="):
            force = force or value[len("--force="):] not in FALSE
        elif value in ("--branch", "--source"):
            index += 1
        elif value.startswith(("--branch=", "--source=")):
            pass
        elif value in ("--help", "-h"):
            return
        elif value.startswith("--"):
            state.unreadable("gh repo sync %s is an option this hook does not know" % value)
            return
        else:
            letters = value[1:]
            for position, letter in enumerate(letters):
                if letter == "f":
                    force = True
                elif letter in "bs":
                    if position == len(letters) - 1:
                        index += 1
                    break
                else:
                    state.unreadable("gh repo sync -%s is an option this hook does not know" % letter)
                    return
    if force:
        state.add("force-push", "gh repo sync --force overwrites a branch")


API_FLAGS = {"-i", "--include", "--paginate", "--silent", "--slurp", "--verbose"}
API_VALUES = {"-X", "--method", "-H", "--header", "-f", "--raw-field", "-F", "--field", "--input", "-q", "--jq", "-t",
              "--template", "--cache", "-p", "--preview", "--hostname"}


def run_api(args, state):
    method = endpoint = None
    fields, has_input = [], False
    options, index = [], 0
    # Read the options as pflag does: a long option takes its value after = or as the next word, short ones may be
    # clustered, and a short one that takes a value takes the rest of the cluster or the next word.
    while index < len(args):
        word = args[index]
        value = word.value()
        index += 1
        if value is None or not value.startswith("-") or value == "-":
            if endpoint is not None:
                state.unreadable("gh api is given two endpoints")
                return
            endpoint = word
            continue
        if value.startswith("--"):
            name, equals, attached = value.partition("=")
            if name in API_FLAGS:
                continue
            if name not in API_VALUES:
                state.unreadable("gh api %s is an option this hook does not follow" % value)
                return
            if equals:
                options.append((name, attached_word(word, attached)))
            else:
                options.append((name, args[index] if index < len(args) else dynamic("no value")))
                index += 1
            continue
        letters = value[1:]
        for position, letter in enumerate(letters):
            short = "-" + letter
            rest = letters[position + 1:]
            if short in API_FLAGS:
                continue
            if short not in API_VALUES:
                state.unreadable("gh api -%s is an option this hook does not follow" % letter)
                return
            if rest:
                options.append((short, attached_word(word, rest)))
            else:
                options.append((short, args[index] if index < len(args) else dynamic("no value")))
                index += 1
            break
    for option, word in options:
        if option in ("-X", "--method"):
            method = word
        elif option in ("-H", "--header"):
            header = word.value()
            if header is None:
                state.unreadable("gh api sends a header that is not plain text")
                return
            if header.lower().replace(" ", "").startswith("x-http-method-override"):
                state.unreadable("gh api overrides its method with a header")
                return
        elif option in ("-f", "--raw-field", "-F", "--field"):
            fields.append((option, word))
        elif option == "--input":
            has_input = True
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
            state.unreadable("gh api %s to an endpoint that is %s" % (verb, endpoint.why_not_plain()))
        return
    if path.startswith("https://api.github.com/"):
        path = path[len("https://api.github.com/"):]
    elif re.match(r"^[a-z]+://", path):
        state.unreadable("gh api to another host")
        return
    path = re.split(r"[?#]", path.lstrip("/"), maxsplit=1)[0]
    segments = [segment for segment in path.lower().split("/") if segment]
    field = api_body(fields, has_input)
    if segments == ["graphql"]:
        query = field("query")
        if query is None or query is UNSURE:
            state.unreadable("gh api graphql with a query this hook cannot read")
        elif re.search(r"\bmutation\b", query[1]):
            state.unreadable("gh api graphql with a mutation, which may change anything")
        return
    if verb in ("GET", "HEAD"):
        return
    if "%" in path or "\\" in path or any(segment in (".", "..") for segment in segments):
        state.unreadable("gh api %s to %s, a path with . or .., an escape or a backslash" % (verb, path))
        return
    step, why = classify_api(verb, segments, field)
    if step:
        state.add(step, "gh api %s %s %s" % (verb, path, why))


def attached_word(word, attached):
    if word.value() is not None:
        return Word([("lit", attached, True)], attached)
    return dynamic("an attached value")


UNSURE = ("unsure", None)


def api_body(fields, has_input):
    """A function that tells what the body of a call says of one field: None when it holds no such field, UNSURE
    when the hook cannot tell, as with --input, a value from a file or a field given twice, and otherwise
    (option, value)."""
    known, unsure = {}, has_input
    for option, word in fields:
        first = word.parts[0] if word.parts else None
        if first is None or first[0] != "lit" or "=" not in first[1]:
            unsure = True
            continue
        name = re.split(r"[\[=]", first[1], maxsplit=1)[0]
        full = word.value()
        value = None if full is None else full.split("=", 1)[1]
        if value is not None and option in ("-F", "--field") and value.startswith("@"):
            value = None
        known.setdefault(name, []).append((option, value))

    def field(name):
        entries = known.get(name)
        if entries:
            if len(entries) > 1 or entries[0][1] is None:
                return UNSURE
            return entries[0]
        return UNSURE if unsure else None
    return field


# What a call under a repository may change without changing a setting: issues, pull requests, their comments and
# reviews, commit comments, and code. Everything else under the repository counts as a setting: variables, secrets,
# environments, hooks, rulesets, branch protection, collaborators, keys, Pages, Actions, statuses and check runs,
# topics, labels and what GitHub adds later. The list names what is not a setting, so that a new endpoint is one.
REPOSITORY_WORK = {"issues", "pulls", "comments", "commits", "contents", "merges"}


def classify_api(verb, segments, field):
    if segments[0] == "repos" and len(segments) >= 3:
        rest = segments[3:]
    elif segments[0] == "repositories" and len(segments) >= 2:
        rest = segments[2:]
    elif segments[:2] == ["user", "repository_invitations"] or segments[0] in ("markdown", "notifications"):
        return None, ""
    else:
        return "settings", "changes an account, an organization or something else outside a repository"
    if not rest:
        return "settings", "changes or deletes the repository"
    head = rest[0]
    if head == "releases":
        return "release", "changes a release"
    if head == "git":
        return classify_git_api(verb, rest, field)
    if head in REPOSITORY_WORK:
        return None, ""
    return "settings", "changes the repository's %s, which counts as a setting" % head


def classify_git_api(verb, rest, field):
    kind = rest[1] if len(rest) > 1 else None
    if kind == "refs":
        if len(rest) == 2:
            ref = field("ref")
            if ref is UNSURE:
                return "tag", "makes a ref from a body this hook has not read, which may be a tag"
            if ref is None:
                return UNREADABLE, "makes a ref with no name"
            if is_tag_ref(ref[1]):
                return "tag", "makes a tag"
            if ref[1].lower().startswith("refs/heads/"):
                return None, ""
            return UNREADABLE, "makes a ref this hook cannot read"
        if rest[2] == "tags":
            return "tag", "changes a tag"
        if rest[2] == "heads":
            if verb == "DELETE":
                return "force-push", "removes a branch"
            force = field("force")
            if force is None or force == ("-F", "false"):
                return None, ""
            if force is UNSURE:
                return "force-push", "may move a branch with force, from a body this hook has not read"
            return "force-push", "overwrites a branch"
        return UNREADABLE, "changes a ref this hook cannot read"
    if kind == "tags":
        return "tag", "makes a tag"
    if kind in ("blobs", "trees", "commits"):
        return None, ""
    return UNREADABLE, "changes something under git/ that this hook does not know"


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
        # The command takes this step, and perhaps others, each of which needs an entry of its own. It is never
        # a command the hook cannot read, or one that touches the approvals file.
        if step not in found or UNREADABLE in found or "approvals" in found:
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
