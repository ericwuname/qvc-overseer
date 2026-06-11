"""进化引擎 - 进化循环调度器"""

from pathlib import Path
from datetime import datetime
from qvc.models.bug import Bug
from qvc.analyzers.static_analyzer import StaticAnalyzer
from .fingerprint import EvolutionReport, FingerprintStatus
from .fingerprint_store import FingerprintStore
from .gap_detector import GapDetector
from .pattern_abstractor import PatternAbstractor


class EvolutionCycle:
    """自我进化循环 —— 每次审查后自动触发"""

    def __init__(
        self,
        static_analyzer: StaticAnalyzer,
        fingerprint_store: FingerprintStore,
        gap_detector: GapDetector | None = None,
        pattern_abstractor: PatternAbstractor | None = None,
        llm_reviewer=None,
    ):
        self.static = static_analyzer
        self.store = fingerprint_store
        self.gap_detector = gap_detector or GapDetector()
        self.abstractor = pattern_abstractor or PatternAbstractor(llm_reviewer)
        self.llm = llm_reviewer

    def run(
        self,
        file_paths: list[Path],
        static_bugs: list[Bug],
        llm_bugs: list[Bug] | None = None,
    ) -> EvolutionReport:
        """执行一次完整的进化循环"""
        report = EvolutionReport()

        # Step 1: 如果没有LLM结果，跳过缺口发现
        if llm_bugs is None or len(llm_bugs) == 0:
            report.details.append("无LLM审查结果，跳过缺口发现")
            report.total_fingerprints = self.store.get_stats()["total"]
            return report

        # Step 2: 缺口发现
        gaps = self.gap_detector.detect(static_bugs, llm_bugs)
        report.new_gaps = len(gaps)
        self.store.log_event("gap_detection", f"发现 {len(gaps)} 个知识缺口")

        if len(gaps) == 0:
            report.details.append("没有发现新的知识缺口")
            report.total_fingerprints = self.store.get_stats()["total"]
            return report

        # Step 3: 保存缺口
        for gap in gaps:
            self.store.add_gap(
                bug_title=gap.bug_title,
                bug_description=gap.bug_description,
                code_snippet=gap.code_snippet,
                gap_category=gap.gap_category,
                file_path=gap.file_path,
                line_number=gap.line_number,
                severity=gap.severity,
            )
        self.store.log_event("gap_saved", f"保存 {len(gaps)} 个知识缺口")

        # Step 4: 按类别聚类
        clusters = self.gap_detector.cluster_by_category(gaps)
        report.details.append(f"知识缺口分布在 {len(clusters)} 个类别")

        # Step 5: 对每个聚类尝试抽象
        for category, cluster_gaps in clusters.items():
            if len(cluster_gaps) >= 2:
                try:
                    fingerprint = self.abstractor.abstract_from_gaps(
                        category, cluster_gaps
                    )
                    if fingerprint:
                        self.store.add_fingerprint(fingerprint, source="local")
                        report.new_candidates += 1
                        report.details.append(
                            f"生成候选指纹: {fingerprint.id} ({category}, {len(cluster_gaps)}个案例)"
                        )
                        self.store.mark_gaps_abstracted(category)
                except Exception as e:
                    self.store.log_event("abstraction_error", str(e))

        # Step 6: 检查是否有待审核的候选指纹
        pending = self.store.get_pending_review()
        report.ready_for_review = len(pending)

        # Step 7: 统计
        stats = self.store.get_stats()
        report.total_fingerprints = stats["total"]

        self.store.log_event(
            "evolution_complete",
            f"新缺口: {report.new_gaps}, 新候选: {report.new_candidates}, 待审核: {report.ready_for_review}"
        )

        return report

    def get_status(self) -> dict:
        """获取进化状态"""
        stats = self.store.get_stats()
        pending = self.store.get_pending_review()
        recent = self.store.get_recent_events(10)

        return {
            "fingerprints": stats,
            "pending_review": [
                {"id": fp.id, "name": fp.pattern_name, "category": fp.category,
                 "occurrences": fp.occurrence_count, "confidence": fp.confidence}
                for fp in pending
            ],
            "recent_events": recent,
        }
