"""进化引擎 - 指纹数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class FingerprintStatus(Enum):
    CANDIDATE = "candidate"        # 自动生成，待验证
    VERIFIED = "verified"          # 人工审核通过
    ACTIVE = "active"              # 正式激活，参与扫描
    DEPRECATED = "deprecated"      # 已废弃
    REJECTED = "rejected"          # 审核拒绝


@dataclass
class Fingerprint:
    """缺陷指纹 —— 从具体bug中抽象出的通用检测模式"""

    id: str                                          # 唯一标识：FP_20260611_042
    category: str                                    # 分类：NULL_SAFETY / VAR_SCOPE / ...
    pattern_name: str                                # 模式名称
    description: str                                 # 自然语言描述
    abstract_signature: dict                         # 抽象代码签名
    severity: str = "SEVERE"                         # 严重度
    confidence: float = 0.5                          # 置信度 0-1
    occurrence_count: int = 1                        # 发现次数
    status: FingerprintStatus = FingerprintStatus.CANDIDATE
    source_bugs: list[str] = field(default_factory=list)  # 来源bug ID
    contributor: str = "anonymous"                   # 贡献者
    fix_template: str = ""                           # 修复模板
    created_at: datetime = field(default_factory=datetime.now)
    promoted_at: datetime | None = None              # 升级时间
    verifier: str = ""                               # 审核者

    def to_dict(self) -> dict:
        return {
            "fingerprint_id": self.id,
            "category": self.category,
            "pattern_name": self.pattern_name,
            "description": self.description,
            "abstract_signature": self.abstract_signature,
            "severity": self.severity,
            "confidence": self.confidence,
            "occurrence_count": self.occurrence_count,
            "status": self.status.value,
            "source_bugs": self.source_bugs,
            "contributor": self.contributor,
            "fix_template": self.fix_template,
            "created_at": self.created_at.isoformat(),
            "promoted_at": self.promoted_at.isoformat() if self.promoted_at else None,
            "verifier": self.verifier,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Fingerprint":
        return cls(
            id=data["fingerprint_id"],
            category=data["category"],
            pattern_name=data["pattern_name"],
            description=data["description"],
            abstract_signature=data.get("abstract_signature", {}),
            severity=data.get("severity", "SEVERE"),
            confidence=data.get("confidence", 0.5),
            occurrence_count=data.get("occurrence_count", 1),
            status=FingerprintStatus(data.get("status", "candidate")),
            source_bugs=data.get("source_bugs", []),
            contributor=data.get("contributor", "anonymous"),
            fix_template=data.get("fix_template", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            promoted_at=datetime.fromisoformat(data["promoted_at"]) if data.get("promoted_at") else None,
            verifier=data.get("verifier", ""),
        )


@dataclass
class KnowledgeGap:
    """知识缺口 —— LLM发现了但静态规则遗漏的缺陷"""

    bug_title: str
    bug_description: str
    code_snippet: str
    gap_category: str
    file_path: str
    line_number: int
    severity: str
    discovered_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "bug_title": self.bug_title,
            "bug_description": self.bug_description,
            "code_snippet": self.code_snippet,
            "gap_category": self.gap_category,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "severity": self.severity,
            "discovered_at": self.discovered_at.isoformat(),
        }


@dataclass
class EvolutionReport:
    """进化循环报告"""

    new_gaps: int = 0
    new_candidates: int = 0
    ready_for_review: int = 0
    total_fingerprints: int = 0
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "new_gaps": self.new_gaps,
            "new_candidates": self.new_candidates,
            "ready_for_review": self.ready_for_review,
            "total_fingerprints": self.total_fingerprints,
            "details": self.details,
        }
