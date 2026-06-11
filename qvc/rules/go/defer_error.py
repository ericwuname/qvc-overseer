"""Deferred call error not checked"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class DeferErrorRule(BaseRule):
    rule_id = "GO_DEFER_ERROR_001"
    name = "defer_error_ignored"
    description = "Deferred call error not checked"
    severity = Severity.MODERATE
    layer = RuleLayer.HEURISTIC
    languages = ['go']
    base_confidence = 0.75
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            s = line.strip()
            if s.startswith('defer ') and 'err' in s.lower():
                if 'if err' not in source:
                    bugs.append(self._create_bug(file_path, i, i, 'Defer error ignored',
                        'Deferred call returns error but not checked', code_snippet=s[:80],
                        confidence=self.base_confidence))
                    break
        return bugs

def register():
    return DeferErrorRule()
