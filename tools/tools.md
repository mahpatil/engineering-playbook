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

---

## 🍺 Homebrew Packages

After installing Homebrew on Desktop, install the following tools:

### **Node.js**
```sh
brew install node
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

```

### **Ohmyzsh**
```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

```

---

## 🤖 Ollama
Install Ollama for running local LLMs inside WSL.  
(Use the Linux installation instructions from the official Ollama site.)

---

## AI Tools Consumption and Costs

https://claudespend.live/
https://github.com/rtk-ai/rtk

---
