"""Load and validate ratchet.json, the single source for every Ratchet rule, and sources.json, the list of sources.

Also the two things every check shares: a strict reader for JSON data files, and
the comparison of a generated file with what its data file generates.

sources.json is not part of what is released: checks/released_text.py does not compare it with a tag, so a
pin that moves needs no new version (D-2026-11-19-batched-releases).

Standard library only. Run on Python 3.9 and 3.12.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "ratchet.json")
SOURCES_PATH = os.path.join(ROOT, "sources.json")

KEY = re.compile(r"^ratchet\.[a-z0-9]+(-[a-z0-9]+)*\Z")
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
RULE_FIELDS = {"key", "part", "status", "enforcement", "rule", "ratchet", "source", "reference_check"}
REQUIRED_RULE_FIELDS = RULE_FIELDS - {"reference_check"}
TOP_FIELDS = {"version", "experimental_cap", "start", "parts", "rules"}
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
    lack the cap, which came in 0.5, and may hold the date and the sources, which left in 0.9. Its sources are not
    read, the files of its reference checks are not looked for, and the budget is not counted. Everything else is
    read as strictly as this version's own file.
    """
    problems = []
    if not isinstance(data, dict):
        return ["the top level must be an object"]
    for field in sorted(TOP_FIELDS - set(data) - ({CAP} if older else set())):
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

    for field in ("start", "parts", "sources", "rules"):
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
        reference = rule.get("reference_check")
        if reference is not None:
            if not PATH.match(reference) or ".." in reference:
                problems.append("%s: the reference check must be a plain path inside the repo" % name)
                continue
            if rule["enforcement"] != "enforced":
                problems.append("%s: only an enforced rule can have a reference check" % name)
            if not older and not os.path.isfile(os.path.join(root, reference)):
                problems.append("%s: the reference check %s does not exist" % (name, reference))

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
