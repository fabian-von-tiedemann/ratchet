# Upgrading to a newer Ratchet

A project states in `register.json` which version of Ratchet it follows. An upgrade moves it to a newer one, in a PR of its own (`ratchet.si-pull`). A new project does not upgrade: it starts with `checks/init.py`, as the [README](README.md#start-here) and [STARTING.md](STARTING.md) say, and so does a project that has an instruction file of its own and no register yet, which `init.py` adopts.

## The command

Run it in the root of your own repo, on a branch of its own, where `.ratchet` is the git clone of Ratchet that the README made.

```sh
python3 .ratchet/checks/upgrade.py register.json
```

It fetches the tags of `.ratchet`, reads the version that `register.json` states, and compares that tag with the latest release, or with the one you ask for with `--to 0.12`. It says how many releases behind the register is, moves `.ratchet` to the release, and prints what the register must do: each adopted rule that changed or was removed, with the entry to paste, the new rules to borrow, and the commands that put `REGISTER.md`, and the instruction file the register names, in place again and check them. Last it prints the commit to pin `.github/workflows/ratchet.yml` to. It says how to move `.ratchet` back. It does not move a clone with changes of its own, or one on a branch, for which it prints the command that moves it to the release.

It fails, and prints no steps, when the register does not pass against the version it states: fix that first. It cannot run when the version the register states has no tag in `.ratchet`. With `--no-fetch`, which uses only the tags the clone has, it prints the command that fetches them. After a fetch, that version was never released.

For a JSON register from 0.3 through 0.11 it prints the commands of the first leg instead: `.ratchet` to `v0.11`, whose `upgrade.py` takes the register to 0.13, then the command again.

When `.ratchet` is not a git clone, clone it again as the README says. Without git, `--from` compares two files you give it and fetches nothing: see [checks/README.md](checks/README.md#upgradepy).

## Then

1. Do each step in `register.json`. A changed rule comes with its new entry: replace the old entry with it. A removed rule is taken out of `adopted`; to keep it, add the printed entry to `own` too. When the ratchet of a rule marked `built` changed, look again at the check. When a rule you adopt with a translation changed its text, translate the new rule and add the translation back with the sha256 printed. When a rule you adopt by reference changed its rule or its ratchet, its entry comes with the new `sha256`: read your own wording in the file the row names again, change it where it no longer says what the rule says, and then set the new `sha256`. The check fails from when you move `ratchet_version` until you do.
2. Choose which new rules, if any, the project adopts. They are listed by key under their part, and `--new-rules full` prints the entry of each. Add a rule when a failure shows you need it, not because it is new.
3. Run the commands printed at the end, in order. They print each file to a new one in the directory you run them in and move it into place, so that nothing is written through a link. For an instruction file at `docs/AGENTS.md` the second is `rm -f AGENTS.md.new && python3 .ratchet/checks/check_register.py register.json --print-instructions > AGENTS.md.new && rm -f docs/AGENTS.md && mv AGENTS.md.new docs/AGENTS.md`.
4. Pin `.github/workflows/ratchet.yml` to the commit printed. Compare it with `.ratchet/templates/ratchet-checks.yml` if you want what is new there. A project that adopt mode started has no such workflow: the command prints instead how to copy `checks/run_pinned.py` again from the new commit, and the line for your local check script and your CI step. Put them in place of the old ones.
5. A project that adopts `ratchet.irreversible-waits` keeps a copy of `checks/tripwire.py` at `.claude/hooks/tripwire.py`. Replace it with the one in `.ratchet`.
6. Open the PR. Its description holds the output of the command and of the check, and says which new rules the project adopted and why. Why each rule changed, and every change of form, is in `.ratchet/CHANGELOG.md`, in the entries after your old version.

## Falling behind

`python3 .ratchet/checks/upgrade.py register.json --behind` prints how many releases came after the register's version, and exits 1 when any did. It moves nothing. The workflow template runs it once a week, in the job `behind`. To add it, keep your workflow and its own checks, and copy the `schedule`, the `if` of each job and the job `behind`. Add the `env`, with `RATCHET_COMMIT` set to the commit you pin, of 0.17 or later, since earlier ones lack `--behind`. Then set the `ref` of the job `ratchet` to `${{ env.RATCHET_COMMIT }}`, so one pin moves both. For a report that never fails, add `|| true`.

## What the command does not do

- It does not change `register.json`, `REGISTER.md` or any other file of the project. It changes only `.ratchet`, with git.
- It reaches no network but the origin of `.ratchet`, and only to fetch tags.
- It does not see whether a check marked `built` still exists or works.
- It does not list a rule that only moved to another part of Ratchet.
