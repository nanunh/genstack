"""
Dynamic AST Cache Manager
Maintains AST trees as JSON files for each project without database dependency
"""

import json
import os
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

@dataclass
class ASTNodeInfo:
    """Represents a parsed AST node"""
    name: str
    type: str  # function, class, import, variable
    start_line: int
    end_line: int
    start_byte: Optional[int] = None
    end_byte: Optional[int] = None
    parameters: List[str] = None
    methods: List[str] = None
    inheritance: List[str] = None
    decorators: List[str] = None
    is_async: bool = False
    docstring: Optional[str] = None
    scope: str = "global"
    file_path: str = ""
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.methods is None:
            self.methods = []
        if self.inheritance is None:
            self.inheritance = []
        if self.decorators is None:
            self.decorators = []

@dataclass 
class FileASTInfo:
    """Represents AST information for a single file"""
    file_path: str
    language: str
    file_hash: str
    last_modified: float
    last_parsed: float
    functions: List[ASTNodeInfo]
    classes: List[ASTNodeInfo]
    imports: List[ASTNodeInfo]
    variables: List[ASTNodeInfo]
    total_lines: int
    complexity_score: int
    has_syntax_errors: bool = False
    parser_type: str = "unknown"
    
    def __post_init__(self):
        if not self.functions:
            self.functions = []
        if not self.classes:
            self.classes = []
        if not self.imports:
            self.imports = []
        if not self.variables:
            self.variables = []

class ProjectASTCache:
    """Manages AST cache for a single project"""
    
    def __init__(self, project_id: str, project_name: str, base_cache_dir: str = "ast_cache"):
        self.project_id = project_id
        self.project_name = project_name
        self.base_cache_dir = Path(base_cache_dir)
        self.project_cache_dir = self.base_cache_dir / f"{project_name}_{project_id[:8]}"
        self.ast_processor = None
        
        # Ensure cache directory exists
        self.project_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache file paths
        self.index_file = self.project_cache_dir / "ast_index.json"
        self.files_cache_dir = self.project_cache_dir / "files"
        self.files_cache_dir.mkdir(exist_ok=True)
        
        # In-memory cache
        self._memory_cache: Dict[str, FileASTInfo] = {}
        self._index_cache: Dict[str, Dict] = {}
        
        # Load existing cache
        self._load_index()
    
    def _load_index(self):
        """Load the AST index from disk"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self._index_cache = json.load(f)
            except Exception as e:
                print(f"[DEBUG] Error loading AST index: {e}")
                self._index_cache = {}
    
    def _save_index(self):
        """Save the AST index to disk"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self._index_cache, f, indent=2)
        except Exception as e:
            print(f"[DEBUG] Error saving AST index: {e}")
    
    def _get_file_hash(self, file_path: str, content: str) -> str:
        """Generate hash for file content"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cache_filename(self, file_path: str) -> str:
        """Generate cache filename for a source file"""
        # Use hash of file path to avoid filesystem issues
        path_hash = hashlib.md5(file_path.encode('utf-8')).hexdigest()
        return f"{path_hash}.json"
    
    def _ast_node_to_dict(self, node: ASTNodeInfo) -> Dict:
        """Convert ASTNodeInfo to dictionary"""
        return asdict(node)
    
    def _dict_to_ast_node(self, data: Dict) -> ASTNodeInfo:
        """Convert dictionary to ASTNodeInfo"""
        return ASTNodeInfo(**data)
    
    def _file_ast_to_dict(self, file_ast: FileASTInfo) -> Dict:
        """Convert FileASTInfo to dictionary for JSON storage"""
        return {
            "file_path": file_ast.file_path,
            "language": file_ast.language,
            "file_hash": file_ast.file_hash,
            "last_modified": file_ast.last_modified,
            "last_parsed": file_ast.last_parsed,
            "functions": [self._ast_node_to_dict(f) for f in file_ast.functions],
            "classes": [self._ast_node_to_dict(c) for c in file_ast.classes],
            "imports": [self._ast_node_to_dict(i) for i in file_ast.imports],
            "variables": [self._ast_node_to_dict(v) for v in file_ast.variables],
            "total_lines": file_ast.total_lines,
            "complexity_score": file_ast.complexity_score,
            "has_syntax_errors": file_ast.has_syntax_errors,
            "parser_type": file_ast.parser_type
        }
    
    def _dict_to_file_ast(self, data: Dict) -> FileASTInfo:
        """Convert dictionary to FileASTInfo"""
        return FileASTInfo(
            file_path=data["file_path"],
            language=data["language"],
            file_hash=data["file_hash"],
            last_modified=data["last_modified"],
            last_parsed=data["last_parsed"],
            functions=[self._dict_to_ast_node(f) for f in data.get("functions", [])],
            classes=[self._dict_to_ast_node(c) for c in data.get("classes", [])],
            imports=[self._dict_to_ast_node(i) for i in data.get("imports", [])],
            variables=[self._dict_to_ast_node(v) for v in data.get("variables", [])],
            total_lines=data.get("total_lines", 0),
            complexity_score=data.get("complexity_score", 0),
            has_syntax_errors=data.get("has_syntax_errors", False),
            parser_type=data.get("parser_type", "unknown")
        )
    
    def _convert_ast_result_to_file_ast(self, file_path: str, content: str, ast_result: Dict) -> FileASTInfo:
        """Convert AST processor result to FileASTInfo"""
        
        # Convert functions
        functions = []
        for func_data in ast_result.get("functions", []):
            functions.append(ASTNodeInfo(
                name=func_data.get("name", ""),
                type="function",
                start_line=func_data.get("line", 0),
                end_line=func_data.get("end_line", func_data.get("line", 0)),
                start_byte=func_data.get("start_byte"),
                end_byte=func_data.get("end_byte"),
                parameters=func_data.get("args", func_data.get("parameters", [])),
                is_async=func_data.get("is_async", False),
                docstring=func_data.get("docstring"),
                decorators=func_data.get("decorators", []),
                file_path=file_path
            ))
        
        # Convert classes
        classes = []
        for class_data in ast_result.get("classes", []):
            classes.append(ASTNodeInfo(
                name=class_data.get("name", ""),
                type="class",
                start_line=class_data.get("line", 0),
                end_line=class_data.get("end_line", class_data.get("line", 0)),
                start_byte=class_data.get("start_byte"),
                end_byte=class_data.get("end_byte"),
                methods=[m.get("name", "") for m in class_data.get("methods", [])],
                inheritance=class_data.get("bases", class_data.get("inheritance", [])),
                docstring=class_data.get("docstring"),
                decorators=class_data.get("decorators", []),
                file_path=file_path
            ))
        
        # Convert imports
        imports = []
        for import_data in ast_result.get("imports", []):
            imports.append(ASTNodeInfo(
                name=import_data.get("module", ""),
                type="import",
                start_line=import_data.get("line", 0),
                end_line=import_data.get("line", 0),
                file_path=file_path
            ))
        
        # Convert variables
        variables = []
        for var_data in ast_result.get("variables", [])[:20]:  # Limit variables
            variables.append(ASTNodeInfo(
                name=var_data.get("name", ""),
                type="variable",
                start_line=var_data.get("line", 0),
                end_line=var_data.get("line", 0),
                scope=var_data.get("scope", "global"),
                file_path=file_path
            ))
        
        return FileASTInfo(
            file_path=file_path,
            language=ast_result.get("language", "unknown"),
            file_hash=self._get_file_hash(file_path, content),
            last_modified=time.time(),
            last_parsed=time.time(),
            functions=functions,
            classes=classes,
            imports=imports,
            variables=variables,
            total_lines=ast_result.get("total_lines", 0),
            complexity_score=ast_result.get("complexity_score", 0),
            has_syntax_errors=ast_result.get("has_syntax_errors", False),
            parser_type=ast_result.get("parser_type", "unknown")
        )
    
    def is_file_cached_and_valid(self, file_path: str, content: str) -> bool:
        """Check if file is cached and cache is still valid"""
        file_hash = self._get_file_hash(file_path, content)
        
        # Check index first
        if file_path in self._index_cache:
            cached_info = self._index_cache[file_path]
            if cached_info.get("file_hash") == file_hash:
                return True
        
        return False
    
    def get_cached_ast(self, file_path: str) -> Optional[FileASTInfo]:
        """Get cached AST for a file"""
        
        # Check memory cache first
        if file_path in self._memory_cache:
            return self._memory_cache[file_path]
        
        # Check disk cache
        if file_path in self._index_cache:
            cache_filename = self._get_cache_filename(file_path)
            cache_file_path = self.files_cache_dir / cache_filename
            
            if cache_file_path.exists():
                try:
                    with open(cache_file_path, 'r') as f:
                        cached_data = json.load(f)
                    
                    file_ast = self._dict_to_file_ast(cached_data)
                    
                    # Store in memory cache
                    self._memory_cache[file_path] = file_ast
                    
                    return file_ast
                    
                except Exception as e:
                    print(f"[DEBUG] Error loading cached AST for {file_path}: {e}")
        
        return None
    
    def cache_ast(self, file_path: str, content: str, ast_result: Dict):
        """Cache AST result for a file"""
        
        try:
            # Convert to FileASTInfo
            file_ast = self._convert_ast_result_to_file_ast(file_path, content, ast_result)
            
            # Store in memory cache
            self._memory_cache[file_path] = file_ast
            
            # Store on disk
            cache_filename = self._get_cache_filename(file_path)
            cache_file_path = self.files_cache_dir / cache_filename
            
            with open(cache_file_path, 'w') as f:
                json.dump(self._file_ast_to_dict(file_ast), f, indent=2)
            
            # Update index
            self._index_cache[file_path] = {
                "file_hash": file_ast.file_hash,
                "last_parsed": file_ast.last_parsed,
                "cache_filename": cache_filename,
                "language": file_ast.language
            }
            
            # Save index
            self._save_index()
            
            print(f"[DEBUG] Cached AST for {file_path} ({file_ast.language})")
            
        except Exception as e:
            print(f"[DEBUG] Error caching AST for {file_path}: {e}")
    
    def get_or_parse_ast(self, file_path: str, content: str, ast_processor) -> FileASTInfo:
        """Get AST from cache or parse and cache it"""
        
        # Check if cached and valid
        if self.is_file_cached_and_valid(file_path, content):
            cached_ast = self.get_cached_ast(file_path)
            if cached_ast:
                print(f"[DEBUG] Using cached AST for {file_path}")
                return cached_ast
        
        # Parse and cache
        print(f"[DEBUG] Parsing AST for {file_path}")
        language = ast_processor.detect_language(file_path)
        ast_result = ast_processor.parse_code(content, language)
        
        # Cache the result
        self.cache_ast(file_path, content, ast_result)
        
        # Return from cache
        return self.get_cached_ast(file_path)
    
    def get_project_ast_summary(self) -> Dict[str, Any]:
        """Get summary of all cached ASTs for the project"""
        
        summary = {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "total_files": len(self._index_cache),
            "languages": {},
            "total_functions": 0,
            "total_classes": 0,
            "total_lines": 0,
            "files": []
        }
        
        # Load all cached files
        for file_path in self._index_cache.keys():
            file_ast = self.get_cached_ast(file_path)
            if file_ast:
                # Update language counts
                lang = file_ast.language
                if lang not in summary["languages"]:
                    summary["languages"][lang] = 0
                summary["languages"][lang] += 1
                
                # Update totals
                summary["total_functions"] += len(file_ast.functions)
                summary["total_classes"] += len(file_ast.classes)
                summary["total_lines"] += file_ast.total_lines
                
                # File info
                summary["files"].append({
                    "file_path": file_path,
                    "language": file_ast.language,
                    "functions": len(file_ast.functions),
                    "classes": len(file_ast.classes),
                    "lines": file_ast.total_lines,
                    "complexity": file_ast.complexity_score
                })
        
        return summary
    
    def find_elements_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Find all AST elements (functions, classes) by name across all files"""
        
        results = []
        name_lower = name.lower()
        
        for file_path in self._index_cache.keys():
            file_ast = self.get_cached_ast(file_path)
            if file_ast:
                # Check functions
                for func in file_ast.functions:
                    if name_lower in func.name.lower():
                        results.append({
                            "type": "function",
                            "name": func.name,
                            "file_path": file_path,
                            "line": func.start_line,
                            "end_line": func.end_line,
                            "element": func
                        })
                
                # Check classes
                for cls in file_ast.classes:
                    if name_lower in cls.name.lower():
                        results.append({
                            "type": "class",
                            "name": cls.name,
                            "file_path": file_path,
                            "line": cls.start_line,
                            "end_line": cls.end_line,
                            "element": cls
                        })
        
        return results
    
    def find_elements_in_file(self, file_path: str, element_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find AST elements in a specific file"""
        
        file_ast = self.get_cached_ast(file_path)
        if not file_ast:
            return []
        
        results = []
        
        # Get all functions and classes
        all_elements = file_ast.functions + file_ast.classes
        
        for element in all_elements:
            if element_name is None or element_name.lower() in element.name.lower():
                results.append({
                    "type": element.type,
                    "name": element.name,
                    "file_path": file_path,
                    "line": element.start_line,
                    "end_line": element.end_line,
                    "element": element
                })
        
        return results
    
    def clear_cache(self):
        """Clear all cached AST data"""
        try:
            # Clear memory cache
            self._memory_cache.clear()
            self._index_cache.clear()
            
            # Remove cache files
            if self.project_cache_dir.exists():
                import shutil
                shutil.rmtree(self.project_cache_dir)
                self.project_cache_dir.mkdir(parents=True, exist_ok=True)
                self.files_cache_dir.mkdir(exist_ok=True)
            
            print(f"[DEBUG] Cleared AST cache for project {self.project_name}")
            
        except Exception as e:
            print(f"[DEBUG] Error clearing cache: {e}")
    
    def cleanup_old_cache(self, max_age_days: int = 7):
        """Remove old cache entries"""
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        files_to_remove = []
        for file_path, index_info in self._index_cache.items():
            if index_info.get("last_parsed", 0) < cutoff_time:
                files_to_remove.append(file_path)
        
        for file_path in files_to_remove:
            # Remove cache file
            cache_filename = self._index_cache[file_path].get("cache_filename")
            if cache_filename:
                cache_file_path = self.files_cache_dir / cache_filename
                if cache_file_path.exists():
                    cache_file_path.unlink()
            
            # Remove from index
            del self._index_cache[file_path]
            
            # Remove from memory
            if file_path in self._memory_cache:
                del self._memory_cache[file_path]
        
        if files_to_remove:
            self._save_index()
            print(f"[DEBUG] Cleaned up {len(files_to_remove)} old cache entries")


class GlobalASTCacheManager:
    """Manages AST caches for all projects"""
    
    def __init__(self, base_cache_dir: str = "ast_cache"):
        self.base_cache_dir = Path(base_cache_dir)
        self.base_cache_dir.mkdir(exist_ok=True)
        self.project_caches: Dict[str, ProjectASTCache] = {}
    
    def get_project_cache(self, project_id: str, project_name: str) -> ProjectASTCache:
        """Get or create AST cache for a project"""
        
        if project_id not in self.project_caches:
            self.project_caches[project_id] = ProjectASTCache(
                project_id, project_name, str(self.base_cache_dir)
            )
        
        return self.project_caches[project_id]
    
    def clear_project_cache(self, project_id: str):
        """Clear cache for a specific project"""
        if project_id in self.project_caches:
            self.project_caches[project_id].clear_cache()
            del self.project_caches[project_id]
    
    def cleanup_all_caches(self, max_age_days: int = 7):
        """Cleanup old cache entries across all projects"""
        for cache in self.project_caches.values():
            cache.cleanup_old_cache(max_age_days)
    
    def get_global_summary(self) -> Dict[str, Any]:
        """Get summary of all projects' AST caches"""
        
        summary = {
            "total_projects": len(self.project_caches),
            "projects": []
        }
        
        for project_id, cache in self.project_caches.items():
            project_summary = cache.get_project_ast_summary()
            summary["projects"].append(project_summary)
        
        return summary


# Global cache manager instance
global_ast_cache = GlobalASTCacheManager()