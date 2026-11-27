# D-2026-11-26-field-comparison: what Ratchet takes from the field of skill sets and spec frameworks, and what it leaves

<!-- generated:status -->
Status: amended by D-2026-11-26-skills-eval (the recipe also counts how often a skill runs)
<!-- /generated:status -->

- Date: 2026-11-26
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-26-road-to-1-0 (two goals and two pieces of work join the order)
- Ends: none

## Question

The maintainer asked for a zoomed-out comparison, in a fresh session, of Ratchet with spec frameworks and skill sets for coding agents, among them the repos with more than 100,000 stars. A Claude Fable 5.2 session compared 14 repos. Their star counts were read on 2026-11-26.

The control room put its five proposals to the maintainer in Swedish, each with the control room's advice in italics. Quoted with the summary before them left out, the control room's own elision:

> […]
> 1. **Kartläggningsläget, och högst tio minuter till den första röda kontrollen.** *Det pågår redan, och målet om tio minuter tar jag med.*
> 2. **Hemlighetsskanning och kontroll av beslutsfilernas format som färdiga kontroller,** så att användaren får lås och inte läxor. *Det ingår redan i planen mot 1.0.*
> 3. **Inga personas eller specifikationsflöden. Skriv i stället ett provat recept:** superpowers eller pstack för arbetet, Ratchet för det som ska hålla. *Mitt råd: ja. Det är billigt och visar hur Ratchet hör ihop med det som alla redan använder.*
> 4. **Mät effekten,** till exempel hur ofta en felklass kommer tillbaka i ett repo som använder Ratchet. *Mitt råd: ja, men först när ett annat repo använder Ratchet. Ditt nästa projekt kan bli mätpunkten.*
> 5. **Ta inte efter självuppdatering.** *Jag håller med: att inget ändras av sig självt är just det som skiljer Ratchet.*
>
> Svara till exempel **"ja på 3 och 4"**, så lägger jag in dem i ordningen mot 1.0, efter kartläggningsläget. […]

Translation:
1. The map-only mode, with at most ten minutes to the first red check. *It is already in progress, and I take the ten-minute goal along.*
2. A secret scan and a check of the decision files' format, shipped as ready checks, so that the user gets locks and not homework. *It is already in the plan toward 1.0.*
3. No personas or spec workflows. Write a tried recipe instead: superpowers or pstack for the work, Ratchet for what must hold. *My advice: yes. It is cheap, and it shows how Ratchet fits with what everyone already uses.*
4. Measure the effect, for example how often a failure class comes back in a repo that uses Ratchet. *My advice: yes, but only once another repo uses Ratchet. Your next project can be the point of measurement.*
5. Do not take self-updating. *I agree: that nothing changes by itself is exactly what sets Ratchet apart.*

Answer, for example, "yes to 3 and 4", and I will put them into the order toward 1.0, after the map-only mode. […]

## Answer

> Ja på dina reks

Translation: yes, on your recommendations.

## What follows

- **The order toward 1.0 of D-2026-11-26-road-to-1-0 stands.** Two goals and two pieces of work join it:
  - the map-only mode aims at ten minutes from the clone to the first red check;
  - the secret scan and the decision-format check are shipped as ready checks;
  - after the map-only mode, a tried recipe: a skill set for the work, superpowers or pstack, together with Ratchet for what must hold. "Tried" means followed once, end to end, in a scratch repo, with the run shown;
  - measuring the effect starts once another repo uses Ratchet. Until then it is a goal, not work.
- **Ratchet takes no personas, no spec workflow and no self-updating.**
- **The comparison itself** is the control room's material, not part of the repo: it holds star counts and readings of other projects that will age.
