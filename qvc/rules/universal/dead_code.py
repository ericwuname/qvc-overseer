"""死代码检测规则 V2 —— 减少误报"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class DeadCodeRule(BaseRule):
    rule_id = "UNI_DEAD_CODE_001"
    name = "死代码检测"
    description = "检测未使用的导入、注释掉的代码块、永远不会执行的代码"
    severity = Severity.MINOR
    category = BugCategory.DEAD_CODE
    languages = ["*"]
    layer = RuleLayer.PATTERN  # base_confidence = 0.7
    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        lines = source.split("\n")

        # 检测注释掉的代码
        commented_code_pattern = re.compile(
            r'^\s*(#|//|<!--)\s*(def |class |function |const |let |var |import |from |export |if |for |while |return |print\()',
        )
        for i, line in enumerate(lines, 1):
            if commented_code_pattern.match(line):
                bugs.append(self._create_bug(
                    file_path=file_path,
                    line_start=i, line_end=i,
                    title="注释掉的代码",
                    description="发现被注释掉的代码行，建议删除或恢复",
                    code_snippet=line.strip()[:200],
                    fix_suggestion="删除注释掉的代码，或添加 TODO 说明保留原因",
                    confidence=0.7,
                    extra_id=f"commented_L{i}",
                    root_cause=RootCause.AGENT_ISOLATION,
                ))

        # 检测 unreachable code: return/raise/break/continue 后同一缩进级别的代码
        # 通过检测缩进变化来避免跨分支误报
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*", "'''", '"""')):
                i += 1
                continue

            # 检测 return/raise/break/continue
            if re.match(r'^\s*(return|raise|break|continue)\b', stripped):
                current_indent = len(line) - len(line.lstrip())
                # 找到下一个同缩进或更浅缩进的非空行
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    next_stripped = next_line.strip()
                    if not next_stripped or next_stripped.startswith(("#", "//", "/*", "*")):
                        j += 1
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    # 同缩进级别的代码在 return/raise 后不可达
                    if next_indent == current_indent and not next_stripped.startswith(("return", "raise", "except", "elif", "else", "finally")):
                        # 确认不是新函数/类定义
                        if not re.match(r'^\s*(def |class |@)', next_stripped):
                            bugs.append(self._create_bug(
                                file_path=file_path,
                                line_start=j+1, line_end=j+1,
                                title="不可达代码",
                                description="return/raise/break/continue 之后的同缩进级别代码不会被执行",
                                code_snippet=next_stripped[:200],
                                fix_suggestion="移除不可达代码或调整控制流",
                                confidence=0.8,
                                extra_id=f"unreachable_L{j+1}",
                                root_cause=RootCause.COPY_PASTE,
                            ))
                    break
                i = j
                continue
            i += 1

        return bugs

    def supports_language(self, language: str) -> bool:
        return True
