# D-2026-11-21-release-and-redraw: release 0.10 without #78, redraw the principles from an outside judgment, and try Ratchet on a production application

<!-- generated:status -->
Status: amended by D-2026-11-22-second-redraw (settles what it left open on #78)
<!-- /generated:status -->

- Date: 2026-11-21
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-20-generated-block (0.10 is released without #78); D-2026-11-20-principles-and-obligations (the redraw aims at six or seven principles)
- Ends: none

## Question

Background. The maintainer asked whether the eleven principles of [D-2026-11-20-principles-and-obligations](D-2026-11-20-principles-and-obligations.md) are the best ones. The control room asked a model from another family (Gemini 4 Neon) for an independent judgment, measured against the maintainer's goal: applications ready for production under the highest demands, run like a factory, with little overhead.

What it found strong: locks over prose, no claim without a run, a fresh review from another model family with the stop after two rounds of the same kind, the threat model of the agent layer, and principles written as questions.

What it found weak:

- The eleven were derived bottom-up from the 54 rules, and several of them are compound.
- Ratchet governs how code reaches `main`, not how it runs in production. It has been tried only on itself, a repo with no users, no database, no dependencies and no service level.
- Five things are missing: safe deploys, with rollback and observability; the security of the application and the supply chain of its dependencies; architectural boundaries and entropy; real contracts and budgets for what is not a function, such as speed and cost; and a fast, hermetic workspace for each agent.
- It suggested merging the eleven into six or seven.
- It found the overhead of hardening the register, of ceremony and of paperwork too high for its value. Its examples: 33 decision files in five days, and `ratchet.review-by-risk`, which names Ratchet's own paths.

The question that followed, four choices, each with a recommendation. Choice 4 refers to an earlier question about the landing page in the control room's chat. Original, in Swedish, with the project in choice 3 replaced in brackets:

> **Val, som delvis ändrar planen:**
> 1. **Släpp 0.10 utan #78.** Blocket är klart. #78 är ännu en kontroll av registret och får vänta tills omritningen avgör om den behövs. **Råd: ja.**
> 2. **Fable-omritningen efter 0.10 utgår från Geminis bedömning:** sex–sju principer, de saknade produktionsprinciperna, och de regler som har hög friktion stryks. Codex granskar, och du beslutar. **Råd: ja.**
> 3. **Pröva Ratchet på en riktig produktionsapp.** Det är Geminis viktigaste poäng: Ratchet har bara prövats på sig själv. [ett av ägarens egna projekt, i produktion], så det kan bli referensprojektet. Det ska aldrig nämnas publikt. **Råd: ja.**
> 4. **Valen om webbsidan från förut gäller fortfarande:** C och B på sidan nu, A får en omgång till. **Råd: ja.**

Translation:

> **Choices, which partly change the plan:**
> 1. **Release 0.10 without #78.** The block is done. #78 is one more check of the register and can wait until the redraw decides whether it is needed. **Recommendation: yes.**
> 2. **The Fable redraw after 0.10 starts from Gemini's judgment:** six or seven principles, the missing production principles, and the rules with high friction removed. Codex reviews, and you decide. **Recommendation: yes.**
> 3. **Try Ratchet on a real production app.** It is Gemini's most important point: Ratchet has only been tried on itself. [one of the owner's own projects, in production], so it can be the reference project. It is never to be named publicly. **Recommendation: yes.**
> 4. **The choices about the landing page from before still hold:** C and B on the page now, A gets one more round. **Recommendation: yes.**

## Answer

Original, in Swedish:

> Ok ja på dina råd

Translation:

> OK, yes to your recommendations

## What follows

- 0.10 is released without #78. #78 waits for the redraw, which decides whether it is still needed. The change of form in 0.10 is the generated block (#100).
- After 0.10, a fresh session of another model (Fable) redraws the principles, starting from the findings of the second model. The aim is six or seven principles, the missing production principles written as questions with obligations under them, and the rules whose friction outweighs their value removed or narrowed. Each change is weighed with the table of coverage before and after that [D-2026-11-20-principles-and-obligations](D-2026-11-20-principles-and-obligations.md) requires, so a protection that disappears still blocks it. A model from another family reviews the redraw, and the maintainer decides.
- Ratchet is tried on an application of the maintainer's own that runs in production, as its reference project. That project is never named in this repo. What it shows comes back as proposals (P) in Ratchet's own words.
- The landing page gets the dial figures, B and C: a logo dial with the eleven principles, and a short loop of a failure becoming a check. They come in a pull request of their own, reviewed as any change to the page. A gets one more round before it goes on the page.
- Proposal (P): [D-2026-11-21-inventory-and-easy-upgrade](D-2026-11-21-inventory-and-easy-upgrade.md) put the inventory, the upgrade in one command and the measure of overhead after #78. With #78 waiting, they follow 0.10 instead. The agent that reads the inventory names the principle each part of an agent layer answers to, so that step uses the principles as they stand after the redraw.
- The second model's judgment is not copied into this repo. Its findings above are the control room's summary.
