# D-2026-11-23-partial-adoption-form: adoption in part is a change of form, and the count toward 1.0 starts from 0.12

- Date: 2026-11-23
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Background. Pull request #133 lets a row adopted by reference be adopted in part: its `where` is exactly `Not stated here: <clause>; <clause>.`, the clauses that the project's own wording does not state. No field is added to `register.json`. But a row of a rule that is text only took no `where` in 0.11, and `checks/check_register.py` of 0.11 refuses one, while that of 0.12 accepts the phrase there. The criterion of 1.0 "The form has been unchanged for three tags and at least 30 days" ([SELF-IMPROVEMENT.md](../SELF-IMPROVEMENT.md#when-10-comes)) counts from the last change of form. The question came from a project that adopted 0.11, which has three rules whose wording nearly matches Ratchet's, one of them `ratchet.evidence-before-done`, a rule that is text only.

The question, asked by the control room on 2026-11-23. Original, in Swedish:

> **Både Codex och Astra anser nu att det här är en formändring.** Den gamla kontrollen godtar inte fritext på en regel som bara är text, och den nya gör det. Därför bör klockan mot 1.0 börja om vid 0.12. Det behöver ditt beslut:
> 1. **Räkna det som en formändring, och klockan börjar om vid 0.12** (mitt råd). 1.0 flyttas ungefär en vecka, från omkring jul till omkring nyår. I gengäld kan appen ta in de tre regler som nästan stämmer, och då blir det omkring 4 av 10 i stället för 1. Det är det som gör Ratchet värt något för ett moget projekt.
> 2. **Ingen formändring.** Frasen får bara användas på regler som har en kontroll. Klockan påverkas inte, men regeln om bevis före "klart", en av de tre i appen, kan då inte tas in delvis.

Translation:

> **Both Codex and Astra now hold that this is a change of form.** The old check does not accept free text on a rule that is text only, and the new one does. So the clock toward 1.0 should start again at 0.12. It needs your decision:
> 1. **Count it as a change of form, and the clock starts again at 0.12** (my recommendation). 1.0 moves about a week, from around Christmas to around New Year. In return the app can take in the three rules that nearly match, and then it becomes about 4 of 10 instead of 1. That is what makes Ratchet worth something for a mature project.
> 2. **No change of form.** The phrase may be used only on rules that have a check. The clock is not affected, but the rule of evidence before "done", one of the three in the app, then cannot be adopted in part.

"Codex" and "Astra" are the two reviewers from another model family than the control room's. "The app" is the project that adopted 0.11, named above.

## Answer

The maintainer answered "ja" on 2026-11-23, to a later message of the control room that recommended yes to all three choices then open, this one among them. Original, in Swedish:

> ja

Translation:

> yes

## What follows

- Choice 1 holds: accepting a `where` on a row by reference of a text-only rule, only as the exact phrase of a row adopted in part, is a change of form of `register.json` in 0.12.
- The entry of 0.12 in [CHANGELOG.md](../CHANGELOG.md) lists it under "Changes of form". `checks/upgrade.py` tells a register that moves to 0.12 or later of it, as a change of form of the register and not as a step, since a register of 0.11 stays valid.
- [SELF-IMPROVEMENT.md](../SELF-IMPROVEMENT.md#when-10-comes) says, in the row of the criterion "The form has been unchanged for three tags and at least 30 days", that the form changed in 0.12, so the count starts from 0.12.
- The 0.11 entry of the changelog, which calls 0.11 the last change of form of `register.json` before the count toward 1.0, is released text and stays as it is. This decision is the later change.
- Nothing else changes: the phrase stays one exact form, the row is never `built`, and the phrase stands on no copied row and no rule of the project's own.
