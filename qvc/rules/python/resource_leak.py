"""Python???????? ?? ??open()???with??????.close()"""
import ast
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class ResourceLeakRule(BaseRule):
    rule_id = "PY_RESOURCE_LEAK_001"
    name = "resource_leak"
    description = "??open()?????with??????????????.close()"
    severity = Severity.SEVERE
    category = BugCategory.RESOURCE_LEAK
    languages = ["python"]
    layer = RuleLayer.PATTERN

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs
        source_lines = source.split("\n")

        safe_lines = set()
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.With):
                for child in ast.walk(node):
                    if hasattr(child, "lineno"):
                        safe_lines.add(child.lineno)

        open_assignments = {}
        for node in ast.walk(ast_tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = getattr(node, "targets", [])
                if isinstance(node, ast.AnnAssign) and node.target:
                    targets = [node.target]
                value = node.value
                is_open = False
                if isinstance(value, ast.Call):
                    if isinstance(value.func, ast.Name) and value.func.id == "open":
                        is_open = True
                if is_open:
                    for t in targets:
                        if isinstance(t, ast.Name):
                            open_assignments[t.id] = node.lineno
                        elif isinstance(t, (ast.Tuple, ast.List)):
                            for elt in t.elts:
                                if isinstance(elt, ast.Name):
                                    open_assignments[elt.id] = node.lineno

        close_calls = set()
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "close":
                        if isinstance(node.func.value, ast.Name):
                            close_calls.add(node.func.value.id)

        for node in ast.walk(ast_tree):
            if not isinstance(node, ast.Call):
                continue
            if not (isinstance(node.func, ast.Name) and node.func.id == "open"):
                continue
            if node.lineno in safe_lines:
                continue

            line_text = (
                source_lines[node.lineno - 1].strip()
                if node.lineno <= len(source_lines)
                else ""
            )

            assigned_name = None
            for p in ast.walk(ast_tree):
                if isinstance(p, (ast.Assign, ast.AnnAssign)):
                    val = p.value
                    if val is node:
                        targets = getattr(p, "targets", [])
                        if isinstance(p, ast.AnnAssign) and p.target:
                            targets = [p.target]
                        for t in targets:
                            if isinstance(t, ast.Name):
                                assigned_name = t.id
                        break

            if assigned_name and assigned_name in close_calls:
                continue

            if assigned_name:
                title = "?????open()?????%s????with?.close()" % assigned_name
                fix = "????%s.close()???with open(...) as %s:" % (assigned_name, assigned_name)
            else:
                title = "?????open()???with????"
                fix = "??with open(...) as f: ??????????"

            bug = self._create_bug(
                file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                title=title,
                description="open()?????with??????????????????",
                code_snippet=line_text[:200],
                fix_suggestion=fix,
                confidence=0.85, extra_id="L%d" % node.lineno,
                root_cause=RootCause.NO_DEFENSE,
            )
            bug.blindspot_type = "context_lost"
            bugs.append(bug)
        return bugs
