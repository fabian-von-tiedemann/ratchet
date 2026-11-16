# Ratchet: the ratchet for agent projects

General rules and templates for long-lived code projects run with AI agents: how decisions are recorded, how questions are asked, how work is reviewed and tested, how secrets are kept out, and how lessons are fed back.

- [RATCHET.md](RATCHET.md): the rules, each with a key, a ratchet and a source.
- [templates/AGENTS.md](templates/AGENTS.md): a template for a project's working rules.
- [templates/SOURCE.md](templates/SOURCE.md): a template for the source and local application of a skill copied from another repo.

## How to use Ratchet

1. Copy the core from `RATCHET.md` verbatim into the project's register and state the version.
2. Add the project's own rules next to the core.
3. Copy the skills the project needs straight from their original repos at a pinned commit, with their licence and a `SOURCE.md`.
4. When the project learns something that would have applied in another project, it becomes a PR here.

## Licence

MIT, see [LICENSE](LICENSE). Ratchet builds on ideas from the sources listed in `RATCHET.md`, but reproduces no text from them.
