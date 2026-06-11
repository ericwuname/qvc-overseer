"""Markdown 报告生成器 V3 — 四层结构 + 外部监工摘要 + 自检声明"""

from pathlib import Path
from datetime import datetime

from qvc import __version__
from qvc.models.report import Report
from qvc.models.bug import Severity
from .base import BaseReporter




class AIFixPromptGenerator:
    """AI fix instruction generator for turning QVC reports into AI-consumable task blocks"""

    MIN_CONFIDENCE = 0.70
    MAX_ITEMS = 5

    @classmethod
    def generate(cls, bugs: list, project_name: str = "") -> list[str]:
        """Generate AI-consumable fix instruction block"""
        lines = []

        actionable = [b for b in bugs if b.confidence >= cls.MIN_CONFIDENCE]
        if not actionable:
            return lines

        actionable.sort(key=lambda b: b.confidence, reverse=True)
        actionable = actionable[:cls.MAX_ITEMS]

        target = project_name or "the project"

        lines.append("## AI Fix Instructions")
        lines.append("")
        lines.append(f"> Copy the content below, paste into your AI coding assistant, press Enter.")
        lines.append(f"> The AI will process these {len(actionable)} issues one by one, fix only, no functional changes.")
        lines.append("")
        lines.append(f"Please fix the following {len(actionable)} issues in {target}:")
        lines.append("")

        for i, bug in enumerate(actionable, 1):
            lines.append(f"### Task {i} [{bug.confidence:.0%}]: {bug.title}")
            lines.append("")
            lines.append(f"- **File**: {bug.file_path}:{bug.line_start}")
            lines.append(f"- **Issue**: {bug.description}")
            if bug.fix_suggestion:
                lines.append(f"- **Fix**: {bug.fix_suggestion}")
            if bug.code_snippet:
                lines.append(f"- **Code**:")
                lines.append("")
                lines.append("`")
                lines.append(bug.code_snippet)
                lines.append("`")
            lines.append("")

        return lines

class MarkdownReporter(BaseReporter):
    """Markdown 格式报告生成器（V3 外部监工版）"""

    def generate(self, report: Report, output_path: Path | None = None, blindspot_report = None) -> str:
        lines = []
        total = max(report.total_bugs, 1)

        # ═══ 头部 ═══
        lines.append(f"# {report.project_name} — 代码缺陷审查报告")
        lines.append("")
        lines.append(f"> **审查日期**：{report.generated_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"> **审查工具**：QVC v{__version__} — 外部监工视角")
        lines.append(f"> **扫描文件数**：{report.scan_summary.total_files}")
        lines.append(f"> **代码总行数**：{report.scan_summary.total_lines:,}")
        if report.scan_summary.languages:
            lines.append(f"> **语言**：{', '.join(report.scan_summary.languages[:8])}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ═══ V3.0 第零层：外部监工摘要 ═══
        if blindspot_report:
            lines.extend(self._format_blindspot_summary(blindspot_report, report))
        else:
            lines.extend(self._format_basic_summary(report))
        lines.append("---")
        lines.append("")

        # ═══ 第一层：高置信度问题 ═══
        high_conf = [b for b in report.bugs if b.confidence >= 0.9]
        if high_conf:
            lines.append("## 🔥 高置信度问题 — 建议立即处理")
            lines.append("")
            for i, bug in enumerate(high_conf[:10], 1):
                lines.extend(self._format_bug(bug, i, highlight=True))
            if len(high_conf) > 10:
                lines.append(f"> ... 还有 {len(high_conf) - 10} 条高置信度问题")
                lines.append("")
        else:
            lines.append("## 🔥 高置信度问题 — 无")
            lines.append("")
            lines.append("> 本次扫描未发现置信度 ≥ 90% 的问题。")
            lines.append("")

        lines.append("---")
        lines.append("")

        # ═══ 第二层：聚合摘要 ═══
        lines.append("## 📋 聚合摘要")
        lines.append("")
        from collections import defaultdict
        groups = defaultdict(list)
        for bug in report.bugs:
            groups[bug.category.label].append(bug)
        lines.append("| 类别 | 数量 | 最高置信度 | 操作建议 |")
        lines.append("|------|------|-----------|---------|")
        for cat, bugs in sorted(groups.items(), key=lambda x: -len(x[1])):
            max_conf = max(b.confidence for b in bugs)
            if max_conf >= 0.9:
                action = "🔴 立即处理"
            elif max_conf >= 0.6:
                action = "🟡 优先审查"
            else:
                action = "🔵 建议关注"
            lines.append(f"| {cat} | {len(bugs)} | {max_conf:.0%} | {action} |")
        lines.append("")

        lines.append("---")
        lines.append("")

        # ═══ 第三层：致命+严重详览 ═══
        fatal = report.fatal_bugs
        severe = report.severe_bugs
        if fatal or severe:
            lines.append("## 📊 致命 & 严重缺陷详览")
            lines.append("")
            for i, bug in enumerate(fatal + severe, 1):
                lines.extend(self._format_bug(bug, i, highlight=(bug.severity == Severity.FATAL)))
            lines.append("")

        # ═══ 完整统计 ═══
        lines.append("---")
        lines.append("")
        lines.append("## 📈 完整统计")
        lines.append("")
        lines.append("### 严重度分布")
        lines.append("")
        lines.append("| 严重度 | 数量 | 占比 |")
        lines.append("|--------|------|------|")
        for sev in Severity:
            count = report.by_severity.get(sev.name, 0)
            pct = count / total * 100
            lines.append(f"| {sev.label} | {count} | {pct:.1f}% |")
        lines.append(f"| **合计** | **{report.total_bugs}** | **100%** |")
        lines.append("")

        if report.by_root_cause:
            lines.append("### 根因分布")
            lines.append("")
            lines.append("| 根因 | 数量 |")
            lines.append("|------|------|")
            for cause, count in sorted(report.by_root_cause.items(), key=lambda x: -x[1]):
                if count > 0:
                    lines.append(f"| {cause} | {count} |")
            lines.append("")

        # ═══ 一般 & 建议级完整列表 ═══
        moderate = [b for b in report.bugs if b.severity == Severity.MODERATE]
        minor = [b for b in report.bugs if b.severity == Severity.MINOR]
        other = moderate + minor
        if other:
            lines.append("---")
            lines.append("")
            lines.append("## 📝 一般 & 建议级（完整列表）")
            lines.append("")
            lines.append("| # | 严重度 | 文件 | 行号 | 标题 | 置信度 | 盲区 |")
            lines.append("|---|--------|------|------|------|--------|------|")
            for i, bug in enumerate(other, 1):
                file_short = Path(bug.file_path).name
                bt_label = bug.blindspot_type or "-"
                lines.append(f"| {i} | {bug.severity.label} | {file_short} | {bug.line_start} | {bug.title} | {bug.confidence:.0%} | {bt_label} |")
            lines.append("")

        # ═══ 报告自检声明 ═══
        lines.append("---")
        lines.append("")
        lines.append("## 🔍 报告自检声明")
        lines.append("")
        lines.append(f"- 扫描范围：{report.scan_summary.total_files} 个文件（已排除 node_modules/.git/fixtures/_removed 等）")
        lines.append("- 报告编码：UTF-8 without BOM")
        lines.append("- 本报告由 QVC v{__version__} 生成并自检")
        lines.append("- 分层策略：L1 确定性(95%+) / L2 模式匹配(60-85%) / L3 启发式(20-50%)")
        if blindspot_report:
            lines.append(f"- 外部监工模式：{blindspot_report.mode_description}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"> **报告生成时间**：{report.generated_at.isoformat()}")
        lines.append(f"> **审查工具**：QVC v{__version__} — 外部监工视角")
        lines.append("")

        content = "\n".join(lines)

        if output_path:
            output_path.write_text(content, encoding="utf-8")

        return content

    # ═══════════════════════════════════════════════════════
    # V3.0 新增：外部监工摘要格式化
    # ═══════════════════════════════════════════════════════

    def _format_blindspot_summary(self, blindspot_report, report: Report) -> list[str]:
        """格式化外部监工摘要（第零层）— V3.0 核心"""
        lines = []
        br = blindspot_report

        lines.append("## 👁 外部监工摘要")
        lines.append("")

        # 对比结果
        if br.mode == "A":
            lines.append("### 对比结果")
            lines.append("")
            lines.append("| 指标 | 数值 |")
            lines.append("|------|------|")
            lines.append(f"| AI Agent 自审 | {br.self_review_summary[:80] or '已提供自审报告'} |")
            lines.append(f"| QVC 外部审查发现 | {br.total_qvc_bugs} 条缺陷 |")
            lines.append(f"| **AI 自审未发现率** | **{br.leak_rate:.0%}**（{br.bugs_not_in_self_review}/{br.total_qvc_bugs} 条未被自审批出）|")
            lines.append("")
            lines.append(f"> 💡 AI 自审未发现率 = QVC 发现但 AI 自审未发现的问题比例。{br.mode_description}。")
        elif br.mode == "B":
            lines.append("### 行业基准参考")
            lines.append("")
            lines.append("| 指标 | 数值 |")
            lines.append("|------|------|")
            lines.append(f"| QVC 外部审查发现 | {br.total_qvc_bugs} 条缺陷 |")
            lines.append(f"| 预估AI 自审未发现率 | **{br.leak_rate:.0%}**（基于行业统计）|")
            lines.append("")
            lines.append(f"> ⚠️ 未提供 AI 自审报告。以上数据为行业基准估算（非 QVC 自身漏报）。")
            lines.append(f"> 传入 `--self-review-report agent-review.md` 获取精确对比。")
        else:
            lines.append("### 外部监工模式待激活")
            lines.append("")
            lines.append("> 本次扫描未发现缺陷，或外部监工模式尚未启用。")
            lines.append(f"> 传入 `--self-review-report <file>` 激活精确对比模式。")
            lines.append("")

        # 盲区分布
        if br.blindspot_distribution:
            lines.append("### 盲区分布")
            lines.append("")
            lines.append("| 盲区类型 | 发现数 | 说明 |")
            lines.append("|---------|--------|------|")
            from qvc.analyzers.blindspot_analyzer import BlindspotAnalyzer
            for bt, count in br.blindspot_distribution.items():
                label = BlindspotAnalyzer.get_blindspot_label(bt)
                desc = BlindspotAnalyzer.get_blindspot_desc(bt)
                lines.append(f"| 🧠 {label} | {count} | {desc} |")
            lines.append("")

        lines.append("> QVC 作为外部监工，不共享 AI Agent 的认知闭环。Agent 自审沿生成链检查，QVC 从外部交叉验证。")
        lines.append("")

        # V5: AI task dispatcher - add copy-paste fix instructions at report bottom
        if report.bugs:
            fix_lines = AIFixPromptGenerator.generate(report.bugs, report.project_name)
            if fix_lines:
                lines.append("---")
                lines.append("")
                lines.extend(fix_lines)
                lines.append("")
        return lines

    def _format_basic_summary(self, report: Report) -> list[str]:
        """V2 兼容：基础摘要（无盲区数据时）"""
        lines = []
        high_conf = [b for b in report.bugs if b.confidence >= 0.9]
        mid_conf = [b for b in report.bugs if 0.6 <= b.confidence < 0.9]
        low_conf = [b for b in report.bugs if b.confidence < 0.6]

        lines.append("## 📊 扫描摘要")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 高置信度问题（≥90%） | {len(high_conf)} |")
        lines.append(f"| 中置信度问题（60-89%） | {len(mid_conf)} |")
        lines.append(f"| 低置信度建议（<60%） | {len(low_conf)} |")
        lines.append(f"| 扫描候选总数 | {report.total_bugs} |")
        lines.append("")
        lines.append("> QVC 只报告问题，不修改代码。它是一个外部视角——不受 AI Agent 自审盲区影响。")
        lines.append("")

        return lines

    def _format_bug(self, bug, index: int, highlight: bool = False) -> list[str]:
        prefix = "🔥 " if highlight else ""
        lines = []
        lines.append(f"#### {prefix}Bug #{index}: {bug.title}")
        lines.append("")
        lines.append(f"- **文件**：`{bug.file_path}:{bug.line_start}`")
        lines.append(f"- **严重度**：{bug.severity.label}")
        lines.append(f"- **分类**：{bug.category.label}")
        lines.append(f"- **置信度**：{bug.confidence:.0%}")
        if bug.blindspot_type:
            from qvc.analyzers.blindspot_analyzer import BlindspotAnalyzer
            label = BlindspotAnalyzer.get_blindspot_label(bug.blindspot_type)
            lines.append(f"- **盲区类型**：{label}")
            lines.append(f"- **AI 可自检**：{'是' if bug.detectable_by_self_review else '否（结构性盲区）'}")
        if bug.root_cause:
            lines.append(f"- **根因**：{bug.root_cause.value}")
        lines.append(f"- **描述**：{bug.description}")
        if bug.code_snippet:
            lines.append(f"- **代码片段**：")
            lines.append("")
            lines.append(f"```")
            lines.append(bug.code_snippet)
            lines.append(f"```")
        if bug.fix_suggestion:
            lines.append(f"- **建议**：{bug.fix_suggestion}")
        lines.append("")
        return lines

    def get_extension(self) -> str:
        return ".md"
