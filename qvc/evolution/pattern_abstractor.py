"""进化引擎 - 模式抽象器 V3.0 — 审查即学习"""

import json
import hashlib
from datetime import datetime
from .fingerprint import Fingerprint, FingerprintStatus, KnowledgeGap


class PatternAbstractor:
    """从具体缺陷中抽象出通用指纹"""

    def __init__(self, llm_reviewer=None):
        self.llm = llm_reviewer

    def abstract_from_gaps(
        self,
        category: str,
        gaps: list[KnowledgeGap],
    ) -> Fingerprint | None:
        """从同一类别的多个缺口抽象一个通用指纹"""

        if len(gaps) < 2:
            return None

        titles = [g.bug_title for g in gaps]
        snippets = [g.code_snippet for g in gaps[:5]]
        severity = self._most_common([g.severity for g in gaps])

        if self.llm:
            return self._llm_abstract(category, titles, snippets, severity, len(gaps))
        else:
            return self._simple_abstract(category, titles, snippets, severity, len(gaps))

    def _llm_abstract(self, category: str, titles: list[str],
                     snippets: list[str], severity: str,
                     count: int) -> Fingerprint | None:
        """使用LLM做深度模式抽象"""
        cases_text = ""
        for i, (title, snippet) in enumerate(zip(titles, snippets)):
            cases_text += "\n案例{}:\n  问题: {}\n  代码: {}\n".format(i+1, title, snippet)

        prompt = (
            "以下是AI生成代码中发现的{}个相似缺陷（类别：{}）：\n\n"
            "{}\n"
            "请将这些具体缺陷抽象为一个通用的检测指纹。返回JSON：\n"
            '{{"pattern_name":"简洁英文名","description":"中文描述",'
            '"abstract_signature":{{"pattern_type":"","trigger_condition":"","example_trigger":"","example_fix":""}},'
            '"fix_template":"通用修复建议"}}\n'
            "只返回JSON，不要其他内容。"
        ).format(count, category, cases_text)

        try:
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1024,
            )
            data = json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return None

        if not data.get("pattern_name"):
            return None

        return Fingerprint(
            id=self._generate_id(category),
            category=category,
            pattern_name=data["pattern_name"],
            description=data.get("description", ""),
            abstract_signature=data.get("abstract_signature", {}),
            severity=severity,
            confidence=0.6,
            occurrence_count=count,
            status=FingerprintStatus.CANDIDATE,
            source_bugs=[t[:50] for t in titles],
            fix_template=data.get("fix_template", ""),
        )

    def _simple_abstract(self, category: str, titles: list[str],
                        snippets: list[str], severity: str,
                        count: int) -> Fingerprint:
        """无LLM时的简单抽象 —— 基于关键词聚类"""
        all_text = " ".join(titles + snippets)
        fingerprint_id = self._generate_id(category)

        return Fingerprint(
            id=fingerprint_id,
            category=category,
            pattern_name="AUTO_{}".format(category),
            description="自动发现：{}".format(titles[0][:80]),
            abstract_signature={
                "pattern_type": "keyword_cluster",
                "keywords": self._extract_keywords(all_text),
                "sample_count": count,
            },
            severity=severity,
            confidence=0.4,
            occurrence_count=count,
            status=FingerprintStatus.CANDIDATE,
            source_bugs=[t[:50] for t in titles],
            fix_template="请审核此候选指纹并补充修复建议",
        )

    # ═══════════════════════════════════════════════════════
    # V3.0 新增：审查即学习
    # ═══════════════════════════════════════════════════════

    def learn_from_scan(self, verified_bugs: list, store=None) -> int:
        """V3.0: 从本次扫描结果中学习，提取新指纹并入库

        Args:
            verified_bugs: 确认过的真bug列表
            store: FingerprintStore实例，None则不存储

        Returns:
            新入库指纹数量
        """
        if len(verified_bugs) < 2:
            return 0

        clusters = self._cluster_by_rule_id(verified_bugs)
        new_count = 0

        for rule_id, bug_cluster in clusters.items():
            if len(bug_cluster) < 2:
                continue

            titles = [b.title for b in bug_cluster]
            snippets = [b.code_snippet for b in bug_cluster if b.code_snippet]
            
            sev = "SEVERE"
            if hasattr(bug_cluster[0], 'severity'):
                sev = getattr(bug_cluster[0].severity, 'name', 'SEVERE')
            
            cat = "INCOMPLETE"
            if hasattr(bug_cluster[0], 'category'):
                cat = getattr(bug_cluster[0].category, 'name', 'INCOMPLETE')

            fingerprint = self._simple_abstract(cat, titles, snippets, sev, len(bug_cluster))

            if not self._quality_filter(fingerprint):
                continue

            if store and hasattr(store, 'add_fingerprint'):
                if not self._is_duplicate(fingerprint, store):
                    store.add_fingerprint(fingerprint, source="self_evolution")
                    new_count += 1

        return new_count

    def _cluster_by_rule_id(self, bugs: list) -> dict:
        """按 rule_id 聚类"""
        clusters = {}
        for bug in bugs:
            rule_id = getattr(bug, 'rule_id', 'UNKNOWN')
            if rule_id not in clusters:
                clusters[rule_id] = []
            clusters[rule_id].append(bug)
        return clusters

    def _quality_filter(self, fp: Fingerprint) -> bool:
        """V3.0: 质量控制 — 同一模式 ≥2 次确认才入库"""
        if fp.occurrence_count < 2:
            return False
        if fp.confidence < 0.3:
            return False
        if not fp.pattern_name or fp.pattern_name.startswith("AUTO_UNKNOWN"):
            return False
        return True

    def _is_duplicate(self, fp: Fingerprint, store) -> bool:
        """相似度 > 70% 视为重复"""
        try:
            existing = store.get_all_fingerprints(status_filter=["active", "verified"])
            fp_keywords = set(self._extract_keywords(fp.description or ""))
            for existing_fp in existing:
                desc = getattr(existing_fp, 'description', '') or ''
                existing_keywords = set(self._extract_keywords(desc))
                if not fp_keywords or not existing_keywords:
                    continue
                overlap = len(fp_keywords & existing_keywords) / max(len(fp_keywords | existing_keywords), 1)
                if overlap > 0.7:
                    return True
        except Exception:
            pass
        return False

    def _generate_id(self, category: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_cat = category[:12]
        return "FP_{}_{}".format(short_cat, timestamp)

    def _extract_keywords(self, text: str, max_kw: int = 5) -> list[str]:
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be",
            "has", "have", "had", "do", "does", "did", "will",
            "not", "no", "or", "and", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "as", "into",
            "this", "that", "it", "its", "if", "else", "then"
        }
        words = [w for w in text.lower().split()
                if len(w) > 3 and w not in stop_words]
        from collections import Counter
        return [w for w, _ in Counter(words).most_common(max_kw)]

    def _most_common(self, items: list[str]) -> str:
        from collections import Counter
        return Counter(items).most_common(1)[0][0]
