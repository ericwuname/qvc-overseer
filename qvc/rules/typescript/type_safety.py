"""
Detect any abuse, ts-ignore, missing return type — Layer 2 (PATTERN, 80%)
"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class TSTypeSafetyRule(BaseRule):
    rule_id = "TS_TYPE_SAFETY_001"
    name = "TypeScript Type Safety"
    description = "Detect any abuse, ts-ignore, missing return type"
    severity = Severity.MODERATE
    category = BugCategory.STYLE
    languages = ['typescript']
    layer = RuleLayer.PATTERN
    base_confidence = 0.80

    def analyze(self, file_path, source, ast_tree=None):
        bugs = []
        sp = str(file_path)
        if not sp.endswith(('.ts', '.tsx')):
            return bugs
        for ln, line in enumerate(source.split("\n"), 1):
            s = line.strip()
            if s.startswith("//"):
                continue
            if re.search(r':\s*any', s) and "catch" not in s and "as any" not in s:
                bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                    title="Using 'any' type",
                    description="Disables TypeScript type checking",
                    code_snippet=s[:200], fix_suggestion="Use concrete type or unknown",
                    confidence=0.75, extra_id=f"any_{ln}"))
            if "@ts-ignore" in s:
                bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                    title="Using @ts-ignore",
                    description="Skips type checking for next line",
                    code_snippet=s[:200], fix_suggestion="Use @ts-expect-error",
                    confidence=0.85, extra_id=f"tsig_{ln}"))
            if re.search(r'export\s+(?:async\s+)?function\s+\w+\s*\([^)]*\)\s*\{', s):
                if not re.search(r':\s*\w+\s*\{', s):
                    bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                        title="Exported function missing return type",
                        description="No explicit return type annotation",
                        code_snippet=s[:200], fix_suggestion="Add return type",
                        confidence=0.60, extra_id=f"rt_{ln}"))
        return bugs

