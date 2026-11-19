# D-2026-11-19-one-point-oh: what 1.0 promises, when it comes, and how experimental rules move in or out

- Date: 2026-11-19
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Item 5 of [D-2026-11-19-batched-releases](D-2026-11-19-batched-releases.md) asked for a draft decision on what 1.0 means. The control room wrote a draft. Another model then made an independent proposal, and the control room adopted it in place of its own draft. The criteria below come from that proposal. Five choices were put to the maintainer together, each with a recommendation. They came after this text.

Original, in Swedish:

> Fable har gjort ett genomtänkt förslag. Det är strängare och mer kontrollerbart än mitt utkast, och på en punkt sa Fable emot mig med rätta. Jag hade föreslagit en andel av kärnan med kontroller som kriterium för 1.0. Andelen räknar vilket slags spärr en regel har, inte om kontrollen är byggd, så den går att uppfylla genom att skriva om reglerna. Fable föreslår i stället att Ratchet ska uppfylla sina egna startregler.
>
> **Ärligt läge:** Ratchet uppfyller i dag bara ett av sex kriterier för 1.0, nämligen att det går att komma igång med ett kommando. 1.0 ligger alltså veckor bort. Det är rimligt för något som startade den 16 november.

Translation into English:

> Fable has made a well-considered proposal. It is stricter and more checkable than my draft, and on one point Fable rightly contradicted me. I had proposed a share of the core with checks as a criterion for 1.0. The share counts what kind of ratchet a rule has, not whether the check is built, so it can be met by rewriting the rules. Fable proposes instead that Ratchet should meet its own start rules.
>
> **Honest status:** Ratchet meets only one of six criteria for 1.0 today, namely that you can get started with one command. So 1.0 is weeks away. That is reasonable for something that started on 16 November.

The choices. Original, in Swedish:

> 1. **Vad 1.0 lovar.** Formen på `ratchet.json` och `register.json`, kärnreglernas nycklar och vilka regler som ingår i kärnan ändras bara i en ny huvudversion. Experimentella regler omfattas inte av löftet. **Råd: ja.**
> 2. **Kriterierna för 1.0.**
>    - Formen har varit oförändrad i tre taggar och minst 30 dagar.
>    - En kontroll stoppar en formändring i en minor-version.
>    - `init.py` fungerar.
>    - En verklig register har gått igenom två uppgraderingar.
>    - En annan repo har följt en tagg i 30 dagar, och ditt eget nästa projekt räknas.
>    - Ratchet använder alla sina nio startregler.
>
>    **Råd: ja.**
> 3. **När en regel flyttar in i kärnan.**
>    - Texten har varit oförändrad i två släpp och 30 dagar.
>    - Ratchet använder regeln själv, och kontrollen är byggd om regeln har en.
>    - Regeln har stoppat ett verkligt fel.
>    - Kärnan får inte bli mjukare, alltså får andelen regler som bara är text inte öka.
>
>    Taket sänks med en vid varje flytt, så att flytta in en regel blir aldrig ett sätt att få plats. **Råd: ja.**
> 4. **När en experimentell regel måste ut.** Varje regel får en ålder. Efter tre släpp och 60 dagar utan beslut stoppar kontrollerna tills du väljer: flytta in i kärnan, slå ihop, ta bort eller behåll en gång till med motivering. Det sker i den utrensning vid släpp som redan är beslutad. Det slår till direkt: 19 av de 23 experimentella reglerna används inte ens i Ratchets egen register. Därför tar vi först in i registret det vi redan gör i praktiken. **Råd: ja.**
> 5. **Två motsägelser rättas.** RATCHET.md säger att "en regel lämnar bara när en kontroll täcker den", och en annan regel säger att en regel som aldrig har slagit till inte ska tas bort. Båda gör det omöjligt att rensa experimentella regler. De får gälla bara kärnan. **Råd: ja.**
>
> Om du säger ja blir det ett beslut och en PR. Ålderfältet är en formändring och görs därför före 1.0. PR:en går via Codex med full granskning, eftersom den ändrar regler och kontroller.

Translation into English:

> 1. **What 1.0 promises.** The form of `ratchet.json` and `register.json`, the keys of the core rules, and which rules belong to the core change only in a new major version. Experimental rules are not covered by the promise. **Advice: yes.**
> 2. **The criteria for 1.0.**
>    - The form has been unchanged for three tags and at least 30 days.
>    - A check stops a change of form in a minor version.
>    - `init.py` works.
>    - A real register has gone through two upgrades.
>    - Another repo has followed a tag for 30 days, and your own next project counts.
>    - Ratchet uses all nine of its start rules.
>
>    **Advice: yes.**
> 3. **When a rule moves into the core.**
>    - Its text has been unchanged for two releases and 30 days.
>    - Ratchet uses the rule itself, and the check is built if the rule has one.
>    - The rule has stopped a real fault.
>    - The core must not get softer, that is, the share of rules that are text only must not rise.
>
>    The cap is lowered by one at each move, so that moving a rule in is never a way to make room. **Advice: yes.**
> 4. **When an experimental rule must leave.** Every rule gets an age. After three releases and 60 days without a decision, the checks stop until you choose: move it into the core, merge it, remove it, or keep it once more with a reason. That happens in the clean-out at a release that is already decided. It bites at once: 19 of the 23 experimental rules are not even used in Ratchet's own register. So we first take into the register what we already do in practice. **Advice: yes.**
> 5. **Two contradictions are fixed.** RATCHET.md says that "a rule leaves only when a check covers it", and another rule says that a rule that has never been triggered is not to be removed. Both make it impossible to clean out experimental rules. They are to apply to the core only. **Advice: yes.**
>
> If you say yes, it becomes a decision and a PR. The age field is a change of form and is therefore made before 1.0. The PR goes through Codex with a full review, because it changes rules and checks.

## Answer

Original, in Swedish:

> Ja

Translation into English:

> Yes

All five choices are taken.

## What follows

- **1. The promise.** [SELF-IMPROVEMENT.md](../SELF-IMPROVEMENT.md#what-10-promises) states it, and `ratchet.si-version` says the same: after 1.0, only a major version changes the form of `ratchet.json` or `register.json`, renames the key of a core rule, or adds a rule to the core or removes one from it. A minor version may change, rename or remove an experimental rule. Before 1.0, a minor version may do all of these, and the changelog lists each. `ratchet.si-version` changes in 0.10, and this repo's register takes the new text.
- **2. The criteria.** [SELF-IMPROVEMENT.md](../SELF-IMPROVEMENT.md#when-10-comes) lists the six, with how each is checked or why it is a judgment, and which are met. On 2026-11-19 one is met, `init.py` works. The checks that the criteria need and that are not built yet are issues of their own: #70 (the form unchanged for three tags and 30 days), #71 (a minor version does not change the form) and #72 (Ratchet adopts and builds its start rules). The PR that records this decision builds none of them.
- **3. Moving a rule into the core.** [SELF-IMPROVEMENT.md](../SELF-IMPROVEMENT.md#rules-promoted-from-projects) lists the four criteria. A rule moves into the core by a decision of the maintainer that cites them, and the same pull request lowers `experimental_cap` by one. That the cap is lowered is text only for now: `checks/test_budget.py` pins the cap, so a change to it changes that test, which the maintainer reads, but no check compares the cap or the core with the last tag: issue #73. After 1.0, a rule moves into the core only in a major version, by choice 1.
- **4. The age of an experimental rule.** Every experimental rule in `ratchet.json` names `since`, the version it entered Ratchet, and may name `kept_by`, the id of a decision that kept it once more. `checks/generate.py --check` fails, naming each rule, when one has stood through three releases and 60 days with no decision. Both are counted at the newest version with a date in `CHANGELOG.md`, so the check first fails when a release is dated, in the pull request of a release, which is where the clean-out of [D-2026-11-17-improvement-loop](D-2026-11-17-improvement-loop.md), item 4, happens. A decision in `kept_by` starts the count again from its date, so it keeps a rule once more, not for good. `since` is a change of form, listed in the changelog of 0.10 and told by `checks/upgrade.py`. A check that `since` does not change between releases is issue #74. This repo's register adopts the experimental rules that it already follows.
- **5. The two contradictions.** [RATCHET.md](../RATCHET.md) says that a core rule leaves only when a check covers it, and `ratchet.si-subtract` says that a core rule that has never been triggered is a candidate for review, not for removal. An experimental rule may also leave in the clean-out at a release, by item 4.

Observation (O): `since` was read from the tags. `ratchet.json` came in 0.3, so `git show v0.3:ratchet.json` and later tags show when a rule entered from 0.3 on. 0.2 held the rules of `CONTROL-ROOM.md` and `SELF-IMPROVEMENT.md` in Markdown tables, under the same keys, which `git grep` at `v0.2` shows. A rule takes the first tag that holds its key: 0.2 for twenty rules, 0.4 for `ratchet.expected-tests-ran`, 0.6 for `ratchet.phases` and 0.7 for `ratchet.irreversible-waits`. The earlier tag is the stricter choice, since an older rule meets the age sooner.

Observation (O): every tag is from 2026-11-16 to 2026-11-19, so no rule has stood 60 days, and the check passes today. What bites at once is the count of rules that the register does not adopt, not the check: the earliest it can fail is a release dated 2027-01-15 or later, 60 days after 0.2.

Proposal (P), which the maintainer did not decide: the count of 19 of 23 in choice 4 was a count of experimental rules that this repo's register does not adopt. Before this PR the register adopted four. This PR adopts three more that the repo follows today, `ratchet.cr-does-not-build`, `ratchet.cr-verify-reports` and `ratchet.si-harden`, the last as "text only for now", and leaves out the rest, where it is not clear that the repo follows them.
