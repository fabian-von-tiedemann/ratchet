# The control room

How a long-lived project is run with AI agents: one coordinating session, the control room, and many short-lived workspaces. The rules below follow the same form as [RATCHET.md](RATCHET.md): key, rule, ratchet and source.

## What it is

The control room is one long-running agent session that holds the project together. It does not build the product. It:

- keeps the status and the handover in one status issue
- starts workspaces for packages of work, each with its own issue, branch and worktree
- starts reviews and records their outcome
- merges when the checks are green and the review has passed
- writes the owner's decisions down
- brings the owner at most five real choices at a time, each with a recommendation.

Workspaces build. Each one works on one issue, on its own branch, and reports back to the control room with a PR link and the exact commit (head). Workspaces never ask the owner directly.

## Rules

| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.cr-does-not-build | The control room does not build the product. It may make small fixes after a review and maintain its own tools. Building happens in workspaces. | Text only | Own experience |
| ratchet.cr-reads-first | Every session starts by reading, in order: the working rules (AGENTS.md), the control room's handbook, the register, the latest handover in the status issue, and the open PRs and issues. Everything else is read only when a task needs it. | Text only | Own experience |
| ratchet.cr-handover | The status lives in the status issue, not in the agent's memory. The handover is a short list: what is running, what waits on what, and the next step. It is replaced after every important event. When a session grows too long, a new session starts from the handover. | A script writes the handover and the automatic status into the status issue | Own experience |
| ratchet.cr-memory | The agent's own memory holds only ways of working and the owner's preferences, never the status of the work. | Text only | Own experience |
| ratchet.cr-workspace | A package of work gets its own issue (assignment, files it may change, cap in time or cost, stop rule), its own branch and its own worktree from the main branch. The workspace reports back with PR link and head. | Text only | Own experience |
| ratchet.cr-delegate-review | Reviews run in new threads on a model from a different family, with an assignment built by a script (see `ratchet.fresh-context`). Results come back as notifications to the control room, which records the outcome and posts the verdict on the PR. | The review script's lock and outcome files | Own experience |
| ratchet.cr-analysis-model | Whole-picture, scope and architecture assessments run on the strongest available model, in a fresh context. If that model is unavailable, the task stops and is reported, without a silent switch. | Text only | Own experience |
| ratchet.cr-wake | A scheduled wake-up every hour reads the feed of new PRs, checks and issues and moves forward whatever is ready. A full status update runs about every two hours. | The schedule and the status script | Own experience |
| ratchet.cr-next-task | When nobody asks anything, the control room takes the next allowed task. A blocked task gets its cause written down, and an independent task is taken instead. Reporting status alone is not progress. | Text only | Own experience |
| ratchet.cr-quiet-hours | During the owner's quiet hours, the control room only continues work already under way and trials with a mandate, and collects questions for the morning. It asks questions at night only when the owner is writing. | Text only | Own experience |
| ratchet.cr-background-wait | A workspace that starts a long run in the background keeps its thread alive until the run is done, with the host's wait mechanism. It does not end its turn while a run it promised to report on is still going. The control room checks at every wake-up that promised runs are actually running. | Text only: thread waits pass no check in the repo | Own experience |
| ratchet.cr-verify-reports | The control room verifies a workspace's report against the repo, the PR and the running processes before acting on it. A report of success is checked independently (see `ratchet.evidence-before-done`). | Text only | Own experience; obra/superpowers `verification-before-completion` |
| ratchet.cr-lead-with-ask | Every message to the owner leads with what the owner must decide or do, in one sentence with a recommendation, before any background. If nothing is needed, it says so. | Text only | Own experience |

## A day in the control room

1. **Wake-up.** Fetch, read the feed and the status issue, check that promised runs are running.
2. **Act.** Merge what is green and reviewed. Start reviews for new heads. Send findings to the workspaces. Take the next allowed task.
3. **Decide.** Bring real choices to the owner, at most five, each with a recommendation. Write the answer down as a decision file in a PR.
4. **Hand over.** Replace the handover after an important event.

## What it is not

- **Not a builder.** It coordinates, reviews and merges. It does not write the product.
- **Not a gatekeeper of everything.** Housekeeping and technical choices are decided by the control room and shown in PRs. Only real choices go to the owner.
- **Not a memory.** If the status is only in a session, it is lost when the session ends.
