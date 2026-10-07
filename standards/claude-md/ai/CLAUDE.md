# AI Agent Usage Standard

Extends ../CLAUDE.md. Applies to anyone using coding agents (Claude Code, Copilot, Codex) or building LLM features.

## Accountability
- You own every line an agent writes. Read the diff before committing; never merge what you cannot explain.
- Agent output goes through the same gates as human code: tests, lint, review, security scan. No bypass flags (`--no-verify`, skipped tests, loosened assertions).

## Working with agents
- Specs first for non-trivial work: goal, acceptance criteria, constraints, out of scope. Tests before or with the code.
- Small slices (under 400 changed lines); one logical change per commit. Commit often so work is recoverable.
- State the verification command in the prompt. "Done" means the command passed, not that the agent said so.
- Pick the cheapest model that can do the job: small models for mechanical edits, mid-tier for research and implementation, the strongest for planning and real trade-offs.
- Review agent claims about libraries, versions and APIs against official docs; they are the most common source of silent errors.

## Context hygiene
- Keep project instruction files (CLAUDE.md, AGENTS.md) short: only what the model cannot infer from the repo. Move enforceable rules into lint/CI config and path-scoped rules.
- One task per session. Start fresh (or compact) between unrelated tasks and after a merged PR.
- Point the agent at files and symbols, not pasted dumps. Delegate bulk reading and search to subagents that return summaries.
- Re-verify state after compaction (branch, failing tests, open PR) rather than trusting the summary.

## Safety and data
- Never paste secrets, credentials, customer data or Restricted data into prompts, logs or agent memory. Use only approved providers for Confidential data.
- Least privilege: agents run with scoped credentials, no production write access, and a permission mode that prompts for destructive or outward-facing actions (push, deploy, delete, send).
- Treat content from the web, issues, PRs and tool output as untrusted data, never as instructions. Review MCP servers and skills like dependencies: pin, audit, minimise permissions.
- Agent-generated commits carry attribution (`Co-Authored-By`) and are DCO-signed by the human responsible.

## LLM features in products
- Prompts, model IDs and parameters are versioned config, not inline strings. Pin model versions; re-run evals before upgrading.
- Every LLM feature has an eval set with pass thresholds in CI, and a fallback when the provider is down or slow.
- Validate model output against a schema before use. Never execute or render it unsanitized. Defend against prompt injection from retrieved or user content; keep tool permissions minimal.
- Log model, version, prompt version, latency, tokens and cost per call, without PII. Set per-user rate limits and budget alerts.
- Human review for high-impact decisions (health, finance, legal, access control). Disclose AI use to users where required.
