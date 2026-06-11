"""外部监工分析器 — V3.0 核心模块

QVC 的竞争力不来自"比 AI Agent 更聪明"，而来自"不在 AI Agent 的认知闭环里"。
本模块量化外部监工的核心价值：自审漏报率。
"""

from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, field
from qvc.models.bug import Bug


@dataclass
class BlindspotReport:
    """外部监工分析结果"""

    # 自审漏报率
    total_qvc_bugs: int = 0
    total_self_review_items: int = 0
    bugs_not_in_self_review: int = 0
    leak_rate: float = 0.0  # 自审漏报率: 0.0 ~ 1.0

    # 盲区分布
    blindspot_distribution: dict[str, int] = field(default_factory=dict)
    # memory_trap / context_lost / self_harvest / cross_file / boundary

    # 模式
    mode: str = "C"  # A=有自审报告 B=行业基准 C=待激活
    mode_description: str = ""

    # 自审解析状态
    self_review_available: bool = False
    self_review_agent: str | None = None  # codex / cursor / gpt / ...
    self_review_summary: str = ""


class BlindspotAnalyzer:
    """外部监工分析器

    输入：QVC 扫描结果 + 可选 AI 自审报告
    输出：BlindspotReport（含自审漏报率、盲区分布、对比摘要）
    """

    BLINDSPOT_DEFINITIONS = {
        "memory_trap": {
            "label": "记忆残留",
            "desc": "AI Agent 沿生成时的逻辑链审查，看不到链上的断裂点",
            "example": "函数A定义变量X，函数B引用X但X不在B的作用域",
        },
        "context_lost": {
            "label": "上下文遗忘",
            "desc": "多轮对话后 Agent 遗忘前文细节",
            "example": "API 函数参数数量或类型不匹配",
        },
        "self_harvest": {
            "label": "自利采摘",
            "desc": "Agent 找几个明显问题就说审查完成",
            "example": "自审只覆盖了前3个文件中的明显语法错误",
        },
        "cross_file": {
            "label": "跨文件一致性",
            "desc": "两个文件对同一概念有不同约定",
            "example": "同名/同义标识符在不同文件中的签名不一致",
        },
        "boundary": {
            "label": "边界条件",
            "desc": "函数参数/返回值未做空值或边界检查",
            "example": "属性/方法调用前缺少空值保护",
        },
    }

    # 规则 → 盲区类型 映射表
    RULE_BLINDSPOT_MAP = {
        "PY_VAR_SCOPE_001": "memory_trap",
        "PY_API_SIGNATURE_001": "context_lost",
        "PY_NULL_SAFETY_001": "boundary",
        "PY_IMPORT_CHECK_001": "cross_file",
        "PY_EXCEPTION_001": "boundary",
        "JS_VAR_SCOPE_001": "memory_trap",
        "REACT_USE_EFFECT_DEPS_001": "context_lost",
        "UNI_ENCODING_001": "cross_file",
        "UNI_DEAD_CODE_001": "self_harvest",
        "UNI_REGEX_001": "boundary",
        "UNI_HARDCODED_SECRETS_001": "boundary",
        "PY_API_DRIFT_001": "context_lost",
        "PY_STALE_REF_001": "context_lost",
        "CROSS_FILE": "context_lost",
    }

    # 规则 → AI 自审能否发现 映射表
    RULE_SELF_REVIEWABLE = {
        "PY_VAR_SCOPE_001": False,       # 作用域盲区，AI自审难以自检
        "PY_API_SIGNATURE_001": False,   # 上下文遗忘
        "PY_NULL_SAFETY_001": False,     # 边界条件盲区
        "PY_IMPORT_CHECK_001": False,    # 跨文件一致性
        "PY_EXCEPTION_001": False,       # 边界条件盲区
        "JS_VAR_SCOPE_001": False,
        "REACT_USE_EFFECT_DEPS_001": False,
        "UNI_ENCODING_001": True,        # 编码问题理论上自审可发现
        "UNI_DEAD_CODE_001": False,
        "UNI_REGEX_001": False,
        "UNI_HARDCODED_SECRETS_001": True,
        "PY_API_DRIFT_001": False,
        "PY_STALE_REF_001": False,
        "CROSS_FILE": False,  # 硬编码密钥自审可发现
    }

    def analyze(
        self,
        bugs: list[Bug],
        self_review_path: str | None = None,
        self_review_agent: str | None = None,
    ) -> BlindspotReport:
        """分析 QVC 扫描结果 vs AI 自审报告

        Args:
            bugs: QVC 扫描出的缺陷列表
            self_review_path: AI 自审报告文件路径（可选）
            self_review_agent: AI Agent 类型（codex/cursor/gpt），用于解析格式
        """
        # Step 1: 给每个 bug 打盲区标签
        self._classify_blindspots(bugs)

        if self_review_path:
            # 模式 A：有自审报告 → 精确对比
            return self._mode_a_with_self_review(bugs, self_review_path, self_review_agent)
        elif len(bugs) > 0:
            # 模式 B：无自审报告但有扫描结果 → 行业基准
            return self._mode_b_industry_baseline(bugs)
        else:
            # 模式 C：完全脱机（0缺陷）
            return self._mode_c_standalone()

    def _classify_blindspots(self, bugs: list[Bug]):
        """给每个 bug 打上盲区类型标签"""
        for bug in bugs:
            # 根据 rule_id 映射盲区类型
            bug.blindspot_type = self.RULE_BLINDSPOT_MAP.get(
                bug.rule_id, "boundary"
            )
            # 标记 AI 自审能否发现
            bug.detectable_by_self_review = self.RULE_SELF_REVIEWABLE.get(
                bug.rule_id, False
            )
            bug.self_review_matched = False

    def _mode_a_with_self_review(
        self, bugs: list[Bug], report_path: str, agent: str | None
    ) -> BlindspotReport:
        """模式 A：精确对比自审报告"""
        report = BlindspotReport(
            mode="A",
            mode_description="精确对比 — 已载入 AI 自审报告",
            self_review_available=True,
            self_review_agent=agent,
        )

        # 解析自审报告
        parsed = self._parse_self_review(report_path, agent)
        report.total_self_review_items = parsed["total_items"]
        report.self_review_summary = parsed.get("summary", "")

        # 对比 QVC 结果 vs 自审结果
        self_review_titles = set(parsed.get("issue_titles", []))
        self_review_files = set(parsed.get("files_covered", []))

        for bug in bugs:
            # 检查自审是否报告了同样的问题
            matched = (
                bug.title in self_review_titles
                or any(
                    keyword in bug.title.lower()
                    for keyword in self_review_titles
                )
                or bug.file_path in self_review_files
            )
            bug.self_review_matched = matched
            if not matched:
                report.bugs_not_in_self_review += 1

        report.total_qvc_bugs = len(bugs)
        report.leak_rate = (
            report.bugs_not_in_self_review / max(report.total_qvc_bugs, 1)
        )
        report.blindspot_distribution = self._calc_distribution(bugs)
        return report

    def _mode_b_industry_baseline(self, bugs: list[Bug]) -> BlindspotReport:
        """模式 B：无自审报告 → 行业基准参考"""
        report = BlindspotReport(
            mode="B",
            mode_description="行业基准参考 — 未提供 AI 自审报告，数据基于行业统计",
            self_review_available=False,
        )

        report.total_qvc_bugs = len(bugs)
        # 行业基准：假定 AI 自审只能发现 detectable_by_self_review=True 的问题
        report.bugs_not_in_self_review = sum(
            1 for b in bugs if not b.detectable_by_self_review
        )
        report.leak_rate = (
            report.bugs_not_in_self_review / max(report.total_qvc_bugs, 1)
        )
        report.blindspot_distribution = self._calc_distribution(bugs)
        return report

    def _mode_c_standalone(self) -> BlindspotReport:
        """模式 C：完全脱机（无缺陷）"""
        return BlindspotReport(
            mode="C",
            mode_description="外部监工模式待激活 — 请提供 AI 自审报告以启用精确对比",
            self_review_available=False,
        )

    def _parse_self_review(self, path: str, agent: str | None) -> dict:
        """解析 AI 自审报告"""
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return {"total_items": 0, "issue_titles": [], "files_covered": []}

        result = {
            "total_items": 0,
            "issue_titles": [],
            "files_covered": [],
            "summary": "",
        }

        lines = content.split("\n")

        # 通用解析：提取标题、文件引用
        import re
        for line in lines:
            # 匹配 "Bug #N: title" 或 "问题 N: title"
            m = re.search(r"(?:Bug|问题|Issue|缺陷)\s*[#＃]\s*\d+\s*[:：]\s*(.+)", line, re.I)
            if m:
                result["issue_titles"].append(m.group(1).strip().lower())

            # 匹配文件路径
            m = re.search(r"`([^`]+\.(?:py|js|ts|jsx|tsx))`", line)
            if m:
                result["files_covered"].append(m.group(1))

            # 提取总结段落
            if "通过" in line or "pass" in line.lower() or "无问题" in line or "no issue" in line.lower():
                result["summary"] += line.strip() + " "

        result["total_items"] = len(result["issue_titles"])
        result["summary"] = result["summary"].strip() or "(未提取到自审摘要)"

        return result

    def _calc_distribution(self, bugs: list[Bug]) -> dict[str, int]:
        """计算盲区分布"""
        dist: dict[str, int] = {}
        for bug in bugs:
            bt = bug.blindspot_type or "boundary"
            dist[bt] = dist.get(bt, 0) + 1
        return dict(sorted(dist.items(), key=lambda x: -x[1]))

    @classmethod
    def get_blindspot_label(cls, blindspot_type: str) -> str:
        """获取盲区类型的中文标签"""
        return cls.BLINDSPOT_DEFINITIONS.get(blindspot_type, {}).get("label", blindspot_type)

    @classmethod
    def get_blindspot_desc(cls, blindspot_type: str) -> str:
        """获取盲区类型的描述"""
        return cls.BLINDSPOT_DEFINITIONS.get(blindspot_type, {}).get("desc", "")
