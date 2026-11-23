<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/ratchet-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/ratchet-light.svg">
  <img src="assets/ratchet-light.svg" width="64" height="64" alt="">
</picture>

# Ratchet

Ratchet is a set of working rules for long-lived code projects built by AI agents, with templates and reference checks. Each rule names its **ratchet**: the check that fails when the rule is broken, or the words "text only" and the reason no check can see it. So no rule claims a protection it does not have.

AI agents read your instructions and still say "done" without running the tests. The maintainer had more than 100 repos built by agents, and no longer knew what governed the agents in them. With Ratchet, each repo owns its rules. It keeps them in one file, the register, borrows the ones it wants from Ratchet, and adds its own. Nothing arrives by itself: a rule changes in your repo only when you upgrade, in a pull request of its own.

Two rules from [RATCHET.md](RATCHET.md), shortened:

| Key | Rule | Ratchet |
|---|---|---|
| ratchet.no-secrets | No secrets, tokens or real personal data in the repo or in the chat. | Check: a secret scan in every PR and every night |
| ratchet.ask-the-owner | The agent looks up facts itself. Decisions belong to the owner. | Text only: a check cannot tell a fact from a decision |

## The principles

<!-- generated:principle-list -->
- Keep one place
- Make the gate independent of the author
- Wait for the owner on what cannot be undone
- Show the run\, and treat silence as red
- Make checks that can fail\, and turn failures into checks
- Guard the boundaries
- Subtract first
- Ship what was tested\, and know the way back
- Keep what was accepted
- Watch production and the ground under the code
<!-- /generated -->

The first seven are for every project. The last three are for an application with users in production, over the opt-in rules in [PRODUCT.md](PRODUCT.md). Each is a question to ask when no rule fits, or an aim: guidance, text only. What is checked is the rules under them in [RATCHET.md](RATCHET.md#the-principles).

## When to use it

Ratchet is built for one person who decides, several coding agents, and a repo that has to last. It assumes issues, pull requests and branch protection, and an agent tool that reads an instruction file such as `AGENTS.md`.

| Your situation | What to do |
|---|---|
| A new repo | Run the three commands under [Start here](#start-here). |
| A repo with an instruction file of its own, such as `AGENTS.md` or `CLAUDE.md` | Run the same three commands. `init.py` sees your file and never changes it. It prints a marker line for each rule, and writes your register when you run it with `--adopt <key>`. |
| One agent and no control room | Run the same three commands, with `--solo` on `init.py`. |
| One agent on a short project | Ratchet is more than you need. Read [the rules to start with](STARTING.md#the-rules-to-start-with) and stop. |
| A register that follows 0.3 or later | [UPGRADING.md](UPGRADING.md): one command moves it to this version. |
| A register written for 0.2 | [MIGRATING.md](MIGRATING.md) first. |
| A rule that does not fit your project | Open an issue with the [proposal form](https://github.com/fabian-von-tiedemann/ratchet/issues/new?template=proposal.yml). That is what Ratchet improves from. |

## Start here

Run these in the root of your own git repo.

1. Fetch Ratchet at the latest release into `.ratchet`.

   ```sh
   git clone --branch v0.11 https://github.com/fabian-von-tiedemann/ratchet .ratchet
   ```

2. See what it would write. This writes nothing.

   ```sh
   python3 .ratchet/checks/init.py --check
   ```

3. Write it. In a repo with an instruction file of its own, this run writes nothing either: it prints what to do, and `--adopt` writes.

   ```sh
   python3 .ratchet/checks/init.py
   ```

`init.py` never overwrites a file. It ends by naming what is left for you to do, and [STARTING.md](STARTING.md) walks through it.

## What you get

| In | `init.py` writes |
|---|---|
| A new repo | `AGENTS.md`, the working rules your agents read first, with parts for you to fill in. `register.json`, your register, with the rules to start with. `REGISTER.md`, the register that people read, generated from it. A workflow that runs the register check on every pull request. |
| A repo with an instruction file of its own | Nothing on the first run. It prints a marker line for each rule to start with. Put the marker by your own wording of a rule, and `init.py --adopt <key>` writes `register.json` with a row by reference that points at it. It also prints one step for your CI, which runs the register check from the pinned commit. |

From then on:

- **A rule cannot be softened quietly.** A rule you borrow is copied verbatim, and the register check fails when a copy differs by one character.
- **The register says what is built.** Each rule that names a check says whether your project has built it. Until it has, the rule is text only in your project.

## The honest limits

- **Most rules come without a check you can copy.** Ratchet ships a reference check for a few rules, listed in [checks/README.md](checks/README.md#reference-checks). For the rest, the ratchet says what your check must do, and you build it with the tools you have. The count is in [RATCHET.md](RATCHET.md#the-core-is-frozen).
- **The checks catch mistakes and drift, not someone who means to get past them.** See [the threat model](checks/README.md#the-threat-model).
- **A row by reference is the weaker mode.** The check sees a marker line in your file, not your words. A rule your file states only in part is adopted in part: its row starts `Not stated here:` and lists what is left out, and the check does not see whether that list is right. See [STARTING.md](STARTING.md#if-your-file-states-a-rule-only-in-part).
- **Some of what holds in this repo is an instruction, not a lock,** such as the review from another model family. [REGISTER.md](REGISTER.md) and [AGENTS.md](AGENTS.md) say which.
- **Ratchet does not clean up an agent layer you already have.** `inventory.py` lists what the layer holds. What to remove is yours to decide.
- **The form may still change.** Before 1.0, a minor version may change the form of the data files, and the changelog lists every such change ([D-2026-11-18-form-change-before-1-0](decisions/D-2026-11-18-form-change-before-1-0.md)).

## Read more

| For | Read |
|---|---|
| The rules, the principles and the sources | [RATCHET.md](RATCHET.md), generated from [ratchet.json](ratchet.json) and [sources.json](sources.json) |
| Every step after `init.py` | [STARTING.md](STARTING.md) |
| What each check claims, and what it does not | [checks/README.md](checks/README.md). The checks are Python with no dependencies. |
| A newer version | [UPGRADING.md](UPGRADING.md) and [CHANGELOG.md](CHANGELOG.md) |
| The terms Ratchet uses | [GLOSSARY.md](GLOSSARY.md) |
| Templates: the instruction file, the register, a decision, a lesson, a glossary, the source of a skill copied from another repo, the workflow and the control room's handbook | [templates/](templates/) |
| Several agents at once, experimental | [CONTROL-ROOM.md](CONTROL-ROOM.md) |
| How a failure becomes a check, and what this repo shows of it, experimental | [SELF-IMPROVEMENT.md](SELF-IMPROVEMENT.md) |
| An application with users in production, experimental and opt-in | [PRODUCT.md](PRODUCT.md) |
| Why a rule or a form is as it is | [decisions/](decisions/) |
| A proposal, or a lesson from your project | [CONTRIBUTING.md](CONTRIBUTING.md). This repo's own working rules are in [AGENTS.md](AGENTS.md). |

Ratchet is how I, Fabian von Tiedemann, work with AI coding agents. It is open source: take the rules that fit your project, leave the rest, and send back what you learn.

## License

MIT, see [LICENSE](LICENSE). Ratchet restates ideas from the sources listed in [RATCHET.md](RATCHET.md#sources) in its own words and credits them rule by rule. It copies no files or passages from them.
