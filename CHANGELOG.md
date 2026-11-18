# Changelog

## 0.6 (2026-11-18)

<!-- generated:count -->
Ratchet 0.6, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 25 experimental rules, under a cap of 25: 11 name a check and 14 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

Four rules are added in this version, and none is changed or removed. The form of `ratchet.json` does not change. The rules come from the decisions `D-2026-11-17-knowledge-and-modes`, items 1 and 4, and `D-2026-11-17-harness-sandbox-risk`, item 1, and they bring the rules outside the core to the cap of 25.

Added:

- `ratchet.irreversible-waits`, experimental, in a new part of `CONTROL-ROOM.md`, "What can be undone": an agent goes ahead with a step that can be undone and waits for the owner on one that cannot, unless a recorded approval names the step and the exact command. Its reference check, `checks/irreversible.py`, is a hook that Claude Code runs before each command. It denies a force push, creating or deleting a tag, a release, deleting outside the working tree and a change to the repository's settings, with exit code 2 and the reason, unless `.claude/ratchet-approvals.json` approves that step for that command until a given day. It denies, and never lets an approval reach, a command it cannot read with certainty, and a command or a file tool that may lead to the approvals file. It stands against an agent's mistake, not against an agent that means to get round it. See [checks/README.md](checks/README.md#irreversiblepy).
- `ratchet.phase-explore`, `ratchet.phase-build` and `ratchet.phase-run`, experimental and text only, in a new part of `CONTROL-ROOM.md`, "The phases": what an agent may do in each phase of a work package, and what ends the phase. Explore changes nothing that others rely on, build works on one approved work package and merges on green checks and a passed review, and run operates what is merged and sends a fix back to build.
- `templates/claude-settings.json` and `templates/ratchet-approvals.json`: the settings that run a copy of the hook in a project, and block the command when the hook fails to run, and an approvals file that approves nothing.

## 0.5 (2026-11-18)

<!-- generated:count -->
Ratchet 0.5, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 21 experimental rules, under a cap of 25: 10 name a check and 11 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

No rule is added or removed in this version, and one is changed. It adds a way for a project to upgrade, and a cap on the rules outside the core, by the decision `D-2026-11-17-pull-and-budget`. The cap is a new required field in `ratchet.json`, a change of form, which a minor version before 1.0 may now make, by the decision `D-2026-11-18-form-change-before-1-0`.

Added:

- `checks/upgrade.py` and `UPGRADING.md`: the upgrade path. Given a project's `register.json` and the `ratchet.json` of the version the register states, the script prints what the register must do to move to the Ratchet it is run from: for each adopted rule that changed or was removed, the entry to paste or the reason to remove it, and for each new rule, the entry to paste if the project adopts it. It writes nothing and runs offline, on the files it is given. It fails when the register does not pass against the version it states, and it checks that the register with every step done passes against the newer one. See [checks/README.md](checks/README.md#upgradepy).
- `experimental_cap` in `ratchet.json`: the most experimental rules there may be, 25, which is the 20 there were when the decision was recorded on `main`, plus five. Every check that reads `ratchet.json` fails when there are more, so `generate.py --check` is red. A new experimental rule then replaces, merges or removes one, or a decision raises the cap. The count of rules states the cap.

Changed:

- `ratchet.si-version`: before 1.0, a minor version may also change the form, and the changelog lists every change of form, as it lists every rename. The rest of the rule is as it was. A register that adopts it replaces its entry: `upgrade.py` prints the new one, and a status and a `where` stay.

Changes of form:

- `ratchet.json` has `experimental_cap`, a required field, a whole number from 0. A `ratchet.json` without it, or with a value of another kind, is not a valid data file. Ratchet's checks read `ratchet.json` strictly, so the checks of 0.4 refuse the `ratchet.json` of 0.5 for the field they do not know, and the checks of 0.5 refuse that of 0.4 for the field it lacks. A project whose checks are those in `.ratchet`, fetched at the version its register states as the README says, has nothing to do: the checks and `ratchet.json` come from the same version. A project that keeps a copy of a Ratchet check, or has a check of its own, that reads `ratchet.json` replaces the copy with the one from 0.5, or changes its check to read the field. `upgrade.py` says so when the form changed between the two versions it compares.

## 0.4 (2026-11-17)

<!-- generated:count -->
Ratchet 0.4, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 21 experimental rules: 10 name a check and 11 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

Added:

- `ratchet.expected-tests-ran`, experimental, in a new part of `SELF-IMPROVEMENT.md` for rules promoted from projects: a suite of tests made from a source fails when a test it expects did not run and pass. Its reference check, `checks/expected_tests.py`, runs this repo's suite in a child process, through `checks/suite_runner.py`, and reads the record that the runner writes of every outcome and of the end of the run. It fails when a test did not pass exactly once, when the run did not finish, and when a file under `checks/fixtures/` was not loaded by a test that passed. It catches tests dropped by mistake, not test code written to defeat it. See [checks/README.md](checks/README.md#expected_testspy).
- `checks/released_text.py`: fails when a released changelog entry, or the `ratchet.json` of a released version, is not as it stood at its tag, when a tag has no changelog entry, and when an entry after the first has no tag. A version that adds a rule is released on its own, by the decision `D-2026-11-17-new-approaches`.
- `checks/release.py` and `.github/workflows/release.yml`: a version is tagged and released when it reaches `main`, from the version in `ratchet.json` (PR #9). The release text is one fixed line, with links to this changelog and to the files at the tag: nothing is copied from the changelog. A run fails closed: when it cannot confirm that every version that `ratchet.json` on `main` has named is tagged and released, it is red, and it writes nothing before every check has passed. It never moves, deletes or edits a tag. A scheduled run every day writes nothing, and is red while a version is unfinished. It names that version when the GitHub API answers, which is not promised. See [checks/README.md](checks/README.md#releasepy) and the decisions `D-2026-11-17-release-on-merge`, `D-2026-11-17-release-links`, `D-2026-11-17-release-narrow-claim` and `D-2026-11-17-release-fail-closed`.
- `checks/watch_sources.py` and `.github/workflows/watch-sources.yml`: a watch, once a day, on the sources pinned in `ratchet.json` (PR #10). When a source has moved past its pin, or its pinned commit is gone, it opens one issue for it. An issue holds only values the watch has checked itself and text written in the code, never text from a source. It is a tool of this repo, not a reference check for a rule. See [checks/README.md](checks/README.md#watch_sourcespy).

Changed:

- Only the first entry of the changelog, the version being released, is generated. Every entry after it stays as it was released.
- The tests in `checks/test_checks.py` and `checks/test_watch_sources.py` load their fixtures through `FixtureTest`.

## 0.3 (2026-11-16)

<!-- generated:count -->
Ratchet 0.3, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 20 experimental rules: 9 name a check and 11 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

In 0.1 and in 0.2, counted the same way: `RATCHET.md` had 35 rules, 14 named a check and 21 were text only (60%). Ratchet shipped no check.

The core is frozen from this version: see [RATCHET.md](RATCHET.md#the-core-is-frozen) and the decision [D-2026-11-16-scope](decisions/D-2026-11-16-scope.md). The tag `v0.2` was already published when this work was finished, so it is released as 0.3: see [D-2026-11-16-renumber](decisions/D-2026-11-16-renumber.md).

**The format of a register changes.** In 0.2 a register was a Markdown file, checked by a few lines of shell. From 0.3 it is a data file, `register.json`, and `REGISTER.md` is generated from it. A register written for 0.2 has to be moved by hand: see [MIGRATING.md](MIGRATING.md). Ratchet ships no reference check for decision files or for the glossary. Two attempts were reviewed and set aside, and how to check them is an open question.

The reason for the new format is that two reviews in a row found new ways to hide a changed row from a check that read Markdown. A data file has one form, and the generated file is compared with it byte for byte.

Added:

- `ratchet.json`: every rule as data, with its part, its status (`core` or `experimental`) and its enforcement (`enforced` or `text-only`). The rule tables are generated from it.
- A reference check for `ratchet.register-on-top`, `checks/check_register.py`. It reads a project's `register.json`, compares it with Ratchet at the version it states, and fails unless `REGISTER.md` is exactly what the data generates. A value in a data file is text, never Markdown: it is written into a generated file with a backslash before every punctuation mark, so that data cannot become a link, HTML or hidden text. The one other form is code, between a pair of backticks. A value is written in Latin script: its characters come from one fixed list of Latin letters, digits, the plain space and marks, written out as code points in the check, so that a value is valid or not the same on every supported version of Python. No character on the list is written right to left or changes the order a line is shown in. No character on the list is a compatibility form, which is not a protection against characters that look alike. A name between two colons is refused, so that a site cannot show it as a picture. A person named with `@`, an issue named with `#` and the id of a commit are accepted and written as text, and what a site makes of them is not covered. Every file a check reads is strict UTF-8, and bytes that are not UTF-8 fail the check. See [checks/README.md](checks/README.md) and [D-2026-11-17-latin-strict-utf8](decisions/D-2026-11-17-latin-strict-utf8.md). It has a clean project copy it passes on and one copy for each fault it fails on, including every way of hiding a row that the reviews found. It runs in this repo's CI, together with a check that the generated text matches the data files.
- `GLOSSARY.md`: Ratchet's own terms.
- Ratchet's own `AGENTS.md`, `register.json` with the generated `REGISTER.md`, `HANDOVER.md` and first seven decisions.
- `.github/CODEOWNERS`: the maintainer owns every path. It takes effect when the protection on `main` requires the code owner's review, which the maintainer sets up after this version is published.
- The templates `register.json`, `DECISION.md`, `GLOSSARY.md` and `ratchet-checks.yml`.
- `MIGRATING.md`: how to move a register written for 0.2.

Changed:

- Ratchet no longer says that it ships no checks. It ships one, and says which.
- `ratchet.one-approver` and `ratchet.checks-owner-read` now name a check: a required review by the owner, through code ownership, with agents under an account of their own. The share of core rules that are text only falls from 21 to 19 of 35.
- A project adopts rules verbatim, in its `register.json`. It chooses which rules it takes and never rewrites one. `templates/register.json` holds the nine starting rules.
- `CONTROL-ROOM.md` and `SELF-IMPROVEMENT.md` are marked experimental and are not counted in the text-only share.
- `ratchet.glossary`: the rule and its ratchet now say the same thing. The glossary lists the terms to avoid, and the check fails on them.
- `ratchet.work-in-issues`: the handover may be a file in the repo that the status issue links to.
- `ratchet.cr-reads-first`: reads "the latest handover", wherever the project keeps it.
- `ratchet.lesson-names-check`: the rule no longer holds a link, which broke when the row was copied into a register.
- The contract for the review script moved from `CONTROL-ROOM.md` to `RATCHET.md`, because three core rules depend on it.
- The README says whose rules these are: the maintainer's own way of working with agents, kept up to date, and open for others to use.
- The README's shell lines for comparing a copy are replaced by the reference check, and the start is written as steps to run from an empty project.
- `templates/DECISION.md` asks for the original and a marked translation when the question was put in another language.
- `templates/AGENTS.md` no longer names one agent tool's directory for skills.

Removed:

- `templates/REGISTER.md`: a register is generated from data, not copied and edited.

## 0.2 (2026-11-16)

Added:

- `SELF-IMPROVEMENT.md`: how a lesson becomes a check and travels back to Ratchet, with versioning and a two-week measure.
- `CONTROL-ROOM.md`: how a project is run with one coordinating agent session and short-lived workspaces, with the contract for the review script.
- The templates `REGISTER.md`, `LESSON.md` and `CONTROL-ROOM-HANDBOOK.md`.
- `ratchet.protected-main`.
- A starting set of nine rows and a way to check a copy, in the README.
- The icon.

Changed:

- The ratchet column now starts with "Check:" or "Text only:", and every "text only" gives its reason. Ratchet says plainly that it ships no checks.
- Decision ids are `D-YYYY-MM-DD-<slug>` (was `U-`). The four kinds of statement are decision (D), proposal (P), outside observation (O) and open question (Q).
- "Trial" is now "experiment", and "mandate" is "approval".
- The source column shows a dash where it said "Own experience".

Renamed keys:

| 0.1 | 0.2 |
|---|---|
| ratchet.keep-kinds-apart | ratchet.kinds-apart |
| ratchet.issues | ratchet.work-in-issues |
| ratchet.one-place | ratchet.one-channel |
| ratchet.facts-yourself | ratchet.look-up-facts |
| ratchet.finding-proof-axis | ratchet.findings-marked |
| ratchet.receive | ratchet.verify-findings |
| ratchet.factory | ratchet.checks-owner-read |
| ratchet.other-family | ratchet.register-review-first |
| ratchet.proven-before-own | ratchet.reuse-first |
| ratchet.run-before-paper | ratchet.run-early |
| ratchet.test-tests-the-claim | ratchet.test-can-fail |
| ratchet.trial-description | ratchet.experiment-plan |
| ratchet.guard-visible | ratchet.nightly-visible |
| ratchet.keys-away | ratchet.agents-without-keys |
| ratchet.ratchet | ratchet.lesson-names-check |

Removed:

- `ratchet.up-to-ratchet`: covered by `ratchet.si-promote`.

## 0.1 (2026-11-16)

- First version: `RATCHET.md` with rules in six parts, and templates for `AGENTS.md` and `SOURCE.md`.
