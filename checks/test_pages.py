"""The landing page, docs/index.html, loads nothing from another origin and says only what the repo shows.

    python3 -m unittest discover -s checks -v

GitHub Pages serves docs/ from main as it stands, with no build step (docs/.nojekyll). The page is a test of this
repo, not a reference check. The test reads the page strictly and fails on what it does not know:

- the page is strict UTF-8, holds no control character but the newline and no character that reorders text, and
  starts with "<!DOCTYPE html>"
- html.parser reads it as well-formed: every element is one the page may hold, with only the attributes it may
  have, each once; every element that is opened is closed, in order; a void element is never closed; there is no
  comment, no processing instruction and no other declaration. There is no script, no frame, no form, no base,
  no style attribute and no event handler, because none of them is an element or an attribute the page may hold
- the page holds no inline SVG: an <svg>, and every element of SVG, is not an element the page may hold, so nothing
  comes in through one. The only <title> is the one in <head>
- the one figure is a file of its own, docs/ratchet-notch.svg, which one <img> loads, once, with alt text. The test
  reads that file as strictly as the page: strict UTF-8, no hidden character, no doctype, comment, processing
  instruction or reference, well-formed XML of six elements of SVG, svg, style, rect, path, circle and text, each
  directly in the <svg> and with only the attributes it may have, whose values are numbers and words. So there is
  no script, use, image, link or foreignObject in it, no href, no style attribute and no event handler. Its one
  <style> follows the rules of the page's CSS, and each color in it is the page's color of the same name
- nothing is loaded from another origin: what an element loads (img src, source srcset, link href) is the name of
  a file in docs/. The CSS in the one <style> element has no at-rule but @media and @keyframes, no function but
  var(), no backslash and no "url", so it loads nothing either
- the CSS moves the page only inside @media (prefers-reduced-motion: no-preference): an animation, a
  transition or scroll-behavior, also with a vendor prefix such as -webkit-, stands in that query, or in a
  @keyframes. A prefixed at-rule, such as @-webkit-keyframes, is not an at-rule the CSS may hold
- a link (a href) goes to a file in docs/, to an id on the page, or into the repo on GitHub: the repo itself, a
  file or a directory on main that exists in this checkout, a pull request, an issue, or the latest release.
  Nothing links out of the repo to another site. A fragment on a link to the page, "#..." or "index.html#...", is
  an id on the page, and the ids on the page stand once each. A link to a logo has no fragment. A link into the
  repo may end in a fragment of the form of an id, and whether GitHub shows that id is not checked
- docs/ holds exactly the page, .nojekyll, the two logos and the figure, and each logo is byte for byte its copy
  in assets/
- the page has one h1, its headings do not skip a level, html has lang="en" and every image has alt text
- the colors are a palette of custom properties, one for light and one for dark, and each pair of text and
  background in it has a contrast ratio of at least 4.5 (WCAG 2, level AA). No other hex color is written.
- every command on the page, a line of a <pre><code> block, is a line of a code block marked sh in README.md
- each step of how Ratchet works, an item of the one <ol class="flow">, links to where the repo shows it
- the list of the principles, the one <ol id="principles">, holds the titles of the principles in ratchet.json, in
  order, as items that hold only text. The test reads the list itself, and does not ask generate.py.

Three parts of the page are written by generate.py, which checks them: the line that fetches Ratchet, which names
the newest version with a date in CHANGELOG.md, as the command in README.md does; the line that counts the rules
of the core, from ratchet.json; and the items of the list of the principles, from ratchet.json. So a release that
moves the README, a rule that changes kind, and a principle that is added, removed, moved or renamed each move the
page when generate.py is run, and generate.py --check fails until it is. The tests of all three are here too, and
they read each line as generate.py does, after the spaces that indent it.

What the test does not claim: that a browser shows the page or the figure as intended, that the figure's labels fit
where they are drawn or that each lies on the background it is checked against, that a named color is legible (it
reads hex colors only), that the border of a box stands out from the background (--edge is not checked: a box says
nothing that its text and its place in the list do not), or that the text is true. The text is taken
from README.md and the files the page links to, and read by the maintainer. That
Pages is turned on is a setting of the repository. Each case is the page with one change, so the cases follow the
page when it changes. Standard library only.
"""

import html.parser
import json
import os
import re
import shutil
import sys
import unittest
import xml.etree.ElementTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import generate  # noqa: E402
import registry  # noqa: E402
from test_checks import ROOT, RepoCopy, first_entry, run  # noqa: E402

DOCS = "docs"
PAGE = "index.html"
REPO = "https://github.com/fabian-von-tiedemann/ratchet"
FETCH = "git clone --branch v%s https://github.com/fabian-von-tiedemann/ratchet .ratchet"
# Every file in docs/. A logo is a copy of the file of the same name in assets/.
FILES = (".nojekyll", "index.html", "ratchet-dark.svg", "ratchet-light.svg", "ratchet-notch.svg")
LOGOS = ("ratchet-dark.svg", "ratchet-light.svg")
# The one figure, which one <img> on the page loads, and every element it may hold, with the attributes it may have.
# Each stands directly in the <svg>. There is no id, no href, no style attribute and no attribute of a color: the
# colors are in the one <style>. A value is numbers and words, so it calls no function and names no file.
FIGURE = "ratchet-notch.svg"
SVG = "http://www.w3.org/2000/svg"
FIGURE_ELEMENTS = {
    "svg": {"viewBox", "width", "height", "role", "aria-label"}, "style": set(),
    "rect": {"class", "x", "y", "width", "height", "rx"}, "path": {"class", "d"}, "circle": {"class", "cx", "cy", "r"},
    "text": {"class", "x", "y", "text-anchor"},
}
FIGURE_VALUE = re.compile(r"[A-Za-z0-9 .,-]+\Z")
# What the figure may not hold anywhere, since each is a way to bring in what the XML parser would not show as an element.
FIGURE_MARKS = (("<!", "a doctype, a comment or a CDATA section"), ("<?", "a processing instruction"),
                ("&", "a character reference or an entity"))
VOID = {"meta", "link", "img", "source", "br"}
GLOBAL = {"id", "class"}
# Every element the page may hold, with the attributes it may have beside id and class.
ELEMENTS = {
    "html": {"lang"}, "head": set(), "meta": {"charset", "name", "content"}, "title": set(), "link": {"rel", "href", "type"},
    "style": set(), "body": set(), "header": set(), "nav": set(), "main": set(), "section": set(), "footer": set(),
    "h1": set(), "h2": set(), "h3": set(), "p": set(), "ul": set(), "ol": set(), "li": set(), "a": {"href"},
    "strong": set(), "em": set(), "code": set(), "pre": set(), "br": set(), "span": set(),
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
    r"(?:/(?P<kind>blob|tree)/main/(?P<path>%s)|/(?:pull|issues)/[1-9][0-9]*|/releases/latest)?(?:#[a-z0-9]+(?:-[a-z0-9]+)*)?\Z"
    % REPO_PATH.pattern
)
# Characters the page may not hold: controls but the newline, and the ones that reorder or hide text.
HIDDEN = re.compile("[\x00-\x09\x0b-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]")
CSS_FUNCTION = re.compile(r"([A-Za-z_-][A-Za-z0-9_-]*)\(")
CSS_AT = re.compile(r"@([A-Za-z-]+)")
HEX = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
PALETTE = re.compile(r"--([a-z]+(?:-[a-z]+)*):\s*(#[0-9a-f]{6});")
ROOT_BLOCK = re.compile(r":root\s*\{([^{}]*)\}")
DARK = "@media (prefers-color-scheme: dark)"
# The only query in which the CSS may move the page: a visitor who asked for less motion sees none.
REDUCED = "@media (prefers-reduced-motion: no-preference)"
AT_RULES = {"media", "keyframes"}
# A property that moves the page, an animation, a transition or smooth scrolling, with or without a vendor prefix such as -webkit-, -moz-, -o- or -ms-: any one word
# between dashes before the name counts as one. A prefixed at-rule, such as @-webkit-keyframes, is not in AT_RULES.
MOTION = re.compile(r"(?:-[a-z]+-)?(?:animation(?:-[a-z]+)*|transition(?:-[a-z]+)*|scroll-behavior)\Z")
# Pairs of text and background in the palette, each to have a contrast ratio of at least 4.5. The button is the
# background on the text color, and on the accent when the pointer is over it: the pairs of fg and bg, and of accent
# and bg, turned around, with the same ratio.
PAIRS = (("fg", "bg"), ("muted", "bg"), ("link", "bg"), ("fg", "code-bg"), ("code-fg", "code-bg"), ("fg", "box"), ("muted", "box"),
         ("link", "box"), ("accent", "bg"), ("accent", "box"))
# The pairs in the figure: its labels on its own background and on the body of the staircase.
FIGURE_PAIRS = (("fg", "box"), ("fg", "code-bg"), ("muted", "box"), ("accent", "box"))
# The list whose items the test reads one by one: the steps of how Ratchet works.
ITEM_LISTS = {"ol": "flow"}
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
        # The classes of each open element, beside self.stack. An item of a list in ITEM_LISTS, a <li> whose list has
        # that class, records the links in it with their text. Each capture is [depth, field, href, parts], and ends
        # when its element is closed.
        self.classes, self.items, self.captures = [], [], []
        self.item, self.item_at = None, None
        # Each list on the page, as (its tag, the classes of its class attribute), in order.
        self.lists = []
        self.head_titles = 0

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
        table = ELEMENTS
        if tag not in table:
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
            if name not in GLOBAL and name not in table.get(tag, set()):
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
        if tag == "title":
            if self.stack[-1:] == ["head"]:
                self.head_titles += 1
            else:
                self.problems.append("%s: a <title> stands in <head>, and nowhere else" % self.where())
        if tag == "source" and self.stack[-1:] != ["picture"]:
            self.problems.append("%s: a <source> stands in a <picture>" % self.where())
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append((self.where(), int(tag[1])))
        if tag == "code" and self.stack[-1:] == ["pre"]:
            self.text_in = []
        classes = (values.get("class") or "").split()
        if tag in ITEM_LISTS:
            self.lists.append((tag, classes))
        if tag == "li" and self.stack and ITEM_LISTS.get(self.stack[-1]) in self.classes[-1]:
            self.item = {"list": ITEM_LISTS[self.stack[-1]], "where": self.where(), "links": []}
            self.items.append(self.item)
            self.item_at = len(self.stack)
        elif self.item is not None and tag not in VOID:
            if tag == "a":
                self.captures.append([len(self.stack), "links", values.get("href"), []])
        if tag not in VOID:
            self.stack.append(tag)
            self.classes.append(classes)

    def handle_endtag(self, tag):
        if tag in VOID:
            self.problems.append("%s: </%s> closes a void element" % (self.where(), tag))
            return
        if not self.stack or self.stack[-1] != tag:
            self.problems.append("%s: </%s> does not close the element that is open, %s"
                                 % (self.where(), tag, "<%s>" % self.stack[-1] if self.stack else "none"))
            if tag in self.stack:
                at = self.stack.index(tag)
                del self.stack[at:], self.classes[at:]
                self.close_items()
            return
        self.stack.pop()
        self.classes.pop()
        self.close_items()
        if tag == "code" and self.text_in is not None:
            self.commands += "".join(self.text_in).split("\n")
            self.text_in = None

    def close_items(self):
        """End the captures and the item whose elements are no longer open."""
        while self.captures and self.captures[-1][0] >= len(self.stack):
            _, field, href, parts = self.captures.pop()
            text = " ".join("".join(parts).split())
            self.item[field].append((href, text))
        if self.item is not None and self.item_at >= len(self.stack):
            self.item, self.item_at = None, None

    def handle_data(self, data):
        if data.strip():
            self.started = True
        for capture in self.captures:
            capture[3].append(data)
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


def css_problems(css, pairs=PAIRS):
    problems = []
    if "\\" in css:
        problems.append("the CSS holds a backslash, which could spell a word the check does not see")
    if "url" in css.lower():
        problems.append('the CSS holds "url", and loads nothing')
    for name in sorted(set(CSS_FUNCTION.findall(css)) - {"var"}):
        problems.append("the CSS calls %s(), and the only function it may call is var()" % name)
    for name in sorted(set(CSS_AT.findall(css)) - AT_RULES):
        problems.append("the CSS holds @%s, and the only at-rules it may hold are @media and @keyframes" % name)
    problems += motion_problems(css)
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
        for text, background in pairs:
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


def motion_problems(css):
    """Why the CSS moves the page for a visitor who asked for less motion: an animation outside the query REDUCED.

    The CSS is read as blocks, each opened by what stands before its "{". A declaration of animation, of a property
    animation-*, of transition, of a property transition-*, or of scroll-behavior, with or without a vendor prefix,
    stands in a block inside REDUCED, written so, or inside a @keyframes, which only says how an animation moves. Comments are removed
    first, so a brace in a comment is not read, but a brace in a string is read as a brace.
    """
    problems, blocks, start = [], [], 0
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for at, char in enumerate(css):
        if char not in "{};":
            continue
        text, start = " ".join(css[start:at].split()), at + 1
        if char == "{":
            blocks.append(text)
            continue
        name = text.partition(":")[0].strip().lower()
        if blocks and ":" in text and MOTION.match(name) and not any(block == REDUCED or block.startswith("@keyframes ") for block in blocks):
            problems.append("the CSS declares %s in %s, and so moves the page outside %s" % (name, " ".join(blocks), REDUCED))
        if char == "}":
            if not blocks:
                problems.append("the CSS has a brace that is not matched: a } with no block open")
                continue
            blocks.pop()
    if blocks:
        problems.append("the CSS has a brace that is not matched: %s is never closed" % blocks[-1])
    return problems


def palettes(css):
    """The light and the dark palette of a CSS that css_problems passed, each as a dict of name and color."""
    return [dict(PALETTE.findall(block)) for block in ROOT_BLOCK.findall(css)]


def figure_problems(root, page_css):
    """Everything wrong with the figure in the checkout at root, as a list of messages that name the file.

    page_css is the CSS of the page, whose palettes the figure's colors are taken from.
    """
    name = "%s/%s" % (DOCS, FIGURE)
    path = os.path.join(root, DOCS, FIGURE)
    if os.path.islink(path) or not os.path.isfile(path):
        return ["%s: there is no such file" % name]
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        return ["%s: not valid UTF-8 at byte %d" % (name, error.start)]
    problems = []
    for number, line in enumerate(text.split("\n"), 1):
        for match in HIDDEN.finditer(line):
            problems.append("%s:%d: holds U+%04X, a control or a character that reorders or hides text" % (name, number, ord(match.group())))
    for mark, what in FIGURE_MARKS:
        if mark in text:
            problems.append("%s: holds %r, %s, which the figure does not hold" % (name, mark, what))
    if problems:
        # A doctype is never given to the parser, so it expands no entity.
        return problems
    try:
        tree = xml.etree.ElementTree.fromstring(text)
    except xml.etree.ElementTree.ParseError as error:
        return ["%s: not well-formed XML: %s" % (name, error)]
    styles = []
    for element in tree.iter():
        space, _, tag = element.tag.rpartition("}")
        if space != "{" + SVG or tag not in FIGURE_ELEMENTS or (tag == "svg") != (element is tree):
            problems.append("%s: <%s> is not an element the figure may hold" % (name, element.tag))
            continue
        for attribute, value in element.attrib.items():
            if attribute not in FIGURE_ELEMENTS[tag]:
                problems.append("%s: <%s> may not have the attribute %s" % (name, tag, attribute))
            elif not FIGURE_VALUE.match(value):
                problems.append("%s: <%s> has %s=%r, and a value in the figure is numbers and words" % (name, tag, attribute, value))
        if element is not tree and len(element):
            problems.append("%s: <%s> holds an element, and each element stands directly in the <svg>" % (name, tag))
        words = [element.tail] + ([] if tag in ("style", "text") else [element.text])
        if any(each and each.strip() for each in words):
            problems.append("%s: text in or after <%s>, and the figure holds text only in <text> and <style>" % (name, tag))
        if tag == "style":
            styles.append(element.text or "")
    if tree.get("role") != "img" or not tree.get("aria-label"):
        problems.append('%s: the <svg> has role="img" and an aria-label that names it' % name)
    if len(styles) != 1:
        return problems + ["%s: holds <style> %d times, and must hold it once" % (name, len(styles))]
    found = css_problems(styles[0], FIGURE_PAIRS)
    if not found and len(palettes(page_css)) == 2:
        for scheme, own, pages in zip(("light", "dark"), palettes(styles[0]), palettes(page_css)):
            for key, color in sorted(own.items()):
                if pages.get(key) != color:
                    found.append("in the %s palette, --%s is %s, and the page's is %s: the figure has the colors of the page"
                                 % (scheme, key, color, pages.get(key, "not there")))
    return problems + ["%s: %s" % (name, problem) for problem in found]


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
    for tag in ("html", "head", "body", "main", "h1", "style"):
        if reader.counts.get(tag, 0) != 1:
            found.append("%s: holds <%s> %d times, and must hold it once" % (name, tag, reader.counts.get(tag, 0)))
    if reader.head_titles != 1:
        found.append("%s: holds <title> %d times in <head>, and must hold it once" % (name, reader.head_titles))
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
    figures = ["<%s>" % tag for _, tag, value in reader.loads if value == FIGURE]
    if figures != ["<img>"]:
        found.append("%s: the figure %s is loaded by %s, and one <img> loads it, once" % (name, FIGURE, ", ".join(figures) or "nothing"))
    duplicates = sorted(set(each for each in reader.ids if reader.ids.count(each) > 1))
    if duplicates:
        found.append("%s: ids that stand more than once: %s" % (name, ", ".join(duplicates)))
    # The page is the one page in docs/ (FILES), so its ids, as html.parser read them, are the ids a fragment may name.
    for where, value in reader.links:
        problem = link_problem(root, value, {PAGE: reader.ids})
        if problem:
            found.append("%s: %s: the link %r %s" % (name, where, value, problem))
    for item in reader.items:
        if item["list"] == "flow" and not any(into_repo(href) for href, _ in item["links"]):
            found.append("%s: %s: a step that links nowhere in this repo. Each step links to where the repo shows it"
                         % (name, item["where"]))
    found += ["%s: %s" % (name, problem) for problem in css_problems("".join(reader.styles))]
    found += figure_problems(root, "".join(reader.styles))
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
    """Why a link on the page is not allowed, or None. ids maps each page in docs/ to the ids on it.

    A link into the repo may end in a fragment of the form of an id, which is not checked against GitHub. A link
    to a page in docs/, or to "#..." on this page, has a fragment only if it is an id on that page. Nothing links
    out of the repo.
    """
    if value.startswith(REPO):
        match = REPO_LINK.match(value[len(REPO):])
        if not match:
            return ("goes into the repo, but not to the repo, a file or directory on main, a pull request, an issue or the "
                    "latest release")
        if match.group("kind"):
            target = os.path.join(root, *match.group("path").split("/"))
            if match.group("kind") == "blob" and not os.path.isfile(target):
                return "names a file that is not in this checkout"
            if match.group("kind") == "tree" and not os.path.isdir(target):
                return "names a directory that is not in this checkout"
        return None
    target, mark, fragment = value.partition("#")
    nowhere = "leads neither to a file in %s/, nor to an id on the page, nor into the repo on GitHub" % DOCS
    if target and not (FILE.match(target) and target in FILES and target != ".nojekyll"):
        return nowhere
    if not mark:
        return None if target else nowhere
    page = target or PAGE
    if page not in ids:
        return "has a fragment, and only a link to a page in %s/ may have a fragment" % DOCS
    if not FRAGMENT.match(mark + fragment) or fragment not in ids[page]:
        return "names #%s, which is not an id on %s" % (fragment, page)
    return None


def into_repo(href):
    """Whether a link leads into this repo on GitHub, as a step must: not out of it, and not to this page."""
    return isinstance(href, str) and (href == REPO or href.startswith(REPO + "/"))


def lines_that_hold(text, marker):
    """The lines of the page that hold marker, without the spaces that indent them, as generate.py reads them."""
    return [line.lstrip(" ") for line in text.split("\n") if marker in line]


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

    def assert_fails(self, *message):
        """One problem holds every part of the message."""
        problems = page_problems(self.copy)
        self.assertTrue(any(all(part in problem for part in message) for problem in problems), "%r not in %r" % (message, problems))

    def test_the_page_as_it_stands_passes(self):
        self.assertEqual(page_problems(ROOT), [])
        self.assertEqual(page_problems(self.copy), [])

    def test_the_page_names_what_it_must(self):
        text = self.page()
        released = generate.changelog_context(self.copy)[1]
        for words in (FETCH % released, "python3 .ratchet/checks/init.py --check", "python3 .ratchet/checks/init.py</code>",
                      REPO + "/releases/latest", REPO + "/blob/main/LICENSE", 'href="%s"' % REPO,
                      "<h2 id=\"start-here\">Start here</h2>", "prefers-color-scheme: dark", '<h2 id="why">Why it exists</h2>',
                      '<h2 id="how-it-works">How it works</h2>', '<h2 id="the-principles">The principles</h2>',
                      REPO + "/blob/main/README.md", REPO + "/blob/main/STARTING.md",
                      '<a class="button" href="#start-here">Start here</a>'):
            self.assertIn(words, text)

    def test_the_page_is_short(self):
        # One page a newcomer reads in a minute: under 450 words outside the CSS, and five headings.
        text = self.page()
        body = re.sub(r"<[^>]+>", " ", text[text.index("</style>"):])
        self.assertLess(len(body.split()), 450)
        reader = PageReader()
        reader.feed(text)
        self.assertEqual([level for _, level in reader.headings], [1, 2, 2, 2, 2])

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
                       '<svg><image href="https://example.invalid/x.png"></image></svg>', '<audio src="x.mp3"></audio>',
                       # The page holds no inline SVG, so an <svg> fails whole, and so does an element of SVG outside one.
                       '<svg viewBox="0 0 1 1" role="img" aria-labelledby="t"><title id="t">x</title></svg>',
                       '<svg onload="alert(1)"></svg>', '<path d="M0 0 L1 1"></path>', '<use href="#why"></use>',
                       "<foreignObject><p>x</p></foreignObject>", '<animate attributeName="x"></animate>'):
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
                       "https://fabian-von-tiedemann.github.io/ratchet/", "//example.invalid/",
                       # A source in sources.json is credited in RATCHET.md, which the page links to, and not on the page.
                       "https://github.com/mattpocock/skills", "https://github.com/cursor/plugins/tree/HEAD/pstack"):
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

    def test_a_link_to_a_pull_request_or_an_issue_passes_and_one_of_another_form_fails(self):
        for target in ("/issues/49", "/pull/42", "/releases/latest"):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="%s/blob/main/LICENSE"' % REPO, 'href="%s%s"' % (REPO, target))
                self.assertEqual(page_problems(self.copy), [])
        for target in ("/issues/0", "/issues/49/../../x", "/issues", "/issues/new", "/pull/0", "/pulls"):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="%s/blob/main/LICENSE"' % REPO, 'href="%s%s"' % (REPO, target))
                self.assert_fails("goes into the repo, but not")

    def test_a_relative_link_or_a_fragment_that_leads_nowhere_fails(self):
        for target in ("missing.html", "../README.md", "/index.html", "#no-such-id", ".nojekyll"):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="#start-here"', 'href="%s"' % target)
                self.assert_fails("the link")

    def test_a_relative_link_to_the_page_passes(self):
        self.change('href="#start-here"', 'href="index.html#start-here"')
        self.assertEqual(page_problems(self.copy), [])

    def test_a_fragment_that_is_not_an_id_on_its_page_fails(self):
        # The first is a typo for the id start-here, in a link to the page by its name.
        for target in ("index.html#start-hree", "index.html#Start-here", "index.html#", "#missing", "#start-hree", "#"):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="#start-here"', 'href="%s"' % target)
                self.assert_fails("the link %r" % target, "is not an id on")

    def test_a_fragment_on_a_link_to_a_file_that_is_not_a_page_fails(self):
        self.change('href="#start-here"', 'href="ratchet-light.svg#logo"')
        self.assert_fails("the link 'ratchet-light.svg#logo'", "only a link to a page in docs/ may have a fragment")

    def test_an_id_twice_on_the_page_fails(self):
        # The second start-here is one a link names, so the link would lead to either.
        self.change('<h2 id="why">', '<h2 id="start-here">')
        self.assert_fails("ids that stand more than once: start-here")

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
                                  ("<main>", "<main><title>x</title>", "a <title> stands in <head>, and nowhere else"),
                                  ("<h1>Ratchet</h1>", "<h1>Ratchet<title>x</title></h1>", "a <title> stands in <head>, and nowhere else")):
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
        # Each key differs between the palettes, so the first match on the page is the one in the palette named.
        for scheme, palette, key, faint in (("light", light, "muted", "#aaaaaa"), ("dark", dark, "link", "#333366"),
                                            ("light", light, "bg", "#777777"), ("light", light, "box", "#555555"),
                                            ("dark", dark, "box", "#9a9a9a"), ("light", light, "accent", "#ffbb66"),
                                            ("dark", dark, "accent", "#3a2a10"), ("light", light, "code-bg", "#555555"),
                                            ("dark", dark, "code-fg", "#3a3a3a")):
            with self.subTest(scheme=scheme, key=key):
                self.setUp()
                self.change("--%s: %s;" % (key, palette[key]), "--%s: %s;" % (key, faint))
                self.assert_fails("in the %s palette" % scheme, "--%s" % key)
        self.setUp()
        self.change("</style>", "p { color: #777; }\n</style>")
        self.assert_fails("a hex color outside the two palettes")
        self.setUp()
        self.change(DARK, "@media (prefers-color-scheme: light)")
        self.assert_fails("the CSS has two :root blocks of colors")

    def test_a_second_title_in_the_head_fails(self):
        self.change("</title>\n", "</title>\n<title>x</title>\n")
        self.assert_fails("holds <title> 2 times in <head>, and must hold it once")

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


class Figure(RepoCopy, unittest.TestCase):
    """The one figure, docs/ratchet-notch.svg, passes as it stands, and each change below fails with its message."""

    def setUp(self):
        super().setUp()
        self.path = os.path.join(self.copy, DOCS, FIGURE)
        with open(self.path, encoding="utf-8", newline="") as handle:
            self.figure = handle.read()

    def write(self, old, new, name=FIGURE):
        """The file as it stands in the repo, with one change."""
        path = os.path.join(self.copy, DOCS, name)
        with open(os.path.join(ROOT, DOCS, name), encoding="utf-8", newline="") as handle:
            text = handle.read()
        self.assertIn(old, text, "the test expects %r in %s" % (old, name))
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text.replace(old, new, 1))

    def assert_fails(self, *message):
        problems = page_problems(self.copy)
        self.assertTrue(any(all(part in problem for part in message) for problem in problems), "%r not in %r" % (message, problems))

    def test_the_figure_as_it_stands_passes_and_is_loaded_once(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8") as handle:
            page = handle.read()
        self.assertEqual(page.count(FIGURE), 1)
        self.assertEqual(page_problems(self.copy), [])
        tree = xml.etree.ElementTree.fromstring(self.figure)
        labels = [element.text for element in tree.iter("{%s}text" % SVG)]
        self.assertEqual(labels, ["failure \u2192 check"] * 3 + ["one notch tighter", "can\u2019t slip back"])

    def test_a_figure_that_no_image_loads_or_that_is_loaded_twice_fails(self):
        image = '<img class="notch" src="ratchet-notch.svg"'
        for old, new, by in ((image, '<img class="notch" src="ratchet-light.svg"', "nothing"),
                             ("</main>", image + ' alt="x">\n</main>', "<img>, <img>"),
                             ('<link rel="icon" href="ratchet-light.svg"', '<link rel="icon" href="ratchet-notch.svg"', "<link>, <img>"),
                             (image, '<picture><source srcset="ratchet-notch.svg"></picture>\n<img src="ratchet-light.svg"', "<source>")):
            with self.subTest(new=new):
                self.write(old, new, PAGE)
                self.assert_fails("the figure ratchet-notch.svg is loaded by %s, and one <img> loads it, once" % by)

    def test_a_figure_without_alt_text_fails(self):
        self.write('height="256" alt="A staircase', 'height="256" alt=" " title="A staircase', PAGE)
        self.assert_fails("an <img> without alt text")

    def test_no_figure_or_a_link_in_its_place_fails(self):
        os.remove(self.path)
        self.assert_fails("docs/ must hold exactly")
        self.assert_fails("docs/ratchet-notch.svg: there is no such file")
        os.symlink("ratchet-light.svg", self.path)
        self.assert_fails("docs/ratchet-notch.svg: there is no such file")

    def test_a_figure_that_is_not_utf8_or_holds_a_hidden_character_fails(self):
        with open(self.path, "ab") as handle:
            handle.write(b"\xff\n")
        self.assert_fails("docs/ratchet-notch.svg: not valid UTF-8 at byte")
        for character in ("\r", "\t", "\u202e", "\u200b", "\ufeff"):
            with self.subTest(character=repr(character)):
                self.write(">one notch tighter<", ">one notch%stighter<" % character)
                self.assert_fails("docs/ratchet-notch.svg:", "holds U+%04X" % ord(character))

    def test_a_doctype_a_comment_a_processing_instruction_or_a_reference_fails(self):
        entity = '<!DOCTYPE svg [<!ENTITY x "failure">]>\n<svg '
        for old, new, mark in (("<svg ", entity, "'<!'"), ("<svg ", '<?xml version="1.0"?>\n<svg ', "'<?'"),
                               ("<svg ", '<?xml-stylesheet href="https://example.invalid/x.css"?>\n<svg ', "'<?'"),
                               ("</style>", "</style>\n<!-- x -->", "'<!'"), (">one notch tighter<", "><![CDATA[one notch]]><", "'<!'"),
                               (">one notch tighter<", ">one notch &#116;ighter<", "'&'"), (">one notch tighter<", ">one &amp; one<", "'&'")):
            with self.subTest(new=new):
                self.write(old, new)
                self.assert_fails("docs/ratchet-notch.svg: holds %s" % mark, "which the figure does not hold")

    def test_a_figure_that_is_not_well_formed_fails(self):
        for old, new in (("</svg>", ""), ('rx="8"/>', 'rx="8">'), ('rx="8"/>', 'rx="8" rx="8"/>'), ("<svg ", "x<svg ")):
            with self.subTest(new=new):
                self.write(old, new)
                self.assert_fails("docs/ratchet-notch.svg: not well-formed XML")

    def test_an_element_that_is_not_on_the_list_fails(self):
        for element in ("<script>alert(1)</script>", '<script href="https://example.invalid/t.js"/>', '<use href="#x"/>',
                        '<image href="https://example.invalid/x.png"/>', '<a href="https://example.invalid/"><text>x</text></a>',
                        "<foreignObject><p>x</p></foreignObject>", '<animate attributeName="x"/>', '<set attributeName="x"/>',
                        "<g><circle/></g>", "<title>x</title>", "<svg/>", '<svg xmlns="http://www.w3.org/2000/svg"/>',
                        '<circle xmlns="http://www.w3.org/1999/xhtml"/>', '<x:script xmlns:x="http://www.w3.org/1999/xhtml">1</x:script>'):
            with self.subTest(element=element):
                self.write("</style>", "</style>\n" + element)
                self.assert_fails("docs/ratchet-notch.svg:", "is not an element the figure may hold")
        self.write(' xmlns="http://www.w3.org/2000/svg"', "")
        self.assert_fails("docs/ratchet-notch.svg: <svg> is not an element the figure may hold")

    def test_an_attribute_that_is_not_on_the_list_fails(self):
        for attribute in ('onload="alert(1)"', 'onclick="x"', 'style="fill: red"', 'fill="#ff0000"', 'stroke="red"', 'id="x"',
                          'href="https://example.invalid/"', 'filter="url(#f)"', 'transform="rotate(45)"',
                          'xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="https://example.invalid/"'):
            with self.subTest(attribute=attribute):
                self.write('<circle class="ball"', '<circle %s class="ball"' % attribute)
                self.assert_fails("docs/ratchet-notch.svg: <circle> may not have the attribute")
        self.write('role="img"', 'role="img" onload="alert(1)"')
        self.assert_fails("docs/ratchet-notch.svg: <svg> may not have the attribute onload")

    def test_a_value_that_is_not_numbers_and_words_fails(self):
        for old, new in (('class="ball"', 'class="url(#x)"'), ('class="ball"', 'class=""'), ('r="13.5"', 'r="calc(1px)"'),
                         ('d="M200 62.5 H218 V36 Z"', 'd="M200 62.5; H218"'), ('text-anchor="end">one', 'text-anchor="javascript:x">one'),
                         ('aria-label="A staircase', 'aria-label="https://example.invalid/ A staircase')):
            with self.subTest(new=new):
                self.write(old, new)
                self.assert_fails("docs/ratchet-notch.svg:", "and a value in the figure is numbers and words")

    def test_an_element_or_text_out_of_place_fails(self):
        self.write(">one notch tighter<", '>one <circle class="ball" cx="1" cy="1" r="1"/><')
        self.assert_fails("docs/ratchet-notch.svg: <text> holds an element, and each element stands directly in the <svg>")
        for old, new in (("</style>", "</style>\nfailure"), ('rx="8"/>', 'rx="8">failure</rect>'), ("</svg>", "failure</svg>")):
            with self.subTest(new=new):
                self.write(old, new)
                self.assert_fails("docs/ratchet-notch.svg: text in or after", "the figure holds text only in <text> and <style>")

    def test_a_figure_without_its_role_its_name_or_its_one_style_fails(self):
        for old, new in (('role="img" ', ""), ('role="img"', 'role="presentation"')):
            with self.subTest(new=new):
                self.write(old, new)
                self.assert_fails('docs/ratchet-notch.svg: the <svg> has role="img" and an aria-label that names it')
        self.write(self.figure[self.figure.index(" aria-label="):self.figure.index(">")], "")
        self.assert_fails('docs/ratchet-notch.svg: the <svg> has role="img" and an aria-label that names it')
        self.write("</style>", "</style>\n<style>text { fill: red; }</style>")
        self.assert_fails("docs/ratchet-notch.svg: holds <style> 2 times, and must hold it once")
        self.write(self.figure[self.figure.index("<style>"):self.figure.index("</style>") + len("</style>")], "")
        self.assert_fails("docs/ratchet-notch.svg: holds <style> 0 times, and must hold it once")

    def test_css_in_the_figure_that_the_page_may_not_hold_fails(self):
        for css, message in (('@import "https://example.invalid/x.css";', "holds @import"),
                             ("@font-face { font-family: x; }", "holds @font-face"),
                             (".ball { fill: url(#g); }", 'holds "url"'), (".ball { fill: \\75rl(x); }", "holds a backslash"),
                             (".ball { r: calc(1px); }", "calls calc()"), (".ball { fill: #ff0000; }", "a hex color outside the two palettes"),
                             (".ball { transition: fill 1s; }", "moves the page outside"), (".ball {", "a brace that is not matched")):
            with self.subTest(css=css):
                self.write("</style>", css + "\n</style>")
                self.assert_fails("docs/ratchet-notch.svg: the CSS ", message)
        self.write(DARK, "@media (prefers-color-scheme: light)")
        self.assert_fails("docs/ratchet-notch.svg: the CSS has two :root blocks of colors")

    def test_a_color_that_is_faint_or_not_the_pages_fails(self):
        light, dark = palettes(self.figure)
        for scheme, palette, key, faint in (("light", light, "muted", "#aaaaaa"), ("light", light, "accent", "#ffbb66"),
                                            ("dark", dark, "fg", "#3a3a3a"), ("dark", dark, "box", "#9a9a9a"),
                                            ("light", light, "code-bg", "#555555")):
            with self.subTest(scheme=scheme, key=key):
                self.write("--%s: %s;" % (key, palette[key]), "--%s: %s;" % (key, faint))
                self.assert_fails("docs/ratchet-notch.svg: in the %s palette" % scheme, "--%s" % key, "under 4.5")
        # A color with contrast enough that is not the page's, the border, which is in no pair, and a name the page does not have.
        for old, new, message in (("--fg: %s;" % light["fg"], "--fg: #000000;", "in the light palette, --fg is #000000, and the page's is %s" % light["fg"]),
                                  ("--edge: %s;" % dark["edge"], "--edge: #444444;", "in the dark palette, --edge is #444444"),
                                  ("--edge: %s;" % light["edge"], "--edge: %s;\n  --line: #000000;" % light["edge"], "the light and the dark palette name different colors")):
            with self.subTest(new=new):
                self.write(old, new)
                self.assert_fails("docs/ratchet-notch.svg: " + message)
        self.write("--edge: %s;" % light["edge"], "--edge: %s;\n  --line: #000000;" % light["edge"])
        with open(self.path, encoding="utf-8", newline="") as handle:
            text = handle.read()
        with open(self.path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text.replace("--edge: %s;" % dark["edge"], "--edge: %s;\n    --line: #ffffff;" % dark["edge"]))
        self.assert_fails("docs/ratchet-notch.svg: in the light palette, --line is #000000, and the page's is not there")

    def test_a_color_of_the_page_that_moves_fails_until_the_figure_follows(self):
        self.write("--accent: #b23a04;", "--accent: #a03000;", PAGE)
        self.assert_fails("docs/ratchet-notch.svg: in the light palette, --accent is #b23a04, and the page's is #a03000")


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
        self.assertEqual(lines_that_hold(self.page(), "git clone"), [line])
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

    def test_an_indented_fetch_line_passes_as_generate_reads_it(self):
        # generate.py reads the line after the spaces that indent it, so the test reads it the same way.
        version, fetched = first_entry(self.copy)
        line = "<pre><code>%s</code></pre>" % (FETCH % fetched)
        self.write_page(self.page().replace(line, "  " + line, 1))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        self.assertEqual(lines_that_hold(self.page(), "git clone"), [line])
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


# The line on the page that counts the rules of the core, as the test expects it. It is spelled out here and counted
# from ratchet.json below, not taken from generate.py, so the test does not compute it the way the generator does.
COUNT_LINE = ('<p id="count" class="count"><strong>Ratchet today:</strong> the core has %d rules. %d name a check and '
              '%d are text only.</p>')


def count_line(root):
    with open(os.path.join(root, "ratchet.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    core = [rule for rule in data["rules"] if rule["status"] == "core"]
    enforced = [rule for rule in core if rule["enforcement"] == "enforced"]
    return COUNT_LINE % (len(core), len(enforced), len(core) - len(enforced))


def rewrite_ratchet(root, change):
    """Change ratchet.json in a copy of the repo, as data, and read it back as every check reads it."""
    path = os.path.join(root, "ratchet.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    change(data)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    registry.load(path)


class PageCount(RepoCopy, unittest.TestCase):
    """generate.py writes the line on the page that counts the rules of the core, and --check fails when it is stale."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def write_page(self, text):
        with open(os.path.join(self.copy, DOCS, PAGE), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def test_the_page_gives_the_count_of_ratchet_json(self):
        self.assertEqual(lines_that_hold(self.page(), 'id="count"'), [count_line(self.copy)])
        self.assertIn("the core has 19 rules. 13 name a check and 6 are text only.", count_line(self.copy))

    def test_a_rule_that_gets_a_check_fails_until_generate_moves_the_page(self):
        before = self.page()
        old = count_line(self.copy)

        def give_a_check(data):
            # A text-only rule of the core that this repo's register does not copy, so that only the count moves.
            with open(os.path.join(self.copy, "register.json"), encoding="utf-8") as handle:
                copied = set(item["key"] for item in json.load(handle)["adopted"])
            rule = next(rule for rule in data["rules"] if rule["status"] == "core" and rule["enforcement"] == "text-only"
                        and rule["key"] not in copied and rule["key"] not in data["start"])
            rule["enforcement"], rule["ratchet"] = "enforced", "Check: a check that the test made up"
        rewrite_ratchet(self.copy, give_a_check)
        new = count_line(self.copy)
        self.assertNotEqual(old, new)
        self.assertIn("14 name a check and 5 are text only.", new)
        self.assert_check_fails("docs/index.html: generated text is out of date or was edited by hand")
        code, output = run("generate.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("wrote docs/index.html", output)
        self.assertEqual(self.page(), before.replace(old, new))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        self.assertEqual(page_problems(self.copy), [])

    def test_a_number_edited_by_hand_fails(self):
        line = count_line(self.copy)
        self.write_page(self.page().replace(line, line.replace("13 name a check", "19 name a check"), 1))
        self.assert_check_fails("docs/index.html: generated text is out of date or was edited by hand")

    def test_an_indented_count_line_passes(self):
        line = count_line(self.copy)
        self.write_page(self.page().replace(line, "  " + line, 1))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def test_a_count_line_of_another_form_fails(self):
        line = count_line(self.copy)
        for new in ("", line + "\n" + line, line + " And more.", line.replace("<strong>", "<strong>about ", 1),
                    line.replace('<p id="count" class="count">', '<p class="count">\n<span id="count"></span>', 1),
                    line + '\n<p id="count">23 rules</p>',
                    line.replace("13 name a check", "thirteen name a check")):
            with self.subTest(new=new):
                self.setUp()
                self.write_page(self.page().replace(line, new, 1))
                code, output = run("generate.py", "--check", root=self.copy)
                self.assertEqual(code, 1, output)
                self.assertIn("docs/index.html: the count of rules must be one line", output)
                self.assertNotIn("Traceback", output)
                code, output = run("generate.py", root=self.copy, cwd=self.copy)
                self.assertEqual(code, 1, output)
                self.assertNotIn("wrote docs/index.html", output)


class PageSteps(RepoCopy, unittest.TestCase):
    """How Ratchet works is one ordered list whose every step links to where the repo shows it."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_fails(self, *message):
        Page.assert_fails(self, *message)

    def test_there_is_one_list_of_three_steps_that_each_link_into_the_repo(self):
        reader = PageReader()
        reader.feed(self.page())
        steps = [item for item in reader.items if item["list"] == "flow"]
        self.assertEqual(len([classes for tag, classes in reader.lists if tag == "ol" and "flow" in classes]), 1)
        self.assertEqual(len(steps), 3)
        self.assertTrue(all(any(into_repo(href) for href, _ in item["links"]) for item in steps))

    def test_the_list_is_counted_by_its_class_in_any_order(self):
        # The class attribute holds a list: "wide  flow" is the list of steps as much as "flow" is.
        self.change('<ol class="flow">', '<ol class="wide  flow">')
        reader = PageReader()
        reader.feed(self.page())
        self.assertEqual(len([classes for tag, classes in reader.lists if tag == "ol" and "flow" in classes]), 1)
        self.assertEqual(len([item for item in reader.items if item["list"] == "flow"]), 3)
        self.assertEqual(page_problems(self.copy), [])

    def test_a_step_without_a_link_fails(self):
        self.change('<a href="https://github.com/fabian-von-tiedemann/ratchet/blob/main/REGISTER.md">Ratchet\'s own register</a>',
                    "Ratchet's own register")
        self.assert_fails("a step that links nowhere in this repo")

    def test_a_step_whose_only_link_leads_to_the_page_fails(self):
        # A link to an id on the page is allowed, but it does not show where this repo does the step.
        self.change('<a href="https://github.com/fabian-von-tiedemann/ratchet/blob/main/REGISTER.md">Ratchet\'s own register</a>',
                    '<a href="#why">Why</a>')
        self.assert_fails("a step that links nowhere in this repo")
        self.assertEqual(len(page_problems(self.copy)), 1)


# The list of the principles: the one <ol> with this id, whose items are the titles of the principles, as text.
PRINCIPLES = "principles"
# Every void element of HTML. One has no end tag, so the reader counts none of them as opening or closing the list.
HTML_VOID = frozenset(("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"))


class ListReader(html.parser.HTMLParser):
    """Reads the list of the principles: each item of it, and what is wrong with its form."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lists, self.items, self.in_list, self.problems, self.text = 0, [], 0, [], None

    def handle_starttag(self, tag, attrs):
        if self.in_list:
            if tag in HTML_VOID:
                self.problems.append("line %d: the list of the principles holds a <%s>, a void element, and its items hold only"
                                     " text" % (self.getpos()[0], tag))
                return
            self.in_list += 1
            if tag == "li" and self.in_list == 2:
                self.text = []
            elif self.in_list == 2:
                self.problems.append("line %d: the list of the principles holds a <%s>, and holds only <li>" % (self.getpos()[0], tag))
            else:
                self.problems.append("line %d: an item of the list of the principles holds a <%s>, and holds only text"
                                     % (self.getpos()[0], tag))
        elif tag == "ol" and dict(attrs).get("id") == PRINCIPLES:
            self.lists, self.in_list = self.lists + 1, 1

    def handle_endtag(self, tag):
        if not self.in_list:
            return
        if tag in HTML_VOID:
            self.problems.append("line %d: the list of the principles holds a </%s>, which a browser reads as a void element,"
                                 " and its items hold only text" % (self.getpos()[0], tag))
            return
        self.in_list -= 1
        if tag == "li" and self.in_list == 1 and self.text is not None:
            self.items.append(" ".join("".join(self.text).split()))
            self.text = None

    def handle_startendtag(self, tag, attrs):
        # <br/> is one problem, not two: in the list, a void element is neither opened nor closed.
        self.handle_starttag(tag, attrs)
        if not (self.in_list and tag in HTML_VOID):
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.in_list == 1 and data.strip():
            self.problems.append("line %d: the list of the principles holds text outside an <li>, and holds only <li>"
                                 % self.getpos()[0])
        if self.text is not None:
            self.text.append(data)


def principle_problems(root):
    """Why the list of the principles on the page does not name the principles in ratchet.json, in order.

    The page holds one <ol id="principles">, of <li> only, and its items, which hold only text, are the titles, in
    order. So a principle that is added, removed, moved or renamed in ratchet.json fails until the list follows, and
    an item edited by hand fails as well. generate.py writes the items, and this reads them without asking it.
    """
    with open(os.path.join(root, DOCS, PAGE), encoding="utf-8") as handle:
        reader = ListReader()
        reader.feed(handle.read())
    if reader.lists != 1:
        return ['the page holds %d lists of the principles, an <ol id="%s">, and must hold one' % (reader.lists, PRINCIPLES)]
    if reader.problems:
        return reader.problems
    titles = [principle["title"] for principle in registry.load(os.path.join(root, "ratchet.json"))["principles"]]
    if reader.items != titles:
        return ["the list of the principles is %r, and the principles in ratchet.json, in order, are %r" % (reader.items, titles)]
    return []


class PagePrinciples(RepoCopy, unittest.TestCase):
    """The list of the principles names the principles in ratchet.json, one per item, in order, and generate.py writes it."""

    stale = "docs/index.html: generated text is out of date or was edited by hand"
    form = "docs/index.html: the list of the principles must be the line"

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_list_fails(self, *message):
        problems = principle_problems(self.copy)
        self.assertTrue(any(all(part in problem for part in message) for problem in problems), "%r not in %r" % (message, problems))

    def test_the_list_names_the_seven_principles_in_order(self):
        self.assertEqual(principle_problems(ROOT), [])
        self.assertEqual(principle_problems(self.copy), [])
        reader = ListReader()
        reader.feed(self.page())
        self.assertEqual(len(reader.items), 7)
        self.assertEqual(reader.items[0], "Keep one place")
        self.assertEqual(reader.items[-1], "Subtract first")

    def test_a_principle_renamed_in_ratchet_json_fails_until_generate_moves_the_page(self):
        before = self.page()
        self.edit("ratchet.json", '"title": "Subtract first"', '"title": "Subtract before you add"')
        self.assert_list_fails("the list of the principles is")
        self.assert_check_fails(self.stale)
        code, output = run("generate.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("wrote docs/index.html", output)
        self.assertEqual(self.page(), before.replace("<li>Subtract first</li>", "<li>Subtract before you add</li>"))
        self.assertEqual(principle_problems(self.copy), [])
        self.assertEqual(page_problems(self.copy), [])

    def test_a_title_is_written_as_text(self):
        # A title holds no "<", by the characters a value may hold. An "&" is written as a character reference.
        import generate as generator
        data = {"principles": [{"title": "Keep one place & no other"}]}
        self.assertEqual(generator.page_principles(data), ["<li>Keep one place &amp; no other</li>"])

    def test_a_principle_added_to_ratchet_json_fails(self):
        def add(data):
            # A principle stands over at least one rule, so a rule moves under it from a principle that keeps another.
            keys = [rule["principle"] for rule in data["rules"]]
            rule = next(rule for rule in data["rules"] if keys.count(rule["principle"]) > 1)
            rule["principle"] = "principle.example"
            data["principles"].append({"key": "principle.example", "title": "An example", "text": "Is this an example?"})
        rewrite_ratchet(self.copy, add)
        self.assert_list_fails("the list of the principles is")
        self.assert_check_fails(self.stale)

    def test_a_principle_removed_from_ratchet_json_fails(self):
        def remove(data):
            # Every rule names a principle, so the rules under the last one move under the first.
            gone = data["principles"].pop()
            for rule in data["rules"]:
                if rule["principle"] == gone["key"]:
                    rule["principle"] = data["principles"][0]["key"]
        rewrite_ratchet(self.copy, remove)
        self.assert_list_fails("the list of the principles is")
        self.assert_check_fails(self.stale)

    def test_two_principles_swapped_in_ratchet_json_fail(self):
        def swap(data):
            data["principles"][0], data["principles"][1] = data["principles"][1], data["principles"][0]
        rewrite_ratchet(self.copy, swap)
        self.assert_list_fails("the list of the principles is")
        self.assert_check_fails(self.stale)

    def test_an_item_of_the_list_edited_moved_or_left_out_fails(self):
        for old, new in (("<li>Subtract first</li>", "<li>Add more</li>"), ("<li>Subtract first</li>\n", ""),
                         ("<li>Keep one place</li>", "<li>Keep one place</li>\n<li>Keep one place</li>"),
                         ("<li>Guard the boundaries</li>", "<li>Guard the boundaries, mostly</li>")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_list_fails("the list of the principles is")
                self.assert_check_fails(self.stale)

    def test_an_item_that_holds_more_than_text_fails(self):
        self.change("<li>Guard the boundaries</li>", "<li>Guard <em>the</em> boundaries</li>")
        self.assert_list_fails("an item of the list of the principles holds a <em>, and holds only text")
        self.assert_check_fails(self.form)

    def test_a_list_of_another_form_fails_and_generate_writes_nothing(self):
        for old, new, message in (('<ol id="principles">', '<ol id="other">', "lists of the principles"),
                                  ('<ol id="principles">', '<ol id="principles" class="wide">', None),
                                  ('<ol id="principles">', '<ol id="principles">\n<ol id="principles">', "holds a <ol>, and holds only <li>"),
                                  ("<li>Keep one place</li>", "<li>Keep one place</li>\n<p>x</p>", "holds only <li>"),
                                  ("<li>Keep one place</li>", "<li>Keep one place</li>\n<li>Keep\none place</li>", None),
                                  # Without the line that closes the list, the next </ol> on the page is not its end: what
                                  # stands before it is not an item, and nothing is written over.
                                  ("<li>Subtract first</li>\n</ol>", "<li>Subtract first</li>", None)):
            with self.subTest(new=new):
                self.setUp()
                before = self.page().replace(old, new, 1)
                self.change(old, new)
                if message:
                    self.assert_list_fails(message)
                self.assert_check_fails(self.form)
                code, output = run("generate.py", root=self.copy, cwd=self.copy)
                self.assertEqual(code, 1, output)
                self.assertNotIn("wrote docs/index.html", output)
                self.assertEqual(self.page(), before)

    def test_an_indented_list_passes(self):
        text = self.page()
        start = text.index('<ol id="principles">')
        end = text.index("</ol>", start) + len("</ol>")
        self.change(text[start:end], "\n".join("  " + line for line in text[start:end].split("\n")))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        self.assertEqual(principle_problems(self.copy), [])

    def test_text_in_the_list_outside_an_item_fails(self):
        # Words straight in the <ol> show on the page as part of the list, and are not an item the test compares.
        for old, new in (("<li>Keep one place</li>", "<li>Keep one place</li>\nand one more"),
                         ('<ol id="principles">', '<ol id="principles">Ship it'),
                         ("<li>Subtract first</li>\n</ol>", "<li>Subtract first</li>\n&#83;hip it</ol>")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_list_fails("holds text outside an <li>")
                self.assert_check_fails(self.form)

    def test_a_void_element_in_the_list_fails_and_leaves_the_count_right(self):
        # A <br> has no end tag. Counted as opened, it would leave the reader one level deep, so that the next <li> was
        # read as nested and a later <p> as inside an item. The reader names the void element and does not count it.
        for old, new in (("<li>Guard the boundaries</li>", "<li>Guard the<br>boundaries</li>"),
                         ("<li>Guard the boundaries</li>", "<li>Guard the<br/>boundaries</li>"),
                         ("<li>Guard the boundaries</li>", "<li>Guard the boundaries</li><hr>"),
                         ("<li>Guard the boundaries</li>", "<li>Guard the boundaries</br></li>")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_list_fails("void element", "and its items hold only text")
                self.assert_check_fails(self.form)
        self.setUp()
        self.change("<li>Guard the boundaries</li>", "<li>Guard the<br>boundaries</li>")
        self.change("<li>Subtract first</li>", "<li>Subtract first</li>\n<p>x</p>")
        self.assert_list_fails("holds a <p>, and holds only <li>")
        reader = ListReader()
        reader.feed(self.page())
        self.assertEqual(reader.in_list, 0)
        self.assertEqual(len(reader.items), 7)


class PageMotion(RepoCopy, unittest.TestCase):
    """The page moves only for a visitor who has not asked for less motion, and the CSS still loads nothing."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_fails(self, *message):
        Page.assert_fails(self, *message)

    def test_the_page_as_it_stands_does_not_move(self):
        css = self.page()[self.page().index("<style>"):self.page().index("</style>")]
        self.assertEqual(motion_problems(css), [])
        for word in ("animation", "transition", "scroll-behavior", "@keyframes"):
            self.assertNotIn(word, css)

    def test_an_animation_inside_the_query_for_no_preference_passes(self):
        self.change("</style>", "%s { .button { transition: color 0.15s ease-out; } }\n"
                    "@keyframes wheel-tick { from { opacity: 0; } to { opacity: 1; } }\n</style>" % REDUCED)
        self.assertEqual(page_problems(self.copy), [])

    def test_an_animation_outside_the_query_fails(self):
        for rule in (".fig { animation: wheel-tick 3.8s linear infinite; }", ".fig { animation-name: wheel-tick; }",
                     ".fig{animation:wheel-tick 1s}", "html { scroll-behavior: smooth; }",
                     "@media (prefers-reduced-motion: reduce) { .fig { animation: wheel-tick 1s; } }",
                     "@media (min-width: 1px) { .fig { animation: wheel-tick 1s; } }",
                     "@media (min-width: 0) { .button { transition: color 0.15s ease-out; } }",
                     "@media (prefers-reduced-motion: no-preference), (min-width: 1px) { .fig { animation: wheel-tick 1s; } }",
                     ".wheel-tick { -webkit-animation: wheel-tick 3.8s linear infinite; }",
                     ".fig { -webkit-animation-name: wheel-tick; }", ".fig { -moz-animation: wheel-tick 1s; }",
                     ".fig { -o-animation-duration: 1s; }", ".fig { -MS-Animation: wheel-tick 1s; }",
                     "html { -webkit-scroll-behavior: smooth; }",
                     ".button::after { transition: translate 0.15s ease-out; }", ".x { transition-duration: 1s; }",
                     ".x { -webkit-transition: opacity 1s; }", ".x{transition:opacity 1s}"):
            with self.subTest(rule=rule):
                self.setUp()
                self.change("</style>", rule + "\n</style>")
                self.assert_fails("moves the page outside %s" % REDUCED)

    def test_a_prefixed_animation_inside_the_query_passes_as_the_unprefixed_one_does(self):
        # A vendor prefix changes nothing: the property is held to the query as the unprefixed one is.
        for rule in ("-webkit-animation: wheel-tick 1s", "-webkit-animation-name: wheel-tick", "-moz-animation: wheel-tick 1s",
                     "-webkit-transition: opacity 1s"):
            with self.subTest(rule=rule):
                self.assertEqual(motion_problems("%s { .fig { %s; } }" % (REDUCED, rule)), [])
                self.assertEqual(len(motion_problems(".fig { %s; }" % rule)), 1)

    def test_a_prefixed_keyframes_fails_as_an_at_rule_the_css_may_not_hold(self):
        for rule in ("@-webkit-keyframes wheel-tick { from { opacity: 0; } }", "@-moz-keyframes wheel-tick { to { opacity: 1; } }"):
            with self.subTest(rule=rule):
                self.setUp()
                self.change("</style>", rule + "\n</style>")
                self.assert_fails("the CSS holds @%s" % rule[1:].split()[0], "the only at-rules it may hold are @media and @keyframes")

    def test_a_brace_that_is_not_matched_fails(self):
        for rule in (".x { color: inherit;", ".x { color: inherit; } }"):
            with self.subTest(rule=rule):
                self.setUp()
                self.change("</style>", rule + "\n</style>")
                self.assert_fails("the CSS has a brace that is not matched")

    def test_an_at_rule_but_media_and_keyframes_still_fails(self):
        for rule in ("@supports (display: grid) { .x { display: grid; } }", "@property --x { syntax: '*'; }",
                     "@namespace svg x;", "@layer x;"):
            with self.subTest(rule=rule):
                self.setUp()
                self.change("</style>", rule + "\n</style>")
                self.assert_fails("the only at-rules it may hold are @media and @keyframes")


if __name__ == "__main__":
    unittest.main()
