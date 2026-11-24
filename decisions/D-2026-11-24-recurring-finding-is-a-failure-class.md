# D-2026-11-24-recurring-finding-is-a-failure-class: a review finding that recurs is a failure class, as a clause in `ratchet.si-harden`

- Date: 2026-11-24
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Put to the maintainer in the control room on 2026-11-24, after a reading of sources on code that agents write and that erodes over time. The question, verbatim, in Swedish:

> **Förslaget** är därför en mening i `ratchet.si-harden` i stället för en ny regel. Då behöver ingen regel ge plats under taket på 17: > *"A review finding that recurs is a failure class: it becomes a check, for code usually a rule of the project's linter in the required job, with a fixture it fails on."* […] SlopCodeBench läggs till som källa, låst till en version. **Vad vill du?** - **A. Ja, lägg till meningen (rekommenderas).** Den kommer med i 0.14. PR:en ändrar regeltexten, så Codex och Astra 6.2 granskar den. - **B. Ändra formuleringen först.** - **C. Bara notera det, ingen ändring nu.**

Translation:

> **The proposal** is therefore one sentence in `ratchet.si-harden` instead of a new rule. Then no rule has to give way under the cap of 17: > *"A review finding that recurs is a failure class: it becomes a check, for code usually a rule of the project's linter in the required job, with a fixture it fails on."* […] SlopCodeBench is added as a source, pinned to a version. **What do you want?** - **A. Yes, add the sentence (recommended).** It goes into 0.14. The PR changes the text of a rule, so Codex and Astra 6.2 review it. - **B. Change the wording first.** - **C. Just note it, no change now.**

## Answer

> A

That is option A.

## What follows

- `ratchet.si-harden` gets the sentence, word for word as quoted, after the sentence on a failure class that comes back after a lesson. No other word of the rule changes. It is an experimental rule, so a minor version may change it, and it goes into 0.14.
- The reason. SlopCodeBench (arXiv 2603.24755, and its code `SprocketLab/slop-code-bench`) measures that code written by agents erodes across iterations. No source read shows that a lint that grows from review findings keeps code maintainable, so the clause states a practice, not a measured effect. The idea already stands in principle 5 and in `ratchet.si-harden`, so a clause in place of a new rule keeps the experimental rules at the cap of 17.
- `SprocketLab/slop-code-bench` is pinned in `sources.json` at commit `de70a479acce7b565d2d0c772f48d7c881c15510`, under the MIT license, and `ratchet.si-harden` cites it. The talk, the manifesto and the lint plugins that the reading also found are not cited.
- A project that adopted `ratchet.si-harden` by copy pastes the new text at its next upgrade. One that adopted it by reference pins the new sha256 that `upgrade.py` prints.
