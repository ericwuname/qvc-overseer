"""Path construction from user input"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class PathTraversalRule(BaseRule):
    rule_id = "PY_PATH_TRAVERSAL_001"
    name = "path_traversal"
    description = "Path construction from user input"
    severity = Severity.SEVERE
    layer = RuleLayer.HEURISTIC
    languages = ['python']
    base_confidence = 0.78
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            s = line.strip()
            if 'os.path.join' in s and any(kw in s.lower() for kw in ['request', 'params', 'args', 'form', 'input', 'user']):
                bugs.append(self._create_bug(file_path, i, i, 'Path traversal risk',
                    'User input in path without sanitization', code_snippet=s[:80],
                    confidence=self.base_confidence))
        return bugs

def register():
    return PathTraversalRule()
