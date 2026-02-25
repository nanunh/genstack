# Contributing to StackGPT

Thank you for your interest in contributing to StackGPT! This document explains how to get involved.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Setting Up a Dev Environment](#setting-up-a-dev-environment)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Code Style](#code-style)
- [Project Structure](#project-structure)

---

## Code of Conduct

Be respectful, constructive, and inclusive. We welcome contributors of all experience levels.

---

## Ways to Contribute

- Report bugs via GitHub Issues
- Suggest new features or improvements
- Fix open issues and submit Pull Requests
- Improve documentation
- Write tests

---

## Reporting Bugs

Before opening a new issue, please search existing issues to avoid duplicates.

When reporting a bug, include:

1. **What you did** — steps to reproduce
2. **What you expected** — the expected behavior
3. **What happened** — the actual behavior (paste error messages/logs)
4. **Environment** — OS, Python version, MySQL version
5. **Screenshots** — if the bug is visual

> Never include your `.env`, API keys, or database credentials in a bug report.

---

## Suggesting Features

Open a GitHub Issue with the label `enhancement` and describe:

- The problem you are trying to solve
- Your proposed solution
- Any alternatives you considered

---

## Setting Up a Dev Environment

### 1. Fork and clone

```bash
git clone https://github.com/your-username/stackgpt.git
cd stackgpt
```

### 2. Create a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your Anthropic API key and MySQL credentials
```

### 5. Start MySQL and initialize the database

Make sure MySQL is running, then start the server once — tables are created automatically:

```bash
uvicorn server:app --host 0.0.0.0 --port 5000 --reload
```

### 6. Verify

Open `http://localhost:5000` in your browser. You should see the login page.

---

## Submitting a Pull Request

1. **Create a branch** from `main` with a descriptive name:
   ```bash
   git checkout -b fix/login-token-expiry
   git checkout -b feature/dark-mode
   ```

2. **Make your changes** — keep them focused and minimal. One PR = one concern.

3. **Test your changes** manually before submitting.

4. **Commit clearly:**
   ```bash
   git commit -m "fix: resolve JWT token expiry on page refresh"
   git commit -m "feat: add dark mode toggle to navbar"
   ```

   Commit message prefixes:
   | Prefix | Use for |
   |---|---|
   | `feat:` | New feature |
   | `fix:` | Bug fix |
   | `docs:` | Documentation only |
   | `refactor:` | Code restructuring, no behavior change |
   | `test:` | Adding or updating tests |
   | `chore:` | Maintenance (deps, config, etc.) |

5. **Push and open a PR:**
   ```bash
   git push origin your-branch-name
   ```
   Then open a Pull Request on GitHub against the `main` branch.

6. **Fill in the PR description** — explain what the change does and why.

---

## Code Style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use descriptive variable and function names
- Keep functions focused — one responsibility per function
- Use type hints where practical

### JavaScript / HTML / CSS

- Use consistent 4-space indentation
- Prefer `const` / `let` over `var`
- Keep inline styles out of HTML where possible — use CSS classes

### General

- Do not commit `.env`, `keys/`, `generated_projects/`, or `token_usage/`
- Do not commit real API keys, passwords, or certificates under any circumstances
- Keep PRs small and focused — large PRs are harder to review

---

## Project Structure

```
stackgpt/
├── server.py                  # Main FastAPI app & API routes
├── auth.py                    # JWT authentication
├── database.py                # MySQL connection & schema init
├── multiLanguageASTParser.py  # Tree-sitter AST parser
├── ast_cache_manager.py       # AST grammar cache
├── enhanced_ast_modifier.py   # AI-driven code modifier
├── token_usage_manager.py     # Token tracking & cost estimation
├── requirements.txt           # Python dependencies
├── static/                    # Frontend assets
└── .env.example               # Environment variable template
```

---

## Questions?

Open a GitHub Issue with the label `question` and we'll be happy to help.
