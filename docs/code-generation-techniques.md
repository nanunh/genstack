# From Token to Tree: The Full Stack of Code Generation Techniques

> How a language model goes from predicting the next character to reliably generating an entire working codebase — and why each step in that journey exists.

---

The core idea of this document is simple: **every technique in modern AI code generation is a layer that constrains or structures the raw, probabilistic output of the one below it.** Each layer exists because the layer beneath it has a specific, well-defined failure mode. Understand the failure mode, and the next layer's purpose becomes obvious.

We'll walk the stack from the bottom up.

---

## Layer 0 — Next-Token Prediction: The Primitive

At the very bottom, there is no "code generator." There is a function that takes a sequence of tokens and returns a probability distribution over the next token.

That's it. That's the whole model.

```
P(next token | all previous tokens)
```

The transformer architecture — attention heads, feed-forward layers, residual connections — is the machinery that learns this function from hundreds of billions of examples. The *attention mechanism* is the key insight: rather than treating all prior tokens equally, it learns which ones are relevant for predicting the next one. The word `return` near the top of a function is more relevant to what comes next than the import statement fifty lines above it.

In practice, the model computes a score over its entire vocabulary (say, 100,000 tokens) at each step and samples from that distribution. Two parameters shape the sample:

- **Temperature** — a divisor applied to the scores before softmax. Low temperature (e.g. 0.1) sharpens the distribution: the top token wins almost every time. High temperature (e.g. 1.0) flattens it: the model takes more risks. Think of it as the **confidence dial** — turn it down when you want reliable structure, turn it up when you want creative variation.
- **Top-p / top-k** — truncate the tail of the distribution before sampling. The model assigns a probability to all ~100,000 tokens at every step — most of them vanishingly small. **Top-k** keeps only the K highest-probability tokens and throws the rest out. **Top-p (nucleus sampling)** is smarter: instead of a fixed count, you set a probability budget. Walk down the ranked list — highest first — and keep adding tokens until their cumulative probability hits your threshold (e.g. 0.95). Everything below gets zeroed out.

  Concretely, if the distribution at one step looks like this:

  ```
  `function`   → 60%
  `const`      → 20%
  `return`     → 10%
  `class`      → 5%
  ... (99,996 other tokens sharing the remaining 5%)
  ```

  With top-p = 0.95 you stop at `class` — four tokens, 95% of the mass. The 99,996-token tail is cut entirely. You sample from just those four. Without it, every one of those weird tail tokens has a non-zero chance of firing. Over hundreds of tokens in a generated function those misfires accumulate. Top-p makes them impossible while preserving real choice between legitimately plausible options.

  Temperature and top-p work together: temperature *reshapes* the whole distribution (flatter or sharper), top-p *truncates* it after reshaping. In practice you set both — temperature for confidence, top-p to cut the long weird tail.

This layer alone can produce impressive-looking code. The model has seen so much source code in training that "what token comes after `def authenticate(token, db):`" is a question it can answer well.

> **The failure mode — and why Layer 1 is needed**
>
> The sampler has no memory of structural commitments it made three tokens ago. It opened a `{` and by the time it's fifty tokens in, it has forgotten the brace is unclosed. It started an `if` block and drifted into prose. The output is *locally coherent* — each token makes sense given the last few — but *globally broken* — the structure collapses at scale.
>
> Think of writing code while being allowed to look back at only the last sentence you wrote. You'd produce fluent sentences. You'd produce terrible code.
>
> **You need something that steers the sampler itself — not just hopes it stays valid.**

---

## Layer 1 — From Tokens to Structured Tokens: Decoding Strategies

Layer 0 gives you tokens — a raw stream sampled one at a time from a probability distribution. Layer 1 gives you *structured* tokens — the same stream, but now constrained so the sequence as a whole conforms to a shape. The primitive hasn't changed; what's changed is that each token is now sampled with awareness of what the whole output is supposed to look like.

The question is: how do you enforce that structure without discarding the model's generative power?

The answer is to intervene before sampling happens — at the point where the model has computed raw scores for every token but hasn't yet converted them to probabilities.

A quick note on terminology: the model doesn't produce probabilities directly. It produces raw numbers called **logits** — one per token in the vocabulary — where higher means "more likely." A softmax function then converts those logits into a proper probability distribution (all values between 0 and 1, summing to 1). The logit stage is the last moment you can reach in and adjust scores before the distribution is finalised and the sample is drawn. This is why it matters: change a logit and you change the probability. Zero out a logit and that token becomes impossible.

Intervening at the logit level means reshaping those raw scores — before softmax, before sampling — to steer the output toward what you want.

**Greedy decoding** is the simplest strategy: always pick the highest-probability token. Fast, deterministic, but brittle. It commits to the first path it sees and can't recover from a locally-reasonable-but-globally-bad choice. Like a GPS that picks the first route it finds and ignores traffic.

**Beam search** keeps multiple candidate sequences in parallel — the top-N at each step — and prunes the worst ones as it goes. It produces better outputs than greedy for short sequences but becomes computationally expensive at the length of real code files. Most production LLM inference doesn't use it.

**Logit biasing** is more surgical: you directly add or subtract from specific token scores before sampling. Want to force the model to follow a `function` keyword with an identifier and not a brace? Suppress the brace token at that position. This is how early "JSON mode" implementations worked — bias against tokens that would break JSON syntax.

**Grammar-constrained decoding** is the principled version of logit biasing. You define a formal grammar (BNF or similar) for your target structure, and at each decoding step you compute *which tokens are valid continuations under that grammar* and mask everything else to zero probability. The model can only emit tokens that keep the output parse-valid. Tools like [Outlines](https://github.com/outlines-dev/outlines) and [LMQL](https://lmql.ai/) implement this. llama.cpp has it built in for local models.

The result: structurally valid output, guaranteed, regardless of what the model's weights would have preferred.

> **The failure mode — and why Layer 2 is needed**
>
> Decoding strategies can guarantee that your token stream is syntactically valid — a well-formed string. But downstream systems can't act on free-form text. They need *structured data* — a string with a guaranteed shape that code can traverse without guessing. JSON is still a string, but it's a string where you know exactly where to find every value: `response["files"][0]["path"]` either works or throws. No hunting, no guessing, no regex. The structure is the contract. A function that receives the model's output needs to extract file paths, code content, dependency names, and execution order — not hunt through a paragraph of English to find them.

"Parsing prose" means writing fragile string-extraction code: regex to find a filename, `split("```")` to extract a code block, `strip()` calls to clean up surrounding text. It works until the model changes its phrasing slightly — "here is the file" vs "I've created the file" — and your extractor silently returns nothing. The pipeline breaks not because the model was wrong, but because your parser didn't anticipate that sentence structure.
>
> A syntactically valid response that says "Sure! Here's how I'd approach this project..." is useless to a code execution pipeline, even if every character is technically legal.
>
> **You need the model's output to be typed, machine-readable data — not just well-formed text.**

---

## Layer 2 — From Structured Tokens to Typed Data: Schema-Enforced Output

Layer 1 gives you structured text — a string you *can* parse. Layer 2 gives you typed data — an object you don't *need* to parse because the structure is already navigable. The difference is the same as between a raw JSON string and a deserialised dataclass or struct: same information, but one of them your code can traverse by key, index, and type without any string manipulation at all.

This layer is about enforcing a schema on the model's output so that what comes back maps directly onto the types your program already speaks.

JSON mode — now standard in most model APIs — is grammar-constrained decoding with a fixed grammar: the JSON specification. The model emits tokens that, when decoded, are always valid JSON. No post-processing, no regex extraction, no "try to find the `{` somewhere in the response."

But you can go further. Give the model a JSON *schema* — declare that the output must have a `files` array where each element has a `path` string and a `content` string — and constrain the decoding to match it. The model can't emit a response that violates the shape you declared.

In a code generation pipeline, this unlocks the **plan-as-data pattern**. Instead of asking the model to directly write code, you ask it to return a machine-executable plan:

```json
{
  "mcp_calls": [
    { "tool": "create_file", "parameters": { "path": "models.py", "content": "..." } },
    { "tool": "create_file", "parameters": { "path": "routes/auth.py", "content": "..." } },
    { "tool": "add_dependency", "parameters": { "package": "bcrypt" } }
  ]
}
```

Your backend iterates this array and executes each call deterministically. The AI produced the *intent*. The machine performs the *action*.

Think of it as casting molten metal. The metal is still molten — the model is still sampling token by token from a probability distribution, nothing about that process has changed. But you've clamped a mold around the pour. The tokens flow into the schema's slots (`"tool"`, `"path"`, `"content"`) and when generation stops, what you have isn't a stream anymore — it's a solid, typed object with addressable fields. Same underlying process, completely different thing on the other side.

> **The failure mode — and why Layer 3 is needed**
>
> Structured output gives you a valid, typed object. But valid structure with wrong *content* is still broken. If the model decides your "Flask REST API" should use React for the frontend because it saw that pattern often in training, you'll get a perfectly valid JSON plan for the wrong project.
>
> The model will fill the schema with whatever it finds most probable given the training data — which may have nothing to do with what *you* asked for.
>
> Imagine handing a contractor a standard work order form (great — now the paperwork is legible) but not writing down what you actually want built. They'll fill it with the most common job they've seen.
>
> **You need to control what the model reasons about before it starts generating — the prompt is the only lever you have.**

---

## Layer 3 — Prompt Engineering: The Context Contract

The model's weights don't change between requests. The only thing you control is what you put in the context window. This layer is about making that context do real work.

**Why the prompt and not mid-stream corrections?** Mid-stream steering does exist — you can bias logits at specific steps, force-inject tokens into the sequence, or stop generation mid-way, append new context, and restart. Token injection works like grabbing the wheel briefly: you force `authenticate` instead of `auth` at the exact step it's about to diverge, and the model conditions all future tokens on your correction. Stop-inject-restart is the coarser version — stop after the plan is generated, inspect it, inject a correction ("actually Postgres not MySQL"), and resume. This is essentially what multi-turn chat does.

But the fundamental constraint is that the model is autoregressive — it only looks *backward*, never forward. It can't revise tokens it has already emitted. Each token becomes permanent context the moment it's sampled. You can steer what's *coming* but you can't undo the wake. Mid-stream corrections are either coarse (stop and re-prompt) or require knowing exactly which token to intercept before it fires — which for open-ended generation is hard to predict.

The prompt is therefore the primary lever because it's the one moment *before* any tokens are committed where you have full control at zero cost.

Think of the system prompt as a **type contract for the generation** — not just instructions, but constraints that narrow the model's solution space before the first token is sampled.

A well-engineered system prompt for code generation does several things simultaneously:

**Verbatim requirement embedding.** If the user said "Flask + plain HTML/CSS/JS", that phrase goes into the prompt verbatim. Paraphrasing it to "a Python web application with a simple frontend" is lossy — the model's paraphrase of your paraphrase will drift further still, and by generation time you might get Jinja templates or a React scaffold. Preserve the signal exactly.

**Explicit prohibition.** Don't just say what to do — say what *not* to do. "Do not use Jinja templates. Do not use React. Do not use any CSS framework." The model has strong priors from training; you need to override them with explicit constraints, not just hope the positive instruction wins.

**Schema injection.** Paste the full JSON output schema and example into the prompt. The model will pattern-match against it. This is the in-context equivalent of a function signature.

**Few-shot examples.** One concrete example of input → output calibrates the model's distribution more reliably than three paragraphs of prose instructions. It's showing, not telling.

**Context as working memory.** The model has no persistent state between calls. Everything it needs to know — existing files, declared dependencies, project structure — must be in the prompt. The context window *is* the working memory.

When the prompt is precise enough, you don't need to steer mid-stream at all — the ship turns by itself. Low temperature means the model picks the highest-probability token at almost every step. If the prompt has shaped the probability landscape correctly, the highest-probability token *at every step* is already the right one. The model isn't exploring — it's following the channel you cut for it.

This is why prompt engineering is a real engineering discipline, not just "write clearer sentences." You're not writing instructions for a human who will reason about them. You're sculpting a probability landscape that a sampler will walk down, one token at a time. Every word shifts that landscape. The goal is a landscape with one deep valley — the output you want — and steep walls on all sides. Get that right, and mid-stream corrections become unnecessary.

> **The failure mode — and why Layer 4 is needed**
>
> Even with a perfect prompt, you're asking the model to plan, generate, reason about file dependencies, and handle edge cases all in a single pass. That's a lot to hold in one stochastic step — and when it goes wrong, it goes wrong *everywhere at once*.
>
> Worse: you can't retry just the broken part. If `routes/auth.py` was generated incorrectly, you have to regenerate the whole response. If a dependency was declared in the middle of the plan and the rest of the plan depends on it, a single bad decision mid-stream corrupts everything that follows.
>
> This is the "god function" problem applied to generation: too many responsibilities in one call. The failure modes are entangled.
>
> **You need to separate the act of reasoning about what to do from the act of doing it.**

---

## Layer 4 — Plan-Then-Execute: Separating Reasoning from Action

This is one of the most important architectural ideas in reliable AI systems, and it maps directly to a pattern every backend engineer has used: the **command pattern** or, more precisely, the **query planner**.

A database query planner doesn't run your SQL directly. It parses the query, builds an execution plan — a tree of operations with estimated costs and chosen indexes — and hands that plan to the execution engine. The planner *thinks*. The engine *acts*. They are separate, with a typed intermediate representation between them.

Plan-then-execute for code generation works the same way:

**Phase 1 (stochastic):** Ask the model to reason about the request and produce a structured plan. The output is a JSON array of tool calls with explicit ordering and reasoning. The model is doing the hard thinking here — dependency resolution, file structure decisions, technology choices — but it's *only* producing a plan, not executing anything.

**Phase 2 (deterministic):** Your backend iterates the plan and executes each step. Each step is atomic: create a file, add a dependency, write content. If step 4 fails, you know exactly which step failed. You can inspect it, fix it, and retry just that step. Nothing else was affected.

The plan itself becomes an **intermediate representation** — like a compiler's IR between source code and machine code. It's human-readable, debuggable, serialisable, and replayable. You can log it, diff it, version it.

Ordering in the plan also matters and becomes explicit. `models.py` must be created before `routes/auth.py` that imports from it. The model, reasoning about the plan holistically, can express this dependency correctly. An execution engine that gets the ordered list just follows it.

> **The failure mode — and why Layer 5 is needed**
>
> Plan-then-execute works beautifully for generating new code on a blank slate. But most real work isn't greenfield generation — it's *modification*. You have an existing codebase and you want to add a field, fix a bug, refactor a function.
>
> When you apply plan-then-execute to modification, the plan says "update `auth.py`" and the execution step regenerates the *entire file* from the model's imagination. The model has no structural awareness of what was in that file. It will re-generate something that looks similar — but it will silently drop the edge case you added last week, rename a variable inconsistently, or slightly change a function signature that three other files depend on.
>
> This is the **full-file rewrite trap**: technically correct in isolation, subtly broken in context.
>
> Imagine asking a junior engineer to "update the `processPayment` function." They delete the whole file, rewrite it from memory, and hand it back. The function works. Everything that called it, doesn't.
>
> **You need structural awareness of what already exists before you touch it.**

---

## Layer 5 — AST-Guided Modification: Structural Code Editing

Every layer so far has been about improving how you generate text. This layer is about recognising that **code is not text** — it's a tree — and using that structure to make generation surgical rather than sweeping.

An Abstract Syntax Tree (AST) is what you get when you parse source code through a grammar. The raw string `def authenticate(token, db):` becomes a `FunctionDefinition` node with an `identifier` child (`authenticate`) and an `arguments` child containing two `Parameter` nodes. Every construct in the language — imports, classes, loops, expressions — becomes a typed node with known children and known line numbers.

The shift this enables: instead of telling the model "here is `auth.py`, please update the authenticate function," you tell it:

> "Function `authenticate` starts at line 42. Its parameters are `[token, db]`. It calls `verify_jwt` at line 45 and `db.get_user` at line 48. Modify only this function. Do not touch anything else in the file."

The model's attention is now focused on a twelve-line region with explicit structural context. It knows what it's modifying, where it is, and what it depends on. The probability of it accidentally changing the wrong thing collapses.

This approach has three parts working together:

**Structural lookup before generation.** Before any LLM call, parse the file with Tree-sitter, extract the target function/class/node, and record its exact line range. You are doing a `querySelector` on the code, not a `grep`. You get a typed handle, not a line number you guessed.

**Context-injected prompt construction.** Build the modification prompt using the AST data: file summary, function inventory, line numbers, argument lists, call sites. The model receives the minimum context needed to make the right change — no noise, no distraction, lower token cost, higher accuracy.

**Post-generation validation.** After the model returns modified code, run a lightweight rule-based pass: check brace balance, catch misplaced `return` statements, verify the function signature hasn't drifted. This isn't a full parser — it's a sanity filter that catches the most common generation errors before they reach disk.

The result is a hybrid: the model still generates the actual code text (you keep its generative power), but AST structure acts as a precision guide throughout. It's the difference between asking someone to "fix the fourth paragraph" of a document versus asking them to "fix the part that says climate change is fake" — specificity changes the outcome.

> **What comes after Layer 5**
>
> AST-guided modification still relies on the model to produce the final changed text of a function. The next frontier — not yet mainstream in production systems — is **pure structural patching**: the model emits a typed diff (`insertBefore(ReturnStatement in processData, console.log(...))`) and a deterministic engine applies it directly to the AST, no free-form code generation involved.
>
> This would be the last gap closed: generation becomes fully replayable, auditable, and immune to formatting drift. The model describes *what change to make*; the engine *makes it*. No text involved.
>
> That's the direction the field is heading.

---

## The Stack in One View

```
Layer 5 — AST-guided modification
          Structural handles on existing code.
          Without it: plan-execute rewrites whole files, causes silent regressions.
              ▲
Layer 4 — Plan-then-execute
          Separates stochastic reasoning from deterministic action.
          Without it: generation and side-effects are tangled; failures are global.
              ▲
Layer 3 — Prompt engineering
          Controls what the model reasons about before it generates.
          Without it: valid structure, wrong content.
              ▲
Layer 2 — Structured output
          Typed, machine-readable data instead of text.
          Without it: downstream code can't act on the response.
              ▲
Layer 1 — Decoding strategies
          Steers the sampler toward structurally valid token sequences.
          Without it: locally fluent, globally broken output.
              ▲
Layer 0 — Next-token prediction
          The primitive. Everything builds on this.
```

Each layer is a response to a specific failure mode. Remove any one of them and the failure mode it was built to solve surfaces directly in your output.

That's not accidental — it's the only honest way to build reliable systems on top of probabilistic foundations.

---

*~15 min read · Covers: transformer decoding, grammar-constrained generation, structured output, prompt design, plan-then-execute, AST-guided modification*
