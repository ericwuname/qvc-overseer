"""正则脆弱性检测规则"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class RegexFragilityRule(BaseRule):
    rule_id = "UNI_REGEX_FRAGILITY_001"
    name = "正则脆弱性检测"
    description = "检测依赖正则解析非结构化数据（Markdown/HTML/自然语言）的代码"
    severity = Severity.MODERATE
    category = BugCategory.REGEX_FRAGILITY
    languages = ["*"]
    layer = RuleLayer.PATTERN  # base_confidence = 0.6
    # 标记正则解析 markdown/html/自然语言的高风险模式
    FRAGILE_PATTERNS = [
        r're\.(search|match|findall|finditer|sub)\(',
        r'\.split\(.*[\*\#\-]',
    ]

    # 高风险内容关键词
    HIGH_RISK_CONTENT = [
        "markdown", "##", "**", "__", "```",
        "<div", "<p>", "<span", "<table",
    ]

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            # 检测是否使用正则解析 markdown 内容
            for pattern in self.FRAGILE_PATTERNS:
                if re.search(pattern, line):
                    for risk_word in self.HIGH_RISK_CONTENT:
                        if risk_word in line:
                            bugs.append(self._create_bug(
                                file_path=file_path,
                                line_start=i,
                                line_end=i,
                                title="脆弱的正则解析",
                                description=f"使用正则表达式解析包含 '{risk_word}' 的文本，AI输出格式变化可能导致正则失效",
                                code_snippet=line.strip()[:200],
                                fix_suggestion="改为结构化数据传递（JSON），而非解析非结构化文本",
                                root_cause=RootCause.REGEX_FRAGILITY,
                                confidence=0.6,
                                extra_id=f"L{i}",
                            ))
                            break
        return bugs

    def supports_language(self, language: str) -> bool:
        return True
