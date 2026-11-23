# How Ratchet tightens over time

> **Experimental.** This file is outside Ratchet's core. Its rules may change in any version, and they are not counted in the share of rules that are text only. A project adopts them row by row, like any other rule.

Every failure in a project should make the same failure harder to repeat, in that project first and then in every project that uses Ratchet. This file describes the loop that does it. The rules follow the same form as [RATCHET.md](RATCHET.md), and the tables are generated from [ratchet.json](ratchet.json).

Two owners appear below. The **project's owner** approves lessons in the project. **Ratchet's maintainer** approves changes to Ratchet.

## The loop

1. **Something fails.** A review rejects a change, an experiment fails, or a bug reaches the main branch.
2. **Capture the lesson.** The project writes it down with [templates/LESSON.md](templates/LESSON.md): what happened, the failure class, the ratchet, and whether it would apply elsewhere (`ratchet.lesson-names-check`).
3. **Tighten locally.** The project's owner approves the lesson (`ratchet.lesson-names-check`). The project adds the ratchet, as a check if a check can see it.
4. **Promote.** If the lesson would have applied in another project, it becomes a PR to Ratchet, with the evidence. Ratchet invites this in [CONTRIBUTING.md](CONTRIBUTING.md#a-lesson-from-a-project). It is not a rule, since Ratchet cannot see a lesson that was never sent.
5. **Release.** Ratchet gets a new version, a tag and a changelog entry. Changes are collected under the first entry of the changelog, headed `(unreleased)`, and released together when the entry gets its date.
6. **Pull.** Projects see that they are behind and upgrade in a PR of its own.
7. **Measure.** At a fixed interval, each project counts how tight it has become and whether any failure class came back.

One turn, as an illustration, not a report from a real project: an agent writes "all tests pass" on a PR, the tests were never run, and the bug reaches the main branch. The failure class is a claim of completion without a run. The ratchet is a required check that runs the tests on the PR head, so the claim no longer matters. It would apply in other projects, so it is sent to Ratchet as a lesson, written with [templates/LESSON.md](templates/LESSON.md).

## Evidence from this repo

Ratchet follows its own rules, and this repo is where they are tried first. Its [AGENTS.md](AGENTS.md), [register.json](register.json), [HANDOVER.md](HANDOVER.md) and [decisions/](decisions/) are Ratchet's own. What the repo shows:

- **A hook that could not be a lock was replaced by locks.** A hook was meant to read shell commands and stop the steps that cannot be undone. A review from another model family rejected it twice, finding ways past it each time, and it was closed unmerged ([PR #42](https://github.com/fabian-von-tiedemann/ratchet/pull/42)). It came back as a tripwire that says it does not catch every spelling, and the locks moved to where they cannot be got around: a ruleset at GitHub and the role of the agents' account ([D-2026-11-19-locks-not-parsing](decisions/D-2026-11-19-locks-not-parsing.md)).
- **Tags are locked by a ruleset.** No one but a repository admin can move or delete a tag. The ruleset is [templates/tag-ruleset.json](templates/tag-ruleset.json), applied on 2026-11-19 and read back ([D-2026-11-19-tag-ruleset-scope](decisions/D-2026-11-19-tag-ruleset-scope.md), [D-2026-11-19-tripwire-and-settings](decisions/D-2026-11-19-tripwire-and-settings.md)).
- **A release is published by the merge that dates it.** Changes are collected under an entry headed `(unreleased)`, and the pull request that gives it its date is the release. The [release workflow](.github/workflows/release.yml) tags it after the merge ([D-2026-11-19-batched-releases](decisions/D-2026-11-19-batched-releases.md)). Every PR compares released text with its tag ([checks/released_text.py](checks/released_text.py)), because the generator once rewrote a released entry, in a round of [PR #12](https://github.com/fabian-von-tiedemann/ratchet/pull/12).
- **A change to a rule or a check is merged only after a model from another family has passed its exact head** ([D-2026-11-17-agent-merges-after-approval](decisions/D-2026-11-17-agent-merges-after-approval.md)). The reviews are comments on the PRs, such as the two rounds on [PR #50](https://github.com/fabian-von-tiedemann/ratchet/pull/50). This is an instruction the agents follow, not a lock, and AGENTS.md says so.
- **The register says honestly which checks are built.** Every rule this repo adopts that names a check stands as "text only for now", and `ratchet.protected-main` says "Not met in this repo" ([REGISTER.md](REGISTER.md)).

## Rules

<!-- generated:table tightening -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.si-harden | A rule whose ratchet is \"text only\" is turned into a check as soon as a check can see it\. A check counts as built only after it has failed at least once on a real or seeded violation\, and only where it can refuse\: a merge check is required for the merge and reads its rules from the base branch\, a hook runs in every harness the project uses\, a scheduled check posts its result and is red when the post is late\, and no deploy can run without a deploy check\. When a failure class comes back after a lesson\, the lesson\'s ratchet was too weak\. Strengthen the ratchet\. Rewording the rule does not count\. | Check\: the periodic count of rules by kind of ratchet\, and of repeated failure classes\. It does not see where a check runs or whether it has failed\, so what makes a check built is a convention\, and the register says where each check is enforced | pstack `principle-encode-lessons-in-structure` |
| ratchet.si-pull | Each project states which version of Ratchet it follows\. A check warns when the project is behind the latest tag\. The upgrade is made in a PR of its own\. | Check\: compare the stated version with Ratchet\'s latest tag | — |
| ratchet.si-measure | Every two weeks\, the project reports four numbers\: review rounds before approval\, the steps and minutes its last upgrade of Ratchet took\, repeated failure classes\, and the share of rules enforced by a check\. The trend goes in the status issue\. With each release of Ratchet\, the steps and minutes to adopt it in an empty repo and to upgrade it by one version are recorded in its changelog\. | Check\: the report is a scheduled job\, and the status issue shows the date of the last one\. No check sees the record with a release | — |
<!-- /generated -->

## What 1.0 promises

From 1.0, the form of `ratchet.json` and of `register.json`, the keys of the core rules, and which rules belong to the core change only in a new major version. Experimental rules are not covered by the promise: a minor version may change, rename or remove one. Before 1.0, a minor version may change all of these, and the changelog lists every change of form, every rename and every rule that enters or leaves the core. This repo's own rule `repo.version`, in [REGISTER.md](REGISTER.md), says the same ([D-2026-11-19-one-point-oh](decisions/D-2026-11-19-one-point-oh.md), choice 1). Until 0.10 it was the experimental rule `si-version`. It applies only to Ratchet, so it moved to Ratchet's own rules (`D-2026-11-20-proposal-triage`, choice 5).

## When 1.0 comes

Ratchet is released as 1.0 when all six of these hold ([D-2026-11-19-one-point-oh](decisions/D-2026-11-19-one-point-oh.md), choice 2). Four can be read by a check: the check for `init.py` is built, and the three others are not. Two are judged, from the evidence named. On 2026-11-19 one holds.

| Criterion | How it is checked | Holds on 2026-11-19 |
|---|---|---|
| The form has been unchanged for three tags and at least 30 days. | A check can read it from the tags: the fields at the top of `ratchet.json` and of its rules, as `checks/upgrade.py` compares them, and the form of `register.json`, the same at the last three tags, the oldest of them dated at least 30 days before the newest. Not built: issue #70. | No. 0.9 changed the form, and 0.10 changes it again with `since` and `not_used_because`. |
| A check stops a change of form in a minor version. | It is itself a check: from 1.0, it fails when a version changes the form and has the same major version as the tag before it. Not built: issue #71. | No. |
| `init.py` works. | `checks/test_init.py`, which the job `checks` runs, and a run by hand: on 2026-11-19, `init.py` from `v0.9`, run in a new git repo, wrote five files and passed `check_register.py`. | Yes. |
| A real register has gone through two upgrades. | Judged. The evidence is two merged pull requests in a project's repo, each with the output of `checks/upgrade.py` and `checks/check_register.py`. The tests of `upgrade.py` move this repo's register from each tag, but they are fixtures, not an upgrade. | No. |
| Another repo has followed a tag for 30 days. The maintainer's own next project counts. | Judged. The evidence is the repo's `register.json`, with the version it follows, unchanged in its history for 30 days. No repo can show it before 2026-12-16, 30 days after the first tag. | No. |
| Ratchet uses all ten of its start rules. | A check can read it: `register.json` adopts every key in `start` in `ratchet.json`, and each of them whose ratchet names a check is "built". Not built: issue #72. | No. The register adopts eight of the ten, and of the six of those that name a check none is built. `ratchet.register-on-top` was, until the definition of "built" by where a check is enforced (D-2026-11-22-second-redraw): its check runs in the required job `checks`, but on the PR's own checks and rule data, not the base branch's. `ratchet.root-cause` came in 0.10, when its ratchet became a check, and `ratchet.owner-paths` in 0.11, when it joined the start set (D-2026-11-22-second-redraw). |

## Rules promoted from projects

A lesson that comes to Ratchet in step 4 and needs a rule of its own starts here, as an experimental rule outside the core: see [The core is frozen](RATCHET.md#the-core-is-frozen). It moves into the core by a decision of Ratchet's maintainer that cites these criteria ([D-2026-11-19-one-point-oh](decisions/D-2026-11-19-one-point-oh.md), choice 3):

- Its text has been unchanged for two releases and 30 days.
- Ratchet uses the rule itself, and its check is built if its ratchet names one.
- The rule has stopped a real fault.
- The core does not get softer: the share of core rules that are text only does not rise.

A new experimental rule is already used by Ratchet itself, or says why Ratchet cannot use it (`D-2026-11-20-proposal-triage`, choice 5). `checks/generate.py --check` fails on an experimental rule whose `since` is the version of `ratchet.json` when this repo's `register.json` does not adopt it and the rule has no `not_used_because`, the reason in words. It fails as well on a rule that the register adopts and that names a reason. A rule that came before 0.10 is not held to it. The check sees that the register adopts the rule, not that Ratchet follows it: see [checks/README.md](checks/README.md#a-rule-that-enters-is-used).

The pull request that moves a rule into the core lowers `experimental_cap` by one, so that moving a rule in is never a way to make room. So does a pull request that moves an experimental rule out of Ratchet into Ratchet's own register: in 0.10, `si-version` and `si-maintainer-approves`, which applied only to Ratchet, became `repo.version` and `repo.maintainer-approves` in [REGISTER.md](REGISTER.md), and the cap went from 25 to 23 (`D-2026-11-20-proposal-triage`, choice 5). That is text only for now. `checks/test_budget.py` pins the cap, so changing it changes that test, which the maintainer reads, but no check compares the cap or the share with the last tag: issue #73. From 1.0, a rule moves into the core only in a major version.

Two rules stand here. `ratchet.expected-tests-ran` came from a project in 0.4. `ratchet.one-exact-form` came in 0.10, from issue #65: two projects met the same failure class, a check that interprets free text and so lets through each spelling it does not know, once in checks of shell commands and command lines and once in checks of addresses (`D-2026-11-20-proposal-triage`, choice 4). Ratchet already follows it, as its own rule `repo.strict-forms` and [D-2026-11-16-strict-forms](decisions/D-2026-11-16-strict-forms.md), and as [D-2026-11-19-locks-not-parsing](decisions/D-2026-11-19-locks-not-parsing.md) says of the tripwire, so this repo's register adopts it.

<!-- generated:table promoted -->
| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.expected-tests-ran | A suite of tests made from a source\, such as a table\, a spec or a directory of fixtures\, fails when a test it expects did not run and pass\. The expected tests are read from that same source\. The run fails when one of them is missing\, skipped\, errored or could not be prepared\, when the suite exits before it is done\, and when two tests run under one id\. Every row of the source has a test that goes red when that row\'s own check is removed\. | Check\: a step of its own runs the suite in a child process\, whose runner writes a record of every outcome and\, at the end\, a completion record\, and the step fails on each expected test that did not pass exactly once\. It catches tests dropped by mistake\. It does not stop test code written to defeat it\, which runs with the same rights\, so a change to the checks is read by the owner \(`ratchet.owner-paths`\)\. It does not see whether a test uses what it reads\: a mutation per row does\, as in `ratchet.test-can-fail` | — |
| ratchet.one-exact-form | A check that must refuse what it does not know accepts one exact form of the whole input and refuses everything else\. It does not interpret free text\, a command line or an address to decide what it means\. Where the input cannot be given one form\, the check is a tripwire and says so\, and a lock elsewhere carries the rule\. | Text only\: a check cannot tell how another check reads its input\. Every form that once got past a check is a fixture it must fail\, and every form it accepts has a fixture it passes\, so the forms it accepts are a finite list | — |
<!-- /generated -->

## The age of an experimental rule

Every experimental rule in `ratchet.json` names `since`, the version it entered Ratchet. It may also name `kept_by`, the id of the decision that kept it once more. A core rule names neither. `checks/generate.py --check` fails, naming each rule, when an experimental rule has stood through three releases and 60 days with no decision ([D-2026-11-19-one-point-oh](decisions/D-2026-11-19-one-point-oh.md), choice 4):

- The releases are the versions with a date in `CHANGELOG.md` that come after `since`, and the days are counted from the date of `since` to the date of the newest of them. So the count moves only when a release is dated: the check first fails in the pull request of a release, and stays red until the maintainer has chosen. That is where the clean-out at every release happens ([D-2026-11-17-improvement-loop](decisions/D-2026-11-17-improvement-loop.md), item 4).
- The maintainer then chooses for each rule it names: move it into the core, merge it with another rule, remove it, or keep it once more. Keeping it is a decision, with the reason, and its id goes in `kept_by`.
- A rule with `kept_by` stands one age more: three releases and 60 days, counted from the release at which it first stood too long. Then the check fails again, and the only choices are to move it into the core, merge it or remove it. The date of the decision does not move the count, so naming another decision in `kept_by` keeps the rule no longer. A rule is kept once, not for good.
- A rule that entered in the version not yet released has no age. `since` names a version with an entry with a date in `CHANGELOG.md`, or the version of `ratchet.json`, and `kept_by` names a file in `decisions/`. A release dated before the version before it fails the check, since a year mistyped in the newest date would hide every rule.

The check does not see whether `since` is true. It was read from the tags once, for 0.10, and a released `ratchet.json` cannot change after its tag (`checks/released_text.py`). Between two releases, `since` can still be changed in a pull request, which the maintainer reads (`ratchet.owner-paths`). A check that it stays as it was at the last tag is issue #74.

## What "tighter" means

Tighter does not mean more rules. It means:

- more of the rules are enforced by a check
- fewer failure classes come back
- fewer review rounds are needed before approval
- adopting and upgrading take fewer steps and minutes.

If the number of rules grows while these numbers stand still, Ratchet is getting heavier, not tighter.

## Ratchet's own count

The count is computed from `ratchet.json` by `checks/generate.py --count` and stated with every version in the [changelog](CHANGELOG.md). The share covers the core. A rule counts as shipped with a reference check only if that check has a fixture it fails on.

<!-- generated:count -->
Ratchet 0.12, computed from `ratchet.json`: the core has 19 rules. 13 name a check and 6 are text only (32%). Ratchet ships a reference check for 1 of the 13. Outside the core there are 10 experimental rules, under a cap of 17: 7 name a check and 3 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->
