import time
from dataclasses import dataclass
from ipaddress import IPv4Address

MAX_SEQUENCE_ID = 2 ** 16


@dataclass(frozen=True, slots=True)
class PingTask:
    address: IPv4Address
    sequence_id: int
    sent_at: float


class PingTaskPool:
    def __init__(self):
        self._tasks_by_sequence: dict[int, PingTask] = dict()
        self._tasks_by_address: dict[int, PingTask] = dict()
        self._current_sequence_id: int = 0

    def get_task_by_sequence(self, sequence_id: int) -> PingTask | None:
        try:
            return self._tasks_by_sequence[sequence_id]
        except KeyError:
            return None

    def get_task_by_address(self, address: IPv4Address) -> PingTask | None:
        try:
            return self._tasks_by_address[int(address)]
        except KeyError:
            return None

    def _get_increased_sequence_id(self) -> int:
        if MAX_SEQUENCE_ID <= self._current_sequence_id + 1:
            return 0
        else:
            return self._current_sequence_id + 1

    def create_new_task(self, address: IPv4Address) -> PingTask | None:
        task = None

        for _ in range(MAX_SEQUENCE_ID):
            if self.get_task_by_sequence(self._current_sequence_id) is None:
                task = PingTask(address=address, sequence_id=self._current_sequence_id, sent_at=time.time())
                self._tasks_by_sequence[self._current_sequence_id] = task
                self._tasks_by_address[int(task.address)] = task
                break
            self._current_sequence_id = self._get_increased_sequence_id()

        return task

    def pop_task(self, sequence_id: int) -> PingTask | None:
        try:
            task = self._tasks_by_sequence.pop(sequence_id)
            self._tasks_by_address.pop(int(task.address))
            return task
        except KeyError:
            return None
