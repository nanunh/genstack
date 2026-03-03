"""
LLM Provider Abstraction Layer

Supports Anthropic (Claude) and Google Gemini.
Active provider is determined by which API key is set in .env
(or explicitly via LLM_PROVIDER=anthropic|gemini).

Usage:
    from services.llm_provider import stream_llm, get_prompt_suffix

    text, input_tokens, output_tokens = stream_llm(
        system="You are a code expert." + get_prompt_suffix(),
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=1000,
    )

    # For calls that must return JSON (project generation, plan creation):
    text, input_tokens, output_tokens = stream_llm(
        system="..." + get_prompt_suffix(),
        messages=[...],
        max_tokens=8000,
        response_format="json",   # enables Gemini's constrained JSON mode
    )
"""

import json
import re
from typing import Callable, Optional, Tuple


# ---------------------------------------------------------------------------
# Provider-specific prompt additions
# ---------------------------------------------------------------------------

# Appended to every system prompt for non-JSON (text/code) Gemini calls.
# Prevents markdown wrapping and preamble.
_GEMINI_TEXT_SUFFIX = (
    "\n\nCRITICAL: Return raw content only. "
    "Do NOT wrap output in markdown code blocks or backticks. "
    "No preamble or explanation text before or after the content."
)

# Appended to every system prompt for JSON Gemini calls.
# Reinforces JSON-only output (constrained decoding handles the rest).
_GEMINI_JSON_SUFFIX = (
    "\n\nCRITICAL: Your entire response MUST be a single valid JSON object. "
    "No markdown, no code fences, no explanation — pure JSON only."
)


def get_prompt_suffix(response_format: str = "text") -> str:
    """Return the provider-specific prompt suffix for the active provider."""
    from store import PROVIDER
    if PROVIDER != "gemini":
        return ""
    return _GEMINI_JSON_SUFFIX if response_format == "json" else _GEMINI_TEXT_SUFFIX


# ---------------------------------------------------------------------------
# Gemini per-model output token limits
# ---------------------------------------------------------------------------

# Gemini 2.0 Flash and older: hard 8 192-token output cap.
# Gemini 2.5 Flash/Pro: up to 65 536 output tokens.
# Passing a value above the model's limit causes a 400 InvalidArgument error.
_GEMINI_TOKEN_LIMITS: dict = {
    "gemini-1.5-flash":           8192,
    "gemini-1.5-pro":             8192,
    "gemini-2.0-flash":           8192,
    "gemini-2.0-flash-lite":      8192,
    "gemini-2.0-flash-thinking":  8192,
    "gemini-2.5-flash":          65536,
    "gemini-2.5-pro":            65536,
}
_GEMINI_DEFAULT_TOKEN_LIMIT = 8192  # conservative default for unknown models


def _gemini_token_limit(model_name: str) -> int:
    """Return the maximum output tokens for a Gemini model name."""
    if model_name in _GEMINI_TOKEN_LIMITS:
        return _GEMINI_TOKEN_LIMITS[model_name]
    # Catch preview / dated variants like "gemini-2.5-flash-preview-04-17"
    for key, limit in _GEMINI_TOKEN_LIMITS.items():
        if model_name.startswith(key):
            return limit
    return _GEMINI_DEFAULT_TOKEN_LIMIT


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def extract_json_from_response(response: str) -> dict:
    """
    Robustly extract and parse JSON from an LLM response.

    Handles these LLM-specific quirks (especially Gemini):
    1. Response wrapped in  ```json ... ```  markdown blocks
    2. Nested code blocks INSIDE the JSON — rfind() finds the outermost marker
    3. Response that is already raw JSON (no wrapper) — Gemini JSON-mode output
    4. Literal newlines / control characters inside JSON string values
    5. Unescaped double-quotes inside string values — fixed by json-repair
    """
    stripped = response.strip()

    # ---- Step 1: extract the raw JSON text --------------------------------
    json_text = None

    # Fast path: if the response starts with { it is already raw JSON
    # (happens when Gemini is in response_mime_type="application/json" mode)
    if stripped.startswith(("{", "[")):
        json_text = stripped
    elif "```" in response:
        open_match = re.search(r"```(?:json)?\s*\n", response)
        if open_match:
            content_start = open_match.end()
            # rfind → always finds the real outermost closing marker,
            # even when the JSON content itself contains nested ``` blocks
            close_pos = response.rfind("\n```")
            if close_pos > content_start:
                json_text = response[content_start:close_pos].strip()

    if json_text is None:
        # Last-resort: extract outermost { ... }
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_text = response[start:end]
        else:
            raise ValueError("No JSON found in LLM response")

    # ---- Step 2: parse — three increasingly permissive attempts -----------

    # Attempt 1: standard strict parse (works for clean JSON and JSON-mode output)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: allow literal control characters (newlines, tabs) inside strings
    try:
        return json.JSONDecoder(strict=False).decode(json_text)
    except json.JSONDecodeError:
        pass

    # Attempt 3: json-repair — fixes unescaped double-quotes, missing commas,
    # trailing commas, and other structural issues common in LLM output
    try:
        from json_repair import repair_json
        result = repair_json(json_text, return_objects=True)
        if isinstance(result, dict):
            return result
        raise ValueError(f"json-repair returned {type(result).__name__}, expected dict")
    except Exception as e:
        raise ValueError(
            f"JSON parsing failed after all attempts: {e}\n"
            f"(first 200 chars): {json_text[:200]}"
        )


# ---------------------------------------------------------------------------
# Unified streaming entry-point
# ---------------------------------------------------------------------------

def stream_llm(
    system: str,
    messages: list,
    max_tokens: int,
    temperature: float = 0.1,
    on_chunk: Optional[Callable[[str], None]] = None,
    response_format: str = "text",
) -> Tuple[str, int, int]:
    """
    Stream text from the active LLM provider.

    Args:
        system:          System prompt text.
        messages:        Messages in Anthropic format:
                         [{"role": "user"|"assistant", "content": "..."}]
        max_tokens:      Maximum output tokens.
        temperature:     Sampling temperature.
        on_chunk:        Optional callback invoked with each streamed text chunk.
        response_format: "text" (default) or "json".
                         When "json" and provider is Gemini, enables
                         response_mime_type="application/json" (constrained
                         decoding — guaranteed valid JSON output).

    Returns:
        Tuple of (full_response_text, input_tokens, output_tokens).
    """
    from store import PROVIDER

    if PROVIDER == "anthropic":
        return _stream_anthropic(system, messages, max_tokens, temperature, on_chunk)
    elif PROVIDER == "gemini":
        return _stream_gemini(system, messages, max_tokens, temperature, on_chunk, response_format)
    else:
        raise RuntimeError(
            "No LLM provider configured. "
            "Set ANTHROPIC_API_KEY or GEMINI_API_KEY in your .env file."
        )


# ---------------------------------------------------------------------------
# Anthropic backend
# ---------------------------------------------------------------------------

def _stream_anthropic(
    system: str,
    messages: list,
    max_tokens: int,
    temperature: float,
    on_chunk: Optional[Callable[[str], None]],
) -> Tuple[str, int, int]:
    from store import client, DEFAULT_MODEL

    response_content = ""
    input_tokens = 0
    output_tokens = 0

    with client.messages.stream(
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=messages,
    ) as stream_response:
        for text in stream_response.text_stream:
            response_content += text
            if on_chunk:
                on_chunk(text)

        final_message = stream_response.get_final_message()
        if hasattr(final_message, "usage"):
            input_tokens = final_message.usage.input_tokens
            output_tokens = final_message.usage.output_tokens

    return response_content, input_tokens, output_tokens


# ---------------------------------------------------------------------------
# Gemini backend
# ---------------------------------------------------------------------------

def _stream_gemini(
    system: str,
    messages: list,
    max_tokens: int,
    temperature: float,
    on_chunk: Optional[Callable[[str], None]],
    response_format: str = "text",
) -> Tuple[str, int, int]:
    import google.generativeai as genai
    from store import DEFAULT_MODEL

    # Clamp requested tokens to this model's hard output ceiling
    model_limit = _gemini_token_limit(DEFAULT_MODEL)
    effective_max_tokens = min(max_tokens, model_limit)

    print(f"[DEBUG][Gemini] model={DEFAULT_MODEL} "
          f"max_output_tokens={effective_max_tokens} "
          f"response_format={response_format}")

    model_instance = genai.GenerativeModel(
        model_name=DEFAULT_MODEL,
        system_instruction=system if system else None,
    )

    gemini_contents = _to_gemini_messages(messages)
    response_content = ""
    input_tokens = 0
    output_tokens = 0

    # Build generation config
    config_kwargs = {
        "max_output_tokens": effective_max_tokens,
        "temperature": temperature,
    }
    if response_format == "json":
        # Constrained decoding: the model is forced to produce valid JSON.
        # This eliminates unescaped quotes, missing commas, markdown wrappers, etc.
        config_kwargs["response_mime_type"] = "application/json"

    try:
        stream_response = model_instance.generate_content(
            contents=gemini_contents,
            stream=True,
            generation_config=genai.GenerationConfig(**config_kwargs),
        )

        for chunk in stream_response:
            # chunk.text raises ValueError on safety blocks — handle gracefully
            try:
                text = chunk.text or ""
            except (ValueError, AttributeError):
                text = ""
            if text:
                response_content += text
                if on_chunk:
                    on_chunk(text)

        # Token usage is available on the resolved response after streaming
        try:
            meta = stream_response.usage_metadata
            input_tokens = meta.prompt_token_count or 0
            output_tokens = meta.candidates_token_count or 0
        except Exception:
            pass

    except Exception as e:
        print(f"[ERROR][Gemini] API call failed: {e}")
        raise

    print(f"[DEBUG][Gemini] response_length={len(response_content)} "
          f"tokens={input_tokens}+{output_tokens}")
    return response_content, input_tokens, output_tokens


def _to_gemini_messages(messages: list) -> list:
    """Convert Anthropic-format messages to Gemini content format."""
    result = []
    for msg in messages:
        # Gemini uses "model" where Anthropic uses "assistant"
        role = "model" if msg["role"] == "assistant" else "user"
        result.append({"role": role, "parts": [{"text": msg["content"]}]})
    return result
