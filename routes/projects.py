import json
import os
import zipfile
from datetime import datetime
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Header, File, UploadFile, Form
from fastapi.responses import StreamingResponse

from models import (
    ProjectRequest, EnhancedCodeAssistantRequest, ChatMessage,
    CodeModificationRequest, CodeModificationResponse, EnhancedCodeAssistantResponse
)
from store import projects_store, project_chats, PROJECTS_DIR, ANTHROPIC_API_KEY, ast_processor, dynamic_ast_modifier
from auth import get_user_from_token
from token_usage_manager import global_token_manager
from utils.file_ops import (
    scan_projects_directory, load_project_from_filesystem, save_project_to_filesystem,
    get_project_response_data, get_file_content, save_chat_message_to_db,
    get_chat_history_from_db, analyze_uploaded_files, process_zip_file, create_backup
)
from utils.project_runner import execute_project, stop_project, get_running_projects, detect_project_url
from services.mcp_tools import MCP_TOOLS, execute_mcp_tool
from services.code_assistant import (
    detect_user_intent_and_respond, process_intelligent_code_request_with_dynamic_ast
)
from services.project_generator import create_project_with_mcp_streaming, create_project_from_files_streaming

router = APIRouter()


# ---------------------------------------------------------------------------
# AST routes
# ---------------------------------------------------------------------------

@router.get("/api/projects/{project_id}/ast-summary")
async def get_project_ast_summary(project_id: str):
    """Get AST summary for a project"""
    try:
        if project_id not in projects_store:
            raise HTTPException(status_code=404, detail="Project not found")

        project = projects_store[project_id]
        summary = dynamic_ast_modifier.get_project_ast_summary(project_id, project.project_name)

        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_id}/find-element/{element_name}")
async def find_element_in_project(project_id: str, element_name: str):
    """Find elements by name in project using AST cache"""
    try:
        if project_id not in projects_store:
            raise HTTPException(status_code=404, detail="Project not found")

        project = projects_store[project_id]
        elements = dynamic_ast_modifier.find_elements_in_project(project_id, project.project_name, element_name)

        return {"elements": elements}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/projects/{project_id}/refresh-ast")
async def refresh_project_ast_cache(project_id: str):
    """Refresh AST cache for all files in project"""
    try:
        if project_id not in projects_store:
            raise HTTPException(status_code=404, detail="Project not found")

        project = projects_store[project_id]

        for file in project.files:
            dynamic_ast_modifier.refresh_file_ast(project_id, project.project_name, file.path, file.content)

        summary = dynamic_ast_modifier.get_project_ast_summary(project_id, project.project_name)

        return {
            "success": True,
            "message": "AST cache refreshed",
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/projects/{project_id}/ast-cache")
async def clear_project_ast_cache(project_id: str):
    """Clear AST cache for a project"""
    try:
        dynamic_ast_modifier.clear_project_cache(project_id)

        return {
            "success": True,
            "message": "AST cache cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Code assistant
# ---------------------------------------------------------------------------

@router.post("/api/projects/{project_id}/enhanced-code-assistant")
async def enhanced_code_assistant_api_with_intent_detection(
    project_id: str,
    request: EnhancedCodeAssistantRequest,
    authorization: Optional[str] = Header(None)
):
    """Enhanced code assistant with intelligent intent detection"""
    try:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Not authenticated")

        token = authorization.replace('Bearer ', '')
        user = get_user_from_token(token)

        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        if project_id not in projects_store:
            raise HTTPException(status_code=404, detail="Project not found")

        project = projects_store[project_id]

        save_chat_message_to_db(
            user_id=user['id'],
            project_id=project_id,
            project_name=project.project_name,
            message=request.message,
            sender='user',
            message_type='text'
        )

        result = await detect_user_intent_and_respond(
            project_id,
            request.message,
            request.context
        )

        if isinstance(result, EnhancedCodeAssistantResponse):
            result_dict = result.dict()
        elif isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {
                'success': False,
                'action_taken': 'error',
                'explanation': str(result),
                'is_information_request': False
            }

        save_chat_message_to_db(
            user_id=user['id'],
            project_id=project_id,
            project_name=project.project_name,
            message=result_dict.get('explanation', 'No response'),
            sender='assistant',
            message_type='text',
            metadata={
                'affected_files': result_dict.get('affected_files', []),
                'new_files': result_dict.get('new_files', []),
                'success': result_dict.get('success', False)
            }
        )

        return result_dict

    except Exception as e:
        print(f"[ERROR] Enhanced code assistant failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Token usage (project-scoped)
# ---------------------------------------------------------------------------

@router.get("/api/projects/{project_id}/token-usage")
async def get_project_token_usage(project_id: str):
    """Get token usage statistics for a specific project"""
    try:
        usage_data = global_token_manager.get_project_usage(project_id)
        return usage_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# File listing / AST analysis
# ---------------------------------------------------------------------------

@router.get("/api/projects/{project_id}/files")
async def list_project_files(project_id: str):
    """List all files in a project with AST analysis"""
    try:
        if project_id not in projects_store:
            raise HTTPException(status_code=404, detail="Project not found")

        project = projects_store[project_id]
        files_info = []

        for file in project.files:
            language = ast_processor.detect_language(file.path)
            ast_info = ast_processor.parse_code(file.content, language)

            files_info.append({
                'path': file.path,
                'language': language,
                'size': len(file.content),
                'lines': ast_info.get('total_lines', 0),
                'functions': len(ast_info.get('functions', [])),
                'classes': len(ast_info.get('classes', [])),
                'ast_available': ast_info.get('ast_available', False),
                'modifiable': language in ['python', 'javascript', 'typescript', 'java', 'cpp', 'c']
            })

        return {'files': files_info}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_id}/files/{file_path}/analyze")
async def analyze_file_ast(project_id: str, file_path: str):
    """Get detailed AST analysis of a specific file"""
    try:
        if project_id not in projects_store:
            raise HTTPException(status_code=404, detail="Project not found")

        project = projects_store[project_id]

        target_file = None
        for file in project.files:
            if file.path == file_path:
                target_file = file
                break

        if not target_file:
            raise HTTPException(status_code=404, detail="File not found")

        language = ast_processor.detect_language(file_path)
        ast_info = ast_processor.parse_code(target_file.content, language)

        return {
            'file_path': file_path,
            'language': language,
            'ast_info': ast_info,
            'code_preview': target_file.content[:1000] + '...' if len(target_file.content) > 1000 else target_file.content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@router.post("/api/projects/{project_id}/chat")
async def send_chat_message(project_id: str, message: ChatMessage):
    """Send a chat message for project-specific code assistance"""
    try:
        if project_id not in projects_store:
            raise HTTPException(status_code=404, detail="Project not found")

        if project_id not in project_chats:
            project_chats[project_id] = []

        message.timestamp = datetime.now().isoformat()
        project_chats[project_id].append(message)

        if message.sender == "user":
            intelligent_response = await process_intelligent_code_request_with_dynamic_ast(
                project_id,
                message.message,
                "User is chatting in the project chat interface"
            )

            ai_response = ChatMessage(
                message=intelligent_response.explanation,
                sender="assistant",
                timestamp=datetime.now().isoformat(),
                project_id=project_id
            )

            project_chats[project_id].append(ai_response)

            return {
                'user_message': message,
                'ai_response': ai_response,
                'intelligent_response': intelligent_response,
                'total_messages': len(project_chats[project_id])
            }

        return {
            'message': message,
            'total_messages': len(project_chats[project_id])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_id}/chat/history")
async def get_chat_history(project_id: str, limit: int = 50):
    """Get chat history for a project"""
    try:
        if project_id not in project_chats:
            return {'messages': []}

        messages = project_chats[project_id][-limit:] if limit else project_chats[project_id]
        return {'messages': messages}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_id}/chat-history")
async def get_chat_history_api(project_id: str, authorization: Optional[str] = Header(None)):
    """Get chat history for a project (DB-backed)"""
    try:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Not authenticated")

        token = authorization.replace('Bearer ', '')
        user = get_user_from_token(token)

        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        history = await get_chat_history_from_db(user['id'], project_id)
        project_specific_history = [
            msg for msg in history
            if msg.get('project_id') == project_id
        ]
        print(f"[DEBUG] Retrieved {len(project_specific_history)} chat messages for project {project_id}")

        return {
            "messages": project_specific_history,
            "count": len(project_specific_history),
            "project_id": project_id
        }

    except Exception as e:
        print(f"[ERROR] Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Project generation
# ---------------------------------------------------------------------------

@router.post("/api/generate")
async def generate_project_api(request: ProjectRequest):
    """Handle text-based project generation with token usage tracking"""
    try:
        if not ANTHROPIC_API_KEY:
            raise HTTPException(status_code=400, detail="Anthropic API key not configured")

        if request.input_mode == "text":
            if not request.prompt:
                raise HTTPException(status_code=400, detail="Prompt is required for text-based generation")

            project_response = await create_project_with_mcp_streaming(request.prompt, request.project_name)

        else:
            raise HTTPException(status_code=400, detail="File-based generation should use /api/generate/files endpoint")

        await save_project_to_filesystem(project_response)
        projects_store[project_response.project_id] = project_response

        execution_result = None
        if request.auto_run:
            try:
                execution_result = await execute_project(project_response.project_id)
            except Exception as exec_error:
                execution_result = {"status": "error", "message": str(exec_error)}

        response_data = get_project_response_data(project_response)
        if execution_result:
            response_data["execution"] = execution_result

        if project_response.token_usage:
            response_data["token_usage"] = project_response.token_usage
            full_usage = global_token_manager.get_project_usage(project_response.project_id)
            response_data["full_token_usage"] = full_usage

        return response_data

    except Exception as e:
        print(f"[ERROR] Project generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/generate/files")
async def generate_project_from_files(
    files: List[UploadFile] = File(...),
    analysis_prompt: str = Form("Analyze and improve this project"),
    project_name: Optional[str] = Form(None),
    auto_run: bool = Form(False)
):
    """Generate project from uploaded files"""
    try:
        if not ANTHROPIC_API_KEY:
            raise HTTPException(status_code=400, detail="Anthropic API key not configured")

        if len(files) == 1 and files[0].filename.endswith('.zip'):
            files_data = await process_zip_file(files[0])
        else:
            files_data = await analyze_uploaded_files(files)

        if files_data['total_files'] == 0:
            raise HTTPException(status_code=400, detail="No valid files found")

        project_response = await create_project_from_files_streaming(
            files_data,
            analysis_prompt,
            project_name
        )

        await save_project_to_filesystem(project_response)
        projects_store[project_response.project_id] = project_response

        execution_result = None
        if auto_run:
            try:
                execution_result = await execute_project(project_response.project_id)
            except Exception as exec_error:
                execution_result = {"status": "error", "message": str(exec_error)}

        response_data = get_project_response_data(project_response)
        response_data["source_files"] = {
            "total_files": files_data['total_files'],
            "total_size": files_data['total_size'],
            "file_tree": files_data['tree']
        }
        if execution_result:
            response_data["execution"] = execution_result

        return response_data

    except Exception as e:
        print(f"[ERROR] File-based project generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/analyze/files")
async def analyze_files_only(files: List[UploadFile] = File(...)):
    """Analyze uploaded files without generating a project"""
    try:
        if len(files) == 1 and files[0].filename.endswith('.zip'):
            files_data = await process_zip_file(files[0])
        else:
            files_data = await analyze_uploaded_files(files)

        return {
            "total_files": files_data['total_files'],
            "total_size": files_data['total_size'],
            "file_tree": files_data['tree'],
            "files_preview": {
                name: {
                    "size": info['size'],
                    "type": info['type'],
                    "preview": info['content'][:500] + "..." if len(info['content']) > 500 else info['content']
                }
                for name, info in list(files_data['files'].items())[:10]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Project management (list / get / scan)
# NOTE: specific paths must come before parameterised {project_id} routes
# ---------------------------------------------------------------------------

@router.get("/api/projects/scan-directory")
async def scan_projects_directory_route():
    """Scan the generated_projects directory for all projects"""
    try:
        return await scan_projects_directory()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/running")
async def get_running_projects_api():
    """Get all running projects"""
    return {"running_projects": get_running_projects()}


@router.get("/api/projects")
async def list_projects_api():
    """List all projects"""
    try:
        store_projects = []
        for project_id, project in projects_store.items():
            store_projects.append({
                "project_id": project_id,
                "project_name": project.project_name,
                "created_at": project.created_at,
                "file_count": len(project.files),
                "source": "store"
            })

        try:
            scan_response = await scan_projects_directory()
            directory_projects = scan_response.get("projects", [])
        except Exception:
            directory_projects = []

        all_projects = {}

        for project in store_projects:
            all_projects[project["project_id"]] = project

        for project in directory_projects:
            if project["project_id"] not in all_projects:
                project["loadable"] = True
                all_projects[project["project_id"]] = project

        projects_list = list(all_projects.values())
        projects_list.sort(key=lambda x: x["created_at"], reverse=True)

        return projects_list

    except Exception as e:
        print(f"Error getting all projects: {e}")
        project_list = []
        for project_id, project in projects_store.items():
            project_list.append({
                "project_id": project_id,
                "project_name": project.project_name,
                "created_at": project.created_at,
                "file_count": len(project.files),
                "source": "store"
            })
        project_list.sort(key=lambda x: x["created_at"], reverse=True)
        return project_list


@router.get("/api/projects/{project_id}")
async def get_project_api(project_id: str):
    """Get project details with automatic loading from filesystem if needed"""
    if project_id in projects_store:
        return projects_store[project_id]

    print(f"[DEBUG] Project {project_id} not in store, trying to load from filesystem...")

    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        metadata_file = project_dir / "project_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                if metadata.get("project_id") == project_id:
                    project = await load_project_from_filesystem(project_id, project_dir)
                    if project:
                        print(f"[DEBUG] Successfully loaded project {project_id} from filesystem")
                        return project
                    else:
                        print(f"[DEBUG] Failed to load project {project_id} from filesystem")
                        break
            except Exception as e:
                print(f"[DEBUG] Error reading metadata for {project_dir.name}: {e}")
                continue

    raise HTTPException(status_code=404, detail="Project not found")


# ---------------------------------------------------------------------------
# Project execution
# ---------------------------------------------------------------------------

@router.post("/api/projects/{project_id}/run")
async def run_project_api(project_id: str, run_command: str = None):
    """Execute a generated project"""
    try:
        result = await execute_project(project_id, run_command)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/projects/{project_id}/stop")
async def stop_project_api(project_id: str):
    """Stop a running project"""
    try:
        result = await stop_project(project_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Code modification (legacy endpoint)
# ---------------------------------------------------------------------------

@router.post("/api/projects/{project_id}/modify-code")
async def modify_project_code(project_id: str, request: CodeModificationRequest):
    """Modify code in a project using AST and LLM (legacy endpoint)"""
    try:
        if project_id not in projects_store:
            raise HTTPException(status_code=404, detail="Project not found")

        project = projects_store[project_id]
        project_dir = PROJECTS_DIR / f"{project.project_name}_{project.project_id[:8]}"
        full_file_path = project_dir / request.file_path

        if not full_file_path.exists():
            raise HTTPException(status_code=404, detail=f"File {request.file_path} not found")

        with open(full_file_path, 'r', encoding='utf-8') as f:
            original_code = f.read()

        await create_backup(project_id, request.file_path)

        intelligent_response = await process_intelligent_code_request_with_dynamic_ast(
            project_id,
            f"Modify {request.file_path}: {request.modification_prompt}",
            f"User wants to modify existing file with type: {request.modification_type}"
        )

        if intelligent_response.success and intelligent_response.affected_files:
            modified_content = None
            for file_obj in project.files:
                if file_obj.path == request.file_path:
                    modified_content = file_obj.content
                    break

            return CodeModificationResponse(
                success=True,
                original_code=original_code,
                modified_code=modified_content or original_code,
                changes_made=intelligent_response.changes_summary,
                file_path=request.file_path,
                modification_type=request.modification_type,
                backup_created=True
            )
        else:
            return CodeModificationResponse(
                success=False,
                original_code=original_code,
                modified_code=original_code,
                changes_made=[intelligent_response.explanation],
                file_path=request.file_path,
                modification_type=request.modification_type,
                backup_created=True
            )

    except Exception as e:
        print(f"[ERROR] Code modification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

@router.get("/download_project/{project_id}")
async def download_project(project_id: str):
    """Download project as ZIP"""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_store[project_id]

    project_folder = PROJECTS_DIR / f"{project.project_name}_{project.project_id[:8]}"

    if not os.path.exists(project_folder):
        raise HTTPException(status_code=404, detail="Project folder not found on filesystem")

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_folder):
            for file in files:
                file_path = os.path.join(root, file)

                arcname = os.path.relpath(file_path, project_folder)

                skip_patterns = [
                    "__pycache__",
                    ".pyc",
                    ".DS_Store",
                    "Thumbs.db"
                ]

                should_skip = any(pattern in file_path for pattern in skip_patterns)

                if not should_skip:
                    try:
                        zf.write(file_path, arcname)
                        print(f"[ZIP] Added: {arcname}")
                    except Exception as e:
                        print(f"[ZIP ERROR] Failed to add {arcname}: {e}")

            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                arcname = os.path.relpath(dir_path, project_folder)

                if not any(pattern in dir_path for pattern in ["__pycache__"]):
                    zf.write(dir_path, arcname + "/")
                    print(f"[ZIP] Added directory: {arcname}/")

    memory_file.seek(0)

    headers = {
        "Content-Disposition": f"attachment; filename={project.project_name}.zip"
    }
    return StreamingResponse(memory_file, media_type="application/zip", headers=headers)


# ---------------------------------------------------------------------------
# MCP server endpoints
# ---------------------------------------------------------------------------

@router.post("/mcp/call_tool")
async def mcp_call_tool(tool_name: str, arguments: dict):
    """Call an MCP tool"""
    try:
        if tool_name in MCP_TOOLS:
            result = await execute_mcp_tool(tool_name, arguments)
            return {"result": result}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/resources/{resource_type}")
async def mcp_get_resource(resource_type: str, resource_id: str = None):
    """Get an MCP resource"""
    try:
        if resource_type == "project" and resource_id:
            if resource_id in projects_store:
                return {"content": json.dumps(projects_store[resource_id].dict(), indent=2)}
        elif resource_type == "projects" and resource_id == "list":
            return {"content": json.dumps([p.dict() for p in projects_store.values()], indent=2)}
        else:
            raise HTTPException(status_code=404, detail="Resource not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/info")
async def mcp_info():
    """Get MCP server information"""
    return {
        "name": "Enhanced MCP Project Generator Server with Intelligent Code Assistant",
        "version": "2.0.0",
        "description": "FastAPI-based MCP server for AI-powered project generation and intelligent code modification",
        "tools": [
            {
                "name": name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for name, tool in MCP_TOOLS.items()
        ],
        "resources": [
            {
                "name": "project://{project_id}",
                "description": "Get a generated project by ID"
            },
            {
                "name": "projects://list",
                "description": "List all generated projects"
            }
        ],
        "mcp_tools_count": len(MCP_TOOLS),
        "features": [
            "Intelligent natural language code modification",
            "Multi-file project generation",
            "AST-powered code analysis",
            "Automatic backup creation",
            "Real-time project execution",
            "File-based project improvement"
        ]
    }


@router.get("/mcp/tools")
async def list_mcp_tools():
    """List available MCP tools"""
    return {
        "tools": [
            {
                "name": name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for name, tool in MCP_TOOLS.items()
        ]
    }


@router.get("/health")
async def health_check():
    from store import ANTHROPIC_API_KEY, running_processes
    return {
        "status": "healthy",
        "anthropic_configured": bool(ANTHROPIC_API_KEY),
        "mcp_tools_available": len(MCP_TOOLS),
        "projects_count": len(projects_store),
        "running_processes": len(running_processes),
        "features": {
            "intelligent_code_assistant": True,
            "ast_analysis": True,
            "multi_language_support": True,
            "project_execution": True,
            "file_based_generation": True
        }
    }


# ---------------------------------------------------------------------------
# MCP convenience endpoints (backward compat)
# ---------------------------------------------------------------------------

@router.post("/mcp/generate_project")
async def mcp_generate_project(prompt: str, project_name: Optional[str] = None):
    """MCP endpoint for project generation"""
    try:
        project_response = await create_project_with_mcp_streaming(prompt, project_name)
        await save_project_to_filesystem(project_response)
        projects_store[project_response.project_id] = project_response
        return {"result": f"Project '{project_response.project_name}' generated successfully with MCP tools. ID: {project_response.project_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/get_project/{project_id}")
async def mcp_get_project(project_id: str):
    """MCP endpoint to get project details"""
    try:
        if project_id not in projects_store:
            raise ValueError(f"Project {project_id} not found")
        return {"result": json.dumps(projects_store[project_id].dict(), indent=2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/list_projects")
async def mcp_list_projects():
    """MCP endpoint to list all projects"""
    try:
        project_list = [
            {
                "project_id": pid,
                "project_name": p.project_name,
                "created_at": p.created_at,
                "file_count": len(p.files)
            }
            for pid, p in projects_store.items()
        ]
        return {"result": json.dumps(project_list, indent=2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/enhanced_code_assistant/{project_id}")
async def mcp_enhanced_code_assistant(project_id: str, message: str, context: Optional[str] = None):
    """MCP endpoint for enhanced code assistant"""
    try:
        result = await process_intelligent_code_request_with_dynamic_ast(project_id, message, context)
        return {"result": result.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
