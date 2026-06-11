"""Python API 签名校验规则 —— 检测函数定义与调用的参数不匹配"""

import ast
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class PythonAPISignatureRule(BaseRule):
    """检测函数调用参数数量与定义不一致"""
    rule_id = "PY_API_SIGNATURE_001"
    name = "Python API 签名校验"
    description = "检测函数调用时传入的参数数量与函数定义不匹配"
    severity = Severity.FATAL
    category = BugCategory.API_MISMATCH
    languages = ["python"]
    layer = RuleLayer.PATTERN  # base_confidence = 0.7
    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs

        # 第一步：收集所有函数定义（名称 -> 参数信息）
        func_defs = {}
        class _FuncDefCollector(ast.NodeVisitor):
            def __init__(self):
                self._class_depth = 0
                self._current_class = None

            def visit_ClassDef(self, node):
                self._class_depth += 1
                prev_class = self._current_class
                self._current_class = node.name
                self.generic_visit(node)
                self._current_class = prev_class
                self._class_depth -= 1

            def visit_FunctionDef(self, node):
                is_method = self._class_depth > 0
                args = node.args
                arg_names = [a.arg for a in args.args]
                implicit_self = 1 if is_method and arg_names and arg_names[0] in ("self", "cls") else 0
                required = max(0, len(args.args) - len(args.defaults) - implicit_self)
                total = len(args.args) - implicit_self
                has_varargs = bool(args.vararg)
                has_kwargs = bool(args.kwarg)
                func_defs[node.name] = {
                    "required": required,
                    "total": total,
                    "has_varargs": has_varargs,
                    "has_kwargs": has_kwargs,
                    "line": node.lineno,
                    "is_method": is_method,
                    "class_name": self._current_class,
                }
                self.generic_visit(node)
            visit_AsyncFunctionDef = visit_FunctionDef

        _FuncDefCollector().visit(ast_tree)

        # 第二步：检查所有函数调用
        class _CallChecker(ast.NodeVisitor):
            def __init__(self, func_defs, source_lines, bug_creator, file_path):
                self.func_defs = func_defs
                self.source_lines = source_lines
                self.create_bug = bug_creator
                self.file_path = file_path
                self.bugs = []

            def visit_Call(self, node):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name and func_name in self.func_defs:
                    definition = self.func_defs[func_name]
                    # obj.method() ?????????
                    if isinstance(node.func, ast.Attribute) and not definition.get("is_method"):
                        self.generic_visit(node)
                        return
                    call_args = len(node.args)
                    call_kwargs = len(node.keywords)

                    # 如果有 *args 或 **kwargs，不做严格检查
                    if definition["has_varargs"] or definition["has_kwargs"]:
                        return

                    # 检查参数数量
                    if call_args < definition["required"]:
                        snippet = self.source_lines[node.lineno - 1].strip() if node.lineno <= len(self.source_lines) else ""
                        self.bugs.append(self.create_bug(
                            file_path=self.file_path,
                            line_start=node.lineno,
                            line_end=node.lineno,
                            title=f"函数 '{func_name}' 调用参数不足",
                            description=f"'{func_name}' 需要至少 {definition['required']} 个参数，但只传入了 {call_args} 个",
                            code_snippet=snippet[:200],
                            fix_suggestion=f"检查函数定义（第 {definition['line']} 行），补全缺失的参数",
                            root_cause=RootCause.AGENT_ISOLATION if func_name != "self" else None,
                            confidence=0.85,
                            extra_id=f"{func_name}_args",
                        ))
                    elif call_args > definition["total"]:
                        snippet = self.source_lines[node.lineno - 1].strip() if node.lineno <= len(self.source_lines) else ""
                        self.bugs.append(self.create_bug(
                            file_path=self.file_path,
                            line_start=node.lineno,
                            line_end=node.lineno,
                            title=f"函数 '{func_name}' 调用参数过多",
                            description=f"'{func_name}' 最多接受 {definition['total']} 个参数，但传入了 {call_args} 个",
                            code_snippet=snippet[:200],
                            fix_suggestion=f"检查函数定义（第 {definition['line']} 行），移除多余的参数或添加 *args",
                            root_cause=RootCause.AGENT_ISOLATION,
                            confidence=0.85,
                            extra_id=f"{func_name}_args",
                        ))

                self.generic_visit(node)

        checker = _CallChecker(
            func_defs,
            source.split("\n"),
            self._create_bug,
            file_path,
        )
        checker.visit(ast_tree)
        bugs.extend(checker.bugs)

        return bugs
