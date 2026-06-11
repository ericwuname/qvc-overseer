"""Python?????????? ?? ?????????list/dict/set?????"""
import ast
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class MutableDefaultsRule(BaseRule):
    rule_id = "PY_MUTABLE_DEFAULTS_001"
    name = "mutable_default_args"
    description = "?????????????(list/dict/set)???????"
    severity = Severity.SEVERE
    category = BugCategory.STYLE
    languages = ["python"]
    layer = RuleLayer.PATTERN

    _MUTABLE_NODES = (ast.List, ast.Dict, ast.Set)
    _LABEL_MAP = {"List": "[]", "Dict": "{}", "Set": "set()"}

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs
        source_lines = source.split("\n")
        for node in ast.walk(ast_tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for arg in node.args.defaults:
                if isinstance(arg, self._MUTABLE_NODES):
                    type_name = type(arg).__name__.replace("ast.", "")
                    label = self._LABEL_MAP.get(type_name, type_name)
                    line_text = (
                        source_lines[node.lineno - 1].strip()
                        if node.lineno <= len(source_lines)
                        else ""
                    )
                    bug = self._create_bug(
                        file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                        title="???????%s???????%s" % (node.name, label),
                        description="??%s???????????%s????????????" % (node.name, label),
                        code_snippet=line_text[:200],
                        fix_suggestion="??None??????????????",
                        confidence=0.95, extra_id="L%d" % node.lineno,
                        root_cause=RootCause.NO_DEFENSE,
                    )
                    bug.blindspot_type = "memory_trap"
                    bugs.append(bug)
            for kw_default in node.args.kw_defaults:
                if isinstance(kw_default, self._MUTABLE_NODES):
                    type_name = type(kw_default).__name__.replace("ast.", "")
                    label = self._LABEL_MAP.get(type_name, type_name)
                    line_text = (
                        source_lines[node.lineno - 1].strip()
                        if node.lineno <= len(source_lines)
                        else ""
                    )
                    bug = self._create_bug(
                        file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                        title="???????%s??????????%s" % (node.name, label),
                        description="??%s??????????????%s" % (node.name, label),
                        code_snippet=line_text[:200],
                        fix_suggestion="??None??????????????",
                        confidence=0.95, extra_id="L%d-kw" % node.lineno,
                        root_cause=RootCause.NO_DEFENSE,
                    )
                    bug.blindspot_type = "memory_trap"
                    bugs.append(bug)
        return bugs
