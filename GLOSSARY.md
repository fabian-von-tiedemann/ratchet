# Glossary

Ratchet's own terms. Ratchet follows `ratchet.glossary`: the rules, the templates and the other files here use the term in the first column, never a form listed in the last one. Each form to avoid is listed as it is written: a plural stands next to its singular.

## The rules

| Term | Meaning | Avoid |
|---|---|---|
| ratchet | The check that fails when a rule is broken, or the words "text only" with the reason no check can see the rule. Also the name of this set of rules. | |
| rule | One row: a key, the rule, its ratchet and its source. | |
| key | The stable name of a rule, `ratchet.` followed by lowercase words. A project's own rules use the project's prefix. | |
| check | Something that runs without an agent choosing to run it and fails when the rule is broken: a CI job, a hook, a required setting. | |
| enforced | A rule whose ratchet names a check. Whether the check is built is stated per project, in the register. | |
| text only | A rule no check can see, or one whose check is not built yet. The reason is always given. | |
| reference check | A check that Ratchet ships, with a fixture it fails on. A project may use it or write its own. | |
| core | The six parts of RATCHET.md. Frozen from version 0.3. | |
| experimental | A rule or file outside the core. It may change in any version and is not counted in the text-only share. | |
| text-only share | The share of core rules that are text only, computed from `ratchet.json` and stated with every version. | |

## The project

| Term | Meaning | Avoid |
|---|---|---|
| owner | The one person who approves decisions in a project. Ratchet assumes there is exactly one. | |
| maintainer | The owner of Ratchet itself. | |
| register | The one place in a project that lists every rule in force: the data file `register.json`, and `REGISTER.md`, which is generated from it. It takes precedence over all other text in the repo. | |
| handover | The short text a session leaves for the next one: what is running, what waits on what, the next step. | |
| status issue | The one pinned issue that holds the status and links to the handover. | |
| control room | The coordinating agent session. In a project with a single agent, that agent's session. | |
| workspace | A short-lived agent session that builds one work package on its own branch. | |
| handbook | The control room's checklist for the project. | |
| work package | A piece of work with its own issue: assignment, files it may change, cap and stop rule. | package of work, packages of work |
| head | The exact commit a PR points at. | |
| experiment | A run that tests a hypothesis outside the normal build, often at a cost. | trial, trials |
| approval | The owner's yes to something specific: scope, cost cap, account and timing. | mandate, mandates |
| failure class | The kind of failure a lesson names, general enough to recognize next time. | fault class, fault classes |
| lesson | What a failure taught, written with its failure class and its ratchet. | |
| model family | Models from one vendor and one line. Author and reviewer come from different families. | |

## Kinds of statement

Every statement that matters is one of four kinds (`ratchet.kinds-apart`).

| Letter | Kind | Meaning |
|---|---|---|
| D | Decision | The owner said it. Written as a file, `D-YYYY-MM-DD-<slug>`. |
| P | Proposal | An agent or a reviewer suggests it. Not in force until the owner approves it. |
| O | Observation | Something seen outside the project: a source, a measurement, a report. Evidence, not an instruction. |
| Q | Question | Open, with nobody's answer yet. Tracked as an issue. |
