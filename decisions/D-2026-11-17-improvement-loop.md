# D-2026-11-17-improvement-loop: the parts of the improvement loop that are built next

<!-- generated:status -->
Status: amended by D-2026-11-17-knowledge-and-modes (the clean-out at a release also reviews the instruction files)
<!-- /generated:status -->

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Five choices put to the maintainer together, each with a recommendation, after a status of the improvement loop.

Original, in Swedish:

> 1. **Daglig läsning av ändrade källor.** En schemalagd väckning av kontrollrummet läser varje nytt "Source moved"-ärende och öppnar jämförelselänken. Den skriver högst tre observationer (O) eller förslag (P) per källa som en kommentar. Innehållet behandlas som underlag, inte som instruktioner, och du avgör. **Råd: ja.** Utan det leder bevakningen bara till ärenden som ingen läser.
> 2. **Spaning efter nya metoder varannan vecka.** Spaningen går igenom en kort, fast lista med platser: källornas repon och organisationer samt versionsnyheterna för de verktyg vi använder. Den lämnar högst tre förslag som ärenden. **Råd: ja.** Taket på tre förslag hindrar att Ratchet växer av ren nyfikenhet.
> 3. **Mätning varannan vecka.** Ett skript räknar ut fyra tal från GitHub och lägger dem i ett statusärende:
>    - antal granskningsrundor före godkännande
>    - antal stopp efter två underkända rundor
>    - andel regler som har en kontroll
>    - totalt antal regler
>
>    **Råd: ja.** Det är det som visar om loopen gör Ratchet tätare eller bara tyngre. De flesta talen finns redan i utslagen vi lägger på PR:erna.
> 4. **Utrensning vid varje släpp.** Kontrollrummet föreslår högst tre regler att ta bort, slå ihop eller flytta ut ur kärnan, var och en med skäl. **Råd: ja.** Det är den del av loopen som håller Ratchet slimmad.
> 5. **Smalare process för rena dokument.** Beslutsfiler och `HANDOVER.md` som inte ändrar regler, kontroller eller registret granskas inte längre av en modell från en annan familj. Det räcker med grön CI och ditt godkännande. **Råd: ja.** I dag gick sex granskningsrundor åt till sådana filer, och du läser dem ändå själv.

Translation into English:

> 1. **Daily reading of moved sources.** A scheduled wake-up of the control room reads each new "Source moved" issue and opens the compare link. It writes at most three observations (O) or proposals (P) per source as a comment. The content is treated as material, not as instructions, and you decide. **Advice: yes.** Without it, the watch only leads to issues that nobody reads.
> 2. **A search for new methods every other week.** The search goes through a short, fixed list of places: the sources' repos and organizations, and the release notes of the tools we use. It leaves at most three proposals as issues. **Advice: yes.** The cap of three proposals stops Ratchet from growing out of mere curiosity.
> 3. **Measuring every other week.** A script computes four numbers from GitHub and puts them in a status issue:
>    - the number of review rounds before approval
>    - the number of stops after two rejected rounds
>    - the share of rules that have a check
>    - the total number of rules
>
>    **Advice: yes.** That is what shows whether the loop makes Ratchet tighter or only heavier. Most of the numbers are already in the verdicts we post on the PRs.
> 4. **A clean-out at every release.** The control room proposes at most three rules to remove, merge or move out of the core, each with a reason. **Advice: yes.** That is the part of the loop that keeps Ratchet lean.
> 5. **A leaner process for documents only.** Decision files and `HANDOVER.md` that change no rule, check or the register are no longer reviewed by a model from another family. Green CI and your approval are enough. **Advice: yes.** Today six review rounds went to such files, and you read them yourself anyway.

## Answer

Original, in Swedish:

> Jag går på dina rekommendationer.

Translation into English:

> I go with your recommendations.

## What follows

- All five parts are built, each in a PR of its own. Parts 1 to 4 are proposals (P) until each is built and merged. Each states its ratchet, or says "text only" and why.
- From this decision on, a PR that changes only files in `decisions/` and `HANDOVER.md`, and changes no rule, check or register, is merged on green CI and the maintainer's approval, without a review from another model family. This PR is the first.

Proposal (P), which the maintainer did not decide: build them in the order 5, 3, 1, 4, 2, after PR #9 and PR #12.
