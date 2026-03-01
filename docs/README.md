# GenStack Documentation

This directory contains technical documentation for the GenStack project. Start here to find the right doc for what you need.

---

## Documents

### [overview.md](./overview.md)
**Start here.** High-level overview of the entire GenStack system.

Covers: tech stack, project structure, how code generation works (pipeline summary), core features (generation, code assistant, AST, token tracking, SSH deployment, auth), API route groups, environment variables, and getting started.

---

### [code-generation.md](./code-generation.md)
**Deep technical reference** for how GenStack generates and modifies code.

Covers:
- Generation pipeline step-by-step (prompt → Claude → MCP execution → disk)
- Full MCP tool registry and execution flow
- Code assistant intent detection (INFORMATION vs CODE_MODIFICATION)
- AST system components, language support (25+ langs), and what the parser extracts
- AST cache structure, invalidation, and lifecycle
- AST-guided code modification flow (`DynamicASTModifier`)
- Token tracking data model and cost estimation
- File-based generation (`POST /api/generate/files`)

---

### [ast-intro.md](./ast-intro.md)
**Conceptual introduction to Abstract Syntax Trees** — useful background for understanding how GenStack's AST layer works.

Covers: what an AST is, the compilation pipeline (lexing → parsing → AST), anatomy of AST nodes, common node types, traversal and the visitor pattern, AST transformation, code generation, source maps, popular AST tools (Babel, Tree-sitter, ESLint, ts-morph, LibCST), CST vs AST, real-world applications (linting, formatting, transpilation, bundling, codemods, SAST), and why ASTs matter for agentic code systems.

*~10–15 min read.*

---

### [position-and-attention.md](./position-and-attention.md)
**Why token position determines whether the model uses your information** — how transformers read context, why attention works through selective leaning, and why information in the middle of a long prompt gets systematically ignored.

Covers: the parallel processing problem, attention and QKV mechanics (with the hiring pool analogy), multi-head attention as multiple companies reading one candidate pool, the invisible position problem, positional encoding approaches (absolute, RoPE, ALiBi), the U-shaped attention curve, the *Lost in the Middle* paper (Liu et al., 2023), and practical prompt design implications.

*~15 min read.*

---

### [code-generation-techniques.md](./code-generation-techniques.md)
**How code is actually generated** — a layered walkthrough of the techniques that power AI code generation, from transformer next-token prediction up to AST-guided modification.

Covers: next-token prediction and temperature, decoding strategies (greedy/beam/grammar-constrained), structured output and JSON schema enforcement, prompt engineering as a context contract, plan-then-execute as an IR pattern, AST-guided surgical modification. Each layer explains the failure mode of the previous one and why the next layer exists.

*~15 min read.*

---

### [coding-tools-landscape.md](./coding-tools-landscape.md)
**Competitive landscape and positioning** — a survey of AI coding tools and where GenStack fits.

Covers: analysis of 18 tools (Copilot, Cursor, Windsurf, Amazon Q, Tabnine, JetBrains AI, Aider, Cline, Roo Code, OpenHands, SWE-agent, Plandex, Tabby, Cody, Goose, Sweep, Amp, Continue.dev) across five axes (edit mechanism, context strategy, model backbone, deployment, key differentiator). Summary comparison table. GenStack's AST-first positioning. Honest gaps and a prioritised roadmap to close them.

---

## Quick Navigation

| I want to... | Go to |
|---|---|
| Understand what GenStack is | [overview.md](./overview.md) |
| Understand the generation pipeline | [overview.md § How Code Generation Works](./overview.md#how-code-generation-works) → [code-generation.md](./code-generation.md) |
| Understand MCP tools | [code-generation.md § MCP Tools](./code-generation.md#2-mcp-tools) |
| Understand the code assistant | [code-generation.md § Code Assistant](./code-generation.md#3-code-assistant--intent-detection) |
| Understand the AST layer | [code-generation.md § AST System](./code-generation.md#4-ast-system) |
| Learn what an AST is | [ast-intro.md](./ast-intro.md) |
| Understand how code generation techniques work | [code-generation-techniques.md](./code-generation-techniques.md) |
| See how GenStack compares to Cursor / Aider / Copilot | [coding-tools-landscape.md](./coding-tools-landscape.md) |
| See the product roadmap | [coding-tools-landscape.md § Closing the Gaps](./coding-tools-landscape.md#closing-the-gaps-a-roadmap) |
| Set up the project locally | [overview.md § Getting Started](./overview.md#getting-started) |
