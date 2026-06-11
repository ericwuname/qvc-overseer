"""Socket without timeout"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

NL = chr(10)

class SocketNoTimeoutRule(BaseRule):
    rule_id = "PY_SOCKET_NO_TIMEOUT_001"
    name = "socket_no_timeout"
    description = "Socket without timeout"
    severity = Severity.SEVERE
    layer = RuleLayer.PATTERN
    languages = ['python']
    base_confidence = 0.85
    blindspot_type = "boundary_condition"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        has_socket = False
        has_timeout = False
        for i, line in enumerate(source.split(NL), 1):
            if 'socket.socket(' in line or 'socket.create_connection(' in line:
                has_socket = True
            if 'settimeout' in line or 'timeout=' in line:
                has_timeout = True
        if has_socket and not has_timeout:
            bugs.append(self._create_bug(file_path, 1, len(source.split(NL)),
                'Socket without timeout',
                'Socket may block forever',
                confidence=self.base_confidence))
        return bugs

def register():
    return SocketNoTimeoutRule()
