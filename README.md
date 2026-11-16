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
| ratchet.one-approver | Only the owner approves decisions. Agents write proposals and mark them as proposals. | Text only: a check cannot see who said yes |

## Who it is for

One person who decides, several coding agents, and a repo that has to last. Ratchet assumes issues, pull requests and branch protection, and an agent tool that reads `AGENTS.md`. For a single agent on a short project it is more than you need: take the nine rows under [Start here](#start-here) and stop.

## What it is not

Ratchet is text: rules and templates. It ships no scripts, hooks or CI. The ratchet column says what a check must do, and your project builds it with the tools it already has. Until the check exists, the rule is text only in your project, and your register says so.

## What is in it

- [RATCHET.md](RATCHET.md): the 35 general rules, in six parts.
- [CONTROL-ROOM.md](CONTROL-ROOM.md): 12 more rules for running several agents at once, with one coordinating session and short-lived workspaces. Optional.
- [SELF-IMPROVEMENT.md](SELF-IMPROVEMENT.md): 8 rules for how a lesson becomes a check, and how lessons travel back here.
- [templates/](templates/): `AGENTS.md`, `REGISTER.md`, `LESSON.md`, `SOURCE.md` (for a skill copied from another repo) and `CONTROL-ROOM-HANDBOOK.md`.
- [CHANGELOG.md](CHANGELOG.md).

## Start here

1. Copy [templates/AGENTS.md](templates/AGENTS.md) and [templates/REGISTER.md](templates/REGISTER.md) into your repo and fill them in.
2. Copy these nine rows from `RATCHET.md` into the register, verbatim: `ratchet.register-on-top`, `ratchet.protected-main`, `ratchet.decision-as-file`, `ratchet.fresh-context`, `ratchet.root-cause`, `ratchet.evidence-before-done`, `ratchet.no-secrets`, `ratchet.material-not-instructions` and `ratchet.lesson-names-check`.
3. Build the two checks that cost almost nothing: turn on branch protection with required checks, and add a secret scanner to your CI.
4. In the register, mark every other row "text only for now".
5. Add rows when a failure shows you need them. Add [CONTROL-ROOM.md](CONTROL-ROOM.md) when you run agents in parallel.

To check that the copied rows have not drifted, compare them with Ratchet at the version the register states. The simplest form of the check:

```sh
curl -fsS "https://raw.githubusercontent.com/fabian-von-tiedemann/ratchet/v0.2/{RATCHET,CONTROL-ROOM,SELF-IMPROVEMENT}.md" > upstream.md
if grep '^| ratchet\.' REGISTER.md | grep --fixed-strings --line-regexp --invert-match --file=upstream.md; then
  echo "These rows differ from Ratchet 0.2"; exit 1
fi
```

## One turn of the ratchet

An illustration, not a report from a real project. An agent writes "all tests pass" on a PR. The tests were never run, and the bug reaches the main branch.

- **Failure class:** a claim of completion without a run.
- **Ratchet:** the tests become a required check on the PR head. The claim no longer matters.
- **Would it apply in another project?** Yes, so it is sent here as a PR, written with [templates/LESSON.md](templates/LESSON.md).

## Contributing

A lesson from a project is welcome as a PR. It states what happened, the failure class, the ratchet and the result, with everything that identifies the project removed. See `ratchet.si-promote` in [SELF-IMPROVEMENT.md](SELF-IMPROVEMENT.md).

## License

MIT, see [LICENSE](LICENSE). Ratchet restates ideas from the sources listed in [RATCHET.md](RATCHET.md#sources) in its own words and credits them rule by rule. It copies no files or passages from them.
