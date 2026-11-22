#!/usr/bin/env python3
"""Judge a pull request by the base branch's checks (the job `base` of .github/workflows/checks.yml).

    git show "HEAD^1:checks/from_base.py" > "$dir/from_base.py"
    python3 -I "$dir/from_base.py" --base-sha BASE --head-sha HEAD

Run in a checkout of the merge commit that GitHub makes for a pull request, with the full history and the tags.
The workflow takes this file from the base commit, HEAD^1, never from the pull request, and runs it from a
directory of its own. It then:

- checks that HEAD is a merge commit whose second parent is the pull request's head, --head-sha, and whose first
  parent is the base, --base-sha, or a later commit of the base branch. The first parent is the base it judges by.
- fails when the pull request changes .github/workflows/checks.yml, the job that runs this: the base branch cannot
  judge the job that judges it.
- makes the tree of the data: the merge commit, with the code of the checks taken from the base, and each file of
  code that only the pull request has left empty, so that a link to it leads somewhere. It runs the base's
  generate.py --check, check_register.py on register.json and REGISTER.md, and released_text.py there. So the base's
  scripts read the pull request's ratchet.json, register.json, generated text and changelog.
- makes the tree of the code: the base commit, with the pull request's code of the checks, but the base's tests and
  the base's runner of the suite. It runs the base's expected_tests.py there. So the base's tests and fixtures,
  under the base's runner, judge the pull request's checks, on the base's data.

The code of the checks is every file directly under checks/ whose name ends in .py, and every file in a directory
under checks/ other than fixtures/. The tests are checks/test_*.py, and the runner is checks/expected_tests.py and
checks/suite_runner.py. Everything else, checks/fixtures/ and checks/README.md among it, is data: generate.py writes
part of it.

When one of these fails, it prints why, and which paths the pull request changes that the base judges by. A pull
request that changes a check or the form of a data file on purpose is one the base branch cannot judge. The job
stays red, and the maintainer reads the change and merges it as an administrator (D-2026-11-16-code-owner). It
never passes such a pull request silently.

Standard library only. Run on Python 3.9 and 3.12.
"""

import sys

# No bytecode is written next to the checks, where a link could lead it out of the repo (round 3 of #100).
sys.dont_write_bytecode = True

import argparse
import os
import re
import shutil
import subprocess
import tempfile

WORKFLOW = ".github/workflows/checks.yml"
RUNNER = ("checks/expected_tests.py", "checks/suite_runner.py")
SHA = re.compile(r"^[0-9a-f]{40}\Z")
# What the base runs in each tree, from the top of the tree. Each is a command the job `own` also runs on the
# pull request's own checks.
DATA_COMMANDS = (
    ("checks/generate.py", "--check"),
    ("checks/check_register.py", "register.json", "--markdown", "REGISTER.md"),
    ("checks/released_text.py",),
)
CODE_COMMANDS = (
    ("checks/expected_tests.py",),
)
WHY = ("The base branch's checks judge a pull request: its scripts read the pull request's data, and its tests and "
       "runner judge the pull request's checks. A pull request that changes a check, the job that runs it, or the form "
       "of a data file on purpose is one the base branch cannot judge, and the job stays red. The maintainer reads the "
       "change and merges it as an administrator (D-2026-11-16-code-owner). Nothing here passes it silently.")


class JudgeError(Exception):
    pass


def git(repo, *args, data=None):
    """What git prints, as bytes. Raises JudgeError when it fails."""
    # Every path is a path, never a pattern: a name such as "checks/*.py" means that one file.
    result = subprocess.run(["git", "--literal-pathspecs", "-C", repo] + list(args), input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise JudgeError("git %s failed: %s" % (" ".join(args), result.stderr.decode("utf-8", "replace").strip()))
    return result.stdout


def rev(repo, name):
    return git(repo, "rev-parse", "--verify", "--quiet", name + "^{commit}").decode("ascii").strip()


def files(repo, commit):
    """Every path that commit tracks, as text."""
    listed = git(repo, "ls-tree", "-r", "-z", "--name-only", commit)
    return [path.decode("utf-8", "surrogateescape") for path in listed.split(b"\0") if path]


def is_code(path):
    """Whether a path is code of the checks: a .py file directly under checks/, or any file in a directory under checks/
    other than fixtures/."""
    parts = path.split("/")
    if parts[0] != "checks" or len(parts) < 2:
        return False
    if len(parts) == 2:
        return parts[1].endswith(".py")
    return parts[1] != "fixtures"


def is_test(path):
    parts = path.split("/")
    return len(parts) == 2 and parts[0] == "checks" and parts[1].startswith("test_") and parts[1].endswith(".py")


def judged_by(path):
    """Whether the base judges by a path: the code of the checks, or the workflow that runs them."""
    return is_code(path) or path == WORKFLOW


def the_base(repo, base_sha, head_sha):
    """The commit to judge by: the first parent of HEAD, after checking that HEAD is the merge of head_sha into the base."""
    for name, value in (("--base-sha", base_sha), ("--head-sha", head_sha)):
        if not SHA.match(value or ""):
            raise JudgeError("%s must be a full commit id of 40 lowercase hex digits, and it is %r" % (name, value))
    parents = git(repo, "rev-list", "--parents", "-n", "1", "HEAD").decode("ascii").split()[1:]
    if len(parents) != 2:
        raise JudgeError("HEAD is not the merge commit of a pull request: it has %d parent(s), not 2. Check out the merge "
                         "commit that GitHub makes, as actions/checkout does on pull_request" % len(parents))
    base, head = parents
    if head != head_sha:
        raise JudgeError("the second parent of HEAD is %s, not the pull request's head %s" % (head, head_sha))
    if base != base_sha and subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", base_sha, base]).returncode != 0:
        raise JudgeError("the first parent of HEAD, %s, is not the base %s or a later commit of it" % (base, base_sha))
    return base


def tree(repo, commit, path):
    """A work tree of its own at path, detached at commit, sharing the repo's objects and tags."""
    git(repo, "worktree", "add", "--quiet", "--detach", path, commit)
    return path


def swap(work, remove, add_from, add):
    """In the work tree, remove the paths in remove, then check out the paths in add from the commit add_from."""
    if remove:
        git(work, "rm", "-q", "-r", "-f", "--ignore-unmatch", "--pathspec-from-file=-", "--pathspec-file-nul",
            data=b"\0".join(path.encode("utf-8", "surrogateescape") for path in remove))
    if add:
        git(work, "checkout", add_from, "--pathspec-from-file=-", "--pathspec-file-nul",
            data=b"\0".join(path.encode("utf-8", "surrogateescape") for path in add))


def placeholders(work, paths):
    """Write an empty file at each path in the work tree, so that a link to it leads somewhere and none of its code runs."""
    for path in paths:
        full = os.path.join(work, *path.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "x", encoding="utf-8"):
            pass


def run(work, command):
    """Run one command of the base in a work tree. Returns its exit status. Its output goes where this process's goes."""
    sys.stdout.flush()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.call([sys.executable, "-B"] + list(command), cwd=work, env=env)


def judge(repo, base, head="HEAD", data_commands=DATA_COMMANDS, code_commands=CODE_COMMANDS):
    """Judge head by the checks of base. Returns the problems, each as a line of text."""
    problems = []
    # By commit id: in a work tree of its own, a name such as HEAD names that tree's commit.
    base, head = rev(repo, base), rev(repo, head)
    base_files, head_files = files(repo, base), files(repo, head)
    changed = [path.decode("utf-8", "surrogateescape") for path in
               git(repo, "diff", "-z", "--name-only", "--no-renames", base, head).split(b"\0") if path]
    if WORKFLOW in changed:
        problems.append("the pull request changes %s, the job that runs these checks. The base branch cannot judge the "
                        "job that judges it" % WORKFLOW)
    scratch = os.path.realpath(tempfile.mkdtemp(prefix="ratchet-from-base-"))
    works = []
    try:
        # The tree of the data: the merge, with the base's code of the checks.
        data = tree(repo, head, os.path.join(scratch, "data"))
        works.append(data)
        swap(data, [path for path in head_files if is_code(path)], base, [path for path in base_files if is_code(path)])
        # A file of code that only the pull request has is there, empty: a link to it from the data leads somewhere, and a
        # module that would stand in for one the base imports, such as json.py, has nothing in it.
        placeholders(data, sorted(set(path for path in head_files if is_code(path)) - set(base_files)))
        # The tree of the code: the base, with the pull request's code of the checks but the base's tests and runner.
        code = tree(repo, base, os.path.join(scratch, "code"))
        works.append(code)
        theirs = [path for path in head_files if is_code(path) and not is_test(path) and path not in RUNNER]
        ours = [path for path in base_files if is_code(path) and not is_test(path) and path not in RUNNER]
        swap(code, ours, head, theirs)
        for name, work, commands in (("data", data, data_commands), ("code", code, code_commands)):
            for command in commands:
                shown = "python3 " + " ".join(command)
                print("from_base: in the tree of the %s: %s" % (name, shown))
                status = run(work, command)
                if status != 0:
                    problems.append("the base's `%s` failed in the tree of the %s, with exit status %d" % (shown, name, status))
    finally:
        for work in works:
            subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", work], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(scratch, ignore_errors=True)
        subprocess.run(["git", "-C", repo, "worktree", "prune"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if problems:
        touched = [path for path in changed if judged_by(path)]
        problems.append("paths this pull request changes that the base judges by: %s" % (", ".join(touched) if touched else "none"))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Judge a pull request by the base branch's checks.")
    parser.add_argument("--base-sha", required=True, help="the base of the pull request, github.event.pull_request.base.sha")
    parser.add_argument("--head-sha", required=True, help="the head of the pull request, github.event.pull_request.head.sha")
    parser.add_argument("--repo", default=".", help="the checkout of the merge commit")
    args = parser.parse_args(argv)
    repo = os.path.realpath(args.repo)
    try:
        base = the_base(repo, args.base_sha, args.head_sha)
        print("from_base: judging %s, the merge of %s, by the checks of the base %s" % (rev(repo, "HEAD"), args.head_sha, base))
        problems = judge(repo, base)
    except JudgeError as error:
        problems = [str(error)]
    if problems:
        print("from_base: FAIL: the base branch's checks do not pass this pull request:")
        for problem in problems:
            print("- " + problem)
        print(WHY)
        return 1
    print("from_base: the base branch's checks pass this pull request, in the tree of the data and in the tree of the code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
