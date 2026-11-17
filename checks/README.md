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

## watch_sources.py

```sh
python3 checks/watch_sources.py
python3 checks/watch_sources.py --data ratchet.json
```

This is not a reference check for a rule. It is a tool this repo runs on its own sources, the list `sources` in [ratchet.json](../ratchet.json) that `RATCHET.md` shows under Sources. Its tests run in this repo's CI with the others. The script itself is meant to run once a day in a workflow of its own, with the workflow's built-in token.

**What it claims.** For each pinned source, the run reads the head of the source's default branch and compares the pinned commit with it, through the GitHub REST API.

- A source without a directory has moved when the compare is not `identical`.
- A source with a directory has moved when at least one changed file is under the directory, or when the compare is `behind` or `diverged`. If the API does not say which files changed, or lists 300 files and none of them under the directory, the watch cannot tell, and counts the source as moved.
- A source that has moved has one open issue, titled `Source moved: <name>`. A pinned commit that is not found upstream has one open issue, titled `Source pin missing: <name>`. A source that has not moved writes nothing.
- Every read comes before any write. Then every title and body is built and passes one gate, and only then is anything written. A read that fails, an answer of a form the watch does not know, or a title or body that fails the gate, fails the run before anything is written.

**Against which threat.**

1. A pinned source moves, and nobody notices, so a rule keeps crediting a source that now says something else, or a project keeps copying a skill at a pin that has gone (`ratchet.skills-pinned`).
2. Text from a source, from an answer of the API or from `ratchet.json` is written so that the issue pings someone, links somewhere, shows HTML or reads as an instruction (`ratchet.material-not-instructions`), or so that a line in the log is read by the runner as a command, such as `::warning::` or `##[error]`.
3. The token is printed in a log or an error, written into an issue, or sent to another host.

**No text from a source (`D-2026-11-17-new-approaches`, in PR #13).** Two review rounds found text from upstream that escaping did not make inert, and a token that got through an encoding the watch did not undo. So the watch no longer tries to make such text safe. No text from a source, and no text from an answer of the API, reaches an issue, a title or a printed line. An issue holds only these values:

| Value | From | Checked as |
|---|---|---|
| Name | `ratchet.json` | The narrow form below |
| Directory | `ratchet.json` | The narrow form below |
| Pinned commit | `ratchet.json` | 40 lowercase hex characters |
| Head of the default branch | The API | 40 lowercase hex characters |
| Status | The API | One of `identical`, `ahead`, `behind`, `diverged` |
| Commits ahead and behind | The API | Integers from 0 to 999999999 |
| Changed files, and those under the directory | Counted by the watch from the API's list | Integers, or "not listed by the API" |
| Compare link | Owner and repo from `ratchet.json`, and the two shas | `https://github.com/<owner>/<repo>/compare/<pin>...<head>` |
| Everything else | Fixed English text in the script | Each line exactly |

No commit subject, file name, branch name, author or message is written. The issue tells the reader to follow the compare link to see the commits and the files, and that what they find there is material, not instructions. File names are read only to count those under the directory. The default branch is read only to build the path of the next request.

**The data.** A source has a `name`, a `repo`, a `commit` and a `license`, and may have a `directory` and an `author`:

```json
{"name": "pstack", "repo": "https://github.com/cursor/plugins", "directory": "pstack",
 "author": "Lauren Tan", "commit": "bf0c7cd80abdbf7fe47b634978a7d1b4071f71a7", "license": "MIT"}
```

- **The name** is lowercase letters, digits, `.`, `-` and `/`, starts with a letter or a digit, and is at most 100 characters long. It has no `_`, since the gate allows no `_` outside a link: in Markdown an `_` can start emphasis. 100 characters keep `Source pin missing: ` and the name at 120 characters, well within the 256 that GitHub takes for a title, so a title is never cut. A name that would be longer is refused. A name is used once, so two sources never share a title.
- **The directory** is parts of lowercase letters, digits, `.` and `-`, joined by single `/`, at most 100 characters. No part is `.`, no `..` stands anywhere in it, and it does not start or end with `/`.
- **Neither holds `www.` or `GH-` and a digit**, in any case. GitHub makes a link of the one and a reference to an issue of the other, from characters the form allows.
- **The repo** is `https://github.com/`, an owner and a repository, and nothing else. The owner is letters, digits and `-`, starts with a letter or a digit and is at most 39 characters. The repository is letters, digits, `.`, `_` and `-`, at most 100 characters, not `.` or `..` and not ending in `.git`.
- **The commit** is a full sha in lowercase hex. The author and the license are text from [the list](#the-characters-a-value-may-hold).

`RATCHET.md` shows the repo, then `, directory` and the directory as code, then the author in brackets after `by`. The generator and the watch read the sources with the same function in [registry.py](registry.py), and the generator fails on the same sources as the watch.

**One gate.** Every planned title and body, and every printed line, passes the same check before it leaves the watch:

- **A grammar of lines.** A title is `Source moved: ` or `Source pin missing: ` and a name of the narrow form. Each line of a body is a blank line, one of the fixed sentences, or one of the lines in the table above, each matched in full by a pattern of its own.
- **A small set of characters.** Outside a link or a path of the API, a line holds only ASCII letters, digits, the space and `.` `,` `:` `'` `(` `)` `/` `-`. So it holds no `@`, `#`, `<`, `>`, `[`, `]`, `!`, backtick, `|`, `\`, `*`, `_`, line break, control, or any character outside ASCII. Inside a link to `https://github.com/` or a path that starts with `/repos/`, it may also hold `_`, as a repository name may. It never holds `::`, and outside a link never `www.` or `GH-` and a digit.
- **The token.** No title, body or printed line holds the token as it stands.

If one planned title or body fails, nothing is written. The error names the planned issue and the line, never the text. A printed line that fails is replaced by `a line that did not pass the output gate is left out`. Errors give only the method, a path built from checked values, and the HTTP status as an integer, never anything from the body or the headers of an answer, and never the text of a network error. An error the watch does not know is printed as its kind and the line of the script.

**Why the token needs nothing more.** The earlier version replaced the token in every answer and looked for it behind escapes and encodings, because upstream text went into issues and logs. Now no text from an answer is written anywhere, so a token that an answer holds, in any encoding, has no way out. The only values that are written are checked for a form that a token of GitHub's does not have, and the gate refuses the token as it stands in case one ever did.

**The size of a body.** No list from the API reaches a body, so its size does not depend on the source. The largest body has a name and a directory of 100 characters, an owner of 39 and a repository of 100, nine-digit counts, 300 changed files, all under the directory, and the notes on a `diverged` compare and on a capped list. It is 1390 bytes, and a test builds it. GitHub takes 65536 characters.

**The token and the transport.** The token is read from the environment variable `GITHUB_TOKEN` and from nowhere else. It is sent only to `https://api.github.com`: the transport refuses any other address before it connects. A redirect is not followed. It is an answer of its own, and the run fails on it, so the token is never sent on. Without a token the reads run unauthenticated. If nothing has moved, the run passes. If something would be written, the run fails, names the titles and writes nothing.

**What the run does with each answer.**

| The compare says | What the watch writes |
|---|---|
| `identical`, and the head is the pin | Nothing. |
| `ahead`, for a source with no directory | It opens or updates `Source moved: <name>`, also when no file differs, as after an empty commit. |
| `ahead`, with a change under the directory | It opens or updates `Source moved: <name>`. |
| `ahead`, with changes only outside the directory, or with no changed file | Nothing. The run prints that the source has not moved under its directory. |
| `ahead`, with 300 files listed and none under the directory, or with no list of files | It opens or updates the issue and says that it cannot tell whether a file under the directory changed. |
| `diverged` or `behind` | It opens or updates `Source moved: <name>` whatever the directory, and says that the pinned commit is not in the history of the default branch. |
| `identical` while the head is not the pin, or anything else while the head is the pin | The run fails and writes nothing. |
| Not found, and the pinned commit is not found | It opens or updates `Source pin missing: <name>`. |
| Not found, and the pinned commit is found | The run fails. |
| Any other error, a redirect, or an answer of a form the watch does not know | The run fails and writes nothing. |

The watch updates only an open issue that it opened itself, as `github-actions[bot]`, with exactly the title. An issue by someone else with the same title is left alone. Two open issues of its own with one title fail the run. When the body would be the same, the watch writes nothing.

**The cases.** Each is a test in [test_watch_sources.py](test_watch_sources.py). The API is answered by a fake that records every call, except in the class `Transport`, which runs the real transport against local servers on `127.0.0.1`. No test reaches the internet.

| Test | What is tried | Result |
|---|---|---|
| `test_fixture_*`, one for each file under [fixtures/sources/](fixtures/sources/) | 49 malformed sources: names with `##[`, `::`, `@`, `#`, `<`, a backtick, a space, a capital, `_`, a leading `.` or `-`, 101 characters, `www.` or `gh-12`; directories with `//`, `..`, a part `.`, a capital, `_`, 101 characters or `www.`; an owner with `_`; and the forms of round 1. | Fails, names the problem, or prints that a line was left out where the problem quotes `_` or `\|`; reads nothing |
| `test_the_sources_in_ratchet_json_have_the_form` | This repo's own sources. | Passes |
| `test_an_unchanged_source_writes_nothing` | Two sources at their pins. | Nothing written |
| `test_a_moved_source_opens_one_issue` | A source two commits ahead. | One issue, with exactly the expected body |
| `test_a_second_run_updates_and_does_not_duplicate` | The same move twice, then a further move. | Nothing written the second time, then the open issue updated |
| `test_an_api_error_fails_without_writing` | An error, a rate limit, a missing repo, an answer that is not JSON, a network failure and a failing list of issues, at the second source after the first has moved. | Fails with exactly the method, the path and the status; writes nothing |
| `test_a_missing_pin_gets_its_own_issue`, `test_a_missing_pin_and_a_move_are_different_issues` | The pinned commit is not found upstream. | Its own issue, with exactly the expected body |
| `test_a_compare_that_fails_while_the_pin_exists_fails_the_run` | The compare is not found, but the pin is. | Fails, writes nothing |
| `test_a_directory_source_with_changes_only_outside_its_directory_writes_nothing` | Changes beside the directory, in a name that starts like it, and in a directory of the same name elsewhere. | Nothing written |
| `test_a_directory_source_with_a_change_inside_opens_an_issue` | Changes inside and outside, and a file renamed out of the directory. | Exactly the expected body: 4 changed files, 2 under the directory |
| `test_a_directory_source_whose_branch_moved_without_a_changed_file_writes_nothing` | An empty commit, for a source with a directory. | Nothing written |
| `test_a_diverged_or_behind_branch_opens_an_issue_also_with_nothing_under_the_directory` | The pinned commit is off the branch. | An issue that says so |
| `test_a_capped_file_list_says_so`, `test_a_directory_source_whose_capped_file_list_has_nothing_under_it_counts_as_moved`, `test_a_directory_source_whose_compare_lists_no_files_counts_as_moved` | 300 files, and no list of files. | An issue that says what the watch cannot tell |
| `test_without_a_token_the_reads_run_and_the_writes_are_refused`, `test_an_empty_token_counts_as_no_token`, `test_without_a_token_and_nothing_moved_the_run_passes` | No token, or an empty one. | Fails and names the titles if anything moved, passes if not; sends no token |
| `test_a_target_that_is_not_owner_and_repo_fails_without_writing` | `GITHUB_REPOSITORY` missing, empty or not of the form owner/repo. | Fails, writes nothing |
| `test_an_issue_by_someone_else_with_the_same_title_is_not_edited`, `test_two_open_issues_of_its_own_with_one_title_fail_without_writing` | Issues by others, and two of its own, with the title. | Theirs left alone; two of its own fail the run |
| `test_an_answer_of_an_unknown_form_fails_without_writing`, `test_a_branch_or_a_head_of_an_unknown_form_fails_without_writing` | An unknown status, counts that are text, a boolean, below zero or above the cap, files that are not a list, names that are not text, a branch with a line break, `..` or a backtick, a short or uppercase head. | Fails with a fixed message, writes nothing |
| `test_every_read_comes_before_any_write` | Two moved sources. | Every read, then both writes |
| `test_the_pinned_directory_is_written_as_before_in_ratchet_md` | The structured fields. | `RATCHET.md` shows the same repo text as before |
| `test_a_compare_that_disagrees_with_the_head_fails_without_writing` | `identical` with a head that is not the pin, and `ahead` with a head that is. | Fails, writes nothing |
| `test_an_ahead_compare_with_no_changed_file_is_a_move` | Round 1, finding 1: a source with no directory, one empty commit ahead. | An issue |
| `test_the_largest_body_is_small_and_holds_nothing_from_the_answer` | Round 1, finding 2: every value at its cap, with 250 commits and 300 files whose names hold mentions, runner commands, HTML and backticks. | 1390 bytes at most, none of that text in it |
| `test_the_gate_refuses_every_mark_outside_its_set`, `test_the_gate_refuses_a_line_of_a_kind_the_watch_does_not_write` | Round 1, finding 3: each refused mark in a title, a body and a printed line, and lines and titles of kinds the watch does not write. | Refused, nothing written |
| `test_a_plan_that_fails_the_gate_writes_nothing_at_all` | A second body that fails the gate. | Fails, names the issue and the line, writes neither issue |
| `test_no_text_from_an_answer_reaches_an_issue_or_a_line` | Round 1, finding 4, and round 2, finding 2: an answer whose every text field holds mentions, runner commands, a link, HTML, and the token as it stands, as `\u` escapes, percent-encoded twice and as HTML entities. | The body is byte for byte the body of a clean answer; the output holds none of it |
| `test_no_text_from_an_error_answer_or_a_network_error_reaches_a_line`, `test_an_error_the_watch_does_not_know_prints_only_its_kind_and_line` | The same text in an error answer, a network error and an unknown error. | Exactly the method, the path and the status, or the kind of error and the line |
| `test_the_gate_refuses_the_token_as_it_stands`, `test_the_token_is_sent_with_every_call_and_never_printed` | A token that would pass the form of a name. | Refused in a title, a body and a printed line |
| `test_values_read_from_the_api_are_used_and_not_assumed` | Round 1, finding 5: a default branch `trunk/next`, and a head, an owner, a repo, a target, issue numbers and counts that no other test uses. | Each value read is the value used |
| `test_a_printed_line_that_fails_the_gate_is_left_out` | Round 2, finding 1: printed lines with `##[error]`, `::error::`, `@`, the token, a carriage return and `_`. | Each replaced by the fixed line |
| `test_names_that_share_a_long_start_get_their_own_titles` | Round 2, finding 3: two names of 100 characters that differ in the last. | Two issues, each titled with the whole name |
| `test_a_redirect_is_not_followed_and_the_token_goes_nowhere_else` | Round 2, finding 4: the real transport, against a local server that answers 301, 302, 303, 307 or 308 with an address on a second local server. | Fails with the status; the token reached the first server only, and the second got nothing |
| `test_the_redirect_handler_makes_no_new_request`, `test_the_transport_sends_nothing_to_another_address`, `test_the_real_transport_reads_an_answer` | The redirect handler alone, a local address that is not the API, and a plain run through the real transport. | No new request; refused before connecting; read as through the fake |

**What it does not claim.**

- It does not judge whether a move matters for a rule. That needs a reader, and the compare is material for one.
- It sees only the default branch and only sources on GitHub.
- It recognizes its own issues by the account `github-actions[bot]`. Run with another token, it does not find them and opens new ones.
- A run writes all of its issues or none, unless GitHub fails a write after an earlier one went through. Then the issues before it are written and those after it are not, and the next run writes them.
- GitHub may show a sha in an issue as a link to a commit of this repository, if this repository has one with that sha. That is a link to this repo, not a mention.
- That GitHub makes no mention, reference or link of a line in the gate's set, other than `www.` and `GH-` and a digit, is how GitHub documents its autolinks today. It has not been tried against a live issue. A repository with custom autolinks of its own may link more.
- A name or a directory of a source upstream that has a capital or an `_` cannot be watched as it stands. The name is ours to choose; the directory is not.
- The limit of 65536 is the one GitHub's answer to a body that is too long states. It is not in the REST reference.

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

## Why JSON

The rules are data that the checks and a project's CI must read. The format was chosen so that the checks need nothing but a Python interpreter:

- Python's standard library reads JSON in every supported version. It reads TOML only from 3.11, and it does not read YAML at all.
- The Python that ships with a common developer operating system is older than 3.11. A check that needs a newer interpreter, or a package, is a check that does not get run.

The cost is that JSON has no comments and escapes quotation marks. The rules are one sentence per field, so it stays readable, and anything that needs explaining belongs in the changelog or in a decision.
