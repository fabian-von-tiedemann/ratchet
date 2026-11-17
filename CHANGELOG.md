# Changelog

## 0.3 (2026-11-16)

<!-- generated:count -->
Ratchet 0.3, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 21 experimental rules: 10 name a check and 11 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
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
