# Spec: Contribution standards and deterministic PR gate

**Issue**: n/a
**Status**: Draft
**Date**: 2026-10-19
**NFR / API / Architecture**: not applicable (docs + CI tooling, no HTTP routes, no UI)

## Problem

Contributor PRs repeatedly draw the same review comments (tool assumptions, bloated or exhaustive configs, missing purpose openers, unlinked docs, broken examples). Reviews are slow and reviewers repeat themselves, and AI-generated filler is hard to spot. We need ten written standards and a zero-LLM automated check that gives feedback within a minute.

## Context

- `.github/workflows/validate.yml` only lints `README.md`; no PR-level content checks exist.
- `CONTRIBUTING.md` has a stale template and checklist that don't reflect the owner's actual review feedback.
- Source of the standards: owner comments on PRs #33, #34, #14 (see approved plan `~/.claude/plans/playful-sparking-phoenix.md`). Reference opener: `standards/detailed/observability/logs.md`.
- Python 3 stdlib only (no installs); the repo has no existing test harness.

## Acceptance Criteria

- [ ] `CONTRIBUTING.md` contains exactly the 10 one-line standards (per plan) and a table mapping each to "bot-checked" or "reviewer-checked"; the stale Review Process checklist is removed.
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` has What changed / How tested / What could go wrong headings and the standards checklist.
- [ ] `tools/contrib-check/check.py` implements the 14 checks in the plan table, each returning findings with file, line, standard id, severity (`error`/`warn`) and message.
- [ ] Given a changed `standards/**/*.md` lacking `What is`/`Why` H2s in its first 40 lines, the checker reports an error for S4.
- [ ] Given a yaml/hcl/tf/json fence over 20 lines, or one containing 2+ top-level resources, the checker reports an error for S5; any fence over 15 lines warns.
- [ ] Given a python fence calling `self.compensate(` with no definition in the fence, the checker warns (S5 syntax/undefined).
- [ ] Given added code lines over 500 (docs exempt), the checker errors for S6.
- [ ] Given a new standards file not referenced in `README.md`, the checker errors for S8.
- [ ] Given a PR body missing any of the three headings or with under 40 chars or `N/A` under one, the checker errors for S10.
- [ ] Heuristic checks (S1, S2, S3, S5 slop/syntax/fenced-share, S7, S9) only warn and never fail the job.
- [ ] `<!-- contrib-check: ignore Sx -->` suppresses that standard for the file and is listed in the summary; `templates/` and `references/` are exempt.
- [ ] `.github/workflows/contrib-check.yml` runs unit tests, then the checker diff-aware against `origin/<base>`, on `pull_request` opened/synchronize/edited, with read-only permissions and the PR body passed via env var only.
- [ ] Run against known-bad content (#33/#34/#14 diffs) it flags the known issues; against merged `observability/logs.md` and #37 it reports no errors.

## Technical Design

### Key Logic

- Pure functions: `check_<name>(path, text, ctx) -> list[Finding]`; a thin CLI collects changed files via `git diff --name-only --diff-filter=AM <base>...HEAD` and prints `file:line: [Sn] msg` plus `::error`/`::warning` annotations. Exit 1 only if any `error`.
- Fence parsing is a single pass over lines tracking language and length; shared by snippet checks.
- Term lists live in `tool-terms.txt` and `slop-terms.txt` (one per line, `#` comments) so they can be tuned without code changes.
- Heuristic checks keep false positives low by being warn-only; thresholds are constants at the top of `check.py`.

### Files

`CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/workflows/contrib-check.yml`, `tools/contrib-check/{check.py,tool-terms.txt,slop-terms.txt}`, `tools/contrib-check/tests/{test_check.py,fixtures/good,fixtures/bad}`.

## Test Scenarios

1. Each check has a passing and a failing fixture; assertion on standard id and severity.
2. Boundary: fence of exactly 15/20 lines passes, 16/21 flags; PR body of 39 vs 40 chars.
3. Pragma suppresses one standard only; exempt directories skipped.
4. PR-body parser handles CRLF, extra whitespace, and untouched template text.
5. CLI exit code: 0 with warnings only, 1 with any error; annotation format matches GitHub syntax.
6. Regression: `observability/logs.md` yields zero errors.

## Out of Scope

- Any LLM-based review (explicit non-goal, cost).
- Judging principle-before-tool (S1), alternatives (S3) and fit (S7) beyond heuristics; the reviewer confirms these.
- Branch-protection required-check wiring (repo setting, applied by owner after merge).
- Phase 2: auto-labelling PRs and a first-response comment bot.
- No UI exists for this repo, so no UI follow-up is needed.

## Open Questions

None. Defaults per plan (Python stdlib, warn-only heuristics). If code exceeds 500 lines, split into two PRs: docs + template, then checker + workflow.

## Implementation Notes

Follow plan order: docs commit, then tests-first per check, workflow last. DCO-signed conventional commits.
