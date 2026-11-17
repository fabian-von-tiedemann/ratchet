# Handover

The state of Ratchet between sessions (`ratchet.work-in-issues`). Replaced, not appended to, after every important event. Every session reads it after [AGENTS.md](AGENTS.md) and [REGISTER.md](REGISTER.md).

Last replaced: 2026-11-17, with auto-merge and the release workflow.

## What is running

Nothing.

## What waits on what

- **Code ownership is pending setup.** `.github/CODEOWNERS` is in the repo. The agents' account is decided and not yet created, and the protection on `main` is not yet set ([D-2026-11-16-code-owner](decisions/D-2026-11-16-code-owner.md)). Until then `ratchet.one-approver`, `ratchet.checks-owner-read` and `ratchet.si-maintainer-approves` are "text only for now" in [REGISTER.md](REGISTER.md). They become "built" in a PR of its own, after these steps:
  1. `gh api repos/fabian-von-tiedemann/ratchet/branches/main/protection` shows one required approval, the code owner's review required, approvals dismissed on a new push, and the job `checks` as a required status check.
  2. `gh api repos/fabian-von-tiedemann/ratchet/collaborators` shows the agents' account with the role Write and no more.
  3. A pull request from the agents' account, with its checks green and an approval from that account, cannot be merged before the code owner approves.
  4. After the code owner approves, a new push from the agents' account removes the approval.
- **The agents' account must not merge by hand, and nothing stops it yet.** It may turn on auto-merge, which merges only after the code owner has approved the latest push ([D-2026-11-17-auto-merge](decisions/D-2026-11-17-auto-merge.md)). With write access it is able to merge by hand a pull request that the code owner has approved. `repo.agents-own-account` stays text only until a lock for that has been found and tried.
- **`ratchet.protected-main` is not met in this repo** and stays "text only for now": administrators are exempt from the protection, and the rule says they are not. Whether the rule should allow that for a sole owner is an open question for the next version.
- `ratchet.no-secrets` is "text only for now" in this repo: no secret scan runs here yet.

## Next step

How to check decision files and the glossary is an open question ([D-2026-11-16-register-only](decisions/D-2026-11-16-register-only.md)). Two attempts to read them as text were reviewed and still let text hide. The proposal on the table is a small data part for each decision that is checked strictly, with the prose left as prose and outside the check. Until that is decided, the next step is a secret scan for this repo.

## Open questions

Tracked as issues with the label `question`.
