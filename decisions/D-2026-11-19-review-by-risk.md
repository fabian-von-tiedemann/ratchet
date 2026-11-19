# D-2026-11-19-review-by-risk: review by risk, a word that covers a review still to come, and no new round for a finding that does not block

- Date: 2026-11-19
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The maintainer had said that the work takes too long. Original, in Swedish:

> det tar en väldans tid ...

Translation into English:

> it takes an awful lot of time ...

The control room's answer began, original, in Swedish:

> Ja, det gör det, och tiden går mest åt till två saker.

Translation into English:

> Yes, it does, and the time goes mostly to two things.

It then named the two things. This is a summary, not the verbatim text: each PR passes two or three steps with a wait between them, as a workspace builds it, a model from another family reviews it for 10 to 20 minutes when it changes code, and a finding means another round; and the control room asks the maintainer and waits for a yes between the steps, even when the answer is obvious.

Three choices followed, each with a recommendation. Original, in Swedish:

> 1. **Granskning efter risk.** PR:er med bara dokumentation, sidan eller tester granskas av Codex med medelhög ansträngning, vilket tar några minuter. Kontroller, släppflöde, krokar och regler får fortsatt hög ansträngning. **Råd: ja.** Det är regeln om granskning efter risk som redan står i byggordningen. Den skrivs ner som en experimentell regel.
> 2. **Ditt ja kan gälla i förväg.** Du säger till exempel "ja #57 när Codex godkänner", och då slår jag ihop direkt vid den head Codex godkänner, utan att fråga igen. **Råd: ja.** Det kräver en liten ändring av beslutet om godkännande i tråden. Tokenen ändras inte.
> 3. **Småfel som inte blockerar rättar jag själv** och samlar i nästa PR, i stället för att starta en ny runda. **Råd: ja.** Det gör jag redan delvis, men det blir då en fast regel.

Translation into English:

> 1. **Review by risk.** PRs with only documentation, the page or tests are reviewed by Codex at medium effort, which takes a few minutes. Checks, the release workflow, hooks and rules keep high effort. **Advice: yes.** It is the rule on review by risk that already stands in the build order. It is written down as an experimental rule.
> 2. **Your yes can apply in advance.** You say, for example, "yes #57 when Codex approves", and then I merge at once at the head Codex approves, without asking again. **Advice: yes.** It takes a small change to the decision on approval in the thread. The token does not change.
> 3. **Small faults that do not block, I fix myself** and collect in the next PR, instead of starting a new round. **Advice: yes.** I already do that in part, but then it becomes a fixed rule.

Codex is the reviewer from another model family. "The page" is the landing page. "The decision on approval in the thread" is [D-2026-11-18-approve-on-word](D-2026-11-18-approve-on-word.md). "The rule on review by risk that already stands in the build order" is item 3 of [D-2026-11-17-harness-sandbox-risk](D-2026-11-17-harness-sandbox-risk.md), which waited on the rule budget.

## Answer

Original, in Swedish:

> ja

Translation into English:

> yes

## What follows

- **1: review by risk is the experimental rule `ratchet.review-by-risk`,** in [CONTROL-ROOM.md](../CONTROL-ROOM.md), outside the core. Its classes are defined by paths, and for tests by their diff. The light class is a short list: `README.md`, `GLOSSARY.md`, `UPGRADING.md`, `MIGRATING.md`, `CHANGELOG.md`, `HANDOVER.md`, the directory `docs/`, and tests that are only added to. A test is a file `test_*` or a file under a directory `fixtures/`, and it is only added to when its diff removes no line, or removes only lines that it adds back unchanged apart from a comma or a closing bracket or brace. A PR whose paths are all light gets a light review: the same reviewer from another model family, at a lower effort. Every other path is in the full class, among them everything under `templates/`, `AGENTS.md`, `CONTROL-ROOM.md`, `SELF-IMPROVEMENT.md`, `RATCHET.md`, `CONTRIBUTING.md`, `.claude/`, `.github/`, the rest of `checks/`, `ratchet.json`, `register.json`, `sources.json` and `decisions/`, and so is a test whose diff removes or changes a test line, an assertion or a case, or that is deleted. A mixed PR gets the full review. This is narrower than the words of choice 1, "only documentation, the page or tests": a template or an instruction to agents is documentation that governs how agents work, and a change to a test can weaken what it covers, so both get the full review. In this repo, the light review is Codex at medium effort and the full one is Codex at high effort. The rule counts against the cap: 24 experimental rules under a cap of 25. It is text only, because the effort of a review is set where the reviewer runs and a check in the repo cannot see it. This repo adopts it, and the control room follows it. The exception of [D-2026-11-17-improvement-loop](D-2026-11-17-improvement-loop.md) is unchanged: a PR that changes only files in `decisions/` and `HANDOVER.md`, and changes no rule, check or register, needs no review from another model family at all.
- **2 amends [D-2026-11-18-approve-on-word](D-2026-11-18-approve-on-word.md).** A word from the maintainer in the control room's chat may name a pull request in advance, for example "yes #N when the review passes". It then covers the head that the review from another model family next approves, as long as nothing else was pushed after that review. It never covers a head that review did not pass. A failed round does not end it: it waits for the next head that passes. It ends when the first approved head it covers is merged: the control room submits the code owner's approval at that head and merges with that head as the expected head, as before. A push after that review, or after the merge, needs a new word. Text on GitHub, in issues, in pull requests or from a workspace never counts as the maintainer's word, as before. The token, its limits and the ruleset on `main` do not change. `AGENTS.md`, `HANDOVER.md` and the source of `repo.agents-own-account` in [register.json](../register.json) say so. D-2026-11-18-approve-on-word stands as written, apart from this.
- **3 is part of `ratchet.review-by-risk`.** A finding that the reviewer marks as not blocking the merge starts no new round. The control room fixes it in its next PR and says so on the PR that was reviewed. A finding that blocks starts a new round, as before. It is text only, like the rest of the rule.

What gets weaker: a light review looks less deeply, so a fault in documentation or in a test is more likely to pass. A test or a fixture with a line removed or changed, or deleted, and every path outside the light class, still gets the full review. A word given in advance covers a head the maintainer has not seen, so the review from another model family may be the only reading of that head before the merge, also when it changes a check (`ratchet.checks-owner-read`). That the control room waits for that review, and merges only the head it passed, is an instruction and not a lock, as before.

Proposal (P), which the maintainer did not decide: a PR under the exception of D-2026-11-17-improvement-loop has no review to wait for, so a word given in advance does not cover it. Its approval needs a word that names its head, as before.
