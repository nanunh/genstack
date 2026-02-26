# Code Generation — Deep Dive

This document covers the full technical detail of how GenStack generates projects, modifies code, and uses AST analysis internally.

---

## Table of Contents

1. [Generation Pipeline](#1-generation-pipeline)
2. [MCP Tools](#2-mcp-tools)
3. [Code Assistant & Intent Detection](#3-code-assistant--intent-detection)
4. [AST System](#4-ast-system)
5. [AST Caching](#5-ast-caching)
6. [AST-Guided Code Modification](#6-ast-guided-code-modification)
7. [Token Tracking](#7-token-tracking)
8. [File-Based Generation](#8-file-based-generation)

---

## 1. Generation Pipeline

### Entry Point
`POST /api/generate` → `services/project_generator.py::create_project_with_mcp_streaming()`

### Step-by-step

```
User prompt
    │
    ▼
Build system prompt
  - Embed user's technology requirements verbatim
  - Attach full MCP tool schemas (names, descriptions, input_schema)
  - Enforce strict rules: respond only with JSON, honour exact tech stack
    │
    ▼
Claude API call (streaming, temperature=0.1, max_tokens=50000)
  - Model: claude-sonnet-4-5-20250929
  - Response streams chunk-by-chunk and is accumulated
    │
    ▼
Extract JSON from response
  - Try to find ```json ... ``` block first
  - Fall back to finding outermost { ... } in the response
  - Parse into a project_plan dict
    │
    ▼
Execute MCP calls sequentially
  - project_plan["mcp_calls"] is an ordered list
  - Each entry: { "tool": "...", "parameters": {...}, "reasoning": "..." }
  - Results are collected into a files[] list and dependencies{} dict
    │
    ▼
Post-processing
  - Auto-generate package.json if npm deps declared but file missing
  - Auto-generate requirements.txt if pip deps declared but file missing
  - Auto-generate README.md if not already created
    │
    ▼
Assign project ID (UUID4), sanitise project name
Save to disk: generated_projects/<name>_<id>/
Register in projects_store (in-memory)
Record token usage
    │
    ▼
Return ProjectResponse to caller
```

### System Prompt Design

The system prompt is the primary driver of generation quality. Key constraints enforced:

- **JSON-only output** — Claude must return a single valid JSON object, no prose.
- **Technology fidelity** — If the user says "Flask + plain HTML/CSS/JS", the prompt explicitly forbids Jinja templates, React, etc.
- **MCP tool awareness** — The full tool registry (names + schemas) is injected so Claude knows exactly what calls it can make.
- **Low temperature (0.1)** — Keeps output deterministic and well-structured.

---

## 2. MCP Tools

MCP (Model Context Protocol) tools are the mechanism Claude uses to build a project. Rather than returning free-form code, Claude returns a **plan** of tool calls. The backend executes each call.

### Tool Registry (`services/mcp_tools.py`)

| Tool | Purpose |
|---|---|
| `create_file` | Create any file with specified path and full content |
| `analyze_requirements` | Analyse requirements and suggest structure (informational, no file written) |
| `add_dependency` | Declare an npm or pip dependency (written to package.json / requirements.txt at the end) |
| `create_new_file` | Create a new file in an existing project (enhanced variant, writes to disk immediately) |
| `update_existing_file` | Replace content of an existing file, with a backup created first |
| `delete_file` | Remove a file from the project on disk and from the in-memory store |
| `add_feature` | Declarative feature annotation (no direct file write — used for planning context) |
| `explain_code` | Return an AST-driven explanation of a file (for the code assistant) |
| `run_project` | Declare how to run the project (port, command) — informational |
| `deploy_to_server` | Trigger SSH deployment via `ssh_deployment` service |
| `check_server_status` | Check if a deployed app is running on a remote server |
| `stop_deployment` | Stop a PM2-managed deployment on a remote server |

### Tool Execution Flow

```
execute_mcp_tool(tool_name, parameters)
    │
    ├── create_file         → returns { type: "file_created", path, content }
    ├── analyze_requirements→ returns { type: "requirements_analyzed", suggestion }
    ├── add_dependency      → returns { type: "dependency_added", package_manager }
    ├── run_project         → returns { type: "project_execution_planned" }
    └── deploy_*/check_*/stop_* → delegated to ssh_deployment service

execute_enhanced_mcp_tool(tool_name, parameters, project_id)  [used by code assistant]
    ├── create_new_file     → writes file to disk + adds to project store + AST cache
    ├── update_existing_file→ creates backup, writes new content to disk + store
    ├── delete_file         → removes from disk + store
    └── explain_code        → runs AST parser on file, returns structured explanation
```

---

## 3. Code Assistant & Intent Detection

### Entry Point
`POST /api/projects/{id}/enhanced-code-assistant` → `services/code_assistant.py::detect_user_intent_and_respond()`

### Intent Detection

Before any code modification, the assistant classifies the user message as either:
- **INFORMATION** — user wants an explanation, overview, or description
- **CODE_MODIFICATION** — user wants to change, add, fix, or delete code

This is done with a fast Claude call (`max_tokens=50`, `temperature=0.1`) returning exactly one word.

```
User message
    │
    ▼
Intent classification call to Claude
    │
    ├── "INFORMATION"  → handle_information_request()
    │       - Sends project file list + AST summary to Claude
    │       - Returns descriptive explanation, no code changes
    │
    └── "CODE_MODIFICATION" → process_intelligent_code_request_with_dynamic_ast()
            - Full modification pipeline (see below)
```

### Code Modification Pipeline

```
process_intelligent_code_request_with_dynamic_ast(project_id, user_message)
    │
    ▼
Load AST summary for the project
  (all files already parsed and cached — instant lookup)
    │
    ▼
Generate MCP modification plan with AST context
  - Sends AST summary (file count, function count, class count, per-file data)
    alongside user request and MCP tool schemas to Claude
  - Claude returns a JSON plan: list of mcp_calls targeting specific files
    │
    ▼
Execute each mcp_call
    │
    ├── update_existing_file
    │       → get current file content from store
    │       → apply_targeted_modification_with_caching()  [AST-guided diff]
    │       → write modified content to disk + store
    │
    ├── create_new_file
    │       → if content provided: use it directly
    │       → else: call Claude to generate file content
    │       → write to disk + store
    │       → refresh AST cache for the new file
    │
    └── analyze_requirements
            → informational, no file changes
    │
    ▼
Aggregate token usage across all sub-calls
Record with global_token_manager (project_id tagged)
    │
    ▼
Return EnhancedCodeAssistantResponse
  { affected_files, new_files, changes_summary, mcp_calls_made, token_usage }
```

---

## 4. AST System

The AST system gives Claude structural understanding of code instead of treating it as plain text. This enables precise modifications (e.g. "add a parameter to this function") without rewriting unrelated code.

### Components

| File | Class | Role |
|---|---|---|
| `multiLanguageASTParser.py` | `DynamicTreeSitterManager` | Loads and manages Tree-sitter parsers per language |
| `multiLanguageASTParser.py` | `MultiLanguageASTProcessor` | Parses code and extracts structure |
| `ast_cache_manager.py` | `ASTCacheManager` | Persists parsed AST data as JSON on disk |
| `enhanced_ast_modifier.py` | `DynamicASTModifier` | Applies code modifications using cached AST |

### Language Support

The parser supports 25+ languages mapped from file extensions:

| Category | Languages |
|---|---|
| Web | JavaScript, TypeScript, TSX, HTML, CSS, SCSS, SASS, Less |
| Backend | Python, Java, Kotlin, Scala, C, C++, C#, PHP, Ruby, Go, Rust, Swift |
| Functional | Haskell, OCaml, F#, Clojure, Erlang |
| Config/Other | JSON, YAML, TOML, Markdown, SQL, Bash |

**Parser priority:**
1. Python files → native `ast` module (most accurate)
2. All other supported languages → Tree-sitter via `tree-sitter-languages` package
3. Unsupported or failed languages → regex-based fallback parser

### What the Parser Extracts

For each file, the parser returns:

```json
{
  "language": "python",
  "total_lines": 120,
  "functions": [
    { "name": "create_user", "line": 14, "args": ["username", "password"] }
  ],
  "classes": [
    { "name": "UserManager", "line": 30, "methods": ["__init__", "get_user"] }
  ],
  "imports": ["from fastapi import FastAPI", "import bcrypt"],
  "variables": ["SECRET_KEY", "DB_URL"],
  "exports": []
}
```

### AST Summary

`MultiLanguageASTProcessor.get_project_summary()` aggregates across all files:

```json
{
  "total_files": 12,
  "total_functions": 47,
  "total_classes": 8,
  "total_lines": 1840,
  "languages": { "python": 8, "javascript": 3, "html": 1 },
  "files": [ ... per-file AST data ... ]
}
```

This summary is injected into the system prompt when Claude generates a modification plan, giving it full awareness of the existing codebase structure.

---

## 5. AST Caching

Parsing with Tree-sitter on every request would be slow. `ast_cache_manager.py` caches parse results as JSON on disk.

### Cache Structure

```
ast_cache/
└── <project_name>_<project_id>/
    ├── app.py.json
    ├── routes/auth.py.json
    └── static/app.js.json
```

Each `.json` file contains the serialised `FileASTInfo` for that source file:

```json
{
  "file_path": "routes/auth.py",
  "language": "python",
  "last_modified": 1708900000.0,
  "functions": [...],
  "classes": [...],
  "imports": [...],
  "variables": [...],
  "total_lines": 160
}
```

### Cache Invalidation

Cache entries are invalidated by comparing the file's `last_modified` timestamp against the cached value. If the file has changed since the cache was written, it is re-parsed automatically on next access.

### Cache Lifecycle

| Event | Action |
|---|---|
| File created (by code assistant) | `refresh_file_ast()` called immediately |
| File modified (by code assistant) | `refresh_file_ast()` called after write |
| AST summary requested | Load from cache; re-parse any stale entries |
| `DELETE /api/projects/{id}/ast-cache` | Clears all cache files for that project |
| `POST /api/projects/{id}/refresh-ast` | Force re-parse all files for that project |

---

## 6. AST-Guided Code Modification

`DynamicASTModifier.apply_targeted_modification_with_caching()` is the core of intelligent code editing.

### Flow

```
File content + user request
    │
    ▼
Load cached AST for this file
  - Identifies functions, classes, line numbers
    │
    ▼
Build targeted modification prompt
  - Include: file content, AST structure, user request
  - Claude is told exactly which functions/classes exist and their line numbers
  - Instruction: modify only what is necessary, preserve everything else
    │
    ▼
Claude generates modified file content
  - Streaming call, max_tokens=4000
  - Extracts code block from response (strips markdown fencing if present)
    │
    ▼
Smart syntax validation
  - Detect common errors (misplaced return, missing braces)
  - Apply rule-based fixes before returning
    │
    ▼
Return { success, modified_content, changes[], parser_used, token_usage }
```

### Why AST Matters for Modifications

Without AST context, Claude would need to re-read entire files and might introduce regressions. With AST context:

- Claude knows the exact line number of the function to modify
- It can target a specific method without touching others
- Class hierarchies and import statements are visible, preventing broken references
- The modification prompt is more specific, so output is more accurate with fewer tokens

---

## 7. Token Tracking

Every Claude API call records token usage via `TokenUsageManager`.

### Data Captured Per Operation

```python
@dataclass
class TokenUsage:
    operation_id: str       # UUID
    timestamp: str          # ISO 8601
    operation_type: str     # "project_generation" | "code_assistant" | "file_generation" | "mcp_planning"
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_estimate: float    # Based on Claude Sonnet pricing
    project_id: Optional[str]
```

### Storage

Token records are stored as JSON files under `token_usage/` (git-ignored):

```
token_usage/
├── token_usage.json       # Global rolling log
└── project_usage.json     # Per-project aggregates
```

### Cost Estimation

Cost is calculated using Claude Sonnet pricing at the time of each call. The formula:

```
cost = (input_tokens / 1_000_000 * input_price) + (output_tokens / 1_000_000 * output_price)
```

### Token Breakdown in Code Assistant

For a single code assistant request, multiple Claude calls may occur:

| Phase | Claude Call | Purpose |
|---|---|---|
| Intent detection | 1 call, ~50 tokens | Classify INFORMATION vs CODE_MODIFICATION |
| MCP plan generation | 1 call, ~2000–8000 tokens | Generate modification plan with AST context |
| Per-file modification | 1 call per file | Apply targeted changes to each file |
| New file generation | 1 call per new file | Generate content for brand-new files |

All token costs across phases are summed and recorded as a single `code_assistant` operation.

---

## 8. File-Based Generation

`POST /api/generate/files` → `create_project_from_files_streaming()`

This follows the same pipeline as prompt-based generation with one difference: instead of a blank slate, the system prompt includes the content of uploaded files.

### Process

1. User uploads a ZIP or multiple files
2. Files are extracted, content is read (text files up to 2000 bytes are included in full; larger files are truncated to 1000 chars)
3. A summary of all files (path, size, type, content) is embedded in the system prompt
4. Claude is asked to produce an **improved** version of the project, not just a copy
5. The same MCP tool execution pipeline runs as in normal generation
6. The result is a new project in `generated_projects/` — the originals are not modified

### Analysis Only

`POST /api/analyze/files` runs the same file reading and summarisation step but stops before calling Claude for generation. It returns metadata and structure analysis only — useful for previewing what was uploaded before committing to a full generation.
