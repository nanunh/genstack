import json
from typing import Dict, Any

from models import MCPTool, FileContent
from store import projects_store, PROJECTS_DIR, ast_processor, dynamic_ast_modifier
from utils.file_ops import (
    create_backup, get_file_content, update_file_in_project,
    add_file_to_project, save_file_to_filesystem
)

# ---------------------------------------------------------------------------
# MCP Tool Registry
# ---------------------------------------------------------------------------

MCP_TOOLS: Dict[str, MCPTool] = {
    "create_file": MCPTool(
        name="create_file",
        description="Create any file with specified content - no restrictions",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to project root"},
                "content": {"type": "string", "description": "Complete file content"},
                "description": {"type": "string", "description": "Brief description of what this file does"}
            },
            "required": ["path", "content"]
        }
    ),
    "analyze_requirements": MCPTool(
        name="analyze_requirements",
        description="Analyze project requirements and suggest file structure",
        input_schema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The user's project request"},
                "technology": {"type": "string", "description": "Primary technology/framework"}
            },
            "required": ["prompt", "technology"]
        }
    ),
    "add_dependency": MCPTool(
        name="add_dependency",
        description="Add a dependency that will be included in package.json or requirements.txt",
        input_schema={
            "type": "object",
            "properties": {
                "dependency": {"type": "string", "description": "Dependency name and optional version"},
                "package_manager": {"type": "string", "description": "npm, pip, or yarn"},
                "description": {"type": "string", "description": "Why this dependency is needed"}
            },
            "required": ["dependency", "package_manager"]
        }
    ),
    "create_new_file": MCPTool(
        name="create_new_file",
        description="Create a completely new file in the project",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path for the new file"},
                "content": {"type": "string", "description": "Complete content for the new file"},
                "description": {"type": "string", "description": "What this new file does"},
                "file_type": {"type": "string", "description": "Type of file (component, utility, config, etc.)"}
            },
            "required": ["file_path", "content", "description"]
        }
    ),
    "update_existing_file": MCPTool(
        name="update_existing_file",
        description="Update or modify an existing file",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path of the file to update"},
                "content": {"type": "string", "description": "Updated complete content"},
                "changes_made": {"type": "array", "items": {"type": "string"}, "description": "List of changes made"},
                "modification_type": {"type": "string", "description": "Type of modification (feature_add, bug_fix, refactor, etc.)"}
            },
            "required": ["file_path", "content", "changes_made"]
        }
    ),
    "delete_file": MCPTool(
        name="delete_file",
        description="Delete a file from the project",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path of the file to delete"},
                "reason": {"type": "string", "description": "Why this file is being deleted"}
            },
            "required": ["file_path", "reason"]
        }
    ),
    "add_feature": MCPTool(
        name="add_feature",
        description="Add a new feature across multiple files",
        input_schema={
            "type": "object",
            "properties": {
                "feature_name": {"type": "string", "description": "Name of the feature to add"},
                "affected_files": {"type": "array", "items": {"type": "string"}, "description": "Files that will be modified"},
                "new_files": {"type": "array", "items": {"type": "string"}, "description": "New files to create"},
                "description": {"type": "string", "description": "Detailed description of the feature"}
            },
            "required": ["feature_name", "description"]
        }
    ),
    "explain_code": MCPTool(
        name="explain_code",
        description="Provide detailed explanation of code functionality",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "File to explain"},
                "code_section": {"type": "string", "description": "Specific section to explain (optional)"},
                "explanation_type": {"type": "string", "description": "Type of explanation (overview, detailed, tutorial)"}
            },
            "required": ["file_path"]
        }
    ),
    "run_project": MCPTool(
        name="run_project",
        description="Execute the generated project",
        input_schema={
            "type": "object",
            "properties": {
                "project_type": {"type": "string", "description": "Type of project (react, python, node, etc.)"},
                "run_command": {"type": "string", "description": "Command to run the project"},
                "port": {"type": "integer", "description": "Port number to run on"}
            },
            "required": ["project_type", "run_command"]
        }
    ),
    "deploy_to_server": MCPTool(
        name="deploy_to_server",
        description="Deploy project to remote Linux server via SSH",
        input_schema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID to deploy"},
                "ssh_host": {"type": "string", "description": "Remote server hostname or IP"},
                "ssh_username": {"type": "string", "description": "SSH username"},
                "ssh_password": {"type": "string", "description": "SSH password"},
                "ssh_port": {"type": "integer", "description": "SSH port (default: 22)"},
                "remote_path": {"type": "string", "description": "Remote deployment path"},
                "port": {"type": "integer", "description": "Application port on remote server"}
            },
            "required": ["project_id", "ssh_host", "ssh_username", "ssh_password"]
        }
    ),
    "check_server_status": MCPTool(
        name="check_server_status",
        description="Check if deployed application is running on remote server",
        input_schema={
            "type": "object",
            "properties": {
                "ssh_host": {"type": "string"},
                "ssh_username": {"type": "string"},
                "ssh_password": {"type": "string"},
                "ssh_port": {"type": "integer"},
                "project_name": {"type": "string"},
                "app_port": {"type": "integer"}
            },
            "required": ["ssh_host", "ssh_username", "ssh_password", "project_name"]
        }
    ),
    "stop_deployment": MCPTool(
        name="stop_deployment",
        description="Stop a running deployment on remote server",
        input_schema={
            "type": "object",
            "properties": {
                "ssh_host": {"type": "string"},
                "ssh_username": {"type": "string"},
                "ssh_password": {"type": "string"},
                "ssh_port": {"type": "integer"},
                "project_name": {"type": "string"}
            },
            "required": ["ssh_host", "ssh_username", "ssh_password", "project_name"]
        }
    ),
}


# ---------------------------------------------------------------------------
# Original MCP tool execution
# ---------------------------------------------------------------------------

async def execute_mcp_tool(tool_name: str, parameters: dict) -> dict:
    """Execute an MCP tool"""

    # Deployment tools are handled by ssh_deployment service
    if tool_name in ["deploy_to_server", "check_server_status", "stop_deployment"]:
        from services.ssh_deployment import execute_deployment_mcp_tool
        return await execute_deployment_mcp_tool(tool_name, parameters)

    if tool_name == "create_file":
        return {
            "type": "file_created",
            "path": parameters["path"],
            "content": parameters["content"],
            "description": parameters.get("description", "")
        }

    elif tool_name == "analyze_requirements":
        prompt = parameters["prompt"]
        technology = parameters["technology"].lower()

        return {
            "type": "requirements_analyzed",
            "prompt": prompt,
            "technology": technology,
            "suggestion": f"Based on '{prompt}' using {technology}, create files dynamically based on specific needs"
        }

    elif tool_name == "add_dependency":
        return {
            "type": "dependency_added",
            "dependency": parameters["dependency"],
            "package_manager": parameters.get("package_manager", "npm"),
            "description": parameters.get("description", "")
        }

    elif tool_name == "run_project":
        project_type = parameters["project_type"].lower()
        run_command = parameters["run_command"]
        port = parameters.get("port", 3000)

        return {
            "type": "project_execution_planned",
            "project_type": project_type,
            "run_command": run_command,
            "port": port,
            "execution_ready": True
        }

    else:
        raise ValueError(f"Unknown MCP tool: {tool_name}")


# ---------------------------------------------------------------------------
# Enhanced MCP tool execution
# ---------------------------------------------------------------------------

async def execute_enhanced_mcp_tool(tool_name: str, parameters: dict, project_id: str) -> dict:
    """Execute enhanced MCP tools for intelligent code operations"""

    project = projects_store[project_id]
    project_dir = PROJECTS_DIR / f"{project.project_name}_{project.project_id[:8]}"

    if tool_name == "create_new_file":
        file_path = parameters["file_path"]
        content = parameters["content"]
        description = parameters.get("description", "")

        full_file_path = project_dir / file_path
        full_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        project.files.append(FileContent(
            path=file_path,
            content=content,
            is_binary=False
        ))

        return {
            "type": "file_created",
            "file_path": file_path,
            "description": description,
            "size": len(content)
        }

    elif tool_name == "update_existing_file":
        file_path = parameters["file_path"]
        new_content = parameters["content"]
        changes_made = parameters.get("changes_made", [])

        await create_backup(project_id, file_path)

        full_file_path = project_dir / file_path
        if full_file_path.exists():
            with open(full_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        for file_obj in project.files:
            if file_obj.path == file_path:
                file_obj.content = new_content
                break

        return {
            "type": "file_updated",
            "file_path": file_path,
            "changes_made": changes_made
        }

    elif tool_name == "delete_file":
        file_path = parameters["file_path"]
        reason = parameters.get("reason", "")

        full_file_path = project_dir / file_path
        if full_file_path.exists():
            full_file_path.unlink()

        project.files = [f for f in project.files if f.path != file_path]

        return {
            "type": "file_deleted",
            "file_path": file_path,
            "reason": reason
        }

    elif tool_name == "explain_code":
        file_path = parameters["file_path"]

        target_file = None
        for f in project.files:
            if f.path == file_path:
                target_file = f
                break

        if not target_file:
            return {"type": "error", "message": f"File {file_path} not found"}

        language = ast_processor.detect_language(file_path)
        ast_info = ast_processor.parse_code(target_file.content, language)

        explanation = f"""File: {file_path}
Language: {language}
Size: {len(target_file.content)} characters
Lines: {ast_info.get('total_lines', 0)}

Functions: {len(ast_info.get('functions', []))}
Classes: {len(ast_info.get('classes', []))}
Imports: {len(ast_info.get('imports', []))}

This file appears to be a {language} file with the following structure:
{ast_processor.get_summary(target_file.content, language)}
"""

        return {
            "type": "code_explained",
            "file_path": file_path,
            "explanation": explanation,
            "ast_info": ast_info
        }

    elif tool_name == "add_feature":
        feature_name = parameters["feature_name"]
        description = parameters["description"]

        return {
            "type": "feature_added",
            "feature_name": feature_name,
            "description": description,
            "affected_files": parameters.get("affected_files", []),
            "new_files": parameters.get("new_files", [])
        }

    else:
        return await execute_mcp_tool(tool_name, parameters)
