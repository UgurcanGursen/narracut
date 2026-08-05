"""Closed Phase 4A fixture-only visual-directive union validator."""
from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass
from typing import Any
from engine.contracts._canonical_json import encode_canonical_json_bytes

_COMMON_FIELDS = (
    "schema_version", "directive_id", "directive_hash", "event_id", "event_hash",
    "track", "kind",
)
_V3_FIELDS = _COMMON_FIELDS + (
    "zoom_start_millionths", "zoom_end_millionths",
    "highlight_left_millionths", "highlight_top_millionths",
    "highlight_right_millionths", "highlight_bottom_millionths",
)
_V4_FIELDS = _COMMON_FIELDS + ("reveal_start_millionths", "reveal_end_millionths")

@dataclass(frozen=True)
class VisualDirective:
    schema_version: str; directive_id: str; directive_hash: str; event_id: str; event_hash: str; track: str; kind: str
    fields: tuple[str, ...]
    values: tuple[Any, ...]

    def as_row(self) -> dict[str, Any]:
        """Return exactly the closed-union arm that was validated at ingress."""
        return dict(zip(self.fields, self.values, strict=True))

def validate_directive(row: Any, pointer: str = "/visual_directives") -> VisualDirective:
    from .fixture_assets import FixtureAssetResolverError
    def bad() -> None: raise FixtureAssetResolverError("ASSET_RESOLUTION_FAILED", pointer)
    if type(row) is not dict:
        bad()
    fields = _V3_FIELDS if (row.get("track"), row.get("kind")) == ("V3", "SOURCE_ZOOM_HIGHLIGHT") else _V4_FIELDS if (row.get("track"), row.get("kind")) == ("V4", "CHART_REVEAL") else ()
    if not fields or tuple(row) != fields or any(type(row[name]) is not str for name in _COMMON_FIELDS):
        bad()
    values = tuple(row[name] for name in fields)
    value = VisualDirective(
        schema_version=row["schema_version"], directive_id=row["directive_id"],
        directive_hash=row["directive_hash"], event_id=row["event_id"],
        event_hash=row["event_hash"], track=row["track"], kind=row["kind"],
        fields=fields, values=values,
    )
    # Video EDL event_hash is a Phase 3 bare digest (unlike artifact hashes);
    # matching its exact existing representation avoids a bridge-side rewrite.
    if (value.schema_version != "FIXTURE-VISUAL-DIRECTIVE-V1" or not value.directive_id.startswith("vdir_") or not value.event_id.startswith("vevt_") or re.fullmatch(r"[0-9a-f]{64}", value.event_hash) is None): bad()
    projection = {name: row[name] for name in fields if name not in {"directive_id", "directive_hash"}}
    digest="sha256:"+hashlib.sha256(encode_canonical_json_bytes(projection)).hexdigest()
    if value.directive_hash != digest or value.directive_id != "vdir_"+digest[7:39]: bad()
    if fields == _V3_FIELDS:
        nums = tuple(row[name] for name in fields[7:])
        if (any(type(x) is not int or type(x) is bool for x in nums)
                or not (1_000_000 <= row["zoom_start_millionths"] <= row["zoom_end_millionths"] <= 2_000_000)
                or not (0 <= row["highlight_left_millionths"] < row["highlight_right_millionths"] <= 1_000_000
                        and 0 <= row["highlight_top_millionths"] < row["highlight_bottom_millionths"] <= 1_000_000)):
            bad()
    else:
        start, end = row["reveal_start_millionths"], row["reveal_end_millionths"]
        if (type(start) is not int or type(start) is bool or type(end) is not int or type(end) is bool
                or not (0 <= start < end <= 1_000_000)):
            bad()
    return value
