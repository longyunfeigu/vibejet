# input: 已处理记录的 (topic, partition, offset)、提交尝试与提交成功的位点
# output: OffsetTracker（每个分区下一次要提交的位点 + 批量提交时机：commit_every_n / commit_interval_ms，失败后按间隔重试）, PartitionKey
# owner: unknown
# pos: 基础设施层 - Kafka 消费位点的批量提交簿记（纯状态，不碰 aiokafka）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
from __future__ import annotations

import time
from typing import Callable, Dict, Iterable, Optional, Tuple

PartitionKey = Tuple[str, int]


class OffsetTracker:
    """Next offset to commit per partition, and whether a batched commit is due.

    A record counts once it is fully handled: acked, or requeued to a retry/DLQ topic.
    A commit is due after ``commit_every_n`` records, or once ``commit_interval_ms`` has
    passed since the last attempt while offsets are still uncommitted. Both counters
    restart on every attempt, so a failing commit is retried once per interval instead
    of on every record. The consumer also flushes on revoke and on stop.
    """

    def __init__(
        self,
        commit_every_n: int,
        commit_interval_ms: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._every_n = max(1, commit_every_n)
        self._interval_s = max(0, commit_interval_ms) / 1000
        self._clock = clock
        self.next_offsets: Dict[PartitionKey, int] = {}
        self._committed: Dict[PartitionKey, int] = {}
        self._since_attempt = 0
        self._last_attempt = clock()

    def processed(self, topic: str, partition: int, offset: int) -> None:
        self.next_offsets[(topic, partition)] = offset + 1
        self._since_attempt += 1

    def commit_due(self) -> bool:
        if self._since_attempt >= self._every_n:
            return True
        if self._clock() - self._last_attempt < self._interval_s:
            return False
        return bool(self.uncommitted())

    def attempted(self) -> None:
        """Start a new batch: called on every full commit attempt, successful or not."""
        self._since_attempt = 0
        self._last_attempt = self._clock()

    def uncommitted(self, keys: Optional[Iterable[PartitionKey]] = None) -> Dict[PartitionKey, int]:
        wanted = None if keys is None else set(keys)
        return {
            key: offset
            for key, offset in self.next_offsets.items()
            if self._committed.get(key) != offset and (wanted is None or key in wanted)
        }

    def mark_committed(self, offsets: Dict[PartitionKey, int]) -> None:
        self._committed.update(offsets)

    def forget(self, keys: Iterable[PartitionKey]) -> None:
        for key in keys:
            self.next_offsets.pop(key, None)
            self._committed.pop(key, None)
