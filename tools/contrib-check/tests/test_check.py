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
        for term in ("TODO: fix", "FIXME", "Lorem ipsum", "test comment", "your-org"):
            f = check.check_placeholders("a.md", f"# T\n\n{term}\n")
            self.assertEqual([(x.std, x.severity, x.line) for x in f], [("S5", "error", 3)], term)

    def test_word_placeholder_only_warns(self):
        f = check.check_placeholders("a.md", "# T\n\nUse a placeholder variable.\n")
        self.assertEqual([(x.std, x.severity, x.line) for x in f], [("S5", "warn", 3)])


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


TOOLS = ["Argo", "Flyway"]


class PrincipleFirst(unittest.TestCase):
    def test_principles_before_tools_passes(self):
        doc = "# T\n\n## Principles\n\n1. Be neutral.\n\n## Tooling\n\nUse Argo.\n"
        self.assertEqual(check.check_principle_first("a.md", doc, TOOLS), [])

    def test_missing_principles_heading_warns(self):
        f = check.check_principle_first("a.md", "# T\n\n## Design\n\ntext\n", TOOLS)
        self.assertEqual([(x.std, x.severity) for x in f], [("S1", "warn")])

    def test_tool_in_heading_warns(self):
        doc = "# T\n\n## Principles\n\nx\n\n## Argo setup\n\ntext\n"
        self.assertEqual(len(check.check_principle_first("a.md", doc, TOOLS)), 1)

    def test_tool_before_principles_warns(self):
        doc = "# T\n\nWe use Argo here.\n\n## Principles\n\nx\n"
        self.assertEqual(len(check.check_principle_first("a.md", doc, TOOLS)), 1)


class ToolDefaults(unittest.TestCase):
    def test_swap_signal_passes(self):
        doc = "Use a rollout controller, e.g. Argo Rollouts, or equivalent.\n"
        self.assertEqual(check.check_tool_defaults("a.md", doc, TOOLS), [])

    def test_bare_tool_warns_once_per_tool(self):
        doc = "We deploy with Argo.\n\nArgo syncs state.\n"
        f = check.check_tool_defaults("a.md", doc, TOOLS)
        self.assertEqual([(x.std, x.severity, x.line) for x in f], [("S2", "warn", 1)])

    def test_the_word_like_is_not_a_swap_signal(self):
        doc = "Teams like the speed of Argo.\n"
        self.assertEqual(len(check.check_tool_defaults("a.md", doc, TOOLS)), 1)

    def test_tool_inside_code_fence_ignored(self):
        doc = "```bash\nargo sync\nflyway migrate\n```\n"
        self.assertEqual(check.check_tool_defaults("a.md", doc, TOOLS), [])


class AlternativesSignal(unittest.TestCase):
    def test_recommend_without_alternatives_warns(self):
        f = check.check_alternatives("a.md", "We recommend GitOps.\n")
        self.assertEqual([(x.std, x.severity) for x in f], [("S3", "warn")])

    def test_recommend_with_alternatives_ok(self):
        self.assertEqual(check.check_alternatives("a.md", "We recommend A.\n\n## When to use B\n"), [])

    def test_no_recommendation_ok(self):
        self.assertEqual(check.check_alternatives("a.md", "Plain text.\n"), [])


class FitsContext(unittest.TestCase):
    EXISTS = staticmethod(lambda p: p in {"standards/b.md", "standards/c.md", "standards/a.md"})

    def test_links_and_related_heading_ok(self):
        doc = "## Related standards\n\n[b](b.md) [c](./c.md)\n"
        self.assertEqual(check.check_fits_context("standards/a.md", doc, self.EXISTS), [])

    def test_too_few_links_warns(self):
        doc = "## Related standards\n\n[b](b.md)\n"
        f = check.check_fits_context("standards/a.md", doc, self.EXISTS)
        self.assertEqual([(x.std, x.severity) for x in f], [("S7", "warn")])

    def test_broken_and_self_links_do_not_count(self):
        doc = "## Related\n\n[x](missing.md) [s](a.md) [b](b.md)\n"
        self.assertEqual(len(check.check_fits_context("standards/a.md", doc, self.EXISTS)), 1)

    def test_no_relationship_text_warns(self):
        doc = "[b](b.md) [c](c.md)\n"
        self.assertEqual(len(check.check_fits_context("standards/a.md", doc, self.EXISTS)), 1)


class UnsupportedClaims(unittest.TestCase):
    def test_bare_number_warns(self):
        f = check.check_claims("a.md", "Tokens must expire within 15 minutes.\n")
        self.assertEqual([(x.std, x.severity, x.line) for x in f], [("S9", "warn", 1)])

    def test_rationale_in_paragraph_ok(self):
        doc = "Tokens expire within 15 minutes because a leaked token is then short-lived.\n"
        self.assertEqual(check.check_claims("a.md", doc), [])

    def test_link_in_paragraph_ok(self):
        doc = "Use p99 under 500ms ([source](https://example.com)).\n"
        self.assertEqual(check.check_claims("a.md", doc), [])

    def test_code_and_tables_ignored(self):
        doc = "```yaml\nttl: 900s\n```\n\n| a | 99.9% |\n"
        self.assertEqual(check.check_claims("a.md", doc), [])


class PrSize(unittest.TestCase):
    def test_docs_are_exempt(self):
        stat = [("standards/a.md", 900), ("docs/specs/x.html", 600), ("docs/y.txt", 700)]
        self.assertEqual(stds(check.check_pr_size(stat), severity="error"), [])

    def test_code_boundary(self):
        self.assertEqual(check.check_pr_size([("tools/a.py", 500)]), [])
        f = check.check_pr_size([("tools/a.py", 300), ("tools/b.sh", 201)])
        self.assertEqual([(x.std, x.severity) for x in f], [("S6", "error")])

    def test_large_single_doc_warns(self):
        f = check.check_pr_size([("standards/a.md", 401)])
        self.assertEqual([(x.std, x.severity) for x in f], [("S6", "warn")])
        self.assertEqual(check.check_pr_size([("standards/a.md", 400)]), [])


class Pragmas(unittest.TestCase):
    def test_parse_ignores(self):
        text = "<!-- contrib-check: ignore S5 -->\n<!-- contrib-check: ignore S2, S9 -->\n"
        self.assertEqual(check.parse_ignores(text), {"S5", "S2", "S9"})

    def test_apply_suppresses_only_listed(self):
        fs = [check.Finding("a", 1, "S5", "error", "m"), check.Finding("a", 1, "S4", "error", "m")]
        kept = check.apply_ignores(fs, {"S5"})
        self.assertEqual([f.std for f in kept], ["S4"])


class Orchestration(unittest.TestCase):
    CTX = check.Context(readme="", tools=TOOLS, slop=["delve"], exists=lambda p: False)

    def test_exempt_paths_skipped(self):
        self.assertEqual(check.check_file("templates/x.md", "TODO", self.CTX, is_new=True), [])
        self.assertEqual(check.check_file("references/x.md", "TODO", self.CTX, is_new=True), [])

    def test_non_standards_files_skipped(self):
        self.assertEqual(check.check_file("CONTRIBUTING.md", "TODO", self.CTX, is_new=True), [])

    def test_standards_doc_runs_checks(self):
        found = {f.std for f in check.check_file("standards/a.md", "# T\n\nTODO\n", self.CTX, is_new=True)}
        self.assertTrue({"S4", "S5", "S8"} <= found)

    def test_readme_check_only_for_new_files(self):
        found = {f.std for f in check.check_file("standards/a.md", GOOD_DOC, self.CTX, is_new=False)}
        self.assertNotIn("S8", found)

    def test_is_checked(self):
        self.assertTrue(check.is_checked("standards/detailed/a.md"))
        for p in ("CONTRIBUTING.md", "templates/a.md", "standards/claude-md/x.md", "standards/a.txt"):
            self.assertFalse(check.is_checked(p), p)

    def test_claude_md_templates_exempt(self):
        self.assertEqual(check.check_file("standards/claude-md/api/CLAUDE.md", "TODO", self.CTX, is_new=True), [])

    def test_modified_files_only_warn(self):
        found = check.check_file("standards/a.md", "# T\n\nTODO\n", self.CTX, is_new=False)
        self.assertTrue(found)
        self.assertEqual(stds(found, severity="error"), [])

    def test_new_files_keep_errors(self):
        found = check.check_file("standards/a.md", "# T\n\nTODO\n", self.CTX, is_new=True)
        self.assertTrue(stds(found, severity="error"))

    def test_pragma_suppresses(self):
        text = "<!-- contrib-check: ignore S5 -->\n# T\n\nTODO\n"
        found = {f.std for f in check.check_file("standards/a.md", text, self.CTX, is_new=False)}
        self.assertNotIn("S5", found)


class NameStatus(unittest.TestCase):
    def test_added_modified_and_renamed(self):
        out = "A\tnew.md\nM\told.md\nR087\tfrom.md\tto.md\n"
        self.assertEqual(check.parse_name_status(out), {"new.md": True, "old.md": False, "to.md": False})


class Report(unittest.TestCase):
    def test_warnings_only_exit_zero(self):
        code, lines = check.report([check.Finding("a.md", 3, "S2", "warn", "msg")])
        self.assertEqual(code, 0)
        self.assertEqual(lines[0], "::warning file=a.md,line=3::[S2] msg")

    def test_error_exit_one(self):
        code, lines = check.report([check.Finding("a.md", 1, "S4", "error", "msg")])
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith("::error file=a.md,line=1::[S4]"))

    def test_ignored_listed_in_summary(self):
        code, lines = check.report([], ignored={"a.md": {"S5"}})
        self.assertEqual(code, 0)
        self.assertTrue(any("a.md" in ln and "S5" in ln for ln in lines))

    def test_clean_message(self):
        self.assertEqual(check.report([])[0], 0)


class RegressionOnRealDocs(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[3]

    def test_logs_doc_has_no_errors(self):
        path = self.ROOT / "standards/detailed/observability/logs.md"
        if not path.exists():
            self.skipTest("logs.md not present")
        ctx = check.Context(readme=(self.ROOT / "README.md").read_text(), tools=[], slop=[], exists=lambda p: True)
        found = check.check_file("standards/detailed/observability/logs.md", path.read_text(), ctx, is_new=False)
        self.assertEqual(stds(found, severity="error"), [])


if __name__ == "__main__":
    unittest.main()
