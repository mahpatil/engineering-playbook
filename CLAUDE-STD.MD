<!-- Inspired by: https://www.humanlayer.dev/blog/writing-a-good-claude-md -->
# Purpose
<Define the what: purpose of the project and function of the different parts of the project>


# Architecture
<!-- Define how to build this map of the codebase

## Tech stack

## Code base
Project structure and map of the code base.
If using monorepos what are various apps/services in this.

WHAT: tell Claude about the tech, your stack, the project structure. Give Claude a map of the codebase. This is especially important in monorepos! Tell Claude what the apps are, what the shared packages are, and what everything is for so that it knows where to look for things

HOW: tell Claude how it should work on the project. For example, do you use bun instead of node? You want to include all the information it needs to actually do meaningful work on the project. How can Claude verify Claude's changes? How can it run tests, typechecks, and compilation steps?


1. Infrastructure lock. You are forbidden from modifying the environment, docker or database without user permission.

2. Immutable stack. You are forbidden from adding new dependencies unless the user gives permission.

3. Never downgrade. Never fix a bug by deleting a feature or downgrading the requirement (Claude code loves to half-ass things, especially when context runs dry).

4. Never downgrade the existing LLMs without the users permission (Claude code is notorious for this. Switching a Gemini 3.0-Pro to Gemini 1.5-Flash, sure, why not).

5. Never change the ports for backend or frontend.

6. Never delete existing database entries without user permission.

7. Plan -> Act. For any task involving >1 file or cross-stack logic (Frontend <-> Backend), you must outline your plan in bullet points and wait for confirmation.

8. Git Pull and Merge Protocol: Always pull and read before writing, use Edit instead of Rewriting, Run git diff safety net after changes.

9. When making the UI changes always conform to the existing design system.

10. End-to-end testing is required: You MUST NOT declare any task complete without thorough end-to-end testing. "It should work" is NOT acceptable

No rocket science. Root of the project should always have (1) Claude.md; (2) Spec.md; (3) Styleguide.md; (4) Compact.md.

# Code style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible (eg. import { foo } from 'bar')

# Workflow
- Be sure to typecheck when you’re done making a series of code changes
- Prefer running single tests, and not the whole test suite, for performance



Common bash commands
Core files and utility functions
Code style guidelines
Testing instructions
Repository etiquette (e.g., branch naming, merge vs. rebase, etc.)
Developer environment setup (e.g., pyenv use, which compilers work)
Any unexpected behaviors or warnings particular to the project
Other information you want Claude to remember
