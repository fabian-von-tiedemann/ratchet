# Moving a register written for 0.2

In 0.2 a register was a Markdown file that you edited, and the check was a few lines of shell in the README. From 0.3 the register is a data file, `register.json`, and `REGISTER.md` is generated from it. The format changed, and a register written for 0.2 has to be moved by hand. Nothing does it for you, because nothing in Ratchet reads rules out of Markdown any more.

## Why

A check that looks for rows in a Markdown file can miss a row that a reader still sees: an indented row, a row inside a comment, a row after a heading that is not a heading. Two reviews in a row found new ways to do that. A data file has one form. The check reads the data, and the Markdown is compared with what the data generates, byte for byte.

## What stays the same

The keys. Every rule in 0.2 has the same key in 0.3. The core is the same 35 rules.

## What changed in the rules

A register takes Ratchet's wording at the version it states, so these change when you move:

- `ratchet.glossary`: the rule and its ratchet now say the same thing.
- `ratchet.work-in-issues`: the handover may be a file in the repo.
- `ratchet.lesson-names-check`: the rule no longer holds a link.
- `ratchet.one-approver` and `ratchet.checks-owner-read`: the ratchet is now a check, a required review by the owner through code ownership.
- Six rules of 0.2 are no longer in Ratchet from 0.10: one merged into another, three removed and two moved into Ratchet's own register. The entry for 0.10 in the [changelog](CHANGELOG.md) names them. `generate.py --entries` refuses a key that is not a rule. To keep one, write it in `own` under your own prefix.

## Steps

Run these in the root of your own repo.

1. Fetch Ratchet 0.8 into `.ratchet`, as in the [README](README.md#start-here).
2. Read your old `REGISTER.md` and write down the keys it adopts, the status of each check, and your own rules. Keep the old file under another name until you are done.
3. Copy the template and write your project's name in it.

   ```sh
   cp .ratchet/templates/register.json register.json
   ```

4. Print the rules you adopt, and put them in the list `adopted` in place of the nine that the template holds. Use the keys your project adopts, not these two.

   ```sh
   python3 .ratchet/checks/generate.py --entries ratchet.register-on-top ratchet.no-secrets
   ```

5. For each rule that has a `status`, set it to `built` and add `where` if your check exists. Otherwise leave `text only for now`.
6. Move your own rules into the list `own`: `key`, `rule`, `ratchet` and `source` for each.
7. Write the new `REGISTER.md` and check it. Then delete the old file.

   ```sh
   python3 .ratchet/checks/check_register.py register.json --write REGISTER.md
   python3 .ratchet/checks/check_register.py register.json --markdown REGISTER.md
   ```

8. Replace the shell lines from the 0.2 README with `.ratchet/templates/ratchet-checks.yml`, and run each command in it once from the root of your repo before you rely on it.

A value in `register.json` is text, not Markdown. A link or emphasis in one of your own rules is shown as the characters you wrote. Put a part in a pair of backticks if it is code. A value is written in Latin script, with the characters listed in `.ratchet/checks/README.md`. The check names any character it does not take, such as a letter from another script or a combining accent, and it refuses a mail address in text and a name between two colons.
