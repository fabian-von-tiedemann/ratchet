# D-2026-11-16-code-owner: agents get an account of their own, and the code owner approves

- Date: 2026-11-16
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-16-scope (point 3)
- Ends: none

Names are left out of this file. Where the original names an account or a user, the name is replaced by a word in square brackets. The mark `[...]` shows where this file leaves out part of a message. Nothing else in the original is changed.

## Question

The question came in two messages. The first described the arrangement, and the second put it as the third of three choices, with the advice "ja" (yes) to all three.

From the first message, original in Swedish:

> **3. Nytt: agenternas bidrag till Ratchet går via ett eget maskinkonto på GitHub,** inte via tokens från ditt konto. [...] **Med ett maskinkonto:**
>
> - **Kontot:** du skapar ett vanligt GitHub-konto för agenterna, till exempel `[kontonamn]`. GitHub tillåter ett maskinkonto per person. Kontot får rollen Write i Ratchet.
> - **Tokens:** `[användare 1]`, `[användare 2]` och `[användare 3]` får var sin token från det kontot. Var och en kan återkallas för sig.
> - **Grenskyddet:** ett godkännande från dig krävs. Du som administratör kan merga ditt eget direkt, men agenterna kan bara föreslå, och du godkänner.

Translation into English:

> **3. New: the agents' contributions to Ratchet go through a machine account of their own on GitHub,** not through tokens from your account. [...] **With a machine account:**
>
> - **The account:** you create an ordinary GitHub account for the agents, for example `[account name]`. GitHub allows one machine account per person. The account gets the role Write in Ratchet.
> - **Tokens:** `[user 1]`, `[user 2]` and `[user 3]` each get a token of their own from that account. Each one can be revoked on its own.
> - **Branch protection:** one approval from you is required. You as administrator can merge your own directly, but the agents can only propose, and you approve.

From the second message, original in Swedish:

> Tre val väntar fortfarande på dig. Mitt råd är ja på alla tre: [...] 3. Låt agenternas bidrag till Ratchet gå via ett eget maskinkonto.

Translation into English:

> Three choices are still waiting for you. My advice is yes to all three: [...] 3. Let the agents' contributions to Ratchet go through a machine account of their own.

## Answer

Original, in Swedish:

> ja på alla tre

Translation into English:

> yes to all three

## What follows

- `.github/CODEOWNERS` names the maintainer as the owner of every path. It is in the repo from this version.
- The maintainer sets up the account and the protection on `main`: a pull request, one approval, the code owner's review, administrators exempt. Until that is done and read back, the register lists the rules that lean on it as "text only for now".
- This replaces point 3 of [D-2026-11-16-scope](D-2026-11-16-scope.md), which had no required approval, included administrators and left code ownership for later. The condition that decision set for code ownership, an identity of their own for the agents, is what this decision provides.
- `ratchet.one-approver` and `ratchet.checks-owner-read` name a check from this version. The share of core rules that are text only falls from 21 to 19 of 35. The share counts what kind of ratchet a rule has, not whether this repo meets the rule.
- `ratchet.protected-main` says that the protection applies to administrators too. This repo does not meet that part of the rule, and its register says so. Whether the rule should allow an exception for a sole owner is an open question for the next version.
