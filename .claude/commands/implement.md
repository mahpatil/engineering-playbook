<!-- // .claude/commands/implement.md -->
Using @REQUIREMENTS.md and @ARCHITECTURE.md, implement the requested change: "$ARGUMENTS".
- Create a plan, referencing impacted modules and patterns mandated in @PRINCIPLES.md.
- Make minimal, testable increments; write/extend tests per @TEST_STRATEGY.md.
- Preserve public API behavior unless REQUIREMENTS explicitly permit change.
- After edits, run the full validation pipeline. If failures occur, fix and rerun.
- Keep changes incremental and well-factored; add docstrings/Javadoc where appropriate
- Python: write/extend pytest tests close to changed modules
- Java: write/extend JUnit tests under `src/test/java`, use Mockito for external deps
