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
INSTRUCTIONS = "instructions must be the path of a Markdown file in the repo"
BLOCK_NOT_GENERATED = "AGENTS.md: the block between the markers is not what register.json generates"
MARKERS = "AGENTS.md: the markers of the generated block are broken"
MARKER_LINE = "must be exactly <!-- ratchet:"
PLACE = "AGENTS.md: the block must stand at the start of the file"
LINKED = "is a symbolic link. The instruction file is read and written only as a plain file in the repo"
REFUSED = "Replace each link with a regular file"
STANDS_IN_FORM = "ratchet.fresh-context: stands_in must be the path of a Markdown file in the repo"
BY_REFERENCE_TEXT = "%s: a row adopted by reference holds no rule text"
RULE_MARKER_LINE = "RULES.md: the line that holds ratchet:rule, line "
# The label of every row by reference, as D-2026-11-22-second-redraw has it, with "guarded" for its "built"
# (D-2026-11-23-new-rules-first).
LABEL = ("Adopted by reference, the weaker mode. The wording in force is the project's own, in the file named. The check "
         "sees a marker, not the words. The wording is %s against softening.")
# A row by reference adopted in part: its where is exactly this phrase with the clauses the project's wording does not
# state, and its label says so before the label of every row by reference.
PART = "Not stated here: %s."
PART_LABEL = "Adopted in part. Not stated in the project's wording: %s. " + LABEL
PART_FORM = ('%s: where holds the words "not stated here", so the row is adopted in part, and then where must be exactly '
             '"Not stated here: <clause>; <clause>."')
PART_CODE = ("%s: where splits code: a clause holds a backtick without its pair. A clause holds no semicolon, in code or out "
             "of it, so a pair of backticks stands in one clause")
# The clauses of the passing fixtures adopted in part.
PART_ONE = ("a change to the register is reviewed before it is merged",)
PART_SEVERAL = ("a subagent's done is checked independently", "every finding is marked proven by a run or unproven",
                "`checks/` is read by the receiver")
# Prose in Japanese, Chinese and Korean that names Ratchet: the word, then letters of a script with no spaces between
# words, with and without a full-width colon. None of it is a marker word in disguise (review of step 9a).
CJK_PROSE = ("ratchet\u306e\u30eb\u30fc\u30eb\u3092\u5b88\u308b\u3002", "Ratchet\uff1a\u898f\u5247\u306f\u3053\u3053\u306b\u3042\u308b\u3002",
             "ratchet\u7684\u89c4\u5219\u5728\u8fd9\u91cc\u5b9a\u4e49\u3002", "RATCHET\u7684\u7ed3\u675f\u548c\u5f00\u59cb",
             "ratchet\uc758\uaddc\uce59\uc744\uc9c0\ud0a8\ub2e4", "\u0e01\u0e0e\u0e02\u0e2d\u0e07ratchet\u0e2d\u0e22\u0e39\u0e48",
             "\u041f\u0440\u0430\u0432\u0438\u043b\u0430 ratchet\u0430 \u0437\u0434\u0435\u0441\u044c",
             "ratchet\u043e\u043c \u043c\u044b \u0436\u0438\u0432\u0451\u043c", "ratchet:\u0433\u0435\u0433\u0438\u043d\u044b")
# Decoys whose letters after the colon are all in disguise. On a line shaped like an HTML comment they are found, as on
# main before the review of step 9a; the same words in prose are not (review of d3f25aa).
BOLD = lambda word: "".join(chr(0x1D41A + ord(char) - 97) for char in word)
MONO = lambda word: "".join(chr(0x1D68A + ord(char) - 97) for char in word)


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
    "trailing-space": "the rule of ratchet.evidence-before-done differs from Ratchet",
    "unknown-key": "ratchet.ship-first is not a rule in Ratchet",
    "duplicate-row": "ratchet.evidence-before-done is adopted twice",
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
    "status-on-text-only": "ratchet.evidence-before-done is text only in Ratchet. It cannot have a status",
    "unknown-field": "ratchet.evidence-before-done: unknown field 'waived'",
    "unknown-top-field": "unknown field 'waivers'",
    "wrong-type": "ratchet.evidence-before-done: every field must be a string",
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
    # The register may name an instruction file, which holds the block that the check generates (D-2026-11-20-generated-block).
    "instructions-outside": INSTRUCTIONS,
    "instructions-absolute": INSTRUCTIONS,
    "instructions-dash": INSTRUCTIONS,
    "instructions-not-markdown": INSTRUCTIONS,
    "instructions-not-text": INSTRUCTIONS,
    "instructions-hidden": INSTRUCTIONS,
    "instructions-marker-in-code": "a value holds ratchet:end in code, and the block of rules for AGENTS.md would hold it outside",
    # An adopted rule may carry a translation, bound to the English rule by its sha256 (#77).
    "translation-wrong-hash": "ratchet.register-on-top: the translation is bound to sha256 ",
    "translation-hash-form": "ratchet.register-on-top: translation sha256 must be 64 characters 0 to 9 and a to f",
    "translation-on-own": "example.changelog: an own rule has no translation",
    "translation-on-unknown": "ratchet.ship-first is not a rule in Ratchet",
    "translation-unknown-field": "ratchet.register-on-top: translation: unknown field 'reviewed_by'",
    "translation-missing-field": "ratchet.register-on-top: translation: missing field 'sha256'",
    "translation-not-object": "ratchet.register-on-top: translation must be an object with the fields language, text and sha256",
    "translation-not-text": "ratchet.register-on-top: translation: every field must be a string",
    "translation-cyrillic-letter": "ratchet.register-on-top: " + outside("translation text", "0430"),
    "translation-han-letter": "ratchet.register-on-top: " + outside("translation text", "4E2D"),
    "translation-zero-width": "ratchet.register-on-top: " + outside("translation text", "200B"),
    "translation-language": "ratchet.register-on-top: translation language must be a language code",
    "translation-no-words": "ratchet.register-on-top: the translation holds no words",
    # A rule of the project's own may say where its check stands, on the same terms as an adopted rule (#60).
    "own-status-on-text-only": "example.changelog is text only. It cannot have a status or a place where its check lives",
    "own-built-nowhere": "example.changelog is marked built but does not say where the check lives",
    "own-status-invalid": 'the status of example.changelog is "done". It must be "built" or "text only for now"',
    "own-where-without-status": 'example.changelog says where its check lives and has no status',
    "own-where-hidden": "example.changelog: " + outside("where", "200B"),
    "own-unknown-field": "example.changelog: unknown field 'waived'",
    "own-missing-field": "example.changelog: missing field 'source'",
    # A row adopted by reference, the weaker mode (D-2026-11-22-second-redraw, step 9a). Each fixture is the register of
    # ref-clean with one fault, and the check fails on the data before it reads any file.
    "ref-unknown-key": "ratchet.ship-first is not a rule in Ratchet",
    "ref-wrong-hash": "ratchet.fresh-context: the sha256 is ",
    "ref-hash-of-rule-only": "ratchet.fresh-context: the sha256 is ",
    "ref-hash-of-other-ratchet": "ratchet.fresh-context: the sha256 is ",
    "ref-hash-form": "ratchet.fresh-context: sha256 must be 64 characters 0 to 9 and a to f: the sha256 of the rule and its ratchet",
    "ref-with-text": BY_REFERENCE_TEXT % "ratchet.fresh-context",
    "ref-copied-with-sha": BY_REFERENCE_TEXT % "ratchet.register-on-top",
    "ref-translation": "ratchet.fresh-context: a row adopted by reference has no translation",
    "ref-on-own": "example.changelog: an own rule is not adopted by reference",
    "ref-unknown-field": "ratchet.fresh-context: unknown field 'reviewed_by'",
    "ref-missing-sha": "ratchet.fresh-context: missing field 'sha256'",
    "ref-missing-stands-in": "ratchet.fresh-context: missing field 'stands_in'",
    "ref-not-text": "ratchet.fresh-context: every field must be a string",
    "ref-path-parent": STANDS_IN_FORM,
    "ref-path-absolute": STANDS_IN_FORM,
    "ref-path-dot": STANDS_IN_FORM,
    "ref-path-dash": STANDS_IN_FORM,
    "ref-path-hidden": STANDS_IN_FORM,
    "ref-not-markdown": STANDS_IN_FORM,
    "ref-is-instructions": "ratchet.fresh-context: stands_in names AGENTS.md, the instruction file",
    "ref-is-instructions-case": "ratchet.fresh-context: stands_in names agents.md, the instruction file",
    "ref-adopted-twice": "ratchet.fresh-context is adopted twice",
    "ref-adopted-twice-by-reference": "ratchet.fresh-context is adopted twice",
    "ref-copied-then-by-reference": "ratchet.fresh-context is adopted twice",
    "ref-status-missing": "ratchet.fresh-context names a check, so it needs a status",
    "ref-status-on-text-only": "ratchet.evidence-before-done is text only in Ratchet. It cannot have a status",
    "ref-built-nowhere": "ratchet.fresh-context is marked built but does not say where the check lives",
    # A row by reference adopted in part: its where lists the clauses its wording does not state, in one exact form.
    "ref-part-built": "ratchet.fresh-context is adopted in part, so it cannot be built",
    "ref-part-case": PART_FORM % "ratchet.fresh-context",
    "ref-part-no-space": PART_FORM % "ratchet.fresh-context",
    "ref-part-no-period": PART_FORM % "ratchet.fresh-context",
    "ref-part-text-before": PART_FORM % "ratchet.fresh-context",
    "ref-part-text-after": PART_FORM % "ratchet.fresh-context",
    "ref-part-comma": PART_FORM % "ratchet.fresh-context",
    "ref-part-no-space-after-semicolon": PART_FORM % "ratchet.fresh-context",
    "ref-part-two-spaces": PART_FORM % "ratchet.fresh-context",
    "ref-part-empty": "ratchet.fresh-context: where says Not stated here and lists no clause",
    "ref-part-empty-clause": "ratchet.fresh-context: where lists an empty clause",
    "ref-part-clause-twice": "ratchet.fresh-context: where lists the clause a change to the register is reviewed before it is merged twice",
    "ref-part-text-only-malformed": PART_FORM % "ratchet.evidence-before-done",
    "ref-part-text-only-status": "ratchet.evidence-before-done is text only in Ratchet. It cannot have a status",
    "ref-part-where-on-text-only": "ratchet.evidence-before-done is text only in Ratchet. It cannot have a status or a place where its check lives",
    "ref-part-copied": "ratchet.root-cause: only a row adopted by reference is adopted in part",
    "ref-part-own": "example.changelog: an own rule is not adopted in part",
    # Look-alikes of the phrase, with the status "built", each of which once passed as a whole rule built (review of
    # 4b29449). The words "not stated here" in any form but the exact phrase fail, read after NFKC, case folding and with
    # every mark of Markdown and every character that is not a letter or a digit taken out.
    "ref-part-like-accent": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-stroke": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-code-first": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-code-middle": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-emphasis": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-underscore": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-hyphens": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-no-spaces": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-digit": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-sharp-s": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-in-clause": PART_FORM % "ratchet.fresh-context",
    "ref-part-like-text-only": PART_FORM % "ratchet.evidence-before-done",
    # Unicode look-alikes and invisible characters, which no value may hold.
    "ref-part-like-cyrillic": "ratchet.fresh-context: where holds U+043E",
    "ref-part-like-full-width": "ratchet.fresh-context: where holds U+FF2E",
    "ref-part-like-math-bold": "ratchet.fresh-context: where holds U+1D427",
    "ref-part-like-zero-width": "ratchet.fresh-context: where holds U+200B",
    "ref-part-like-soft-hyphen": "ratchet.fresh-context: where holds U+00AD",
    "ref-part-like-combining": "ratchet.fresh-context: where holds U+0301",
    # The same on a copied row and on a rule of the project's own.
    "ref-part-like-copied-accent": "ratchet.root-cause: only a row adopted by reference is adopted in part",
    "ref-part-like-copied-code": "ratchet.root-cause: only a row adopted by reference is adopted in part",
    "ref-part-like-copied-stroke": "ratchet.root-cause: only a row adopted by reference is adopted in part",
    "ref-part-like-own-accent": "example.changelog: an own rule is not adopted in part",
    "ref-part-like-own-code": "example.changelog: an own rule is not adopted in part",
    "ref-part-like-own-stroke": "example.changelog: an own rule is not adopted in part",
    # Code in a clause: a separator inside code splits nothing, and a clause holds no half of a pair of backticks.
    "ref-part-code-split": PART_CODE % "ratchet.fresh-context",
    "ref-part-code-split-three": PART_CODE % "ratchet.fresh-context",
    "ref-part-code-semicolon": PART_CODE % "ratchet.fresh-context",
    "ref-part-code-period-space": PART_FORM % "ratchet.fresh-context",
}

# Fixtures with a clean register.json that names AGENTS.md, and an AGENTS.md whose block is not what it generates,
# or whose markers are broken. Fixture name -> the text the check must print.
FAILING_BLOCK = {
    "block-edited": BLOCK_NOT_GENERATED,
    "block-row-in-comment": BLOCK_NOT_GENERATED,
    "block-extra-line": BLOCK_NOT_GENERATED,
    "block-stale": BLOCK_NOT_GENERATED,
    "block-translation-edited": BLOCK_NOT_GENERATED,
    "block-crlf-inside": BLOCK_NOT_GENERATED,
    "block-no-markers": "AGENTS.md: holds no generated block, and register.json names it in instructions",
    "block-missing-begin": MARKERS,
    "block-missing-end": MARKERS,
    "block-doubled-begin": MARKERS,
    "block-doubled": MARKERS,
    "block-marker-in-code-block": MARKERS,
    "block-marker-spaces": MARKER_LINE,
    "block-marker-no-spaces": MARKER_LINE,
    "block-marker-indented": MARKER_LINE,
    "block-marker-trailing-space": MARKER_LINE,
    "block-marker-text-after": MARKER_LINE,
    "block-marker-case": MARKER_LINE,
    "block-crlf-marker": MARKER_LINE,
    "block-crlf": MARKER_LINE,
    "block-end-no-newline": MARKER_LINE,
    "block-end-before-begin": "AGENTS.md: the line <!-- ratchet:end --> stands before <!-- ratchet:begin -->",
    "block-not-utf8": "AGENTS.md: " + NOT_UTF8,
    "block-file-missing": "AGENTS.md: the file is missing. register.json names it in instructions",
    # The block stands at the start of the file, so no text before it can put it in a code block, a comment or an
    # element that hides it, and the check reads no Markdown outside it (round 2 of #100).
    "block-after-text": PLACE,
    "block-after-empty-line": PLACE,
    "block-in-backtick-fence": PLACE,
    "block-in-tilde-fence": PLACE,
    "block-in-div-hidden": PLACE,
    "block-in-details": PLACE,
    "block-in-comment": PLACE,
    "block-after-unclosed-fence": PLACE,
    "block-indented": MARKER_LINE,
    "block-after-bom": MARKER_LINE,
    # A marker word with a character that shows as nothing, a letter of another script or a full-width colon in it
    # counts as the word, so a copy of the block under such a marker fails, and so does such a marker in place.
    "block-lookalike-zero-width": MARKERS,
    "block-lookalike-cyrillic": MARKERS,
    "block-lookalike-fullwidth": MARKERS,
    "block-lookalike-control": MARKERS,
    "block-marker-zero-width": MARKER_LINE,
    # A marker in disguise among prose in Japanese and Chinese that names Ratchet is still found.
    "block-lookalike-in-cjk": MARKERS,
    # Review of d3f25aa: on a line shaped like a comment, letters after the colon that are all in disguise still count.
    "block-lookalike-math-bold": MARKERS,
    "block-lookalike-monospace": MARKERS,
    "block-lookalike-accented": MARKERS,
    "block-lookalike-mixed-script": MARKERS,
    "block-lookalike-comment-lines": MARKERS,
    "block-lookalike-dashes": MARKERS,
}
# Fixtures with a register that names AGENTS.md and an AGENTS.md that holds the block it generates. In block-cjk-prose
# the project's own text names Ratchet in Japanese and Chinese, which is not taken for a marker in disguise.
PASSING_BLOCK = ("block-clean", "block-crlf-outside", "block-cjk-prose")

# Fixtures with the register of ref-clean, its REGISTER.md, and a RULES.md, the file its rows by reference name, with one
# fault. Fixture name -> the text the check must print.
FAILING_REFERENCE = {
    "ref-marker-missing": "RULES.md: holds no marker for ratchet.evidence-before-done",
    "ref-marker-twice": "RULES.md: the marker <!-- ratchet:rule ratchet.fresh-context --> stands 2 times",
    "ref-marker-stray": "RULES.md: holds the marker <!-- ratchet:rule ratchet.root-cause -->, and no row adopted by reference names this file",
    "ref-marker-spaces": RULE_MARKER_LINE,
    "ref-marker-no-spaces": RULE_MARKER_LINE,
    "ref-marker-case": RULE_MARKER_LINE,
    "ref-marker-key-case": RULE_MARKER_LINE,
    "ref-marker-indented": RULE_MARKER_LINE,
    "ref-marker-trailing-space": RULE_MARKER_LINE,
    "ref-marker-text-after": RULE_MARKER_LINE,
    "ref-marker-crlf": RULE_MARKER_LINE,
    "ref-marker-no-newline": RULE_MARKER_LINE,
    "ref-marker-other-form": RULE_MARKER_LINE,
    "ref-marker-two-on-line": RULE_MARKER_LINE,
    "ref-marker-zero-width": RULE_MARKER_LINE,
    "ref-key-lookalike": RULE_MARKER_LINE,
    "ref-lookalike-cyrillic": RULE_MARKER_LINE,
    "ref-lookalike-zero-width": RULE_MARKER_LINE,
    "ref-lookalike-fullwidth": RULE_MARKER_LINE,
    "ref-lookalike-control": RULE_MARKER_LINE,
    "ref-lookalike-in-cjk": RULE_MARKER_LINE,
    "ref-lookalike-math-bold": RULE_MARKER_LINE,
    "ref-lookalike-monospace": RULE_MARKER_LINE,
    "ref-lookalike-accented": RULE_MARKER_LINE,
    "ref-lookalike-mixed-script": RULE_MARKER_LINE,
    "ref-lookalike-comment-lines": RULE_MARKER_LINE,
    "ref-not-utf8": "RULES.md: " + NOT_UTF8,
    "ref-file-missing": "RULES.md: the file is missing. register.json names it in stands_in for ratchet.fresh-context, ratchet.evidence-before-done",
    "ref-md-edited": NOT_GENERATED,
}
# Fixtures with rows by reference that pass, with --markdown REGISTER.md.
PASSING_REFERENCE = ("ref-clean", "ref-no-markdown", "ref-crlf-outside", "ref-in-code-block", "ref-only", "ref-owner-built", "ref-block",
                     "ref-cjk-prose", "ref-part-one", "ref-part-several")

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


def printed(*args):
    """Run check_register.py in a print mode: (exit code, the bytes on standard output, standard error as text)."""
    result = subprocess.run([sys.executable, os.path.join(ROOT, "checks", "check_register.py")] + list(args),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode, result.stdout, result.stderr.decode("utf-8", errors="replace")


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
        self.assertIn("10 rules match Ratchet", output)

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

    def test_nothing_is_printed_from_a_register_that_cannot_be_written(self):
        code, out, err = printed(self.fixture_file("register/project-surrogate/register.json"), "--print-markdown")
        self.assertEqual((code, out), (1, b""), err)
        self.assertNotIn("Traceback", err)

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
            list(FAILING_DATA) + list(FAILING_MARKDOWN) + list(FAILING_BLOCK) + list(PASSING_BLOCK)
            + list(FAILING_REFERENCE) + list(PASSING_REFERENCE)
            + ["clean", "escaped", "latin", "references", "md-missing", "md-not-utf8"]))

    def test_the_template_and_this_repos_register_pass(self):
        code, output = run("check_register.py", os.path.join(ROOT, "templates", "register.json"))
        self.assertEqual(code, 0, output)
        code, output = run("check_register.py", os.path.join(ROOT, "register.json"), "--markdown", os.path.join(ROOT, "REGISTER.md"))
        self.assertEqual(code, 0, output)

    def test_a_missing_register_is_not_a_pass(self):
        code, output = run("check_register.py", os.path.join(scratch(self), "register.json"))
        self.assertEqual(code, 2, output)

    def test_printing_gives_the_file_that_the_check_accepts(self):
        code, out, err = printed(self.fixture_file("register/clean/register.json"), "--print-markdown")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, self.fixture_bytes("register/clean/REGISTER.md"))

    def test_nothing_is_printed_from_a_register_that_fails(self):
        code, out, err = printed(self.fixture_file("register/changed-row/register.json"), "--print-markdown")
        self.assertEqual((code, out), (1, b""), err)
        self.assertIn("FAIL", err)

    def test_a_print_mode_takes_no_other_option(self):
        data = self.fixture_file("register/clean/register.json")
        for args in (("--print-markdown", "--print-instructions"), ("--print-markdown", "--markdown", "REGISTER.md"),
                     ("--print-instructions", "--agents", "AGENTS.md")):
            with self.subTest(args=args):
                code, out, err = printed(data, *args)
                self.assertEqual((code, out), (2, b""), err)

    def test_the_write_options_are_gone(self):
        data = self.fixture_file("register/clean/register.json")
        for args in (("--write", os.path.join(os.path.dirname(data), "REGISTER.md")), ("--write-block",)):
            with self.subTest(args=args):
                code, out, err = printed(data, *args)
                self.assertEqual(code, 2, err)
                self.assertFalse(os.path.exists(os.path.join(os.path.dirname(data), "REGISTER.md")))

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


class RegisterBlock(FixtureTest):
    """The block that check_register.py generates into the instruction file the register names (D-2026-11-20-generated-block)."""

    def block(self, name, *args):
        """A copy of the fixture's directory, and what the check says about its register.json and the file it names."""
        directory = self.fixture_directory("register/" + name)
        return directory, run("check_register.py", os.path.join(directory, "register.json"), *args)

    def agents(self, directory):
        with open(os.path.join(directory, "AGENTS.md"), "rb") as handle:
            return handle.read()

    def test_a_block_that_is_what_the_register_generates_passes(self):
        for name in PASSING_BLOCK:
            with self.subTest(fixture=name):
                directory, (code, output) = self.block(name)
                self.assertEqual(code, 0, output)
                self.assertIn("AGENTS.md: the block between the markers is what register.json generates", output)
                code, output = run("check_register.py", os.path.join(directory, "register.json"),
                                   "--markdown", os.path.join(directory, "REGISTER.md"), "--agents", os.path.join(directory, "AGENTS.md"))
                self.assertEqual(code, 0, output)
        self.assertIn("1 translated", self.block("block-clean")[1][1])

    def test_every_fault_in_the_block_fails_for_its_own_reason(self):
        for name, message in sorted(FAILING_BLOCK.items()):
            with self.subTest(fixture=name):
                directory, (code, output) = self.block(name)
                self.assertEqual(code, 1, output)
                self.assertIn(message, output)
                self.assertIn("FAIL: 1 problem(s)", output, "a fixture carries exactly one fault")
                self.assertNotIn("Traceback", output)

    def test_the_block_shows_the_translation_the_english_rule_and_where_each_check_stands(self):
        text = self.fixture_text("register/block-clean/AGENTS.md")
        self.assertEqual(text.count("<!-- ratchet:begin -->\n"), 1)
        self.assertEqual(text.count("<!-- ratchet:end -->\n"), 1)
        block = text.split("<!-- ratchet:begin -->\n")[1].split("<!-- ratchet:end -->\n")[0]
        register = json.loads(self.fixture_text("register/block-clean/register.json"))
        translated = next(entry for entry in register["adopted"] if "translation" in entry)
        sys.path.insert(0, HERE)
        import registry
        for line in (
            "Generated from `register.json` by Ratchet's `check_register.py`. Never edit this block by hand",
            registry.row(translated),
            "| %s | %s | %s |" % (translated["key"], translated["translation"]["language"], registry.cell(translated["translation"]["text"])),
            "| example.changelog | built | `checks/changelog.sh` |",
        ):
            self.assertIn(line, block)
        self.assertIn("Varje regel", block, "Swedish letters stand as themselves")
        self.assertIn("\u00e5", block)
        # The block stands first. The rest of the file, after it, is the project's own, and is never read.
        self.assertTrue(text.startswith("<!-- ratchet:begin -->\n## Rules in force\n"))
        self.assertIn("<!-- ratchet:end -->\n\n# Working rules for the example project\n", text)
        self.assertIn("<!-- a comment of the project's own -->", text.split("<!-- ratchet:end -->")[1])

    def test_a_marker_word_is_found_in_any_disguise_and_other_text_is_not_taken_for_one(self):
        sys.path.insert(0, HERE)
        import check_register
        for line in ("<!-- ratchet:begin -->", "<!-- RATCHET:END -->", "ratchet\u200b:begin", "r\u0430tchet:begin",
                     "ratchet\uff1aend", "\uff52\uff41\uff54\uff43\uff48\uff45\uff54:begin", "ratch\u00e9t:end",
                     "rat\u00adchet:begin", "ratchet:\u2060end", "r\u0430t\u0441h\u0435t:b\u0435g\u0456n", "ratchet:beginning",
                     "ratchet\u306e:begin", "\u898f\u5247ratchet:end\u3067\u3059", "ratchet\uff1ab\u0435g\u0456n"):
            with self.subTest(line=line):
                self.assertTrue(check_register.holds_marker_word(line), line)
        for word in ("begin", "end"):
            for disguise in (BOLD(word), MONO(word), "\u00e9\u0148\u010f", "\u0185\u0435\u0261\u0456\u0578"):
                for line in ("<!-- ratchet:%s -->" % disguise, "\u3053\u306e<!-- ratchet:%s -->\u306f" % disguise,
                             "ratchet:%s -->" % disguise, "<!\u2212\u2212 ratchet:%s \u2212\u2212>" % disguise,
                             "<!--\nratchet:%s\n-->" % disguise):
                    with self.subTest(line=line):
                        self.assertTrue(check_register.holds_marker_word(line), line)
                with self.subTest(prose=disguise):
                    self.assertFalse(check_register.holds_marker_word("ratchet:%s in prose" % disguise))
                    self.assertFalse(check_register.holds_marker_word("<!-- a comment -->\nratchet:%s" % disguise))
        for line in ("Ratchet: begin with the register.", "\u67d0" * 30 + ":" + "\u67d0" * 30,
                     "ratchet-begin", "the ratchet ends here", "x" * 200) + CJK_PROSE:
            with self.subTest(line=line):
                self.assertFalse(check_register.holds_marker_word(line), line)

    def test_a_translation_is_bound_to_the_sha256_of_the_english_rule(self):
        import hashlib
        register = json.loads(self.fixture_text("register/block-clean/register.json"))
        rules = json.loads(read("ratchet.json"))["rules"]
        by_key = dict((rule["key"], rule) for rule in rules)
        translated = [entry for entry in register["adopted"] if "translation" in entry]
        self.assertTrue(translated)
        for entry in translated:
            self.assertEqual(entry["translation"]["sha256"], hashlib.sha256(by_key[entry["key"]]["rule"].encode("utf-8")).hexdigest())

    def print_block(self, directory):
        return printed(os.path.join(directory, "register.json"), "--print-instructions")

    def test_printing_the_file_changes_only_the_block_and_gives_what_the_check_accepts(self):
        clean = self.fixture_bytes("register/block-clean/AGENTS.md")
        begin, end = clean.index(b"<!-- ratchet:begin -->"), clean.index(b"<!-- ratchet:end -->\n") + len(b"<!-- ratchet:end -->\n")
        for name in ("block-edited", "block-stale", "block-row-in-comment", "block-extra-line", "block-translation-edited", "block-crlf-inside"):
            with self.subTest(fixture=name):
                directory = self.fixture_directory("register/" + name)
                before = self.agents(directory)
                code, out, err = self.print_block(directory)
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(out, clean)
                self.assertEqual(self.agents(directory), before, "nothing is written")
        directory = self.fixture_directory("register/block-no-markers")
        code, out, err = self.print_block(directory)
        self.assertEqual((code, err), (0, ""))
        before = self.fixture_bytes("register/block-no-markers/AGENTS.md")
        self.assertEqual(out, clean[begin:end] + b"\n" + before, "the block goes first, then an empty line")
        self.assertEqual(self.agents(directory), before, "nothing is written")
        self.assertEqual(self.block("block-no-markers")[1][0], 1, "the fixture fails before the block is put in")
        with open(os.path.join(directory, "AGENTS.md"), "wb") as handle:
            handle.write(out)
        code, output = run("check_register.py", os.path.join(directory, "register.json"))
        self.assertEqual(code, 0, output)

    def test_printing_the_file_keeps_the_rest_of_it_byte_for_byte(self):
        directory = self.fixture_directory("register/block-crlf-outside")
        code, out, err = self.print_block(directory)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, self.fixture_bytes("register/block-crlf-outside/AGENTS.md"))

    def test_a_missing_file_is_printed_as_the_block_alone(self):
        clean = self.fixture_bytes("register/block-clean/AGENTS.md")
        begin, end = clean.index(b"<!-- ratchet:begin -->"), clean.index(b"<!-- ratchet:end -->\n") + len(b"<!-- ratchet:end -->\n")
        directory = self.fixture_directory("register/block-file-missing")
        code, out, err = self.print_block(directory)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, clean[begin:end])
        self.assertFalse(os.path.exists(os.path.join(directory, "AGENTS.md")))

    def test_nothing_is_printed_where_the_markers_are_broken(self):
        for name in sorted(FAILING_BLOCK):
            if FAILING_BLOCK[name] not in (MARKERS, MARKER_LINE, PLACE) and name not in ("block-not-utf8", "block-end-before-begin"):
                continue
            with self.subTest(fixture=name):
                directory = self.fixture_directory("register/" + name)
                code, out, err = self.print_block(directory)
                self.assertEqual((code, out), (1, b""), err)
                self.assertIn("AGENTS.md: the file is not printed", err)
                self.assertNotIn("Traceback", err)

    def linked(self, link_to, instructions="link/AGENTS.md"):
        """A copy of block-clean whose register names instructions, a valid AGENTS.md outside the copy, and a
        symbolic link "link" in the copy that points at link_to, "directory" for the directory outside or "file" for the
        file in it. Returns the copy, the file outside, and its bytes."""
        directory = self.fixture_directory("register/block-clean")
        outside = scratch(self)
        agents = os.path.join(outside, "AGENTS.md")
        shutil.copyfile(os.path.join(directory, "AGENTS.md"), agents)
        with open(agents, "ab") as handle:
            handle.write(b"Outside the repo.\n")
        os.symlink(outside if link_to == "directory" else agents, os.path.join(directory, "link"))
        path = os.path.join(directory, "register.json")
        with open(path, encoding="utf-8") as handle:
            register = json.load(handle)
        register["instructions"] = instructions
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(register, handle)
        with open(agents, "rb") as handle:
            return directory, agents, handle.read()

    def test_an_instruction_file_behind_a_symbolic_link_is_not_read(self):
        # Round 2 of #100: a link in any part of the path, the last or one before it, could lead out of the repo. The
        # check refuses the path, and so does --print-instructions, which prints nothing.
        for link_to, instructions in (("directory", "link/AGENTS.md"), ("file", "link.md"), ("directory", "link/new.md")):
            with self.subTest(link_to=link_to, instructions=instructions):
                directory, agents, before = self.linked(link_to, instructions)
                if instructions == "link.md":
                    os.rename(os.path.join(directory, "link"), os.path.join(directory, "link.md"))
                code, output = run("check_register.py", os.path.join(directory, "register.json"))
                self.assertEqual(code, 1, output)
                self.assertIn(LINKED, output)
                self.assertIn("FAIL: 1 problem(s)", output)
                self.assertNotIn("is what register.json generates", output, "the file outside was not read as the block")
                self.assertNotIn("Traceback", output)
                code, out, err = self.print_block(directory)
                self.assertEqual((code, out), (1, b""), err)
                self.assertIn(LINKED, err)
                with open(agents, "rb") as handle:
                    self.assertEqual(handle.read(), before, "nothing outside the repo was written")
                self.assertFalse(os.path.exists(os.path.join(os.path.dirname(agents), "new.md")))

    def test_an_instruction_file_named_outside_the_repo_is_not_read(self):
        for instructions in ("../AGENTS.md", "/AGENTS.md", "a/../../AGENTS.md", "./AGENTS.md", os.path.join(scratch(self), "AGENTS.md")):
            with self.subTest(instructions=instructions):
                directory, agents, before = self.linked("directory", instructions)
                os.remove(os.path.join(directory, "link"))
                code, output = run("check_register.py", os.path.join(directory, "register.json"))
                self.assertEqual(code, 1, output)
                self.assertIn(INSTRUCTIONS, output)
                self.assertNotIn("Traceback", output)
                code, out, err = self.print_block(directory)
                self.assertEqual((code, out), (1, b""), err)
                self.assertIn(INSTRUCTIONS, err)

    def test_an_instruction_file_in_a_directory_that_is_missing_is_not_printed(self):
        directory, agents, before = self.linked("directory", "docs/AGENTS.md")
        os.remove(os.path.join(directory, "link"))
        code, out, err = self.print_block(directory)
        self.assertEqual((code, out), (1, b""), err)
        self.assertIn("docs is missing", err)
        os.mkdir(os.path.join(directory, "docs"))
        code, out, err = self.print_block(directory)
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(out.startswith(b"<!-- ratchet:begin -->\n"))

    def test_nothing_is_printed_from_a_register_that_fails(self):
        directory = self.fixture_directory("register/block-clean")
        path = os.path.join(directory, "register.json")
        with open(path, encoding="utf-8") as handle:
            register = json.load(handle)
        register["own"][0]["status"] = "done"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(register, handle)
        code, out, err = self.print_block(directory)
        self.assertEqual((code, out), (1, b""), err)

    def test_printing_the_file_needs_an_instruction_file_in_the_register(self):
        code, out, err = printed(self.fixture_file("register/clean/register.json"), "--print-instructions")
        self.assertEqual((code, out), (1, b""), err)
        self.assertIn("register.json names no instruction file in instructions, so there is no file to print", err)

    def test_a_block_typed_by_hand_passes_and_its_translation_is_bound_by_a_hash_typed_by_hand(self):
        handwritten = self.fixture_directory("handwritten")
        source = os.path.join(handwritten, "ratchet.json")
        code, output = run("check_register.py", "--source", source, os.path.join(handwritten, "block", "register.json"),
                           "--markdown", os.path.join(handwritten, "block", "REGISTER.md"))
        self.assertEqual(code, 0, output)
        self.assertIn("block/AGENTS.md: the block between the markers is what register.json generates", output)
        self.assertIn("1 rules of the project's own, 1 with a status: 1 built", output)


class RegisterByReference(FixtureTest):
    """Rows adopted by reference, the weaker mode, in a register that mixes them with copied rows
    (D-2026-11-22-second-redraw, step 9a)."""

    def check(self, name, *args):
        """A copy of the fixture's directory, and what the check says about its register.json with --markdown REGISTER.md."""
        directory = self.fixture_directory("register/" + name)
        return directory, run("check_register.py", os.path.join(directory, "register.json"),
                              "--markdown", os.path.join(directory, "REGISTER.md"), *args)

    def test_rows_by_reference_that_pass_are_labeled(self):
        for name in PASSING_REFERENCE:
            with self.subTest(fixture=name):
                directory, (code, output) = self.check(name)
                self.assertEqual(code, 0, output)
                register = json.loads(self.fixture_text("register/%s/register.json" % name))
                rows = [entry for entry in register["adopted"] if "stands_in" in entry]
                self.assertTrue(rows)
                said = LABEL % ("guarded" if name == "ref-owner-built" else "not guarded")
                for entry in rows:
                    if "where" in entry and entry["where"].startswith("Not stated here: "):
                        line = PART_LABEL % (entry["where"][len("Not stated here: "):-1], "not guarded")
                    else:
                        line = said
                    self.assertIn("register.json: %s stands in %s. %s\n" % (entry["key"], entry["stands_in"], line), output)
                self.assertIn("%d rules are adopted by reference, the weaker mode" % len(rows), output)
                self.assertIn("RULES.md: holds the marker line of ", output)
        self.assertIn("REGISTER.md: not there, which a register with rows adopted by reference may leave out",
                      self.check("ref-no-markdown")[1][1])
        self.assertIn("AGENTS.md: the block between the markers is what register.json generates", self.check("ref-block")[1][1])
        self.assertIn("docs/more.md: holds the marker line of ", self.check("ref-only")[1][1])
        self.assertIn("0 rules match Ratchet", self.check("ref-only")[1][1], "every row is by reference")

    def test_every_fault_in_the_file_a_row_names_fails_for_its_own_reason(self):
        for name, message in sorted(FAILING_REFERENCE.items()):
            with self.subTest(fixture=name):
                directory, (code, output) = self.check(name)
                self.assertEqual(code, 1, output)
                self.assertIn(message, output)
                self.assertIn("FAIL: 1 problem(s)", output, "a fixture carries exactly one fault")
                self.assertNotIn("Traceback", output)
                self.assertNotIn("stands in RULES.md. Adopted by reference", output, "no label on a register that fails")

    def test_the_label_is_the_decisions_sentence_and_says_built_only_on_the_registers_own_claim(self):
        sys.path.insert(0, HERE)
        import check_register
        self.assertEqual(check_register.LABEL, LABEL)
        register = json.loads(self.fixture_text("register/ref-clean/register.json"))
        owner = next(entry for entry in register["adopted"] if entry["key"] == "ratchet.owner-paths")
        self.assertEqual(owner["status"], "text only for now")
        self.assertEqual(check_register.label(register), LABEL % "not guarded")
        owner.update(status="built", where="`.github/CODEOWNERS`")
        self.assertEqual(check_register.label(register), LABEL % "guarded")
        # Adopted by reference with the status "built", it does not count: the project's own wording of the rule that
        # protects the wording is the one the check does not see (review of step 9a).
        index = register["adopted"].index(owner)
        register["adopted"][index] = {"key": "ratchet.owner-paths", "stands_in": "RULES.md", "sha256": "0" * 64,
                                      "status": "built", "where": "`.github/CODEOWNERS`"}
        self.assertEqual(check_register.label(register), LABEL % "not guarded", "owner-paths by reference")
        register["adopted"][index] = owner
        register["adopted"].remove(owner)
        self.assertEqual(check_register.label(register), LABEL % "not guarded", "a register that does not adopt it")
        built = self.fixture_text("register/ref-owner-built/REGISTER.md")
        self.assertIn(check_register.registry.cell(LABEL % "guarded"), built)
        self.assertNotIn("not guarded", built)
        # An adoption report on 0.12: "built" meant two things on one screen. The label never says it, so "built" means
        # only a rule's enforcement.
        for word in ("guarded", "not guarded"):
            self.assertNotIn("built", LABEL % word)
        clean = self.fixture_text("register/ref-clean/REGISTER.md")
        self.assertEqual(clean.count(check_register.registry.cell(LABEL % "not guarded")), 2, "each row is labeled")

    def test_the_rows_by_reference_stand_in_a_table_of_their_own_with_no_rule_text(self):
        sys.path.insert(0, HERE)
        import registry
        rules = registry.rules_by_key(registry.load())
        markdown = self.fixture_text("register/ref-clean/REGISTER.md")
        self.assertIn("## Rules from Ratchet\n", markdown)
        self.assertIn("## Rules adopted by reference\n", markdown)
        for key in ("ratchet.fresh-context", "ratchet.evidence-before-done"):
            self.assertIn("| %s | `RULES.md` | Adopted by reference\\, the weaker mode\\." % key, markdown)
            self.assertNotIn(registry.cell(rules[key]["rule"]), markdown)
            self.assertNotIn(registry.cell(rules[key]["ratchet"]), markdown)
        self.assertIn(registry.row(rules["ratchet.register-on-top"]), markdown, "a copied row stands as before")
        only = self.fixture_text("register/ref-only/REGISTER.md")
        self.assertNotIn("## Rules from Ratchet", only, "no table of copied rows when there is none")
        self.assertNotIn("ratchet:rule", markdown + only, "REGISTER.md holds no marker line")

    def test_the_sha256_is_that_of_the_rule_a_line_feed_and_the_ratchet(self):
        import hashlib
        rules = dict((rule["key"], rule) for rule in json.loads(read("ratchet.json"))["rules"])
        register = json.loads(self.fixture_text("register/ref-only/register.json"))
        for entry in register["adopted"]:
            rule = rules[entry["key"]]
            self.assertEqual(entry["sha256"], hashlib.sha256((rule["rule"] + "\n" + rule["ratchet"]).encode("utf-8")).hexdigest())
            self.assertNotEqual(entry["sha256"], hashlib.sha256(rule["rule"].encode("utf-8")).hexdigest())

    def test_the_command_in_the_readme_takes_the_sha256_of_every_rule_and_the_check_prints_it(self):
        # Review of step 9a: printf and shasum took the rule through the shell, which broke on a backtick or a quote. The
        # command in checks/README.md reads ratchet.json, so no rule text passes through the shell.
        sys.path.insert(0, HERE)
        import check_register
        commands = re.findall(r"(?m)^(python3 -c 'import hashlib.*) \.ratchet/ratchet\.json (ratchet\.[a-z-]+)$", read("checks/README.md"))
        self.assertEqual(len(commands), 1, "one command, with the path of ratchet.json in .ratchet and a key")
        command = commands[0][0]
        rules = json.loads(read("ratchet.json"))["rules"]
        hard = [rule for rule in rules if any(mark in rule["rule"] + rule["ratchet"] for mark in "`'\"$")]
        self.assertTrue(hard, "some rules hold a backtick or a quote")
        # Review of d3f25aa: no rule of Ratchet holds "$" today, so a rule made up here holds each mark a shell reads.
        made_up = {"key": "ratchet.made-up", "rule": "Run `echo $HOME` and $(touch made-up) and ${PATH} \"in quotes\" and 'single'.",
                   "ratchet": "Check: `$(rm -f x)` and $1, \\n, %s and %% with \"it's\"."}
        for mark in ("`", "'", '"', "$", "$(", "\\", "%"):
            self.assertIn(mark, made_up["rule"] + made_up["ratchet"])
        made_up_path = os.path.join(scratch(self), "ratchet.json")
        with open(made_up_path, "w", encoding="utf-8") as handle:
            json.dump({"rules": [made_up]}, handle)
        for rule, path in [(rule, os.path.join(ROOT, "ratchet.json")) for rule in hard + [rules[0]]] + [(made_up, made_up_path)]:
            with self.subTest(key=rule["key"]):
                result = subprocess.run(["/bin/sh", "-c", "%s %s %s" % (command.replace("python3 ", shlex.quote(sys.executable) + " ", 1),
                                                                         shlex.quote(path), rule["key"])],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                                        cwd=os.path.dirname(made_up_path))
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(result.stdout, check_register.reference_sha256(rule) + "\n")
        self.assertEqual(os.listdir(os.path.dirname(made_up_path)), ["ratchet.json"], "nothing in the rule was run")
        # A wrong sha256 fails, and the check prints the right one.
        directory, (code, output) = self.check("ref-wrong-hash")
        rule = next(rule for rule in rules if rule["key"] == "ratchet.fresh-context")
        self.assertIn("and that of the rule and its ratchet in Ratchet %s is %s" % (json.loads(read("ratchet.json"))["version"],
                                                                                    check_register.reference_sha256(rule)), output)

    def test_a_file_name_outside_ascii_is_refused_as_not_ascii_letters(self):
        sys.path.insert(0, HERE)
        import check_register
        for value in ("ARBETSS\u00c4TT.md", "docs/r\u00e8gles.md"):
            with self.subTest(value=value):
                self.assertIn("parts of ASCII letters, digits", check_register.instructions_problem(value, "stands_in"))
                self.assertIn("parts of ASCII letters, digits", check_register.instructions_problem(value))

    def test_register_md_is_optional_only_for_a_register_with_rows_by_reference(self):
        directory, (code, output) = self.check("md-missing")
        self.assertEqual(code, 1, output)
        directory = self.fixture_directory("register/ref-no-markdown")
        os.mkdir(os.path.join(directory, "REGISTER.md"))
        code, output = run("check_register.py", os.path.join(directory, "register.json"), "--markdown", os.path.join(directory, "REGISTER.md"))
        self.assertEqual(code, 1, output)
        self.assertIn("REGISTER.md: the file is missing", output, "a directory in its place is not left out")

    def test_printing_a_mixed_register_prints_the_rows_by_reference_and_no_marker(self):
        directory = self.fixture_directory("register/ref-block")
        before = self.fixture_bytes("register/ref-block/RULES.md")
        code, out, err = printed(os.path.join(directory, "register.json"), "--print-instructions")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, self.fixture_bytes("register/ref-block/AGENTS.md"))
        block = out.decode("utf-8").split("<!-- ratchet:end -->")[0]
        self.assertIn("### Rules adopted by reference\n", block)
        self.assertIn("| ratchet.fresh-context | `RULES.md` | Adopted by reference", block)
        self.assertNotIn("ratchet:rule", block)
        with open(os.path.join(directory, "RULES.md"), "rb") as handle:
            self.assertEqual(handle.read(), before, "nothing is written")
        code, out, err = printed(os.path.join(directory, "register.json"), "--print-markdown")
        self.assertEqual((code, out, err), (0, self.fixture_bytes("register/ref-block/REGISTER.md"), ""))
        # Neither print mode reads the file a row by reference names.
        directory = self.fixture_directory("register/ref-file-missing")
        code, out, err = printed(os.path.join(directory, "register.json"), "--print-markdown")
        self.assertEqual((code, out, err), (0, self.fixture_bytes("register/ref-file-missing/REGISTER.md"), ""))
        directory = self.fixture_directory("register/ref-block")
        os.remove(os.path.join(directory, "RULES.md"))
        code, output = run("check_register.py", os.path.join(directory, "register.json"))
        self.assertEqual(code, 1, output)
        self.assertIn("RULES.md: the file is missing", output, "the check reads it")
        code, out, err = printed(os.path.join(directory, "register.json"), "--print-instructions")
        self.assertEqual((code, out, err), (0, self.fixture_bytes("register/ref-block/AGENTS.md"), ""),
                         "--print-instructions does not")
        with open(os.path.join(directory, "RULES.md"), "w", encoding="utf-8") as handle:
            handle.write("<!-- ratchet:rule broken\n")
        code, out, err = printed(os.path.join(directory, "register.json"), "--print-instructions")
        self.assertEqual((code, out, err), (0, self.fixture_bytes("register/ref-block/AGENTS.md"), ""),
                         "nor a file whose marker is broken")

    def test_a_file_a_row_names_behind_a_symbolic_link_is_not_read(self):
        for stands_in, link_to in (("RULES.md", "file"), ("docs/RULES.md", "directory")):
            with self.subTest(stands_in=stands_in):
                directory = self.fixture_directory("register/ref-no-markdown")
                outside = scratch(self)
                shutil.move(os.path.join(directory, "RULES.md"), os.path.join(outside, "RULES.md"))
                if link_to == "file":
                    os.symlink(os.path.join(outside, "RULES.md"), os.path.join(directory, "RULES.md"))
                else:
                    os.symlink(outside, os.path.join(directory, "docs"))
                path = os.path.join(directory, "register.json")
                with open(path, encoding="utf-8") as handle:
                    register = json.load(handle)
                for entry in register["adopted"]:
                    if "stands_in" in entry:
                        entry["stands_in"] = stands_in
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(register, handle)
                code, output = run("check_register.py", path)
                self.assertEqual(code, 1, output)
                self.assertIn("is a symbolic link. The file a row by reference names is read only as a plain file in the repo", output)
                self.assertIn("FAIL: 1 problem(s)", output)
                self.assertNotIn("holds the marker line", output)
        directory = self.fixture_directory("register/ref-no-markdown")
        path = os.path.join(directory, "register.json")
        with open(path, encoding="utf-8") as handle:
            register = json.load(handle)
        for entry in register["adopted"]:
            if "stands_in" in entry:
                entry["stands_in"] = "docs/RULES.md"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(register, handle)
        code, output = run("check_register.py", path)
        self.assertEqual(code, 1, output)
        self.assertIn("docs is missing or is not a directory. register.json names docs/RULES.md in stands_in", output)

    def test_the_word_of_the_rule_marker_is_found_in_any_disguise(self):
        sys.path.insert(0, HERE)
        import check_register
        for line in ("<!-- ratchet:rule ratchet.x -->", "RATCHET:RULE", "ratchet\u200b:rule", "r\u0430tchet:rule", "ratchet\uff1arule",
                     "ratchet\x00:rule", "rat\u00adchet:rule", "ratchet\u306e:rule", "\u898f\u5247 r\u0430tchet:rul\u0435 \u3067\u3059",
                     "ratchet:\u0433ul\u0435"):
            with self.subTest(line=line):
                self.assertEqual(len(check_register.marker_words(line, check_register.RULE_WORD)[0]), 1, line)
        for disguise in (BOLD("rule"), MONO("rule"), "\u0155\u00fa\u013a\u00e9", "\u0433\u057d\u04cf\u0435"):
            for line in ("<!-- ratchet:%s ratchet.fresh-context -->" % disguise, "<!--\nratchet:%s ratchet.x\n-->" % disguise):
                with self.subTest(line=line):
                    self.assertEqual(len(check_register.marker_words(line, check_register.RULE_WORD)[0]), 1, line)
            with self.subTest(prose=disguise):
                self.assertEqual(check_register.marker_words("ratchet:%s in prose" % disguise, check_register.RULE_WORD)[0], [])
        for line in ("Ratchet: rule of the register.", "ratchet-rule", "the ratchet rules here") + CJK_PROSE:
            with self.subTest(line=line):
                self.assertEqual(check_register.marker_words(line, check_register.RULE_WORD)[0], [], line)

    def test_a_mixed_register_typed_by_hand_passes_with_a_hash_typed_by_hand(self):
        handwritten = self.fixture_directory("handwritten")
        source = os.path.join(handwritten, "ratchet.json")
        code, output = run("check_register.py", "--source", source, os.path.join(handwritten, "reference", "register.json"),
                           "--markdown", os.path.join(handwritten, "reference", "REGISTER.md"))
        self.assertEqual(code, 0, output)
        self.assertIn("1 rules match Ratchet 9.9 (1 core, 0 experimental). 1 rules are adopted by reference", output)
        self.assertIn("ratchet.example-two stands in RULES.md. " + LABEL % "not guarded", output)


class RegisterInPart(FixtureTest):
    """A row by reference adopted in part: its where lists, in one exact form, the clauses the project's wording does
    not state yet. No field is added, but the form of register.json changed in 0.12: a row by reference of a rule that
    is text only may now take a where, and only as that phrase."""

    def check(self, name):
        directory = self.fixture_directory("register/" + name)
        return run("check_register.py", os.path.join(directory, "register.json"), "--markdown", os.path.join(directory, "REGISTER.md"))

    def module(self):
        sys.path.insert(0, HERE)
        import check_register
        return check_register

    def test_the_one_exact_form_gives_the_clauses_and_nothing_else_does(self):
        check_register = self.module()
        self.assertEqual(check_register.part_clauses(PART % "one"), ["one"])
        self.assertEqual(check_register.part_clauses(PART % "one; two; `a.b`"), ["one", "two", "`a.b`"])
        for where in ("Not stated here: one", "not stated here: one.", "Not stated here:one.", "Not stated here : one.",
                      "We say: Not stated here: one.", "Not stated here: one. And more.", "Not stated here: one;two.",
                      "Not stated here: one;  two.", "Not stated here:  one.", "Not stated here: one, two", "built",
                      "`.github/CODEOWNERS`", ""):
            with self.subTest(where=where):
                self.assertIsNone(check_register.part_clauses(where))

    def test_the_label_says_adopted_in_part_and_lists_the_clauses_in_the_output_and_in_register_md(self):
        check_register = self.module()
        for name, key, clauses in (("ref-part-one", "ratchet.fresh-context", PART_ONE),
                                   ("ref-part-several", "ratchet.evidence-before-done", PART_SEVERAL)):
            with self.subTest(fixture=name):
                register = json.loads(self.fixture_text("register/%s/register.json" % name))
                entry = next(row for row in register["adopted"] if row["key"] == key)
                self.assertEqual(entry["where"], PART % "; ".join(clauses))
                self.assertEqual(sorted(entry), sorted(["key", "stands_in", "sha256", "where"] + (["status"] if "status" in entry else [])),
                                 "no field is added")
                code, output = self.check(name)
                self.assertEqual(code, 0, output)
                label = PART_LABEL % ("; ".join(clauses), "not guarded")
                self.assertEqual(check_register.row_label(register, entry), label)
                self.assertIn("register.json: %s stands in RULES.md. %s\n" % (key, label), output)
                self.assertIn("1 of them adopted in part: the check sees the clauses listed, not whether they are the ones the wording leaves out", output)
                markdown = self.fixture_text("register/%s/REGISTER.md" % name)
                self.assertIn("| %s | `RULES.md` | %s |" % (key, check_register.registry.cell(label)), markdown)
                # The other row by reference keeps the label of a whole rule.
                other = next(row for row in register["adopted"] if "stands_in" in row and row["key"] != key)
                self.assertIn("register.json: %s stands in RULES.md. %s\n" % (other["key"], LABEL % "not guarded"), output)
        # A register with no row in part says nothing of it.
        self.assertNotIn("adopted in part", self.check("ref-clean")[1])

    def test_the_words_are_found_in_any_form_and_nothing_else_is(self):
        check_register = self.module()
        for where in ("Not stated here: one.", "N\u00f3t stated here: one.", "Not stated \u0127ere: one.", "`Not` stated here: one.",
                      "Not `stated` here: the owner review.", "*Not* stated here: one.", "_not_ **stated** here", "NOT-STATED-HERE",
                      "notstatedhere", "N0t stat3d h3r3", "Not sta\u0167ed here", "Not stated here", "In short, not stated here.",
                      "N\u043et stated here", "\uff2eot stated here", "\U0001d427ot stated here", "Not\u200b stated here",
                      "No\u00adt stated here", "No\u0301t stated here", "Not\u00a0stated\u00a0here", "Not stated here\u2060",
                      "N.o.t s.t.a.t.e.d h.e.r.e", "Not\tstated\nhere", "Not st\u00e5ted h\u00e9re", "Not \u017ftated here"):
            with self.subTest(where=where):
                self.assertTrue(check_register.holds_part({"where": where}))
        for where in ("checks/check_register.py, run in CI", "not here", "stated here", "not stated", "in our heads",
                      "Not yet stated: here.", "`.github/CODEOWNERS`", ""):
            with self.subTest(where=where):
                self.assertFalse(check_register.holds_part({"where": where}))

    def test_a_clause_never_splits_code(self):
        check_register = self.module()
        for where in ("Not stated here: `one; two`.", "Not stated here: `a; b; c`.", "Not stated here: x `a; b` y.",
                      "Not stated here: `a;b`.", "Not stated here: `a. b`.", "Not stated here: one; `two.",
                      "Not stated here: one; `` two ``."):
            with self.subTest(where=where):
                self.assertIsNone(check_register.part_clauses(where))
                self.assertIsNotNone(check_register.part_problem("k", where))
        self.assertEqual(check_register.part_clauses("Not stated here: `a.b`; `c` and d."), ["`a.b`", "`c` and d"])
        self.assertEqual(check_register.part_problem("k", "Not stated here: `one; two`."), PART_CODE % "k")

    def test_a_text_only_rule_takes_where_only_as_the_phrase(self):
        register = json.loads(self.fixture_text("register/ref-part-several/register.json"))
        entry = next(row for row in register["adopted"] if row["key"] == "ratchet.evidence-before-done")
        self.assertNotIn("status", entry, "a text-only rule has no status, in part or whole")

    def test_upgrade_keeps_the_phrase_and_an_own_rule_never_takes_it(self):
        sys.path.insert(0, HERE)
        import upgrade
        check_register = self.module()
        rules = dict((rule["key"], rule) for rule in json.loads(read("ratchet.json"))["rules"])
        register = json.loads(self.fixture_text("register/ref-part-one/register.json"))
        fresh = next(row for row in register["adopted"] if row["key"] == "ratchet.fresh-context")
        self.assertEqual(upgrade.entry(rules["ratchet.fresh-context"], fresh)["where"], fresh["where"])
        several = json.loads(self.fixture_text("register/ref-part-several/register.json"))
        done = next(row for row in several["adopted"] if row["key"] == "ratchet.evidence-before-done")
        kept = upgrade.entry(rules["ratchet.evidence-before-done"], done)
        self.assertEqual(kept["where"], done["where"])
        self.assertNotIn("status", kept)
        # A rule that comes to name a check keeps the phrase beside its new status; one that comes to be text only keeps it alone.
        named = dict(rules["ratchet.evidence-before-done"], enforcement="enforced", ratchet="Check: a made-up check")
        self.assertEqual(upgrade.entry(named, done), dict(kept, sha256=check_register.reference_sha256(named), status="text only for now"))
        plain = dict(rules["ratchet.fresh-context"], enforcement="text-only", ratchet="A made-up ratchet")
        self.assertEqual(upgrade.entry(plain, fresh)["where"], fresh["where"])
        self.assertNotIn("status", upgrade.entry(plain, fresh))
        # A removed rule becomes an own rule in full, with Ratchet's text, so it does not take the phrase.
        own = upgrade.own_entry(rules["ratchet.fresh-context"], fresh, "example", set())
        self.assertNotIn("where", own)
        self.assertEqual(check_register.part_clauses(own.get("where", "")), None)


class AdoptGuidance(unittest.TestCase):
    """What STARTING.md tells a project that adopts by reference, from an adoption report on 0.12
    (D-2026-11-23-new-rules-first). The words are text only; these tests keep them from being dropped."""

    def setUp(self):
        self.text = " ".join(read("STARTING.md").split())

    def test_the_pinned_step_may_run_in_a_job_that_is_not_required_and_never_passes_when_ratchet_is_out_of_reach(self):
        self.assertIn("The step may run in a job that the protection of `main` does not require", self.text)
        self.assertIn("it fails, and never passes, when it cannot reach Ratchet", self.text)

    def test_a_sentence_with_any_part_not_stated_is_listed_whole(self):
        self.assertIn("When your wording leaves out any part of a sentence of the rule, list that whole sentence as one "
                      "clause", self.text)

    def test_a_marker_stands_outside_a_markdown_list(self):
        self.assertIn("Put it outside a Markdown list, before or after it: a marker between two list items ends the list.",
                      self.text)


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
        self.assert_check_fails("ratchet.owner-paths: " + outside("rule", "200B"))

    def test_a_rule_that_is_text_only_without_a_reason_fails(self):
        self.edit("ratchet.json", '"ratchet": "Text only: a check cannot see work that was never written down"', '"ratchet": "Text only"')
        self.assert_check_fails('ratchet.work-in-issues: the ratchet is "Check: " and the check, or "Text only" and the reason')

    def test_a_rule_with_html_is_written_as_text(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "<!-- Only the owner approves decisions. -->")
        code, output = run("generate.py", root=self.copy)
        with open(os.path.join(self.copy, "RATCHET.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("| ratchet.owner-paths | \\<\\!\\-\\- Only the owner approves decisions\\. \\-\\-\\> Agents write", text)
        self.assertNotIn("<!-- Only the owner", text)

    def test_a_rule_that_mixes_a_link_a_comment_and_code_is_written_as_text_and_code(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "[ok](https://example.invalid/`)<span hidden>Only the owner approves decisions.</span>`tail")
        run("generate.py", root=self.copy)
        with open(os.path.join(self.copy, "RATCHET.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("| ratchet.owner-paths | \\[ok\\]\\(https\\:\\/\\/example\\.invalid\\/`)<span hidden>Only the owner approves decisions.</span>`tail Agents write", text)

    def test_a_rule_with_a_combining_accent_fails_without_a_traceback(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "Cafe\\u0301 approval is mandatory.")
        self.assert_check_fails("ratchet.owner-paths: rule holds U+0301")

    def test_a_rule_with_a_name_between_two_colons_fails(self):
        self.edit("ratchet.json", "Only the owner approves decisions.", "Only the owner :example: approves decisions.")
        self.assert_check_fails("ratchet.owner-paths: rule has :example:, " + EMOJI_NAME)

    def test_a_rule_in_another_script_fails_the_same_on_every_version(self):
        # U+1E4D0 is a letter that only the newer of the supported interpreters knows.
        for escape, code in (("\\ud839\\udcd0", "1E4D0"), ("\\u05be", "05BE"), ("\\u202e", "202E"), ("\\ufffd", "FFFD")):
            with self.subTest(code=code):
                self.edit("ratchet.json", "Only the owner approves decisions.", "Only the owner %s approves decisions." % escape)
                self.assert_check_fails("ratchet.owner-paths: " + outside("rule", code))
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
        self.edit("RATCHET.md", "are text only (", "are text only, down to (")
        self.assert_check_fails("RATCHET.md: generated text is out of date or was edited by hand")

    def test_a_fixture_edited_by_hand_fails(self):
        self.edit(os.path.join("checks", "fixtures", "register", "changed-row", "register.json"), ", where practical.", ".")
        self.assert_check_fails("generated text is out of date or was edited by hand")

    def test_this_repos_register_edited_by_hand_fails(self):
        self.edit("REGISTER.md", "| ratchet.no-secrets | text only for now |", "| ratchet.no-secrets | built |")
        self.assert_check_fails("REGISTER.md: generated text is out of date or was edited by hand")

    def test_this_repos_agents_md_carries_the_block_and_an_edit_to_it_fails(self):
        code, output = run("check_register.py", os.path.join(self.copy, "register.json"))
        self.assertEqual(code, 0, output)
        self.assertIn("AGENTS.md: the block between the markers is what register.json generates", output)
        self.edit("AGENTS.md", "| ratchet.no-secrets | text only for now |", "| ratchet.no-secrets | built |")
        code, output = run("check_register.py", os.path.join(self.copy, "register.json"))
        self.assertEqual(code, 1, output)
        self.assertIn("AGENTS.md: the block between the markers is not what register.json generates", output)
        self.assert_check_fails("AGENTS.md: generated text is out of date or was edited by hand")

    def test_generate_writes_the_block_of_this_repos_agents_md(self):
        self.edit("AGENTS.md", "| ratchet.no-secrets | text only for now |", "| ratchet.no-secrets | built |")
        code, output = run("generate.py", root=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("wrote AGENTS.md", output)
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        with open(os.path.join(self.copy, "AGENTS.md"), "rb") as handle:
            self.assertEqual(handle.read(), read("AGENTS.md").encode("utf-8"))

    def test_the_generator_neither_reads_nor_writes_an_instruction_file_behind_a_symbolic_link(self):
        # Round 2 of #100: register.json names link/AGENTS.md, and link leads out of the repo. Since round 3 the
        # generator refuses the tree, which holds a link, before it reads anything.
        outside = scratch(self)
        with open(os.path.join(self.copy, "AGENTS.md"), "rb") as handle:
            before = handle.read().replace(b"| ratchet.no-secrets | text only for now |", b"| ratchet.no-secrets | built |")
        with open(os.path.join(outside, "AGENTS.md"), "wb") as handle:
            handle.write(before)
        os.symlink(outside, os.path.join(self.copy, "link"))
        self.edit("register.json", '"instructions": "AGENTS.md"', '"instructions": "link/AGENTS.md"')
        for args in (("--check",), ()):
            with self.subTest(args=args):
                code, output = run("generate.py", *args, root=self.copy)
                self.assertEqual(code, 1, output)
                self.assertIn(REFUSED, output)
                self.assertIn("every entry was walked): link.", output)
                self.assertNotIn("Traceback", output)
                with open(os.path.join(outside, "AGENTS.md"), "rb") as handle:
                    self.assertEqual(handle.read(), before, "nothing outside the repo was written")

    def test_broken_markers_in_this_repos_agents_md_fail_the_generator(self):
        self.edit("AGENTS.md", "<!-- ratchet:end -->", "<!-- ratchet:end -->\n<!-- ratchet:end -->")
        self.assert_check_fails("AGENTS.md: the markers of the generated block are broken")

    def test_this_repos_register_data_with_a_changed_rule_fails(self):
        self.edit("register.json", "Only the owner approves decisions.", "The owner usually approves decisions.")
        self.assert_check_fails("register.json: the rule of ratchet.owner-paths differs from Ratchet")

    def test_a_row_changed_behind_a_removed_end_marker_fails(self):
        self.edit("CONTROL-ROOM.md", "The status lives in the status issue", "The status lives in the agent\'s memory")
        self.edit("CONTROL-ROOM.md", "<!-- /generated -->", "<!-- broken -->", count=-1)
        self.assert_check_fails("CONTROL-ROOM.md: the markers of the generated blocks are broken")

    def test_a_removed_start_marker_fails(self):
        self.edit("CONTROL-ROOM.md", "<!-- generated:table control-room -->", "<!-- broken -->")
        self.assert_check_fails("CONTROL-ROOM.md: the markers of the generated blocks are broken")

    def test_a_count_block_replaced_by_plain_text_fails(self):
        # The count stands in RATCHET.md, among its other generated blocks. The README holds only the list of the principles.
        path = os.path.join(self.copy, "RATCHET.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        changed, found = re.subn(r"<!-- generated:count -->.*?<!-- /generated -->", "There are zero text-only rules (0%).", text, flags=re.S)
        self.assertEqual(found, 1)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(changed)
        self.assert_check_fails("RATCHET.md: must hold exactly these generated blocks, once each: count, principles, sources, table ")
        self.assert_check_fails(", version. Missing: count. Not expected: none")

    def test_a_block_that_the_readme_no_longer_holds_fails_there(self):
        self.append("README.md", "\n<!-- generated:count -->\n<!-- /generated -->\n")
        self.assert_check_fails("README.md: must hold exactly these generated blocks, once each: principle-list. Missing: none. "
                                "Not expected: count")

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
        self.edit("ratchet.json", '"key": "ratchet.owner-paths",', '"key": "ratchet.owner-paths",\n      "rule": "Anyone approves.",')
        self.assert_check_fails("the field 'rule' appears twice in one object")

    def test_a_label_that_disagrees_with_its_ratchet_fails(self):
        self.edit("ratchet.json", '"ratchet": "Text only: a check cannot see work that was never written down"', '"ratchet": "Check: a check sees it"')
        self.assert_check_fails("ratchet.work-in-issues: a text-only rule has a ratchet that starts with")

    def test_a_mention_of_a_key_that_is_not_a_rule_fails(self):
        self.edit("CONTROL-ROOM.md", "`ratchet.owner-paths`", "`ratchet.owner-pathss`")
        self.assert_check_fails("ratchet.owner-pathss is not a rule in ratchet.json")

    def test_an_inline_link_that_leads_nowhere_fails(self):
        self.edit(os.path.join("checks", "README.md"), "](../ratchet.json)", "](ratchet.json)")
        self.assert_check_fails("checks/README.md")
        self.assert_check_fails("the link to ratchet.json leads nowhere")

    def test_a_link_definition_that_leads_nowhere_fails(self):
        self.append("README.md", "\n[Missing source][missing]\n\n[missing]: checks/does-not-exist.py\n")
        self.assert_check_fails("the link to checks/does-not-exist.py leads nowhere")

    def test_the_links_to_the_reference_checks_lead_somewhere(self):
        # The table stands in checks/README.md alone, which the README links to, so each link is relative to checks/.
        for name in (os.path.join("checks", "README.md"),):
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
        heading = re.search(r"^## %s \(\d{4}-\d{2}-\d{2}\)$" % re.escape(fetched), rest, re.M).group(0)
        self.assert_check_fails("CHANGELOG.md: the entries must stand newest first, each version higher than the one after "
                                "it. '## 0.6 (2026-11-19)' stands before '%s'" % heading)
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
            if command[0] == "init":
                # In the new repo's own config too, so that what the README runs there starts no gc or maintenance.
                for setting in (["gc.auto", "0"], ["maintenance.auto", "false"]):
                    subprocess.run(["git", "config"] + setting, cwd=directory, check=True, stdout=subprocess.DEVNULL,
                                   env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"))
        # The start: the three commands in the README, and every step after them in STARTING.md.
        self.readme = read("README.md") + read("STARTING.md")

    def run_in_project(self, command):
        if command.startswith("rm -f "):
            # A command that puts a printed file in place is shell, run as written with this interpreter for python3.
            result = subprocess.run(["/bin/sh", "-c", command.replace("python3 ", shlex.quote(sys.executable) + " ")],
                                    cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            return result.returncode, result.stdout
        words = shlex.split(command)
        self.assertEqual(words[0], "python3")
        result = subprocess.run([sys.executable] + words[1:], cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        return result.returncode, result.stdout

    def run_the_readme(self):
        commands = re.findall(r"(?m)^\s*((?:rm -f \S+ && )?python3 \.ratchet/\S.*)$", self.readme)
        self.assertEqual(len(commands), 4)
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
        # Step 1 of "A new repo" in STARTING.md fills in AGENTS.md. Until it does, the workflow's register check fails.
        import check_register
        self.run_the_readme()
        path = os.path.join(self.project, "AGENTS.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        commands = re.findall(r"(?m)^\s+run: (python3 \.ratchet/\S.*)$", read("templates", "ratchet-checks.yml"))
        self.assertGreaterEqual(len(commands), 1)
        self.assertIn(1, [self.run_in_project(command)[0] for command in commands])
        for placeholder in check_register.PLACEHOLDERS:
            text = text.replace(placeholder, "Filled in.")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        for command in commands:
            with self.subTest(command=command):
                code, output = self.run_in_project(command)
                self.assertEqual(code, 0, output)

    def test_check_register_fails_on_the_placeholders_of_the_agents_template(self):
        import check_register
        register = os.path.join(ROOT, "templates", "register.json")
        code, output = run("check_register.py", register, "--agents", os.path.join(ROOT, "templates", "AGENTS.md"))
        self.assertEqual(code, 1, output)
        for placeholder in check_register.PLACEHOLDERS:
            self.assertIn("still holds the template's placeholder %s" % placeholder, output)
        self.assertIn("FAIL: %d problem(s)" % len(check_register.PLACEHOLDERS), output)
        code, output = run("check_register.py", register, "--agents", os.path.join(ROOT, "AGENTS.md"))
        self.assertEqual(code, 0, output)
        code, output = run("check_register.py", register, "--agents", os.path.join(scratch(self), "AGENTS.md"))
        self.assertEqual(code, 1, output)
        self.assertIn("AGENTS.md: the file is missing", output)

    def test_check_register_fails_on_a_placeholder_left_inside_a_filled_in_one(self):
        # The status issue chosen for the handover, its number not filled in, every other placeholder filled in.
        import check_register
        register = os.path.join(ROOT, "templates", "register.json")
        text = read("templates", "AGENTS.md").replace("<`HANDOVER.md`, or the status issue (#<n>)>", "status issue #N-LEFT")
        for placeholder in check_register.PLACEHOLDERS:
            text = text.replace(placeholder, "Filled in.")
        text = text.replace("N-LEFT", "<n>")
        self.assertIn("\n3. The latest handover: status issue #<n>.\n", text)
        path = os.path.join(scratch(self), "AGENTS.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, output = run("check_register.py", register, "--agents", path)
        self.assertEqual(code, 1, output)
        self.assertIn("AGENTS.md: still holds the template's placeholder <n>", output)
        self.assertIn("FAIL: 1 problem(s)", output)

    def test_the_readme_starts_with_init(self):
        commands = re.findall(r"(?m)^\s*(python3 \.ratchet/\S.*)$", self.readme)
        self.assertEqual(commands[:2], ["python3 .ratchet/checks/init.py --check", "python3 .ratchet/checks/init.py"])
        self.run_the_readme()
        for name in ("AGENTS.md", "register.json", "REGISTER.md", os.path.join(".github", "workflows", "ratchet.yml")):
            self.assertTrue(os.path.isfile(os.path.join(self.project, name)), name)

    def test_every_command_in_the_migration_runs_from_the_root_of_a_project(self):
        self.assertIn("cp .ratchet/templates/register.json register.json", read("MIGRATING.md"))
        shutil.copyfile(os.path.join(ROOT, "templates", "register.json"), os.path.join(self.project, "register.json"))
        commands = re.findall(r"(?m)^\s*((?:rm -f \S+ && )?python3 \.ratchet/\S.*)$", read("MIGRATING.md"))
        self.assertEqual(len(commands), 3)
        for command in commands:
            with self.subTest(command=command):
                code, output = self.run_in_project(command)
                self.assertEqual(code, 0, output)

    def test_no_instruction_tells_the_reader_to_leave_the_root(self):
        for name in ("README.md", "STARTING.md", "MIGRATING.md", "UPGRADING.md"):
            with self.subTest(document=name):
                text = read(name)
                self.assertIsNone(re.search(r"(?m)^\s*cd ", text))
                self.assertNotIn("run from `.ratchet", text)
                for command in re.findall(r"(?m)^\s*python3 (\S+)", text):
                    self.assertTrue(command.startswith(".ratchet/checks/"), command)

    def test_the_entry_that_is_printed_can_be_pasted(self):
        code, output = self.run_in_project("python3 .ratchet/checks/init.py")
        self.assertEqual(code, 0, output)
        code, output = self.run_in_project("python3 .ratchet/checks/generate.py --entries ratchet.simplest ratchet.test-can-fail")
        self.assertEqual(code, 0, output)
        path = os.path.join(self.project, "register.json")
        with open(path, encoding="utf-8") as handle:
            register = json.load(handle)
        register["adopted"] += json.loads("[" + output + "]")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(register, handle, indent=2)
        code, output = self.run_in_project("python3 .ratchet/checks/check_register.py register.json")
        self.assertEqual(code, 0, output)
        self.assertIn("12 rules match Ratchet", output)

    def test_the_templates_name_no_agent_tool(self):
        for name in sorted(os.listdir(os.path.join(ROOT, "templates"))):
            with self.subTest(template=name):
                self.assertIsNone(re.search(r"\.[a-z]+/skills/", read("templates", name)), "a tool's own directory for skills")



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


class NestedTooDeeply(unittest.TestCase):
    """Issue #26: the strict reader refuses data nested deeper than registry.MAX_DEPTH itself, with its own message, on
    every Python from 3.9 up. From Python 3.14 json.loads measures the C stack, not the recursion limit, and reads
    100000 levels."""

    def assert_too_deep(self, text):
        import registry
        with self.assertRaises(RecursionError) as raised:
            registry.strict_loads(text)
        self.assertEqual(str(raised.exception), "nested too deeply")
        with self.assertRaises(registry.RegistryError) as raised:
            registry.parse_json(text.encode("utf-8"))
        self.assertEqual(str(raised.exception), "not a valid data file: it is nested too deeply")

    def test_one_level_past_the_limit_is_refused(self):
        import registry
        self.assertEqual(registry.MAX_DEPTH, 100)
        self.assert_too_deep("[" * 101 + "]" * 101)
        self.assert_too_deep('{"a": ' * 101 + "1" + "}" * 101)
        self.assert_too_deep("[" * 50 + '{"a": ' * 51 + "1" + "}" * 51 + "]" * 50)
        self.assert_too_deep("[" * 100000 + "]" * 100000)

    def test_text_cut_off_deep_is_refused_as_too_deep(self):
        self.assert_too_deep("[" * 101)

    def test_the_limit_itself_is_read(self):
        import registry
        value = registry.strict_loads('{"a": ' * 100 + "1" + "}" * 100)
        for _ in range(100):
            self.assertEqual(list(value), ["a"])
            value = value["a"]
        self.assertEqual(value, 1)
        value = registry.strict_loads("[" * 100 + "]" * 100)
        for _ in range(99):
            self.assertEqual(len(value), 1)
            value = value[0]
        self.assertEqual(value, [])

    def test_brackets_in_a_string_are_not_nesting(self):
        import registry
        for text in ('["' + "[{" * 200 + '"]', '["\\"' + "[" * 200 + '"]', '{"' + "{" * 200 + '": "]"}'):
            with self.subTest(text=text[:12]):
                self.assertIsInstance(registry.strict_loads(text), (list, dict))

    def run_reader(self, text):
        """What strict_loads says of text, from a child process stopped after a few seconds. The old reader took about
        10 seconds on 64 KB of escaped quotes and 1.5 to 2 minutes on 200 KB (review of #106)."""
        code = ("import sys\nsys.dont_write_bytecode = True\nsys.path.insert(0, sys.argv[1])\nimport registry\n"
                "text = sys.stdin.read()\ntry:\n    registry.strict_loads(text)\n"
                "except (ValueError, RecursionError) as error:\n    print(type(error).__name__, error)\n"
                "else:\n    print('read')\n")
        try:
            result = subprocess.run([sys.executable, "-B", "-c", code, HERE], input=text, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, universal_newlines=True, timeout=5)
        except subprocess.TimeoutExpired:
            self.fail("the reader took more than 5 seconds on %d characters" % len(text))
        self.assertEqual(result.returncode, 0, result.stdout)
        return result.stdout

    def test_a_string_that_never_ends_is_read_in_linear_time(self):
        # An opening quote, then 100000 escaped quotes and no closing one: 200001 characters.
        output = self.run_reader('"' + '\\"' * 100000)
        self.assertTrue(output.startswith("JSONDecodeError Unterminated string"), output)

    def test_brackets_after_a_quote_that_never_ends_are_not_nesting(self):
        output = self.run_reader('"' + "[" * 101)
        self.assertTrue(output.startswith("JSONDecodeError Unterminated string"), output)
        self.assertNotIn("nested too deeply", output)

    def test_an_escaped_backslash_ends_the_escape(self):
        # The string holds one backslash, so the quote after it ends the string, and the 100 levels after it count,
        # one more than the limit with the array around them.
        self.assertEqual(self.run_reader('["\\\\",' + "[" * 100 + "]" * 100 + "]"), "RecursionError nested too deeply\n")
        self.assertEqual(self.run_reader('["\\\\",' + "[" * 99 + "]" * 99 + "]"), "read\n")


if __name__ == "__main__":
    unittest.main()
