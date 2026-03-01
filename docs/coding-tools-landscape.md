# AI Coding Tools Landscape: Where GenStack Fits

A survey of the major AI coding tools — open and closed source — with their key technical differentiators, and an honest positioning of GenStack's AST-first approach relative to the field.

---

## How to Read This Document

Each tool is assessed on five axes:

| Axis | What It Means |
|---|---|
| **Edit mechanism** | How code changes are expressed and applied |
| **Context strategy** | How the tool understands your codebase |
| **Model backbone** | What LLM(s) power the tool |
| **Deployment model** | Where it runs and how you access it |
| **Key tech differentiator** | The single most distinctive technical choice |

---

## Closed Source Tools

### GitHub Copilot
**By:** Microsoft / GitHub
**Type:** IDE extension (VS Code, JetBrains, Vim, etc.)

| Axis | Detail |
|---|---|
| Edit mechanism | Inline ghost-text autocomplete + chat sidebar + multi-file edits ("Copilot Workspace") |
| Context strategy | Open files + repo index (embeddings via Copilot Enterprise), recent edits |
| Model backbone | OpenAI GPT-4o / o1 (Microsoft exclusive deal) |
| Deployment model | Cloud SaaS; Enterprise adds private model option |
| Key tech differentiator | **Scale and distribution** — deepest IDE integration, largest user base, GitHub repo context in Enterprise; Copilot Workspace adds a plan-then-edit agentic loop |

**Limitation:** Edits are text-based. No structural understanding of the code being changed.

---

### Cursor
**By:** Anysphere
**Type:** VS Code fork (standalone IDE)

| Axis | Detail |
|---|---|
| Edit mechanism | Inline edit (Ctrl+K), Composer (multi-file agent), chat |
| Context strategy | Repo-wide embeddings, `@file` / `@codebase` / `@docs` references, cursor rules (`.cursorrules`) |
| Model backbone | Claude 3.5/3.7 Sonnet, GPT-4o, o1, user-configured |
| Deployment model | Cloud SaaS; local model support via Ollama |
| Key tech differentiator | **Composer + repo embeddings** — multi-file agentic edits with semantic codebase search; shadow workspace for speculative edits before applying |

**Limitation:** Text-based diffs. Embedding-based retrieval can miss structural relationships.

---

### Windsurf (by Codeium)
**By:** Codeium
**Type:** VS Code fork (standalone IDE)

| Axis | Detail |
|---|---|
| Edit mechanism | "Flow" — a continuous agentic loop that observes your actions and acts proactively |
| Context strategy | Cascade context engine: file history, terminal output, linter errors, repo structure |
| Model backbone | Codeium's own models + frontier models (Claude, GPT-4o) |
| Deployment model | Cloud SaaS; enterprise on-premise |
| Key tech differentiator | **Flow paradigm** — the agent doesn't just respond to requests, it observes your editing session and acts on inferred intent; tighter feedback loop than request/response |

**Limitation:** Still text-based edits; proprietary context engine is a black box.

---

### Amazon Q Developer (formerly CodeWhisperer)
**By:** AWS
**Type:** IDE plugin + CLI

| Axis | Detail |
|---|---|
| Edit mechanism | Inline autocomplete, chat, `/dev` agentic task mode |
| Context strategy | Open files + AWS service documentation + your AWS account context |
| Model backbone | Amazon's proprietary models |
| Deployment model | Cloud; enterprise customisation via private model fine-tuning on your codebase |
| Key tech differentiator | **AWS-native context** — knows your IAM policies, Lambda functions, CloudFormation stacks; can suggest code that matches your actual AWS environment |

**Limitation:** Weak outside the AWS ecosystem; edit quality lags behind Cursor/Copilot.

---

### Tabnine
**By:** Tabnine
**Type:** IDE plugin (all major IDEs)

| Axis | Detail |
|---|---|
| Edit mechanism | Inline autocomplete + chat |
| Context strategy | Local codebase indexing + team-shared model fine-tuning |
| Model backbone | Mix of own small models + GPT-4 for chat; private model training on your codebase |
| Deployment model | Cloud, on-premise, or fully local (air-gapped) |
| Key tech differentiator | **Privacy + team learning** — can be trained exclusively on your company's codebase, runs fully on-prem with no data leaving the network; GDPR/SOC2 focused |

**Limitation:** Smaller model capacity than frontier tools; less capable at complex multi-file tasks.

---

### JetBrains AI Assistant
**By:** JetBrains
**Type:** Built-in to all JetBrains IDEs

| Axis | Detail |
|---|---|
| Edit mechanism | Inline suggestions, chat, refactoring actions |
| Context strategy | **PSI (Program Structure Interface)** — JetBrains' own deep AST/semantic model of your code |
| Model backbone | JetBrains' own models + cloud LLMs; local via Ollama |
| Deployment model | JetBrains subscription; on-prem available |
| Key tech differentiator | **PSI integration** — JetBrains IDEs have always maintained a full semantic AST of your project (powering refactoring, find usages, type inference). AI Assistant is wired into this, giving it genuine structural understanding that other tools lack |

**Note:** This is the closest existing commercial tool to a true AST-first approach.

---

### Amp (by Sourcegraph)
**By:** Sourcegraph
**Type:** Terminal agent + IDE extension

| Axis | Detail |
|---|---|
| Edit mechanism | Agentic — reads files, runs commands, edits, iterates |
| Context strategy | Sourcegraph code graph (cross-repo symbol resolution) |
| Model backbone | Claude 3.7 Sonnet |
| Deployment model | Cloud SaaS (early access) |
| Key tech differentiator | **Code graph context** — Sourcegraph's underlying tech resolves symbols, definitions, and usages across repositories, giving the agent a richer structural map than embedding-based search |

---

## Open Source Tools

### Continue.dev
**Repo:** `continuedev/continue`
**Type:** VS Code / JetBrains extension

| Axis | Detail |
|---|---|
| Edit mechanism | Inline edit, chat, autocomplete |
| Context strategy | `@file`, `@codebase` (embeddings), `@docs`, `@terminal`, custom context providers via plugin API |
| Model backbone | Bring your own — any OpenAI-compatible endpoint, Ollama, Anthropic, etc. |
| Deployment model | Fully local or cloud; open protocol |
| Key tech differentiator | **Open context protocol** — the context provider system is extensible; you can write a plugin that injects any data (your AST, your DB schema, your test results) into the LLM context |

---

### Aider
**Repo:** `paul-gauthier/aider`
**Type:** CLI tool

| Axis | Detail |
|---|---|
| Edit mechanism | **Unified diffs** — model outputs standard diff format; Aider applies them precisely |
| Context strategy | **Repo map** — uses Tree-sitter to extract symbols (functions, classes, calls) across the entire repo and gives the LLM a compact structural map; only loads files the model asks for |
| Model backbone | Claude 3.7 Sonnet, GPT-4o, o1, DeepSeek (user-configured) |
| Deployment model | Local CLI |
| Key tech differentiator | **Tree-sitter repo map + diff-based edits** — the repo map is a genuine structural index (not embeddings); the diff format ensures edits are applied exactly where intended. Git-aware: every change is auto-committed |

**This is the closest OSS tool to GenStack's approach** — Aider uses Tree-sitter for *understanding* code structure, but still outputs *text diffs* for the actual edit. GenStack goes one step further by using AST for the modification itself.

---

### Cline
**Repo:** `cline/cline`
**Type:** VS Code extension

| Axis | Detail |
|---|---|
| Edit mechanism | Agentic loop — reads files, writes files, runs terminal commands, uses browser |
| Context strategy | Reads files on demand; no persistent index |
| Model backbone | Any (Claude, GPT-4o, DeepSeek, local via Ollama) |
| Deployment model | Local VS Code extension |
| Key tech differentiator | **Full OS-level agency** — can run shell commands, interact with a browser (via Playwright), read/write any file. MCP server support for extending capabilities. Most capable "do anything" open agent |

---

### Roo Code
**Repo:** `RooVetGit/Roo-Code`
**Type:** VS Code extension (Cline fork)

| Axis | Detail |
|---|---|
| Edit mechanism | Same as Cline + additional "modes" (Code, Architect, Ask, Debug) |
| Context strategy | Same as Cline |
| Model backbone | Any |
| Deployment model | Local VS Code extension |
| Key tech differentiator | **Boomerang tasks** — subtasks that spawn child agents with scoped context, then return results to the parent; enables structured multi-step orchestration |

---

### OpenDevin / OpenHands
**Repo:** `All-Hands-AI/OpenHands`
**Type:** Web UI + agent framework

| Axis | Detail |
|---|---|
| Edit mechanism | Agentic — bash, file editor, browser, Jupyter |
| Context strategy | Event stream (full history of all actions and observations) |
| Model backbone | Any (Claude, GPT-4o, local) |
| Deployment model | Docker (fully sandboxed); cloud hosted version |
| Key tech differentiator | **Sandboxed OS environment** — agent runs inside a Docker container with a real shell, browser, and Python kernel. Safe to let it run arbitrary commands. Designed for SWE-bench-style software engineering tasks |

---

### SWE-agent
**Repo:** `princeton-nlp/SWE-agent`
**Type:** Research agent / CLI

| Axis | Detail |
|---|---|
| Edit mechanism | Custom ACI (Agent-Computer Interface) — structured file viewer and editor designed to minimize LLM errors |
| Context strategy | File search, grep, targeted reads |
| Model backbone | GPT-4, Claude |
| Deployment model | Local / research |
| Key tech differentiator | **ACI design** — purpose-built interface optimised for LLMs (not humans). Compact file viewer shows line numbers in a format that reduces edit mistakes. Research origin means it's benchmarked rigorously on real GitHub issues |

---

### Plandex
**Repo:** `plandex-ai/plandex`
**Type:** CLI tool

| Axis | Detail |
|---|---|
| Edit mechanism | Plan-then-execute: builds a full edit plan across multiple files, then applies atomically |
| Context strategy | Explicit file loading; change diffs tracked across the plan |
| Model backbone | OpenAI (GPT-4o, o1) primarily |
| Deployment model | Local CLI + optional cloud sync |
| Key tech differentiator | **Pending changes buffer** — all proposed edits are staged in a buffer. You review the full plan before anything is applied to disk. Supports long-running multi-session tasks |

---

### Tabby
**Repo:** `TabbyML/tabby`
**Type:** Self-hosted AI coding server

| Axis | Detail |
|---|---|
| Edit mechanism | Inline autocomplete + chat |
| Context strategy | RAG over local codebase (embeddings) |
| Model backbone | Open models (StarCoder, CodeLlama, DeepSeek Coder) |
| Deployment model | Self-hosted (Docker); no data leaves your network |
| Key tech differentiator | **Self-hosted completions server** — designed as a drop-in replacement for Copilot with zero cloud dependency; enterprise-grade privacy with full control over the model |

---

### Cody (Sourcegraph)
**Repo:** `sourcegraph/cody`
**Type:** VS Code / JetBrains extension

| Axis | Detail |
|---|---|
| Edit mechanism | Inline edit, chat, commands |
| Context strategy | Sourcegraph code graph — cross-repo symbol search, definition/usage resolution |
| Model backbone | Claude 3.5 Sonnet (default), configurable |
| Deployment model | Cloud (Sourcegraph.com) or self-hosted Sourcegraph instance |
| Key tech differentiator | **Code graph context** — unlike embedding similarity search, the code graph resolves *exact* symbol relationships (who calls this function, where is this type defined, what does this import resolve to) |

---

### Goose (by Block)
**Repo:** `block/goose`
**Type:** CLI agent

| Axis | Detail |
|---|---|
| Edit mechanism | Agentic — file, shell, browser |
| Context strategy | On-demand file reads + MCP tool results |
| Model backbone | Claude 3.5/3.7 (default), configurable |
| Deployment model | Local CLI |
| Key tech differentiator | **MCP-first extensibility** — Goose is built around MCP as a first-class primitive; you extend it by adding MCP servers (databases, APIs, custom tools), making it a general-purpose OS agent, not just a coding tool |

---

### Sweep AI
**Repo:** `sweepai/sweep`
**Type:** GitHub App

| Axis | Detail |
|---|---|
| Edit mechanism | Opens PRs autonomously from GitHub issues |
| Context strategy | Repo search (embeddings + keyword), file reads |
| Model backbone | GPT-4, Claude |
| Deployment model | GitHub App (cloud) or self-hosted |
| Key tech differentiator | **GitHub-native async workflow** — you file an issue tagged `sweep:`, it opens a PR. No IDE needed. Designed for small, well-defined tasks rather than open-ended sessions |

---

## Summary Comparison Table

| Tool | Open? | Edit Mechanism | Context Strategy | AST Use | Unique Angle |
|---|---|---|---|---|---|
| GitHub Copilot | ✗ | Text autocomplete + multi-file agent | Embeddings + open files | None | Scale, distribution, GitHub integration |
| Cursor | ✗ | Text diff (multi-file) | Embeddings + rules | None | Repo embeddings + shadow workspace |
| Windsurf | ✗ | Text diff (agentic) | Session observation | None | Flow: proactive agent |
| Amazon Q | ✗ | Text autocomplete + chat | AWS account context | None | AWS-native environment context |
| Tabnine | ✗ | Text autocomplete | Team-trained local model | None | Privacy + on-prem fine-tuning |
| JetBrains AI | ✗ | Text suggestions | **PSI (full semantic AST)** | **Deep (PSI)** | AST-backed IDE intelligence |
| Amp | ✗ | Agentic text edits | Code graph (cross-repo) | Partial | Cross-repo symbol graph |
| Continue.dev | ✓ | Text diff | Pluggable context providers | None | Open protocol extensibility |
| Aider | ✓ | **Unified diffs** | **Tree-sitter repo map** | Read only | Structural repo map + git integration |
| Cline | ✓ | Agentic (full OS) | On-demand file reads | None | Full OS agency + MCP |
| Roo Code | ✓ | Agentic + modes | On-demand file reads | None | Boomerang subtask orchestration |
| OpenHands | ✓ | Agentic (sandboxed) | Event stream | None | Sandboxed Docker environment |
| SWE-agent | ✓ | Custom ACI | Grep + targeted reads | None | LLM-optimised interface design |
| Plandex | ✓ | Plan buffer → apply | Explicit file loading | None | Staged multi-file plan review |
| Tabby | ✓ | Text autocomplete | RAG embeddings | None | Self-hosted completions server |
| Cody | ✓ | Text diff | Code graph | None | Cross-repo symbol resolution |
| Goose | ✓ | Agentic | MCP tools | None | MCP-first extensibility |
| Sweep | ✓ | PR from issue | Embeddings + search | None | GitHub-native async workflow |
| **GenStack** | **✓** | **AST modification** | **Tree-sitter (25+ langs)** | **Write (modify via AST)** | **AST-first code generation + editing** |

---

## Where GenStack Sits

### The Core Differentiator

Every tool in this list — without exception — uses one of two edit strategies:

1. **Text-based edits** — the LLM outputs raw source code or diffs, which are applied as string operations
2. **Agentic file writes** — the agent calls a `write_file` or `str_replace` tool with new text content

**GenStack does neither.** Its `enhanced_ast_modifier.py` parses code to a Tree-sitter AST, applies modifications at the node level, and regenerates source from the modified tree. The edit target is a *syntax node*, not a *line range*.

### What This Enables

| Capability | Text-based tools | GenStack (AST-based) |
|---|---|---|
| Add a parameter to all call sites of a function | Error-prone, misses dynamic patterns | Exact — finds all `CallExpression` nodes by callee name |
| Rename a symbol safely | Regex-risky (renames strings, comments) | Precise — only renames `Identifier` nodes in scope |
| Wrap a function body in try-catch | Fragile indentation/bracket matching | Structural — inserts `TryStatement` node around `BlockStatement` |
| Extract a code block to a new function | Often breaks with complex nesting | Tree-aware — correctly handles nested scopes |
| Guarantee syntactically valid output | No — LLMs hallucinate syntax | Yes — regenerated from valid AST |
| Multi-language (25+ langs same API) | Each tool handles 1-2 languages natively | Yes — Tree-sitter grammar per language, unified query API |

### What Aider Gets Right (and GenStack Goes Further)

Aider is the most technically sophisticated OSS competitor. It uses Tree-sitter to build a **repo map** (a structural index of all symbols across the codebase) and feeds that to the LLM as context. This is genuinely better than embedding-based retrieval.

But Aider still *outputs unified text diffs* — the actual edit is a string operation. The Tree-sitter usage is read-only (for context), not write (for modification).

GenStack uses Tree-sitter for *both*:
- **Read** — understanding what's in each file (functions, classes, imports, exports)
- **Write** — making modifications at the AST node level, not the text level

### What JetBrains Gets Right

JetBrains' PSI is the most mature production example of AST-backed code intelligence. IntelliJ has always maintained a full semantic model of your project — that's what powers "find all usages", "rename symbol", and "extract method" refactors. JetBrains AI Assistant plugs into this.

The difference: JetBrains PSI is language-specific and IDE-bound. GenStack's Tree-sitter foundation is language-agnostic (25+ languages, same API) and server-side, meaning it works in any editor or CLI context.

### Positioning Summary

```
                        AST for editing?

                 NO                    YES
              ┌─────────────────────────────────────┐
    Text      │  Copilot, Cursor,                   │
    diffs     │  Windsurf, Aider*,                  │   (nothing here yet)
              │  Continue, Plandex                  │
              ├─────────────────────────────────────┤
    Agentic   │  Cline, OpenHands,                  │  GenStack
    file      │  Goose, Roo Code,                   │  JetBrains AI (PSI)
    writes    │  SWE-agent, Sweep                   │
              └─────────────────────────────────────┘

* Aider uses Tree-sitter for READ (context) but text diffs for WRITE (edits)
```

GenStack occupies a largely empty cell: **agentic code modification where the modification primitive is an AST operation, not a string replacement.**

---

## Gaps and Honest Limitations

| Gap | Notes |
|---|---|
| **No IDE integration** | GenStack is a web app / API server. Cursor and Copilot win on UX because they live inside the editor. |
| **Limited to generated projects** | Current scope is projects GenStack created. Importing arbitrary existing codebases is not yet supported. |
| **AST modification is hard** | Tree-sitter gives you read access easily; write/modify is significantly harder (node replacement, source regeneration). This is the moat but also the engineering challenge. |
| **No repo-wide symbol graph** | GenStack parses files on demand. It doesn't maintain a live cross-file symbol index the way Sourcegraph/Cody or JetBrains does. |
| **Benchmark coverage** | SWE-bench and similar benchmarks measure text-edit agents. AST-based agents aren't well-represented in current benchmarks. |

---

## Key Takeaway

The industry has converged on two patterns: *LLM outputs text → apply text patch* (Copilot, Cursor, Aider) and *LLM calls file-write tool → overwrite file* (Cline, OpenHands). Both treat the LLM as the source of code text.

GenStack's approach — *LLM drives AST operations → regenerate source* — is structurally different and closer to how professional refactoring tools (IntelliJ, Roslyn, jscodeshift) have always worked. The bet is that semantic precision, multi-language consistency, and guaranteed syntactic validity will matter more as agents tackle larger, longer-lived codebases.

---

*Last updated: March 2026*
