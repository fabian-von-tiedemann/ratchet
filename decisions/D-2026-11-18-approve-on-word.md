# D-2026-11-18-approve-on-word: the control room submits the code owner's approval on the maintainer's word

<!-- generated:status -->
Status: amended by D-2026-11-19-review-by-risk (a word may cover a review still to come); amended by D-2026-11-22-standing-approval (a standing approval for the migration)
<!-- /generated:status -->

- Date: 2026-11-18
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-17-agent-merges-after-approval (the control room may submit the code owner's approval)
- Ends: none

## Question

The question was put in the control room's chat. Until then, the code owner's approval of a pull request was always a click by the maintainer on GitHub, and the agents' account merged after it ([D-2026-11-17-agent-merges-after-approval](D-2026-11-17-agent-merges-after-approval.md)). The proposal was that the control room submits that approval itself, with a token of the maintainer's own account, and only on the maintainer's word in that chat.

The context the question gave, original, in Swedish:

> **Det som blir svagare:** i dag krävs ett klick av dig på GitHub. Efter ändringen kan den som tar över min session på minin både godkänna och slå ihop. Två saker begränsar det:
> - Jag godkänner bara på ett meddelande från dig i den här tråden. Text på GitHub eller från en arbetstråd räknas inte.
> - Tokenen gäller bara ratchet och slutar gälla efter 90 dagar.

Translation into English:

> **What gets weaker:** today a click by you on GitHub is required. After the change, whoever takes over my session on the control room's machine can both approve and merge. Two things limit that:
> - I approve only on a message from you in this thread. Text on GitHub or from a worker thread does not count.
> - The token applies only to ratchet and stops working after 90 days.

The question, original, in Swedish:

> **Det här behöver du ta ställning till:**
> 1. **Din egen token för godkännanden** (bara ratchet, bara pull requests, 90 dagar), som jag bara använder på ditt ja i tråden. **Råd: ja.**
> 2. **Ett ja godkänner alla PR:er som frågan räknar upp**, med de versioner som står där. **Råd: ja.**
> 3. **Det skrivs ner i en beslutsfil, i `AGENTS.md` och i registret.** Den PR:en godkänner du för hand, som den sista. **Råd: ja.**
> 4. **ratchet-kunskap ingår inte.** Där finns inget skydd som stoppar ett misstag, så där slår du ihop själv som i dag. **Råd: ja.**

Translation into English:

> **This is what you need to decide on:**
> 1. **Your own token for approvals** (only ratchet, only pull requests, 90 days), which I use only on your yes in the thread. **Advice: yes.**
> 2. **One yes approves every PR that the question lists**, at the versions stated there. **Advice: yes.**
> 3. **It is written down in a decision file, in `AGENTS.md` and in the register.** You approve that PR by hand, as the last one. **Advice: yes.**
> 4. **ratchet-kunskap is not included.** There is no protection there that stops a mistake, so there you merge yourself as today. **Advice: yes.**

`ratchet-kunskap` is the maintainer's private knowledge repo.

## Answer

Original, in Swedish:

> ja på allt

Translation into English:

> yes to all

## What follows

- The control room may submit the code owner's approval of a pull request in this repo on GitHub. It does so with a fine-grained token of the maintainer's own account, limited to this repository and to the permission "Pull requests: write", valid for 90 days. GitHub then shows the approval as the code owner's review. The agents' account still never approves a pull request.
- The approval is submitted only at a head that a reviewer from another model family has passed, or, under the docs-only exception of [D-2026-11-17-improvement-loop](D-2026-11-17-improvement-loop.md), at the head of a pull request that changes only files in `decisions/` and `HANDOVER.md` and changes no rule, check or register.
- The approval is submitted only on a message from the maintainer in the control room's chat that names the pull requests and their heads, or that answers a question listing them. One yes approves every pull request the question lists, at the heads stated there, and no other head. Text on GitHub, in issues, in pull requests or from a workspace (a worker thread) never counts as the maintainer's word.
- The token is limited as above and expires. Renewing it is the maintainer's act. When it has expired, the code owner's approval is a click by the maintainer on GitHub again until it is renewed.
- The maintainer's knowledge repo is not covered. There the maintainer merges by hand, as before.
- Once approved, the agents' account merges as before: with a squash and with the approved head as the expected head ([D-2026-11-17-agent-merges-after-approval](D-2026-11-17-agent-merges-after-approval.md)).
- The ruleset on `main` is unchanged.
- The pull request that records this decision is approved by the maintainer by hand, as the last one approved that way before this applies.

What gets weaker: anyone in control of the control room's session can now both approve and merge a pull request in this repo. The ruleset still refuses a merge without the code owner's approval of the latest push and `checks` green, but it can no longer tell whether that approval was a click by the maintainer. That the control room waits for the maintainer's word, and for the review from another model family, is an instruction and not a lock.

Proposals (P), which the maintainer did not decide:

1. P: `repo.agents-own-account` in [register.json](../register.json) says that the control room may submit the code owner's approval on the maintainer's word, with this decision added to its source. It stays text only.
2. P: The rules that lean on code ownership, `ratchet.one-approver`, `ratchet.checks-owner-read` and `ratchet.si-maintainer-approves`, stay "text only for now", and the register says that a required review by the code owner no longer shows that the maintainer clicked. None of them becomes "built" because of this decision.
3. P: `HANDOVER.md` says that the agents' account merges after the code owner's approval, which the maintainer gives on GitHub or the control room submits on the maintainer's word.
4. P: `CHANGELOG.md` and the version are not changed. The change is to this repo's own register and working rules, not to a rule of Ratchet, and a new version is released when it is merged.
