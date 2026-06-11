"""TODO/FIXME without issue link"""

import re
from pathlib import Path
from qvc.models.bug import Bug, Severity, RootCause
from qvc.models.severity import RuleLayer
from qvc.rules.base import BaseRule

class TODOTicketRule(BaseRule):
    rule_id = "UNI_TODO_TICKET_001"
    name = "todo_no_ticket"
    description = "TODO/FIXME without issue link"
    severity = Severity.MINOR
    layer = RuleLayer.HEURISTIC
    languages = ['*']
    base_confidence = 0.6
    blindspot_type = "context_lost"

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        bugs = []
        for i, line in enumerate(source.split(chr(10)), 1):
            s = line.strip()
            if re.search(r'(?:TODO|FIXME|HACK)\b', s, re.IGNORECASE):
                if not re.search(r'(?:#\d+|issue|jira|ticket|http)', s, re.IGNORECASE):
                    bugs.append(self._create_bug(file_path, i, i, 'TODO without ticket',
                        'Link to issue tracker', code_snippet=s[:80],
                        confidence=self.base_confidence))

        return bugs

def register():
    return TODOTicketRule()
