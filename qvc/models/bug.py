"""数据模型：缺陷 Bug"""

from dataclasses import dataclass, field
from datetime import datetime
from .severity import Severity, BugCategory, RootCause


@dataclass
class Bug:
    """单个代码缺陷"""
    id: str
    severity: Severity
    category: BugCategory
    title: str
    description: str
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    root_cause: RootCause | None = None
    fix_suggestion: str = ""
    confidence: float = 1.0
    # V3.0 新增：外部监工字段
    blindspot_type: str | None = None       # memory_trap / context_lost / self_harvest / cross_file / boundary
    detectable_by_self_review: bool = True   # AI 自审理论上能否发现此问题
    self_review_matched: bool = False        # AI 自审实际是否报告了此问题
    rule_id: str = ""
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity.name,
            "severity_label": str(self.severity),
            "category": self.category.name,
            "category_label": self.category.label,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "root_cause": self.root_cause.value if self.root_cause else None,
            "fix_suggestion": self.fix_suggestion,
            "confidence": self.confidence,
            "rule_id": self.rule_id,
            "blindspot_type": self.blindspot_type,
            "detectable_by_self_review": self.detectable_by_self_review,
            "self_review_matched": self.self_review_matched,
            "detected_at": self.detected_at.isoformat(),
        }

    def __hash__(self) -> int:
        return hash((self.file_path, self.line_start, self.rule_id))
