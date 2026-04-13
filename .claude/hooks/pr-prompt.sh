#!/bin/bash
# PostToolUse hook (Bash): after a successful git commit or staging, prompts to raise a PR.
# Outputs a reminder to stdout so Claude sees it as context.

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL_NAME" != "Bash" ] && exit 0

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null | tr '[:upper:]' '[:lower:]')
[ -z "$COMMAND" ] && exit 0

EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_response.exit_code // 1' 2>/dev/null)
[ "$EXIT_CODE" != "0" ] && exit 0

# Only trigger on git commit or git push
IS_COMMIT=false
IS_PUSH=false
if echo "$COMMAND" | grep -qE "git commit"; then
  IS_COMMIT=true
fi
if echo "$COMMAND" | grep -qE "git push"; then
  IS_PUSH=true
fi

[ "$IS_COMMIT" = "false" ] && [ "$IS_PUSH" = "false" ] && exit 0

# Check git status to understand what's left
GIT_STATUS=$(git status --porcelain 2>/dev/null)
STAGED=$(git diff --cached --name-only 2>/dev/null)
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
LOWER_BRANCH=$(echo "$CURRENT_BRANCH" | tr '[:upper:]' '[:lower:]')

echo ""
if [ "$IS_PUSH" = "true" ]; then
  # After push — suggest creating PR
  echo "🚀 PR PROMPT: Branch '${CURRENT_BRANCH}' has been pushed."
  echo "  - [ ] Create a pull request: gh pr create --fill"
  echo "  - [ ] Add reviewers and link related issues if applicable."
elif [ "$IS_COMMIT" = "true" ]; then
  if [ -z "$GIT_STATUS" ] && [ -z "$STAGED" ]; then
    # All clean after commit — ready to push/PR
    echo "✅ PR PROMPT: Commit complete, working tree is clean on '${CURRENT_BRANCH}'."
    if [[ "$LOWER_BRANCH" != "main" && "$LOWER_BRANCH" != "master" ]]; then
      echo "  - [ ] Push and raise PR: git push -u origin ${CURRENT_BRANCH} && gh pr create --fill"
    else
      echo "  - [ ] Consider whether changes on '${CURRENT_BRANCH}' should be on a feature branch + PR instead."
    fi
  else
    # Commit done but uncommitted changes remain
    echo "✅ PR PROMPT: Commit made on '${CURRENT_BRANCH}'. Uncommitted changes still remain."
    echo "  - [ ] Commit remaining changes or stash them."
    echo "  - [ ] Then push and raise PR: git push -u origin ${CURRENT_BRANCH} && gh pr create --fill"
  fi
fi

echo ""
exit 0
