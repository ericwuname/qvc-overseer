"""Django SQL injection detection — raw() / extra() / RawSQL with f-string / format / % formatting"""
import ast
import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class DjangoSQLInjectionRule(BaseRule):
    rule_id = "PY_DJANGO_SQLI_001"
    name = "django_sql_injection"
    description = "Django ORM raw()/extra()/RawSQL with f-string/.format()/% formatting — SQL injection risk"
    severity = Severity.FATAL
    category = BugCategory.SECURITY
    languages = ["python"]
    layer = RuleLayer.PATTERN

    _DJANGO_INJECTION_TARGETS = {"raw", "extra", "RawSQL"}
    _PCT_FORMAT_RE = re.compile(r"%\s*(?:\(\s*\w+(?:\s*,\s*\w+)*\s*\)\s*)?[sdrf]")

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

            # Detect: Model.objects.raw(f"..."), Model.objects.extra(where=[...])
            target_name = None
            if isinstance(node.func, ast.Attribute):
                target_name = node.func.attr

            # Also detect: RawSQL(f"...") as a direct call
            is_rawsql = False
            if isinstance(node.func, ast.Name) and node.func.id == "RawSQL":
                target_name = "RawSQL"
                is_rawsql = True

            if target_name not in self._DJANGO_INJECTION_TARGETS:
                continue

            if not node.args:
                continue

            # For extra(), check keyword arg `where`
            if target_name == "extra" and not is_rawsql:
                has_injectable = False
                for kw in node.keywords:
                    if kw.arg == "where" and isinstance(kw.value, ast.List):
                        for elt in kw.value.elts:
                            if self._is_injectable(elt):
                                has_injectable = True
                                break
                if has_injectable:
                    bug = self._make_bug(file_path, node, source_lines, target_name, "extra(where=[...])")
                    bugs.append(bug)
                continue

            # For raw() / RawSQL() / raw(), check first arg
            first_arg = node.args[0]
            if self._is_injectable(first_arg):
                context = "RawSQL(...)" if is_rawsql else f"{target_name}(...)"
                bug = self._make_bug(file_path, node, source_lines, target_name, context)
                bugs.append(bug)

        return bugs

    def _is_injectable(self, arg_node) -> bool:
        """Check if an AST node represents injectable SQL (f-string / .format() / % formatting)"""
        # f-string: JoinedStr
        if isinstance(arg_node, ast.JoinedStr):
            return True
        # .format() call on a string
        if isinstance(arg_node, ast.Call):
            if isinstance(arg_node.func, ast.Attribute) and arg_node.func.attr == "format":
                return True
        # % formatting — check via regex on the source (best effort)
        if isinstance(arg_node, ast.Constant) and isinstance(arg_node.value, str):
            if self._PCT_FORMAT_RE.search(arg_node.value):
                return any(tok in arg_node.value for tok in ("%s", "%d", "%r", "%f", "%("))
        return False

    def _make_bug(self, file_path, node, source_lines, target_name, context):
        line_no = node.lineno
        line_text = source_lines[line_no - 1].strip() if line_no <= len(source_lines) else ""

        return self._create_bug(
            file_path=file_path,
            line_start=line_no,
            line_end=line_no,
            title=f"Django {target_name}() with injectable SQL — {context}",
            description=(
                f"Django {target_name}() called with string interpolation "
                f"(f-string, .format(), or % formatting). "
                f"This bypasses Django's SQL parameterization and enables SQL injection. "
                f"Use parameterized queries: {target_name}('SELECT * FROM t WHERE x = %s', [user_input])"
            ),
            code_snippet=line_text[:200],
            fix_suggestion=(
                f"Replace with: {target_name}('SELECT * FROM t WHERE x = %s', [user_input])\n"
                f"Never concatenate user input into SQL strings in Django ORM."
            ),
            confidence=0.92,
            extra_id=f"L{line_no}",
            root_cause=RootCause.NO_DEFENSE,
        )
