"""后处理器 — 去重聚合 + 严重度归一化 + 降噪"""

from collections import defaultdict
from qvc.models.bug import Bug, Severity

# 目标分布
TARGET_DIST = {
    Severity.FATAL: 0.05,
    Severity.SEVERE: 0.15,
    Severity.MODERATE: 0.35,
    Severity.MINOR: 0.45,
}

# 最低置信度阈值（低于此值的丢弃）
MIN_CONFIDENCE = 0.50


def deduplicate(bugs: list[Bug]) -> list[Bug]:
    """去重聚合：同规则+同类别的缺陷合并"""

    groups = defaultdict(list)
    for bug in bugs:
        # 按 (rule_id, category) 分组
        key = (bug.rule_id, bug.category.name)
        groups[key].append(bug)

    result = []
    for (rule_id, cat), group in groups.items():
        if len(group) == 1:
            result.append(group[0])
        else:
            # 保留置信度最高的作为代表
            rep = max(group, key=lambda b: b.confidence)
            # 修改描述，体现聚合信息
            rep.description = f"[{len(group)} 处] {rep.description}"
            rep.title = f"[{len(group)} 处] {rep.title}"
            # 置信度取最高值
            result.append(rep)

    return result


def normalize_severity(bugs: list[Bug]) -> list[Bug]:
    """严重度归一化：按置信度降序排列，按目标分布重新分配严重度"""

    if not bugs:
        return bugs

    sorted_bugs = sorted(bugs, key=lambda b: -b.confidence)
    total = len(sorted_bugs)

    # 累计分配
    fatal_cut = max(1, int(total * TARGET_DIST[Severity.FATAL]))
    severe_cut = fatal_cut + max(1, int(total * TARGET_DIST[Severity.SEVERE]))
    moderate_cut = severe_cut + max(1, int(total * TARGET_DIST[Severity.MODERATE]))

    for i, bug in enumerate(sorted_bugs):
        if i < fatal_cut and bug.confidence >= 0.90:
            bug.severity = Severity.FATAL
        elif i < severe_cut and bug.confidence >= 0.60:
            bug.severity = Severity.SEVERE
        elif i < moderate_cut and bug.confidence >= 0.30:
            bug.severity = Severity.MODERATE
        else:
            bug.severity = Severity.MINOR

    return sorted_bugs


def filter_noise(bugs: list[Bug], min_confidence: float = MIN_CONFIDENCE) -> list[Bug]:
    """过滤低置信度噪声"""
    return [b for b in bugs if b.confidence >= min_confidence]


def post_process(bugs: list[Bug]) -> list[Bug]:
    """完整后处理流水线：降噪 → 去重 → 归一化"""
    bugs = filter_noise(bugs)
    bugs = deduplicate(bugs)
    bugs = normalize_severity(bugs)
    return bugs