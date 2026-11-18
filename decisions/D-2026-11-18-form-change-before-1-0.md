# D-2026-11-18-form-change-before-1-0: before 1.0, a minor version may change the form

- Date: 2026-11-18
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

A reviewer from another model family rejected the first round of PR #34. Its finding 2: the PR makes `experimental_cap` a required field in `ratchet.json`, so the `ratchet.json` of 0.4 no longer validates, and that change of form is released as the minor version 0.5. `ratchet.si-version` says that a major version changes the form, and that before 1.0 a minor version may rename keys. The question was put to the maintainer twice, and the answer came directly after the second time.

The first time. Original, in Swedish:

> **Fråga: Ska regeln för versioner tillåta även ändrad form i en minor-version före 1.0, så länge changelogen listar varje ändring, precis som för namnbyten?** **Råd: ja.**
> - Före 1.0 är det rimligt att formen fortfarande sätter sig.
> - Att hoppa till 1.0 för ett enda fält vore att lova en stabilitet som Ratchet inte har än.
> - Ändringen gäller en regel i kärnan, så den behöver ditt beslut. Den skrivs ner som en beslutsfil och följer med i 0.5.
>
> Om du svarar nej gör vi fältet frivilligt i stället, så att filen från 0.4 fortfarande godtas. Taket kontrolleras då bara i det här repot.

Translation into English:

> **Question: Should the rule for versions also allow a changed form in a minor version before 1.0, as long as the changelog lists every change, just as for renames?** **Advice: yes.**
> - Before 1.0 it is reasonable that the form is still settling.
> - Jumping to 1.0 for a single field would be to promise a stability that Ratchet does not have yet.
> - The change concerns a rule in the core, so it needs your decision. It is written down as a decision file and goes out in 0.5.
>
> If you answer no, we make the field optional instead, so that the file from 0.4 is still accepted. The cap is then checked only in this repo.

The second time. Original, in Swedish:

> Jag föreslår att regeln för versioner tillåter en ändrad form i en minor-version före 1.0, om changelogen listar varje ändring. **Råd: ja.** Svarar du nej blir fältet frivilligt i stället.

Translation into English:

> I propose that the rule for versions allows a changed form in a minor version before 1.0, if the changelog lists every change. **Advice: yes.** If you answer no, the field becomes optional instead.

## Answer

Original, in Swedish:

> ja

Translation into English:

> yes

## What follows

- `ratchet.si-version` says that before 1.0 a minor version may also change the form, and that the changelog lists every change of form, as it lists every rename. The rest of the rule stays as it was.
- `experimental_cap` stays a required field in `ratchet.json`, and 0.5 is released as a minor version. The entry of 0.5 in `CHANGELOG.md` lists the change to `ratchet.si-version`, and lists the new required field as a change of form, with what a project must do about it.

Observation (O): `ratchet.si-version` is an experimental rule in `SELF-IMPROVEMENT.md`, not a rule of the core, although the question calls it one. The core in `RATCHET.md` is not changed.

Proposal (P), which the maintainer did not decide, and which PR #34 builds: `checks/upgrade.py` says when the fields at the top of `ratchet.json` differ between the two versions, and `UPGRADING.md` tells a project that keeps a copy of a Ratchet check, or has a check of its own, that reads `ratchet.json` to update it. Ratchet's checks in `.ratchet` read the `ratchet.json` of the version they come with, so a project that uses them as the README says has nothing to do.
