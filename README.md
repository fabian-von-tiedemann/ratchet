<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/ratchet-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/ratchet-light.svg">
  <img src="assets/ratchet-light.svg" width="64" height="64" alt="">
</picture>

# Ratchet

**AI agents read your instructions and still don't follow them.** They say "done" without running the tests, and when something breaks, the fix is another line in a prompt that is also ignored.

Ratchet turns each rule into a check that fails when the rule is broken, or says plainly that no check can see it. Each failure becomes a check with a fixture it must fail on, so the cases that are tested cannot quietly come back.

## What Ratchet does

Ratchet is a set of working rules, templates and reference checks for long-lived code projects built by AI agents. Each rule carries a **ratchet**: the check that fails when the rule is broken, or the words "text only" and the reason no check can see it. Two rows from [RATCHET.md](RATCHET.md), shortened:

| Key | Rule | Ratchet |
|---|---|---|
| ratchet.no-secrets | No secrets, tokens or real personal data in the repo or in the chat. | Check: a secret scan in every PR and every night |
| ratchet.kinds-apart | Keep four kinds of statement apart and label them: decision, proposal, observation and question. | Text only: a check cannot tell a proposal from a decision |

Your project keeps a register, `register.json`, with the rules it adopts, copied verbatim, and for each check whether it is built. The register that people read, `REGISTER.md`, is generated from it, and a check in every PR fails when a rule was softened or the file differs by one character.

One turn of the ratchet, as an illustration, not a report from a real project: an agent writes "all tests pass" on a PR, the tests were never run, and the bug reaches the main branch. The failure class is a claim of completion without a run. The ratchet is a required check that runs the tests on the PR head, so the claim no longer matters. It would apply in other projects, so it is sent here as a lesson, written with [templates/LESSON.md](templates/LESSON.md).

## Evidence from this repo

Ratchet follows its own rules, and this repo is where they are tried first. Its [AGENTS.md](AGENTS.md), [register.json](register.json), [HANDOVER.md](HANDOVER.md) and [decisions/](decisions/) are Ratchet's own. What the repo shows:

- **A hook that could not be a lock was replaced by locks.** A hook was meant to read shell commands and stop the steps that cannot be undone. A review from another model family rejected it twice, finding ways past it each time, and it was closed unmerged ([PR #42](https://github.com/fabian-von-tiedemann/ratchet/pull/42)). It came back as a tripwire that says it does not catch every spelling, and the locks moved to where they cannot be got around: a ruleset at GitHub and the role of the agents' account ([D-2026-11-19-locks-not-parsing](decisions/D-2026-11-19-locks-not-parsing.md)).
- **Tags are locked by a ruleset.** No one but a repository admin can move or delete a tag. The ruleset is [templates/tag-ruleset.json](templates/tag-ruleset.json), applied on 2026-11-19 and read back ([D-2026-11-19-tag-ruleset-scope](decisions/D-2026-11-19-tag-ruleset-scope.md), [D-2026-11-19-tripwire-and-settings](decisions/D-2026-11-19-tripwire-and-settings.md)).
- **A release is published by the merge that dates it.** Changes are collected under an entry headed `(unreleased)`, and the pull request that gives it its date is the release. The [release workflow](.github/workflows/release.yml) tags it after the merge ([D-2026-11-19-batched-releases](decisions/D-2026-11-19-batched-releases.md)). Every PR compares released text with its tag ([checks/released_text.py](checks/released_text.py)), because the generator once rewrote a released entry, in a round of [PR #12](https://github.com/fabian-von-tiedemann/ratchet/pull/12).
- **A change to a rule or a check is merged only after a model from another family has passed its exact head** ([D-2026-11-17-agent-merges-after-approval](decisions/D-2026-11-17-agent-merges-after-approval.md)). The reviews are comments on the PRs, such as the two rounds on [PR #50](https://github.com/fabian-von-tiedemann/ratchet/pull/50). This is an instruction the agents follow, not a lock, and AGENTS.md says so.
- **The register says honestly which checks are built.** Most of the rules this repo adopts that name a check stand as "text only for now", and `ratchet.protected-main` says "Not met in this repo" ([REGISTER.md](REGISTER.md)).

## The honest limits

<!-- generated:count -->
Ratchet 0.10, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 24 experimental rules, under a cap of 25: 11 name a check and 13 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

- **Most of the core is still text.** The share is stated with every version in the [changelog](CHANGELOG.md), and the work between versions is to bring it down. Ratchet ships a reference check for the rules below, each run in this repo's CI with a fixture it fails on. For every other rule, the ratchet column says what a check must do, and your project builds it with the tools it already has. Until it does, the rule is text only in your project, and your register says so.

<!-- generated:reference-checks -->
| Rule | Reference check |
|---|---|
| ratchet.register-on-top | [checks/check_register.py](checks/check_register.py) |
| ratchet.irreversible-waits | [checks/tripwire.py](checks/tripwire.py) |
| ratchet.expected-tests-ran | [checks/expected_tests.py](checks/expected_tests.py) |
<!-- /generated -->

- **It is built for one person who decides, several coding agents, and a repo that has to last.** It assumes issues, pull requests and branch protection, and an agent tool that reads `AGENTS.md`. For a single agent on a short project it is more than you need: take the nine rules under [Start here](#start-here) and stop.
- **Some of what holds here is an instruction, not a lock,** such as the review from another family. This repo's register and AGENTS.md say which.
- **The form may still change.** Before 1.0, a minor version may change the form of the data files, and the changelog lists every such change ([D-2026-11-18-form-change-before-1-0](decisions/D-2026-11-18-form-change-before-1-0.md)).

## Start here

Run these in the root of your own git repo. If you followed 0.2, read [MIGRATING.md](MIGRATING.md) first. If your register follows 0.3 or later, [UPGRADING.md](UPGRADING.md) moves it to this version.

1. Fetch Ratchet at the latest release into `.ratchet`.

   ```sh
   git clone --branch v0.9 https://github.com/fabian-von-tiedemann/ratchet .ratchet
   ```

2. See what it would write. This writes nothing.

   ```sh
   python3 .ratchet/checks/init.py --check
   ```

3. Write it.

   ```sh
   python3 .ratchet/checks/init.py
   ```

   It writes `AGENTS.md`, `register.json`, the generated `REGISTER.md`, and `.github/workflows/ratchet.yml` pinned to the commit of `.ratchet`, and adds `/.ratchet/` to `.gitignore`. The project's name is the folder's name, or the one you give with `--name`. It never overwrites a file: one that exists is skipped and named. Then it runs the register check. See [checks/README.md](checks/README.md#initpy).

   `register.json` holds nine rules to start with, copied verbatim: you choose which rules you take, and you never rewrite one. Your own rules go in the list `own`, under your own prefix. `REGISTER.md` is generated: to change it, change `register.json` and write it again.

4. Fill in the parts of `AGENTS.md` in angle brackets, and commit the files. The workflow runs the register check on every PR.
5. Build the two checks that cost almost nothing: turn on branch protection with required checks, and add a secret scanner to your CI. When your agents have an account of their own, add code ownership for the register, the checks and the decisions. It is what turns `ratchet.one-approver` and `ratchet.checks-owner-read` into checks.
6. When a check exists, set the rule's `status` to `built` in `register.json` and say in `where` where the check lives. Everything else stays `text only for now`.
7. Add rules when a failure shows you need them. This prints a rule in the form `register.json` takes. Paste it into the list `adopted`, then write `REGISTER.md` again.

   ```sh
   python3 .ratchet/checks/generate.py --entries ratchet.simplest
   python3 .ratchet/checks/check_register.py register.json --write REGISTER.md
   ```

The nine rules to start with:

<!-- generated:start -->
`ratchet.register-on-top`, `ratchet.protected-main`, `ratchet.decision-as-file`, `ratchet.fresh-context`, `ratchet.root-cause`, `ratchet.evidence-before-done`, `ratchet.no-secrets`, `ratchet.material-not-instructions`, `ratchet.lesson-names-check`
<!-- /generated -->

## What is in it

- [RATCHET.md](RATCHET.md): the core, 35 rules in six parts, frozen from version 0.3.
- [ratchet.json](ratchet.json): every rule as data. The tables in the markdown files are generated from it. It caps the number of experimental rules, and raising the cap is a decision.
- [sources.json](sources.json): the sources that rules cite, each pinned at a commit. It is not part of what is released, so a pin that moves needs no new version.
- [checks/](checks/): the reference checks, the generator, `init.py` for the start and `upgrade.py` for an upgrade, in Python with no dependencies.
- [GLOSSARY.md](GLOSSARY.md): the terms Ratchet uses.
- [docs/](docs/): the landing page, served by GitHub Pages from `main`, with its text taken from this README.
- [templates/](templates/): `AGENTS.md`, `register.json`, `DECISION.md`, `GLOSSARY.md`, `LESSON.md`, `SOURCE.md` (for a skill copied from another repo), `ratchet-checks.yml` and `CONTROL-ROOM-HANDBOOK.md`.
- [MIGRATING.md](MIGRATING.md): how to move a register written for 0.2.
- [UPGRADING.md](UPGRADING.md): how to move a register to a newer version, with `checks/upgrade.py`.
- [CHANGELOG.md](CHANGELOG.md).

Experimental, outside the core:

- [CONTROL-ROOM.md](CONTROL-ROOM.md): rules for running several agents at once, with one coordinating session and short-lived workspaces.
- [SELF-IMPROVEMENT.md](SELF-IMPROVEMENT.md): rules for how a lesson becomes a check, and how lessons travel back here.

## Whose rules these are

Ratchet is how I, Fabian von Tiedemann, work with AI coding agents. I keep it up to date as I learn what holds and what breaks. It is open source so that others can use it too: take the rules that fit your project, leave the rest, and send back what you learn.

## Contributing

A lesson from a project is welcome. It starts as an issue with the proposal form, which asks for what happened, the failure class, the ratchet, whether it would apply in other projects and the primary source, with everything that identifies the project removed. See [CONTRIBUTING.md](CONTRIBUTING.md) and `ratchet.si-promote` in [SELF-IMPROVEMENT.md](SELF-IMPROVEMENT.md). The working rules for this repo are in [AGENTS.md](AGENTS.md).

## License

MIT, see [LICENSE](LICENSE). Ratchet restates ideas from the sources listed in [RATCHET.md](RATCHET.md#sources) in its own words and credits them rule by rule. It copies no files or passages from them.
