"""Promise not returned/awaited"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class FloatingPromiseRule(BaseRule):
    rule_id = "JS_FLOATING_PROMISE_001"
    name = "floating_promise"
    description = "Promise not returned/awaited"
    severity = Severity.SEVERE
    layer = RuleLayer.HEURISTIC
    languages = ['javascript', 'typescript']
    base_confidence = 0.78
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            s = line.strip()
            if 'new Promise(' in s and 'return' not in s and 'const' not in s and 'let' not in s and 'var' not in s:
                if 'await' not in s:
                    bugs.append(self._create_bug(file_path, i, i, 'Floating Promise',
                        'Promise created but not stored or awaited', code_snippet=s[:80],
                        confidence=self.base_confidence))
        return bugs

def register():
    return FloatingPromiseRule()
