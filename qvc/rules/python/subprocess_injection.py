"""subprocess with shell=True"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class SubprocessInjectionRule(BaseRule):
    rule_id = "PY_SUBPROCESS_INJECTION_001"
    name = "subprocess_injection"
    description = "subprocess with shell=True"
    severity = Severity.FATAL
    layer = RuleLayer.PATTERN
    languages = ['python']
    base_confidence = 0.88
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            s = line.strip()
            if 'shell=True' in s:
                if any(kw in s.lower() for kw in ['request', 'params', 'args', 'form', 'input', 'user', 'cmd', 'argv']):
                    bugs.append(self._create_bug(file_path, i, i, 'Subprocess injection',
                        'shell=True with user input', code_snippet=s[:80],
                        confidence=self.base_confidence))
        return bugs

def register():
    return SubprocessInjectionRule()
