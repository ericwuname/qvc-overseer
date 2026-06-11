"""进化引擎 - 缺口发现器"""

from pathlib import Path
from qvc.models.bug import Bug
from .fingerprint import KnowledgeGap, Fingerprint


class GapDetector:
    """对比静态规则与LLM审查结果，发现知识缺口"""

    def detect(
        self,
        static_bugs: list[Bug],
        llm_bugs: list[Bug],
    ) -> list[KnowledgeGap]:
        """找出LLM发现但静态规则遗漏的缺陷"""

        # 按 (文件路径, 行号, 缺陷类别) 构建静态规则已覆盖的位置
        static_covered = set()
        for b in static_bugs:
            static_covered.add((b.file_path, b.line_start, b.rule_id))

        # 按 (文件路径, 行号) 去重LLM结果
        llm_positions = {}
        for b in llm_bugs:
            key = (b.file_path, b.line_start)
            if key not in llm_positions:
                llm_positions[key] = b

        gaps = []
        for (file_path, line), bug in llm_positions.items():
            # 检查静态规则是否已覆盖这个位置
            is_covered = any(
                (file_path, line, rule_id) in static_covered
                for rule_id in [b.rule_id for b in static_bugs]
            )
            if not is_covered:
                gaps.append(KnowledgeGap(
                    bug_title=bug.title,
                    bug_description=bug.description,
                    code_snippet=bug.code_snippet[:500],
                    gap_category=bug.category.name,
                    file_path=file_path,
                    line_number=line,
                    severity=bug.severity.name,
                ))

        return gaps

    def cluster_by_category(self, gaps: list[KnowledgeGap]) -> dict[str, list[KnowledgeGap]]:
        """按缺陷类别聚类缺口"""
        clusters = {}
        for gap in gaps:
            clusters.setdefault(gap.gap_category, []).append(gap)
        return clusters

    def find_new_categories(self, gaps: list[KnowledgeGap],
                           known_categories: set[str]) -> list[str]:
        """发现全新的缺陷类别（之前指纹库中不存在的）"""
        gap_categories = {g.gap_category for g in gaps}
        return list(gap_categories - known_categories)
