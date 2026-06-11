"""本地进化基因池 V3.1 — 单机闭环，零网络

每次扫描自动发现新模式 → 本地 SQLite 存储 → 置信度膨胀。
不需要网络，不需要 GitHub，不需要配置。
"""

from pathlib import Path
from qvc.evolution.fingerprint_store import FingerprintStore


class GenePool:
    """本地进化基因池

    设计原则：
    - 零网络：不需要 GitHub、API Key
    - 零感知：用户在后台默默工作
    - 零退化：50 条种子是底线，空社区不影响体验
    - 自生长：每次扫描自动学习新模式
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            home = Path.home() / ".qvc"
            home.mkdir(exist_ok=True)
            db_path = home / "gene_pool.db"
        self.store = FingerprintStore(db_path=Path(db_path))
        self._stats = self.store.get_stats()

    def on_scan_complete(self, bugs: list) -> int:
        """每次扫描完成后自动调用——自生长的核心。

        1. 聚类：同规则 >= 2 个缺陷 → 候选模式
        2. 去重：检查是否已存在
        3. 存储：写入本地候选指纹池

        Returns: 本次新增候选指纹数量
        """
        if len(bugs) < 2:
            return 0

        # 按 rule_id 聚类
        clusters = {}
        for bug in bugs:
            rule_id = getattr(bug, 'rule_id', 'UNKNOWN')
            if rule_id not in clusters:
                clusters[rule_id] = []
            clusters[rule_id].append(bug)

        new_count = 0
        for rule_id, bug_cluster in clusters.items():
            if len(bug_cluster) < 2:
                continue

            # 提取摘要信息
            title = bug_cluster[0].title if bug_cluster else "auto"
            desc = bug_cluster[0].description if bug_cluster else ""
            snippet = bug_cluster[0].code_snippet if bug_cluster else ""

            # 生成简单指纹并写入
            from qvc.evolution.fingerprint import Fingerprint, FingerprintStatus
            import hashlib

            hash_id = hashlib.md5(
                (rule_id + title).encode()
            ).hexdigest()[:12]

            fp = Fingerprint(
                id="FP_LOCAL_{}".format(hash_id),
                category=str(getattr(bug_cluster[0], 'category', 'INCOMPLETE')).split('.')[-1] if getattr(bug_cluster[0], 'category', None) else 'INCOMPLETE',
                pattern_name="AUTO_{}".format(rule_id),
                description="自动发现: {} ({}次)".format(title[:80], len(bug_cluster)),
                abstract_signature={
                    "rule_id": rule_id,
                    "sample_count": len(bug_cluster),
                    "sample_title": title[:100],
                    "sample_snippet": snippet[:200],
                },
                severity="SEVERE",
                confidence=0.4,
                occurrence_count=len(bug_cluster),
                status=FingerprintStatus.CANDIDATE,
                source_bugs=[getattr(b, 'id', '?') for b in bug_cluster[:5]],
                fix_template="",
            )

            # 尝试存储（FingerprintStore 会处理去重）
            try:
                self.store.add_fingerprint(fp, source="local")
                new_count += 1
            except Exception:
                pass

        return new_count

    def get_confidence_boost(self, bug) -> float:
        """BLINDSPOT_FOUND: 缺陷匹配已有指纹 → 置信度膨胀

        - 种子指纹匹配：+0.15
        - 本地进化指纹匹配：+0.05
        - 无匹配：+0.00
        """
        # 简化实现：基于 rule_id 查询指纹库
        rule_id = getattr(bug, 'rule_id', '')
        if not rule_id:
            return 0.0

        try:
            # 查询是否有该规则的活跃指纹
            matching = self.store.query_by_rule(rule_id) if hasattr(self.store, 'query_by_rule') else []
            if matching:
                sources = {getattr(fp, 'source', 'local') for fp in matching if hasattr(fp, 'source')}
                if 'seed' in str(sources):
                    return min(0.15, 1.0 - bug.confidence)
                return min(0.05, 1.0 - bug.confidence)
        except Exception:
            pass

        return 0.0

    def get_candidate_count(self) -> int:
        """本地候选指纹数量（不含种子）"""
        stats = self.store.get_stats()
        return stats.get("local", 0) + stats.get("candidates", 0)

    def get_seed_count(self) -> int:
        """内置种子指纹数量"""
        stats = self.store.get_stats()
        return stats.get("seed", 0)

    def get_total_count(self) -> int:
        """基因池总指纹数"""
        stats = self.store.get_stats()
        return stats.get("total", 0)
