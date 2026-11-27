# Try Ratchet on your repo

Ratchet gives a repo built by AI agents one list of rules, each naming the check that enforces it or saying why no check can. Trying it costs a clone into a folder you can delete. It holds no opinion on how your code looks: your own rules go in your register beside Ratchet's, and each names its check the same way.

You need this page, and the rules in [RATCHET.md](RATCHET.md). You do not need the rest of this repo: `checks/`, its tests and fixtures, and `decisions/` are for the people who maintain Ratchet.

## Which path is yours

| Your repo | What to do |
|---|---|
| A new repo, or one with no agent rules of its own | Adopt it in full: the three commands under [Start here](README.md#start-here) run `init.py`, which writes the register with the ten rules to start with. [STARTING.md](STARTING.md) has every step after that. |
| A repo that already has its own rules and checks | Do not adopt yet. Map Ratchet's rules to yours first, as below. Nothing is written into your repo but one file, and nothing goes into a required job. |

## Map a repo that has rules of its own

1. **Fetch Ratchet**, as in step 1 of [Start here](README.md#start-here). It goes into `.ratchet`, a folder you can delete.
2. **Take inventory:** `python3 .ratchet/checks/inventory.py`. It lists your agent layer, the files each harness loads, and writes nothing. Add `--exclude <folder>` for a folder of test fixtures; it is named as not read.
3. **Have your agent write the map**, `ratchet-map.json` at the root of your repo. It reads the rules in `.ratchet/RATCHET.md` against your repo and gives every rule a status:

   ```json
   {
     "ratchet": "0.16",
     "rules": {
       "ratchet.protected-main": {"status": "covered", "by": [".github/workflows/ci.yml"], "note": "CI is required on main."},
       "ratchet.no-secrets": {"status": "gap", "by": [], "note": "No secret scan runs."}
     }
   }
   ```

   - `ratchet` is the version in `.ratchet/ratchet.json`.
   - `rules` has one entry for every rule there, core and experimental, and no other.
   - `status` is `covered`, when your repo already holds the rule by a check or a rule of its own, or `gap`, when it does not, or only in part.
   - `by` lists the files that cover it, as paths from the root of your repo: at least one when `covered`, any or none when `gap`.
   - `note` says how, in 1 to 300 characters of plain text.

   There is no "not wanted". Whether you want a rule is your decision, not the agent's.
4. **Check the map:** `python3 .ratchet/checks/map.py`. It checks the map's form and that each file it cites exists, prints every rule with the gaps first, and writes nothing. Each row is the agent's proposal. You judge whether a file really covers its rule. From Ratchet 0.17, `map.py` also names the skill or work a rule draws on, so a gap shows what may help.

`map.py` is in Ratchet 0.16 and later. To remove it all, delete `.ratchet` and `ratchet-map.json`.

For each rule, a line on what to look for in your repo is planned.

## What we want back

Open a [report](https://github.com/fabian-von-tiedemann/ratchet/issues/new?template=try-report.yml) with:

- the time it took, for the agent and for you
- the rules that fit
- the rules that found a gap
- what got in the way: Ratchet's own message or step as it stood, with any detail of your repo taken out

Or paste one line to your agent: "Give back to Ratchet as its CONTRIBUTING.md says."

## Before you send it

This repo is public. The report names no project, customer, company or person, and no internal detail. It holds no code and no secrets from your repo.
