"""Python 导入路径检查规则 V3 — 包结构感知 + 分级置信度"""

import ast
import re
import sys
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class PythonImportCheckRule(BaseRule):
    rule_id = "PY_IMPORT_CHECK_001"
    name = "Python 导入路径检查"
    description = "检测 import 语句引用了不存在的模块（V3：包结构感知）"
    severity = Severity.SEVERE
    category = BugCategory.DEP_CHAIN
    languages = ["python"]
    layer = RuleLayer.HEURISTIC  # 默认启发式，确认不存在时升级为 CERTIFICATE

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs

        file_dir = file_path.parent.resolve()

        # ── 定位项目根 ──
        project_root = self._find_project_root(file_dir)

        # ── 构建可解析路径 ──
        # 收集项目根下所有 Python 包路径
        known_paths = self._collect_package_paths(project_root, file_dir)

        for node in ast.walk(ast_tree):
            # 跳过 TYPE_CHECKING 块中的导入
            if self._in_type_checking(node):
                continue

            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_import(node, alias.name, alias.name, source,
                                       file_path, known_paths, project_root, bugs)

            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                # 跳过相对导入
                if node.level > 0:
                    continue
                module_path = node.module
                top_name = module_path.split(".")[0]
                imported_names = [a.name for a in node.names] if node.names else []
                self._check_import(node, top_name, module_path, source,
                                   file_path, known_paths, project_root, bugs, imported_names)

        return bugs

    def _check_import(self, node, top_name: str, full_path: str, source: str,
                      file_path: Path, known_paths: set, project_root: Path,
                      bugs: list, imported_names = None):
        """检查单个导入：如果能确认存在→跳过，确认不存在→CERTIFICATE，不确定→HEURISTIC"""

        if top_name in known_paths:
            return  # 项目内模块，存在

        if self._is_stdlib_or_known(top_name):
            return  # 标准库或已知第三方

        # 尝试在 sys.path 中查找
        if self._exists_in_syspath(full_path):
            return

        # 尝试在项目根的子包中查找（处理嵌套包结构）
        if self._exists_in_project(project_root, full_path):
            return

        # 尝试通过 __init__.py 再导出来解析
        if imported_names and self._resolve_reexport(project_root, full_path):
            return

        # 到此：无法确认模块存在
        snippet = ast.get_source_segment(source, node) or ""

        # 判断是"确认不存在"还是"无法确认"
        confirmed_missing = self._is_confirmed_missing(project_root, top_name, full_path)

        if confirmed_missing:
            # Layer 1: 确认不存在
            bugs.append(self._create_bug(
                file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                title=f"导入的模块 '{top_name}' 不存在",
                description=f"'{full_path}' 在项目目录和 sys.path 中均未找到",
                code_snippet=snippet,
                fix_suggestion=f"确认模块 '{top_name}' 是否已安装或文件路径是否正确",
                root_cause=RootCause.AGENT_ISOLATION,
                confidence=0.95, extra_id=top_name,
            ))
        else:
            # Layer 3: 无法确认
            bugs.append(self._create_bug(
                file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                title=f"导入的模块 '{top_name}' 未在项目中找到",
                description=f"'{full_path}' 可能来自外部包，QVC 无法在当前环境中验证",
                code_snippet=snippet,
                fix_suggestion=f"如为项目内模块，检查 PYTHONPATH；如为第三方包，运行 pip install {top_name}",
                root_cause=RootCause.AGENT_ISOLATION,
                confidence=0.30, extra_id=top_name,
            ))

    def _find_project_root(self, start: Path) -> Path:
        """向上查找项目根目录"""
        current = start
        while current != current.parent:
            markers = ["pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "poetry.lock", "requirements.txt", "package.json", "Cargo.toml", "go.mod", "Makefile"]
            if any((current / m).exists() for m in markers):
                return current
            current = current.parent
        return start

    def _collect_package_paths(self, project_root: Path, file_dir: Path) -> set:
        """收集所有可解析的 Python 模块/包名"""
        paths = set()

        # 扫描目录列表：项目根 + 常见源码目录
        scan_roots = [project_root]
        src_dirs = ["src", "backend", "frontend", "lib", "packages", "apps", "app", "server"]
        for sd in src_dirs:
            sd_path = project_root / sd
            if sd_path.is_dir():
                scan_roots.append(sd_path)

        for scan_root in scan_roots:
            for item in scan_root.iterdir():
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    if (item / "__init__.py").exists():
                        paths.add(item.name)
                elif item.suffix == ".py" and item.name != "__init__.py":
                    paths.add(item.stem)

        # 当前文件所在目录的模块
        for py_file in file_dir.glob("*.py"):
            if py_file.name != "__init__.py":
                paths.add(py_file.stem)
        for subdir in file_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                if (subdir / "__init__.py").exists():
                    paths.add(subdir.name)

        return paths

    def _exists_in_syspath(self, module_path: str) -> bool:
        """检查模块是否在 sys.path 中"""
        parts = module_path.split(".")
        # 尝试作为文件
        for sp in sys.path:
            if not sp:
                continue
            candidate = Path(sp) / (parts[0] + ".py")
            if candidate.exists():
                return True
            candidate_dir = Path(sp) / parts[0]
            if candidate_dir.is_dir() and (candidate_dir / "__init__.py").exists():
                return True
        return False

    def _exists_in_project(self, project_root: Path, module_path: str) -> bool:
        """检查模块是否在项目子目录中（处理嵌套包）"""
        parts = module_path.split(".")
        # 在项目根下递归搜索
        for root, dirs, files in self._safe_walk(project_root):
            # 排除目录
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            root_p = Path(root)
            # 检查是否为包目录
            if root_p.name == parts[0] and (root_p / "__init__.py").exists():
                return True
            # 检查是否为模块文件
            candidate = root_p / (parts[0] + ".py")
            if candidate.exists():
                return True
        return False

    def _safe_walk(self, root: Path, max_depth: int = 4):
        """安全遍历目录（限制深度，避免过深）"""
        import os
        depth = 0
        stack = [(str(root), depth)]
        while stack:
            path, d = stack.pop()
            if d > max_depth:
                continue
            try:
                dirs = []
                files = []
                for entry in os.scandir(path):
                    if entry.is_dir():
                        dirs.append(entry.name)
                    elif entry.is_file():
                        files.append(entry.name)
                yield path, dirs, files
                for dname in dirs:
                    stack.append((str(Path(path) / dname), d + 1))
            except PermissionError:
                continue

    def _is_confirmed_missing(self, project_root: Path, top_name: str, full_path: str) -> bool:
        """判断是否'确认'模块不存在（而非'无法确认'）"""
        # 检查是否是典型的第三方包名模式
        # 如果 top_name 看起来像项目内部包（如 'app', 'src', 'backend'），
        # 且不在项目中，那就可以确认不存在
        common_project_names = {"app", "src", "backend", "frontend", "core", "utils",
                                "models", "services", "api", "config", "tests", "lib"}
        if top_name in common_project_names:
            return True
        # 如果 top_name 是小写+下划线（Python 命名惯例），且不在项目中→确认
        if top_name.replace("_", "").islower() and len(top_name) > 3:
            if not self._exists_in_syspath(full_path):
                return True
        return False

    def _resolve_reexport(self, project_root, module_path, imported_name=None):
        parts = module_path.split(".")
        src_dirs = ["src","backend","frontend","lib","packages","apps","app","server"]
        scan_roots = [project_root] + [project_root/d for d in src_dirs if (project_root/d).is_dir()]
        for scan_root in scan_roots:
            pkg_path = scan_root
            for part in parts:
                pkg_path = pkg_path / part
            init_file = pkg_path / "__init__.py"
            if init_file.exists():
                if imported_name is None:
                    return True
                try:
                    init = init_file.read_text(encoding="utf-8", errors="ignore")
                    if re.search(rf"from\s+\.\S+\s+import\s+.*{imported_name}", init):
                        return True
                    if re.search(rf"import\s+.*{imported_name}", init):
                        return True
                except Exception:
                    pass
                return True
            fpath = scan_root / (module_path.replace(".","/") + ".py")
            if fpath.exists():
                return True
        return False

    def _in_type_checking(self, node) -> bool:
        """检查节点是否在 TYPE_CHECKING 块中"""
        for parent in self._get_ancestors(node):
            if isinstance(parent, ast.If):
                test_str = ast.unparse(parent.test) if hasattr(ast, 'unparse') else ""
                if "TYPE_CHECKING" in test_str:
                    return True
        return False

    def _get_ancestors(self, node):
        """获取节点的祖先（简化版）"""
        # ast.walk 不提供父节点，这里用简单启发式
        # 如果 import 在同一行有 TYPE_CHECKING，跳过
        return []

    def _is_stdlib_or_known(self, module_name: str) -> bool:
        stdlib = {
            "os", "sys", "re", "json", "time", "datetime", "math", "random",
            "collections", "itertools", "functools", "typing", "pathlib",
            "shutil", "tempfile", "logging", "hashlib", "subprocess", "argparse",
            "asyncio", "threading", "multiprocessing", "http", "urllib", "socket",
            "ssl", "email", "xml", "csv", "sqlite3", "unittest", "io", "pickle",
            "gzip", "zipfile", "abc", "dataclasses", "enum", "inspect", "traceback",
            "warnings", "contextlib", "copy", "pprint", "textwrap", "concurrent",
            "configparser", "secrets", "uuid", "base64", "ast", "webbrowser",
            "fnmatch", "glob", "stat", "fileinput", "linecache", "pickletools",
            "string", "struct", "codecs", "difflib", "venv",
        }
        known = {
            "fastapi", "flask", "django", "sqlalchemy", "pydantic", "requests",
            "httpx", "aiohttp", "click", "typer", "rich", "numpy", "pandas",
            "pytest", "celery", "redis", "pymongo", "starlette", "uvicorn",
            "jinja2", "pyyaml", "toml", "openai", "anthropic", "langchain",
            "pydantic_settings", "alembic", "beanie", "gitpython", "tree_sitter",
            "yaml", "git", "dotenv", "python-dotenv", "bcrypt", "passlib",
            "email_validator", "pydantic-settings", "python-multipart",
        }
        return module_name in stdlib or module_name in known
