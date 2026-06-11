"""Python 空值安全检查规则 V4 —— 精准区分外部变量与安全局部变量"""

import ast
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class PythonNullSafetyRule(BaseRule):
    rule_id = "PY_NULL_SAFETY_001"
    name = "Python 空值安全检查"
    description = "检测可能为 None 的对象被直接使用而未做空值检查"
    severity = Severity.SEVERE
    category = BugCategory.NULL_SAFETY
    languages = ["python"]
    layer = RuleLayer.PATTERN  # base_confidence = 0.75
    SAFE_MODULES = {
        "re", "os", "sys", "json", "math", "random", "datetime",
        "collections", "itertools", "functools", "typing", "pathlib",
        "logging", "hashlib", "subprocess", "argparse", "asyncio",
        "threading", "multiprocessing", "csv", "io", "pickle",
        "gzip", "zipfile", "abc", "dataclasses", "enum", "inspect",
        "traceback", "warnings", "contextlib", "copy", "pprint",
        "textwrap", "configparser", "secrets", "uuid", "base64",
    }

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs

        imported_modules = set()
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module.split(".")[0])

        visitor = _NullSafetyVisitorV4(source, imported_modules)
        visitor.visit(ast_tree)
        for issue in visitor.issues:
            bugs.append(self._create_bug(
                file_path=file_path, line_start=issue["line"], line_end=issue["line"],
                title=issue["title"], description=issue["detail"],
                code_snippet=issue["snippet"],
                fix_suggestion=issue.get("fix", "添加空值检查"),
                confidence=issue.get("confidence", 0.7),
                extra_id=f"L{issue['line']}",
                root_cause=RootCause.NO_DEFENSE,
            ))
        return bugs


class _NullSafetyVisitorV4(ast.NodeVisitor):
    def __init__(self, source: str, imported_modules: set):
        self.source_lines = source.split("\n")
        self.issues = []
        self.imported_modules = imported_modules
        self._safe_in_checks: set[int] = set()
        self._local_assigns: set[str] = set()  # 局部赋值变量（安全）
        self._func_params: set[str] = set()     # 函数参数（可能为 None）

    def visit_If(self, node):
        if isinstance(node.test, ast.Compare):
            for op in node.test.ops:
                if isinstance(op, (ast.IsNot, ast.Is)):
                    for comp in node.test.comparators:
                        if isinstance(comp, ast.Constant) and comp.value is None:
                            for child in ast.walk(node):
                                if hasattr(child, "lineno"):
                                    self._safe_in_checks.add(child.lineno)
        # and 短路不求值: if auth and auth.startswith(...)
        if isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.And):
            for value in node.test.values:
                if isinstance(value, ast.Name):
                    for child in ast.walk(node):
                        if hasattr(child, "lineno"):
                            self._safe_in_checks.add(child.lineno)
                    break
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        for arg in node.args.args:
            self._func_params.add(arg.arg)
        self.generic_visit(node)
    visit_AsyncFunctionDef = visit_FunctionDef

    def _add_target(self, target):
        if isinstance(target, ast.Name):
            if target.id not in self._func_params:
                self._local_assigns.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._add_target(elt)

    def visit_Assign(self, node):
        for target in node.targets:
            self._add_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if node.target:
            self._add_target(node.target)
        self.generic_visit(node)

    def visit_For(self, node):
        self._add_target(node.target)
        self.generic_visit(node)
    visit_AsyncFor = visit_For

    def visit_ListComp(self, node):
        for gen in node.generators:
            self._add_target(gen.target)
        self.generic_visit(node)
    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            name = node.value.id
            if name in PythonNullSafetyRule.SAFE_MODULES or name in self.imported_modules:
                self.generic_visit(node)
                return
            if name in ("self", "cls"):
                self.generic_visit(node)
                return
            # 函数参数 + 未在 if None check 中 = 需要检查
            if name in self._func_params and node.lineno not in self._safe_in_checks:
                snippet = self.source_lines[node.lineno - 1].strip() if node.lineno <= len(self.source_lines) else ""
                self.issues.append({
                    "title": "属性访问 '%s.%s' 缺少空值保护" % (name, node.attr),
                    "line": node.lineno,
                    "detail": "参数 '%s' 可能为 None，访问 '%s.%s' 前应检查" % (name, name, node.attr),
                    "snippet": snippet[:200],
                    "fix": "在访问前添加: if %s is not None:" % name,
                    "confidence": 0.7,
                })
            # 非参数、非局部、非安全检查 = 外部来源变量
            elif name not in self._local_assigns and node.lineno not in self._safe_in_checks:
                snippet = self.source_lines[node.lineno - 1].strip() if node.lineno <= len(self.source_lines) else ""
                self.issues.append({
                    "title": "属性访问 '%s.%s' 缺少空值保护" % (name, node.attr),
                    "line": node.lineno,
                    "detail": "对 '%s' 访问属性 '%s' 前未检查是否为 None" % (name, node.attr),
                    "snippet": snippet[:200],
                    "fix": "在访问前添加: if %s is not None:" % name,
                    "confidence": 0.5,
                })
        self.generic_visit(node)

    def visit_Subscript(self, node):
        if isinstance(node.value, ast.Name):
            name = node.value.id
            if name in ("self", "cls"):
                self.generic_visit(node)
                return
            if name in self._func_params and node.lineno not in self._safe_in_checks:
                snippet = self.source_lines[node.lineno - 1].strip() if node.lineno <= len(self.source_lines) else ""
                self.issues.append({
                    "title": "下标访问 '%s[...]' 缺少空值保护" % name,
                    "line": node.lineno,
                    "detail": "参数 '%s' 可能为 None，使用下标前应检查" % name,
                    "snippet": snippet[:200],
                    "fix": "添加检查: if %s is not None:" % name,
                    "confidence": 0.7,
                })
            elif name not in self._local_assigns and node.lineno not in self._safe_in_checks:
                snippet = self.source_lines[node.lineno - 1].strip() if node.lineno <= len(self.source_lines) else ""
                self.issues.append({
                    "title": "下标访问 '%s[...]' 缺少空值保护" % name,
                    "line": node.lineno,
                    "detail": "对 '%s' 使用下标访问前未检查是否为 None 或空",
                    "snippet": snippet[:200],
                    "fix": "添加检查: if %s is not None:" % name,
                    "confidence": 0.5,
                })
        self.generic_visit(node)
