"""
Detect setInterval/event listener leaks — Layer 2 (PATTERN, 65%)
"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class JSMemoryLeakRule(BaseRule):
    rule_id = "JS_MEMORY_LEAK_001"
    name = "JavaScript Memory Leak Detection"
    description = "Detect setInterval/event listener leaks"
    severity = Severity.MODERATE
    category = BugCategory.EVENT_INTEGRITY
    languages = ['javascript', 'typescript']
    layer = RuleLayer.PATTERN
    base_confidence = 0.65

    def analyze(self, file_path, source, ast_tree=None):
        bugs = []
        lines = source.split("\n")
        iv = len(re.findall(r'setInterval\s*\(', source))
        cv = len(re.findall(r'clearInterval\s*\(', source))
        if iv > cv:
            for ln, line in enumerate(lines, 1):
                if "setInterval(" in line:
                    bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                        title="setInterval without clearInterval",
                        description="Timer may cause memory leak",
                        code_snippet=line.strip()[:200], fix_suggestion="Clear on unmount",
                        confidence=0.60, extra_id=f"iv_{ln}"))
        av = len(re.findall(r'addEventListener\s*\(', source))
        rv = len(re.findall(r'removeEventListener\s*\(', source))
        if av > rv:
            for ln, line in enumerate(lines, 1):
                if "addEventListener(" in line:
                    bugs.append(self._create_bug(file_path=file_path, line_start=ln, line_end=ln,
                        title="addEventListener without removeEventListener",
                        description="Listener may cause memory leak",
                        code_snippet=line.strip()[:200], fix_suggestion="Remove on unmount",
                        confidence=0.60, extra_id=f"ev_{ln}"))
        ie, hs, hc, es = False, False, False, 0
        for ln, line in enumerate(lines, 1):
            s = line.strip()
            if re.search(r'useEffect\s*\(\s*\(\)\s*=>\s*\{', s):
                ie, hs, hc, es = True, False, False, ln
                continue
            if ie:
                if re.search(r'(?:addEventListener|subscribe|on\s*\(|setInterval)\s*\(', s):
                    hs = True
                if re.search(r'return\s+\(\)\s*=>', s):
                    hc = True
                if s in ("}","});","})"):
                    if hs and not hc:
                        bugs.append(self._create_bug(file_path=file_path, line_start=es, line_end=ln,
                            title="useEffect has subscriptions but no cleanup",
                            description="Missing return cleanup function",
                            code_snippet=lines[es-1].strip()[:200],
                            fix_suggestion="Return cleanup function",
                            confidence=0.70, extra_id=f"ec_{es}"))
                    ie = False
        return bugs

