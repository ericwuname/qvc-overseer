"""
Detect direct state mutation — Layer 2 (PATTERN, 75%)
"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class ReactStateImmutableRule(BaseRule):
    rule_id = "REACT_STATE_IMMUTABLE_001"
    name = "React State Immutability"
    description = "Detect direct state mutation"
    severity = Severity.SEVERE
    category = BugCategory.EVENT_INTEGRITY
    languages = ['javascript', 'typescript']
    layer = RuleLayer.PATTERN
    base_confidence = 0.75

    def analyze(self, file_path, source, ast_tree=None):
        bugs = []
        sv = {"state","data","items","list","users","tasks","records","results"}
        for ln, line in enumerate(source.split("\n"), 1):
            s = line.strip()
            if s.startswith("//"):
                continue
            sa = re.search(r'this\.state\.(\w+)\s*=', s)
            if sa:
                bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                    title="Direct mutation of this.state",
                    description="Does not trigger React re-render",
                    code_snippet=s[:200], fix_suggestion="Use this.setState()",
                    confidence=0.90, extra_id=f"sm_{ln}",
                    root_cause=RootCause.STALE_STATE))
            for vn in sv:
                for mt in ["push","pop","splice","sort","reverse","shift","unshift"]:
                    if re.search(rf"{vn}\.{mt}\(", s):
                        bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                            title="Mutable array operation",
                            description="Mutates original array",
                            code_snippet=s[:200], fix_suggestion="Use immutable update",
                            confidence=0.70, extra_id=f"am_{ln}",
                            root_cause=RootCause.STALE_STATE))
                        break
        return bugs

