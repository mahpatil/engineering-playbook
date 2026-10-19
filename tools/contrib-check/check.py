#!/usr/bin/env python3
"""Deterministic contribution checks. No LLM, stdlib only. See CONTRIBUTING.md."""
import argparse
import ast
import json
import os
import posixpath
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

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
SWAP_RE = re.compile(r"e\.g\.|such as|or equivalent|alternative|swap|for example|for instance|\blike\b", re.I)
ALT_RE = re.compile(r"alternative|when to use|trade-?offs?|trade off", re.I)
RECOMMEND_RE = re.compile(r"\brecommend|\bdefault\b", re.I)
RELATED_RE = re.compile(r"related|how this fits|relationship to|\bvs\.?\b|compared (to|with)|complements", re.I)
LINK_RE = re.compile(r"\]\((?!https?:)([^)#\s]+\.md)")
CLAIM_RE = re.compile(r"\b\d+(\.\d+)?\s?(%|ms\b|seconds?\b|minutes?\b|hours?\b|days?\b|MB\b|GB\b)|\bv\d+\.\d+")
SUPPORT_RE = re.compile(r"\]\(https?:|because|so that|rationale|since |to avoid|which means", re.I)
MIN_RELATED_LINKS = 2
CODE_CAP = 500
DOC_WARN_LINES = 400
DOC_SUFFIXES = (".md", ".html")
DOC_DIRS = ("docs/", "specs/")
EXEMPT_DIRS = ("templates/", "references/")
IGNORE_RE = re.compile(r"<!--\s*contrib-check:\s*ignore\s+([^>]*?)\s*-->", re.I)
HERE = Path(__file__).resolve().parent
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


def _tool_re(tools):
    return re.compile(r"\b(" + "|".join(re.escape(t) for t in tools) + r")\b", re.I) if tools else None


def check_principle_first(path, text, tools):
    lines = list(prose_lines(text))
    principle = next((no for no, ln in lines if re.match(r"#{2,3}\s.*principle", ln, re.I)), None)
    tool_re = _tool_re(tools)
    out = []
    if principle is None:
        out.append(Finding(path, 1, "S1", WARN, "no 'Principles' heading: state the principle before the tool"))
    if tool_re:
        for no, ln in lines:
            if re.match(r"#{1,2}\s", ln) and tool_re.search(ln):
                out.append(Finding(path, no, "S1", WARN, "tool named in a top-level heading; lead with the principle"))
            elif principle and no < principle and not ln.startswith("#") and tool_re.search(ln):
                out.append(Finding(path, no, "S1", WARN, "tool named before the Principles section"))
                break
    return out


def _paragraphs(text):
    """Yield (first_line_no, paragraph_text) for prose outside code fences."""
    start, buf = None, []
    for no, ln in prose_lines(text):
        if ln.strip():
            start = start or no
            buf.append(ln)
        elif buf:
            yield start, "\n".join(buf)
            start, buf = None, []
    if buf:
        yield start, "\n".join(buf)


def check_tool_defaults(path, text, tools):
    tool_re = _tool_re(tools)
    if not tool_re:
        return []
    out, seen = [], set()
    for start, para in _paragraphs(text):
        for m in tool_re.finditer(para):
            name = m.group(1).lower()
            if name not in seen and not SWAP_RE.search(para):
                seen.add(name)
                out.append(Finding(path, start, "S2", WARN,
                                   f"'{m.group(1)}' reads as a default; frame it as an example (e.g., 'such as')"))
    return out


def check_alternatives(path, text):
    if RECOMMEND_RE.search(text) and not ALT_RE.search(text):
        return [Finding(path, 1, "S3", WARN, "recommends an approach but never covers alternatives or when to use them")]
    return []


def check_fits_context(path, text, exists):
    base = posixpath.dirname(path)
    targets = {posixpath.normpath(posixpath.join(base, link)) for link in LINK_RE.findall(text)}
    targets = {t for t in targets if t != path and t.startswith("standards/") and exists(t)}
    if len(targets) >= MIN_RELATED_LINKS and RELATED_RE.search(text):
        return []
    return [Finding(path, 1, "S7", WARN,
                    f"link >= {MIN_RELATED_LINKS} related standards and say how this fits (Related / vs / relationship)")]


def check_claims(path, text):
    out = []
    for start, para in _paragraphs(text):
        if para.lstrip().startswith("|") or para.startswith("#"):
            continue
        if CLAIM_RE.search(para) and not SUPPORT_RE.search(para):
            out.append(Finding(path, start, "S9", WARN, "number/version claim without a rationale or source"))
    return out


def _is_doc(path):
    return path.endswith(DOC_SUFFIXES) or path.startswith(DOC_DIRS)


def check_pr_size(numstat):
    out = []
    code = sum(n for p, n in numstat if not _is_doc(p))
    if code > CODE_CAP:
        out.append(Finding("PR", 1, "S6", ERROR, f"{code} code lines added (cap {CODE_CAP}); split into slices"))
    out += [Finding(p, 1, "S6", WARN, f"{n} lines added to one doc; keep additions high-level")
            for p, n in numstat if p.endswith(".md") and n > DOC_WARN_LINES]
    return out


def parse_ignores(text):
    return {t.strip().upper() for m in IGNORE_RE.finditer(text) for t in m.group(1).split(",") if t.strip()}


def apply_ignores(findings, ignores):
    return [f for f in findings if f.std not in ignores]


@dataclass
class Context:
    readme: str
    tools: list
    slop: list
    exists: Callable[[str], bool]


def check_file(path, text, ctx, is_new):
    if path.startswith(EXEMPT_DIRS) or not (path.startswith("standards/") and path.endswith(".md")):
        return []
    found = (check_purpose_opener(path, text) + check_snippet_limits(path, text)
             + check_placeholders(path, text) + check_snippet_syntax(path, text)
             + check_slop(path, text, ctx.slop) + check_principle_first(path, text, ctx.tools)
             + check_tool_defaults(path, text, ctx.tools) + check_alternatives(path, text)
             + check_fits_context(path, text, ctx.exists) + check_claims(path, text))
    if is_new:
        found += check_readme_indexed(path, ctx.readme)
    return apply_ignores(found, parse_ignores(text))


def report(findings, ignored=None):
    lines = [f"::{'error' if f.severity == ERROR else 'warning'} file={f.path},line={f.line}::[{f.std}] {f.message}"
             for f in findings]
    lines += [f"suppressed in {p}: {', '.join(sorted(stds))}" for p, stds in (ignored or {}).items() if stds]
    errors = sum(f.severity == ERROR for f in findings)
    warns = len(findings) - errors
    lines.append(f"contrib-check: {errors} error(s), {warns} warning(s)")
    return (1 if errors else 0), lines


def _load_terms(name):
    f = HERE / name
    return [ln.strip() for ln in f.read_text().splitlines() if ln.strip() and not ln.startswith("#")]


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def _changed(base):
    """Return ({path: is_new}, [(path, added_lines)]) for the PR diff against base."""
    status = {}
    for ln in _git("diff", "--name-status", "--diff-filter=AM", f"{base}...HEAD").splitlines():
        code, path = ln.split("\t", 1)
        status[path] = code == "A"
    numstat = []
    for ln in _git("diff", "--numstat", f"{base}...HEAD").splitlines():
        added, _, path = ln.split("\t", 2)
        numstat.append((path, int(added) if added.isdigit() else 0))
    return status, numstat


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--pr-body-file")
    args = ap.parse_args(argv)
    if args.files is not None:
        status, numstat = {f: False for f in args.files}, []
    else:
        status, numstat = _changed(args.base)
    ctx = Context(readme=Path("README.md").read_text() if Path("README.md").exists() else "",
                  tools=_load_terms("tool-terms.txt"), slop=_load_terms("slop-terms.txt"),
                  exists=os.path.exists)
    findings, ignored = check_pr_size(numstat), {}
    for path, is_new in sorted(status.items()):
        if path.endswith(".md") and Path(path).exists():
            text = Path(path).read_text()
            findings += check_file(path, text, ctx, is_new)
            ignored[path] = parse_ignores(text)
    body = Path(args.pr_body_file).read_text() if args.pr_body_file else os.environ.get("PR_BODY")
    if body is not None:
        findings += check_pr_body(body)
    code, lines = report(findings, ignored)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
