"""Hardcoded API keys / passwords"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

class HardcodedCredentialsRule(BaseRule):
    rule_id = "UNI_HARDCODED_CRED_001"
    name = "hardcoded_credentials"
    description = "Hardcoded API keys / passwords"
    severity = Severity.FATAL
    layer = RuleLayer.PATTERN
    languages = ['*']
    base_confidence = 0.88
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        secrets = [
            (r'sk-[A-Za-z0-9]{20,}', 'OpenAI Key'),
            (r'AKIA[0-9A-Z]{16}', 'AWS Key'),
            (r'ghp_[A-Za-z0-9]{36}', 'GitHub Token'),
            (r'glpat-[A-Za-z0-9\-_]{20,}', 'GitLab Token'),
            (r'(?:api_key|apikey|secret_key|private_key)\s*[=:]\s*["\'][A-Za-z0-9\-_]{16,}["\']', 'Generic Key'),
        ]
        for i, line in enumerate(source.split(chr(10)), 1):
            s = line.strip()
            if s.startswith('#') or s.startswith('//'):
                continue
            for pat, label in secrets:
                if re.search(pat, s, re.IGNORECASE):
                    bugs.append(self._create_bug(file_path, i, i, f'Hardcoded: {label}',
                        'Never commit secrets to source', code_snippet=s[:80],
                        confidence=self.base_confidence))
                    break

        return bugs

def register():
    return HardcodedCredentialsRule()
