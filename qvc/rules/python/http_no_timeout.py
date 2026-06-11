"""Python HTTP??????? ?? ??HTTP?????timeout??"""
import ast
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class HTTPNoTimeoutRule(BaseRule):
    rule_id = "PY_HTTP_NO_TIMEOUT_001"
    name = "http_no_timeout"
    description = "??requests/httpx/urllib?HTTP???????timeout??"
    severity = Severity.SEVERE
    category = BugCategory.SECURITY
    languages = ["python"]
    layer = RuleLayer.PATTERN

    _REQUESTS_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "request"}
    _HTTPX_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "request", "stream"}
    _URLLIB_METHODS = {"urlopen", "Request"}

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            if ast_tree is None:
                ast_tree = ast.parse(source)
        except SyntaxError:
            return bugs
        source_lines = source.split("\n")

        requests_aliases = set()
        httpx_aliases = set()
        urllib_aliases = set()

        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    if name == "requests":
                        requests_aliases.add(asname)
                    elif name == "httpx":
                        httpx_aliases.add(asname)
                    elif name in ("urllib", "urllib.request", "urllib2"):
                        urllib_aliases.add(asname)
            elif isinstance(node, ast.ImportFrom):
                if node.module == "urllib":
                    for alias in node.names:
                        urllib_aliases.add(alias.asname or alias.name)

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
            if method_name is None:
                continue

            library = None
            label = ""
            if module_name and module_name in requests_aliases and method_name in self._REQUESTS_METHODS:
                library = "requests"
                label = "%s.%s()" % (module_name, method_name)
            elif module_name and module_name in httpx_aliases and method_name in self._HTTPX_METHODS:
                library = "httpx"
                label = "%s.%s()" % (module_name, method_name)
            elif module_name and module_name in urllib_aliases and method_name in self._URLLIB_METHODS:
                library = "urllib"
                label = "%s.%s()" % (module_name, method_name)
            elif isinstance(node.func, ast.Name) and method_name in self._REQUESTS_METHODS:
                library = "requests"
                label = "%s()" % method_name
            elif isinstance(node.func, ast.Name) and method_name in self._HTTPX_METHODS:
                library = "httpx"
                label = "%s()" % method_name
            else:
                continue

            has_timeout = False
            for kw in node.keywords:
                if kw.arg == "timeout":
                    has_timeout = True
                    break
            if has_timeout:
                continue

            line_text = (
                source_lines[node.lineno - 1].strip()
                if node.lineno <= len(source_lines)
                else ""
            )

            bug = self._create_bug(
                file_path=file_path, line_start=node.lineno, line_end=node.lineno,
                title="HTTP???????%s" % label,
                description="%s??%s?????timeout???????????" % (library, label),
                code_snippet=line_text[:200],
                fix_suggestion="??timeout???%s(timeout=30)" % label.rstrip("()"),
                confidence=0.85, extra_id="L%d" % node.lineno,
                root_cause=RootCause.NO_DEFENSE,
            )
            bug.blindspot_type = "boundary_condition"
            bugs.append(bug)
        return bugs
