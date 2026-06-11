"""Prototype pollution"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class PrototypePollutionRule(BaseRule):
    rule_id = "JS_PROTOTYPE_POLLUTION_001"
    name = "prototype_pollution"
    description = "Prototype pollution"
    severity = Severity.SEVERE
    layer = RuleLayer.PATTERN
    languages = ['javascript', 'typescript']
    base_confidence = 0.88
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            s = line.strip()
            if '__proto__' in s and '=' in s:
                if 'Object.create' not in s and 'Object.defineProperty' not in s:
                    bugs.append(self._create_bug(file_path, i, i, 'Prototype pollution',
                        'Modifying __proto__', code_snippet=s[:80],
                        confidence=self.base_confidence))
        return bugs

def register():
    return PrototypePollutionRule()
