#!/usr/bin/env python3
"""Run Ratchet's register check from the commit a project pins, and from nothing else.

    python3 -I run_pinned.py <commit> -- register.json
    python3 -I run_pinned.py <commit> --store .ratchet --repository <url> -- register.json --markdown REGISTER.md

A project copies this one file, once, from the commit it pins, into its own repo, and runs it with python3 -I in the
step of a job its protection of main requires, or in the local check script that CI runs:

    mkdir -p .github/ratchet && git -C .ratchet --no-replace-objects show <commit>:checks/run_pinned.py > .github/ratchet/run_pinned.py
    python3 -I .github/ratchet/run_pinned.py <commit> -- register.json

It uses the Ratchet clone, .ratchet unless --store names another, only as a store of git objects. When there is none
it clones one from the repository, Ratchet's on GitHub unless --repository names another, with no checkout. When the
commit is not in it, it fetches the commit. It never reads the clone's working tree, so an edit there, one that git
status does not show because of git update-index --assume-unchanged included, and a file beside the check that is not
Ratchet's, such as a checks/argparse.py, are never run.

It reads the commit, its tree and every blob under it from the store with git cat-file, with replace objects off, and
hashes each object itself: an object whose bytes do not give its name is refused, so a corrupt or swapped object, or
one that a replace ref would put in its place, is never run. It reads raw objects rather than git archive's output,
because git archive applies the attributes and the filters that the store's own config names. It writes the tree into
a new directory from tempfile, which it removes at the end, and runs checks/check_register.py there with python3 -E -s,
so neither the environment nor the user's site directory changes what is imported, and the directory of the check
holds only the commit's files. The arguments after -- are the check's, and it runs from the directory it is started in.

Before any of that, it compares its own bytes with checks/run_pinned.py of the commit, and refuses to go on when they
differ: a copy that is stale after an upgrade, or edited, is named, with the command that copies it again.

Threat model: the shared one in checks/README.md. It catches mistakes and drift: a check edited in the clone and
hidden from git status, a module planted beside the check, a clone at another commit, a missing clone, a corrupt
object, a copy of this file that is not the pinned commit's. It does not stand against someone who edits the copy,
the step or the script that runs it: those are files of the project, and a change to them is in the project's diff,
for the owner's required review of the owner's paths to catch. It runs git in the store, whose config it does not read
or neutralize beyond hooks, so it does not stand against a store whose git config was set to run a program: the
guarantee is about the bytes of the check that runs.

It imports nothing from beside it, so python3 -I, which leaves the directory of the script out of sys.path, runs it.
Exit code: the check's, 0 or 1. 2: it could not run, and the check did not run. Standard library only. Run on
Python 3.9 and 3.12.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import os
import re
import shutil
import subprocess
import tempfile

# The repository a missing store is cloned from, and a missing commit fetched from: the one init.py prints.
REPOSITORY = "https://github.com/fabian-von-tiedemann/ratchet"
STORE = ".ratchet"
CHECK = ("checks", "check_register.py")
SELF = "checks/run_pinned.py"
COMMIT = re.compile(r"^[0-9a-f]{40}\Z")
# A tree entry: a mode, a space, a name, NUL and the 20 bytes of the object's name.
ENTRY = re.compile(rb"([0-7]{5,6}) ([^\0]+)\0", re.S)
FILE_MODES = {b"100644": 0o644, b"100755": 0o755}
DIRECTORY = b"40000"
# A link and a submodule are not written: the check needs neither, and neither is a file to run.
SKIPPED = (b"120000", b"160000")
USAGE = "usage: python3 -I run_pinned.py <commit> [--store <dir>] [--repository <url>] -- <arguments of check_register.py>"


class Refused(Exception):
    """The pinned check cannot be run. Nothing of the store's has been run."""


def environment():
    """git with nothing from the environment that names a repo, an object store or a replacement, and no prompt."""
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    env.update(LC_ALL="C", GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    return env


def git(git_dir, *args, data=None):
    """Run git on the store, with no work tree, no replace objects and no hooks. (exit code, stdout bytes, stderr)."""
    command = ["git", "--no-replace-objects", "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false"]
    if git_dir is not None:
        command.append("--git-dir=" + git_dir)
    try:
        result = subprocess.run(command + list(args), input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=environment(), timeout=600)
    except (OSError, subprocess.SubprocessError) as error:
        raise Refused("cannot run git: %s" % error)
    return result.returncode, result.stdout, result.stderr.decode("utf-8", "replace").strip()


def git_dir_of(store):
    """The git directory of the store: store/.git, or the store itself when it is a bare repo. Never one above it, so a
    store that is not a repo of its own is refused rather than taken for the project's repo."""
    dot_git = os.path.join(store, ".git")
    if os.path.isdir(dot_git) or os.path.isfile(dot_git):
        return dot_git
    if os.path.isfile(os.path.join(store, "HEAD")) and os.path.isdir(os.path.join(store, "objects")):
        return store
    raise Refused("%s exists and is not a git repo of its own. Remove it, and the next run clones Ratchet there" % store)


def store_with(store, commit, repository):
    """The git directory of the store, cloned when it is missing, and holding the commit, fetched when it does not."""
    if not os.path.lexists(store):
        code, _, error = git(None, "clone", "--quiet", "--no-checkout", repository, store)
        if code != 0:
            raise Refused("cannot clone %s into %s: %s" % (repository, store, error))
    git_dir = git_dir_of(store)
    if kind(git_dir, commit) is None:
        code, _, error = git(git_dir, "fetch", "--quiet", "--no-tags", repository, commit)
        if code != 0:
            raise Refused("commit %s is not in %s, and cannot be fetched from %s: %s" % (commit, store, repository, error))
    found = kind(git_dir, commit)
    if found != "commit":
        raise Refused("%s is not a commit in %s%s" % (commit, store, ", it is a %s" % found if found else ""))
    return git_dir


def kind(git_dir, name):
    """The type of the object name in the store, or None when it is not there."""
    code, out, _ = git(git_dir, "cat-file", "-t", name)
    return out.decode("ascii", "replace").strip() if code == 0 else None


class Objects:
    """Objects read from the store with one git cat-file --batch, each hashed here: an object whose bytes do not give
    its name is refused."""

    def __init__(self, git_dir):
        self.git_dir = git_dir

    def read(self, names):
        """{name: (type, bytes)} for the names, every one checked against its hash."""
        code, out, error = git(self.git_dir, "cat-file", "--batch", data="".join(name + "\n" for name in names).encode("ascii"))
        if code != 0:
            raise Refused("git cat-file failed: %s" % error)
        found, at = {}, 0
        for name in names:
            end = out.find(b"\n", at)
            header = out[at:end].decode("ascii", "replace").split(" ")
            if end < 0 or len(header) != 3 or header[0] != name or not header[2].isdigit():
                raise Refused("object %s is missing from the store, or unreadable" % name)
            size = int(header[2])
            body = out[end + 1:end + 1 + size]
            if len(body) != size or out[end + 1 + size:end + 2 + size] != b"\n":
                raise Refused("object %s is cut short in the store" % name)
            at = end + 2 + size
            digest = hashlib.sha1(header[1].encode("ascii") + b" " + header[2].encode("ascii") + b"\0" + body).hexdigest()
            if digest != name:
                raise Refused("object %s is corrupt in the store: its bytes hash to %s. Remove the store, and the next "
                              "run clones it again" % (name, digest))
            found[name] = (header[1], body)
        return found


def tree_of(objects, commit):
    """The name of the tree of the commit, from the commit's bytes."""
    kind_, body = objects.read([commit])[commit]
    match = re.match(rb"tree ([0-9a-f]{40})\n", body)
    if kind_ != "commit" or not match:
        raise Refused("%s is not a commit with a tree" % commit)
    return match.group(1).decode("ascii")


def entries(tree, body):
    """(mode, name, object) for each entry of a tree, every name one plain part of a path."""
    found, at = [], 0
    while at < len(body):
        match = ENTRY.match(body, at)
        if not match or match.end() + 20 > len(body):
            raise Refused("tree %s cannot be read" % tree)
        mode, name = match.group(1), match.group(2)
        if name in (b".", b"..", b".git") or b"/" in name:
            raise Refused("tree %s holds an entry named %r" % (tree, name))
        found.append((mode, name, body[match.end():match.end() + 20].hex()))
        at = match.end() + 20
    return found


def export(objects, tree, directory):
    """Write the tree, read and hashed object by object, into directory, which is new and empty. Returns the bytes of
    checks/run_pinned.py in it, or None."""
    pending, own = [(tree, directory, "")], None
    while pending:
        name, path, shown = pending.pop()
        kind_, body = objects.read([name])[name]
        if kind_ != "tree":
            raise Refused("%s is not a tree" % name)
        listed = entries(name, body)
        blobs = objects.read([oid for mode, _, oid in listed if mode in FILE_MODES]) if listed else {}
        for mode, part, oid in listed:
            target = os.path.join(path, os.fsdecode(part))
            relative = shown + part.decode("utf-8", "replace")
            if mode == DIRECTORY:
                os.mkdir(target, 0o755)
                pending.append((oid, target, relative + "/"))
            elif mode in FILE_MODES:
                blob_kind, data = blobs[oid]
                if blob_kind != "blob":
                    raise Refused("%s is not a blob" % relative)
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODES[mode])
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(data)
                if relative == SELF:
                    own = data
            elif mode not in SKIPPED:
                raise Refused("%s has a mode this does not know: %s" % (relative, mode.decode("ascii", "replace")))
    return own


def parse(argv):
    """(commit, store, repository, the check's arguments) from the command line."""
    if "--" not in argv:
        raise Refused(USAGE)
    at = argv.index("--")
    own, rest = argv[:at], argv[at + 1:]
    options = {"--store": STORE, "--repository": REPOSITORY}
    commit = None
    while own:
        word = own.pop(0)
        if word in options and own:
            options[word] = own.pop(0)
        elif commit is None and not word.startswith("-"):
            commit = word
        else:
            raise Refused(USAGE)
    if commit is None:
        raise Refused(USAGE)
    if not COMMIT.match(commit):
        raise Refused("%s is not a commit: a commit is 40 characters 0-9 and a-f" % commit)
    return commit, options["--store"], options["--repository"], rest


def main(argv=None, out=None):
    out = out or sys.stdout
    argv = list(sys.argv[1:] if argv is None else argv)
    directory = None
    try:
        commit, store, repository, rest = parse(argv)
        git_dir = store_with(store, commit, repository)
        objects = Objects(git_dir)
        tree = tree_of(objects, commit)
        directory = tempfile.mkdtemp(prefix="ratchet-pinned-")
        own = export(objects, tree, directory)
        with open(os.path.abspath(__file__), "rb") as handle:
            mine = handle.read()
        if own != mine:
            raise Refused("this copy, %s, is not checks/run_pinned.py of commit %s, so it may not be the code that commit "
                          "runs. Copy it again: git -C %s --no-replace-objects show %s:checks/run_pinned.py > %s"
                          % (sys.argv[0], commit, store, commit, sys.argv[0]))
        check = os.path.join(directory, *CHECK)
        if not os.path.isfile(check):
            raise Refused("commit %s holds no %s" % (commit, "/".join(CHECK)))
        out.write("run_pinned: Ratchet at %s, every object hashed, exported to a new directory; running %s\n"
                  % (commit, "/".join(CHECK)))
        out.flush()
        return subprocess.run([sys.executable, "-E", "-s", "-B", check] + rest).returncode
    except Refused as error:
        out.write("run_pinned: refused: %s\n" % error)
        out.write("run_pinned: the check did not run\n")
        return 2
    except OSError as error:
        out.write("run_pinned: cannot run: %s\n" % error)
        out.write("run_pinned: the check did not run\n")
        return 2
    finally:
        if directory is not None:
            shutil.rmtree(directory, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
