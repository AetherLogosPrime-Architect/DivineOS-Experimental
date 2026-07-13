"""
TaskQueue: A priority-based task scheduler with retry logic.

Supports:
- Adding tasks with priority levels (1=highest, 5=lowest)
- Automatic retry with exponential backoff on failure
- Task deduplication by name
- Execution history tracking
- Statistics reporting
"""

from __future__ import annotations

import time
import hashlib
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable
from collections import defaultdict


class Priority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class Task:
    name: str
    fn: Callable[..., Any]
    priority: Priority = Priority.NORMAL
    max_retries: int = 3
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    _attempts: int = 0
    _last_error: str | None = None
    _created_at: float = field(default_factory=time.time)

    @property
    def task_id(self) -> str:
        """Generate unique ID from task name."""
        return hashlib.md5(self.name.encode()).hexdigest()

    @property
    def can_retry(self) -> bool:
        return self._attempts < self.max_retries

    @property
    def backoff_seconds(self) -> float:
        """Exponential backoff: 2^attempts seconds."""
        return 2**self._attempts


class TaskResult:
    def __init__(self, task: Task, success: bool, value: Any = None, error: str | None = None):
        self.task = task
        self.success = success
        self.value = value
        self.error = error
        self.timestamp = time.time()
        self.duration = 0.0


class TaskQueue:
    def __init__(self, max_queue_size: int = 100, sleep_fn: Callable[[float], None] = time.sleep):
        self._queue: list[Task] = []
        self._history: list[TaskResult] = []
        self._max_size = max_queue_size
        self._running = False
        self._completed_names: set[str] = set()
        self._stats = defaultdict(int)
        self._sleep_fn = sleep_fn

    def add_task(self, task: Task) -> bool:
        """Add a task to the queue. Returns False if queue is full or task is duplicate."""
        # Check for duplicates
        if self._is_duplicate(task):
            return False

        # Check queue capacity
        if len(self._queue) >= self._max_size:
            return False

        self._queue.append(task)
        self._sort_queue()
        self._stats["tasks_added"] += 1
        return True

    def add_batch(self, tasks: list[Task]) -> dict[str, bool]:
        """Add multiple tasks. Returns dict of name -> success."""
        results = {}
        for task in tasks:
            if task.name not in results:
                results[task.name] = self.add_task(task)
        return results

    def execute_next(self) -> TaskResult | None:
        """Execute the highest priority task in the queue."""
        if not self._queue:
            return None

        task = self._queue.pop(0)
        return self._execute_task(task)

    def execute_all(self) -> list[TaskResult]:
        """Execute all tasks in priority order."""
        results = []
        self._running = True

        while self._queue and self._running:
            result = self.execute_next()
            if result:
                results.append(result)

        self._running = False
        return results

    def cancel_task(self, task_name: str) -> bool:
        """Remove a task from the queue by name."""
        for i, task in enumerate(self._queue):
            if task.name == task_name:
                del self._queue[i]
                self._stats["tasks_cancelled"] += 1
                return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Return execution statistics."""
        total = self._stats["tasks_succeeded"] + self._stats["tasks_failed"]
        success_rate = self._stats["tasks_succeeded"] / total if total else 0

        avg_duration = 0.0
        if self._history:
            avg_duration = sum(r.duration for r in self._history) / len(self._history)

        return {
            "queue_size": len(self._queue),
            "total_executed": total,
            "succeeded": self._stats["tasks_succeeded"],
            "failed": self._stats["tasks_failed"],
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "retries": self._stats["total_retries"],
            "tasks_added": self._stats["tasks_added"],
            "tasks_cancelled": self._stats["tasks_cancelled"],
        }

    def get_history(self, last_n: int = 10) -> list[TaskResult]:
        """Return the last N results."""
        return self._history[-last_n:]

    def clear(self) -> int:
        """Clear the queue. Returns number of tasks removed."""
        count = len(self._queue)
        self._queue.clear()
        return count

    def peek(self) -> Task | None:
        """Look at the next task without removing it."""
        if self._queue:
            return self._queue[0]
        return None

    def get_tasks_by_priority(self, priority: Priority) -> list[Task]:
        """Get all queued tasks with a specific priority."""
        return [t for t in self._queue if t.priority == priority]

    def _execute_task(self, task: Task) -> TaskResult:
        """Execute a single task with retry logic."""
        start_time = time.time()

        while True:
            task._attempts += 1
            try:
                value = task.fn(*task.args, **task.kwargs)
                result = TaskResult(task, success=True, value=value)
                result.duration = time.time() - start_time
                self._history.append(result)
                self._completed_names.add(task.name)
                self._stats["tasks_succeeded"] += 1
                return result

            except Exception as e:
                task._last_error = str(e)
                self._stats["total_retries"] += 1

                if not task.can_retry:
                    result = TaskResult(task, success=False, error=str(e))
                    result.duration = time.time() - start_time
                    self._history.append(result)
                    self._stats["tasks_failed"] += 1
                    return result

                # Backoff before retry
                self._sleep_fn(task.backoff_seconds)

    def _is_duplicate(self, task: Task) -> bool:
        """Check if a task with the same name is already queued or completed."""
        # Check current queue
        for queued in self._queue:
            if queued.name == task.name:
                return True

        # Check completed tasks
        if task.name in self._completed_names:
            return True

        return False

    def _sort_queue(self) -> None:
        """Sort queue by priority (lowest number = highest priority)."""
        self._queue.sort(key=lambda t: t.priority)


def run_pipeline(steps: list[Callable], data: Any = None) -> tuple[bool, Any, list[str]]:
    """
    Execute a series of functions as a pipeline.
    Each step receives the output of the previous step.
    Returns (success, final_result, errors).
    """
    errors = []
    current = data

    for i, step in enumerate(steps):
        try:
            current = step(current)
        except Exception as e:
            errors.append(f"Step {i}: {str(e)}")
            return (False, current, errors)

    return (True, current, errors)


def merge_task_stats(*stat_dicts: dict[str, Any]) -> dict[str, Any]:
    """Merge statistics from multiple TaskQueue instances."""
    merged = defaultdict(int)

    for stats in stat_dicts:
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                merged[key] += value
            elif key == "success_rate":
                pass  # Recompute below

    # Recompute success rate
    total = merged["succeeded"] + merged["failed"]
    merged["success_rate"] = merged["succeeded"] / total if total else 0.0

    return dict(merged)
