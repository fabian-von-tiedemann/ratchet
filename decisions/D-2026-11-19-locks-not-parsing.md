# D-2026-11-19-locks-not-parsing: real locks at GitHub and in the sandbox, the hook as a tripwire, and the phases first

- Date: 2026-11-19
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Five choices put to the maintainer together, each with a recommendation. They came after Codex rejected PR #42 twice for the same kind of fault. The text that came with them, in the original Swedish (with the link to #42 as plain text) and in English:

> Codex har underkänt #42 två gånger av samma skäl. Kroken skulle tolka shellkommandon säkert, men båda gångerna fanns det sätt att ta sig förbi den. I runda 2 hittade Codex åtta sådana, bland annat `printf %n d` och `find . -delete`. Kontrollerna gick igenom, och testerna gav samma resultat i fem körningar. Enligt regeln kör jag ingen tredje runda. Granskningen ligger som kommentar på PR:en.
>
> **Slutsatsen är att en krok som tolkar skalet aldrig kan bli ett lås.** Det som behöver vara ett riktigt lås bör sitta där det inte går att ta sig förbi: hos GitHub och i sandlådan. Här är det nya angreppssättet i fem val:

> Codex has rejected #42 twice for the same reason. The hook was meant to read shell commands safely, but both times there were ways past it. In round 2 Codex found eight, among them `printf %n d` and `find . -delete`. The checks passed, and the tests gave the same result in five runs. By the rule, I run no third round. The review is a comment on the PR.
>
> **The conclusion is that a hook that reads the shell can never become a lock.** What needs to be a real lock should sit where it cannot be got around: at GitHub and in the sandbox. Here is the new approach in five choices:

Original, in Swedish:

> 1. **Kroken blir en snubbeltråd.** Den fångar de vanliga skrivsätten för de fem stegen, och texten säger rent ut att den inte fångar alla skrivsätt. Regeln står då som "delvis byggd". **Råd: ja.**
> 2. **Taggar och släpp låses hos GitHub.** En regeluppsättning för taggar tillåter bara dig och släppflödet att skapa eller ta bort en tagg. Jag kontrollerar först att släppflödet fortfarande kan tagga, och lägger sedan fram exakt vad du ska slå på, eftersom inställningar är dina. **Råd: ja.**
> 3. **Inställningar låses av rollen.** Agentkontot har rollen Write, som jag just har läst tillbaka, och den kan inte ändra repots inställningar. Etiketter kan rollen ändra, och dem räknar vi som ofarliga och ångringsbara. **Råd: ja.**
> 4. **Radering utanför arbetskatalogen låses av sandlådan.** Det gör vi i provet med sandlåda för arbetstrådarna, som redan står i byggordningen, i stället för i kroken. **Råd: ja.**
> 5. **#42 delas upp.** Faserna blir en enda regel och kommer först som 0.6, med 22 experimentella regler av 25. Snubbeltråden och låsen kommer sedan som 0.7. **Råd: ja.**

Translation into English:

> 1. **The hook becomes a tripwire.** It catches the usual spellings of the five steps, and the text says plainly that it does not catch every spelling. The rule then stands as "partly built". **Advice: yes.**
> 2. **Tags and releases are locked at GitHub.** A ruleset for tags lets only you and the release workflow create or delete a tag. I first check that the release workflow can still tag, and then set out exactly what you should turn on, because settings are yours. **Advice: yes.**
> 3. **Settings are locked by the role.** The agents' account has the role Write, which I have just read back, and that role cannot change the repository's settings. The role can change labels, and we count those as harmless and possible to undo. **Advice: yes.**
> 4. **Deletion outside the working directory is locked by the sandbox.** We do that in the trial of a sandbox for the worker threads, which is already in the build order, instead of in the hook. **Advice: yes.**
> 5. **#42 is split.** The phases become a single rule and come first, as 0.6, with 22 experimental rules of 25. The tripwire and the locks come after, as 0.7. **Advice: yes.**

## Answer

Original, in Swedish:

> Ja

Translation into English:

> Yes

## What follows

- 0.6 carries the phases explore, build and run as one experimental rule, `ratchet.phases`, in `CONTROL-ROOM.md`. It is text only, and it brings the rules outside the core to 22 of the cap of 25. It carries nothing about the hook.
- 0.7 carries the hook from issue #23, for the proposed rule `ratchet.irreversible-waits`, as a tripwire. Its claim is limited to the usual spellings of the five steps, and it says plainly that it does not catch every spelling. In a register, the rule stands as partly built, and the steps it does not lock are named as text only.
- 0.7 also sets out a ruleset for tags that lets only the maintainer and the release workflow create or delete a tag, after a check that the release workflow can still tag. The maintainer applies it, because settings are the maintainer's.
- The role Write of the agents' account is the lock on the repository's settings. Labels, which that role can change, count as harmless and possible to undo.
- Deletion outside the working tree is left to the trial of a sandbox for the worker threads (`D-2026-11-17-harness-sandbox-risk`, item 2), not to the hook.
- PR #42 is closed in favor of 0.6 and 0.7.
