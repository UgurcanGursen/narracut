"""Fail-closed, replay-first source acquisition and evidence treatment.

This module deliberately does not open URLs, start a browser, or bypass an
access control.  A future transport may populate ``ReplaySourcePackage`` only
after its own network-security checks; this Phase 6 core makes the resulting
evidence deterministic and safe to pass to later rendering phases.
"""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot


SOURCE_CAPTURE_PLAN_V1 = "SOURCE-CAPTURE-PLAN-V1"
SOURCE_PRIORITY_POLICY_V1 = "SOURCE-PRIORITY-POLICY-V1"
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


class AcquisitionAdapterId(str, Enum):
    OFFICIAL_PDF = "official_pdf"
    ACCESSIBLE_HTML = "accessible_html"
    FEED_API = "feed_api"
    MANUAL_CAPTURE = "manual_capture"


class SourceType(str, Enum):
    REGULATOR_FILING = "regulator_filing"
    COMPANY_FILING = "company_filing"
    OFFICIAL_REPORT = "official_report"
    OFFICIAL_PRESS_RELEASE = "official_press_release"
    TRUSTED_REPORTING = "trusted_reporting"
    FEED = "feed"


class AccessStatus(str, Enum):
    ACCESSIBLE = "accessible"
    CHALLENGE_DETECTED = "challenge_detected"
    PAYWALL_DETECTED = "paywall_detected"
    COOKIE_WALL_DETECTED = "cookie_wall_detected"
    AUTHENTICATION_REQUIRED = "authentication_required"
    MANUAL_CAPTURE_REQUIRED = "manual_capture_required"
    TEXT_FOUND = "text_found"
    TEXT_NOT_FOUND = "text_not_found"
    SNAPSHOT_AVAILABLE = "snapshot_available"
    UNAVAILABLE = "unavailable"


class FallbackMode(str, Enum):
    NO_FALLBACK = "no_fallback"
    SNAPSHOT_EVIDENCE = "snapshot_evidence"
    MANUAL_CAPTURE_PACKAGE = "manual_capture_package"
    TEXT_ONLY_EVIDENCE = "text_only_evidence"
    BLOCK_PLANNER = "block_planner"


class EvidenceFocusKind(str, Enum):
    FULL_PAGE = "full_page"
    HEADLINE = "headline"
    TARGET_PARAGRAPH = "target_paragraph"
    SENTENCE_HIGHLIGHT = "sentence_highlight"
    NUMBER_CALLOUT = "number_callout"


class PlannerGateDecision(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"


ACCESS_STATUS_FALLBACKS = {
    AccessStatus.ACCESSIBLE: FallbackMode.NO_FALLBACK,
    AccessStatus.TEXT_FOUND: FallbackMode.NO_FALLBACK,
    AccessStatus.SNAPSHOT_AVAILABLE: FallbackMode.SNAPSHOT_EVIDENCE,
    AccessStatus.CHALLENGE_DETECTED: FallbackMode.MANUAL_CAPTURE_PACKAGE,
    AccessStatus.PAYWALL_DETECTED: FallbackMode.MANUAL_CAPTURE_PACKAGE,
    AccessStatus.COOKIE_WALL_DETECTED: FallbackMode.MANUAL_CAPTURE_PACKAGE,
    AccessStatus.AUTHENTICATION_REQUIRED: FallbackMode.MANUAL_CAPTURE_PACKAGE,
    AccessStatus.MANUAL_CAPTURE_REQUIRED: FallbackMode.MANUAL_CAPTURE_PACKAGE,
    AccessStatus.TEXT_NOT_FOUND: FallbackMode.TEXT_ONLY_EVIDENCE,
    AccessStatus.UNAVAILABLE: FallbackMode.BLOCK_PLANNER,
}


class SourceAcquisitionError(ValueError):
    """Stable rejection code; input errors never create partial capture plans."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _reject(code: str) -> None:
    raise SourceAcquisitionError(code)


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _string(value: object) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _canonical_url(value: object) -> str:
    if not _string(value):
        _reject("SOURCE_URL_INVALID")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        _reject("SOURCE_URL_INVALID")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))


@dataclass(frozen=True)
class DOMRegion:
    dom_path: str
    text: str
    left_millionths: int
    top_millionths: int
    right_millionths: int
    bottom_millionths: int

    def as_data(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in self.__dataclass_fields__}


@dataclass(frozen=True)
class ReplaySourcePackage:
    source_id: str
    source_type: SourceType
    adapter_id: AcquisitionAdapterId
    url: str
    access_status: AccessStatus
    source_label: str
    publication_date: str
    document_text: str | None
    target_text: str | None
    snapshot_hash: str | None
    regions: tuple[DOMRegion, ...]


@dataclass(frozen=True)
class ManualCapturePackage:
    """User-captured package; its payload remains external and content-addressed."""

    source_id: str
    source_type: SourceType
    url: str
    source_label: str
    publication_date: str
    snapshot_hash: str
    regions: tuple[DOMRegion, ...]

    def as_replay_source_package(self) -> ReplaySourcePackage:
        """Convert an explicit user capture into the same closed adapter input."""
        if not all(_string(value) for value in (self.source_id, self.source_label, self.publication_date)) or type(self.source_type) is not SourceType or type(self.snapshot_hash) is not str or not _HASH.fullmatch(self.snapshot_hash) or any(not _region_valid(region) for region in self.regions):
            _reject("MANUAL_CAPTURE_PACKAGE_INVALID")
        return ReplaySourcePackage(
            self.source_id, self.source_type, AcquisitionAdapterId.MANUAL_CAPTURE,
            self.url, AccessStatus.SNAPSHOT_AVAILABLE, self.source_label,
            self.publication_date, "\n".join(region.text for region in self.regions),
            None, self.snapshot_hash, self.regions,
        )


@dataclass(frozen=True)
class SourceCapturePlan:
    schema_version: str
    source_capture_plan_id: str
    source_capture_plan_hash: str
    source_package_hash: str
    source_id: str
    source_type: SourceType
    acquisition_adapter: AcquisitionAdapterId
    url: str
    access_status: AccessStatus
    target_text: str | None
    target_dom_path: str | None
    crop_regions: tuple[DOMRegion, ...]
    scroll_events: tuple[str, ...]
    highlight_events: tuple[str, ...]
    source_label: str
    publication_date: str
    fallback_mode: FallbackMode
    snapshot_hash: str | None


@dataclass(frozen=True)
class EvidenceFocusEvent:
    focus_id: str
    kind: EvidenceFocusKind
    region: DOMRegion | None


@dataclass(frozen=True)
class EvidenceTreatmentPlan:
    source_capture_plan_id: str
    source_capture_plan_hash: str
    fallback_mode: FallbackMode
    focus_events: tuple[EvidenceFocusEvent, ...]
    source_label: str
    publication_date: str


@dataclass(frozen=True)
class SourcePriorityPolicy:
    policy_version: str
    ranked_source_types: tuple[SourceType, ...]
    mandatory_primary_source_types: tuple[SourceType, ...]
    policy_snapshot_id: str
    policy_snapshot_hash: str


def _region_valid(region: object) -> bool:
    return (
        type(region) is DOMRegion and _string(region.dom_path) and _string(region.text)
        and all(type(getattr(region, name)) is int for name in (
            "left_millionths", "top_millionths", "right_millionths", "bottom_millionths"
        )) and 0 <= region.left_millionths < region.right_millionths <= 1_000_000
        and 0 <= region.top_millionths < region.bottom_millionths <= 1_000_000
    )


class ChallengeDetector:
    """Classifies only explicit captured status; it never probes or circumvents."""

    @staticmethod
    def is_blocked(status: AccessStatus) -> bool:
        if type(status) is not AccessStatus:
            _reject("ACCESS_STATUS_INVALID")
        return status in {
            AccessStatus.CHALLENGE_DETECTED, AccessStatus.PAYWALL_DETECTED,
            AccessStatus.COOKIE_WALL_DETECTED, AccessStatus.AUTHENTICATION_REQUIRED,
        }


class DOMRegionExtractor:
    """Exact-text region selector. It deliberately has no nearest-coordinate mode."""

    @staticmethod
    def target_region(package: ReplaySourcePackage) -> DOMRegion | None:
        if package.target_text is None:
            return None
        if type(package.document_text) is not str or package.document_text.count(package.target_text) != 1:
            return None
        matches = [region for region in package.regions if region.text == package.target_text]
        return matches[0] if len(matches) == 1 and _region_valid(matches[0]) else None


def _plan_projection(plan: SourceCapturePlan) -> dict[str, object]:
    return {
        "schema_version": plan.schema_version, "source_package_hash": plan.source_package_hash,
        "source_id": plan.source_id,
        "source_type": plan.source_type.value, "acquisition_adapter": plan.acquisition_adapter.value,
        "url": plan.url, "access_status": plan.access_status.value,
        "target_text": plan.target_text, "target_dom_path": plan.target_dom_path,
        "crop_regions": [item.as_data() for item in plan.crop_regions],
        "scroll_events": list(plan.scroll_events), "highlight_events": list(plan.highlight_events),
        "source_label": plan.source_label, "publication_date": plan.publication_date,
        "fallback_mode": plan.fallback_mode.value, "snapshot_hash": plan.snapshot_hash,
    }


def _source_package_projection(package: ReplaySourcePackage, *, canonical_url: str) -> dict[str, object]:
    return {
        "source_id": package.source_id, "source_type": package.source_type.value,
        "adapter_id": package.adapter_id.value, "url": canonical_url,
        "access_status": package.access_status.value, "source_label": package.source_label,
        "publication_date": package.publication_date, "document_text": package.document_text,
        "target_text": package.target_text, "snapshot_hash": package.snapshot_hash,
        "regions": [region.as_data() for region in package.regions],
    }


def _validate_capture_plan(plan: object) -> SourceCapturePlan:
    if type(plan) is not SourceCapturePlan:
        _reject("CAPTURE_PLAN_INVALID")
    digest = _hash(_plan_projection(plan))
    if plan.schema_version != SOURCE_CAPTURE_PLAN_V1 or plan.source_capture_plan_hash != digest or plan.source_capture_plan_id != "scplan_" + digest[7:39]:
        _reject("CAPTURE_PLAN_INVALID")
    return plan


class _ReplayAdapter:
    adapter_id: AcquisitionAdapterId

    def capture(self, package: ReplaySourcePackage) -> SourceCapturePlan:
        if type(package) is not ReplaySourcePackage or package.adapter_id is not self.adapter_id:
            _reject("SOURCE_PACKAGE_INVALID")
        if not all(_string(value) for value in (package.source_id, package.source_label, package.publication_date)):
            _reject("SOURCE_PACKAGE_INVALID")
        url = _canonical_url(package.url)
        if type(package.access_status) is not AccessStatus or type(package.source_type) is not SourceType:
            _reject("SOURCE_PACKAGE_INVALID")
        if ((package.document_text is not None and type(package.document_text) is not str)
                or (package.target_text is not None and not _string(package.target_text))
                or type(package.regions) is not tuple
                or any(not _region_valid(region) for region in package.regions)
                or len({region.dom_path for region in package.regions}) != len(package.regions)):
            _reject("SOURCE_PACKAGE_INVALID")
        fallback = ACCESS_STATUS_FALLBACKS[package.access_status]
        blocked = ChallengeDetector.is_blocked(package.access_status)
        if package.snapshot_hash is not None and (type(package.snapshot_hash) is not str or not _HASH.fullmatch(package.snapshot_hash)):
            _reject("SNAPSHOT_HASH_INVALID")
        if blocked and package.snapshot_hash is not None:
            _reject("CHALLENGE_SNAPSHOT_FORBIDDEN")
        if fallback is FallbackMode.SNAPSHOT_EVIDENCE and package.snapshot_hash is None:
            _reject("SNAPSHOT_REQUIRED")
        target = DOMRegionExtractor.target_region(package)
        direct = fallback is FallbackMode.NO_FALLBACK
        if direct and target is None:
            fallback = FallbackMode.TEXT_ONLY_EVIDENCE
            status = AccessStatus.TEXT_NOT_FOUND
        else:
            status = package.access_status
        crops = package.regions if fallback in {FallbackMode.NO_FALLBACK, FallbackMode.SNAPSHOT_EVIDENCE} else ()
        package_hash = _hash(_source_package_projection(package, canonical_url=url))
        base = SourceCapturePlan(
            SOURCE_CAPTURE_PLAN_V1, "", "", package_hash, package.source_id, package.source_type,
            self.adapter_id, url, status, package.target_text if crops else None,
            target.dom_path if target is not None and crops else None, crops,
            (target.dom_path,) if target is not None and crops else (), (target.dom_path,) if target is not None and crops else (),
            package.source_label, package.publication_date, fallback, package.snapshot_hash,
        )
        digest = _hash(_plan_projection(base))
        return SourceCapturePlan(**(base.__dict__ | {
            "source_capture_plan_hash": digest,
            "source_capture_plan_id": "scplan_" + digest[7:39],
        }))


class OfficialPdfAdapter(_ReplayAdapter):
    adapter_id = AcquisitionAdapterId.OFFICIAL_PDF


class AccessibleHtmlAdapter(_ReplayAdapter):
    adapter_id = AcquisitionAdapterId.ACCESSIBLE_HTML


class FeedApiAdapter(_ReplayAdapter):
    adapter_id = AcquisitionAdapterId.FEED_API


class ManualCaptureAdapter(_ReplayAdapter):
    adapter_id = AcquisitionAdapterId.MANUAL_CAPTURE


class SourceAdapterRegistry:
    """Closed registry; no runtime discovery or provider-specific domain forks."""

    def __init__(self, adapters: Iterable[_ReplayAdapter] = ()) -> None:
        self._adapters: dict[AcquisitionAdapterId, _ReplayAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: _ReplayAdapter) -> None:
        if not isinstance(adapter, _ReplayAdapter) or adapter.adapter_id in self._adapters:
            _reject("ADAPTER_REGISTRATION_INVALID")
        self._adapters[adapter.adapter_id] = adapter

    def acquire(self, package: ReplaySourcePackage) -> SourceCapturePlan:
        if type(package) is not ReplaySourcePackage:
            _reject("SOURCE_PACKAGE_INVALID")
        try:
            return self._adapters[package.adapter_id].capture(package)
        except KeyError:
            _reject("ADAPTER_UNAVAILABLE")


class EvidenceTreatmentPlanner:
    def plan(self, capture: SourceCapturePlan, *, focus_regions: tuple[DOMRegion, ...] = ()) -> EvidenceTreatmentPlan:
        capture = _validate_capture_plan(capture)
        if ChallengeDetector.is_blocked(capture.access_status):
            _reject("CHALLENGE_CANNOT_RENDER")
        if capture.fallback_mode in {FallbackMode.TEXT_ONLY_EVIDENCE, FallbackMode.MANUAL_CAPTURE_PACKAGE}:
            events = (EvidenceFocusEvent("focus_text_only", EvidenceFocusKind.FULL_PAGE, None),)
        elif capture.fallback_mode is FallbackMode.BLOCK_PLANNER:
            _reject("PLANNER_BLOCKED")
        else:
            candidates = focus_regions or capture.crop_regions
            if not candidates or any(not _region_valid(item) for item in candidates):
                _reject("EVIDENCE_REGION_REQUIRED")
            unique = {item.dom_path for item in candidates}
            if len(unique) != len(candidates):
                _reject("EVIDENCE_REGION_DUPLICATE")
            verified = {region.dom_path: region.as_data() for region in capture.crop_regions}
            if any(verified.get(region.dom_path) != region.as_data() for region in candidates):
                _reject("EVIDENCE_REGION_UNVERIFIED")
            kinds = (EvidenceFocusKind.FULL_PAGE, EvidenceFocusKind.HEADLINE,
                     EvidenceFocusKind.TARGET_PARAGRAPH, EvidenceFocusKind.SENTENCE_HIGHLIGHT,
                     EvidenceFocusKind.NUMBER_CALLOUT)
            events = tuple(EvidenceFocusEvent(f"focus_{index + 1}", kinds[min(index, len(kinds) - 1)], region) for index, region in enumerate(candidates))
        return EvidenceTreatmentPlan(capture.source_capture_plan_id, capture.source_capture_plan_hash, capture.fallback_mode, events, capture.source_label, capture.publication_date)


class SourcePreviewRenderer:
    """Produces a diagnostic SVG only; final media rendering stays in later phases."""

    def render_svg(self, treatment: EvidenceTreatmentPlan, *, capture: SourceCapturePlan) -> bytes:
        capture = _validate_capture_plan(capture)
        if (type(treatment) is not EvidenceTreatmentPlan
                or treatment.fallback_mode is FallbackMode.BLOCK_PLANNER
                or ChallengeDetector.is_blocked(capture.access_status)
                or (treatment.source_capture_plan_id, treatment.source_capture_plan_hash, treatment.fallback_mode, treatment.source_label, treatment.publication_date) != (capture.source_capture_plan_id, capture.source_capture_plan_hash, capture.fallback_mode, capture.source_label, capture.publication_date)):
            _reject("SOURCE_PREVIEW_INVALID")
        labels = "".join(
            f'<text x="24" y="{50 + 30 * index}">{html.escape(event.kind.value)}</text>'
            for index, event in enumerate(treatment.focus_events)
        )
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">'
                f'<text x="24" y="24">{html.escape(treatment.source_label)} — {html.escape(treatment.publication_date)}</text>{labels}</svg>').encode("utf-8")


def source_priority_policy_from_snapshot(snapshot: DomainPolicySnapshot) -> SourcePriorityPolicy:
    if type(snapshot) is not DomainPolicySnapshot:
        _reject("POLICY_SNAPSHOT_INVALID")
    data = {field: getattr(snapshot, field) for field in snapshot.__dataclass_fields__}
    if not snapshot.immutable or snapshot.canonical_hash != policy_snapshot_hash(data):
        _reject("POLICY_SNAPSHOT_INVALID")
    bundles = snapshot.resolved_policy.get("policy_bundles") if type(snapshot.resolved_policy) is dict else None
    matches = []
    if type(bundles) is list:
        for bundle in bundles:
            research = bundle.get("policy", {}).get("research") if type(bundle) is dict and type(bundle.get("policy")) is dict else None
            if type(research) is dict and "source_priority_policy" in research:
                matches.append(research["source_priority_policy"])
    if len(matches) != 1 or type(matches[0]) is not dict:
        _reject("SOURCE_PRIORITY_POLICY_MISSING")
    raw = matches[0]
    required = {"policy_version", "ranked_source_types", "mandatory_primary_source_types"}
    if set(raw) != required or raw["policy_version"] != SOURCE_PRIORITY_POLICY_V1 or type(raw["ranked_source_types"]) is not list or type(raw["mandatory_primary_source_types"]) is not list:
        _reject("SOURCE_PRIORITY_POLICY_INVALID")
    try:
        ranked = tuple(SourceType(item) for item in raw["ranked_source_types"])
        mandatory = tuple(SourceType(item) for item in raw["mandatory_primary_source_types"])
    except (TypeError, ValueError):
        _reject("SOURCE_PRIORITY_POLICY_INVALID")
    if not ranked or len(set(ranked)) != len(ranked) or len(set(mandatory)) != len(mandatory) or not set(mandatory).issubset(set(ranked)):
        _reject("SOURCE_PRIORITY_POLICY_INVALID")
    return SourcePriorityPolicy(SOURCE_PRIORITY_POLICY_V1, ranked, mandatory, snapshot.snapshot_id, snapshot.canonical_hash)


def gate_primary_source_requirement(policy: SourcePriorityPolicy, captures: Iterable[SourceCapturePlan]) -> PlannerGateDecision:
    if type(policy) is not SourcePriorityPolicy:
        _reject("SOURCE_PRIORITY_POLICY_INVALID")
    values = tuple(_validate_capture_plan(capture) for capture in captures)
    accepted_statuses = {AccessStatus.ACCESSIBLE, AccessStatus.TEXT_FOUND, AccessStatus.SNAPSHOT_AVAILABLE}
    types = {
        capture.source_type for capture in values
        if capture.access_status in accepted_statuses
        and capture.fallback_mode in {FallbackMode.NO_FALLBACK, FallbackMode.SNAPSHOT_EVIDENCE}
    }
    return PlannerGateDecision.ALLOWED if set(policy.mandatory_primary_source_types).issubset(types) else PlannerGateDecision.BLOCKED


def rank_source_packages(policy: SourcePriorityPolicy, packages: Iterable[ReplaySourcePackage]) -> tuple[ReplaySourcePackage, ...]:
    """Apply domain policy without leaking domain-specific branches into adapters."""
    if type(policy) is not SourcePriorityPolicy:
        _reject("SOURCE_PRIORITY_POLICY_INVALID")
    values = tuple(packages)
    if any(type(value) is not ReplaySourcePackage for value in values):
        _reject("SOURCE_PACKAGE_INVALID")
    rank = {source_type: index for index, source_type in enumerate(policy.ranked_source_types)}
    if any(value.source_type not in rank for value in values):
        _reject("SOURCE_TYPE_NOT_RANKED")
    return tuple(sorted(values, key=lambda value: (rank[value.source_type], value.source_id, value.url)))
