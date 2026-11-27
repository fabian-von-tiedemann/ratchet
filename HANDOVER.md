# Handover

Who waits on whom, who acts next, and the order of the work (`ratchet.work-in-issues`). It is replaced, not appended to, after every important event, and repeats no fact that lives elsewhere.

## Read first

Read in the order [AGENTS.md](AGENTS.md#read-first) gives. The state lives in three places:

- [REGISTER.md](REGISTER.md): the rules, and the status of each check.
- The open issues and pull requests: the work and the reviews. Questions for the maintainer have the label `question`.
- [decisions/](decisions/): why. Read a decision when a rule's `source` or a text names it, never the whole directory.

## Who waits on whom

- **A merge** waits on the code owner's approval of the exact head, a reviewer from another model family passing it, and `checks` green ([The main branch](AGENTS.md#the-main-branch)).
- **A change to a check** merges only after two reviewers from two model families pass the same head (`repo.review-classes`), and is built only after its plan was reviewed ([D-2026-11-25-plan-review-before-build](decisions/D-2026-11-25-plan-review-before-build.md)).
- **A pull request that the base branch's checks cannot judge** waits on the maintainer, who merges it as an administrator ([How to change a check](AGENTS.md#how-to-change-a-check)).
- **A change of the form of `ratchet.json` or `register.json`** waits on the maintainer's word on that change, and restarts the count of the first criterion of 1.0.
- **A release** waits on a release pull request and the maintainer's word ([How to release a version](AGENTS.md#how-to-release-a-version)).
- **`ratchet.owner-paths` and `repo.maintainer-approves`** stay text only until these steps have been tried and recorded:
  1. The ruleset on `main`, read with `gh api repos/fabian-von-tiedemann/ratchet/rulesets` and then `rulesets/<id>`, shows one required approval, the code owner's review required, approvals dismissed on a new push, and the job `checks` required.
  2. The agents' account has the role Write and no more.
  3. A pull request from the agents' account, with its checks green and an approval from that account, cannot be merged before the code owner approves.
  4. After the code owner approves, a new push from the agents' account removes the approval.

## Who acts next

- **The maintainer** approves heads, gives the word for a release, renews the token for approvals, changes settings, and answers the issues labeled `question`.
- **The control room** starts a workspace for the work left, has each head reviewed, posts the verdict, submits the code owner's approval on the maintainer's word, and merges.

## The order of the work toward 1.0

By [D-2026-11-26-road-to-1-0](decisions/D-2026-11-26-road-to-1-0.md) and [D-2026-11-26-field-comparison](decisions/D-2026-11-26-field-comparison.md):

1. The checks for the criteria of 1.0: #71 and #72.
2. Points 2 and 3 of [D-2026-11-27-stale-text](decisions/D-2026-11-27-stale-text.md), each in a pull request of its own.
3. Checks for the start rules `ratchet.no-secrets` and `ratchet.decision-as-file`; point 2 builds the format check of the latter.
4. A tried recipe.
5. Questions for the maintainer (Q): #170, and what counts as the first red check in the map-only mode.
6. Follow-ups, when the code they name is touched again: #162, #33, #35 and #21.

After that: the checks #73 and #74, the proposals and questions among the issues, building `ratchet.irreversible-waits` in every harness, the sandbox trial in #49, and the loop of [D-2026-11-17-pull-and-budget](decisions/D-2026-11-17-pull-and-budget.md).
