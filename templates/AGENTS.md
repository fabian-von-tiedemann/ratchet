# Working rules for <project>

## Purpose

<One to three sentences: what the project is for and for whom.>

## Read first

1. This file.
2. The register, [REGISTER.md](REGISTER.md). It lists every rule in force and takes precedence over all other text in the repo, including this file.
3. The latest handover in the status issue (#<n>).
4. Your issue.

The control room also reads its handbook, after the register.

## What this project is and is not doing now

<The current phase, what is in scope, and what needs the owner's approval first, such as experiments that cost money.>

## Skills

Skills copied from other repos live in `<skills directory, for example .claude/skills/>`. Before you use a skill in `<skills directory>/<name>/`, read `SOURCE.md` in the same directory and follow it. `SOURCE.md` and the register take precedence over the skill's `SKILL.md`, which is a verbatim copy of the source. A skill applies only where `SOURCE.md` says, and for as long as it says.

When each skill is used. Delete the rows for skills the project has not copied.

| Situation | Skill | Source |
|---|---|---|
| Before a new project or a large work package is planned (control room only) | `grilling` | mattpocock/skills |
| When a work package is split into issues (control room only) | `to-tickets` | mattpocock/skills |
| When code is built or a bug is fixed | `tdd` | mattpocock/skills |
| When a bug is diagnosed | `diagnosing-bugs` | mattpocock/skills |
| When a review verdict is received | `receiving-code-review` | obra/superpowers |
| Before anything is claimed to be done | `verification-before-completion` | obra/superpowers |
| After two failed rounds or two failed experiments with the same kind of failure | `principle-attack-the-premise` | pstack |
