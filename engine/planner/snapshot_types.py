"""Opaque source-produced snapshot value shared by producer and store."""
from __future__ import annotations

class ProducedPlannerSnapshot:
    __slots__ = ("kind", "payload", "_capability")
    def __init__(self, kind: str, payload: dict[str, object], capability: object) -> None:
        self.kind, self.payload, self._capability = kind, payload, capability
