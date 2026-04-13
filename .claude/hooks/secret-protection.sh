#!/bin/bash
# PreToolUse hook: blocks reads/searches of secret/credential files
# Exit 2 to block the tool call with a message to Claude.

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)

# Extract the relevant path/command depending on tool
case "$TOOL_NAME" in
  Read)
    TARGET=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
    ;;
  Bash)
    TARGET=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    ;;
  Glob)
    TARGET=$(echo "$INPUT" | jq -r '(.tool_input.pattern // "") + " " + (.tool_input.path // "")' 2>/dev/null)
    ;;
  Grep)
    # Check both the search path/glob AND the pattern itself (catches: grep "password" .)
    GREP_PATH=$(echo "$INPUT" | jq -r '(.tool_input.path // "") + " " + (.tool_input.glob // "")' 2>/dev/null)
    GREP_PATTERN=$(echo "$INPUT" | jq -r '.tool_input.pattern // ""' 2>/dev/null)
    TARGET="$GREP_PATH"
    # Also check if someone is grepping FOR secret-looking content
    SECRET_SEARCH_TERMS=("password" "passwd" "secret" "api.key" "api_key" "private.key" "token" "credential" "auth.token" "access.key" "bearer")
    LOWER_GREP_PATTERN=$(echo "$GREP_PATTERN" | tr '[:upper:]' '[:lower:]')
    for term in "${SECRET_SEARCH_TERMS[@]}"; do
      if echo "$LOWER_GREP_PATTERN" | grep -qE "^${term}$|^${term}[[:space:]=]|=${term}"; then
        echo "⛔ BLOCKED: Grep pattern '$GREP_PATTERN' looks like a search for sensitive credentials." >&2
        echo "Searching for hardcoded secrets is not permitted. Use a secret scanner tool instead." >&2
        exit 2
      fi
    done
    ;;
  *)
    exit 0
    ;;
esac

[ -z "$TARGET" ] && exit 0

LOWER_TARGET=$(echo "$TARGET" | tr '[:upper:]' '[:lower:]')

# Secret file patterns to block
SECRET_PATTERNS=(
  "\.env$" "\.env\." "\.env\.local" "\.env\.prod" "\.env\.dev" "\.env\.test"
  "id_rsa" "id_ed25519" "id_dsa" "id_ecdsa"
  "\.pem$" "\.key$" "\.p12$" "\.pfx$" "\.jks$" "\.keystore$" "\.crt$"
  "credentials\.json" "credentials\.yaml" "credentials\.yml"
  "service.account" "serviceaccountkey"
  "secrets\.yaml" "secrets\.yml"
  "aws-credentials" "\.netrc$" "htpasswd"
  "\.npmrc$" "\.pypirc$"
)

for pattern in "${SECRET_PATTERNS[@]}"; do
  if echo "$LOWER_TARGET" | grep -qE "$pattern"; then
    FILENAME=$(basename "$TARGET" 2>/dev/null || echo "$TARGET")
    echo "⛔ BLOCKED: '$FILENAME' matches a sensitive file pattern ('$pattern')." >&2
    echo "This file may contain secrets, credentials, or private keys. Do not read it directly." >&2
    echo "If you need values from this file, ask the user to provide them explicitly." >&2
    exit 2
  fi
done

exit 0
