# D-2026-11-22-owner-reads-outside-gates: the owner reads a change to a gate or a reviewer outside the repo, and Astra and Fable review while Gemini 4 Neon is out

- Date: 2026-11-22
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Background. Step 8 of the migration in [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md) merged `ratchet.one-approver` and `ratchet.checks-owner-read` into `ratchet.owner-paths` (#122). The old `ratchet.checks-owner-read` said: "Checks, gates and automated reviewers change only after the owner has read the change." `ratchet.owner-paths` says that a change to the owner's paths merges only after the owner has read it and approved its head, so it covers only what is merged in the repo. A gate or an automated reviewer that is changed outside the repo, such as a ruleset of the host or the brief or the model of an automated reviewer, fell out of the rule, and the decision's table of losses has no row for it. Claude Fable found this in its review of step 8. Gemini 4 Neon, which [D-2026-11-22-standing-approval](D-2026-11-22-standing-approval.md), choice 3, names beside Codex for steps 5 to 11, had no quota left at the time.

The question, asked by the control room on 2026-11-22. Original, in Swedish:

> 1. **Fables fråga om kärnan.** Den gamla regeln sa att kontroller, spärrar och automatiska granskare bara ändras efter att du har läst ändringen. Den nya gäller bara det som slås ihop i repot. Därmed faller till exempel uppdraget jag ger granskarna bort, och likaså vilken modell som granskar. **Mitt råd: lägg tillbaka det** som en mening i regeln om ägarens filer. Det skyddar mot att jag i tysthet gör granskningen svagare. Det är ny text i den frysta kärnan, så det kräver ditt ja.
> 2. **Granskare medan Neon är borta.** **Mitt råd:** Astra och Fable granskar båda tillsammans med Codex på stegen med kontrollkod (9a och 9b). Astra granskar också kärnstegen 10 och 11, eftersom Astra hittade ett fel i kärnan som Codex missade.

Translation:

> 1. **Fable's question about the core.** The old rule said that checks, gates and automated reviewers change only after you have read the change. The new one applies only to what is merged in the repo. So, for example, the brief I give the reviewers falls out, and likewise which model reviews. **My recommendation: put it back** as a sentence in the rule on the owner's files. It protects against my quietly making the review weaker. It is new text in the frozen core, so it needs your yes.
> 2. **Reviewers while Neon is away.** **My recommendation:** Astra and Fable both review together with Codex on the steps with check code (9a and 9b). Astra also reviews the core steps 10 and 11, since Astra found an error in the core that Codex missed.

"Neon" is Gemini 4 Neon, "Astra" is GPT-6 Astra and "Fable" is Claude Fable. "The rule on the owner's files" is `ratchet.owner-paths`.

## Answer

Original, in Swedish:

> Ja

Translation:

> Yes

## What follows

- **1: one sentence in the core.** `ratchet.owner-paths` ends with: "Checks, gates and automated reviewers that act outside the repo, such as the host's rules or the brief and model of an automated reviewer, change only after the owner has read the change." This is a departure from the frozen wording of the core ([RATCHET.md](../RATCHET.md#the-core-is-frozen)), authorized here as [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md) authorized its seven clauses. It restores what `ratchet.checks-owner-read` covered, so step 8 loses nothing that its table of losses does not list.
- The ratchet of `ratchet.owner-paths` stays a check for what is merged in the repo, and says that it does not see whether the owner read a change to a gate or a reviewer outside the repo. That part is text only: the host's review requirement sees only the files of a pull request.
- This repo's register takes the new entry of `ratchet.owner-paths`, still "text only for now". Its `where` names the gates and automated reviewers that act outside the repo as missing on its way to "built".
- **2: reviewers while Gemini 4 Neon's quota is out.** In place of Gemini 4 Neon, GPT-6 Astra and Claude Fable both review beside Codex the steps that change a check's code, 9a and 9b, at the same head, and GPT-6 Astra also reviews the core steps 10 and 11. Everything else in choice 3 of [D-2026-11-22-standing-approval](D-2026-11-22-standing-approval.md) stands: the approval waits for every reviewer named for a step to pass its head, and the steps that only move text are reviewed by Codex alone. The review from another model family that [AGENTS.md](../AGENTS.md) requires is unchanged.

Proposals (P), which the maintainer did not say in words:

1. P: Claude Fable is of the control room's own model family, so its review is in addition to, and never in place of, the review from another model family.
2. P: When Gemini 4 Neon's quota is back, it takes up the steps of choice 3 of [D-2026-11-22-standing-approval](D-2026-11-22-standing-approval.md) that are not yet reviewed, and the steps already passed by Codex, GPT-6 Astra and Claude Fable are not reviewed again.
