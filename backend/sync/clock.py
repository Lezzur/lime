"""
Hybrid Logical Clock (HLC) for causal ordering across devices.

Combines physical wall-clock time with a logical counter to provide
monotonically increasing timestamps without requiring NTP synchronization.
Format: "{wall_ms}:{counter:04d}:{node_id}"
"""

import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class HLCTimestamp:
    wall_ms: int
    counter: int
    node_id: str

    def __str__(self) -> str:
        return f"{self.wall_ms}:{self.counter:04d}:{self.node_id}"

    @classmethod
    def from_string(cls, s: str) -> "HLCTimestamp":
        parts = s.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid HLC timestamp: {s}")
        return cls(
            wall_ms=int(parts[0]),
            counter=int(parts[1]),
            node_id=parts[2],
        )

    def __gt__(self, other: "HLCTimestamp") -> bool:
        if self.wall_ms != other.wall_ms:
            return self.wall_ms > other.wall_ms
        if self.counter != other.counter:
            return self.counter > other.counter
        return self.node_id > other.node_id

    def __ge__(self, other: "HLCTimestamp") -> bool:
        return self == other or self > other

    def __lt__(self, other: "HLCTimestamp") -> bool:
        return not self >= other

    def __le__(self, other: "HLCTimestamp") -> bool:
        return not self > other


class HybridLogicalClock:
    """Thread-safe HLC implementation."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._lock = threading.Lock()
        self._last_wall_ms = 0
        self._counter = 0

    def _physical_ms(self) -> int:
        return int(time.time() * 1000)

    def now(self) -> HLCTimestamp:
        """Generate a new timestamp for a local event."""
        with self._lock:
            phys = self._physical_ms()
            if phys > self._last_wall_ms:
                self._last_wall_ms = phys
                self._counter = 0
            else:
                self._counter += 1
            return HLCTimestamp(
                wall_ms=self._last_wall_ms,
                counter=self._counter,
                node_id=self.node_id,
            )

    def receive(self, remote: HLCTimestamp) -> HLCTimestamp:
        """Update clock upon receiving a remote timestamp. Returns new local timestamp."""
        with self._lock:
            phys = self._physical_ms()
            if phys > self._last_wall_ms and phys > remote.wall_ms:
                self._last_wall_ms = phys
                self._counter = 0
            elif remote.wall_ms > self._last_wall_ms:
                self._last_wall_ms = remote.wall_ms
                self._counter = remote.counter + 1
            elif self._last_wall_ms == remote.wall_ms:
                self._counter = max(self._counter, remote.counter) + 1
            else:
                self._counter += 1
            return HLCTimestamp(
                wall_ms=self._last_wall_ms,
                counter=self._counter,
                node_id=self.node_id,
            )
