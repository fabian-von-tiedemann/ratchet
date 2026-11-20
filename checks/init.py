#!/usr/bin/env python3
"""Start a project on Ratchet with one command, from the root of its repo.

    git clone --branch v<version> https://github.com/fabian-von-tiedemann/ratchet .ratchet
    python3 .ratchet/checks/init.py --check     # say what it would write and what it skips, write nothing
    python3 .ratchet/checks/init.py             # write it
    python3 .ratchet/checks/init.py --name "My project"
    python3 .ratchet/checks/init.py --solo           # one agent and no control room

It writes what README's "Start here" sets up:

- AGENTS.md, from templates/AGENTS.md, with the project's name in its title, and without the lines
  <!-- team --> and <!-- /team -->. With --solo it also leaves out what stands between them: the control room's
  line and the skills
- register.json, from templates/register.json, with the project's name
- REGISTER.md, generated from the register.json that stands after the run, as check_register.py --write does
- .github/workflows/ratchet.yml, from templates/ratchet-checks.yml, with the commit of the Ratchet checkout it
  runs from, read with git rev-parse HEAD, as the pin. It has the job ratchet, whose register check also fails
  while AGENTS.md holds a placeholder of the template, and the job project-checks, the place for the project's
  own checks
- the line /.ratchet/ at the end of .gitignore, unless the last line there that mentions .ratchet is exactly
  .ratchet/ or /.ratchet/, with no negation after it

The name is the folder's name unless --name gives one. It is ASCII letters and digits, in words joined by one
space, "-", "." or "_", at most 100 characters.

It never overwrites a file. A file that exists with the content it would write is unchanged. A file that exists
with other content, or that is not a plain file, is skipped, named, and left as it is, and the run exits 1. The one
file it changes is .gitignore, and only by adding its line at the end, in one step, and only if .gitignore still
holds what it read: when it changed meanwhile, init.py stops and leaves it as it is. With --check it writes
nothing and says the same. A second run says that nothing changed. Then it names what is left to do: each
placeholder of the template that AGENTS.md holds, from the fixed list in check_register.py, the jobs to require in
the protection of main, and, when the repo's git config names no remote, the adopted rules that wait for one. At
the end it runs check_register.py on register.json and REGISTER.md and shows the result.

Each file is written in full to a temporary file beside it, synced, and then linked into place with a hard link,
which fails when the file appeared meanwhile, so a file is either missing or whole and is never overwritten. On a
file system with no hard links it stops and writes no file there, rather than write one directly. A run that
stops halfway leaves whole files, and the next run writes the rest.

It runs only from the root of a git repo: a .git directory that holds HEAD and objects/, or a .git file of the one
line "gitdir: <path>", naming a directory that holds HEAD and commondir or objects/, as a worktree or a submodule
has. It reads these files and does not run git there.

Threat model: a person or an agent runs it in their own repo. It guards against mistakes: overwriting work, a
pin that is not a full commit or not the commit of the files it copies, a result that is half written, an edit
to .gitignore lost, a run in the wrong folder, .ratchet/ not ignored, a placeholder left in AGENTS.md, text that
does not apply to the project, a check not marked as required. It does not guard against a hostile Ratchet
checkout, whose code it is, or a concurrent attacker. It never runs code from the project's repo: it runs git
only in the Ratchet checkout, never in the project's repo, whose git config could name a program to run, and the
check at the end is Ratchet's own. It reads the repo's git config as a file to see whether it names a remote.

Exit code 0: everything is in place and the register passes. 1: a file was skipped, or the register does not
pass. 2: it could not run, and wrote nothing, or it stopped at a file it could not write or at a .gitignore that
changed, and says how many files it wrote before.
Standard library only. Run on Python 3.9 and 3.12.
"""

import argparse
import errno
import json
import os
import re
import secrets
import subprocess
import sys

import check_register
import registry

RATCHET = registry.ROOT
AGENTS_TITLE = "# Working rules for %s"
PLACEHOLDER = "<40-character commit sha>"
WORKFLOW = os.path.join(".github", "workflows", "ratchet.yml")
IGNORE = "/.ratchet/"
IGNORED = (b".ratchet/", b"/.ratchet/")
NAME = re.compile(r"^[A-Za-z0-9]+(?:[-._ ][A-Za-z0-9]+)*\Z")
NAME_LENGTH = 100
COMMIT = re.compile(r"^[0-9a-f]{40}\Z")
TEAM = ("<!-- team -->\n", "<!-- /team -->\n")
JOBS = ("ratchet", "project-checks")
# The rules of the starter register whose check cannot run before the repo has a remote, and why.
WAIT_FOR_REMOTE = {
    "ratchet.register-on-top": "the workflow runs its check on the host",
    "ratchet.protected-main": "the protection of main is a setting of the host",
    "ratchet.no-secrets": "its scan runs in CI on the host",
    "ratchet.lesson-names-check": "the lesson template is an issue template of the host",
}


class InitError(Exception):
    """init.py cannot run. Nothing has been written."""


class Changed(Exception):
    """A file changed between the plan and the write. It was left as it is."""


def name_problem(name):
    """Why name cannot be the project's name, or None."""
    if not NAME.match(name):
        return ('it must be ASCII letters and digits, in words joined by one space, "-", "." or "_", '
                "with nothing else before, between or after them")
    if len(name) > NAME_LENGTH:
        return "it is longer than %d characters" % NAME_LENGTH
    if registry.AUTOLINK.search(name):
        return "it would be shown as a link"
    problem = registry.text_problem(name)
    if problem:
        return "it " + problem
    return None


def commit_problem(text):
    """Why text is not a full commit sha, or None."""
    if not COMMIT.match(text):
        return "%s is not a commit: a commit is 40 characters 0-9 and a-f" % json.dumps(text)
    return None


def git_root_problem(root):
    """Why root is not the root of a git repo, or None. Read from the files in .git: git is not run there."""
    dot_git = os.path.join(root, ".git")
    if os.path.isdir(dot_git):
        if os.path.isfile(os.path.join(dot_git, "HEAD")) and os.path.isdir(os.path.join(dot_git, "objects")):
            return None
        return ".git is a directory without HEAD and objects/"
    if not os.path.isfile(dot_git):
        return "there is no .git"
    with open(dot_git, "rb") as handle:
        data = handle.read(4097)
    match = re.match(rb"gitdir: ([^\r\n]+)\r?\n?\Z", data)
    if len(data) > 4096 or not match:
        return 'the file .git is not one line "gitdir: <path>"'
    named = os.fsdecode(match.group(1))
    target = os.path.join(root, named)  # a relative path is from the folder of the .git file
    if not os.path.isdir(target):
        return "the file .git names %s, which is not a directory" % json.dumps(named)
    if os.path.isfile(os.path.join(target, "HEAD")) and (os.path.isfile(os.path.join(target, "commondir"))
                                                         or os.path.isdir(os.path.join(target, "objects"))):
        return None
    return "the file .git names %s, which holds no HEAD and commondir or objects/" % json.dumps(named)


def git_directory(root):
    """The directory that holds the repo, for a root that git_root_problem passed: .git, or the one a .git file names."""
    dot_git = os.path.join(root, ".git")
    if os.path.isdir(dot_git):
        return dot_git
    with open(dot_git, "rb") as handle:
        named = re.match(rb"gitdir: ([^\r\n]+)", handle.read(4097)).group(1)
    return os.path.join(root, os.fsdecode(named))


def names_remote(root):
    """Whether the repo's git config names a remote: a line [remote "..."] in the config of its common directory,
    which a worktree names in commondir. The file is read, git is not run, and an include in it is not followed."""
    directory = git_directory(root)
    common = os.path.join(directory, "commondir")
    if os.path.isfile(common):
        with open(common, "rb") as handle:
            directory = os.path.join(directory, os.fsdecode(handle.read().strip()))
    path = os.path.join(directory, "config")
    if not os.path.isfile(path):
        return False
    with open(path, "rb") as handle:
        return re.search(rb'(?im)^[ \t]*\[remote[ \t]+"', handle.read()) is not None


def git(*args):
    """Run git in the Ratchet checkout, and only there. Returns (exit code, output)."""
    env = dict(os.environ, LC_ALL="C")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                 "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM"):
        env.pop(name, None)
    try:
        result = subprocess.run(["git", "-C", RATCHET, "-c", "core.fsmonitor=false"] + list(args), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    except OSError as error:
        raise InitError("cannot run git: %s" % error)
    return result.returncode, result.stdout.strip()


def ratchet_commit():
    """The commit of the Ratchet checkout, checked: the checkout is a git repo of its own, at that commit, clean."""
    code, top = git("rev-parse", "--show-toplevel")
    if code != 0 or os.path.realpath(top) != os.path.realpath(RATCHET):
        raise InitError("%s is not a git checkout of its own, so there is no commit to pin. Fetch Ratchet with git clone, "
                        "as README.md says" % RATCHET)
    code, commit = git("rev-parse", "--verify", "HEAD^{commit}")
    problem = commit_problem(commit) if code == 0 else "git rev-parse HEAD failed"
    if problem:
        raise InitError("cannot read the commit of %s: %s" % (RATCHET, problem))
    code, changes = git("status", "--porcelain", "--untracked-files=no")
    if code != 0:
        raise InitError("cannot read the state of %s with git status" % RATCHET)
    if changes:
        raise InitError("%s has changes that are not committed, so commit %s does not hold the files init.py would copy. "
                        "Fetch Ratchet again" % (RATCHET, commit))
    return commit


def template(name):
    text = registry.read(os.path.join(RATCHET, "templates", name))
    if text is None:
        raise InitError("templates/%s is missing from %s" % (name, RATCHET))
    return text


def team_parts(text, solo):
    """text without the lines that mark the parts for a team, the control room and the skills, and with solo without
    those parts too. Each mark is a line of its own, they stand in pairs, one pair at least, and none is inside another."""
    kept, inside, pairs = [], False, 0
    for line in text.splitlines(True):
        if line == TEAM[0] and not inside:
            inside = True
        elif line == TEAM[1] and inside:
            inside, pairs = False, pairs + 1
        elif line in TEAM or "team -->" in line:
            raise InitError("templates/AGENTS.md: the lines %s and %s must stand in pairs, each on a line of its own"
                            % tuple(json.dumps(mark.rstrip("\n")) for mark in TEAM))
        elif not (solo and inside):
            kept.append(line)
    if inside or not pairs:
        raise InitError("templates/AGENTS.md: the lines %s and %s must stand in pairs, one pair at least"
                        % tuple(json.dumps(mark.rstrip("\n")) for mark in TEAM))
    return "".join(kept)


def agents_text(name, solo):
    first, rest = template("AGENTS.md").split("\n", 1)
    if first != AGENTS_TITLE % "<project>":
        raise InitError("templates/AGENTS.md does not start with %r" % (AGENTS_TITLE % "<project>"))
    return AGENTS_TITLE % name + "\n" + team_parts(rest, solo)


def register_text(name, ratchet):
    try:
        register = registry.strict_loads(template("register.json"))
    except (ValueError, RecursionError) as error:
        raise InitError("templates/register.json is not a valid data file: %s" % error)
    if not isinstance(register, dict) or register.get("project") != "<project>":
        raise InitError('templates/register.json does not hold "project": "<project>"')
    register["project"] = name
    problems, _ = check_register.check(register, ratchet)
    if problems:
        raise InitError("the register from the template does not pass: %s" % "; ".join(problems))
    return json.dumps(register, indent=2, ensure_ascii=True) + "\n"


def workflow_text_from(text, commit):
    if text.count(PLACEHOLDER) != 1:
        raise InitError("templates/ratchet-checks.yml must hold %r once, found it %d times" % (PLACEHOLDER, text.count(PLACEHOLDER)))
    for job in JOBS:
        found = text.count("\n  %s:\n" % job)
        if found != 1:
            raise InitError("templates/ratchet-checks.yml must hold the job %s once, found it %d times" % (job, found))
    return text.replace(PLACEHOLDER, commit)


def workflow_text(commit):
    return workflow_text_from(template("ratchet-checks.yml"), commit)


def existing(path):
    """(the state of path, its text with CRLF read as LF or None): missing, a plain file, or something else."""
    if not os.path.lexists(path):
        return "missing", None
    if os.path.islink(path) or not os.path.isfile(path):
        return "other", None
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        return "file", data.decode("utf-8", errors="strict").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return "file", None


def register_md_text(register_state, register_text_now, ratchet):
    """REGISTER.md as the register.json that stands after the run generates it, or (None, the reason)."""
    if register_state == "other" or register_text_now is None:
        return None, "register.json is not a plain file in UTF-8"
    try:
        register = registry.parse_json(register_text_now.encode("utf-8"))
    except registry.RegistryError as error:
        return None, "register.json: %s" % error
    problems, _ = check_register.check(register, ratchet)
    if problems:
        return None, "register.json does not pass check_register.py: %s" % "; ".join(problems)
    return check_register.render(register), None


def ignores_ratchet(data):
    """Whether .gitignore, as bytes, ignores .ratchet for sure: the last line that mentions .ratchet is exactly
    .ratchet/ or /.ratchet/, and no negation comes after it. Anything else gets the line. A leading space is part
    of the pattern in gitignore, so it is not stripped, and neither is a trailing one."""
    lines = [line[:-1] if line.endswith(b"\r") else line for line in data.split(b"\n")]
    mentions = [number for number, line in enumerate(lines) if b".ratchet" in line]
    if not mentions or lines[mentions[-1]] not in IGNORED:
        return False
    return not any(line.startswith(b"!") for line in lines[mentions[-1] + 1:])


def gitignore_plan(path):
    """(action, what to write or None, what to say) for the line /.ratchet/ in .gitignore. What to write is the
    bytes of a new file, or, for "add", (the bytes read now, the bytes to put in their place)."""
    if not os.path.lexists(path):
        return "write", (IGNORE + "\n").encode("ascii"), ""
    if os.path.islink(path) or not os.path.isfile(path):
        return "skip", None, "it exists and is not a plain file. Add the line %s to it by hand" % IGNORE
    with open(path, "rb") as handle:
        data = handle.read()
    if ignores_ratchet(data):
        return "unchanged", None, ""
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    after = data + (newline if data and not data.endswith(b"\n") else b"") + IGNORE.encode("ascii") + newline
    return "add", (data, after), ""


def temporary(path):
    """A new file beside path, opened for writing, with a name of its own. (descriptor, its path)."""
    directory, base = os.path.split(path)
    for _ in range(100):
        candidate = os.path.join(directory, ".%s.init-%s.tmp" % (base, secrets.token_hex(6)))
        try:
            return os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666), candidate
        except FileExistsError:
            continue
    raise OSError(errno.EEXIST, "no free name for a temporary file", path)


def write_new(path, data):
    """Write data to path, which must not exist, in full or not at all. False if path appeared meanwhile."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    descriptor, part = temporary(path)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(part, path)
        except FileExistsError:
            return False
        except OSError as error:
            # No hard link, so no way here to put a whole file in place without the risk of overwriting one.
            # Writing it directly could leave it half written, and a second run would then skip it.
            raise OSError(error.errno, "it cannot be linked into place (%s), so it was not written, rather than "
                                       "written directly" % (error.strerror or error), path)
        return True
    finally:
        if os.path.lexists(part):
            os.unlink(part)


def add_line(path, before, after):
    """Put after in place of path in one step, keeping its mode, if path still holds before. For .gitignore, which
    only gains a line. Changed, and path left as it is, when it no longer holds what was read."""
    mode = os.stat(path).st_mode & 0o7777
    descriptor, part = temporary(path)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(part, mode)
        # Read again just before the file is replaced, so that an edit made since the plan is not lost.
        if os.path.islink(path) or not os.path.isfile(path):
            raise Changed("it is no longer a plain file")
        with open(path, "rb") as handle:
            if handle.read() != before:
                raise Changed("it is not what init.py read")
        os.replace(part, path)
    finally:
        if os.path.lexists(part):
            os.unlink(part)


def main(argv=None, out=None):
    out = out or sys.stdout
    parser = argparse.ArgumentParser(description="Start a project on Ratchet: write AGENTS.md, register.json, REGISTER.md, "
                                                 "the workflow and .gitignore, never overwriting a file.")
    parser.add_argument("--check", action="store_true", help="say what would be written and what is skipped, write nothing")
    parser.add_argument("--name", help="the project's name (default: the name of the current folder)")
    parser.add_argument("--solo", action="store_true", help="one agent and no control room: leave the control room's line "
                                                            "and the skills out of AGENTS.md")
    args = parser.parse_args(argv)

    def say(text=""):
        out.write(text + "\n")

    root = os.getcwd()
    try:
        if os.path.realpath(root) == os.path.realpath(RATCHET):
            raise InitError("this is Ratchet's own checkout. Run init.py from the root of your own repo, with Ratchet in .ratchet")
        problem = git_root_problem(root)
        if problem:
            raise InitError("%s is not the root of a git repo: %s. Run init.py from the root of your own repo"
                            % (root, problem))
        name = args.name if args.name is not None else os.path.basename(root)
        problem = name_problem(name)
        if problem:
            hint = "" if args.name is not None else ". It is the folder's name: give one with --name"
            raise InitError("%s cannot be the project name: %s%s" % (json.dumps(name), problem, hint))
        ratchet = registry.load(os.path.join(RATCHET, "ratchet.json"))
        commit = ratchet_commit()
        texts = [("AGENTS.md", agents_text(name, args.solo)), ("register.json", register_text(name, ratchet)),
                 (WORKFLOW, workflow_text(commit))]
    except (InitError, registry.RegistryError, OSError) as error:
        say("init: cannot run: %s" % error)
        say("init: nothing was written")
        return 2

    version = ratchet["version"]
    code, tags = git("tag", "--points-at", "HEAD")
    tag = "v" + version
    say("init: Ratchet %s from %s, at commit %s" % (version, RATCHET, commit))
    if code == 0 and tag in tags.split("\n"):
        say("init: that is the commit of the tag %s, and the workflow pins it" % tag)
    else:
        say("init: that is not the commit of the tag %s. The workflow pins it all the same, and fetches it from GitHub, "
            "so it must be a commit there. README.md fetches a release" % tag)
    say("init: project name %s" % json.dumps(name))
    say()

    # The plan, all of it worked out before anything is written.
    plan = []  # (action, name, bytes or None, note)
    states = {}
    for file, text in texts:
        state, current = existing(os.path.join(root, file))
        states[file] = (state, current, text)
        if state == "missing":
            plan.append(("write", file, text.encode("utf-8"), ""))
        elif current == text:
            plan.append(("unchanged", file, None, ""))
        elif state == "other":
            plan.append(("skip", file, None, "it exists and is not a plain file. It was left as it is"))
        else:
            plan.append(("skip", file, None, "it exists and differs from what init.py writes. It was left as it is: "
                                             "compare it with .ratchet/templates/%s by hand" % {
                                                 "AGENTS.md": "AGENTS.md", "register.json": "register.json",
                                                 WORKFLOW: "ratchet-checks.yml"}[file]))
    state, current, text = states["register.json"]
    standing = text if state == "missing" else current
    markdown, reason = register_md_text(state, standing, ratchet)
    state, current = existing(os.path.join(root, "REGISTER.md"))
    if markdown is None:
        plan.insert(2, ("skip", "REGISTER.md", None, "it cannot be generated: %s" % reason))
    elif state == "missing":
        plan.insert(2, ("write", "REGISTER.md", markdown.encode("utf-8"), ""))
    elif current == markdown:
        plan.insert(2, ("unchanged", "REGISTER.md", None, ""))
    else:
        plan.insert(2, ("skip", "REGISTER.md", None, "it exists and is not what register.json generates. It was left as "
                                                     "it is: generate it with check_register.py --write"))
    action, data, note = gitignore_plan(os.path.join(root, ".gitignore"))
    plan.append((action, ".gitignore", data, note))

    shown = {"write": "would write", "add": "would add"} if args.check else {}
    written = skipped = 0
    for action, file, data, note in plan:
        label = file.replace(os.sep, "/")
        if action == "add":
            label = "%s to .gitignore" % IGNORE
        if action in ("write", "add") and not args.check:
            path = os.path.join(root, file)
            try:
                if action == "write":
                    done = write_new(path, data)
                else:
                    add_line(path, *data)
                    done = True
            except Changed as error:
                say("init: .gitignore changed while init.py ran (%s), so %s was not added. It was left as it is: "
                    "run init.py again" % (error, IGNORE))
                say("init: %d file(s) were written before it" % written)
                return 2
            except OSError as error:
                say("init: cannot write %s: %s" % (label, error))
                say("init: %d file(s) were written before it. A second run writes the rest" % written)
                return 2
            if not done:
                action, note = "skip", "it appeared while init.py ran. It was left as it is"
        say(("%-11s %s" % (shown.get(action, action), label)) + (": " + note if note else ""))
        if action in ("write", "add"):
            written += 1
        elif action == "skip":
            skipped += 1
    left = "1 file left as it is" if skipped == 1 else "%d files left as they are" % skipped
    say()
    if args.check:
        say("init: --check. Nothing was written: %d file(s) would be written, %s" % (written, left))
    elif written:
        say("init: %d file(s) written, %s" % (written, left))
    else:
        say("init: Nothing changed" + (", " + left if skipped else ""))

    result = 1 if skipped else 0
    for line in notes(root, states, standing, args.check):
        say(line)
    say()
    if args.check:
        if markdown is not None:
            say("init: the register it would leave passes check_register.py (%s)" % check_register.check(
                registry.parse_json(standing.encode("utf-8")), ratchet)[1])
        else:
            say("init: the register it would leave does not pass check_register.py: %s" % reason)
            result = 1
        return result

    command = [sys.executable, "-E", "-s", os.path.join(RATCHET, "checks", "check_register.py"), "register.json",
               "--markdown", "REGISTER.md"]
    say("init: python3 %s register.json --markdown REGISTER.md" % os.path.relpath(command[3], root).replace(os.sep, "/"))
    check = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    for line in check.stdout.rstrip("\n").split("\n"):
        say("  " + line)
    if check.returncode != 0:
        say("init: the register check failed, with exit code %d" % check.returncode)
        return 1
    if result == 0:
        say("init: done. Fill in AGENTS.md, and commit AGENTS.md, register.json, REGISTER.md, %s and .gitignore"
            % WORKFLOW.replace(os.sep, "/"))
    return result


def notes(root, states, standing, check):
    """What is left to do after the run: the placeholders that AGENTS.md holds, the jobs to require, and the adopted
    rules that wait for a remote when the repo's git config names none."""
    lines = []
    state, current, text = states["AGENTS.md"]
    agents = text if state == "missing" else current
    left = check_register.placeholders(agents) if agents is not None else []
    if left:
        lines += ["", "init: AGENTS.md %s %d placeholder(s) of the template. Fill in or delete each: the workflow's "
                      "register check fails while one is left" % ("would hold" if check else "holds", len(left))]
        lines += ["  " + placeholder for placeholder in left]
    lines += ["", "init: in the protection of main, require the jobs %s of %s" % (" and ".join(JOBS), WORKFLOW.replace(os.sep, "/"))]
    try:
        remote = names_remote(root)
        adopted = [rule.get("key") for rule in registry.parse_json(standing.encode("utf-8"))["adopted"]]
    except (OSError, AttributeError, TypeError, KeyError, registry.RegistryError):
        return lines
    waiting = [key for key in WAIT_FOR_REMOTE if key in adopted]
    if not remote and waiting:
        lines += ["", "init: the repo's git config names no remote, so these adopted rules wait for one:"]
        lines += ["  %s: %s" % (key, WAIT_FOR_REMOTE[key]) for key in waiting]
    return lines


if __name__ == "__main__":
    sys.exit(main())
