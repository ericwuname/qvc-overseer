"""
Detect missing await and unhandled Promise — Layer 2 (PATTERN, 75%)
"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class JSAsyncAwaitRule(BaseRule):
    rule_id = "JS_ASYNC_AWAIT_001"
    name = "JavaScript Async/Await Check"
    description = "Detect missing await and unhandled Promise"
    severity = Severity.SEVERE
    category = BugCategory.EVENT_INTEGRITY
    languages = ['javascript', 'typescript']
    layer = RuleLayer.PATTERN
    base_confidence = 0.75

    def analyze(self, file_path, source, ast_tree=None):
        bugs = []
        side = {"addEventListener","removeEventListener","setTimeout","setInterval",
                "clearTimeout","clearInterval","console.log","console.error",
                "console.warn","console.info","console.debug"}
        for ln, line in enumerate(source.split("\n"), 1):
            s = line.strip()
            if s.startswith("//"):
                continue
            m = re.search(r"(?<!await\s)(?<!\.)(fetch|axios|\w+Async|\w+Request|\w+Query)\s*\(", s)
            if m and not s.startswith(("return ","const ")):
                fn = m.group(1)
                if fn not in side:
                    bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                        title="Async call may be missing await",
                        description="Async function may return Promise",
                        code_snippet=s[:200], fix_suggestion="Add await",
                        confidence=0.65, extra_id=f"await_{ln}"))
            if ".then(" in s and ".catch(" not in s:
                bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                    title="Promise chain missing .catch()",
                    description=".then() without .catch()",
                    code_snippet=s[:200], fix_suggestion="Add .catch()",
                    confidence=0.70, extra_id=f"catch_{ln}"))
        return bugs

