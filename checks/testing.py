"""The git setup that the tests share: git run in a repository a test made, with no configuration of the user's or the
system's. And where a script stands: in checks/, what a project runs, or in maintain/, what only Ratchet's own
maintenance runs (D-2026-11-27-maintain-apart).

It is not named test_*, so the runner does not collect it. It keeps no state between calls: each call builds what it
needs from os.environ and its arguments, and every difference between callers is an argument.

Standard library only. CI runs it on Python 3.9 and the newest Python 3.
"""

import os
import subprocess

# No automatic gc or maintenance in a repository a test makes. git starts them in the background after a commit or a
# fetch, and one still writing in .git is a likely, not a proven, cause of an intermittent "could not parse HEAD" and
# of a removal that finds .git/objects/pack not empty. git() writes them into the config of each repository it inits or
# clones, so that a script under test that runs git there starts none either.
QUIET = (("gc.auto", "0"), ("maintenance.auto", "false"))
# The variables that name a repository from outside, as a git hook sets them.
LOCATION = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
EMAIL = "test@example.invalid"
# The two directories of the code of the checks, in this repo. A script's name stands in one of them, never in both.
CHECKS = os.path.dirname(os.path.abspath(__file__))
MAINTAIN = os.path.join(os.path.dirname(CHECKS), "maintain")
CODE = ("checks", "maintain")


def directory(name):
    """The directory, "checks" or "maintain", that holds the script with this name in this repo. A name that is in
    neither, such as a script a test writes, is in checks/."""
    return "maintain" if os.path.isfile(os.path.join(MAINTAIN, name)) else "checks"


def script(root, name):
    """The path of the script with this name in the copy of this repo at root."""
    return os.path.join(root, directory(name), name)


def identity(name):
    """The author and committer of a test's commits, as variables of the environment."""
    return {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": EMAIL, "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": EMAIL}


def environment(drop=LOCATION, **changes):
    """os.environ with no global or system config for git. drop names the variables left out, or is "GIT_" to leave out
    every GIT_ variable. changes are set last."""
    env = {k: v for k, v in os.environ.items() if not (k.startswith("GIT_") if drop == "GIT_" else k in drop)}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    env.update(changes)
    return env


def quiet_options(flag="-c"):
    """Each setting of QUIET after flag: -c for one call of git, --config for the repository a clone makes."""
    return [part for name, value in QUIET for part in (flag, "%s=%s" % (name, value))]


def git(directory, *args, env, options=(), **kwargs):
    """What git prints on standard output for args in directory, run with options before them and env as its
    environment. kwargs go to subprocess.run. A failure raises AssertionError with what git printed. QUIET is written
    into the config of the repository that init or clone makes."""
    if args[:1] == ("clone",):
        args = args[:1] + tuple(quiet_options("--config")) + args[1:]
    result = subprocess.run(["git"] + list(options) + ["-C", directory] + list(args), env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True, **kwargs)
    if result.returncode:
        raise AssertionError("git %s: %s%s" % (" ".join(args), result.stdout, result.stderr))
    if args[:1] == ("init",):
        for name, value in QUIET:
            git(directory, "config", name, value, env=env, options=options)
    return result.stdout.strip()


def commit(directory, message, env, options=()):
    """Commit every file in directory, even when nothing changed, and return the new commit."""
    git(directory, "add", "-A", env=env, options=options)
    git(directory, "commit", "-q", "--allow-empty", "-m", message, env=env, options=options)
    return git(directory, "rev-parse", "HEAD", env=env, options=options)
