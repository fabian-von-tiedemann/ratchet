# Handover

What a new session needs that GitHub does not show: who waits on whom, who acts next, and the next step (`ratchet.work-in-issues`). It does not copy what GitHub already shows: which PRs are open, their reviews and checks, which issues are open, or the settings. Read those there, after [AGENTS.md](AGENTS.md) and [REGISTER.md](REGISTER.md):

- the open pull requests, with their descriptions and review verdicts in the comments
- the open issues, and among them the open questions for the maintainer, which have the label `question`
- the decisions in [decisions/](decisions/).

Replaced, not appended to, after every important event. The [decision](decisions/D-2026-11-17-workflows-checks-handover.md) that gave it this form is from 2026-11-17.

## Who waits on whom

- **Rules that lean on code ownership** wait on the protection of `main`. These are `ratchet.one-approver`, `ratchet.checks-owner-read` and `ratchet.si-maintainer-approves`, which stay "text only for now" in [REGISTER.md](REGISTER.md). They become "built" in a PR of their own, after four steps:
  1. The protection on `main` shows one required approval, the code owner's review required, approvals dismissed on a new push, and the job `checks` as a required status check. The ruleset that protects `main` is listed by `gh api repos/fabian-von-tiedemann/ratchet/rulesets`, and its rules are read from `gh api repos/fabian-von-tiedemann/ratchet/rulesets/<id>`.
  2. The agents' account has the role Write and no more.
  3. A pull request from the agents' account, with its checks green and an approval from that account, cannot be merged before the code owner approves.
  4. After the code owner approves, a new push from the agents' account removes the approval.
- **The agents' account merges, and waits on two approvals of the same head.** By [D-2026-11-17-agent-merges-after-approval](decisions/D-2026-11-17-agent-merges-after-approval.md) it merges a pull request with a squash, and with that head as the expected head, after the code owner has approved the head and a reviewer from another model family has passed it. A PR that changes only decisions and this file needs no such reviewer ([D-2026-11-17-improvement-loop](decisions/D-2026-11-17-improvement-loop.md)). Auto-merge is not used. The ruleset on `main` refuses the merge without the code owner's approval of the latest push and `checks` green. Nothing stops the account from merging before the other review has passed, so `repo.agents-own-account` stays text only.
- **The release of 0.4 waits on #12.** The release workflow from #9 is on `main`, and it tags and releases a new version when that version is merged. #12 raises the version to 0.4.
- **A rule whose check is not built** stays "text only for now" in [REGISTER.md](REGISTER.md), and the register says what is missing.

## Who acts next

- **The maintainer** approves the exact head of each PR, changes settings, and answers the open issues with the label `question`.
- **The control room** starts a workspace for each open PR or issue with work left, has every head reviewed by a model from another family (except a PR that changes only decisions and this file, [D-2026-11-17-improvement-loop](decisions/D-2026-11-17-improvement-loop.md)), posts the verdict on the PR, and merges the PR once the code owner has approved that same head. It never starts a third round after two rejections of the same kind: it takes a different approach to the maintainer as a decision.

## Next step

1. #12 is rebased on `main` and reviewed by a model from another family at its new head. The maintainer approves that head, and the agents' account merges it. The merge publishes 0.4.
2. Then the build order after 0.4 from [D-2026-11-17-pull-and-budget](decisions/D-2026-11-17-pull-and-budget.md): first the upgrade path, `checks/upgrade.py` with `UPGRADING.md`, and the rule budget. Then the issue form for proposals, #23 together with the phases, and the parts of the loop: measuring, the daily reading of moved sources, the clean-out and the search.

Proposal (P), not decided by the maintainer: a secret scan for this repo, which issue #17 waits on, comes after these.
