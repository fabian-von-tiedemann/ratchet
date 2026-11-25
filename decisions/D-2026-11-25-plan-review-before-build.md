# D-2026-11-25-plan-review-before-build: a fresh reviewer reads the plan of a check change before it is built

- Date: 2026-11-25
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Put to the maintainer by the control room on 2026-11-25, in Swedish. The maintainer had asked whether the work should follow the elephant-goldfish model, with subagents in worktrees of their own, so as to work faster. Quoted with the control room's own elisions:

> **Vad EGM egentligen säger** (README vid den pinnade versionen): elefanten skriver *specifikationen*, guldfiskar granskar den med nya ögon *innan man bygger*, och du väljer avvägningarna. Vi granskar i stället först när koden är skriven.
>
> […]
>
> - **A. Granska planen innan bygget (rekommenderas).** För varje PR som ändrar en kontroll skriver jag en kort plan: vad den lovar, vilka fall den täcker och vilka filer den rör. En guldfisk från en annan modellfamilj granskar planen på några minuter, och först därefter bygger arbetaren. Det tar bort de dyra rundorna. Jag börjar med nästa PR som ändrar en kontroll.
> - **B. Två till tre arbetare samtidigt, på filer som inte överlappar** (rekommenderas, tillsammans med A). […]
> - **C. Installera EGM-pluginet i Claude Code.** Det är ett pluginet från en tredje part, och arbetssättet kan vi köra utan det. *Inte nu.*

Translation: **What EGM actually says** (its README at the pinned commit): the elephant writes the *specification*, goldfish review it with fresh eyes *before anything is built*, and you choose the trade-offs. We review only once the code is written. […] **A. Review the plan before the build (recommended).** For each PR that changes a check, I write a short plan: what it claims, which cases it covers and which files it touches. A goldfish from another model family reviews the plan in a few minutes, and only then does the worker build. That removes the costly rounds. I start with the next PR that changes a check. **B. Two to three workers at once, on files that do not overlap** (recommended, together with A). […] **C. Install the EGM plugin in Claude Code.** It is a plugin from a third party, and we can run the method without it. *Not now.*

## Answer

> a

Translation: A. The control room reads this as A alone. B, more workers at once, is not decided, and C is not chosen.

## What follows

- Before a worker builds a PR that changes a check, the control room writes a short plan: what the check claims, against which threat, the finite list of cases, and the files it will touch. A reviewer from another model family reads the plan in a fresh context, with no account from the control room beyond the plan and the code. The worker builds only after the plan has passed. The plan and its review go in the PR body.
- The review of the built PR at its exact head stays as it is (`ratchet.fresh-context`, `ratchet.review-by-risk`).
- This is a working method of the control room, not a rule in the register, and it is text only: no check sees whether a plan was reviewed.
- Workers still run one at a time where their files overlap, as before.
