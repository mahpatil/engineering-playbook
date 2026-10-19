#!/usr/bin/env python3
"""Deterministic contribution checks. No LLM, stdlib only. See CONTRIBUTING.md."""
import re
from dataclasses import dataclass

ERROR, WARN = "error", "warn"
OPENER_WINDOW = 40
PR_SECTION_MIN = 40
PR_SECTIONS = ("What changed", "How tested", "What could go wrong")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    std: str
    severity: str
    message: str


def check_purpose_opener(path, text):
    head = text.splitlines()[:OPENER_WINDOW]
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
