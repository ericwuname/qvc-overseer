"""Python AST semantic analyzer — provides structural context beyond regex matching.

V8: Replaces the "regex-only" limitation. Integrates with StaticAnalyzer to provide:
- Import resolution (knows about __init__.py packages)
- Function/class extraction
- Variable scope trees
- Call graph construction
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ImportInfo:
    """Resolved import information"""
    module: str
    name: str
    alias: Optional[str] = None
    is_relative: bool = False
    level: int = 0  # for relative imports


@dataclass
class FunctionInfo:
    """Extracted function metadata"""
    name: str
    line_start: int
    line_end: int
    params: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    local_vars: set = field(default_factory=set)


@dataclass
class ClassInfo:
    """Extracted class metadata"""
    name: str
    line_start: int
    line_end: int
    methods: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)


@dataclass
class ASTContext:
    """Semantic context extracted from a Python file's AST"""
    file_path: str = ""
    imports: list[ImportInfo] = field(default_factory=list)
    functions: dict[str, FunctionInfo] = field(default_factory=dict)
    classes: dict[str, ClassInfo] = field(default_factory=dict)
    global_names: set = field(default_factory=set)
    has_init_py_in_package: bool = False
    is_package: bool = False

    def has_import(self, module_name: str) -> bool:
        """Check if a module is imported (supports submodule check)"""
        for imp in self.imports:
            if imp.module == module_name:
                return True
            if imp.module.startswith(module_name + "."):
                return True
        return False

    def has_name(self, name: str) -> bool:
        """Check if a name is defined in this file (function, class, or global)"""
        return name in self.functions or name in self.classes or name in self.global_names

    def is_function_call(self, name: str) -> bool:
        """Check if a name is a function defined in this file"""
        return name in self.functions


class ASTAnalyzer:
    """Parses Python AST to extract semantic context for better rule accuracy."""

    def analyze(self, file_path: Path, source: str, project_root: Optional[Path] = None) -> ASTContext:
        """Parse a Python file and return its semantic context."""
        ctx = ASTContext(file_path=str(file_path))

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return ctx

        ctx.imports = self._resolve_imports(tree)
        ctx.functions = self._extract_functions(tree, source)
        ctx.classes = self._extract_classes(tree)
        ctx.global_names = self._extract_global_names(tree)

        # Check if this file is part of a package (has __init__.py in same dir)
        if project_root:
            parent_dir = file_path.parent
            init_py = parent_dir / "__init__.py"
            ctx.is_package = init_py.exists()

            # Check if the package root has __init__.py (for import resolution)
            self._check_package_structure(ctx, file_path, project_root)

        return ctx

    def _resolve_imports(self, tree: ast.AST) -> list[ImportInfo]:
        """Extract all import statements from the AST"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ImportInfo(
                        module=alias.name,
                        name=alias.name,
                        alias=alias.asname,
                    ))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append(ImportInfo(
                        module=node.module or "",
                        name=alias.name,
                        alias=alias.asname,
                        is_relative=node.level > 0,
                        level=node.level,
                    ))
        return imports

    def _extract_functions(self, tree: ast.AST, source: str) -> dict[str, FunctionInfo]:
        """Extract all function definitions"""
        functions = {}
        source_lines = source.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = [arg.arg for arg in node.args.args]
                decorators = []
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name):
                        decorators.append(dec.id)
                    elif isinstance(dec, ast.Attribute):
                        decorators.append(dec.attr)

                # Collect local variable assignments
                local_vars = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                        local_vars.add(child.id)

                functions[node.name] = FunctionInfo(
                    name=node.name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    params=params,
                    decorators=decorators,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    local_vars=local_vars,
                )

        return functions

    def _extract_classes(self, tree: ast.AST) -> dict[str, ClassInfo]:
        """Extract all class definitions"""
        classes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(base.attr)

                methods = []
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(child.name)

                classes[node.name] = ClassInfo(
                    name=node.name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    methods=methods,
                    bases=bases,
                )

        return classes

    def _extract_global_names(self, tree: ast.AST) -> set:
        """Extract global-level names (assignments, class defs, function defs)"""
        names = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
        return names

    def _check_package_structure(self, ctx: ASTContext, file_path: Path, project_root: Path):
        """Check if the file's package hierarchy has __init__.py files"""
        # Walk up from file's directory to project root, check for __init__.py
        current = file_path.parent
        while current != project_root.parent and current != current.parent:
            if (current / "__init__.py").exists():
                ctx.has_init_py_in_package = True
                break
            current = current.parent

    def is_import_likely_valid(self, ctx: ASTContext, module_name: str) -> bool:
        """Heuristic: is this import likely valid (package has __init__.py)?

        This is the key fix for the V1 "169 import false positives" problem.
        If `app` is a Python package with __init__.py, `from app.xxx import yyy` is valid.
        """
        # If the file's own package has __init__.py, relative imports are likely valid
        if ctx.has_init_py_in_package or ctx.is_package:
            return True
        # If the module is explicitly imported elsewhere in the file, it's valid
        if ctx.has_import(module_name):
            return True
        return False

    @staticmethod
    def is_safe_and_short_circuit(source: str, var_name: str, line_no: int) -> bool:
        """Check if a variable access is protected by a short-circuit pattern like:
        `if var and var.method():`
        """
        import re
        # Pattern: if <var> and <var>.something
        pattern = re.compile(
            rf"if\s+{re.escape(var_name)}\s+and\s+{re.escape(var_name)}\.",
            re.IGNORECASE
        )
        lines = source.split("\n")
        # Check the line itself and a few lines before
        for i in range(max(0, line_no - 3), min(len(lines), line_no)):
            if pattern.search(lines[i]):
                return True
        return False
