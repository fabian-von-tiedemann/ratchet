#!/usr/bin/env python3
"""Start a project on Ratchet with one command, from the root of its repo.

    git clone --branch v<version> https://github.com/fabian-von-tiedemann/ratchet .ratchet
    python3 .ratchet/checks/init.py --check     # say what it would write and what it skips, write nothing
    python3 .ratchet/checks/init.py             # write it
    python3 .ratchet/checks/init.py --name "My project"
    python3 .ratchet/checks/init.py --solo           # one agent and no control room
    python3 .ratchet/checks/init.py --adopt ratchet.no-secrets   # adopt mode: write register.json with that row

It writes what README's "Start here" sets up:

- AGENTS.md, from templates/AGENTS.md, with the project's name in its title, and without the lines
  <!-- team --> and <!-- /team -->. With --solo it also leaves out what stands between them: the control room's
  line and the skills
- register.json, from templates/register.json, with the project's name
- REGISTER.md, generated from the register.json that stands after the run, as check_register.py --print-markdown
  prints it
- .github/workflows/ratchet.yml, from templates/ratchet-checks.yml, with the commit of the Ratchet checkout it
  runs from, read with git rev-parse HEAD, as the pin. It has the job ratchet, whose register check also fails
  while AGENTS.md holds a placeholder of the template, and the job project-checks, the place for the project's
  own checks
- the line /.ratchet/ at the end of .gitignore, unless the last line there that mentions .ratchet is exactly
  .ratchet/ or /.ratchet/, with no negation after it

A repo that already has an instruction file of its own, a plain file at one of INSTRUCTION_FILES, such as AGENTS.md or
CLAUDE.md, is adopted, in adopt mode (step 9b of D-2026-11-22-second-redraw), unless .github/workflows/ratchet.yml
exists, which init.py writes first in a start, or a register.json names an instruction file in instructions. It says
so, and suggests running inventory.py first. In adopt mode it never writes or changes the instruction file, and does
not read it to choose adopt mode or the rules and rows it prints. It reads AGENTS.md once, as bytes, only to say when it
is, below its title, the file init.py writes: a start before 0.11 wrote AGENTS.md first, and one that stopped before
the workflow is taken for adopt mode now. The register check at the end reads the files that rows by reference name, for
their marker lines. Its first run writes nothing: no register.json until the project names, with --adopt, once for
each, the rules whose marker line it has put in its file. Then it writes register.json alone, the template's with a row
by reference for each rule named and no other, and only when that register passes check_register.py: a copied
ratchet.register-on-top, which an earlier adopt mode wrote as the floor, says that the register lists every rule in
force and takes precedence, which is false while the project's own instruction file governs (finding from a real
adoption). No REGISTER.md, which it does not read either, no workflow and no line in .gitignore. It prints, for each
rule to start with that the register does not adopt yet, the rule, its marker line and its row by reference, pointing
at the first instruction file, each line as it is pasted, from column zero, and says where to put the marker, that a
marker counts only in a file in UTF-8 with LF line endings, and how to record a rule as built with a where that names
the enforcement point, which it does not assert. It prints how to copy checks/run_pinned.py from the pinned commit, and
the one step that runs it, to add to a job that the protection of main already requires, with permissions: contents:
read for the job and persist-credentials: false for its checkout, and the same command as a line for a local check
script that CI runs: it adds no workflow and no required job, so no admin is needed. Its check at the end, and the
verdict of --check, is check_register.py register.json, without REGISTER.md.

The name is the one --name gives, or else the repo's name in the url of its git remote, origin first, read from the
git config as a file, when that is a name, or else the folder's name, and the run says which. It is ASCII letters and
digits, in words joined by one space, "-", "." or "_", at most 100 characters.

It never overwrites a file. A file that exists with the content it would write is unchanged. A file that exists
with other content, or that is not a plain file, is skipped, named, and left as it is. That is reported, not a
failure: the run goes on and writes the rest (step 5 of D-2026-11-22-second-redraw). The one
file it changes is .gitignore, and only by adding its line at the end, in one step, and only if .gitignore still
holds what it read: when it changed meanwhile, init.py stops and leaves it as it is. With --check it writes
nothing and says the same. A second run says that nothing changed. Then it names what is left to do: each
placeholder of the template that AGENTS.md holds, from the fixed list in check_register.py, the jobs to require in
the protection of main, and, when the repo's git config names no remote, the adopted rules that wait for one. At
the end it runs check_register.py on register.json and REGISTER.md and shows the result.

The root is the directory it runs in, as the shell gives it in PWD when that is the same directory, taken as given
and never resolved. The paths it prints are as the user typed them: the Ratchet checkout, when it stands under the
root, is named from the root, such as .ratchet, and never by the path the system resolves a link above the root to. It refuses to run when the path to the root passes through a symbolic link, below the enclosing
git root (registry.root_link), and each function that writes refuses a link on any part of the path from the root
to the file it writes (registry.guard_path), so nothing is written through a link (round 3 of #100).

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

Exit code 0: the plan was carried out, or with --check can be, and the register passes, files skipped or not, or, in
adopt mode with no register.json and no --adopt, there is no register to check yet. 1: the
register does not pass, or with --check would not, and in adopt mode the register.json --adopt names is then not
written: register.json does not pass check_register.py, REGISTER.md is not
a plain file or not what register.json generates, or the instruction file that register.json names in instructions
is not a plain file holding the block it generates. --check reaches that verdict with check_register.generated_problems,
the function of the check at the end of a real run, given the bytes it would write (review of d86ff3e). 2: it could not run, and wrote nothing, or it stopped at a file it could not write or at a .gitignore that
changed, and says how many files it wrote before.
Standard library only. Run on Python 3.9 and 3.12.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True
# Its own directory on the path, named explicitly, so that python3 -I, which leaves the script's directory out of
# sys.path, still finds the modules beside it.
import os  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import errno
import json
import os
import re
import secrets
import subprocess

import check_register
import registry
import run_pinned

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
# The instruction files of a project's own that switch init.py to adopt mode, in the order the first is named, each as
# a path from the root: the ones a harness loads at the root of a repo (checks/inventory.py has the full list).
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md", ".claude/CLAUDE.md")
# Where the step that adopt mode prints fetches Ratchet from: the repository the workflow template fetches, and the one
# checks/run_pinned.py clones and fetches from.
REPOSITORY = "https://github.com/fabian-von-tiedemann/ratchet"
# The rule that a register adopted by reference, with the project's own instruction file canonical, does not meet.
REGISTER_ON_TOP = "ratchet.register-on-top"
# Where adopt mode says to copy checks/run_pinned.py to, in the project's repo, from the pinned commit.
RUNNER = ".github/ratchet/run_pinned.py"
# The rules of the starter register whose check cannot run before the repo has a remote, and why.
WAIT_FOR_REMOTE = {
    "ratchet.register-on-top": "its check runs in CI on the host",
    "ratchet.protected-main": "the protection of main is a setting of the host",
    "ratchet.owner-paths": "the owner's required review on the owner's paths is a setting of the host",
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


def git_config(root):
    """The bytes of the repo's git config, in its common directory, which a worktree names in commondir, or b"". The file
    is read, git is not run, and an include in it is not followed."""
    directory = git_directory(root)
    common = os.path.join(directory, "commondir")
    if os.path.isfile(common):
        with open(common, "rb") as handle:
            directory = os.path.join(directory, os.fsdecode(handle.read().strip()))
    path = os.path.join(directory, "config")
    if not os.path.isfile(path):
        return b""
    with open(path, "rb") as handle:
        return handle.read()


def names_remote(root):
    """Whether the repo's git config names a remote: a line [remote "..."] in git_config. A worktree's own
    config.worktree is not read: with extensions.worktreeConfig set, a remote named only there is one git reports and
    this does not see, so the rules are named as waiting all the same."""
    return re.search(rb'(?im)^[ \t]*\[remote[ \t]+"', git_config(root)) is not None


def remote_repo(root):
    """(the remote, the repo's name in its url) for the remote origin, or else the first remote with a url, in
    git_config, or None. The name is the last part of the url's path, without ".git": a worktree's folder, such as one a
    tool names at random, is not the project's name, and the remote's url names the repo (finding from a real adoption)."""
    remotes, current = [], None
    for raw in git_config(root).split(b"\n"):
        line = raw.strip()
        section = re.match(rb'\[remote[ \t]+"([^"\\]*)"\]\Z', line)
        if section:
            current = section.group(1).decode("utf-8", "replace")
            continue
        if line.startswith(b"["):
            current = None
            continue
        url = re.match(rb'url[ \t]*=[ \t]*"?([^"]*?)"?\Z', line, re.I)
        if current is not None and url and current not in [remote for remote, _ in remotes]:
            remotes.append((current, url.group(1).decode("utf-8", "replace")))
    remotes.sort(key=lambda remote: remote[0] != "origin")
    for remote, url in remotes:
        name = re.split(r"[/:]", url.rstrip("/"))[-1]
        name = name[:-4] if name.endswith(".git") else name
        if name:
            return remote, name
    return None


def project_name(root, given):
    """(the project's name, where it comes from): given with --name; else the repo's name in the url of its git remote,
    when that is a name; else the folder's name."""
    if given is not None:
        return given, "given with --name"
    try:
        found = remote_repo(root)
    except OSError:
        found = None
    folder = os.path.basename(root)
    if found and not name_problem(found[1]):
        return found[1], "the repo's name in the url of the git remote %s" % found[0]
    if found:
        return folder, "the folder's name, since the repo's name in the url of the git remote %s, %s, cannot be one: %s" % (
            found[0], json.dumps(found[1]), name_problem(found[1]))
    return folder, "the folder's name, since the repo's git config names no remote with a url"


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


def typed(path):
    """path as the user typed it. A path under the root, or under the directory the system gives for it, is named from
    the root, so that a link above the root, such as /var to /private/var on macOS, is not resolved in what is printed.
    Any other path is shown as it is."""
    for base in (here(), os.getcwd()):
        if os.path.commonpath([base, path]) == base:
            return os.path.relpath(path, base).replace(os.sep, "/")
    return path


def ratchet_commit():
    """The commit of the Ratchet checkout, checked: the checkout is a git repo of its own, at that commit, clean."""
    code, top = git("rev-parse", "--show-toplevel")
    if code != 0 or os.path.realpath(top) != os.path.realpath(RATCHET):
        raise InitError("%s is not a git checkout of its own, so there is no commit to pin. Fetch Ratchet with git clone, "
                        "as README.md says" % typed(RATCHET))
    code, commit = git("rev-parse", "--verify", "HEAD^{commit}")
    problem = commit_problem(commit) if code == 0 else "git rev-parse HEAD failed"
    if problem:
        raise InitError("cannot read the commit of %s: %s" % (typed(RATCHET), problem))
    code, changes = git("status", "--porcelain", "--untracked-files=no")
    if code != 0:
        raise InitError("cannot read the state of %s with git status" % typed(RATCHET))
    if changes:
        raise InitError("%s has changes that are not committed, so commit %s does not hold the files init.py would copy. "
                        "Fetch Ratchet again" % (typed(RATCHET), commit))
    return commit


def template(name):
    text = registry.read(os.path.join(RATCHET, "templates", name))
    if text is None:
        raise InitError("templates/%s is missing from %s" % (name, typed(RATCHET)))
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


def adopt_register_text(name, ratchet, keys, stands_in):
    """register.json for adopt mode: the template's, with the project's name, and in adopted only the rows by reference
    for keys, the rules the project chose with --adopt, each pointing at stands_in. No copied row: a copied
    ratchet.register-on-top would say that the register lists every rule in force and takes precedence, which is not
    true of a project whose own instruction file is canonical (finding from a real adoption). Checked here in memory, on
    its form; the markers it needs in stands_in are checked before it is written."""
    by_key = registry.rules_by_key(ratchet)
    for key in keys:
        if key not in by_key:
            raise InitError("--adopt %s: there is no rule %s in Ratchet %s" % (key, key, ratchet["version"]))
    if len(set(keys)) != len(keys):
        raise InitError("--adopt names a rule twice")
    register = json.loads(register_text(name, ratchet))
    register["adopted"] = [reference_row(key, stands_in, ratchet) for key in keys]
    problems, _ = check_register.check(register, ratchet)
    if problems:
        raise InitError("the register for adopt mode does not pass: %s" % "; ".join(problems))
    return json.dumps(register, indent=2, ensure_ascii=True) + "\n"


def own_instructions(root):
    """The instruction files of the project's own that stand under root, from INSTRUCTION_FILES and in that order: each a
    plain file with no link on its path from root. Only whether each is there is looked at, never what it holds, so adopt
    mode is chosen without reading one."""
    found = []
    for name in INSTRUCTION_FILES:
        path = os.path.join(root, *name.split("/"))
        try:
            registry.guard_path(root, path)
        except (registry.RegistryError, OSError):
            continue
        if os.path.isfile(path) and not os.path.islink(path):
            found.append(name)
    return found


def names_instructions(root):
    """Whether a register.json at root names an instruction file in instructions, so that the project has chosen the
    generated block, the copied mode, and is not adopted by reference."""
    state, text = existing(os.path.join(root, "register.json"))
    try:
        register = registry.parse_json(text.encode("utf-8")) if state == "file" and text is not None else None
    except registry.RegistryError:
        return False
    return isinstance(register, dict) and check_register.INSTRUCTIONS in register


def adopt_mode(root):
    """The instruction files of the project's own when init.py runs in adopt mode, else nothing. Adopt mode is for a repo
    that already has an instruction file (step 9b of D-2026-11-22-second-redraw). A project that init.py started has
    its workflow, which init.py writes first, and a register that names an instruction file has chosen the block: either
    keeps the run as it was."""
    if os.path.lexists(os.path.join(root, WORKFLOW)) or names_instructions(root):
        return []
    return own_instructions(root)


def written_by_init(root, name):
    """Whether the instruction file name is, below its title line, byte for byte the AGENTS.md that init.py writes, with
    or without --solo: what a start before 0.11, which wrote AGENTS.md first, left when it stopped before the workflow.
    The one read of an instruction file in adopt mode, as bytes, and only for this note: it chooses nothing else."""
    if name != "AGENTS.md":
        return False
    bodies = [agents_text("x", solo).split("\n", 1)[1].encode("utf-8") for solo in (False, True)]
    title = (AGENTS_TITLE % "").encode("utf-8")
    try:
        with open(os.path.join(root, name), "rb") as handle:
            data = handle.read(len(title) + NAME_LENGTH + max(len(body) for body in bodies) + 2)
    except OSError:
        return False
    first, _, rest = data.partition(b"\n")
    return first.startswith(title) and rest in bodies


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


def write_new(root, path, data):
    """Write data to path, which must not exist, in full or not at all. False if path appeared meanwhile. Refused, with
    RegistryError, when a part of the path from root down to path is a symbolic link."""
    registry.guard_path(root, path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    registry.guard_path(root, path)
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


def add_line(root, path, before, after):
    """Put after in place of path in one step, keeping its mode, if path still holds before. For .gitignore, which
    only gains a line. Changed, and path left as it is, when it no longer holds what was read. Refused, with
    RegistryError, when a part of the path from root down to path is a symbolic link."""
    registry.guard_path(root, path)
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


def here():
    """The directory init.py runs in, as the shell gives it in PWD when that names the same directory, else as the system
    gives it. Never resolved, so that a path through a link is seen and refused."""
    physical = os.getcwd()
    given = os.environ.get("PWD")
    if given and os.path.isabs(given):
        try:
            if os.path.samefile(given, physical):
                return os.path.abspath(given)
        except OSError:
            pass
    return physical


def main(argv=None, out=None):
    out = out or sys.stdout
    parser = argparse.ArgumentParser(description="Start a project on Ratchet: write AGENTS.md, register.json, REGISTER.md, "
                                                 "the workflow and .gitignore, never overwriting a file.")
    parser.add_argument("--check", action="store_true", help="say what would be written and what is skipped, write nothing")
    parser.add_argument("--name", help="the project's name (default: the name of the current folder)")
    parser.add_argument("--solo", action="store_true", help="one agent and no control room: leave the control room's line "
                                                            "and the skills out of AGENTS.md")
    parser.add_argument("--adopt", action="append", default=[], metavar="KEY",
                        help="adopt mode only: write register.json with a row by reference for this rule, pointing at the "
                             "project's instruction file, which must hold the rule's marker line. May be given more than once")
    args = parser.parse_args(argv)

    def say(text=""):
        out.write(text + "\n")

    root = here()
    try:
        problem = registry.link_problem(root)
        if problem:
            raise InitError(problem)
        if os.path.realpath(root) == os.path.realpath(RATCHET):
            raise InitError("this is Ratchet's own checkout. Run init.py from the root of your own repo, with Ratchet in .ratchet")
        problem = git_root_problem(root)
        if problem:
            raise InitError("%s is not the root of a git repo: %s. Run init.py from the root of your own repo"
                            % (root, problem))
        name, origin = project_name(root, args.name)
        problem = name_problem(name)
        if problem:
            hint = "" if args.name is not None else ". It is %s: give one with --name" % origin
            raise InitError("%s cannot be the project name: %s%s" % (json.dumps(name), problem, hint))
        ratchet = registry.load(os.path.join(RATCHET, "ratchet.json"))
        commit = ratchet_commit()
        adopting = adopt_mode(root)
        if args.adopt and not adopting:
            raise InitError("--adopt is for adopt mode, a repo with an instruction file of its own, and this run is a start")
        if adopting:
            # No register.json until the project names the rules its file states: an empty one does not pass, and a
            # copied row of its own would claim what is not true (finding from a real adoption).
            texts = [("register.json", adopt_register_text(name, ratchet, args.adopt, adopting[0]))] if args.adopt else []
            runner = runner_blob(commit)
        else:
            # The workflow first: a start that stops halfway has it, so the next run is not taken for adopt mode.
            texts = [(WORKFLOW, workflow_text(commit)), ("AGENTS.md", agents_text(name, args.solo)),
                     ("register.json", register_text(name, ratchet))]
    except (InitError, registry.RegistryError, OSError) as error:
        say("init: cannot run: %s" % error)
        say("init: nothing was written")
        return 2

    version = ratchet["version"]
    code, tags = git("tag", "--points-at", "HEAD")
    tag = "v" + version
    pins = "the step it prints" if adopting else "the workflow"
    say("init: Ratchet %s from %s, at commit %s" % (version, typed(RATCHET), commit))
    if code == 0 and tag in tags.split("\n"):
        say("init: that is the commit of the tag %s, and %s pins it" % (tag, pins))
    else:
        say("init: that is not the commit of the tag %s. %s pins it all the same, and fetches it from GitHub, "
            "so it must be a commit there. README.md fetches a release" % (tag, pins[0].upper() + pins[1:]))
    say("init: project name %s, %s" % (json.dumps(name), origin))
    if adopting:
        say("init: adopt mode: %s is the project's own instruction file, so init.py writes only register.json, never %s, "
            "and adds no workflow" % (adopting[0], adopting[0]))
        say("init: to see the agent layer as it stands first, run the inventory, which writes nothing: python3 %s"
            % typed(os.path.join(RATCHET, "checks", "inventory.py")))
        if args.solo:
            say("init: --solo changes nothing in adopt mode, which writes no instruction file")
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
        elif adopting:
            plan.append(("skip", file, None, "it exists and differs from what init.py writes. It was left as it is, and "
                                             "is checked as it stands"))
        else:
            plan.append(("skip", file, None, "it exists and differs from what init.py writes. It was left as it is: "
                                             "compare it with %s/templates/%s by hand" % (typed(RATCHET), {
                                                 "AGENTS.md": "AGENTS.md", "register.json": "register.json",
                                                 WORKFLOW: "ratchet-checks.yml"}[file])))
    if "register.json" not in states:
        # Adopt mode with no --adopt: register.json is not written, and one of the project's own is checked as it stands.
        state, current = existing(os.path.join(root, "register.json"))
        states["register.json"] = (state, current, None)
        if state == "missing":
            plan.append(("not yet", "register.json", None, "it is written once you name with --adopt the rules your file "
                                                           "states: see below"))
        elif state == "other":
            plan.append(("skip", "register.json", None, "it exists and is not a plain file. It was left as it is"))
        else:
            plan.append(("skip", "register.json", None, "it is the project's own. It was left as it is, and is checked "
                                                        "as it stands"))
    register_state, current, register_planned = states["register.json"]
    standing = register_planned if register_state == "missing" else current
    markdown, reason = (register_md_text(register_state, standing, ratchet) if standing is not None or register_state != "missing"
                        else (None, None))
    # Adopt mode writes register.json alone: no REGISTER.md, which a register with rows by reference may leave out and
    # its check is not given, so it is not read either, and no line in .gitignore (review of 58ca014).
    markdown_state, current = ("not read", None) if adopting else existing(os.path.join(root, "REGISTER.md"))
    if adopting:
        pass
    elif markdown is None:
        plan.append(("skip", "REGISTER.md", None, "it cannot be generated: %s" % reason))
    elif markdown_state == "missing":
        plan.append(("write", "REGISTER.md", markdown.encode("utf-8"), ""))
    elif current == markdown:
        plan.append(("unchanged", "REGISTER.md", None, ""))
    elif markdown_state == "other":
        plan.append(("skip", "REGISTER.md", None, "it exists and is not a plain file. It was left as it is"))
    else:
        plan.append(("skip", "REGISTER.md", None, "it exists and is not what register.json generates. It was left as "
                                                  "it is: print it with check_register.py --print-markdown"))
    if not adopting:
        action, data, note = gitignore_plan(os.path.join(root, ".gitignore"))
        plan.append((action, ".gitignore", data, note))

    # Every file it would write or change, checked for a link on its path while it plans, as a real run checks it when it
    # writes: so --check never says "would write" for a file a real run refuses, and a real run never writes some files
    # before it stops at another (review of ef5cbaa).
    for action, file, data, note in plan:
        if action in ("write", "add"):
            try:
                registry.guard_path(root, os.path.join(root, file))
            except (registry.RegistryError, OSError) as error:
                say("init: cannot run: %s" % error)
                say("init: nothing was written")
                return 2

    # Adopt mode writes register.json only when it passes as it would stand: its rows by reference need their markers,
    # which only the project puts in its own file, so a register that does not pass is never left behind.
    refused = []
    if adopting and any(action == "write" for action, file, data, note in plan):
        refused = verdict(plan, markdown, reason, markdown_state, standing, None)
        if refused:
            plan = [(("skip", file, None, "the register would not pass check_register.py, so it is not written: see below")
                     if action == "write" else (action, file, data, note)) for action, file, data, note in plan]

    shown = {"write": "would write", "add": "would add"} if args.check else {}
    written = skipped = 0
    changed = []  # the files written or changed, as they are named to commit
    for action, file, data, note in plan:
        label = file.replace(os.sep, "/")
        if action == "add":
            label = "%s to .gitignore" % IGNORE
        if action in ("write", "add") and not args.check:
            path = os.path.join(root, file)
            try:
                if action == "write":
                    done = write_new(root, path, data)
                else:
                    add_line(root, path, *data)
                    done = True
            except Changed as error:
                say("init: .gitignore changed while init.py ran (%s), so %s was not added. It was left as it is: "
                    "run init.py again" % (error, IGNORE))
                say("init: %d file(s) were written before it" % written)
                return 2
            except (OSError, registry.RegistryError) as error:
                say("init: cannot write %s: %s" % (label, error))
                say("init: %d file(s) were written before it. A second run writes the rest" % written)
                return 2
            if not done:
                action, note = "skip", "it appeared while init.py ran. It was left as it is"
        say(("%-11s %s" % (shown.get(action, action), label)) + (": " + note if note else ""))
        if action in ("write", "add"):
            written += 1
            changed.append(file.replace(os.sep, "/"))
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

    # A file skipped is reported, not a failure: only the register decides (step 5 of D-2026-11-22-second-redraw).
    result = 0
    lines = (adopt_notes(root, adopting, standing, ratchet, commit, register_state == "missing", runner) if adopting
             else notes(root, states, standing, args.check))
    for line in lines + waiting(root, standing):
        say(line)
    say()
    if refused:
        say("init: register.json %s not written: the register would not pass check_register.py:"
            % ("would be" if args.check else "was"))
        for problem in refused:
            say("  " + problem.replace("\n", "\n  "))
        return 1
    if adopting and standing is None and register_state == "missing":
        say("init: there is no register.json yet, so there is no register to check. Name the rules your file states "
            "with --adopt, as above")
        return 0
    markdown_path = None if adopting else "REGISTER.md"
    if args.check:
        problems = verdict(plan, markdown, reason, markdown_state, standing, markdown_path)
        if not problems:
            say("init: the register it would leave passes check_register.py (%s)" % check_register.check(
                registry.parse_json(standing.encode("utf-8")), ratchet)[1])
        else:
            say("init: the register it would leave does not pass check_register.py:")
            for problem in problems:
                say("  " + problem.replace("\n", "\n  "))
            result = 1
        return result

    command = [sys.executable, "-E", "-s", os.path.join(RATCHET, "checks", "check_register.py"), "register.json"]
    if markdown_path:
        command += ["--markdown", markdown_path]
    say("init: python3 %s" % " ".join([typed(command[3])] + command[4:]))
    check = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    for line in check.stdout.rstrip("\n").split("\n"):
        say("  " + line)
    if check.returncode != 0:
        say("init: the register check failed, with exit code %d" % check.returncode)
        return 1
    say("init: done. %s" % closing(0 if adopting else skipped, changed))
    return 0


def verdict(plan, markdown, reason, markdown_state, standing, markdown_path="REGISTER.md"):
    """What --check says the register check at the end of a real run would find, as a list of problems. The check is the
    same function, check_register.generated_problems, given the bytes that the run would write (review of d86ff3e). In
    adopt mode the check at the end is not given REGISTER.md, so markdown_path is None, and markdown only says whether
    the register passes."""
    if markdown is None:
        return [reason]
    if markdown_path and markdown_state == "other":
        # The check at the end refuses a link at REGISTER.md, and reads a directory there as missing.
        return ["REGISTER.md: it is not a plain file"]
    planned = {file: data for action, file, data, note in plan if action == "write"}
    return check_register.generated_problems("register.json", registry.parse_json(standing.encode("utf-8")), markdown_path,
                                             planned)[0]


def closing(skipped, changed):
    """The last line of a run that passed, saying only what applies: compare what was left as it is, fill in AGENTS.md when
    it was written, and commit what was written or changed. Adopt mode gives no files skipped: the one file it writes,
    register.json, when it is left as it is, is the project's and is checked as it stands, with nothing to compare."""
    parts = []
    if skipped:
        parts.append("compare each file left as it is with what init.py would write, by hand")
    if "AGENTS.md" in changed:
        parts.append("fill in AGENTS.md")
    if changed:
        parts.append("commit " + (" and ".join(changed) if len(changed) < 3 else
                                  ", ".join(changed[:-1]) + " and " + changed[-1]))
    if not parts:
        return "Nothing to commit"
    text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + ", and " + parts[-1]
    return text[0].upper() + text[1:]


def notes(root, states, standing, check):
    """What is left to do after the run: the placeholders that AGENTS.md holds and the jobs to require."""
    lines = []
    state, current, text = states["AGENTS.md"]
    agents = text if state == "missing" else current
    left = check_register.placeholders(agents) if agents is not None else []
    if left:
        lines += ["", "init: AGENTS.md %s %d placeholder(s) of the template. Fill in or delete each: the workflow's "
                      "register check fails while one is left" % ("would hold" if check else "holds", len(left))]
        lines += ["  " + placeholder for placeholder in left]
    lines += ["", "init: in the protection of main, require the jobs %s of %s" % (" and ".join(JOBS), WORKFLOW.replace(os.sep, "/"))]
    return lines


def adopted_keys(standing):
    """The keys that the register which stands after the run adopts, or None when it cannot be read."""
    try:
        return [rule.get("key") for rule in registry.parse_json(standing.encode("utf-8"))["adopted"]]
    except (AttributeError, TypeError, KeyError, registry.RegistryError):
        return None


def waiting(root, standing):
    """The adopted rules that wait for a remote, when the repo's git config names none."""
    try:
        remote = names_remote(root)
    except OSError:
        return []
    adopted = adopted_keys(standing) or []
    keys = [key for key in WAIT_FOR_REMOTE if key in adopted]
    if remote or not keys:
        return []
    return (["", "init: the repo's git config names no remote, so these adopted rules wait for one:"]
            + ["  %s: %s" % (key, WAIT_FOR_REMOTE[key]) for key in keys])


def reference_row(key, stands_in, ratchet):
    """The row by reference for a rule of Ratchet, its project's wording in stands_in, as register.json takes it."""
    rule = registry.rules_by_key(ratchet)[key]
    row = {"key": key, check_register.STANDS_IN: stands_in, check_register.SHA: check_register.reference_sha256(rule)}
    if rule["enforcement"] == "enforced":
        row["status"] = "text only for now"
    return row


def runner_blob(commit):
    """(the object directory of the Ratchet checkout, as typed, the name of the blob of checks/run_pinned.py in the
    commit), read with run_pinned's reader: no git config, every object on the way from the commit hashed."""
    try:
        return typed(run_pinned.objects_of(RATCHET)), run_pinned.stored_blob(RATCHET, commit, run_pinned.SELF)
    except (run_pinned.Refused, OSError) as error:
        raise InitError("cannot read %s of commit %s from %s, every object hashed: %s"
                        % (run_pinned.SELF, commit, typed(RATCHET), error))


def adopt_notes(root, files, standing, ratchet, commit, missing, runner):
    """What adopt mode prints for the project to do: for each rule to start with that the register does not adopt yet,
    its marker line and its row by reference, pointing at the first instruction file; when register.json is missing, how
    --adopt writes it; how to record a rule as built; the copy of checks/run_pinned.py, which keeps the copy only when it
    is the blob runner names, and the one step that runs it after hashing it the same way, with
    the job's permissions and the checkout's credentials, or the line for a local check script; and the line for
    .gitignore when it does not ignore .ratchet. It reads no instruction file for any of it: only written_by_init reads
    AGENTS.md, for its own note (review of 58ca014)."""
    stands_in, version = files[0], ratchet["version"]
    adopted = adopted_keys(standing) or []
    keys = [key for key in ratchet["start"] if key not in adopted]
    by_key = registry.rules_by_key(ratchet)
    script = typed(os.path.join(RATCHET, "checks", "init.py"))
    lines = []
    if keys:
        lines += ["", "init: the rules to start with, as rows by reference, the weaker mode. For each rule that %s states in "
                      "the project's own words, put its marker line in %s, alone on a line, by that wording. Leave out a "
                      "rule the file does not state, or state it there first. The sha256 binds the row to the rule and its "
                      "ratchet in Ratchet %s, in %s: the check sees the marker, not the words"
                      % (stands_in, stands_in, version, typed(os.path.join(RATCHET, "ratchet.json"))),
                  "init: paste each line as it stands, from its first character. A marker line counts only in a file in "
                  "UTF-8 with LF line endings: the check fails on a file in another encoding, or on a marker line that "
                  "ends in CRLF"]
        if REGISTER_ON_TOP in keys:
            lines += ["init: %s fits only where the register, not %s, lists every rule in force and takes precedence: "
                      "leave it out while %s is the file that governs" % (REGISTER_ON_TOP, stands_in, stands_in)]
        for key in keys:
            lines += ["", "%s: %s" % (key, by_key[key]["rule"]),
                      check_register.MARKER % key,
                      json.dumps(reference_row(key, stands_in, ratchet))]
        if missing:
            lines += ["", "init: register.json is written once you name the rules whose marker you put in %s: run init.py "
                          "again with --adopt and the key of each, such as python3 %s --adopt %s. It writes register.json "
                          "with their rows, and only if the register passes. No row is copied: a copied "
                          "ratchet.register-on-top would say that the register lists every rule in force and takes "
                          "precedence, which is not so while %s is the project's own" % (
                              stands_in, script, ([key for key in keys if key != REGISTER_ON_TOP] or keys)[0], stands_in)]
        else:
            lines += ["", "init: paste the row of each rule whose marker you put in %s into adopted in register.json" % stands_in]
        if any("status" in reference_row(key, stands_in, ratchet) for key in keys):
            lines += ["", 'init: a row whose rule names a check is printed with "status": "text only for now": init.py cannot '
                          "see what the host enforces, and does not say. Where a check enforces the rule and can refuse, as "
                          "GLOSSARY.md defines built, record it in the row as \"status\": \"built\", with \"where\" naming "
                          "the enforcement point and when it was read back: for ratchet.protected-main, the ruleset or branch "
                          "protection of main at the host"]
    if files[1:]:
        lines += ["", "init: the project also has %s. A row may name one of them in stands_in in place of %s"
                  % (" and ".join(files[1:]), stands_in)]
    objects, blob = runner
    run = run_pinned.run_command(commit, blob, RUNNER)
    lines += ["", "init: the check runs from the pinned commit with checks/run_pinned.py. It reads .ratchet only as a store "
                  "of git objects, cloning it when it is missing, with no git config of the store's, the user's or the "
                  "system's, hashes every object it uses, and runs the check from a new directory, so an edit in .ratchet, "
                  "or a file planted beside the check, never runs. Copy it into the repo once, from the pinned commit, with "
                  "this command, run from the root: it keeps the copy only when its bytes are blob %s, the one the pinned "
                  "commit names. Commit the copy: a change to it is then a change in the repo, for review" % blob,
              "  " + run_pinned.copy_command(objects, commit, blob, RUNNER),
              "init: add this one step to a job that the protection of main already requires. No workflow and no "
              "required job are added, so no admin is needed. In GitHub Actions, after the checkout:",
              "  - name: Ratchet's register check",
              "    run: |",
              "      " + run,
              "init: and give that job these, if it does not have them:",
              "  permissions:",
              "    contents: read",
              "init:   the job's token can then only read the repo, so no step in the job can push or approve with it",
              "  - uses: actions/checkout@<the pin the job has>",
              "    with:",
              "      persist-credentials: false",
              "init:   the checkout then leaves no token in .git/config, where a later step could read it",
              "init: where the project's definition of done is a local check script that CI runs, put the command in it as "
              "a line of its own, in place of the step:",
              "  " + run,
              "init: to see which jobs main requires, export its ruleset or branch protection from the host and give it "
              "to the inventory, which marks each job required or not: python3 %s --ruleset <file>"
              % typed(os.path.join(RATCHET, "checks", "inventory.py"))]
    if os.path.lexists(os.path.join(root, "REGISTER.md")):
        lines += ["", "init: REGISTER.md is left as it is and not checked in adopt mode: the check the step runs, "
                      "check_register.py register.json, does not read it"]
    if written_by_init(root, stands_in):
        lines += ["", "init: AGENTS.md is, below its title, the file init.py writes. A start before Ratchet 0.11 wrote it "
                      "first, and one that stopped before the workflow is taken for adopt mode now. If that is how it "
                      "came, delete AGENTS.md and register.json and run init.py again for the start"]
    action = gitignore_plan(os.path.join(root, ".gitignore"))[0]
    if action != "unchanged":
        lines += ["", "init: .gitignore does not ignore .ratchet. Add the line %s to it, so the clone is not committed" % IGNORE]
    return lines


if __name__ == "__main__":
    sys.exit(main())
