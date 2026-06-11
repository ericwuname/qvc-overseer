"""Promise without .catch() or await"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

class UnhandledPromiseRule(BaseRule):
    rule_id = "JS_UNHANDLED_PROMISE_001"
    name = "unhandled_promise"
    description = "Promise without .catch() or await"
    severity = Severity.SEVERE
    layer = RuleLayer.HEURISTIC
    languages = ['javascript', 'typescript']
    base_confidence = 0.8
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(chr(10)), 1):
            if re.search(r'\basync\s+function', line):
                pass  # async function definition is fine
            elif re.search(r'\bfetch\s*\(', line) and '.catch' not in line and 'await' not in line:
                bugs.append(self._create_bug(file_path, i, i, 'Unhandled Promise',
                    'fetch() without await or .catch()', code_snippet=line.strip()[:80],
                    confidence=self.base_confidence))

        return bugs

def register():
    return UnhandledPromiseRule()
