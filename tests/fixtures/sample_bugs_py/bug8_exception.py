"""模拟异常处理缺陷"""


def risky_operation_1(data):
    """BUG: 裸 except + 静默吞没"""
    try:
        result = data["key"]
        return int(result)
    except:  # 裸 except
        pass  # 静默吞没


def risky_operation_2(data):
    """BUG: 异常转为空返回"""
    try:
        return data["key"].split(",")
    except KeyError:
        return []  # 调用方无法区分"key不存在"和"key存在但值为空"


def safe_operation(data):
    """正确做法"""
    if "key" not in data:
        raise ValueError("Missing required key")
    return data["key"].split(",")
