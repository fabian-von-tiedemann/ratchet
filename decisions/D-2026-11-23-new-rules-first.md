# D-2026-11-23-new-rules-first: for a repo with rules of its own, Ratchet leads with its new rules

- Date: 2026-11-23
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Background. A project with its own rule layer that adopted 0.11 by reference and upgraded to 0.12 reported three things:

- The markers for rules the project already enforced gave it little. One row by reference stayed.
- Three rows adopted in part passed the check at once. Then two review rounds in a row each found one more clause missing from "Not stated here", the same class of error twice, and the three rows were dropped.
- One new product rule, `ratchet.platform-lifecycle`, read against the repo, found a runtime past its end of support that no one had noticed, and that the project's own checks had not caught.

The question, asked by the control room on 2026-11-23. Original, in Swedish:

> **Fyra val**
> 1. **Gör de nya reglerna till huvudvägen för repon med egna regler.** Först kommer en beslutsfil som säger vem fullt intag är till för, nämligen nya repon. Sedan bygger vi ett läge som bara kartlägger: det ger en rapport och lägger inget i det krävda jobbet. Till sist skriver `upgrade.py` ut, för varje ny regel, vad man ska leta efter i repot. *Mitt råd: ja.* Ett nytt fält i `ratchet.json` kan räknas som en formändring, så beslutsfilen ska väga det mot klockan till 1.0.
> 2. **Gör steget billigare utan att det släpper igenom fel.** Det ska hämta bara den låsta committen och kontrollera bara den committens objekt. `STARTING.md` ska säga att steget får gå i ett jobb som inte är krävt. *Mitt råd: ja, men inte "godkänn när Ratchet inte går att nå".* Det strider mot regeln att en kontroll fallerar på det den inte vet.
> 3. **Behåll formen för delvis intag och skärp bara texten:** saknas en del av en mening, listas hela meningen. Klockan börjar inte om igen. *Mitt råd: ja.* Att ta bort formen vore en ny formändring, och vi har bara ett försök att gå på.
> 4. **Rätta småfelen i en PR till 0.13** ... *Mitt råd: ja.*

Translation:

> **Four choices**
> 1. **Make the new rules the main path for repos with rules of their own.** First comes a decision file that says who full adoption is for, namely new repos. Then we build a mode that only maps: it gives a report and puts nothing in the required job. Last, `upgrade.py` prints, for each new rule, what to look for in the repo. *My advice: yes.* A new field in `ratchet.json` may count as a change of form, so the decision file is to weigh that against the clock to 1.0.
> 2. **Make the step cheaper without letting faults through.** It is to fetch only the pinned commit and verify only that commit's objects. `STARTING.md` is to say that the step may run in a job that is not required. *My advice: yes, but not "pass when Ratchet cannot be reached".* That goes against the rule that a check fails on what it does not know.
> 3. **Keep the form for adoption in part and only sharpen the text:** when part of a sentence is missing, the whole sentence is listed. The clock does not start again. *My advice: yes.* Removing the form would be a new change of form, and we have only one trial to go on.
> 4. **Fix the small faults in a PR for 0.13** ... *My advice: yes.*

The text of choice 4 is shortened here. It lists plain fixes and needs no decision.

## Answer

Original, in Swedish:

> ja på dina råd

Translation:

> yes to your advice

## What follows

### Choice 1: the new rules first

- Full adoption is for a new repo, or for one with no rule layer of its own. A repo with its own checked rule layer reads each release's new and changed rules against itself, and builds the ones that fit as its own checks. Full adoption and adoption by reference stay as they are, but they are not the path Ratchet leads with for such a repo.
- A map-only mode will be built: a report of Ratchet's rules mapped to the project's own checks. It puts nothing in the required job, and there is no register to keep in step.
- `checks/upgrade.py` will print, for each new or changed rule, what to look for in the repo.

The clock toward 1.0. The criterion "The form has been unchanged for three tags and at least 30 days" in [SELF-IMPROVEMENT.md](../SELF-IMPROVEMENT.md#when-10-comes) reads the form as "the fields at the top of `ratchet.json` and of its rules, as `checks/upgrade.py` compares them". That comparison counts a field of a rule as new when some rule of one version holds it and no rule of the other does, whether the field is required or optional. So a new optional field in `ratchet.json` is a change of form, and would start the count again. Therefore:

- The "look for" text does not go in `ratchet.json`. It goes in a data file of its own beside it, keyed by the rule's key, which `upgrade.py` reads. The criterion names neither that file nor what `upgrade.py` prints, so it is not a change of form, and the count from 0.12 stands.
- That file's form is not covered by the promise of 1.0 until a decision says it is.
- The map-only mode keeps no register, so it does not change the form of `register.json`.
- That a check in this repo fails on a key in the new file that `ratchet.json` lacks is a proposal (P).

### Choice 2: a cheaper pinned step

- `STARTING.md` says the pinned step may run in a job that is not required.
- The step never passes when Ratchet cannot be reached.
- It fetches only the pinned commit and verifies only that commit's objects.

### Choice 3: the form for adoption in part stays

- The phrase `Not stated here: <clause>; <clause>.` stays as it is.
- The guidance says: when any part of a sentence of the rule is not stated, the whole sentence is listed.
- The clock does not start again. The count toward 1.0 still starts from 0.12 ([D-2026-11-23-partial-adoption-form](D-2026-11-23-partial-adoption-form.md)).

### Choice 4

The small faults the same upgrade found in `upgrade.py`, `init.py` and their printed commands are fixed in a pull request for 0.13, with no decision of their own.

### Rejected

- **Passing when Ratchet cannot be reached.** A check fails on what it does not know (`repo.strict-forms`). A project that does not want the step to block a merge puts it in a job that is not required.
- **Removing the form for adoption in part.** It would be another change of form and start the count toward 1.0 again, on the evidence of one trial. The errors in that trial were in which clauses were listed, which the sharper guidance addresses.
- **`run_pinned.py --copy-to`.** A copy cannot vouch for itself before it is verified: the script that would make the copy is the one not yet checked.
