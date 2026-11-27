# D-2026-11-22-owner-reads-outside-gates: the owner reads a change to a check, a gate or a reviewer and to a setting outside the repo it depends on, and Astra and Fable review while Gemini 4 Neon is out

- Date: 2026-11-22
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-22-second-redraw (step 8 keeps what ratchet.checks-owner-read covered); D-2026-11-22-standing-approval (choice 3, the reviewers while Gemini 4 Neon is out)
- Ends: none

The mark `[…]` shows where this file leaves out part of a message.

## Question

Background. Step 8 of the migration in [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md) merged `ratchet.one-approver` and `ratchet.checks-owner-read` into `ratchet.owner-paths` (#122). The old `ratchet.checks-owner-read` said: "Checks, gates and automated reviewers change only after the owner has read the change." `ratchet.owner-paths` says that a change to the owner's paths merges only after the owner has read it and approved its head, so it covers only what is merged in the repo. A gate or an automated reviewer that is changed outside the repo, such as a ruleset of the host or the brief or the model of an automated reviewer, fell out of the rule, and the decision's table of losses has no row for it. Claude Fable found this in its review of step 8. Gemini 4 Neon, which [D-2026-11-22-standing-approval](D-2026-11-22-standing-approval.md), choice 3, names beside Codex for steps 5 to 11, had no quota left at the time.

The first question, asked by the control room on 2026-11-22. Original, in Swedish:

> 1. **Fables fråga om kärnan.** Den gamla regeln sa att kontroller, spärrar och automatiska granskare bara ändras efter att du har läst ändringen. Den nya gäller bara det som slås ihop i repot. Därmed faller till exempel uppdraget jag ger granskarna bort, och likaså vilken modell som granskar. **Mitt råd: lägg tillbaka det** som en mening i regeln om ägarens filer. Det skyddar mot att jag i tysthet gör granskningen svagare. Det är ny text i den frysta kärnan, så det kräver ditt ja.
> 2. **Granskare medan Neon är borta.** **Mitt råd:** Astra och Fable granskar båda tillsammans med Codex på stegen med kontrollkod (9a och 9b). Astra granskar också kärnstegen 10 och 11, eftersom Astra hittade ett fel i kärnan som Codex missade.

Translation:

> 1. **Fable's question about the core.** The old rule said that checks, gates and automated reviewers change only after you have read the change. The new one applies only to what is merged in the repo. So, for example, the brief I give the reviewers falls out, and likewise which model reviews. **My recommendation: put it back** as a sentence in the rule on the owner's files. It protects against my quietly making the review weaker. It is new text in the frozen core, so it needs your yes.
> 2. **Reviewers while Neon is away.** **My recommendation:** Astra and Fable both review together with Codex on the steps with check code (9a and 9b). Astra also reviews the core steps 10 and 11, since Astra found an error in the core that Codex missed.

"Neon" is Gemini 4 Neon, "Astra" is GPT-6 Astra and "Fable" is Claude Fable. "The rule on the owner's files" is `ratchet.owner-paths`.

The first answer put this sentence at the end of `ratchet.owner-paths`: "Checks, gates and automated reviewers that act outside the repo, such as the host's rules or the brief and model of an automated reviewer, change only after the owner has read the change." GPT-6 Astra, Claude Fable and Codex then approved #125, the pull request that wrote it, at head `18d1ce8`. In its review Claude Fable found a gap in that wording: a setting of the host that feeds a check in the repo, such as a variable of Actions, which the agents' account may change, was covered by the old `ratchet.checks-owner-read`, which covered every change, and is not covered by a sentence on checks, gates and reviewers that act outside the repo.

The second question, asked by the control room on 2026-11-22 after those reviews. Original, in Swedish:

> Alla tre granskarna godkänner nu #125. Fable påpekar två saker som gäller just dig.
>
> Ditt "Ja" gällde att lägga tillbaka skyddet. Den exakta meningen har du inte sett. Så här står den nu i regeln om ägarens filer:
>
> > *"Checks, gates and automated reviewers that act outside the repo, such as the host's rules or the brief and model of an automated reviewer, change only after the owner has read the change."*
>
> Fable hittade dessutom en lucka i formuleringen. En inställning som ligger på GitHub men styr en kontroll i repot täcks inte. Ett exempel är en variabel i Actions, och den får agentkontot ändra. Den gamla regeln täckte alla ändringar, så där fanns inte luckan.
>
> **Två val:**
> 1. **Täpp till luckan först** (mitt råd). Meningen blir:
>    > *"Checks, gates and automated reviewers, and the settings outside the repo they depend on, such as the host's rules, its variables or the brief and model of an automated reviewer, change only after the owner has read the change."*
>
>    Samtidigt rättar jag Fables fyra små fynd om tester som kontrollerar för löst. Codex läser ändringen, och sedan slår jag ihop när du har sagt ja till den nya headen.
> 2. **Slå ihop som den är**, vid head `18d1ce8`, och ta luckan i en senare PR.
>
> […]

Translation:

> All three reviewers now approve #125. Fable points out two things that concern you in particular.
>
> Your "Yes" was to putting the protection back. You have not seen the exact sentence. This is how it now stands in the rule on the owner's files:
>
> > *"Checks, gates and automated reviewers that act outside the repo, such as the host's rules or the brief and model of an automated reviewer, change only after the owner has read the change."*
>
> Fable also found a gap in the wording. A setting that lives on GitHub but controls a check in the repo is not covered. One example is a variable in Actions, and the agents' account may change it. The old rule covered every change, so the gap was not there.
>
> **Two choices:**
> 1. **Close the gap first** (my recommendation). The sentence becomes:
>    > *"Checks, gates and automated reviewers, and the settings outside the repo they depend on, such as the host's rules, its variables or the brief and model of an automated reviewer, change only after the owner has read the change."*
>
>    At the same time I fix Fable's four small findings about tests that check too loosely. Codex reads the change, and then I merge once you have said yes to the new head.
> 2. **Merge as it is**, at head `18d1ce8`, and take the gap in a later PR.
>
> […]

The maintainer then asked. Original, in Swedish:

> Vad rekommenderar du?

Translation:

> What do you recommend?

The control room recommended choice 1. Its reply is not quoted here.

"Fable" is Claude Fable, "the rule on the owner's files" is `ratchet.owner-paths`, and "the new head" is the head of #125 after this change.

## Answer

To the first question. Original, in Swedish:

> Ja

Translation:

> Yes

To the second question. Original, in Swedish:

> Ja

Translation:

> Yes

## What follows

- **1: one sentence in the core.** `ratchet.owner-paths` ends with the sentence of the second answer, choice 1: "Checks, gates and automated reviewers, and the settings outside the repo they depend on, such as the host's rules, its variables or the brief and model of an automated reviewer, change only after the owner has read the change." It replaces the first wording, which #125 wrote and the maintainer saw only in the second question. Claude Fable found the gap in the first wording in its review of #125 at `18d1ce8`: a setting of the host that feeds a check in the repo, such as a variable of Actions that the agents' account may change, was covered by the old `ratchet.checks-owner-read` and not by the first wording. This is a departure from the frozen wording of the core ([RATCHET.md](../RATCHET.md#the-core-is-frozen)), authorized here as [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md) authorized its seven clauses. It restores what `ratchet.checks-owner-read` covered, so step 8 loses nothing that its table of losses does not list.
- The ratchet of `ratchet.owner-paths` stays a check for what is merged in the repo, and says that it does not see whether the owner read a change to a check, gate or automated reviewer, or to a setting outside the repo they depend on. That part is text only: the host's review requirement sees only the files of a pull request, and a required review does not show that the owner read the change.
- This repo's register takes the new entry of `ratchet.owner-paths`, still "text only for now". Its `where` names the gates and automated reviewers outside the repo, and the settings outside the repo that the checks depend on, among them the variables and secrets of Actions, as missing on its way to "built".
- **2: reviewers while Gemini 4 Neon's quota is out.** In place of Gemini 4 Neon, GPT-6 Astra and Claude Fable both review beside Codex the steps that change a check's code, 9a and 9b, at the same head, and GPT-6 Astra also reviews the core steps 10 and 11. Everything else in choice 3 of [D-2026-11-22-standing-approval](D-2026-11-22-standing-approval.md) stands: the approval waits for every reviewer named for a step to pass its head, and the steps that only move text are reviewed by Codex alone. The review from another model family that [AGENTS.md](../AGENTS.md) requires is unchanged.

Proposals (P), which the maintainer did not say in words:

1. P: Claude Fable is of the control room's own model family, so its review is in addition to, and never in place of, the review from another model family.
2. P: When Gemini 4 Neon's quota is back, it takes up the steps of choice 3 of [D-2026-11-22-standing-approval](D-2026-11-22-standing-approval.md) that are not yet reviewed, and the steps already passed by Codex, GPT-6 Astra and Claude Fable are not reviewed again.
