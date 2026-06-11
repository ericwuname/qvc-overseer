"""Python 变量作用域检查规则 —— V2 修复行号检测"""

import ast
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class PythonVariableScopeRule(BaseRule):
    rule_id = "PY_VAR_SCOPE_001"
    name = "Python 变量作用域检查"
    description = "检测函数/模块中引用了未在作用域链中定义的变量"
    severity = Severity.FATAL
    category = BugCategory.VAR_SCOPE
    languages = ["python"]
    layer = RuleLayer.HEURISTIC  # base_confidence = 0.35
    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs
        visitor = _VariableScopeVisitor(source)
        visitor.visit(ast_tree)
        for issue in visitor.issues:
            bugs.append(self._create_bug(
                file_path=file_path,
                line_start=issue["line"],
                line_end=issue["line"],
                title=f"可能未定义的变量 '{issue['name']}'",
                description=issue["detail"],
                code_snippet=issue["snippet"],
                fix_suggestion=issue.get("fix", "检查变量是否已在作用域内定义"),
                confidence=issue.get("confidence", 0.8),
                extra_id=issue["name"],
            ))
        return bugs


PYTHON_BUILTINS = {
    "print", "len", "range", "int", "str", "float", "bool", "complex",
    "list", "dict", "set", "tuple", "frozenset", "type", "object",
    "isinstance", "issubclass", "enumerate", "zip", "map", "filter",
    "sorted", "reversed", "any", "all", "sum", "min", "max",
    "abs", "round", "pow", "divmod", "input", "next", "iter",
    "hash", "id", "getattr", "setattr", "hasattr", "delattr",
    "True", "False", "None", "Exception", "ValueError", "TypeError",
    "KeyError", "IndexError", "AttributeError", "ImportError",
    "RuntimeError", "NotImplementedError", "StopIteration",
    "OSError", "IOError", "FileNotFoundError", "PermissionError",
    "SyntaxError", "IndentationError", "TabError", "NameError", "UnboundLocalError",
    "ZeroDivisionError", "OverflowError", "FloatingPointError", "ArithmeticError",
    "BufferError", "EOFError", "LookupError", "MemoryError", "RecursionError",
    "ReferenceError", "SystemError", "SystemExit", "KeyboardInterrupt",
    "UnicodeError", "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeTranslateError",
    "AssertionError", "BlockingIOError", "BrokenPipeError", "ChildProcessError",
    "ConnectionError", "ConnectionAbortedError", "ConnectionRefusedError",
    "ConnectionResetError", "FileExistsError", "InterruptedError",
    "IsADirectoryError", "NotADirectoryError", "ModuleNotFoundError",
    "ProcessLookupError", "TimeoutError", "StopAsyncIteration", "Warning",
    "UserWarning", "DeprecationWarning", "PendingDeprecationWarning",
    "SyntaxWarning", "RuntimeWarning", "FutureWarning", "ImportWarning",
    "UnicodeWarning", "BytesWarning", "ResourceWarning",
    "super", "self", "cls", "__name__", "__file__", "__doc__",
    "open", "bytes", "bytearray", "memoryview", "slice",
    "property", "staticmethod", "classmethod", "callable",
    "format", "repr", "ascii", "chr", "ord", "bin", "oct", "hex",
    "locals", "globals", "vars", "dir", "eval", "exec", "compile",
    "__import__", "breakpoint", "help",
}


class _VariableScopeVisitor(ast.NodeVisitor):
    def __init__(self, source: str):
        self.source_lines = source.split("\n")
        self.scopes = [{"defined": set(), "used": {}, "used_lines": {}}]
        self.issues = []

    def _push_scope(self):
        self.scopes.append({"defined": set(), "used": {}, "used_lines": {}})

    def _pop_scope(self):
        if len(self.scopes) <= 1:
            return
        scope = self.scopes.pop()
        all_defined = set()
        for outer in self.scopes:
            all_defined |= outer["defined"]
        undefined_vars = set(scope["used"].keys()) - scope["defined"] - all_defined - PYTHON_BUILTINS

        for var in undefined_vars:
            if var.startswith("_"):
                continue
            use_line = scope["used_lines"].get(var, 1)
            snippet = self.source_lines[use_line - 1].strip() if use_line <= len(self.source_lines) else ""
            self.issues.append({
                "name": var,
                "line": use_line,
                "detail": "变量 '%s' 在当前作用域使用了但未在任何外围作用域定义" % var,
                "snippet": snippet[:200],
                "fix": "检查是否应在作用域内声明 '%s'，或确认变量来源" % var,
                "confidence": 0.8,
            })

    def visit_FunctionDef(self, node):
        self.scopes[-1]["defined"].add(node.name)
        self._push_scope()
        scope = self.scopes[-1]
        for arg in node.args.args:
            scope["defined"].add(arg.arg)
        if node.args.vararg:
            scope["defined"].add(node.args.vararg.arg)
        if node.args.kwarg:
            scope["defined"].add(node.args.kwarg.arg)
        self.generic_visit(node)
        self._pop_scope()
    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.scopes[-1]["defined"].add(node.name)
        self._push_scope()
        self.generic_visit(node)
        self._pop_scope()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.scopes[-1]["defined"].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.scopes[-1]["used"][node.id] = True
            # 记录每个变量最近一次使用的行号
            if hasattr(node, "lineno"):
                self.scopes[-1]["used_lines"][node.id] = node.lineno

    def visit_Assign(self, node):
        for target in node.targets:
            self._add_defined(target)
        self.generic_visit(node)

    def _add_defined(self, node):
        if isinstance(node, ast.Name):
            self.scopes[-1]["defined"].add(node.id)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                self._add_defined(elt)

    def visit_AnnAssign(self, node):
        if node.target:
            self._add_defined(node.target)
        self.generic_visit(node)

    def visit_NamedExpr(self, node):
        self._add_defined(node.target)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.scopes[-1]["defined"].add(name)
    visit_ImportFrom = visit_Import

    def visit_For(self, node):
        self._add_defined(node.target)
        self.generic_visit(node)
    visit_AsyncFor = visit_For

    def visit_ListComp(self, node):
        self._push_scope()
        for gen in node.generators:
            self._add_defined(gen.target)
        self.generic_visit(node)
        self._pop_scope()
    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_Lambda(self, node):
        self._push_scope()
        scope = self.scopes[-1]
        for arg in node.args.args:
            scope["defined"].add(arg.arg)
        if node.args.vararg:
            scope["defined"].add(node.args.vararg.arg)
        if node.args.kwarg:
            scope["defined"].add(node.args.kwarg.arg)
        self.generic_visit(node)
        self._pop_scope()

    def visit_ExceptHandler(self, node):
        if node.name:
            self.scopes[-1]["defined"].add(node.name)
        self.generic_visit(node)

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars:
                self._add_defined(item.optional_vars)
        self.generic_visit(node)
    visit_AsyncWith = visit_With
