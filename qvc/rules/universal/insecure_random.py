"""Insecure random for security context"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

class InsecureRandomRule(BaseRule):
    rule_id = "UNI_INSECURE_RANDOM_001"
    name = "insecure_random"
    description = "Insecure random for security context"
    severity = Severity.SEVERE
    layer = RuleLayer.PATTERN
    languages = ['*']
    base_confidence = 0.82
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(chr(10)), 1):
            s = line.strip()
            if re.search(r'Math\.random\s*\(', s):
                ctx = source.lower()
                if any(kw in ctx for kw in ['token', 'password', 'secret', 'crypto', 'auth']):
                    bugs.append(self._create_bug(file_path, i, i, 'Insecure Math.random()',
                        'Use crypto.randomUUID() for security', code_snippet=s[:80],
                        confidence=self.base_confidence))

        return bugs

def register():
    return InsecureRandomRule()
