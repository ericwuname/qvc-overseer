"""Python API 漂移检测规则 — V5 核心差异化规则

检测 AI Agent 在多轮对话中生成的同名函数在不同文件里签名不一致。
这是"外部监工"视角的典型应用：AI 自审沿着生成链检查，看不到跨文件矛盾。
"""

import ast
from pathlib import Path
from collections import defaultdict
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class PythonAPIDriftRule(BaseRule):
    """检测跨文件的函数签名漂移 — AI 上下文遗忘的典型症状"""

    rule_id = "PY_API_DRIFT_001"
    name = "Python API 签名漂移检测"
    description = "检测同名函数在不同文件中的参数签名不一致 — AI 多轮对话上下文遗忘"
    severity = Severity.SEVERE
    category = BugCategory.API_MISMATCH
    languages = ["python"]
    layer = RuleLayer.PATTERN
    base_confidence = 0.80

    # 类级别缓存：跨文件共享
    _signatures: dict[str, list[dict]] = {}  # {func_name: [{file, params, line}, ...]}
    _calls: list[dict] = []  # [{func_name, file, line, arg_count}]

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        """单文件分析：收集函数签名和调用"""
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs

        file_str = str(file_path)

        # 收集函数定义
        for node in ast.walk(ast_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = self._extract_params(node)
                key = node.name
                if key not in self._signatures:
                    self._signatures[key] = []
                self._signatures[key].append({
                    "file": file_str,
                    "line": node.lineno,
                    "params": params,
                    "param_count": len(params),
                    "required_count": sum(1 for p in params if not p.get("has_default")),
                    "has_varargs": bool(node.args.vararg),
                    "has_kwargs": bool(node.args.kwarg),
                })

            # 收集函数调用
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name:
                    self._calls.append({
                        "func_name": func_name,
                        "file": file_str,
                        "line": node.lineno,
                        "arg_count": len(node.args),
                        "kwarg_count": len(node.keywords),
                    })

        return bugs

    @classmethod
    def cross_file_check(cls, file_paths: list[Path], create_bug_fn) -> list:
        """跨文件检查：在所有文件分析完成后调用"""
        bugs = []

        for func_name, sigs in cls._signatures.items():
            if len(sigs) < 2:
                continue  # 只有一个定义，无漂移

            # 跳过魔术方法、私有方法
            if func_name.startswith("_"):
                continue

            # 按文件去重（同一文件内同名函数是重载，不算漂移）
            files_seen = set()
            unique_sigs = []
            for sig in sigs:
                if sig["file"] not in files_seen:
                    files_seen.add(sig["file"])
                    unique_sigs.append(sig)

            if len(unique_sigs) < 2:
                continue

            # 检查参数数量是否一致
            param_counts = [s["param_count"] for s in unique_sigs]
            if len(set(param_counts)) > 1:
                # 参数数量不同 → 高置信度漂移
                files_info = ", ".join(
                    f"{Path(s['file']).name}:{s['line']}({s['param_count']} params)"
                    for s in unique_sigs
                )
                bugs.append(create_bug_fn(
                    fp=Path(unique_sigs[0]["file"]),
                    line_start=unique_sigs[0]["line"],
                    line_end=unique_sigs[0]["line"],
                    title=f"函数 '{func_name}' 在不同文件中签名不一致",
                    description=(
                        f"'{func_name}' 在 {len(unique_sigs)} 个文件中有不同签名: {files_info}。"
                        f"这通常意味着 AI Agent 在多轮对话中忘记了最初定义的接口。"
                    ),
                    code_snippet="",
                    fix_suggestion=f"统一 '{func_name}' 的参数签名，选择一个版本作为标准并更新所有调用方",
                    confidence=0.90,
                    extra_id=f"{func_name}_drift",
                    root_cause=RootCause.AGENT_ISOLATION,
                ))
                continue

            # 检查参数名是否一致（参数数量相同但名称不同 → 中置信度）
            if all(s["param_count"] > 0 for s in unique_sigs):
                param_name_sets = [tuple(p["name"] for p in s["params"]) for s in unique_sigs]
                if len(set(param_name_sets)) > 1:
                    files_info = ", ".join(
                        f"{Path(s['file']).name}:{s['line']}"
                        for s in unique_sigs
                    )
                    bugs.append(create_bug_fn(
                        fp=Path(unique_sigs[0]["file"]),
                        line_start=unique_sigs[0]["line"],
                        line_end=unique_sigs[0]["line"],
                        title=f"函数 '{func_name}' 参数名在不同文件中不一致",
                        description=(
                            f"'{func_name}' 参数数量相同但参数名不同: {files_info}。"
                            f"不同命名可能反映 AI 在不同轮次对接口的理解不一致。"
                        ),
                        code_snippet="",
                        fix_suggestion=f"统一 '{func_name}' 的参数命名",
                        confidence=0.70,
                        extra_id=f"{func_name}_name_drift",
                        root_cause=RootCause.AGENT_ISOLATION,
                    ))

        # 清理缓存，准备下次扫描
        cls._clear_cache()
        return bugs

    @classmethod
    def _clear_cache(cls):
        cls._signatures.clear()
        cls._calls.clear()

    def _extract_params(self, node) -> list[dict]:
        """提取函数参数信息"""
        params = []
        # 跳过 self/cls
        args = node.args.args
        if args and args[0].arg in ("self", "cls"):
            args = args[1:]

        defaults_start = len(args) - len(node.args.defaults) if node.args.defaults else len(args)

        for i, arg in enumerate(args):
            params.append({
                "name": arg.arg,
                "has_default": i >= defaults_start,
                "annotation": ast.unparse(arg.annotation) if arg.annotation and hasattr(ast, "unparse") else None,
            })
        return params
