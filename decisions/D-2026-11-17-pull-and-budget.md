# D-2026-11-17-pull-and-budget: how projects pull Ratchet, a budget against bloat, and contributions

<!-- generated:status -->
Status: amended by D-2026-11-20-proposal-triage (the cap goes from 25 to 23); amended by D-2026-11-22-second-redraw (the cap goes from 23 to 17)
<!-- /generated:status -->

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The maintainer stated the goal first. Original, in Swedish:

> grejjen jag vill få till med ratchet är att jag kan ha ett ramverk som uppdateras med best practices hela tiden. Och att jag kan be mina repon. kolla i det och uppdatera sitt arbetssätt. Det är mitt mål. Och att det blir bättre och bättre hela tiden.
>
> Kul såklart om andra vill bidra.
>
> Målet är verkligen att kika på vad andra gör, bedöma om det är värt att lära sig av och sen föra in det på ett strukturerat sätt. men också ta bort saker. Så att det inte bloatar iväg liksoom

Translation into English:

> The thing I want to achieve with Ratchet is a framework that is updated with best practices all the time, and that I can ask my repos to check it and update their way of working. That is my goal, and that it gets better and better all the time.
>
> Of course it would be fun if others want to contribute.
>
> The goal really is to look at what others do, judge whether it is worth learning from, and then bring it in in a structured way, but also to remove things, so that it does not bloat.

Five choices were then put to the maintainer, each with a recommendation. Original, in Swedish:

> 1. **Uppgraderingsväg för repona.** Ett kommando, `python3 checks/upgrade.py register.json`, jämför projektets version med Ratchets senaste. Det listar vilka regler som är nya, ändrade och borttagna, med motivering från ändringsloggen. En kort, fast instruktion, `UPGRADING.md`, beskriver hur agenten i ett repo kör kommandot, väljer vilka rader som ska in eller ut, kör `check_register.py` och öppnar en egen PR. **Råd: ja.** Det är kärnan i ditt mål. Ett repo kan då be om att uppdatera sitt arbetssätt och få en granskningsbar PR.
> 2. **En regelbudget som spärr mot svällning.** `ratchet.json` anger ett tak för antalet experimentella regler, och `generate.py --check` blir rött om taket överskrids. En ny regel måste då ersätta, slå ihop eller ta bort en befintlig, om du inte höjer taket genom ett beslut. **Råd: ja,** med taket på dagens antal plus fem. Då gör en kontroll att Ratchet inte växer, inte bara en rutin.
> 3. **Bidrag från andra.** `CONTRIBUTING.md` och ett ärendeformulär för förslag. Obligatoriska fält:
>    - vad som hände
>    - felklassen
>    - spärrhaken
>    - om det gäller i andra projekt
>    - förstahandskällan.
>
>    **Råd: ja.** Det gör `ratchet.lesson-names-check` byggd för Ratchet självt, och bidrag kommer in i en form som går att bedöma snabbt.
> 4. **Ratchet tillämpar sin egen loop.** Ratchets eget register tar in `si-pull`, `si-measure`, `si-subtract` och lärdomsreglerna i takt med att de byggs. **Råd: ja.** Det som inte fungerar för Ratchet självt ska inte skickas ut till andra.
> 5. **Byggordning efter 0.4.** Först uppgraderingsvägen (1) och regelbudgeten (2). Sedan formuläret (3), #23 tillsammans med faserna, och loopens delar: mätning, daglig läsning av ändrade källor, utrensning och spaning. **Råd: ja.** Uppgraderingsvägen gör att varje förbättring faktiskt når dina repon, och budgeten skyddar mot svällning innan nya regler kommer in.

Translation into English:

> 1. **An upgrade path for the repos.** A command, `python3 checks/upgrade.py register.json`, compares the project's version with Ratchet's latest. It lists which rules are new, changed and removed, with the reasons from the changelog. A short, fixed instruction, `UPGRADING.md`, describes how the agent in a repo runs the command, chooses which rows go in or out, runs `check_register.py` and opens a PR of its own. **Advice: yes.** It is the core of your goal. A repo can then ask to update its way of working and get a PR that can be reviewed.
> 2. **A rule budget as a guard against bloat.** `ratchet.json` states a cap on the number of experimental rules, and `generate.py --check` goes red if the cap is exceeded. A new rule must then replace, merge or remove an existing one, unless you raise the cap by a decision. **Advice: yes,** with the cap at today's number plus five. Then a check, not just a routine, keeps Ratchet from growing.
> 3. **Contributions from others.** `CONTRIBUTING.md` and an issue form for proposals. Required fields:
>    - what happened
>    - the failure class
>    - the ratchet
>    - whether it applies in other projects
>    - the primary source.
>
>    **Advice: yes.** It makes `ratchet.lesson-names-check` built for Ratchet itself, and contributions arrive in a form that can be judged quickly.
> 4. **Ratchet applies its own loop.** Ratchet's own register adopts `si-pull`, `si-measure`, `si-subtract` and the lesson rules as they are built. **Advice: yes.** What does not work for Ratchet itself should not be sent out to others.
> 5. **Build order after 0.4.** First the upgrade path (1) and the rule budget (2). Then the form (3), #23 together with the phases, and the parts of the loop: measuring, daily reading of moved sources, clean-out, and the search. **Advice: yes.** The upgrade path makes every improvement actually reach your repos, and the budget protects against bloat before new rules come in.

In the same exchange, the maintainer asked whether the knowledge repo should not live on the mini. The recommendation was a private repo on GitHub, `fabian-von-tiedemann/ratchet-kunskap`, cloned to the mini, with raw material from other people's videos kept only on the mini and never in a repo. The alternative was a git repo that exists only on the mini, which was advised against.

## Answer

Original, in Swedish:

> ja på dina råd

Translation into English:

> yes to your recommendations

## What follows

- Projects get an upgrade path: `checks/upgrade.py` and `UPGRADING.md`.
- `ratchet.json` gets a cap on experimental rules, checked by `generate.py --check`, at today's number of experimental rules plus five. Raising the cap is a decision.
- Ratchet gets `CONTRIBUTING.md` and an issue form for proposals with the five required fields.
- Ratchet's own register adopts `ratchet.si-pull`, `ratchet.si-measure`, `ratchet.si-subtract` and the lesson rules as each is built.
- The build order after 0.4 is: the upgrade path and the budget, then the form, #23 with the phases, and the parts of the loop.
- The knowledge repo is private on GitHub and cloned to the mini. Raw material stays on the mini only.
