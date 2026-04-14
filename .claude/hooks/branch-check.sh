#!/bin/bash
# UserPromptSubmit hook: suggests creating a feature branch when starting new work on main/master.
# Outputs a reminder to stdout (injected into Claude's context).

INPUT=$(cat)

PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
[ -z "$PROMPT" ] && exit 0

LOWER_PROMPT=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

# Keywords that suggest new/changed work
NEW_WORK_KEYWORDS=(
  "create" "add" "implement" "build" "feature" "new"
  "fix" "bug" "refactor" "update" "modify" "change"
  "improve" "support" "integrate" "setup" "configure" "migrate"
)

DETECTED=false
for kw in "${NEW_WORK_KEYWORDS[@]}"; do
  if echo "$LOWER_PROMPT" | grep -qw "$kw"; then
    DETECTED=true
    break
  fi
done

[ "$DETECTED" = "false" ] && exit 0

# Check current branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
[ -z "$CURRENT_BRANCH" ] && exit 0

LOWER_BRANCH=$(echo "$CURRENT_BRANCH" | tr '[:upper:]' '[:lower:]')

if [[ "$LOWER_BRANCH" != "main" && "$LOWER_BRANCH" != "master" && "$LOWER_BRANCH" != "develop" ]]; then
  exit 0
fi

echo ""
echo "⚠️  BRANCH CHECK: You're on '${CURRENT_BRANCH}'. The prompt suggests new work."
echo "Consider creating a feature branch before making changes:"
echo "  git checkout -b feature/<short-description>"
echo "Proceed on '${CURRENT_BRANCH}' only if this is intentional."

exit 0
