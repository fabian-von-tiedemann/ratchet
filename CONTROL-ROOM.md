# The control room

> **Experimental.** This file is outside Ratchet's core. Its rules may change in any version, and they are not counted in the share of rules that are text only. A project adopts them row by row, like any other rule.

How a long-lived project is run with several AI agents at once: one coordinating session, the control room, and many short-lived workspaces. The rules follow the same form as [RATCHET.md](RATCHET.md): key, rule, ratchet and source. The tables are generated from [ratchet.json](ratchet.json).

## When to use it

Use a control room when more than one agent works on the repo at the same time, or when work continues while the owner is away. A project with one agent and an owner who is present does not need it. The rules in RATCHET.md work without it.

## What it is

The control room is one long-running agent session that holds the project together. It:

- keeps the status and the handover in one place
- starts workspaces for work packages, each with its own issue, branch and worktree
- starts reviews and records their outcome
- merges when the checks are green and the review has passed
- writes the owner's decisions down
- brings the owner at most five decisions at a time, each with a recommendation.

Workspaces build. Each one works on one issue, on its own branch, and reports back to the control room with a PR link and the head.

The owner does not read every PR. Code is merged on green checks and a passed review by an independent reviewer. The owner reads decisions, changes to the register and changes to the checks themselves (`ratchet.checks-owner-read`). A project that wants the owner to read more adds those paths to the list.

## Rules

<!-- generated:table control-room -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.cr-does-not-build | The control room does not build the product\. It may make small fixes after a review and maintain its own tools\. Building happens in workspaces\. | Text only\: a check cannot tell which session wrote a commit | — |
| ratchet.cr-reads-first | Every session starts by reading\, in order\: the working rules \(AGENTS\.md\)\, the register\, the control room\'s handbook\, the latest handover\, and the open PRs and issues\. Everything else is read only when a task needs it\. | Text only\: a check cannot see what a session read | — |
| ratchet.cr-handover | The status lives in the status issue\. The handover is a short list\: what is running\, what waits on what\, and the next step\. It is replaced after every important event\. When a session grows too long\, a new session starts from the handover\. The agent\'s own memory holds only ways of working and the owner\'s preferences\, never the status of the work\. | Check\: a script writes the handover and the automatic status into the status issue | — |
| ratchet.cr-workspace | A work package gets its own issue \(assignment\, files it may change\, cap in time or cost\, stop rule\)\, its own branch and its own worktree from the main branch\. The workspace reports back with the PR link and the head\. | Text only until the project has an issue template with these fields as required | — |
| ratchet.cr-review | The control room starts each review with the review script \(see below\)\, records the outcome and posts the verdict on the PR\. | Check\: the review script\'s lock files and outcome files | — |
| ratchet.cr-analysis-model | Overall\, scope and architecture assessments run on the strongest model the project has\, in a fresh context\. If that model is unavailable\, the task stops and is reported\. There is no silent switch to another model\. | Text only\: a check in the repo cannot see which model ran a task | — |
| ratchet.cr-wake | A scheduled wake\-up reads the feed of new PRs\, checks and issues and advances whatever is ready\. The project sets the interval\. Hourly is a good default\, with a full status update every second time\. | Check\: the schedule exists and the status issue shows the time of the last wake\-up | — |
| ratchet.cr-next-task | When nobody asks anything\, the control room takes the next permitted task\. A blocked task gets its cause written down\, and an independent task is taken instead\. Reporting status alone is not progress\. | Text only\: a check cannot judge progress | — |
| ratchet.cr-quiet-hours | During the owner\'s quiet hours\, the control room only continues work already under way and experiments already approved\, and collects questions for the morning\. It asks at night only if the owner is already in the conversation\. | Text only\: messages pass no check | — |
| ratchet.cr-background-wait | A workspace that starts a long run in the background keeps its thread alive until the run is done\, using whatever wait mechanism its agent tool has\. It does not end its turn while a run it promised to report on is still going\. The control room checks at every wake\-up that promised runs are actually running\. | Text only\: thread waits pass no check in the repo | — |
| ratchet.cr-verify-reports | The control room verifies a workspace\'s report against the repo\, the PR and the running processes before acting on it \(see `ratchet.evidence-before-done`\)\. | Text only\: a check cannot see whether a report was verified | obra\/superpowers `verification-before-completion` |
| ratchet.cr-lead-with-ask | Every message to the owner leads with what the owner must decide or do\, in one sentence with a recommendation\, before any background\. If nothing is needed\, it says so\. | Text only\: messages pass no check | — |
<!-- /generated -->

## What can be undone

More autonomy is safe where a mistake can be undone. An agent goes ahead with what it can take back, and waits for the owner on what it cannot. The rule below names the steps, and its reference check stops them.

<!-- generated:table undo -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.irreversible-waits | An agent goes ahead with a step that can be undone\, and waits for the owner on a step that cannot\. Such a step goes ahead only with a recorded approval that names the step and the exact command\. The project lists the steps\. Ratchet\'s list is a force push\, creating or deleting a tag\, a release\, deleting outside the working tree\, and a change to the repository\'s settings\. | Check\: a hook in the agent\'s harness denies each listed step before it runs unless an approval names it\, and denies a command it cannot read with certainty\. It stands against an agent\'s mistake\, not against an agent that writes its own approval or works around the hook | — |
<!-- /generated -->

The reference check is [checks/irreversible.py](checks/irreversible.py), a hook that Claude Code runs before each command. A project adopts it like this:

1. Copy the hook to `.claude/hooks/irreversible.py` and [templates/claude-settings.json](templates/claude-settings.json) to `.claude/settings.json`, or add its hook to the settings you have. The settings block the command when the hook fails to run, so a missing or broken hook stops work instead of letting it through.
2. Add `/.claude/ratchet-approvals.json` to `.gitignore`. The approvals stay on the machine, out of the repo.
3. When the owner approves a step, the owner writes it into `.claude/ratchet-approvals.json`, in the form of [templates/ratchet-approvals.json](templates/ratchet-approvals.json): one entry per step, with the step, the exact command, the last day it holds and a reason. A command that takes several steps needs an entry for each. The hook refuses to let an agent write that file.

What the hook denies, what it lets through and what it does not see are in [checks/README.md](checks/README.md#irreversiblepy).

## The phases

A work package is in one of three phases at a time: explore, build or run. The phase is named in the package's issue. Each phase says what an agent may do in it and what ends it.

<!-- generated:table phases -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.phase-explore | In explore\, an agent reads\, searches and tries things out in scratch space\, and writes what it finds as proposals and questions\. It changes nothing that others rely on\: it does not merge\, release or change the register\. Explore ends when the owner picks a proposal to build\, or drops it\. | Text only\: a check cannot tell which phase a session is in | — |
| ratchet.phase-build | In build\, an agent works on one work package that the owner approved\, on its own branch\, and changes only the files the package names\. It opens a PR\, and merges it only when the checks are green and the review has passed\. Build ends when the PR is merged\, or when the package\'s stop rule is reached\. | Text only\: a check cannot tell which phase a session is in\. The required checks and the review on the PR guard the merge | — |
| ratchet.phase-run | In run\, an agent operates what is merged\: it watches it\, reports on it\, and undoes a change that fails\. A fix\, or anything new\, goes back to build as a work package\. Run ends when the owner retires what runs\, or opens a new phase\. | Text only\: a check cannot tell which phase a session is in | — |
<!-- /generated -->

## The review script

`ratchet.cr-review` leans on the review script, like three rules in the core. What the script must do is in [RATCHET.md](RATCHET.md#the-review-script).

## A day in the control room

1. **Wake up.** Fetch, read the feed and the handover, check that promised runs are running.
2. **Act.** Merge what is green and reviewed. Start reviews for new heads. Send findings to the workspaces. Take the next permitted task.
3. **Decide.** Bring decisions to the owner, at most five, each with a recommendation. Write the answer down as a decision file in a PR.
4. **Hand over.** Replace the handover after every important event.
