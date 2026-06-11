"""React useEffect 依赖检查 — Layer 2 (PATTERN, 75%)"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class ReactUseEffectDepsRule(BaseRule):
    rule_id = "REACT_USE_EFFECT_DEPS_001"
    name = "React useEffect 依赖检查"
    description = "检测 useEffect 中使用了外部变量但未列入依赖数组"
    severity = Severity.SEVERE
    category = BugCategory.EVENT_INTEGRITY
    languages = ["javascript", "typescript"]
    layer = RuleLayer.PATTERN
    base_confidence = 0.75

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []

        # 简单检测：useEffect 回调中使用了 useState 的 setter 以外的外部变量
        # 但依赖数组为空 [] 或缺少这些变量
        pattern = r'useEffect\s*\(\s*(?:\(\)\s*=>|function\s*\(\))'
        uses_external = r'(?:props\.|state\.|[a-z]\w*\.)'

        lines = source.split("\n")
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()

            # 检测 useEffect(() => { ... }, [])
            match = re.search(r'useEffect\s*\(\s*\(\)\s*=>\s*\{', stripped)
            if not match:
                match = re.search(r'useEffect\s*\(\s*function\s*\(\)\s*\{', stripped)

            if match:
                # 找到 useEffect 调用，检查依赖数组
                # 在接下来的行中找依赖数组
                useEffect_start = line_no
                deps_found = False
                empty_deps = False

                for look_ahead in range(line_no, min(line_no + 30, len(lines) + 1)):
                    look_line = lines[look_ahead - 1]
                    # 找 ], [ 或 ],[])  或  }, [])
                    if re.search(r'\},\s*\[\s*\]\s*\)', look_line):
                        empty_deps = True
                        deps_found = True
                        break
                    elif re.search(r'\},\s*\[', look_line):
                        deps_found = True
                        break
                    # 看是否有 }, ) 即空依赖
                    if re.search(r'\},\s*\)', look_line):
                        empty_deps = True
                        deps_found = True
                        break

                if empty_deps:
                    # 在回调体内检查是否使用了外部变量
                    has_external = False
                    for check_line in range(line_no + 1, min(line_no + 25, len(lines) + 1)):
                        check = lines[check_line - 1].strip()
                        if re.search(r'(?:props\.|state\.|\w+\.\w+)', check):
                            if not re.search(r'(?:set\w+|console\.|Math\.|JSON\.)', check):
                                has_external = True
                                break
                        if check == "}" or check == "});" or check == "})":
                            break

                    if has_external:
                        bugs.append(self._create_bug(
                            file_path=file_path,
                            line_start=useEffect_start,
                            line_end=useEffect_start,
                            title="useEffect 依赖数组为空但使用了外部变量",
                            description="useEffect(() => {...}, []) 中的回调引用了外部变量，但依赖数组为空。可能导致闭包陷阱或使用了过时的状态值。",
                            code_snippet=stripped[:200],
                            fix_suggestion="将回调中使用的外部变量加入依赖数组，或使用 useRef / useCallback 优化",
                            root_cause=RootCause.STALE_STATE,
                            confidence=0.75,
                            extra_id=f"use_effect_{useEffect_start}",
                        ))

        return bugs
