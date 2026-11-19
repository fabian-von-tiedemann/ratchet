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
- **A new version waits on a release pull request and the maintainer's word.** By [D-2026-11-19-batched-releases](decisions/D-2026-11-19-batched-releases.md), the next version is collected under the first entry of the changelog, headed `(unreleased)`, and no merge publishes it. The release is a pull request of its own that gives the entry its date and moves the tag that the README fetches. It is merged on the maintainer's word, at most once a week or when the maintainer asks, and a fix for a security fault is released at once. Its merge publishes the version through the release workflow, and a daily scheduled run turns red while any version dated on `main` lacks its tag or its release. 0.9 was the first version released this way, on 2026-11-19. A pin of a source moves in `sources.json` with no new version.
- **A rule whose check is not built** stays "text only for now" in [REGISTER.md](REGISTER.md), and the register says what is missing.

## Who acts next

- **The maintainer** approves the exact head of each PR, on GitHub or by a word in the control room's chat, renews the token for approvals, changes settings, and answers the open issues with the label `question`.
- **The control room** starts a workspace for each open PR or issue with work left, has every head reviewed by a model from another family (except a PR that changes only files in `decisions/` and this file, and changes no rule, check or register, [D-2026-11-17-improvement-loop](decisions/D-2026-11-17-improvement-loop.md)), posts the verdict on the PR, submits the code owner's approval of that head when the maintainer gives the word in the control room's chat, and merges the PR once the code owner has approved that same head. It never starts a third round after two rejections of the same kind: it takes a different approach to the maintainer as a decision.

## Next step

1. After the merge of the release pull request of 0.9, the control room reads back the tag `v0.9` and its release, which the release workflow makes after the merge. Until the run has tagged, the command in the README that fetches `v0.9` fails, and the scheduled run is red if it never does. The next version starts as a new first entry headed `(unreleased)`, opened by the first pull request that changes what is released.
2. Next, the loop, as one loop: scanning the feeds in the sources list of the maintainer's knowledge repo, and the daily reading of the sources that moved past their pin in `sources.json`, such as #52 and #53. These are parts of the loop from [D-2026-11-17-pull-and-budget](decisions/D-2026-11-17-pull-and-budget.md), beside measuring and the clean-out.
3. The draft decision on what 1.0 means, item 5 of [D-2026-11-19-batched-releases](decisions/D-2026-11-19-batched-releases.md): a proposal with criteria for the maintainer to take a position on, such as a form unchanged for some weeks, a start with one command, at least one other repo that uses Ratchet, and a share of the core with checks.
4. The proposals from the reading of the sources moved in 0.8: #46 (say what a fresh reviewer still sees from its host, and probe it) and #47 (name sending something outside the project among the steps that cannot be undone).
5. Follow-ups: #33 (`expected_tests.py` accepts a test name with a Unicode line separator) and #35 (`upgrade.py` leaves a given `--source` out of the commands it prints).

Observation (O): the sandbox from the trial in #49 ([D-2026-11-17-harness-sandbox-risk](decisions/D-2026-11-17-harness-sandbox-risk.md), item 2) is on for the agents' sessions. Inside it, the whole suite passes since #51 and #55. It is the lock on deleting outside the working tree, and the tripwire is not.

Proposal (P), not decided by the maintainer: a secret scan for this repo, which issue #17 waits on, comes after these.
