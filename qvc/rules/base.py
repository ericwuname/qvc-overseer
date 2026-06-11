"""检测规则基类 V2 — 置信度分层"""

from abc import ABC, abstractmethod
from pathlib import Path
from qvc.models.bug import Bug, Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer


class RuleResult:
    def __init__(self, bugs: list[Bug] | None = None):
        self.bugs = bugs or []

    def add_bug(self, bug: Bug):
        self.bugs.append(bug)

    def extend(self, other: "RuleResult"):
        self.bugs.extend(other.bugs)


class BaseRule(ABC):
    """代码审查规则基类（V2：分层置信度）"""

    rule_id: str = ""
    name: str = ""
    description: str = ""
    severity: Severity = Severity.MODERATE
    category: BugCategory = BugCategory.STYLE
    languages: list[str] = []

    # V2 新增：分层属性
    layer: RuleLayer = RuleLayer.HEURISTIC  # 默认启发式（最保守）
    base_confidence: float | None = None     # None 则使用 layer.base_confidence

    @abstractmethod
    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list[Bug]:
        ...

    def get_confidence(self, evidence_strength: float = 1.0) -> float:
        """根据证据强度计算置信度。evidence_strength: 0.0-1.0，1.0 = 完全匹配"""
        base = self.base_confidence if self.base_confidence is not None else self.layer.base_confidence
        return min(0.99, base * evidence_strength)

    def _create_bug(
        self,
        file_path: Path,
        line_start: int,
        line_end: int,
        title: str,
        description: str,
        code_snippet: str = "",
        fix_suggestion: str = "",
        confidence: float | None = None,
        extra_id: str = "",
        root_cause: RootCause | None = None,
    ) -> Bug:
        bug_id = self.rule_id
        if extra_id:
            bug_id = f"{bug_id}-{extra_id}"

        # 使用分层默认置信度（如果未显式指定）
        if confidence is None:
            confidence = self.get_confidence()

        # Layer 3 规则禁止产出 FATAL
        effective_severity = self.severity
        if self.layer == RuleLayer.HEURISTIC and effective_severity == Severity.FATAL:
            effective_severity = Severity.SEVERE

        return Bug(
            id=bug_id,
            severity=effective_severity,
            category=self.category,
            title=title,
            description=description,
            file_path=str(file_path),
            line_start=line_start,
            line_end=line_end,
            code_snippet=code_snippet,
            fix_suggestion=fix_suggestion,
            confidence=confidence,
            rule_id=self.rule_id,
            root_cause=root_cause,
        )

    def supports_language(self, language: str) -> bool:
        return language.lower() in (l.lower() for l in self.languages)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.rule_id}, L{self.layer.value})>"