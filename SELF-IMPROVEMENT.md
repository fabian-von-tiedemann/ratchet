# How Ratchet tightens over time

> **Experimental.** This file is outside Ratchet's core. Its rules may change in any version, and they are not counted in the share of rules that are text only. A project adopts them row by row, like any other rule.

Every failure in a project should make the same failure harder to repeat, in that project first and then in every project that uses Ratchet. This file describes the loop that does it. The rules follow the same form as [RATCHET.md](RATCHET.md), and the tables are generated from [ratchet.json](ratchet.json).

Two owners appear below. The **project's owner** approves lessons in the project. **Ratchet's maintainer** approves changes to Ratchet.

## The loop

1. **Something fails.** A review rejects a change, an experiment fails, or a bug reaches the main branch.
2. **Capture the lesson.** The project writes it down with [templates/LESSON.md](templates/LESSON.md): what happened, the failure class, the ratchet, and whether it would apply elsewhere (`ratchet.lesson-names-check`).
3. **Tighten locally.** The project's owner approves the lesson (`ratchet.lesson-loop`). The project adds the ratchet, as a check if a check can see it.
4. **Promote.** If the lesson would have applied in another project, it becomes a PR to Ratchet, with the evidence.
5. **Release.** Ratchet gets a new version, a tag and a changelog entry. Changes are collected under the first entry of the changelog, headed `(unreleased)`, and released together when the entry gets its date.
6. **Pull.** Projects see that they are behind and upgrade in a PR of its own.
7. **Measure.** At a fixed interval, each project counts how tight it has become and whether any failure class came back.

## Rules

<!-- generated:table tightening -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.si-harden | A rule whose ratchet is \"text only\" is turned into a check as soon as a check can see it\. The share of rules enforced by a check is the measure of how tight a project is\. A check counts only if it has failed at least once on a real or seeded violation\. | Check\: the periodic count of rules by kind of ratchet | — |
| ratchet.si-repeat-is-signal | When a failure class comes back after a lesson\, the lesson\'s ratchet was too weak\. The response is a stronger ratchet\, moving from text to a check where possible\. Rewording the rule is not a response\. | Check\: the periodic count of repeated failure classes | pstack `principle-encode-lessons-in-structure` |
| ratchet.si-promote | A lesson that would have applied in another project becomes a PR to Ratchet within a week\, with what happened\, the ratchet and the result in the project\. Everything that identifies the project is removed first\. | Text only\: Ratchet cannot see a lesson that was never sent | — |
| ratchet.si-version | Ratchet is versioned `MAJOR.MINOR`\, with a git tag `vMAJOR.MINOR` and a changelog entry for each version\. A minor version adds or tightens rules\. A major version changes the form\, renames keys or removes rules that a check now covers\. Before 1\.0\, a minor version may also rename keys and change the form\, and the changelog lists every rename and every change of form\. | Check\: the changelog has an entry for every tag | — |
| ratchet.si-pull | Each project states which version of Ratchet it follows\. A check warns when the project is behind the latest tag\. The upgrade is made in a PR of its own\. | Check\: compare the stated version with Ratchet\'s latest tag | — |
| ratchet.si-measure | Every two weeks\, the project reports four numbers\: review rounds before approval\, decisions that came up after work started\, repeated failure classes\, and the share of rules enforced by a check\. The trend goes in the status issue\. | Check\: the report is a scheduled job\, and the status issue shows the date of the last one | — |
| ratchet.si-subtract | A rule may be removed only when a check covers it completely\, or when a stronger or simpler rule replaces it\. A rule that has never been triggered is a candidate for review\, not for removal\. | Text only\: a check cannot judge whether a check covers a rule completely | — |
| ratchet.si-maintainer-approves | Changes to Ratchet itself are proposed in PRs\, by people or by agents\, and approved by Ratchet\'s maintainer\, like any change to checks \(see `ratchet.checks-owner-read`\)\. | Check\: branch protection on Ratchet\'s main branch | — |
<!-- /generated -->

## Rules promoted from projects

A lesson that comes to Ratchet in step 4 and needs a rule of its own starts here, as an experimental rule outside the core: see [The core is frozen](RATCHET.md#the-core-is-frozen). It moves into the core only by a decision of Ratchet's maintainer.

<!-- generated:table promoted -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.expected-tests-ran | A suite of tests made from a source\, such as a table\, a spec or a directory of fixtures\, fails when a test it expects did not run and pass\. The expected tests are read from that same source\. The run fails when one of them is missing\, skipped\, errored or could not be prepared\, when the suite exits before it is done\, and when two tests run under one id\. Every row of the source has a test that goes red when that row\'s own check is removed\. | Check\: a step of its own runs the suite in a child process\, whose runner writes a record of every outcome and\, at the end\, a completion record\, and the step fails on each expected test that did not pass exactly once\. It catches tests dropped by mistake\. It does not stop test code written to defeat it\, which runs with the same rights\, so a change to the checks is read by the owner \(`ratchet.checks-owner-read`\)\. It does not see whether a test uses what it reads\: a mutation per row does\, as in `ratchet.test-can-fail` | — |
<!-- /generated -->

## What "tighter" means

Tighter does not mean more rules. It means:

- more of the rules are enforced by a check
- fewer failure classes come back
- fewer review rounds are needed before approval
- fewer decisions come up after work has started.

If the number of rules grows while these numbers stand still, Ratchet is getting heavier, not tighter.

## Ratchet's own count

The count is computed from `ratchet.json` by `checks/generate.py --count` and stated with every version in the [changelog](CHANGELOG.md). The share covers the core. A rule counts as shipped with a reference check only if that check has a fixture it fails on.

<!-- generated:count -->
Ratchet 0.10, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 23 experimental rules, under a cap of 25: 11 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->
