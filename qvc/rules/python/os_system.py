"""os.system() / os.popen()"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class OSSystemRule(BaseRule):
    rule_id = "PY_OS_SYSTEM_001"
    name = "os_system"
    description = "os.system() / os.popen()"
    severity = Severity.FATAL
    layer = RuleLayer.CERTIFICATE
    languages = ['python']
    base_confidence = 0.9
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            if 'os.system(' in line or 'os.popen(' in line:
                bugs.append(self._create_bug(file_path, i, i, 'Dangerous os.system/popen',
                    'Prefer subprocess.run() with list args', code_snippet=line.strip()[:80],
                    confidence=self.base_confidence))
        return bugs

def register():
    return OSSystemRule()
