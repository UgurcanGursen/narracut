"""Opaque source-produced snapshot value shared by producer and store."""
from __future__ import annotations
import copy

_PRODUCER_CAPABILITY = object()

class ProducedPlannerSnapshot:
    __slots__ = ("_kind", "_payload", "_capability")
    def __init__(self, kind: str, payload: dict[str, object], capability: object) -> None:
        if capability is not _PRODUCER_CAPABILITY:
            raise ValueError("PLANNER_SNAPSHOT_CAPABILITY_INVALID")
        object.__setattr__(self, "_kind", kind)
        object.__setattr__(self, "_payload", copy.deepcopy(payload))
        object.__setattr__(self, "_capability", capability)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("PLANNER_SNAPSHOT_IMMUTABLE")

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def payload(self) -> dict[str, object]:
        return copy.deepcopy(self._payload)
