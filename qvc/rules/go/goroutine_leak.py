"""Goroutine without context"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class GoroutineLeakRule(BaseRule):
    rule_id = "GO_GOROUTINE_LEAK_001"
    name = "goroutine_leak"
    description = "Goroutine without context"
    severity = Severity.SEVERE
    layer = RuleLayer.HEURISTIC
    languages = ['go']
    base_confidence = 0.8
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            if line.strip().startswith('go ') and 'func(' in line:
                if 'context.Context' not in source and 'cancel' not in source:
                    bugs.append(self._create_bug(file_path, i, i, 'Goroutine leak risk',
                        'Goroutine without context or cancel', code_snippet=line.strip()[:80],
                        confidence=self.base_confidence))
                    break
        return bugs

def register():
    return GoroutineLeakRule()
