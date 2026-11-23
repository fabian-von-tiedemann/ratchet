# Starting with Ratchet

Every step after the three commands under [Start here](README.md#start-here) in the README. Run everything in the root of your own git repo. If you followed 0.2, read [MIGRATING.md](MIGRATING.md) first. If your register follows 0.3 or later, [UPGRADING.md](UPGRADING.md) moves it to this version.

`init.py` takes one of two paths, and says which:

| Your repo | Path |
|---|---|
| Has no instruction file | [A new repo](#a-new-repo) |
| Has an instruction file of its own, such as `AGENTS.md` or `CLAUDE.md` | [A repo with an instruction file of its own](#a-repo-with-an-instruction-file-of-its-own) |

## A new repo

`init.py` writes `AGENTS.md`, `register.json`, the generated `REGISTER.md`, and `.github/workflows/ratchet.yml` pinned to the commit of `.ratchet`, and adds `/.ratchet/` to `.gitignore`. It never overwrites a file: one that exists is skipped and named.

| Option | What it does |
|---|---|
| `--name` | Sets the project's name. Without it, the name is the folder's name. |
| `--solo` | For one agent and no control room. Leaves the control room and the skills out of `AGENTS.md`. |

Then it names what is left: the placeholders in `AGENTS.md`, the jobs to require in the protection of `main`, and, when the repo has no remote yet, the adopted rules that wait for one. Last it runs the register check. See [checks/README.md](checks/README.md#initpy).

`register.json` holds ten rules to start with, copied verbatim: you choose which rules you take, and you never rewrite one. Your own rules go in the list `own`, under your own prefix. `REGISTER.md` is generated: to change it, change `register.json` and write it again.

What is left for you:

1. Fill in the parts of `AGENTS.md` in angle brackets, and commit the files. The workflow runs the register check on every PR, and it fails while `AGENTS.md` still holds a placeholder of the template.
2. Build the two checks that cost almost nothing: turn on branch protection with the jobs `ratchet` and `project-checks` required, and add a secret scanner to your CI, in the job `project-checks`, which is the place for your own checks. When your agents have an account of their own, add code ownership for the decisions, the register and every file it names, and the checks. It is what turns `ratchet.owner-paths` into a check.
3. When a check exists, set the rule's `status` to `built` in `register.json` and say in `where` where the check lives. Everything else stays `text only for now`.
4. [Add a rule](#add-a-rule) when a failure shows you need it.

## A repo with an instruction file of its own

`init.py` runs in adopt mode. Run `python3 .ratchet/checks/inventory.py` first to see what your agent layer holds. `init.py` writes only `register.json`, with one rule copied, `ratchet.register-on-top`, and never changes your file. It writes no `AGENTS.md` to fill in, no `REGISTER.md`, and no workflow, so there are no jobs `ratchet` or `project-checks` to require.

What is left for you:

1. For each other rule to start with, `init.py` prints the rule, a marker line and a row by reference. Where your file states the rule in your own words, put the marker line there, alone on a line, and paste the row into `adopted` in `register.json`, each as printed, from its first character. Leave out a rule your file does not state, or state it there first. A marker counts only in a file in UTF-8 with LF line endings.
2. Add the one step it prints to a job that the protection of your `main` already requires, and commit `register.json` and your file. It adds no workflow and no required job, so you need no admin. `python3 .ratchet/checks/inventory.py --ruleset <file>`, given the ruleset or branch protection of `main` exported from your host, names which jobs are required. Add `/.ratchet/` to `.gitignore` if `init.py` says it is missing.
3. [Add a rule](#add-a-rule) when a failure shows you need it, with the rows you add.

A row by reference is the weaker mode: the check sees the marker, not your words.

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
