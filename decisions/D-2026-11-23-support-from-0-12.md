# D-2026-11-23-support-from-0-12: support registers from 0.12 on, and remove what served only older ones

- Date: 2026-11-23
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Background. A sweep of the repo on 2026-11-23 listed what exists only for a project on a version before 0.12, in thirteen findings ranked by the cost to keep against the risk of removing. The one project that follows Ratchet is on 0.12, adopted by reference. No project follows 0.3 to 0.11. Findings 1 to 8 were: the registers and `ratchet.json` of 0.3 to 0.9 as fixtures of `upgrade.py`, and their test (1); the allowances of the reader of an older `ratchet.json` for the forms before 0.10 (2); the refusal of a release before 0.11 in `upgrade.py`, and the fake `upgrade.py` of 0.10 in its tests (3); the notes on the form of `register.json` for 0.10, 0.11 and 0.12 (4); the search of `init.py` for the `AGENTS.md` that a start before 0.11 left (5); the paragraph of `UPGRADING.md` for a clone on 0.10 or earlier (6); the sentence there on `check_register.py --write`, which 0.9 had (7); and the sentences "a register that follows 0.3 or later" (8). Finding 9 was the offline mode of `upgrade.py`, `--from` and `--source`, and finding 10 the note for a project that keeps a copy of a check that reads `ratchet.json`.

The question, asked by the control room in the maintainer's chat on 2026-11-23. Original, in Swedish:

> *Mitt råd:* - **Ta bort 1–8 i en PR efter 0.13**, så att vi inte försenar släppet. Allt får ersättas av en enda testfil för 0.12, den version som faktiskt används. PR:en rör kontrollerna, så `base` blir rött och du slår ihop den för hand. - **Låt 9 och 10 vara tills vidare.**

Translation:

> *My recommendation:* - **Remove 1–8 in one PR after 0.13**, so that we do not delay the release. All of it may be replaced by a single test file for 0.12, the version that is actually used. The PR touches the checks, so `base` goes red and you merge it by hand. - **Leave 9 and 10 for now.**

## Answer

Original, in Swedish:

> Ja

Translation:

> Yes

## What follows

- Findings 1 to 8 are removed in one pull request after the release of 0.13. Findings 9 and 10 stay as they are, and the sweep's findings 11 to 13 are not part of this decision.
- Removing a test, a fixture or a code path that serves only a register, or a `ratchet.json`, of a version before 0.12 is allowed. Removing a test loosens a check in form, so the pull request cites this decision, as "How to change a check" in [AGENTS.md](../AGENTS.md) asks.
- The fixtures of 0.3 to 0.9 are replaced by one fixture of 0.12, a register by reference as adopt mode of 0.12 writes it, so that `upgrade.py` still runs on real released data.
- P: the `ratchet.json` of 0.3 and of 0.9 stay under `checks/fixtures/upgrade/released/`, without their registers. `test_budget.py` reads them to show where each rule of the redraw went, which serves no register of an older version, so this decision does not cover removing them.
- An upgrade starts from 0.12 or later. A register on an earlier version upgrades with Ratchet 0.13 first.
- The pull request changes the checks and their tests, so the base branch's checks cannot judge it: the job `base` fails, `checks` stays red, and the maintainer reads it and merges it as an administrator ([checks/README.md](../checks/README.md#from_basepy)).
- This follows the observation in [HANDOVER.md](../HANDOVER.md): until a second project follows a tag, nothing is written for compatibility older than the latest version a real project follows.
