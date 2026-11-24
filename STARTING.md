# Starting with Ratchet

Every step after the three commands under [Start here](README.md#start-here) in the README. Run everything in the root of your own git repo. If your `register.json` follows an earlier version, [UPGRADING.md](UPGRADING.md) moves it to this version.

`init.py` takes one of two paths, and says which:

| Your repo | Path |
|---|---|
| Has no instruction file | [A new repo](#a-new-repo) |
| Has an instruction file of its own: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` or `.claude/CLAUDE.md` | [A repo with an instruction file of its own](#a-repo-with-an-instruction-file-of-its-own) |

## A new repo

`init.py` writes `AGENTS.md`, `register.json`, the generated `REGISTER.md`, and `.github/workflows/ratchet.yml` pinned to the commit of `.ratchet`, and adds `/.ratchet/` to `.gitignore`. It never overwrites a file: one that exists is skipped and named.

| Option | What it does |
|---|---|
| `--name` | Sets the project's name. Without it, the name is the repo's name in the url of its git remote, or else the folder's name, and `init.py` says which. |
| `--solo` | For one agent and no control room. Leaves the control room and the skills out of `AGENTS.md`. |

Then it names what is left: the placeholders in `AGENTS.md`, the jobs to require in the protection of `main`, and, when the repo has no remote yet, the adopted rules that wait for one. Last it runs the register check. See [checks/README.md](checks/README.md#initpy).

`register.json` holds ten rules to start with, copied verbatim: you choose which rules you take, and you never rewrite one. Your own rules go in the list `own`, under your own prefix. `REGISTER.md` is generated: to change it, change `register.json` and write it again.

What is left for you:

1. Fill in the parts of `AGENTS.md` in angle brackets, and commit the files. The workflow runs the register check on every PR, and it fails while `AGENTS.md` still holds a placeholder of the template.
2. Build the two checks that cost almost nothing: turn on branch protection with the jobs `ratchet` and `project-checks` required, and add a secret scanner to your CI, in the job `project-checks`, which is the place for your own checks. When your agents have an account of their own, add code ownership for the decisions, the register and every file it names, and the checks. It is what turns `ratchet.owner-paths` into a check.
3. When a check exists, set the rule's `status` to `built` in `register.json` and say in `where` where the check lives. Everything else stays `text only for now`.
4. [Add a rule](#add-a-rule) when a failure shows you need it.

## A repo with an instruction file of its own

`init.py` runs in adopt mode. Run `python3 .ratchet/checks/inventory.py` first to see what your agent layer holds. `init.py` never changes your file, and writes no `AGENTS.md`, no `REGISTER.md` and no workflow, so there are no jobs `ratchet` or `project-checks` to require. The first run writes nothing at all.

What is left for you:

1. For each rule to start with, `init.py` prints the rule, a marker line and a row by reference. Where your file states the rule in your own words, put the marker line there, alone on a line, as printed, from its first character. Put it outside a Markdown list, before or after it: a marker between two list items ends the list. Leave out a rule your file does not state, or state it there first. A marker counts only in a file in UTF-8 with LF line endings. Leave out `ratchet.register-on-top` while your own file is the one that governs.
2. Run `init.py` again with `--adopt <key>` for each rule whose marker you put in. It writes `register.json` with those rows and no other, and only when the register passes. No row is copied: a copied `ratchet.register-on-top` would say that the register lists every rule in force and takes precedence, which is not so while your file governs.
3. Copy `checks/run_pinned.py` into your repo from the pinned commit, with the command `init.py` prints, and add the one step it prints to a job that the protection of your `main` already requires, or the line it prints for the local check script that CI runs, which stops the script when the check fails, with `set -e` or without it. The copy is kept only when it is the pinned commit's file, and the step checks that again before it runs it. It runs the register check from the pinned commit's own files, read with no git config, so an edit in `.ratchet` never runs. Give the job `permissions: contents: read` and its checkout `persist-credentials: false`, as printed. Commit `register.json`, the copy and your file. No workflow and no required job are added, so you need no admin. `python3 .ratchet/checks/inventory.py --ruleset <file>`, given the ruleset or branch protection of `main` exported from your host, names which jobs are required. Add `/.ratchet/` to `.gitignore` if `init.py` says it is missing. See [checks/README.md](checks/README.md#run_pinnedpy).

   The step may run in a job that the protection of `main` does not require, if you would rather not block a merge on it. Either way it fails, and never passes, when it cannot reach Ratchet to fetch the pinned commit.
4. A row whose rule names a check starts as `text only for now`. When your host enforces it, such as the protection of `main`, set `status` to `built` and say in `where` where it is enforced and when you read it back.
5. [Add a rule](#add-a-rule) when a failure shows you need it, with the rows you add.

A row by reference is the weaker mode: the check sees the marker, not your words.

### If your file states a rule only in part

When your wording holds a rule's core but not every clause, you may still adopt it by reference, in part: put the marker line by your wording, and in the row's `where` list what it leaves out, exactly as `"where": "Not stated here: <clause>; <clause>."`. When your wording leaves out any part of a sentence of the rule, list that whole sentence as one clause, not only the part it misses: a list of parts tends to miss one more at each review. The row is then labeled "adopted in part" with those clauses, and it cannot be `built` until your wording states them and the phrase is gone. The check sees the phrase, not whether the clauses you list are the real gaps. The details are in [checks/README.md](checks/README.md#check_registerpy).

## Add a rule

The first command prints a rule in the form `register.json` takes. Paste it into the list `adopted`. The second prints `REGISTER.md` again and puts it in place.

```sh
python3 .ratchet/checks/generate.py --entries ratchet.simplest
rm -f REGISTER.md.new && python3 .ratchet/checks/check_register.py register.json --print-markdown > REGISTER.md.new && rm -f REGISTER.md && mv REGISTER.md.new REGISTER.md
```

The check writes nothing: the second command prints the file to a new one and moves that into place, and `rm -f` first removes a link at either name, so nothing is written through one.

## The rules to start with

The ten rules to start with:

<!-- generated:start -->
`ratchet.register-on-top`, `ratchet.protected-main`, `ratchet.decision-as-file`, `ratchet.owner-paths`, `ratchet.fresh-context`, `ratchet.root-cause`, `ratchet.evidence-before-done`, `ratchet.no-secrets`, `ratchet.material-not-instructions`, `ratchet.lesson-names-check`
<!-- /generated -->

Each is a row of [RATCHET.md](RATCHET.md), with its ratchet. For one agent on a short project, these ten are enough.
