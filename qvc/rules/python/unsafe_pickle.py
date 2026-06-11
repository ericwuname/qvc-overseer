"""Python???pickle???? ?? ??pickle.load()/pickle.loads()??"""
import ast
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class UnsafePickleRule(BaseRule):
    rule_id = "PY_UNSAFE_PICKLE_001"
    name = "unsafe_pickle"
    description = "??pickle.load()/pickle.loads()/cPickle????????????????RCE"
    severity = Severity.FATAL
    category = BugCategory.SECURITY
    languages = ["python"]
    layer = RuleLayer.PATTERN

    _DANGEROUS_METHODS = {"load", "loads", "Unpickler"}

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs
        source_lines = source.split("\n")

        pickle_aliases = set()
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("pickle", "cPickle", "_pickle"):
                        pickle_aliases.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module in ("pickle", "cPickle", "_pickle"):
                    for alias in node.names:
                        pickle_aliases.add(alias.asname or alias.name)

        for node in ast.walk(ast_tree):
            if not isinstance(node, ast.Call):
                continue
            method_name = None
            module_name = None
            if isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                if isinstance(node.func.value, ast.Name):
                    module_name = node.func.value.id
            elif isinstance(node.func, ast.Name):
                method_name = node.func.id
            if method_name not in self._DANGEROUS_METHODS:
                continue

            line_text = (
                source_lines[node.lineno - 1].strip()
                if node.lineno <= len(source_lines)
                else ""
            )

            if module_name and module_name in pickle_aliases:
                bug = self._create_bug(
                    file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                    title="????????%s.%s()" % (module_name, method_name),
                    description="??%s.%s()???????????????????(RCE)" % (module_name, method_name),
                    code_snippet=line_text[:200],
                    fix_suggestion="?????????????????json.loads()?????",
                    confidence=0.90, extra_id="L%d" % node.lineno,
                    root_cause=RootCause.NO_DEFENSE,
                )
                bug.blindspot_type = "boundary_condition"
                bugs.append(bug)
            elif isinstance(node.func, ast.Name):
                bug = self._create_bug(
                    file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                    title="????????%s()" % method_name,
                    description="????%s()???????????????????(RCE)" % method_name,
                    code_snippet=line_text[:200],
                    fix_suggestion="?????????????????json.loads()?????",
                    confidence=0.88, extra_id="L%d-direct" % node.lineno,
                    root_cause=RootCause.NO_DEFENSE,
                )
                bug.blindspot_type = "boundary_condition"
                bugs.append(bug)
        return bugs
