# genStack — AI-Powered Full-Stack Project Generator

genStack is an open-source web application that generates complete, production-ready full-stack projects from a single text prompt. Powered by **Anthropic Claude** or **Google Gemini** (your choice), it uses MCP (Model Context Protocol) tool integration to intelligently create, modify, and deploy multi-language codebases.

---

<details>
<summary>💰 Donate — Support this project</summary>
<br>

If you find this project useful, consider supporting it!

Scan the QR code below to donate via **UPI**:

<img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=upi%3A%2F%2Fpay%3Fpa%3D8778990202a%40kotak" alt="Donate via UPI" width="220"/>

<br>

**UPI ID:** `8778990202a@kotak`

</details>

---

## Quick Start (TL;DR)

```bash
git clone https://github.com/nanunh/genstack.git
cd genstack
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                               # fill in your API key + DB details
python3 generate_keys.py                           # generates SSL certificates
python3 server.py                                  # starts the server
```

Then open **https://localhost:8000** in your browser.
> On first visit you will see a browser security warning — click **Advanced → Proceed to localhost**. This is expected for self-signed certificates.

---

## LLM Provider Setup

genStack supports **Anthropic Claude** and **Google Gemini**. You only need one API key. Set the values in your `.env` file.

---

### Option A — Anthropic Claude

Get your API key at: https://console.anthropic.com/settings/keys

```env
# .env
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: override the default model (default: claude-sonnet-4-5-20250929)
# ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

genStack auto-detects Anthropic when `ANTHROPIC_API_KEY` is present.
No `LLM_PROVIDER` line needed.

**Recommended Anthropic models:**

| Model | ID | Best for |
|---|---|---|
| Claude Sonnet 4.5 (default) | `claude-sonnet-4-5-20250929` | Best balance of quality and speed |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Latest, highest quality |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | Faster and cheaper |

To switch model, add to `.env`:
```env
ANTHROPIC_MODEL=claude-sonnet-4-6
```

---

### Option B — Google Gemini

Get your API key at: https://aistudio.google.com/app/apikey

```env
# .env
GEMINI_API_KEY=AIzaSy-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: override the default model (default: gemini-2.0-flash)
GEMINI_MODEL=gemini-2.5-flash
```

genStack auto-detects Gemini when `GEMINI_API_KEY` is present (and no Anthropic key is set).
No `LLM_PROVIDER` line needed.

**Recommended Gemini models:**

| Model | ID | Best for |
|---|---|---|
| Gemini 2.5 Flash (recommended) | `gemini-2.5-flash` | Best quality, 65K output tokens |
| Gemini 2.0 Flash (default) | `gemini-2.0-flash` | Fast, 8K output tokens |
| Gemini 2.5 Pro | `gemini-2.5-pro` | Highest quality |

To switch model, add to `.env`:
```env
GEMINI_MODEL=gemini-2.5-flash
```

> **Note:** Use `gemini-2.5-flash` or `gemini-2.5-pro` for generating larger projects. The older `gemini-2.0-flash` has an 8 192-token output limit which can truncate complex projects.

---

### Option C — Force a specific provider

If you have both keys set, Anthropic takes priority by default.
To override, set `LLM_PROVIDER` explicitly:

```env
# Use Anthropic even if GEMINI_API_KEY is also present
LLM_PROVIDER=anthropic

# Use Gemini even if ANTHROPIC_API_KEY is also present
LLM_PROVIDER=gemini
```

---

### Complete .env examples

**Using Anthropic:**
```env
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-sonnet-4-6

DB_HOST=localhost
DB_PORT=3306
DB_NAME=stackgpt_db
DB_USER=stackgpt_user
DB_PASSWORD=your_db_password
```

**Using Gemini:**
```env
GEMINI_API_KEY=AIzaSy-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-2.5-flash
LLM_PROVIDER=gemini

DB_HOST=localhost
DB_PORT=3306
DB_NAME=stackgpt_db
DB_USER=stackgpt_user
DB_PASSWORD=your_db_password
```

**Using both keys (Anthropic active, Gemini as fallback option):**
```env
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSy-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_PROVIDER=anthropic   # switch to "gemini" any time without removing keys
```

---

## Features

- **Prompt-to-Project** — Describe your app in plain English and get a complete project with all files generated
- **Dual LLM Support** — Works with Anthropic Claude and Google Gemini; switch providers by changing one env variable
- **Multi-Language AST Parsing** — Understands and modifies code structure across Python, JavaScript, TypeScript, and more via Tree-sitter
- **AI Code Assistant** — Chat with the AI to add features, fix bugs, create/delete/modify files in your generated project
- **Token Usage Dashboard** — Tracks and estimates API cost per project and operation (provider-aware pricing)
- **User Authentication** — JWT-based signup/login with MySQL backend
- **SSH Deployment** — Deploy generated projects directly to a remote Linux server via SSH/SCP with PM2 support
- **Project History** — Browse and reload previously generated projects
- **File Upload & Analysis** — Upload existing code files for AI analysis and enhancement

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| AI (Anthropic) | Claude Sonnet 4.5 / 4.6 via `anthropic` SDK |
| AI (Gemini) | Gemini 2.0 / 2.5 Flash via `google-generativeai` SDK |
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

### 3. An LLM API Key

You need **one** of the following:

| Provider | Where to get it | Cost |
|---|---|---|
| Anthropic | https://console.anthropic.com/settings/keys | Pay-per-token |
| Google Gemini | https://aistudio.google.com/app/apikey | Free tier + pay-per-token |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/nanunh/genstack.git
cd genstack
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

### 4. Generate SSL Certificates

genStack runs over **HTTPS** and requires SSL certificate files in the `keys/` folder.
Run the included key generator to create self-signed certificates for local development:

```bash
python3 generate_keys.py
```

**What this does:**
- Generates an RSA 4096-bit private key → `keys/privkey.pem`
- Generates a self-signed X.509 certificate → `keys/fullchain.pem`
- Valid for 825 days (~2 years)
- Covers `localhost`, `127.0.0.1`, and `::1`

**Expected output:**
```
✅ SSL keys generated successfully!
  Private key : keys/privkey.pem
  Certificate : keys/fullchain.pem
  Valid until : 2028-06-01
```

> **Browser warning:** Self-signed certificates will trigger a security warning in your browser.
> Click **Advanced → Proceed to localhost (unsafe)** to continue. This is safe for local development.

> **Production use:** Replace `keys/privkey.pem` and `keys/fullchain.pem` with real certificates
> from [Let's Encrypt](https://letsencrypt.org/getting-started/) using certbot:
> ```bash
> sudo certbot certonly --standalone -d yourdomain.com
> sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem keys/privkey.pem
> sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem keys/fullchain.pem
> ```

### 5. Configure environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set your LLM provider key and database credentials. See the [LLM Provider Setup](#llm-provider-setup) section above for full examples.

Minimum required fields:
```env
# Pick ONE provider:
ANTHROPIC_API_KEY=sk-ant-...    # Anthropic Claude
# or
GEMINI_API_KEY=AIzaSy-...       # Google Gemini

# Database
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

Make sure you have completed all setup steps above (including `generate_keys.py`), then run:

```bash
python3 server.py
```

Then open your browser at:

```
https://localhost:8000
```

> **First-time browser warning:** Click **Advanced → Proceed to localhost** to bypass the
> self-signed certificate warning. This only appears once per browser session.

You will be greeted by the login/signup page. Create an account and start generating projects.

The startup log confirms which LLM provider is active:
```
LLM provider : gemini (model: gemini-2.5-flash)
```
or
```
LLM provider : anthropic (model: claude-sonnet-4-5-20250929)
```

---

## Project Structure

```
genstack/
├── server.py                  # FastAPI application entry point
├── generate_keys.py           # SSL key pair generator (run before server.py)
├── auth.py                    # JWT authentication helpers
├── database.py                # MySQL connection & table initialization
├── store.py                   # LLM client initialization & provider detection
├── models.py                  # Pydantic data models
├── multiLanguageASTParser.py  # Tree-sitter multi-language AST parser
├── ast_cache_manager.py       # AST grammar cache manager
├── enhanced_ast_modifier.py   # AI-driven AST code modifier
├── token_usage_manager.py     # Token usage tracking & cost estimation
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── services/
│   ├── llm_provider.py        # Unified Anthropic + Gemini streaming abstraction
│   ├── project_generator.py   # MCP-based project generation logic
│   ├── code_assistant.py      # AI code modification & chat logic
│   └── mcp_tools.py           # MCP tool definitions and execution
├── routes/                    # FastAPI route handlers
├── keys/                      # SSL certificates (git-ignored)
│   ├── privkey.pem
│   └── fullchain.pem
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

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | One of these two | — | Anthropic API key |
| `GEMINI_API_KEY` | One of these two | — | Google Gemini API key |
| `LLM_PROVIDER` | No | auto-detected | Force provider: `anthropic` or `gemini` |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-5-20250929` | Override Anthropic model |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Override Gemini model |
| `SERVER_URL` | No | `https://localhost:8000` | Server base URL |
| `OUTPUT_DIR` | No | `generated_projects` | Generated projects directory |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `DB_HOST` | Yes | `localhost` | MySQL host |
| `DB_PORT` | No | `3306` | MySQL port |
| `DB_NAME` | Yes | — | MySQL database name |
| `DB_USER` | Yes | — | MySQL username |
| `DB_PASSWORD` | Yes | — | MySQL password |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Copyright (c) 2026 River Transformation Hub
