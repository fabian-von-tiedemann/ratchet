# Changelog

## 0.10 (unreleased)

<!-- generated:count -->
Ratchet 0.10, computed from `ratchet.json`: the core has 35 rules. 17 name a check and 18 are text only (51%). Ratchet ships a reference check for 1 of the 17. Outside the core there are 19 experimental rules, under a cap of 23: 8 name a check and 11 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

Two rules are added in this version, six leave the experimental rules, and four are changed. It records what 1.0 promises, the six criteria for 1.0, when a rule moves into the core and when an experimental rule must leave, by the decision `D-2026-11-19-one-point-oh`. Every experimental rule gets an age, `since`, a change of form. `ratchet.review-by-risk` comes from the decision `D-2026-11-19-review-by-risk`, choices 1 and 3, and item 3 of `D-2026-11-17-harness-sandbox-risk`. The core rule `ratchet.root-cause` gets a ratchet that names a check, a new experimental rule comes from a project, and the experimental rules are cleaned out under a lower cap, by the decision `D-2026-11-20-proposal-triage`, choices 4 and 5. Choice 5 asks for the clean-out at the next release. Releases are batched, and this version is not released yet, so this version is that release.

Changes of form:

- Every experimental rule in `ratchet.json` has `since`, the version it entered Ratchet, a required field for an experimental rule. It may have `kept_by`, the id of a decision in `decisions/` that kept it once more. A core rule has neither. Both are text. `since` is a version with an entry with a date in the changelog, or the version of the file, and `kept_by` is `D-YYYY-MM-DD-<slug>` with a date that exists. An unknown field still fails, so a misspelled `keptby` is refused. `since` was read from the tags: the first tag whose `ratchet.json`, from 0.3, or whose Markdown tables, in 0.2, hold the key. That is 0.2 for twenty rules, 0.4 for `ratchet.expected-tests-ran`, 0.6 for `ratchet.phases` and 0.7 for `ratchet.irreversible-waits`. `ratchet.review-by-risk`, which enters in this version, has 0.10. The checks of 0.9 refuse the `ratchet.json` of 0.10 for the field they do not know. A register holds neither field, so a project that runs the checks in `.ratchet` has nothing to do. `checks/upgrade.py` reads an older `ratchet.json` without `since`, and says `"since" in a rule is new`. See [UPGRADING.md](UPGRADING.md).
- An experimental rule in `ratchet.json` may have `not_used_because`: why Ratchet itself cannot use the rule, text with at least one letter or digit. A core rule may not. No rule has it in this version, so `checks/upgrade.py` does not name it. The checks of 0.9 would refuse it as a field they do not know.
- `experimental_cap` is 23, from 25 (`D-2026-11-20-proposal-triage`, choice 5).

Added:

- `ratchet.review-by-risk`, experimental, in `CONTROL-ROOM.md`: the depth of a review follows the risk of the paths a PR changes. The light class is `docs/`, the landing page, and `CHANGELOG.md`; a release also changes `RATCHET.md` and gets the full review. A PR whose paths are all light gets a light review, from the same reviewer from another model family at a lower effort. Every other path gets the full review, every test and fixture among them, even one that is only added to, `README.md`, `GLOSSARY.md`, `UPGRADING.md`, `MIGRATING.md` and `HANDOVER.md`, and `templates/`, the instructions to agents, `.claude/`, `.github/`, the checks, the rules, the register and `decisions/`. A mixed PR gets the full review. A finding marked as not blocking starts no new round: the control room fixes it in its next PR and says so on the PR that was reviewed. It is text only, because a check in the repo cannot see the effort of a review. It counts against the cap, which after the clean-out in this version holds 19 experimental rules under a cap of 23.
- `ratchet.one-exact-form`, experimental, in `SELF-IMPROVEMENT.md`, "Rules promoted from projects", from issue #65 (`D-2026-11-20-proposal-triage`, choice 4): a check that must refuse what it does not know accepts one exact form of the whole input and refuses everything else, and where the input cannot be given one form, the check is a tripwire and says so, and a lock elsewhere carries the rule. It is text only, for the reason `repo.strict-forms` gives. Two projects met the failure class. This repo already follows it, as `repo.strict-forms` and `D-2026-11-16-strict-forms`, and its register adopts it. It has `since` 0.10.
- `checks/generate.py --check` fails, naming each rule, when an experimental rule enters in this version, its `since` the version of `ratchet.json`, and this repo's register neither adopts it nor finds in its `not_used_because` why Ratchet cannot use it. It also fails on a rule that the register adopts and that names a reason. It holds only the rules that enter from 0.10 (`D-2026-11-20-proposal-triage`, choice 5). See [checks/README.md](checks/README.md#a-rule-that-enters-is-used).
- This repo's register adopts `ratchet.root-cause`, as "text only for now", since no test here is tagged with a defect's issue and no registry is generated, and `ratchet.one-exact-form`. Its own rules gain `repo.version` and `repo.maintainer-approves`, moved out of Ratchet, and `repo.new-rule-used`, whose check is the one above.
- `RATCHET.md`: "The check for the root cause", what the check of `ratchet.root-cause` must do. Ratchet ships no reference check for it, because tagging a test and reading a registry depend on the project's language and tools.
- `checks/generate.py --check` fails, naming each rule, when an experimental rule has stood through three releases and 60 days with no decision: three versions with a date in the changelog after `since`, and the newest of them 60 days or more after the date of `since`. A rule with `kept_by` stands one age more, counted from the release at which it first stood too long, and then fails with only move, merge or remove: the date of the decision does not move the count, so a rule is kept once, and a later decision in `kept_by` keeps it no longer. The age moves only when a release is dated, so the check fails in the pull request of a release, which is where the clean-out at every release happens. Every tag is from 2026-11-16 to 2026-11-19, so no rule fails today, and the earliest a release can make one fail is 2027-01-15. It also fails on a heading of the changelog whose date does not exist, and, naming both entries, on a release dated before the version before it, since a year mistyped in the newest date would hide every rule. See [checks/README.md](checks/README.md#the-age-of-an-experimental-rule) and [SELF-IMPROVEMENT.md](SELF-IMPROVEMENT.md#the-age-of-an-experimental-rule).
- `SELF-IMPROVEMENT.md`: "What 1.0 promises" and "When 1.0 comes". From 1.0, the form of `ratchet.json` and `register.json`, the keys of the core rules, and which rules belong to the core change only in a major version, and experimental rules are not covered. Six criteria, each with how it is checked or why it is judged, and whether it holds: on 2026-11-19 only one does, `init.py` works. The checks the criteria need are issues #70, #71 and #72, not built here.
- `SELF-IMPROVEMENT.md`, "Rules promoted from projects": a rule moves into the core by a decision of the maintainer that cites four criteria, its text unchanged for two releases and 30 days, used by Ratchet with its check built, a real fault it stopped, and a core that does not get softer, and the same pull request lowers `experimental_cap` by one. That the cap is lowered is text only for now: issue #73.
- This repo's register adopts three experimental rules it already follows: `ratchet.cr-does-not-build`, `ratchet.cr-verify-reports` and `ratchet.si-harden`, the last as "text only for now".
- `decisions/D-2026-11-19-one-point-oh.md`.
- `checks/fixtures/upgrade/released/0.9/`: this repo's register and `ratchet.json` at `v0.9`, which the tests of `upgrade.py` move to this version.
- `docs/index.html`: a landing page for GitHub Pages, served from `docs/` on `main` with no build step (`docs/.nojekyll`). It is one page with its CSS inline, no script, and nothing loaded from another origin, in light and dark. Its text is taken from `README.md`. It goes live when the maintainer turns on Pages for `main` and `/docs`, a setting of the repository.
- `checks/test_pages.py`: a test of this repo that reads the page strictly. It fails on an element or an attribute the page may not hold, an element left open, anything loaded from another origin, a link that leads out of the repo or to a file that does not exist, a link to the page whose fragment is not an id on it, an id twice, a heading that skips a level, an image without alt text, a pair of colors under a contrast ratio of 4.5, and a command that is not a line of a code block in `README.md`. See [checks/README.md](checks/README.md#the-landing-page).
- `checks/init.py --solo`, for one agent and no control room: `AGENTS.md` is written without the line that the control room reads its handbook and without the section on skills. `templates/AGENTS.md` marks those parts with two lines that are HTML comments, one holding `team` before them and one holding `/team` after, which `init.py` never writes, and it does not run when the marks are not in pairs. By choice 3 of the decision `D-2026-11-20-proposal-triage`, from issue #58.
- `checks/check_register.py --agents AGENTS.md` also fails while the file holds a placeholder of `templates/AGENTS.md`, and names each. The placeholders are a fixed list of exact texts in `check_register.py`, a placeholder nested in another one, such as the `<n>` of the handover's, on it on its own, and a test fails when the template holds a part in angle brackets, nested or not, that is not on it. The file is not parsed. From issue #58.
- `checks/init.py` names what is left after the run: each placeholder that `AGENTS.md` holds, the jobs to require in the protection of `main`, and, when the repo's git config names no remote, the adopted rules that wait for one, `ratchet.register-on-top`, `ratchet.protected-main`, `ratchet.no-secrets` and `ratchet.lesson-names-check`, with why. It reads the config as a file and does not run git in the project's repo, so it does not see a remote named only in an include or in a worktree's `config.worktree`. From issues #58 and #59.
- `templates/ratchet-checks.yml` has a second job, `project-checks`, the place for the project's own checks, with one step that says what goes there. `init.py` does not run when the template lacks the job `ratchet` or `project-checks`, or holds one twice. From issue #59.
- `decisions/D-2026-11-20-proposal-triage.md`: the five choices on the open proposals, after two independent triages by other models. This version carries choice 3. Choices 2, 4 and 5 follow in pull requests of their own.

Removed and moved, by `D-2026-11-20-proposal-triage`, choice 5. A register that adopts one of these takes it out of `adopted`, and to keep it, adds it to `own` under its own prefix, as `checks/upgrade.py` prints: see [UPGRADING.md](UPGRADING.md).

- `ratchet.cr-background-wait` is merged into `ratchet.cr-wake`, which keeps its key and its `since`, 0.2. The rule of `ratchet.cr-wake` now holds the wait of a workspace on a run in the background, and the list of open delegations from issue #86.
- `ratchet.cr-lead-with-ask` is removed. It repeated `ratchet.five-choices`, which already asks for each decision in one sentence with a recommendation.
- `ratchet.cr-reads-first` is removed. It repeated `ratchet.work-in-issues`, under which every session reads the status and the handover first, and the order of reading that the working rules give.
- `ratchet.cr-review` is removed. It repeated `ratchet.fresh-context`, `ratchet.once-per-version` and `ratchet.two-rounds`, whose review script it named. `CONTROL-ROOM.md` points to the review script in `RATCHET.md`.
- `ratchet.si-version` moves out of Ratchet into this repo's own register as `repo.version`, with its text as it stood in this version, since it applies only to Ratchet. Its check, `checks/released_text.py`, is the same, and the own rule says so.
- `ratchet.si-maintainer-approves` moves out the same way, as `repo.maintainer-approves`, its text unchanged. It is "Text only for now" until the steps in `HANDOVER.md` are tried, as `ratchet.one-approver` is.
- The count: 24 experimental rules before this, plus `ratchet.one-exact-form`, less the one merged, the three removed and the two moved, is 19, under a cap of 23. The cap goes down by the two that moved, so that the move frees no place.

Changed:

- `ratchet.root-cause`, a core rule, names a check, where it was text only (`D-2026-11-20-proposal-triage`, choice 4, from issues #80, #63 and #66). The check: a PR that links an issue labeled as a defect adds or changes a test tagged with that issue, or says why no test can catch it, and a registry of the tagged tests, generated from the tags, is checked in every PR. A finding that names a failure class is closed by a test that lists every place where the class can occur and fails on each that lacks the guard, and a PR that removes a tagged test or a guard shows a run in which a test still catches its case. The rule gains three sentences so that rule and ratchet say the same thing, as `RATCHET.md` allows for the core: the run stays as a tagged test and is merged with the fix, a fix closes the class and not only the case, and a guard is removed only when a test shows that its case is still caught. Its first three sentences are as they were. The core's text-only share goes from 19 of 35 (54%) to 18 of 35 (51%). A register that adopts it replaces its entry, which gets the status "text only for now" until the project builds the check: `upgrade.py` prints it.
- `ratchet.cr-wake` also holds the list of open delegations, kept in a file and gone through at every wake-up, and what was `ratchet.cr-background-wait`. Its ratchet adds the number of open delegations to the status issue, and says that it does not see whether a workspace waited.
- `checks/upgrade.py`: the step for a removed rule that the register adopts adds that the changelog of the newer Ratchet says why it was removed, and that when it was merged into another rule, the register may adopt that rule in its place.
- `CONTROL-ROOM.md`, `SELF-IMPROVEMENT.md`, `MIGRATING.md`, `HANDOVER.md`, `CONTRIBUTING.md`, `checks/README.md` and `docs/index.html` no longer cite the rules that left, and say that a new experimental rule is used by Ratchet or says why not.
- `ratchet.si-version`: says what 1.0 promises. A minor version adds or tightens rules, and may change, rename or remove an experimental rule. Only a major version changes the form of `ratchet.json` or `register.json`, renames the key of a core rule, or adds a rule to the core or removes one from it. Before 1.0 a minor version may do these too, and the changelog lists every rename, every change of form and every rule that enters or leaves the core. Before, it said that a major version removes rules that a check now covers, and did not separate the core from the experimental rules. Later in this version it moved to this repo's own register as `repo.version`, above, so for an adopting register it is removed: `upgrade.py` from 0.9 says to take it out of `adopted`, or to keep it as an own rule with the entry it prints, which has its 0.9 wording.
- `ratchet.si-subtract`: the removal only when a check covers a rule, and "a candidate for review, not for removal", apply to a core rule. An experimental rule may also be removed in the clean-out at a release, once it has stood through three releases and 60 days with no decision to keep it. Before, the two together made it impossible to remove an experimental rule that no check covers.
- `RATCHET.md`: a core rule leaves only when a check covers it, and an experimental rule may also leave in the clean-out at a release. A rule moves into the core by a decision that cites the criteria in `SELF-IMPROVEMENT.md`, and from 1.0 only in a major version.
- `checks/upgrade.py` says when a field of a rule is new or gone, as it says for a field at the top of `ratchet.json`. A field of a rule counts when some rule of one version holds it and no rule of the other does.
- `docs/index.html`: the line on how a rule leaves says that an experimental rule that has stood too long stops the checks at the next release, and that the rest of the clean-out is planned.
- `checks/generate.py` writes the version in the line of `docs/index.html` that fetches Ratchet, the newest version with a date, as the command in `README.md` names it. `--check` fails when the line is not current, is missing, stands twice, or another line of the page holds `git clone`. So the pull request of a release moves the page with the README when it runs `generate.py`.
- `docs/index.html` explains the concept. A shorter opening says the problem and the promise and leads to "Start here". Two diagrams, ordered lists styled by CSS, with no script, show how the ratchet turns, from a failure to a lesson, a check, the register and the release, and how this repo is run, from the control room to a reviewed and approved merge. Each step links to where the repo shows it. "What Ratchet builds on" lists the four sources in `sources.json`, each with its license, what Ratchet takes from it in Ratchet's own words, and the rules that cite it. "How it stays tight" gives the frozen core, the cap on experimental rules, batched releases, the daily watch of the sources, review before every merge, and the clean-out, which is planned and not built yet. The honest limits stay as they were.
- `checks/generate.py` also writes the line of `docs/index.html` that gives the count of rules and the cap on experimental rules, from `ratchet.json`. `--check` fails when it is not current, is missing, stands twice, is of another form, or another line of the page holds `id="budget"`.
- `docs/index.html` has a new design, made in a separate design session and reviewed by the maintainer. Its text, its links, its two diagrams, the list of sources and the two lines that `generate.py` writes are kept. It adds three figures in inline SVG, a ratchet wheel held by a pawl, one turn of the loop, and how this repo is run, each named by its own title, and dark and orange bands. The wheel turns only for a visitor who has not asked for less motion.
- `checks/test_pages.py` allows inline SVG, a `<title>` in each figure, and `@keyframes`, and nothing wider. An `<svg>` holds only `g`, `path`, `circle`, `rect`, `line`, `text` and `title`, each with a fixed list of attributes, so a `use`, an `image`, a link, a script, a `style`, a `foreignObject`, a marker, a gradient, a filter, `href` and event attributes fail. A value in an `<svg>` is numbers and words and calls only `translate()` and `rotate()`, and a fill or a stroke is `none` or `currentColor`. Each `<svg>` has `role="img"` and one title, which its `aria-labelledby` names, and the only other `title` is in `<head>`. Every `animation` and `scroll-behavior`, also with a vendor prefix such as `-webkit-`, stands inside `@media (prefers-reduced-motion: no-preference)`, a prefixed at-rule such as `@-webkit-keyframes` fails, and a brace that is not matched fails. The colors of the dark and the orange bands, and the `$` before a command on the code of the orange band, are held to a contrast ratio of 4.5 in light and dark, as the others are. See [checks/README.md](checks/README.md#the-landing-page).
- `checks/test_pages.py` reads the list of sources on the page against `sources.json` and the rules in `ratchet.json` that cite each, and fails on a source left out or out of order, a license that differs, or a rule too many or too few. A link out of the repo is allowed only to a source in `sources.json`, matched whole, and a link to an issue of the repo is allowed. Each step of a diagram must link into the repo. The new colors of the boxes and the accent are held to a contrast ratio of 4.5 in light and dark. See [checks/README.md](checks/README.md#the-landing-page).
- `RATCHET.md`, "The review script": the two lines decided in `D-2026-11-17-proposals-2-6` and never written in. In "Build", the assignment states its base and the size of the diff, and the script refuses when the base is not the PR's own, which for a PR stacked on another is the head of the layer below, not the main branch (issue #5). In "Lock", a command that locks for good states what stays locked and what the next allowed step is before it does anything (issue #6). No rule is added or removed.
- `templates/ratchet-checks.yml`: the register check passes `--agents AGENTS.md`, so a project's CI stays red until `AGENTS.md` is filled in. A project that already has the workflow keeps it as it is: see [UPGRADING.md](UPGRADING.md).
- `README.md`, "Start here": `--solo`, what `init.py` names after the run, and the two jobs to require.

Fixed:

- `checks/test_pages.py` passed a step of a diagram whose only link went to a source in `sources.json`. A step now needs a link into this repo, as the page promises.
- `checks/test_pages.py` counted the diagrams by the text `<ol class="flow`, so a list whose class attribute named `flow` after another class was not counted. It now counts the lists that `html.parser` reads with the class `flow` among their classes.
- `checks/test_pages.py` read the line of the page that fetches Ratchet without stripping the spaces that indent it, so an indented line passed `generate.py --check` and failed the test. It now reads the line as `generate.py` does.

## 0.9 (2026-11-19)

<!-- generated:count -->
Ratchet 0.9, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 23 experimental rules, under a cap of 25: 11 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

No rule is added, changed or removed in this version. It changes how Ratchet is released, by the decision `D-2026-11-19-batched-releases`: changes are collected under the first entry of the changelog, headed `(unreleased)`, and released together by a pull request that gives the entry its date. The list of sources moves out of `ratchet.json`, so that a pin that moves needs no new version. It also adds `checks/init.py`, which starts a project with one command, rewrites the README, and fixes the tripwire's exception for a directory from `mktemp -d` on macOS.

Changes of form:

- `date` is gone from `ratchet.json`. The date of a version is in the heading of its entry in `CHANGELOG.md`, and nowhere else.
- `sources` is gone from `ratchet.json`. The list is in `sources.json`, an object with the one field `sources`, read as strictly as every data file. `checks/released_text.py` does not compare it with a tag, so it is not part of what is released. A rule cites its sources by their names in `sources.json`, and `checks/generate.py` fails on a name that is not there. A project that only runs the checks in `.ratchet` has nothing to do: see [UPGRADING.md](UPGRADING.md).

Changed:

- `CHANGELOG.md`: the first entry may be headed `## <version> (unreleased)`. While it is, the release workflow publishes nothing for that version, on a push and on its schedule, and `ratchet.json` may name that version and change. An entry with a date is released by the next push to `main`, and from its tag on it is frozen as before. An unreleased heading anywhere but first, twice, of another form, or for a version that has a tag, fails. See [checks/README.md](checks/README.md#releasepy).
- `checks/release.py` reads, with git, the changelog at each commit on `main` beside `ratchet.json`. A version must be released once a commit on `main` names it with an entry that has a date, also when a later commit heads it `(unreleased)` again: that commit's run fails and names the commit that dated it. A version that `main` only named as unreleased needs nothing.
- `checks/generate.py`: `RATCHET.md` says that the version is not yet released, and the command in `README.md` that fetches Ratchet names the newest version with a date. It is read as one exact line in a code block marked `sh`, and no other line of `README.md` may run `git clone`. The pull request of a release moves it, so for the minutes the release run takes after the merge, and until a rerun if that run is cancelled, it names a tag that does not exist yet. The daily release run is red while it lasts.
- `checks/upgrade.py` says when a field at the top of `ratchet.json` is gone, as it says when one is new.
- `checks/watch_sources.py` and its workflow read `sources.json`.
- The release of a version is a pull request that replaces `(unreleased)` with the date and moves the tag that `README.md` fetches. `checks/generate.py` writes the rest, and `--check` names what is left.
- `README.md` is rewritten: the problem first, then what Ratchet does, the evidence from this repo with a link for each claim, the honest limits, and "Start here" with `init.py`. It fetches 0.9, the first version with `init.py`.

Added:

- `checks/init.py`: one command that starts a project, run from the root of its repo with Ratchet in `.ratchet`. It writes `AGENTS.md` and `register.json` from the templates with the project's name, the generated `REGISTER.md`, and `.github/workflows/ratchet.yml` pinned to the commit of the Ratchet checkout it runs from, and adds `/.ratchet/` to `.gitignore` unless the last line there on `.ratchet` is exactly `.ratchet/` or `/.ratchet/` with no negation after it. It never overwrites a file: a file that exists with other content is skipped and named, and the run exits 1. A file is linked into place whole or not written at all, a `.gitignore` edited meanwhile is left as it is, and it runs only from the root of a git repo, read from `.git` without running git there, and from a Ratchet that is a git checkout of its own with no changes that are not committed. `--check` writes nothing. A second run changes nothing. It ends by running `check_register.py`. See [checks/README.md](checks/README.md#initpy).

Fixed, from the review of PR #50:

- `checks/generate.py` fails when the entries of the changelog do not stand newest first, each version higher than the one after it, and the command in `README.md` that fetches Ratchet names the highest version with a date. Before, it named the first entry with a date, so a changelog with an older entry moved up let a stale pin pass.
- `checks/README.md` says that a green run of `release.py` confirms a tag and a release for every version ever dated on `main`, not every version `main` named, and the tag of the version in the checkout only when its entry has a date, as the review of PR #54 asked.

Fixed, from the sandbox trial in issue #49 (PR #51 and PR #55):

- `checks/tripwire.py`: on macOS, the exception for deleting one's own directory from `mktemp -d` looks where `mktemp -d` writes, the per-user temporary directory that the system gives, and no longer follows `TMPDIR`. Before, a session whose `TMPDIR` was elsewhere had the deletion of a real directory from `mktemp -d` denied, and a directory of that form made in `TMPDIR` let through. When the system gives no absolute path of an existing directory, that root is not trusted at all. `/tmp` stays the second root, and Linux is unchanged. See [checks/README.md](checks/README.md#tripwirepy).
- The tests of the tripwire write nothing to `/tmp`: a directory from `mktemp -d` stands in for it. So the suite passes in a sandbox that refuses writes to `/tmp`, as well as outside one. The hook behaves as before.

## 0.8 (2026-11-19)

<!-- generated:count -->
Ratchet 0.8, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 23 experimental rules, under a cap of 25: 11 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

No rule is added, changed or removed in this version. The form of `ratchet.json` does not change. Two pins in its list `sources` move. `checks/released_text.py` fails when `ratchet.json` names a released version and is not as it stood at that tag, so the move is a version of its own.

Changed:

- `sources`: `google/elephant-goldfish-model` is pinned at `70406c4d22cc7ea8299637c2c5b44625c48b3f08`, in place of `403d8881d62022490637d740657b33f01e321ea8`, and `pstack` at `35a90942a7f02e1ebbc2443643179815f2147954`, in place of `bf0c7cd80abdbf7fe47b634978a7d1b4071f71a7`. These are the heads that the source watch named in #40 and #41. Each new commit is ahead of the old pin, with none behind. The change between the two was read in the maintainer's notes and reviewed by a model from another family: nothing that a rule relies on changed. The proposals that came from that reading are issues of their own, #46 and #47, and change nothing here.
- The table of sources in `RATCHET.md` shows the new pins.

## 0.7 (2026-11-19)

<!-- generated:count -->
Ratchet 0.7, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 23 experimental rules, under a cap of 25: 11 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

One rule is added in this version, and none is changed or removed. The form of `ratchet.json` does not change. The rule comes from issue #23 and the decision `D-2026-11-17-knowledge-and-modes`, item 1. By the decision `D-2026-11-19-locks-not-parsing`, its hook is a tripwire and not a lock, and the locks sit with GitHub and the sandbox. By the decision `D-2026-11-19-tag-ruleset-scope`, the tag ruleset locks moving and deleting a tag, and not creating one.

Added:

- `ratchet.irreversible-waits`, experimental, in a new part of `CONTROL-ROOM.md`, "What cannot be undone": an agent goes ahead with a step that can be undone, and a step that cannot waits for an approval from the owner that names the step and the exact command. The five steps are a force push, creating or deleting a tag, creating or changing a release, deleting outside the working tree, and changing the repository's settings. The part says where each step is locked and where it is not.
- `checks/tripwire.py`, its reference check: a `PreToolUse` hook for Claude Code that denies the usual spellings of the five steps when no approval names them, and any write by an agent to the approvals file. It is a tripwire, not a lock: it claims the cases that [checks/README.md](checks/README.md#tripwirepy) lists and no others, and another spelling gets past it. It never exits other than 0 or 2. The templates `claude-settings.json` and `ratchet-approvals.json` wire it into a project, and this repo runs it from `.claude/settings.json`.
- `templates/tag-ruleset.json`: a ruleset for every tag, with the rules `deletion`, `update` and `non_fast_forward` and the repository admin role as the only bypass actor, for the owner to apply. It leaves creating a tag open, so the release workflow tags as before. See [checks/README.md](checks/README.md#the-tag-ruleset).

Changed:

- `checks/README.md` describes the rehearsal of the release of 0.7 and the upgrade fixtures from 0.3 to 0.6, which it had left at 0.5 and at 0.3 and 0.4.

## 0.6 (2026-11-19)

<!-- generated:count -->
Ratchet 0.6, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 22 experimental rules, under a cap of 25: 10 name a check and 12 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

One rule is added in this version, and none is changed or removed. The form of `ratchet.json` does not change. The rule comes from the decision `D-2026-11-17-knowledge-and-modes`, item 4, and is one rule rather than three by the decision `D-2026-11-19-locks-not-parsing`, item 5.

Added:

- `ratchet.phases`, experimental and text only, in a new part of `CONTROL-ROOM.md`, "The phases": a work package is in one phase at a time, explore, build and run, and for each the rule says what an agent may do in it and what ends it. Explore changes nothing that others rely on, build works on one approved work package and merges on green checks and a passed review, and run operates what is merged and sends a fix back to build.

## 0.5 (2026-11-18)

<!-- generated:count -->
Ratchet 0.5, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 21 experimental rules, under a cap of 25: 10 name a check and 11 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

No rule is added or removed in this version, and one is changed. It adds a way for a project to upgrade, and a cap on the rules outside the core, by the decision `D-2026-11-17-pull-and-budget`. The cap is a new required field in `ratchet.json`, a change of form, which a minor version before 1.0 may now make, by the decision `D-2026-11-18-form-change-before-1-0`.

Added:

- `checks/upgrade.py` and `UPGRADING.md`: the upgrade path. Given a project's `register.json` and the `ratchet.json` of the version the register states, the script prints what the register must do to move to the Ratchet it is run from: for each adopted rule that changed or was removed, the entry to paste or the reason to remove it, and for each new rule, the entry to paste if the project adopts it. It writes nothing and runs offline, on the files it is given. It fails when the register does not pass against the version it states, and it checks that the register with every step done passes against the newer one. See [checks/README.md](checks/README.md#upgradepy).
- `experimental_cap` in `ratchet.json`: the most experimental rules there may be, 25, which is the 20 there were when the decision was recorded on `main`, plus five. Every check that reads `ratchet.json` fails when there are more, so `generate.py --check` is red. A new experimental rule then replaces, merges or removes one, or a decision raises the cap. The count of rules states the cap.

Changed:

- `ratchet.si-version`: before 1.0, a minor version may also change the form, and the changelog lists every change of form, as it lists every rename. The rest of the rule is as it was. A register that adopts it replaces its entry: `upgrade.py` prints the new one, and a status and a `where` stay.

Changes of form:

- `ratchet.json` has `experimental_cap`, a required field, a whole number from 0. A `ratchet.json` without it, or with a value of another kind, is not a valid data file. Ratchet's checks read `ratchet.json` strictly, so the checks of 0.4 refuse the `ratchet.json` of 0.5 for the field they do not know, and the checks of 0.5 refuse that of 0.4 for the field it lacks. A project whose checks are those in `.ratchet`, fetched at the version its register states as the README says, has nothing to do: the checks and `ratchet.json` come from the same version. A project that keeps a copy of a Ratchet check, or has a check of its own, that reads `ratchet.json` replaces the copy with the one from 0.5, or changes its check to read the field. `upgrade.py` says so when the form changed between the two versions it compares.

## 0.4 (2026-11-17)

<!-- generated:count -->
Ratchet 0.4, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 21 experimental rules: 10 name a check and 11 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

Added:

- `ratchet.expected-tests-ran`, experimental, in a new part of `SELF-IMPROVEMENT.md` for rules promoted from projects: a suite of tests made from a source fails when a test it expects did not run and pass. Its reference check, `checks/expected_tests.py`, runs this repo's suite in a child process, through `checks/suite_runner.py`, and reads the record that the runner writes of every outcome and of the end of the run. It fails when a test did not pass exactly once, when the run did not finish, and when a file under `checks/fixtures/` was not loaded by a test that passed. It catches tests dropped by mistake, not test code written to defeat it. See [checks/README.md](checks/README.md#expected_testspy).
- `checks/released_text.py`: fails when a released changelog entry, or the `ratchet.json` of a released version, is not as it stood at its tag, when a tag has no changelog entry, and when an entry after the first has no tag. A version that adds a rule is released on its own, by the decision `D-2026-11-17-new-approaches`.
- `checks/release.py` and `.github/workflows/release.yml`: a version is tagged and released when it reaches `main`, from the version in `ratchet.json` (PR #9). The release text is one fixed line, with links to this changelog and to the files at the tag: nothing is copied from the changelog. A run fails closed: when it cannot confirm that every version that `ratchet.json` on `main` has named is tagged and released, it is red, and it writes nothing before every check has passed. It never moves, deletes or edits a tag. A scheduled run every day writes nothing, and is red while a version is unfinished. It names that version when the GitHub API answers, which is not promised. See [checks/README.md](checks/README.md#releasepy) and the decisions `D-2026-11-17-release-on-merge`, `D-2026-11-17-release-links`, `D-2026-11-17-release-narrow-claim` and `D-2026-11-17-release-fail-closed`.
- `checks/watch_sources.py` and `.github/workflows/watch-sources.yml`: a watch, once a day, on the sources pinned in `ratchet.json` (PR #10). When a source has moved past its pin, or its pinned commit is gone, it opens one issue for it. An issue holds only values the watch has checked itself and text written in the code, never text from a source. It is a tool of this repo, not a reference check for a rule. See [checks/README.md](checks/README.md#watch_sourcespy).

Changed:

- Only the first entry of the changelog, the version being released, is generated. Every entry after it stays as it was released.
- The tests in `checks/test_checks.py` and `checks/test_watch_sources.py` load their fixtures through `FixtureTest`.

## 0.3 (2026-11-16)

<!-- generated:count -->
Ratchet 0.3, computed from `ratchet.json`: the core has 35 rules. 16 name a check and 19 are text only (54%). Ratchet ships a reference check for 1 of the 16. Outside the core there are 20 experimental rules: 9 name a check and 11 are text only. They are not counted in the share. The share counts what kind of ratchet a rule has, not whether a project has built the check: a project's register says that, and Ratchet's own is REGISTER.md.
<!-- /generated -->

In 0.1 and in 0.2, counted the same way: `RATCHET.md` had 35 rules, 14 named a check and 21 were text only (60%). Ratchet shipped no check.

The core is frozen from this version: see [RATCHET.md](RATCHET.md#the-core-is-frozen) and the decision [D-2026-11-16-scope](decisions/D-2026-11-16-scope.md). The tag `v0.2` was already published when this work was finished, so it is released as 0.3: see [D-2026-11-16-renumber](decisions/D-2026-11-16-renumber.md).

**The format of a register changes.** In 0.2 a register was a Markdown file, checked by a few lines of shell. From 0.3 it is a data file, `register.json`, and `REGISTER.md` is generated from it. A register written for 0.2 has to be moved by hand: see [MIGRATING.md](MIGRATING.md). Ratchet ships no reference check for decision files or for the glossary. Two attempts were reviewed and set aside, and how to check them is an open question.

The reason for the new format is that two reviews in a row found new ways to hide a changed row from a check that read Markdown. A data file has one form, and the generated file is compared with it byte for byte.

Added:

- `ratchet.json`: every rule as data, with its part, its status (`core` or `experimental`) and its enforcement (`enforced` or `text-only`). The rule tables are generated from it.
- A reference check for `ratchet.register-on-top`, `checks/check_register.py`. It reads a project's `register.json`, compares it with Ratchet at the version it states, and fails unless `REGISTER.md` is exactly what the data generates. A value in a data file is text, never Markdown: it is written into a generated file with a backslash before every punctuation mark, so that data cannot become a link, HTML or hidden text. The one other form is code, between a pair of backticks. A value is written in Latin script: its characters come from one fixed list of Latin letters, digits, the plain space and marks, written out as code points in the check, so that a value is valid or not the same on every supported version of Python. No character on the list is written right to left or changes the order a line is shown in. No character on the list is a compatibility form, which is not a protection against characters that look alike. A name between two colons is refused, so that a site cannot show it as a picture. A person named with `@`, an issue named with `#` and the id of a commit are accepted and written as text, and what a site makes of them is not covered. Every file a check reads is strict UTF-8, and bytes that are not UTF-8 fail the check. See [checks/README.md](checks/README.md) and [D-2026-11-17-latin-strict-utf8](decisions/D-2026-11-17-latin-strict-utf8.md). It has a clean project copy it passes on and one copy for each fault it fails on, including every way of hiding a row that the reviews found. It runs in this repo's CI, together with a check that the generated text matches the data files.
- `GLOSSARY.md`: Ratchet's own terms.
- Ratchet's own `AGENTS.md`, `register.json` with the generated `REGISTER.md`, `HANDOVER.md` and first seven decisions.
- `.github/CODEOWNERS`: the maintainer owns every path. It takes effect when the protection on `main` requires the code owner's review, which the maintainer sets up after this version is published.
- The templates `register.json`, `DECISION.md`, `GLOSSARY.md` and `ratchet-checks.yml`.
- `MIGRATING.md`: how to move a register written for 0.2.

Changed:

- Ratchet no longer says that it ships no checks. It ships one, and says which.
- `ratchet.one-approver` and `ratchet.checks-owner-read` now name a check: a required review by the owner, through code ownership, with agents under an account of their own. The share of core rules that are text only falls from 21 to 19 of 35.
- A project adopts rules verbatim, in its `register.json`. It chooses which rules it takes and never rewrites one. `templates/register.json` holds the nine starting rules.
- `CONTROL-ROOM.md` and `SELF-IMPROVEMENT.md` are marked experimental and are not counted in the text-only share.
- `ratchet.glossary`: the rule and its ratchet now say the same thing. The glossary lists the terms to avoid, and the check fails on them.
- `ratchet.work-in-issues`: the handover may be a file in the repo that the status issue links to.
- `ratchet.cr-reads-first`: reads "the latest handover", wherever the project keeps it.
- `ratchet.lesson-names-check`: the rule no longer holds a link, which broke when the row was copied into a register.
- The contract for the review script moved from `CONTROL-ROOM.md` to `RATCHET.md`, because three core rules depend on it.
- The README says whose rules these are: the maintainer's own way of working with agents, kept up to date, and open for others to use.
- The README's shell lines for comparing a copy are replaced by the reference check, and the start is written as steps to run from an empty project.
- `templates/DECISION.md` asks for the original and a marked translation when the question was put in another language.
- `templates/AGENTS.md` no longer names one agent tool's directory for skills.

Removed:

- `templates/REGISTER.md`: a register is generated from data, not copied and edited.

## 0.2 (2026-11-16)

Added:

- `SELF-IMPROVEMENT.md`: how a lesson becomes a check and travels back to Ratchet, with versioning and a two-week measure.
- `CONTROL-ROOM.md`: how a project is run with one coordinating agent session and short-lived workspaces, with the contract for the review script.
- The templates `REGISTER.md`, `LESSON.md` and `CONTROL-ROOM-HANDBOOK.md`.
- `ratchet.protected-main`.
- A starting set of nine rows and a way to check a copy, in the README.
- The icon.

Changed:

- The ratchet column now starts with "Check:" or "Text only:", and every "text only" gives its reason. Ratchet says plainly that it ships no checks.
- Decision ids are `D-YYYY-MM-DD-<slug>` (was `U-`). The four kinds of statement are decision (D), proposal (P), outside observation (O) and open question (Q).
- "Trial" is now "experiment", and "mandate" is "approval".
- The source column shows a dash where it said "Own experience".

Renamed keys:

| 0.1 | 0.2 |
|---|---|
| ratchet.keep-kinds-apart | ratchet.kinds-apart |
| ratchet.issues | ratchet.work-in-issues |
| ratchet.one-place | ratchet.one-channel |
| ratchet.facts-yourself | ratchet.look-up-facts |
| ratchet.finding-proof-axis | ratchet.findings-marked |
| ratchet.receive | ratchet.verify-findings |
| ratchet.factory | ratchet.checks-owner-read |
| ratchet.other-family | ratchet.register-review-first |
| ratchet.proven-before-own | ratchet.reuse-first |
| ratchet.run-before-paper | ratchet.run-early |
| ratchet.test-tests-the-claim | ratchet.test-can-fail |
| ratchet.trial-description | ratchet.experiment-plan |
| ratchet.guard-visible | ratchet.nightly-visible |
| ratchet.keys-away | ratchet.agents-without-keys |
| ratchet.ratchet | ratchet.lesson-names-check |

Removed:

- `ratchet.up-to-ratchet`: covered by `ratchet.si-promote`.

## 0.1 (2026-11-16)

- First version: `RATCHET.md` with rules in six parts, and templates for `AGENTS.md` and `SOURCE.md`.
