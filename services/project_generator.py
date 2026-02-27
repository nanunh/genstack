import json
import re
import uuid
from datetime import datetime
from typing import Optional

from models import FileContent, ProjectResponse
from store import client, ANTHROPIC_API_KEY
from token_usage_manager import global_token_manager, extract_token_usage
from services.mcp_tools import MCP_TOOLS, execute_mcp_tool
from utils.project_runner import generate_package_json, generate_readme


async def create_project_with_mcp_streaming(
    prompt: str,
    project_name: Optional[str] = None
) -> ProjectResponse:
    """Generate project using Anthropic API with MCP tools - WITH TOKEN TRACKING"""

    if not client:
        raise Exception("Anthropic API client not initialized. Please set ANTHROPIC_API_KEY environment variable.")

    mcp_system_prompt = f"""You are an expert software engineer and UI/UX designer with access to MCP tools for DYNAMIC CODE GENERATION.

CRITICAL INSTRUCTIONS:
1. RESPOND ONLY WITH VALID JSON - no explanations, no markdown, no extra text
2. FOLLOW USER TECHNOLOGY REQUIREMENTS EXACTLY - do not substitute or add frameworks
3. If user specifies "HTML, CSS, JS with Python Flask" - use ONLY these technologies
4. Do NOT add Jinja templates unless explicitly requested
5. Create files dynamically based on the EXACT user request with SPECIFIED technologies

USER TECHNOLOGY REQUIREMENTS: {prompt}

TECHNOLOGY ENFORCEMENT RULES:
- If user says "HTML, CSS, JS" - create separate .html, .css, .js files
- If user says "Flask" - create Python Flask routes that serve static files
- If user says "no Jinja" - do not use template rendering
- If user specifies database - use only that database type
- Do not add frameworks, libraries, or patterns not requested

UI/UX DESIGN RULES (apply to ALL frontend files — HTML, CSS, JS, React, Vue, etc.):
- NEVER generate plain or bare UI. Every project must look professionally designed.
- Use a modern, attractive color palette: rich primary colors, complementary accents, subtle neutrals
- Apply gradients on hero sections, headers, buttons, and backgrounds where appropriate
- Use Google Fonts (import via @import in CSS) — prefer Inter, Poppins, or Nunito for body text
- Add smooth CSS transitions and hover effects on all interactive elements (buttons, cards, links, inputs)
- Use CSS custom properties (variables) for consistent theming: --primary, --accent, --bg, --text, etc.
- Layout: use CSS Grid or Flexbox for all layouts — never use tables for layout
- Cards and containers: rounded corners (border-radius 8–16px), subtle box-shadows, proper padding
- Buttons: gradient backgrounds, border-radius, padding, hover lift effect (transform + box-shadow)
- Forms and inputs: styled with borders, focus rings, padding, placeholder styling
- Add a sticky/fixed navbar with logo, navigation links, and a call-to-action button
- Use icons from Font Awesome (CDN link in HTML head) for visual enhancement
- Include micro-animations: fade-in on page load, subtle scale on hover, smooth scrolling
- Ensure full responsiveness: mobile-first CSS with media queries for tablet and desktop
- Color contrast must be accessible (WCAG AA minimum)
- Overall aesthetic: modern SaaS / professional product — NOT a basic HTML exercise

Available MCP Tools:
{json.dumps([{"name": name, "description": tool.description, "input_schema": tool.input_schema} for name, tool in MCP_TOOLS.items()], indent=2)}

Response format (JSON only):
{{
  "project_name": "project-name",
  "mcp_calls": [
    {{
      "tool": "analyze_requirements",
      "parameters": {{"prompt": "user exact request", "technology": "user specified tech only"}},
      "reasoning": "Understanding exact user requirements"
    }},
    {{
      "tool": "create_file",
      "parameters": {{"path": "file.ext", "content": "complete file content using ONLY specified technologies"}},
      "reasoning": "Create file with user-specified tech stack and professional UI"
    }}
  ],
  "instructions": "setup instructions using only specified technologies"
}}"""

    print("[DEBUG] Making MCP-enabled streaming API call with token tracking...")

    try:
        response_content = ""
        input_tokens = 0
        output_tokens = 0

        with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=50000,
            temperature=0.1,
            system=mcp_system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Create a complete, production-ready project for: {prompt}\n\nUse MCP tools to build the project structure systematically."
                }
            ]
        ) as stream:
            for text in stream.text_stream:
                response_content += text
                print(text, end='', flush=True)

            final_message = stream.get_final_message()
            input_tokens, output_tokens = extract_token_usage(final_message)

            if input_tokens > 0 or output_tokens > 0:
                print(f"\n[TOKEN USAGE] Input: {input_tokens}, Output: {output_tokens}, Total: {input_tokens + output_tokens}")
            else:
                print(f"\n[DEBUG] Token usage not available in response")

        print(f"\n[DEBUG] Got streaming response, length: {len(response_content)}")

        json_match = re.search(r'```json\s*\n(.*?)\n```', response_content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        else:
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_content = response_content[start_idx:end_idx]
            else:
                raise ValueError("No JSON found in response")

        project_plan = json.loads(json_content)
        print(f"[DEBUG] Parsed project plan: {len(project_plan.get('mcp_calls', []))} MCP calls")

        files = []
        dependencies = {"npm": [], "pip": []}

        for call in project_plan.get("mcp_calls", []):
            tool_name = call["tool"]
            parameters = call["parameters"]
            reasoning = call.get("reasoning", "")

            print(f"[DEBUG] Executing MCP tool: {tool_name} - {reasoning}")

            try:
                result = await execute_mcp_tool(tool_name, parameters)

                if result["type"] == "file_created":
                    files.append(FileContent(
                        path=result["path"],
                        content=result["content"],
                        is_binary=False
                    ))
                    print(f"[DEBUG] Created file: {result['path']} ({len(result['content'])} chars)")

                elif result["type"] == "dependency_added":
                    package_manager = result.get("package_manager", "npm")
                    if package_manager in dependencies:
                        dependencies[package_manager].append(result["dependency"])
                        print(f"[DEBUG] Added {package_manager} dependency: {result['dependency']}")

            except Exception as tool_error:
                print(f"[DEBUG] MCP tool error: {tool_error}")
                continue

        if dependencies["npm"] and not any(f.path == "package.json" for f in files):
            package_json_content = generate_package_json(project_plan.get("project_name", "project"), dependencies["npm"])
            files.append(FileContent(path="package.json", content=package_json_content, is_binary=False))

        if dependencies["pip"] and not any(f.path == "requirements.txt" for f in files):
            requirements_content = "\n".join(dependencies["pip"]) + "\n"
            files.append(FileContent(path="requirements.txt", content=requirements_content, is_binary=False))

        if not any(f.path == "README.md" for f in files):
            readme_content = generate_readme(project_plan.get("project_name", "project"), prompt)
            files.append(FileContent(path="README.md", content=readme_content, is_binary=False))

        token_usage_record = None
        if input_tokens > 0 or output_tokens > 0:
            token_usage_record = global_token_manager.record_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                operation_type="project_generation"
            )
            print(f"[DEBUG] Token usage recorded: {token_usage_record.total_tokens} tokens, ~${token_usage_record.cost_estimate:.4f}")

        project_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        final_project_name = project_name or project_plan.get("project_name", "generated-project")
        final_project_name = re.sub(r'[^\w\-_]', '_', final_project_name.lower())

        project_response = ProjectResponse(
            project_id=project_id,
            project_name=final_project_name,
            files=files,
            instructions=project_plan.get("instructions", f"Project created with {len(project_plan.get('mcp_calls', []))} MCP tool calls"),
            created_at=created_at,
            token_usage={
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'cost_estimate': token_usage_record.cost_estimate if token_usage_record else 0.0,
                'operation_type': 'project_generation'
            } if token_usage_record else None
        )

        return project_response

    except Exception as e:
        print(f"[DEBUG] MCP project generation failed: {e}")
        raise Exception(f"Failed to generate project with MCP tools: {str(e)}")


async def create_project_from_files_streaming(
    files_data: dict,
    analysis_prompt: str = None,
    project_name: Optional[str] = None
) -> ProjectResponse:
    """Generate project based on uploaded files using streaming"""

    if not client:
        raise Exception("Anthropic API client not initialized. Please set ANTHROPIC_API_KEY environment variable.")

    files_summary = []
    for file_path, file_info in files_data['files'].items():
        files_summary.append(f"**{file_path}** ({file_info['size']} bytes, {file_info['type']}):")
        if file_info['type'] == 'text' and len(file_info['content']) < 2000:
            files_summary.append(f"```\n{file_info['content']}\n```")
        elif file_info['type'] == 'text':
            files_summary.append(f"```\n{file_info['content'][:1000]}...\n[truncated - {file_info['size']} total bytes]\n```")
        else:
            files_summary.append(f"[Binary file - {file_info['size']} bytes]")
        files_summary.append("")

    files_content = "\n".join(files_summary)

    mcp_system_prompt = f"""You are an expert software engineer analyzing uploaded project files and creating an IMPROVED version using MCP tools.

Available MCP Tools:
{json.dumps([{"name": name, "description": tool.description, "input_schema": tool.input_schema} for name, tool in MCP_TOOLS.items()], indent=2)}

ANALYSIS TASK:
1. Analyze the uploaded files to understand the project structure and purpose
2. Identify areas for improvement (better structure, missing files, updated dependencies, etc.)
3. Create an ENHANCED version of the project with improvements

USER REQUEST: {analysis_prompt or "Analyze and improve this project"}

UPLOADED FILES ANALYSIS:
Total files: {files_data['total_files']}
Total size: {files_data['total_size']} bytes

FILE CONTENTS:
{files_content}

INSTRUCTIONS:
1. RESPOND ONLY WITH VALID JSON - no explanations, no markdown, no extra text
2. Analyze the existing code and create an IMPROVED version
3. Fix any issues, update dependencies, improve structure
4. Add missing files that would benefit the project
5. Keep the core functionality but enhance it

Response format (JSON only):
{{
  "project_name": "improved-project-name",
  "mcp_calls": [
    {{
      "tool": "analyze_requirements",
      "parameters": {{"prompt": "analysis summary", "technology": "detected tech"}},
      "reasoning": "Understanding existing project"
    }},
    {{
      "tool": "create_file",
      "parameters": {{"path": "file.ext", "content": "improved file content"}},
      "reasoning": "Creating improved version"
    }}
  ],
  "instructions": "Setup and run instructions"
}}"""

    print("[DEBUG] Making file-based MCP streaming API call...")

    try:
        response_content = ""
        input_tokens = 0
        output_tokens = 0

        with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=50000,
            temperature=0.1,
            system=mcp_system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Analyze these uploaded files and create an improved project version.\n\nUser request: {analysis_prompt or 'Create an enhanced version of this project'}"
                }
            ]
        ) as stream:
            for text in stream.text_stream:
                response_content += text
                print(text, end='', flush=True)

            final_message = stream.get_final_message()
            if hasattr(final_message, 'usage'):
                input_tokens = final_message.usage.input_tokens
                output_tokens = final_message.usage.output_tokens
                total_tokens = input_tokens + output_tokens

                print(f"\n[TOKEN USAGE] Input tokens: {input_tokens}")
                print(f"[TOKEN USAGE] Output tokens: {output_tokens}")
                print(f"[TOKEN USAGE] Total tokens: {total_tokens}")

        print(f"\n[DEBUG] Got file-based streaming response, length: {len(response_content)}")

        json_match = re.search(r'```json\s*\n(.*?)\n```', response_content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        else:
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_content = response_content[start_idx:end_idx]
            else:
                raise ValueError("No JSON found in response")

        project_plan = json.loads(json_content)
        print(f"[DEBUG] Parsed file-based project plan: {len(project_plan.get('mcp_calls', []))} MCP calls")

        files = []
        dependencies = {"npm": [], "pip": []}

        for call in project_plan.get("mcp_calls", []):
            tool_name = call["tool"]
            parameters = call["parameters"]
            reasoning = call.get("reasoning", "")

            print(f"[DEBUG] Executing MCP tool: {tool_name} - {reasoning}")

            try:
                result = await execute_mcp_tool(tool_name, parameters)

                if result["type"] == "file_created":
                    files.append(FileContent(
                        path=result["path"],
                        content=result["content"],
                        is_binary=False
                    ))
                    print(f"[DEBUG] Created improved file: {result['path']} ({len(result['content'])} chars)")

                elif result["type"] == "dependency_added":
                    package_manager = result.get("package_manager", "npm")
                    if package_manager in dependencies:
                        dependencies[package_manager].append(result["dependency"])
                        print(f"[DEBUG] Added {package_manager} dependency: {result['dependency']}")

            except Exception as tool_error:
                print(f"[DEBUG] MCP tool error: {tool_error}")
                continue

        if dependencies["npm"] and not any(f.path == "package.json" for f in files):
            package_json_content = generate_package_json(project_plan["project_name"], dependencies["npm"])
            files.append(FileContent(path="package.json", content=package_json_content, is_binary=False))

        if dependencies["pip"] and not any(f.path == "requirements.txt" for f in files):
            requirements_content = "\n".join(dependencies["pip"]) + "\n"
            files.append(FileContent(path="requirements.txt", content=requirements_content, is_binary=False))

        if not any(f.path == "README.md" for f in files):
            readme_content = generate_readme(
                project_plan["project_name"],
                analysis_prompt or "Project improved from uploaded files"
            )
            files.append(FileContent(path="README.md", content=readme_content, is_binary=False))

        project_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        final_project_name = project_name or project_plan.get("project_name", "improved-project")
        final_project_name = re.sub(r'[^\w\-_]', '_', final_project_name.lower())

        return ProjectResponse(
            project_id=project_id,
            project_name=final_project_name,
            files=files,
            instructions=project_plan.get("instructions", f"Improved project created from {files_data['total_files']} uploaded files"),
            created_at=created_at
        )

    except Exception as e:
        print(f"[DEBUG] File-based MCP project generation failed: {e}")
        raise Exception(f"Failed to generate project from files: {str(e)}")