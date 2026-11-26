"""repo.short-pages: the word caps that generate.py --check holds the first pages, HANDOVER.md and the changelog to.

    python3 -m unittest discover -s checks -v

Each case writes the pages and the changelog it needs in a scratch directory of its own, or a copy of this repo, and
runs the check on them. The case across pull requests makes a small git repo of a copy of this one, a pull request
that lengthens a page and raises its cap in the same commit, and the merge, and judges it with from_base.py.
Standard library only.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

import from_base
import generate
import registry
import testing

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def words(count):
    return " ".join(["word"] * count)


def entry(version, short=10, bullets=(10,), dated=True, extra=""):
    """A changelog entry: its heading, "In short" of `short` words in all (None for none), one bullet per count."""
    lines = ["## %s (%s)" % (version, "2026-11-26" if dated else "unreleased"), ""]
    if short is not None:
        lines += ["In short: " + words(short - 2), ""]
    lines += ["- " + words(count) for count in bullets]
    return "\n".join(lines) + "\n" + extra + "\n"


def changelog(*entries):
    return "# Changelog\n\n" + "".join(entries)


class Pages(unittest.TestCase):
    """The caps of the pages, and the changelog, on a scratch directory that holds only what each case writes."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ratchet-test-")
        self.addCleanup(shutil.rmtree, self.root)
        for name, cap in generate.PAGE_CAPS.items():
            self.page(name, cap)

    def page(self, name, count, data=None):
        with open(os.path.join(self.root, name), "wb") as handle:
            handle.write(data if data is not None else ("# Title\n\n" + words(count - 2) + "\n").encode("utf-8"))

    def problems(self, text=None):
        return generate.short_page_problems(self.root, text if text is not None else changelog(entry("0.17")))

    def test_the_five_pages_and_their_caps_are_pinned(self):
        """Read from the rule, not from generate.py, so a page dropped from PAGE_CAPS, or a cap moved, turns this red."""
        self.assertEqual(generate.PAGE_CAPS, {"README.md": 1600, "TRYING.md": 700, "STARTING.md": 1300,
                                              "UPGRADING.md": 900, "HANDOVER.md": 2000})

    def test_each_page_at_its_cap_passes(self):
        self.assertEqual(self.problems(), [])
        self.page("README.md", generate.PAGE_CAPS["README.md"] - 300)
        self.assertEqual(self.problems(), [])

    def test_a_page_one_word_over_its_cap_fails_naming_it(self):
        for name, cap in sorted(generate.PAGE_CAPS.items()):
            with self.subTest(name=name):
                self.page(name, cap + 1)
                self.assertEqual(self.problems(), ["%s: %d words, over its cap of %d (repo.short-pages). Shorten it"
                                                   % (name, cap + 1, cap)])
                self.page(name, cap)

    def test_a_missing_page_fails(self):
        for name in sorted(generate.PAGE_CAPS):
            with self.subTest(name=name):
                os.remove(os.path.join(self.root, name))
                self.assertEqual(self.problems(), ["%s: missing, and repo.short-pages caps its words" % name])
                self.page(name, 5)

    def test_a_page_that_is_not_utf8_fails(self):
        for name in sorted(generate.PAGE_CAPS):
            with self.subTest(name=name):
                self.page(name, 0, b"# Title\n\ncaf\xe9\n")
                with self.assertRaises(registry.RegistryError) as raised:
                    self.problems()
                self.assertIn(name, str(raised.exception))
                self.assertIn("Every file a check reads is UTF-8", str(raised.exception))
                self.page(name, 5)

    def test_in_short_at_60_words_passes_and_at_61_fails(self):
        self.assertEqual(self.problems(changelog(entry("0.17", short=60))), [])
        self.assertEqual(self.problems(changelog(entry("0.17", short=61))),
                         ['CHANGELOG.md:5: "In short" in the entry of 0.17 has 61 words, over the cap of 60 (repo.short-pages)'])

    def test_in_short_is_counted_to_the_first_blank_line(self):
        text = changelog(entry("0.17", short=None, extra="")).replace(
            "\n- ", "\nIn short: %s\n%s\n\n- " % (words(30), words(29)), 1)
        self.assertEqual(self.problems(text),
                         ['CHANGELOG.md:5: "In short" in the entry of 0.17 has 61 words, over the cap of 60 (repo.short-pages)'])

    def test_a_bullet_at_40_words_passes_and_at_41_fails(self):
        self.assertEqual(self.problems(changelog(entry("0.17", bullets=(40, 40)))), [])
        self.assertEqual(self.problems(changelog(entry("0.17", bullets=(40, 41)))),
                         ["CHANGELOG.md:8: a bullet of 41 words in the entry of 0.17, over the cap of 40 (repo.short-pages)"])

    def test_an_entry_from_0_17_with_no_in_short_fails(self):
        for dated in (True, False):
            with self.subTest(dated=dated):
                self.assertEqual(self.problems(changelog(entry("0.17", short=None, dated=dated))),
                                 ['CHANGELOG.md: the entry of 0.17 has no paragraph that starts with "In short:" (repo.short-pages)'])

    def test_a_bullet_wrapped_over_lines_is_counted_whole(self):
        wrapped = changelog(entry("0.17", bullets=())).rstrip("\n") + "\n\n- %s\n  %s\n\n" % (words(20), words(21))
        self.assertEqual(self.problems(wrapped),
                         ["CHANGELOG.md:7: a bullet of 41 words in the entry of 0.17, over the cap of 40 (repo.short-pages)"])
        unindented = wrapped.replace("\n  word", "\nword")
        self.assertEqual(self.problems(unindented),
                         ["CHANGELOG.md:7: a bullet of 41 words in the entry of 0.17, over the cap of 40 (repo.short-pages)"])

    def test_a_bullet_ends_at_the_next_bullet_a_blank_line_a_table_row_or_the_count(self):
        ends = {"next bullet": "- " + words(5), "blank line": "", "table row": "| a | b |",
                "generated count": "<!-- generated:count -->"}
        for name, line in ends.items():
            with self.subTest(end=name):
                text = changelog(entry("0.17", bullets=(30,))).rstrip("\n") + "\n" + line + "\n" + words(30) + "\n"
                self.assertEqual(self.problems(text), [])

    def test_entries_before_0_17_are_not_counted(self):
        old = entry("0.16", short=None, bullets=(184,))
        self.assertEqual(self.problems(changelog(entry("0.17"), old)), [])
        for version in ("0.9", "0.10", "0.16"):
            with self.subTest(version=version):
                self.assertEqual(self.problems(changelog(entry("0.17"), entry(version, short=None, bullets=(184,)))), [])

    def test_versions_are_compared_as_numbers(self):
        for version in ("0.18", "0.170", "1.0", "2.3"):
            with self.subTest(version=version):
                problems = self.problems(changelog(entry(version, bullets=(41,)), entry("0.17")))
                self.assertEqual(problems, ["CHANGELOG.md:7: a bullet of 41 words in the entry of %s, over the cap of 40 "
                                            "(repo.short-pages)" % version])

    def test_a_dated_entry_with_a_table_and_the_count_passes(self):
        table = "| Path | Steps | Seconds |\n|---|---|---|\n| " + " | ".join([words(30)] * 3) + " |\n"
        count = "<!-- generated:count -->\n" + words(90) + "\n<!-- /generated -->\n"
        text = changelog(entry("0.18", bullets=(40, 40), extra="\n" + table + "\n" + count), entry("0.17"))
        self.assertEqual(self.problems(text), [])
        glued = changelog(entry("0.18", bullets=(40,), extra=table + count), entry("0.17"))
        self.assertEqual(self.problems(glued), [])


class ThisRepo(unittest.TestCase):

    def test_the_pages_and_the_changelog_of_this_repo_pass(self):
        self.assertEqual(generate.short_page_problems(ROOT, registry.read(os.path.join(ROOT, "CHANGELOG.md"))), [])

    def test_generate_check_fails_on_a_page_over_its_cap_in_a_copy_of_this_repo(self):
        copy = os.path.join(tempfile.mkdtemp(prefix="ratchet-test-"), "ratchet")
        self.addCleanup(shutil.rmtree, os.path.dirname(copy))
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        path = os.path.join(copy, "HANDOVER.md")
        with open(path, encoding="utf-8") as handle:
            count = len(handle.read().split())
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n" + words(generate.PAGE_CAPS["HANDOVER.md"] - count + 1) + "\n")
        result = subprocess.run([sys.executable, "-B", os.path.join(copy, "checks", "generate.py"), "--check"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("HANDOVER.md: %d words, over its cap of %d (repo.short-pages)"
                      % (generate.PAGE_CAPS["HANDOVER.md"] + 1, generate.PAGE_CAPS["HANDOVER.md"]), result.stdout)


class AcrossPullRequests(unittest.TestCase):
    """A pull request that lengthens a page past the base's cap and raises the cap in the same commit passes its own
    generate.py --check, and fails the base's, as the job `base` runs it."""

    def setUp(self):
        scratch = os.path.realpath(tempfile.mkdtemp(prefix="ratchet-test-"))
        self.addCleanup(shutil.rmtree, scratch)
        self.repo = os.path.join(scratch, "repo")
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.env = testing.environment(HOME=scratch, LC_ALL="C", PYTHONDONTWRITEBYTECODE="1",
                                       **testing.identity("Ratchet test"))
        self.git("init", "-q", "-b", "main")
        self.git("config", "commit.gpgsign", "false")
        self.base = self.commit("the base")

    def git(self, *args):
        return testing.git(self.repo, *args, env=self.env)

    def commit(self, message):
        return testing.commit(self.repo, message, self.env)

    def edit(self, name, change):
        path = os.path.join(self.repo, name)
        with open(path, encoding="utf-8", newline="") as handle:
            text = handle.read()
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(change(text))

    def test_raising_the_cap_with_the_page_fails_the_base(self):
        cap = generate.PAGE_CAPS["HANDOVER.md"]
        self.git("switch", "-q", "-c", "pr", self.base)
        self.edit("HANDOVER.md", lambda text: text + "\n" + words(cap + 50 - len(text.split())) + "\n")
        old = '"HANDOVER.md": %d}' % cap
        self.edit("checks/generate.py", lambda text: text.replace(old, '"HANDOVER.md": %d}' % (cap + 100), 1)
                  if old in text else self.fail("the test expects %r in generate.py" % old))
        self.commit("the pull request")
        self.git("switch", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", "the merge", "pr")

        own = subprocess.run([sys.executable, "-B", "checks/generate.py", "--check"], cwd=self.repo, env=self.env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(own.returncode, 0, own.stdout)

        outputs = []

        def run(work, command):
            result = subprocess.run([sys.executable, "-B"] + list(command), cwd=work, env=self.env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            outputs.append(result.stdout)
            return result.returncode

        with unittest.mock.patch.object(from_base, "run", run), unittest.mock.patch("sys.stdout"):
            problems = from_base.judge(self.repo, self.base, data_commands=(("checks/generate.py", "--check"),),
                                       code_commands=())
        self.assertIn("the base's `python3 checks/generate.py --check` failed in the tree of the data, with exit status 1",
                      problems)
        self.assertIn("HANDOVER.md: %d words, over its cap of %d (repo.short-pages)" % (cap + 50, cap), "".join(outputs))


if __name__ == "__main__":
    unittest.main()
