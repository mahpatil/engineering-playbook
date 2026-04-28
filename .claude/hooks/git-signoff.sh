#!/usr/bin/env bash
# Intercepts git commit commands and injects -s (DCO sign-off) if missing.

input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command // ""')

# Only act on git commit commands
if ! echo "$cmd" | grep -qE '(^|[[:space:]])git[[:space:]]+commit'; then
  exit 0
fi

# Already signed off — nothing to do
if echo "$cmd" | grep -qE '[[:space:]](-s|--signoff)([[:space:]]|$)'; then
  exit 0
fi

# Inject -s immediately after 'git commit'
modified_cmd=$(echo "$cmd" | sed 's/\(git commit\)/\1 -s/')

echo "$input" | jq \
  --arg cmd "$modified_cmd" \
  '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      updatedInput: (.tool_input + {command: $cmd}),
      additionalContext: "git-signoff hook: injected -s (Signed-off-by: Mahesh Patil <maheshfinity@gmail.com>)"
    }
  }'
