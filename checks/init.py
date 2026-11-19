#!/usr/bin/env python3
"""Start a project on Ratchet with one command, from the root of its repo.

    git clone --branch v<version> https://github.com/fabian-von-tiedemann/ratchet .ratchet
    python3 .ratchet/checks/init.py --check     # say what it would write and what it skips, write nothing
    python3 .ratchet/checks/init.py             # write it
    python3 .ratchet/checks/init.py --name "My project"

It writes what README's "Start here" sets up:

- AGENTS.md, from templates/AGENTS.md, with the project's name in its title
- register.json, from templates/register.json, with the project's name
- REGISTER.md, generated from the register.json that stands after the run, as check_register.py --write does
- .github/workflows/ratchet.yml, from templates/ratchet-checks.yml, with the commit of the Ratchet checkout it
  runs from, read with git rev-parse HEAD, as the pin
- the line .ratchet/ in .gitignore, when no line there already keeps .ratchet out

The name is the folder's name unless --name gives one. It is ASCII letters and digits, in words joined by one
space, "-", "." or "_", at most 100 characters.

It never overwrites a file. A file that exists with the content it would write is unchanged. A file that exists
with other content, or that is not a plain file, is skipped, named, and left as it is, and the run exits 1. The one
file it changes is .gitignore, and only by adding its line at the end. With --check it writes nothing and says
the same. A second run says that nothing changed. At the end it runs check_register.py on register.json and
REGISTER.md and shows the result.

Each file is written in full to a temporary file beside it and then linked into place, so a file is either
missing or whole, and a file that appears meanwhile is not overwritten. A run that stops halfway leaves whole
files, and the next run writes the rest.

Threat model: a person or an agent runs it in their own repo. It guards against mistakes: overwriting work, a
pin that is not a full commit or not the commit of the files it copies, a result that is half written. It does
not guard against a hostile Ratchet checkout, whose code it is. It never runs code from the project's repo: it
runs git only in the Ratchet checkout, and the check at the end is Ratchet's own.

Exit code 0: everything is in place and the register passes. 1: a file was skipped, or the register does not
pass. 2: it could not run, and wrote nothing.
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
IGNORE = ".ratchet/"
IGNORED = {".ratchet", ".ratchet/", "/.ratchet", "/.ratchet/"}
NAME = re.compile(r"^[A-Za-z0-9]+(?:[-._ ][A-Za-z0-9]+)*\Z")
NAME_LENGTH = 100
COMMIT = re.compile(r"^[0-9a-f]{40}\Z")


class InitError(Exception):
    """init.py cannot run. Nothing has been written."""


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


def agents_text(name):
    first, rest = template("AGENTS.md").split("\n", 1)
    if first != AGENTS_TITLE % "<project>":
        raise InitError("templates/AGENTS.md does not start with %r" % (AGENTS_TITLE % "<project>"))
    return AGENTS_TITLE % name + "\n" + rest


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


def workflow_text(commit):
    text = template("ratchet-checks.yml")
    if text.count(PLACEHOLDER) != 1:
        raise InitError("templates/ratchet-checks.yml must hold %r once, found it %d times" % (PLACEHOLDER, text.count(PLACEHOLDER)))
    return text.replace(PLACEHOLDER, commit)


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


def gitignore_plan(path):
    """(action, the bytes to write or None, what to say) for the line .ratchet/ in .gitignore."""
    if not os.path.lexists(path):
        return "write", (IGNORE + "\n").encode("ascii"), ""
    if os.path.islink(path) or not os.path.isfile(path):
        return "skip", None, "it exists and is not a plain file. Add the line %s to it by hand" % IGNORE
    with open(path, "rb") as handle:
        data = handle.read()
    lines = [line.strip(b" \t\r") for line in data.split(b"\n")]
    if any(line.decode("utf-8", "replace") in IGNORED for line in lines):
        return "unchanged", None, ""
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    if data and not data.endswith(b"\n"):
        data += newline
    return "add", data + IGNORE.encode("ascii") + newline, ""


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
        except OSError:
            # A file system with no hard links. Create the file only if it does not exist, then fill it.
            try:
                with open(path, "xb") as handle:
                    handle.write(data)
            except FileExistsError:
                return False
        return True
    finally:
        if os.path.lexists(part):
            os.unlink(part)


def replace_file(path, data):
    """Write data in place of path in one step, keeping its mode. For .gitignore, which only gains a line."""
    mode = os.stat(path).st_mode & 0o7777
    descriptor, part = temporary(path)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(part, mode)
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
    args = parser.parse_args(argv)

    def say(text=""):
        out.write(text + "\n")

    root = os.getcwd()
    try:
        if os.path.realpath(root) == os.path.realpath(RATCHET):
            raise InitError("this is Ratchet's own checkout. Run init.py from the root of your own repo, with Ratchet in .ratchet")
        if not os.path.lexists(os.path.join(root, ".git")):
            raise InitError("%s is not the root of a git repo. Run init.py from the root of your own repo" % root)
        name = args.name if args.name is not None else os.path.basename(root)
        problem = name_problem(name)
        if problem:
            hint = "" if args.name is not None else ". It is the folder's name: give one with --name"
            raise InitError("%s cannot be the project name: %s%s" % (json.dumps(name), problem, hint))
        ratchet = registry.load(os.path.join(RATCHET, "ratchet.json"))
        commit = ratchet_commit()
        texts = [("AGENTS.md", agents_text(name)), ("register.json", register_text(name, ratchet)),
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
                    replace_file(path, data)
                    done = True
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
        say("init: done. Commit AGENTS.md, register.json, REGISTER.md, %s and .gitignore, and fill in the parts of "
            "AGENTS.md in angle brackets" % WORKFLOW.replace(os.sep, "/"))
    return result


if __name__ == "__main__":
    sys.exit(main())
