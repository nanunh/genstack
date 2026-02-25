# StackGPT — AI-Powered Full-Stack Project Generator

StackGPT is an open-source web application that generates complete, production-ready full-stack projects from a single text prompt. Powered by Claude (Anthropic), it uses MCP (Model Context Protocol) tool integration to intelligently create, modify, and deploy multi-language codebases.

---

## Features

- **Prompt-to-Project** — Describe your app in plain English and get a complete project with all files generated
- **Multi-Language AST Parsing** — Understands and modifies code structure across Python, JavaScript, TypeScript, and more via Tree-sitter
- **AI Code Assistant** — Chat with the AI to add features, fix bugs, create/delete/modify files in your generated project
- **Token Usage Dashboard** — Tracks and estimates API cost per project and operation
- **User Authentication** — JWT-based signup/login with MySQL backend
- **SSH Deployment** — Deploy generated projects directly to a remote Linux server via SSH/SCP with PM2 support
- **Project History** — Browse and reload previously generated projects
- **File Upload & Analysis** — Upload existing code files for AI analysis and enhancement

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| AI | Anthropic Claude API (claude-sonnet) |
| AST Parsing | Tree-sitter |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Database | MySQL 8.0+ |
| Deployment | Paramiko (SSH), SCP, PM2 |
| Frontend | Vanilla HTML / CSS / JavaScript |

---

## Prerequisites

### 1. Python

Install **Python 3.10 or higher**:

- **Windows:** https://www.python.org/downloads/windows/
- **macOS:** https://www.python.org/downloads/macos/
- **Linux (Ubuntu/Debian):** https://docs.python-guide.org/starting/install3/linux/

Verify installation:
```bash
python --version
```

### 2. MySQL

Install **MySQL 8.0 or higher**:

- **Windows:** https://dev.mysql.com/downloads/installer/
- **macOS:** https://dev.mysql.com/downloads/mysql/
- **Linux (Ubuntu/Debian):** https://dev.mysql.com/doc/refman/8.0/en/linux-installation.html

Verify installation:
```bash
mysql --version
```

### 3. Anthropic API Key

Get your API key at: https://console.anthropic.com/settings/keys

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/stackgpt.git
cd stackgpt
```

### 2. Create a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set:

```env
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

DB_HOST=localhost
DB_PORT=3306
DB_NAME=stackgpt_db
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
```

---

## Database Setup

### Step 1 — Create a MySQL user (optional but recommended)

Log in to MySQL as root:

```bash
mysql -u root -p
```

Run the following SQL:

```sql
CREATE USER 'stackgpt_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON stackgpt_db.* TO 'stackgpt_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> Update `DB_USER` and `DB_PASSWORD` in your `.env` to match.

### Step 2 — Auto-initialize the database

The database and all required tables are **created automatically** the first time you run the server. No manual SQL import is needed.

Tables created on first run:
- `users` — stores registered user accounts
- `user_sessions` — stores active sessions
- `code_assistant_history` — stores per-project chat history

If you need to recreate the tables manually, you can trigger it by running:

```bash
python database.py
```

---

## Running the Server

```bash
uvicorn server:app --host 0.0.0.0 --port 5000 --reload
```

Then open your browser at:

```
http://localhost:5000
```

You will be greeted by the login/signup page. Create an account and start generating projects.

---

## Project Structure

```
stackgpt/
├── server.py                  # Main FastAPI application & all API routes
├── auth.py                    # JWT authentication helpers
├── database.py                # MySQL connection & table initialization
├── multiLanguageASTParser.py  # Tree-sitter multi-language AST parser
├── ast_cache_manager.py       # AST grammar cache manager
├── enhanced_ast_modifier.py   # AI-driven AST code modifier
├── token_usage_manager.py     # Token usage tracking & cost estimation
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── static/                    # Frontend (HTML, CSS, JS)
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── app.js
│   ├── auth.js
│   ├── styles.css
│   └── auth-styles.css
├── generated_projects/        # Runtime: AI-generated project output (git-ignored)
├── token_usage/               # Runtime: token usage data (git-ignored)
└── ast_cache/                 # Runtime: compiled AST grammars (git-ignored)
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `SERVER_URL` | No | Server base URL (default: `http://localhost:5000`) |
| `OUTPUT_DIR` | No | Generated projects directory (default: `generated_projects`) |
| `LOG_LEVEL` | No | Logging verbosity (default: `INFO`) |
| `DB_HOST` | Yes | MySQL host (default: `localhost`) |
| `DB_PORT` | No | MySQL port (default: `3306`) |
| `DB_NAME` | Yes | MySQL database name |
| `DB_USER` | Yes | MySQL username |
| `DB_PASSWORD` | Yes | MySQL password |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Copyright (c) 2026 River Transformation Hub
