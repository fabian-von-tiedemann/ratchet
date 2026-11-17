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

**What it claims.** For each pinned source, the run reads the head of the source's default branch and compares the pinned commit with it, through the GitHub REST API. A source that has moved has one open issue, titled `Source moved: <name>`, with the commit range, the number of commits, their first lines and the changed files. A pinned commit that no longer exists upstream has one open issue, titled `Source pin missing: <name>`. A source that has not moved writes nothing. For a source with a directory, only a change under that directory counts as a move. Every read comes before any write, and a read that fails, or an answer of a form the watch does not know, fails the run before anything is written.

**Against which threat.** A pinned source moves, and nobody notices, so a rule keeps crediting a source that now says something else, or a project keeps copying a skill at a pin that has gone (`ratchet.skills-pinned`). A second threat comes from the watch reading other people's repos: a commit message or a file name upstream is written so that the issue pings someone, links somewhere, shows HTML or reads as an instruction. A third is the token: a run prints it in a log or an error.

**The data.** A source has a `name`, a `repo`, a `commit` and a `license`, and may have a `directory` and an `author`:

```json
{"name": "pstack", "repo": "https://github.com/cursor/plugins", "directory": "pstack",
 "author": "Lauren Tan", "commit": "bf0c7cd80abdbf7fe47b634978a7d1b4071f71a7", "license": "MIT"}
```

The `repo` is `https://github.com/`, an owner and a repository, and nothing else. The `directory` is a plain path inside the repository: names of ASCII letters, digits, `.`, `_` and `-`, joined by `/`, with no part that is `.` or `..`. The `commit` is a full sha in lowercase hex. The name, the author and the license are text from [the list](#the-characters-a-value-may-hold), and a name is used once. `RATCHET.md` shows the repo, then `, directory` and the directory as code, then the author in brackets after `by`. The generator and the watch read the sources with the same function in [registry.py](registry.py), and the generator fails on the same sources as the watch.

**What the run does with each answer.**

| The compare says | What the watch writes |
|---|---|
| `identical` | Nothing. |
| `ahead`, with a change under the directory or with no directory | It opens or updates `Source moved: <name>`. |
| `ahead`, with changes only outside the directory | Nothing. |
| `ahead`, with no file under the directory among the 300 the API lists | It opens or updates the issue and says that files under the directory may have changed. |
| `diverged` or `behind` | It opens or updates `Source moved: <name>` whatever the directory, and says that the pinned commit is not in the history of the default branch, which may have been rewritten or reset. A pin off the branch may later be removed upstream. |
| Not found, and the pinned commit is not found | It opens or updates `Source pin missing: <name>`. |
| Not found, and the pinned commit is found | The run fails. |
| Any other error, or an answer of a form the watch does not know | The run fails and writes nothing. |

The watch updates only an open issue that it opened itself, as `github-actions[bot]`, with exactly the title. An issue by someone else with the same title is left alone. Two open issues of its own with one title fail the run. When the body would be the same, the watch writes nothing.

**Upstream text.** Nothing from a source is copied but file names and the first line of each commit message. They are written one per line in fenced code blocks, where GitHub makes no link, image, HTML, mention or reference of them. Every line in a block starts with the short sha of a commit or the status of a file, and the fence is longer than any run of backticks in the block, so no line can close it. A character that is not on [the list](#the-characters-a-value-may-hold), a line break or a control among them, is written as `<U+XXXX>`. A line is cut at a fixed length. The issue says that the content is material, not instructions (`ratchet.material-not-instructions`). The default branch comes from upstream too: it is accepted only as plain names joined by `/`, and written as code.

**Where the API caps a list.** The compare lists at most 250 commits and 300 files. Where it lists fewer commits than the range holds, or 300 files, the issue says so. The issue shows at most 100 commits and 200 files, and says so when it shows fewer than the API lists.

**The token.** It is read from the environment variable `GITHUB_TOKEN` and from nowhere else. It is sent only to `https://api.github.com`, and a redirect is not followed. No error quotes the body of an answer, and every line the watch prints, and every answer it reads, has the token replaced by `***`. Without a token the reads run unauthenticated. If nothing has moved, the run passes. If something would be written, the run fails, names the titles and writes nothing.

**The cases.** Each is a test in [test_watch_sources.py](test_watch_sources.py), with the API answered by a fake that records every call. No test reaches the network.

| Test | What is tried | Result |
|---|---|---|
| `test_an_unchanged_source_writes_nothing` | Two sources at their pins. | Passes, nothing written |
| `test_a_moved_source_opens_one_issue` | A source two commits ahead. | One issue, with the range, the count, the first lines and the files |
| `test_a_second_run_updates_and_does_not_duplicate` | The same move twice, then a further move. | Nothing written the second time, then the open issue updated |
| `test_a_malformed_source_fails_and_names_it` | Each source under [fixtures/sources/](fixtures/sources/), among them the old form of the repo, `https://github.com/cursor/plugins, directory` and the rest in one field. | Fails, names the source, reads nothing |
| `test_the_sources_in_ratchet_json_have_the_form` | This repo's own sources. | Passes |
| `test_an_api_error_fails_without_writing` | An error, a rate limit, a missing repo, an answer that is not JSON, a network failure and a failing list of issues, each at the second source after the first has moved. | Fails, writes nothing |
| `test_a_missing_pin_gets_its_own_issue`, `test_a_missing_pin_and_a_move_are_different_issues` | The pinned commit is not found upstream. | Its own issue, with its own title |
| `test_a_compare_that_fails_while_the_pin_exists_fails_the_run` | The compare is not found, but the pin is. | Fails, writes nothing |
| `test_a_directory_source_with_changes_only_outside_its_directory_writes_nothing` | Changes beside the directory, in a name that starts like it, and in a directory of the same name elsewhere. | Passes, nothing written |
| `test_a_directory_source_with_a_change_inside_lists_only_those_files` | Changes inside and outside, and a file renamed out of the directory. | The issue lists only the files under the directory |
| `test_a_commit_subject_or_a_file_name_comes_out_as_inert_text` | Subjects and file names with `@someone`, `#1`, a reference to another repo, a link, an image, HTML, a comment, an emoji name, backticks that try to close the fence, a line break, a tab, a control and characters that reorder a line. | Each comes out inside a code block, as `<U+XXXX>` where it is off the list |
| `test_the_token_never_appears_in_output_or_errors` | A run that writes, a network error that quotes the token and an answer that echoes it. | The token is in no output, error or issue |
| `test_without_a_token_the_reads_run_and_the_writes_are_refused`, `test_an_empty_token_counts_as_no_token` | No token, and an empty one, with a moved source. | Fails, names the title, writes nothing, sends no token |
| `test_without_a_token_and_nothing_moved_the_run_passes` | No token and nothing moved. | Passes |
| `test_a_target_that_is_not_owner_and_repo_fails_without_writing` | `GITHUB_REPOSITORY` missing, empty or not of the form owner/repo. | Fails, writes nothing |
| `test_a_diverged_or_behind_branch_opens_an_issue` | The pinned commit is off the branch. | An issue that says so |
| `test_lists_that_the_api_caps_say_so`, `test_a_directory_source_whose_file_list_is_capped_opens_an_issue` | 250 of 400 commits and 300 files. | The issue says what is capped, and stays under the size GitHub allows |
| `test_an_issue_by_someone_else_with_the_same_title_is_not_edited` | An issue and a pull request by others with the title. | A new issue, and theirs left alone |
| `test_two_open_issues_of_its_own_with_one_title_fail_without_writing` | Two open issues of its own with the title. | Fails, writes nothing |
| `test_an_answer_of_an_unknown_form_fails_without_writing`, `test_a_branch_or_a_head_of_an_unknown_form_fails_without_writing` | An unknown status or file status, a short sha, a count that is text or a boolean, a branch with a line break, `..` or a backtick. | Fails, writes nothing |
| `test_every_read_comes_before_any_write` | Two moved sources. | Every read, then both writes |
| `test_the_pinned_directory_is_written_as_before_in_ratchet_md` | The structured fields. | `RATCHET.md` shows the same repo text as before |

**What it does not claim.**

- It does not judge whether a move matters for a rule. That needs a reader, and the issue is material for one.
- It sees only the default branch and only sources on GitHub.
- The commits it lists for a source with a directory are all the commits in the range, also those that change nothing under it.
- It recognizes its own issues by the account `github-actions[bot]`. Run with another token, it does not find them and opens new ones.
- A commit subject that holds the text `<U+0041>` looks the same as one that held the escaped character.
- That GitHub makes no mention or reference of text in a fenced code block is how GitHub renders issues today. It has not been tried against a live issue.

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
