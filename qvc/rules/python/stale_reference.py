"""Python 过期引用检测规则 — V5 核心差异化规则

检测 AI Agent 生成的代码引用了已删除、已重命名或已移动的符号。
多轮对话中 AI 可能在第 5 轮定义了一个函数，到第 20 轮又删了它，
但忘记更新所有引用方。
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class PythonStaleReferenceRule(BaseRule):
    """检测过期引用 — AI 上下文遗忘导致引用了不存在的符号"""

    rule_id = "PY_STALE_REF_001"
    name = "Python 过期引用检测"
    description = "检测 import 引用的模块/符号在项目中不存在 — AI 多轮对话上下文遗忘"
    severity = Severity.SEVERE
    category = BugCategory.DEP_CHAIN
    languages = ["python"]
    layer = RuleLayer.PATTERN
    base_confidence = 0.85

    # 类级别缓存
    _imports: list[dict] = []  # [{module, names, file, line, level}]
    _defined_symbols: dict[str, set[str]] = defaultdict(set)  # {file_abs: {symbols}}
    _all_symbols: set[str] = set()  # 全局符号表（用于快速查找）
    _init_exports: dict[str, set[str]] = defaultdict(set)  # {package_path: {exported_symbols}}

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        """单文件分析：收集导入和定义"""
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs

        file_str = str(file_path)

        for node in ast.walk(ast_tree):
            # 收集函数定义
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._defined_symbols[file_str].add(node.name)
                self._all_symbols.add(node.name)

            # 收集类定义
            if isinstance(node, ast.ClassDef):
                self._defined_symbols[file_str].add(node.name)
                self._all_symbols.add(node.name)

            # 收集顶层赋值（模块级变量）
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self._defined_symbols[file_str].add(target.id)
                        self._all_symbols.add(target.id)

            # 收集 import 语句
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_name = alias.name.split(".")[0]
                    self._imports.append({
                        "type": "import",
                        "module": alias.name,
                        "top_name": top_name,
                        "names": [alias.asname or alias.name],
                        "file": file_str,
                        "line": node.lineno,
                    })

            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                # 只关注绝对导入（level=0）
                if node.level > 0:
                    continue
                top_name = node.module.split(".")[0]
                imported = [a.asname or a.name for a in node.names] if node.names else [node.module]
                self._imports.append({
                    "type": "import_from",
                    "module": node.module,
                    "top_name": top_name,
                    "names": imported,
                    "file": file_str,
                    "line": node.lineno,
                })

        # 收集 __init__.py 中的导出
        if file_path.name == "__init__.py":
            self._collect_init_exports(file_path, source, ast_tree)

        return bugs

    @classmethod
    def cross_file_check(cls, file_paths: list[Path], create_bug_fn) -> list:
        """跨文件检查：验证所有 import 的目标是否存在"""
        bugs = []

        # 构建文件系统中的模块映射
        project_modules = cls._build_module_map(file_paths)

        for imp in cls._imports:
            top_name = imp["top_name"]
            module = imp["module"]

            # 跳过标准库和知名第三方库
            if cls._is_stdlib_or_known(top_name):
                continue

            # 跳过项目中已存在的模块
            if cls._module_exists(top_name, module, project_modules):
                continue

            # 检查 __init__.py 再导出
            if cls._is_reexported(top_name, project_modules):
                continue

            # 到这里：引用了一个项目中不存在的模块
            file_path = Path(imp["file"])
            confidence = 0.90 if cls._looks_like_project_module(top_name) else 0.60

            bugs.append(create_bug_fn(
                fp=file_path,
                line_start=imp["line"],
                line_end=imp["line"],
                title=f"引用的模块 '{top_name}' 在项目中不存在",
                description=(
                    f"'{module}' 未在项目目录和 sys.path 中找到。"
                    f"模块可能已被删除、重命名或移动到其他位置。"
                    f"这是 AI Agent 多轮对话上下文遗忘的典型症状。"
                ),
                code_snippet=f"from {module} import ..." if imp["type"] == "import_from" else f"import {module}",
                fix_suggestion=f"确认 '{module}' 是否存在。如果已重命名，更新 import 语句；如果已删除，移除相关代码",
                confidence=confidence,
                extra_id=top_name,
                root_cause=RootCause.AGENT_ISOLATION,
            ))

        # 清理缓存
        cls._clear_cache()
        return bugs

    @classmethod
    def _build_module_map(cls, file_paths: list[Path]) -> dict[str, Path]:
        """构建模块名 → 文件路径的映射"""
        module_map = {}
        for fp in file_paths:
            if fp.suffix != ".py":
                continue
            stem = fp.stem
            # 记录文件名（不含扩展名）
            if stem != "__init__":
                module_map[stem] = fp
            # __init__.py → 包名
            if fp.name == "__init__.py":
                pkg_name = fp.parent.name
                module_map[pkg_name] = fp.parent
        return module_map

    @classmethod
    def _module_exists(cls, top_name: str, full_path: str, module_map: dict) -> bool:
        """检查模块是否在项目中存在"""
        # 直接匹配
        if top_name in module_map:
            return True
        # 检查完整路径的第一段
        parts = full_path.split(".")
        if parts[0] in module_map:
            return True
        return False

    @classmethod
    def _is_reexported(cls, name: str, module_map: dict) -> bool:
        """检查是否通过 __init__.py 再导出"""
        return name in cls._init_exports

    @classmethod
    def _looks_like_project_module(cls, name: str) -> bool:
        """判断模块名是否看起来像项目内部模块"""
        common_project_names = {
            "app", "src", "backend", "frontend", "core", "utils",
            "models", "services", "api", "config", "tests", "lib",
            "handlers", "routes", "schemas", "middleware", "helpers",
            "controllers", "repositories", "entities", "dto", "validators",
        }
        return name.lower() in common_project_names or (
            name.replace("_", "").islower() and len(name) > 3
        )

    @classmethod
    def _is_stdlib_or_known(cls, module_name: str) -> bool:
        stdlib = {
            "os", "sys", "re", "json", "time", "datetime", "math", "random",
            "collections", "itertools", "functools", "typing", "pathlib",
            "shutil", "tempfile", "logging", "hashlib", "hmac", "builtins", "subprocess", "argparse",
            "asyncio", "threading", "multiprocessing", "http", "urllib", "socket",
            "ssl", "email", "xml", "csv", "sqlite3", "unittest", "io", "pickle",
            "gzip", "zipfile", "abc", "dataclasses", "enum", "inspect", "traceback",
            "warnings", "contextlib", "copy", "pprint", "textwrap", "concurrent",
            "configparser", "secrets", "uuid", "base64", "ast", "webbrowser",
            "fnmatch", "glob", "stat", "string", "struct", "codecs", "venv",
        }
        known = {
            "fastapi", "flask", "django", "sqlalchemy", "pydantic", "requests",
            "httpx", "aiohttp", "click", "typer", "rich", "numpy", "pandas",
            "pytest", "celery", "redis", "pymongo", "starlette", "uvicorn",
            "jinja2", "yaml", "toml", "openai", "anthropic", "langchain",
            "alembic", "gitpython", "dotenv", "bcrypt", "passlib",
            "python-dotenv", "pydantic-settings", "python-multipart", "docx", "pptx", "matplotlib", "seaborn", "plotly", "scipy", "sklearn", "scikit-learn", "tensorflow", "torch", "transformers", "pillow", "PIL", "opencv", "cv2", "beautifulsoup4", "bs4", "lxml", "requests", "urllib3", "certifi", "charset-normalizer", "idna", "PyYAML", "yaml", "watchdog", "pydub", "moviepy",
        }
        return module_name in stdlib or module_name in known

    @classmethod
    def _collect_init_exports(cls, file_path: Path, source: str, ast_tree):
        """收集 __init__.py 中的导出符号"""
        pkg = str(file_path.parent)
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.ImportFrom):
                if node.names:
                    for alias in node.names:
                        cls._init_exports[pkg].add(alias.asname or alias.name)

    @classmethod
    def _clear_cache(cls):
        cls._imports.clear()
        cls._defined_symbols.clear()
        cls._all_symbols.clear()
        cls._init_exports.clear()
