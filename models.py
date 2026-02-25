from pydantic import BaseModel
from typing import Dict, List, Any, Optional


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str
    remember: bool = False


class ProjectRequest(BaseModel):
    prompt: Optional[str] = None
    project_name: Optional[str] = None
    auto_run: bool = False
    input_mode: str = "text"
    file_analysis_prompt: Optional[str] = None


class FileContent(BaseModel):
    path: str
    content: str
    is_binary: bool = False


class ProjectResponse(BaseModel):
    project_id: str
    project_name: str
    files: List[FileContent]
    instructions: str
    created_at: str
    token_usage: Optional[Dict[str, Any]] = None


class MCPTool(BaseModel):
    name: str
    description: str
    input_schema: dict


class MCPToolCall(BaseModel):
    tool: str
    parameters: dict


class CodeModificationRequest(BaseModel):
    project_id: str
    file_path: str
    modification_prompt: str
    modification_type: str = "general"


class CodeModificationResponse(BaseModel):
    success: bool
    original_code: str
    modified_code: str
    changes_made: List[str]
    file_path: str
    modification_type: str
    backup_created: bool


class EnhancedCodeAssistantRequest(BaseModel):
    project_id: str
    message: str
    context: Optional[str] = None


class EnhancedCodeAssistantResponse(BaseModel):
    success: bool
    action_taken: str
    affected_files: List[str]
    new_files: List[str]
    deleted_files: List[str]
    explanation: str
    changes_summary: List[str]
    next_steps: List[str]
    mcp_calls_made: List[dict]
    token_usage: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    message: str
    sender: str
    timestamp: str
    project_id: str
