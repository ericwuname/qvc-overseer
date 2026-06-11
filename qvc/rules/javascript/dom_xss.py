"""DOM XSS via innerHTML/document.write"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

class DOMXSSRule(BaseRule):
    rule_id = "JS_DOM_XSS_001"
    name = "dom_xss"
    description = "DOM XSS via innerHTML/document.write"
    severity = Severity.SEVERE
    layer = RuleLayer.PATTERN
    languages = ['javascript', 'typescript']
    base_confidence = 0.85
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(chr(10)), 1):
            if re.search(r'\binnerHTML\s*=|\bouterHTML\s*=|insertAdjacentHTML|document\.write\s*\(', line):
                bugs.append(self._create_bug(file_path, i, i, 'DOM XSS risk',
                    'innerHTML/outerHTML/document.write', code_snippet=line.strip()[:80],
                    confidence=self.base_confidence))

        return bugs

def register():
    return DOMXSSRule()
