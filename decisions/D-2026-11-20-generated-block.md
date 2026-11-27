# D-2026-11-20-generated-block: a project adopts rules through a block generated into its own instruction file

<!-- generated:status -->
Status: amended by D-2026-11-21-release-and-redraw (0.10 is released without #78); amended by D-2026-11-22-second-redraw (adoption by reference is allowed as a weaker mode)
<!-- /generated:status -->

- Date: 2026-11-20
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Choice 2 of [D-2026-11-20-proposal-triage](D-2026-11-20-proposal-triage.md) accepted one change of form from #60, #76, #77 and #78, with #3, after a question on #89 about the mechanism. #89 was written for a project of the maintainer's own, so the maintainer answers it. The control room put the question in the chat, with a recommendation. Original, in Swedish:

> **Kan det andra projektet ha ett block i sin instruktionsfil som Ratchet genererar och kontrollerar?**
> - Reglerna redigeras i `register.json`. Ratchet skriver in dem i ett markerat block i projektets instruktionsfil, till exempel `CLAUDE.md` eller `AGENTS.md`, och kontrollerar att blocket stämmer exakt.
> - Agenterna läser reglerna där de redan läser, och det finns bara ett ställe att ändra dem på.
> - Det som försvinner är att projektet skriver reglerna med egna ord. En översättning, till exempel till svenska, kan ligga i blocket, bunden till originalet.
>
> **Mitt råd:** ja, om projektet klarar att instruktionsfilen har ett genererat avsnitt som inte redigeras för hand. Det är det enda sättet där en kontroll ser själva regeltexten. Vill projektet absolut behålla egna formuleringar måste kontrollen lita på en markering i stället, och då kan en uppmjukad regel slinka igenom.

Translation:

> **Can the other project have a block in its instruction file that Ratchet generates and checks?**
> - The rules are edited in `register.json`. Ratchet writes them into a marked block in the project's instruction file, for example `CLAUDE.md` or `AGENTS.md`, and checks that the block matches exactly.
> - The agents read the rules where they already read, and there is only one place to change them.
> - What goes away is the project writing the rules in its own words. A translation, for example into Swedish, can sit in the block, bound to the original.
>
> **My recommendation:** yes, if the project can live with its instruction file having a generated section that is not edited by hand. It is the only way in which a check sees the text of the rule itself. If the project must keep its own wording, the check has to trust a marker instead, and then a softened rule can slip through.

## Answer

Original, in Swedish:

> ja

Translation:

> yes

## What follows

- `register.json` stays the data. A project may have the rules it adopts, and its own rules, generated into a marked block in its own instruction file, and the register check compares the block exactly with what it generates from the register. The block is never edited by hand. This answers #76 without reading rules out of free Markdown (`D-2026-11-16-strict-forms`).
- An adopted rule may carry a translation, bound by a hash to the rule's text at the version the project follows, so that an upgrade that changes the rule fails until the translation is looked at again (#77). The translation is text from the fixed character list, like any other value.
- A project's own rules may carry a status and where their check stands, like an adopted rule (#60).
- A check counts as built only when it is required for the merge and reads its rules from the base branch (#78, with #3), in a pull request of its own after the block.
- These change the form of `register.json` once, in 0.10. Each comes with fixtures that must fail, and each pull request is reviewed by a model from another family. The control room answers on #89 without naming the project.
