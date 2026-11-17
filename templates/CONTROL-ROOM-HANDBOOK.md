# Control room handbook for <project>

## Start of a session

1. Read AGENTS.md, the register, this handbook and the latest handover.
2. Check the open PRs, their heads and the state of their reviews.
3. Check that the runs the workspaces have promised are actually running.

## New work

- [ ] Before a new project or a large work package: interview the owner with `grilling`, at most five questions per round.
- [ ] Split the work package into issues with `to-tickets`.
- [ ] Give each issue: assignment, files it may change, cap (time or cost), stop rule.
- [ ] Start a workspace as its own thread with its own worktree from the main branch, with the issue number in the prompt.

## Review

1. Build the assignment with the review script: PR, issue, head, role, model.
2. Start the reviewer in a new thread, on a model from a different family than the author's. Give it the assignment the script built and nothing else.
3. Record the outcome (approved or rejected) and post the verdict on the PR.
4. After two rejected rounds in a row with the same kind of failure: no third round without the owner's decision. The workspace writes down the shared premise with `principle-attack-the-premise` and proposes another approach.

## Merge

- [ ] Review approved at the exact head.
- [ ] Required checks and the security scan green on that head.
- [ ] Changes to the register, or to checks, gates and automated reviewers: the owner has read them.

## Decisions

- [ ] Write the question and the owner's answer verbatim in a decision file `decisions/D-YYYY-MM-DD-<slug>.md`, in a PR.
- [ ] Propose any change to the register in the same PR.

## Lessons

- [ ] After a failed review or a failed experiment: propose at most three lessons with the lesson template.
- [ ] After the owner approves a lesson: add its ratchet, and send the lesson to Ratchet if it would apply in another project.

## Handover

- [ ] Replace the handover after every important event: what is running, what waits on what, the next step.

## Schedule

| Name | What | When |
|---|---|---|
| Wake-up | Read the feed and advance what is ready | <Every hour> |
| Status | Rewrite the automatic status | <Every two hours> |
| Measure | Report the four numbers in `ratchet.si-measure` | Every two weeks |
