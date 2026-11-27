# D-2026-11-20-proposal-triage: what to do with the open proposals after two triages

<!-- generated:status -->
Status: amended by D-2026-11-22-second-redraw (choice 1, no product rules now)
<!-- /generated:status -->

- Date: 2026-11-20
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-17-pull-and-budget (the cap goes from 25 to 23)
- Ends: none

## Question

Five choices put to the maintainer together, each with a recommendation, after two independent triages of the open proposals, made by other models.

Original, in Swedish:

> Båda sorteringarna är klara. De är överens om det mesta, och där de skiljer sig har jag valt det som håller Ratchet minst och ärligast.
>
> 1. **Inga produktregler nu.** Det gäller drift (#81), mätning mot verklig användning (#82), livscykel för plattform och leverantörer (#84), en modul för språkmodeller i produkten (#83), roller och mandat (#79) och arkivering av körningar (#64). Ratchet har ingen egen produkt att pröva dem på, och de skulle ta platser vi inte har. Ett projekt kan i stället ha dem som egna regler, när val 2 är byggt. **Råd: ja.**
> 2. **#89:s huvudinvändning löses med en enda formändring.** En regel ska kunna tas in genom att peka på var projektet redan har den (#76), med översättning bunden till originalet (#77). Projektets egna regler får status (#60), och en kontroll räknas som byggd bara om den krävs (#78). Fable föreslår ett starkare sätt än det som förslaget beskriver: reglerna genereras in i ett markerat block i projektets egen instruktionsfil och jämförs exakt. Då finns texten bara på ett ställe, och spärren håller. Jag frågar projektet på #89 om det fungerar för dem. **Råd: ja.**
> 3. **Snabba vinster utan nya regler:**
>    - `init.py` lämnar inga platshållare och får ett läge för en ensam agent (#58).
>    - Arbetsflödet får plats för projektets egna kontroller (#59).
>    - De två granskningsraderna, som är beslutade sedan 17 november men aldrig skrevs in, läggs till (#5, #6).
>    - #23 stängs, eftersom den redan är byggd.
>
>    **Råd: ja.**
> 4. **Två regler, men bara en ny plats.** #80, att en rättning av ett rapporterat fel ska slås ihop tillsammans med ett märkt test, blir kontrollen för kärnregeln `root-cause`. Den regeln är i dag bara text, så ingen ny plats behövs, och andelen av kärnan som bara är text sjunker. #63 och #66 blir delar av samma kontroll. Den enda lediga platsen går till #65, "en exakt form, ingen tolkning", som två projekt har stött på och som Ratchet redan följer. **Råd: ja.**
> 5. **Taket.** Vi behåller 25, men städar under det:
>    - En ny experimentell regel ska redan användas av Ratchet själv, eller säga varför den inte kan det.
>    - Vid nästa släpp slås `cr-background-wait` ihop med `cr-wake` (#86).
>    - Tre regler som upprepar andra tas bort: `cr-lead-with-ask`, `cr-reads-first` och `cr-review`.
>    - `si-version` och `si-maintainer-approves`, som bara gäller Ratchet självt, flyttas till Ratchets egna regler, och taket sänks med två så att flytten inte frigör platser.
>
>    **Råd: ja.**

Translation into English:

> Both triages are done. They agree on most things, and where they differ I have chosen what keeps Ratchet smallest and most honest.
>
> 1. **No product rules now.** That covers operations (#81), measurement against real use (#82), the life cycle of platform and vendors (#84), a module for language models in the product (#83), roles and mandates (#79) and the archiving of runs (#64). Ratchet has no product of its own to try them on, and they would take places we do not have. A project can have them as rules of its own instead, once choice 2 is built. **Advice: yes.**
> 2. **#89's main objection is solved by one change of form.** A rule can be adopted by pointing to where the project already has it (#76), with a translation bound to the original (#77). The project's own rules get a status (#60), and a check counts as built only if it is required (#78). Fable proposes a stronger way than the proposal describes: the rules are generated into a marked block in the project's own instruction file and compared exactly. Then the text exists in one place only, and the lock holds. I am asking the project on #89 whether that works for them. **Advice: yes.**
> 3. **Quick wins without new rules:**
>    - `init.py` leaves no placeholders and gets a mode for a single agent (#58).
>    - The workflow gets a place for the project's own checks (#59).
>    - The two review lines, decided on 17 November but never written in, are added (#5, #6).
>    - #23 is closed, since it is already built.
>
>    **Advice: yes.**
> 4. **Two rules, but only one new place.** #80, that a fix of a reported fault is merged together with a marked test, becomes the check for the core rule `root-cause`. That rule is text only today, so no new place is needed, and the share of the core that is text only goes down. #63 and #66 become parts of the same check. The one free place goes to #65, "one exact form, no interpretation", which two projects have run into and which Ratchet already follows. **Advice: yes.**
> 5. **The cap.** We keep 25, but clean up under it:
>    - A new experimental rule must already be used by Ratchet itself, or say why it cannot be.
>    - At the next release, `cr-background-wait` is merged with `cr-wake` (#86).
>    - Three rules that repeat others are removed: `cr-lead-with-ask`, `cr-reads-first` and `cr-review`.
>    - `si-version` and `si-maintainer-approves`, which apply only to Ratchet itself, move to Ratchet's own rules, and the cap is lowered by two so that the move frees no places.
>
>    **Advice: yes.**

## Answer

Original, in Swedish:

> ja på dina rek

Translation into English:

> yes to your recommendations

## What follows

- Choice 1: no rule is added. The control room closed issues #64, #79, #81, #82, #83 and #84 with a comment on 2026-11-20.
- Choice 2: the change of form follows in a pull request of its own, after the question on #89.
- Choice 3: the pull request that adds this decision carries it. `init.py --solo` leaves the control room and the skills out of `AGENTS.md` (#58). The register check in the workflow `init.py` writes fails while `AGENTS.md` holds a placeholder of the template, and names each (#58). `init.py` names the adopted rules that wait for a remote when the repo has none (#58). The workflow has a job for the project's own checks, and `init.py` names the jobs to require (#59). The two lines decided in [D-2026-11-17-proposals-2-6](D-2026-11-17-proposals-2-6.md) stand in [RATCHET.md](../RATCHET.md#the-review-script) (#5, #6). No rule is added or removed. The control room closed #23 as done on 2026-11-20.
- Choice 4: pull request #92 carries the check for `ratchet.root-cause`, with #63 and #66 as parts of it, and #65 as the experimental rule `ratchet.one-exact-form`.
- Choice 5: pull request #92 carries the clean-out under the cap of 23, with the merge of `cr-background-wait` into `cr-wake`, released with the next version.
