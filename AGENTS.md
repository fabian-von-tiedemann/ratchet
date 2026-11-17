# Working rules for Ratchet

## Purpose

Ratchet is a set of working rules and templates for long-lived code projects built by AI agents. Every rule names the check that enforces it, or says "text only" and why. This repo holds the rules, the templates and the reference checks.

## Read first

1. This file.
2. The register, [REGISTER.md](REGISTER.md). It lists every rule in force in this repo and takes precedence over all other text here, including this file. It is generated from [register.json](register.json).
3. The handover, [HANDOVER.md](HANDOVER.md).
4. Your issue.

The words used here are defined in [GLOSSARY.md](GLOSSARY.md).

## What this repo is and is not doing now

- The core, the six parts of [RATCHET.md](RATCHET.md), is frozen: no rule is added to it or removed from it without the maintainer's decision. A new rule is a proposal (P) for the maintainer and starts as experimental.
- The work now is turning rules that are text only into reference checks, one at a time, each with a fixture it fails on.
- The maintainer approves decisions, tags and releases. An agent proposes and opens a PR. It does not tag, release or change the repository's settings.

## How to change a rule

1. Edit [ratchet.json](ratchet.json). The rule tables are generated from it.
2. Run `python3 checks/generate.py`. It rewrites the tables, the count, `templates/register.json`, `REGISTER.md` and the registers under `checks/fixtures/register/`.
3. If a rule that [register.json](register.json) adopts changed, paste the new entry. `python3 checks/generate.py --entries` followed by the key prints it.
4. Add the change to [CHANGELOG.md](CHANGELOG.md).
5. Run the commands under "Before you say it is done".

## How to change this repo's register

Edit [register.json](register.json) and run `python3 checks/generate.py`. `REGISTER.md` is generated and never edited.

## How to change a check

A change to `checks/`, `.github/`, `ratchet.json`, `register.json` or `decisions/` is read by the maintainer before it is merged (`ratchet.checks-owner-read`). The PR states what the check claims and against which threat, with the list of cases, as [checks/README.md](checks/README.md) does. A check may be tightened. A PR that loosens one cites the decision that allows it.

A check reads a data file, read strictly. It fails on what it does not know, and it never looks for rules in free Markdown ([D-2026-11-16-strict-forms](decisions/D-2026-11-16-strict-forms.md)). A value from a data file is text, never Markdown, and is written into a generated file as text. Its characters come from one fixed list, and every file a check reads is strict UTF-8 ([D-2026-11-17-latin-strict-utf8](decisions/D-2026-11-17-latin-strict-utf8.md)). Every way that has been found to hide something from a check is a copy under `checks/fixtures/` that must fail.

Checks use Python's standard library only.

## Before you say it is done

```sh
python3 checks/generate.py --check
python3 checks/check_register.py register.json --markdown REGISTER.md
python3 -m unittest discover -s checks
```

Show the commands and their results in the PR (`ratchet.evidence-before-done`).

## Writing

- English, American spelling, the terms in the glossary.
- Nothing here identifies a project that uses Ratchet, its company, its vendors or its incidents.
- Label what you write: decision (D), proposal (P), observation (O) or question (Q). A decision is a file in `decisions/`, written with [templates/DECISION.md](templates/DECISION.md).

## The main branch

`main` takes changes only through pull requests. A pull request needs the job `checks` green and the approval of the code owner, who is the maintainer ([.github/CODEOWNERS](.github/CODEOWNERS)). Administrators are exempt from the protection, so that the one maintainer can merge their own changes ([D-2026-11-16-code-owner](decisions/D-2026-11-16-code-owner.md)).

Agents contribute through a machine account of their own with write access. It opens pull requests. It does not approve or merge one. That is an instruction and not a lock: an account with write access is able to merge once the requirements are met. What the protection makes sure of is that the code owner has approved the latest change. An approval from the agents' account does not count as the code owner's, and a new push dismisses an approval already given.

The account exists and has the role Write. The protection is the ruleset that guards `main`, which requires the code owner's review and the job `checks` and refuses force pushes and deletion. Both were read back on 2026-11-17. They have not yet been tried with a real pull request. Until they are, [REGISTER.md](REGISTER.md) lists the rules that lean on them as "text only for now", and [HANDOVER.md](HANDOVER.md) names the steps that make them "built".

A published tag is never moved ([D-2026-11-16-tags-stay](decisions/D-2026-11-16-tags-stay.md)).
