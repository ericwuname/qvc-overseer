"""Python 异常处理检测规则 —— 检测静默吞没异常、裸 except"""

import ast
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class PythonExceptionHandlingRule(BaseRule):
    """检测不恰当的异常处理"""
    rule_id = "PY_EXCEPTION_001"
    name = "Python 异常处理检测"
    description = "检测裸 except、静默吞没异常、异常捕获过宽"
    severity = Severity.SEVERE
    category = BugCategory.ERR_HANDLING
    languages = ["python"]
    layer = RuleLayer.PATTERN  # base_confidence = 0.65
    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs

        lines = source.split("\n")

        for node in ast.walk(ast_tree):
            # 检测裸 except（没有指定异常类型）
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    bugs.append(self._create_bug(
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        title="裸 except 语句",
                        description="except 未指定异常类型，会捕获所有异常（包括 SystemExit/KeyboardInterrupt），可能掩盖严重问题",
                        code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                        fix_suggestion="指定具体的异常类型，如 except ValueError: 或 except Exception:",
                        root_cause=RootCause.NO_DEFENSE,
                        confidence=0.9,
                        extra_id=f"bare_except_L{node.lineno}",
                    ))

                # 检测静默吞没异常（except SyntaxError/ImportError 等正常解析异常除外）
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    # 跳过已知的合法静默模式
                    if node.type and isinstance(node.type, ast.Name):
                        benign = {"SyntaxError", "ImportError", "ModuleNotFoundError", "IndentationError", "TabError"}
                        if node.type.id in benign:
                            continue  # 这些异常的 pass 是正常模式'
                    bugs.append(self._create_bug(
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        title="异常被静默吞没",
                        description="except 块中只有 pass，异常被完全忽略，调用方无法感知错误",
                        code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                        fix_suggestion="至少应记录日志：logger.exception(...) 或重新抛出",
                        root_cause=RootCause.NO_DEFENSE,
                        confidence=0.85,
                        extra_id=f"silent_except_L{node.lineno}",
                    ))

                # 检测 except 块只有 return None 或 return []
                if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                    return_val = node.body[0].value
                    is_empty_return = (
                        return_val is None
                        or (isinstance(return_val, ast.Constant) and return_val.value in (None, [], {}, ""))
                    )
                    if is_empty_return:
                        bugs.append(self._create_bug(
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.lineno,
                            title="异常被转换为空返回值",
                            description="except 块中返回空值（None/[]/{}），调用方无法区分'正常空结果'和'发生了异常'",
                            code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                            fix_suggestion="记录异常日志，考虑是否应重新抛出或返回错误信息",
                            root_cause=RootCause.NO_DEFENSE,
                            confidence=0.7,
                            extra_id=f"empty_return_L{node.lineno}",
                        ))

        return bugs
