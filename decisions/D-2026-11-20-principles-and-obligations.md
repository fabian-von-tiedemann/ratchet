# D-2026-11-20-principles-and-obligations: eleven principles on top, the rules as obligations under them

- Date: 2026-11-20
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Background. The maintainer asked whether Ratchet looks for rules that solve as many problems as possible, so that it does not become a patchwork. Original, in Swedish:

> Man vill hitta regler som löser så många problem som möjligt eller hur? Så att det inte blir mer och mer komplicerat? Men det kanske finns med? Att regler kan slås ihop osv? Så att det inte blir ett lapptäcke liksom. Drömmen är ju enkla regler som kan styra komplexa system. Tänker att trafikregler är ett bra exempel på det, eller marknadsekonomi. Man behöver inte planera för allt, utan låta reglerna hantera beteendet

Translation:

> You want to find rules that solve as many problems as possible, right? So that it does not get more and more complicated? But maybe that is already in there? That rules can be merged and so on? So that it does not become a patchwork. The dream is simple rules that can govern complex systems. I think traffic rules are a good example of that, or a market economy. You do not have to plan for everything, but let the rules handle the behavior.

The control room then had a fresh session of another model (Fable) redraw the 54 rules as a proposal. It found that the 25 rules that name a check lean on eight mechanisms, and proposed eleven rules, one per mechanism, with five rules dropped. The maintainer said yes to having a model from another family check it first. That check (Codex) read all 30 decisions and all 54 issues and found the eleven not sound as a replacement: failure classes recorded in issues and decisions lose their checks or become text when the details go, among them partial protection reading as full (#61, #78), a test count shrinking while green (#2, #21), the sweep and the guard removal of `ratchet.root-cause` (#63, #66), the lock matrix of `ratchet.irreversible-waits`, and the review contract from #5 and #6. Its smallest fix: keep the eleven as headings, with the rules under them as obligations that each keep their check and their status.

The question that followed, four choices, each with a recommendation. Original, in Swedish:

> 1. **Två nivåer:** elva principer överst, skyldigheter under, och varje skyldighet behåller sin kontroll och sin status. Beslutet skrivs med Fables förslag, Codex granskning och ditt ja. **Råd: ja.**
> 2. **Första steget är en karta, inte en sammanslagning.** Varje regel får sin princip i `ratchet.json`, och README och RATCHET.md visar principerna först. Ingen regel tas bort och inget skydd ändras. **Råd: ja.** Det ger den enkla läsningen direkt och utan risk.
> 3. **Sammanslagningar bara med en tabell som visar täckningen före och efter.** Codex granskar mot tabellen. Ett skydd som försvinner blockerar sammanslagningen. Bevisreglerna (Fables steg 1) blir första kandidaten, men allvarlighetsgrad, räckvidd och tidig körning behålls. **Råd: ja.**
> 4. **Förslag i framtiden anger sin princip,** och om de lägger till en skyldighet eller skärper en som finns. Andra omgången av förslagen går in på samma sätt. **Råd: ja.**

Translation:

> 1. **Two levels:** eleven principles on top, obligations under them, and each obligation keeps its check and its status. The decision is written with Fable's proposal, Codex's review and your yes. **Recommendation: yes.**
> 2. **The first step is a map, not a merge.** Every rule gets its principle in `ratchet.json`, and the README and RATCHET.md show the principles first. No rule is removed and no protection changes. **Recommendation: yes.** It gives the simple reading at once and without risk.
> 3. **Merges only with a table that shows the coverage before and after.** Codex reviews against the table. A protection that disappears blocks the merge. The evidence rules (Fable's step 1) are the first candidate, but severity, scope and the early run are kept. **Recommendation: yes.**
> 4. **Future proposals name their principle,** and whether they add an obligation or tighten one that exists. The second round of proposals goes in the same way. **Recommendation: yes.**

## Answer

Original, in Swedish:

> ja på dina råd

Translation:

> yes to your recommendations

## What follows

- The goal for 1.0: a project reads Ratchet as eleven principles, each a few sentences that apply to cases no one listed, and adopts the obligations under them, each with its check or "text only" and why. The register keeps its status per obligation, as it does per rule today, so this needs no change to the form of `register.json`.
- This decision opens the core for the work it names: giving each rule its principle, and merging rules whose coverage is the same. Each such pull request still needs the maintainer's approval of its head. A principle names no check of its own and claims nothing beyond the obligations under it.
- The first pull request adds the eleven principles and a principle for each rule to `ratchet.json`, and shows the principles first in `README.md` and `RATCHET.md`. It removes no rule and changes no rule's text or check. The six parts stay until a later pull request decides what replaces them.
- A pull request that merges rules carries a table of the failure classes each rule covers before and after, with the evidence for each (a decision or an issue), and the cross-family review checks the merge against it. A class that loses its check, or a lock that becomes a tripwire, blocks the merge.
- A proposal names its principle and says whether it adds an obligation or tightens one. The open proposals that were to be the second round of `D-2026-11-20-proposal-triage` are sorted under the principles in the same way. The proposal form asks for the principle once the principles stand in `ratchet.json`.
- Fable's proposal and Codex's review are not copied into this repo. The eleven principle texts are written in the first pull request, starting from Fable's eleven and amended for Codex's findings, and reviewed there.
