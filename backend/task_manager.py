"""
简单内存任务管理器（无需 celery，适合桌面 App）
"""
import uuid
from enum import Enum
from typing import Any
from datetime import datetime


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Task:
    def __init__(self, task_id: str, description: str = ""):
        self.id = task_id
        self.description = description
        self.status: TaskStatus = TaskStatus.PENDING
        self.result: Any = None
        self.error: str = ""
        self.progress: int = 0    # 0~100
        self.total: int = 0       # 总数
        self.current: int = 0       # 当前处理数
        self.created_at: str = datetime.now().strftime("%H:%M:%S")

    def update(self, status: TaskStatus = None, progress: int = None,
               current: int = None, total: int = None,
               result: Any = None, error: str = None):
        if status is not None:
            self.status = status
        if progress is not None:
            self.progress = progress
        if current is not None:
            self.current = current
        if total is not None:
            self.total = total
        if result is not None:
            self.result = result
        if error is not None:
            self.error = error

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress,
            "total": self.total,
            "current": self.current,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
        }


# 全局任务存储（进程内内存）
_tasks: dict[str, Task] = {}


def create_task(description: str = "") -> Task:
    task_id = str(uuid.uuid4())[:8]
    task = Task(task_id, description)
    _tasks[task_id] = task
    return task


def get_task(task_id: str) -> Task | None:
    return _tasks.get(task_id)


def remove_task(task_id: str):
    _tasks.pop(task_id, None)
