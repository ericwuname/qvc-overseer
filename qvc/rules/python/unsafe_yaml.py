"""yaml.load() instead of safe_load()"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class UnsafeYAMLRule(BaseRule):
    rule_id = "PY_UNSAFE_YAML_001"
    name = "unsafe_yaml"
    description = "yaml.load() instead of safe_load()"
    severity = Severity.FATAL
    layer = RuleLayer.CERTIFICATE
    languages = ['python']
    base_confidence = 0.92
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            if 'yaml.load(' in line and 'safe_load' not in line:
                bugs.append(self._create_bug(file_path, i, i, 'Unsafe YAML load',
                    'Use yaml.safe_load()', code_snippet=line.strip()[:80],
                    confidence=self.base_confidence))
        return bugs

def register():
    return UnsafeYAMLRule()
