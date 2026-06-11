"""模拟 Bug #6：依赖链断裂导致无输出"""


def ceo_aggregate(sub_reports: list):
    """汇总子报告 —— BUG：所有子报告因上游 bug 可能全部为空"""
    
    if not sub_reports:
        # BUG: 返回空，上游调用方未处理此情况
        return {"summary": "", "details": []}
    
    # 如果 sub_reports 全是因上游错误产生的空对象
    valid_reports = [r for r in sub_reports if r.get("reports")]
    if not valid_reports:
        # BUG: CEO 报告产出为空，但未向用户提示原因
        return {"summary": "无有效报告", "details": []}
    
    return {"summary": "汇总完成", "details": valid_reports}
