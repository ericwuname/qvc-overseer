"""模拟 API 签名不匹配缺陷"""


def process_task(task_id: str, user_name: str, priority: int = 1):
    """需要 2 个必需参数 + 1 个可选参数"""
    return f"Processing {task_id} for {user_name} with priority {priority}"


def trigger_task():
    # BUG: 只传了 1 个参数，缺少 user_name
    result = process_task("TASK-001")  # TypeError: missing 1 required positional argument
    return result


def trigger_task_too_many():
    # BUG: 传了 4 个参数，最多接受 3 个
    result = process_task("TASK-001", "Alice", 2, "extra")  # TypeError: too many arguments
    return result
