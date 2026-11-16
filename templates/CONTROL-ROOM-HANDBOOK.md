# Control room handbook for <project>

## Start of a session

1. Read AGENTS.md, this handbook, the register and the latest handover in the status issue (#<n>).
2. Check open PRs, their heads and the state of their reviews.
3. Check that runs the workspaces have promised are actually running.

## New work

- [ ] Create an issue with: assignment, files it may change, cap (time or cost), stop rule.
- [ ] Before a new project or a larger package: interview the owner with `/grilling`, at most five questions per round.
- [ ] Split the package into issues with `/to-tickets`.
- [ ] Start a workspace as its own thread with its own worktree from the main branch, with the issue number in the prompt.

## Review

1. Build the assignment with the review script: PR, issue, head, role, model.
2. Start the reviewer in a new thread on a model from a different family, with only the line the script prints.
3. Record the outcome (approved or rejected) and post the verdict on the PR.
4. After two rejected rounds in a row with the same kind of fault: no third round without the owner's decision. The workspace describes the premise with `/principle-attack-the-premise` and proposes another approach.

## Merge

- [ ] Review approved at the exact head.
- [ ] Checks and the security guard green on that head.
- [ ] Changes to judges, gates, guards or checks: the owner has read them.

## Decisions

- [ ] Write the question and the owner's answer verbatim in a decision file `decisions/U-YYYY-MM-DD-<slug>.md`, in a PR.
- [ ] Propose any change to the register in the same PR.

## Handover

- [ ] Replace the handover in the status issue after every important event: what is running, what waits on what, the next step.

## Schedule

| Schedule | What | When |
|---|---|---|
| Wake-up | Read the feed and move forward what is ready | Every hour |
| Status | Rewrite the automatic status | About every two hours |
| Weekly | Compare the register with the rest of the repo | Once a week |
