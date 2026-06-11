"""模拟 Bug #2：track_event 参数不匹配"""


def track_event(event_type: str, extract_data=None):
    """装饰器工厂函数 —— 返回装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            print(f"[{event_type}] {func.__name__} completed")
            return result
        return wrapper
    return decorator


# 正确用法：@track_event("task_executed")
# 错误用法：直接当普通函数调用，传入了4个参数
# 下面这行会导致 TypeError
# track_event("task_executed", task_id, user_id, duration)  # BUG: 4 args given, expects 1-2
