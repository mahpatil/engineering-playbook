#!/bin/bash
# install-hooks.sh — install shared AI hooks to Claude Code, OpenCode, and/or Codex globally.
# Run from the repo root or tools/ directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
HOOKS_SRC="$REPO_DIR/.claude/hooks"

# Colours
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}  →${NC} $*"; }
success() { echo -e "${GREEN}  ✓${NC} $*"; }
warn()    { echo -e "${YELLOW}  ⚠${NC} $*"; }
error()   { echo -e "${RED}  ✗${NC} $*"; }
header()  { echo -e "\n${BOLD}${CYAN}$*${NC}"; }

# ── helpers ────────────────────────────────────────────────────────────────────

require_jq() {
  if ! command -v jq &>/dev/null; then
    error "jq is required but not installed. Install with: brew install jq"
    exit 1
  fi
}

copy_hooks() {
  local dest="$1"
  mkdir -p "$dest"
  for f in "$HOOKS_SRC"/*.sh; do
    cp "$f" "$dest/"
    chmod +x "$dest/$(basename "$f")"
    info "Copied $(basename "$f") → $dest/"
  done
}

# ── Claude Code ────────────────────────────────────────────────────────────────

install_claude() {
  header "Installing hooks for Claude Code"
  require_jq

  local claude_dir="$HOME/.claude"
  local hooks_dir="$claude_dir/hooks"
  local settings="$claude_dir/settings.json"

  copy_hooks "$hooks_dir"

  # Build the hooks JSON block
  local hooks_json
  hooks_json=$(cat <<EOF
{
  "UserPromptSubmit": [
    {
      "matcher": ".*",
      "hooks": [{ "type": "command", "command": "bash $hooks_dir/branch-check.sh" }]
    }
  ],
  "PreToolUse": [
    {
      "matcher": "Read|Bash|Glob|Grep",
      "hooks": [{ "type": "command", "command": "bash $hooks_dir/secret-protection.sh" }]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        { "type": "command", "command": "bash $hooks_dir/post-work-reminder.sh" },
        { "type": "command", "command": "bash $hooks_dir/pr-prompt.sh" }
      ]
    }
  ]
}
EOF
)

  # Create or merge into ~/.claude/settings.json
  if [ ! -f "$settings" ]; then
    echo '{}' > "$settings"
    info "Created $settings"
  fi

  # Merge hooks block (preserves existing keys, overwrites hooks section)
  local tmp
  tmp=$(mktemp)
  jq --argjson h "$hooks_json" '.hooks = ($h + (.hooks // {} | del(.UserPromptSubmit, .PreToolUse, .PostToolUse)))' "$settings" > "$tmp" && mv "$tmp" "$settings"

  success "Claude Code: hooks wired in $settings"
  echo -e "    ${YELLOW}Restart Claude Code for hooks to take effect.${NC}"
}

# ── OpenCode ───────────────────────────────────────────────────────────────────

install_opencode() {
  header "Installing hooks for OpenCode"

  local opencode_dir="$HOME/.config/opencode"
  local plugins_dir="$opencode_dir/plugins"
  local config="$opencode_dir/config.json"

  mkdir -p "$plugins_dir"

  # Copy .sh scripts
  copy_hooks "$plugins_dir"

  # Register in OpenCode global config
  if [ ! -f "$config" ]; then
    echo '{ "$schema": "https://opencode.ai/config.json", "permission": "allow" }' > "$config"
    info "Created $config"
  fi

  if command -v jq &>/dev/null; then
    local plugin_list
    plugin_list=$(ls "$plugins_dir"/*.sh 2>/dev/null | jq -R . | jq -s .)
    local tmp; tmp=$(mktemp)
    jq --argjson p "$plugin_list" '.plugin = $p' "$config" > "$tmp" && mv "$tmp" "$config"
    success "OpenCode: plugin list updated in $config"
  else
    warn "jq not found — manually add plugin paths to $config"
  fi

  echo -e "    ${YELLOW}Note: OpenCode runs .sh scripts as shell plugins. Restart OpenCode to reload.${NC}"
}

# ── Codex ──────────────────────────────────────────────────────────────────────

install_codex() {
  header "Installing hooks for Codex"

  local codex_dir="$HOME/.codex"
  local hooks_dir="$codex_dir/hooks"

  copy_hooks "$hooks_dir"

  # Codex reads instructions.md for system-level guidance
  local instructions="$codex_dir/instructions.md"
  if [ ! -f "$instructions" ]; then
    mkdir -p "$codex_dir"
    cat > "$instructions" <<'MD'
# Hooks

The following shell hooks are active in this session:

- **Secret protection**: Never read `.env`, credential, key, or certificate files directly.
- **Branch check**: Suggest creating a feature branch when starting new work on main/master.
- **Post-work reminder**: After builds/tests, check README, tests, and OpenSpec are up to date.
- **PR prompt**: After committing, suggest raising a pull request.
MD
    info "Created $instructions with hook guidance"
  else
    warn "Codex instructions.md already exists — review $instructions manually."
  fi

  success "Codex: hooks copied to $hooks_dir"
  echo -e "    ${YELLOW}Note: Codex does not have native hooks. The .sh files are available for manual use.${NC}"
}

# ── Menu ───────────────────────────────────────────────────────────────────────

show_menu() {
  echo -e "\n${BOLD}AI Hooks Installer${NC}"
  echo "─────────────────────────────────────────"
  echo "  Hooks source: $HOOKS_SRC"
  echo ""
  echo "  Which tools would you like to install hooks for?"
  echo ""
  echo "  1) Claude Code  (~/.claude/hooks + settings.json)"
  echo "  2) OpenCode     (~/.config/opencode/plugins)"
  echo "  3) Codex        (~/.codex/hooks)"
  echo "  4) All of the above"
  echo "  q) Quit"
  echo ""
  printf "  Choice [1-4/q]: "
}

# ── Entry point ────────────────────────────────────────────────────────────────

if [ ! -d "$HOOKS_SRC" ]; then
  error "Hooks directory not found: $HOOKS_SRC"
  error "Run this script from the repo root or tools/ directory."
  exit 1
fi

# Non-interactive mode via arg
case "${1:-}" in
  claude)   install_claude;  exit 0 ;;
  opencode) install_opencode; exit 0 ;;
  codex)    install_codex;   exit 0 ;;
  all)      install_claude; install_opencode; install_codex; exit 0 ;;
esac

# Interactive menu
while true; do
  show_menu
  read -r choice
  case "$choice" in
    1) install_claude ;;
    2) install_opencode ;;
    3) install_codex ;;
    4) install_claude; install_opencode; install_codex ;;
    q|Q) echo ""; info "Aborted."; exit 0 ;;
    *) warn "Invalid choice — enter 1, 2, 3, 4, or q." ;;
  esac
  echo -e "\n${GREEN}Done.${NC}"
  break
done
