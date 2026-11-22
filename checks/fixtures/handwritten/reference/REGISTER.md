# Register for a project written by hand

Every rule in force in this project. This file takes precedence over all other text in the repo. It is generated from `register.json`: change that file, never this one.

## Rules from Ratchet

Ratchet version: 9.9. The rows below are copied verbatim from Ratchet at that version. The project chooses which rows it adopts and never rewrites one.

| Key | Rule | Ratchet | Source |
|---|---|---|---|
| ratchet.example-one | Every change has a test\. | Check\: the tests run on every PR | — |

## Rules adopted by reference

Ratchet version: 9.9. Each row below names a rule of Ratchet at that version and the file where the project's own wording of it stands, and its sha256 in `register.json` is that of the rule and its ratchet. Each file named holds one marker line for each of its rows. No rule text stands here.

| Key | Stands in | Mode |
|---|---|---|
| ratchet.example-two | `RULES.md` | Adopted by reference\, the weaker mode\. The wording in force is the project\'s own\, in the file named\. The check sees a marker\, not the words\. Protection against a softened wording\: not built\. |

## Where each check stands

One row for each adopted rule whose ratchet starts with "Check:". The status is "built" or "text only for now". A built check says where it lives.

| Key | Status | Where the check lives |
|---|---|---|
| ratchet.example-one | built | `.github/workflows/tests.yml` |

## The project's own rules

None yet.
