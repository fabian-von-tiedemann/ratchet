# D-2026-11-17-workflows-checks-handover: workflow files, the required check, the handover, and proposals #17 and #18

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Five choices put to the maintainer together, each with a recommendation.

Original, in Swedish:

> 1. **[#15](https://github.com/fabian-von-tiedemann/ratchet/issues/15): agenterna pushar arbetsflödesfiler i sina PR:er, och du godkänner den version (head) som innehåller dem.** Råd: ja. Tokenen har redan omfånget `workflow`, och `CODEOWNERS` kräver redan din granskning av allt under `.github/`.
> 2. **[#16](https://github.com/fabian-von-tiedemann/ratchet/issues/16): jobbet `checks` blir en obligatorisk statuskontroll i `skydd-main`.** Råd: ja. I dag kan en PR med röd CI slås ihop när den är godkänd.
> 3. **Överlämningen (#14) slutar skriva av läget från GitHub.** `HANDOVER.md` innehåller då bara det GitHub inte visar: vem som väntar på vad, vem som ska agera och nästa steg. Läget hänvisas i stället till öppna PR:er och till ärenden med etiketten `question`. Varje öppen fråga blir ett ärende, även de två som saknas nu. Råd: ja. Båda rundorna föll på att en handskriven kopia av ett läge som ändras hann bli inaktuell eller ofullständig innan granskningen var klar.
> 4. **[#17](https://github.com/fabian-von-tiedemann/ratchet/issues/17), två lager säkerhetskontroller: skannrar alltid, plus en låst säkerhetsskill vid släpp och vid känsliga ändringar.** Råd: vänta, ärendet står öppet. Lagret med skannrar täcks till stor del redan av `ratchet.no-secrets` och `ratchet.nightly-visible`, och Ratchet har ingen hemlighetsskanning av sig själv än. Den kommer först, och sedan prövas förslaget som en experimentell regel. Förslaget hänvisar också till regeln `ratchet.finding-proof-axis`, som inte finns.
> 5. **[#18](https://github.com/fabian-von-tiedemann/ratchet/issues/18), faser (explore, build, run) och regler som anger i vilka faser de gäller.** Råd: nej, ärendet stängs med en notering. `RATCHET.md` säger uttryckligen att projektets fas hör till projektet och inte till Ratchet. Förslaget skulle dessutom ändra formen på varje regel, och det är en ändring av huvudversionen. Ett projekt kan ha det som en egen regel.

Translation into English:

> 1. **[#15](https://github.com/fabian-von-tiedemann/ratchet/issues/15): the agents push workflow files in their PRs, and you approve the version (head) that holds them.** Advice: yes. The token already has the `workflow` scope, and `CODEOWNERS` already requires your review of everything under `.github/`.
> 2. **[#16](https://github.com/fabian-von-tiedemann/ratchet/issues/16): the job `checks` becomes a required status check in `skydd-main`.** Advice: yes. Today a PR with red CI can be merged once it is approved.
> 3. **The handover (#14) stops copying the state from GitHub.** `HANDOVER.md` then holds only what GitHub does not show: who waits on what, who is to act, and the next step. For the state, it points to the open PRs and to the issues with the label `question` instead. Every open question becomes an issue, including the two that are missing now. Advice: yes. Both rounds failed because a hand-written copy of a changing state had become out of date or incomplete before the review was done.
> 4. **[#17](https://github.com/fabian-von-tiedemann/ratchet/issues/17), two layers of security checks: scanners always, plus a pinned security skill at releases and at sensitive changes.** Advice: wait, the issue stays open. The layer of scanners is largely covered already by `ratchet.no-secrets` and `ratchet.nightly-visible`, and Ratchet has no secret scan of itself yet. That comes first, and then the proposal is tried as an experimental rule. The proposal also refers to the rule `ratchet.finding-proof-axis`, which does not exist.
> 5. **[#18](https://github.com/fabian-von-tiedemann/ratchet/issues/18), phases (explore, build, run) and rules that state which phases they apply in.** Advice: no, the issue is closed with a note. `RATCHET.md` says explicitly that the project's phase belongs to the project, not to Ratchet. The proposal would also change the form of every rule, and that is a change of the major version. A project can have it as a rule of its own.

## Answer

Original, in Swedish:

> vi kör på dina råd

Translation into English:

> we go with your advice

## What follows

- Workflow files are pushed in the PRs that need them, and the code owner approves the head that holds them. Issue #15 is answered.
- The job `checks` is to be a required status check in the ruleset `skydd-main`. Only the maintainer can change the ruleset. Issue #16 stays open until the setting has been read back.
- `HANDOVER.md` holds only who waits on what, who is to act, and the next step. It points to the open PRs and to the issues with the label `question` for the state, and every open question is an issue.
- Issue #17 stays open until this repo has a secret scan.
- Issue #18 is closed without a change.
