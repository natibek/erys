# Copyright 2025 Nathnael (Nati) Bekele
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import deque
from typing import Any
from threading import Condition


class Queue:
    """Custom thread safe queue to use for producer/consumer code cell execution."""

    def __init__(self) -> None:
        self.queue = deque()
        self.condition = Condition()

    def enqueue(self, val: Any) -> None:
        """Enqueue element to the queue.

        Args:
            val: element to enqueue
        """
        with self.condition:
            self.queue.append(val)
            self.condition.notify()

    def dequeue(self) -> Any:
        """Dequeue element from the queue.

        Returns dequeued element.
        """
        with self.condition:
            if not self.queue:
                self.condition.wait()
            return self.queue.popleft()

    def clear(self) -> list[Any]:
        """Clear queue and return previous elements.

        Returns elements of the queue before clearing.
        """
        with self.condition:
            elements = list(self.queue)
            self.queue.clear()
            return elements

    def empty(self) -> bool:
        """Returns True if the queue is empty."""
        with self.condition:
            return not self.queue

    def push_left(self, val: Any) -> None:
        """Add element to the begining of the queue.

        Args:
            val: element to add.
        """
        with self.condition:
            self.queue.appendleft(val)
