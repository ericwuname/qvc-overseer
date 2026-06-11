"""Python SQL?????? ?? ??cursor.execute()/.raw()????????"""
import ast
import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class SQLInjectionRule(BaseRule):
    rule_id = "PY_SQL_INJECTION_001"
    name = "sql_injection"
    description = "???cursor.execute()/.raw()?????f-string / .format() / %????SQL????"
    severity = Severity.FATAL
    category = BugCategory.SECURITY
    languages = ["python"]
    layer = RuleLayer.PATTERN

    _PCT_FORMAT_RE = re.compile(
        r"%\s*(?:\(\s*\w+(?:\s*,\s*\w+)*\s*\)\s*)?[sdrf]",
    )

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs
        source_lines = source.split("\n")
        for node in ast.walk(ast_tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = None
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name not in ("execute", "raw", "executemany"):
                continue
            if not node.args:
                continue
            first_arg = node.args[0]
            line_text = (
                source_lines[node.lineno - 1].strip()
                if node.lineno <= len(source_lines)
                else ""
            )
            if isinstance(first_arg, ast.JoinedStr):
                bug = self._create_bug(
                    file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                    title="SQL??????%s()???f-string" % func_name,
                    description="?%s()?????f-string????SQL???????????" % func_name,
                    code_snippet=line_text[:200],
                    fix_suggestion="????????cursor.execute(sql, (param1, param2))",
                    confidence=0.92, extra_id="L%d" % node.lineno,
                    root_cause=RootCause.NO_DEFENSE,
                )
                bug.blindspot_type = "boundary_condition"
                bugs.append(bug)
                continue
            if isinstance(first_arg, ast.Call):
                if isinstance(first_arg.func, ast.Attribute) and first_arg.func.attr == "format":
                    bug = self._create_bug(
                        file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                        title="SQL??????%s()???.format()" % func_name,
                        description="?%s()?????.format()????SQL???????????" % func_name,
                        code_snippet=line_text[:200],
                        fix_suggestion="????????cursor.execute(sql, (param1, param2))",
                        confidence=0.92, extra_id="L%d" % node.lineno,
                        root_cause=RootCause.NO_DEFENSE,
                    )
                    bug.blindspot_type = "boundary_condition"
                    bugs.append(bug)
                    continue
            if self._PCT_FORMAT_RE.search(line_text):
                if any(token in line_text for token in ("%s", "%d", "%r", "%f", "%(")):
                    bug = self._create_bug(
                        file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                        title="SQL??????%s()???%%???" % func_name,
                        description="?%s()?????%%??????????SQL???????????" % func_name,
                        code_snippet=line_text[:200],
                        fix_suggestion="????????cursor.execute(sql, (param1, param2))",
                        confidence=0.85, extra_id="L%d" % node.lineno,
                        root_cause=RootCause.NO_DEFENSE,
                    )
                    bug.blindspot_type = "boundary_condition"
                    bugs.append(bug)
        return bugs
