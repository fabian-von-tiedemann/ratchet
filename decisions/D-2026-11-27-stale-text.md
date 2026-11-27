# D-2026-11-27-stale-text: prune stale text, give decisions a status, and refuse citations of decisions that no longer hold

- Date: 2026-11-27
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: none
- Ends: D-2026-11-22-standing-approval

## Question

An outside reader who uses Ratchet in a real project reported this. Their living documents and code cited decisions everywhere. Agents had several times acted on a decision that a later one had overturned. 63 of their 1,168 citations pointed at revoked decisions. They now forbid decision citations in living text and code, and keep history in `git log`. The maintainer asked the control room to zoom out, and to check with three assessments in fresh contexts, by models from three families. The three assessments are the control room's material, not part of this repo. The control room then put this to the maintainer, in Swedish. The summary of the three assessments before it is left out here, and so is the control room's reading of them:

> **Mina råd**
> 1. **Rensa nu.** En PR rättar allt som är bevisat inaktuellt: det stående godkännandet, veckoregeln, siffrorna i HANDOVER, sandlådan och de gamla kommentarerna. Samtidigt slutar HANDOVER säga åt agenter att läsa `decisions/` i klump. *Mitt råd: ja, först av allt.* Det tar bort den risk som finns i dag.
> 2. **Status på besluten, med Fables variant.** Nya beslut anger `Replaces:`, `Amends:` och `Ends:`, med `none` som ett obligatoriskt svar. `generate.py` skriver statusraden överst i det äldre beslutet, och den ordagranna frågan och det ordagranna svaret lämnas orörda. De ungefär tolv relationer som redan finns fylls i för hand. Det blir också den kontroll av format som `ratchet.decision-as-file` saknar i dag. *Mitt råd: ja, efter punkt 1.*
> 3. **En kontroll som stoppar hänvisningar till ersatta eller avslutade beslut.** Vid delvis ersatta beslut fungerar den som en snubbeltråd och säger det öppet. Regeltext hänvisar till regelnycklar. Hänvisningar i koden får stå kvar så länge de inte pekar på ett ersatt beslut. *Mitt råd: ja, efter punkt 2.* Den fångar det farliga utan att kosta 468 ändringar.
> 4. **Bara ett ställe för varje fakta.** HANDOVER skrivs om till en kort sida som pekar på registret och ärendena i stället för att upprepa siffror. Det står redan på listan över saker att göra. *Mitt råd: ja, tillsammans med punkt 1.*
> 5. **Till användarna** som en del av kontrollen i `ratchet.decision-as-file` och inte som en ny regel, först när vår egen kontroll har stoppat ett inlagt fel. *Mitt råd: vänta.*
>
> Svara till exempel **"ja på dina råd"**.

Translation:
1. **Prune now.** One PR corrects everything proven stale: the standing approval, the weekly rule, the counts in HANDOVER, the sandbox and the old comments. At the same time, HANDOVER stops telling agents to read `decisions/` wholesale. *My advice: yes, first of all.* It removes the risk that exists today.
2. **A status on decisions, in Fable's variant.** A new decision states `Replaces:`, `Amends:` and `Ends:`, with `none` as a required answer. `generate.py` writes the status line at the top of the older decision, and the verbatim question and answer stay untouched. The roughly twelve relations that already exist are filled in by hand. This also becomes the format check that `ratchet.decision-as-file` lacks today. *My advice: yes, after point 1.*
3. **A check that refuses citations of replaced or ended decisions.** For a partly replaced decision it is a tripwire and says so openly. Rule text cites rule keys. Citations in code may stay as long as they do not point at a replaced decision. *My advice: yes, after point 2.* It catches what is dangerous without costing 468 changes.
4. **One place for each fact.** HANDOVER is rewritten into a short page that points at the register and the issues, instead of repeating counts. It is already on the list of things to do. *My advice: yes, together with point 1.*
5. **To adopters** as part of the check in `ratchet.decision-as-file`, not as a new rule, and only once our own check has refused a seeded fault. *My advice: wait.*

Answer, for example, "yes to your advice".

## Answer

> ja på dina råd

Translation: yes to your advice.

## What follows

- **Points 1 and 4** come first, in one PR with a reviewed plan, after the move to `maintain/`. The standing approval of D-2026-11-22-standing-approval is described as ended: its migration's last step merged on 2026-11-23, and nothing records a later step.
- **Point 2**, then **point 3**, each in a PR of its own with a reviewed plan.
- **Point 5** waits until Ratchet's own check has refused a seeded fault.
