import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check  # noqa: E402

GOOD_DOC = """# Title

Intro.

## What is it?

Text.

## Why it's required

Text.
"""


def stds(findings, std=None, severity=None):
    return [f for f in findings
            if (std is None or f.std == std) and (severity is None or f.severity == severity)]


class PurposeOpener(unittest.TestCase):
    def test_passes_with_what_and_why(self):
        self.assertEqual(check.check_purpose_opener("standards/a.md", GOOD_DOC), [])

    def test_fails_without_opener(self):
        f = check.check_purpose_opener("standards/a.md", "# T\n\n## Overview\n\ntext\n")
        self.assertEqual([(x.std, x.severity) for x in f], [("S4", "error")])

    def test_fails_when_why_missing(self):
        f = check.check_purpose_opener("standards/a.md", "# T\n\n## What is it\n\nx\n")
        self.assertEqual(len(f), 1)

    def test_opener_beyond_40_lines_fails(self):
        text = "# T\n" + "filler\n" * 45 + "## What is it\n## Why\n"
        self.assertEqual(len(check.check_purpose_opener("standards/a.md", text)), 1)


class ReadmeIndexed(unittest.TestCase):
    def test_indexed_passes(self):
        readme = "[x](./standards/detailed/foo.md)"
        self.assertEqual(check.check_readme_indexed("standards/detailed/foo.md", readme), [])

    def test_unindexed_fails(self):
        f = check.check_readme_indexed("standards/detailed/foo.md", "nothing")
        self.assertEqual([(x.std, x.severity) for x in f], [("S8", "error")])

    def test_nested_readme_is_indexed_by_dir_link(self):
        readme = "[d](./standards/detailed/data/README.md)"
        self.assertEqual(check.check_readme_indexed("standards/detailed/data/README.md", readme), [])


class PrBody(unittest.TestCase):
    FULL = ("## What changed\n" + "Adds the contribution checker for standards. " * 2 +
            "\n\n## How tested\n" + "Ran unit tests and the checker locally. " * 2 +
            "\n\n## What could go wrong\n" + "False positives on heuristics warn only. " * 2 + "\n")

    def test_full_body_passes(self):
        self.assertEqual(check.check_pr_body(self.FULL), [])

    def test_missing_heading_fails(self):
        body = self.FULL.replace("## How tested", "## Notes")
        f = check.check_pr_body(body)
        self.assertEqual([(x.std, x.severity) for x in f], [("S10", "error")])

    def test_short_or_na_section_fails(self):
        body = self.FULL.replace("Ran unit tests and the checker locally. " * 2, "N/A")
        self.assertEqual(len(check.check_pr_body(body)), 1)

    def test_comment_only_section_fails(self):
        body = self.FULL.replace("Ran unit tests and the checker locally. " * 2,
                                 "<!-- Commands run, docs rendered, links checked, checker output. -->")
        self.assertEqual(len(check.check_pr_body(body)), 1)

    def test_39_vs_40_chars(self):
        base = "## What changed\n{}\n## How tested\n{}\n## What could go wrong\n{}\n"
        ok, short = "a" * 40, "a" * 39
        self.assertEqual(check.check_pr_body(base.format(ok, ok, ok)), [])
        self.assertEqual(len(check.check_pr_body(base.format(ok, short, ok))), 1)

    def test_crlf(self):
        self.assertEqual(check.check_pr_body(self.FULL.replace("\n", "\r\n")), [])

    def test_empty_body(self):
        self.assertEqual(len(check.check_pr_body("")), 3)


if __name__ == "__main__":
    unittest.main()
