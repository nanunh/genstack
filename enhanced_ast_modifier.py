"""
Enhanced AST Modifier with Dynamic JSON Caching
Uses cached AST trees stored as JSON for fast modifications
"""

from typing import Dict, List, Any, Optional, Callable
from ast_cache_manager import global_ast_cache, ASTNodeInfo, FileASTInfo
from multiLanguageASTParser import MultiLanguageASTProcessor

class DynamicASTModifier:
    """AST Modifier that uses dynamic JSON caching for performance"""
    
    def __init__(self):
        self.ast_processor = MultiLanguageASTProcessor()
        self.cache_manager = global_ast_cache

    def _detect_syntax_error_type(self, user_message: str, file_content: str) -> str:
        """Detect specific syntax error types for smarter fixing"""
        
        message_lower = user_message.lower()
        
        # Check for common syntax errors
        if "return outside of function" in message_lower:
            # Look for misplaced return statements
            lines = file_content.split('\n')
            for i, line in enumerate(lines):
                if 'return' in line and not self._is_inside_function(lines, i):
                    return "misplaced_return"
        
        if "missing" in message_lower and ("brace" in message_lower or "bracket" in message_lower):
            return "missing_brace"
        
        return "general_syntax_error"

    def _is_inside_function(self, lines: List[str], return_line_index: int) -> bool:
        """Check if a return statement is properly inside a function"""
        # Count braces backwards from the return statement
        brace_count = 0
        in_function = False
        
        for i in range(return_line_index, -1, -1):
            line = lines[i].strip()
            if 'const ' in line and '= (' in line and '=>' in line:
                in_function = True
            elif line.endswith('{'):
                brace_count += 1
            elif line == '}' or line.endswith('}'):
                brace_count -= 1
                if brace_count < 0 and in_function:
                    return False  # We've exited the function
        
        return in_function and brace_count >= 0
    
    def _fix_syntax_error_smart(self, file_content: str, error_type: str, user_message: str) -> str:
        """Smart syntax error fixing without multiple LLM calls"""
        
        if error_type == "misplaced_return":
            lines = file_content.split('\n')
            
            # Find the problematic return statement
            for i, line in enumerate(lines):
                if 'return (' in line.strip() and not self._is_inside_function(lines, i):
                    # Look backwards for the function that needs a closing brace
                    for j in range(i-1, -1, -1):
                        if ('const ' in lines[j] and '= (' in lines[j]) or 'function ' in lines[j]:
                            # Find where this function should end
                            brace_count = 0
                            for k in range(j+1, i):
                                if '{' in lines[k]:
                                    brace_count += 1
                                if '}' in lines[k]:
                                    brace_count -= 1
                            
                            # If brace_count > 0, we need to add closing braces
                            if brace_count > 0:
                                # Add the missing closing brace before the return
                                lines.insert(i, '  };')  # Add proper indentation
                                break
                            break
                    
                    break
            
            return '\n'.join(lines)
        
        return file_content  # Fallback to original if we can't fix it
    
    def apply_targeted_modification_with_caching(self, 
                                           project_id: str,
                                           project_name: str,
                                           file_path: str,
                                           file_content: str,
                                           user_message: str,
                                           client,
                                           stream_callback: Callable[[str, str], None] = None) -> Dict[str, Any]:
        """Apply modifications using cached AST data"""
        
        def stream(message_type: str, content: str):
            if stream_callback:
                stream_callback(message_type, content)
            print(f"[{message_type.upper()}] {content}")
        
        error_type = self._detect_syntax_error_type(user_message, file_content)
    
        if error_type != "general_syntax_error":
            stream("smart_fix", f"Detected {error_type}, applying smart fix...")
            
            # Try smart fix first
            fixed_content = self._fix_syntax_error_smart(file_content, error_type, user_message)
            
            if fixed_content != file_content:
                return {
                    "success": True,
                    "original_content": file_content,
                    "modified_content": fixed_content,
                    "changes": [f"Applied smart fix for {error_type}"],
                    "modification_type": "smart_syntax_fix",
                    "targets_modified": 1,
                    "parser_used": "smart_syntax_fixer"
                }
        
        # Get project cache
        project_cache = self.cache_manager.get_project_cache(project_id, project_name)
        
        stream("cache_check", f"Checking AST cache for {file_path}")
        
        # Get or parse AST
        file_ast = project_cache.get_or_parse_ast(file_path, file_content, self.ast_processor)
        
        if not file_ast:
            stream("error", "Failed to get AST information")
            return {"success": False, "error": "AST parsing failed"}
        
        stream("ast_loaded", f"AST loaded: {len(file_ast.functions)} functions, {len(file_ast.classes)} classes")
        
        # Analyze modification intent using cached AST
        analysis = self._analyze_modification_intent_from_cache(file_ast, user_message)
        
        stream("analysis", f"Modification type: {analysis['modification_type']}")
        stream("analysis", f"Target elements: {len(analysis['targets'])}")
        
        if analysis['targets']:
            target_names = [t['name'] for t in analysis['targets']]
            stream("analysis", f"Targets found: {', '.join(target_names)}")
        
        # Apply modifications
        if analysis['targets']:
            return self._apply_cached_ast_modifications(
                file_content, file_ast, analysis, user_message, client, stream
            )
        else:
            # No specific targets - general modification
            return self._apply_general_modification(
                file_content, file_ast, user_message, client, stream
            )
        
      
    
    def _analyze_modification_intent_from_cache(self, file_ast: FileASTInfo, user_message: str) -> Dict[str, Any]:
        """Analyze modification intent using cached AST data"""
        
        modification_type = self._detect_modification_type(user_message)
        targets = self._extract_targets_from_cached_ast(file_ast, user_message)
        
        return {
            "modification_type": modification_type,
            "language": file_ast.language,
            "targets": targets,
            "file_ast": file_ast,
            "is_syntax_fix": self._is_syntax_error_fix(user_message)
        }
    
    def _extract_targets_from_cached_ast(self, file_ast: FileASTInfo, user_message: str) -> List[Dict[str, Any]]:
        """Extract target elements from cached AST - DEDUPLICATED VERSION"""
    
        targets = []
        message_lower = user_message.lower()
        seen_targets = set()  # Add this to prevent duplicates
        
        # Keywords to ignore
        ignore_keywords = {
            'if', 'else', 'elif', 'for', 'while', 'do', 'switch', 'case', 'break', 
            'continue', 'return', 'try', 'catch', 'finally', 'throw', 'new', 'var', 
            'let', 'const', 'function', 'class', 'import', 'export', 'default'
        }
        
        # Check functions
        for func in file_ast.functions:
            func_name = func.name
            target_key = f"function:{func_name}:{func.start_line}"  # Unique key
            
            if (func_name and 
                target_key not in seen_targets and  # Check for duplicates
                func_name.lower() not in ignore_keywords and
                len(func_name) > 2 and
                (func_name.lower() in message_lower or 
                any(keyword in message_lower for keyword in ['function', 'method']))):
                
                targets.append({
                    "type": "function",
                    "name": func_name,
                    "start_line": func.start_line,
                    "end_line": func.end_line,
                    "start_byte": func.start_byte,
                    "end_byte": func.end_byte,
                    "element": func,
                    "file_path": func.file_path
                })
                seen_targets.add(target_key)
        
        return targets
    
    def _apply_cached_ast_modifications(self, 
                                       file_content: str, 
                                       file_ast: FileASTInfo, 
                                       analysis: Dict[str, Any], 
                                       user_message: str,
                                       client,
                                       stream: Callable[[str, str], None]) -> Dict[str, Any]:
        """Apply modifications using cached AST information"""
        
        lines = file_content.split('\n')
        changes = []
        
        # Sort targets by end line (descending) to avoid offset issues
        targets = sorted(analysis['targets'], key=lambda x: x['end_line'], reverse=True)
        
        stream("processing", f"Applying modifications to {len(targets)} elements")
        
        for i, target in enumerate(targets):
            element_name = target['name']
            element_type = target['type']
            start_line = target['start_line'] - 1  # Convert to 0-based
            end_line = target['end_line'] - 1
            
            stream("modifying", f"Modifying {element_type} '{element_name}' at lines {start_line+1}-{end_line+1} ({i+1}/{len(targets)})")
            
            # Extract original section
            if end_line < len(lines):
                original_section = '\n'.join(lines[start_line:end_line + 1])
            else:
                # Handle edge case where end_line exceeds file length
                original_section = '\n'.join(lines[start_line:])
                end_line = len(lines) - 1
            
            # Generate modified section
            modified_section = self._generate_section_modification_with_context(
                original_section, target, user_message, file_ast, client, stream
            )
            
            if modified_section and modified_section.strip() != original_section.strip():
                # Apply modification
                modified_lines = modified_section.split('\n')
                lines[start_line:end_line + 1] = modified_lines
                
                changes.append(f"Modified {element_type} '{element_name}' at line {start_line + 1}")
                stream("success", f"Successfully modified {element_type} '{element_name}'")
            else:
                stream("unchanged", f"No changes needed for {element_type} '{element_name}'")
        
        modified_content = '\n'.join(lines)
        
        return {
            "success": True,
            "original_content": file_content,
            "modified_content": modified_content,
            "changes": changes,
            "modification_type": analysis["modification_type"],
            "targets_modified": len([c for c in changes if "Modified" in c]),
            "parser_used": f"cached_ast_{file_ast.parser_type}"
        }
    
    def _generate_section_modification_with_context(self, 
                                                   original_section: str,
                                                   target: Dict[str, Any],
                                                   user_message: str,
                                                   file_ast: FileASTInfo,
                                                   client,
                                                   stream: Callable[[str, str], None]) -> str:
        """Generate modified section with full AST context"""
        
        element = target['element']
        
        # Build context from AST
        context_info = self._build_modification_context(element, file_ast)
        
        system_prompt = f"""You are modifying a specific {target['type']} in {file_ast.language} code with STRICT USER INSTRUCTION ENFORCEMENT.

ORIGINAL TECHNOLOGY STACK ENFORCEMENT:
- Language: {file_ast.language}
- Parser: {file_ast.parser_type}
- MAINTAIN the exact same technology stack and patterns
- DO NOT substitute, "improve", or add technologies not requested

AST CONTEXT:
{context_info}

MODIFICATION RULES:
1. Return ONLY the modified {target['type']} code
2. Maintain the same indentation level as the original
3. Keep the same technology stack and import patterns
4. Only modify what's necessary based on the user request
5. Preserve the original code structure and style

Original {target['type']} ({file_ast.language}):
```{file_ast.language}
{original_section}
```

User request: {user_message}

ENFORCE: Use the same technologies as the original code. Do not change the tech stack."""

        try:
            stream("llm_call", f"Generating modification for {target['name']} with AST context")
            
            response_content = ""
            with client.messages.stream(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
                temperature=0.1,
                system=system_prompt,
                messages=[{
                    "role": "user", 
                    "content": f"Modify the {target['type']} '{target['name']}' according to this request: {user_message}"
                }]
            ) as stream_response:
                for text in stream_response.text_stream:
                    response_content += text
                    if len(response_content) % 100 == 0:
                        stream("llm_progress", f"Generated {len(response_content)} characters...")
            
            stream("llm_complete", "Section modification complete")
            
            # Extract code from response
            modified_code = self._extract_code_from_response(response_content)
            return modified_code or original_section
            
        except Exception as e:
            stream("error", f"Error generating modification: {e}")
            return original_section
    
    def _build_modification_context(self, element: ASTNodeInfo, file_ast: FileASTInfo) -> str:
        """Build context information from AST for better modifications"""
        
        context_parts = []
        
        # Element-specific context
        if element.type == "function":
            context_parts.append(f"Function: {element.name}")
            if element.parameters:
                context_parts.append(f"Parameters: {', '.join(element.parameters)}")
            if element.is_async:
                context_parts.append("Type: Async function")
            if element.decorators:
                context_parts.append(f"Decorators: {', '.join(element.decorators)}")
        
        elif element.type == "class":
            context_parts.append(f"Class: {element.name}")
            if element.inheritance:
                context_parts.append(f"Inherits from: {', '.join(element.inheritance)}")
            if element.methods:
                context_parts.append(f"Methods: {', '.join(element.methods)}")
        
        # File context
        context_parts.append(f"File: {file_ast.file_path}")
        context_parts.append(f"Language: {file_ast.language}")
        context_parts.append(f"Total functions in file: {len(file_ast.functions)}")
        context_parts.append(f"Total classes in file: {len(file_ast.classes)}")
        
        # Import context
        if file_ast.imports:
            import_names = [imp.name for imp in file_ast.imports[:5]]  # First 5 imports
            context_parts.append(f"File imports: {', '.join(import_names)}")
        
        return "\n".join(context_parts)
    
    def _apply_general_modification(self, 
                                   file_content: str, 
                                   file_ast: FileASTInfo, 
                                   user_message: str,
                                   client,
                                   stream: Callable[[str, str], None]) -> Dict[str, Any]:
        """Apply general modification with AST context"""
        
        stream("general_mod", "Applying general modification with AST context")
        
        # Build comprehensive context
        ast_context = self._build_file_ast_context(file_ast)
        
        system_prompt = f"""You are modifying a {file_ast.language} file with STRICT TECHNOLOGY STACK ENFORCEMENT.

AST ANALYSIS CONTEXT:
{ast_context}

TECHNOLOGY RULES:
- Original language: {file_ast.language}
- Parser used: {file_ast.parser_type}
- MAINTAIN the exact same technology stack
- DO NOT add frameworks or technologies not present in original

MODIFICATION APPROACH:
- Make targeted changes based on the AST context provided
- Focus only on what the user is asking for
- Preserve original imports, structure, and patterns

Return the complete modified file content while maintaining the original technology choices."""

        try:
            response_content = ""
            with client.messages.stream(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                temperature=0.1,
                system=system_prompt,
                messages=[{
                    "role": "user", 
                    "content": f"Original file:\n```\n{file_content}\n```\n\nUser request (with AST context): {user_message}"
                }]
            ) as stream_response:
                for text in stream_response.text_stream:
                    response_content += text
                    if len(response_content) % 200 == 0:
                        stream("llm_progress", f"Generated {len(response_content)} characters...")
            
            stream("llm_complete", "General modification complete")
            
            modified_content = self._extract_code_from_response(response_content) or file_content
            
            return {
                "success": True,
                "original_content": file_content,
                "modified_content": modified_content,
                "changes": ["Applied general modifications with AST context"],
                "modification_type": "general_with_ast",
                "targets_modified": 0,
                "parser_used": f"cached_ast_{file_ast.parser_type}"
            }
            
        except Exception as e:
            stream("error", f"Error in general modification: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_content": file_content,
                "modified_content": file_content
            }
    
    def _build_file_ast_context(self, file_ast: FileASTInfo) -> str:
        """Build comprehensive AST context for a file"""
        
        context_parts = []
        
        # File overview
        context_parts.append(f"File: {file_ast.file_path}")
        context_parts.append(f"Language: {file_ast.language}")
        context_parts.append(f"Total lines: {file_ast.total_lines}")
        context_parts.append(f"Complexity score: {file_ast.complexity_score}")
        context_parts.append(f"Has syntax errors: {file_ast.has_syntax_errors}")
        
        # Functions
        if file_ast.functions:
            context_parts.append(f"\nFunctions ({len(file_ast.functions)}):")
            for func in file_ast.functions:
                func_info = f"  - {func.name}()"
                if func.parameters:
                    func_info += f" [params: {', '.join(func.parameters)}]"
                if func.is_async:
                    func_info += " [async]"
                context_parts.append(func_info)
        
        # Classes
        if file_ast.classes:
            context_parts.append(f"\nClasses ({len(file_ast.classes)}):")
            for cls in file_ast.classes:
                cls_info = f"  - {cls.name}"
                if cls.inheritance:
                    cls_info += f" extends {', '.join(cls.inheritance)}"
                if cls.methods:
                    cls_info += f" [methods: {', '.join(cls.methods)}]"
                context_parts.append(cls_info)
        
        # Imports
        if file_ast.imports:
            context_parts.append(f"\nImports ({len(file_ast.imports)}):")
            for imp in file_ast.imports[:10]:  # First 10 imports
                context_parts.append(f"  - {imp.name}")
        
        return "\n".join(context_parts)
    
    def get_project_ast_summary(self, project_id: str, project_name: str) -> Dict[str, Any]:
        """Get AST summary for a project"""
        project_cache = self.cache_manager.get_project_cache(project_id, project_name)
        return project_cache.get_project_ast_summary()
    
    def find_elements_in_project(self, project_id: str, project_name: str, element_name: str) -> List[Dict[str, Any]]:
        """Find elements by name across the project"""
        project_cache = self.cache_manager.get_project_cache(project_id, project_name)
        return project_cache.find_elements_by_name(element_name)
    
    def refresh_file_ast(self, project_id: str, project_name: str, file_path: str, file_content: str):
        """Force refresh AST cache for a specific file"""
        project_cache = self.cache_manager.get_project_cache(project_id, project_name)
        
        # Remove from cache
        if file_path in project_cache._memory_cache:
            del project_cache._memory_cache[file_path]
        if file_path in project_cache._index_cache:
            del project_cache._index_cache[file_path]
        
        # Re-parse and cache
        project_cache.get_or_parse_ast(file_path, file_content, self.ast_processor)
    
    def clear_project_cache(self, project_id: str):
        """Clear AST cache for a project"""
        self.cache_manager.clear_project_cache(project_id)
    
    # Helper methods
    def _detect_modification_type(self, message: str) -> str:
        """Detect modification type from user message"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["add", "create", "new", "implement"]):
            return "add"
        elif any(word in message_lower for word in ["fix", "bug", "error", "correct", "syntax"]):
            return "fix"
        elif any(word in message_lower for word in ["update", "modify", "change", "improve"]):
            return "update"
        elif any(word in message_lower for word in ["remove", "delete", "drop"]):
            return "remove"
        elif any(word in message_lower for word in ["refactor", "restructure", "optimize"]):
            return "refactor"
        else:
            return "general"
    
    def _is_syntax_error_fix(self, user_message: str) -> bool:
        """Check if this is a syntax error fix"""
        syntax_keywords = [
            'syntax error', 'unexpected identifier', 'parse error', 
            'syntax', 'identifier', 'template literal', 'quote', 'bracket'
        ]
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in syntax_keywords)
    
    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract code from LLM response"""
        import re
        
        # Look for code blocks
        code_block_match = re.search(r'```(?:\w+)?\s*\n(.*?)\n```', response, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1)
        
        # If no code block, check if entire response looks like code
        lines = response.strip().split('\n')
        if len(lines) > 1:
            code_indicators = ['def ', 'function ', 'class ', '{', '}', 'import ', 'from ']
            if any(indicator in response for indicator in code_indicators):
                return response.strip()
        
        return None