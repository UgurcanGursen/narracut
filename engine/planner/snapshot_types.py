"""Opaque source-produced snapshot value shared by producer and store."""
from __future__ import annotations

_PRODUCER_CAPABILITY = object()

class ProducedPlannerSnapshot:
    __slots__ = ("kind", "payload", "_capability")
    def __init__(self, kind: str, payload: dict[str, object], capability: object) -> None:
        if capability is not _PRODUCER_CAPABILITY:
            raise ValueError("PLANNER_SNAPSHOT_CAPABILITY_INVALID")
        self.kind, self.payload, self._capability = kind, payload, capability
