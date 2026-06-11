"""dangerouslySetInnerHTML XSS risk"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

class DangerousHTMLRule(BaseRule):
    rule_id = "REACT_DANGEROUS_HTML_001"
    name = "dangerous_html"
    description = "dangerouslySetInnerHTML XSS risk"
    severity = Severity.FATAL
    layer = RuleLayer.CERTIFICATE
    languages = ['javascript', 'typescript']
    base_confidence = 0.92
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(chr(10)), 1):
            if 'dangerouslySetInnerHTML' in line:
                bugs.append(self._create_bug(file_path, i, i, 'dangerouslySetInnerHTML',
                    'XSS risk via dangerouslySetInnerHTML', code_snippet=line.strip()[:80],
                    confidence=self.base_confidence))

        return bugs

def register():
    return DangerousHTMLRule()
