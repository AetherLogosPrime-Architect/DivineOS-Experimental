"""Tests for TaskQueue module."""

from task_queue import Task, TaskQueue, Priority, run_pipeline, merge_task_stats


# --- Helper functions for tests ---


def success_fn():
    return "done"


def failing_fn():
    raise ValueError("task failed")


def add_one(x):
    return x + 1


def double(x):
    return x * 2


def stringify(x):
    return str(x)


def sometimes_fails(counter=[0]):
    """Fails the first 2 times, succeeds on 3rd."""
    counter[0] += 1
    if counter[0] % 3 != 0:
        raise RuntimeError(f"Attempt {counter[0]} failed")
    return f"success on attempt {counter[0]}"


# --- Task Tests ---


class TestTask:
    def test_create_task(self):
        task = Task(name="test", fn=success_fn)
        assert task.name == "test"
        assert task.priority == Priority.NORMAL
        assert task.max_retries == 3
        assert task._attempts == 0

    def test_task_id_is_deterministic(self):
        t1 = Task(name="same_name", fn=success_fn)
        t2 = Task(name="same_name", fn=failing_fn)
        assert t1.task_id == t2.task_id

    def test_different_names_different_ids(self):
        t1 = Task(name="alpha", fn=success_fn)
        t2 = Task(name="beta", fn=success_fn)
        assert t1.task_id != t2.task_id

    def test_can_retry_initially_true(self):
        task = Task(name="test", fn=success_fn, max_retries=3)
        assert task.can_retry is True

    def test_can_retry_after_max(self):
        task = Task(name="test", fn=success_fn, max_retries=2)
        task._attempts = 2
        assert task.can_retry is False

    def test_backoff_increases_exponentially(self):
        task = Task(name="test", fn=success_fn)
        task._attempts = 0
        assert task.backoff_seconds == 1  # 2^0
        task._attempts = 1
        assert task.backoff_seconds == 2  # 2^1
        task._attempts = 3
        assert task.backoff_seconds == 8  # 2^3


# --- TaskQueue Basic Tests ---


class TestTaskQueueBasic:
    def test_add_task(self):
        q = TaskQueue()
        task = Task(name="test", fn=success_fn)
        assert q.add_task(task) is True
        assert len(q._queue) == 1

    def test_add_duplicate_rejected(self):
        q = TaskQueue()
        t1 = Task(name="test", fn=success_fn)
        t2 = Task(name="test", fn=success_fn)
        q.add_task(t1)
        assert q.add_task(t2) is False

    def test_queue_full_rejected(self):
        q = TaskQueue(max_queue_size=2)
        q.add_task(Task(name="a", fn=success_fn))
        q.add_task(Task(name="b", fn=success_fn))
        assert q.add_task(Task(name="c", fn=success_fn)) is False

    def test_priority_ordering(self):
        q = TaskQueue()
        q.add_task(Task(name="low", fn=success_fn, priority=Priority.LOW))
        q.add_task(Task(name="critical", fn=success_fn, priority=Priority.CRITICAL))
        q.add_task(Task(name="normal", fn=success_fn, priority=Priority.NORMAL))
        assert q._queue[0].name == "critical"
        assert q._queue[1].name == "normal"
        assert q._queue[2].name == "low"

    def test_peek_returns_highest_priority(self):
        q = TaskQueue()
        q.add_task(Task(name="low", fn=success_fn, priority=Priority.LOW))
        q.add_task(Task(name="high", fn=success_fn, priority=Priority.HIGH))
        peeked = q.peek()
        assert peeked.name == "high"
        assert len(q._queue) == 2  # peek doesn't remove

    def test_clear(self):
        q = TaskQueue()
        q.add_task(Task(name="a", fn=success_fn))
        q.add_task(Task(name="b", fn=success_fn))
        removed = q.clear()
        assert removed == 2
        assert len(q._queue) == 0

    def test_cancel_task(self):
        q = TaskQueue()
        q.add_task(Task(name="keep", fn=success_fn))
        q.add_task(Task(name="remove", fn=success_fn))
        assert q.cancel_task("remove") is True
        assert len(q._queue) == 1
        assert q._queue[0].name == "keep"

    def test_cancel_nonexistent(self):
        q = TaskQueue()
        assert q.cancel_task("ghost") is False


# --- Execution Tests ---


class TestTaskExecution:
    def test_execute_success(self):
        q = TaskQueue()
        q.add_task(Task(name="test", fn=success_fn))
        result = q.execute_next()
        assert result.success is True
        assert result.value == "done"

    def test_execute_failure_exhausts_retries(self):
        q = TaskQueue()
        q.add_task(Task(name="fail", fn=failing_fn, max_retries=1))
        result = q.execute_next()
        assert result.success is False
        assert "task failed" in result.error

    def test_execute_all(self):
        q = TaskQueue()
        q.add_task(Task(name="a", fn=success_fn))
        q.add_task(Task(name="b", fn=success_fn))
        q.add_task(Task(name="c", fn=success_fn))
        results = q.execute_all()
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_execute_empty_queue(self):
        q = TaskQueue()
        assert q.execute_next() is None

    def test_task_with_args(self):
        def add(a, b):
            return a + b

        q = TaskQueue()
        q.add_task(Task(name="add", fn=add, args=(3, 4)))
        result = q.execute_next()
        assert result.success is True
        assert result.value == 7

    def test_task_with_kwargs(self):
        def greet(name="world"):
            return f"hello {name}"

        q = TaskQueue()
        q.add_task(Task(name="greet", fn=greet, kwargs={"name": "andrew"}))
        result = q.execute_next()
        assert result.value == "hello andrew"

    def test_completed_task_blocks_readd(self):
        q = TaskQueue()
        q.add_task(Task(name="once", fn=success_fn))
        q.execute_next()
        # Try to add same task again after completion
        assert q.add_task(Task(name="once", fn=success_fn)) is False

    def test_get_tasks_by_priority(self):
        q = TaskQueue()
        q.add_task(Task(name="a", fn=success_fn, priority=Priority.HIGH))
        q.add_task(Task(name="b", fn=success_fn, priority=Priority.LOW))
        q.add_task(Task(name="c", fn=success_fn, priority=Priority.HIGH))
        high = q.get_tasks_by_priority(Priority.HIGH)
        assert len(high) == 2


# --- Stats Tests ---


class TestStats:
    def test_initial_stats(self):
        q = TaskQueue()
        stats = q.get_stats()
        assert stats["queue_size"] == 0
        assert stats["total_executed"] == 0
        assert stats["success_rate"] == 0

    def test_stats_after_success(self):
        q = TaskQueue()
        q.add_task(Task(name="test", fn=success_fn))
        q.execute_next()
        stats = q.get_stats()
        assert stats["succeeded"] == 1
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0

    def test_stats_after_failure(self):
        q = TaskQueue()
        q.add_task(Task(name="fail", fn=failing_fn, max_retries=1))
        q.execute_next()
        stats = q.get_stats()
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.0

    def test_history_limit(self):
        q = TaskQueue()
        for i in range(20):
            q.add_task(Task(name=f"task_{i}", fn=success_fn))
        q.execute_all()
        last_5 = q.get_history(last_n=5)
        assert len(last_5) == 5

    def test_add_batch(self):
        q = TaskQueue()
        tasks = [
            Task(name="a", fn=success_fn),
            Task(name="b", fn=success_fn),
            Task(name="a", fn=success_fn),  # duplicate
        ]
        results = q.add_batch(tasks)
        assert results["a"] is True
        assert results["b"] is True
        # Second "a" should be rejected as duplicate
        assert len(q._queue) == 2


# --- Pipeline Tests ---


class TestPipeline:
    def test_simple_pipeline(self):
        success, result, errors = run_pipeline([add_one, double, stringify], data=5)
        assert success is True
        assert result == "12"  # (5+1)*2 = 12
        assert errors == []

    def test_pipeline_with_failure(self):
        def explode(x):
            raise RuntimeError("boom")

        success, result, errors = run_pipeline([add_one, explode, stringify], data=5)
        assert success is False
        assert len(errors) == 1
        assert "Step 1" in errors[0]

    def test_empty_pipeline(self):
        success, result, errors = run_pipeline([], data="unchanged")
        assert success is True
        assert result == "unchanged"


# --- Merge Stats Tests ---


class TestMergeStats:
    def test_merge_two_queues(self):
        q1 = TaskQueue()
        q2 = TaskQueue()
        q1.add_task(Task(name="a", fn=success_fn))
        q2.add_task(Task(name="b", fn=success_fn))
        q1.execute_all()
        q2.execute_all()
        merged = merge_task_stats(q1.get_stats(), q2.get_stats())
        assert merged["succeeded"] == 2
        assert merged["total_executed"] == 2

    def test_merge_preserves_success_rate(self):
        """After merging stats from queues with different success rates,
        the merged success_rate should reflect the combined ratio."""
        q1 = TaskQueue()
        q2 = TaskQueue()
        # q1: 1 success
        q1.add_task(Task(name="ok", fn=success_fn))
        q1.execute_all()
        # q2: 1 failure
        q2.add_task(Task(name="bad", fn=failing_fn, max_retries=1))
        q2.execute_all()
        merged = merge_task_stats(q1.get_stats(), q2.get_stats())
        assert merged["success_rate"] == 0.5  # 1 success, 1 failure
