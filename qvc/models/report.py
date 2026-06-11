"""数据模型：审查报告"""

from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
from .bug import Bug
from .severity import Severity, BugCategory, RootCause


@dataclass
class ScanSummary:
    """扫描统计摘要"""
    total_files: int = 0
    total_lines: int = 0
    languages: list[str] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "languages": self.languages,
            "duration_ms": self.duration_ms,
        }


@dataclass
class Report:
    """审查报告"""
    project_name: str
    scan_summary: ScanSummary
    bugs: list[Bug]
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def total_bugs(self) -> int:
        return len(self.bugs)

    @property
    def by_severity(self) -> dict[str, int]:
        counts = Counter(b.severity.name for b in self.bugs)
        return {s.name: counts.get(s.name, 0) for s in Severity}

    @property
    def by_category(self) -> dict[str, int]:
        counts = Counter(b.category.name for b in self.bugs)
        return {c.name: counts.get(c.name, 0) for c in BugCategory}

    @property
    def by_root_cause(self) -> dict[str, int]:
        counts = Counter(
            b.root_cause.value if b.root_cause else "未归类"
            for b in self.bugs
        )
        return dict(counts)

    @property
    def fatal_bugs(self) -> list[Bug]:
        return [b for b in self.bugs if b.severity == Severity.FATAL]

    @property
    def severe_bugs(self) -> list[Bug]:
        return [b for b in self.bugs if b.severity == Severity.SEVERE]

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "scan_summary": self.scan_summary.to_dict(),
            "total_bugs": self.total_bugs,
            "by_severity": self.by_severity,
            "by_category": self.by_category,
            "by_root_cause": self.by_root_cause,
            "bugs": [b.to_dict() for b in self.bugs],
            "generated_at": self.generated_at.isoformat(),
        }
