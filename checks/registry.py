"""Load and validate ratchet.json, the single source for every Ratchet rule, and sources.json, the list of sources.

Also the two things every check shares: a strict reader for JSON data files, and
the comparison of a generated file with what its data file generates.

sources.json is not part of what is released: checks/released_text.py does not compare it with a tag, so a
pin that moves needs no new version (D-2026-11-19-batched-releases).

Standard library only. Run on Python 3.9 and 3.12.
"""

import datetime
import json
import os
import re
import stat
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "ratchet.json")
SOURCES_PATH = os.path.join(ROOT, "sources.json")

KEY = re.compile(r"^ratchet\.[a-z0-9]+(-[a-z0-9]+)*\Z")
# The key of a principle: one exact form, as the key of a rule has (D-2026-11-20-principles-and-obligations).
PRINCIPLE_KEY = re.compile(r"^principle\.[a-z0-9]+(-[a-z0-9]+)*\Z")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\Z")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
MAIL = re.compile(r"[^ ]@[^ ]")
PATH = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*\Z")
# Every ASCII punctuation mark, which is what Markdown lets a backslash escape.
PUNCTUATION = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")

# The characters a value may hold, as code points: (first, last), both included. Everything else is refused.
# The list is written out here and not read from the interpreter's Unicode tables, which differ between
# versions of Python: a value is valid or not by this list alone, the same on every version.
# Latin letters: ASCII, Latin-1, Latin Extended-A and -B, and Latin Extended Additional. Left out: the
# compatibility forms (U+0132, U+0133, U+013F, U+0140, U+0149, U+017F, U+01C4 to U+01CC, U+01F1 to U+01F3,
# U+1E9A, U+1E9B) and the click letters U+01C0 to U+01C3, which look like | and !.
LETTERS = (
    (0x0041, 0x005A), (0x0061, 0x007A),
    (0x00C0, 0x00D6), (0x00D8, 0x00F6), (0x00F8, 0x00FF),
    (0x0100, 0x0131), (0x0134, 0x013E), (0x0141, 0x0148), (0x014A, 0x017E),
    (0x0180, 0x01BF), (0x01CD, 0x01F0), (0x01F4, 0x024F),
    (0x1E00, 0x1E99), (0x1E9C, 0x1EFF),
)
DIGITS = ((0x0030, 0x0039),)
# Every ASCII punctuation mark, and sixteen marks outside ASCII:
# U+00A1 and U+00BF inverted marks, U+00A3 pound, U+00A7 section, U+00AB and U+00BB angle quotation marks,
# U+00B0 degree, U+00B7 middle dot, U+2013 and U+2014 dashes, U+2018, U+2019, U+201C, U+201D and U+201E
# quotation marks, U+20AC euro.
MARKS = (
    (0x0021, 0x002F), (0x003A, 0x0040), (0x005B, 0x0060), (0x007B, 0x007E),
    (0x00A1, 0x00A1), (0x00A3, 0x00A3), (0x00A7, 0x00A7), (0x00AB, 0x00AB), (0x00B0, 0x00B0),
    (0x00B7, 0x00B7), (0x00BB, 0x00BB), (0x00BF, 0x00BF),
    (0x2013, 0x2014), (0x2018, 0x2019), (0x201C, 0x201E), (0x20AC, 0x20AC),
)
SPACE = ((0x0020, 0x0020),)
ALLOWED = frozenset(chr(code) for first, last in LETTERS + DIGITS + MARKS + SPACE for code in range(first, last + 1))
# A letter or a digit from the list above: what makes a value hold a word.
WORD = re.compile("[%s]" % "".join("%s-%s" % (chr(first), chr(last)) for first, last in LETTERS + DIGITS))
# A name between two colons, which a site that renders the file may replace with a picture after Markdown is done:
# one or more letters or digits from the list above, or _ + -, between two colons.
EMOJI_NAME = re.compile(":[%s_+\\-]+:" % "".join("%s-%s" % (chr(first), chr(last)) for first, last in LETTERS + DIGITS))

STATUSES = ("core", "experimental")
ENFORCEMENTS = ("enforced", "text-only")
RULE_FIELDS = {"key", "part", "principle", "status", "enforcement", "rule", "ratchet", "source", "reference_check", "since",
               "kept_by", "not_used_because"}
# The fields of an experimental rule only: the version it entered Ratchet, which every experimental rule names from
# 0.10, and the decision that kept it once more (D-2026-11-19-one-point-oh, choice 4). The ratchet.json of an older
# version has neither.
AGE_FIELDS = ("since", "kept_by")
# A field of an experimental rule only: why Ratchet itself cannot use the rule. A rule that enters Ratchet is adopted in
# Ratchet's own register, or names this (D-2026-11-20-proposal-triage, choice 5). generate.py --check reads the two
# together, since only it reads the register too.
NOT_USED = "not_used_because"
# Every rule names the key of one principle in "principle". It is read on its own, after the other fields, since the
# ratchet.json of a version before 0.10 has no principles and no rule of it names one.
PRINCIPLE = "principle"
REQUIRED_RULE_FIELDS = RULE_FIELDS - {"reference_check", NOT_USED, PRINCIPLE} - set(AGE_FIELDS)
# An experimental rule that has stood through this many releases and this many days, with no decision, fails.
AGE_RELEASES = 3
AGE_DAYS = 60
DECISION_ID = re.compile(r"^D-([0-9]{4}-[0-9]{2}-[0-9]{2})-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
TOP_FIELDS = {"version", "experimental_cap", "start", "principles", "parts", "rules"}
# The principles, from 0.10: a heading over the rules, a question to ask when no rule fits or an aim, and text only. It
# names no check, and what is checked is the rules under it (D-2026-11-20-principles-and-obligations). A principle has exactly these fields, each text.
PRINCIPLES = "principles"
PRINCIPLE_FIELDS = ("key", "title", "text")
# A title is short, as a heading. A text applies to cases no one listed, in at most this many sentences.
TITLE_LENGTH = 60
SENTENCES = 3
# Where a sentence ends: a full stop, a question mark or an exclamation mark, then a space or the end of the text.
SENTENCE_END = re.compile(r"[.?!](?= |\Z)")
# The fields that ratchet.json had up to 0.8 and no longer has: the date, which is in the heading of the entry in
# CHANGELOG.md, and the sources, which are in sources.json (D-2026-11-19-batched-releases). The ratchet.json of an
# older version may hold them.
GONE_FIELDS = {"date", "sources"}
# The budget: the most experimental rules there may be (D-2026-11-17-pull-and-budget). Raising it is a decision.
CAP = "experimental_cap"

SOURCE_FIELDS = {"name", "repo", "directory", "author", "commit", "license"}
REQUIRED_SOURCE_FIELDS = {"name", "repo", "commit", "license"}
# A source repository on GitHub: the address, an owner and a repository, and nothing else. An owner and a
# repository are written in the characters GitHub allows in them.
OWNER = r"[A-Za-z0-9][A-Za-z0-9-]{0,38}"
REPOSITORY = r"[A-Za-z0-9._-]{1,100}"
GITHUB_REPO = re.compile(r"^https://github\.com/(%s)/(%s)\Z" % (OWNER, REPOSITORY))
# The name of a source goes into the title and the body of an issue as plain text, so it has a narrow form:
# lowercase letters, digits, ".", "-" and "/", starting with a letter or a digit. It has no "_", because the
# watch writes no "_" outside a link (an "_" can start emphasis). At most SOURCE_LENGTH characters, so that
# "Source pin missing: " and the name fit GitHub's 256 characters for a title with room to spare, and the
# title is never cut.
SOURCE_LENGTH = 100
SOURCE_NAME = r"[a-z0-9][a-z0-9./-]{0,%d}" % (SOURCE_LENGTH - 1)
# A directory in a repository: parts of the same characters but "/", joined by single "/". No part is ".",
# and no ".." stands anywhere in it.
SOURCE_DIRECTORY = r"(?=[a-z0-9./-]{1,%d}\Z)[a-z0-9.-]+(?:/[a-z0-9.-]+)*" % SOURCE_LENGTH
# Text that GitHub turns into a link or a reference although it holds only the characters above: a "www."
# address and a "GH-" issue reference (GitHub's "Autolinked references and URLs").
AUTOLINK = re.compile(r"www\.|gh-[0-9]", re.IGNORECASE)
COMMIT = re.compile(r"^[0-9a-f]{40}\Z")

TABLE_HEADER = "| Key | Rule | Ratchet | Source |"
TABLE_RULE = "|---|---|---|---|"


class RegistryError(Exception):
    """ratchet.json is missing, unreadable or breaks its own format."""


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("the field %r appears twice in one object" % key)
        result[key] = value
    return result


def _constant(name):
    raise ValueError("%s is not allowed" % name)


def strict_loads(text):
    """Parse JSON text strictly: no field twice in one object, no NaN or Infinity.

    Raises ValueError, or RecursionError for text nested too deeply. Every check that reads JSON parses it here.
    """
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)


def load_json(path):
    """Read a JSON data file strictly: valid UTF-8, no field twice in one object, no NaN or Infinity."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError as error:
        raise RegistryError("not a valid data file: %s" % error)
    return parse_json(data)


def parse_json(data):
    """The bytes of a JSON data file, read strictly as load_json reads a file."""
    try:
        text = data.decode("utf-8", errors="strict")
        return strict_loads(text)
    except RecursionError:
        raise RegistryError("not a valid data file: it is nested too deeply")
    except UnicodeDecodeError as error:
        raise RegistryError("not a valid data file: it %s" % not_utf8(error))
    except ValueError as error:
        raise RegistryError("not a valid data file: %s" % error)


def not_utf8(error):
    """What to say about bytes that are not UTF-8. They are never read as some other character."""
    return "is not valid UTF-8, at byte %d (0x%02X)" % (error.start, error.object[error.start])


def text_problem(value):
    """Why a value cannot stand in a data file as one line of text, or None.

    A value is text, never Markdown. It is one line, with no | and no spaces at
    the ends. Every character is in ALLOWED: a Latin letter, a digit, a plain space
    or one of the listed marks. Everything else is refused, whatever it is: another
    script, a combining mark, a control or format character, another kind of space,
    a character that is written right to left or that changes the order a line is
    shown in, a replacement character, a compatibility form such as a full-width
    letter. No two characters in ALLOWED join into another, so a value is in the
    normal forms NFC and NFKC as it stands.

    A name between two colons is refused, in text and in code, because a site may
    show it as a picture. An @ does not stand between two characters, because that
    is read as a mail address whatever is escaped.

    The one form besides text is code: a part between a pair of backticks. That is
    the data's own way to mark code. It is not read as Markdown.
    """
    if not isinstance(value, str):
        return "must be text"
    if value != value.strip(" ") or "\n" in value or "\r" in value or "|" in value:
        return "must be one line, without | and without spaces at the ends"
    for character in value:
        if character not in ALLOWED:
            return (
                "holds U+%04X, which is not among the characters a value may hold: "
                "Latin letters, digits, the plain space and the marks listed in checks/README.md" % ord(character)
            )
    name = EMOJI_NAME.search(value)
    if name:
        return (
            "has %s, which is a name between two colons. A site that renders the file may show it as a picture. "
            "Put a space beside one of the colons" % name.group(0)
        )
    parts = value.split("`")
    if len(parts) % 2 == 0:
        return "has a backtick without its pair. A pair of backticks marks code"
    if "``" in value:
        return "has two backticks in a row. Code is one part between one pair, with text between two such parts"
    for code in parts[1::2]:
        if not code.strip(" ") or code != code.strip(" "):
            return "has code that is empty or has spaces at its ends"
    if any(MAIL.search(text) for text in parts[0::2]):
        return "has @ between two characters, which can be turned into a mail link. Write it as code, or put a space beside the @"
    return None


def cell(value):
    """A value as it is written into generated Markdown.

    Text is written so that Markdown reads none of it as markup: every ASCII
    punctuation mark gets a backslash. Code, the part between a pair of backticks
    in the data, is written as a code span fenced by more backticks than it holds.
    No value can become a link, an image, emphasis, HTML or a comment.
    """
    parts = value.split("`")
    for number, part in enumerate(parts):
        if number % 2:
            runs = re.findall(r"`+", part)
            fence = "`" * (max([len(run) for run in runs] or [0]) + 1)
            parts[number] = fence + part + fence
        else:
            parts[number] = "".join("\\" + c if c in PUNCTUATION else c for c in part)
    return "".join(parts)


def ratchet_problem(value):
    """Why a ratchet is not "Check: ..." or "Text only" with its reason, or None."""
    if value.startswith("Check: ") and WORD.search(value[len("Check: "):]):
        return None
    if value.startswith("Text only") and WORD.search(value[len("Text only"):]):
        return None
    return 'the ratchet is "Check: " and the check, or "Text only" and the reason no check can see the rule'


def read(path):
    """The text of a file, or None if there is no such file.

    One policy for line endings, everywhere: CRLF is read as LF, and generated files
    are written with LF. A carriage return alone is kept and so counts as a difference.
    The file is read as strict UTF-8. Bytes that are not UTF-8 are an error, with the
    file named: they are never read as some other character.
    """
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        return data.decode("utf-8", errors="strict").replace("\r\n", "\n")
    except UnicodeDecodeError as error:
        raise RegistryError("%s: %s. Every file a check reads is UTF-8" % (path, not_utf8(error)))


# The trees that refuse_links passed in this process. write_file writes only inside one.
_WALKED = []
# A symbolic link in the index of git, in the output of git ls-files -s.
LINK_MODE = "120000"


def tracked_links(top):
    """The paths, relative to top, of the symbolic links that git tracks under top, or None when top is not in a git
    work tree or git cannot be run. git runs with a fixed list of arguments and no shell, with no GIT_ variable of
    the environment, no global or system config, no fsmonitor and no optional locks, so it reads the index and
    writes nothing."""
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0",
               LC_ALL="C")
    try:
        result = subprocess.run(["git", "-c", "core.fsmonitor=false", "ls-files", "-s", "-z"], cwd=top, env=env,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    links = []
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        head, tab, path = entry.partition(b"\t")
        if not tab:
            return None
        if head.split(b" ")[0] == LINK_MODE.encode("ascii"):
            links.append(os.fsdecode(path))
    return links


def refuse_links(root):
    """Return None if root may be written in, or what to say, naming each link, if it may not. Only a tree that passes
    is recorded, and write_file writes nowhere else.

    In a git work tree, root is refused while git tracks a symbolic link under it (git ls-files -s, mode 120000).
    A link that git does not track, such as one that the user's own tools make in .venv or node_modules, does not
    refuse it: write_file refuses a link on the path of each file it writes. Where root is not in a git work tree, or
    git cannot be run, root is walked without following a link, skipping .git, and refused while any entry is a link.

    generate.py, and check_register.py before it writes, call this first, before anything else is read or written. A
    tree whose content is not trusted, a branch, a project's tree or a fixture, can hold a link that leads anywhere, and
    a write through it would land there with the rights of whoever runs the check (round 3 of #100).
    """
    top = os.path.abspath(root)
    links = tracked_links(top)
    if links is not None:
        how = "that git tracks (git ls-files)"
    else:
        how = "(it is not a git work tree, or git could not be run, so every entry was walked)"
        links = []
        for folder, folders, files in os.walk(top, followlinks=False):
            folders[:] = sorted(name for name in folders if name != ".git")
            for name in sorted(folders + [name for name in files if name != ".git"]):
                path = os.path.join(folder, name)
                if os.path.islink(path):
                    links.append(os.path.relpath(path, top).replace(os.sep, "/"))
    if links:
        return ("%s holds %d symbolic link(s) %s: %s. Nothing is written in a tree that holds a link, since a write could "
                "follow one out of it. Replace each link with a regular file, such as a copy of what it points at, and run "
                "this again" % (root or ".", len(links), how, ", ".join(sorted(links))))
    if top not in _WALKED:
        _WALKED.append(top)
    return None


def forget_walks():
    """Forget every tree that refuse_links passed. For the tests."""
    del _WALKED[:]


def link_on_path(top, target):
    """The first part of the path from top down to target, target included, that is a symbolic link, or None. A part
    that does not exist yet ends the search: nothing below it exists either."""
    path = top
    for part in os.path.relpath(target, top).split(os.sep):
        path = os.path.join(path, part)
        try:
            if stat.S_ISLNK(os.lstat(path).st_mode):
                return path
        except FileNotFoundError:
            return None
    return None


def write_file(path, data, parents=False):
    """Write data, text as UTF-8 with its line endings as they are, or bytes, to path. The one place where
    generate.py and check_register.py write.

    Refused, with RegistryError, unless refuse_links passed a tree in this process that path stands in, after "." and
    ".." are resolved, or if any part of the path from that tree down to the file, the file included, is a symbolic
    link. The parts are checked again after the directories above the file are made, with parents. The file is opened
    without following a link at its last part, and is written only if it is a regular file with no second hard link.
    """
    target = os.path.abspath(path)
    if not _WALKED:
        raise RegistryError("%s: not written: no tree was checked for links first" % path)
    tops = [top for top in _WALKED if os.path.commonpath([top, target]) == top and target != top]
    if not tops:
        raise RegistryError("%s: not written: it stands outside the tree that was checked for links" % path)
    top = max(tops, key=len)
    if isinstance(data, str):
        data = data.encode("utf-8", errors="strict")
    def refuse_link():
        link = link_on_path(top, target)
        if link:
            raise RegistryError("%s: not written: %s is a symbolic link. Replace it with a regular file or directory"
                                % (path, os.path.relpath(link, top).replace(os.sep, "/")))

    refuse_link()
    if parents:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        refuse_link()
    flags = os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(target, flags, 0o666)
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise RegistryError("%s: not written: it is not a regular file" % path)
        if status.st_nlink != 1:
            raise RegistryError("%s: not written: it has a second hard link, which could stand outside the tree" % path)
        os.ftruncate(descriptor, 0)
        handle = os.fdopen(descriptor, "wb")
    except BaseException:
        os.close(descriptor)
        raise
    with handle:
        handle.write(data)


def compare(name, current, expected, source):
    """Problems with a generated file: it must be, byte for byte, what its data file generates."""
    if current is None:
        return ["%s: the file is missing. Generate it from %s" % (name, source)]
    if current == expected:
        return []
    have, want = current.split("\n"), expected.split("\n")
    line = next((n for n, (a, b) in enumerate(zip(have, want), 1) if a != b), min(len(have), len(want)) + 1)
    def show(lines):
        text = lines[line - 1] if line <= len(lines) else "(the file ends)"
        return repr(text if len(text) <= 100 else text[:97] + "...")
    return [
        "%s: is not what %s generates. It is generated: change %s, never this file. First difference at line %d\n  expected: %s\n  found:    %s"
        % (name, source, source, line, show(want), show(have))
    ]


def load(path=SOURCE):
    """Return the parsed registry, or raise RegistryError listing every problem."""
    try:
        data = load_json(path)
    except RegistryError as error:
        raise RegistryError("%s: %s" % (path, error))
    problems = validate(data, os.path.dirname(os.path.abspath(path)))
    if problems:
        raise RegistryError("\n".join("%s: %s" % (os.path.basename(path), p) for p in problems))
    return data


def validate(data, root, older=False):
    """Every problem with a parsed ratchet.json, or nothing.

    With older=True, the ratchet.json of an older version, which checks/upgrade.py compares with this one: it may
    lack the cap, which came in 0.5, may hold the date and the sources, which left in 0.9, and its experimental
    rules may lack "since", which came in 0.10. Its sources are not read, the files of its reference checks and of
    the decisions in "kept_by" are not looked for, and the budget is not counted. Everything else is read as
    strictly as this version's own file.
    """
    problems = []
    if not isinstance(data, dict):
        return ["the top level must be an object"]
    for field in sorted(TOP_FIELDS - set(data) - ({CAP, PRINCIPLES} if older else set())):
        problems.append("missing field %r" % field)
    for field in sorted(set(data) - TOP_FIELDS - (GONE_FIELDS if older else set())):
        problems.append("unknown field %r" % field)
    if problems:
        return problems

    if not isinstance(data["version"], str) or not VERSION.match(data["version"]):
        problems.append("version must look like 0.2")
    if "date" in data and (not isinstance(data["date"], str) or not DATE.match(data["date"])):
        problems.append("date must look like 2026-01-31")
    cap = data.get(CAP)
    if CAP in data and (isinstance(cap, bool) or not isinstance(cap, int) or cap < 0):
        problems.append("%s must be a whole number from 0, found %s" % (CAP, json.dumps(cap)))

    for field in ("start", "principles", "parts", "sources", "rules"):
        if field in data and not isinstance(data[field], list):
            problems.append("%s must be a list" % field)
    if problems:
        return problems

    parts = {}
    for part in data["parts"]:
        if not isinstance(part, dict) or set(part) != {"id", "file", "title"} or not all(isinstance(value, str) for value in part.values()):
            problems.append("a part needs exactly id, file and title: %r" % (part,))
            continue
        if part["id"] in parts:
            problems.append("part %s is listed twice" % part["id"])
        parts[part["id"]] = part

    principles = principle_problems(data.get(PRINCIPLES, []), problems)
    under = dict((key, 0) for key in principles)

    keys = set()
    for rule in data["rules"]:
        name = rule.get("key", "<no key>") if isinstance(rule, dict) else "<not an object>"
        if not isinstance(rule, dict):
            problems.append("a rule must be an object")
            continue
        missing = sorted(REQUIRED_RULE_FIELDS - set(rule))
        unknown = sorted(set(rule) - RULE_FIELDS)
        if missing:
            problems.append("%s: missing %s" % (name, ", ".join(missing)))
        if unknown:
            problems.append("%s: unknown field %s" % (name, ", ".join(unknown)))
        if missing or unknown:
            continue
        if not all(isinstance(value, str) for value in rule.values()):
            problems.append("%s: every field must be a string" % name)
            continue
        if not KEY.match(name):
            problems.append("%s: a key is ratchet. followed by lowercase words joined by hyphens" % name)
        if name in keys:
            problems.append("%s: the key is used twice" % name)
        keys.add(name)
        if rule["part"] not in parts:
            problems.append("%s: unknown part %s" % (name, rule["part"]))
        if PRINCIPLE not in rule:
            if PRINCIPLES in data:
                problems.append("%s: has no principle. Every rule names the key of one principle in principles" % name)
        elif rule[PRINCIPLE] not in under:
            problems.append("%s: names %s, which is not a principle in principles" % (name, rule[PRINCIPLE]))
        else:
            under[rule[PRINCIPLE]] += 1
        if rule["status"] not in STATUSES:
            problems.append("%s: status must be one of %s" % (name, ", ".join(STATUSES)))
        if rule["enforcement"] not in ENFORCEMENTS:
            problems.append("%s: enforcement must be one of %s" % (name, ", ".join(ENFORCEMENTS)))
        for field in ("rule", "ratchet", "source"):
            if text_problem(rule[field]):
                problems.append("%s: %s %s" % (name, field, text_problem(rule[field])))
        if not rule["rule"]:
            problems.append("%s: the rule is empty" % name)
        names_check = rule["ratchet"].startswith("Check: ")
        admits_text = rule["ratchet"].startswith("Text only")
        if rule["enforcement"] == "enforced" and not names_check:
            problems.append('%s: an enforced rule has a ratchet that starts with "Check: "' % name)
        if rule["enforcement"] == "text-only" and not admits_text:
            problems.append('%s: a text-only rule has a ratchet that starts with "Text only"' % name)
        if ratchet_problem(rule["ratchet"]):
            problems.append("%s: %s" % (name, ratchet_problem(rule["ratchet"])))
        problems += ["%s: %s" % (name, problem) for problem in age_field_problems(rule, root, older)]
        if NOT_USED in rule:
            if rule["status"] != "experimental":
                problems.append("%s: only an experimental rule has %s" % (name, NOT_USED))
            elif text_problem(rule[NOT_USED]):
                problems.append("%s: %s %s" % (name, NOT_USED, text_problem(rule[NOT_USED])))
            elif not WORD.search(rule[NOT_USED]):
                problems.append("%s: %s must say why, in words" % (name, NOT_USED))
        reference = rule.get("reference_check")
        if reference is not None:
            if not PATH.match(reference) or ".." in reference:
                problems.append("%s: the reference check must be a plain path inside the repo" % name)
                continue
            if rule["enforcement"] != "enforced":
                problems.append("%s: only an enforced rule can have a reference check" % name)
            if not older and not os.path.isfile(os.path.join(root, reference)):
                problems.append("%s: the reference check %s does not exist" % (name, reference))

    if not problems:
        for key, count in under.items():
            if not count:
                problems.append("%s has no rule under it. A principle stands over at least one rule" % key)

    if not all(isinstance(key, str) for key in data["start"]):
        problems.append("start must list keys")
        return problems
    if len(set(data["start"])) != len(data["start"]):
        problems.append("start lists a key twice")
    for key in data["start"]:
        if key not in keys:
            problems.append("start names %s, which is not a rule" % key)

    if older or problems:
        return problems
    return budget_problems(data)


def principle_problems(principles, problems):
    """Read the list of principles, add every problem with it to problems, and return the keys of the principles.

    A principle is an object with exactly a key, a title and a text, each text. The key has the one form
    principle.<slug> and is used once. The title holds words, has no two spaces in a row, is at most TITLE_LENGTH
    characters long, and is not the title of another principle, compared without regard to case. The text holds words, ends a sentence, and has at
    most SENTENCES sentences. Title and text are values like every other: one line from the fixed list of characters.
    A principle names no check: a field "check", or any other field, is unknown.
    """
    keys, titles = [], {}
    for principle in principles:
        if not isinstance(principle, dict):
            problems.append("a principle must be an object")
            continue
        name = principle.get("key") if isinstance(principle.get("key"), str) else "<a principle with no key>"
        missing = [field for field in PRINCIPLE_FIELDS if field not in principle]
        unknown = sorted(set(principle) - set(PRINCIPLE_FIELDS))
        if missing:
            problems.append("%s: missing %s" % (name, ", ".join(missing)))
        if unknown:
            problems.append("%s: unknown field %s. A principle has exactly key, title and text, and names no check of its own"
                            % (name, ", ".join(unknown)))
        if missing or unknown:
            continue
        if not all(isinstance(value, str) for value in principle.values()):
            problems.append("%s: every field must be a string" % name)
            continue
        if not PRINCIPLE_KEY.match(name):
            problems.append("%s: a key is principle. followed by lowercase words joined by hyphens" % name)
        if name in keys:
            problems.append("%s: the key is used twice" % name)
        keys.append(name)
        title, text = principle["title"], principle["text"]
        if text_problem(title):
            problems.append("%s: title %s" % (name, text_problem(title)))
        elif not WORD.search(title):
            problems.append("%s: the title holds no words" % name)
        elif "  " in title:
            problems.append("%s: the title has two spaces in a row, and HTML shows them as one" % name)
        elif len(title) > TITLE_LENGTH:
            problems.append("%s: the title is %d characters long, and a title is at most %d" % (name, len(title), TITLE_LENGTH))
        elif title.lower() in titles:
            problems.append("%s: its title is the title of %s, compared without regard to case" % (name, titles[title.lower()]))
        else:
            titles[title.lower()] = name
        if text_problem(text):
            problems.append("%s: text %s" % (name, text_problem(text)))
        elif not WORD.search(text):
            problems.append("%s: the text holds no words" % name)
        elif text[-1] not in ".?!":
            problems.append("%s: the text must end with a full stop, a question mark or an exclamation mark, so that its "
                            "sentences can be counted" % name)
        elif len(SENTENCE_END.findall(text)) > SENTENCES:
            problems.append("%s: the text has %d sentences, and a principle has at most %d"
                            % (name, len(SENTENCE_END.findall(text)), SENTENCES))
    return keys


def rules_under(data, key):
    """The rules under one principle, in the order of ratchet.json."""
    return [rule for rule in data["rules"] if rule.get(PRINCIPLE) == key]


def version_key(version):
    """A version of the form MAJOR.MINOR as a pair of integers, so that 0.10 is newer than 0.9."""
    major, minor = version.split(".")
    return int(major), int(minor)


def decision_date(value):
    """The date in the id of a decision, D-YYYY-MM-DD-<slug>, or None when it is not of that form or the date does not exist."""
    match = DECISION_ID.match(value) if isinstance(value, str) else None
    if not match:
        return None
    try:
        return datetime.date(*map(int, match.group(1).split("-")))
    except ValueError:
        return None


def age_field_problems(rule, root, older):
    """Why "since" and "kept_by" of one rule break their form, or nothing.

    An experimental rule names "since", the version it entered Ratchet. It may name "kept_by", the id of the decision
    that kept it once more, whose file is in decisions/. A core rule names neither. That "since" names a version with
    an entry in the changelog, or this version, is read by age_problems, which has the changelog: so a version later
    than this one fails there. The reader does not compare it with "version", which the tests of release.py rewrite.
    """
    problems = []
    if rule["status"] != "experimental":
        return ["only an experimental rule has %s" % field for field in AGE_FIELDS if field in rule]
    if "since" not in rule:
        if not older:
            problems.append("an experimental rule has since, the version it entered Ratchet")
    elif not VERSION.match(rule["since"]):
        problems.append("since must look like 0.2")
    if "kept_by" in rule:
        if decision_date(rule["kept_by"]) is None:
            problems.append("kept_by must be the id of a decision, D-YYYY-MM-DD-<slug>, with a date that exists")
        elif not older and not os.path.isfile(os.path.join(root, "decisions", rule["kept_by"] + ".md")):
            problems.append("kept_by names %s, and decisions/%s.md does not exist" % (rule["kept_by"], rule["kept_by"]))
    return problems


def first_too_old(releases, version):
    """The first release, in version order, at which a rule counted from version has stood too long, or None.

    That is the first release with AGE_RELEASES releases after version, up to and with it, that is AGE_DAYS days or
    more after the date of version.
    """
    later = sorted((each for each in releases if version_key(each) > version_key(version)), key=version_key)
    for number, each in enumerate(later, 1):
        if number >= AGE_RELEASES and (releases[each] - releases[version]).days >= AGE_DAYS:
            return each
    return None


def age_problems(data, releases):
    """Why an experimental rule has stood too long with no decision, one problem per rule, or nothing.

    releases maps each version that has an entry with a date in CHANGELOG.md to that date. The age is measured at
    the newest of them, so it changes only when a release is dated, and the pull request of a release is where it
    fails: in the clean-out at a release (D-2026-11-17-improvement-loop, item 4). A rule has stood too long when
    AGE_RELEASES releases have come after the version in "since" and the newest is AGE_DAYS days or more after the
    date of that version. A rule kept by the decision in "kept_by" stands one age more, counted the same way from
    the release at which it first stood too long. The decision's date does not move the count, so a rule is kept
    once: naming another decision in "kept_by" keeps it no longer, and when its age more has run out, it is not
    offered another keep. A rule that entered in this version, which has no date yet, has no age.
    """
    if not releases:
        return []
    newest = max(releases, key=version_key)
    problems = []
    for rule in data["rules"]:
        if rule["status"] != "experimental":
            continue
        since = rule["since"]
        if since not in releases and since != data["version"]:
            problems.append("%s: since is %s, which has no entry with a date in CHANGELOG.md and is not this version, %s"
                            % (rule["key"], since, data["version"]))
            continue
        if since not in releases:
            continue
        first = first_too_old(releases, since)
        if first is None:
            continue
        if "kept_by" not in rule:
            problems.append(
                "%s is experimental since %s and has stood through %d releases and %d days, up to %s (%s), with no decision "
                "to keep it. In the clean-out of this release, move it into the core, merge it with another rule, remove it, "
                "or keep it once more by a decision named in kept_by (D-2026-11-19-one-point-oh)"
                % (rule["key"], since, sum(1 for each in releases if version_key(each) > version_key(since)),
                   (releases[newest] - releases[since]).days, newest, releases[newest].isoformat()))
        elif first_too_old(releases, first) is not None:
            problems.append(
                "%s was kept by %s and has stood through %d releases and %d days more since it first stood too long, at %s "
                "(%s), up to %s (%s). It has had its one keep, and another decision in kept_by keeps it no longer. In the "
                "clean-out of this release, move it into the core, merge it with another rule, or remove it "
                "(D-2026-11-19-one-point-oh)"
                % (rule["key"], rule["kept_by"], sum(1 for each in releases if version_key(each) > version_key(first)),
                   (releases[newest] - releases[first]).days, first, releases[first].isoformat(), newest,
                   releases[newest].isoformat()))
    return problems


def load_sources(path=SOURCES_PATH):
    """The list of sources in sources.json, or RegistryError naming every problem.

    The file is read as strictly as every data file: strict UTF-8, no field twice, no NaN. It is an object with
    the one field "sources", and every source has the form that source_problems describes.
    """
    name = os.path.basename(path)
    try:
        data = load_json(path)
    except RegistryError as error:
        raise RegistryError("%s: %s" % (name, error))
    problems = sources_file_problems(data)
    if problems:
        raise RegistryError("\n".join("%s: %s" % (name, problem) for problem in problems))
    return data["sources"]


def sources_file_problems(data):
    """Why a parsed sources.json breaks its form, or nothing."""
    if not isinstance(data, dict):
        return ["the top level must be an object"]
    problems = [] if "sources" in data else ["missing field 'sources'"]
    problems += ["unknown field %r" % field for field in sorted(set(data) - {"sources"})]
    return problems or source_problems(data["sources"])


def citation_problems(data, sources):
    """Why the source of a rule does not cite the sources by their names in sources.json, or nothing.

    The source of a rule is empty, or one or more citations separated by "; ". A citation starts with the name of
    a source in sources.json, and then, after a space or a comma, says what is taken from it.
    """
    names = set(source["name"] for source in sources)
    problems = []
    for rule in data["rules"]:
        for name in cited_names(rule):
            if name not in names:
                problems.append('%s: the source cites "%s", which is not the name of a source in sources.json. A source is a list '
                                'of names from sources.json, each with what is taken from it, separated by "; "' % (rule["key"], name))
    return problems


def cited_names(rule):
    """The names of the sources a rule cites, in the order it cites them, each once. Empty when its source is empty."""
    names = []
    for part in rule["source"].split("; ") if rule["source"] else []:
        name = re.split(r"[ ,]", part, 1)[0]
        if name not in names:
            names.append(name)
    return names


def budget_problems(data):
    """Why the experimental rules break the budget, or nothing. A new rule replaces, merges or removes one."""
    experimental = counts(data)["experimental"]["rules"]
    if experimental <= data[CAP]:
        return []
    return [
        "there are %d experimental rules, which is more than the cap of %d in %s. A new experimental rule replaces, "
        "merges or removes one, or a decision raises the cap (D-2026-11-17-pull-and-budget)" % (experimental, data[CAP], CAP)
    ]


def github_repo(value):
    """(owner, repository) for the address of a repository on GitHub, or None."""
    match = GITHUB_REPO.match(value) if isinstance(value, str) else None
    if not match or match.group(2) in (".", "..") or match.group(2).endswith(".git"):
        return None
    return match.group(1), match.group(2)


def plain_directory(value):
    """Whether a value is a directory of the narrow form: no part ".", no "..", no "/" at its ends or twice."""
    return (
        isinstance(value, str) and re.fullmatch(SOURCE_DIRECTORY, value) is not None
        and ".." not in value and "." not in value.split("/")
    )


def source_repo_text(source):
    """The repo of a source as RATCHET.md shows it: the address, then the directory and the author if given."""
    text = source["repo"]
    if "directory" in source:
        text += ", directory `%s`" % source["directory"]
    if "author" in source:
        text += " (by %s)" % source["author"]
    return text


def source_problems(sources):
    """Why the list of sources breaks its form, as messages that each name the source. Empty if it holds.

    A source has a name, a repo, a commit and a license, and may have a directory and an author. The name and
    the directory have the narrow form above, and the name is used once. The repo is https://github.com/ with
    an owner and a repository and nothing else. The commit is a full sha in lowercase hex. The author and the
    license are text from the fixed list.
    """
    if not isinstance(sources, list):
        return ["sources must be a list"]
    problems, names = [], set()
    for number, source in enumerate(sources, 1):
        name = source.get("name") if isinstance(source, dict) else None
        good_name = isinstance(name, str) and re.fullmatch(SOURCE_NAME, name) is not None and not AUTOLINK.search(name)
        label = name if good_name else str(number)
        said = []
        if not isinstance(source, dict):
            said.append("a source must be an object")
        else:
            said += ["missing field %r" % field for field in sorted(REQUIRED_SOURCE_FIELDS - set(source))]
            said += ["unknown field %r" % field for field in sorted(set(source) - SOURCE_FIELDS)]
            if not said:
                if not isinstance(name, str) or re.fullmatch(SOURCE_NAME, name) is None:
                    said.append("the name must be lowercase letters, digits, '.', '-' and '/', start with a letter "
                                "or a digit, and be at most %d characters long" % SOURCE_LENGTH)
                elif AUTOLINK.search(name):
                    said.append("the name holds text that GitHub turns into a link or a reference")
                elif name in names:
                    said.append("the name is used twice")
                names.add(label)
                for field in ("author", "license"):
                    if field in source and text_problem(source[field]):
                        said.append("%s %s" % (field, text_problem(source[field])))
                if github_repo(source["repo"]) is None:
                    said.append("the repo must be https://github.com/ and an owner and a repository, and nothing else")
                if "directory" in source:
                    if not plain_directory(source["directory"]):
                        said.append("the directory must be lowercase letters, digits, '.' and '-', in parts joined by "
                                    "single '/', with no part '.' and no '..', and be at most %d characters long"
                                    % SOURCE_LENGTH)
                    elif AUTOLINK.search(source["directory"]):
                        said.append("the directory holds text that GitHub turns into a link or a reference")
                if not isinstance(source["commit"], str) or not COMMIT.match(source["commit"]):
                    said.append("the commit must be a full 40-character sha, in lowercase hex")
                if not said and text_problem(source_repo_text(source)):
                    said.append("the repo as RATCHET.md shows it %s" % text_problem(source_repo_text(source)))
        problems += ["source %s: %s" % (label, problem) for problem in said]
    return problems


def row(rule):
    """The one canonical markdown row for a rule. Project registers copy it verbatim."""
    return "| %s | %s | %s | %s |" % (rule["key"], cell(rule["rule"]), cell(rule["ratchet"]), cell(rule["source"]) or "—")


def rules_by_key(data):
    return {rule["key"]: rule for rule in data["rules"]}


def counts(data):
    """Count rules by status and enforcement. The text-only share covers the core only."""
    result = {}
    for status in STATUSES:
        rules = [rule for rule in data["rules"] if rule["status"] == status]
        enforced = [rule for rule in rules if rule["enforcement"] == "enforced"]
        result[status] = {
            "rules": len(rules),
            "enforced": len(enforced),
            "text_only": len(rules) - len(enforced),
            "reference_checks": len([rule for rule in enforced if rule.get("reference_check")]),
        }
    core = result["core"]
    result["text_only_percent"] = int(round(100.0 * core["text_only"] / core["rules"])) if core["rules"] else 0
    return result
