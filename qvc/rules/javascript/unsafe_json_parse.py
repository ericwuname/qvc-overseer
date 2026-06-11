"""JSON.parse() without try-catch"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

class UnsafeJSONParseRule(BaseRule):
    rule_id = "JS_UNSAFE_JSON_PARSE_001"
    name = "unsafe_json_parse"
    description = "JSON.parse() without try-catch"
    severity = Severity.MODERATE
    layer = RuleLayer.PATTERN
    languages = ['javascript', 'typescript']
    base_confidence = 0.78
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        lines = source.split(chr(10))
        for i, line in enumerate(lines, 1):
            if 'JSON.parse(' in line:
                ctx_start = max(0, i - 5)
                ctx_end = min(len(lines), i + 1)
                nearby = chr(10).join(lines[ctx_start:ctx_end])
                if 'try' not in nearby or 'catch' not in nearby:
                    bugs.append(self._create_bug(file_path, i, i, 'JSON.parse no try-catch',
                        'May throw on malformed input', code_snippet=line.strip()[:80],
                        confidence=self.base_confidence))

        return bugs

def register():
    return UnsafeJSONParseRule()
