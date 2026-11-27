# D-2026-11-26-skills-eval: measure whether a skill helps, with Ratchet as the judge, and write no skills of Ratchet's own

- Date: 2026-11-26
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-26-field-comparison (the recipe also counts how often a skill runs)
- Ends: none

## Question

An outside reader asked whether Ratchet helps a project take in the skills its rules draw on. The maintainer then wrote in Swedish:

> Det som vore intressant att mäta är om skillsen faktiskt hjälper eller stjälper. Är du med? Det kanske vi kan ha som eval på nåt sätt? Vilka skills hjälper oss faktiskt att bygga bättre redan från början

> Tänker att ratchet på detta sätt kan identifiera vilka skills man behöver för att bygga långsiktiga ai projekt som går att förvalta och vidareutveckla med agenter. […] Fatta vilken grej om vi verkligen med bevis kan peka ut vilka skills som gör jobbet. Och kanske ska vi också ta fram egna skills/optimera utifrån det man vill uppnå liksom. Nya modeller kommer ju också ändr apå skillsen allt eftersom. Och kanske behövs det bara regler i slutet ändå ...

Translation: "What would be interesting to measure is whether the skills actually help or hurt. Are you with me? Maybe we can have it as an eval somehow? Which skills actually help us build better from the start." And: "I think Ratchet could in this way identify which skills you need to build long-lived AI projects that can be maintained and developed further with agents. […] Imagine if we could really point out, with evidence, which skills do the job. And maybe we should also make our own skills, or optimize for what you want to achieve. New models will also change the skills over time. And maybe only rules are needed in the end anyway ..."

The elision is the maintainer's request for a fresh session to think first. A Claude Fable 5.2 session wrote a memo on it, which is the control room's material and not part of this repo. The control room then put this to the maintainer, in Swedish. It is quoted from the proposals on, with the summary of the memo before them left out:

> **Fables förslag och mina råd:**
> 1. **Mät om skillen alls körs, när receptet prövas.** Det är 10 till 20 sessioner, med och utan att skillen nämns vid namn. *Fable: före 1.0. Mitt råd: ja, det är billigt och ingår ändå i receptet.*
> 2. **Ett pilotförsök: `tdd` mot `test-can-fail`, med 120 sessioner** och mått som bestäms i förväg. *Fable: efter 1.0. Mitt råd: ja, efter 1.0, och planen granskas först.*
> 3. **Lägg till en variant utan Ratchet i pilotförsöket.** Då prövas Ratchets eget påstående, som är obevisat i dag. *Mitt råd: ja. Det är kanske den viktigaste varianten.*
> 4. **Inga egna skills.** *Mitt råd: håll med Fable. Belägget är starkt, och det stämmer med varför Ratchet finns.*
> 5. **Märk varje skill i receptet "mätt" eller "omätt".** *Mitt råd: vänta tills pilotförsöket har gett ett resultat.*
>
> […]
>
> Svara till exempel **"ja på dina råd"**. Då skriver jag beslutet med din fråga och ditt svar ordagrant. Punkt 1 lägger jag in i receptet, och punkt 2 och 3 i ordningen efter 1.0.

Translation:
1. Measure whether the skill runs at all, when the recipe is tried: 10 to 20 sessions, with and without naming the skill. *Fable: before 1.0. My advice: yes, it is cheap and part of the recipe anyway.*
2. A pilot of `tdd` against `test-can-fail`, with 120 sessions and measures set in advance. *Fable: after 1.0. My advice: yes, after 1.0, with the plan reviewed first.*
3. Add a variant without Ratchet to the pilot, which tests Ratchet's own claim, unproven today. *My advice: yes, it may be the most important variant.*
4. No skills of Ratchet's own. *My advice: agree with Fable. The evidence is strong, and it fits why Ratchet exists.*
5. Mark each skill in the recipe "measured" or "unmeasured". *My advice: wait until the pilot has given a result.*

The elision is a note on a leftover scratch directory. Answer "yes to your advice", and I will write the decision with your question and your answer verbatim. Point 1 goes into the recipe, and points 2 and 3 into the order after 1.0.

## Answer

> ja på dina råd

Translation: yes, on your advice.

## What follows

- **Ratchet is the inspection, and skills are the craft.** A rule says what must hold and names its check. A skill says how to do the work. Ratchet takes the requirement from a skill and writes it as a rule, and it installs no skill.
- **The recipe**, decided in D-2026-11-26-field-comparison, also counts how often the named skill actually runs: 10 to 20 sessions, with and without naming it.
- **After 1.0, a pilot**, with its plan reviewed before it runs:
  - `tdd` against `ratchet.test-can-fail`;
  - variants with no Ratchet, with Ratchet's rules only, and with rules and the skill;
  - judged by hidden tests and seeded faults that the pilot builds, not by the check the rule names, since that check was drawn from the skill.
- **Ratchet writes no skills of its own, and optimizes none against its checks.**
- **Measuring the effect of Ratchet itself** is the pilot's variant without Ratchet. It does not replace the measure in a real repo that D-2026-11-26-field-comparison waits for.
