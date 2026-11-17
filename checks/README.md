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
 "ratchet_version": "0.4",
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
python3 checks/expected_tests.py
```

The reference check for `ratchet.expected-tests-ran`. It runs in a step of its own in CI, and it runs the suite in a process of its own: it starts [suite_runner.py](suite_runner.py), which runs `unittest discover -s checks` with unittest's own text runner, and reads what the runner records. A test that loads fixtures is a `FixtureTest`, from `suite_runner.py`, and loads each one by its name under [fixtures/](fixtures/), with `fixture_bytes`, `fixture_text`, `fixture_file` or `fixture_directory`. The last two give a copy in a scratch directory, made from the bytes that were loaded, and the check under test is run on the copy.

**What it claims.** In the run, every test that discover collects ran once under its id and passed, with exactly one outcome record, nothing ran that was not collected, the run finished, and every file under `checks/fixtures/` was loaded, with the bytes it held before the run, by a test that passed. Otherwise the check prints each problem and exits 1, whatever the suite's own exit status was.

**Against which threat.** Tests dropped by mistake, while the suite still looks green: a test skipped, errored or not prepared, a class or module whose set-up skips, a module that no longer imports, a run that exits before it is done, a run that returns before it is done because it was interrupted, told to stop or stopped at the first failure, two tests under one id so that one hides the other, a fixture added and never tested, or a test that names a fixture that is gone. A green summary says only that the tests that ran passed, not that the tests that were meant to run did.

**What it does not claim.** It does not stop test code written to defeat it. Such code runs with the same rights as the check: it can write records of its own, rewrite the runner or this check, or pass without testing anything. A change to `checks/` is read by the maintainer before it is merged (`ratchet.checks-owner-read`), and that reading is what stands against it.

**How it works.**

- **A process of its own.** The check makes a temporary directory, starts the runner as a child process with the path of a record file in it, waits for the child and reads the file. It does not run in the process it watches, so nothing the tests do to unittest's result, to its hooks or to the exit of their own process changes what the check sees: an exit is a missing record, not a pass.
- **What was collected.** Before the run, the runner writes a record "collected" for every test in the suite that discover returns, each with a number of its own, and the completion record holds unittest's own `countTestCases()` of the suite, taken before the run. A test that starts uses the number it was collected under. One that was not collected gets a new number, and fails the run.
- **The outcomes come from the runner.** The runner's result class takes the outcomes from unittest's result object: passed, failed, errored, skipped, expected failure or unexpected success. When a test stops, the runner writes one record "outcome" for it, with every outcome unittest gave it while it ran, in order. So a test that fails and then errors in `tearDown`, or whose subtests fail twice, has one record, and a second record of one instance is always a problem. An outcome of a subtest is an outcome of its test. An outcome given outside the run of its test, such as one given to a test after it stopped, is a record of its own at once. An outcome of a `setUpClass`, `tearDownClass`, `setUpModule` or `tearDownModule` has an instance that was never collected and never started, and fails the run.
- **The tests write only what they loaded.** A `FixtureTest` writes the fixture's name and the sha256 of the bytes it read, with the instance that was running. A load outside any test, as in `setUpClass`, does not count.
- **The completion record.** After unittest has printed its summary, the runner writes one last record with the number of tests collected, of tests run, of outcomes and of loads. A child that exits early, with `sys.exit` anywhere, `os._exit`, a `KeyboardInterrupt` or another error the runner does not catch, or that is killed, leaves it out, and the check fails. A run that returns early writes it: under unittest's Ctrl-C handler, after `result.stop()` sets `shouldStop`, or with `failfast` after a failure. The tests it did not run were collected and have no start, and the check fails on each.
- **Read strictly.** One JSON object per line, each ending in a line break, in UTF-8, parsed by the strict reader every check uses, `registry.strict_loads`: a field twice, `NaN` or `Infinity`, or a line nested too deeply is a problem, not a crash. Each kind of record has exactly its fields, each of its own form: an instance is a whole number from 1, the outcomes are a list of one or more of the six, a test is a name of one line with no lone surrogate, a fixture is a fixture's name, a sha256 is 64 lowercase hex digits. Anything else, a line cut off, a record after the completion record, a test collected after the run started, fails the run.
- **The comparison.** The check fails on: an exit status other than 0, or a signal; no completion record, two of them, or counts that disagree with the records; a test that was collected and did not run; a test that ran and was not collected, which covers no fixture; a test whose outcomes are not exactly one "passed", or that started and has no outcome; a second outcome record of one instance, after which the instance does not count as passed; an id that ran more than once; an instance collected twice or started twice, a start or an outcome that names another test than its instance; a fixture that no test that passed loaded with the bytes it held before the run; a load of a fixture that does not exist, or of other bytes; a fixture that changed while the suite ran; a suite that ran no tests.
- **The expected set.** The tests are the ones discover collects, and the fixtures are read from the directory, not from a list in a test and not from Markdown. Every file is one fixture. A file whose name starts with a dot, or holds a character other than letters, digits, `_`, `.` and `-`, fails, and so does a link.

**The cases.** Each is a test in [test_expected_tests.py](test_expected_tests.py). The tests in `Runs` run the check, as CI runs it, on a small suite in a scratch directory whose fixtures are a copy of [fixtures/tests-ran/tree/](fixtures/tests-ran/tree/). The tests in `Records` give the reader of the records a file that no runner wrote. The first eight rows are the ways the two review rounds kept the earlier, in-process check from seeing a test that did not run.

| Case | What is wrong | Test | Result |
|---|---|---|---|
| A skip in `setUpClass` | The class's tests never start. | `Runs.test_a_skip_in_set_up_class_fails`, `Runs.test_a_skip_in_a_set_up_class_that_every_fixture_test_shares_fails` | Fails |
| `sys.exit(0)` in `setUpClass` | unittest does not catch it. The run stops with no summary and exit status 0. | `Runs.test_sys_exit_in_set_up_class_fails` | Fails: no completion record |
| `sys.exit(0)` in `load_tests` | The run stops while discover loads it, with exit status 0. | `Runs.test_sys_exit_in_load_tests_fails` | Fails: no completion record |
| A duplicate id through a class alias | `Alias = Loads` runs every test twice under one id, and a later pass hid an earlier skip. | `Runs.test_a_duplicate_id_through_a_class_alias_fails`, `Runs.test_a_duplicate_id_that_passes_both_times_fails` | Fails |
| An expected failure | A test marked `expectedFailure` fails, which does not fail a unittest run. | `Runs.test_an_expected_failure_fails` | Fails |
| A skip decorator on a class | Every test of the class is skipped. | `Runs.test_a_skip_decorator_on_a_class_fails` | Fails |
| A module that fails to import | discover gives a test that errors in its place. | `Runs.test_a_module_that_fails_to_import_fails` | Fails |
| The release steps | The release of 0.4 on a copy: the workflow's regex finds the entry, the guard passes before and after the tag, and the full suite passes after it, run by this check. | `test_released_text.ReleaseSteps` | Passes |
| A killed child | A test kills its own process. | `Runs.test_a_killed_child_fails` | Fails: the signal, no completion record, a test with no outcome |
| A record of an unknown form | An unknown kind, an unknown or missing field, an instance that is not a whole number from 1, an unknown outcome, a sha256 or a name of another form, a line that is not one JSON object, a field twice, a line cut off, bytes that are not UTF-8. | `Records.test_a_record_of_a_form_the_check_does_not_know_fails` and the six after it | Fails |
| A complete set | Nothing. Every fixture is loaded by a test that passes, as bytes, as text, as a copied file or as a copied directory. | `Runs.test_a_complete_set_passes`, `Runs.test_every_way_of_loading_counts`, `Records.test_a_complete_run_passes` | Passes |
| An exit from inside a test | `os._exit(0)` in a test. | `Runs.test_an_exit_from_inside_a_test_fails` | Fails: no completion record |
| A missing test | A fixture that no test loads. | `Runs.test_a_fixture_that_no_test_loads_fails` | Fails |
| A skipped, failing or erroring test, or one not prepared | Before or after the test loaded its fixtures, or in `setUp`. | `Runs.test_a_skipped_test_fails`, `Runs.test_a_test_skipped_after_it_loaded_fails`, `Runs.test_a_failing_test_fails`, `Runs.test_an_erroring_test_fails`, `Runs.test_a_test_that_could_not_be_prepared_fails` | Fails |
| An unexpected success | A test marked `expectedFailure` passes. | `Runs.test_an_unexpected_success_fails` | Fails |
| A subtest | A subtest fails, or is skipped. | `Runs.test_a_failing_subtest_fails`, `Runs.test_a_skipped_subtest_fails` | Fails |
| A tear-down of a module | `tearDownModule` errors after its tests passed. | `Runs.test_an_error_in_tear_down_module_after_the_tests_passed_fails` | Fails |
| A load outside a test | A fixture loaded in `setUpClass`. | `Runs.test_a_fixture_loaded_outside_a_test_fails` | Fails |
| Not as it stands | A fixture changed before it was loaded, or only opened by its path. | `Runs.test_a_fixture_changed_before_it_was_loaded_fails`, `Runs.test_a_fixture_that_is_only_named_fails` | Fails |
| No such fixture | A name that does not exist, a directory, a name outside the tree or one that starts with a dot. | `Runs.test_a_name_that_is_not_a_fixture_fails_the_test`, `Records.test_a_fixture_that_does_not_exist_fails` | Fails |
| A tree that cannot be read | A link or a hidden file in the tree, no fixtures, no directory. | `Runs.test_a_tree_that_cannot_be_read_fails`, `Runs.test_an_empty_fixtures_directory_fails`, `Runs.test_a_missing_fixtures_directory_fails` | Fails |
| The counts and the order | No record file, no completion record, two, a record after it, counts that disagree, an instance started twice, an outcome of another test, an outcome outside any test, a load by an instance that never started. | the other tests in `Records` | Fails |
| A pass beside a failure | Two tests load a fixture and one fails, or one instance has a pass and an error. | `Records.test_a_passing_test_does_not_cover_for_one_that_failed_on_the_same_fixture`, `Records.test_a_pass_and_another_outcome_of_one_instance_is_not_a_pass` | Fails for the test that did not pass |
| An interruption under the Ctrl-C handler | `unittest.installHandler()` and a SIGINT: unittest stops after the test that is running, prints `OK` and exits 0. Finding 1 of round 1 of the new approach. | `Runs.test_an_interruption_under_the_ctrl_c_handler_fails`, `Records.test_a_collected_test_that_did_not_run_fails` | Fails: collected and did not run |
| `result.shouldStop` | A test calls `result.stop()`, and the run returns with the next test not run. | `Runs.test_a_run_told_to_stop_fails` | Fails: collected and did not run |
| `failfast` | The run stops at the first failure. | `Runs.test_failfast_after_a_failure_fails_for_the_tests_it_did_not_run` | Fails: the failure, and collected and did not run |
| A `KeyboardInterrupt` | Raised in a test. unittest does not catch it, and the child exits with no summary. | `Runs.test_a_keyboard_interrupt_raised_in_a_test_fails` | Fails: no completion record, no outcome, collected and did not run |
| `self.skipTest` in `setUp` | The test is skipped before its body runs. | `Runs.test_a_skip_in_set_up_fails` | Fails |
| Ran and was not collected | A test runs another test case that discover did not collect, which loads the fixtures. | `Runs.test_a_test_that_ran_and_was_not_collected_fails`, `Records.test_a_test_that_ran_and_was_not_collected_fails` | Fails, and the loads count for nothing |
| A second outcome of one instance | `result.addSuccess` once more after the test stopped. Finding 6 of round 1 of the new approach. | `Runs.test_a_second_pass_of_one_instance_fails`, `Records.test_a_second_outcome_record_of_one_instance_fails`, `Records.test_two_passes_in_one_outcome_are_not_a_pass` | Fails, and the instance is not a pass |
| Several outcomes while a test runs | A failure and an error in `tearDown`, or two failing subtests. | `Runs.test_a_test_with_several_outcomes_has_one_outcome_record` | Fails, with one outcome record |
| A fixture changed after it was loaded | A test appends to a fixture, removes one, or adds one, after the loads. Finding 5 of round 1 of the new approach. | `Runs.test_a_fixture_changed_after_it_was_loaded_fails` | Fails: changed while the suite ran |
| What was collected, out of order | A test collected twice, collected after the run started, or started under another test's number, or a count of collected tests that disagrees. | `Records.test_a_test_collected_twice_fails`, `Records.test_a_test_collected_after_the_run_started_fails`, `Records.test_a_start_of_another_test_than_its_collected_instance_fails`, `Records.test_counts_that_disagree_with_the_records_fail` | Fails |
| Records that are not strict JSON | `NaN`, `Infinity`, a field twice, a line nested too deeply. | `Records.test_a_constant_that_is_not_json_fails`, `Records.test_a_field_twice_in_one_record_fails`, `Records.test_a_line_nested_too_deeply_fails` | Fails, with no crash |

**Known limits.**

- Test code that defeats the check on purpose, as above.
- It does not see whether a test uses what it loads. A test that loads a fixture and then checks something else passes. One mutation per case shows that a test uses its fixture (`ratchet.test-can-fail`), and the PR that adds a case shows the mutation.
- The outcome is a test method's, not a subtest's. A method that loads many fixtures in subtests counts for all of them when it passes, and fails all of them when one subtest fails.
- A test can still open a fixture by its path. Such a test is not counted, so the fixture stays expected and the run fails unless another test loads it.
- It relies on unittest's runner and on discover. A test that discover does not collect, because its module's name does not start with `test`, is not expected. Another runner, such as pytest, needs a check of its own.
- It reads how unittest reports the set-up and tear-down of a class or a module: as an outcome of an object that is not a test, the same in 3.9 and 3.12. Every such outcome fails the run.
- `python3 -m unittest discover -s checks` still runs the suite on its own, and records nothing. Only `checks/expected_tests.py` checks that every expected test ran.

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
- the first entry in the changelog is not the version in `ratchet.json`, or a heading of an entry is not of the form `## <version> (<date>)`
- `.github/CODEOWNERS` holds anything but the one rule that gives every path to the maintainer.

In the changelog only the first entry is generated: the entry of the version that `ratchet.json` names, which is released when it is merged. Every entry after it is released text, and the generator never rewrites it. That it stays as it was released is checked against the tags, by `released_text.py`.

## released_text.py

```sh
python3 checks/released_text.py
```

**What it claims.** Released text is as it stood at its tag. It reads the tags of the checkout, every one of the form `vMAJOR.MINOR`, and compares:

- every entry of `CHANGELOG.md` that a tag holds, from its heading to the next one, with the same entry at that tag, byte for byte after CRLF is read as LF. Every tag that holds a changelog is compared with every entry it holds, so an entry is compared with each later tag too.
- `ratchet.json`, when it names a version that has a tag, with `ratchet.json` at that tag. A change to the rules raises the version (`D-2026-11-17-new-approaches`). It is read first as every check reads it, with `registry.strict_loads` and `registry.validate`, and fails when it is not a valid data file.

It also fails when a tag has no entry in the changelog (`ratchet.si-version`), when an entry after the first has no tag, when a heading is not of the form `## <version> (<date>)` or a version stands twice, when there are no tags, when a tag is of another form, and when the tags cannot be read.

**Against which threat.** Released text rewritten after its tag, as the count under the released heading of 0.3 was, by the generator, in the first round of PR #12. A record of the release kept in the repo does not protect it, because the same PR can change the record. The tag is published, and is never moved (`repo.tags-stay`).

**In CI.** The checkout of the job `checks` fetches the tags, with `fetch-depth: 0`, and a step runs this check. Without the tags it fails, and says so: it is never skipped. The tests in [test_released_text.py](test_released_text.py) make a git repo of their own, with tags of their own, so they need none of this repo's tags.

| Case | Result |
|---|---|
| Released text as it stood at its tags | Passes |
| The version not yet released changes | Passes |
| A word changed in a released entry, its count regenerated, its date changed, or a line added at the end of the last entry | Fails |
| A released entry removed | Fails |
| A tag with no entry, also a tag that holds no changelog, as `v0.1` | Fails |
| An entry after the first with no tag | Fails |
| A heading of another form, such as `## Unreleased`, `## 0.4` or `## 0.4 (soon)`, or an entry twice | Fails |
| A changelog that is not UTF-8, or no changelog | Fails |
| `ratchet.json` names a released version and is as it stood at its tag | Passes |
| `ratchet.json` names a released version and its rules changed, or the tag holds no `ratchet.json`, or it cannot be read | Fails |
| `ratchet.json` is not a valid data file, read as every check reads it: a field twice, `NaN` or `Infinity`, an unknown or a missing field, nested too deeply, not an object, not UTF-8. Finding 4 of round 1 of the new approach. | Fails |
| A tag of another form, such as `v0.4-rc1` or `latest` | Fails |
| An annotated tag | Passes |
| No tags, or no git checkout | Fails |
| The release of 0.4 on a copy of this repo: the regex of the release workflow, `^## 0.4 \(`, finds its entry, the guard passes before the tag and after it, and the full suite passes after it | Passes |
| After that release, a rule changed without a new version | Fails |

**What it does not claim.** It trusts the tags it is given. A tag deleted or moved on the server is outside what it can see: that is a setting of the repository. It does not see whether the text of the first entry, the version not yet released, is right.

## Why JSON

The rules are data that the checks and a project's CI must read. The format was chosen so that the checks need nothing but a Python interpreter:

- Python's standard library reads JSON in every supported version. It reads TOML only from 3.11, and it does not read YAML at all.
- The Python that ships with a common developer operating system is older than 3.11. A check that needs a newer interpreter, or a package, is a check that does not get run.

The cost is that JSON has no comments and escapes quotation marks. The rules are one sentence per field, so it stays readable, and anything that needs explaining belongs in the changelog or in a decision.
