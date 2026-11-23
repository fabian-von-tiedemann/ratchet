# Control room handbook for <project>

## Start of a session

1. Read AGENTS.md, the register, this handbook and the latest handover.
2. Check the open PRs, their heads and the state of their reviews.
3. Check that the runs the workspaces have promised are actually running.

## Ways of working

- The control room does not build the product. It may make small fixes after a review and maintain its own tools. Building happens in workspaces.
- Overall, scope and architecture assessments run on the strongest model the project has.
- Run it for real as early as possible. A desk review finds edge cases without end. A run shows which ones matter. A standing approval for local experiments at no cost removes the excuse.
- During the owner's quiet hours, <hours>, the control room only continues work already under way and experiments already approved, and collects questions for the morning. It asks at night only if the owner is already in the conversation.

## Phases

A work package is in one phase at a time, named in its issue: explore, build or run.

- **Explore.** An agent reads, searches, tries things in scratch space and writes proposals and questions. It does not merge, release or change the register. Explore ends when the owner picks a proposal to build, or drops it.
- **Build.** An agent works on one work package the owner approved, on its own branch, changes only the files the package names, and merges only on green checks and a passed review. Build ends when the PR is merged or the stop rule is reached.
- **Run.** An agent watches what is merged, reports on it and undoes a change that fails. A fix, or anything new, goes back to build. Run ends when the owner retires what runs or opens a new phase.

## New work

- [ ] Before a new project or a large work package: interview the owner with `grilling`, in rounds of at most five questions, with a recommended answer for each question, until no decision is left as an unstated assumption.
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
- [ ] Changes to the owner's paths, the decisions, the register and every file it names, the checks, the gates and the automated reviewers: the owner has read them and approved the head.

## Decisions

- [ ] Write the question and the owner's answer verbatim in a decision file `decisions/D-YYYY-MM-DD-<slug>.md`, or as a record with that id in the one log the project names, in a PR.
- [ ] Keep four kinds of statement apart and label them: decision (D), proposal (P), outside observation (O) and open question (Q).
- [ ] Propose any change to the register in the same PR.

## Lessons

- [ ] After a failed review or a failed experiment: propose lessons with the lesson template.
- [ ] After the owner approves a lesson: add its ratchet, and send the lesson to Ratchet if it would apply in another project.

## Handover

- [ ] Replace the handover after every important event: what is running, what waits on what, the next step.

## Schedule

Hourly is a good default for the wake-up, with a full status update every second time. The project sets the interval.

| Name | What | When |
|---|---|---|
| Wake-up | Read the feed and advance what is ready | <Every hour> |
| Status | Rewrite the automatic status | <Every two hours> |
| Measure | Report the four numbers in `ratchet.si-measure` | Every two weeks |
