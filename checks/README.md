# Reference checks

Checks that Ratchet ships. Each one runs in this repo's CI ([checks.yml](../.github/workflows/checks.yml)) and has a fixture it fails on. They use Python's standard library only, so a project needs nothing installed to use them. They have been run on Python 3.9 and 3.12.

<!-- generated:reference-checks -->
| Rule | Reference check |
|---|---|
| ratchet.register-on-top | [checks/check_register.py](check_register.py) |
| ratchet.expected-tests-ran | [checks/expected_tests.py](expected_tests.py) |
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

## expected_tests.py

```sh
python3 -m unittest discover -s checks -v
```

The reference check for `ratchet.expected-tests-ran`. It is not a script of its own: it runs inside the suite. A test that loads fixtures is a `FixtureTest`, and loads each one by its name under [fixtures/](fixtures/), with `fixture_bytes`, `fixture_text`, `fixture_file` or `fixture_directory`. The last two give a copy in a scratch directory, made from the bytes that were loaded, and the check under test is run on the copy.

**What it claims.** In every run of the suite, every file under `checks/fixtures/` was loaded by a test that ran and passed in that same run. Otherwise the run fails, with each fixture named, before unittest prints its summary and sets the exit status.

**Against which threat.** A suite that stays green while it runs fewer tests than it should: a test removed, skipped or broken in its preparation, a module that no longer imports, a fixture added and never tested, or a test that names a fixture that is gone. A green summary says only that the tests that ran passed, not that the tests that were meant to run did.

**How it works.**

- **The expected set is the fixtures themselves.** It is read from the directory, not from a list in a test and not from Markdown. Every file is one fixture. A file whose name starts with a dot, or holds a character other than letters, digits, `_`, `.` and `-`, fails, and so does a link.
- **Every load is recorded.** The record holds the fixture's name, the test and the sha256 of the bytes the test read. It is kept on the run's own result, so a suite run inside a test keeps its own.
- **Every outcome is recorded.** When a test ends, the record says whether it passed, failed, errored, could not be prepared (an error before its body started, as in `setUp`), was skipped, or was an expected failure or an unexpected success. That holds for the body, a subtest, `tearDown` and a cleanup. A load counts only for a test that passed.
- **A class or a module that did not pass.** unittest records a `setUpClass`, `tearDownClass`, `setUpModule` or `tearDownModule` that errored or skipped under its own name, such as `tearDownClass (test_checks.RegisterCheck)`. A test that passed in that class or module does not count for the fixtures it loaded. An outcome of the run that the check cannot place fails the run.
- **The comparison runs when the run stops.** It hooks the result's `stopTestRun`, which unittest's runner calls after the last test and before its summary. The comparison reads every fixture again. A record counts only if its bytes are the fixture's own as it stands then, so a name without its content does not count. Each problem is named in one failed test, `test_every_expected_test_ran_and_passed`.
- **It does not depend on the tests it watches.** [test_0_expected_tests_ran.py](test_0_expected_tests_ran.py) holds nothing but a `load_tests`, which gives one `Comparison`: a suite that holds no test. When the run reaches it, it hooks `stopTestRun` for the directory of fixtures. Every `FixtureTest` hooks it too, for a run that does not go through discover. What happens to the tests that load fixtures, before or after, does not change whether the comparison runs.

**Why it runs, and runs last.** Each step is unittest's own code, the same in Python 3.9 and 3.12:

1. `TestLoader.discover` lists the directory with `sorted(os.listdir(start_dir))` and loads the modules in that order, so `test_0_expected_tests_ran.py` comes before every module whose name starts with `test_` and a letter. A test in `Collected` fails when the comparison is not the first thing discover gives.
2. `loadTestsFromModule` returns what the module's `load_tests` returns. A filter such as `-k` is applied in `getTestCaseNames`, to the methods of a test class, so it does not reach a suite that holds no test.
3. `TestSuite.run` calls every child in order. It stops early only when `result.shouldStop` is set, by `-f` after a failure or by `-c` after an interrupt, and neither can happen before the first child. So the comparison is hooked before any test runs.
4. `TextTestRunner.run` calls `stopTestRun` in a `finally`, after `test(result)` has returned. That is after the last test, its tear-down and the tear-down of the last class and module. Then it prints the errors and the summary, and `unittest.main` exits with `not result.wasSuccessful()`.

**Every way that was tried to keep the comparison from running.** Each is a test that runs `unittest discover` in a process of its own, on a project of `expected_tests.py`, `test_0_expected_tests_ran.py` and the fake tree, and the run must exit 1 and name the fixtures.

| How the tests that load fixtures were kept from running | Test in `Discover` |
|---|---|
| A `setUpClass` shared by every `FixtureTest` raises `SkipTest`: the reviewer's probe | `test_a_set_up_shared_by_every_fixture_test_that_skips_exits_nonzero` |
| A `setUpClass` of the class raises `SkipTest`, or an error | `test_a_class_set_up_that_skips_exits_nonzero`, `test_a_class_set_up_that_errors_names_the_fixtures` |
| A `setUpModule` raises `SkipTest`, or an error | `test_a_module_set_up_that_skips_exits_nonzero`, `test_a_module_set_up_that_errors_names_the_fixtures` |
| The class has a skip decorator | `test_a_class_skip_decorator_exits_nonzero` |
| A `load_tests` in the module drops every test | `test_a_load_tests_hook_that_drops_the_tests_exits_nonzero` |
| The only module that loads fixtures cannot be imported | `test_the_only_module_that_loads_fixtures_cannot_be_imported` |
| The module has a name that discover does not collect | `test_a_module_that_discover_does_not_collect_exits_nonzero` |
| `-k` selects no test that loads fixtures, or only some | `test_a_filter_that_selects_no_test_that_loads_fixtures_exits_nonzero`, `test_a_filter_that_selects_some_of_them_names_the_rest` |
| `-f` stops the run at a failure before any test that loads fixtures | `test_a_run_that_stops_at_the_first_failure_names_the_rest` |
| `-c` and an interrupt stop the run before any test that loads fixtures | `test_a_run_interrupted_before_any_fixture_test_names_every_fixture` |
| A `tearDownModule` raises an error, or `SkipTest`, after the tests passed | `test_a_tear_down_module_that_errors_names_the_fixtures_of_the_module`, `test_a_tear_down_module_that_skips_exits_nonzero` |
| There is no test at all | `test_the_comparison_alone_exits_nonzero` |

**The cases.** Each is a test in [test_expected_tests.py](test_expected_tests.py). They use a fake tree of two fixtures, [fixtures/tests-ran/tree/](fixtures/tests-ran/tree/), copied into a scratch directory, and give the check either fake results or the results of a small suite run with unittest's own runner.

| Case | What is wrong | Result |
|---|---|---|
| A complete set | Nothing. Every fixture is loaded by a test that passes, as bytes, as text, as a copied file or as a copied directory. | Passes |
| A missing test | A fixture that no test loads. | Fails |
| A skipped test | The only test for a fixture is skipped, before it loads the fixture or after. | Fails |
| An erroring test | A test that loaded a fixture raised an error. | Fails |
| A failing test | A test that loaded a fixture failed. | Fails |
| An expected failure | A test marked `expectedFailure` loaded a fixture and failed, which by itself does not fail a run. | Fails |
| An unexpected success | A test marked `expectedFailure` loaded a fixture and passed. | Fails, and names the fixture |
| A subtest | A subtest of a test that loaded fixtures failed, errored or was skipped. Every fixture of the test is named. | Fails |
| Not prepared | A `setUp` that loaded a fixture raised an error before the test's body ran. | Fails |
| A tear-down or a cleanup | `tearDown` or a cleanup failed after the body had loaded a fixture. | Fails |
| A class or a module | A `setUpClass` skipped or errored, or the class is skipped, so no test loaded the fixtures. A `tearDownClass` or a `tearDownModule` errored or skipped after its tests passed. | Fails |
| An outcome the check cannot place | The run holds an outcome of a class or a module under a name of another form. | Fails |
| Without discover | A run with no comparison suite: the first `FixtureTest` hooks the comparison. | Fails |
| A failure beside a pass | Two tests load a fixture, and one of them fails. | Fails |
| Only named | A test that names the fixture, or opens its path, without loading it through `FixtureTest`. | Fails |
| Not as it stands | A record of a fixture without its bytes, with another fixture's bytes, or with bytes the fixture no longer holds when the run stops. | Fails |
| No such fixture | A test names a fixture that does not exist, a directory, or a name outside the tree, even if the test passes. | Fails |
| An empty directory | The directory of fixtures holds no fixtures. A run that expects nothing has not shown that everything ran. | Fails |
| No directory | There is no directory of fixtures. | Fails |
| A name no test can give | A file whose name starts with a dot. | Fails |
| A link | A link in the tree. | Fails |
| A module that cannot be imported | Its tests never run. The run fails on the import, and the fixtures that only it loads are named. | Fails |
| `unittest discover` | In a process of its own, as CI runs it: exit status 0 for a complete set and 1 for a missing test, and 1 for every way above of keeping the tests from running. | Passes, then fails |
| The comparison is collected | Discover over this directory gives the comparison first, also with `-k`. | Passes |

**What it does not claim.**

- It does not see whether a test uses what it loads. A test that loads a fixture and then checks something else, or drops a case it could not prepare after it loaded the fixture, passes. One mutation per case shows that a test uses its fixture (`ratchet.test-can-fail`), and the PR that adds a case shows the mutation.
- The outcome is a test method's, not a subtest's. A method that loads many fixtures in subtests counts for all of them when it passes, and fails all of them when one subtest fails.
- A test can still open a fixture by its path. Such a test is not counted, so the fixture stays expected and the run fails unless another test loads it.
- It is a part of the run, and code in the run can switch it off: a test that replaces the result's `stopTestRun` or empties the ledger. Removing or renaming `test_0_expected_tests_ran.py` is a change to `checks/` that the maintainer reads (`ratchet.checks-owner-read`), and the tests in `Collected` fail without it.
- It relies on unittest's runner and on discover. A run of one module without discover, such as `python3 -m unittest test_checks`, holds no comparison suite: the first `FixtureTest` that runs hooks it, and if none runs, nothing compares. So does a pattern given with `-p` that does not match `test_0_expected_tests_ran.py`. Another runner, such as pytest, needs a check of its own.
- It reads how unittest names a class or a module that did not pass, `tearDownClass (module.Class)`. That name is unittest's own and the same in 3.9 and 3.12. A name of another form fails the run rather than being passed over.
- A run of part of the suite, with `-k` or a single module, fails on purpose: it did not run every expected test.
- A fixture is a file. A fixture that is a directory, such as `register/md-missing`, is expected as the files it holds. That it holds no `REGISTER.md` is the test's to check.

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
- the first entry in the changelog is not the version in `ratchet.json`, or `## Unreleased` and then that version
- a released entry of the changelog is not as it was released: see below
- `.github/CODEOWNERS` holds anything but the one rule that gives every path to the maintainer.

**Released text stays as it was released.** [releases.json](../releases.json) records every release: its version, its date, and the sha256 of its changelog entry and of its `ratchet.json` as they stood at its tag. 0.1 and 0.2 had no `ratchet.json`. It is read strictly, newest first, and every released entry of the changelog must be one of its records, in the same order.

- **The state.** When `ratchet.json` is, byte for byte, the release it names, every text that names the version names it alone. When it holds changes after that release, the count, the version in `RATCHET.md` and the version line of a register say "with unreleased changes", and `check_register.py` says so in what it prints. The register check reads `releases.json` next to the `ratchet.json` it runs from.
- **The changelog.** An entry is headed `## Unreleased` or `## <version> (<date>)`, and nothing else. When `ratchet.json` holds changes after its release, the first entry must be `## Unreleased`. It may stand first at other times too, for changes that are not to the rules. Only the first entry is generated, when it is `## Unreleased` or the entry of the version being released. Every entry after it is never rewritten, and its sha256 must be the one in `releases.json`.
- **A release.** A release PR renames `## Unreleased` to `## <version> (<date>)`, sets the version and the date in `ratchet.json`, the version in `register.json` and the fetch command in the README, and runs the generator. The generator then fails once, and prints the record of the new release to add as the first line of `releases.json`. The release workflow finds the entry by `^## <version> \(`. A test runs these steps on a copy of the repo.
- **What the tags show.** CI checks out one commit without tags, so the check in CI compares the changelog with `releases.json`. Two tests compare the changelog and `releases.json` with the tags themselves, where the checkout holds them, as it does locally after `git fetch --tags`. In a checkout without the tags they are skipped, and say so.

| Case | Result |
|---|---|
| A word changed in a released entry, or a line added at the end of the last one | Fails |
| The generator runs: the count in a released entry stays as it was released | Passes |
| `ratchet.json` holds changes after its release, and the changelog has no `## Unreleased` | Fails |
| `## Unreleased` without its count, with its count edited by hand, or not first | Fails |
| A heading of another form, such as `## 0.4` or `## unreleased` | Fails |
| A released entry with no record, or a record with no entry | Fails |
| A record with a field the check does not know, a short sha256, a version twice or another form of date | Fails |
| No `releases.json` | Fails, in the generator and in the register check |
| The steps of a release on a copy of the repo | Passes, and no generated text says "with unreleased changes" |
| A change to the rules after that release, first without `## Unreleased`, then with it | Fails, then passes |

## Why JSON

The rules are data that the checks and a project's CI must read. The format was chosen so that the checks need nothing but a Python interpreter:

- Python's standard library reads JSON in every supported version. It reads TOML only from 3.11, and it does not read YAML at all.
- The Python that ships with a common developer operating system is older than 3.11. A check that needs a newer interpreter, or a package, is a check that does not get run.

The cost is that JSON has no comments and escapes quotation marks. The rules are one sentence per field, so it stays readable, and anything that needs explaining belongs in the changelog or in a decision.
