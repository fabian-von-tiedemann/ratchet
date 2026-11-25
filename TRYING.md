# Try Ratchet on your repo

Ratchet gives a repo built by AI agents one list of rules, each naming the check that enforces it or saying why no check can, and trying it costs a clone into a folder you can delete and an estimated 20 to 40 minutes of reading.

## Which path is yours

| Your repo | What to do |
|---|---|
| A new repo, or one with no agent rules of its own | Adopt it in full: the three commands under [Start here](README.md#start-here) run `init.py`, which writes the register with the ten rules to start with. [STARTING.md](STARTING.md) has every step after that. |
| A repo that already has its own rules and checks | Do not adopt yet. Fetch Ratchet as in step 1 of [Start here](README.md#start-here), then run `python3 .ratchet/checks/inventory.py`, which reads your agent layer and writes nothing. Read the rules in [RATCHET.md](RATCHET.md), and the new and changed rules of the latest release in [CHANGELOG.md](CHANGELOG.md), against your repo. Note each rule that finds a gap. Put nothing in a required job. |

For the second path, a mode that only maps your checks to Ratchet's rules, and a line per rule on what to look for in your repo, are planned.

## What we want back

Open a [report](https://github.com/fabian-von-tiedemann/ratchet/issues/new?template=try-report.yml) with:

- the time it took, for the agent and for you
- the rules that fit
- the rules that found a gap
- what got in the way: Ratchet's own message or step as it stood, with any detail of your repo taken out

Or paste one line to your agent: "Give back to Ratchet as its CONTRIBUTING.md says."

## Before you send it

This repo is public. The report names no project, customer, company or person, and no internal detail. It holds no code and no secrets from your repo.
