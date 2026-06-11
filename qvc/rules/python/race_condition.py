"""Threading without lock on shared state"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class RaceConditionRule(BaseRule):
    rule_id = "PY_RACE_CONDITION_001"
    name = "race_condition"
    description = "Threading without lock on shared state"
    severity = Severity.SEVERE
    layer = RuleLayer.HEURISTIC
    languages = ['python']
    base_confidence = 0.8
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        has_thread = False
        has_lock = False
        for i, line in enumerate(source.split(NL), 1):
            if 'Thread(' in line or 'threading.Thread' in line:
                has_thread = True
            if 'Lock()' in line or 'RLock()' in line:
                has_lock = True
        if has_thread and not has_lock:
            bugs.append(self._create_bug(file_path, 1, len(source.split(NL)),
                'Potential race condition',
                'Thread used without Lock/RLock',
                confidence=self.base_confidence))
        return bugs

def register():
    return RaceConditionRule()
