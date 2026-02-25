"""
Multi-language AST Parser with Dynamic Tree-sitter Support
Supports Python (native AST), JavaScript/TypeScript (regex-based), and other languages via Tree-sitter
"""

import ast
import re
import json
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import sys

# Try to import Tree-sitter components
try:
    import tree_sitter
    from tree_sitter import Language, Parser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    print("[WARNING] tree-sitter not available. Install with: pip install tree-sitter")

# Try to import tree-sitter-languages (comprehensive language pack)
try:
    import tree_sitter_languages as tsl
    TREE_SITTER_LANGUAGES_AVAILABLE = True
except ImportError:
    TREE_SITTER_LANGUAGES_AVAILABLE = False
    print("[INFO] tree-sitter-languages not available. Install with: pip install tree-sitter-languages")

class DynamicTreeSitterManager:
    """Dynamically manages Tree-sitter parsers for multiple languages"""
    
    def __init__(self):
        self.parsers = {}
        self.languages = {}
        self.language_mapping = {}
        self.failed_languages = set()  # Track languages that failed to load
        self._initialize_language_mappings()
        
    def _initialize_language_mappings(self):
        """Initialize file extension to language mappings"""
        self.language_mapping = {
            # Web languages
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.mjs': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'tsx',
            '.html': 'html',
            '.htm': 'html',
            '.xhtml': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'css',
            '.styl': 'stylus',
            
            # Backend languages
            '.py': 'python',
            '.pyx': 'python',
            '.pyi': 'python',
            '.java': 'java',
            '.kt': 'kotlin',
            '.kts': 'kotlin',
            '.scala': 'scala',
            '.sc': 'scala',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c++': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.hxx': 'cpp',
            '.cs': 'c_sharp',
            '.php': 'php',
            '.php3': 'php',
            '.php4': 'php',
            '.php5': 'php',
            '.rb': 'ruby',
            '.rbw': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift',
            '.m': 'objective_c',
            '.mm': 'objective_c',
            
            # Functional languages
            '.hs': 'haskell',
            '.lhs': 'haskell',
            '.ml': 'ocaml',
            '.mli': 'ocaml',
            '.fs': 'fsharp',
            '.fsx': 'fsharp',
            '.clj': 'clojure',
            '.cljs': 'clojure',
            '.cljc': 'clojure',
            '.erl': 'erlang',
            '.hrl': 'erlang',
            '.ex': 'elixir',
            '.exs': 'elixir',
            '.elm': 'elm',
            
            # Data/Config languages
            '.json': 'json',
            '.jsonc': 'json',
            '.json5': 'json',
            '.xml': 'xml',
            '.xsd': 'xml',
            '.xsl': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'ini',
            '.properties': 'properties',
            
            # Shell languages
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.fish': 'fish',
            '.ps1': 'powershell',
            '.psm1': 'powershell',
            '.psd1': 'powershell',
            
            # Database
            '.sql': 'sql',
            '.psql': 'sql',
            '.mysql': 'sql',
            
            # Other languages
            '.r': 'r',
            '.R': 'r',
            '.lua': 'lua',
            '.dart': 'dart',
            '.vim': 'vim',
            '.dockerfile': 'dockerfile',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.tex': 'latex',
            '.jl': 'julia',
            '.pl': 'perl',
            '.pm': 'perl',
            '.zig': 'zig',
            '.nim': 'nim',
            '.cr': 'crystal',
            '.d': 'd',
            '.pas': 'pascal',
            '.pp': 'pascal',
            '.ada': 'ada',
            '.adb': 'ada',
            '.ads': 'ada',
            '.f': 'fortran',
            '.f90': 'fortran',
            '.f95': 'fortran',
            '.cob': 'cobol',
            '.cbl': 'cobol',
        }
    
    def get_language_for_file(self, file_path: str) -> str:
        """Get language identifier for a file"""
        file_name = Path(file_path).name.lower()
        
        # Handle special filenames without extensions
        special_files = {
            'dockerfile': 'dockerfile',
            'makefile': 'make',
            'cmake': 'cmake',
            'cmakelists.txt': 'cmake',
            'rakefile': 'ruby',
            'gemfile': 'ruby',
            'vagrantfile': 'ruby',
            'requirements.txt': 'text',
            'package.json': 'json',
            'composer.json': 'json',
            'tsconfig.json': 'json',
            '.gitignore': 'gitignore',
            '.dockerignore': 'gitignore',
            '.env': 'dotenv',
        }
        
        if file_name in special_files:
            return special_files[file_name]
        
        # Use extension mapping
        suffix = Path(file_path).suffix.lower()
        return self.language_mapping.get(suffix, 'unknown')
    
    def _try_import_language_module(self, language: str) -> Optional[object]:
        """Try to dynamically import a tree-sitter language module"""
        possible_module_names = [
            f'tree_sitter_{language}',
            f'tree-sitter-{language}',
            f'tree_sitter.{language}',
            f'tree_sitter_{language.replace("-", "_")}',
        ]
        
        for module_name in possible_module_names:
            try:
                module = importlib.import_module(module_name)
                return module
            except ImportError:
                continue
                
        return None
    
    def _get_language_from_tree_sitter_languages(self, language: str):
        """Try to get language from tree-sitter-languages package"""
        if not TREE_SITTER_LANGUAGES_AVAILABLE:
            return None
            
        try:
            # tree-sitter-languages uses get_language() function
            return tsl.get_language(language)
        except Exception as e:
            # Try alternative names
            alternatives = self._get_alternative_language_names(language)
            for alt_name in alternatives:
                try:
                    return tsl.get_language(alt_name)
                except Exception:
                    continue
            
            print(f"[DEBUG] Could not get {language} from tree-sitter-languages: {e}")
            return None
    
    def get_parser_for_language(self, language: str) -> Optional[Parser]:
        """Get or create a parser for the specified language"""
        if not TREE_SITTER_AVAILABLE:
            return None
            
        # Return cached parser if available
        if language in self.parsers:
            return self.parsers[language]
        
        # Skip if we already know this language failed
        if language in self.failed_languages:
            return None
        
        # Try to create new parser
        ts_language = None
        
        # Method 1: Try tree-sitter-languages package first (most reliable)
        ts_language = self._get_language_from_tree_sitter_languages(language)
        
        # Method 2: Try individual language modules
        if ts_language is None:
            lang_module = self._try_import_language_module(language)
            if lang_module:
                try:
                    # Different modules have different ways to get the language
                    if hasattr(lang_module, 'language'):
                        if callable(lang_module.language):
                            ts_language = Language(lang_module.language(), language)
                        else:
                            ts_language = lang_module.language
                    elif hasattr(lang_module, 'LANGUAGE'):
                        ts_language = lang_module.LANGUAGE
                    elif hasattr(lang_module, f'{language.upper()}_LANGUAGE'):
                        ts_language = getattr(lang_module, f'{language.upper()}_LANGUAGE')
                except Exception as e:
                    print(f"[DEBUG] Error getting language from module: {e}")
        
        # Method 3: Try alternative language names
        if ts_language is None and language != 'unknown':
            alternative_names = self._get_alternative_language_names(language)
            for alt_name in alternative_names:
                ts_language = self._get_language_from_tree_sitter_languages(alt_name)
                if ts_language:
                    break
        
        # Create parser if language was found
        if ts_language:
            try:
                parser = Parser()
                parser.set_language(ts_language)
                self.parsers[language] = parser
                self.languages[language] = ts_language
                print(f"[INFO] Successfully loaded Tree-sitter parser for {language}")
                return parser
            except Exception as e:
                print(f"[DEBUG] Error creating parser for {language}: {e}")
                self.failed_languages.add(language)
        else:
            self.failed_languages.add(language)
        
        return None
    
    def _get_alternative_language_names(self, language: str) -> List[str]:
        """Get alternative names for languages"""
        alternatives = {
            'javascript': ['js', 'ecmascript', 'node'],
            'typescript': ['ts'],
            'c_sharp': ['csharp', 'cs', 'c-sharp'],
            'cpp': ['c++', 'cxx', 'c_plus_plus'],
            'objective_c': ['objc', 'objective-c'],
            'bash': ['shell', 'sh'],
            'yaml': ['yml'],
            'markdown': ['md'],
            'dockerfile': ['docker'],
            'make': ['makefile'],
            'properties': ['ini'],
            'gitignore': ['ignore'],
        }
        return alternatives.get(language, [])
    
    def parse_code(self, code: str, language: str) -> Optional[tree_sitter.Tree]:
        """Parse code using Tree-sitter"""
        parser = self.get_parser_for_language(language)
        if not parser:
            return None
            
        try:
            return parser.parse(bytes(code, 'utf8'))
        except Exception as e:
            print(f"[DEBUG] Error parsing {language} code: {e}")
            return None
    
    def get_available_languages(self) -> List[str]:
        """Get list of available languages that can be parsed"""
        available = []
        
        if TREE_SITTER_LANGUAGES_AVAILABLE:
            # Get languages from tree-sitter-languages
            try:
                # Different versions might have different ways to list languages
                if hasattr(tsl, 'get_language_names'):
                    available.extend(tsl.get_language_names())
                else:
                    # Fallback: try common languages
                    common_languages = [
                        'python', 'javascript', 'typescript', 'java', 'cpp', 'c',
                        'html', 'css', 'json', 'yaml', 'go', 'rust', 'ruby',
                        'php', 'swift', 'kotlin', 'scala', 'bash', 'sql'
                    ]
                    for lang in common_languages:
                        try:
                            if tsl.get_language(lang):
                                available.append(lang)
                        except:
                            pass
            except Exception as e:
                print(f"[DEBUG] Error getting available languages: {e}")
        
        # Add languages we know from extension mapping
        unique_languages = set(self.language_mapping.values())
        unique_languages.discard('unknown')
        available.extend(unique_languages)
        
        return sorted(list(set(available)))

class MultiLanguageASTProcessor:
    """Enhanced AST processor with dynamic Tree-sitter support"""
    
    def __init__(self):
        self.tree_sitter_manager = DynamicTreeSitterManager()
        self.parsers = {}  # Keep for backward compatibility
        
    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file path"""
        return self.tree_sitter_manager.get_language_for_file(file_path)
    
    def parse_code(self, code: str, language: str) -> Dict[str, Any]:
        """Parse code using the best available parser"""
        
        # Try Tree-sitter first for supported languages
        tree = self.tree_sitter_manager.parse_code(code, language)
        if tree:
            return self.parse_with_tree_sitter(code, language, tree)
        
        # Fallback to language-specific parsers
        if language == 'python':
            return self.parse_python_ast(code)
        elif language in ['javascript', 'typescript']:
            return self.parse_js_ts_ast(code, language)
        elif language == 'java':
            return self.parse_java_ast(code)
        elif language in ['c', 'cpp']:
            return self.parse_c_cpp_ast(code, language)
        elif language == 'csharp':
            return self.parse_csharp_ast(code)
        elif language == 'go':
            return self.parse_go_ast(code)
        elif language == 'rust':
            return self.parse_rust_ast(code)
        elif language in ['html', 'css', 'json', 'xml']:
            return self.parse_markup_ast(code, language)
        else:
            return self.parse_generic_code(code, language)
    
    def parse_with_tree_sitter(self, code: str, language: str, tree: tree_sitter.Tree) -> Dict[str, Any]:
        """Parse code using Tree-sitter AST"""
        try:
            root_node = tree.root_node
            
            # Extract information based on language
            functions = []
            classes = []
            imports = []
            variables = []
            errors = []
            
            # Check for syntax errors
            if root_node.has_error:
                errors.append("Syntax errors detected in code")
            
            # Language-specific traversal
            self._traverse_tree_sitter_node(root_node, code, functions, classes, imports, variables, language)
            
            return {
                'language': language,
                'functions': functions,
                'classes': classes,
                'imports': imports,
                'variables': variables[:20],  # Limit to prevent overwhelming output
                'total_lines': len(code.split('\n')),
                'ast_available': True,
                'parser_type': 'tree_sitter',
                'complexity_score': self._calculate_tree_sitter_complexity(functions, classes),
                'errors': errors,
                'has_syntax_errors': root_node.has_error
            }
            
        except Exception as e:
            print(f"[DEBUG] Tree-sitter parsing failed for {language}: {e}")
            return {
                'language': language,
                'error': str(e),
                'ast_available': False,
                'parser_type': 'tree_sitter_failed',
                'total_lines': len(code.split('\n')),
                'functions': [],
                'classes': [],
                'imports': [],
                'variables': []
            }
    
    def _traverse_tree_sitter_node(self, node: Node, code: str, functions: List, classes: List, imports: List, variables: List, language: str):
        """Recursively traverse Tree-sitter AST node"""
        
        # Language-specific node type mappings
        node_mappings = self._get_node_mappings_for_language(language)
        
        node_type = node.type
        
        if node_type in node_mappings:
            category = node_mappings[node_type]
            
            # Get node information
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            start_byte = node.start_byte
            end_byte = node.end_byte
            node_text = code[start_byte:end_byte]
            
            # Extract name
            name = self._extract_node_name(node, code, language, node_type)
            
            # Categorize and store information
            if category == 'function' and name:
                func_info = {
                    'name': name,
                    'line': start_line,
                    'end_line': end_line,
                    'node_type': node_type,
                    'parameters': self._extract_function_parameters(node, code, language),
                    'is_async': 'async' in node_text.lower() or 'await' in node_text.lower(),
                    'text_preview': node_text[:100] + '...' if len(node_text) > 100 else node_text
                }
                functions.append(func_info)
                
            elif category in ['class', 'interface', 'struct', 'enum'] and name:
                class_info = {
                    'name': name,
                    'line': start_line,
                    'end_line': end_line,
                    'type': category,
                    'node_type': node_type,
                    'methods': [],
                    'inheritance': self._extract_inheritance(node, code, language)
                }
                classes.append(class_info)
                
            elif category == 'import' and name:
                import_info = {
                    'module': name,
                    'line': start_line,
                    'type': 'import',
                    'import_type': self._classify_import_type(node, code, language)
                }
                imports.append(import_info)
                
            elif category == 'variable' and name and len(variables) < 20:
                var_info = {
                    'name': name,
                    'line': start_line,
                    'type': 'variable',
                    'scope': self._determine_variable_scope(node, language)
                }
                variables.append(var_info)
        
        # Recursively process child nodes
        for child in node.children:
            self._traverse_tree_sitter_node(child, code, functions, classes, imports, variables, language)
    
    def _get_node_mappings_for_language(self, language: str) -> Dict[str, str]:
        """Get node type mappings for specific languages"""
        
        # Common mappings that work across many languages
        common_mappings = {
            # Functions
            'function_definition': 'function',
            'function_declaration': 'function',
            'method_definition': 'function',
            'function': 'function',
            'arrow_function': 'function',
            'function_expression': 'function',
            'generator_function': 'function',
            'async_function': 'function',
            'lambda': 'function',
            
            # Classes and types
            'class_definition': 'class',
            'class_declaration': 'class',
            'interface_declaration': 'interface',
            'struct_declaration': 'struct',
            'enum_declaration': 'enum',
            'type_declaration': 'class',
            
            # Imports
            'import_statement': 'import',
            'import_declaration': 'import',
            'from_import_statement': 'import',
            'include_directive': 'import',
            'use_declaration': 'import',
            'require_call': 'import',
            
            # Variables
            'variable_declaration': 'variable',
            'variable_declarator': 'variable',
            'assignment_expression': 'variable',
            'let_declaration': 'variable',
            'const_declaration': 'variable',
            'var_declaration': 'variable',
        }
        
        # Language-specific extensions
        language_specific = {
            'python': {
                'async_function_definition': 'function',
                'decorated_definition': 'function',
            },
            'javascript': {
                'export_statement': 'export',
                'lexical_declaration': 'variable',
            },
            'typescript': {
                'type_alias_declaration': 'class',
                'ambient_declaration': 'declaration',
            },
            'java': {
                'constructor_declaration': 'function',
                'annotation_type_declaration': 'interface',
            },
            'go': {
                'function_declaration': 'function',
                'type_declaration': 'class',
                'type_spec': 'class',
            },
            'rust': {
                'function_item': 'function',
                'struct_item': 'struct',
                'enum_item': 'enum',
                'trait_item': 'interface',
                'impl_item': 'class',
            }
        }
        
        # Merge common and language-specific mappings
        mappings = common_mappings.copy()
        if language in language_specific:
            mappings.update(language_specific[language])
        
        return mappings
    
    def _extract_node_name(self, node: Node, code: str, language: str, node_type: str) -> Optional[str]:
        """Extract name from a Tree-sitter node"""
        try:
            # Strategy 1: Look for identifier children
            for child in node.children:
                if child.type in ['identifier', 'name', 'type_identifier']:
                    return code[child.start_byte:child.end_byte]
            
            # Strategy 2: Language-specific name extraction
            if language == 'python' and node_type == 'function_definition':
                # Python: def name(...):
                for child in node.children:
                    if child.type == 'identifier':
                        return code[child.start_byte:child.end_byte]
                        
            elif language in ['javascript', 'typescript']:
                # JS: function name() {} or const name = () => {}
                for child in node.children:
                    if child.type in ['identifier', 'property_identifier']:
                        return code[child.start_byte:child.end_byte]
            
            # Strategy 3: Extract from import statements
            if 'import' in node_type.lower():
                return self._extract_import_name(node, code, language)
            
            # Strategy 4: Generic extraction - find first identifier
            node_text = code[node.start_byte:node.end_byte]
            
            # Simple regex to find identifier (language-agnostic)
            patterns = [
                r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b',  # Standard identifier
                r'["\']([^"\']+)["\']',  # String literals (for imports)
            ]
            
            for pattern in patterns:
                match = re.search(pattern, node_text)
                if match:
                    candidate = match.group(1)
                    # Filter out keywords
                    if not self._is_keyword(candidate, language):
                        return candidate
                        
        except Exception as e:
            print(f"[DEBUG] Error extracting node name: {e}")
            
        return None
    
    def _extract_import_name(self, node: Node, code: str, language: str) -> Optional[str]:
        """Extract import name/module from import nodes"""
        node_text = code[node.start_byte:node.end_byte]
        
        if language == 'python':
            # import module or from module import name
            if 'from' in node_text:
                match = re.search(r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)', node_text)
            else:
                match = re.search(r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)', node_text)
            return match.group(1) if match else None
            
        elif language in ['javascript', 'typescript']:
            # import ... from 'module' or require('module')
            match = re.search(r'["\']([^"\']+)["\']', node_text)
            return match.group(1) if match else None
            
        elif language == 'java':
            # import package.Class;
            match = re.search(r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)', node_text)
            return match.group(1) if match else None
        
        return None
    
    def _extract_function_parameters(self, node: Node, code: str, language: str) -> List[str]:
        """Extract function parameters"""
        parameters = []
        
        try:
            # Look for parameter list nodes
            for child in node.children:
                if child.type in ['parameters', 'parameter_list', 'formal_parameters']:
                    for param_node in child.children:
                        if param_node.type in ['identifier', 'parameter', 'typed_parameter']:
                            param_name = self._extract_node_name(param_node, code, language, param_node.type)
                            if param_name and param_name not in ['(', ')', ',']:
                                parameters.append(param_name)
        except Exception as e:
            print(f"[DEBUG] Error extracting parameters: {e}")
        
        return parameters
    
    def _extract_inheritance(self, node: Node, code: str, language: str) -> List[str]:
        """Extract inheritance/base classes"""
        inheritance = []
        
        try:
            for child in node.children:
                if child.type in ['argument_list', 'superclass', 'type_parameters']:
                    # Extract inheritance information
                    text = code[child.start_byte:child.end_byte]
                    # Simple extraction - can be improved per language
                    matches = re.findall(r'\b([A-Z][a-zA-Z0-9_]*)\b', text)
                    inheritance.extend(matches)
        except Exception as e:
            print(f"[DEBUG] Error extracting inheritance: {e}")
        
        return inheritance
    
    def _classify_import_type(self, node: Node, code: str, language: str) -> str:
        """Classify the type of import"""
        node_text = code[node.start_byte:node.end_byte].lower()
        
        if 'from' in node_text:
            return 'from_import'
        elif 'require' in node_text:
            return 'require'
        elif 'use' in node_text:
            return 'use'
        elif 'include' in node_text:
            return 'include'
        else:
            return 'import'
    
    def _determine_variable_scope(self, node: Node, language: str) -> str:
        """Determine variable scope (simplified)"""
        # This is a simplified implementation
        # In practice, you'd need to traverse up the AST to determine scope
        parent = node.parent
        if parent:
            if parent.type in ['function_definition', 'method_definition']:
                return 'local'
            elif parent.type in ['class_definition', 'class_declaration']:
                return 'class'
        return 'global'
    
    def _is_keyword(self, word: str, language: str) -> bool:
        """Check if word is a language keyword"""
        keywords = {
            'python': {'def', 'class', 'import', 'from', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 'with', 'as', 'return', 'yield', 'lambda', 'and', 'or', 'not', 'in', 'is'},
            'javascript': {'function', 'class', 'import', 'from', 'export', 'if', 'else', 'for', 'while', 'do', 'try', 'catch', 'finally', 'return', 'var', 'let', 'const', 'typeof', 'instanceof'},
            'java': {'class', 'interface', 'import', 'package', 'if', 'else', 'for', 'while', 'do', 'try', 'catch', 'finally', 'return', 'public', 'private', 'protected', 'static'},
            'go': {'func', 'type', 'import', 'package', 'if', 'else', 'for', 'range', 'return', 'var', 'const'},
            'rust': {'fn', 'struct', 'enum', 'impl', 'trait', 'use', 'if', 'else', 'for', 'while', 'loop', 'return', 'let', 'mut'},
        }
        
        return word.lower() in keywords.get(language, set())
    
    def _calculate_tree_sitter_complexity(self, functions: List, classes: List) -> int:
        """Calculate complexity score based on Tree-sitter analysis"""
        complexity = 0
        complexity += len(functions)
        complexity += len(classes) * 2
        
        # Add complexity based on function parameters
        for func in functions:
            complexity += len(func.get('parameters', []))
        
        return complexity
    
    def get_supported_languages(self) -> List[str]:
        """Get list of all supported languages"""
        tree_sitter_langs = self.tree_sitter_manager.get_available_languages()
        builtin_langs = ['python', 'javascript', 'typescript', 'java', 'cpp', 'c', 'csharp', 'go', 'rust', 'html', 'css', 'json', 'xml']
        
        all_langs = list(set(tree_sitter_langs + builtin_langs))
        return sorted(all_langs)
    
    # Fallback parsers for when Tree-sitter is not available
    
    def parse_python_ast(self, code: str) -> Dict[str, Any]:
        """Parse Python code using built-in AST"""
        try:
            tree = ast.parse(code)
            
            # Extract key information
            functions = []
            classes = []
            imports = []
            variables = []
            decorators = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    function_info = {
                        'name': node.name,
                        'line': node.lineno,
                        'end_line': getattr(node, 'end_lineno', node.lineno),
                        'args': [arg.arg for arg in node.args.args],
                        'docstring': ast.get_docstring(node),
                        'decorators': [self._get_decorator_name(dec) for dec in node.decorator_list],
                        'returns': self._get_annotation_name(node.returns) if node.returns else None,
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    }
                    functions.append(function_info)
                    
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'line': node.lineno,
                        'end_line': getattr(node, 'end_lineno', node.lineno),
                        'bases': [self._get_base_name(base) for base in node.bases],
                        'docstring': ast.get_docstring(node),
                        'methods': [],
                        'decorators': [self._get_decorator_name(dec) for dec in node.decorator_list]
                    }
                    
                    # Get methods within the class
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            class_info['methods'].append({
                                'name': item.name,
                                'line': item.lineno,
                                'is_async': isinstance(item, ast.AsyncFunctionDef),
                                'decorators': [self._get_decorator_name(dec) for dec in item.decorator_list]
                            })
                    
                    classes.append(class_info)
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append({
                                'module': alias.name,
                                'alias': alias.asname,
                                'type': 'import',
                                'line': node.lineno
                            })
                    else:
                        module = node.module or ''
                        for alias in node.names:
                            imports.append({
                                'module': f"{module}.{alias.name}" if module else alias.name,
                                'alias': alias.asname,
                                'type': 'from_import',
                                'from': module,
                                'line': node.lineno
                            })
                
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.append({
                                'name': target.id,
                                'line': node.lineno,
                                'type': 'assignment'
                            })
            
            return {
                'language': 'python',
                'functions': functions,
                'classes': classes,
                'imports': imports,
                'variables': variables[:20],
                'decorators': list(set(decorators)),
                'total_lines': len(code.split('\n')),
                'ast_available': True,
                'parser_type': 'python_builtin',
                'complexity_score': self._calculate_python_complexity(tree)
            }
        
        except SyntaxError as e:
            return {
                'language': 'python',
                'error': str(e),
                'ast_available': False,
                'parser_type': 'python_builtin_failed',
                'total_lines': len(code.split('\n')),
                'functions': [],
                'classes': [],
                'imports': [],
                'variables': []
            }
    
    def parse_js_ts_ast(self, code: str, language: str) -> Dict[str, Any]:
        """Parse JavaScript/TypeScript code using regex patterns"""
        try:
            # Enhanced regex patterns for JS/TS analysis
            function_patterns = [
                r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)',
                r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)',
                r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:\s*(?:async\s+)?function\s*\(',
                r'(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{',
            ]
            
            class_pattern = r'class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*(?:extends\s+([a-zA-Z_$][a-zA-Z0-9_$]*))?\s*\{'
            import_patterns = [
                r'import\s+.*?from\s+[\'"]([^\'\"]+)[\'"]',
                r'(?:const|let|var)\s+.*?=\s*require\([\'"]([^\'\"]+)[\'"]\)',
                r'import\s*\(\s*[\'"]([^\'\"]+)[\'"]\s*\)',
            ]
            
            functions = []
            classes = []
            imports = []
            variables = []
            
            lines = code.split('\n')
            
            # Find functions
            for pattern in function_patterns:
                for match in re.finditer(pattern, code, re.MULTILINE):
                    if match.group(1):
                        line_num = code[:match.start()].count('\n') + 1
                        functions.append({
                            'name': match.group(1),
                            'line': line_num,
                            'type': 'function',
                            'is_async': 'async' in match.group(0)
                        })
            
            # Find classes
            for match in re.finditer(class_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                classes.append({
                    'name': match.group(1),
                    'line': line_num,
                    'extends': match.group(2) if len(match.groups()) > 1 and match.group(2) else None,
                    'methods': []
                })
            
            # Find imports
            for pattern in import_patterns:
                for match in re.finditer(pattern, code, re.MULTILINE):
                    imports.append({
                        'module': match.group(1),
                        'line': code[:match.start()].count('\n') + 1,
                        'type': 'import'
                    })
            
            # Find variable declarations
            var_pattern = r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)'
            for match in re.finditer(var_pattern, code):
                variables.append({
                    'name': match.group(1),
                    'line': code[:match.start()].count('\n') + 1,
                    'type': 'variable'
                })
            
            return {
                'language': language,
                'functions': functions[:50],
                'classes': classes[:20],
                'imports': imports[:30],
                'variables': variables[:30],
                'total_lines': len(lines),
                'ast_available': True,
                'parser_type': 'regex',
                'complexity_score': len(functions) + len(classes) * 2
            }
        
        except Exception as e:
            return {
                'language': language,
                'error': str(e),
                'ast_available': False,
                'parser_type': 'regex_failed',
                'total_lines': len(code.split('\n')),
                'functions': [],
                'classes': [],
                'imports': []
            }
    
    def parse_java_ast(self, code: str) -> Dict[str, Any]:
        """Parse Java code using regex patterns"""
        try:
            class_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?(?:final\s+)?class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)'
            method_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?(?:abstract\s+)?[a-zA-Z_$<>\[\]]+\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*(?:\{|;)'
            import_pattern = r'import\s+(?:static\s+)?([a-zA-Z_$][a-zA-Z0-9_$.*]*);'
            
            classes = []
            methods = []
            imports = []
            
            for match in re.finditer(class_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                classes.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'class'
                })
            
            for match in re.finditer(method_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                methods.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'method'
                })
            
            for match in re.finditer(import_pattern, code, re.MULTILINE):
                imports.append({
                    'module': match.group(1),
                    'line': code[:match.start()].count('\n') + 1,
                    'type': 'import'
                })
            
            return {
                'language': 'java',
                'functions': methods,
                'classes': classes,
                'imports': imports,
                'total_lines': len(code.split('\n')),
                'ast_available': True,
                'parser_type': 'regex',
                'complexity_score': len(methods) + len(classes) * 2
            }
        
        except Exception as e:
            return self.parse_generic_code(code, 'java')
    
    def parse_c_cpp_ast(self, code: str, language: str) -> Dict[str, Any]:
        """Parse C/C++ code using regex patterns"""
        try:
            function_pattern = r'(?:extern\s+)?(?:static\s+)?(?:inline\s+)?[a-zA-Z_][a-zA-Z0-9_*\s]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*(?:\{|;)'
            class_pattern = r'(?:class|struct)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
            
            functions = []
            classes = []
            includes = []
            
            for match in re.finditer(function_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                functions.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'function'
                })
            
            for match in re.finditer(class_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                classes.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'class' if 'class' in match.group(0) else 'struct'
                })
            
            for match in re.finditer(include_pattern, code, re.MULTILINE):
                includes.append({
                    'module': match.group(1),
                    'line': code[:match.start()].count('\n') + 1,
                    'type': 'include'
                })
            
            return {
                'language': language,
                'functions': functions,
                'classes': classes,
                'imports': includes,
                'total_lines': len(code.split('\n')),
                'ast_available': True,
                'parser_type': 'regex',
                'complexity_score': len(functions) + len(classes) * 2
            }
        
        except Exception as e:
            return self.parse_generic_code(code, language)
    
    def parse_csharp_ast(self, code: str) -> Dict[str, Any]:
        """Parse C# code using regex patterns"""
        try:
            class_pattern = r'(?:public\s+|private\s+|protected\s+|internal\s+)?(?:abstract\s+|sealed\s+)?class\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            method_pattern = r'(?:public\s+|private\s+|protected\s+|internal\s+)?(?:static\s+)?(?:virtual\s+|override\s+|abstract\s+)?[a-zA-Z_<>\[\]]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)'
            using_pattern = r'using\s+([a-zA-Z_][a-zA-Z0-9_.]*);'
            
            classes = []
            methods = []
            usings = []
            
            for match in re.finditer(class_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                classes.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'class'
                })
            
            for match in re.finditer(method_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                methods.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'method'
                })
            
            for match in re.finditer(using_pattern, code, re.MULTILINE):
                usings.append({
                    'module': match.group(1),
                    'line': code[:match.start()].count('\n') + 1,
                    'type': 'using'
                })
            
            return {
                'language': 'csharp',
                'functions': methods,
                'classes': classes,
                'imports': usings,
                'total_lines': len(code.split('\n')),
                'ast_available': True,
                'parser_type': 'regex',
                'complexity_score': len(methods) + len(classes) * 2
            }
        
        except Exception as e:
            return self.parse_generic_code(code, 'csharp')
    
    def parse_go_ast(self, code: str) -> Dict[str, Any]:
        """Parse Go code using regex patterns"""
        try:
            function_pattern = r'func\s+(?:\([^)]*\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)'
            struct_pattern = r'type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+struct'
            import_pattern = r'import\s+(?:"([^"]+)"|`([^`]+)`)'
            
            functions = []
            structs = []
            imports = []
            
            for match in re.finditer(function_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                functions.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'function'
                })
            
            for match in re.finditer(struct_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                structs.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'struct'
                })
            
            for match in re.finditer(import_pattern, code, re.MULTILINE):
                module = match.group(1) or match.group(2)
                imports.append({
                    'module': module,
                    'line': code[:match.start()].count('\n') + 1,
                    'type': 'import'
                })
            
            return {
                'language': 'go',
                'functions': functions,
                'classes': structs,
                'imports': imports,
                'total_lines': len(code.split('\n')),
                'ast_available': True,
                'parser_type': 'regex',
                'complexity_score': len(functions) + len(structs) * 2
            }
        
        except Exception as e:
            return self.parse_generic_code(code, 'go')
    
    def parse_rust_ast(self, code: str) -> Dict[str, Any]:
        """Parse Rust code using regex patterns"""
        try:
            function_pattern = r'fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)'
            struct_pattern = r'struct\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            impl_pattern = r'impl\s+(?:[^{]+\s+for\s+)?([a-zA-Z_][a-zA-Z0-9_]*)'
            use_pattern = r'use\s+([a-zA-Z_][a-zA-Z0-9_:]*);'
            
            functions = []
            structs = []
            impls = []
            uses = []
            
            for match in re.finditer(function_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                functions.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'function'
                })
            
            for match in re.finditer(struct_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                structs.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'struct'
                })
            
            for match in re.finditer(impl_pattern, code, re.MULTILINE):
                line_num = code[:match.start()].count('\n') + 1
                impls.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'impl'
                })
            
            for match in re.finditer(use_pattern, code, re.MULTILINE):
                uses.append({
                    'module': match.group(1),
                    'line': code[:match.start()].count('\n') + 1,
                    'type': 'use'
                })
            
            return {
                'language': 'rust',
                'functions': functions,
                'classes': structs + impls,
                'imports': uses,
                'total_lines': len(code.split('\n')),
                'ast_available': True,
                'parser_type': 'regex',
                'complexity_score': len(functions) + len(structs) * 2
            }
        
        except Exception as e:
            return self.parse_generic_code(code, 'rust')
    
    def parse_markup_ast(self, code: str, language: str) -> Dict[str, Any]:
        """Parse markup languages (HTML, CSS, JSON, XML)"""
        try:
            if language == 'html':
                tag_pattern = r'<([a-zA-Z][a-zA-Z0-9]*)'
                tags = re.findall(tag_pattern, code)
                return {
                    'language': language,
                    'elements': list(set(tags))[:20],
                    'total_lines': len(code.split('\n')),
                    'ast_available': False,
                    'parser_type': 'regex',
                    'functions': [],
                    'classes': [],
                    'imports': []
                }
            
            elif language == 'css':
                selector_pattern = r'([.#]?[a-zA-Z_-][a-zA-Z0-9_-]*)\s*\{'
                selectors = re.findall(selector_pattern, code)
                return {
                    'language': language,
                    'selectors': list(set(selectors))[:30],
                    'total_lines': len(code.split('\n')),
                    'ast_available': False,
                    'parser_type': 'regex',
                    'functions': [],
                    'classes': [],
                    'imports': []
                }
            
            elif language == 'json':
                try:
                    parsed = json.loads(code)
                    return {
                        'language': language,
                        'keys': list(parsed.keys()) if isinstance(parsed, dict) else [],
                        'total_lines': len(code.split('\n')),
                        'ast_available': False,
                        'parser_type': 'json',
                        'functions': [],
                        'classes': [],
                        'imports': []
                    }
                except:
                    pass
            
            return self.parse_generic_code(code, language)
        
        except Exception as e:
            return self.parse_generic_code(code, language)
    
    def parse_generic_code(self, code: str, language: str) -> Dict[str, Any]:
        """Generic code analysis for unsupported languages"""
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Try to find function-like patterns
        function_patterns = [
            r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{',
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*function',
        ]
        
        functions = []
        for pattern in function_patterns:
            for match in re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE):
                line_num = code[:match.start()].count('\n') + 1
                functions.append({
                    'name': match.group(1),
                    'line': line_num,
                    'type': 'function_like'
                })
        
        return {
            'language': language,
            'total_lines': len(lines),
            'non_empty_lines': len(non_empty_lines),
            'ast_available': False,
            'parser_type': 'generic',
            'functions': functions[:20],
            'classes': [],
            'imports': [],
            'estimated_complexity': len(non_empty_lines) // 10
        }
    
    # Helper methods for Python AST parsing
    
    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_name_from_node(decorator.value)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        else:
            return str(decorator)
    
    def _get_base_name(self, base) -> str:
        """Extract base class name from AST node"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{self._get_name_from_node(base.value)}.{base.attr}"
        else:
            return str(base)
    
    def _get_annotation_name(self, annotation) -> str:
        """Extract type annotation name from AST node"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return f"{self._get_name_from_node(annotation.value)}.{annotation.attr}"
        elif isinstance(annotation, ast.Subscript):
            return f"{self._get_annotation_name(annotation.value)}[...]"
        else:
            return str(annotation)
    
    def _get_name_from_node(self, node) -> str:
        """Extract name from various AST node types"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name_from_node(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        else:
            return "unknown"
    
    def _calculate_python_complexity(self, tree) -> int:
        """Calculate a simple complexity score for Python code"""
        complexity = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity += 1
            elif isinstance(node, ast.ClassDef):
                complexity += 2
            elif isinstance(node, ast.Lambda):
                complexity += 1
        
        return complexity
    
    def get_summary(self, code: str, language: str) -> str:
        """Get a human-readable summary of the code analysis"""
        analysis = self.parse_code(code, language)
        
        summary_parts = [
            f"Language: {analysis.get('language', 'unknown')}",
            f"Lines: {analysis.get('total_lines', 0)}",
            f"Functions: {len(analysis.get('functions', []))}",
            f"Classes: {len(analysis.get('classes', []))}",
            f"Imports: {len(analysis.get('imports', []))}"
        ]
        
        if 'complexity_score' in analysis:
            summary_parts.append(f"Complexity: {analysis['complexity_score']}")
        
        if 'error' in analysis:
            summary_parts.append(f"Error: {analysis['error']}")
        
        if 'parser_type' in analysis:
            summary_parts.append(f"Parser: {analysis['parser_type']}")
        
        return " | ".join(summary_parts)