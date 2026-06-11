"""
Detect loose equality and parseInt radix — Layer 2 (PATTERN, 80%)
"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class JSTypeCoercionRule(BaseRule):
    rule_id = "JS_TYPE_COERCION_001"
    name = "JavaScript Implicit Type Coercion"
    description = "Detect loose equality and parseInt radix"
    severity = Severity.MODERATE
    category = BugCategory.STYLE
    languages = ['javascript', 'typescript']
    layer = RuleLayer.PATTERN
    base_confidence = 0.80

    def analyze(self, file_path, source, ast_tree=None):
        bugs = []
        for ln, line in enumerate(source.split("\n"), 1):
            s = line.strip()
            if s.startswith("//"):
                continue
            if re.search(r'[^=!><]==(?!=)', s) and not re.search(r'\w+\s*==\s*null|null\s*==\s*\w+', s):
                bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                    title="Using == instead of ===",
                    description="Loose equality triggers type coercion",
                    code_snippet=s[:200], fix_suggestion="Use ===",
                    confidence=0.80, extra_id=f"eq_{ln}"))
            if "parseInt(" in s and not re.search(r'parseInt\([^,]+,\s*\d+', s):
                bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                    title="parseInt() missing radix",
                    description="parseInt without radix may misinterpret",
                    code_snippet=s[:200], fix_suggestion="Use parseInt(x, 10)",
                    confidence=0.85, extra_id=f"radix_{ln}"))
        return bugs

