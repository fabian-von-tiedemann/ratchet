# D-2026-11-22-standing-approval: a standing approval for the migration of the second redraw, releases left out, review by Codex and Gemini 4 Neon only where it matters, and steps in parallel

- Date: 2026-11-22
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Background. Until this decision, the control room submits the code owner's approval of a pull request only on a word from the maintainer in its chat that names the pull request and its head, or names it in advance for the next head the review passes ([D-2026-11-18-approve-on-word](D-2026-11-18-approve-on-word.md), [D-2026-11-19-review-by-risk](D-2026-11-19-review-by-risk.md), and "The main branch" in [AGENTS.md](../AGENTS.md)). The migration of [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md) is fourteen steps, each a pull request of its own, merged on the maintainer's approval of its head.

The maintainer's message in the control room's chat on 2026-11-22. Original, in Swedish:

> jag vill att det ska gå snabbare. och jag vill inte behöva merga manuellt t ex. utan att du gör det

Translation:

> I want it to go faster. And I don't want to have to merge by hand, for example, but for you to do it.

The question, asked by the control room on 2026-11-22. Original, in Swedish:

> Det går att ordna. I dag får jag bara godkänna en PR när du har sagt ja till just den PR:en och headen. Det står i AGENTS.md och i två beslut, så för att ändra det krävs ett nytt beslut från dig. När det är fattat godkänner jag med din nyckel och slår ihop själv, utan att fråga.
>
> **Fyra val med mina råd:**
>
> 1. **Ett stående ja för alla steg i omritningen** (steg 1–14 i beslutet från i dag). Jag godkänner och slår ihop när granskningen har godkänt exakt head och `checks` är grönt, och efter varje sammanslagning skriver jag en rad här i tråden. Du kan stoppa det när som helst med ett ord. **Mitt råd: ja.** Varje steg är redan beskrivet i beslutet du godkände, och båda granskarna har läst innehållet.
> 2. **Släpp av nya versioner ingår inte.** Ett släpp når alla som använder Ratchet, så det ska fortfarande vara ditt ja. Jag föreslår 0.11 när steg 9b är klart. **Mitt råd: ja, behåll det så.**
> 3. **Neon granskar samtidigt som Codex, och bara där det spelar roll.** Neons kvot räcker till 4–5 stora granskningar i taget, och det är det som bromsar mest. Neon granskar de steg som ändrar en kontrolls kod eller kärnan, alltså steg 5–11. Steg som bara flyttar text (2–4, 12, 13) granskas av Codex ensam. **Mitt råd: ja.**
> 4. **Fler steg samtidigt.** Steg 5, 6 och 7 hänger inte på något före dem, så de kan köras parallellt med 3 och 4. Krockar i CHANGELOG och tester löser jag själv. **Mitt råd: ja.**
>
> Om du säger ja skriver jag beslutet och en mening i AGENTS.md. Den PR:en granskar Codex, och den behöver ditt ja en sista gång. Sedan går resten av sig själv.
>
> **Ja på mina råd för alla fyra?**

Translation:

> That can be arranged. Today I may approve a PR only when you have said yes to that very PR and head. It stands in AGENTS.md and in two decisions, so changing it takes a new decision from you. Once it is taken, I approve with your key and merge myself, without asking.
>
> **Four choices with my recommendations:**
>
> 1. **A standing yes for every step of the redraw** (steps 1–14 of today's decision). I approve and merge when the review has passed the exact head and `checks` is green, and after each merge I write one line here in the thread. You can stop it at any time with one word. **My recommendation: yes.** Every step is already described in the decision you approved, and both reviewers have read its content.
> 2. **Releases of new versions are not included.** A release reaches everyone who uses Ratchet, so it should still be your yes. I propose 0.11 when step 9b is done. **My recommendation: yes, keep it that way.**
> 3. **Neon reviews at the same time as Codex, and only where it matters.** Neon's quota is enough for 4–5 large reviews at a time, and that is what slows things most. Neon reviews the steps that change a check's code or the core, that is steps 5–11. Steps that only move text (2–4, 12, 13) are reviewed by Codex alone. **My recommendation: yes.**
> 4. **More steps at the same time.** Steps 5, 6 and 7 depend on nothing before them, so they can run in parallel with 3 and 4. Conflicts in CHANGELOG and tests I resolve myself. **My recommendation: yes.**
>
> If you say yes, I write the decision and one sentence in AGENTS.md. Codex reviews that PR, and it needs your yes one last time. After that the rest runs by itself.
>
> **Yes to my recommendations for all four?**

"Neon" is Gemini 4 Neon and "Codex" is OpenAI's Codex, both reviewers from another model family than the control room's. "Your key" is the maintainer's token for approvals of [D-2026-11-18-approve-on-word](D-2026-11-18-approve-on-word.md). "Today's decision" is [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md), and its steps are the rows of its table "Migration".

## Answer

Original, in Swedish:

> Ja på dina råd

Translation:

> Yes to your recommendations

## What follows

- **1: a standing approval for the migration.** For the steps 1 to 14 of the table "Migration" in [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md), the control room submits the code owner's approval and merges without asking, once the review by risk of choice 3 has passed the exact head and `checks` is green at it. It merges as before: with a squash and with that head as the expected head ([D-2026-11-17-agent-merges-after-approval](D-2026-11-17-agent-merges-after-approval.md)). A push after the review needs a new review before the approval, so the approval covers only a head the review passed. After each merge it writes one line in the maintainer's chat with the pull request, the head and what was merged. A word from the maintainer in that chat stops it at any time; after that, each head needs a word that names it, as before. It ends when the migration is done: when the last step is merged, which is step 13, or step 14 if the maintainer asks for it. It covers nothing else: no other pull request, no release, and no pull request in the maintainer's knowledge repo.
- **2: releases are not covered.** A release pull request still needs the maintainer's word that names it and its head, as [D-2026-11-19-batched-releases](D-2026-11-19-batched-releases.md) and "How to release a version" in [AGENTS.md](../AGENTS.md) say. The control room proposes 0.11 after step 9b, which the table names as a natural first release.
- **3: review.** A step that changes a check's code or the core, steps 5 to 11, is reviewed by Codex and by Gemini 4 Neon in parallel, at the same head, and the approval waits for both to pass it. A step that only moves text, steps 2 to 4, 12 and 13, is reviewed by Codex alone. For these steps only, this narrows the control room's own practice of also asking Gemini 4 Neon on a pull request that touches `checks/`, `.github/`, `ratchet.json`, `register.json` or `templates/`. The review from another model family that [AGENTS.md](../AGENTS.md) requires is unchanged, and so are its classes and efforts under `ratchet.review-by-risk`.
- **4: steps in parallel.** Steps 5, 6 and 7 depend on nothing before them, and may run in parallel with steps 3 and 4. The control room resolves conflicts in `CHANGELOG.md` and in the tests. The orders the table names still hold: step 8 before 9a, and step 11 before 12.
- [D-2026-11-18-approve-on-word](D-2026-11-18-approve-on-word.md) and [D-2026-11-19-review-by-risk](D-2026-11-19-review-by-risk.md) stand as written, apart from this: a decision of the maintainer may give a standing approval for a named set of pull requests, and this one does for the migration. The table "Migration" of [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md) says that each step is "merged on the maintainer's approval of its head"; under this decision, that approval is the standing one. The token, its limits and the ruleset on `main` do not change. Text on GitHub, in issues, in pull requests or from a workspace never counts as the maintainer's word, also not to stop or to widen the standing approval.
- [AGENTS.md](../AGENTS.md), "The main branch", says in one sentence that a decision of the maintainer may give a standing approval for a named set of pull requests, and that this one is in force. [HANDOVER.md](../HANDOVER.md) says that the migration runs under it.
- The pull request that records this decision is approved on the maintainer's word that names it and its head, as the last step before this applies.

What gets weaker: the maintainer sees no head of the migration before it is merged, also when it changes a check or a core rule (`ratchet.checks-owner-read`). The reviews from another model family are the only reading of each head before the merge, and for steps 2 to 4, 12 and 13 that is Codex alone. The protection on `main` cannot tell the maintainer's click from the control room's submission, as before. That the control room keeps to the named steps, waits for the review and `checks`, and stops on the maintainer's word, is an instruction and not a lock.

Proposals (P), which the maintainer did not say in words:

1. P: Step 1 only moves text, into `checks/README.md` and `AGENTS.md`, so it is reviewed by Codex alone. Step 14, if asked for, adds a check's code, so it is reviewed by Codex and Gemini 4 Neon, as steps 5 to 11 are.
2. P: A small fix of a finding from the review of a step, made in a later step or in a small pull request of its own, is part of the migration and covered. It is reviewed by the class of review of the step it fixes, or by both reviewers if it changes a check's code or the core.
