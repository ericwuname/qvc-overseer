"""useState setter never called"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class UnusedStateRule(BaseRule):
    rule_id = "REACT_UNUSED_STATE_001"
    name = "unused_state_setter"
    description = "useState setter never called"
    severity = Severity.MODERATE
    layer = RuleLayer.HEURISTIC
    languages = ['javascript', 'typescript']
    base_confidence = 0.7
    blindspot_type = "context_lost"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            import re
            m = re.search(r'const\s*\[\s*(\w+)\s*,\s*set(\w+)\s*\]\s*=\s*useState', line)
            if m:
                setter_name = 'set' + m.group(2)
                if setter_name + '(' not in source:
                    bugs.append(self._create_bug(file_path, i, i, 'Unused state setter',
                        setter_name + ' never called', code_snippet=line.strip()[:80],
                        confidence=self.base_confidence))
        return bugs

def register():
    return UnusedStateRule()
