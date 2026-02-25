import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from models import EnhancedCodeAssistantResponse
from store import client, projects_store, dynamic_ast_modifier
from token_usage_manager import global_token_manager, extract_token_usage
from utils.file_ops import (
    get_file_content, update_file_in_project, add_file_to_project, save_file_to_filesystem
)
from services.mcp_tools import MCP_TOOLS, execute_enhanced_mcp_tool


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------

async def analyze_modification_request_with_streaming(
    project,
    user_message: str,
    context: Optional[str],
    stream_output: Callable[[str, str], None]
) -> Dict[str, Any]:
    """Analyze modification request with streaming output"""

    files_list = [f.path for f in project.files]

    stream_output("analysis", f"Analyzing request against {len(files_list)} project files...")

    analysis_prompt = f"""Analyze this code modification request to determine which files need changes.

Available files: {files_list}
User request: {user_message}
Context: {context or "No additional context"}

Determine which files need modification and what type. Be selective - only modify what's necessary.

Return JSON:
{{
  "files_to_modify": [
    {{"file_path": "exact_file_path", "modification_type": "update", "reason": "why modify this file"}}
  ],
  "new_files": [
    {{"file_path": "new_file_path", "reason": "why create this file"}}
  ]
}}"""

    try:
        stream_output("llm_call", "Requesting file analysis from LLM...")

        response_content = ""
        with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=3000,
            temperature=0.1,
            system="You are a code analysis expert. Return only valid JSON.",
            messages=[{"role": "user", "content": analysis_prompt}]
        ) as stream_response:
            for text in stream_response.text_stream:
                response_content += text
                print(text, end='', flush=True)
                if len(response_content) % 100 == 0:
                    stream_output("llm_chunk", f"Analysis response: {len(response_content)} chars...")

        stream_output("llm_complete", "File analysis complete, parsing response...")

        json_match = re.search(r'```json\s*\n(.*?)\n```', response_content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        else:
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_content = response_content[start_idx:end_idx]
            else:
                stream_output("warning", "No JSON found in analysis response")
                return {"files_to_modify": [], "new_files": []}

        result = json.loads(json_content)

        files_to_modify = result.get("files_to_modify", [])
        new_files = result.get("new_files", [])

        stream_output("analysis_result", f"Analysis complete: {len(files_to_modify)} to modify, {len(new_files)} to create")

        return result

    except Exception as e:
        stream_output("error", f"Analysis error: {e}")
        return {"files_to_modify": [], "new_files": []}


async def generate_new_file_content_with_streaming(
    file_path: str,
    user_message: str,
    reason: str,
    client_instance,
    stream_output: Callable[[str, str], None]
) -> str:
    """Generate content for a new file with streaming output"""

    file_extension = file_path.split('.')[-1] if '.' in file_path else ''

    stream_output("generating", f"Generating content for new {file_extension} file: {file_path}")

    system_prompt = f"""Generate complete, working code for a new {file_extension} file.

File: {file_path}
Purpose: {reason}
User Request: {user_message}

Generate clean, well-structured code that fulfills the requirements.
Include appropriate imports, comments, and follow best practices.
Return ONLY the code without explanations."""

    try:
        stream_output("llm_call", f"Requesting LLM to generate {file_path}...")

        response_content = ""
        with client_instance.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            temperature=0.1,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Create new file {file_path}: {user_message}"}]
        ) as stream_response:
            for text in stream_response.text_stream:
                response_content += text
                print(text, end='', flush=True)
                if len(response_content) % 150 == 0:
                    stream_output("llm_chunk", f"Generated {len(response_content)} chars for {file_path}...")

        stream_output("llm_complete", f"Content generation complete for {file_path}")

        code_match = re.search(r'```(?:\w+)?\n(.*?)\n```', response_content, re.DOTALL)
        if code_match:
            extracted_content = code_match.group(1)
            stream_output("code_extracted", f"Extracted {len(extracted_content)} characters of code")
            return extracted_content
        else:
            stream_output("code_direct", f"Using direct response ({len(response_content)} chars)")
            return response_content.strip()

    except Exception as e:
        stream_output("error", f"Error generating {file_path}: {str(e)}")
        return f"# Error generating file content: {str(e)}\n# File: {file_path}\n# Purpose: {reason}"


async def generate_new_file_content_with_streaming_and_tokens(
    file_path: str,
    user_message: str,
    reason: str,
    client_instance,
    stream_output: Callable[[str, str], None]
) -> Dict[str, Any]:
    """Generate content for a new file with streaming output and token tracking"""

    file_extension = file_path.split('.')[-1] if '.' in file_path else ''

    stream_output("generating", f"Generating content for new {file_extension} file: {file_path}")

    system_prompt = f"""Generate complete, working code for a new {file_extension} file.

File: {file_path}
Purpose: {reason}
User Request: {user_message}

Generate clean, well-structured code that fulfills the requirements.
Include appropriate imports, comments, and follow best practices.
Return ONLY the code without explanations."""

    try:
        stream_output("llm_call", f"Requesting LLM to generate {file_path}...")

        response_content = ""
        input_tokens = 0
        output_tokens = 0

        with client_instance.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            temperature=0.1,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Create new file {file_path}: {user_message}"}]
        ) as stream_response:
            for text in stream_response.text_stream:
                response_content += text
                print(text, end='', flush=True)
                if len(response_content) % 150 == 0:
                    stream_output("llm_chunk", f"Generated {len(response_content)} chars for {file_path}...")

            final_message = stream_response.get_final_message()
            input_tokens, output_tokens = extract_token_usage(final_message)

        stream_output("llm_complete", f"Content generation complete for {file_path}")

        code_match = re.search(r'```(?:\w+)?\n(.*?)\n```', response_content, re.DOTALL)
        if code_match:
            extracted_content = code_match.group(1)
            stream_output("code_extracted", f"Extracted {len(extracted_content)} characters of code")
            content = extracted_content
        else:
            stream_output("code_direct", f"Using direct response ({len(response_content)} chars)")
            content = response_content.strip()

        return {
            "content": content,
            "token_usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "operation_type": "file_generation"
            }
        }

    except Exception as e:
        stream_output("error", f"Error generating {file_path}: {str(e)}")
        return {
            "content": f"# Error generating file content: {str(e)}\n# File: {file_path}\n# Purpose: {reason}",
            "token_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "operation_type": "file_generation_failed"
            }
        }


# ---------------------------------------------------------------------------
# MCP plan generation
# ---------------------------------------------------------------------------

async def generate_mcp_style_modification_plan_with_ast(
    project,
    user_message: str,
    context: Optional[str],
    client_instance,
    stream_output: Callable[[str, str], None],
    ast_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate MCP modification plan enhanced with AST information - WITH TOKEN TRACKING"""

    files_list = [f.path for f in project.files]

    ast_context = f"""
AST ANALYSIS CONTEXT:
- Total files analyzed: {ast_summary['total_files']}
- Languages detected: {list(ast_summary.get('languages', {}).keys())}
- Functions found: {ast_summary['total_functions']}
- Classes found: {ast_summary['total_classes']}
- Total lines of code: {ast_summary['total_lines']}

Files with AST data:
{json.dumps(ast_summary['files'][:10], indent=2)}  # First 10 files
"""

    mcp_system_prompt = f"""You are an expert software engineer with access to MCP tools and DYNAMIC AST ANALYSIS for PRECISE CODE MODIFICATION.

{ast_context}

Available MCP Tools:
{json.dumps([{"name": name, "description": tool.description, "input_schema": tool.input_schema} for name, tool in MCP_TOOLS.items()], indent=2)}

Current Project Files: {files_list}
User Request: {user_message}
Context: {context or "No additional context"}

CRITICAL INSTRUCTIONS:
1. RESPOND ONLY WITH VALID JSON - no explanations, no markdown, no extra text
2. Use the AST analysis to identify specific functions/classes to target
3. Be precise about which elements to modify based on AST data
4. Maintain original technology stack and patterns

Response format (JSON only):
{{
  "project_name": "{project.project_name}",
  "modification_type": "update|create|delete|analyze",
  "ast_guided": true,
  "mcp_calls": [
    {{
      "tool": "analyze_requirements",
      "parameters": {{"prompt": "user request with AST guidance", "technology": "detected from AST"}},
      "reasoning": "Understanding requirements with AST context"
    }},
    {{
      "tool": "update_existing_file",
      "parameters": {{"file_path": "specific/file.ext", "modification_type": "ast_precise", "changes_made": ["AST-guided changes"]}},
      "reasoning": "Precise modification using AST targeting"
    }}
  ],
  "expected_outcome": "AST-guided precise modifications"
}}"""

    try:
        stream_output("llm_call", "Generating MCP plan with AST guidance...")

        response_content = ""
        input_tokens = 0
        output_tokens = 0

        with client_instance.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            temperature=0.1,
            system=mcp_system_prompt,
            messages=[{"role": "user", "content": f"Create AST-guided MCP modification plan for: {user_message}"}]
        ) as stream_response:
            for text in stream_response.text_stream:
                response_content += text
                print(text, end='', flush=True)

            final_message = stream_response.get_final_message()
            input_tokens, output_tokens = extract_token_usage(final_message)

        stream_output("llm_complete", "AST-guided MCP plan generation complete")

        if input_tokens > 0 or output_tokens > 0:
            stream_output("token_usage", f"Planning phase: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total tokens")

        json_match = re.search(r'```json\s*\n(.*?)\n```', response_content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        else:
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_content = response_content[start_idx:end_idx]
            else:
                raise ValueError("No JSON found in AST-guided MCP plan response")

        mcp_plan = json.loads(json_content)

        mcp_plan["token_usage"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "operation_type": "mcp_planning"
        }

        return mcp_plan

    except Exception as e:
        stream_output("error", f"AST-guided MCP plan generation failed: {e}")
        return {
            "project_name": project.project_name,
            "modification_type": "error",
            "ast_guided": False,
            "mcp_calls": [],
            "expected_outcome": f"Failed to generate AST-guided MCP plan: {str(e)}",
            "token_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "operation_type": "mcp_planning_failed"
            }
        }


# ---------------------------------------------------------------------------
# Information request handler
# ---------------------------------------------------------------------------

async def handle_information_request(
    project_id: str,
    project,
    user_message: str,
    ast_summary: Dict[str, Any]
):
    """Handle information/explanation requests about the project"""

    information_prompt = f"""The user wants information about this project.

PROJECT: {project.project_name}
FILES: {[f.path for f in project.files]}
AST SUMMARY:
- {ast_summary['total_files']} files
- {ast_summary['total_functions']} functions
- {ast_summary['total_classes']} classes
- {ast_summary['total_lines']} lines of code
- Languages: {list(ast_summary.get('languages', {}).keys())}

INSTRUCTIONS:
- Focus on what the project does, how it works, its structure
- Be descriptive and informative
- Do NOT suggest code changes
- This is purely informational

Answer the user's question about this project:"""

    try:
        response_content = ""
        with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.2,
            system="You are a helpful project analyst providing information and explanations about code projects. You explain what projects do, how they work, and their structure. You do not make code changes.",
            messages=[{"role": "user", "content": information_prompt + "\n\n" + user_message}]
        ) as stream_response:
            for text in stream_response.text_stream:
                response_content += text

        return {
            "success": True,
            "action_taken": "explanation",
            "explanation": response_content.strip(),
            "affected_files": [],
            "new_files": [],
            "deleted_files": [],
            "changes_summary": [],
            "next_steps": [],
            "mcp_calls_made": [],
            "is_information_request": True
        }

    except Exception as e:
        return {
            "success": False,
            "action_taken": "error",
            "explanation": f"Error generating explanation: {str(e)}",
            "affected_files": [],
            "new_files": [],
            "deleted_files": [],
            "changes_summary": [],
            "next_steps": [],
            "mcp_calls_made": [],
            "is_information_request": True
        }


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

async def detect_user_intent_and_respond(
    project_id: str,
    user_message: str,
    context: Optional[str] = None
):
    """Detect if user wants information/explanation vs code modification"""

    if not client:
        raise Exception("Anthropic API client not initialized")

    if project_id not in projects_store:
        raise ValueError(f"Project {project_id} not found")

    project = projects_store[project_id]

    ast_summary = dynamic_ast_modifier.get_project_ast_summary(project_id, project.project_name)

    intent_detection_prompt = f"""Analyze this user message to determine their intent.

USER MESSAGE: "{user_message}"

PROJECT CONTEXT:
- Project Name: {project.project_name}
- Files: {len(project.files)}
- Functions: {ast_summary['total_functions']}
- Classes: {ast_summary['total_classes']}

INSTRUCTIONS:
Determine if the user wants:
1. INFORMATION/EXPLANATION - They want to understand, learn about, or get descriptions of the project
2. CODE_MODIFICATION - They want to change, add, delete, or modify code

INFORMATION/EXPLANATION keywords: describe, explain, what does, how does, tell me about, show me, understand, documentation, overview, summary, analyze
CODE_MODIFICATION keywords: add, create, fix, change, update, modify, delete, remove, implement, build

Respond with exactly one word: either "INFORMATION" or "CODE_MODIFICATION"
"""

    try:
        response_content = ""
        with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=50,
            temperature=0.1,
            system="You are an intent classifier. Respond with exactly one word: INFORMATION or CODE_MODIFICATION",
            messages=[{"role": "user", "content": intent_detection_prompt}]
        ) as stream_response:
            for text in stream_response.text_stream:
                response_content += text

        intent = response_content.strip().upper()

        if "INFORMATION" in intent:
            return await handle_information_request(project_id, project, user_message, ast_summary)
        else:
            return await process_intelligent_code_request_with_dynamic_ast(project_id, user_message, context)

    except Exception as e:
        return {
            "success": False,
            "action_taken": "error",
            "explanation": f"Error processing request: {str(e)}",
            "affected_files": [],
            "new_files": [],
            "deleted_files": [],
            "changes_summary": [],
            "next_steps": [],
            "mcp_calls_made": [],
            "token_usage": None
        }


# ---------------------------------------------------------------------------
# Main code request processor
# ---------------------------------------------------------------------------

async def process_intelligent_code_request_with_dynamic_ast(
    project_id: str,
    user_message: str,
    context: Optional[str] = None
) -> EnhancedCodeAssistantResponse:
    """Process user message with dynamic AST caching and MCP streaming - WITH TOKEN TRACKING"""

    if not client:
        raise Exception("Anthropic API client not initialized")

    if project_id not in projects_store:
        raise ValueError(f"Project {project_id} not found")

    project = projects_store[project_id]
    total_input_tokens = 0
    total_output_tokens = 0

    def stream_output(message_type: str, content: str):
        """MCP-style streaming output with AST cache info"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if message_type == "cache_check":
            print(f"[{timestamp}] [AST_CACHE] {content}")
        elif message_type == "ast_loaded":
            print(f"[{timestamp}] [AST_LOADED] {content}")
        elif message_type == "modifying":
            print(f"[{timestamp}] [AST_MODIFY] {content}")
        elif message_type == "mcp_analysis":
            print(f"Making MCP-enabled code modification analysis with AST caching...")
            print(content)
        elif message_type == "token_usage":
            print(f"[{timestamp}] [TOKEN_USAGE] {content}")
        else:
            print(f"[{timestamp}] [{message_type.upper()}] {content}")

    try:
        stream_output("mcp_analysis", "Starting MCP-enhanced code modification with dynamic AST caching...")

        ast_summary = dynamic_ast_modifier.get_project_ast_summary(project_id, project.project_name)
        stream_output("ast_loaded", f"Project AST: {ast_summary['total_files']} files, {ast_summary['total_functions']} functions, {ast_summary['total_classes']} classes")

        mcp_plan = await generate_mcp_style_modification_plan_with_ast(
            project, user_message, context, client, stream_output, ast_summary
        )

        planning_token_usage = mcp_plan.get("token_usage", {})
        planning_input_tokens = planning_token_usage.get("input_tokens", 0)
        planning_output_tokens = planning_token_usage.get("output_tokens", 0)

        total_input_tokens += planning_input_tokens
        total_output_tokens += planning_output_tokens

        if planning_input_tokens > 0 or planning_output_tokens > 0:
            stream_output("token_usage", f"Planning phase consumed: {planning_input_tokens + planning_output_tokens} tokens")

        plan_display = {k: v for k, v in mcp_plan.items() if k != "token_usage"}
        stream_output("mcp_analysis", json.dumps(plan_display, indent=2))

        affected_files = []
        new_files_created = []
        changes_summary = []
        mcp_calls_made = []

        for mcp_call in mcp_plan.get("mcp_calls", []):
            tool_name = mcp_call["tool"]
            parameters = mcp_call["parameters"]
            reasoning = mcp_call.get("reasoning", "")

            stream_output("mcp_execution", f"{tool_name} - {reasoning}")

            try:
                if tool_name == "update_existing_file":
                    file_path = parameters["file_path"]

                    current_content = get_file_content(project, file_path)

                    modification_result = dynamic_ast_modifier.apply_targeted_modification_with_caching(
                        project_id=project_id,
                        project_name=project.project_name,
                        file_path=file_path,
                        file_content=current_content,
                        user_message=user_message,
                        client=client,
                        stream_callback=stream_output
                    )

                    if 'token_usage' in modification_result:
                        mod_input = modification_result['token_usage'].get('input_tokens', 0)
                        mod_output = modification_result['token_usage'].get('output_tokens', 0)
                        total_input_tokens += mod_input
                        total_output_tokens += mod_output

                        if mod_input > 0 or mod_output > 0:
                            stream_output("token_usage", f"File modification consumed: {mod_input + mod_output} tokens")

                    if modification_result["success"]:
                        update_file_in_project(project, file_path, modification_result["modified_content"])
                        await save_file_to_filesystem(project, file_path, modification_result["modified_content"])

                        affected_files.append(file_path)
                        changes_summary.extend(modification_result["changes"])

                        stream_output("mcp_result", f"File updated: {file_path} (using {modification_result['parser_used']})")
                    else:
                        stream_output("mcp_result", f"Failed to update: {file_path}")

                elif tool_name == "create_new_file":
                    file_path = parameters["file_path"]

                    if "content" in parameters:
                        content = parameters["content"]
                    else:
                        content_result = await generate_new_file_content_with_streaming_and_tokens(
                            file_path, user_message, reasoning, client, stream_output
                        )

                        if isinstance(content_result, dict) and "token_usage" in content_result:
                            gen_input = content_result['token_usage'].get('input_tokens', 0)
                            gen_output = content_result['token_usage'].get('output_tokens', 0)
                            total_input_tokens += gen_input
                            total_output_tokens += gen_output

                            if gen_input > 0 or gen_output > 0:
                                stream_output("token_usage", f"File generation consumed: {gen_input + gen_output} tokens")

                            content = content_result.get("content", "")
                        else:
                            content = content_result

                    add_file_to_project(project, file_path, content)
                    await save_file_to_filesystem(project, file_path, content)

                    dynamic_ast_modifier.refresh_file_ast(project_id, project.project_name, file_path, content)

                    new_files_created.append(file_path)
                    changes_summary.append(f"Created new file: {file_path}")

                    stream_output("mcp_result", f"File created: {file_path} (AST cached)")

                elif tool_name == "analyze_requirements":
                    result = {
                        "type": "requirements_analyzed_with_ast",
                        "ast_summary": ast_summary,
                        "analysis": parameters.get("prompt", ""),
                        "technology": parameters.get("technology", "")
                    }
                    stream_output("mcp_result", "Requirements analyzed with AST context")

                mcp_calls_made.append({
                    "tool": tool_name,
                    "success": True,
                    "description": reasoning
                })

            except Exception as tool_error:
                stream_output("mcp_result", f"Error with {tool_name}: {str(tool_error)}")
                mcp_calls_made.append({
                    "tool": tool_name,
                    "success": False,
                    "error": str(tool_error)
                })

        token_usage_record = None
        if total_input_tokens > 0 or total_output_tokens > 0:
            token_usage_record = global_token_manager.record_usage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                operation_type="code_assistant",
                project_id=project_id
            )
            print(f"[DEBUG] Code assistant total token usage: {token_usage_record.total_tokens} tokens, ~${token_usage_record.cost_estimate:.4f}")
            stream_output("token_usage", f"Total session usage: {total_input_tokens} input + {total_output_tokens} output = {total_input_tokens + total_output_tokens} tokens (~${token_usage_record.cost_estimate:.4f})")

        if new_files_created:
            action_taken = "create"
        elif affected_files:
            action_taken = "update"
        else:
            action_taken = "analyze"

        summary = {
            "project_name": project.project_name,
            "mcp_operations_completed": len(mcp_calls_made),
            "files_modified": len(affected_files),
            "files_created": len(new_files_created),
            "total_changes": len(changes_summary),
            "ast_cache_used": True,
            "cached_files": ast_summary['total_files'],
            "token_usage": {
                'input_tokens': total_input_tokens,
                'output_tokens': total_output_tokens,
                'total_tokens': total_input_tokens + total_output_tokens,
                'cost_estimate': token_usage_record.cost_estimate if token_usage_record else 0.0,
                'breakdown': {
                    'planning': planning_input_tokens + planning_output_tokens,
                    'modifications': (total_input_tokens + total_output_tokens) - (planning_input_tokens + planning_output_tokens)
                }
            } if token_usage_record else None
        }

        stream_output("mcp_summary", json.dumps(summary, indent=2))
        stream_output("mcp_summary", "MCP-enhanced code modification with AST caching completed successfully")

        return EnhancedCodeAssistantResponse(
            success=True,
            action_taken=action_taken,
            affected_files=affected_files,
            new_files=new_files_created,
            deleted_files=[],
            explanation="Completed MCP-enhanced code modifications with dynamic AST caching for precision targeting.",
            changes_summary=changes_summary,
            next_steps=[
                "Review the AST-guided changes",
                "Test the modified functionality",
                "AST cache updated automatically",
                f"Total MCP operations: {len(mcp_calls_made)} completed with AST assistance"
            ],
            mcp_calls_made=mcp_calls_made,
            token_usage=summary.get("token_usage")
        )

    except Exception as e:
        stream_output("error", f"MCP processing with AST caching failed: {str(e)}")
        return EnhancedCodeAssistantResponse(
            success=False,
            action_taken="error",
            affected_files=[],
            new_files=[],
            deleted_files=[],
            explanation=f"Error during MCP-enhanced code processing with AST caching: {str(e)}",
            changes_summary=[],
            next_steps=["Check the error logs", "Try rephrasing your request"],
            mcp_calls_made=[],
            token_usage=None
        )
