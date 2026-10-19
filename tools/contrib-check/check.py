#!/usr/bin/env python3
"""Deterministic contribution checks. No LLM, stdlib only. See CONTRIBUTING.md."""
import ast
import json
import re
import textwrap
from dataclasses import dataclass

ERROR, WARN = "error", "warn"
OPENER_WINDOW = 40
PR_SECTION_MIN = 40
FENCE_WARN_LINES = 15
CONFIG_FENCE_MAX = 20
FENCE_SHARE_WARN = 0.30
CONFIG_LANGS = {"yaml", "yml", "hcl", "terraform", "tf", "json", "dockerfile"}
PLACEHOLDER_RE = re.compile(r"\b(TODO|FIXME|lorem ipsum|placeholder|test comment|your-org)\b", re.I)
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
SELF_CALL_RE = re.compile(r"\bself\.(\w+)\(")
PR_SECTIONS = ("What changed", "How tested", "What could go wrong")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    std: str
    severity: str
    message: str


def parse_fences(text):
    """Return [(lang, first_body_line_no, [body lines])] for each closed code fence."""
    out, cur = [], None
    for no, ln in enumerate(text.splitlines(), 1):
        if ln.lstrip().startswith("```"):
            if cur is None:
                cur = (ln.strip()[3:].strip().lower(), no + 1, [])
            else:
                out.append(cur)
                cur = None
        elif cur is not None:
            cur[2].append(ln)
    return out


def prose_lines(text):
    """Yield (line_no, line) for lines outside code fences."""
    inside = False
    for no, ln in enumerate(text.splitlines(), 1):
        if ln.lstrip().startswith("```"):
            inside = not inside
        elif not inside:
            yield no, ln


def check_purpose_opener(path, text):
    head = [ln for no, ln in prose_lines(text) if no <= OPENER_WINDOW]
    h2s = [ln.lower() for ln in head if ln.startswith("## ")]
    has_what = any(re.search(r"\bwhat\b", h) for h in h2s)
    has_why = any(re.search(r"\bwhy\b", h) for h in h2s)
    if has_what and has_why:
        return []
    return [Finding(path, 1, "S4", ERROR,
                    f"missing purpose opener: add '## What is ...' and '## Why ...' "
                    f"within the first {OPENER_WINDOW} lines")]


def check_readme_indexed(path, readme_text):
    if path in readme_text or ("./" + path) in readme_text:
        return []
    return [Finding(path, 1, "S8", ERROR, "not linked from README.md index")]


def _section_body(body, heading):
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S | re.I)
    if not m:
        return None
    return re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S).strip()


def check_pr_body(body):
    body = body.replace("\r\n", "\n")
    out = []
    for name in PR_SECTIONS:
        content = _section_body(body, name)
        if content is None:
            out.append(Finding("PR body", 1, "S10", ERROR, f"missing '## {name}' section"))
        elif len(content) < PR_SECTION_MIN or content.lower().strip(". ") in {"n/a", "na", "none", "tbd"}:
            out.append(Finding("PR body", 1, "S10", ERROR,
                               f"'## {name}' needs specifics (>= {PR_SECTION_MIN} chars, not N/A)"))
    return out


def _multi_resource(lang, body):
    if lang in ("yaml", "yml"):
        seps = [i for i, ln in enumerate(body) if ln.strip() == "---" and i > 0]
        kinds = [ln for ln in body if re.match(r"kind:", ln)]
        return bool(seps) or len(kinds) > 1
    if lang in ("hcl", "terraform", "tf"):
        return len(re.findall(r'^(resource|module|provider)\s+"', "\n".join(body), re.M)) > 1
    return False


def check_snippet_limits(path, text):
    out, fenced = [], 0
    for lang, start, body in parse_fences(text):
        fenced += len(body)
        if lang in CONFIG_LANGS and len(body) > CONFIG_FENCE_MAX:
            out.append(Finding(path, start, "S5", ERROR,
                               f"{lang} block is {len(body)} lines (max {CONFIG_FENCE_MAX}); show an excerpt"))
        elif _multi_resource(lang, body):
            out.append(Finding(path, start, "S5", ERROR,
                               f"{lang} block holds several resources/documents; show one excerpt"))
        elif len(body) > FENCE_WARN_LINES:
            out.append(Finding(path, start, "S5", WARN,
                               f"code block is {len(body)} lines (> {FENCE_WARN_LINES}); trim to an excerpt"))
    total = len(text.splitlines())
    if total and fenced / total > FENCE_SHARE_WARN:
        out.append(Finding(path, 1, "S5", WARN,
                           f"code is {fenced * 100 // total}% of the doc (share > {int(FENCE_SHARE_WARN * 100)}%)"))
    return out


def check_placeholders(path, text):
    return [Finding(path, no, "S5", ERROR, f"placeholder text '{m.group(0)}'")
            for no, ln in enumerate(text.splitlines(), 1)
            for m in [PLACEHOLDER_RE.search(ln)] if m]


def _python_findings(path, start, body):
    src = textwrap.dedent("\n".join(body))
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [Finding(path, start, "S5", WARN, f"python block does not parse: {e.msg}")]
    defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    called = {m.group(1) for m in SELF_CALL_RE.finditer(src)}
    return [Finding(path, start, "S5", WARN, f"self.{name}() is called but never defined in the block")
            for name in sorted(called - defined)]


def check_snippet_syntax(path, text):
    out = []
    for lang, start, body in parse_fences(text):
        joined = "\n".join(body)
        if "..." in joined:
            continue
        if lang in ("python", "py"):
            out += _python_findings(path, start, body)
        elif lang == "json" and "//" not in joined:
            try:
                json.loads(joined)
            except ValueError as e:
                out.append(Finding(path, start, "S5", WARN, f"json block does not parse: {e}"))
    return out


def check_slop(path, text, terms):
    out = []
    for no, ln in enumerate(text.splitlines(), 1):
        low = ln.lower()
        out += [Finding(path, no, "S5", WARN, f"slop phrase '{t}'") for t in terms if t.lower() in low]
        if ln.startswith("#") and EMOJI_RE.search(ln):
            out.append(Finding(path, no, "S5", WARN, "emoji in heading"))
    return out
