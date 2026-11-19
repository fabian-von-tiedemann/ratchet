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

## The phases

A work package is explored, built or run, one at a time. The phase says what an agent may do and what ends it. It is one rule, so that the three are adopted together.

<!-- generated:table phases -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.phases | A work package is in one phase at a time\, named in its issue\: explore\, build or run\. In explore\, an agent reads\, searches\, tries things in scratch space and writes proposals and questions\. It does not merge\, release or change the register\. Explore ends when the owner picks a proposal to build\, or drops it\. In build\, an agent works on one work package the owner approved\, on its own branch\, changes only the files the package names\, and merges only on green checks and a passed review\. Build ends when the PR is merged or the stop rule is reached\. In run\, an agent watches what is merged\, reports on it and undoes a change that fails\. A fix\, or anything new\, goes back to build\. Run ends when the owner retires what runs or opens a new phase\. | Text only\: a check cannot tell which phase a session is in\. In build\, the required checks and the review on the PR guard the merge | — |
<!-- /generated -->

## What cannot be undone

An agent may go ahead with a step that can be undone, because a mistake there costs a revert. A step that cannot be undone waits for the owner. The rule names five such steps. Each of them needs a lock in a place the agent cannot get around, and a hook in the harness is not such a place: a hook that reads the shell can always be shown a spelling it does not know ([D-2026-11-19-locks-not-parsing](decisions/D-2026-11-19-locks-not-parsing.md)). So the hook is a tripwire, and the locks are with the host and in the sandbox.

<!-- generated:table irreversible -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.irreversible-waits | An agent goes ahead with a step that can be undone\, and waits on a step that cannot\. A step that cannot be undone goes ahead only with an approval from the owner that names the step and the exact command\, with the last day it holds\. The steps are a force push\, creating or deleting a tag\, creating or changing a release\, deleting outside the working tree\, and changing the repository\'s settings\. | Check\: a hook in the agent\'s harness denies\, before it runs\, each of a listed set of usual spellings of the five steps that no approval names\. It is a tripwire and not a lock\: another spelling gets past it\. The locks sit with the host and the sandbox\: a tag ruleset refuses moving or deleting a tag\, the role of the agents\' account refuses the settings that only an admin may change\, the protection of the main branch refuses a force push to it\, and a sandbox keeps deletion inside the working tree\. Creating a tag or a release\, a force push to another branch\, and the secrets and variables that the role Write may change are caught by the hook alone | — |
<!-- /generated -->

Where each step is locked, in a project that is set up as Ratchet's own repo is:

| Step | Locked by | Caught by the tripwire |
|---|---|---|
| Moving or deleting a tag | A tag ruleset at GitHub, [templates/tag-ruleset.json](templates/tag-ruleset.json), once the owner applies it. It does not block creating a tag: see [D-2026-11-19-tag-ruleset-scope](decisions/D-2026-11-19-tag-ruleset-scope.md). In Ratchet's own repo, the maintainer applied it on 2026-11-19, and it was read back the same day: see [checks/README.md](checks/README.md#the-tag-ruleset) | Yes |
| Changing a setting that only an admin may change: the settings page, rulesets and branch protection, webhooks and deploy keys, collaborators, topics, and configuring an environment | The role Write of the agents' account. In a repository that a personal account owns, as Ratchet's own is, GitHub's table of roles reserves all of these to its owner ([personal account](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-personal-account-settings/permission-levels-for-a-personal-account-repository), [environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)). In a repository that an organization owns, the table reserves them to the role Admin, except topics, which the role Maintain may manage too ([organization](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/repository-roles-for-an-organization)). The role Write may change none of them in either kind of repository | Yes |
| Changing Actions secrets and variables, of the repository or of an environment, Dependabot and Codespaces secrets, and enabling or disabling a workflow | Nothing. The role Write may create, update and delete Actions secrets and variables, on the site and with the REST API, and the REST API asks only for collaborator access ([secrets](https://docs.github.com/en/rest/actions/secrets), [variables](https://docs.github.com/en/rest/actions/variables)). The docs do not reserve the others to an admin either | Yes, alone |
| A force push to the main branch | The ruleset on the main branch, which refuses force pushes and deletion | Yes |
| Creating a tag or a release | Nothing. A tag created by mistake publishes nothing, and the owner can delete it | Yes, alone |
| A force push to another branch | Nothing | Yes, alone |
| Deleting outside the working tree | Nothing yet. It waits on the trial of a sandbox for the workspaces ([D-2026-11-17-harness-sandbox-risk](decisions/D-2026-11-17-harness-sandbox-risk.md), item 2) | Yes, alone |

The role Write may also change labels. They are not counted as settings: they count as harmless and can be undone ([D-2026-11-19-locks-not-parsing](decisions/D-2026-11-19-locks-not-parsing.md), item 3), although a deleted label disappears from every issue and pull request that had it ([D-2026-11-19-tripwire-and-settings](decisions/D-2026-11-19-tripwire-and-settings.md)).

The tripwire is [checks/tripwire.py](checks/tripwire.py), a `PreToolUse` hook for Claude Code. It denies the cases that [checks/README.md](checks/README.md#tripwirepy) lists, and no others. To use it, a project copies it to `.claude/hooks/tripwire.py`, copies [templates/claude-settings.json](templates/claude-settings.json) to `.claude/settings.json`, and adds `/.claude/ratchet-approvals.json` to `.gitignore`. The owner approves a step by adding an entry to `.claude/ratchet-approvals.json`, which starts as [templates/ratchet-approvals.json](templates/ratchet-approvals.json). The hook denies any agent write to that file. A project that upgrades replaces its copy of the hook with the one from the newer Ratchet.

## The review script

`ratchet.cr-review` leans on the review script, like three rules in the core. What the script must do is in [RATCHET.md](RATCHET.md#the-review-script).

## A day in the control room

1. **Wake up.** Fetch, read the feed and the handover, check that promised runs are running.
2. **Act.** Merge what is green and reviewed. Start reviews for new heads. Send findings to the workspaces. Take the next permitted task.
3. **Decide.** Bring decisions to the owner, at most five, each with a recommendation. Write the answer down as a decision file in a PR.
4. **Hand over.** Replace the handover after every important event.
