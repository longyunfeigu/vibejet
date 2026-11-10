# input: OffsetTracker + 可手动拨动的假时钟（纯状态，不需要 aiokafka）
# output: 批量提交簿记测试：下一位点跟踪、按条数/按间隔到期、每次尝试重新计批（失败后按间隔重试而不是每条都试）、提交成功后的增量、按分区筛选与遗忘
# pos: 后端测试 - Kafka 消费位点批量提交时机的确定性验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
from __future__ import annotations

from infrastructure.external.messaging.providers.aiokafka._offsets import OffsetTracker


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def make_tracker(every_n: int = 3, interval_ms: int = 1_000) -> tuple[OffsetTracker, FakeClock]:
    clock = FakeClock()
    return OffsetTracker(every_n, interval_ms, clock=clock), clock


def test_tracks_the_next_offset_per_partition() -> None:
    tracker, _ = make_tracker()

    tracker.processed("orders", 0, 5)
    tracker.processed("orders", 0, 6)
    tracker.processed("orders", 1, 9)

    assert tracker.next_offsets == {("orders", 0): 7, ("orders", 1): 10}
    assert tracker.uncommitted() == {("orders", 0): 7, ("orders", 1): 10}
    assert tracker.uncommitted([("orders", 1), ("orders", 4)]) == {("orders", 1): 10}


def test_commit_is_due_after_every_n_records() -> None:
    tracker, _ = make_tracker(every_n=3)

    tracker.processed("orders", 0, 0)
    tracker.processed("orders", 0, 1)
    assert not tracker.commit_due()

    tracker.processed("orders", 0, 2)
    assert tracker.commit_due()


def test_commit_is_due_after_the_interval_only_with_uncommitted_offsets() -> None:
    tracker, clock = make_tracker(every_n=100, interval_ms=1_000)

    clock.now += 2
    assert not tracker.commit_due()  # 间隔到了，但没有要提交的

    tracker.processed("orders", 0, 0)
    assert tracker.commit_due()


def test_each_attempt_starts_a_new_batch_so_a_failure_is_retried_per_interval() -> None:
    tracker, clock = make_tracker(every_n=2, interval_ms=1_000)
    tracker.processed("orders", 0, 0)
    tracker.processed("orders", 0, 1)
    assert tracker.commit_due()

    tracker.attempted()  # 这次提交失败：不调用 mark_committed

    assert tracker.uncommitted() == {("orders", 0): 2}
    tracker.processed("orders", 0, 2)
    assert not tracker.commit_due()  # 不是每来一条就重试
    clock.now += 1
    assert tracker.commit_due()  # 下一个间隔再试


def test_committed_offsets_drop_out_until_the_partition_advances() -> None:
    tracker, _ = make_tracker()
    tracker.processed("orders", 0, 4)
    tracker.processed("orders", 1, 8)

    tracker.mark_committed({("orders", 0): 5, ("orders", 1): 9})
    assert tracker.uncommitted() == {}

    tracker.processed("orders", 1, 9)
    assert tracker.uncommitted() == {("orders", 1): 10}


def test_forget_drops_next_and_committed_offsets() -> None:
    tracker, _ = make_tracker()
    tracker.processed("orders", 0, 4)
    tracker.mark_committed({("orders", 0): 5})

    tracker.forget([("orders", 0)])
    tracker.processed("orders", 0, 4)  # 重新分配回来后从同一位点继续

    assert tracker.uncommitted() == {("orders", 0): 5}
