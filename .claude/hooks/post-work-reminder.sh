#!/bin/bash
# PostToolUse hook (Bash): after significant commands, reminds to update README, tests, and OpenSpec.
# Outputs reminders to stdout so Claude sees them as context.

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL_NAME" != "Bash" ] && exit 0

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null | tr '[:upper:]' '[:lower:]')
[ -z "$COMMAND" ] && exit 0

EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_response.exit_code // 0' 2>/dev/null)

# Only trigger on meaningful execution commands
TRIGGER_KEYWORDS=("test" "build" "run" "start" "serve" "lint" "deploy" "migrate" "generate" "compile")
TRIGGERED=false
for kw in "${TRIGGER_KEYWORDS[@]}"; do
  if echo "$COMMAND" | grep -qE "\b$kw\b"; then
    TRIGGERED=true
    break
  fi
done
[ "$TRIGGERED" = "false" ] && exit 0

# Skip very short or trivial commands (like `echo`, `ls`, `cat`)
TRIVIAL_COMMANDS=("echo " "ls " "cat " "pwd" "cd " "export " "which " "type " "alias")
for trivial in "${TRIVIAL_COMMANDS[@]}"; do
  if echo "$COMMAND" | grep -q "^$trivial"; then
    exit 0
  fi
done

echo ""
if [ "$EXIT_CODE" != "0" ]; then
  echo "⚠️  POST-WORK REMINDER (command exited with errors — fix first, then consider):"
else
  echo "✅ POST-WORK REMINDER (command succeeded — consider before closing out):"
fi

# README reminder — always relevant for feature/fix work
echo "  - [ ] README: Does documentation reflect this change? (new flags, usage, setup steps)"

# Tests reminder
if echo "$COMMAND" | grep -qE "(build|compile|generate|migrate|serve|deploy)"; then
  echo "  - [ ] TESTS: Are there tests covering this change? Run the test suite to verify."
fi

# OpenSpec/API spec reminder
if echo "$COMMAND" | grep -qE "(api|endpoint|schema|model|service|spec|openapi|swagger)"; then
  echo "  - [ ] OPENSPEC: Does the API/OpenSpec need updating? Check route signatures and request/response schemas."
fi

echo ""
exit 0
