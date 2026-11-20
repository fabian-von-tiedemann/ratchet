# Reference checks

Checks that Ratchet ships. Each one runs in this repo's CI ([checks.yml](../.github/workflows/checks.yml)) and has a fixture it fails on. They use Python's standard library only, so a project needs nothing installed to use them. They have been run on Python 3.9 and 3.12.

<!-- generated:reference-checks -->
| Rule | Reference check |
|---|---|
| ratchet.register-on-top | [checks/check_register.py](check_register.py) |
| ratchet.irreversible-waits | [checks/tripwire.py](tripwire.py) |
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
- **Read strictly.** One JSON object per line, each ending in a line break, in UTF-8, parsed by the strict reader every check uses, `registry.strict_loads`: a field twice, `NaN` or `Infinity`, or a line nested too deeply is a problem, not a crash. The kind of a record is text, and its type is checked before the kind is looked up. Each kind of record has exactly its fields, each of its own form: an instance is a whole number from 1, the outcomes are a list of one or more of the six, a test is a name of one line with no lone surrogate, a fixture is a fixture's name, a sha256 is 64 lowercase hex digits. Anything else, a line cut off, a record after the completion record, a test collected after the run started, fails the run.
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
| The release steps | The version that `ratchet.json` names, on a copy: first unreleased, when a merge publishes nothing, then given its date and released. The guard passes before and after the tag, and the full suite passes after it, run by this check. | `test_released_text.ReleaseSteps` | Passes |
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
| A kind of record that is not text | A list, an object, a number, `true` or `null` as the kind. A list or an object raised `TypeError`, because the kind was looked up before its type was checked. | `Records.test_a_kind_of_record_that_is_not_text_fails`, `Records.test_a_value_of_any_json_type_in_any_field_gives_problems_and_no_exception` | Fails, with no crash |
| Records that are not strict JSON | `NaN`, `Infinity`, a field twice, a line nested too deeply. | `Records.test_a_constant_that_is_not_json_fails`, `Records.test_a_field_twice_in_one_record_fails`, `Records.test_a_line_nested_too_deeply_fails` | Fails, with no crash |

**Known limits.**

- Test code that defeats the check on purpose, as above.
- It does not see whether a test uses what it loads. A test that loads a fixture and then checks something else passes. One mutation per case shows that a test uses its fixture (`ratchet.test-can-fail`), and the PR that adds a case shows the mutation.
- The outcome is a test method's, not a subtest's. A method that loads many fixtures in subtests counts for all of them when it passes, and fails all of them when one subtest fails.
- A test can still open a fixture by its path. Such a test is not counted, so the fixture stays expected and the run fails unless another test loads it.
- It relies on unittest's runner and on discover. A test that discover does not collect, because its module's name does not start with `test`, is not expected. Another runner, such as pytest, needs a check of its own.
- It reads how unittest reports the set-up and tear-down of a class or a module: as an outcome of an object that is not a test, the same in 3.9 and 3.12. Every such outcome fails the run.
- `python3 -m unittest discover -s checks` still runs the suite on its own, and records nothing. Only `checks/expected_tests.py` checks that every expected test ran.

## watch_sources.py

```sh
python3 checks/watch_sources.py
python3 checks/watch_sources.py --data sources.json
```

This is not a reference check for a rule. It is a tool this repo runs on its own sources, the list `sources` in [sources.json](../sources.json) that `RATCHET.md` shows under Sources. The data file is an object with the one field `sources`, and any other field fails the run before anything is read ([D-2026-11-19-batched-releases](../decisions/D-2026-11-19-batched-releases.md)). Its tests run in this repo's CI with the others. The script itself is meant to run once a day in a workflow of its own, with the workflow's built-in token.

**What it claims.** For each pinned source, the run reads the head of the source's default branch and compares the pinned commit with it, through the GitHub REST API. It reads the head as `commits/HEAD`, which GitHub resolves to the head of the default branch, so it never reads the name of the branch.

- A source without a directory has moved when the compare is not `identical`.
- A source with a directory has moved when at least one changed file is under the directory, or when the compare is `behind` or `diverged`. If the API does not say which files changed, or lists 300 files and none of them under the directory, the watch cannot tell, and counts the source as moved.
- A source that has moved has one open issue, titled `Source moved: <name>`. A pinned commit that is not found upstream has one open issue, titled `Source pin missing: <name>`. A source that has not moved writes nothing.
- Every read comes before any write. Then every title and body is built and passes one gate, and only then is anything written. A read that fails, an answer of a form the watch does not know, or a title or body that fails the gate, fails the run before anything is written.

**Against which threat.**

1. A pinned source moves, and nobody notices, so a rule keeps crediting a source that now says something else, or a project keeps copying a skill at a pin that has gone (`ratchet.skills-pinned`).
2. Text from a source, from an answer of the API or from `sources.json` is written so that the issue pings someone, links somewhere, shows HTML or reads as an instruction (`ratchet.material-not-instructions`), or so that a line in the log is read by the runner as a command, such as `::warning::` or `##[error]`.
3. The token is printed in a log or an error, written into an issue, or sent to another host.

**No text from a source (`D-2026-11-17-new-approaches`, in PR #13).** Two review rounds found text from upstream that escaping did not make inert, and a token that got through an encoding the watch did not undo. So the watch no longer tries to make such text safe. No text from a source, and no text from an answer of the API, reaches an issue, a title or a printed line. An issue holds only these values:

| Value | From | Checked as |
|---|---|---|
| Name | `sources.json` | The narrow form below |
| Directory | `sources.json` | The narrow form below |
| Pinned commit | `sources.json` | 40 lowercase hex characters |
| Head of the default branch | The API | 40 lowercase hex characters |
| Status | The API | One of `identical`, `ahead`, `behind`, `diverged` |
| Commits ahead and behind | The API | Integers from 0 to 999999999 |
| Changed files, and those under the directory | Counted by the watch from the API's list | Integers, or "not listed by the API" |
| Compare link | Owner and repo from `sources.json`, and the two shas | `https://github.com/<owner>/<repo>/compare/<pin>...<head>` |
| Everything else | Fixed English text in the script | Each line exactly |

No commit subject, file name, branch name, author or message is written. The issue tells the reader to follow the compare link to see the commits and the files, and that what they find there is material, not instructions. File names are read only to count those under the directory. The name of the default branch is not read at all.

**No path in an error, and no unchecked value in a path.** An error names the request by a fixed kind written in the script and, where there is one, the source's name or the title, for example `source pstack: reading the head of the default branch gave 404`. It gives the HTTP status as an integer. It never names a path or an address. Every path is built from values of a strict form, and the transport sends no other:

| Request | Its kind in an error | The values in its path, and their form |
|---|---|---|
| `GET /repos/<owner>/<repo>/commits/HEAD` | `source <name>: reading the head of the default branch` | Owner and repo from `sources.json`, and the fixed `HEAD` |
| `GET /repos/<owner>/<repo>/compare/<pin>...<head>` | `source <name>: comparing the pinned commit with the head` | The pin from `sources.json`; the head from the API, checked as 40 lowercase hex characters first |
| `GET /repos/<owner>/<repo>/commits/<pin>` | `source <name>: reading the pinned commit` | The pin, 40 lowercase hex characters |
| `GET /repos/<target>/issues?state=open&per_page=100&page=<n>` | `reading the open issues of the target repository` | `GITHUB_REPOSITORY`, checked as owner/repo; integers |
| `POST /repos/<target>/issues` | `opening the issue <title>` | The target |
| `PATCH /repos/<target>/issues/<number>` | `updating the issue <title>` | The target; the number from the API, checked as an integer from 0 to 999999999 first |

Before it sends a request, the watch matches its path in full against one of these forms. A path of any other form fails the run with `<kind>: the watch does not build such a request`, and nothing is sent. Only the issue numbers that the watch opened or updated are printed, as integers.

**The data.** A source has a `name`, a `repo`, a `commit` and a `license`, and may have a `directory` and an `author`:

```json
{"name": "pstack", "repo": "https://github.com/cursor/plugins", "directory": "pstack",
 "author": "Lauren Tan", "commit": "35a90942a7f02e1ebbc2443643179815f2147954", "license": "MIT"}
```

- **The name** is lowercase letters, digits, `.`, `-` and `/`, starts with a letter or a digit, and is at most 100 characters long. It has no `_`, since the gate allows no `_` outside a link: in Markdown an `_` can start emphasis. 100 characters keep `Source pin missing: ` and the name at 120 characters, well within the 256 that GitHub takes for a title, so a title is never cut. A name that would be longer is refused. A name is used once, so two sources never share a title.
- **The directory** is parts of lowercase letters, digits, `.` and `-`, joined by single `/`, at most 100 characters. No part is `.`, no `..` stands anywhere in it, and it does not start or end with `/`.
- **Neither holds `www.` or `GH-` and a digit**, in any case. GitHub makes a link of the one and a reference to an issue of the other, from characters the form allows.
- **The repo** is `https://github.com/`, an owner and a repository, and nothing else. The owner is letters, digits and `-`, starts with a letter or a digit and is at most 39 characters. The repository is letters, digits, `.`, `_` and `-`, at most 100 characters, not `.` or `..` and not ending in `.git`.
- **The commit** is a full sha in lowercase hex. The author and the license are text from [the list](#the-characters-a-value-may-hold).

`RATCHET.md` shows the repo, then `, directory` and the directory as code, then the author in brackets after `by`. The generator and the watch read the sources with the same function in [registry.py](registry.py), and the generator fails on the same sources as the watch.

**One gate.** Every planned title and body, and every printed line, passes the same check before it leaves the watch:

- **A grammar of lines.** A title is `Source moved: ` or `Source pin missing: ` and a name of the narrow form. Each line of a body is a blank line, one of the fixed sentences, or one of the lines in the table above, each matched in full by a pattern of its own.
- **A small set of characters.** Outside a link, a line holds only ASCII letters, digits, the space and `.` `,` `:` `'` `(` `)` `/` `-`. So it holds no `@`, `#`, `<`, `>`, `[`, `]`, `!`, backtick, `|`, `\`, `*`, `_`, line break, control, or any character outside ASCII. Inside a link to `https://github.com/`, it may also hold `_`, as a repository name may. No printed line names a path, so a path is not let through. A line never holds `::`, and outside a link never `www.` or `GH-` and a digit.
- **The token.** No title, body or printed line holds the token as it stands.

If one planned title or body fails, nothing is written. The error names the planned issue and the line, never the text. A printed line that fails is replaced by `a line that did not pass the output gate is left out`. Errors give only the kind of the request and the HTTP status as an integer, never a path, never anything from the body or the headers of an answer, and never the text of a network error. An error the watch does not know is printed as its kind and the line of the script.

The gate cannot tell a token that is encoded, for example in hex, from a sha or a name. That is why nothing from an answer may reach a line, a path in an error included, and not a reason to undo encodings.

**Why the token needs nothing more.** The earlier version replaced the token in every answer and looked for it behind escapes and encodings, because upstream text went into issues and logs. Now no text from an answer is written anywhere, so a token that an answer holds, in any encoding, has no way out. The only values that are written are checked for a form that a token of GitHub's does not have, and the gate refuses the token as it stands in case one ever did.

**The size of a body.** No list from the API reaches a body, so its size does not depend on the source. The largest body has a name and a directory of 100 characters, an owner of 39 and a repository of 100, nine-digit counts, 300 changed files, all under the directory, and the notes on a `diverged` compare and on a capped list. It is 1390 bytes, and a test builds it. GitHub takes 65536 characters.

**The token and the transport.** The token is read from the environment variable `GITHUB_TOKEN` and from nowhere else. It is sent only to `https://api.github.com`: the transport refuses an address before it connects unless it is printable ASCII, since `urllib.parse` drops tabs and line breaks that `urllib.request` keeps, and unless, split with `urllib.parse`, the scheme is `https`, the netloc (the host and the port as written, and any userinfo) is exactly `api.github.com`, the path starts with `/` and there is no fragment. It never compares by prefix, so `https://api.github.com.evil.invalid/`, `https://api.github.com@evil.invalid/`, `https://user@api.github.com/`, `https://api.github.com:443/`, `http://api.github.com/` and `https://API.GITHUB.COM/` are all refused. A redirect is not followed. It is an answer of its own, and the run fails on it, so the token is never sent on. Without a token the reads run unauthenticated. If nothing has moved, the run passes. If something would be written, the run fails, names the titles and writes nothing.

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
| `test_fixture_*`, one for each file under [fixtures/sources/](fixtures/sources/), each loaded through `FixtureTest` | 49 malformed sources: names with `##[`, `::`, `@`, `#`, `<`, a backtick, a space, a capital, `_`, a leading `.` or `-`, 101 characters, `www.` or `gh-12`; directories with `//`, `..`, a part `.`, a capital, `_`, 101 characters or `www.`; an owner with `_`; and the forms of round 1. | Fails, names the problem, or prints that a line was left out where the problem quotes `_` or `\|`; reads nothing |
| `test_the_sources_in_sources_json_have_the_form` | This repo's own sources. | Passes |
| `test_with_no_arguments_the_watch_reads_sources_json_in_this_repo` | No arguments: this repo's `sources.json`. | Passes, reads each source |
| `test_a_data_file_with_any_field_but_sources_fails_before_any_read` | `ratchet.json` with sources, a field besides `sources`, no field, a list, a field twice. | Fails, reads nothing |
| `test_an_unchanged_source_writes_nothing` | Two sources at their pins. | Nothing written |
| `test_a_moved_source_opens_one_issue` | A source two commits ahead. | One issue, with exactly the expected body |
| `test_a_second_run_updates_and_does_not_duplicate` | The same move twice, then a further move. | Nothing written the second time, then the open issue updated |
| `test_an_api_error_fails_without_writing` | An error, a rate limit, a missing repo, an answer that is not JSON, a network failure and a failing list of issues, at the second source after the first has moved. | Fails with exactly the kind of the request and the status; writes nothing |
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
| `test_an_answer_of_an_unknown_form_fails_without_writing`, `test_a_head_of_an_unknown_form_fails_without_writing` | An unknown status, counts that are text, a boolean, below zero or above the cap, files that are not a list, names that are not text; a head that is `HEAD`, uppercase, 39 or 41 characters, a number, missing or a list. | Fails with a fixed message, writes nothing; nothing is read after a bad head |
| `test_every_read_comes_before_any_write` | Two moved sources. | Every read, then both writes |
| `test_the_pinned_directory_is_written_as_before_in_ratchet_md` | The structured fields. | `RATCHET.md` shows the same repo text as before |
| `test_a_compare_that_disagrees_with_the_head_fails_without_writing` | `identical` with a head that is not the pin, and `ahead` with a head that is. | Fails, writes nothing |
| `test_an_ahead_compare_with_no_changed_file_is_a_move` | Round 1, finding 1: a source with no directory, one empty commit ahead. | An issue |
| `test_the_largest_body_is_small_and_holds_nothing_from_the_answer` | Round 1, finding 2: every value at its cap, with 250 commits and 300 files whose names hold mentions, runner commands, HTML and backticks. | 1390 bytes at most, none of that text in it |
| `test_the_gate_refuses_every_mark_outside_its_set`, `test_the_gate_refuses_a_line_of_a_kind_the_watch_does_not_write` | Round 1, finding 3: each refused mark in a title, a body and a printed line, and lines and titles of kinds the watch does not write. | Refused, nothing written |
| `test_a_plan_that_fails_the_gate_writes_nothing_at_all` | A second body that fails the gate. | Fails, names the issue and the line, writes neither issue |
| `test_no_text_from_an_answer_reaches_an_issue_or_a_line` | Round 1, finding 4, and round 2, finding 2: an answer whose every text field holds mentions, runner commands, a link, HTML, and the token as it stands, as `\u` escapes, percent-encoded twice and as HTML entities. | The body is byte for byte the body of a clean answer; the output holds none of it |
| `test_no_text_from_an_error_answer_or_a_network_error_reaches_a_line`, `test_an_error_the_watch_does_not_know_prints_only_its_kind_and_line` | The same text in an error answer, a network error and an unknown error. | Exactly the kind of the request and the status, or the kind of error and the line |
| `test_the_gate_refuses_the_token_as_it_stands`, `test_the_token_is_sent_with_every_call_and_never_printed` | A token that would pass the form of a name. | Refused in a title, a body and a printed line |
| `test_values_read_from_the_api_are_used_and_not_assumed` | Round 1, finding 5: a head, an owner, a repo, a target, issue numbers and counts that no other test uses. The head is read as `commits/HEAD`, so there is no branch name to assume. | Each value read is the value used |
| `test_a_printed_line_that_fails_the_gate_is_left_out` | Round 2, finding 1: printed lines with `##[error]`, `::error::`, `@`, the token, a carriage return and `_`, and a line that names a path with `_`. | Each replaced by the fixed line |
| `test_names_that_share_a_long_start_get_their_own_titles` | Round 2, finding 3: two names of 100 characters that differ in the last. | Two issues, each titled with the whole name |
| `test_no_error_names_a_path_or_a_value_from_an_answer` | Round 1 of the new approach, finding 1: a repository whose default branch is the token in hex, and each request in turn failing with a status, a network error or an answer that is not JSON: the head, the compare, the pinned commit, the list of issues, opening and updating. | Exactly the kind and the status; no path, no sha, no issue number, no `HEAD`, and neither the token nor its hex |
| `test_the_head_is_read_without_the_name_of_the_branch` | The same repository, moved. | Reads `commits/HEAD` and then the compare, and no request holds the branch |
| `test_a_request_is_built_only_from_checked_values` | Paths of every form the watch builds, and 19 it does not: the repository alone, a branch, `main`, an owner with `_`, an uppercase or short sha, `..` instead of `...`, `HEAD/../x`, a query, an issue number below zero, of ten digits or with `%0A`, `..` or `.` as a part, a line break, a percent-encoded `/`, `//evil.invalid` and another query on the issues. | The first sent; each of the others fails with the kind, and nothing is sent |
| `test_a_redirect_is_not_followed_and_the_token_goes_nowhere_else` | Round 2, finding 4: the real transport, against a local server that answers 301, 302, 303, 307 or 308 with an address on a second local server. | Fails with the status; the token reached the first server only, and the second got nothing |
| `test_the_redirect_handler_makes_no_new_request`, `test_the_transport_sends_nothing_to_another_address`, `test_the_real_transport_reads_an_answer` | The redirect handler alone, a local address that is not the API, and a plain run through the real transport. | No new request; refused before connecting; read as through the fake |
| `test_the_token_goes_only_to_the_exact_origin_of_the_api` | Round 1 of the new approach, finding 2: 23 addresses near the API, among them `api.github.com.evil.invalid`, `api.github.com@evil.invalid`, a userinfo part, the ports 443 and 8443, `http`, capitals, a trailing dot, a percent-encoded dot, a backslash, no path, a fragment, another scheme, a tab, a line break, a leading space and a character outside ASCII, with an opener that records what reaches it. | Each refused before an opener is built; the API itself reaches the opener with the token |

**What it does not claim.**

- It does not judge whether a move matters for a rule. That needs a reader, and the compare is material for one.
- It sees only the default branch and only sources on GitHub. It takes the default branch to be what GitHub resolves `HEAD` to, as it did for the sources here and for a repository whose default branch is `master` when this was written.
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
- the first entry in the changelog is not the version in `ratchet.json`, headed `## <version> (<date>)` or `## <version> (unreleased)`, an entry after the first is headed `(unreleased)`, or a heading of an entry is of another form
- the entries in the changelog do not stand newest first: each version, compared as a pair of integers, must be higher than the one after it, so a version twice or an entry moved up fails
- the command in `README.md` that fetches Ratchet is not the one line `git clone --branch v<version> https://github.com/fabian-von-tiedemann/ratchet .ratchet`, once, in a code block marked `sh`, for the highest version with a date in the changelog, or another line of `README.md` runs `git clone`. The line is matched whole, after the spaces that indent it, so a pin written in prose, a command with more on its line, or the command outside such a block does not count. `generate.py` reads no tags, so it does not claim that the tag exists: the window in which it does not is under "What it does not claim" in [released_text.py](#released_textpy)
- the landing page, `docs/index.html`, does not hold the line `<pre><code>git clone --branch v<version> https://github.com/fabian-von-tiedemann/ratchet .ratchet</code></pre>` exactly once, with any version, after the spaces that indent it, or another line of the page holds `git clone`. The generator writes into that line the version that the command in `README.md` must fetch, so `--check` fails when the page fetches another version than the README. The rest of the page is checked by a test: see [The landing page](#the-landing-page)
- the landing page does not hold the line `<p id="budget" class="stat"><strong>N experimental rules, with a cap of N.</strong> The core holds N rules and is frozen: N name a check and N are text only. Counted by <code>checks/generate.py</code> from <code>ratchet.json</code>.</p>` exactly once, with any numbers, after the spaces that indent it, or another line of the page holds `id="budget"`. The generator writes the numbers from `ratchet.json`, as in the count of rules, so `--check` fails when a rule or the cap changes and the page is not written again
- `sources.json` is not a valid data file: not strict JSON in UTF-8, a field twice, any field but `sources`, a source of another form, a name twice
- the source of a rule cites a name that is not a source in `sources.json`. The source of a rule is empty, or citations separated by `; `, each of which starts with the name of a source and then, after a space or a comma, says what is taken from it
- `.github/CODEOWNERS` holds anything but the one rule that gives every path to the maintainer.
- there are more experimental rules than `experimental_cap` in `ratchet.json`, or the cap is not a whole number from 0 (see [The budget](#the-budget)).
- an experimental rule has stood through three releases and 60 days with no decision, `since` or `kept_by` breaks its form, or a heading of the changelog has a date that does not exist or is earlier than that of the version before it (see [The age of an experimental rule](#the-age-of-an-experimental-rule)).

From [sources.json](../sources.json) it writes the table of sources in `RATCHET.md`, and the first line of `RATCHET.md` says the version and its date, or that it is not yet released. The date of a version is in the heading of its entry in the changelog, and nowhere else ([D-2026-11-19-batched-releases](../decisions/D-2026-11-19-batched-releases.md)).

In the changelog only the first entry is generated: the entry of the version that `ratchet.json` names, which is released when it is merged with a date in its heading. While it is headed `(unreleased)`, changes are collected under it, and no merge publishes it. Every entry after it is released text, and the generator never rewrites it. That it stays as it was released is checked against the tags, by `released_text.py`.

## released_text.py

```sh
python3 checks/released_text.py
```

**What it claims.** Released text is as it stood at its tag. It reads the tags of the checkout, every one of the form `vMAJOR.MINOR`, and compares:

- every entry of `CHANGELOG.md` that a tag holds, from its heading to the next one, with the same entry at that tag, byte for byte after CRLF is read as LF. Every tag that holds a changelog is compared with every entry it holds, so an entry is compared with each later tag too.
- `ratchet.json`, when it names a version that has a tag, with `ratchet.json` at that tag. A change to the rules raises the version (`D-2026-11-17-new-approaches`). It is read first as every check reads it, with `registry.strict_loads` and `registry.validate`, and fails when it is not a valid data file.

It also fails when a tag has no entry in the changelog (`ratchet.si-version`), when an entry after the first has no tag, when a heading is not of the form `## <version> (<date>)` or a version stands twice, when there are no tags, when a tag is of another form, and when the tags cannot be read.

**An unreleased first entry** ([D-2026-11-19-batched-releases](../decisions/D-2026-11-19-batched-releases.md)). The first entry may be headed `## <version> (unreleased)`, exactly. It passes while its version has no tag, and `ratchet.json` may name that version and change: nothing of it is released. An entry after the first headed so fails, and so does the first when its version has a tag: a released version stays released. Once the heading has a date, the next push to `main` releases it, and from its tag on the entry and `ratchet.json` are compared as every released one is. `sources.json` is not read: the list of sources is not part of what is released, so a pin that moves needs no new version. The threat here is the one that item 3 of [D-2026-11-17-new-approaches](../decisions/D-2026-11-17-new-approaches.md) named: an unreleased heading was once how released text got rewritten. So the heading has one exact form, only the first entry may have it, and released text is compared from its tag on as before.

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
| The first entry headed `## 0.4 (unreleased)`, with no tag `v0.4`, and `ratchet.json` and the entry changed under it | Passes, and says that the first entry is unreleased |
| That entry given its date, then tagged | Passes. From the tag on, the entry headed `(unreleased)` again fails |
| An entry headed `(unreleased)` after the first, two such entries, or the first for a version that has a tag | Fails |
| `(Unreleased)`, a space or a no-break space after it, no parentheses, no space before them, or one left open | Fails, not the heading of an entry |
| `ratchet.json` with `sources` or `date`, which left it in 0.9 | Fails, an unknown field |
| A changelog that is not UTF-8, or no changelog | Fails |
| `ratchet.json` names a released version and is as it stood at its tag | Passes |
| `ratchet.json` names a released version and its rules changed, or the tag holds no `ratchet.json`, or it cannot be read | Fails |
| `ratchet.json` is not a valid data file, read as every check reads it: a field twice, `NaN` or `Infinity`, an unknown or a missing field, nested too deeply, not an object, not UTF-8. Finding 4 of round 1 of the new approach. | Fails |
| A tag of another form, such as `v0.4-rc1` or `latest` | Fails |
| An annotated tag | Passes |
| No tags, or no git checkout | Fails |
| The version that `ratchet.json` names, on a copy of this repo, with `release.py`'s own code and no copy of it, against a fake GitHub that holds the tags and releases from before it. First headed `(unreleased)`: `RATCHET.md` says it is not yet released, the README fetches the newest release, the checks pass, and a push and a scheduled run, on the history of `main` in the copy read with `release.main_history` and `release.read_pending`, write nothing and say why. Then given its date, with the README moved to its tag and `generate.py` run: the checks pass, `release.publish` tags the merge and releases it, the next scheduled run writes nothing, the guard passes, and the full suite passes after it. Finding 3 of round 1 of the new approach | Passes |
| While that version is unreleased, a rule changed | Passes |
| After its release, a rule changed without a new version | Fails |
| After its release, a pin moved in `sources.json` | Passes, with no new version. `generate.py` writes only `RATCHET.md` |

**What it does not claim.** It trusts the tags it is given. A tag deleted or moved on the server is outside what it can see: that is a setting of the repository. It does not see whether the text of the first entry, the version not yet released, is right. It does not see whether a dated first entry was released: on a pull request, and on the push of `main` before the release run is done, the tag does not exist yet. That is the release workflow's to see, on its next run and on its schedule. So the command in `README.md` that fetches Ratchet names a tag that may not exist yet: the pull request of a release moves it to the version it dates, and the tag is created by the release run after the merge. For the minutes that run takes, the command fails. If the run is cancelled or fails before it tags, the command fails until a rerun tags, and the daily scheduled run of `release.py` is red each day until then ([PR #50](https://github.com/fabian-von-tiedemann/ratchet/pull/50), round 2, finding 2). Moving the pin in a pull request of its own after the tag exists would close that window, at the cost of a second pull request for each release, and is a question for the maintainer.

## release.py

```sh
python3 checks/release.py notes --repo OWNER/NAME   # print the release text, with no token and no network
python3 checks/release.py publish                   # tag and release, in the release workflow; only report, on a schedule
```

This one checks no rule in a register. It is the script that the release workflow, [release.yml](../.github/workflows/release.yml), runs after the three commands of the job `checks` ([D-2026-11-17-release-on-merge](../decisions/D-2026-11-17-release-on-merge.md), [D-2026-11-17-release-links](../decisions/D-2026-11-17-release-links.md), [D-2026-11-17-release-narrow-claim](../decisions/D-2026-11-17-release-narrow-claim.md), [D-2026-11-17-release-fail-closed](../decisions/D-2026-11-17-release-fail-closed.md)). The workflow holds no logic of its own, so that the logic can be tested. Its tests, in [test_release.py](test_release.py), run with the others and never reach the network: the GitHub API is a function given to the script, and the HTTP client is given a fake opener.

The script reads no Markdown and copies nothing from the changelog. The versions that must already be released come from the history of `main`, read with git, and not from the changelog. It does not try to finish an older version. When anything older is unfinished, the run is red, nothing is written, and the message names the commit whose run the maintainer reruns.

**What it claims, in short** ([D-2026-11-17-release-narrow-claim](../decisions/D-2026-11-17-release-narrow-claim.md), [D-2026-11-17-release-fail-closed](../decisions/D-2026-11-17-release-fail-closed.md)). It catches mistakes in normal operation, and it fails closed. With the history on `main` intact, a run is green only when it has confirmed, from git and from the answers of the GitHub API, that every version that was ever dated on `main`, up to the one in the checkout, has a tag and a published release (a version that `main` only named under a first entry headed `(unreleased)` needs nothing, see below), and, when the first entry of the changelog, the one of the version in the checkout, has a date, that the tag of that version is at this commit or at an earlier commit of it. While that entry is headed `(unreleased)`, the version in the checkout has no tag yet, nothing is written for it, and a run passes once every older version is finished. Every run, whether of a push, by hand or on the schedule, that cannot confirm that is red:

- A scheduled run writes nothing at all.
- A run of a push or by hand writes nothing when it cannot confirm that every older version is finished, or when any check before its writes fails. Its only writes are the tag and the release of the version in `ratchet.json`, made after every check has passed. If it cannot confirm either one, it is red.

The workflow also runs on a schedule, every day, on the head of `main`, also when nothing is merged. While a version is unfinished, the scheduled run is red each day that GitHub starts it (see "What it does not claim").

Naming the version, the commit and the rerun is best effort. The run names them when it has read what is unfinished, and in the one message after the tag. It is red either way. When the API does not answer, or answers with an error such as HTTP 503, or with something that is not JSON or not of the form expected, before the run has read the tags and the releases, the run is red. It writes nothing, and its message may name only the request that failed. An error the script does not expect before any write is not caught. Python exits with 1, so the run is red and names nothing.

That holds through:

- a run that was cancelled or failed, before or after its tag;
- a publication that failed: a refused tag, a release that was not created, an answer lost;
- a changelog that was edited, with an entry taken out or a heading moved out of its form;
- a merged version left without a tag or a release, for any of these reasons or because a waiting run was replaced by a newer one.

It does not stand against someone who changes the runner's git data, such as a graft, a replace ref, a shallow file, an object store of its own or a forged object, nor against someone who deliberately writes a version in an unusual form. Two cheap barriers stand there anyway, and they are not a claim: every version must have one strict form, and a checkout with any of the first four is refused.

**Why that boundary holds.** Nothing reaches `main` but through a pull request, and every commit on it has passed the code owner's approval and the required job `checks` (`ratchet.checks-owner-read`). The ruleset on `main` refuses a force push and a deletion, so a commit on `main` stays as it was approved. Every run of the release workflow starts from a fresh checkout on a runner of GitHub's, so the git data it reads are the ones the checkout wrote, from `main`, and not ones a person left behind. To change the git data or the version on purpose, someone has to get it past that approval, or turn the ruleset off. The review of the change, not the script, is what stands against that.

**What it claims, in detail.**

- **The release text is one fixed line, written in the script.** For version 0.4 of `OWNER/NAME` it is, exactly: `Ratchet 0.4: see [the changelog entry](https://github.com/OWNER/NAME/blob/v0.4/CHANGELOG.md) and [the files at this tag](https://github.com/OWNER/NAME/tree/v0.4)`. Nothing else is in it. No byte of `CHANGELOG.md` reaches the release, so the release cannot say something other than the entry: it says where the entry is. The links name the file and the tree at the tag, with no anchor, so they do not depend on how GitHub makes the anchor of a heading.
- **Every version has one form.** Each version the script reads must match `^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`: ASCII digits, no leading zero, nothing before or after. That holds for `ratchet.json` in the checkout, `ratchet.json` at each commit on `main`, each tag under `refs/tags/v` (`v` and the version), and each heading of a version in the changelog. Anything else fails the run, and the message names the value, as JSON in ASCII, and where it came from: the checkout, the commit, the tag, or the line of the changelog. Versions are compared only as pairs of integers, so 0.10 is newer than 0.9, and `00.4` never stands beside `0.4`.
- **From the changelog it reads only which versions have an entry.** It reads the version from `ratchet.json` at the checked-out commit, strictly, and `CHANGELOG.md` as strict UTF-8. CRLF is read as LF, and the text is split at LF. A line is the heading of a version only when the whole line matches `^## ([0-9]+\.[0-9]+) \(([0-9]{4}-[0-9]{2}-[0-9]{2})\)\Z`: `[0-9]`, because `\d` in Python matches the digits of every script, and `\Z`, because `$` also matches before a final LF. Every other line is passed over, whatever a reader makes of it.
- **The version has an entry, and nothing newer has one.** The run fails before any request when no line names the version in `ratchet.json`, or when a line names a newer version.
- **A checkout that swaps objects or parents is refused.** Before it reads any history, the run fails when the checkout has `.git/info/grafts`, a ref under `refs/replace/`, loose or packed, a `.git/shallow` file, even an empty one, or a `.git/objects/info/alternates` file, even an empty one. git reads a graft as the parents of a commit, a replace ref as another object, a shallow file as the end of the history, and an alternate store as the source of an object the checkout lacks, without checking its hash: each changes what is read, and the tests show it. Beside the refusal, git runs with `GIT_NO_REPLACE_OBJECTS=1`, `--no-replace-objects` and `GIT_GRAFT_FILE` set to an empty file in a directory the script makes for each call, so that the reading ignores grafts and replace refs anyway. A fresh checkout on GitHub has none of these.
- **The older versions are the ones `main` has had.** Before any request, it reads with git every commit on the first-parent history of `GITHUB_SHA` (`git rev-list --first-parent`) and the bytes of `ratchet.json` in each (`git cat-file`), and reads each as strictly as `registry.py` reads a data file: UTF-8, no field twice, no NaN, and a `version` of the form `MAJOR.MINOR`. Every commit is read, not only those git reports as changing the file. The run fails when the checkout is shallow, when it is not at `GITHUB_SHA`, when `ratchet.json` at `GITHUB_SHA` names another version than the checkout, when a commit names a version newer than the one being released, or when the file is missing at a commit after an earlier commit held it. Commits from before `ratchet.json` existed name no version. git runs with no `GIT_` variable of the environment, no system or global config, no replace refs and no graft file of the checkout, and it does not look for a repository above the checkout.
- **Every tag has an entry, and every older version is finished.** Before any write, it lists the tags and the releases. A tag `vMAJOR.MINOR` up to this version with no line of its own fails the run, and so does a tag under `refs/tags/v` of another form, which is named. Each version that was dated on `main` and that is older than the one being released must have a tag and a published release, not a draft. Which versions those are is under "The versions that must be released" below. 0.1 needs only its tag, because it was tagged before Ratchet published releases (`BEFORE_RELEASES` in the script). If any is missing, the run fails, names each version, what it lacks and the commit whose run to rerun, and writes nothing. Tags and releases of versions newer than the one in `ratchet.json` are ignored, so that a rerun for 0.4 does not trip over a `v0.5`.
- **An unreleased first entry publishes nothing** ([D-2026-11-19-batched-releases](../decisions/D-2026-11-19-batched-releases.md)). A line `## MAJOR.MINOR (unreleased)`, matched as a whole line as the dated heading is, is an entry of a version that is not released. When the first entry is headed so, for the version in `ratchet.json`, the run reads the tags and the releases, fails as before when an older version is not finished, and otherwise passes, writes nothing and says: `Ratchet <version> is not released: its entry in CHANGELOG.md is headed "(unreleased)". Every older version is finished. Nothing was written.` That holds for a push, a run by hand and a scheduled run. It fails and writes nothing when that version already has a tag or a release, when an entry after the first is headed `(unreleased)`, when a version has two headings, and when the checkout and its commit on `main` disagree on whether the entry is unreleased. A heading of any other form, such as `(Unreleased)`, is no entry at all, so the run fails as for a missing entry. The release is the push of the commit that gives the entry its date.
- **The versions that must be released are the ones `main` has named with a date.** Beside `ratchet.json`, the run reads with git the `CHANGELOG.md` of every commit on the first-parent history (`release.read_pending`), as strict UTF-8, and only its headings. A commit is pending when its first entry is the one exact unreleased heading for the version its `ratchet.json` names. A version must be released once a commit on `main` names it and is not pending, so a version merged with a date cannot be hidden by a later pull request, as before. A version that `main` only named as pending needs nothing. A version that a commit on `main` named and that was not pending must be released also when a later commit is pending for it again, with `(unreleased)` put back: the run of that later commit, on a push and on a schedule, fails, writes nothing and says `Ratchet <version> is not finished: commit <sha> on main gave its entry in CHANGELOG.md a date, and at commit <head> it is headed "(unreleased)" again.`, with the rerun. The commit that a message names for a rerun is the first commit on `main` that names the version and is not pending, since a rerun of a pending commit publishes nothing. A commit whose changelog is missing, or holds the heading in another form, counts as not pending: its version must be released. A changelog that is not UTF-8 at a commit on `main` fails the run and names the commit.
- **A release is made only from `main`.** `GITHUB_REF` must be `refs/heads/main`, or the run fails before any request. A scheduled run is on the default branch, `main`, and passes this check like the others.
- **The event is one of three.** `GITHUB_EVENT_NAME` must be exactly `push`, `workflow_dispatch` or `schedule`, or the run fails before any request. A push and a run by hand write as described below.
- **A scheduled run writes nothing, and is red on what is unfinished.** It runs the same checks on the head of `main` and reads the same tags and releases. Its API function sends a `GET` and refuses every other request, which is not sent, whatever the logic asks for. When a read fails, it is red as any run is, and its message may name only the request that failed. When the reads are answered and a run of a push would write, it fails instead: for a version with no tag, the message names the version, the head commit, the first commit on `main` whose `ratchet.json` names it, and the rerun; for a tag at the head with no published release, it names the version, the commit the tag points at, and that the release is missing. Every other fault fails as in a run of a push, and writes nothing. On a state where every version is finished, it passes.
- **Why a scheduled run only reports.** It could also create the release when the tag is at the head of `main`, since that write would be the same as a rerun's. It does not, because that is the safer choice: every write stays tied to an event that a person caused, the push of an approved commit, a rerun or a run by hand. A run that nobody started then never writes a tag or a release, and an error in its logic can at most turn a run red. The cost is one click: the maintainer reruns the run that the message names.
- **Nothing is written before every check has passed.** The writes are two, in this order: the tag, then the release.
- **The tag is created at this commit, or not at all.** It is created with `POST /repos/OWNER/NAME/git/refs`, which refuses a ref that exists. Then the release is created for that tag, and the tag is read back. The run fails when the answer to the creation or the tag read back points anywhere but `GITHUB_SHA`.
- **Every failure after the tag ends in one message.** Once the tag may exist, a failure of any kind, whether no answer, an error the script does not expect, an HTTP error, an answer that is not JSON or an answer of the wrong form, gives one message. It says what failed, then names the version and the commit, says what is missing, and gives the rerun. There are four states, one form each, in `release.py`: the creation of the tag failed in a way that may have written it (`TAG_MAYBE`), the answer to the creation does not confirm the commit (`TAG_ELSEWHERE`), the tag is at the commit and the release is missing or not confirmed (`RELEASE_MISSING`), and the release was created and the tag was not confirmed (`TAG_UNCONFIRMED`). The creation of the release and the read-back are in one `try` that catches every `Exception`. An error the script does not expect is named by its type and the request, and its text is not shown. Only HTTP 422 on the creation of the tag, a ref that exists, still says that nothing was written. A cancelled run is stopped by GitHub and prints nothing. The next scheduled run is red on it, and names it when the API answers.
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

- **The token.** Only `GITHUB_TOKEN` from the environment is used. It is sent in one header, to `https://api.github.com` only, to paths under `/repos/OWNER/NAME/`, and a redirect is not followed. It is never printed: it is taken out of every message. An error names the method, the path and the status. Nothing from the body of an answer is read for an error or printed, except a version that has matched `MAJOR.MINOR` and a tag name of another form, which is written as JSON in ASCII and cut at 60 characters.
- **The workflow keeps its reviewed form.** The tests read the workflow as strict UTF-8, read CRLF as LF, and refuse every other control character but the tab and LF, among them a lone CR and NEL, and U+2028 and U+2029: a YAML parser may break a line there where the comparison does not. Then they compare the workflow, without its comments, line for line with the reviewed form, and test each part the design leans on. A line is blank, or a comment, by ASCII rules only: a line that holds a tab or a space that is not ASCII before `#` is kept, and then fails the comparison. The checkout has `fetch-depth: 0`, so that the history of `main` is there to read.

**Against which threat.** Mistakes in normal operation, as above:

- A release that says something other than the entry that was approved. Two review rounds found that a script reading free Markdown could not know what a renderer will show ([D-2026-11-16-strict-forms](../decisions/D-2026-11-16-strict-forms.md)). Now no text is copied, so there is nothing to differ.
- A version that is merged and left unreleased, or made impossible to release, with no red run: a run that fails or is cancelled after it tags, a waiting run replaced in the concurrency group by a newer one, or a later pull request that takes the version's heading out of the changelog.
- A release attached to a tag at another commit than the one approved, because the tag appeared between a check and a write.
- A version hard-coded in the script instead of read from `ratchet.json`.
- A version collected under an unreleased entry that is published before its pull request of release, or a version merged with a date that is then never released because the changelog says it was unreleased. Only the exact heading, as the first entry, holds a version back, and only at commits whose own changelog says so ([D-2026-11-19-batched-releases](../decisions/D-2026-11-19-batched-releases.md)). Once a commit on `main` has dated a version, a later commit that heads it `(unreleased)` again does not take the duty away: the run fails and names the commit that dated it (PR #50, round 2, finding 1).
- The token sent somewhere else, or shown in a log.

A version written in an odd form by mistake, such as `0.04`, fails the run and is named. The threats that are out of scope are under "What it does not claim".

**Why an edit of the changelog can no longer hide a version.** The versions that must be released are read from commits already on `main`. A pull request adds a commit on top of them and cannot change one of them: the ruleset on `main` refuses a force-push and a deletion, and git names a commit by the hash of its content and of its parents. The first-parent line is the line of `main` itself: a commit on a branch that was merged in is not on it, and the merge commit is. What the script still reads from the changelog can only make a run fail: the version must have an entry, no entry may be newer, and every tag up to the version must have one. A heading taken out of the exact form, or an entry taken out, therefore turns the run red or changes nothing. It never lets a version on `main` through without its tag and its release.

**Why the rerun of this version finishes its release.** A rerun that finds the tag of the version being released at its own `GITHUB_SHA`, with no release, creates the release. This is the version's own run, not an older one. It is safe: the tag is on the commit that was approved, where it would be anyway, so nothing has to move; the text is the fixed line for that version; every older version has passed the check above; and a release created before an answer was lost is found, so no second one is made. Failing there instead would leave no way through the workflow to finish the version.

**When a run is red because something is unfinished.** The message names each version and what it lacks. Then, in this order:

1. Under Actions, open the workflow `release` and find the run of the commit that the message names. If the tag exists, that is the commit the tag points at. It may be a later commit than the first one with the version, when the run of the first was replaced and a later run made the tag. A run of any other commit fails on that tag and writes nothing. If the tag is missing, it is the first commit on `main` at which `ratchet.json` names the version. Choose "Re-run all jobs". It tags that commit if the tag is missing, and creates the release. It ignores the newer versions.
2. When that run is green, rerun the red run, with "Re-run all jobs".
3. If the run of step 1 cannot be rerun (GitHub allows a rerun for 30 days, and a run may never have started), and the head of `main` still has that version in `ratchet.json` and its tag is missing or is at the head, start the workflow by hand: Actions → `release` → "Run workflow", on `main`. It takes no input, runs the same three checks, and releases what `ratchet.json` names at the head of `main`. On any other branch it fails before any request.
4. If neither is possible, the maintainer makes the release by hand for the tag that exists, or the tag by hand on the first commit with the version, with the line that `python3 checks/release.py notes --repo OWNER/NAME` prints at that commit. The workflow never does this.

**Why the concurrency group stays.** It keeps one release run at a time, so that two runs never write at once. A waiting run can still be replaced by a newer one, and the replaced run shows as cancelled. That cannot lose a version without a red run: the newer run checks every older version that `main` has had, and fails and names one without a tag or a published release. The last run in the queue is never replaced. A run that was cancelled can be rerun for its commit, and then the newer one.

A scheduled run is in the same group, `release`, with no expression, so it never runs beside a run that writes. It cannot read a state halfway through a run of a push. When it replaces a waiting run of a push, it is red, and when the API answers it names the version that the replaced run would have released, with no tag or with a tag and no release. When a run of a push replaces a waiting scheduled run, the run of the push does the work, and the next day's scheduled run reads its result.

**The cases.** Each is a test in [test_release.py](test_release.py).

| Case | Result |
|---|---|
| The release text for 0.4 of `owner/name`, and for 12.30 | Exactly the fixed line, with no `#` in it |
| A changelog with a lone carriage return before a second heading, lines of a no-break space, an em space and an ideographic space, a link definition and a comment | The published body is the fixed line, and holds none of those bytes. `publish` and `notes` from a checkout give the same |
| A line of the exact form | Names a version |
| Seventeen lines that are not of the exact form: a space or a tab before or inside it, `v0.4`, no date, `###`, `#`, in a block quote or a list item, after a lone carriage return, a no-break space before or after it, digits of another script, a full-width digit, U+2028 after it | Passed over |
| CRLF | Read as LF |
| A line of the exact form in a code block | Counted. See the known limits |
| No line for the version in `ratchet.json`, also when the heading is in one of the seventeen other forms | Fails before any request |
| A tag for 0.2 and no line for it, also when its heading is in one of the other forms | Fails, writes nothing |
| Bytes that are not UTF-8 | Fails |
| Today's `CHANGELOG.md` | Every version from the one in `ratchet.json` down to 0.1 |
| A new version | The tag, then the release, then the tag read back |
| An older version without a tag, with a tag and no release, with only a draft, also when nothing is to be released | Fails, names it and what it lacks, writes nothing |
| 0.1 with its tag and no release, 0.1 with no tag | Passes; fails |
| 0.4 merged and never tagged, then 0.5 in a real git history, with 0.4's heading after a space, in a list item, with two spaces, or taken out | Fails, names 0.4 and the first commit with it, writes nothing. With 0.4 released, the same history releases 0.5 |
| A history with commits before `ratchet.json`, and a commit that changes only the changelog | Every commit that holds the file, newest first |
| A version only on a branch merged into `main` with `-s ours` | Not counted |
| A merge commit that raises the version | Named as the first commit with it |
| A shallow clone, a directory that is not a repository, a checkout not at `GITHUB_SHA` | Fails |
| `ratchet.json` at an earlier commit with a field twice, NaN, bytes that are not UTF-8, a BOM, cut short, a version `0.3.1`, digits of another script, a number, no version, not an object | Fails, names the commit, and the value when there is one |
| A version `00.4`, `0.04`, `+0.4`, ` 0.4`, `0.4 ` or `٠.٤` in the checkout, at a commit on `main`, or as a tag | Fails, names the value and where it came from: the checkout (also for `notes`), the commit, or the tag. Before any request, or writes nothing |
| The history 0.3, then 0.4, never tagged, then `00.4` | Fails on `00.4` and writes nothing |
| A heading `## 00.4 (…)` or `## 0.04 (…)` | Fails, names the line |
| 0.9, then 0.10, in a real git history | With 0.9 released, releases 0.10. With 0.9 unfinished, fails and names 0.9. Versions compare as pairs of integers |
| `.git/info/grafts` that makes 0.3 the parent of 0.5 | git reads 0.4 out of the history; the run refuses the file before any request. The reading ignores the file, and `GIT_GRAFT_FILE` from the environment |
| A replace ref that swaps the commit of 0.4, loose or packed | The reading ignores it; the run refuses it and names the ref |
| `.git/shallow` naming the commit of 0.4 in a full clone, or empty | git stops the history at 0.4; the run refuses it |
| `.git/objects/info/alternates` naming a store with other bytes under the name of a blob the checkout lacks, or empty | git reads the other bytes, 0.4 is read as 0.3; the run refuses it |
| A tag named with the token | Fails; the token is not in the output |
| `ratchet.json` removed from `main` and added again | Fails, names both commits |
| A commit on `main` that names a newer version | Fails before any request |
| A checkout whose `ratchet.json` names another version than its commit | Fails before any request |
| `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` and `GIT_REPLACE_REF_BASE` set to another repository | Change nothing |
| An older version without a tag | The message names the first commit on `main` whose `ratchet.json` names it |
| An older version whose tag is at a later commit than the first with it | The message names the commit of the tag, not the first. That rerun finishes it, and then the newer one releases |
| An older version whose tag is not a plain tag of a commit | The message says to look at it by hand |
| This version tagged at another commit, with no published release | The message names the commit of the tag |
| A newer tag, a newer annotated tag, a newer draft | Ignored |
| A tag up to this version without an entry, a tag that is not a version | Fails, writes nothing |
| 0.4 fails after its tag, then 0.5 is merged | The run for 0.5 fails, names 0.4 and writes nothing. The rerun for 0.4 creates only its release. The rerun for 0.5 then releases 0.5 |
| A rerun for 0.4 when `v0.5` exists | Creates the release for 0.4 |
| A run cancelled right after its tag | A later run on 0.4 and the run for 0.5 fail and write nothing. The rerun of the cancelled run finishes it |
| A run cancelled right after its tag, and nothing merged after it | The next scheduled run fails, names 0.4, the commit the tag points at and the missing release, and writes nothing. After the rerun, the scheduled run passes and writes nothing |
| A version with no tag, at its own commit or at a later commit of `main` that keeps it, in a scheduled run | Fails, names the version, the head and the first commit with it, writes nothing |
| A finished state in a scheduled run: the tag at the head, or at an earlier commit, with its release | Passes, writes nothing |
| An unfinished older version, a draft, a tag at another commit, a release with no tag, in a scheduled run | Fails as in a run of a push, writes nothing |
| A read of a scheduled run fails with HTTP 503, 500 or 502, no answer, an answer that is not JSON or one of the wrong form, at the list of tags, the first page of releases or the comparison, with 0.4 cancelled after its tag, never tagged, or released at an earlier commit | Red, sends only `GET`, writes nothing. The message of an HTTP error starts with the request and its status. An error the script does not expect is not caught. When the API answers again, the run names 0.4, or passes on the finished state |
| `publish` told to report, in each case where a push would write | Fails, says that a scheduled run writes nothing, writes nothing |
| The API of a scheduled run, asked for a `POST`, `PATCH`, `PUT`, `DELETE` or a `get` in lower case, also through `main()` with a `publish` that writes anyway | Not sent |
| A push and a run by hand | Tag and release |
| `GITHUB_EVENT_NAME` missing, empty, `pull_request`, `pull_request_target`, `release`, `Schedule`, or `schedule` with a line feed | Fails before any request |
| A scheduled run with `GITHUB_REF` not `main`, or missing | Fails before any request |
| The publication fails with no answer, an error the script does not expect, HTTP 500, an answer that is not JSON or one of the wrong form, after a new tag and on a rerun with the tag | The one message: the version, the commit of the tag, the release missing or not confirmed, the rerun. Then the scheduled run names it, and the rerun creates only the release |
| The publication reaches GitHub and its answer is lost: no answer, an unexpected error, HTTP 500 | The one message. The scheduled run then passes, and the rerun writes nothing |
| The read-back of the tag fails in each of the five ways | The one message: the release was created, the tag not confirmed at the commit, the rerun. The rerun writes nothing |
| The creation of the tag fails with no answer, before or after it reaches GitHub, an unexpected error, HTTP 500, or an answer that is not JSON | The one message: the tag may have been created at the commit, no release, the rerun. The rerun finishes it |
| The answer to the creation of the tag is of the wrong form | The one message: the tag was created, no release, look at it by hand, then the rerun |
| `KeyError`, `TypeError`, `ValueError`, `AttributeError`, `IndexError`, `OSError` or a `ReleaseError` raised by the API at each request after the tag | The one message, each time |
| No answer to a `GET` before the tag | Fails, names the request, says that nothing was written |
| Each row of the table above | As the table says |
| A refused ref creation | Fails, writes nothing more |
| An answer to the creation that puts the tag elsewhere | Fails, creates no release |
| A tag read back at another commit | Fails |
| An API error at each of the four requests | Fails with method, path and status, writes nothing more |
| An answer of the wrong form | Fails, writes nothing |
| An answer to the publication that is a draft, has `draft` null, names another tag or none, is a list, or is empty | Fails, and the tag is not read back |
| The release of 0.3 after 100 releases, or between 50 and 50; 98, 99, 100 and 201 releases | Found. Pages are read until one holds fewer than 100 |
| This version's release on the second page | Found, nothing written |
| A list of releases with no end | Fails after 100 pages, writes nothing |
| The version is not the newest entry, or has none | Fails before any request |
| The first entry headed `## 0.4 (unreleased)`, with every older version finished, on a push and on a schedule | Passes, says that 0.4 is not released, writes nothing |
| The same, with 0.3 tagged and not released | Fails, names 0.3, writes nothing |
| The same, with a tag `v0.4` at another commit or at this one with its release, or with a release `v0.4` and no tag | Fails, writes nothing |
| An entry headed `(unreleased)` after the first, or a version with two headings | Fails before any request, names the line or the version |
| `## 0.4 (Unreleased)`, a space or a no-break space after it, no parentheses, no space before them, one left open, `## Unreleased`, two spaces, more words | No entry: fails before any request |
| The checkout heads 0.4 `(unreleased)` and its commit does not, or the other way round | Fails before any request |
| In a real git history: 0.4 unreleased twice, then dated | Both unreleased commits are pending. The push of the dated one tags it and releases it |
| In a real git history: a push of 0.4 unreleased, and the scheduled run after it | Pass, send only `GET`, write nothing |
| 0.4 unreleased, then dated, then a later commit, with no tag, in a scheduled run | Fails, names the dated commit as the one to rerun |
| 0.4 unreleased, then dated and never released, then 0.5 unreleased, on a push and on a schedule | Fails, names 0.4 and the dated commit |
| 0.4 only ever unreleased, then 0.5 dated | 0.4 needs nothing. 0.5 is tagged and released |
| 0.4 unreleased, then dated with its run cancelled before the tag, then headed `(unreleased)` again, on a push and on a schedule | Fails, names the dated commit and the head, writes nothing. Round 2, finding 1 |
| The same, then the late run of the dated commit | Tags and releases 0.4 at the dated commit. The head then fails, since a released version is headed `(unreleased)`, until a commit dates it again, which passes as released at an earlier commit |
| 0.4 dated, its late run releases it, then headed `(unreleased)` again | Fails on a push and on a schedule, writes nothing |
| 0.4 dated, unreleased, dated again, unreleased again | Fails, names the first commit that dated it |
| A commit on `main` whose changelog heads 0.4 `(Unreleased)`, with a space after, or with no date | Not pending: 0.4 must be released, and is named |
| A changelog at a commit on `main` that is not UTF-8 | Fails, names the commit and the byte |
| `ratchet.json` in another checkout names 9.7 | `publish` tags `v9.7` with the fixed line for 9.7, and `notes` prints it |
| The token in five runs, with an answer that holds it | Never in the output, and sent only to `api.github.com` |
| No token, a repository, a commit or a branch not of its form | Fails before any request |
| A path outside the repository, a redirect | Not sent, not followed |
| `notes` | Needs no token and no network, and prints the fixed line |
| `.github/workflows/release.yml` | Runs on a push to `main`, on `workflow_dispatch` with no input and on a schedule, with read-only permissions but on its job, the checkout pinned by commit, no expression in a script, and the three commands before the script |
| The concurrency group `release`, with `cancel-in-progress: false` | Exactly that, once |
| The permissions | `contents: read` at the top and `contents: write` on the job, and no other |
| The triggers | A push to `main`, `workflow_dispatch` and `schedule`, and no `if:` that could skip the job |
| The schedule | One cron line, `23 4 * * *`: a fixed minute and hour, and every day of the month, every month and every day of the week. A weekly line fails |
| `timeout-minutes: 5` on the job | Exactly that, once |
| The steps | The three checks in order, then the script. No `continue-on-error`, `always()` or `failure()` |
| The whole workflow, without its comments | The reviewed form line for line, and nothing else. The checkout may move to another pinned commit |
| A no-break space, an em space, an ideographic space, U+2028 or a tab before `#`, or alone on a line | Kept as code, not read as a comment or a blank line |
| A lone CR, NUL, backspace, VT, FF, ESC, U+001F, DEL, NEL, U+009F, U+2028 or U+2029 after a comment and before `if: false`, and bytes that are not UTF-8 | The workflow is not read, and the test fails |
| The workflow with CRLF, a tab in it | Read as with LF; the tab is kept as code |
| The checkout | `fetch-depth: 0` and `persist-credentials: false`, and no filter or sparse checkout |

**What it does not claim.**

- A line of the exact form counts wherever it stands, also where a renderer does not show it as a heading: in a code block, in an HTML comment. Then the script may take a version for one that has an entry when a reader sees none. No text is copied, so such a line can no longer put text into a release. The most it can do is let a tag or a release through for a version whose entry a reader cannot see, in a pull request the maintainer has approved.
- A heading a renderer shows in another form, for example after a space or in a list item, is not counted. That fails the run, and never releases anything.
- It does not check that the entry says anything, that its date is a real date, or that the entries stand in any order.
- The release page shows no text of the entry. A reader follows the link. The link opens `CHANGELOG.md` at the tag at its top, not at the entry for the version.
- It does not see branch protection or tag protection. Who may push a tag by hand is a setting of the repository.
- It does not read the release text back after it is published.
- It does not make GitHub start a scheduled run. GitHub may start one late, and at times of high load it may drop one. In a public repository, GitHub turns off a scheduled workflow after 60 days with no activity in the repository, and it stays off until someone turns it on again. Within those limits, while a version is unfinished, the scheduled run is red each day. A cancelled run prints nothing itself. The next run is red on it.
- It does not promise to name the unfinished version ([D-2026-11-17-release-fail-closed](../decisions/D-2026-11-17-release-fail-closed.md)). When the GitHub API is down, or answers a read with an error such as HTTP 503, or with something that is not JSON or not of the form expected, the run is red and writes nothing. Its message may name only the request that failed, and not the version, the commit or the rerun. As long as the API fails that way on the scheduled runs, a version can stay unfinished with no run that names it. Each of those runs is still red.
- A scheduled run has the same job, and so the same token with `contents: write`, as a run of a push. What keeps it to reading is the script, which sends nothing but a `GET` on a schedule, not the token. A second job with a read-only token would need an `if:` on the event, and the workflow has none.
- A version that is collected under an unreleased entry can be dropped on purpose, by a later pull request that raises `ratchet.json` past it before the entry has a date. That is a choice made in a pull request, as a skipped version is. Once a commit on `main` has dated the entry, the version must be released, whatever the changelog says later.
- A version may be skipped on purpose, from 0.4 to 0.6, by a pull request that never puts 0.5 in `ratchet.json` on `main`. That is a choice made in a pull request, not a version lost. A version that a pull request names only in its own commits, and that `main` never names, is not counted.
- Versions from before `ratchet.json` was on `main`, 0.1 and 0.2, are not in that history. Both were tagged by hand. The script checks them only as tags with an entry.
- It does not stand against someone who changes the runner's git data ([D-2026-11-17-release-narrow-claim](../decisions/D-2026-11-17-release-narrow-claim.md)). It refuses grafts, replace refs, a shallow file and alternates, and nothing more: a forged object written into the checkout's own store, a changed `HEAD` or ref, or a changed `git` binary are not looked for. On a fresh checkout on GitHub there is none, for the reasons under "Why that boundary holds".
- It does not stand against someone who deliberately writes a version in an unusual form. It refuses every form but one, so such a version makes the run red; a version skipped on purpose, as below, is still possible.
- It trusts the history of `main` as the ruleset keeps it. An administrator who turns the ruleset off and force-pushes `main` could take a version out of that history.
- `generate.py` and `check_register.py` read `version` in `ratchet.json` with the older form `^[0-9]+\.[0-9]+$`, so they accept `00.4`. Only the release script refuses it. Making `registry.py` as strict is a proposal (P) in the decision, not done here.
- A workflow file on another branch can be changed by anyone who can push to it. The check of `GITHUB_REF` stops a mistake, not a change to the workflow or the script.

## The budget

`ratchet.json` holds `experimental_cap`: the most rules outside the core there may be ([D-2026-11-17-pull-and-budget](../decisions/D-2026-11-17-pull-and-budget.md)). It is 25: there were 20 experimental rules in `ratchet.json` at the commit on `main` that added that decision, and the decision put the cap at that number plus five.

**What it claims.** Every check that reads `ratchet.json` through `registry.load` fails when there are more experimental rules than the cap, so `generate.py --check` is red and nothing is generated. It fails the same way when the cap is missing, stands twice, or is anything but a whole number from 0: text, `true`, `2.0` or a negative number. The count of rules, in the README, `RATCHET.md`, `SELF-IMPROVEMENT.md` and the first entry of the changelog, states the cap.

**Against which threat.** Ratchet grows a rule at a time until no one reads it. With the cap, a new experimental rule replaces, merges or removes one, or a decision raises the cap.

**What it does not claim.** It does not count the core, which is frozen, and it does not judge whether a rule is worth its place. A PR can raise the cap in the same change that adds a rule. That is a change to `ratchet.json`, which the maintainer reads before it is merged (`ratchet.checks-owner-read`), and raising the cap is a decision.

| Fixture | What is wrong | Result |
|---|---|---|
| `budget/at-cap.json` | Nothing. Two experimental rules under a cap of 2. | Passes |
| `budget/over-cap.json` | Two experimental rules under a cap of 1. | Fails |
| `budget/no-cap.json` | No cap. | Fails |
| `budget/cap-text.json`, `budget/cap-true.json`, `budget/cap-fraction.json`, `budget/cap-negative.json` | A cap that is text, `true`, `2.0` or `-1`. | Fails |
| `budget/cap-twice.json` | The cap twice, and the higher one would win. | Fails |

The tests are in [test_budget.py](test_budget.py). Each runs `generate.py --check` on a directory that holds only the fixture as `ratchet.json`, and the data file fails before anything else is read. Two more run on a copy of this repo: the cap in `ratchet.json` is 25, and one experimental rule over it fails the check.

## The age of an experimental rule

Every experimental rule in `ratchet.json` names `since`, the version it entered Ratchet, and may name `kept_by`, the id of a decision that kept it once more ([D-2026-11-19-one-point-oh](../decisions/D-2026-11-19-one-point-oh.md), choice 4). How the age is counted is in [SELF-IMPROVEMENT.md](../SELF-IMPROVEMENT.md#the-age-of-an-experimental-rule).

**What it claims.** `generate.py --check` fails, with one line per rule that names it, when an experimental rule has stood through three releases and 60 days with no decision. The releases are the versions with a date in the changelog after `since`, and the days run from the date of `since` to the date of the newest of them. A rule with `kept_by` stands one age more, counted the same way from the release at which it first stood too long, and then fails with only three outcomes: move it into the core, merge it, or remove it. The date of the decision does not move the count, so naming a later decision in `kept_by` keeps the rule no longer: a rule is kept once. The age moves only when a release is dated, so the check first fails in the pull request of a release, and never on a day with no change. Every check that reads `ratchet.json` through `registry.load` fails when an experimental rule has no `since`, when a core rule has `since` or `kept_by`, when `since` is not a version, when `kept_by` is not the id of a decision with a date that exists, or names a decision with no file in `decisions/`, and, as before, on a field it does not know or a field twice. `generate.py --check` also fails when `since` does not name a version with an entry with a date in the changelog, or the version of the file, so a version later than the file's fails there. It fails, naming both entries, when a release is dated before the version before it, since the age is measured at the newest version, and a year mistyped there would hide every rule. Two versions may have the same date.

**Against which threat.** A mistake in the bookkeeping of rules: an experimental rule that lingers release after release with no one deciding on it, and a field misspelled so that the reader passes over it.

**What it does not claim.** It does not see whether `since` is true. It was read from the tags once, for 0.10, and a released `ratchet.json` cannot change after its tag (`released_text.py`), but between two releases a pull request can change it, as it can raise the cap, and the maintainer reads it (`ratchet.checks-owner-read`). A check that it stays as it was at the last tag is issue #74. It does not judge the decision in `kept_by`, only that it exists. A rule removed and added again under another key starts a new age, which the maintainer reads in the pull request. It reads no clock: a rule that has stood long since the last release is not caught until the next one is dated. The check passes today, because every tag is from 2026-11-16 to 2026-11-19.

| Fixture | What is wrong | Result |
|---|---|---|
| `age/ratchet.json` with `age/CHANGELOG.md` | One rule since a version three releases and 60 days before the newest, one with two releases and 60 days, two of the same age as the first and kept by a decision, one dated between the releases and one before the first, one that entered in the version not yet released | Fails, naming only the first |
| `age/ratchet.json` with `age/CHANGELOG-day-59.md` | The same, with the newest release a day earlier: 59 days | Passes |
| `age/ratchet.json` with `age/CHANGELOG-kept-out.md` | Three releases more, the newest 60 days after the release at which the kept rules first stood too long | Fails, naming the two kept rules too, with only move, merge or remove. With two releases more, or 59 days, the kept rules pass |
| `age/second-keep.json` with `age/CHANGELOG-kept-out.md`, and the decision of one kept rule named for the other in the test | A kept rule whose keep has run out names a second, later decision in `kept_by` | Fails, as with the first decision |
| `age/CHANGELOG-date-backwards.md`, and a copy of this repo with 0.9 dated 2026-01-16 | A release dated before the version before it, a year mistyped, which leaves the age check silent | Fails, naming both entries |
| `age/no-entry.json`, and `age/ratchet.json` with `since` set to 9.10 in the test | `since` names a version with no entry in the changelog, or one later than the version of the file | Fails |
| `age/form/since-missing.json` | An experimental rule with no `since` | Fails. An older `ratchet.json`, which `upgrade.py` reads, may lack it |
| `age/form/since-on-core.json`, `age/form/kept-by-on-core.json` | A core rule with `since` or `kept_by` | Fails |
| `age/form/since-not-a-version.json`, `age/form/since-number.json` | `since` is `9.8.1` or a number | Fails |
| `age/form/kept-by-not-an-id.json`, `age/form/kept-by-no-such-date.json`, `age/form/kept-by-no-file.json` | `kept_by` is not the id of a decision, names 2026-02-30, or names a decision with no file | Fails |
| `age/form/kept-by-misspelled.json`, `age/form/since-twice.json` | `keptby` in place of `kept_by`, and `since` twice | Fails |
| This repo, and a copy with 0.9 dated 2027-01-15 or 2027-01-14 | 60 days after 0.2, and 59 | Passes today. Fails at 60 days, naming the twenty rules since 0.2 and no other, and passes at 59 |

The tests are in [test_age.py](test_age.py). The faults of form run `generate.py --check` on a directory that holds only the fixture as `ratchet.json`, as the budget does. The age is tested on `registry.age_problems`, with the dates that `generate.release_dates` reads from the fixture's changelog, and on a copy of this repo.

## The issue form

A proposal starts as an issue with the form [proposal.yml](../.github/ISSUE_TEMPLATE/proposal.yml), which asks for the five fields of [D-2026-11-17-pull-and-budget](../decisions/D-2026-11-17-pull-and-budget.md): what happened, the failure class, the ratchet, whether it would apply in other projects, and the primary source. See [CONTRIBUTING.md](../CONTRIBUTING.md). The form is a test of this repo, not a reference check.

**What it claims.** The form has exactly these five fields, in this order, each a text area marked required, and it gives an issue opened with it the one label `proposal`. GitHub reads the form as YAML, and the standard library has no YAML parser, so the test reads one fixed form line by line and fails on every line outside it: a top of `name`, `description`, `labels` and `body`, then seven lines per field in a fixed order and indentation. A value is one plain line that starts with a capital letter and holds only letters, digits, spaces and `,.;()'?-`, and is not a word that YAML 1.1 reads as true, false or null. The labels line is exactly `labels: [proposal]`. Any YAML parser reads such a file the same way, so what the test reads is what GitHub reads.

**Against which threat.** A field is dropped, renamed or made optional, and proposals arrive without what is needed to judge them. Or the label is dropped or changed, and proposals are not found under it. Or the form is written in a way of YAML that the test would read differently from GitHub.

**What it does not claim.** It does not claim that GitHub accepts the form or shows it, or that the label `proposal` exists in the repo, without which GitHub adds no label: that is seen on GitHub once the form is on `main`. It does not stop an issue opened without the form, from the blank issue or through the API.

| Case | Result |
|---|---|
| The form as it stands | Passes |
| A field left out, a field twice, a field renamed or relabeled | Fails |
| A field not required, with no `validations`, cut short at the end, or of another type than `textarea` | Fails |
| A value with a colon, quoted, a block scalar, or `Yes` | Fails |
| The labels line left out or twice, a different label, a second label, the labels as a block list or as a string, the label quoted | Fails |
| A comment, a key the test does not know, a line indented one more, a trailing space | Fails |
| A tab, a carriage return, a letter that is not ASCII, no final newline | Fails |

The cases are in [test_issue_form.py](test_issue_form.py). Each is the form with one change, so they follow the form when it changes.

## The landing page

[docs/index.html](../docs/index.html) is the landing page. GitHub Pages serves it from `docs/` on `main`, as the files stand, with no build step and no workflow: `docs/.nojekyll` tells Pages not to run Jekyll. It goes live when the maintainer sets Settings, Pages, "Deploy from a branch", `main` and `/docs`, a setting of the repository. To see it before then, open the file: `open docs/index.html` on macOS, or any browser. The page is a test of this repo, not a reference check.

**What it claims.** [test_pages.py](test_pages.py) reads the page strictly and fails on what it does not know:

- The page is strict UTF-8, starts with `<!DOCTYPE html>`, and holds no control character but the newline and no character that reorders or hides text.
- `html.parser` reads it as well-formed: each element is one of a fixed list, with only the attributes listed for it, each once and with a value. Every element that is opened is closed, in order, and a void element is never closed. There is no comment, processing instruction or other declaration. No script, frame, object, form, base, style attribute or event handler is on the list.
- The figures are inline SVG, from a list of their own: `svg`, `g`, `path`, `circle`, `rect`, `line` and `text`, and `title`, each with only the attributes listed for it. Inside an `<svg>` only that list holds, so there is no `use`, `image`, `a`, `script`, `style`, `foreignObject`, marker, gradient, filter or animation element, and no `href`, `xlink:href`, `style` or event attribute. A value in an `<svg>` is numbers and words, with no colon and no function but `translate()` and `rotate()`, so it holds no `url(`, and a fill or a stroke is `none` or `currentColor`, so no color in a figure escapes the palettes. An element of SVG outside an `<svg>`, or an `<svg>` in an `<svg>`, fails.
- Each `<svg>` has `role="img"` and one `<title>` directly in it, whose id its `aria-labelledby` names, so a screen reader reads each figure by its title. The only other `<title>` is the one in `<head>`.
- Nothing is loaded from another origin. What an element loads, `img src`, `source srcset` and `link href`, is the name of a file in `docs/`, and the one `link` is the icon. The CSS, all in one `<style>`, has no at-rule but `@media` and `@keyframes`, no function but `var()`, no backslash and no `url`, so it loads nothing and no escape can spell a word the test does not see.
- The CSS moves the page only for a visitor who has not asked for less motion: every `animation`, `animation-*` and `scroll-behavior`, also with a vendor prefix such as `-webkit-`, `-moz-`, `-o-` or `-ms-`, stands in a block inside `@media (prefers-reduced-motion: no-preference)`, written so, or in a `@keyframes`, which only says how an animation moves. A prefixed at-rule such as `@-webkit-keyframes` is refused, as any at-rule but `@media` and `@keyframes` is. A brace that is not matched fails.
- A link goes to a file in `docs/`, to an id on the page, or into the repo on GitHub: the repo, a file or a directory on `main` that exists in the checkout, a pull request, an issue or the latest release. A link elsewhere fails, and so does a path with a part that is `.` or `..`.
- The only links out of the repo are to the sources in [sources.json](../sources.json), each matched whole: the repo of a source, or for a source with a directory, `<repo>/tree/HEAD/<directory>`. They name no commit, so a pin that moves does not make the page stale. Any other address of the same host, owner or repo fails.
- A link to the page, `#…` or `index.html#…`, names an id that is on the page, as `html.parser` reads it, character for character. The page is the one page in `docs/`, so a link to a logo has no fragment. The ids on the page stand once each.
- A link into the repo on GitHub may end in a fragment, which must have the form of an id: lowercase letters and digits in words joined by `-`. Whether GitHub shows that id on its page is not checked.
- `docs/` holds exactly `index.html`, `.nojekyll` and the two logos, and each logo is byte for byte its copy in `assets/`.
- The page has `lang="en"`, one `h1`, headings that do not skip a level, and alt text on every image.
- The colors are two palettes of custom properties, for light and for dark (`prefers-color-scheme`), and no hex color is written outside them. In each, the text, the muted text and the links on the background and on the background of a box, the accent of the diagrams and the counts on both, and the text on the background of code, have a contrast ratio of at least 4.5 (WCAG 2, level AA). So do the text, the muted text and the accent of the dark bands, `--ink-*`, on their background, their boxes and their code, and the text of the orange band, `--go-fg` on `--signal`, and its code, with the `$` before each command, `--ink-accent`, on that code. The border of a box, `--edge`, is not checked: a box says nothing that its text and its place in the list do not.
- Every command on the page, a line of a `<pre><code>` block, is a line of a code block marked `sh` in `README.md`.
- The list of sources, `<ul class="sources">`, holds one item for each source in `sources.json`, in its order. Each item starts with a link to the source, named by its name, gives its license once in an element of the class `license`, and names in `<code>`, in the order of `ratchet.json`, exactly the rules whose source cites it. So a rule that starts citing a source, a source added or dropped, or a license that changes fails the test until the page says so.
- The two diagrams are ordered lists of the class `flow`, in any order among their classes, styled as boxes with arrows by the CSS and read as numbered lists without it. Each step links to where the repo shows it: at least one of its links goes into this repo on GitHub, so a step whose only link goes to a source does not pass. They are drawn with HTML and CSS: the figures beside them are pictures of the same steps, and the lists are what the test reads.
- The line that fetches Ratchet and the line that gives the count of rules and the cap are written by `generate.py`, and `--check` fails when either is not current (see [generate.py](#generatepy)). So the pull request of a release, which moves the command in `README.md` and runs `generate.py`, moves the page with it, and so does a change to the rules or the cap. The test reads each line as `generate.py` does, after the spaces that indent it.

**Against which threat.** The page is the first thing many people read, so it must not promise more than the repo shows, and it must not track them: no script, font, stylesheet or image from another origin. A figure in SVG is a second way in for all of these, through a link, a `use`, an `image`, a `foreignObject` or an event attribute, so the figures get a list of their own. A figure that moves must not move for a visitor who has asked for less motion. The threat is a mistake, not intent. A release that moves the README and forgets the page would send people to an older version, a count written by hand would go stale at the next rule, a credit to a source would drift from the rules that cite it, and a link that leads nowhere would go unseen, because nothing else reads the page.

**What it does not claim.** It does not claim that a browser shows the page as intended, or that Pages is turned on and serves it. It reads hex colors only, so a named color is not checked for contrast. It does not check that a figure is legible or that its title says what it shows. It does not read a `transition`: the one on the page moves the arrow of a button by a quarter of a letter on hover, for 0.15 seconds. It reads the CSS by its braces after removing its comments, so a brace in a comment is not read, but a brace in a string is read as a brace. It does not check that the text is true: it is taken from `README.md` and the files the page links to, and read by the maintainer. What each source gives Ratchet is said in Ratchet's own words, and the test does not see whether anything was copied. A link into the repo is checked against the checkout, not against GitHub, so the fragment of such a link, as in the README's `#start-here`, is checked for its form only.

| Case | Result |
|---|---|
| The page as it stands, in this repo and in a copy | Passes |
| No `docs/`, no `.nojekyll`, a file that is not known in `docs/` such as `CNAME` or `404.html`, or a logo that differs from its copy in `assets/` | Fails |
| A byte that is not UTF-8, or a carriage return, a tab, a NUL, a right-to-left override, a zero-width space or a byte order mark | Fails |
| No doctype | Fails |
| A script, inline or loaded, also in capitals, a frame, an object, an embed, a base, a form, an `image` in an inline SVG, or audio | Fails |
| Three figures in inline SVG, each with `role="img"` and its own title, which its `aria-labelledby` names | Passes |
| In an `<svg>`: a `use`, an `image`, an `a`, a `script`, a `style`, a `foreignObject`, a `marker`, a `linearGradient`, a `filter`, an `animate`, a `set`, a second `svg` or a `p` | Fails |
| A `path` outside an `<svg>` | Fails |
| On an `<svg>` or in one: `onload`, `onclick`, `onmouseover`, `href`, `xlink:href`, `xmlns:xlink`, `style` with `url(`, `filter`, `marker-end` | Fails |
| A fill of `url(#g)`, of a `url(` to another origin, of a hex color or of a named color | Fails |
| A transform of `url(#x)` or `matrix()`, a transform with `;` and `:` after it, a path that starts with `javascript:`, a colon written as a character reference | Fails |
| A figure without `role="img"`, with another role, whose `aria-labelledby` names another title or is missing, whose title has no id, or with two titles | Fails |
| A `title` in `main`, in an `h1`, or in a `g` of a figure, or a second `title` in `head` | Fails |
| The animations of the first figure, inside `@media (prefers-reduced-motion: no-preference)`, and their `@keyframes` | Passes |
| An `animation`, an `animation-name` or `scroll-behavior` outside that query, inside `prefers-reduced-motion: reduce`, inside another `@media`, or inside a list of queries that holds it, or the query renamed | Fails |
| `-webkit-animation`, `-webkit-animation-name`, `-moz-animation`, `-o-animation-duration`, `-MS-Animation` or `-webkit-scroll-behavior` outside that query | Fails |
| A prefixed animation inside that query | Passes |
| `@-webkit-keyframes` or `@-moz-keyframes` | Fails |
| A brace left open, or one closed twice | Fails |
| `@supports`, `@property`, `@namespace` or `@layer` | Fails |
| An event handler, a style attribute, a `srcset` or `loading` on an image | Fails |
| An image, a source or the icon loaded from another origin, from `//`, with the scheme written as a character reference, from the repo's raw files, or from `../assets/` | Fails |
| `@import`, `@font-face`, `url(`, `URL(`, `url` spelled with a CSS escape, `image-set()`, `calc()`, or a `link` that is a stylesheet | Fails |
| A link to another site, to `http:`, to another repo of the same owner, to `javascript:`, also written as a character reference, to `mailto:`, to the Pages origin, or to `//` | Fails |
| A link into the repo to a file or a directory that is not there, to a directory as a file, through `..`, to another branch, to the settings | Fails |
| A link to an issue numbered 0, through `..`, to the list of issues or to a new issue | Fails |
| A link to a source at a branch, to its owner, with a trailing slash, over `http:`, or to the repo of a source that has a directory | Fails |
| A relative link to a file that is not in `docs/`, out of `docs/`, from the root, to `.nojekyll`, or to an id that is not on the page | Fails |
| A link to `index.html#start-here` | Passes |
| A link to the page whose fragment is not an id on it: `index.html#start-hree`, a typo for `start-here`, `index.html#Start-here`, `index.html#`, `#missing`, `#start-hree` or `#` | Fails |
| A link with a fragment to a logo, `ratchet-light.svg#logo` | Fails |
| An id twice on the page, here a second `start-here`, which a link names | Fails |
| An element left open, closed out of order, a void element closed, a self-closed `p`, a comment, a CDATA section, a processing instruction, an attribute twice or one not on the list, a `title` outside `head` and the figures | Fails |
| No `lang`, an empty or a missing alt text, an `h3` after the `h1`, no `h1` | Fails |
| Muted text, links or the background changed to a color under 4.5, a hex color outside the palettes, or no palette for dark | Fails |
| A command on the page that is not in `README.md`, or a second line added to a command | Fails |
| The sources as they stand, each with its link, its license and the rules that cite it, written out in the test | Passes |
| A source left out, two sources swapped, or a source added to `sources.json` | Fails |
| A license that is not the one in `sources.json` | Fails |
| A rule that starts citing a source and is not on the page, a rule on the page that does not cite the source, or a rule left out | Fails |
| Two diagrams, every step with a link, the sandbox linked to issue #49 | Passes |
| A step of a diagram without a link, or whose only link goes to a source in `sources.json` | Fails |
| A diagram whose class attribute lists `flow` after another class | Passes, and is counted |
| The background of a box or the accent changed to a color under 4.5, in light or in dark | Fails |
| The muted text or a box of a dark band, the text of a dark band, the text of the orange band, or the text of code changed to a color under 4.5 | Fails |
| The background of the code of the orange band changed so that only the `$` before a command, `--ink-accent`, is under 4.5, in light or in dark | Fails |
| The count of rules and the cap as they stand, counted in the test from `ratchet.json` | Passes |
| The cap raised in `ratchet.json`, before `generate.py` is run | `generate.py --check` fails on `docs/index.html`, and `generate.py` writes it |
| A number in the count edited by hand | `generate.py --check` fails |
| The count removed, twice, with more on its line, changed in its words, its id moved to another element, a second element with its id, or a number spelled out | `generate.py --check` fails, and `generate.py` writes nothing to the page |
| The count or the fetch line indented by two spaces | Passes |
| A release that dates the first entry and moves the README, before `generate.py` is run | `generate.py --check` fails on `docs/index.html`, and `generate.py` writes it |
| The page moved to a version that the README does not fetch | `generate.py --check` fails |
| The fetch line removed, twice, with more on its line, outside `<pre><code>`, another line that holds `git clone`, or a version of another form | `generate.py --check` fails, and `generate.py` writes nothing to the page |
| No page, or a page that is not UTF-8 | `generate.py --check` fails, with no traceback |

Each case is the page with one change, so the cases follow the page when it changes.

## upgrade.py

```sh
python3 .ratchet/checks/upgrade.py register.json --from .ratchet/from.json
```

This one checks no rule in a register. It is the upgrade path for a project ([UPGRADING.md](../UPGRADING.md)). `--from` is the `ratchet.json` of the version the register states, taken from its tag. `--source`, by default the `ratchet.json` next to the script, is the newer Ratchet.

**What it claims.** It reads three data files strictly, and when they are valid it prints, rule by rule, what is different between the two versions of Ratchet and what the register must do about it:

- a rule the register adopts that changed: which of its status, enforcement, rule, ratchet and source changed, and the entry to put in its place. The entry is the newer rule, character for character. It keeps the status and the place of the check when the rule still names a check, gets `text only for now` when its ratchet now names one, and loses both when it is text only now. When the ratchet of a rule marked `built` changed, it says to look at the check again.
- a rule the register adopts that was removed: take it out of `adopted`, and, to keep it, add the printed entry to `own`. The entry is the older rule with only the fields of an own rule, `key`, `rule`, `ratchet` and `source`, so a status and a `where` are dropped. Its key is the prefix of the register's first own rule, or one made from the project's name, then a dot and the name in Ratchet's key, with `-2` and so on when that key is taken. A name that gives no prefix, or gives `ratchet`, gives `project`.
- when every rule the register adopts was removed: adopt at least one rule, from the new rules, or from the rules to start with when there are no new ones, each printed with its entry. A register that adopts no rule does not pass `check_register.py`.
- a new rule: the entry to add, if the project adopts it.
- a rule that changed or was removed and is not adopted: its key, with nothing to do.
- when the fields of `ratchet.json` differ between the two versions, at the top or in its rules: which are new and which are gone, and that a copy of a Ratchet check kept in the project, or a check of the project's own, that reads `ratchet.json` must be updated. The checks in `.ratchet` need nothing, and nothing in the register changes. The older file may lack the cap and may hold `date` and `sources`, which left `ratchet.json` in 0.9 ([D-2026-11-19-batched-releases](../decisions/D-2026-11-19-batched-releases.md)), and no other field the newer one does not know. A field of a rule is new when some rule of the newer file holds it and no rule of the older one does, as `since` is from 0.10 ([D-2026-11-19-one-point-oh](../decisions/D-2026-11-19-one-point-oh.md)), and gone the other way round.

Before it prints a step, it checks that the register passes `check_register.py` against the older Ratchet, and that the register with every step done, and no new rule adopted, passes it against the newer one. When the register adopts a removed rule, it checks that register twice: with each removed rule taken out, and with each also moved to `own` by the printed entry. When every adopted rule was removed, it checks both with every rule it printed to choose from adopted. A register that does not pass against the older Ratchet is not upgraded, so one that adopts no rule from Ratchet, or a rule that is not in the version it states, still fails. It writes nothing, and reads no file but the three it is given. It runs offline.

**Against which threat.** A project that upgrades by hand misses a rule that changed, keeps a softened copy, or keeps a status that no longer holds, and the register still looks like Ratchet's.

**The older `ratchet.json`.** It is read with the same strict reader, `registry.validate`, with these things left out, because they are not what an upgrade compares and an older version may not have them in today's form: it may lack the cap, which came in 0.5, it may hold `date` and `sources`, which left in 0.9, its experimental rules may lack `since`, which came in 0.10, its sources are not read (Ratchet 0.3 wrote one in a form that 0.4 refuses), the files of its reference checks and of the decisions in `kept_by` are not looked for, and its budget is not counted. A field it does not know, a field twice, a rule of another form or bytes that are not UTF-8 still fail.

**What it does not claim.**

- It does not find the latest version, and does not reach the network. It compares the files it is given.
- It does not see that the file given with `--from` is the one at the tag. It checks that the register passes against it and that the version is older or the same, and that two files that name the same version have the same rules.
- It does not see whether a check marked `built` exists or works.
- It does not list a rule that only moved to another part, or whose reference check changed. Neither changes the register.
- It does not say why a rule changed. The changelog of the newer Ratchet does.

**The cases.** Each is a test in [test_upgrade.py](test_upgrade.py). The fixtures are under [fixtures/upgrade/](fixtures/upgrade/): a Ratchet 9.8 and a 9.9 with every kind of change between them, a register on 9.8, a smaller 9.8 and 9.9 under `removed/`, in which a rule that names a check and a rule that is text only are removed and one rule is added, and this repo's own `register.json` and `ratchet.json` as they stood at the tags `v0.3` to `v0.9`, under `released/`.

| Case | Fixture | Result |
|---|---|---|
| Every kind of change: a rule reworded, one that now names a check, one that is now text only, one whose ratchet and source changed while its check is built, one removed, two new, and one changed and one removed that are not adopted | `register.json`, `old/ratchet.json`, `new/ratchet.json` | Passes, with a step for each, and an entry for `own` for the removed rule |
| Each printed entry is the newer rule, with the status that holds | the same | Passes |
| The register with every step done passes against the newer Ratchet, and the rules that did not change keep their entries | the same | Passes |
| Nothing is written | the same | Passes, every file as it was |
| This repo's register at 0.3 to 0.9, upgraded to this version, with a note that `date` and `sources` are gone before 0.9 and that `since` in a rule is new, and the steps in `UPGRADING.md` run on the register at 0.8. The steps fetch a version with a date in the changelog | `released/0.3/` to `released/0.9/` | Passes |
| An older `ratchet.json` whose sources have a form that is no longer read | `old-source-form/ratchet.json` | Passes |
| A register already on the newer version | `register-current.json` | Passes: nothing to change |
| A register whose rule was softened | `register-drifted.json` | Fails: no step is printed |
| A register on another version than the older `ratchet.json` | `register-other-version.json` | Fails |
| A newer Ratchet that is older than the register | `register-current.json` with the two swapped | Fails |
| A `ratchet.json`, older or newer, with a field twice, not JSON, not UTF-8, a field it does not know at the top or in a rule, a field missing, a character not on the list, a version that is a number, a key twice, a rule in a part that does not exist | `faults/` | Cannot run, with the fault named |
| A file that does not exist, or no `--from` | none | Cannot run |
| An older `ratchet.json` without the cap, as at `v0.3` and `v0.4`, and two with the same fields | `old-source-form/ratchet.json`, `released/`, and `old/ratchet.json` with the cap taken out in the test | Passes, with a note that `experimental_cap` is new, after the steps, and that `date` and `sources` are gone where the older file holds them. With the same fields, no note |
| A removed rule marked `built` with a `where`, and one whose key in `own` is taken, each kept in `own` by the printed entry | `removed/register.json`, `removed/old.json`, `removed/new.json` | Passes, with an entry that has the fields of an own rule only, and `-2` on the taken key |
| The same, with an entry for `own` that keeps the status and the `where` | the same, with the entry changed in the test | Fails: no step is printed |
| A register that adopts only rules that were removed | `removed/register-only-removed.json` | Passes, with the removals, the new rules and a step to adopt one |
| The same, against a Ratchet with no new rule | the same, with the new rule left out in the test | Passes, with the rules to start with |
| A register without own rules whose project name gives no prefix, or gives `ratchet` | the same, with the name changed in the test | Passes, with the prefix `project` |
| A register that adopts no rule from Ratchet | `removed/register-adopts-nothing.json` | Fails: it does not pass against the version it states |

## init.py

```sh
python3 .ratchet/checks/init.py --check            # say what it would write and what it skips, write nothing
python3 .ratchet/checks/init.py                    # write it
python3 .ratchet/checks/init.py --name "My project"
```

This one checks no rule in a register. It is the start of a project, run from the root of the project's repo with Ratchet cloned into `.ratchet`, as the [README](../README.md#start-here) says. It is new in 0.9.

**What it claims.** It writes what the steps of "Start here" set up by hand, and never overwrites a file:

- `AGENTS.md` from `templates/AGENTS.md`, with the project's name in its title. The rest of the template, with its parts in angle brackets, is the project's to fill in.
- `register.json` from `templates/register.json`, with the project's name, checked with `check_register.py` before it is written.
- `REGISTER.md`, generated from the `register.json` that stands after the run, as `check_register.py --write` does. When `register.json` already exists, that is the one it is generated from.
- `.github/workflows/ratchet.yml` from `templates/ratchet-checks.yml`, with the commit of the Ratchet checkout it runs from as the pin. The commit is read with `git rev-parse` in that checkout and must be 40 characters `0-9` and `a-f`. It does not run when the checkout is not a git repo of its own, or has changes that are not committed, since the commit would then not hold the files it copies. It says whether the commit is the one of the tag of its version.
- the line `/.ratchet/` at the end of `.gitignore`, unless the last line there that mentions `.ratchet` is exactly `.ratchet/` or `/.ratchet/`, with no line starting `!` after it. A space at the start or the end of a line is part of it, as gitignore reads a leading space, so ` .ratchet/` gets the line, and so does any other form, which at worst adds a line that is not needed. A file with CRLF gets CRLF. This is the one file it changes, and only by that line, in one step: it is read again just before it is replaced, and when it no longer holds what was read, the run stops with exit 2 and leaves it as it is.

The name is the folder's name, unless `--name` gives one: ASCII letters and digits, in words joined by one space, `-`, `.` or `_`, at most 100 characters, and nothing that is shown as a link. So it can stand as text in a heading and in the register.

A file that exists with the content it would write is unchanged. A file that exists with other content, or that is not a plain file, is skipped, named, and left as it is, and the run exits 1. With `--check` it writes nothing and says the same, and checks in memory the register it would leave. Otherwise it ends by running `check_register.py register.json --markdown REGISTER.md` from the same checkout and shows its output. A second run says that nothing changed. Each file is written in full to a temporary file beside it and synced, then linked into place with a hard link, which fails when the file appeared meanwhile, so a file is missing or whole. On a file system with no hard links it stops with exit 2 and writes no file there: it never writes a file directly, which a cut-off write could leave half written for a second run to skip. A run that stops halfway leaves whole files, and the next run writes the rest. Exit code 0: everything is in place and the register passes. 1: a file was skipped, or the register does not pass. 2: it could not run, and wrote nothing, or it stopped at a file it could not write or at a `.gitignore` that changed, and says how many files it wrote before.

It runs only from the root of a git repo, read from the files and not by running git there: a `.git` directory that holds `HEAD` and `objects/`, or a `.git` file of the one line `gitdir: <path>`, the path absolute or from the project's root, naming a directory that holds `HEAD` and `commondir` or `objects/`, as a worktree, a submodule or `git init --separate-git-dir` leaves it.

**Against which threat.** Mistakes by the person or the agent who starts a project in their own repo: work overwritten by a template, a pin that is a tag name, a placeholder or the commit of other files than the ones copied, the line in `.gitignore` forgotten or not taking effect, an edit to `.gitignore` lost, a result left half written, a run in a folder that is not the root of a repo.

**What it does not claim.** It does not guard against a hostile Ratchet checkout: its code is the code that runs. It never runs code from the project's repo. It runs git only in the Ratchet checkout, never in the project's repo, whose git config could name a program to run (`core.fsmonitor`), and the check at the end is the checkout's own. It does not read `.git/info/exclude`, a global excludes file or a `.gitignore` below the root, and it does not stand against an edit made to `.gitignore` in the instant between the second read and the replacement. It does not guard against a concurrent attacker. It does not see whether the pinned commit is on GitHub: a commit that is not the one of a tag is named, and fetched by the workflow all the same. It does not merge an `AGENTS.md` the project already has with the template, and it does not build any check.

**The cases.** Each is a test in [test_init.py](test_init.py), on a project of its own: a git repo with a clone of a copy of this checkout, with one commit, as its `.ratchet`.

| Case | Result |
|---|---|
| An empty repo | Every file written, with the folder's name, `.ratchet/` in `.gitignore`, exit 0 |
| The pinned commit | The workflow is the template with the commit of the checkout in place of the placeholder |
| The generated `REGISTER.md` | Passes `check_register.py --markdown`, and every step of the workflow runs |
| An `AGENTS.md` that exists, or a directory in its place | Skipped and named, left as it is, the rest written, exit 1 |
| A `register.json` that exists | Skipped, and `REGISTER.md` generated from it, exit 1 |
| A second run | Nothing changed, every file unchanged, exit 0 |
| `--check`, on an empty repo and with an `AGENTS.md` that exists | Writes nothing, names what it would write and skip, exit 0 and 1 |
| A bad name: empty, spaces at the ends or two in a row, `\|`, `@`, a mark at the ends, `www.`, a letter outside ASCII, another script, a character that shows as nothing, 101 characters, the placeholder | Cannot run, writes nothing |
| A folder whose name is not a name | Cannot run and says to give `--name`. With it, passes |
| A `.gitignore` that exists without the line, or with CRLF | The line added, with CRLF for CRLF, and git's own `check-ignore` says `.ratchet` is ignored |
| A `.gitignore` whose last line on `.ratchet` is `.ratchet/` or `/.ratchet/`, after a `!.ratchet/`, with LF and CRLF | Nothing changed, and `.ratchet` is ignored |
| A `.gitignore` whose last line on `.ratchet` is ` .ratchet/`, a tab and `.ratchet/`, `.ratchet/` with a space after it, `.ratchet`, `/.ratchet`, `.ratchet/*`, a comment or `!.ratchet/`, or is `.ratchet/` with `!*` after it | `/.ratchet/` added as the last line, `.ratchet` ignored, and a second run changes nothing |
| A `.gitignore` edited after the plan and before the write | Stops with exit 2, the edit kept and the line not added; the next run adds it |
| The line added to a `.gitignore` that no longer holds what was read | Refused, the file left as it is |
| Outside the root of a git repo, a Ratchet that is not a git checkout, one with changes not committed, or in Ratchet's own checkout | Cannot run, writes nothing |
| An empty `.git` directory, one with `HEAD` and no `objects/`, a stale `.git` file, one naming a directory that is no repo, one of two lines, one with no `gitdir:`, an empty one | Cannot run, writes nothing |
| A worktree made with `git worktree add`, and a `.git` file naming a repo elsewhere by an absolute and by a relative path | Runs |
| No hard links on the file system | `write_new` raises and creates nothing; `init.py` stops with exit 2 and writes no file; the next run writes them all |
| Every write cut off halfway, with and without hard links | The file does not exist and no temporary file is left |
| A file linked into place | At the link, the file does not exist and the temporary file holds all of it |
| A file that appears just before the link | Not overwritten: `write_new` returns false |
| A commit that is not 40 characters `0-9` and `a-f` | Refused |
| A checkout at the tag of its version, and one that is not | Named either way |
| No temporary file is left behind | Passes |

## tripwire.py

```sh
python3 checks/tripwire.py < call.json   # exit 0: the call goes ahead; exit 2: it is denied, with the reason on stderr
```

The reference check for `ratchet.irreversible-waits`. It is a `PreToolUse` hook for Claude Code ([Anthropic's hooks reference](https://code.claude.com/docs/en/hooks)): Claude Code runs it before every Bash command and every write to a file, and gives it the call as JSON on stdin. This repo runs it from [.claude/settings.json](../.claude/settings.json), and a project copies it as [CONTROL-ROOM.md](../CONTROL-ROOM.md#what-cannot-be-undone) says.

**It is a tripwire, not a lock.** It reads a command line well enough to catch the usual spellings of the five steps, and no better. It does not claim every spelling: another spelling of the same step gets past it, and a hook that reads the shell can always be shown one (D-2026-11-19-locks-not-parsing). Its claim is exactly the cases listed below. Where each step is locked, and where nothing locks it, is in [CONTROL-ROOM.md](../CONTROL-ROOM.md#what-cannot-be-undone).

**What it claims.** For a Bash command, it exits 2 and names each step on a line of its own, `tripwire: <step>`, when the command is one of the cases below and the approvals file has no entry for each step it takes with that exact command. For `Write`, `Edit`, `MultiEdit` and `NotebookEdit`, it exits 2 when the path is the approvals file. Every other tool exits 0. Input it cannot read, an empty call, a call that is not JSON or not UTF-8, has a field twice, names no tool or lacks the command or the path, exits 2. Any failure of its own exits 2 as well: it never exits other than 0 or 2, and its settings use `"onFailure": "block"`, so a hook that cannot start or times out blocks the call too.

**Against which threat.** An agent's mistake: a force push it takes to be harmless, a tag or a release nobody asked for, `rm -rf` on the wrong directory, a change to the settings, written in the way agents usually write these commands. It does not stand against an agent that means to get past it: such an agent writes the step another way, from a script, from another language, or edits the hook and its settings, which are files the maintainer reads before a merge (`ratchet.checks-owner-read`).

**How it reads a line.** It splits the line into simple commands at `;`, `&`, `|`, `&&`, `||`, newlines and parentheses, and also reads every `$(...)`, backtick and `<(...)` as commands of their own. It takes quotes and backslashes away as the shell does, skips the body of a here-document, and skips assignments, `if`, `then`, `do` and the like. It looks past `env`, `command`, `builtin`, `exec`, `nohup`, `nice`, `timeout`, `sudo`, `xargs`, `stdbuf` and `time`, and past a path before the program, such as `/usr/bin/git`. A `cd` to a literal path is followed for the commands after it in the same line, and a `cd` to anything else makes every later path unknown. It does not expand a variable, a pattern or a tilde other than a leading `~`.

**The steps, as it reads them.**

- `force-push`: `git push` with an option that starts `--force`, with `-f` alone or in a cluster such as `-uf`, `--mirror`, `--prune`, `--delete` or `-d`, a refspec that starts with `+`, or one with no source, `:ref`; `gh api` deleting `git/refs/heads/...`, or changing one with `force=true` or with a body from `--input`.
- `tag`: `git tag` with a name, `-a`, `-s`, `-f`, `-m`, `-F` or `-u`, and no listing option, or with `-d` or `--delete`; `git push` with `--tags`, `--follow-tags` or `--mirror`, the word `tag`, a refspec under `refs/tags/`, or a name that is a tag in the local repository, also with `--delete` or as `:ref`; `git update-ref` and `git symbolic-ref` on `refs/tags/`; `gh api` changing `git/refs/tags/...` or `git/tags`, or creating `git/refs` with `ref=refs/tags/...` or with a body from `--input`.
- `release`: `gh release create`, `edit`, `delete`, `upload` and `delete-asset`; `gh api` with any method but `GET` under `repos/{owner}/{repo}/releases`.
- `delete-outside`: `rm` with `-r`, `-R` or `--recursive`, alone or in a cluster, when an operand resolves to the working tree itself or to a path outside it, after links are resolved, or holds a variable or a substitution. The one exception is the temporary directory of the same line: `d=$(mktemp -d)`, or `$(mktemp -d -t <name>)`, followed in the same line by `rm -r "$d"` or `"${d}"`, quoted and with nothing after it, when nothing else in the line assigns `d` or names it as a word. And since the shell's state does not last from one Bash call to the next, a later call may delete such a directory by its path, or a path inside it, written from the directory where `mktemp -d` writes or from `/tmp`. On macOS that directory is the per-user temporary directory the system gives, `confstr(_CS_DARWIN_USER_TEMP_DIR)`, which `mktemp -d` uses whatever `TMPDIR` says, so `TMPDIR` does not move the exception there. When the system gives no absolute path of an existing directory, or the call fails, that root is not trusted at all and nothing takes its place, not `TMPDIR` and not a default; `/tmp` stays. Elsewhere it is the temporary directory that `TMPDIR` names, as GNU `mktemp` reads it. The entry directly in it is a real directory, named `tmp.` and six or more letters or digits as `mktemp -d` names it, and owned by the user the hook runs as. That entry and every part of the path after it are read as written, with `lstat` and before any link is followed, so none may be a link, `.` or `..`, with or without a `/` at the end. A part that does not exist ends the walk, since nothing below it exists. Another session of the same user may have a directory of that form, which this does not tell apart. The tests put a fresh directory from `mktemp -d` in the place of `/tmp`, so that they need no write to `/tmp`. They do it through a constant in the hook, which nothing in a call, its JSON or its environment, can change.
- `settings`: `gh repo edit`, `delete`, `rename`, `archive`, `unarchive` and `deploy-key`; `gh secret` and `gh variable` with `set`, `delete` or `remove`; `gh workflow enable` and `disable`; `gh api` with any method but `GET` on `repos/{owner}/{repo}` itself, or under one of its settings paths: `rulesets`, `branches`, `collaborators`, `invitations`, `hooks`, `keys`, `actions`, `environments`, `pages`, `secrets`, `variables`, `topics`, `vulnerability-alerts`, `automated-security-fixes`, `autolinks`, `properties`, `private-vulnerability-reporting`, `transfer`, `tags`, `dependabot`, `codespaces`, `interaction-limits` and `teams`. Labels are not on the list: they count as harmless and can be undone. Of these, the role Write may change Actions secrets and variables, of the repository and of an environment, and GitHub's docs do not reserve Dependabot and Codespaces secrets or enabling a workflow to an admin, so for these the tripwire is the only guard ([CONTROL-ROOM.md](../CONTROL-ROOM.md#what-cannot-be-undone)). Their usual spellings, with `gh secret`, `gh variable` and `gh api`, are cases below.
- `approvals-file`: any word or redirection in the command that names the approvals file, from the directory the command runs in. No approval covers it.

`gh api` takes its method from `-X`, `-XMETHOD`, `--method` or `--method=METHOD`, and without one, from GitHub CLI's own default: `POST` when a field (`-f`, `-F`, `--field`, `--raw-field`) or `--input` is given, `GET` otherwise.

**The approvals.** They are in `.claude/ratchet-approvals.json` in the project, which git ignores, so an approval stays on the machine where the owner wrote it and is never published. The owner writes it; [templates/ratchet-approvals.json](../templates/ratchet-approvals.json) is the empty file to start from.

```json
{"approvals": [{"step": "tag", "command": "git tag v0.7", "until": "2026-11-30"}]}
```

- It is read strictly: strict UTF-8, valid JSON, no field twice, exactly the field `approvals` at the top and exactly `step`, `command` and `until` in each entry. One defect anywhere, and the file approves nothing, and the denial names the defect.
- `step` is one of the five steps. A command that takes two, such as `git push --mirror origin`, needs an entry for each.
- `command` is the whole command, character for character, and one plain command: printable ASCII, no space at either end and none of `;`, `&`, `|`, `<`, `>`, `(`, `)`, `$`, a backtick or a backslash. So an approval never covers a chain or a substitution. A command that is not plain cannot be approved, and the denial says to run the step on its own line.
- `until` is a real date, `YYYY-MM-DD`, and the approval holds through that day, by the machine's own date.

**The cases.** Each is a test in [test_tripwire.py](test_tripwire.py), which runs the hook in a child process, as Claude Code does, in a scratch git work tree with a tag `v1` and a branch `feature`. The cases are in [fixtures/tripwire/](fixtures/tripwire/). In a command, `{tree}` stands for the scratch work tree.

Every case below is denied, and names its step and no other. With an entry for each of its steps and that exact command, a case in the third column passes, and the same command with a space after it, with `true && ` before it or with `; true` after it is still denied. A case in the fourth column stays denied with such entries.

| Step | What it is | Denied, and passes when approved | Denied, and cannot be approved |
|---|---|---|---|
| `force-push` | Force push, or deleting a remote branch | `git push --force origin feature`, `git push -f origin feature`, `git push -uf origin feature`, `git push --force-with-lease origin feature`, `git push --force-with-lease=feature origin feature`, `git push origin +feature`, `git push origin +HEAD:refs/heads/main`, `git push --delete origin feature`, `git push -d origin feature`, `git push origin :feature`, `git push --prune origin`, `git push --mirror origin`, `git -C . push -f origin feature`, `/usr/bin/git push -f origin feature`, `env GIT_TRACE=1 git push -f origin feature`, `nohup git push -f origin feature`, `'git' push '--force' origin feature`, `gh api -X DELETE repos/o/r/git/refs/heads/feature`, `gh api -X PATCH repos/o/r/git/refs/heads/main -F force=true` | `true && git push -f origin feature`, `git status; git push --force origin feature`, `(git push -f origin feature)`, `echo "$(git push -f origin feature)"` |
| `tag` | Creating, moving or deleting a tag | `git push --mirror origin`, `git tag v2`, `git tag -a v2 -m "Release v2"`, `git tag v2 HEAD~1`, `git tag -f v1`, `git tag -d v1`, `git tag --delete v1`, `git push origin v1`, `git push origin refs/tags/v1`, `git push origin tag v1`, `git push --tags`, `git push origin --tags`, `git push --follow-tags origin main`, `git push origin :refs/tags/v1`, `git push --delete origin v1`, `git update-ref refs/tags/v2 HEAD`, `git update-ref -d refs/tags/v1`, `gh api repos/o/r/git/refs -f ref=refs/tags/v2 -f sha=abc`, `gh api -X POST repos/o/r/git/refs --input ref.json`, `gh api -X PATCH repos/o/r/git/refs/tags/v1 -f sha=abc`, `gh api -X DELETE repos/o/r/git/refs/tags/v1`, `gh api repos/o/r/git/tags -f tag=v2 -f object=abc` | none |
| `release` | Creating or changing a release | `gh release create v2`, `gh release create v2 --notes x`, `gh release create -R o/r v2`, `gh release edit v1 --draft`, `gh release delete v1 --yes`, `gh release upload v1 file.zip`, `gh release delete-asset v1 file.zip`, `gh api repos/o/r/releases -f tag_name=v2`, `gh api -X PATCH repos/o/r/releases/1 -f draft=false`, `gh api -X DELETE repos/o/r/releases/1`, `gh api --method DELETE /repos/o/r/releases/1`, `gh api -XDELETE repos/o/r/releases/1`, `gh api --method=POST repos/o/r/releases --input release.json` | none |
| `delete-outside` | Deleting outside the working tree | `rm -rf /etc/x`, `rm -r /var/x`, `rm -fr ../x`, `rm -R ../../x`, `rm --recursive /opt/x`, `rm -rf sub/../../x`, `rm -rf ~/x`, `rm -rf ~`, `rm -rf .`, `rm -rf {tree}`, `/bin/rm -rf /etc/x`, `sudo rm -rf /etc/x`, `command rm -rf /etc/x` | `rm -rf "$HOME/x"`, `rm -rf "$d"`, `rm -rf "$(pwd)/x"`, `cd /etc && rm -rf x`, `cd .. && rm -rf x`, `d=$(mktemp -d); d=/etc; rm -rf "$d"`, `d=$(mktemp -d); read d; rm -rf "$d"`, `d=$(mktemp -d); printf %n d; rm -rf "$d"`, `d=$(mktemp -d); rm -rf "$d/sub"`, `d=$(mktemp -d); rm -rf $d`, `d=$(mktemp -d /missing/tmp.XXXXXX); rm -rf "$d"` |
| `settings` | Changing the repository's settings | `gh api -X PATCH repos/o/r -f description=x`, `gh api -X PATCH repos/{owner}/{repo} -F has_wiki=false`, `gh api -X DELETE repos/o/r`, `gh api repos/o/r/rulesets --input ruleset.json`, `gh api -X PUT repos/o/r/rulesets/1 --input ruleset.json`, `gh api -X PUT repos/o/r/branches/main/protection --input protection.json`, `gh api -X PUT repos/o/r/collaborators/someone`, `gh api repos/o/r/hooks -f name=web`, `gh api repos/o/r/keys -f key=x`, `gh api -X PUT repos/o/r/actions/permissions -F enabled=false`, `gh api -X PUT repos/o/r/actions/secrets/X -f encrypted_value=x`, `gh api repos/o/r/actions/variables -f name=X -f value=y`, `gh api -X PUT repos/o/r/environments/production`, `gh api -X PUT repos/o/r/topics -f names[]=x`, `gh api -X POST repos/o/r/pages --input pages.json`, `gh repo edit --visibility public`, `gh repo delete o/r --yes`, `gh repo rename other`, `gh repo archive --yes`, `gh repo deploy-key add key.pub`, `gh secret set X --body y`, `gh secret delete X`, `gh variable set X --body y`, `gh variable delete X`, `gh workflow disable checks.yml`, `gh workflow enable checks.yml`, `gh secret set X --env production --body y`, `gh secret set X --app dependabot --body y`, `gh secret set X -R o/r --body y`, `gh secret set -f secrets.env`, `gh secret delete X --env production`, `gh secret delete X --app codespaces`, `gh secret remove X`, `gh variable set X --env production --body y`, `gh variable set -f vars.env`, `gh variable delete X -e production`, `gh api -X DELETE repos/o/r/actions/secrets/X`, `gh api --method DELETE /repos/o/r/actions/secrets/X`, `gh api --method=PUT https://api.github.com/repos/o/r/actions/secrets/X --input secret.json`, `gh api -XDELETE repos/{owner}/{repo}/actions/variables/X`, `gh api -X PATCH repos/o/r/actions/variables/X -f value=y`, `gh api -X PUT repos/o/r/environments/production/secrets/X -f encrypted_value=x`, `gh api repos/o/r/environments/production/variables -f name=X -f value=y`, `gh api -X DELETE repos/o/r/environments/production/variables/X`, `gh api -X PUT repos/o/r/dependabot/secrets/X -f encrypted_value=x`, `gh api -X DELETE repos/o/r/codespaces/secrets/X`, `gh api -X PUT repos/o/r/actions/workflows/checks.yml/disable` | `gh secret set X < secret.txt` |
| `approvals-file` | Naming the approvals file | none | `echo x > .claude/ratchet-approvals.json`, `cp other.json .claude/ratchet-approvals.json`, `cat .claude/ratchet-approvals.json`, `cd .claude && rm ratchet-approvals.json`, `tee {tree}/.claude/ratchet-approvals.json` |

The control room's normal work passes with no approvals file: `git status`, `git log --oneline -3`, `git push -u origin personlig/topic`, `git push origin personlig/topic`, `git push origin HEAD`, `git push --set-upstream origin personlig/topic`, `git push origin HEAD:refs/heads/personlig/topic`, `git fetch origin --tags`, `git fetch -q origin pull/42/head:refs/remotes/origin/pr42`, `git worktree add ../wt -b personlig/topic origin/main`, `git worktree remove ../wt`, `git tag`, `git tag -l 'v*'`, `git tag --list`, `git tag --contains HEAD`, `git tag --points-at HEAD`, `git tag -n5`, `git commit -m "Do not git push --force, git tag v2 or rm -rf /etc"`, `git commit -F message.txt`, `echo git push --force origin main`, `grep -n "gh release create" README.md`, `gh api repos/o/r/pulls/42`, `gh api repos/o/r/rulesets`, `gh api repos/o/r/rulesets/1 --jq .rules`, `gh api -X GET repos/o/r/releases`, `gh api repos/o/r/git/refs/tags`, `gh api repos/o/r/pulls -f title=x -f head=personlig/topic -f base=main -F body=@body.md`, `gh api -X PATCH repos/o/r/pulls/42 -F body=@body.md`, `gh api -X PUT repos/o/r/pulls/42/merge -f merge_method=squash -f sha=abc123`, `gh api repos/o/r/issues/42/comments -F body=@comment.md`, `gh api -X PATCH repos/o/r/issues/42 -f state=closed`, `gh api repos/o/r/labels -f name=x`, `gh api -X PATCH user/repository_invitations/1`, `gh pr view 42`, `gh release list`, `gh release view v1`, `gh label create x`, `gh secret list`, `gh variable list`, `gh variable get X`, `gh api repos/o/r/actions/secrets`, `gh api repos/o/r/actions/variables/X`, `gh api -X GET repos/o/r/environments/production/secrets`, `rm -rf build`, `rm -rf {tree}/build`, `rm -rf ./build/../dist`, `rm -f notes.txt`, `d=$(mktemp -d) && rm -rf "$d"`, `d=$(mktemp -d); rm -r "$d"`, `d=$(mktemp -d -t ratchet) && rm -rf "${d}"`, `d=$(mktemp -d) && git worktree add "$d/wt" origin/main && git -C "$d/wt" log -1 && git worktree remove "$d/wt" && rm -rf "$d"`, `d=$(mktemp -d) && printf '%s\n' "text" > "$d/body.md" && gh api -X PATCH repos/o/r/pulls/42 -F body=@"$d/body.md" && rm -rf "$d"`, `cat > body.md <<'EOF' Do not run git push --force or gh release create. rm -rf /etc EOF`, `/usr/bin/python3 -m unittest discover -s checks`, `git -C {tree} status`, `cat templates/ratchet-approvals.json`.

| Case | Test | Result |
|---|---|---|
| A directory from `mktemp -d`, and a path inside it, deleted by its path in a later call; the temporary directory itself, `..` from such a directory, a directory of another name, a name too short, and a link of that form | `test_a_directory_from_mktemp_may_be_deleted_by_its_path_in_a_later_call` | The first two pass; the rest are denied |
| Such a directory with a `/` at the end, with `//` inside, and by its path after links; a sibling `tmp.` link to it, with and without a `/` at the end and with a path under it; a link inside it to a directory outside or to another such directory, with and without a `/` at the end; `..` and `.` after the entry, also where `..` leads to another such directory | `test_a_link_to_or_inside_a_directory_from_mktemp_is_never_followed` | The first three pass; the rest are denied |
| The two tests above, run in four processes at once. Each makes its entries in the temporary directory with fresh names, never a fixed one | `Parallel.test_runs_at_the_same_time_do_not_touch_each_other` | All four pass |
| `TMPDIR` set to an unrelated directory, as Claude Code's sandbox sets it: a directory from `mktemp -d`, and a path inside it, deleted by its path; where `mktemp -d` did not write to `TMPDIR`, a directory of that form made in `TMPDIR`, and a path inside it | `test_the_temporary_directory_is_where_mktemp_writes_whatever_TMPDIR_says` | The first two pass; the rest are denied |
| On macOS, `confstr(_CS_DARWIN_USER_TEMP_DIR)` raising `OSError` or `ValueError`, or giving `None`, an empty string, a relative path or a directory that does not exist, with `TMPDIR` at an unrelated directory: a `tmp.` directory in `TMPDIR`, and a path inside it; a directory from `mktemp -d` in `/tmp`, and a path inside it. Then `confstr` giving that directory, and the same on Linux with `confstr` failing. A fresh directory from `mktemp -d` stands in for `/tmp` | `test_on_macOS_a_system_temporary_directory_it_cannot_establish_is_not_trusted` | With each failure the first two are denied and the last two pass; the rest pass |
| A directory made by `mktemp -d /tmp/tmp.XXXXXXXXXX`, a path inside it, and the directory with a `/` at the end, with `TMPDIR` and the directory where `mktemp -d` writes at an unrelated directory. A fresh directory from `mktemp -d` stands in for `/tmp` | `test_a_directory_from_mktemp_in_tmp_may_be_deleted_by_its_path_in_a_later_call` | All pass |
| The second root the hook trusts | `test_the_second_root_is_tmp` | It is `/tmp` |
| A directory from `mktemp -d` in the temporary directory and one in `/tmp`, and a path inside each, with the hook running as this user, then as another uid. Fresh directories from `mktemp -d` stand in for both | `test_a_directory_of_another_owner_is_never_deleted` | Pass, then denied |
| `git push --mirror origin` with an entry for `force-push` only, then for both steps | `test_a_command_with_two_steps_needs_an_entry_for_each` | Denied and names `tag`, then passes |
| An entry whose last day is today, and one whose last day was yesterday | `test_an_approval_holds_through_its_last_day_and_not_after` | Passes, then denied |
| An approvals file with one defect: an unknown field at the top or in an entry, a missing field, a field twice, not JSON, not UTF-8, a top level that is not an object, `approvals` that is not a list, an unknown step, a date of another form, an impossible date, a date that is a number, a command with `;` or `$(...)`, an empty command, a command with a space at either end, a command that is not ASCII | `test_an_approvals_file_with_a_defect_approves_nothing`, `fixtures/tripwire/approvals/` | `git tag v9` denied, and the defect named |
| A valid approvals file whose entry has expired, names another command or names another step | the same | `git tag v9` denied |
| The message says what the owner writes to approve it | `test_the_message_says_what_the_owner_writes` | The entry, with `YYYY-MM-DD` |
| `Write`, `Edit`, `MultiEdit` and `NotebookEdit` on the approvals file, also by a path with `..`, and on a file of the same name elsewhere | `test_no_file_tool_writes_the_approvals_file` | Denied; the other file passes. `cat .claude/ratchet-approvals.json` stays denied with an entry for every step |
| `Read`, `Glob`, `Grep` and `WebFetch` | `test_other_tools_pass` | Passes |
| Eleven kinds of input it cannot read | `test_input_it_cannot_read_is_denied` | Denied |
| Forty-one odd lines: unclosed quotes and substitutions, lone operators, here-documents with no end, a null byte, a line of 100,000 characters, 2,000 parentheses, 500 nested substitutions, 2,000 refspecs, characters that are not ASCII | `test_it_never_exits_other_than_0_or_2` | Exits 0 or 2, with no traceback |
| The settings in [templates/claude-settings.json](../templates/claude-settings.json) and in this repo, the empty approvals template, and the line in `.gitignore` | `Settings` | Each exactly as described here |

**What it does not claim.**

- Any spelling that is not a case above. Among them: a step run from a script, a Makefile, a git hook, an alias or another language; `git -c` and git config that change what a push does, such as `remote.*.mirror` or `push.followTags`; a variable or a pattern that names the program; `find -delete`, `rmdir`, `git clean`, `rsync --delete` and `rm` without `-r`; GraphQL mutations; `gh` aliases and extensions; options of `gh` before the command, such as `gh -R o/r release create`; `gh api` on `repositories/{id}/...`, and on the secrets and variables of an organization or a user; a workflow file that names an environment, which creates it when it runs; a tag pushed by a short name from a repository other than the one the command runs in.
- That a deletion inside the working tree is safe. It sees only where the operand resolves when it runs.
- Anything in a session of another harness, or at a person's terminal. Codex and other harnesses do not run it.
- That the approvals file was written by the owner. The hook denies an agent's write to it through the cases above. An agent that writes it another way gets past it, like any other spelling.

## The tag ruleset

[templates/tag-ruleset.json](../templates/tag-ruleset.json) is the lock on moving and deleting a tag (`repo.tags-stay`, D-2026-11-19-tag-ruleset-scope). It is a repository ruleset in the form of GitHub's REST API, [Create a repository ruleset](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset):

- `target` `tag`, and `conditions.ref_name.include` `~ALL`, every tag.
- `enforcement` `active`.
- `rules`: `deletion` ("Only allow users with bypass permissions to delete matching refs"), `update` ("Only allow users with bypass permission to update matching refs") and `non_fast_forward` ("Prevent users with push access from force pushing to refs"). Not `creation`.
- `bypass_actors`: one, `actor_type` `RepositoryRole` with `actor_id` 5 and `bypass_mode` `always`. Observation (O): the documentation does not list the ids of the repository roles. Public reports and rulesets made in GitHub's settings page show the repository admin role as id 5. The read-back below shows what GitHub stored.

Creation is left open because the release workflow creates each tag with the built-in token of GitHub Actions, and a block on creation would stop it (O: GitHub's documentation does not say whether that token can be a bypass actor, and public reports say it cannot; see the decision). [release.py](release.py) only creates a tag, with one `POST` to `/repos/{owner}/{repo}/git/refs`, and never moves, deletes or edits one, so the ruleset does not touch a release.

**Applying it is the maintainer's.** Settings are the maintainer's, and the agents' account, with the role Write, cannot create a ruleset. The maintainer runs, under the maintainer's own login and from the root of a checkout:

```sh
gh api -X POST repos/fabian-von-tiedemann/ratchet/rulesets --input templates/tag-ruleset.json
```

or makes the same ruleset on the settings page: Rules, Rulesets, New tag ruleset, enforcement Active, target all tags, the rules "Restrict updates", "Restrict deletions" and "Block force pushes", and "Repository admin" on the bypass list.

**Reading it back.** The answer to the `POST` holds the ruleset's `id`. Then:

```sh
gh api repos/fabian-von-tiedemann/ratchet/rulesets/<id>
```

Under the maintainer's login, it shows `target` `tag`, `enforcement` `active`, `conditions` `~ALL`, the three rules and no `creation`, and the one bypass actor. Under the agents' account, `bypass_actors` is not shown, and `current_user_can_bypass` must be `never`.

**Applied and read back in this repo.** The maintainer applied the ruleset on 2026-11-19, as `tags-stay`. The answer to the maintainer's `POST` showed the one bypass actor, `[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]`. The control room read it back the same day with the agents' account: target `tag`, enforcement `active`, `conditions.ref_name.include` `["~ALL"]`, the rules `deletion`, `update` and `non_fast_forward` and no `creation`, `current_user_can_bypass` `never`, and `bypass_actors` null, because the role Write is not shown it. Not tried: deleting or moving a tag with the agents' account, which would put a published tag at risk if the rule did not apply. Tried: 0.7 is the first release under the ruleset, and the release workflow created the tag `v0.7` and its release with the built-in token, about two and a half hours after the ruleset was made. With the read-back recorded, `ratchet.irreversible-waits` is "built" in [REGISTER.md](../REGISTER.md) ([D-2026-11-19-tripwire-and-settings](../decisions/D-2026-11-19-tripwire-and-settings.md)).

**The case.** `TagRuleset` in [test_tripwire.py](test_tripwire.py) reads the file strictly and pins exactly these fields, these three rules in this order and no `creation`, and the one bypass actor. It also reads `release.py` and fails if it holds a `PATCH`, `DELETE` or `PUT`, or no longer creates a tag with its one `POST`.

## Why JSON

The rules are data that the checks and a project's CI must read. The format was chosen so that the checks need nothing but a Python interpreter:

- Python's standard library reads JSON in every supported version. It reads TOML only from 3.11, and it does not read YAML at all.
- The Python that ships with a common developer operating system is older than 3.11. A check that needs a newer interpreter, or a package, is a check that does not get run.

The cost is that JSON has no comments and escapes quotation marks. The rules are one sentence per field, so it stays readable, and anything that needs explaining belongs in the changelog or in a decision.
