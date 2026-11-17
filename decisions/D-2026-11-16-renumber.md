# D-2026-11-16-renumber: the published tag stays, and the new work is 0.3 and 0.4

- Date: 2026-11-16
- Decided by: Ratchet's maintainer
- Kind: decision (D)

Names are left out of this file. Where the original names the external tester, a model or a reviewer, the name is replaced by a word in square brackets. Nothing else in the original is changed.

## Question

Original, in Swedish:

> Mitt råd är att numrera om.
>
> - **Taggar är löften.** Den som har hämtat `v0.2` ska alltid få samma innehåll. Ett repo som säger att regler bara rör sig framåt kan inte skriva om sin egen release, och det skulle [testaren] och andra som granskar se direkt.
> - **Det kostar nästan ingenting.** Omnumreringen är mekanisk: versionsnummer, ändringslogg och den version kontrollen jämför mot. Det tar mindre än en timme.
> - **Det blir bättre så.** 0.2 är redan ett riktigt steg från 0.1. Då blir 0.3 "Ratchet bevisar sitt löfte med en fungerande kontroll", och 0.4 är den vassare versionen. Det är en tydligare historia än att 0.2 ändras i efterhand.
>
> Säg "ok", så sätter jag i gång omnumreringen och [granskarens] granskning av kontrollen. Du får kommandona när båda är klara.

Translation into English:

> My advice is to renumber.
>
> - **Tags are promises.** Whoever has fetched `v0.2` must always get the same content. A repo that says rules only move forward cannot rewrite its own release, and [the tester] and others who review would see that at once.
> - **It costs almost nothing.** The renumbering is mechanical: version numbers, changelog and the version the check compares against. It takes less than an hour.
> - **It is better this way.** 0.2 is already a real step from 0.1. Then 0.3 becomes "Ratchet proves its promise with a working check", and 0.4 is the sharper version. That is a clearer story than 0.2 being changed afterwards.
>
> Say "ok", and I will start the renumbering and [the reviewer's] review of the check. You get the commands when both are done.

## Answer

Original, in Swedish:

> ok

Translation into English:

> ok

## What follows

- The tag `v0.2` and its release are not moved, deleted or edited.
- The changelog keeps the entry for 0.2 exactly as it was published.
- Of the two builds, 0.3 is released. The other is set aside: see [D-2026-11-16-register-only](D-2026-11-16-register-only.md).
- The rule `repo.tags-stay` is in the register, so that the answer holds for later versions too. Approved in [D-2026-11-16-tags-stay](D-2026-11-16-tags-stay.md).
