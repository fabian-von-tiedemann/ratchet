# Upgrading to a newer Ratchet

A project states in `register.json` which version of Ratchet it follows. To move to a newer version, the project runs `checks/upgrade.py` from the newer Ratchet. The script compares the two versions rule by rule and prints what the register must do. It writes nothing, and it reads only the files it is given. The upgrade is a PR of its own (`ratchet.si-pull`).

This works for a register on 0.3 or later. A register written for 0.2 is moved by hand first: see [MIGRATING.md](MIGRATING.md).

## Steps

Run these in the root of your own repo, on a branch of their own. The commands below move a register from 0.4 to 0.5. Put in the version your register states and the version you move to.

1. Fetch the newer Ratchet into `.ratchet`, in place of the old one. Then take the `ratchet.json` of the version your register states from its tag, and keep it beside the new Ratchet.

   ```sh
   rm -rf .ratchet
   git clone --branch v0.5 https://github.com/fabian-von-tiedemann/ratchet .ratchet
   git -C .ratchet show v0.4:ratchet.json > .ratchet/from.json
   ```

2. Print what the register must do.

   ```sh
   python3 .ratchet/checks/upgrade.py register.json --from .ratchet/from.json
   ```

   It fails, and prints no steps, when the register does not pass against the version it states. Fix that first: an upgrade starts from a register that matches its Ratchet.

3. Do each step in `register.json`. A changed rule comes with its new entry: replace the old entry with it. A removed rule is taken out of `adopted`, or moved to `own` under your own prefix if the project keeps it. When a rule's ratchet changed and your check is marked `built`, look again at whether the check still does what the ratchet says.
4. Choose which new rules, if any, the project adopts. Each comes with its entry. Add a rule when a failure shows you need it, not because it is new. Before 1.0, a new version may rename a key: the changelog lists every rename, and the old key shows as removed and the new one as new.
5. Write `REGISTER.md` again and check it.

   ```sh
   python3 .ratchet/checks/check_register.py register.json --write REGISTER.md
   python3 .ratchet/checks/check_register.py register.json --markdown REGISTER.md
   ```

6. In `.github/workflows/ratchet.yml`, put in the commit of the new tag. This prints it.

   ```sh
   git -C .ratchet rev-parse "v0.5^{commit}"
   ```

7. Open the PR. Its description holds the output of `upgrade.py` and of the check, and says which new rules the project adopted and why. Read why each rule changed in the newer Ratchet's [CHANGELOG.md](CHANGELOG.md), in the entries after your old version.

## What the script does not do

- It does not find out which version is the latest. You say which Ratchet you fetch.
- It does not change `register.json`, `REGISTER.md` or any other file.
- It does not see whether a check marked `built` still exists or works. When a rule's ratchet changed, it says so, and the project looks.
- It does not list a rule that only moved to another part of Ratchet.
