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

# Check days since last commit
LAST_COMMIT_DATE=$(git log -1 --format="%ct" 2>/dev/null)
NOW=$(date +%s)

if [ -n "$LAST_COMMIT_DATE" ]; then
  DAYS_SINCE=$(( (NOW - LAST_COMMIT_DATE) / 86400 ))
else
  DAYS_SINCE=999
fi

# Only warn if last commit is more than 1 day old, or if there's existing history suggesting divergence
if [ "$DAYS_SINCE" -ge 1 ]; then
  echo ""
  echo "⚠️  BRANCH CHECK: You're on '${CURRENT_BRANCH}' (last commit ${DAYS_SINCE}d ago). The prompt suggests new work."
  echo "Consider creating a feature branch before making changes:"
  echo "  git checkout -b feature/<short-description>"
  echo "Proceed on '${CURRENT_BRANCH}' only if this is intentional."
fi

exit 0
