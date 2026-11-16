# Working rules for <project>

## Purpose

<One to three sentences: what the project is for and for whom.>

## Core from Ratchet

The rows below are a verbatim copy of the core of Ratchet, version <x.y>. Do not edit them by hand. A new version is copied in its own PR.

<Paste the tables from RATCHET.md, or the keys the project uses.>

## The project's own rules

<Phase, mandates for trials, cost caps, glossary and domain checks.>

## Read first

1. This file.
2. The register.
3. The control room's handbook.
4. The latest handover in the status issue.
5. Your issue.

## Skills in `.claude/skills/`

Before you use a skill in `.claude/skills/<name>/`, read `SOURCE.md` in the same directory and follow it. `SOURCE.md` and the register take precedence over the skill's `SKILL.md`, which is a verbatim copy of the source. A skill applies only where and for as long as `SOURCE.md` says.

When they are used:

| Situation | Skill |
|---|---|
| Before a new project or a larger package is planned | `/grilling`, only in the control room's thread |
| When a package is split into issues | `/to-tickets`, control room only |
| When code is built or a fault is fixed | `tdd` |
| When a fault is debugged | `diagnosing-bugs` |
| When a review verdict is received | `receiving-code-review` |
| Before anything is claimed to be done | `verification-before-completion` |
| After two failed rounds or two failed trials with the same kind of fault | `/principle-attack-the-premise` |
