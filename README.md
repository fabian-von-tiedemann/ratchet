<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/ratchet-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/ratchet-light.svg">
  <img src="assets/ratchet-light.svg" width="64" height="64" alt="">
</picture>

# Ratchet

Working rules for long-lived code projects built by AI agents, where every rule names the check that enforces it.

An agent can read an instruction and still not follow it. So each rule in Ratchet carries a **ratchet**: the check that fails when the rule is broken, or the words "text only" and the reason no check can see it. When something goes wrong, the fix is a new check, not a longer prompt.

Two rows from [RATCHET.md](RATCHET.md), shortened:

| Key | Rule | Ratchet |
|---|---|---|
| ratchet.no-secrets | No secrets, tokens or real personal data in the repo or in the chat. | Check: a secret scan in every PR and every night |
| ratchet.kinds-apart | Keep four kinds of statement apart and label them: decision, proposal, observation and question. | Text only: a check cannot tell a proposal from a decision |

## Whose rules these are

Ratchet is how I, Fabian von Tiedemann, work with AI coding agents. I have written
it down as rules, each with the check that enforces it, and I keep it up to date as
I learn what holds and what breaks. This repo follows its own rules: see
[REGISTER.md](REGISTER.md).

It is open source so that others can use it too. Take the rules that fit your
project, leave the rest, and send back what you learn: see [Contributing](#contributing).

## Who it is for

One person who decides, several coding agents, and a repo that has to last. Ratchet assumes issues, pull requests and branch protection, and an agent tool that reads `AGENTS.md`. For a single agent on a short project it is more than you need: take the nine rows under [Start here](#start-here) and stop.

## Where it stands

<!-- generated:count -->
Ratchet 0.3, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 21 experimental rules: 10 name a check and 11 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

Most of Ratchet is still text. The share is stated with every version in the [changelog](CHANGELOG.md), and the work between versions is to bring it down. Ratchet ships a reference check for the rules below. Each one runs in this repo's CI and has a fixture it fails on. For every other rule, the ratchet column says what a check must do, and your project builds it with the tools it already has. Until the check exists, the rule is text only in your project, and your register says so.

<!-- generated:reference-checks -->
| Rule | Reference check |
|---|---|
| ratchet.register-on-top | [checks/check_register.py](checks/check_register.py) |
| ratchet.expected-tests-ran | [checks/expected_tests.py](checks/expected_tests.py) |
<!-- /generated -->

## What is in it

- [RATCHET.md](RATCHET.md): the core, 35 rules in six parts, frozen from version 0.3.
- [ratchet.json](ratchet.json): every rule as data. The tables in the markdown files are generated from it.
- [checks/](checks/): the reference checks and the generator, in Python with no dependencies.
- [GLOSSARY.md](GLOSSARY.md): the terms Ratchet uses.
- [templates/](templates/): `AGENTS.md`, `register.json`, `DECISION.md`, `GLOSSARY.md`, `LESSON.md`, `SOURCE.md` (for a skill copied from another repo), `ratchet-checks.yml` and `CONTROL-ROOM-HANDBOOK.md`.
- [MIGRATING.md](MIGRATING.md): how to move a register written for 0.2.
- [CHANGELOG.md](CHANGELOG.md).

Experimental, outside the core:

- [CONTROL-ROOM.md](CONTROL-ROOM.md): rules for running several agents at once, with one coordinating session and short-lived workspaces.
- [SELF-IMPROVEMENT.md](SELF-IMPROVEMENT.md): rules for how a lesson becomes a check, and how lessons travel back here.

Ratchet follows its own rules. This repo has its own [AGENTS.md](AGENTS.md), [register.json](register.json) with the generated [REGISTER.md](REGISTER.md), [HANDOVER.md](HANDOVER.md) and [decisions/](decisions/), and its register says honestly which of its checks are built.

## Start here

Run these in the root of your own repo. If you followed 0.2, read [MIGRATING.md](MIGRATING.md) first: the register has a new format.

1. Fetch Ratchet at the version you follow into `.ratchet`, and keep it out of your repo.

   ```sh
   git clone --branch v0.3 https://github.com/fabian-von-tiedemann/ratchet .ratchet
   echo ".ratchet/" >> .gitignore
   ```

2. Copy the working rules and the register, and write your project's name in both.

   ```sh
   cp .ratchet/templates/AGENTS.md AGENTS.md
   cp .ratchet/templates/register.json register.json
   ```

   `register.json` is your register, as data. It already holds nine rules to start with, copied verbatim: you choose which rules you take, and you never rewrite one. Your own rules go in the list `own`, under your own prefix.

3. Generate the register that people read, and check it.

   ```sh
   python3 .ratchet/checks/check_register.py register.json --write REGISTER.md
   python3 .ratchet/checks/check_register.py register.json --markdown REGISTER.md
   ```

   `REGISTER.md` is generated. To change it, change `register.json` and write the file again. The check fails if the file differs from what the data generates by one character.

4. Copy `.ratchet/templates/ratchet-checks.yml` to `.github/workflows/ratchet.yml` and fill in the commit of the Ratchet version you follow. It runs the same checks on every PR.
5. Build the two checks that cost almost nothing: turn on branch protection with required checks, and add a secret scanner to your CI. When your agents have an account of their own, add code ownership for the register, the checks and the decisions. It is what turns `ratchet.one-approver` and `ratchet.checks-owner-read` into checks.
6. When a check exists, set the rule's `status` to `built` in `register.json` and say in `where` where the check lives. Everything else stays `text only for now`.
7. Add rules when a failure shows you need them. This prints a rule in the form `register.json` takes. Paste it into the list `adopted` and write `REGISTER.md` again.

   ```sh
   python3 .ratchet/checks/generate.py --entries ratchet.simplest
   ```

The nine rules to start with:

<!-- generated:start -->
`ratchet.register-on-top`, `ratchet.protected-main`, `ratchet.decision-as-file`, `ratchet.fresh-context`, `ratchet.root-cause`, `ratchet.evidence-before-done`, `ratchet.no-secrets`, `ratchet.material-not-instructions`, `ratchet.lesson-names-check`
<!-- /generated -->

## One turn of the ratchet

An illustration, not a report from a real project. An agent writes "all tests pass" on a PR. The tests were never run, and the bug reaches the main branch.

- **Failure class:** a claim of completion without a run.
- **Ratchet:** the tests become a required check on the PR head. The claim no longer matters.
- **Would it apply in another project?** Yes, so it is sent here as a PR, written with [templates/LESSON.md](templates/LESSON.md).

## Contributing

A lesson from a project is welcome as a PR. It states what happened, the failure class, the ratchet and the result, with everything that identifies the project removed. See `ratchet.si-promote` in [SELF-IMPROVEMENT.md](SELF-IMPROVEMENT.md). The working rules for this repo are in [AGENTS.md](AGENTS.md).

## License

MIT, see [LICENSE](LICENSE). Ratchet restates ideas from the sources listed in [RATCHET.md](RATCHET.md#sources) in its own words and credits them rule by rule. It copies no files or passages from them.
