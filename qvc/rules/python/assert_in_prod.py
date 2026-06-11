"""Python assert?????? ?? ??assert????????"""
import ast
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class AssertForLogicRule(BaseRule):
    rule_id = "PY_ASSERT_IN_PROD_001"
    name = "assert_for_logic"
    description = "??assert????????/?????????(-O)?????"
    severity = Severity.MODERATE
    category = BugCategory.ERR_HANDLING
    languages = ["python"]
    layer = RuleLayer.HEURISTIC

    _VALIDATION_OPS = {
        "isinstance", "hasattr", "callable", "len",
        "all", "any", "issubclass",
    }

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs
        source_lines = source.split("\n")

        for node in ast.walk(ast_tree):
            if not isinstance(node, ast.Assert):
                continue
            if isinstance(node.test, ast.Constant):
                continue
            if isinstance(node.test, getattr(ast, "NameConstant", ())):
                continue
            if isinstance(node.test, ast.Name):
                continue

            line_text = (
                source_lines[node.lineno - 1].strip()
                if node.lineno <= len(source_lines)
                else ""
            )

            is_validation = False
            evidence = ""

            if isinstance(node.test, ast.Call):
                if isinstance(node.test.func, ast.Name):
                    if node.test.func.id in self._VALIDATION_OPS:
                        is_validation = True
                        evidence = "??%s()????/????" % node.test.func.id

            if isinstance(node.test, ast.Compare):
                has_call = any(
                    isinstance(op, ast.Call)
                    for op in ast.walk(node.test)
                    if op is not node.test
                )
                if has_call or len(node.test.ops) > 1:
                    is_validation = True
                    evidence = "????????????"
                elif not (
                    len(node.test.comparators) == 1
                    and isinstance(node.test.comparators[0], ast.Constant)
                ):
                    is_validation = True
                    evidence = "??????"

            if isinstance(node.test, ast.BoolOp):
                is_validation = True
                evidence = "????????"

            if isinstance(node.test, (ast.Subscript, ast.Attribute)):
                has_call = any(
                    isinstance(child, ast.Call)
                    for child in ast.walk(node.test)
                    if child is not node.test
                )
                if has_call:
                    is_validation = True
                    evidence = "?????????????"

            if not is_validation:
                continue

            bug = self._create_bug(
                file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                title="assert????????",
                description="assert?????%s??Python -O?????assert????" % (evidence or "????"),
                code_snippet=line_text[:200],
                fix_suggestion="?assert??????if-raise: if not condition: raise ValueError()",
                confidence=0.75, extra_id="L%d" % node.lineno,
                root_cause=RootCause.NO_DEFENSE,
            )
            bug.blindspot_type = "boundary_condition"
            bugs.append(bug)
        return bugs
