"""MongoDB query injection"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class NoSQLInjectionRule(BaseRule):
    rule_id = "JS_NOSQL_INJECTION_001"
    name = "nosql_injection"
    description = "MongoDB query injection"
    severity = Severity.SEVERE
    layer = RuleLayer.PATTERN
    languages = ['javascript', 'typescript']
    base_confidence = 0.82
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(NL), 1):
            s = line.strip()
            if 'collection.' in source and ('$where' in s or '$gt' in s or '$ne' in s or '$regex' in s):
                if '+' in s or 'concat' in source.lower():
                    bugs.append(self._create_bug(file_path, i, i, 'NoSQL injection risk',
                        'Dynamic MongoDB operator with concatenation', code_snippet=s[:80],
                        confidence=self.base_confidence))
                    break
        return bugs

def register():
    return NoSQLInjectionRule()
