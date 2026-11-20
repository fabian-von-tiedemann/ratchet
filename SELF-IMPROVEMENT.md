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
| ratchet.si-version | Ratchet is versioned `MAJOR.MINOR`\, with a git tag `vMAJOR.MINOR` and a changelog entry for each version\. A minor version adds or tightens rules\, and may change\, rename or remove an experimental rule\. Only a major version changes the form of `ratchet.json` or `register.json`\, renames the key of a core rule\, or adds a rule to the core or removes one from it\. Before 1\.0\, a minor version may do these too\, and the changelog lists every rename\, every change of form and every rule that enters or leaves the core\. | Check\: the changelog has an entry for every tag | — |
| ratchet.si-pull | Each project states which version of Ratchet it follows\. A check warns when the project is behind the latest tag\. The upgrade is made in a PR of its own\. | Check\: compare the stated version with Ratchet\'s latest tag | — |
| ratchet.si-measure | Every two weeks\, the project reports four numbers\: review rounds before approval\, decisions that came up after work started\, repeated failure classes\, and the share of rules enforced by a check\. The trend goes in the status issue\. | Check\: the report is a scheduled job\, and the status issue shows the date of the last one | — |
| ratchet.si-subtract | A core rule may be removed only when a check covers it completely\, or when a stronger or simpler rule replaces it\. A core rule that has never been triggered is a candidate for review\, not for removal\. An experimental rule may also be removed in the clean\-out at a release\, once it has stood through three releases and 60 days with no decision to keep it\. | Text only\: a check cannot judge whether a check covers a rule completely | — |
| ratchet.si-maintainer-approves | Changes to Ratchet itself are proposed in PRs\, by people or by agents\, and approved by Ratchet\'s maintainer\, like any change to checks \(see `ratchet.checks-owner-read`\)\. | Check\: branch protection on Ratchet\'s main branch | — |
<!-- /generated -->

## What 1.0 promises

From 1.0, the form of `ratchet.json` and of `register.json`, the keys of the core rules, and which rules belong to the core change only in a new major version. Experimental rules are not covered by the promise: a minor version may change, rename or remove one. Before 1.0, a minor version may change all of these, and the changelog lists every change of form, every rename and every rule that enters or leaves the core. `ratchet.si-version` says the same ([D-2026-11-19-one-point-oh](decisions/D-2026-11-19-one-point-oh.md), choice 1).

## When 1.0 comes

Ratchet is released as 1.0 when all six of these hold ([D-2026-11-19-one-point-oh](decisions/D-2026-11-19-one-point-oh.md), choice 2). Four can be read by a check: the check for `init.py` is built, and the three others are not. Two are judged, from the evidence named. On 2026-11-19 one holds.

| Criterion | How it is checked | Holds on 2026-11-19 |
|---|---|---|
| The form has been unchanged for three tags and at least 30 days. | A check can read it from the tags: the fields at the top of `ratchet.json` and of its rules, as `checks/upgrade.py` compares them, and the form of `register.json`, the same at the last three tags, the oldest of them dated at least 30 days before the newest. Not built: issue #70. | No. 0.9 changed the form, and 0.10 changes it again with `since`. |
| A check stops a change of form in a minor version. | It is itself a check: from 1.0, it fails when a version changes the form and has the same major version as the tag before it. Not built: issue #71. | No. |
| `init.py` works. | `checks/test_init.py`, which the job `checks` runs, and a run by hand: on 2026-11-19, `init.py` from `v0.9`, run in a new git repo, wrote five files and passed `check_register.py`. | Yes. |
| A real register has gone through two upgrades. | Judged. The evidence is two merged pull requests in a project's repo, each with the output of `checks/upgrade.py` and `checks/check_register.py`. The tests of `upgrade.py` move this repo's register from each tag, but they are fixtures, not an upgrade. | No. |
| Another repo has followed a tag for 30 days. The maintainer's own next project counts. | Judged. The evidence is the repo's `register.json`, with the version it follows, unchanged in its history for 30 days. No repo can show it before 2026-12-16, 30 days after the first tag. | No. |
| Ratchet uses all nine of its start rules. | A check can read it: `register.json` adopts every key in `start` in `ratchet.json`, and each of them whose ratchet names a check is "built". Not built: issue #72. | No. The register adopts six of the nine, and of the four of those that name a check only `ratchet.register-on-top` is built. |

## Rules promoted from projects

A lesson that comes to Ratchet in step 4 and needs a rule of its own starts here, as an experimental rule outside the core: see [The core is frozen](RATCHET.md#the-core-is-frozen). It moves into the core by a decision of Ratchet's maintainer that cites these criteria ([D-2026-11-19-one-point-oh](decisions/D-2026-11-19-one-point-oh.md), choice 3):

- Its text has been unchanged for two releases and 30 days.
- Ratchet uses the rule itself, and its check is built if its ratchet names one.
- The rule has stopped a real fault.
- The core does not get softer: the share of core rules that are text only does not rise.

The pull request that moves a rule into the core lowers `experimental_cap` by one, so that moving a rule in is never a way to make room. That is text only for now. `checks/test_budget.py` pins the cap, so changing it changes that test, which the maintainer reads, but no check compares the cap or the share with the last tag: issue #73. From 1.0, a rule moves into the core only in a major version.

<!-- generated:table promoted -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.expected-tests-ran | A suite of tests made from a source\, such as a table\, a spec or a directory of fixtures\, fails when a test it expects did not run and pass\. The expected tests are read from that same source\. The run fails when one of them is missing\, skipped\, errored or could not be prepared\, when the suite exits before it is done\, and when two tests run under one id\. Every row of the source has a test that goes red when that row\'s own check is removed\. | Check\: a step of its own runs the suite in a child process\, whose runner writes a record of every outcome and\, at the end\, a completion record\, and the step fails on each expected test that did not pass exactly once\. It catches tests dropped by mistake\. It does not stop test code written to defeat it\, which runs with the same rights\, so a change to the checks is read by the owner \(`ratchet.checks-owner-read`\)\. It does not see whether a test uses what it reads\: a mutation per row does\, as in `ratchet.test-can-fail` | — |
<!-- /generated -->

## The age of an experimental rule

Every experimental rule in `ratchet.json` names `since`, the version it entered Ratchet. It may also name `kept_by`, the id of the decision that kept it once more. A core rule names neither. `checks/generate.py --check` fails, naming each rule, when an experimental rule has stood through three releases and 60 days with no decision ([D-2026-11-19-one-point-oh](decisions/D-2026-11-19-one-point-oh.md), choice 4):

- The releases are the versions with a date in `CHANGELOG.md` that come after `since`, and the days are counted from the date of `since` to the date of the newest of them. So the count moves only when a release is dated: the check first fails in the pull request of a release, and stays red until the maintainer has chosen. That is where the clean-out at every release happens ([D-2026-11-17-improvement-loop](decisions/D-2026-11-17-improvement-loop.md), item 4).
- The maintainer then chooses for each rule it names: move it into the core, merge it with another rule, remove it, or keep it once more. Keeping it is a decision, with the reason, and its id goes in `kept_by`.
- A rule with `kept_by` stands one age more: three releases and 60 days, counted from the release at which it first stood too long. Then the check fails again, and the only choices are to move it into the core, merge it or remove it. The date of the decision does not move the count, so naming another decision in `kept_by` keeps the rule no longer. A rule is kept once, not for good.
- A rule that entered in the version not yet released has no age. `since` names a version with an entry with a date in `CHANGELOG.md`, or the version of `ratchet.json`, and `kept_by` names a file in `decisions/`. A release dated before the version before it fails the check, since a year mistyped in the newest date would hide every rule.

The check does not see whether `since` is true. It was read from the tags once, for 0.10, and a released `ratchet.json` cannot change after its tag (`checks/released_text.py`). Between two releases, `since` can still be changed in a pull request, which the maintainer reads (`ratchet.checks-owner-read`). A check that it stays as it was at the last tag is issue #74.

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
Ratchet 0.10, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 24 experimental rules, under a cap of 25: 11 name a check and 13 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->
