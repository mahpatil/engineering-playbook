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


def fence(lang, n, body="key: v"):
    return f"```{lang}\n" + "\n".join(f"{body}{i}" for i in range(n)) + "\n```\n"


class SnippetLimits(unittest.TestCase):
    def test_short_fence_ok(self):
        self.assertEqual(check.check_snippet_limits("a.md", GOOD_DOC + fence("bash", 5)), [])

    def test_boundaries_generic(self):
        doc = GOOD_DOC + "x\n" * 100
        self.assertEqual(check.check_snippet_limits("a.md", doc + fence("bash", 15)), [])
        f = check.check_snippet_limits("a.md", doc + fence("bash", 16))
        self.assertEqual([(x.std, x.severity) for x in f], [("S5", "warn")])

    def test_boundaries_config_error(self):
        doc = GOOD_DOC + "x\n" * 200
        self.assertEqual(stds(check.check_snippet_limits("a.md", doc + fence("yaml", 20)), severity="error"), [])
        f = check.check_snippet_limits("a.md", doc + fence("yaml", 21))
        self.assertEqual(len(stds(f, "S5", "error")), 1)

    def test_multi_document_yaml_errors(self):
        doc = GOOD_DOC + "x\n" * 50 + "```yaml\na: 1\n---\nb: 2\n```\n"
        self.assertEqual(len(stds(check.check_snippet_limits("a.md", doc), severity="error")), 1)

    def test_multi_resource_terraform_errors(self):
        tf = 'resource "a" "b" {}\nresource "c" "d" {}\n'
        doc = GOOD_DOC + "x\n" * 50 + f"```hcl\n{tf}```\n"
        self.assertEqual(len(stds(check.check_snippet_limits("a.md", doc), severity="error")), 1)

    def test_fenced_share_warns(self):
        doc = "intro\n" + fence("bash", 14) + fence("bash", 14)
        f = check.check_snippet_limits("a.md", doc)
        self.assertTrue(any("share" in x.message for x in f))

    def test_lines_in_fence_not_treated_as_headings(self):
        doc = "# T\n```md\n## What is\n## Why\n```\n"
        self.assertEqual(len(check.check_purpose_opener("a.md", doc)), 1)


class Placeholders(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(check.check_placeholders("a.md", GOOD_DOC), [])

    def test_flags_each_term(self):
        for term in ("TODO: fix", "FIXME", "Lorem ipsum", "placeholder", "test comment", "your-org"):
            f = check.check_placeholders("a.md", f"# T\n\n{term}\n")
            self.assertEqual([(x.std, x.severity, x.line) for x in f], [("S5", "error", 3)], term)


class SnippetSyntax(unittest.TestCase):
    def test_valid_python_ok(self):
        doc = "```python\ndef f():\n    return 1\n```\n"
        self.assertEqual(check.check_snippet_syntax("a.md", doc), [])

    def test_invalid_python_warns(self):
        doc = "```python\ndef f(:\n```\n"
        self.assertEqual([(x.std, x.severity) for x in check.check_snippet_syntax("a.md", doc)], [("S5", "warn")])

    def test_ellipsis_skipped(self):
        doc = "```python\ndef f(:\n    ...\n```\n"
        self.assertEqual(check.check_snippet_syntax("a.md", doc), [])

    def test_undefined_self_method_warns(self):
        doc = ("```python\nclass S:\n    async def run(self):\n"
               "        await self.compensate(1)\n```\n")
        f = check.check_snippet_syntax("a.md", doc)
        self.assertEqual(len(f), 1)
        self.assertIn("compensate", f[0].message)

    def test_defined_self_method_ok(self):
        doc = ("```python\nclass S:\n    def run(self):\n        self.c()\n"
               "    def c(self):\n        pass\n```\n")
        self.assertEqual(check.check_snippet_syntax("a.md", doc), [])

    def test_bad_json_warns_good_json_ok(self):
        self.assertEqual(len(check.check_snippet_syntax("a.md", "```json\n{a:1}\n```\n")), 1)
        self.assertEqual(check.check_snippet_syntax("a.md", '```json\n{"a": 1}\n```\n'), [])


class SlopPhrases(unittest.TestCase):
    TERMS = ["delve", "it's important to note"]

    def test_clean(self):
        self.assertEqual(check.check_slop("a.md", GOOD_DOC, self.TERMS), [])

    def test_flags_terms_case_insensitive(self):
        f = check.check_slop("a.md", "# T\n\nLet us Delve in. It's important to note this.\n", self.TERMS)
        self.assertEqual([(x.std, x.severity) for x in f], [("S5", "warn")] * 2)

    def test_emoji_in_heading_warns(self):
        f = check.check_slop("a.md", "# T\n\n## \U0001F680 Quick start\n", [])
        self.assertEqual(len(f), 1)

    def test_emoji_in_body_ok(self):
        self.assertEqual(check.check_slop("a.md", "# T\n\nship it \U0001F680\n", []), [])


if __name__ == "__main__":
    unittest.main()
