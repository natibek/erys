from collections import deque
from typing import Any
from threading import Lock, Condition

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