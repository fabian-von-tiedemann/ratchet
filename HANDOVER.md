# Handover

The state of Ratchet between sessions (`ratchet.work-in-issues`). Replaced, not appended to, after every important event. Every session reads it after [AGENTS.md](AGENTS.md) and [REGISTER.md](REGISTER.md).

Last replaced: 2026-11-17, after PR #13 was merged.

## What is done

- PR #13 is merged: [D-2026-11-17-new-approaches](decisions/D-2026-11-17-new-approaches.md). PR #10 and PR #12 were each rejected in two review rounds in a row with the same kinds of failure, and the maintainer chose a new approach for each. A PR that adds a rule raises the version and is released on merge.
- PR #11 is approved by the code owner and waits to be merged. It records `D-2026-11-17-proposals-2-6`, which says what happens with the proposals in issues #2 to #6. Issue #4 is closed as not planned.

## What is running

Each PR below is built in a workspace of its own and is reviewed by a model from another family before it is merged. Proposal (P), not decided by the maintainer: a rebuilt PR starts again at review round 1.

- **PR #9, release on merge.** Rejected in round 1: the changelog entry was found inside fenced code, a queued run could drop a version, and a tag could appear between the check and the release. The logic is moving into a tested script under `checks/`.
- **PR #10, issue #8, the source watch.** Rebuilt at `a0e58a3`, so that no text from a source or from an API response reaches an issue or a log line. It is under review in round 1 of the new approach.
- **PR #12, issue #2, expected tests ran.** Being rebuilt with the check in a process of its own, outside the tests it watches, and with the version raised to 0.4.

## What waits on what

- **Workflow files.** PR #9, PR #10 and PR #12 each add or change a workflow file. PR #9 holds `.github/workflows/release.yml` in its diff. PR #10 holds `watch-sources.yml` in its description. PR #12's rebuild is to hold the new `checks.yml` in its description. The agents were told that their token cannot push workflow files, but it carries the `workflow` scope, read back on 2026-11-17. How workflow files reach `main` is issue #15.
- **PR #12 waits on PR #9.** 0.4 is released on merge only when the release workflow is on `main`.
- **Issues #5 and #6** wait on PR #12. They become two lines in the requirements on the review script, in one PR.
- **Issue #3** waits on the check of the protection on `main`. Its requirement goes into that check.
- **The protection on `main`**, read back on 2026-11-17. `main` is protected by the ruleset `skydd-main`, not by classic branch protection, which reads as 404. The ruleset:
  - requires one approval and the code owner's review
  - dismisses approvals on a new push
  - requires that the latest push is approved by someone other than the person who pushed it.

  It does **not** require the job `checks` as a status check. The agents' account `fabian-agent` has the role Write. Step 1 of the steps below is therefore not met.
- **Code ownership.** `ratchet.one-approver`, `ratchet.checks-owner-read` and `ratchet.si-maintainer-approves` stay "text only for now" in [REGISTER.md](REGISTER.md). They become "built" in a PR of their own, after these steps:
  1. The protection on `main` shows one required approval, the code owner's review required, approvals dismissed on a new push, and the job `checks` as a required status check.
  2. `fabian-agent` has the role Write and no more. Read back 2026-11-17.
  3. A pull request from the agents' account, with its checks green and an approval from that account, cannot be merged before the code owner approves.
  4. After the code owner approves, a new push from the agents' account removes the approval.
- **The agents' account must not merge by hand.** It may turn on auto-merge (`D-2026-11-17-auto-merge`, in PR #9). Nothing stops a merge by hand yet.
- **`ratchet.protected-main` is not met in this repo** and stays "text only for now". Whether the rule allows administrators to be exempt for a sole owner is an open question.
- `ratchet.no-secrets` is "text only for now". No secret scan runs here yet.

## Next step

Proposal (P), not decided by the maintainer: finish PR #9, then PR #10 and PR #12, each through review. Then build #5 and #6 together. After that, the secret scan for this repo.

## Open questions

Tracked as issues with the label `question`:

- #15: how workflow files reach `main`.
- #16: whether the job `checks` becomes a required status check on `main`.

Not yet an issue: how to check decision files and the glossary ([D-2026-11-16-register-only](decisions/D-2026-11-16-register-only.md)). Two attempts to read them as text were reviewed, and both still let text hide. The proposal on the table is a small data part for each decision, checked strictly, with the prose left as prose and outside the check.
