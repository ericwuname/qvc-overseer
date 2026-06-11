"""Missing key prop in list render"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

class MissingKeyRule(BaseRule):
    rule_id = "REACT_MISSING_KEY_001"
    name = "missing_list_key"
    description = "Missing key prop in list render"
    severity = Severity.SEVERE
    layer = RuleLayer.CERTIFICATE
    languages = ['javascript', 'typescript']
    base_confidence = 0.9
    blindspot_type = "memory_trap"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(chr(10)), 1):
            if '.map(' in line and '((' in line or '=>' in line:
                if 'key=' not in line:
                    bugs.append(self._create_bug(file_path, i, i, 'Missing key prop',
                        '.map() callback missing key=', code_snippet=line.strip()[:80],
                        confidence=self.base_confidence))

        return bugs

def register():
    return MissingKeyRule()
