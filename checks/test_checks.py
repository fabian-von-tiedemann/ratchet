"""Every check must fail on the fault it claims to catch (ratchet.test-can-fail).

    python3 -m unittest discover -s checks -v

Each fixture under checks/fixtures/ carries one fault, and the test names the
message the check must give for it. Among them is every way that reviews have
found to hide something from a check. A test loads a fixture through FixtureTest,
which copies it into a scratch directory: checks/expected_tests.py fails if a fixture
is not loaded by a test that passes (ratchet.expected-tests-ran). Standard library only.
"""

import json
import os
import re
import shlex
import shutil
import string
import subprocess
import sys
import tempfile
import unicodedata
import unittest
import unittest.mock

from suite_runner import FixtureTest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REGISTERS = os.path.join(HERE, "fixtures", "register")
VERSION = "must be exactly a version like"
NOT_GENERATED = "REGISTER.md: is not what register.json generates"
NOT_UTF8 = "is not valid UTF-8"
EMOJI_NAME = "which is a name between two colons"


def outside(field, code):
    return "%s holds U+%s, which is not among the characters a value may hold" % (field, code)


# The characters a value may hold, written out a second time and in another way than in registry.py.
LETTERS_LEFT_OUT = {0xD7, 0xF7, 0x132, 0x133, 0x13F, 0x140, 0x149, 0x17F, 0x1F1, 0x1F2, 0x1F3} | set(range(0x1C0, 0x1CD))
LATIN_LETTERS = (
    set(string.ascii_letters)
    | set(chr(code) for code in range(0xC0, 0x250) if code not in LETTERS_LEFT_OUT)
    | set(chr(code) for code in range(0x1E00, 0x1F00) if code not in (0x1E9A, 0x1E9B))
)
MARKS = set(string.punctuation) | set("\u00a1\u00a3\u00a7\u00ab\u00b0\u00b7\u00bb\u00bf\u2013\u2014\u2018\u2019\u201c\u201d\u201e\u20ac")
MAY_HOLD = LATIN_LETTERS | set(string.digits) | MARKS | {" "}
# Bytes that are not UTF-8: a byte that never occurs, a lone continuation byte, an overlong form,
# a surrogate, a sequence cut short, and a code point past the last one.
NOT_UTF8_BYTES = (b"\xff", b"\x80", b"\xc0\xaf", b"\xed\xa0\x80", b"\xe2\x82", b"\xf4\x90\x80\x80")

# Fixture name -> the text the register check must print for a fault in the data.
FAILING_DATA = {
    "changed-row": "the rule of ratchet.register-on-top differs from Ratchet",
    "changed-ratchet": "the ratchet of ratchet.register-on-top differs from Ratchet",
    "changed-source": "the source of ratchet.fresh-context differs from Ratchet",
    "trailing-space": "the rule of ratchet.root-cause differs from Ratchet",
    "unknown-key": "ratchet.ship-first is not a rule in Ratchet",
    "duplicate-row": "ratchet.root-cause is adopted twice",
    "no-rows": "no rules from Ratchet",
    "wrong-version": "the register follows Ratchet 0.0",
    "patch-version": VERSION,
    "version-alpha": VERSION,
    "version-suffix": VERSION,
    "version-dot-space": VERSION,
    "version-number": VERSION,
    "two-versions": "the field 'ratchet_version' appears twice in one object",
    "duplicate-field": "the field 'rule' appears twice in one object",
    "status-missing": "names a check, so it needs a status",
    "status-invalid": 'It must be "built" or "text only for now"',
    "built-nowhere": "is marked built but does not say where the check lives",
    "status-on-text-only": "ratchet.root-cause is text only in Ratchet. It cannot have a status",
    "unknown-field": "ratchet.root-cause: unknown field 'waived'",
    "unknown-top-field": "unknown field 'waivers'",
    "wrong-type": "ratchet.root-cause: every field must be a string",
    "prefix-outside": "ratchet.changelog uses Ratchet's prefix",
    "own-ratchet-missing": 'example.changelog: the ratchet is "Check: " and the check, or "Text only" and the reason',
    "own-text-only-no-reason": 'example.changelog: the ratchet is "Check: " and the check, or "Text only" and the reason',
    "own-check-names-nothing": 'example.changelog: the ratchet is "Check: " and the check, or "Text only" and the reason',
    "own-no-words": "example.changelog: the rule holds no words",
    "own-pipe": "example.changelog: rule must be one line, without |",
    "own-odd-backticks": "example.changelog: rule has a backtick without its pair",
    "own-double-backticks": "example.changelog: rule has two backticks in a row",
    "own-code-padded": "example.changelog: rule has code that is empty or has spaces at its ends",
    "own-zero-width": "example.changelog: " + outside("rule", "200B"),
    "own-control-character": "example.changelog: " + outside("rule", "0007"),
    "own-tab": "example.changelog: " + outside("rule", "0009"),
    "own-no-break-space": "example.changelog: " + outside("rule", "00A0"),
    "own-line-separator": "example.changelog: " + outside("rule", "2028"),
    "own-paragraph-separator": "example.changelog: " + outside("rule", "2029"),
    "own-combining-joiner": "example.changelog: " + outside("rule", "034F"),
    "own-variation-selector": "example.changelog: " + outside("rule", "FE0F"),
    "own-combining-accent": "example.changelog: " + outside("rule", "0301"),
    "own-hangul-filler": "example.changelog: " + outside("rule", "1160"),
    "own-braille-blank": "example.changelog: " + outside("rule", "2800"),
    "own-source-zero-width": "example.changelog: " + outside("source", "200B"),
    "own-full-width": "example.changelog: " + outside("rule", "FF1C"),
    "own-long-s": "example.changelog: " + outside("rule", "017F"),
    "own-mail-address": "example.changelog: rule has @ between two characters",
    "link-code-confusion": "example.changelog: rule has code that is empty or has spaces at its ends",
    "link-code-hidden-element": "example.changelog: rule has code that is empty or has spaces at its ends",
    "own-ratchet-link-code": "example.changelog: ratchet has code that is empty or has spaces at its ends",
    "own-source-link-code": "example.changelog: source has code that is empty or has spaces at its ends",
    "project-link-code": "project must be the project's name: it has code that is empty or has spaces at its ends",
    "where-link-code": "ratchet.register-on-top: where has code that is empty or has spaces at its ends",
    "project-surrogate": "project must be the project's name: it " + outside("", "D800").lstrip(),
    "project-no-name": "project must be the project's name: it holds no letter or digit",
    "where-hidden": "ratchet.register-on-top: " + outside("where", "200B"),
    "nested-too-deep": "not a valid data file: it is nested too deeply",
    "not-an-object": "the register must be one object",
    "not-json": "not a valid data file",
    "not-utf8": "not a valid data file: it " + NOT_UTF8,
    "own-rtl-punctuation": "example.changelog: " + outside("rule", "05BE"),
    "own-rtl-symbol": "example.changelog: " + outside("rule", "0608"),
    "own-rtl-question-mark": "example.changelog: " + outside("rule", "061F"),
    "own-rtl-letter": "example.changelog: " + outside("rule", "05D0"),
    "own-arabic-digit": "example.changelog: " + outside("rule", "0661"),
    "own-bidi-override": "example.changelog: " + outside("rule", "202E"),
    "own-bidi-isolate": "example.changelog: " + outside("rule", "2067"),
    "own-bidi-mark": "example.changelog: " + outside("rule", "200F"),
    "own-replacement-character": "example.changelog: " + outside("rule", "FFFD"),
    "own-object-replacement": "example.changelog: " + outside("rule", "FFFC"),
    "own-later-letter": "example.changelog: " + outside("rule", "1E4D0"),
    "own-musical-null": "example.changelog: " + outside("rule", "1D159"),
    "own-division-slash": "example.changelog: " + outside("rule", "2215"),
    "own-minus-sign": "example.changelog: " + outside("rule", "2212"),
    "own-greek-letter": "example.changelog: " + outside("rule", "03BF"),
    "own-cyrillic-letter": "example.changelog: " + outside("rule", "0430"),
    "own-han-letter": "example.changelog: " + outside("rule", "4E2D"),
    "own-click-letter": "example.changelog: " + outside("rule", "01C0"),
    "own-emoji-character": "example.changelog: " + outside("rule", "1F600"),
    "own-symbol-not-listed": "example.changelog: " + outside("rule", "2192"),
    "own-emoji-name": "example.changelog: rule has :example:, " + EMOJI_NAME,
    "own-emoji-name-plus": "example.changelog: rule has :+1:, " + EMOJI_NAME,
    "own-emoji-name-in-code": "example.changelog: rule has :example:, " + EMOJI_NAME,
    "own-time-with-seconds": "example.changelog: rule has :30:, " + EMOJI_NAME,
    "project-emoji-name": "project must be the project's name: it has :example:, " + EMOJI_NAME,
    "where-emoji-name": "ratchet.register-on-top: where has :example:, " + EMOJI_NAME,
    "version-other-digits": VERSION,
}

# Fixtures with a clean register.json and a REGISTER.md that is not what it generates.
FAILING_MARKDOWN = (
    "md-changed-row", "md-indented-row", "md-indent-three", "md-indent-tab", "md-indented-duplicate",
    "md-no-leading-pipe", "md-no-outer-pipes", "md-single-cell-row", "md-comment-hides-row",
    "md-comment-fake-heading", "md-fake-heading-last", "md-escaped-pipe", "md-extra-text",
)


def run(script, *args, root=ROOT, cwd=None):
    result = subprocess.run(
        [sys.executable, os.path.join(root, "checks", script)] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, cwd=cwd,
    )
    return result.returncode, result.stdout


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8", newline="") as handle:
        return handle.read()


def scratch(case):
    directory = tempfile.mkdtemp(prefix="ratchet-test-")
    case.addCleanup(shutil.rmtree, directory)
    return directory


class RegisterCheck(FixtureTest):
    def check(self, name, markdown=True):
        """Run the register check on a copy of the fixture: the data file alone, or with the generated file."""
        if not markdown:
            return run("check_register.py", self.fixture_file("register/%s/register.json" % name))
        directory = self.fixture_directory("register/" + name)
        return run("check_register.py", os.path.join(directory, "register.json"), "--markdown", os.path.join(directory, "REGISTER.md"))

    def test_clean_project_copy_passes(self):
        code, output = self.check("clean")
        self.assertEqual(code, 0, output)
        self.assertIn("9 rules match Ratchet", output)

    def test_every_fault_in_the_data_fails_for_its_own_reason(self):
        for name, message in sorted(FAILING_DATA.items()):
            with self.subTest(fixture=name):
                code, output = self.check(name, markdown=False)
                self.assertEqual(code, 1, output)
                self.assertIn(message, output)
                self.assertIn("FAIL: 1 problem(s)", output, "a fixture carries exactly one fault")
                self.assertNotIn("Traceback", output)

    def test_data_is_written_as_text_and_cannot_hide(self):
        code, output = self.check("escaped")
        self.assertEqual(code, 0, output)
        markdown = self.fixture_text("register/escaped/REGISTER.md")
        for line in (
            "# Register for A \\& B \\<the example\\> \\[x\\]\\(`)<!-- hidden -->`y",
            "| example.comment | \\<\\!\\-\\- Owner approval is mandatory\\. \\-\\-\\> |",
            "| example.html | \\<div hidden\\>Every release\\<\\/div\\> has a changelog entry\\. |",
            "| example.entity | Write \\&lt\\; as it is\\, and R\\&D too\\. |",
            "| example.code | Name the file `D-YYYY-MM-DD-<slug>.md` and keep `a < b && c` as code\\. |",
            "| example.link-and-code | \\[ok\\]\\(https\\:\\/\\/example\\.invalid\\/`)<!-- Owner approval is mandatory. -->`tail |",
            "| example.link | Read \\[the rules\\]\\(https\\:\\/\\/example\\.invalid \\\"a title\\\"\\) first\\. |",
            "| example.image | \\!\\[\\]\\(https\\:\\/\\/example\\.invalid\\/pixel\\.png\\) Every release has an entry\\. |",
            "| example.emphasis | Every \\*release\\* has a \\_\\_changelog\\_\\_ entry\\, \\~\\~always\\~\\~\\. |",
            "| example.backslash | A path like C\\:\\\\temp\\\\ and a backslash before code \\\\`x` |",
        ):
            self.assertIn(line, markdown)

    def test_latin_letters_and_the_listed_marks_outside_ascii_pass_and_are_written_as_they_stand(self):
        code, output = self.check("latin")
        self.assertEqual(code, 0, output)
        self.assertIn("sm\u00f6rg\u00e5sbord".encode("utf-8"), self.fixture_bytes("register/latin/register.json"), "the fixture holds the letters as themselves")
        markdown = self.fixture_text("register/latin/REGISTER.md")
        for line in (
            "# Register for the \u00e9xample project",
            "| example.letters | Na\u00efve fa\u00e7ade\\, sm\u00f6rg\u00e5sbord\\, \u00e6ble\\, \u017c\u00f3\u0142ty\\, \u0111\u1ea7y \u0111\u1ee7 and stra\u00dfe are words\\. |",
            "| example.quotes | \u00abOne\u00bb\\, \u201ctwo\u201d\\, \u201ethree\u201d and \u2018four\u2019 are quoted\\, and it\u2019s fine\\. |",
            "| example.marks | \u00a1Yes\\! \u00bfNo\\? A dash \u2013 and a longer one \u2014 then \u00a7 5\\, 20 \u00b0\\, \u00a3 5\\, \u20ac 5 and a\u00b7b\\. |",
        ):
            self.assertIn(line, markdown)

    def test_a_reference_to_a_person_an_issue_or_a_commit_passes_and_is_written_as_text(self):
        # A boundary that is stated, not a protection: see "What it does not claim" in checks/README.md.
        code, output = self.check("references")
        self.assertEqual(code, 0, output)
        markdown = self.fixture_text("register/references/REGISTER.md")
        for line in (
            "| example.person | Ask \\@someone and \\@some\\-group\\/some\\-team before every release\\. |",
            "| example.person-first | \\@someone approves every release\\. |",
            "| example.issue | Every release closes \\#123 and some\\-group\\/some\\-repo\\#123\\. |",
            "| example.commit | Every release names 0123abc and 0123456789abcdef0123456789abcdef01234567\\. |",
        ):
            self.assertIn(line, markdown)

    def test_the_characters_a_value_may_hold_are_one_fixed_list(self):
        sys.path.insert(0, HERE)
        import registry
        self.assertEqual(registry.ALLOWED, frozenset(MAY_HOLD))
        self.assertEqual(len(registry.ALLOWED), 741)
        self.assertFalse(hasattr(registry, "unicodedata"), "what a value may hold does not depend on the interpreter's Unicode tables")

    def test_every_character_outside_the_list_is_refused_and_named(self):
        sys.path.insert(0, HERE)
        import registry
        accepted = set()
        for code in range(0x110000):
            character = chr(code)
            problem = registry.text_problem("a" + character + "a")
            if problem is None:
                accepted.add(character)
            elif character not in MAY_HOLD and character not in "\r\n":
                self.assertIn("holds U+%04X, which is not among the characters" % code, problem)
        # Three of the listed marks have a meaning of their own and are refused where they stand here.
        self.assertEqual(accepted, MAY_HOLD - set("|`@"))

    def test_no_character_a_value_may_hold_reorders_the_line_or_is_a_compatibility_form(self):
        # Read from this interpreter's own Unicode tables, as a check on the list, on every supported version.
        for character in sorted(MAY_HOLD - {" "}):
            with self.subTest(character="U+%04X" % ord(character)):
                # Left to right, a European number, its separators and terminators, or neutral: never R, AL, AN or a control.
                self.assertIn(unicodedata.bidirectional(character), ("L", "EN", "ES", "ET", "CS", "ON"))
                self.assertEqual(unicodedata.normalize("NFKC", character), character)
                self.assertEqual(unicodedata.normalize("NFC", character), character)
                self.assertEqual(unicodedata.combining(character), 0)
                if character in LATIN_LETTERS:
                    self.assertTrue(character.isalpha() and "LATIN" in unicodedata.name(character))
                elif character in MARKS:
                    self.assertIn(unicodedata.category(character)[0], "PS")
                    self.assertFalse(character.isalnum())

    def test_no_two_characters_a_value_may_hold_join_into_another(self):
        # So a value made of them is in the normal forms NFC and NFKC as it stands.
        characters = "".join(sorted(MAY_HOLD))
        for first in characters:
            pairs = "".join(first + second for second in characters)
            self.assertEqual(unicodedata.normalize("NFC", pairs), pairs)
            self.assertEqual(unicodedata.normalize("NFKC", pairs), pairs)

    def test_a_name_between_two_colons_is_refused_and_other_colons_are_not(self):
        sys.path.insert(0, HERE)
        import registry
        for value in (":example:", "a :example: b", ":+1:", ":-1:", ":a_b:", ":1234:", "a:b:c", "`:example:`", "a `x:y:z` b", "12:30:00", "::a::", ":\u00e9:", ":smil\u00e9:", "`:\u00e9:`", ":\u1e9e1:"):
            with self.subTest(refused=value):
                self.assertIn(EMOJI_NAME, registry.text_problem(value) or "")
        for value in ("Check: a: b", "12:30", "a::b", ": a :", "https://example.invalid", "Text only: see `a:b`", ":a b:", ":a.b:", "a: b :c"):
            with self.subTest(accepted=value):
                self.assertIsNone(registry.text_problem(value))

    def test_a_name_needs_a_latin_letter_or_a_digit(self):
        sys.path.insert(0, HERE)
        import registry
        for value in ("a", "7", "\u00e9", "\u1ec7"):
            self.assertTrue(registry.WORD.search(value), ascii(value))
        for value in ("--", "\u00ab\u00bb", "\u2014", "_", " "):
            self.assertFalse(registry.WORD.search(value), ascii(value))

    def test_every_punctuation_mark_is_escaped_in_text_and_none_in_code(self):
        sys.path.insert(0, HERE)
        import registry
        marks = "!\"#$%&'()*+,-./:;<=>?@[\\]^_{|}~"
        self.assertEqual(registry.cell(marks), "".join("\\" + mark for mark in marks))
        self.assertEqual(registry.cell("a `" + marks + "` b"), "a `" + marks + "` b")
        self.assertEqual(registry.cell("plain words 123 åäö"), "plain words 123 åäö")
        self.assertEqual(len(marks) + 1, len(registry.PUNCTUATION), "every ASCII punctuation mark but the backtick")

    def test_no_text_makes_normalization_fail_with_a_traceback(self):
        sys.path.insert(0, HERE)
        import registry
        for value in ("Cafe\u0301", "\u0301", "\ud800", "\U0010ffff", "\ufb01", "\u2126", "\u1160", "a\u00a0b", "", "`", "``", "` `", "a`b`c`d", "x@y"):
            with self.subTest(value=ascii(value)):
                self.assertTrue(registry.text_problem(value) or value == "")

    def test_a_data_file_with_very_many_fields_is_read_in_linear_time(self):
        path = os.path.join(scratch(self), "register.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{" + ",".join('"field%d": 0' % number for number in range(300000)) + "}")
        result = subprocess.run([sys.executable, os.path.join(HERE, "check_register.py"), path],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
        self.assertEqual(result.returncode, 1, result.stdout[:300])
        self.assertIn("missing field 'project'", result.stdout)

    def test_a_generated_file_that_is_not_utf8_fails_and_says_so(self):
        code, output = self.check("md-not-utf8", markdown=False)
        self.assertEqual(code, 0, "the data in this fixture is clean:\n" + output)
        code, output = self.check("md-not-utf8")
        self.assertEqual(code, 1, output)
        self.assertIn("REGISTER.md: " + NOT_UTF8, output)
        self.assertIn("at byte 47 (0xFF)", output)
        self.assertIn("FAIL: 1 problem(s)", output)
        self.assertNotIn("Traceback", output)

    def test_no_bytes_that_are_not_utf8_are_read_as_text(self):
        directory = scratch(self)
        markdown, data = os.path.join(directory, "REGISTER.md"), os.path.join(directory, "register.json")
        clean = self.fixture_file("register/clean/register.json")
        clean_markdown = self.fixture_bytes("register/clean/REGISTER.md")
        clean_data = self.fixture_bytes("register/clean/register.json")
        for wrong in NOT_UTF8_BYTES:
            with self.subTest(generated_file=wrong):
                with open(markdown, "wb") as handle:
                    handle.write(clean_markdown.replace(b"Every rule", b"Every " + wrong + b" rule", 1))
                code, output = run("check_register.py", clean, "--markdown", markdown)
                self.assertEqual(code, 1, output)
                self.assertIn("REGISTER.md: " + NOT_UTF8, output)
                self.assertNotIn("Traceback", output)
            with self.subTest(data_file=wrong):
                with open(data, "wb") as handle:
                    handle.write(clean_data.replace(b"the example project", b"the example " + wrong + b" project", 1))
                code, output = run("check_register.py", data)
                self.assertEqual(code, 1, output)
                self.assertIn("not a valid data file: it " + NOT_UTF8, output)
                self.assertNotIn("Traceback", output)

    def test_the_replacement_character_in_the_data_does_not_stand_in_for_bytes_that_are_not_utf8(self):
        # The pair a review found: U+FFFD in a value, and a generated file with one wrong byte in its place.
        directory = scratch(self)
        register = json.loads(self.fixture_text("register/clean/register.json"))
        register["own"][0]["rule"] = "Every release \ufffd has a changelog entry."
        data, markdown = os.path.join(directory, "register.json"), os.path.join(directory, "REGISTER.md")
        with open(data, "w", encoding="utf-8") as handle:
            json.dump(register, handle, ensure_ascii=False)
        sys.path.insert(0, HERE)
        import check_register
        with open(markdown, "wb") as handle:
            handle.write(check_register.render(register).encode("utf-8").replace("\ufffd".encode("utf-8"), b"\xff"))
        code, output = run("check_register.py", data, "--markdown", markdown)
        self.assertEqual(code, 1, output)
        self.assertIn(outside("rule", "FFFD"), output)
        code, output = run("check_register.py", self.fixture_file("register/clean/register.json"), "--markdown", markdown)
        self.assertEqual(code, 1, output)
        self.assertIn("REGISTER.md: " + NOT_UTF8, output)

    def test_nothing_is_written_from_a_register_that_cannot_be_written(self):
        target = os.path.join(scratch(self), "REGISTER.md")
        code, output = run("check_register.py", self.fixture_file("register/project-surrogate/register.json"), "--write", target)
        self.assertEqual(code, 1, output)
        self.assertNotIn("Traceback", output)
        self.assertFalse(os.path.exists(target))

    def test_every_change_to_the_generated_file_fails(self):
        for name in FAILING_MARKDOWN:
            with self.subTest(fixture=name):
                code, output = self.check(name, markdown=False)
                self.assertEqual(code, 0, "the data in this fixture is clean:\n" + output)
                code, output = self.check(name)
                self.assertEqual(code, 1, output)
                self.assertIn(NOT_GENERATED, output)
                self.assertIn("FAIL: 1 problem(s)", output)

    def test_a_missing_generated_file_fails(self):
        code, output = self.check("md-missing")
        self.assertEqual(code, 1, output)
        self.assertIn("REGISTER.md: the file is missing. Generate it from register.json", output)

    def test_every_fixture_has_an_expectation(self):
        self.assertEqual(sorted(os.listdir(REGISTERS)), sorted(
            list(FAILING_DATA) + list(FAILING_MARKDOWN) + ["clean", "escaped", "latin", "references", "md-missing", "md-not-utf8"]))

    def test_the_template_and_this_repos_register_pass(self):
        code, output = run("check_register.py", os.path.join(ROOT, "templates", "register.json"))
        self.assertEqual(code, 0, output)
        code, output = run("check_register.py", os.path.join(ROOT, "register.json"), "--markdown", os.path.join(ROOT, "REGISTER.md"))
        self.assertEqual(code, 0, output)

    def test_a_missing_register_is_not_a_pass(self):
        code, output = run("check_register.py", os.path.join(scratch(self), "register.json"))
        self.assertEqual(code, 2, output)

    def test_writing_gives_the_file_that_the_check_accepts(self):
        directory = scratch(self)
        target = os.path.join(directory, "REGISTER.md")
        data = self.fixture_file("register/clean/register.json")
        code, output = run("check_register.py", data, "--write", target)
        self.assertEqual(code, 0, output)
        with open(target, encoding="utf-8", newline="") as handle:
            self.assertEqual(handle.read(), self.fixture_text("register/clean/REGISTER.md"))

    def test_nothing_is_written_from_a_register_that_fails(self):
        target = os.path.join(scratch(self), "REGISTER.md")
        code, output = run("check_register.py", self.fixture_file("register/changed-row/register.json"), "--write", target)
        self.assertEqual(code, 1, output)
        self.assertFalse(os.path.exists(target))

    def test_line_endings_of_the_generated_file_do_not_matter(self):
        target = os.path.join(scratch(self), "REGISTER.md")
        with open(target, "w", encoding="utf-8", newline="") as handle:
            handle.write(self.fixture_text("register/clean/REGISTER.md").replace("\n", "\r\n"))
        code, output = run("check_register.py", self.fixture_file("register/clean/register.json"), "--markdown", target)
        self.assertEqual(code, 0, output)

    def test_a_register_typed_by_hand_passes_and_its_changed_copy_fails(self):
        handwritten = self.fixture_directory("handwritten")
        source = os.path.join(handwritten, "ratchet.json")
        code, output = run("check_register.py", "--source", source, os.path.join(handwritten, "register.json"),
                           "--markdown", os.path.join(handwritten, "REGISTER.md"))
        self.assertEqual(code, 0, output)
        self.assertIn("2 rules match Ratchet 9.9 (2 core, 0 experimental). 1 name a check: 1 built", output)
        code, output = run("check_register.py", "--source", source, os.path.join(handwritten, "register-changed.json"))
        self.assertEqual(code, 1, output)
        self.assertIn("the rule of ratchet.example-one differs from Ratchet 9.9", output)
        self.assertIn("FAIL: 1 problem(s)", output)


class RepoCopy:
    """A copy of this repo that a test may break."""

    def setUp(self):
        self.copy = os.path.join(tempfile.mkdtemp(prefix="ratchet-test-"), "ratchet")
        shutil.copytree(ROOT, self.copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.addCleanup(shutil.rmtree, os.path.dirname(self.copy))

    def edit(self, name, old, new, count=1):
        path = os.path.join(self.copy, name)
        with open(path, encoding="utf-8", newline="") as handle:
            text = handle.read()
        self.assertIn(old, text, "the test expects %r in %s" % (old, name))
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text.replace(old, new, count))

    def append(self, name, text):
        with open(os.path.join(self.copy, name), "a", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def assert_check_fails(self, message):
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn(message, output)
        self.assertNotIn("Traceback", output)



class GeneratedText(RepoCopy, unittest.TestCase):
    def test_untouched_copy_passes(self):
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def test_line_endings_are_read_the_same_by_the_generator_and_the_register_check(self):
        for name in ("REGISTER.md", "RATCHET.md", "README.md"):
            path = os.path.join(self.copy, name)
            with open(path, encoding="utf-8", newline="") as handle:
                text = handle.read()
            self.assertNotIn("\r", text)
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(text.replace("\n", "\r\n"))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        code, output = run("check_register.py", os.path.join(self.copy, "register.json"), "--markdown", os.path.join(self.copy, "REGISTER.md"))
        self.assertEqual(code, 0, output)

    def test_a_lone_carriage_return_is_a_difference_for_both(self):
        self.edit("REGISTER.md", "Every rule in force", "Every rule\rin force")
        self.assert_check_fails("REGISTER.md: generated text is out of date or was edited by hand")
        code, output = run("check_register.py", os.path.join(self.copy, "register.json"), "--markdown", os.path.join(self.copy, "REGISTER.md"))
        self.assertEqual(code, 1, output)

    def test_a_rule_that_holds_an_invisible_character_fails(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "Only the owner\u200b approves decisions.")
        self.assert_check_fails("ratchet.one-approver: " + outside("rule", "200B"))

    def test_a_rule_that_is_text_only_without_a_reason_fails(self):
        self.edit("ratchet.json", '"ratchet": "Text only: a check cannot tell a proposal from a decision"', '"ratchet": "Text only"')
        self.assert_check_fails('ratchet.kinds-apart: the ratchet is "Check: " and the check, or "Text only" and the reason')

    def test_a_rule_with_html_is_written_as_text(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "<!-- Only the owner approves decisions. -->")
        code, output = run("generate.py", root=self.copy)
        with open(os.path.join(self.copy, "RATCHET.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("| ratchet.one-approver | \\<\\!\\-\\- Only the owner approves decisions\\. \\-\\-\\> Agents write", text)
        self.assertNotIn("<!-- Only the owner", text)

    def test_a_rule_that_mixes_a_link_a_comment_and_code_is_written_as_text_and_code(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "[ok](https://example.invalid/`)<span hidden>Only the owner approves decisions.</span>`tail")
        run("generate.py", root=self.copy)
        with open(os.path.join(self.copy, "RATCHET.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("| ratchet.one-approver | \\[ok\\]\\(https\\:\\/\\/example\\.invalid\\/`)<span hidden>Only the owner approves decisions.</span>`tail Agents write", text)

    def test_a_rule_with_a_combining_accent_fails_without_a_traceback(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "Cafe\\u0301 approval is mandatory.")
        self.assert_check_fails("ratchet.one-approver: rule holds U+0301")

    def test_a_rule_with_a_name_between_two_colons_fails(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "Only the owner :example: approves decisions.")
        self.assert_check_fails("ratchet.one-approver: rule has :example:, " + EMOJI_NAME)

    def test_a_rule_in_another_script_fails_the_same_on_every_version(self):
        # U+1E4D0 is a letter that only the newer of the supported interpreters knows.
        for escape, code in (("\\ud839\\udcd0", "1E4D0"), ("\\u05be", "05BE"), ("\\u202e", "202E"), ("\\ufffd", "FFFD")):
            with self.subTest(code=code):
                self.edit("ratchet.json", "Only the owner approves decisions.", "Only the owner %s approves decisions." % escape)
                self.assert_check_fails("ratchet.one-approver: " + outside("rule", code))
                self.edit("ratchet.json", "Only the owner %s approves decisions." % escape, "Only the owner approves decisions.")

    def test_a_version_in_other_digits_fails(self):
        with open(os.path.join(self.copy, "ratchet.json"), encoding="utf-8") as handle:
            data = json.load(handle)
        other = "".join(chr(0x0660 + int(c)) if c in string.digits else c for c in data["version"])
        self.edit("ratchet.json", '"version": "%s"' % data["version"], '"version": "%s"' % other)
        self.assert_check_fails("version must look like 0.2")

    def test_a_file_that_is_not_utf8_fails_the_check_of_the_generated_text(self):
        for name in ("README.md", "CHANGELOG.md", "REGISTER.md", "ratchet.json", "sources.json", "register.json", os.path.join(".github", "CODEOWNERS")):
            path = os.path.join(self.copy, name)
            with open(path, "rb") as handle:
                original = handle.read()
            with self.subTest(file=name):
                with open(path, "wb") as handle:
                    handle.write(original + b"\n# \xff\n" if name.endswith("CODEOWNERS") else original.replace(b"e", b"\xff", 1))
                code, output = run("generate.py", "--check", root=self.copy)
                self.assertEqual(code, 1, output)
                self.assertIn(name.replace(os.sep, "/"), output)
                self.assertIn(NOT_UTF8, output)
                self.assertNotIn("Traceback", output)
                code, output = run("generate.py", root=self.copy)
                self.assertEqual(code, 1, output)
                self.assertNotIn("Traceback", output)
                with open(path, "rb") as handle:
                    self.assertIn(b"\xff", handle.read(), "a file that cannot be read is left as it is")
            with open(path, "wb") as handle:
                handle.write(original)

    def test_a_source_of_the_wrong_kind_fails_without_a_traceback(self):
        path = os.path.join(self.copy, "sources.json")
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        data["sources"][0]["commit"] = [data["sources"][0]["commit"]]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        self.assert_check_fails("sources.json: source google/elephant-goldfish-model: the commit must be a full 40-character sha")

    def sources_text(self):
        with open(os.path.join(self.copy, "sources.json"), encoding="utf-8", newline="") as handle:
            return handle.read()

    def test_sources_json_is_read_strictly(self):
        # D-2026-11-19-batched-releases, choice 3: the list of sources is a data file of its own, read as every data file is.
        valid = self.sources_text()
        self.assertTrue(valid.startswith('{\n  "sources": [\n'))
        cases = {
            "a field twice": (valid.replace('{\n  "sources": [', '{\n  "sources": [],\n  "sources": [', 1),
                              "sources.json: not a valid data file: the field 'sources' appears twice in one object"),
            "an unknown field": (valid.replace('{\n  "sources"', '{\n  "rules": [],\n  "sources"', 1), "sources.json: unknown field 'rules'"),
            "no field sources": ('{}\n', "sources.json: missing field 'sources'"),
            "not an object": ("[]\n", "sources.json: the top level must be an object"),
            "a list of the wrong kind": ('{"sources": {}}\n', "sources.json: sources must be a list"),
            "NaN": ('{"sources": NaN}\n', "sources.json: not a valid data file: NaN is not allowed"),
            "not JSON": (valid[:-3], "sources.json: not a valid data file"),
            "a name twice": (valid.replace('"name": "pstack"', '"name": "obra/superpowers"'), "sources.json: source obra/superpowers: the name is used twice"),
        }
        path = os.path.join(self.copy, "sources.json")
        for case, (text, message) in cases.items():
            with self.subTest(case=case):
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(text)
                self.assert_check_fails(message)
        os.remove(path)
        self.assert_check_fails("sources.json: not a valid data file")

    def test_the_sources_in_ratchet_md_come_from_sources_json(self):
        self.edit("sources.json", '"license": "Apache-2.0"', '"license": "Apache-2.0, as read again"')
        self.assert_check_fails("RATCHET.md: generated text is out of date or was edited by hand")
        code, output = run("generate.py", root=self.copy)
        self.assertEqual(code, 0, output)
        with open(os.path.join(self.copy, "RATCHET.md"), encoding="utf-8") as handle:
            self.assertIn("| Apache\\-2\\.0\\, as read again |", handle.read())
        with open(os.path.join(self.copy, "ratchet.json"), encoding="utf-8") as handle:
            self.assertNotIn("as read again", handle.read())

    def test_ratchet_json_holds_no_sources_and_no_date(self):
        for field, value in (("sources", "[]"), ("date", '"2026-11-19"')):
            with self.subTest(field=field):
                self.edit("ratchet.json", '  "experimental_cap"', '  "%s": %s,\n  "experimental_cap"' % (field, value))
                self.assert_check_fails("ratchet.json: unknown field %r" % field)
                self.edit("ratchet.json", '  "%s": %s,\n  "experimental_cap"' % (field, value), '  "experimental_cap"')

    def test_a_rule_cites_its_sources_by_their_names_in_sources_json(self):
        with open(os.path.join(self.copy, "ratchet.json"), encoding="utf-8") as handle:
            rules = json.load(handle)["rules"]
        cited = [rule for rule in rules if rule["source"]]
        self.assertTrue(cited)
        self.edit("ratchet.json", '"source": "pstack `principle-attack-the-premise`"', '"source": "pstak `principle-attack-the-premise`"')
        self.assert_check_fails('ratchet.json: ratchet.two-rounds: the source cites "pstak", which is not the name of a source in sources.json. '
                                'A source is a list of names from sources.json, each with what is taken from it, separated by "; "')
        self.edit("ratchet.json", '"source": "pstak `principle-attack-the-premise`"', '"source": "pstack `principle-attack-the-premise`"')
        # A source that a rule cites cannot leave sources.json.
        with open(os.path.join(self.copy, "sources.json"), encoding="utf-8") as handle:
            data = json.load(handle)
        data["sources"] = [source for source in data["sources"] if source["name"] != "obra/superpowers"]
        with open(os.path.join(self.copy, "sources.json"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2) + "\n")
        self.assertNotIn("Traceback", run("generate.py", root=self.copy)[1])
        self.assert_check_fails('the source cites "obra/superpowers", which is not the name of a source in sources.json')

    def test_every_source_is_cited_by_a_rule_as_written(self):
        # Every citation in today's rules is read the same way: names from sources.json, separated by "; ".
        with open(os.path.join(self.copy, "ratchet.json"), encoding="utf-8") as handle:
            rules = json.load(handle)["rules"]
        with open(os.path.join(self.copy, "sources.json"), encoding="utf-8") as handle:
            names = set(source["name"] for source in json.load(handle)["sources"])
        cited = set()
        for rule in rules:
            for part in filter(None, rule["source"].split("; ")):
                cited.add(re.split(r"[ ,]", part, 1)[0])
        self.assertEqual(cited, names)

    def test_a_glossary_file_in_the_repo_changes_nothing(self):
        with open(os.path.join(self.copy, "glossary.json"), "w", encoding="utf-8") as handle:
            handle.write("{}")
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def test_a_table_row_edited_by_hand_fails(self):
        self.edit("RATCHET.md", "Only the owner approves decisions", "The owner usually approves decisions")
        self.assert_check_fails("RATCHET.md: generated text is out of date or was edited by hand")

    def test_a_rule_changed_without_regenerating_fails(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "The owner usually approves decisions.")
        self.assert_check_fails("RATCHET.md: generated text is out of date or was edited by hand")

    def test_a_count_edited_by_hand_fails(self):
        self.edit("README.md", "are text only (", "are text only, down to (")
        self.assert_check_fails("README.md: generated text is out of date or was edited by hand")

    def test_a_fixture_edited_by_hand_fails(self):
        self.edit(os.path.join("checks", "fixtures", "register", "changed-row", "register.json"), ", where practical.", ".")
        self.assert_check_fails("generated text is out of date or was edited by hand")

    def test_this_repos_register_edited_by_hand_fails(self):
        self.edit("REGISTER.md", "| ratchet.no-secrets | text only for now |", "| ratchet.no-secrets | built |")
        self.assert_check_fails("REGISTER.md: generated text is out of date or was edited by hand")

    def test_this_repos_register_data_with_a_changed_rule_fails(self):
        self.edit("register.json", "Only the owner approves decisions.", "The owner usually approves decisions.")
        self.assert_check_fails("register.json: the rule of ratchet.one-approver differs from Ratchet")

    def test_a_row_changed_behind_a_removed_end_marker_fails(self):
        self.edit("CONTROL-ROOM.md", "The control room does not build the product", "The control room builds the product")
        self.edit("CONTROL-ROOM.md", "<!-- /generated -->", "<!-- broken -->", count=-1)
        self.assert_check_fails("CONTROL-ROOM.md: the markers of the generated blocks are broken")

    def test_a_removed_start_marker_fails(self):
        self.edit("CONTROL-ROOM.md", "<!-- generated:table control-room -->", "<!-- broken -->")
        self.assert_check_fails("CONTROL-ROOM.md: the markers of the generated blocks are broken")

    def test_a_count_block_replaced_by_plain_text_fails(self):
        path = os.path.join(self.copy, "README.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        changed, found = re.subn(r"<!-- generated:count -->.*?<!-- /generated -->", "There are zero text-only rules (0%).", text, flags=re.S)
        self.assertEqual(found, 1)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(changed)
        self.assert_check_fails("README.md: must hold exactly these generated blocks, once each: count, reference-checks, start. Missing: count")

    def test_a_block_added_twice_fails(self):
        self.edit("SELF-IMPROVEMENT.md", "## Ratchet's own count", "<!-- generated:count -->\n<!-- /generated -->\n\n## Ratchet's own count")
        self.assert_check_fails("SELF-IMPROVEMENT.md: must hold exactly these generated blocks")

    def test_a_table_inside_a_comment_fails(self):
        self.edit("CONTROL-ROOM.md", "<!-- generated:table control-room -->", "<!--\n<!-- generated:table control-room -->")
        self.assert_check_fails("CONTROL-ROOM.md:")
        self.assert_check_fails("the only comments here are the markers of generated blocks")

    def test_a_table_inside_a_code_block_fails(self):
        self.edit("CONTROL-ROOM.md", "<!-- generated:table control-room -->", "```text\n<!-- generated:table control-room -->")
        self.assert_check_fails("a code block here opens and closes with ``` alone")

    def test_a_table_inside_a_plain_code_block_fails(self):
        self.edit("CONTROL-ROOM.md", "<!-- generated:table control-room -->", "```\n<!-- generated:table control-room -->")
        self.assert_check_fails("a generated block inside a code block")

    def test_a_table_inside_a_hidden_element_fails(self):
        self.edit("CONTROL-ROOM.md", "<!-- generated:table control-room -->", "<div hidden>\n\n<!-- generated:table control-room -->")
        self.edit("CONTROL-ROOM.md", "<!-- /generated -->", "<!-- /generated -->\n\n</div>", count=-1)
        self.assert_check_fails('a line here does not start with "<"')

    def test_a_marker_with_text_after_it_fails(self):
        self.edit("CONTROL-ROOM.md", "<!-- /generated -->", "<!-- /generated --> and more", count=-1)
        self.assert_check_fails("the only comments here are the markers of generated blocks")

    def test_a_missing_file_with_generated_blocks_fails(self):
        os.remove(os.path.join(self.copy, "README.md"))
        self.assert_check_fails("README.md: the file is missing")

    def test_a_malformed_data_file_fails_without_a_traceback(self):
        path = os.path.join(self.copy, "ratchet.json")
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        data["parts"] = None
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        self.assert_check_fails("parts must be a list")

    def test_a_rule_written_twice_in_the_data_fails(self):
        self.edit("ratchet.json", '"key": "ratchet.one-approver",', '"key": "ratchet.one-approver",\n      "rule": "Anyone approves.",')
        self.assert_check_fails("the field 'rule' appears twice in one object")

    def test_a_label_that_disagrees_with_its_ratchet_fails(self):
        self.edit("ratchet.json", '"ratchet": "Text only: a check cannot tell a proposal from a decision"', '"ratchet": "Check: a check tells them apart"')
        self.assert_check_fails("ratchet.kinds-apart: a text-only rule has a ratchet that starts with")

    def test_a_mention_of_a_key_that_is_not_a_rule_fails(self):
        self.edit("CONTROL-ROOM.md", "`ratchet.checks-owner-read`", "`ratchet.checks-owner-reads`")
        self.assert_check_fails("ratchet.checks-owner-reads is not a rule in ratchet.json")

    def test_an_inline_link_that_leads_nowhere_fails(self):
        self.edit(os.path.join("checks", "README.md"), "](../ratchet.json)", "](ratchet.json)")
        self.assert_check_fails("checks/README.md")
        self.assert_check_fails("the link to ratchet.json leads nowhere")

    def test_a_link_definition_that_leads_nowhere_fails(self):
        self.append("README.md", "\n[Missing source][missing]\n\n[missing]: checks/does-not-exist.py\n")
        self.assert_check_fails("the link to checks/does-not-exist.py leads nowhere")

    def test_the_links_to_the_reference_checks_lead_somewhere(self):
        for name in ("README.md", os.path.join("checks", "README.md")):
            text = read(name)
            block = text[text.index("<!-- generated:reference-checks -->"):]
            block = block[:block.index("<!-- /generated -->")]
            targets = re.findall(r"\]\(([^)]+)\)", block)
            self.assertTrue(targets, name)
            for target in targets:
                with self.subTest(document=name, target=target):
                    self.assertTrue(os.path.isfile(os.path.join(ROOT, os.path.dirname(name), target)))

    def test_a_changelog_behind_the_version_fails(self):
        self.edit("ratchet.json", '"version": "', '"version": "9')
        self.assert_check_fails("CHANGELOG.md: the first entry must be")

    def test_only_the_first_entry_of_the_changelog_is_generated(self):
        # The count under the released heading of 0.3 was rewritten when every entry was generated.
        code, output = run("generate.py", root=self.copy)
        self.assertEqual(code, 0, output)
        with open(os.path.join(self.copy, "CHANGELOG.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(text, read("CHANGELOG.md"))
        released = text[text.index("## 0.3 (2026-11-16)"):]
        self.assertIn("Ratchet 0.3, computed from `ratchet.json`: the core has 35 rules.", released)
        self.assertIn("Outside the core there are 20 experimental rules: 9 name a check", released)

    def test_a_count_in_a_released_entry_is_not_checked_against_the_data(self):
        self.edit("CHANGELOG.md", "Outside the core there are 20 experimental rules", "Outside the core there are 19 experimental rules")
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def test_a_first_entry_without_its_count_fails(self):
        text = read("CHANGELOG.md")
        first = text[:text.index("## 0.3 (")]
        block = first[first.index("<!-- generated:count -->"):first.index("<!-- /generated -->") + len("<!-- /generated -->")]
        self.edit("CHANGELOG.md", block + "\n", "")
        self.assert_check_fails("CHANGELOG.md: the first entry must hold exactly these generated blocks, once each: count. Missing: count")

    def test_a_count_in_the_first_entry_edited_by_hand_fails(self):
        version = json.loads(read("ratchet.json"))["version"]
        self.edit("CHANGELOG.md", "Ratchet %s, computed" % version, "Ratchet %s (almost), computed" % version)
        self.assert_check_fails("CHANGELOG.md: generated text is out of date or was edited by hand")

    def test_a_heading_of_another_form_fails(self):
        for heading in ("## Unreleased", "## 0.3", "## 0.3 (soon)", "## 0.3  (2026-11-16)"):
            with self.subTest(heading=heading):
                self.setUp()
                self.edit("CHANGELOG.md", "## 0.3 (2026-11-16)\n", heading + "\n")
                self.assert_check_fails("CHANGELOG.md: %r is not the heading of an entry" % heading)

    def test_the_first_entry_may_be_unreleased_and_then_the_readme_fetches_the_newest_release(self):
        # D-2026-11-19-batched-releases, choice 1. The README never fetches a tag that does not exist yet.
        version, fetched = first_entry(self.copy)
        self.assertNotEqual(version, fetched)
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        with open(os.path.join(self.copy, "RATCHET.md"), encoding="utf-8") as handle:
            self.assertIn("Version %s, not yet released. See [CHANGELOG.md](CHANGELOG.md)." % version, handle.read())
        self.edit("README.md", "--branch v%s " % fetched, "--branch v%s " % version)
        self.assert_check_fails(fetch_problem(fetched, 0, 1))

    def test_the_entry_given_its_date_is_the_release_and_the_readme_fetches_it(self):
        version, fetched = first_entry(self.copy)
        self.edit("CHANGELOG.md", "## %s (unreleased)" % version, "## %s (2026-12-01)" % version)
        self.assert_check_fails(fetch_problem(version, 0, 1))
        self.assert_check_fails("RATCHET.md: generated text is out of date or was edited by hand")
        self.assertEqual(first_entry(self.copy, "2026-12-01"), (version, version))
        with open(os.path.join(self.copy, "RATCHET.md"), encoding="utf-8") as handle:
            self.assertIn("Version %s, 2026-12-01. See [CHANGELOG.md](CHANGELOG.md)." % version, handle.read())
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def test_the_pin_in_prose_does_not_stand_for_the_command(self):
        # Round 2 of PR #50, finding 3: the real command was changed to fetch the version that has no tag yet,
        # and prose holding the pin of the newest release was added. The check read the pin anywhere in the file.
        version, fetched = first_entry(self.copy)
        self.edit("README.md", "--branch v%s " % fetched, "--branch v%s " % version)
        self.append("README.md", "\nThe pin used to say --branch v%s here.\n" % fetched)
        self.assert_check_fails(fetch_problem(fetched, 0, 1))

    def test_the_command_outside_a_code_block_does_not_count(self):
        version, fetched = first_entry(self.copy)
        self.edit("README.md", "   %s\n" % (FETCH % fetched), "")
        self.append("README.md", "\n%s\n" % (FETCH % fetched))
        self.assert_check_fails(fetch_problem(fetched, 0, 1))

    def test_a_second_command_that_fetches_ratchet_fails(self):
        version, fetched = first_entry(self.copy)
        for other in (version, fetched):
            with self.subTest(other=other):
                self.setUp()
                first_entry(self.copy)
                self.append("README.md", "\n```sh\n%s\n```\n" % (FETCH % other))
                self.assert_check_fails(fetch_problem(fetched, 2, 0) if other == fetched else fetch_problem(fetched, 1, 1))

    def test_the_command_with_more_on_its_line_fails(self):
        version, fetched = first_entry(self.copy)
        self.edit("README.md", FETCH % fetched + "\n", FETCH % fetched + " && git -C .ratchet checkout main\n")
        self.assert_check_fails(fetch_problem(fetched, 0, 1))

    def test_the_command_in_a_code_block_not_marked_sh_does_not_count(self):
        version, fetched = first_entry(self.copy)
        self.edit("README.md", "```sh\n   %s" % (FETCH % fetched), "```\n   %s" % (FETCH % fetched))
        self.assert_check_fails(fetch_problem(fetched, 0, 1))

    def test_entries_out_of_order_fail_and_the_readme_fetches_the_highest_dated_version(self):
        # Review of PR #50, round 2, nonblocking: the generator took the first entry with a date for the pin, not the
        # newest version. With the intact entry of 0.6 moved above 0.8 and 0.7, a README pinned to v0.6 passed.
        version, fetched = first_entry(self.copy)
        path = os.path.join(self.copy, "CHANGELOG.md")
        with open(path, encoding="utf-8", newline="") as handle:
            text = handle.read()
        start, end = text.index("## 0.6 ("), text.index("## 0.5 (")
        moved, rest = text[start:end], text[:start] + text[end:]
        at = rest.index("## %s (" % fetched)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(rest[:at] + moved + rest[at:])
        self.edit("README.md", "--branch v%s " % fetched, "--branch v0.6 ")
        self.assert_check_fails("CHANGELOG.md: the entries must stand newest first, each version higher than the one after "
                                "it. '## 0.6 (2026-11-19)' stands before '## %s (2026-11-19)'" % fetched)
        self.assert_check_fails(fetch_problem(fetched, 0, 1))

    def test_a_version_twice_in_the_changelog_fails(self):
        self.edit("CHANGELOG.md", "## 0.6 (2026-11-19)\n", "## 0.7 (2026-11-19)\n")
        self.assert_check_fails("CHANGELOG.md: the entries must stand newest first, each version higher than the one after "
                                "it. '## 0.7 (2026-11-19)' stands before '## 0.7 (2026-11-19)'")

    def test_only_the_first_entry_may_be_unreleased(self):
        self.edit("CHANGELOG.md", "## 0.8 (2026-11-19)\n", "## 0.8 (unreleased)\n")
        self.assert_check_fails("CHANGELOG.md: '## 0.8 (unreleased)' is headed (unreleased), and only the first entry may be")

    def test_an_unreleased_heading_of_another_form_fails(self):
        for heading in ("## %s (Unreleased)", "## %s (unreleased) ", "## %s unreleased", "## Unreleased"):
            with self.subTest(heading=heading):
                self.setUp()
                version, _ = first_entry(self.copy)
                heading = heading % version if "%s" in heading else heading
                self.edit("CHANGELOG.md", "## %s (unreleased)\n" % version, heading + "\n")
                self.assert_check_fails('CHANGELOG.md: the first entry must be "## %s (<date>)" or "## %s (unreleased)", found %r'
                                        % (version, version, heading))
                self.assert_check_fails("CHANGELOG.md: %r is not the heading of an entry" % heading)


FETCH = "git clone --branch v%s https://github.com/fabian-von-tiedemann/ratchet .ratchet"


def fetch_problem(released, found, others):
    """The message of generate.py --check when the command in README.md that fetches Ratchet is not as it must be."""
    return ('README.md: the command that fetches Ratchet must be the line "%s", once, in a code block marked sh, and no other '
            "line may run git clone. v%s is the newest version with a date in CHANGELOG.md. Found that line %d times in such a "
            "block, and %d other lines that run git clone" % (FETCH % released, released, found, others))


def first_entry(copy, date=None):
    """Head the first entry of the changelog in a copy of this repo with date, or "(unreleased)" when date is None.

    Then point the command in README.md that fetches Ratchet at the newest version that has a date, and run
    generate.py. Returns (the version of the first entry, the version that README.md fetches). This is the state
    before and after the pull request that releases a version (D-2026-11-19-batched-releases), whichever the repo is in.
    """
    path = os.path.join(copy, "CHANGELOG.md")
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    headings = re.findall(r"(?m)^## ([0-9]+\.[0-9]+) \((?:unreleased|[0-9]{4}-[0-9]{2}-[0-9]{2})\)$", text)
    version = headings[0]
    text, count = re.subn(r"(?m)^## %s \((?:unreleased|[0-9]{4}-[0-9]{2}-[0-9]{2})\)$" % re.escape(version),
                          "## %s (%s)" % (version, date or "unreleased"), text, count=1)
    assert count == 1
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    fetched = version if date else headings[1]
    path = os.path.join(copy, "README.md")
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    assert len(re.findall(r"--branch v[0-9]+\.[0-9]+ ", text)) == 1
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(re.sub(r"--branch v[0-9]+\.[0-9]+ ", "--branch v%s " % fetched, text))
    code, output = run("generate.py", root=copy, cwd=copy)
    assert code == 0, output
    return version, fetched


class CodeOwnership(RepoCopy, unittest.TestCase):
    """.github/CODEOWNERS holds one rule: every path belongs to the maintainer."""

    owners = os.path.join(".github", "CODEOWNERS")
    message = '.github/CODEOWNERS: must hold exactly one rule, "* @fabian-von-tiedemann"'

    def replace(self, text):
        with open(os.path.join(self.copy, self.owners), "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_the_file_is_exactly_the_one_rule(self):
        rules = [line for line in read(".github", "CODEOWNERS").split("\n") if line.strip() and not line.startswith("#")]
        self.assertEqual(rules, ["* @fabian-von-tiedemann"])

    def test_an_owner_without_a_name_fails(self):
        self.replace("* @\n")
        self.assert_check_fails(self.message)

    def test_another_owner_fails(self):
        self.replace("* @agent-who-is-not-the-maintainer\n")
        self.assert_check_fails(self.message)

    def test_a_second_owner_on_the_line_fails(self):
        self.replace("* @fabian-von-tiedemann @agent-who-is-not-the-maintainer\n")
        self.assert_check_fails(self.message)

    def test_a_later_rule_that_takes_a_path_away_fails(self):
        self.replace("* @fabian-von-tiedemann\nchecks/ @agent-who-is-not-the-maintainer\n")
        self.assert_check_fails(self.message)

    def test_an_indented_rule_fails(self):
        self.replace(" * @fabian-von-tiedemann\n")
        self.assert_check_fails(self.message)

    def test_a_missing_file_fails(self):
        os.remove(os.path.join(self.copy, self.owners))
        self.assert_check_fails(self.message)


class StartPath(unittest.TestCase):
    """The README's start, run from an empty git repo with this repo as .ratchet, a git checkout with one commit."""

    def setUp(self):
        # A folder of a fixed, valid name: init.py takes the project's name from it, and tempfile's names are random.
        self.project = os.path.join(scratch(self), "demo-project")
        os.mkdir(self.project)
        ratchet = os.path.join(self.project, ".ratchet")
        shutil.copytree(ROOT, ratchet, ignore=shutil.ignore_patterns(".git", "__pycache__", "fixtures", ".claude"))
        for directory, command in ((self.project, ["init", "-q"]), (ratchet, ["init", "-q"]), (ratchet, ["add", "-A"]),
                                   (ratchet, ["commit", "-q", "-m", "Ratchet as it stands"])):
            subprocess.run(["git", "-c", "user.name=Ratchet test", "-c", "user.email=test@example.invalid",
                            "-c", "commit.gpgsign=false", "-c", "gc.auto=0", "-c", "maintenance.auto=false"] + command, cwd=directory, check=True, stdout=subprocess.DEVNULL,
                           env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"))
        self.readme = read("README.md")

    def run_in_project(self, command):
        words = shlex.split(command)
        self.assertEqual(words[0], "python3")
        result = subprocess.run([sys.executable] + words[1:], cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        return result.returncode, result.stdout

    def run_the_readme(self):
        commands = re.findall(r"(?m)^\s*(python3 \.ratchet/\S.*)$", self.readme)
        self.assertGreaterEqual(len(commands), 3)
        for command in commands:
            with self.subTest(command=command):
                code, output = self.run_in_project(command)
                self.assertEqual(code, 0, output)

    def test_every_command_in_the_readme_runs_in_an_empty_project(self):
        self.run_the_readme()

    def test_the_project_name_does_not_come_from_the_temporary_directory(self):
        # tempfile names a directory at random, and a name such as ratchet-test-_duwh33j is not a project name.
        # Forced here, so the README's commands pass whatever name tempfile gives.
        real = tempfile.mkdtemp

        def mkdtemp(prefix=None, **kwargs):
            return real(prefix=(prefix or "") + "_", suffix="_ not a name!", **kwargs)

        with unittest.mock.patch.object(tempfile, "mkdtemp", mkdtemp):
            self.setUp()
        self.assertIn("_ not a name!", self.project)
        self.run_the_readme()

    def test_every_step_in_the_workflow_template_runs_after_the_readme(self):
        self.run_the_readme()
        commands = re.findall(r"(?m)^\s+run: (python3 \.ratchet/\S.*)$", read("templates", "ratchet-checks.yml"))
        self.assertGreaterEqual(len(commands), 1)
        for command in commands:
            with self.subTest(command=command):
                code, output = self.run_in_project(command)
                self.assertEqual(code, 0, output)

    def test_the_readme_starts_with_init(self):
        commands = re.findall(r"(?m)^\s*(python3 \.ratchet/\S.*)$", self.readme)
        self.assertEqual(commands[:2], ["python3 .ratchet/checks/init.py --check", "python3 .ratchet/checks/init.py"])
        self.run_the_readme()
        for name in ("AGENTS.md", "register.json", "REGISTER.md", os.path.join(".github", "workflows", "ratchet.yml")):
            self.assertTrue(os.path.isfile(os.path.join(self.project, name)), name)

    def test_every_command_in_the_migration_runs_from_the_root_of_a_project(self):
        self.assertIn("cp .ratchet/templates/register.json register.json", read("MIGRATING.md"))
        shutil.copyfile(os.path.join(ROOT, "templates", "register.json"), os.path.join(self.project, "register.json"))
        commands = re.findall(r"(?m)^\s*(python3 \.ratchet/\S.*)$", read("MIGRATING.md"))
        self.assertEqual(len(commands), 3)
        for command in commands:
            with self.subTest(command=command):
                code, output = self.run_in_project(command)
                self.assertEqual(code, 0, output)

    def test_no_instruction_tells_the_reader_to_leave_the_root(self):
        for name in ("README.md", "MIGRATING.md", "UPGRADING.md"):
            with self.subTest(document=name):
                text = read(name)
                self.assertIsNone(re.search(r"(?m)^\s*cd ", text))
                self.assertNotIn("run from `.ratchet", text)
                for command in re.findall(r"(?m)^\s*python3 (\S+)", text):
                    self.assertTrue(command.startswith(".ratchet/checks/"), command)

    def test_the_entry_that_is_printed_can_be_pasted(self):
        code, output = self.run_in_project("python3 .ratchet/checks/init.py")
        self.assertEqual(code, 0, output)
        code, output = self.run_in_project("python3 .ratchet/checks/generate.py --entries ratchet.simplest ratchet.test-first")
        self.assertEqual(code, 0, output)
        path = os.path.join(self.project, "register.json")
        with open(path, encoding="utf-8") as handle:
            register = json.load(handle)
        register["adopted"] += json.loads("[" + output + "]")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(register, handle, indent=2)
        code, output = self.run_in_project("python3 .ratchet/checks/check_register.py register.json")
        self.assertEqual(code, 0, output)
        self.assertIn("11 rules match Ratchet", output)

    def test_the_templates_name_no_agent_tool(self):
        for name in sorted(os.listdir(os.path.join(ROOT, "templates"))):
            with self.subTest(template=name):
                self.assertIsNone(re.search(r"\.[a-z]+/skills/", read("templates", name)), "a tool's own directory for skills")


if __name__ == "__main__":
    unittest.main()


class ExactFormEnd(unittest.TestCase):
    """An exact form ends at the end of the value: a trailing line break is refused."""

    def test_a_trailing_line_break_is_refused(self):
        import check_register
        import registry
        cases = (
            (registry.KEY, "ratchet.one-place"),
            (registry.VERSION, "0.3"),
            (registry.DATE, "2026-11-17"),
            (registry.PATH, "checks/registry.py"),
            (check_register.OWN_KEY, "project.own-rule"),
        )
        for pattern, value in cases:
            with self.subTest(pattern=pattern.pattern):
                self.assertTrue(pattern.match(value))
                self.assertIsNone(pattern.match(value + "\n"))
