"""模拟 Bug #10：脆弱的正则解析"""

import re


def parse_audit_data(markdown_text: str):
    """从 markdown 文本中解析审计数据 —— BUG：依赖正则，AI格式稍变即失效"""
    
    # BUG: 正则匹配非结构化输出，格式变化即失效
    audit_pattern = re.compile(r"\*\*(\w+)\*\*:\s*(\w+)")
    results = {}
    
    for match in audit_pattern.finditer(markdown_text):
        key = match.group(1)
        value = match.group(2)
        results[key] = value
    
    return results


# 当 AI 输出格式改变时，正则全部失效：
# 之前： **status**: completed
# 之后： - Status: completed  (正则不再匹配)
