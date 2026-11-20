# Upgrading to a newer Ratchet

A project states in `register.json` which version of Ratchet it follows. To move to a newer version, the project runs `checks/upgrade.py` from the newer Ratchet. The script compares the two versions rule by rule and prints what the register must do. It writes nothing, and it reads only the files it is given. The upgrade is a PR of its own (`ratchet.si-pull`).

This works for a register on 0.3 or later. A register written for 0.2 is moved by hand first: see [MIGRATING.md](MIGRATING.md).

A new project does not upgrade. From 0.9 it starts with `checks/init.py`, as the [README](README.md#start-here) says. `init.py` never overwrites a file, so it is not a way to move a register: in a project that already has one, it skips the files that exist and writes only what is missing.

## Steps

Run these in the root of your own repo, on a branch of their own. The commands below move a register from 0.8 to 0.9. Put in the version your register states and the version you move to.

1. Fetch the newer Ratchet into `.ratchet`, in place of the old one. Then take the `ratchet.json` of the version your register states from its tag, and keep it beside the new Ratchet.

   ```sh
   rm -rf .ratchet
   git clone --branch v0.9 https://github.com/fabian-von-tiedemann/ratchet .ratchet
   git -C .ratchet show v0.8:ratchet.json > .ratchet/from.json
   ```

2. Print what the register must do.

   ```sh
   python3 .ratchet/checks/upgrade.py register.json --from .ratchet/from.json
   ```

   It fails, and prints no steps, when the register does not pass against the version it states. Fix that first: an upgrade starts from a register that matches its Ratchet.

3. Do each step in `register.json`. A changed rule comes with its new entry: replace the old entry with it. A removed rule is taken out of `adopted`. If the project keeps it, add the entry printed with it to `own` as well. That entry has the fields of an own rule, `key`, `rule`, `ratchet` and `source`, and keeps the status and the `where` it had, which an own rule may have from 0.10. It has no translation: an own rule is written in the project's own words. Its key has the prefix of your first own rule, or, when you have none, a prefix made from the project's name; you may change the prefix, but not to `ratchet`. When a rule's ratchet changed and your check is marked `built`, look again at whether the check still does what the ratchet says. When a rule you adopt with a translation changed its text, the script prints its entry without the translation and with the sha256 of the new text: translate the new rule and add the translation back with that sha256. Until then the register check fails on the old translation, which is what binds it to the text it translates.

   When every rule the register adopts was removed, the register must adopt at least one rule, because a register that adopts none does not pass the check. The script then says so, and prints the entries to choose from: the new rules, or the rules to start with when there are no new ones.
4. Choose which new rules, if any, the project adopts. Each comes with its entry. Add a rule when a failure shows you need it, not because it is new. Before 1.0, a new version may rename a key: the changelog lists every rename, and the old key shows as removed and the new one as new. Before 1.0, a new version may also change the form of `ratchet.json`: the changelog lists every change of form.

   When the fields at the top of `ratchet.json` differ between the two versions, the script says so after the steps. Nothing changes in the register for it. The checks in `.ratchet` come with the `ratchet.json` of their own version, so they need nothing. If the project keeps a copy of a Ratchet check, or has a check of its own, that reads `ratchet.json`, replace the copy with the one from the newer Ratchet, or change the check: Ratchet's checks read `ratchet.json` strictly, so the checks of one version refuse the `ratchet.json` of another whose form differs. From 0.4 to 0.5, `experimental_cap` is new. From 0.5 to 0.6, from 0.6 to 0.7 and from 0.7 to 0.8, the form does not change. From 0.8 to 0.9, `date` and `sources` are gone: the date of a version is in the heading of its entry in the changelog, and the sources are in `sources.json`, which is not part of what is released ([D-2026-11-19-batched-releases](decisions/D-2026-11-19-batched-releases.md)). The register holds neither, and none of the templates reads them, so a project that runs the checks in `.ratchet` has nothing to do. From 0.9 to 0.10, every experimental rule in `ratchet.json` has `since`, the version it entered Ratchet, and may have `kept_by`, the id of a decision that kept it once more ([D-2026-11-19-one-point-oh](decisions/D-2026-11-19-one-point-oh.md)). The script tells it as `"since" in a rule is new`. The register copies only the key, the rule, the ratchet and the source of a rule, so it holds neither, and a project that runs the checks in `.ratchet` has nothing to do. An experimental rule of 0.10 may also have `not_used_because`, why Ratchet itself cannot use it. No rule has it in 0.10, and the register does not hold it either. Also from 0.9 to 0.10, `ratchet.json` has a list `principles`, and every rule names one of them in `principle` (`D-2026-11-20-principles-and-obligations`). A principle is a question to ask when no rule fits, or an aim: guidance, text only, and what is checked is the rules under it. The script tells it as `"principles" is new` and `"principle" in a rule is new`. A register adopts rules, not principles, and holds neither field, so a project that runs the checks in `.ratchet` has nothing to do.

   From 0.9 to 0.10 the form of `register.json` grows too (`D-2026-11-20-generated-block`), and the script says so. Each new field may be left out, so a register of 0.9 stays valid and nothing is a step. A register may name its instruction file, such as `AGENTS.md` or `CLAUDE.md`, in `instructions`. The register check then checks a block of the rules that it generates into that file, between a begin and an end marker, byte for byte, and `check_register.py register.json --write-block` writes the block, at the end of the file the first time. Write it there, and say in the rest of the file that the block is generated, if you like: the check reads nothing outside it. An adopted rule may carry a `translation`, a language, the text and the sha256 of the English rule, in Latin script only. An own rule may carry `status` and `where`, as an adopted rule does. See [checks/README.md](checks/README.md#check_registerpy).

   From 0.9 to 0.10, six experimental rules leave Ratchet ([CHANGELOG.md](CHANGELOG.md), the entry for 0.10). The script shows each as removed. `cr-background-wait` is merged into `ratchet.cr-wake`: if you adopted it, adopt `ratchet.cr-wake` in its place, or keep the old rule in `own`. `cr-lead-with-ask`, `cr-reads-first` and `cr-review` are removed, because other rules say the same. `si-version` and `si-maintainer-approves` applied only to Ratchet itself, and moved into Ratchet's own register. A project that adopted any of them and wants to keep it adds the entry the script prints to `own`, under the project's own prefix. That is what Ratchet's own register did with the two that moved. `ratchet.root-cause` now names a check: its entry gets the status "text only for now" until the project builds the check that [RATCHET.md](RATCHET.md#the-check-for-the-root-cause) describes.

   A rule whose check runs in the agent's harness, not in CI, needs that check copied into the project. From 0.7, that is `ratchet.irreversible-waits`, whose check is the hook `checks/tripwire.py`: a project that adopts the rule keeps a copy at `.claude/hooks/tripwire.py`, as [CONTROL-ROOM.md](CONTROL-ROOM.md#what-cannot-be-undone) says, and replaces it with the one from the newer Ratchet at each upgrade.
5. Write `REGISTER.md` again and check it. If the register names an instruction file, write its block again too, with `--write-block`: the script prints that command then.

   ```sh
   python3 .ratchet/checks/check_register.py register.json --write REGISTER.md
   python3 .ratchet/checks/check_register.py register.json --markdown REGISTER.md
   ```

6. In `.github/workflows/ratchet.yml`, put in the commit of the new tag. This prints it.

   ```sh
   git -C .ratchet rev-parse "v0.9^{commit}"
   ```

   From 0.9 to 0.10, `templates/ratchet-checks.yml` also passes `--agents AGENTS.md` to the register check, which then fails while `AGENTS.md` holds a placeholder of the template, and has a job `project-checks` for the project's own checks. Nothing requires them: take them from `.ratchet/templates/ratchet-checks.yml` if you want them.

7. Open the PR. Its description holds the output of `upgrade.py` and of the check, and says which new rules the project adopted and why. Read why each rule changed in the newer Ratchet's [CHANGELOG.md](CHANGELOG.md), in the entries after your old version.

## What the script does not do

- It does not find out which version is the latest. You say which Ratchet you fetch.
- It does not change `register.json`, `REGISTER.md` or any other file.
- It does not see whether a check marked `built` still exists or works. When a rule's ratchet changed, it says so, and the project looks.
- It does not list a rule that only moved to another part of Ratchet.
