import os
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
import anthropic

from models import ProjectResponse, ChatMessage
from multiLanguageASTParser import MultiLanguageASTProcessor
from enhanced_ast_modifier import DynamicASTModifier

load_dotenv()

# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PROJECTS_DIR = Path("generated_projects")
STATIC_DIR = Path("static")

# Create directories
PROJECTS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Provider detection
# Explicit LLM_PROVIDER env var wins; otherwise infer from which key is set.
# Anthropic takes priority if both keys are present.
# ---------------------------------------------------------------------------
_explicit_provider = os.getenv("LLM_PROVIDER", "").strip().lower()

if _explicit_provider in ("anthropic", "gemini"):
    PROVIDER = _explicit_provider
elif ANTHROPIC_API_KEY:
    PROVIDER = "anthropic"
elif GEMINI_API_KEY:
    PROVIDER = "gemini"
else:
    PROVIDER = ""

# ---------------------------------------------------------------------------
# Default model per provider
# Override with ANTHROPIC_MODEL or GEMINI_MODEL env vars if needed.
# ---------------------------------------------------------------------------
_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5-20250929",
    "gemini": "gemini-2.0-flash",
}

if PROVIDER == "anthropic":
    DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL") or _DEFAULT_MODELS["anthropic"]
elif PROVIDER == "gemini":
    DEFAULT_MODEL = os.getenv("GEMINI_MODEL") or _DEFAULT_MODELS["gemini"]
else:
    DEFAULT_MODEL = _DEFAULT_MODELS.get(PROVIDER, "claude-sonnet-4-5-20250929")

# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------
client = None

if PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
elif PROVIDER == "gemini" and GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        # client is not used directly for Gemini; llm_provider.py creates
        # GenerativeModel instances. We set a truthy sentinel so callers that
        # check `if not client` still work correctly.
        client = genai
    except ImportError:
        print("WARNING: google-generativeai package not installed. Run: pip install google-generativeai")

try:
    import tree_sitter
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    print("Warning: tree-sitter not available. Only Python AST will work.")

# Shared processor instances
ast_processor = MultiLanguageASTProcessor()
dynamic_ast_modifier = DynamicASTModifier()

# In-memory stores
projects_store: Dict[str, ProjectResponse] = {}
running_processes: dict = {}
project_chats: Dict[str, List[ChatMessage]] = {}
active_generations: dict = {}  # task_id -> {"cancelled": bool}
