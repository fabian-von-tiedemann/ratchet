# Changelog

## 0.10 (unreleased)

<!-- generated:count -->
Ratchet 0.10, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 23 experimental rules, under a cap of 25: 11 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

No rule is added, changed or removed in this version.

Added:

- `docs/index.html`: a landing page for GitHub Pages, served from `docs/` on `main` with no build step (`docs/.nojekyll`). It is one page with its CSS inline, no script, and nothing loaded from another origin, in light and dark. Its text is taken from `README.md`. It goes live when the maintainer turns on Pages for `main` and `/docs`, a setting of the repository.
- `checks/test_pages.py`: a test of this repo that reads the page strictly. It fails on an element or an attribute the page may not hold, an element left open, anything loaded from another origin, a link that leads out of the repo or to a file that does not exist, a heading that skips a level, an image without alt text, a pair of colors under a contrast ratio of 4.5, and a command that is not a line of a code block in `README.md`. See [checks/README.md](checks/README.md#the-landing-page).

Changed:

- `checks/generate.py` writes the version in the line of `docs/index.html` that fetches Ratchet, the newest version with a date, as the command in `README.md` names it. `--check` fails when the line is not current, is missing, stands twice, or another line of the page holds `git clone`. So the pull request of a release moves the page with the README when it runs `generate.py`.

## 0.9 (2026-11-19)

<!-- generated:count -->
Ratchet 0.9, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 23 experimental rules, under a cap of 25: 11 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

No rule is added, changed or removed in this version. It changes how Ratchet is released, by the decision `D-2026-11-19-batched-releases`: changes are collected under the first entry of the changelog, headed `(unreleased)`, and released together by a pull request that gives the entry its date. The list of sources moves out of `ratchet.json`, so that a pin that moves needs no new version. It also adds `checks/init.py`, which starts a project with one command, rewrites the README, and fixes the tripwire's exception for a directory from `mktemp -d` on macOS.

Changes of form:

- `date` is gone from `ratchet.json`. The date of a version is in the heading of its entry in `CHANGELOG.md`, and nowhere else.
- `sources` is gone from `ratchet.json`. The list is in `sources.json`, an object with the one field `sources`, read as strictly as every data file. `checks/released_text.py` does not compare it with a tag, so it is not part of what is released. A rule cites its sources by their names in `sources.json`, and `checks/generate.py` fails on a name that is not there. A project that only runs the checks in `.ratchet` has nothing to do: see [UPGRADING.md](UPGRADING.md).

Changed:

- `CHANGELOG.md`: the first entry may be headed `## <version> (unreleased)`. While it is, the release workflow publishes nothing for that version, on a push and on its schedule, and `ratchet.json` may name that version and change. An entry with a date is released by the next push to `main`, and from its tag on it is frozen as before. An unreleased heading anywhere but first, twice, of another form, or for a version that has a tag, fails. See [checks/README.md](checks/README.md#releasepy).
- `checks/release.py` reads, with git, the changelog at each commit on `main` beside `ratchet.json`. A version must be released once a commit on `main` names it with an entry that has a date, also when a later commit heads it `(unreleased)` again: that commit's run fails and names the commit that dated it. A version that `main` only named as unreleased needs nothing.
- `checks/generate.py`: `RATCHET.md` says that the version is not yet released, and the command in `README.md` that fetches Ratchet names the newest version with a date. It is read as one exact line in a code block marked `sh`, and no other line of `README.md` may run `git clone`. The pull request of a release moves it, so for the minutes the release run takes after the merge, and until a rerun if that run is cancelled, it names a tag that does not exist yet. The daily release run is red while it lasts.
- `checks/upgrade.py` says when a field at the top of `ratchet.json` is gone, as it says when one is new.
- `checks/watch_sources.py` and its workflow read `sources.json`.
- The release of a version is a pull request that replaces `(unreleased)` with the date and moves the tag that `README.md` fetches. `checks/generate.py` writes the rest, and `--check` names what is left.
- `README.md` is rewritten: the problem first, then what Ratchet does, the evidence from this repo with a link for each claim, the honest limits, and "Start here" with `init.py`. It fetches 0.9, the first version with `init.py`.

Added:

- `checks/init.py`: one command that starts a project, run from the root of its repo with Ratchet in `.ratchet`. It writes `AGENTS.md` and `register.json` from the templates with the project's name, the generated `REGISTER.md`, and `.github/workflows/ratchet.yml` pinned to the commit of the Ratchet checkout it runs from, and adds `/.ratchet/` to `.gitignore` unless the last line there on `.ratchet` is exactly `.ratchet/` or `/.ratchet/` with no negation after it. It never overwrites a file: a file that exists with other content is skipped and named, and the run exits 1. A file is linked into place whole or not written at all, a `.gitignore` edited meanwhile is left as it is, and it runs only from the root of a git repo, read from `.git` without running git there, and from a Ratchet that is a git checkout of its own with no changes that are not committed. `--check` writes nothing. A second run changes nothing. It ends by running `check_register.py`. See [checks/README.md](checks/README.md#initpy).

Fixed, from the review of PR #50:

- `checks/generate.py` fails when the entries of the changelog do not stand newest first, each version higher than the one after it, and the command in `README.md` that fetches Ratchet names the highest version with a date. Before, it named the first entry with a date, so a changelog with an older entry moved up let a stale pin pass.
- `checks/README.md` says that a green run of `release.py` confirms a tag and a release for every version ever dated on `main`, not every version `main` named, and the tag of the version in the checkout only when its entry has a date, as the review of PR #54 asked.

Fixed, from the sandbox trial in issue #49 (PR #51 and PR #55):

- `checks/tripwire.py`: on macOS, the exception for deleting one's own directory from `mktemp -d` looks where `mktemp -d` writes, the per-user temporary directory that the system gives, and no longer follows `TMPDIR`. Before, a session whose `TMPDIR` was elsewhere had the deletion of a real directory from `mktemp -d` denied, and a directory of that form made in `TMPDIR` let through. When the system gives no absolute path of an existing directory, that root is not trusted at all. `/tmp` stays the second root, and Linux is unchanged. See [checks/README.md](checks/README.md#tripwirepy).
- The tests of the tripwire write nothing to `/tmp`: a directory from `mktemp -d` stands in for it. So the suite passes in a sandbox that refuses writes to `/tmp`, as well as outside one. The hook behaves as before.

## 0.8 (2026-11-19)

<!-- generated:count -->
Ratchet 0.8, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 23 experimental rules, under a cap of 25: 11 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

No rule is added, changed or removed in this version. The form of `ratchet.json` does not change. Two pins in its list `sources` move. `checks/released_text.py` fails when `ratchet.json` names a released version and is not as it stood at that tag, so the move is a version of its own.

Changed:

- `sources`: `google/elephant-goldfish-model` is pinned at `70406c4d22cc7ea8299637c2c5b44625c48b3f08`, in place of `403d8881d62022490637d740657b33f01e321ea8`, and `pstack` at `35a90942a7f02e1ebbc2443643179815f2147954`, in place of `bf0c7cd80abdbf7fe47b634978a7d1b4071f71a7`. These are the heads that the source watch named in #40 and #41. Each new commit is ahead of the old pin, with none behind. The change between the two was read in the maintainer's notes and reviewed by a model from another family: nothing that a rule relies on changed. The proposals that came from that reading are issues of their own, #46 and #47, and change nothing here.
- The table of sources in `RATCHET.md` shows the new pins.

## 0.7 (2026-11-19)

<!-- generated:count -->
Ratchet 0.7, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 23 experimental rules, under a cap of 25: 11 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

One rule is added in this version, and none is changed or removed. The form of `ratchet.json` does not change. The rule comes from issue #23 and the decision `D-2026-11-17-knowledge-and-modes`, item 1. By the decision `D-2026-11-19-locks-not-parsing`, its hook is a tripwire and not a lock, and the locks sit with GitHub and the sandbox. By the decision `D-2026-11-19-tag-ruleset-scope`, the tag ruleset locks moving and deleting a tag, and not creating one.

Added:

- `ratchet.irreversible-waits`, experimental, in a new part of `CONTROL-ROOM.md`, "What cannot be undone": an agent goes ahead with a step that can be undone, and a step that cannot waits for an approval from the owner that names the step and the exact command. The five steps are a force push, creating or deleting a tag, creating or changing a release, deleting outside the working tree, and changing the repository's settings. The part says where each step is locked and where it is not.
- `checks/tripwire.py`, its reference check: a `PreToolUse` hook for Claude Code that denies the usual spellings of the five steps when no approval names them, and any write by an agent to the approvals file. It is a tripwire, not a lock: it claims the cases that [checks/README.md](checks/README.md#tripwirepy) lists and no others, and another spelling gets past it. It never exits other than 0 or 2. The templates `claude-settings.json` and `ratchet-approvals.json` wire it into a project, and this repo runs it from `.claude/settings.json`.
- `templates/tag-ruleset.json`: a ruleset for every tag, with the rules `deletion`, `update` and `non_fast_forward` and the repository admin role as the only bypass actor, for the owner to apply. It leaves creating a tag open, so the release workflow tags as before. See [checks/README.md](checks/README.md#the-tag-ruleset).

Changed:

- `checks/README.md` describes the rehearsal of the release of 0.7 and the upgrade fixtures from 0.3 to 0.6, which it had left at 0.5 and at 0.3 and 0.4.

## 0.6 (2026-11-19)

<!-- generated:count -->
Ratchet 0.6, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 22 experimental rules, under a cap of 25: 10 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

One rule is added in this version, and none is changed or removed. The form of `ratchet.json` does not change. The rule comes from the decision `D-2026-11-17-knowledge-and-modes`, item 4, and is one rule rather than three by the decision `D-2026-11-19-locks-not-parsing`, item 5.

Added:

- `ratchet.phases`, experimental and text only, in a new part of `CONTROL-ROOM.md`, "The phases": a work package is in one phase at a time, explore, build and run, and for each the rule says what an agent may do in it and what ends it. Explore changes nothing that others rely on, build works on one approved work package and merges on green checks and a passed review, and run operates what is merged and sends a fix back to build.

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
