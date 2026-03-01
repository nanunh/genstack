# How Language Models Actually Work: The Foundation for Understanding AI Code Generation

> A ground-up explanation of how transformers predict the next token, how they decide which parts of the context to pay attention to, and why that mechanism determines whether your prompt instructions get followed or silently ignored.

---

## 1 — The Foundation: Parallel Processing, Order, and Attention

### The parallel processing problem

Transformers read all tokens simultaneously — every word in the prompt lands at once, not left to right like a human reading a sentence. That parallelism is what makes them fast at scale. But it creates an immediate problem.

If everything is read at once with equal weight, word order disappears. "The cat sat on the mat" and "the mat sat on the cat" contain identical tokens. Without something that weighs which token matters for which prediction, the model would produce the same internal summary — the same list of numbers it uses to capture what a sequence means — for both sentences. Meaning collapses. Order becomes invisible.

### Attention as the solution

Before anything else: a transformer is a **next-token predictor**. That is its entire job. Given every token that has come before — the full prompt, plus anything it has already generated — it predicts the single most likely next token. Then it appends that token and predicts the next one. Then the next. One token at a time, left to right, until the response is complete. Everything else — the layers, the heads, the weight matrices — is machinery in service of making that one prediction well. Each of these will make complete sense by the end of this doc; for now just hold the shape: one job, one output, one token at a time.

So the question at every step is: *given everything before this point, which single token should come next?*

Start with this: the empty slot after "the cat sat on the" could be filled by any of the ~100,000 words the model knows. Mat. Dog. Parrot. Democracy. Semicolon. Every single one of them is always a candidate — the model never pre-selects or shortlists. The full vocabulary is always in play.

Here is how the winner emerges. The model looks back at all the previous words and leans on the ones that matter — "cat", "sat", "on" score high, the three instances of "the" are mostly noise. From that selective leaning it builds a picture of what the context means: *something a cat sat on, a surface, a location*. It then takes that picture and compares it against all 100,000 possible next words simultaneously. Whichever word's meaning is most aligned with that picture scores highest. This time it's "mat." That becomes the next token.

The direction matters: the context builds a picture first, then scores the vocabulary. The leaning goes *context → vocabulary*, not the other way around. The model does not look at each possible next word and ask "does this fit?" It builds a context summary and asks "what does this summary point toward?"

That selective leaning — done fresh for every single token the model generates, across every token in the context — is attention.

Back to the two sentences: with attention, the token "sat" issues a question. "Cat" and "mat" respond with their profiles. "Cat" (the subject doing the sitting) scores higher for predicting what sat. "Mat" (the object being sat on) scores lower. Swap the order and the scores flip. The two sentences now produce different representations. Order shapes scores. Scores shape output. Meaning is restored.

### QKV — the three roles every token plays

The attention mechanism works through three roles:

**Q (Query) — the job description.** The current position asks: *what am I looking for to make the right prediction here?* This is the seeker. It has a specific need.

**K (Key) — the resume.** Every prior token in the context advertises what it contains. Not passive storage — an active signal saying *here is what I offer*. The match between a Query and a Key produces the attention score: how much should this prior token influence the current prediction?

**V (Value) — the work output.** What the token actually contributes once selected. This is the critical part: V has no meaning until the Query that selected it defines the role. The same token hired by a different Query contributes differently. Same person, different job, different output. The score (Q·K) decides *whether* a token is selected; the Value decides *what flows through* when it is.

The output at each position is a weighted blend of all Values in the context, each weighted by how well its Key matched the Query. High match = heavy contribution. Low match = barely present.

**The order of operations matters here.** Relevance is scored first, weights are assigned second, values flow third — in that exact sequence and not the other way around.

First, every token in the context computes a raw relevance score against the current Query — the dot product of Q and K. This is just a number: how well does this candidate's resume match this job description? No commitment yet, just scoring. Second, those raw scores are passed through softmax — a formula that takes any set of numbers and squashes them into a 0-to-1 range so they all add up to 1, turning raw scores into something that behaves like percentages. This is the shortlist forming — the model decides *how much* to draw from each candidate, proportional to their score. Third, each token's Value is multiplied by its weight and the results are summed. This is the actual contribution flowing through — the weighted blend that becomes the representation used to predict the next token.

Score → normalise → blend. Relevance is always computed before weights are assigned, and weights are always assigned before values flow. You cannot skip or reorder these steps — the whole mechanism depends on that sequence.

### What "listening" actually means — no brain required

When we say the position after "the" *listens* to previous tokens, that word deserves unpacking. A human listens and predicts because they have a brain that understands language. A transformer has no such thing. So what is actually happening?

Every token is represented as a **list of numbers** — typically hundreds or thousands of them — called an embedding. That list is learned during training and encodes everything the model has absorbed about how that token relates to every other token it has ever seen. "Cat" is a list of numbers. "Sat" is a different list. "The" is another.

Every token — including the current one deciding what comes next — starts from that same embedding. The Query is simply that current token's embedding pushed through a learned transformation (W_Q), producing a new list of numbers tuned for the question *"what am I looking for?"* Every other token in the context goes through its own transformation (W_K) to produce a Key — a list tuned for *"here is what I contain."* Q and K are not separate things that appear from nowhere. They are different projections of the same underlying token embeddings, each shaped by a different learned matrix.

The dot product of Q and K — multiply the two lists pairwise, sum the results — measures how **aligned** those two vectors are. Think of each list of numbers as an arrow pointing in some direction. If two arrows point in roughly the same direction, they are aligned and the score is high. If they point in opposite directions, the score is low. The model has thousands of these directions, one per dimension in the embedding — too many to visualise, but the geometry works the same way. One number comes out of the dot product. That is the score.

No understanding. No interpretation. Just: *are these two lists of numbers pointing in a similar direction?* If yes, high score — this prior token is relevant. If no, low score — mostly ignored. The model learned during training that tokens which tend to matter to each other end up with embeddings that point in similar directions. "Cat" and "sat" learned to align because they co-occurred in meaningful ways across billions of training examples. The arithmetic just measures that learned alignment on demand, for the specific tokens in front of it right now.

So "listen" really means: *project the current token's embedding into a Query, project every prior token's embedding into a Key, compute geometric similarity between them via multiplication and addition, use those scores to weight how much of each prior token's Value gets blended into the output.*

No brain. Multiply, add, weight, blend.

### How the next token is actually chosen

A related question worth addressing directly: does the model propose candidate next words ("mat", "dog", "parrot") and ask previous tokens to vote? Or does each previous token suggest what it thinks should come next, and the model polls them?

Neither. Here is what happens.

The position where the next token will land attends to all previous tokens through the mechanism above — selective leaning, gathering context. Through that process it builds up a **summary vector** — a single list of numbers encoding the accumulated meaning of everything it attended to. Something like "we are talking about a surface that a cat sat on."

That summary vector is then handed to a separate component — the language model head — which scores **every single token in the vocabulary simultaneously** against it. All 100,000 tokens get a score in one arithmetic pass. "Mat" comes out high. "Floor" comes out reasonably high. "Dog" comes out low. "Parrot" comes out very low. Softmax converts those scores into probabilities. The next token is sampled.

```
All previous tokens
        │
        │  attention — selective leaning, building a context summary
        ▼
A single vector encoding "what the context means so far"
        │
        │  language model head — score all 100k vocabulary tokens at once
        ▼
Probability distribution across the entire vocabulary
        │
        │  sample (or take highest)
        ▼
Next token: "mat"
```

Previous tokens do not vote. They do not propose. They contribute to shaping a context summary through arithmetic. That summary then faces the full vocabulary and scores it. The next word isn't chosen by the past — it emerges from a representation that the past collectively shaped.

---

## 2 — Multiple Companies, One Pool: Multi-Head Attention

A single attention head asks one question of the context. That's limiting — real language has multiple relationships happening simultaneously. "Cat" plays several roles at once: it is the one doing the action, it is the main noun of the sentence, it was mentioned near the start, and it will likely be referenced again. One question can't capture all of those angles at once.

Multi-head attention runs the entire QKV process in parallel across multiple heads — each with its own independently learned W_Q, W_K, W_V weight matrices.

This is the key point: it's not that each head looks at a different *subset* of the same QKVs. Each head has its own learned way of **reading** the resume (W_K) and its own learned way of **extracting** the work output (W_V). The same token produces a completely different Key and Value when processed by a different head.

Think of it as multiple companies hiring from the same candidate pool simultaneously:

- **Company A — syntax head:** reads every resume looking for structural signals. Grammatical role, nesting, punctuation patterns. Its job description (W_Q) is tuned to those signals.
- **Company B — semantics head:** reads the same resumes looking for conceptual depth, meaning relationships, domain knowledge. Completely different reading lens.
- **Company C — long-range dependency head:** looks for candidates whose experience connects ideas across large spans — does this token have a meaningful relationship with something said 500 tokens ago?

Same candidate pool. Three completely different sets of resumes, produced by three different reading lenses applied to the same raw person. Three different shortlists. Three different contributions pulled through.

The outputs of all heads are concatenated and projected back down — the company consortium pools their findings into a single richer representation than any one company could produce alone. One head might notice "cat" is the syntactic subject; another notices it carries semantic agency; a third notices it was referenced again thirty tokens later. All of that lands in the final representation.

---

## 3 — The Invisible Problem: What Happens Without Position

Here is where things get interesting — and where a subtle flaw in the setup so far becomes visible.

Each head's W_Q, W_K, W_V matrices are **the same for every token position**. The same transformation gets applied to every token regardless of where it sits in the sequence.

This means "cat" at position 5 and "cat" at position 1800 go through identical projections. They produce the same Q, K, V vectors. Their attention scores against any given Query are identical. The model has no way to distinguish them.

In the hiring analogy: all 2048 candidates hand in resumes that differ only in content. No queue number, no timestamp, no arrival order. The pile is completely unordered. Two candidates with identical resumes are indistinguishable — whether they arrived first or last makes no difference.

This is a real problem. Consider a code generation context where the user's hard constraint ("do not use React") appears at position 50 and the generation is happening at position 3000. Without position, that constraint and a token at position 2990 are evaluated identically. There is no mechanism for recency. There is no mechanism for "this instruction came before this code."

**Position must be explicitly injected or it simply does not exist.**

---

## 4 — Stamping the Resume: Positional Encodings

Three main approaches to injecting position, each with a different philosophy:

### Absolute encodings — sinusoidal and learned (BERT, GPT-2)

A position vector is added to the token embedding *before* it enters the QKV projection. "Cat" at position 5 and "cat" at position 1800 now arrive at W_Q, W_K, W_V as slightly different vectors. Same word, different positional stamp, different Q, K, V out.

*In the hiring analogy: a queue number gets stamped onto the resume before the company reads it. Same candidate, different stamp. The company sees a different profile.*

The original approach used wave-shaped mathematical patterns — called sinusoidal functions — to generate a unique fingerprint for each position. Think of it as each seat in a concert hall having its own distinct lighting colour: no two seats look exactly the same, so you can always tell where someone is sitting. This was used in the original transformer paper and in early well-known models like BERT (Google's language understanding model) and GPT-2 (an early OpenAI text generator). It works well for short sequences but struggles when the model encounters positions it never saw during training.

### RoPE — Rotary Position Encoding (LLaMA, Mistral, Claude)

Position isn't added to the embedding upfront. Instead, after W_Q and W_K produce their vectors, those vectors are *rotated* by an angle proportional to their position in the sequence. The Q·K dot product then naturally encodes relative distance — two tokens far apart have a larger rotational difference between their vectors, which reduces their score. Distance becomes a geometric penalty baked into the match computation itself.

*In the hiring analogy: the company's job description rotates slightly as it reads further back in the pile. The criteria drift away from candidates the further back they sit. A candidate at position 2000 is being evaluated against a version of the job description that has rotated 2000 steps away from its original orientation. The further back, the more the criteria have drifted from their profile.*

RoPE generalises well to longer sequences because it encodes *relative* distance, not absolute seat numbers. It doesn't need to have seen position 4000 in training — it just needs to know that 4000 steps of rotation is a lot.

### ALiBi — Attention with Linear Biases

The simplest approach. Don't touch the embeddings. Don't rotate the vectors. Just subtract a fixed penalty from the attention score directly, proportional to distance. Token 10 positions away loses 10 points. Token 500 positions away loses 500 points. Explicit, interpretable, and effective.

*In the hiring analogy: HR adds a straight distance deduction to the scorecard after the interview. No rotating criteria, no stamped resumes — just a line on the scorecard that says "subtract 1 point per position in the queue." Candidate at position 1800 gets 1800 points subtracted before the final score is tallied.*

---

The consequence across all three approaches is the same: **the further back in the pile, the lower the attention score**, all else being equal. Distance is now a penalty baked into every match. The model can still attend to distant tokens — but it has to overcome a structural headwind to do so.

---

## 5 — Attention, Position, and Why the Middle Gets Ignored

Once you understand the distance penalty, the next finding follows mechanically — no experiment needed to predict it.

Imagine the model generating a token at the very end of a long context. It looks back at the entire prompt. The distance penalty applies to everything:

- **Tokens at the front of the prompt** — furthest away, highest penalty. But the model has learned through training to pay special attention to the opening of a prompt, where instructions typically live. These tokens tend to be high-signal — role definitions, hard constraints, output format rules — and that learned habit is strong enough to survive the distance penalty.
- **Tokens at the end of the prompt** — closest to the generation point, lowest distance penalty. Recency works in their favour. They score well almost automatically.
- **Tokens in the middle** — penalised from both ends. Not close enough for recency to save them. Not high-signal enough (usually) for trained priors to rescue them. They fall into the valley.

The result is a U-shaped attention curve across position. High at the start. High at the end. A trough in the middle. The valley isn't a bug or a surprise — it is the direct mechanical consequence of how position gets encoded into attention scores.

---

## 6 — The Paper: *Lost in the Middle* (Liu et al., 2023)

This structural prediction was confirmed experimentally in a 2023 Stanford paper. The setup was simple and clean: take a task that requires retrieving one specific piece of information from a long context. Place that information at different positions — beginning, middle, end — and measure whether the model retrieves it correctly.

The results matched the mechanical prediction exactly. Performance was high when the relevant information was near the beginning of the context. Performance was high when it was near the end. Performance dropped sharply when it was placed in the middle. A clean U-shape.

The finding held across model sizes and model families — it wasn't a quirk of one architecture or one scale. It was consistent. And the effect got worse as context length increased: the longer the context, the deeper the valley, the more middle there is to get lost in.

The paper named the failure mode directly: **lost in the middle**. The information is there. The model isn't ignoring it deliberately. It is structurally disadvantaged by where it sits.

---

## 7 — Why the Middle Gets Lost — The Full Story

Three effects compound to create the valley:

**The distance penalty.** As covered above — positional encodings reduce attention scores for tokens far from the generation point. Tokens in the middle of a 10,000-token context are a long way from everything.

**The serial position effect.** This one comes from cognitive science, not machine learning, and the parallel is striking. Humans given a list of items to remember consistently recall the first items (primacy effect) and the last items (recency effect) better than items in the middle. The middle of the list is the hardest to retain. Transformers exhibit the same U-shaped recall curve, through a completely different mechanism — not memory decay but structural attention penalties. The pattern is the same. The cause is different.

**The needle-in-a-haystack failure.** In a long context, a single relevant fact buried in the middle has to compete for attention against thousands of other tokens. Even if it scores reasonably well in isolation, it may never make it into the effective shortlist. The candidate is in the pool. The resume is accurate. The company just never gets to it. At sufficient context length this stops being a probability and starts being a near-certainty.

---

## 8 — Implications for Prompt and System Design

Understanding the mechanics translates directly into better prompt construction:

**Put hard constraints near the end.** Output schemas, explicit prohibitions ("do not use React"), required formats — these need to win against the model's training priors at generation time. Place them close to the generation boundary where recency works in their favour.

**Put critical context at the start or end, never buried.** If a piece of information must be retrieved — a user's requirement, a key constraint, a code snippet to reference — it belongs at the beginning or very end of the prompt. Middle placement is a structural penalty on retrieval.

**Repeat important things near the end.** If a constraint necessarily appears early in a long prompt, echo it near the end. It costs tokens but the retrieval reliability gain is worth it for genuinely hard constraints.

**Shorter prompts attend more uniformly.** The U-shaped valley deepens with context length. A focused, tight prompt with less middle has less information loss than a long sprawling one. Don't pad context — every extra token makes the middle worse.

**RAG as a structural fix.** RAG stands for Retrieval-Augmented Generation. Instead of stuffing all potentially relevant context into the prompt upfront and hoping the model finds the right piece, RAG works differently: it searches a database for only the specific chunks relevant to the current query and injects just those into the prompt at the moment they are needed. The prompt stays short, the relevant content lands close to the generation point, and the distance penalty never gets a chance to bury it. It addresses the root cause rather than working around it — rather than leaving the right candidate at position 4000 and hoping it survives, RAG brings it to the front of the pile.

---

*~15 min read · Covers: attention and selective leaning, QKV mechanics, multi-head attention, the position problem, positional encoding approaches (absolute, RoPE, ALiBi), the U-shaped attention curve, the Lost in the Middle paper, and prompt design implications*
