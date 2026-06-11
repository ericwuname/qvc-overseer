"""eval() / new Function() code injection"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

class EvalUsageRule(BaseRule):
    rule_id = "JS_EVAL_USAGE_001"
    name = "eval_usage"
    description = "eval() / new Function() code injection"
    severity = Severity.FATAL
    layer = RuleLayer.CERTIFICATE
    languages = ['javascript', 'typescript']
    base_confidence = 0.95
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(chr(10)), 1):
            if re.search(r'(?:eval|new\s+Function)\s*\(', line):
                bugs.append(self._create_bug(file_path, i, i, 'Dangerous eval',
                    'eval()/new Function() allows code injection', code_snippet=line.strip()[:80],
                    confidence=self.base_confidence))

        return bugs

def register():
    return EvalUsageRule()
