# Reference checks

Checks that Ratchet ships. Each one runs in this repo's CI ([checks.yml](../.github/workflows/checks.yml)) and has a fixture it fails on. They use Python's standard library only, so a project needs nothing installed to use them. They have been run on Python 3.9 and 3.12.

<!-- generated:reference-checks -->
| Rule | Reference check |
|---|---|
| ratchet.register-on-top | [checks/check_register.py](check_register.py) |
<!-- /generated -->

## Data files and strict forms

No check here looks for rules in free Markdown. A check that does can be shown a file in which a reader sees a row and the check does not: an indented row, a row in a comment, a row under a heading that is not a heading. Each way that was found is closed the same way:

- **What a check needs to read is data.** The register is `register.json`. A data file is read strictly: valid JSON in UTF-8, no field twice in one object, no field the check does not know, every value of the kind it must be.
- **Every file is strict UTF-8.** A check decodes every file it reads as UTF-8 and fails on bytes that are not, with the file and the byte named. No byte is read as some other character, so a file with a wrong byte never compares equal to a file without it.
- **What people read is generated.** `REGISTER.md` is written from the data file and compared with it byte for byte. Nothing can be added to the generated file, hidden in it or changed in it without failing the check.
- **A value is text, never Markdown.** When a value from a data file is written into a generated file, every ASCII punctuation mark in it gets a backslash, so Markdown reads none of it as markup. A value cannot become a link, an image, emphasis, HTML or a comment. The generator does not try to work out what Markdown would make of a value.
- **Code is the one other form.** A part of a value between a pair of backticks is code. That is the data's own way to mark it, and the generator writes it as a code span. Two such parts have text between them, and code has no spaces at its ends.
- **Characters from one fixed list.** A value is one line. Every character in it is a Latin letter, a digit, a plain space or one of the marks listed under [The characters a value may hold](#the-characters-a-value-may-hold). Everything else is refused, with the character named: other scripts, combining marks, control and format characters, other kinds of space, line and paragraph separators, fillers that show as nothing, lone surrogates, the replacement characters, characters that are written right to left, controls that change the order a line is shown in, and compatibility forms such as full-width letters. An `@` between two characters is refused outside code, because it is read as a mail address whatever is escaped.
- **The list is code points in the check.** It stands in [registry.py](registry.py) as ranges of code points. The check does not ask the interpreter what kind of character it has, because the answer depends on the version of Unicode the interpreter carries. A value is valid or not by the list alone, the same on every supported version of Python.
- **No name between two colons.** A colon, then one or more letters, digits, `_`, `+` or `-`, then a colon is refused, in text and in code. A site that renders the file may replace such a name with a picture after Markdown is done, and no backslash stops that.
- **What that costs.** A value is written in Latin script: no other script, no symbol that is not on the list, and an accented letter only in its one-character form. A time with seconds, or anything else with a word between two colons, is written another way. A link in a value is shown as its text.
- **Keys, statuses and versions are not free text.** Each has its own exact form and is written as it stands.
- **One policy for line endings.** CRLF is read as LF, by every check and by the generator. Generated files are written with LF. A carriage return alone counts as a difference.
- **A file that failed once fails forever.** Every way that has been found to hide something from a check is a copy under [fixtures/](fixtures/) that must fail, with a test that names the message.

## The characters a value may hold

741 characters, and no other:

- **Latin letters.** `A` to `Z` and `a` to `z`. U+00C0 to U+00FF without the two signs U+00D7 and U+00F7. U+0100 to U+024F. U+1E00 to U+1EFF. Left out of those ranges: the compatibility forms U+0132, U+0133, U+013F, U+0140, U+0149, U+017F, U+01C4 to U+01CC, U+01F1 to U+01F3, U+1E9A and U+1E9B, and the click letters U+01C0 to U+01C3, which look like a pipe and an exclamation mark.
- **Digits.** `0` to `9`.
- **The plain space.** U+0020.
- **The ASCII marks.** All 32, from `!` to `~`. Two have a meaning of their own: a pipe is refused because it would break the table, and a backtick marks code.
- **Sixteen marks outside ASCII.** ¡ U+00A1, £ U+00A3, § U+00A7, « U+00AB, ° U+00B0, · U+00B7, » U+00BB, ¿ U+00BF, – U+2013, — U+2014, ‘ U+2018, ’ U+2019, “ U+201C, ” U+201D, „ U+201E and € U+20AC.

What the list is chosen to give, and how far that goes:

- **The order of a line.** No character on the list is written right to left, is a digit of a right-to-left script or is a control for direction. By the Unicode rules for mixing directions, a line made only of such characters is shown in the order it is stored. A test reads the direction class of every character on the list from the interpreter's own tables, on every supported version. It has not been tried in a browser.
- **Compatibility forms, not look-alikes.** No character on the list is a compatibility form: a test compares each with its normal form NFKC, and no two of them join into another, so a value is in the normal forms NFC and NFKC as it stands. That shuts out full-width letters, ligatures, the long s and the like. It is not a protection against characters that look like one another. Some on the list do in some fonts: the capital `I` and the small `l`, the digit `0` and the capital `O`, a dash and a hyphen, a curved quotation mark and a straight one, and letters that differ by a small accent. The division slash, the minus sign and the ratio sign are refused because they are not on the list, not because the check knows what they look like.
- **Adding a character.** A character is added to the list only by a decision, because that loosens the check.

## check_register.py

```sh
python3 checks/check_register.py register.json
python3 checks/check_register.py register.json --write REGISTER.md
python3 checks/check_register.py register.json --markdown REGISTER.md
```

**What it claims.** Every rule that `register.json` adopts is a rule in Ratchet at the version the register states, and its rule, ratchet and source are Ratchet's own, character for character. With `--markdown`, the file given is exactly what the data generates.

**Against which threat.** An agent, or a person, softens an adopted rule in the project's own copy, or adds a rule of its own under Ratchet's name, and nobody notices because the register still looks like Ratchet.

**The data file.**

```json
{"project": "the project's name",
 "ratchet_version": "0.3",
 "adopted": [{"key": "...", "rule": "...", "ratchet": "...", "source": "...",
              "status": "built", "where": "path to the check"}],
 "own": [{"key": "project.key", "rule": "...", "ratchet": "Check: ...", "source": ""}]}
```

`status` and `where` stand on a rule whose ratchet starts with "Check:", and only there. The status is `built` or `text only for now`, and a built check says where it lives.

**The cases in the data.** Each is a `register.json` under [fixtures/register/](fixtures/register/) and a test in [test_checks.py](test_checks.py).

| Fixture | What is wrong | Result |
|---|---|---|
| `clean` | Nothing. Nine adopted rules and one rule of the project's own. | Passes |
| `changed-row` | The rule of an adopted rule has been softened. | Fails |
| `changed-ratchet` | The ratchet of an adopted rule has been replaced. | Fails |
| `changed-source` | The source of an adopted rule has been removed. | Fails |
| `trailing-space` | A rule has one space added at the end. | Fails |
| `unknown-key` | A rule under Ratchet's prefix that Ratchet does not have. | Fails |
| `duplicate-row` | A rule is adopted twice. | Fails |
| `no-rows` | The register adopts nothing. | Fails |
| `wrong-version` | The register states another version than the check runs at. | Fails |
| `patch-version`, `version-alpha`, `version-suffix`, `version-dot-space` | The version starts like the right one and goes on. | Fails |
| `version-number` | The version is a number, not text. | Fails |
| `two-versions` | The version is stated twice. | Fails |
| `duplicate-field` | One rule has its text twice, and the softened one would win. | Fails |
| `status-missing` | An adopted rule names a check and has no status. | Fails |
| `status-invalid` | A status is something other than the two allowed. | Fails |
| `built-nowhere` | A check is marked built without saying where it lives. | Fails |
| `status-on-text-only` | A rule that is text only in Ratchet is marked built. | Fails |
| `unknown-field`, `unknown-top-field` | A field the check does not know, such as a waiver. | Fails |
| `wrong-type` | A rule is a list of texts, not a text. | Fails |
| `prefix-outside` | One of the project's own rules uses Ratchet's prefix. | Fails |
| `own-ratchet-missing` | An own rule whose ratchet says neither "Check:" nor "Text only". | Fails |
| `own-text-only-no-reason`, `own-check-names-nothing` | An own rule that is text only without its reason, or names a check without saying which. | Fails |
| `own-no-words`, `project-no-name` | A rule or a name that holds no words. | Fails |
| `own-pipe` | An own rule that would break the generated table. | Fails |
| `own-odd-backticks`, `own-double-backticks`, `own-code-padded` | Backticks that do not mark one plain piece of code: one without its pair, two in a row, or code with spaces at its ends. | Fails |
| `link-code-confusion`, `link-code-hidden-element`, `project-link-code`, `where-link-code`, `own-ratchet-link-code`, `own-source-link-code` | The value that got past the earlier escaping: a link address that ends in a backtick, then a comment or a hidden element. It is refused here for the spaces in its code, and it would be written as text and code if it were not: see `escaped`. | Fails |
| `own-zero-width`, `own-control-character`, `own-tab`, `own-no-break-space`, `own-line-separator`, `own-paragraph-separator`, `where-hidden`, `own-source-zero-width`, `project-surrogate` | A character that is not on the list: one that shows as nothing, a control, another kind of space or half of a pair. | Fails |
| `own-combining-joiner`, `own-variation-selector`, `own-combining-accent` | A combining mark, which has no shape of its own. | Fails |
| `own-hangul-filler`, `own-braille-blank` | A letter or a symbol by its class that shows as nothing. | Fails |
| `own-full-width`, `own-long-s` | A character in a compatibility form. | Fails |
| `own-rtl-punctuation`, `own-rtl-symbol`, `own-rtl-question-mark`, `own-rtl-letter`, `own-arabic-digit` | A character that is written right to left, or a digit of such a script. Between two numbers, such a punctuation mark can change the order the numbers are shown in, with no control character. | Fails |
| `own-bidi-override`, `own-bidi-isolate`, `own-bidi-mark` | A control that changes the order a line is shown in. | Fails |
| `own-replacement-character`, `own-object-replacement` | A replacement character. The first is what a lenient reader makes of bytes that are not UTF-8. | Fails |
| `own-later-letter` | A letter that only a newer version of Unicode knows. It fails the same on every supported version of Python. | Fails |
| `own-greek-letter`, `own-cyrillic-letter`, `own-han-letter`, `own-click-letter` | A letter from another script, two of them looking like a Latin letter, and a Latin letter that is left out because it looks like a pipe. | Fails |
| `own-division-slash`, `own-minus-sign`, `own-symbol-not-listed`, `own-musical-null`, `own-emoji-character` | A symbol that is not on the list. Two look like an ASCII mark, and one may show as nothing. | Fails |
| `own-emoji-name`, `own-emoji-name-plus`, `own-emoji-name-in-code`, `project-emoji-name`, `where-emoji-name` | A name between two colons: in text, in code, in the project's name and in the place of a check. | Fails |
| `own-time-with-seconds` | A time with seconds. It has digits between two colons, and is the cost of the rule above. | Fails |
| `own-mail-address` | A mail address in text, which becomes a link whatever is escaped. | Fails |
| `version-other-digits` | The version is written with the digits of another script. | Fails |
| `nested-too-deep` | A file nested so deeply that it cannot be read. | Fails |
| `not-an-object`, `not-json` | The file is not a register at all. | Fails |
| `not-utf8` | The file holds a byte that is not UTF-8. | Fails |

In a fixture that fails, every character outside ASCII stands as its JSON escape, such as `\u05be`, so that the file shows which character it holds and none of them hides or reorders a line of the fixture itself.

**The cases in the generated file.** Each has a clean `register.json` and a `REGISTER.md` that is not what it generates. These are the ways that were found to hide a row when the check still read Markdown. All fail for the same reason now.

| Fixture | What was done to `REGISTER.md` | Result |
|---|---|---|
| `md-changed-row` | A row was softened. | Fails |
| `md-indented-row`, `md-indent-three`, `md-indent-tab` | A softened row was indented. | Fails |
| `md-indented-duplicate` | A second, indented copy of a row was added. | Fails |
| `md-no-leading-pipe`, `md-no-outer-pipes` | A softened row lost its outer pipes. | Fails |
| `md-single-cell-row` | A line without a pipe was added under the table, which is still a row. | Fails |
| `md-comment-hides-row` | A row was put inside a comment. | Fails |
| `md-comment-fake-heading`, `md-fake-heading-last` | A heading inside a comment, then a changed row with its key as a link. | Fails |
| `md-escaped-pipe` | A pipe was escaped so that the cells moved. | Fails |
| `md-extra-text` | A sentence was added at the end. | Fails |
| `md-missing` | There is no `REGISTER.md`. | Fails |

One more has a clean `register.json` and fails for a reason of its own: in `md-not-utf8`, one byte of `REGISTER.md` is not UTF-8. The check does not read that byte as some other character and compare. It fails because the file cannot be read.

Three more copies pass:

- `escaped` has own rules, a project name, a ratchet, a source and a place for a check that hold HTML, comments, entities, links, images, emphasis, every punctuation mark, and code. Its `REGISTER.md` shows every one of them as text or as code.
- `latin` has a project name and own rules with Latin letters outside ASCII and each of the sixteen marks outside ASCII. Its data file holds them as themselves, in UTF-8, and its `REGISTER.md` shows them as they stand.
- `references` has own rules that name a person with `@`, an issue with `#` and a commit by its id. The check accepts them, and this fixture is there to say so: see what the check does not claim.

The registers above are generated from `ratchet.json`. [fixtures/handwritten/](fixtures/handwritten/) holds a small set of rules, a register and the `REGISTER.md` it must generate, all typed by hand, and a copy with a changed rule, so that the generator and the check do not only agree with each other.

**What it does not claim.**

- It does not see whether a check marked "built" exists or works.
- That a value is shown as it stands has been tried with one Markdown library, the one with the table, strikethrough and autolink extensions that GitHub publishes. What a site adds on top, after Markdown is done, has not been tried.
- One such addition is shut out by the form of the data: a name between two colons is refused, so a value holds no emoji name for a site to replace with a picture.
- The others are not shut out. A value may hold `@name`, `@group/team`, `#123`, `owner/repo#123` and the id of a commit, short or full, and the check accepts them (fixture `references`). They are written with a backslash before each `@`, `#`, `/` and `-`, and Markdown shows them as text. A site that makes links of people, issues and commits after Markdown is done sees the same text with the backslashes as without, and may still make a link of it. Whether it does depends on the site and on the kind of page.
- It does not claim that two characters on the list cannot be taken for one another: see [The characters a value may hold](#the-characters-a-value-may-hold).
- A project may leave a rule out. A missing rule is a choice, not drift.
- It runs from the version of Ratchet it was fetched at. The project's workflow pins that version by commit, and a change to the workflow is a change to a check (`ratchet.checks-owner-read`).

## generate.py

```sh
python3 checks/generate.py            # write the generated text
python3 checks/generate.py --check    # fail if any generated text is out of date
```

[ratchet.json](../ratchet.json) is the one place a rule is written. From it the generator writes the rule tables, the count of rules, [templates/register.json](../templates/register.json) and the registers under [fixtures/register/](fixtures/register/). From this repo's [register.json](../register.json) it writes `REGISTER.md`. With `--check` it changes nothing and fails when:

- a generated table, count, file or fixture differs from what its data file gives
- a file does not hold exactly the generated blocks it must hold, once each, or a marker is missing or broken
- a file that must hold generated blocks is missing
- a file that holds generated blocks could hide one: it has a comment that is not a marker, a line that starts with `<`, a generated block inside a code block, or a code block opened in any way but three backticks
- a data file breaks its own format, for example a rule labeled `enforced` whose ratchet does not start with "Check:", a rule that is text only without its reason, or a value that holds a character outside the list or a name between two colons
- a file it reads is not valid UTF-8
- a markdown file in the root, in `templates/` or in `checks/` mentions a key that is not a rule
- such a file links to a local file that does not exist, with an inline link or with a link definition at the start of a line. Links to the web and links inside a page are not followed.
- the first entry in the changelog is not the version in `ratchet.json`
- `.github/CODEOWNERS` holds anything but the one rule that gives every path to the maintainer.

## release.py

```sh
python3 checks/release.py notes --repo OWNER/NAME   # print the release text, with no token and no network
python3 checks/release.py publish                   # tag and release, in the release workflow
```

This one checks no rule in a register. It is the script that the release workflow, [release.yml](../.github/workflows/release.yml), runs after the three commands of the job `checks` ([D-2026-11-17-release-on-merge](../decisions/D-2026-11-17-release-on-merge.md), [D-2026-11-17-release-verbatim](../decisions/D-2026-11-17-release-verbatim.md)). The workflow holds no logic of its own, so that the logic can be tested. Its tests, in [test_release.py](test_release.py), run with the others and never reach the network: the GitHub API is a function given to the script, and the HTTP client is given a fake opener.

The script does not try to finish an older version, and it does not rewrite the entry. When anything older is unfinished, the run is red, nothing is written, and the maintainer reruns the run of that version by hand.

**What it claims.**

- **The release text is the entry, verbatim.** It reads the version from `ratchet.json` at the checked-out commit, strictly, and `CHANGELOG.md` as strict UTF-8 with CRLF read as LF. An entry starts only at a line `## MAJOR.MINOR (YYYY-MM-DD)` at the start of a line and outside a code block, and ends at the next. The run fails on anything that a reader could take for such a heading and the script would not: a heading of level one or two in another form or with spaces before it, a heading made with an underline, a code block opened in another way than three backticks at the start of a line, a comment that is not the marker of a generated block, HTML, a link definition, text before the first entry. It also fails on two entries for one version, entries that are not newest first, an empty entry, and a newest entry that is not the version in `ratchet.json`. The release text is the lines of the entry exactly as they stand, without the blank lines before and after them, then a blank line and one fixed line written in the script: `The files of this version: [vMAJOR.MINOR](https://github.com/OWNER/NAME/tree/vMAJOR.MINOR)`. No link, no code and no marker in the entry is changed.
- **An unfinished older version stops the run.** Before any write, it lists the tags and the releases. Each version in the changelog that is older than the one being released must have a tag and a published release, not a draft. 0.1 needs only its tag, because it was tagged before Ratchet published releases (`BEFORE_RELEASES` in the script). If any is missing, the run fails, names each version and what it lacks, and writes nothing. A tag `vMAJOR.MINOR` up to this version with no entry fails, and so does a tag under `refs/tags/v` of another form. Tags and releases of versions newer than the one in `ratchet.json` are ignored, so that a rerun for 0.4 does not trip over a `v0.5`.
- **A release is made only from `main`.** `GITHUB_REF` must be `refs/heads/main`, or the run fails before any request.
- **Nothing is written before every check has passed.** The writes are two, in this order: the tag, then the release.
- **The tag is created at this commit, or not at all.** It is created with `POST /repos/OWNER/NAME/git/refs`, which refuses a ref that exists. Then the release is created for that tag, and the tag is read back. The run fails when the answer to the creation or the tag read back points anywhere but `GITHUB_SHA`.
- **A tag that exists is never moved, deleted or edited** (`repo.tags-stay`). What the run does with the tag of the version being released:

| The tag for the version | The release for it | What the run does |
|---|---|---|
| does not exist | none | creates the tag at `GITHUB_SHA`, then the release, then reads the tag back |
| does not exist | exists, draft or not | fails and writes nothing |
| at `GITHUB_SHA` | none | a rerun of this version's run: creates only the release, then reads the tag back |
| at `GITHUB_SHA` | draft | fails and writes nothing: publish the draft by hand |
| at `GITHUB_SHA` | published | nothing to do |
| at an earlier commit of `GITHUB_SHA` | published | nothing to do: this commit does not raise the version |
| at another commit, or not a plain tag | none, a draft, or a commit that is not earlier | fails and writes nothing |
| any | two or more | fails and writes nothing |

- **The token.** Only `GITHUB_TOKEN` from the environment is used. It is sent in one header, to `https://api.github.com` only, to paths under `/repos/OWNER/NAME/`, and a redirect is not followed. It is never printed. An error names the method, the path and the status. Nothing from the body of an answer is read for an error or printed, except a version that has matched `MAJOR.MINOR`.

**Against which threat.**

- A release that says something other than the entry that was approved: a version heading in a code example that the script takes for the entry, or a link rewritten inside code.
- A version that is merged and left unreleased, or made impossible to release, with no red run that says so: a run that fails or is cancelled after it tags, or a waiting run replaced in the concurrency group by a newer one.
- A release attached to a tag at another commit than the one approved, because the tag appeared between a check and a write.
- A version hard-coded in the script instead of read from `ratchet.json`.
- The token sent somewhere else, or shown in a log.

**Why the rerun of this version finishes its release.** A rerun that finds the tag of the version being released at its own `GITHUB_SHA`, with no release, creates the release. This is the version's own run, not an older one. It is safe: the tag is on the commit that was approved, where it would be anyway, so nothing has to move; the text is the entry in the changelog at that same commit, the one that was approved; every older version has passed the check above; and a release created before an answer was lost is found, so no second one is made. Failing there instead would leave no way through the workflow to finish the version.

**When a run is red because something is unfinished.** The message names each version and what it lacks. Then, in this order:

1. Under Actions, open the workflow `release` and find the run of the commit that raised the version to the one named: the first commit on `main` at which `ratchet.json` names it. If the tag exists, it points at that commit. Choose "Re-run all jobs". It tags that commit if the tag is missing, and creates the release. It ignores the newer versions.
2. When that run is green, rerun the red run, with "Re-run all jobs".
3. If the run of step 1 cannot be rerun (GitHub allows a rerun for 30 days, and a run may never have started), and the head of `main` still has that version in `ratchet.json` and its tag is missing, start the workflow by hand: Actions → `release` → "Run workflow", on `main`. It takes no input, runs the same three checks, and releases what `ratchet.json` names at the head of `main`. On any other branch it fails before any request.
4. If neither is possible, the maintainer makes the tag or the release by hand, on the commit that raised the version, with the text that `python3 checks/release.py notes --repo OWNER/NAME` prints at that commit. The workflow never does this.

**Why the concurrency group stays.** It keeps one release run at a time, so that two runs never write at once. A waiting run can still be replaced by a newer one, and the replaced run shows as cancelled. That cannot lose a version without a red run: the newer run checks every older version in the changelog, and fails and names one without a tag or a published release. The last run in the queue is never replaced. A run that was cancelled can be rerun for its commit, and then the newer one.

**The cases.** Each is a test in [test_release.py](test_release.py).

| Case | Result |
|---|---|
| A heading inside a code block in an entry | Part of that entry |
| A code block before the first entry, holding a heading | Fails |
| A code block opened with `~~~`, four backticks, spaces before it or another word after it | Fails |
| A code block that is never closed | Fails |
| Two entries for one version | Fails |
| A heading that is not `## MAJOR.MINOR (YYYY-MM-DD)`, of eleven kinds | Fails |
| A heading made with an underline | Fails |
| A comment or HTML that could hide a heading | Fails |
| A link definition | Fails |
| Entries that are not newest first, an empty entry, a file that does not start with its title | Fails |
| CRLF | Read as LF, the same text |
| A lone carriage return in a heading | Fails |
| Bytes that are not UTF-8 | Fails |
| An entry with single, double and triple backtick code, a code span over two lines, an odd backtick, links, fenced blocks, markers, tabs and trailing spaces | The release text and the published body are the entry byte for byte, then the fixed line |
| The 0.3 entry of today's `CHANGELOG.md` | The entry as it stands, then the fixed line. The published `v0.3`, kept under [fixtures/release/](fixtures/release/) as GitHub gave it, was made with the old rewriting: undo its links to the tag and put back the two marker lines, and it is the same |
| A new version | The tag, then the release, then the tag read back |
| An older version without a tag, with a tag and no release, with only a draft, also when nothing is to be released | Fails, names it and what it lacks, writes nothing |
| 0.1 with its tag and no release, 0.1 with no tag | Passes; fails |
| A newer tag, a newer annotated tag, a newer draft | Ignored |
| A tag up to this version without an entry, a tag that is not a version | Fails, writes nothing |
| 0.4 fails after its tag, then 0.5 is merged | The run for 0.5 fails, names 0.4 and writes nothing. The rerun for 0.4 creates only its release. The rerun for 0.5 then releases 0.5 |
| A rerun for 0.4 when `v0.5` exists | Creates the release for 0.4 |
| A run cancelled right after its tag | A later run on 0.4 and the run for 0.5 fail and write nothing. The rerun of the cancelled run finishes it |
| Each row of the table above | As the table says |
| A refused ref creation | Fails, writes nothing more |
| An answer to the creation that puts the tag elsewhere | Fails, creates no release |
| A tag read back at another commit | Fails |
| An API error at each of the four requests | Fails with method, path and status, writes nothing more |
| An answer of the wrong form | Fails, writes nothing |
| The version is not the newest entry, or has none | Fails before any request |
| `ratchet.json` in another checkout names 9.7 | `publish` tags `v9.7` with that entry, and `notes` prints it |
| The token in five runs, with an answer that holds it | Never in the output, and sent only to `api.github.com` |
| No token, a repository, a commit or a branch not of its form | Fails before any request |
| A path outside the repository, a redirect | Not sent, not followed |
| `notes` | Needs no token and no network |
| `.github/workflows/release.yml` | Runs on a push to `main` and on `workflow_dispatch` with no input, with read-only permissions but on its job, the checkout pinned by commit, no expression in a script, and the three commands before the script |

**What it does not claim.**

- It does not see branch protection or tag protection. Who may push a tag by hand is a setting of the repository.
- It does not read the release text back after it is published.
- A relative link in an entry, such as a link to the file `RATCHET.md`, is published as it stands, and on the release page GitHub does not resolve it to the file. The fixed line links to the files at the tag. This is the cost of the verbatim text.
- The markers of generated blocks are published as they stand. They are HTML comments, which GitHub does not show.
- A version may be skipped on purpose, from 0.4 to 0.6, by leaving out an entry for 0.5. That is a choice made in a pull request, not a version lost.
- A workflow file on another branch can be changed by anyone who can push to it. The check of `GITHUB_REF` stops a mistake, not a change to the workflow or the script.

## Why JSON

The rules are data that the checks and a project's CI must read. The format was chosen so that the checks need nothing but a Python interpreter:

- Python's standard library reads JSON in every supported version. It reads TOML only from 3.11, and it does not read YAML at all.
- The Python that ships with a common developer operating system is older than 3.11. A check that needs a newer interpreter, or a package, is a check that does not get run.

The cost is that JSON has no comments and escapes quotation marks. The rules are one sentence per field, so it stays readable, and anything that needs explaining belongs in the changelog or in a decision.
