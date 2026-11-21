# D-2026-11-21-inventory-and-easy-upgrade: a read-only inventory of the agent layer, an upgrade in one command, and a measure of overhead

- Date: 2026-11-21
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Background. The maintainer described why Ratchet was built, and asked whether it matches what is being built. Original, in Swedish:

> * Anledningen att jag byggde detta från början var att jag insåg att jag satt på 100+ repon och att jag inte hade koll på vad som faktiskt styrde dem. De hade utvecklats över tid och i mina globala inställningar låg en massa skills som krockade med varandra. Jag ville liksom städa upp. Över tid så var många skills helt onödiga, en doctor körning med claude visade det ganska omgående.
> * Men projekten hade alla olika regler som höll det tajt, det agentiska lagret.
> * när jag startade ett nytt projekt där det var vitkigt att det var tajt från början och jag ville ärva det bästa från alla mina projekt och vad som händer ute i omvälrden så bestämde jag mig för att bygga regelverket utanför repot för första gången. Och att underhålla det med lärdomar från alla projekt och omvälrden.
> * Det ska vara enelt att uppdatera, kolla om det finns något nytt i kontrollrepot (mitt agentiska skillrepo kanske man kan kalla det, styrrepo) och kuna kolla enkelt. Men vare projekt äger ändå sin uppsättning, då varje projejt har olika saker som är viktigta.
> * Tanen är också att ta det bästa från de som är bäst på agentisk kodning och underhålla det så att det inte krockar med mina repon. Därför har jag lutat mig mot skils från de stora pocock, obra, poteto. Men även fler. Se listan liksom.
>
> Stämmer det mot vad vi bygger? Att man kan onboarda och tvätta sin skillsstack i efterhand?
> Att varje repo äger sin uppsättning men man kan alltid checka in och se om det finns något nytt att låna liksom?
>
> Målet är också att det ska vara så lite overhead som möjligt. Men det vet jag inte om det stämmer eller inte. Men det ska iaf vara lätt och tydligt hur man underhåller reglerna i sitt agentiska lager.

Translation:

> * The reason I built this in the first place was that I realized I was sitting on 100+ repos and did not know what actually governed them. They had grown over time, and my global settings held a lot of skills that collided with each other. I wanted to clean up, sort of. Over time many skills turned out to be entirely unnecessary; a doctor run with Claude showed that pretty much at once.
> * But the projects all had different rules that kept them tight, the agentic layer.
> * When I started a new project where it mattered that it was tight from the start, and I wanted to inherit the best from all my projects and from what happens in the world outside, I decided to build the rules outside the repo for the first time. And to maintain them with lessons from all the projects and the world outside.
> * It should be easy to update, to check whether there is anything new in the control repo (my agentic skill repo, you might call it, a steering repo), and to be able to check easily. But each project still owns its set, since each project has different things that matter.
> * The idea is also to take the best from those who are best at agentic coding and maintain it so that it does not collide with my repos. That is why I have leaned on skills from the big ones, pocock, obra, poteto. But others too. See the list, sort of.
>
> Does that match what we are building? That you can onboard and clean up your skill stack afterwards?
> That each repo owns its set, but you can always check in and see if there is anything new to borrow, sort of?
>
> The goal is also for there to be as little overhead as possible. But I do not know whether that holds or not. But at least it should be easy and clear how you maintain the rules in your agentic layer.

The control room answered that half of it holds. Each repo owns its register, `upgrade.py` shows the new rules there are to borrow, the pinned sources in `sources.json` are watched, and lessons flow back from the projects (#89). What does not hold yet: nothing cleans up an existing agent layer afterwards, since `init.py` skips files that exist and nothing reads what governs a repo, what collides, and what is a duplicate or unused; Ratchet thinks one repo at a time; and the overhead is too high, since an upgrade is seven manual steps and `UPGRADING.md` has grown into a wall of text.

The question that followed, four choices, each with a recommendation. Original, in Swedish, with account names replaced in brackets:

> 1. **Ett inventeringskommando (bara läsning):** det går igenom ett repos agentlager, inklusive globala skills, och listar vad som styr, vad som krockar, vad som är dubblett och vilken Ratchet-princip varje del motsvarar. Det skriver ingenting. **Råd: ja, först.** Det är ditt ursprungsproblem, och det är också den bästa vägen in för ett befintligt repo: först se vad man har, sedan välja.
> 2. **Uppgradering i ett steg:** kommandot hämtar själv senaste versionen och visar kort vad som är nytt att låna och vad som har ändrats i det man har valt. Det ersätter de sju stegen. **Råd: ja.**
> 3. **Överblick över alla repon**, som ett skript i kontrollrummet och inte i Ratchet. **Råd: ja, men efter 1 och 2.** En begränsning: jag når bara repona under [the control room's account]. Repona under [two other accounts] behöver köra det själva.
> 4. **Mät overheaden:** hur många steg och minuter det tar att börja använda Ratchet och att uppgradera. Måttet läggs bredvid komplexitetsmåttet i `si-measure`. **Råd: ja.** Då ser vi om vi blir enklare eller bara säkrare.

Translation:

> 1. **An inventory command (read only):** it goes through a repo's agent layer, including global skills, and lists what governs, what collides, what is a duplicate and which Ratchet principle each part corresponds to. It writes nothing. **Recommendation: yes, first.** It is your original problem, and it is also the best way in for an existing repo: first see what you have, then choose.
> 2. **Upgrade in one step:** the command fetches the latest version itself and shows in short what is new to borrow and what has changed in what you have chosen. It replaces the seven steps. **Recommendation: yes.**
> 3. **An overview across all repos**, as a script in the control room and not in Ratchet. **Recommendation: yes, but after 1 and 2.** One limit: I reach only the repos under [the control room's account]. The repos under [two other accounts] need to run it themselves.
> 4. **Measure the overhead:** how many steps and minutes it takes to start using Ratchet and to upgrade. The measure goes beside the complexity measure in `si-measure`. **Recommendation: yes.** Then we see whether we get simpler or only safer.

## Answer

Original, in Swedish:

> överblick över alla repon behöver man väl inte? eller vad menar du?
> annars ja!

Translation:

> You do not need an overview across all repos, do you? Or what do you mean?
>
> Otherwise yes!

The control room reads this as: choices 1, 2 and 4 are accepted, and choice 3 is dropped, because each repo checks for itself.

## What follows

- The inventory is a read-only command in `checks/`, standard library only. It reports facts and does not interpret Markdown ([D-2026-11-16-strict-forms](D-2026-11-16-strict-forms.md)): which files make up the agent layer (instruction files at any depth, skills, commands, agents, hooks, settings, and, when asked with a flag, the user's global layer), which harness loads each, duplicates by name and by content hash, and references to files that do not exist. Judging what each part means, and which principle it answers to, is the agent's job, on the inventory's output, and its result is a proposal to the owner, never a change. The command writes nothing and reads only within the paths it is given. It is the first step of `init.py`'s path for a repo that already has an agent layer.
- The upgrade becomes one command. It fetches the version asked for, or the latest tag, and prints in short what is new to borrow and what changed in the rules the project adopted, with the entries to paste. It still never changes the register by itself. `UPGRADING.md` shrinks to match.
- The measure of overhead is the number of steps and minutes it takes to adopt Ratchet in an empty repo and to upgrade by one version, recorded with each release. Under `principle.subtract-first` it goes into `ratchet.si-measure` beside the numbers there and replaces one of them rather than adding one, or the pull request says why it cannot. (O: `ratchet.si-measure` names four numbers today, and none of them is a measure of complexity; the pull request picks which one, if any, the new measure replaces.)
- There is no overview across repos. Each repo checks for itself.
- Order: after #100 (the generated block) and the pull request for #78 with #3, which complete the change of form in 0.10. Each of the three is its own pull request, with fixtures that must fail where a check is involved, and is reviewed by a model from another family.
