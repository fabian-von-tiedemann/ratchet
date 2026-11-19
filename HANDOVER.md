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
- **The agents' account merges, and waits on two approvals of the same head.** By [D-2026-11-17-agent-merges-after-approval](decisions/D-2026-11-17-agent-merges-after-approval.md) it merges a pull request with a squash, and with that head as the expected head, after the code owner has approved the head and a reviewer from another model family has passed it. The code owner's approval is the maintainer's click on GitHub, or the control room submits it with a token of the maintainer's own account on the maintainer's word in the control room's chat, only at a head that has passed that review or falls under the exception below ([D-2026-11-18-approve-on-word](decisions/D-2026-11-18-approve-on-word.md)). A PR that changes only files in `decisions/` and this file, and changes no rule, check or register, needs no such reviewer ([D-2026-11-17-improvement-loop](decisions/D-2026-11-17-improvement-loop.md)). Auto-merge is not used. The ruleset on `main` refuses the merge without the code owner's approval of the latest push and `checks` green. Nothing stops the account from merging before the other review has passed, or the control room from approving without the maintainer's word, so `repo.agents-own-account` stays text only.
- **A new version waits on a merge that raises it.** The release workflow from #9 tags and releases a version when the commit that raises `ratchet.json` to it reaches `main`. 0.4 was released that way on 2026-11-18, when #12 was merged, and a daily scheduled run turns red while any version that `main` has had lacks its tag or its release.
- **A rule whose check is not built** stays "text only for now" in [REGISTER.md](REGISTER.md), and the register says what is missing.

## Who acts next

- **The maintainer** approves the exact head of each PR, on GitHub or by a word in the control room's chat, renews the token for approvals, changes settings, and answers the open issues with the label `question`.
- **The control room** starts a workspace for each open PR or issue with work left, has every head reviewed by a model from another family (except a PR that changes only files in `decisions/` and this file, and changes no rule, check or register, [D-2026-11-17-improvement-loop](decisions/D-2026-11-17-improvement-loop.md)), posts the verdict on the PR, submits the code owner's approval of that head when the maintainer gives the word in the control room's chat, and merges the PR once the code owner has approved that same head. It never starts a third round after two rejections of the same kind: it takes a different approach to the maintainer as a decision.

## Next step

1. 0.7 was published by the merge of #44 on 2026-11-19. The maintainer applied the tag ruleset `tags-stay` the same day, and the control room read it back with the agents' account ([checks/README.md](checks/README.md#the-tag-ruleset)). The PR after 0.7 records that read-back, moves `ratchet.irreversible-waits` to "built" in [REGISTER.md](REGISTER.md) and corrects item 3 of [D-2026-11-19-locks-not-parsing](decisions/D-2026-11-19-locks-not-parsing.md) ([D-2026-11-19-tripwire-and-settings](decisions/D-2026-11-19-tripwire-and-settings.md)). The release workflow created the tag `v0.7` and its release under the ruleset. Not tried: a deletion or move of a tag by the agents' account, because it would put a published tag at risk.
2. Next, the trial of a sandbox for the worker threads ([D-2026-11-17-harness-sandbox-risk](decisions/D-2026-11-17-harness-sandbox-risk.md), item 2), which is the lock on deleting outside the working tree. The tripwire is not.
3. After it, the parts of the loop from [D-2026-11-17-pull-and-budget](decisions/D-2026-11-17-pull-and-budget.md): measuring, the daily reading of moved sources, the clean-out and the search.
4. Follow-ups: #33 (`expected_tests.py` accepts a test name with a Unicode line separator) and #35 (`upgrade.py` leaves a given `--source` out of the commands it prints).

Proposal (P), not decided by the maintainer: a secret scan for this repo, which issue #17 waits on, comes after these.
