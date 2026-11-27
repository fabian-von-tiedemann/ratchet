# D-2026-11-19-tripwire-and-settings: 0.7 merged, the tripwire runs here, the rule is built, and Actions secrets and variables are caught by the tripwire alone

- Date: 2026-11-19
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-19-locks-not-parsing (item 3)
- Ends: none

## Question

Five choices put to the maintainer together, each with a recommendation, before the merge of PR #44.

Original, in Swedish:

> 1. **Får jag godkänna och slå ihop [#44](https://github.com/fabian-von-tiedemann/ratchet/pull/44) vid `5a34592`?** Då publiceras 0.7, med regeln från #23, snubbeltråden och filen med regeluppsättningen för taggar. Codex har godkänt den, och `checks` är grönt. **Råd: ja.**
> 2. **Snubbeltråden körs i det här repot.** Från sammanslagningen gäller den också för mig och arbetstrådarna. Codex har kontrollerat att det vanliga arbetet fortfarande går igenom. **Råd: ja.**
> 3. **Regeln står som "bara text tills vidare" i 0.7.** Den ändras till "byggd" i en egen PR, som också skriver in att du har slagit på regeluppsättningen och att jag har läst tillbaka den, vilket jag gjorde nyss. **Råd: ja.**
> 4. **En kort rättelse av gårdagens beslut, i en egen PR.** Rollen Write låser inte hemligheter och variabler för Actions, så dem fångar bara snubbeltråden. I samma PR rättar jag det lilla fel som Codex hittade om ämnestaggarna. **Råd: ja.**
> 5. **Etiketter räknas som ofarliga**, som i ditt beslut, trots att en raderad etikett försvinner från alla ärenden. **Råd: ja.**

Translation into English:

> 1. **May I approve and merge [#44](https://github.com/fabian-von-tiedemann/ratchet/pull/44) at `5a34592`?** That publishes 0.7, with the rule from #23, the tripwire and the file with the ruleset for tags. Codex has passed it, and `checks` is green. **Advice: yes.**
> 2. **The tripwire runs in this repo.** From the merge, it also applies to me and the worker threads. Codex has checked that the usual work still gets through. **Advice: yes.**
> 3. **The rule stands as "text only for now" in 0.7.** It is changed to "built" in a PR of its own, which also records that you have turned on the ruleset and that I have read it back, which I just did. **Advice: yes.**
> 4. **A short correction of yesterday's decision, in a PR of its own.** The role Write does not lock Actions secrets and variables, so only the tripwire catches them. In the same PR I correct the small mistake that Codex found about the topics. **Advice: yes.**
> 5. **Labels count as harmless**, as in your decision, even though a deleted label disappears from every issue. **Advice: yes.**

## Answer

Original, in Swedish:

> går på dina reks

Translation into English:

> going with your recommendations

## What follows

- PR #44 is approved at its head `5a34592` and merged, and its merge publishes 0.7.
- This repo runs the tripwire `checks/tripwire.py` from `.claude/settings.json`, for the control room and for every worker thread.
- In this repo's register, `ratchet.irreversible-waits` becomes "built", with a place where its check lives that says which steps a lock refuses and which only the tripwire catches. The same PR records that the maintainer applied `templates/tag-ruleset.json` as the ruleset `tags-stay` on 2026-11-19 and that the control room read it back.
- This amends item 3 of [D-2026-11-19-locks-not-parsing](D-2026-11-19-locks-not-parsing.md), which said that the role Write cannot change the repository's settings. The role Write locks only the settings that need an admin. It may create, change and delete Actions secrets and variables, of the repository and of an environment, so those are guarded by the tripwire alone.
- `CONTROL-ROOM.md` no longer says that only an admin may manage topics in a repository that an organization owns: there the role Maintain may manage them too. The role Write may not, in either kind of repository.
- Choices 3 and 4 each asked for a PR of their own, apart from #44. They are carried together in one PR after 0.7, with this decision, because both change only this repo's register, its decisions and text that no check ties to a release. Neither raises the version.
- Labels stay outside the settings. They count as harmless and possible to undo, although a deleted label disappears from every issue and pull request that had it.
