"""Go nil pointer detection — Layer 2 (PATTERN, 80%)"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class GoNilSafetyRule(BaseRule):
    rule_id = "GO_NIL_SAFETY_001"
    name = "Go Nil Pointer Safety"
    description = "Detect potential nil pointer dereference without prior nil check"
    severity = Severity.SEVERE
    category = BugCategory.NULL_SAFETY
    languages = ["go"]
    layer = RuleLayer.PATTERN
    base_confidence = 0.80

    def analyze(self, file_path, source, ast_tree=None):
        bugs = []
        lines = source.split("\n")

        for line_no, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("//") or s.startswith("/*"):
                continue

            # Pattern 1: Type assertion without ok check
            # x := val.(Type) without checking ok
            if re.search(r":=\s*\w+\.\([^)]+\)(?!\s*,)", s):
                bugs.append(self._create_bug(
                    file_path=file_path, line_start=line_no, line_end=line_no,
                    title="Type assertion without ok check",
                    description="Type assertion may panic if the assertion fails. Use 'val, ok := x.(Type)' pattern.",
                    code_snippet=s[:200],
                    fix_suggestion="Use the comma-ok pattern: val, ok := x.(Type)",
                    confidence=0.85, extra_id=f"type_assert_{line_no}",
                ))

            # Pattern 2: Pointer method call without nil check
            # ptr.Method() where ptr could be nil (heuristic)
            ptr_call = re.search(r'(\w+)\.(\w+)\s*\(', s)
            if ptr_call and not s.startswith("if ") and "err" not in s.lower():
                var_name = ptr_call.group(1)
                # Simple heuristic: if variable name suggests a pointer (starts with lowercase letter, not built-in)
                if var_name[0].islower() and var_name not in ("fmt", "os", "io", "http", "json", "time", "strings", "strconv", "context", "errors", "log", "sync", "math", "sort", "bytes", "bufio"):
                    # Check if there's a nil guard nearby (within 5 lines before)
                    has_guard = False
                    for check_line in range(max(0, line_no - 5), line_no):
                        if check_line - 1 < len(lines):
                            check = lines[check_line - 1].strip()
                            if f"{var_name} != nil" in check or f"{var_name} == nil" in check:
                                has_guard = True
                                break
                    if not has_guard:
                        bugs.append(self._create_bug(
                            file_path=file_path, line_start=line_no, line_end=line_no,
                            title=f"Method call on potentially nil pointer '{var_name}'",
                            description=f"'{var_name}.{ptr_call.group(2)}()' may panic if '{var_name}' is nil. Add nil check before this line.",
                            code_snippet=s[:200],
                            fix_suggestion=f"Add: if {var_name} != nil {{ ... }}",
                            confidence=0.60, extra_id=f"nil_ptr_{line_no}",
                            root_cause=RootCause.NO_DEFENSE,
                        ))

        return bugs
