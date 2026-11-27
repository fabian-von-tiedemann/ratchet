# D-2026-11-17-knowledge-and-modes: what the first video gave, the knowledge layer, and the modes of the control room

<!-- generated:status -->
Status: amended by D-2026-11-17-harness-sandbox-risk (the instruction files are reviewed now, not at the next release)
<!-- /generated:status -->

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-17-improvement-loop (the clean-out at a release also reviews the instruction files)
- Ends: none

## Question

Five choices put to the maintainer together, each with a recommendation. They came after the first analysis of a video for the knowledge layer: a secondary source on working practices with the strongest model, read from a pasted transcript.

Original, in Swedish:

> 1. **Ny experimentell regel: gör det som går att ångra, vänta med det som inte går att ångra.** Projektet anger var agenten får verka. En krok i Claude Code (`hook`) stoppar en fast lista med steg som inte går att ångra om de saknar ett godkännande som nämner just dem: force-push, taggar, släpp, radering utanför arbetskatalogen och ändrade inställningar. **Råd: ja.** Ratchet har ingen sådan allmän regel, och den här ger mer självständighet utan att säkerheten blir sämre. Jag lägger den som ett ärende och bygger den efter #9 och #12.
> 2. **Granska instruktionsfilerna vid varje modellbyte.** Granskningen läggs in i den utrensning vid varje släpp som du redan har beslutat om. Den letar efter absoluta ord som "aldrig" och "VIKTIGT" och efter rader som skrevs för äldre modeller i AGENTS.md, CLAUDE.md och arbetsbeskrivningarna. **Råd: ja.** Ingen ny regel behövs, bara ett steg till i en rutin som redan finns.
> 3. **Kunskapslagret blir ett privat repo, `ratchet-kunskap`.** Du skapar det med `ny-repo fabian-von-tiedemann/ratchet-kunskap` och bjuder in `fabian-agent`. Till dess ligger anteckningarna i `~/kunskap/notes/`. **Råd: ja.** Andras filmer och transkriberingar hör inte hemma i ett publikt repo.
> 4. **Faserna utforska, bygga och drifta blir experimentella regler i `CONTROL-ROOM.md`.** **Råd: ja.** Då förblir kärnan fryst, och det stämmer med beslutet om #18.
> 5. **Videokedjan byggs parallellt med Ratchet-arbetet.** **Råd: ja.** Verktygen är installerade. Nästa gång börjar kedjan med ljudet och transkriberar lokalt, så att 429 från undertextservern undviks.

Translation into English:

> 1. **A new experimental rule: do what can be undone, wait with what cannot.** The project states where the agent may act. A hook in Claude Code stops a fixed list of steps that cannot be undone when they lack an approval that names them: force push, tags, releases, deletion outside the working directory, and changed settings. **Advice: yes.** Ratchet has no such general rule, and this one gives more autonomy without making safety worse. I open it as an issue and build it after #9 and #12.
> 2. **Review the instruction files at every change of model.** The review becomes part of the clean-out at every release that you have already decided on. It looks for absolute words like "never" and "IMPORTANT", and for lines written for older models, in AGENTS.md, CLAUDE.md and the work briefs. **Advice: yes.** No new rule is needed, only one more step in a routine that already exists.
> 3. **The knowledge layer becomes a private repo, `ratchet-kunskap`.** You create it with `ny-repo fabian-von-tiedemann/ratchet-kunskap` and invite `fabian-agent`. Until then, the notes are kept in `~/kunskap/notes/`. **Advice: yes.** Other people's videos and transcripts do not belong in a public repo.
> 4. **The phases explore, build and run become experimental rules in `CONTROL-ROOM.md`.** **Advice: yes.** That keeps the core frozen, and it agrees with the decision on #18.
> 5. **The video pipeline is built in parallel with the work on Ratchet.** **Advice: yes.** The tools are installed. Next time the pipeline starts with the audio and transcribes locally, so that a 429 from the subtitle server is avoided.

## Answer

Original, in Swedish:

> ja på allt

Translation into English:

> yes to everything

## What follows

- The rule in item 1 is proposed in an issue and built after PR #9 and PR #12. As an experimental rule, it raises the version when it is added.
- The clean-out at every release (`D-2026-11-17-improvement-loop`, item 4) also reviews the instruction files for absolute words and for lines written for older models.
- The knowledge layer is a private repo, `fabian-von-tiedemann/ratchet-kunskap`, which the maintainer creates. Other people's material is kept out of this repo. Ratchet gets only proposals, in its own words, that cite the primary sources.
- The phases explore, build and run become experimental rules in `CONTROL-ROOM.md`, not rules of the core.
- The video pipeline lives in the knowledge repo and is built in parallel with the work on Ratchet.

Proposal (P), not decided by the maintainer: the phases are built after the rule in item 1, so that both go into one version.
