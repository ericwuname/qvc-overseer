"""Explicit any type annotation"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class TSAnyTypeRule(BaseRule):
    rule_id = "TS_ANY_TYPE_001"
    name = "ts_any_type"
    description = "Explicit any type annotation"
    severity = Severity.MODERATE
    layer = RuleLayer.HEURISTIC
    languages = ['typescript']
    base_confidence = 0.72
    blindspot_type = "memory_trap"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            s = line.strip()
            if ': any' in s and not s.startswith('//') and not s.startswith('*'):
                if 'eslint-disable' not in s:
                    bugs.append(self._create_bug(file_path, i, i, 'TypeScript any type',
                        'Explicit any defeats type checking', code_snippet=s[:80],
                        confidence=self.base_confidence))
        return bugs

def register():
    return TSAnyTypeRule()
