"""模拟 Bug #1：变量 sub_tasks 未定义"""
# 文件：executor_service.py


def execute_single_task(task_id: str):
    """执行单个任务"""
    reports = [f"Report for {task_id}"]
    duration_ms = 1500

    # BUG: sub_tasks 在这里从未定义，但被 return 引用
    return {
        "status": "completed",
        "reports": reports,
        "sub_tasks": sub_tasks,  # <-- NameError: name "sub_tasks" is not defined
        "duration_ms": duration_ms,
    }


def execute_group_task(task_ids: list):
    """执行群组任务 —— sub_tasks 在这里定义"""
    sub_tasks = []
    for tid in task_ids:
        sub_tasks.append(execute_single_task(tid))
    return sub_tasks
