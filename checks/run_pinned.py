#!/usr/bin/env python3
"""Run Ratchet's register check from the commit a project pins, and from nothing else.

    python3 -I run_pinned.py <commit> -- register.json
    python3 -I run_pinned.py <commit> --store .ratchet --repository <url> -- register.json --markdown REGISTER.md

A project copies this one file, once, from the commit it pins, into its own repo, and runs it with python3 -I in the
step of a job its protection of main requires, or in the local check script that CI runs. init.py prints both
commands, with the name of this file's blob in the pinned tree (copy_command and run_command below): the copy is kept
only when git hash-object gives it that name, and the step runs the copy only when it still does, so a copy that is
missing, empty, cut short or not the pinned commit's fails the step.

It uses the Ratchet clone, .ratchet unless --store names another, only as a store of git objects. When there is none
it makes one, empty, and fetches the pinned commit alone into it, shallow and by its id, from the repository, Ratchet's
on GitHub unless --repository names another. When the repository does not give a commit by its id, it fetches the
repository's branches and tags into it, what a clone fetches, as 0.12 did. When the commit is not in a store that was there, it fetches the commit, from
that repository only. When the repository cannot be reached and the store lacks the commit, it refuses: it never
passes without the pinned commit. It never reads the clone's working tree, so an
edit there, one that git status does not show because of git update-index --assume-unchanged included, and a file
beside the check that is not Ratchet's, such as a checks/argparse.py, are never run.

git never reads a config of the store's, the user's or the system's, and never fetches while it reads: it runs in a
new, empty git directory, with the store's object directory as GIT_OBJECT_DIRECTORY, GIT_CONFIG_NOSYSTEM, the global
config an empty file, HOME in a new directory, every GIT_ variable of the environment dropped, and no lazy fetch (see
Git). So a core.sshCommand, core.fsmonitor, hook, credential helper, url rewrite or upload-pack of the store's config,
or of the user's, never runs, also not for a partial clone that misses an object. The fetches into a missing
store and the fetch of a missing commit are the only steps that reach the network, each explicit and with the same
isolation.

It reads the commit, its tree and every blob under it with git cat-file, and no other object of the store, the trees
one level at a time and the blobs together, with replace objects off, and hashes each
object itself: an object whose bytes do not give its name is refused, so a corrupt or swapped object, or one that a
replace ref would put in its place, is never run. It reads raw objects rather than git archive's output, which applies
attributes and filters. It writes the tree into a new directory from tempfile, which it removes at the end, and runs
checks/check_register.py there with python3 -E -s, so neither the environment nor the user's site directory changes
what is imported, and the directory of the check holds only the commit's files. The arguments after -- are the check's,
and it runs from the directory it is started in.

Before it runs the check, it compares its own bytes with checks/run_pinned.py of the commit, and refuses to go on when
they differ: a copy that is stale after an upgrade, or edited, is named, with the command that copies it again. A copy
cut short after the guard at the top refuses as cut short. One cut before it, or empty, cannot refuse, and exits 0:
the hash in the printed step is what catches that.

Threat model: the shared one in checks/README.md. It catches mistakes and drift: a check edited in the clone and
hidden from git status, a module planted beside the check, a clone at another commit, a missing clone, a corrupt
object, a store or user config that names a program, a copy of this file that is not the pinned commit's. It does not
stand against someone who edits the copy, the step or the script that runs it: those are files of the project, and a
change to them is in the project's diff, for the owner's required review of the owner's paths to catch. It does not
stand against a git, a python3 or a PATH that is not what it says, or against the repository it clones from.

It imports nothing from beside it, so python3 -I, which leaves the directory of the script out of sys.path, runs it.
Exit code: the check's, 0 or 1. 2: it could not run, and the check did not run. Standard library only. Run on
Python 3.9 and 3.12.
"""

import sys

sys.dont_write_bytecode = True

# The last line of this file. A copy cut short after this point would define the functions and never run main, and exit
# 0; it refuses instead. A copy cut before it, or empty, cannot refuse: the step that adopt mode prints hashes the copy
# before it runs it, and refuses that.
END = b"# The end of run_pinned.py.\n"
if __name__ == "__main__":
    try:
        with open(__file__, "rb") as _handle:
            _whole = _handle.read().endswith(END)
    except OSError:
        _whole = False
    if not _whole:
        sys.stdout.write("run_pinned: refused: %s is cut short or cannot be read, so it is not the pinned commit's\n"
                         "run_pinned: the check did not run\n" % sys.argv[0])
        sys.exit(2)

import hashlib
import os
import re
import shlex
import shutil
import subprocess
import tempfile

# The repository a missing store is cloned from, and a missing commit fetched from: the one init.py prints.
REPOSITORY = "https://github.com/fabian-von-tiedemann/ratchet"
STORE = ".ratchet"
# Where adopt mode says to copy this file to, in the project's repo, from the pinned commit.
COPY = ".github/ratchet/run_pinned.py"
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
# Settings given on every git command line. Config is read from nowhere else, so these are git's own defaults made
# explicit: no hooks, no fsmonitor, and no automatic gc or maintenance, which would prune the store's objects as
# unreachable from the empty repo it is read through.
SETTINGS = ("core.hooksPath=" + os.devnull, "core.fsmonitor=false", "gc.auto=0", "maintenance.auto=false",
            "fetch.writeCommitGraph=false")


class Refused(Exception):
    """The pinned check cannot be run. Nothing of the store's has been run."""


def objects_of(store):
    """The object directory of the store: that of store/.git, of the git directory a .git file names, or of the store
    itself when it is a bare repo, and, for a worktree, that of its common directory. Never one above the store, so a
    store that is not a repo of its own is refused rather than taken for the project's repo. Only paths are read here:
    nothing of the store's config, hooks or refs."""
    dot_git = os.path.join(store, ".git")
    if os.path.isdir(dot_git):
        git_dir = dot_git
    elif os.path.isfile(dot_git):
        with open(dot_git, "r", encoding="utf-8", errors="replace") as handle:
            line = handle.readline().rstrip("\n")
        if not line.startswith("gitdir: "):
            raise Refused("%s holds a .git file that names no git directory" % store)
        git_dir = os.path.join(store, line[len("gitdir: "):])
    elif os.path.isfile(os.path.join(store, "HEAD")) and os.path.isdir(os.path.join(store, "objects")):
        git_dir = store
    else:
        raise Refused("%s exists and is not a git repo of its own. Remove it, and the next run clones Ratchet there" % store)
    common = os.path.join(git_dir, "commondir")
    if os.path.isfile(common):
        with open(common, "r", encoding="utf-8", errors="replace") as handle:
            git_dir = os.path.join(git_dir, handle.readline().rstrip("\n"))
    objects = os.path.join(git_dir, "objects")
    if not os.path.isdir(objects):
        raise Refused("%s has no object directory at %s" % (store, objects))
    return os.path.abspath(objects)


class Git:
    """git with no configuration from the store, the user or the system, and no implicit fetch.

    It runs in a new, empty git directory of its own, made in scratch, with the store's object directory given as
    GIT_OBJECT_DIRECTORY, so the store's config, hooks, refs, attributes and info are never read. GIT_CONFIG_NOSYSTEM,
    GIT_CONFIG_GLOBAL and GIT_CONFIG pointing at an empty file, and HOME and XDG_CONFIG_HOME set to scratch, leave out
    the system's and the user's config, and every GIT_ variable of the environment is dropped, GIT_CONFIG_PARAMETERS
    and GIT_CONFIG_COUNT included. With no config there is no promisor remote, so a missing object is never fetched
    lazily; GIT_NO_LAZY_FETCH and --no-lazy-fetch, where the installed git knows it, say so again. Replace objects are
    off. Objects that the store's alternates name are read too: every object is hashed by Objects, so that is harmless."""

    def __init__(self, scratch):
        home = os.path.join(scratch, "home")
        os.mkdir(home, 0o700)
        empty = os.path.join(scratch, "empty-config")
        os.close(os.open(empty, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
        env.update(LC_ALL="C", HOME=home, XDG_CONFIG_HOME=home, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=empty,
                   GIT_CONFIG=empty, GIT_ATTR_NOSYSTEM="1", GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
                   GIT_TERMINAL_PROMPT="0", GIT_CEILING_DIRECTORIES=os.path.dirname(os.path.abspath(scratch)))
        self.env, self.git_dir, self.objects = env, os.path.join(scratch, "git"), None
        self.options = ["--no-replace-objects"]
        if self.run(None, "--no-lazy-fetch", "version")[0] == 0:
            self.options.insert(0, "--no-lazy-fetch")
        code, _, error = self.run(None, "init", "--quiet", "--bare", "--template=", self.git_dir)
        if code != 0:
            raise Refused("cannot make an empty git directory to read the store through: %s" % error)

    def run(self, objects, *args, data=None):
        """(exit code, stdout bytes, stderr). With objects, git reads and writes objects there, through the empty git
        directory; with None, it runs with no repo, for git init and git clone."""
        env = dict(self.env)
        if objects is not None:
            env.update(GIT_DIR=self.git_dir, GIT_OBJECT_DIRECTORY=objects)
        command = ["git"] + list(getattr(self, "options", []))
        for setting in SETTINGS:
            command += ["-c", setting]
        try:
            result = subprocess.run(command + list(args), input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    env=env, cwd=os.path.dirname(self.env["HOME"]), timeout=600)
        except (OSError, subprocess.SubprocessError) as error:
            raise Refused("cannot run git: %s" % error)
        return result.returncode, result.stdout, result.stderr.decode("utf-8", "replace").strip()

    def kind(self, objects, name):
        """The type of the object name in the store, or None when it is not there."""
        code, out, _ = self.run(objects, "cat-file", "-t", name)
        return out.decode("ascii", "replace").strip() if code == 0 else None


def store_with(git, store, commit, repository):
    """The object directory of the store, made when it is missing, and holding the commit, fetched when it does not.
    A missing store is made empty, with no checkout, and the pinned commit alone fetched into it, shallow and by its id,
    so neither the history nor any other commit is fetched and indexed. When the repository does not give a commit by
    its id, the branches and tags of the repository are fetched into the store, which is what a clone fetches, as
    0.12 did. A store that was there and lacks the commit fetches it by its id, with the same fall back. The fetches are the only
    steps that reach the network, each explicit, from the repository named alone, and with the same isolation as every
    read: a fetch runs in the empty git directory, writing into the store's object directory, so not even the store's
    remotes or url rewrites are read. Nothing is removed. When none of them gives the commit, it is refused: the check
    never runs, and never passes, without the pinned commit."""
    made = not os.path.lexists(store)
    if made:
        code, _, error = git.run(None, "init", "--quiet", "--template=", os.path.abspath(store))
        if code != 0:
            raise Refused("cannot make a store at %s: %s" % (store, error))
    objects = objects_of(store)
    if git.kind(objects, commit) is None:
        # A store made now gets the commit alone, shallow. One that was there, perhaps left empty by a run that could
        # not reach the host, fetches it by its id, with its history (round 2 of #140).
        shallow = ["--depth=1"] if made else []
        code, _, error = git.run(objects, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", *shallow,
                                 repository, commit)
        if code != 0 or git.kind(objects, commit) != "commit":
            # The host does not give a commit by its id, or this id is not one: fetch what a clone would.
            by_id = error
            code, _, error = git.run(objects, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", repository,
                                     "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*")
            if code != 0 and made:
                raise Refused("cannot fetch %s into %s: %s" % (repository, store, error))
            if code != 0 or git.kind(objects, commit) is None:
                raise Refused("commit %s is not in %s, and cannot be fetched from %s: %s"
                              % (commit, store, repository, error or by_id or "it is in none of its branches or tags"))
    found = git.kind(objects, commit)
    if found != "commit":
        raise Refused("%s is not a commit in %s%s" % (commit, store, ", it is a %s" % found if found else ""))
    return objects


class Objects:
    """Objects read from the store with one git cat-file --batch, each hashed here: an object whose bytes do not give
    its name is refused."""

    def __init__(self, git, objects):
        self.git, self.objects = git, objects

    def read(self, names):
        """{name: (type, bytes)} for the names, every one checked against its hash."""
        code, out, error = self.git.run(self.objects, "cat-file", "--batch",
                                        data="".join(name + "\n" for name in names).encode("ascii"))
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


def blob_hash(data):
    """The name git gives a blob with these bytes."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def blob_of(objects, commit, path):
    """The name of the blob at path in the commit's tree, read through the commit and each tree on the way, every one
    hashed, so the name is the one the pinned commit gives."""
    name, parts = tree_of(objects, commit), path.split("/")
    for at, part in enumerate(parts):
        kind_, body = objects.read([name])[name]
        if kind_ != "tree":
            raise Refused("%s is not a tree" % name)
        found = [(mode, oid) for mode, entry, oid in entries(name, body) if entry == part.encode("utf-8")]
        last = at == len(parts) - 1
        if not found or (found[0][0] in FILE_MODES) != last or (not last and found[0][0] != DIRECTORY):
            raise Refused("commit %s holds no file %s" % (commit, path))
        name = found[0][1]
    return name


def stored_blob(store, commit, path):
    """blob_of for a store of objects in a directory of its own, made and removed here. For init.py, which prints the
    name in the commands below."""
    scratch = tempfile.mkdtemp(prefix="ratchet-pinned-")
    try:
        git = Git(scratch)
        objects = objects_of(store)
        if git.kind(objects, commit) != "commit":
            raise Refused("%s is not a commit in %s" % (commit, store))
        return blob_of(Objects(git, objects), commit, path)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def quoted(path):
    """A path for sh, from the directory the command runs in."""
    return shlex.quote(path) if os.path.isabs(path) else '"$PWD"/' + shlex.quote(path)


def copy_command(objects, commit, blob, target):
    """The sh command, run from the project's root, that copies checks/run_pinned.py of the commit out of the store's
    object directory to target, and verifies it: every git it runs starts under env -i, so no GIT_ variable of the
    environment (GIT_DIR, GIT_COMMON_DIR, GIT_CONFIG_COUNT and the rest) is in effect, and reads through a new, empty git
    directory, with no config of the store's, the user's or the system's and no lazy fetch. The copy is kept only when
    git hash-object gives it the name blob, the one the pinned tree names. Otherwise nothing is left at target, and the
    command fails."""
    temporary = target + ".new"
    return ("mkdir -p %s && (t=$(mktemp -d) && trap 'rm -rf \"$t\"' EXIT && "
            "g() { env -i PATH=\"$PATH\" HOME=\"$t\" XDG_CONFIG_HOME=\"$t\" GIT_CONFIG_NOSYSTEM=1 "
            "GIT_CONFIG_GLOBAL=/dev/null GIT_NO_LAZY_FETCH=1 GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 \"$@\"; } && "
            "g git init -q --bare --template= \"$t/git\" && g GIT_DIR=\"$t/git\" GIT_OBJECT_DIRECTORY=%s git "
            "--no-replace-objects cat-file blob %s > %s && "
            "test \"$(g GIT_DIR=\"$t/git\" git hash-object --no-filters --stdin < %s)\" = %s && "
            "mv %s %s) || { rm -f %s; echo 'run_pinned.py was not copied: the store does not hold blob %s of commit %s "
            "as it is' >&2; false; }"
            % (shlex.quote(os.path.dirname(target) or "."), quoted(objects), blob, shlex.quote(temporary),
               shlex.quote(temporary), blob, shlex.quote(temporary), shlex.quote(target), shlex.quote(temporary),
               blob, commit))


def run_command(commit, blob, target, register="register.json", markdown=False):
    """The sh command that runs the copy at target, on the register at the path register from where it runs: only when git hash-object gives its bytes the name blob, so a copy
    that is missing, empty, cut short or not the pinned commit's stops the step or the script rather than passing it.
    The hash check is an if with exit 1, not the left side of &&, which set -e does not stop on: a script with set -e or
    without it ends there, in sh, bash and dash."""
    return ("if ! test \"$(git hash-object --no-filters --stdin < %s)\" = %s; then echo '%s is not checks/run_pinned.py "
            "of commit %s: copy it again' >&2; exit 1; fi; python3 -I %s %s -- %s%s"
            % (shlex.quote(target), blob, target, commit, shlex.quote(target), commit,
               # A name that starts with - would be read as an option by the check after the runner's --.
               shlex.quote("./" + register if register.startswith("-") else register),
               " --markdown REGISTER.md" if markdown else ""))


def local_line(commit, blob, target, register="register.json", markdown=False):
    """The line for a local check script: run_command in a subshell, and exit 1 when it fails. A script without set -e
    goes on after a command that fails, so a register that fails the check, or a runner that is not the pinned one,
    would be followed by the rest of the script, to "all green". The subshell's own exit and the || exit 1 stop the
    script in sh, bash and dash, with set -e or without it."""
    return "( %s ) || exit 1" % run_command(commit, blob, target, register, markdown)


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
    checks/run_pinned.py in it, or None. Only the objects reachable from the tree are read: the trees one level at a
    time, each level in one read, and then every blob in one read, so the number of reads follows the depth of the
    tree and not the number of its directories."""
    level, files, own = [(tree, directory, "")], [], None
    while level:
        trees = objects.read(sorted(set(name for name, _, _ in level)))
        following = []
        for name, path, shown in level:
            kind_, body = trees[name]
            if kind_ != "tree":
                raise Refused("%s is not a tree" % name)
            for mode, part, oid in entries(name, body):
                target = os.path.join(path, os.fsdecode(part))
                relative = shown + part.decode("utf-8", "replace")
                if mode == DIRECTORY:
                    os.mkdir(target, 0o755)
                    following.append((oid, target, relative + "/"))
                elif mode in FILE_MODES:
                    files.append((mode, oid, target, relative))
                elif mode not in SKIPPED:
                    raise Refused("%s has a mode this does not know: %s" % (relative, mode.decode("ascii", "replace")))
        level = following
    blobs = objects.read(sorted(set(oid for _, oid, _, _ in files))) if files else {}
    for mode, oid, target, relative in files:
        blob_kind, data = blobs[oid]
        if blob_kind != "blob":
            raise Refused("%s is not a blob" % relative)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODES[mode])
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        if relative == SELF:
            own = data
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
    scratch = None
    try:
        commit, store, repository, rest = parse(argv)
        if os.path.exists(repository):
            repository = os.path.abspath(repository)
        scratch = tempfile.mkdtemp(prefix="ratchet-pinned-")
        git = Git(scratch)
        objects = Objects(git, store_with(git, store, commit, repository))
        tree = tree_of(objects, commit)
        directory = os.path.join(scratch, "tree")
        os.mkdir(directory, 0o700)
        own = export(objects, tree, directory)
        if own is None:
            raise Refused("commit %s holds no %s, so this copy, %s, cannot be checked against it" % (commit, SELF, sys.argv[0]))
        with open(os.path.abspath(__file__), "rb") as handle:
            mine = handle.read()
        if own != mine:
            raise Refused("this copy, %s, is not checks/run_pinned.py of commit %s, so it may not be the code that commit "
                          "runs. Copy it again, from the project's root: %s"
                          % (sys.argv[0], commit, copy_command(os.path.relpath(objects.objects)
                                                               if not os.path.isabs(store) else objects.objects,
                                                               commit, blob_hash(own), sys.argv[0])))
        check = os.path.join(directory, *CHECK)
        if not os.path.isfile(check):
            raise Refused("commit %s holds no %s" % (commit, "/".join(CHECK)))
        out.write("run_pinned: Ratchet at %s, every object hashed, read with no git config, exported to a new directory; "
                  "running %s\n" % (commit, "/".join(CHECK)))
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
        if scratch is not None:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
# The end of run_pinned.py.
