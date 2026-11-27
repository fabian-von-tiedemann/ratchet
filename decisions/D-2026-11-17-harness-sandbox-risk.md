# D-2026-11-17-harness-sandbox-risk: deny rules, a sandbox trial, review by risk, and an early audit of instruction files

<!-- generated:status -->
Status: amended by D-2026-11-19-locks-not-parsing (the deny rules become a tripwire)
<!-- /generated:status -->

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-17-knowledge-and-modes (the instruction files are reviewed now, not at the next release)
- Ends: none

## Question

Five choices put to the maintainer together, each with a recommendation. They came after the analysis of a primary source: a talk by a member of the Claude Code team on how its practices changed as agents ran longer without a person in the loop.

Original, in Swedish:

> 1. **#23 byggs som spärrregler (`deny`) i Claude Code, sparade i repot så att de följer med.** Varje steg som stoppas får ett testfall som måste vägras, och alla hooks Ratchet beskriver får regeln om kod 2. **Råd: ja.**
> 2. **Ett försök med sandlåda för arbetstrådarna på minin.** Skalkommandon får bara skriva i arbetskatalogen och bara nå godkända värdar. Vi ser vad som går sönder, till exempel `gh` som behöver sin token. **Råd: ja.** I dag kan vilket testskript som helst som körs som `personlig` läsa allt den användaren kan läsa.
> 3. **Granskning efter risk blir en regel i Ratchet.** Den slår ihop det vi redan gör på två ställen. **Råd: ja,** men efter regelbudgeten, eftersom den räknas mot taket.
> 4. **Granska instruktionsfilerna nu, i stället för vid nästa släpp.** Det gäller `AGENTS.md`, `~/.claude/CLAUDE.md` och mina arbetsbeskrivningar. Absoluta ord som "aldrig" och "VIKTIGT" tas bort, och bara det som inte syns i koden står kvar. **Råd: ja.** Föredraget säger att sådana ord nu gör resultaten sämre, och vi har många av dem.
> 5. **Kedjan tar bara ljud som standard och plockar bilder bara när du ber om det.** **Råd: ja.** Det blir färre förfrågningar till YouTube och mindre risk för spärr.

Translation into English:

> 1. **#23 is built as deny rules in Claude Code, saved in the repo so that they travel with it.** Each step that is stopped gets a test case that must be refused, and every hook Ratchet describes gets the rule about exit code 2. **Advice: yes.**
> 2. **A trial of a sandbox for the worker threads on the mini.** Shell commands may write only in the working directory and reach only approved hosts. We see what breaks, for example `gh`, which needs its token. **Advice: yes.** Today any test script run as `personlig` can read everything that user can read.
> 3. **Review by risk becomes a rule in Ratchet.** It merges what we already do in two places. **Advice: yes,** but after the rule budget, because it counts against the cap.
> 4. **Review the instruction files now, instead of at the next release.** That covers `AGENTS.md`, `~/.claude/CLAUDE.md` and my work briefs. Absolute words like "never" and "IMPORTANT" are removed, and only what cannot be seen in the code stays. **Advice: yes.** The talk says such words now make results worse, and we have many of them.
> 5. **The pipeline takes only audio by default and pulls frames only when you ask.** **Advice: yes.** That means fewer requests to YouTube and less risk of being blocked.

## Answer

Original, in Swedish:

> går på dina reks

Translation into English:

> going with your recommendations

## What follows

- Issue #23 is built as deny rules for the agent's harness, committed in the repo. Each denied step has a test case that must be refused. Every hook Ratchet describes that sends work back uses exit code 2.
- A sandbox for shell commands in the worker threads on the mini is tried as an experiment, and what breaks is written down. It is a trial, not a rule.
- Review by risk becomes a rule in Ratchet after the rule budget is in place, and it counts against the cap.
- The instruction files are reviewed now. Absolute words are removed, and only what cannot be seen in the code stays.
- The video pipeline fetches audio only by default. It pulls frames only when the maintainer asks.

Proposal (P), not decided by the maintainer: the review of the instruction files starts with `AGENTS.md` in this repo, in a PR of its own. Changes to `~/.claude/CLAUDE.md`, which lives outside the repo, are shown to the maintainer before they are written.
