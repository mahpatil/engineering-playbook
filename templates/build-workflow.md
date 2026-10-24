<!-- build-workflow.md -->

# Claude Code + Context OS Workflow (macOS, Java + TypeScript, VS Code, Ghostty)

This is an efficient workflow to use terminal, IDE and claude code together. This document describes a practical setup to recreate the workflow:

- macOS
- Ghostty terminal
- Java backend
- TypeScript frontend
- VS Code as IDE
- Claude Code as the “Context OS” and primary assistant

The core philosophy: **Claude is the planner/brain, VS Code is the editor/hands, Ghostty is the execution engine.**


## 1. Overall Physical Layout

On macOS, arrange your workspace roughly as:

- Left: **Ghostty** – long‑running servers, builds, test commands.
- Center: **VS Code** – single main window for backend + frontend code.
- Right: **Claude Code** – 3–4 long‑lived terminals with clear roles.

Avoid multiple IDE windows; treat VS Code as a single “surface” for both Java and TypeScript.


## 2. Claude Code Terminals and Roles

Create 3–4 Claude Code terminals and keep them persistent. Name and use them like this:

- `#1 – Build & Backend`  
  For Java backend implementation, tests, and backend‑focused reasoning.

- `#2 – Frontend & UX`  
  For TypeScript/React/Vue/etc., UI flows, and client‑side concerns.

- `#3 – Architecture / Docs`  
  For higher‑level design, trade‑offs, architecture decisions, and documentation.

- `#4 – Context OS / State`  
  For managing YAML state, process, session summaries, and tool pruning.

At the start of using each terminal, give Claude a short description of its role and your stack so it can stay focused.


## 3. Ghostty + VS Code + Claude Interaction Model

Use each tool with a narrow, clear responsibility:

- **Ghostty** (real shell)
  - Start/stop backend servers and frontend dev servers.
  - Run tests, linters, build commands.
  - Call small `tools/*.sh` scripts (see below).

- **VS Code** (single main window)
  - Open and edit project files for backend and frontend.
  - Navigate based on Claude’s instructions (“Open `src/main/java/...`”, “Open `src/components/LoginForm.tsx`”).
  - Keep extensions minimal: language servers and essentials, not heavy AI integrations.

- **Claude Code**
  - Plans work, writes/edits code snippets, generates tests, suggests commands.
  - You copy/paste code between Claude and VS Code as needed.
  - You run commands in Ghostty (or via simple scripts) instead of letting Claude directly manipulate your environment.


## 4. Creating the Context Folder and YAML State

Add a `context/` directory to your repository to hold your “Context OS” state:

- `context/`
  - `project.yaml`
  - `backend.yaml` (optional)
  - `frontend.yaml` (optional)
  - `sessions.yaml`

Start small; expand only as needed.

### 4.1 Example: context/project.yaml

```yaml
name: customer-portal
stack:
  backend: java-spring
  frontend: typescript-react
constraints:
  - must follow zero-trust principles for auth
  - must be observable (metrics, logs, traces)
goals:
  - id: G1
    description: Implement secure login + session management
    status: in_progress
  - id: G2
    description: Add customer dashboard with account summary
    status: todo
next_actions:
  - "Backend: finalize login controller and service"
  - "Frontend: hook login form to backend API"
  - "Add integration tests for login flow"
