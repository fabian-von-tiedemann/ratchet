# D-2026-11-23-two-reviewers-for-check-code: a change to a check's code is reviewed by two model families other than the author's

- Date: 2026-11-23
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Background. During the migration of [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md), several pull requests that changed a check's code were reviewed by two reviewers from two model families other than the author's, as choice 3 of [D-2026-11-22-standing-approval](D-2026-11-22-standing-approval.md) set for those steps. On several of them the second reviewer found real defects that the first had passed: a run of `init.py --check` that disagreed with the real run, an untested re-exec and a broken recovery command in the upgrade, the following of links and silent defaults in the inventory, and a measure of overhead in the core that had been narrowed. The maintainer's knowledge repo held the position `two-reviewers-for-risky-changes` as watched, with the condition "a second reviewer from a third model family, on changes to checks, finds what the first reviewer missed". That condition is met.

The question, asked by the control room in its proposal of Monday 2026-11-23. Original, in Swedish:

> **Två granskare på kontrollkod** (`two-reviewers-for-risky-changes`, bevakas). Villkoret för att ändra oss är uppfyllt: en andra granskare från en tredje modellfamilj hittade det den första missade, och det har hänt flera gånger i vår egen migrering. Neon gjorde det på #115, #117 och #119, och Astra på #122. Förslag: en regel på prov i Ratchet om att ändringar av en kontrolls kod granskas av två familjer. **Mitt råd: ja, efter 0.11.**

Translation:

> **Two reviewers on check code** (`two-reviewers-for-risky-changes`, watched). The condition for changing our minds is met: a second reviewer from a third model family found what the first one missed, and it has happened several times in our own migration. Neon did it on #115, #117 and #119, and Astra on #122. Proposal: an experimental rule in Ratchet that changes to a check's code are reviewed by two families. **My recommendation: yes, after 0.11.**

"Neon" and "Astra" are review models, each from a model family other than the control room's. The numbers are Ratchet's own pull requests.

## Answer

Original, in Swedish:

> Ja på dina råd

Translation:

> yes to your recommendations

Later, before 0.12 was released, the maintainer said yes again, to doing the work after 0.12. That word is not quoted here.

## What follows

- `ratchet.review-by-risk`, experimental, gets one clause: a PR that changes a check's code, in the paths the project lists as its checks, is reviewed by two reviewers from two model families other than the author's, each at the same head, and it merges only when both have passed that head. Its ratchet stays text only, and says why: a check in the repo cannot see who reviewed a head, or from which model family.
- It is a clause and not a rule of its own, so it takes no place under the cap of 17, which is full. It fits the rule: both say how deep a review goes, read from the paths a PR changes, and both are text only, so the merge rule of [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md) allows it. It does not enter the core.
- Ratchet's own rule `repo.review-classes` names this repo's checks: every file under `checks/`, its tests and fixtures among them, and under `.github/workflows/`. A PR that changes one is reviewed by two reviewers from two model families other than the author's, at the same head. This repo's register adopts the new text of `ratchet.review-by-risk`.
- The change enters in 0.13 and is released with it ([D-2026-11-19-batched-releases](D-2026-11-19-batched-releases.md)).

What gets heavier: every PR that changes a check waits for a second review, and the quota of a second reviewer limits how many can run at once. Whether both reviews happened, and from which families, is an instruction and not a lock.

Proposals (P), which the maintainer did not say in words:

1. P: The paths of check code in this repo are `checks/` and `.github/workflows/`. The control room's practice of also asking a second reviewer on a PR that changes `.github/`, `ratchet.json`, `register.json` or `templates/` stands beside it, and is not made a rule here.
2. P: If the second reviewer is unavailable, the PR waits and the control room reports it, as `ratchet.review-by-risk` already says of a model that is unavailable. It does not merge on one review.
