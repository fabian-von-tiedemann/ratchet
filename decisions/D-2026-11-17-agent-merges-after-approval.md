# D-2026-11-17-agent-merges-after-approval: the agents' account merges a pull request after the code owner has approved its exact head

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

Names are left out of this file. Where the original names a reviewer, or the instruction file of the reviewer's tool, the name is replaced by words in square brackets. Nothing else in the original is changed.

## Question

The question was put after auto-merge, turned on by the agents' account while a pull request waited for review ([D-2026-11-17-auto-merge](D-2026-11-17-auto-merge.md)), had failed four times to merge a pull request after the code owner approved it: #11, #22, #29 and #9.

Original, in Swedish:

> **Förslag:** när [granskaren från en annan modellfamilj] har godkänt en PR och du har godkänt exakt samma version slår jag ihop den själv, med squash. GitHub vägrar om något har pushats efter ditt godkännande, om `checks` inte är grönt eller om ditt godkännande saknas, så regeluppsättningen på `main` stoppar fortfarande allt annat. Auto-merge slutar vi använda, eftersom den inte fungerar här.
>
> För att det ska gälla behövs:
> - en beslutsfil;
> - en ny formulering i `AGENTS.md`, där det i dag står att agenten inte slår ihop;
> - samma ändring i `~/.claude/CLAUDE.md` och [instruktionsfilen för granskarens verktyg].
>
> Det blir en egen PR som du godkänner, och den slår jag ihop själv. **Råd: ja.**

Translation into English:

> **Proposal:** when [the reviewer from another model family] has approved a PR and you have approved exactly the same version, I merge it myself, with a squash. GitHub refuses if anything has been pushed after your approval, if `checks` is not green or if your approval is missing, so the ruleset on `main` still stops everything else. We stop using auto-merge, because it does not work here.
>
> For this to apply, there must be:
> - a decision file;
> - a new wording in `AGENTS.md`, where it says today that the agent does not merge;
> - the same change in `~/.claude/CLAUDE.md` and [the instruction file of the reviewer's tool].
>
> It becomes a PR of its own that you approve, and I merge that one myself. **Advice: yes.**

## Answer

Original, in Swedish:

> Ja

Translation into English:

> Yes

## What follows

- The agent merges with `PUT /repos/OWNER/NAME/pulls/N/merge`, using `merge_method=squash` and `sha` set to the head that both the cross-family review and the code owner approved. GitHub refuses the merge if the head has moved.
- The agent merges only when the code owner's approval is on that head and `checks` is green.
- PRs under the docs-only exception of [D-2026-11-17-improvement-loop](D-2026-11-17-improvement-loop.md) need no cross-family review, but still need the code owner's approval.
- The agent still never approves, never tags and never releases by hand.
- Auto-merge is no longer used.
- The ruleset is unchanged.
- `AGENTS.md` and the agents' instruction files outside the repo say that the agents' account merges after the code owner's approval of the exact head, instead of saying that it does not merge.
- The pull request that records this decision is merged by the agents' account, the first under it.

Proposals (P), which the maintainer did not decide:

- `repo.agents-own-account` in [register.json](../register.json) changes to match, with this decision as its source. It stays text only: the ruleset refuses a merge without the code owner's approval of the latest push and `checks` green, but it cannot see whether the cross-family review passed.
- `HANDOVER.md` says that the agents' account merges, and no longer that the maintainer merges when auto-merge cannot.
- `CHANGELOG.md` is not changed. It holds one entry for each version of Ratchet, the first entry must be the version in `ratchet.json`, and a new version is released when it is merged. The change is to this repo's own register and working rules, not to a rule of Ratchet, and editing the entry of the released 0.3 would make it differ from the text at the tag `v0.3`.
