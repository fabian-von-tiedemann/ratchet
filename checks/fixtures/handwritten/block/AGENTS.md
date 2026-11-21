<!-- ratchet:begin -->
## Rules in force

Generated from `register.json` by Ratchet's `check_register.py`. Never edit this block by hand: change `register.json` and print the file again with `check_register.py register.json --print-instructions`. The check fails on any other text between the two markers. `REGISTER.md` holds the same rules and takes precedence over all other text in the repo.

### Rules from Ratchet

Ratchet version: 9.9. The rows below are copied verbatim from Ratchet at that version. The project chooses which rows it adopts and never rewrites one.

| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.example-one | Every change has a test\. | Check\: the tests run on every PR | — |

### Translations

A translation is there for the people who read the rules in that language. The English text above is the rule. Each translation is bound to the English text it translates by that text's sha256, so a rule that changes fails the check until its translation is made again.

| Key | Language | Translation |
|---|---|---|
| ratchet.example-one | sv | Varje ändring har ett test\. |

### Where each check stands

One row for each adopted rule whose ratchet starts with "Check:". The status is "built" or "text only for now". A built check says where it lives. Then one row for each of the project's own rules that has a status.

| Key | Status | Where the check lives |
|---|---|---|
| ratchet.example-one | built | `.github/workflows/tests.yml` |
| hand.lint | built | `.github/workflows/lint.yml` |

### The project's own rules

Same form as Ratchet's. The keys use the project's own prefix, never `ratchet.`.

| Key | Rule | Ratchet | Source |
|---|---|---|---|
| hand.lint | Every file passes the lint\. | Check\: the lint runs on every PR | — |
<!-- ratchet:end -->

# Working rules, typed by hand

Text of the project's own.
