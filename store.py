import os
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
import anthropic

from models import ProjectResponse, ChatMessage
from multiLanguageASTParser import MultiLanguageASTProcessor
from enhanced_ast_modifier import DynamicASTModifier

load_dotenv()

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PROJECTS_DIR = Path("generated_projects")
STATIC_DIR = Path("static")

# Create directories
PROJECTS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Initialize Anthropic client
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None

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
