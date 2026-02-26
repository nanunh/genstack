# GenStack — App Overview

GenStack is an AI-powered full-stack project generator. Users describe an application in plain English and receive a complete, production-ready project with all necessary files, structure, and dependencies. A built-in AI code assistant allows further modifications through a chat interface.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| AI / LLM | Anthropic Claude API |
| AST Parsing | Tree-sitter (25+ languages) |
| Authentication | JWT, bcrypt |
| Database | MySQL 8.0+ |
| Deployment | Paramiko (SSH/SCP), PM2 |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Validation | Pydantic 2.x |

---

## Project Structure

```
genstack/
├── server.py                    # FastAPI app entry point
├── auth.py                      # JWT authentication
├── database.py                  # MySQL setup & schema init
├── models.py                    # Pydantic request/response models
├── store.py                     # In-memory state (projects, processes, chats)
├── multiLanguageASTParser.py    # Multi-language AST parser (Tree-sitter)
├── ast_cache_manager.py         # AST grammar caching
├── enhanced_ast_modifier.py     # AI-driven code modification via AST
├── token_usage_manager.py       # Token & cost tracking
│
├── routes/
│   ├── auth.py                  # Auth endpoints
│   ├── projects.py              # Project generation & management
│   ├── deployment.py            # SSH deployment endpoints
│   └── token_usage.py           # Token usage endpoints
│
├── services/
│   ├── project_generator.py     # Core project generation logic
│   ├── code_assistant.py        # AI code modification & intent detection
│   ├── mcp_tools.py             # MCP tool definitions
│   └── ssh_deployment.py        # SSH/SCP deployment manager
│
├── utils/
│   ├── file_ops.py              # File backup, load, save helpers
│   └── project_runner.py        # Project execution & process management
│
├── static/                      # Frontend (HTML, CSS, JS)
├── docs/                        # Documentation
├── tests/                       # Test suite
└── requirements.txt
```

---

## How Code Generation Works

When a user submits a prompt, the backend follows this pipeline:

1. **Prompt ingestion** — The user's natural language description is received by `POST /api/generate`.
2. **System prompt construction** — A detailed system prompt is built that embeds the user's technology requirements and the full list of available MCP tools with their schemas.
3. **Claude API call (streaming)** — The prompt is sent to Claude (`claude-sonnet-4-5`) with `temperature=0.1` and `max_tokens=50000`. The response streams back in real time.
4. **JSON plan parsing** — Claude responds with a structured JSON plan containing an ordered list of `mcp_calls` — each specifying a tool, parameters, and reasoning.
5. **MCP tool execution** — Each call in the plan is executed sequentially. The primary tool is `create_file`, which writes files with full content. Other tools handle dependencies (`add_dependency`), requirement analysis (`analyze_requirements`), and execution planning (`run_project`).
6. **Post-processing** — If `package.json` or `requirements.txt` are missing but dependencies were declared, they are auto-generated. A `README.md` is appended if not already created.
7. **Project storage** — All files are saved to disk under `generated_projects/<name>_<id>/` and registered in the in-memory `projects_store`.
8. **Token tracking** — Input and output token counts are extracted from the final message and recorded via `TokenUsageManager`.

For deeper details on each step, see [code-generation.md](./code-generation.md).

---

## Core Features

### 1. Project Generation
Users submit a natural language prompt. The backend calls Claude with MCP (Model Context Protocol) tools, which systematically create files and directory structure. Generation streams in real time so users see progress as it happens.

### 2. AI Code Assistant
A chat interface lets users modify generated projects through conversation — add features, fix bugs, refactor code, or ask for explanations. Intent is auto-detected and routed to the appropriate handler.

### 3. Multi-Language AST Support
Tree-sitter parses 25+ languages to give the AI structural understanding of code (functions, classes, variables) rather than treating it as plain text. Falls back to regex parsing for unsupported languages. Results are cached for performance.

### 4. Token Usage Tracking
Every API call is tracked — input tokens, output tokens, estimated cost. Data is stored per project and aggregated daily. Users can view a cost dashboard.

### 5. SSH Deployment
Projects can be deployed directly to a remote Linux server over SSH. The system packages the project, transfers it via SCP, installs dependencies, and manages the process with PM2. SSH connections can be tested before deploying.

### 6. Authentication
JWT-based auth with bcrypt password hashing. Users register and log in; protected endpoints require a Bearer token. Sessions and chat history are stored in MySQL.

### 7. Project History & Execution
Generated projects are saved to disk and reloaded on startup. Projects can be run directly from the web interface with real-time output streaming.

---

## API Summary

| Group | Base Path | Description |
|---|---|---|
| Auth | `/api/auth/` | Signup, login, logout, current user |
| Projects | `/api/projects/` | Generate, list, get, run, stop, download |
| Code Assistant | `/api/projects/{id}/` | Chat, enhanced assistant, history |
| AST | `/api/projects/{id}/` | File analysis, AST summary, cache management |
| Deployment | `/api/projects/{id}/deploy` | SSH deploy, test connection |
| Token Usage | `/api/token-usage/` | Per-project, summary, daily, cleanup |
| MCP | `/mcp/` | Tool execution, resource access, server info |

---

## Environment Variables

Key variables required in `.env` (see `.env.example`):

- `ANTHROPIC_API_KEY` — Claude API key
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` — MySQL connection
- `SECRET_KEY` — JWT signing secret
- `SSL_KEYFILE`, `SSL_CERTFILE` — Paths to SSL certificates (optional)

---

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values

# Run the server
uvicorn server:app --host 0.0.0.0 --port 8000
```
