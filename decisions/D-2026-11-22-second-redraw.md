# D-2026-11-22-second-redraw: ten principles, 54 rules to 29 and a product module of seven, adoption by reference as a weaker mode, "built" by enforcement point, and one threat model

<!-- generated:status -->
Status: amended by D-2026-11-22-owner-reads-outside-gates (step 8 keeps what ratchet.checks-owner-read covered); amended by D-2026-11-22-standing-approval (the steps of the migration merge under the standing approval); amended by D-2026-11-23-adopt-mode-no-copied-row (the floor of adopt mode in step 9b); amended by D-2026-11-23-values-and-principles (eleven principles of one or two sentences)
<!-- /generated:status -->

- Date: 2026-11-22
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-16-register-only (the core rules on decisions and on the glossary); D-2026-11-16-scope (point 1, a row by reference holds the project's wording); D-2026-11-17-pull-and-budget (the cap goes from 23 to 17); D-2026-11-19-one-point-oh (choice 2 counts ten start rules); D-2026-11-20-generated-block (adoption by reference is allowed as a weaker mode); D-2026-11-20-principles-and-obligations (the principles and the rules under them); D-2026-11-20-proposal-triage (choice 1, no product rules now); D-2026-11-21-release-and-redraw (settles what it left open on #78)
- Ends: none

The mark `[…]` shows where this file leaves out part of a message.

## Question

Background. [D-2026-11-21-release-and-redraw](D-2026-11-21-release-and-redraw.md) had a fresh session of another model (Fable) redraw the principles and the rules, starting from the findings of a second model from another family (Gemini 4 Neon), after Ratchet was tried on an application of the maintainer's own that runs in production. Fable's first version was checked by Codex and reviewed by Gemini 4 Neon. It put five questions, each with a recommendation. The control room put them to the maintainer with the conditions the two reviewers set. The proposal itself stays out of this repo, so what was decided is written out under "What follows".

The first question, asked by the control room on 2026-11-22. Original, in Swedish:

> **Fables fem frågor med mina råd.** Båda granskarna säger ja till alla fem, med villkor:
> 1. **Markering i stället för kopia: ja.** Markeringen ska heta det den är, en svagare väg. Skyddet räknas först när kodägaren måste godkänna de utpekade filerna och agenten inte kan gå förbi.
> 2. **Kärnan från 35 till 18 regler: ja.** Varje skydd som försvinner ska antingen stå uttryckligen i beslutet eller få tillbaka en kort mening. Regler med olika kontroller slås inte ihop.
> 3. **#78: ja, som en överenskommelse plus inventeringen.** "Byggd" definieras efter var kontrollen verkar.
> 4. **Produktionsreglerna: ja, frivilliga och på prov.** Larm när appen är trasig och låsta beroenden läggs till, och reglerna lovar inget utöver det kontrollerna ser.
> 5. **Sluta skärpa: ja.** Det blir en gemensam hotmodell plus varje kontrolls egen gräns. Ett fynd utanför gränsen blir ett beslut om omfattning, inte en ny granskningsrunda.
> […]
> **Ja på mina råd för alla fem, och att Fable gör version 2?**

Translation:

> **Fable's five questions with my recommendations.** Both reviewers say yes to all five, with conditions:
> 1. **A marker instead of a copy: yes.** The marker is to be called what it is, a weaker way. The protection counts only when the code owner must approve the files pointed at and the agent cannot get past it.
> 2. **The core from 35 to 18 rules: yes.** Every protection that disappears is either to stand explicitly in the decision or to get a short sentence back. Rules with different checks are not merged.
> 3. **#78: yes, as a convention plus the inventory.** "Built" is defined by where the check acts.
> 4. **The production rules: yes, opt-in and on trial.** An alert when the app is broken and locked dependencies are added, and the rules promise nothing beyond what the checks see.
> 5. **Stop hardening: yes.** It becomes one shared threat model plus each check's own limit. A finding outside the limit becomes a decision on scope, not a new round of review.
> […]
> **Yes to my recommendations for all five, and that Fable makes version 2?**

Fable then wrote version 2. Codex and Gemini 4 Neon reviewed it, and both found it ready with small fixes. Both reproduced its counts. Before the decision they asked for six fixes: the requirement of a fresh context for overall, scope and architecture assessments was lost without being listed; the wording of the scope boundary; quoting the question and the answer verbatim; an express authorization of the new clauses in the core and of the listed losses; `ratchet.owner-paths` in the start set; and the hash of a row by reference covering the rule and its ratchet. Gemini 4 Neon also named five cuts that lose no protection.

The second question, asked on 2026-11-22 after both reviews of version 2. Original, in Swedish:

> **Två val med mina råd:**
> 1. **Ta med Neons fem strykningar?** Mitt råd är ja. Det går rakt mot ditt mål med få och enkla regler, och båda granskarna har konstaterat att inget skydd hänger på de här bitarna.
> 2. **Beslutsfilen som PR nu?** Mitt råd är ja. En arbetare skriver beslutsfilen i ratchet. Den citerar din fråga och ditt "Ja" ordagrant och tar med alla sex rättelserna och strykningarna. Codex granskar den, och sedan godkänner du med PR och head som vanligt. Därefter kommer de små PR:erna, och de som tar bort saker går först.
> **Ja på båda?**

Translation:

> **Two choices with my recommendations:**
> 1. **Take in Neon's five cuts?** My recommendation is yes. It goes straight toward your goal of few and simple rules, and both reviewers have established that no protection hangs on these pieces.
> 2. **The decision file as a PR now?** My recommendation is yes. A worker writes the decision file in ratchet. It quotes your question and your "Yes" verbatim and includes all six fixes and the cuts. Codex reviews it, and then you approve with PR and head as usual. After that come the small PRs, and those that remove things go first.
> **Yes to both?**

## Answer

To the first question. Original, in Swedish:

> Ja

Translation:

> Yes

To the second question. Original, in Swedish:

> Ja

Translation:

> Yes

## What follows

Everything below that the maintainer did not say is a proposal (P) until the pull request that carries it is merged. Each later step still needs the maintainer's approval of its head.

### The principles

Ratchet reads as seven principles for every project and three for an application with users, in place of the eleven of [D-2026-11-20-principles-and-obligations](D-2026-11-20-principles-and-obligations.md). A principle is still a question to ask when no rule fits: guidance, text only, claiming no protection. What is checked is the rules under it.

| # | Principle | The question | Rules under it |
|---|---|---|---|
| 1 | Keep one place | Where is this rule, this state or this decision written, and is that the one place the next session reads? | `register-on-top`, `decision-as-file`, `work-in-issues`, `cr-handover`, `cr-workspace`, `si-pull` |
| 2 | Make the gate independent of the author | Does this change reach main only through required checks at the merged head and a reviewer who never saw my reasoning? | `protected-main`, `owner-paths`, `fresh-context`, `two-rounds`, `review-by-risk` |
| 3 | Wait for the owner on what cannot be undone | Can I undo this myself, and is it mine to decide? If not, ask once with a recommendation and record the answer. | `ask-the-owner`, `irreversible-waits` |
| 4 | Show the run, and treat silence as red | What run shows this, on which head, and what did it not cover? What should have reported and has not? | `evidence-before-done`, `silence-is-red`, `cr-wake` |
| 5 | Make checks that can fail, and turn failures into checks | Has this check failed on the fault it claims to catch, and does it run where it can refuse? Which check now goes red on the failure I just fixed? | `root-cause`, `test-can-fail`, `lesson-names-check`, `si-harden`, `expected-tests-ran`, `one-exact-form` |
| 6 | Guard the boundaries | What crosses a boundary here: a secret going out, outside text or code coming in, or a right wider than the work needs? | `no-secrets`, `no-tracing`, `material-not-instructions`, `skills-pinned`, `agents-without-keys`, `dependencies-pinned` |
| 7 | Subtract first | What is the simplest thing that meets the requirement, what can be removed, and is the project getting tighter or only heavier? | `simplest`, `si-measure` |
| 8 | Ship what was tested, and know the way back | Is what runs in production the exact build that passed, and have I tried the way back? | `release-what-was-tested` |
| 9 | Keep what was accepted | Who can judge this change, have they accepted it, and which test goes red if that behavior or boundary changes later? | `accepted-by-who-can-judge`, `boundaries-have-tests` |
| 10 | Watch production and the ground under the code | Would I know within minutes if production stopped working? What does real use show that the tests do not, and what outside the repo is about to change state? | `production-health`, `measure-real-use`, `platform-lifecycle` |

Principles 1 to 7 are the core. Principles 8 to 10 enter in the same pull request as the product rules under them, since the check of the principles fails on a principle with no rule.

### The rules

54 rules become 29: the core goes from 35 to 19 and the experimental rules from 19 to 10. Seven experimental product rules come on top, so Ratchet holds 36. Every rule stands under one principle. All keys are `ratchet.` keys.

The merge rule:

1. Two rules merge when both are text only, or when both name the same check: one mechanism at one enforcement point.
2. A text-only rule may join a rule that names a check. The merged ratchet then says in words what the check does not see.
3. Two different checks never stand under one rule.
4. A core rule merges only with core rules, and an experimental rule only with experimental rules. Nothing moves into the core without the criteria of [D-2026-11-19-one-point-oh](D-2026-11-19-one-point-oh.md), choice 3.
5. A merged rule is "built" in a register only when its check is, and its `where` says which part stands.

The map of the 54:

| Rule now | Core or experimental | What happens |
|---|---|---|
| register-on-top | core | Kept, with the clause on adoption by reference (L1) |
| protected-main | core | Kept, unchanged |
| decision-as-file | core | Kept, with the decision log (L2) |
| one-approver | core | Into the new `owner-paths`, whole |
| kinds-apart | core | The letters D, P, O and Q leave the core (M5) |
| work-in-issues | core | Kept, unchanged |
| glossary | core | Out, to Ratchet's own rules (L3) |
| one-channel | core | Into the new `ask-the-owner`, whole |
| five-choices | core | Into `ask-the-owner`, whole |
| look-up-facts | core | Into `ask-the-owner`, whole |
| grill-first | core | Out, to the handbook template (R1) |
| fresh-context | core | Kept, takes `once-per-version` and `register-review-first` |
| once-per-version | core | Into `fresh-context`, with its lock per PR, head and model |
| two-rounds | core | Kept, unchanged |
| findings-marked | core | Into `evidence-before-done`, without the marks of R2 |
| verify-findings | core | Into `evidence-before-done`, whole |
| checks-owner-read | core | Into `owner-paths`, whole |
| register-review-first | core | Into `fresh-context`, whole |
| root-cause | core | Kept, unchanged |
| reuse-first | core | Into `simplest`, whole |
| simplest | core | Kept, takes `reuse-first` and `slices` |
| run-early | core | Out, to the handbook template (R3) |
| test-first | core | Into `test-can-fail`, whole |
| test-can-fail | core | Kept, with mutations on a schedule (L4) |
| evidence-before-done | core | Kept, takes `findings-marked` and `verify-findings`, with T3 |
| slices | core | Into `simplest`, whole |
| experiment-plan | core | The spending approval and the account's spending limit into `ask-the-owner`, word for word; the design checklist is dropped (R9) |
| no-secrets | core | Kept, unchanged |
| no-tracing | core | Kept, unchanged: its check is a hook, not the scan of `no-secrets` |
| material-not-instructions | core | Kept, unchanged |
| skills-pinned | core | Kept, unchanged |
| nightly-visible | core | Kept, widened and renamed `silence-is-red` (T1) |
| agents-without-keys | core | Kept, widened (T2) |
| lesson-names-check | core | Kept, takes `lesson-loop` |
| lesson-loop | core | Into `lesson-names-check`, without "at most three" (R10) |
| cr-does-not-build | experimental | Out, to the handbook template (R4) |
| cr-handover | experimental | Kept, unchanged |
| cr-workspace | experimental | Kept, takes one sentence of `phases` and the clean clone |
| review-by-risk | experimental | Kept; Ratchet's own path list moves out (M3); takes two clauses of `cr-analysis-model`; may name a security review (T5) |
| cr-analysis-model | experimental | "No silent switch" and the fresh context into `review-by-risk`; "the strongest model" to the handbook template (R5) |
| cr-wake | experimental | Kept, takes `cr-next-task` |
| cr-next-task | experimental | Into `cr-wake`, whole |
| cr-quiet-hours | experimental | Out, to the handbook template (R7) |
| cr-verify-reports | experimental | Dropped as a duplicate of `evidence-before-done` (R11) |
| phases | experimental | One sentence into `cr-workspace`, the rest to the handbook template (R8) |
| irreversible-waits | experimental | Kept, unchanged: its steps and its lock matrix are not touched |
| si-harden | experimental | Kept, takes `si-repeat-is-signal` and the definition of "built" (T6) |
| si-repeat-is-signal | experimental | Into `si-harden`, the rule and its count together |
| si-promote | experimental | Out, to `CONTRIBUTING.md` (M1) |
| si-pull | experimental | Kept, unchanged: its check is not the register check |
| si-measure | experimental | Kept, one number replaced by the overhead (M4) |
| si-subtract | experimental | Out, to Ratchet's own rules (M2) |
| expected-tests-ran | experimental | Kept, unchanged but for the key it cites, `owner-paths` |
| one-exact-form | experimental | Kept, unchanged |

So 27 rules are kept, 13 unchanged and 14 changed. 18 merge into another rule, whole or in part. 4 move to Ratchet's own rules or documents. 5 leave as a handbook line or as a duplicate. With the two new rules, `owner-paths` and `ask-the-owner`, that is 29. One key is renamed, `nightly-visible` to `silence-is-red`, because the old name would be false. Every key of the start set stays.

The two new core rules, as decided:

- `ratchet.owner-paths`. Rule: "Only the owner approves decisions. Agents write proposals and mark them as proposals. The project lists the paths that are the owner's: the decisions, the register and every file it names, the checks, the gates and the automated reviewers. A change to any of them merges only after the owner has read it and approved its head. A work package that changes a check, a gate or an automated reviewer states, before review, what it claims and against which threat, with a finite list of cases." Ratchet: "Check: the host requires the owner's review on the listed paths and dismisses it on a new push, and agents work under an account of their own that cannot approve and cannot bypass the requirement. It does not see whether the claim and the threat were stated, or whether a proposal is marked as one".
- `ratchet.ask-the-owner`. Rule: "The agent looks up facts itself. Decisions belong to the owner. Questions to the owner come through one channel, the control room, never directly from the workspaces, and so do manual steps only the owner can do. The owner gets at most five decisions at a time, each in one sentence with a recommendation, so the answer can be "yes" or "yes except 2". Housekeeping and technical choices are made by the control room and shown in PRs. An experiment that costs money needs the owner's approval of scope, cost cap, account and timing before anything is created." Ratchet: "Text only: messages pass no check, a check cannot tell a fact from a decision, and a check cannot see spending before it happens. A spending limit on the account is the backstop".

The start set grows from nine rules to ten: `ratchet.owner-paths` joins it, because the protection of a row by reference depends on it. Eight of the ten name a check. The criterion of 1.0 that Ratchet uses all its start rules ([D-2026-11-19-one-point-oh](D-2026-11-19-one-point-oh.md), choice 2) then counts ten.

### The counts, and how they were counted

| | Before | After |
|---|---|---|
| Principles | 11 (682 words) | 7 core and 3 production (200 and 88, 288 words) |
| Core rules | 35 (1,632 words) | 19 (1,718 words) |
| Experimental rules that exist today | 19 (1,715 words) | 10 (1,430 words) |
| All rules that exist today | 54 (3,347 words) | 29 (3,148 words) |
| New product rules | 0 | 7 (757 words) |
| All rules | 54 (3,347 words) | 36 (3,905 words) |
| Core rules that are text only | 18 of 35 | 6 of 19 |
| The start set | 9 rules (574 words) | 10 rules (1,016 words) |
| Reference checks shipped | 3 | 3 |

The method: a rule's words are its rule and its ratchet, split at white space in Python, `len((rule + " " + ratchet).split())`. The words "Check:" and "Text only:" count, and the key does not. A principle's words are its title and its question. The "before" column is `ratchet.json` at `ed615d6`. The "after" column counts the unchanged rules from that file and the changed and new rules from the drafts the migration starts from, with the six fixes and the five cuts applied. Each migration pull request counts again from `ratchet.json` as it then stands.

Observation (O): the share of the core that is text only falls because text-only rules merged or left, not because a check was built. It is not to be quoted as progress.

Observation (O): the number of rules nearly halves and the number of words barely moves. The core grows by 86 words, because it gains the seven clauses below. What the redraw cuts is the number of rules to hold and the work of adopting them, not the text.

**Why the core is 19 and not 18.** The question said 18. The terms of the same answer give 19: rules with different checks are not merged, so `ratchet.no-tracing`, whose check is a hook, stays apart from `ratchet.no-secrets`, whose check is a scan. Version 2 had 20, because it kept `ratchet.experiment-plan` whole. The first of the five cuts drops its design checklist and moves its spending approval into `ratchet.ask-the-owner`, which brings the core to 19.

**The product module and the cap.** The question said six product rules. The answer added an alert when the app is broken and locked dependencies, and the rule for a model in the product is deferred, so the module has seven. The cap of [D-2026-11-17-pull-and-budget](D-2026-11-17-pull-and-budget.md) goes from 23 to 17: 10 experimental rules that exist today and 7 product rules. So the seven take places the clean-out freed, and a rule after them needs a place or a decision.

### What is lost, and what is authorized

Every protection or obligation that changes. "Loosened" means that a check goes or gets looser.

| # | What changes | Was in | After | Kind |
|---|---|---|---|---|
| L1 | A Ratchet row may point at the project's own wording, and the check then sees a marker, not the rule's text. | register-on-top | A second, weaker mode, labeled. The copied row and the generated block stay as they are. | Loosened, by a new mode |
| L2 | A decision may be a record in one log the project names, not a file of its own. | decision-as-file | The id form, the verbatim question and answer, and a strict lint of the form chosen all stay. | Loosened |
| L3 | The glossary and its lint leave the core. | glossary | A rule of Ratchet's own with the same text. An adopter may keep it as a rule of its own. | Loosened, moved out |
| L4 | Mutations may run on a schedule the project sets, not in every PR. | test-first, test-can-fail | A scheduled run names the revision it tested and posts its result. It is red when a mutation survives or when the last run is older than the age the project sets. | Loosened |
| R1 | The interview before a project or a large work package. | grill-first | A line in the handbook template. Its number leaves `si-measure` in the same PR. | Removed as a rule |
| R2 | A finding is marked "standards" or "spec". | findings-marked | Gone. "Proven by a run" or "unproven", and the severity, stay. | Removed |
| R3 | Run it for real as early as possible, and a standing approval for local experiments at no cost. | run-early | A line in the handbook template. | Removed as a rule |
| R4 | The control room does not build the product. | cr-does-not-build | A line in the handbook template. | Removed as a rule |
| R5 | Overall, scope and architecture assessments run on the strongest model the project has. | cr-analysis-model | A line in the handbook template. That they run in a fresh context stays, as a clause in `review-by-risk`, and so does "no silent switch to another model". | Removed as a rule |
| R6 | Hourly as the default interval, with a full status every second time. | cr-wake | A line in the handbook template. The project sets the interval. | Removed as a rule |
| R7 | Quiet hours. | cr-quiet-hours | A line in the handbook template. | Removed as a rule |
| R8 | The three phases as a state machine. | phases | "Building starts only on a work package the owner approved, and changes only the files it names" stays, in `cr-workspace`. The rest is a section of the handbook template. | Removed as a rule |
| R9 | An experiment states its hypothesis, the alternatives, how the result is measured, the threshold for success and what would falsify it. | experiment-plan | Gone. The owner's approval of scope, cost cap, account and timing before anything that costs money is created, and the account's spending limit as the backstop, stand in `ask-the-owner` word for word. | Removed |
| R10 | At most three lessons after a failed review or experiment. | lesson-loop | Gone. Lessons are proposed, and apply only after the owner approves them. | Removed |
| R11 | The control room checks a workspace's report against the repo, the PR and the running processes before acting on it. | cr-verify-reports | Gone as a duplicate: `evidence-before-done` keeps "a subagent's 'done' is checked independently". | Removed |
| M1 | A lesson that would apply elsewhere is sent to Ratchet within a week. | si-promote | The same text in `CONTRIBUTING.md`, as an invitation. | Moved out |
| M2 | A core rule leaves only when a check covers it, or a stronger or simpler rule replaces it. | si-subtract | A rule of Ratchet's own, with the same text. | Moved out |
| M3 | The paths of Ratchet's own light and full review classes. | review-by-risk | A rule of Ratchet's own, word for word as [D-2026-11-19-review-by-risk](D-2026-11-19-review-by-risk.md) has them, in the same PR. An adopter lists its classes in a file the owner owns. | Moved out |
| M4 | The steps and minutes to adopt and to upgrade, recorded with each release. | D-2026-11-21-inventory-and-easy-upgrade | Stays as decided. `si-measure` takes the adopter's own number in place of one it has. | Kept |
| M5 | The four letters D, P, O and Q for kinds of statement. | kinds-apart | A line in the handbook template, and a rule of Ratchet's own. "Only the owner approves decisions. Agents write proposals and mark them as proposals" stays in the core, in `owner-paths`. | Moved out |
| T1 | Every scheduled job posts its result, and a late post is red. | nightly-visible | `silence-is-red`. The nightly security scan is still named. | Tightened |
| T2 | The agents' forge account has no admin role, and agents use a temporary directory of their own. | agents-without-keys | Two clauses added. | Tightened |
| T3 | A claim shows the head it ran on, and for a change a user sees, the run shows what the user sees. | evidence-before-done | Two clauses added. | Tightened |
| T4 | The owner's paths include the register and every file it names. The owner's review is dismissed on a new push, and the agents' account cannot bypass it. | one-approver, checks-owner-read | `owner-paths`. | Tightened |
| T5 | A path may also need a security review. | review-by-risk | New, and text only. A test still always gets the full review. | Tightened |
| T6 | "Built" means enforced where the check can refuse, and failed once. | si-harden | Below. Text only for the enforcement half. | Tightened, as a convention |

Two trims of wording carry no obligation: "using whatever wait mechanism its agent tool has" leaves `cr-wake`, and "(see `ratchet.evidence-before-done`)" leaves with R11.

**The authorization.** [RATCHET.md](../RATCHET.md#the-core-is-frozen) lets the wording of a core rule change only to correct an error or to make a rule and its ratchet say the same thing. This decision authorizes, as departures from that, the seven new clauses in core rules: L1, L2, L4, T1, T2, T3 and T4. It also authorizes every loss in the table above: L1 to L4, R1 to R11 and M1 to M5, and that `ratchet.glossary`, `ratchet.grill-first`, `ratchet.run-early`, `ratchet.experiment-plan` and `ratchet.kinds-apart` leave the core although no check covers them and no rule replaces them whole. This amends [D-2026-11-16-register-only](D-2026-11-16-register-only.md), which kept `ratchet.decision-as-file` and `ratchet.glossary` in the core as they were, and choice 1 of [D-2026-11-20-proposal-triage](D-2026-11-20-proposal-triage.md), "no product rules now", whose reason was that Ratchet had no product to try them on. Any other loss, one that is not in the table, still blocks its pull request under [D-2026-11-20-principles-and-obligations](D-2026-11-20-principles-and-obligations.md).

### Adoption by reference, the weaker mode

A Ratchet row in a register has two modes.

- **Copied**, as today. The row holds the rule, the ratchet and the source, and the check compares them character for character, or with `instructions` the block is generated into the instruction file. This is the only mode in which a check sees the text of a rule. A new project starts this way, and the block stays the default.
- **By reference**, new and weaker. The row holds no rule text. It names, in `stands_in`, the file where the rule stands in the project's own words, and that wording is the one in force. The file holds exactly one line `<!-- ratchet:rule <key> -->`, and nothing else in it is read. The row has no version of its own: it follows the register's one `ratchet_version`, so the check runs offline as today. Its `sha256` is the hash of the rule and its ratchet in Ratchet at that version, so an upgrade that changes either fails until someone has looked at the project's wording again. `stands_in` has the path form of `instructions` and is checked the same way.

What the check claims: the file exists, the marker stands in it once, the key is a rule in Ratchet at the stated version, and the hash is that rule's and its ratchet's. It fails on a missing file, a missing or doubled marker, an unknown key, a wrong hash, a row with both text and `stands_in`, `stands_in` on a project's own rule, and a field it does not know, each a fixture that must fail. What it does not claim: it does not read the words under the marker, or whether they say what the rule says, or whether any harness loads the file.

The check and `REGISTER.md` label each such row: "Adopted by reference, the weaker mode. The wording in force is the project's own, in the file named. The check sees a marker, not the words. Protection against a softened wording: not built." The last sentence says "built" only when the register adopts `ratchet.owner-paths` with the status `built`. That reads the register's own claim, not the host. `REGISTER.md` is optional for a register with rows by reference, and where it is generated those rows stand in a table of their own, with no rule text.

The exceptions, named:

- To [D-2026-11-20-generated-block](D-2026-11-20-generated-block.md). That decision chose the block because it is the only way a check sees the text of a rule, and said that with a marker a softened rule can slip through. Both stay true. A marker is allowed all the same, as a weaker mode that says so.
- To [D-2026-11-16-scope](D-2026-11-16-scope.md), point 1, "a project may choose which rows it takes, but not rewrite them". A row by reference is not a copy: for that row the project's wording stands in the rule's place and is the wording in force. Ratchet's own text is not rewritten anywhere. The sentence in [RATCHET.md](../RATCHET.md) that a register "never rewrites" a rule changes with the form.
- Not an exception to [D-2026-11-16-strict-forms](D-2026-11-16-strict-forms.md): the check looks for one exact line and reads no Markdown.

`init.py` gets an adopt mode for a repo that already has an instruction file: it writes only `register.json`, with one copied row, and prints the rows by reference and the marker lines to add. The inventory of [D-2026-11-21-inventory-and-easy-upgrade](D-2026-11-21-inventory-and-easy-upgrade.md) comes first, and gains three things: given the host's exported ruleset as a file, it lists the jobs that run and are not required and what the ruleset says of required review and bypass; it lists files that no harness in use loads; and it prints the lines of the code owners file beside the files the register names, for the owner to compare.

### "Built", by where a check is enforced (#78)

A check counts as built only if it has failed at least once on a real or seeded violation, and only where it can refuse:

| Kind of check | Built when |
|---|---|
| A merge check | It is required for the merge, and it reads its rules from the base branch. |
| A hook | It runs in every harness the project uses. |
| A scheduled check | It posts its result, and it is red when the post is late. |
| A deploy check | No deploy can run without it. |

This is a convention, not an enforced property. A check in the repo cannot see what the host requires or which hooks a machine runs. The definition stands in `ratchet.si-harden` and in the glossary. A register's `where` names the enforcement point and when it was read back. The inventory lists the jobs that run and are not required. No check compares the register with the host: if a second project is bitten, that comes back as a proposal. A script that runs only on an agent's machine, with no lock at the host behind it, is a tripwire and not a lock. This settles what [D-2026-11-21-release-and-redraw](D-2026-11-21-release-and-redraw.md) left open on #78. #78 closes when the inventory exists, not before.

### The product module

Seven rules, all experimental and opt-in, under principles 8, 9, 10 and 6. They are written from one run on one application, so they stay experimental until a second project has used them. Each ratchet ends with what its check does not see.

| Principle | Rule | The check sees | The check does not see |
|---|---|---|---|
| 8 | `release-what-was-tested` | That the deploy step refuses an artifact with no passing run in the test environment, and that a smoke test posts after each deploy. | A deploy by another route. Whether the way back was tried. Whether a change to stored data can be undone. |
| 9 | `accepted-by-who-can-judge` | That each issue marked as accepted has a tagged test in the registry of `root-cause`. | That the test holds what was accepted. Whether the person could judge it. |
| 9 | `boundaries-have-tests` | That each test named in the list of boundaries ran and passed. | Whether the test would catch a crossing. Whether the list is complete. Authorization at every entry point. |
| 10 | `production-health` | That an outside probe posts on its schedule, and that a failure opens an alert. | Errors on paths the probe does not ask for. Whether anyone acted. |
| 10 | `measure-real-use` | That the analysis ran and posted its result. | Whether it read real use. Whether anything was done with it. |
| 10 | `platform-lifecycle` | Dates in one list, against a warning time. | Whether the dates are right. Whether the list is complete. |
| 6 | `dependencies-pinned` | That the required job installs in frozen mode from the lockfile. | Whether a pinned version is safe. Pins the package tool does not record. |

A deploy to production waits for the owner's word, as a text-only clause in `release-what-was-tested`. `irreversible-waits` is not touched. Six of the seven need `not_used_because` in Ratchet's own register, since Ratchet has no runtime, no production and no lockfile. Ratchet can use `platform-lifecycle` itself. The rule for a model in the product is deferred.

### One threat model, and the end of a hardening round

`checks/README.md` gets one text before the first check, and a review brief cites it. `AGENTS.md` gets one line under "How to change a check" that points at it. The text that step 1 writes:

> **What every check here is for.** Ratchet's checks catch mistakes and drift: a rule copied wrong, a test that was dropped, a step taken the usual way without its approval, a job that stopped reporting.
>
> **What no check here is for.** They are not written to stop someone who means to get past them. An agent or a person with write access can soften a rule, reword a check or take a step another way, and a check in the repo will often not see it. What stands against that is a lock at the host: the owner's required review of the paths that hold the rules and the checks, from an account the agents cannot approve with. Where that lock is not built, nothing stands against it, and the register says so. No check guards against someone who controls the owner's account, the host, or the machine a session runs on.
>
> **Tripwires.** A script that runs only on an agent's machine, with no lock at the host behind it, is a tripwire. It catches the usual way and no other.
>
> **Each check's own limits.** This shared text sets the threat model for every check. Each check states its own, narrower claim, under "What it claims" and "What it does not claim", and that claim sets what the check covers.
>
> **When a review finds something the check does not cover.** A finding that the check's own claim does not cover starts no new round of hardening. It becomes one question to the owner: widen the claim by a decision, or record the finding as outside it. A finding inside the check's own claim is fixed as before, and `ratchet.two-rounds` still applies.

The text promises nothing against deliberate softening. The marker of a row by reference gets its fixtures and no further hardening.

### Migration

Smallest and most subtractive first. Each step is a pull request of its own, reviewed by a model from another family by risk, and merged on the maintainer's approval of its head. "Core" means the text of a core rule changes.

| Step | What | Core |
|---|---|---|
| 0 | This decision. | no |
| 1 | The threat model in `checks/README.md`, and the line in `AGENTS.md`. | no |
| 2 | Clean-out of the control room's experimental rules: R4 to R8 become handbook lines, `cr-next-task` goes into `cr-wake`, `cr-verify-reports` leaves (R11), one sentence of `phases` goes into `cr-workspace`, two clauses of `cr-analysis-model` go into `review-by-risk`, whose path list becomes a rule of Ratchet's own in the same PR (M3). The cap goes from 23 to 17. | no |
| 3 | Clean-out of the loop, and the definition of "built": `si-repeat-is-signal` into `si-harden`, rule and count together, with the glossary entry. `si-promote` to `CONTRIBUTING.md`, `si-subtract` to Ratchet's own rules. | no |
| 4 | Principles 11 to 7, every rule under its new principle, and the dial on the landing page drawn again. | no text |
| 5 | `init.py --check` exits 0 when a file exists, and prints paths as typed. | no |
| 6 | The upgrade in one command: `upgrade.py` fetches the tag asked for, or the latest, compares the tags itself, says how far behind the register is, and handles missing history. `UPGRADING.md` shrinks to match. | no |
| 7 | The inventory, as decided, with the three additions. | no |
| 8 | Core batch A, the owner and the questions: `owner-paths`, `ask-the-owner` with the spending clause (R9), the decision log, the glossary out, `grill-first` out with its number in `si-measure`, the letters out (M5), `owner-paths` into the start set. | yes |
| 9a | By reference in the register: `stands_in` and `sha256`, the fixtures, the label, and the clause in `register-on-top`. Validation, rendering and upgrade change together. | yes, one rule |
| 9b | Adopt mode in `init.py`. | no |
| 10 | Core batch B, review and evidence: `fresh-context` and `evidence-before-done`, with `run-early` out (R3). | yes |
| 11 | Core batch C, building, security and lessons: `simplest`, `test-can-fail` with the schedule, `silence-is-red`, `agents-without-keys`, `lesson-names-check` (R10). | yes |
| 12 | The product module: principles 8 to 10 and the seven rules, 10 to 17 under the cap of 17. | no |
| 13 | Documents: the tables of cases move out of what an adopter reads, and the start in the README shrinks. | no |
| 14 | Only if asked: one reference check for an adopter, the check of `silence-is-red` first. | no |

Order that matters: step 8 before 9a, so that the owner's review covers a referenced file before a row can point at one. Step 11 before 12, since three product rules cite `silence-is-red`. A handbook line is added in the pull request in which its rule leaves. Steps 5, 6 and 7 depend on nothing before them. Each core batch carries the table of [D-2026-11-20-principles-and-obligations](D-2026-11-20-principles-and-obligations.md): every failure class each rule covers, before and after, with its evidence. A natural first release is after step 9b, since `stands_in` and `sha256` are meant as the last change of form before the count toward 1.0 starts.

### Fixed in the implementation, not here

These were found by the reviews of version 2 and are fixed in the pull request of their step:

- `release-what-was-tested`: the smoke test fails the deploy, or raises an alert, when it fails or is missing.
- `accepted-by-who-can-judge`: a way out for a change that no test can catch, recorded as such.
- Fixtures for a register that mixes copied rows and rows by reference.
- Trimming prose that repeats itself, in `si-harden` first.
- Owner coverage stays "not built" until there is evidence from the host.
- The upgrade command compares tags and handles missing history.
- #78 closes only when the inventory exists.
- Scanning for known vulnerabilities in dependencies is a stated non-goal of `dependencies-pinned`.

### Unchanged

[D-2026-11-21-inventory-and-easy-upgrade](D-2026-11-21-inventory-and-easy-upgrade.md) stands as written: the inventory, the upgrade in one command, and the overhead recorded with each release. Fable's proposal and the two reviews are not copied into this repo. What they decided is above.
