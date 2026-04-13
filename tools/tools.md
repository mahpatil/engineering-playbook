# 🚀 Development Environment Setup

This README documents the steps and tools used to set up a modern development environment on **Mac** or **WSL (Windows Subsystem for Linux)** using **Debian**.

---

## 🧩 System Setup - WSL + Debian 

### **1. Update WSL to the latest version**
Make sure your system is running the newest WSL release.

### **2. Install Debian**
```sh
wsl --install debian
```

### **3. Start Debian**
Launch from the Start Menu or run:
```sh
wsl -d debian
```

---

## 🛠️ Tools to Install

### **VS Code** / **Zed**
Install VS Code or **Zed** and use the **Remote – WSL** extension to work inside Debian.
Themes: Monokai color theme.
File Icon Theme: Minimual (CodeOSS)

---

## 🍺 Homebrew Packages

After installing Homebrew on Desktop, install the following tools:

### **Node.js**
```sh
brew install node nvm
```

### **Python 3**
```sh
brew install python3
```

### **OpenJDK (latest)**
```sh
brew install openjdk
brew install gradle
brew install jenv #if using multiple java versions
```

### **Tools**
```sh
brew install opencode gemini-cli claude-code
brew install gh # GitHub CLI for managing repos, issues, PRs
brew install kubectl
```
**Utilities**: wget, yarn, terraform, jq, yq, gradle, tree, sqllite, httpie (or postman), tig (text view git)

### **Ohmybash**
OhMyBash or OhMyZsh is useful for liverly terminal
```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" #Mac
bash -c "$(curl -fsSL https://raw.githubusercontent.com/ohmybash/oh-my-bash/master/tools/install.sh)" #Windows DSL
```

---

## 🤖 Ollama
Install Ollama for running local LLMs inside WSL.  
(Use the Linux installation instructions from the official Ollama site.)

---

## 🪝 AI Hooks Installer

Install shared lifecycle hooks for Claude Code, OpenCode, and Codex in one step.

```sh
# From the repo root — interactive menu
./tools/install-hooks.sh

# Or non-interactive
./tools/install-hooks.sh claude    # Claude Code only
./tools/install-hooks.sh opencode  # OpenCode only
./tools/install-hooks.sh codex     # Codex only
./tools/install-hooks.sh all       # All three
```

| Hook | Trigger | Purpose |
|------|---------|---------|
| `secret-protection.sh` | Pre-tool | Blocks reads of `.env`, keys, certs, credentials |
| `branch-check.sh` | Prompt submit | Warns when starting new work on `main`/`master` |
| `post-work-reminder.sh` | Post-bash | Reminds to update README, tests, OpenSpec after builds |
| `pr-prompt.sh` | Post-bash | Prompts to raise a PR after `git commit` / `git push` |

Requires: `jq` (`brew install jq`)

---

## AI Tools Consumption and Costs

https://claudespend.live/
https://github.com/rtk-ai/rtk

---
