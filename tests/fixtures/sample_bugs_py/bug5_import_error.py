"""模拟 Bug #5：导入路径错误"""

# BUG: 试图导入不存在的函数
# from executor_service import execute_group_task  # ImportError

# 或者在 __init__.py 中未正确导出
# __all__ = ["execute_single_task"]  # 但缺少 execute_group_task


def broken_import_example():
    try:
        from nonexistent_module import some_function
    except ImportError:
        pass  # BUG: 静默吞没导入错误
