"""
Detect missing null safety — Layer 2 (PATTERN, 70%)
"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class JSNullSafetyRule(BaseRule):
    rule_id = "JS_NULL_SAFETY_001"
    name = "JavaScript Null Safety"
    description = "Detect missing null safety"
    severity = Severity.SEVERE
    category = BugCategory.NULL_SAFETY
    languages = ['javascript', 'typescript']
    layer = RuleLayer.PATTERN
    base_confidence = 0.70

    def analyze(self, file_path, source, ast_tree=None):
        bugs = []
        for ln, line in enumerate(source.split("\n"), 1):
            s = line.strip()
            if s.startswith("//"):
                continue
            m = re.search(r"(\w+)\.(\w+)\.(\w+)", s)
            if m and "?." not in s:
                if not re.search(rf"if\s*\(\s*{re.escape(m.group(1))}", s):
                    bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                        title="Deep property access missing null guard",
                        description="Chained access may crash if null",
                        code_snippet=s[:200], fix_suggestion="Use optional chaining (?.)",
                        confidence=0.70, extra_id=f"null_{ln}",
                        root_cause=RootCause.MISSING_NULL_CHECK))
            m2 = re.search(r"(\w+)\.(getElementById|querySelector)\([^)]+\)\.", s)
            if m2 and "?." not in s:
                bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                    title="DOM query missing null check",
                    description="DOM query may return null",
                    code_snippet=s[:200], fix_suggestion="Use optional chaining",
                    confidence=0.80, extra_id=f"dom_{ln}",
                    root_cause=RootCause.MISSING_NULL_CHECK))
        return bugs

