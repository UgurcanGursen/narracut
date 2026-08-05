"""Phase 9 local REPLAY/MANUAL_UI task contracts.

This module intentionally has no network client, browser driver or provider SDK.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot


PHASE9_TASK_V1 = "PHASE9-LLM-TASK-V1"
PHASE9_RESPONSE_V1 = "PHASE9-LLM-RESPONSE-V1"
CLAIM_RESEARCH_POLICY_V1 = "CLAIM-RESEARCH-POLICY-V1"


class ResearchError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise ResearchError(code)


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _bytes_hash(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _hash_ok(value: object) -> bool:
    return type(value) is str and len(value) == 71 and value.startswith("sha256:") and all(item in "0123456789abcdef" for item in value[7:])


def _token(value: object) -> bool:
    return type(value) is str and bool(value) and value == value.strip() and value == value.lower()


def _tokens(value: object) -> tuple[str, ...]:
    if type(value) not in {list, tuple} or any(not _token(item) for item in value) or len(set(value)) != len(value):
        _fail("RESEARCH_TOKEN_INVALID")
    return tuple(value)


def _id(value: object, prefix: str) -> bool:
    return type(value) is str and value.startswith(prefix) and len(value) > len(prefix) and all(item in "abcdefghijklmnopqrstuvwxyz0123456789_-" for item in value[len(prefix):])


def _canonical_json_load(value: bytes) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        output: dict[str, object] = {}
        for key, item in items:
            if key in output:
                _fail("RESPONSE_CANONICAL_INVALID")
            output[key] = item
        return output
    try:
        raw = json.loads(value.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        _fail("RESPONSE_CANONICAL_INVALID")
    if encode_canonical_json_bytes(raw) != value:
        _fail("RESPONSE_CANONICAL_INVALID")
    return raw


def canonical_url(value: object) -> str:
    if type(value) is not str or not value.strip():
        _fail("SOURCE_URL_INVALID")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        _fail("SOURCE_URL_INVALID")
    normalized = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))
    if normalized != value:
        _fail("SOURCE_URL_NOT_CANONICAL")
    return normalized


def _iso_date(value: object) -> str:
    if type(value) is not str:
        _fail("DATE_INVALID")
    try:
        date.fromisoformat(value)
    except ValueError:
        _fail("DATE_INVALID")
    return value


class BackendMode(str, Enum):
    REPLAY = "replay"
    MANUAL_UI = "manual_ui"
    LOCAL_MODEL = "local_model"
    API = "api"


class TaskType(str, Enum):
    SOURCE_DISCOVERY = "source_discovery"
    SOURCE_EXTRACTION = "source_extraction"
    CLAIM_NORMALIZATION = "claim_normalization"
    REPAIR = "repair"


class TaskStatus(str, Enum):
    CREATED = "created"
    PACKAGE_READY = "package_ready"
    RESPONSE_SUBMITTED = "response_submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class ClaimResearchPolicyV1:
    profile_id: str
    manifest_hash: str
    resolved_policy_hash: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    allowed_claim_types: tuple[str, ...]
    allowed_claim_statuses: tuple[str, ...]
    allowed_authority_tokens: tuple[str, ...]
    allowed_contradiction_kinds: tuple[str, ...]
    allowed_date_precisions: tuple[str, ...]
    allowed_safe_wording_tokens: tuple[str, ...]
    allowed_visible_contradiction_wording_tokens: tuple[str, ...]


def claim_research_policy_from_snapshot(snapshot: DomainPolicySnapshot) -> ClaimResearchPolicyV1:
    if type(snapshot) is not DomainPolicySnapshot or not snapshot.immutable:
        _fail("POLICY_SNAPSHOT_INVALID")
    raw_snapshot = {field: getattr(snapshot, field) for field in snapshot.__dataclass_fields__}
    if snapshot.canonical_hash != policy_snapshot_hash(raw_snapshot):
        _fail("POLICY_SNAPSHOT_INVALID")
    bundles = snapshot.resolved_policy.get("policy_bundles") if type(snapshot.resolved_policy) is dict else None
    matches: list[object] = []
    if type(bundles) is list:
        for bundle in bundles:
            research = bundle.get("policy", {}).get("research") if type(bundle) is dict and type(bundle.get("policy")) is dict else None
            if type(research) is dict and "claim_research_policy" in research:
                matches.append(research["claim_research_policy"])
    expected = {"policy_version", "allowed_claim_types", "allowed_claim_statuses", "allowed_authority_tokens", "allowed_contradiction_kinds", "allowed_date_precisions", "allowed_safe_wording_tokens", "allowed_visible_contradiction_wording_tokens"}
    if len(matches) != 1 or type(matches[0]) is not dict or set(matches[0]) != expected or matches[0]["policy_version"] != CLAIM_RESEARCH_POLICY_V1:
        _fail("CLAIM_RESEARCH_POLICY_MISSING")
    raw = matches[0]
    values = {name: _tokens(raw[name]) for name in expected - {"policy_version"}}
    if any(not values[name] for name in values):
        _fail("CLAIM_RESEARCH_POLICY_INVALID")
    return ClaimResearchPolicyV1(snapshot.profile_id, snapshot.manifest_hash,
                                 _hash(snapshot.resolved_policy), snapshot.snapshot_id,
                                 snapshot.canonical_hash, **values)


class DomainAwareResearchPolicyResolver:
    """Typed adapter from the selected immutable Domain Pack snapshot."""

    def resolve(self, snapshot: DomainPolicySnapshot) -> ClaimResearchPolicyV1:
        return claim_research_policy_from_snapshot(snapshot)


@dataclass(frozen=True)
class LLMTaskV1:
    task_id: str
    task_hash: str
    logical_task_id: str
    supersedes_task_id: str | None
    task_type: TaskType
    project_id: str
    input_manifest: dict[str, object]
    prompt_template_ref: str
    context_artifacts: tuple[dict[str, str], ...]
    expected_output_schema: dict[str, object]
    backend_mode: BackendMode
    status: TaskStatus
    attempt: int
    parent_task_id: str | None
    created_at: str
    completed_at: str | None


def _task_projection(task: LLMTaskV1) -> dict[str, object]:
    manifest = dict(task.input_manifest)
    manifest["task_id"] = "pending"
    manifest["task_hash"] = "pending"
    return {
        "logical_task_id": task.logical_task_id, "supersedes_task_id": task.supersedes_task_id,
        "task_type": task.task_type.value, "project_id": task.project_id,
        "input_manifest": manifest, "prompt_template_ref": task.prompt_template_ref,
        "context_artifacts": list(task.context_artifacts), "expected_output_schema": task.expected_output_schema,
        "backend_mode": task.backend_mode.value, "status": task.status.value, "attempt": task.attempt,
        "parent_task_id": task.parent_task_id, "created_at": task.created_at, "completed_at": task.completed_at,
    }


def validate_task(task: LLMTaskV1) -> LLMTaskV1:
    if type(task) is not LLMTaskV1 or not _id(task.task_id, "task_") or not _id(task.logical_task_id, "ltask_") or (task.supersedes_task_id is not None and not _id(task.supersedes_task_id, "task_")) or (task.parent_task_id is not None and not _id(task.parent_task_id, "task_")) or type(task.task_type) is not TaskType or type(task.backend_mode) is not BackendMode or type(task.status) is not TaskStatus or not _id(task.project_id, "prj_") or type(task.attempt) is not int or task.attempt < 0 or type(task.created_at) is not str or not task.created_at.endswith("Z") or (task.completed_at is not None and (type(task.completed_at) is not str or not task.completed_at.endswith("Z"))):
        _fail("TASK_INVALID")
    manifest = task.input_manifest
    expected = {"schema_version", "task_id", "task_hash", "logical_task_id", "project_id", "task_type", "backend_mode", "policy_snapshot_id", "policy_snapshot_hash", "prompt_template_ref", "prompt_hash", "readme_hash", "context_artifact_refs", "expected_output_schema_hash"}
    if type(manifest) is not dict or set(manifest) != expected or manifest["schema_version"] != PHASE9_TASK_V1 or (manifest["task_id"], manifest["task_hash"], manifest["logical_task_id"], manifest["project_id"], manifest["task_type"], manifest["backend_mode"], manifest["prompt_template_ref"]) != (task.task_id, task.task_hash, task.logical_task_id, task.project_id, task.task_type.value, task.backend_mode.value, task.prompt_template_ref) or not _id(manifest["policy_snapshot_id"], "dps_") or not all(_hash_ok(manifest[key]) for key in ("policy_snapshot_hash", "prompt_hash", "readme_hash", "expected_output_schema_hash")) or type(manifest["context_artifact_refs"]) is not list:
        _fail("TASK_MANIFEST_INVALID")
    if not _hash_ok(task.task_hash) or task.task_hash != _hash(_task_projection(task)) or task.task_id != "task_" + task.task_hash[7:27]:
        _fail("TASK_IDENTITY_INVALID")
    return task


def _response_schema(task_type: TaskType) -> dict[str, object]:
    base = {"schema_version": PHASE9_RESPONSE_V1, "task_type": task_type.value}
    if task_type is TaskType.SOURCE_DISCOVERY:
        return {**base, "result_fields": ["candidates"]}
    if task_type is TaskType.SOURCE_EXTRACTION:
        return {**base, "result_fields": ["facts", "quotes", "numbers", "uncertainties"]}
    if task_type is TaskType.CLAIM_NORMALIZATION:
        return {**base, "result_fields": ["claims"]}
    return {**base, "result_fields": ["original_task_id", "errors"]}


class LLMTaskService:
    def transition(self, *, previous: LLMTaskV1, status: TaskStatus,
                   completed_at: str | None) -> LLMTaskV1:
        """Append a status-only immutable revision after package/result processing."""
        validate_task(previous)
        if status not in {TaskStatus.ACCEPTED, TaskStatus.REJECTED}:
            _fail("TASK_TRANSITION_INVALID")
        base = LLMTaskV1("", "", previous.logical_task_id, previous.task_id,
                         previous.task_type, previous.project_id,
                         {**previous.input_manifest, "task_id": "pending", "task_hash": "pending"},
                         previous.prompt_template_ref, previous.context_artifacts,
                         previous.expected_output_schema, previous.backend_mode, status,
                         previous.attempt, previous.parent_task_id, previous.created_at,
                         completed_at)
        digest = _hash(_task_projection(base)); task_id = "task_" + digest[7:27]
        manifest = {**base.input_manifest, "task_id": task_id, "task_hash": digest}
        return LLMTaskV1(task_id, digest, base.logical_task_id, base.supersedes_task_id,
                         base.task_type, base.project_id, manifest,
                         base.prompt_template_ref, base.context_artifacts,
                         base.expected_output_schema, base.backend_mode, base.status,
                         base.attempt, base.parent_task_id, base.created_at,
                         base.completed_at)
    def create_task(self, *, task_type: TaskType, project_id: str, policy: ClaimResearchPolicyV1, backend_mode: BackendMode, prompt_template_ref: str, domain_pack_root: Path, topic: str, scope_tokens: tuple[str, ...] = (), context_artifacts: tuple[dict[str, str], ...] = (), logical_task_id: str | None = None, supersedes_task_id: str | None = None, parent_task_id: str | None = None, attempt: int = 0, status: TaskStatus = TaskStatus.CREATED, created_at: str = "2026-08-05T00:00:00Z", completed_at: str | None = None, repair_prompt_text: str | None = None) -> LLMTaskV1:
        if type(task_type) is not TaskType or not _id(project_id, "prj_") or type(policy) is not ClaimResearchPolicyV1 or type(backend_mode) is not BackendMode or backend_mode not in {BackendMode.REPLAY, BackendMode.MANUAL_UI} or type(prompt_template_ref) is not str or type(topic) is not str or not topic.strip() or type(attempt) is not int or attempt < 0:
            _fail("TASK_CREATE_INVALID")
        if repair_prompt_text is not None:
            if task_type is not TaskType.REPAIR or type(repair_prompt_text) is not str or not repair_prompt_text.strip():
                _fail("TASK_CREATE_INVALID")
            prompt_text = repair_prompt_text
        else:
            prompt_text = DomainPromptResolver().resolve(pack_root=domain_pack_root, prompt_template_ref=prompt_template_ref)
        try:
            manifest = json.loads((domain_pack_root / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, TypeError, json.JSONDecodeError):
            _fail("DOMAIN_PACK_BINDING_INVALID")
        if (type(manifest) is not dict
                or _bytes_hash(encode_canonical_json_bytes(manifest)) != policy.manifest_hash
                or prompt_template_ref not in manifest.get("prompt_bundle_refs", [])):
            _fail("DOMAIN_PACK_BINDING_INVALID")
        scope = _tokens(scope_tokens)
        schema = _response_schema(task_type)
        logical = logical_task_id or "ltask_" + _hash({"project_id": project_id, "task_type": task_type.value, "topic": topic, "scope": list(scope), "parent_task_id": parent_task_id})[7:27]
        if not _id(logical, "ltask_"):
            _fail("TASK_CREATE_INVALID")
        readme_text = f"# {task_type.value}\n\nBackend: {backend_mode.value}\n"
        empty_manifest = {"schema_version": PHASE9_TASK_V1, "task_id": "pending", "task_hash": "pending", "logical_task_id": logical, "project_id": project_id, "task_type": task_type.value, "backend_mode": backend_mode.value, "policy_snapshot_id": policy.policy_snapshot_id, "policy_snapshot_hash": policy.policy_snapshot_hash, "prompt_template_ref": prompt_template_ref, "prompt_hash": _bytes_hash(prompt_text.encode("utf-8")), "readme_hash": _bytes_hash(readme_text.encode("utf-8")), "context_artifact_refs": list(context_artifacts), "expected_output_schema_hash": _hash(schema)}
        base = LLMTaskV1("", "", logical, supersedes_task_id, task_type, project_id, empty_manifest, prompt_template_ref, context_artifacts, schema, backend_mode, status, attempt, parent_task_id, created_at, completed_at)
        digest = _hash(_task_projection(base))
        task_id = "task_" + digest[7:27]
        manifest = {**empty_manifest, "task_id": task_id, "task_hash": digest}
        task = LLMTaskV1(task_id, digest, logical, supersedes_task_id, task_type, project_id, manifest, prompt_template_ref, context_artifacts, schema, backend_mode, status, attempt, parent_task_id, created_at, completed_at)
        # Manifest has task identity but task identity cannot recursively include it.
        return task

    def revise_task(self, *, previous: LLMTaskV1, policy: ClaimResearchPolicyV1,
                    domain_pack_root: Path, topic: str, status: TaskStatus,
                    created_at: str, completed_at: str | None = None) -> LLMTaskV1:
        """Create, rather than mutate, a lifecycle revision of an LLM task."""
        validate_task(previous)
        if status not in {TaskStatus.PACKAGE_READY, TaskStatus.RESPONSE_SUBMITTED,
                          TaskStatus.ACCEPTED, TaskStatus.REJECTED,
                          TaskStatus.SUPERSEDED}:
            _fail("TASK_TRANSITION_INVALID")
        prompt_text = DomainPromptResolver().resolve(pack_root=domain_pack_root, prompt_template_ref=previous.prompt_template_ref)
        if (policy.policy_snapshot_id != previous.input_manifest["policy_snapshot_id"]
                or policy.policy_snapshot_hash != previous.input_manifest["policy_snapshot_hash"]
                or _bytes_hash(prompt_text.encode("utf-8")) != previous.input_manifest["prompt_hash"]):
            _fail("TASK_REVISION_BINDING_INVALID")
        return self.create_task(
            task_type=previous.task_type, project_id=previous.project_id,
            policy=policy, backend_mode=previous.backend_mode,
            prompt_template_ref=previous.prompt_template_ref,
            domain_pack_root=domain_pack_root, topic=topic,
            context_artifacts=previous.context_artifacts,
            logical_task_id=previous.logical_task_id,
            supersedes_task_id=previous.task_id,
            parent_task_id=previous.parent_task_id,
            attempt=previous.attempt, status=status, created_at=created_at,
            completed_at=completed_at,
        )


class DomainPromptResolver:
    """Read a prompt only from the selected Domain Pack, without a domain branch."""

    def resolve(self, *, pack_root: Path, prompt_template_ref: str) -> str:
        if not isinstance(pack_root, Path) or type(prompt_template_ref) is not str:
            _fail("PROMPT_REFERENCE_INVALID")
        root = pack_root.resolve()
        path = (root / prompt_template_ref).resolve()
        if not prompt_template_ref.startswith("prompts/") or not path.is_relative_to(root) or not path.is_file():
            _fail("PROMPT_REFERENCE_INVALID")
        try:
            value = path.read_text(encoding="utf-8")
        except OSError:
            _fail("PROMPT_REFERENCE_INVALID")
        if not value.strip():
            _fail("PROMPT_REFERENCE_INVALID")
        return value


class TaskPackageBuilder:
    def build(self, *, task: LLMTaskV1, workspace_root: Path, domain_pack_root: Path, topic: str, scope_tokens: tuple[str, ...], domain_profile: Mapping[str, object], resolved_policy: Mapping[str, object], sources: tuple[dict[str, object], ...] = (), claims: tuple[dict[str, object], ...] = (), repair_prompt_text: str | None = None) -> Path:
        if not isinstance(workspace_root, Path) or type(topic) is not str or not topic.strip():
            _fail("TASK_PACKAGE_INVALID")
        if type(task) is not LLMTaskV1 or task.backend_mode not in {BackendMode.REPLAY, BackendMode.MANUAL_UI}:
            _fail("TASK_PACKAGE_INVALID")
        prompt_text = repair_prompt_text if task.task_type is TaskType.REPAIR and type(repair_prompt_text) is str else DomainPromptResolver().resolve(pack_root=domain_pack_root, prompt_template_ref=task.prompt_template_ref)
        if not prompt_text.strip():
            _fail("TASK_PACKAGE_INVALID")
        root = workspace_root.resolve(); target = (root / "llm_tasks" / task.task_id).resolve()
        if not target.is_relative_to(root):
            _fail("TASK_PACKAGE_PATH_INVALID")
        target.mkdir(parents=True, exist_ok=False); (target / "response").mkdir()
        readme = f"# {task.task_type.value}\n\nBackend: {task.backend_mode.value}\n"
        files: dict[str, bytes] = {
            "README.md": readme.encode("utf-8"), "prompt.md": prompt_text.encode("utf-8"),
            "input_manifest.json": encode_canonical_json_bytes(task.input_manifest),
            "topic_or_scope.json": encode_canonical_json_bytes({"topic": topic, "scope_tokens": list(_tokens(scope_tokens))}),
            "domain_profile.json": encode_canonical_json_bytes(dict(domain_profile)),
            "resolved_domain_policies.json": encode_canonical_json_bytes(dict(resolved_policy)),
            "relevant_sources.json": encode_canonical_json_bytes(list(sources)),
            "relevant_claims.json": encode_canonical_json_bytes(list(claims)),
            "expected_output.schema.json": encode_canonical_json_bytes(task.expected_output_schema),
        }
        if _bytes_hash(files["prompt.md"]) != task.input_manifest["prompt_hash"] or _bytes_hash(files["README.md"]) != task.input_manifest["readme_hash"]:
            _fail("TASK_PACKAGE_BINDING_INVALID")
        for name, contents in files.items():
            (target / name).write_bytes(contents)
        return target


class ReplayBackend:
    """Fixture-only backend; it never falls through to a provider."""

    def __init__(self, responses_by_task_hash: Mapping[str, bytes]) -> None:
        if any(not _hash_ok(key) or type(value) is not bytes for key, value in responses_by_task_hash.items()):
            _fail("REPLAY_BACKEND_INVALID")
        self._responses = dict(responses_by_task_hash)

    def response_for(self, task: LLMTaskV1) -> bytes:
        validate_task(task)
        if task.backend_mode is not BackendMode.REPLAY:
            _fail("REPLAY_BACKEND_MODE_INVALID")
        try:
            return self._responses[task.task_hash]
        except KeyError:
            _fail("REPLAY_RESPONSE_MISSING")


class ManualUIBackend:
    """Creates a local task package and deliberately does nothing else."""

    def prepare(self, *, builder: TaskPackageBuilder, task: LLMTaskV1, workspace_root: Path, domain_pack_root: Path, topic: str, scope_tokens: tuple[str, ...], domain_profile: Mapping[str, object], resolved_policy: Mapping[str, object], sources: tuple[dict[str, object], ...] = (), claims: tuple[dict[str, object], ...] = ()) -> Path:
        if task.backend_mode is not BackendMode.MANUAL_UI:
            _fail("MANUAL_UI_BACKEND_MODE_INVALID")
        return builder.build(task=task, workspace_root=workspace_root, domain_pack_root=domain_pack_root, topic=topic, scope_tokens=scope_tokens, domain_profile=domain_profile, resolved_policy=resolved_policy, sources=sources, claims=claims)


class LocalModelBackend:
    def response_for(self, task: LLMTaskV1) -> bytes:
        validate_task(task); _fail("LOCAL_MODEL_UNAVAILABLE")


class ApiBackend:
    def response_for(self, task: LLMTaskV1) -> bytes:
        validate_task(task); _fail("API_BACKEND_UNAVAILABLE")


class RepairTaskBuilder:
    def build(self, *, failed_task: LLMTaskV1, policy: ClaimResearchPolicyV1, service: LLMTaskService, workspace_root: Path, domain_pack_root: Path, topic: str, scope_tokens: tuple[str, ...], domain_profile: Mapping[str, object], resolved_policy: Mapping[str, object], original_response: bytes, validation_errors: tuple[str, ...], created_at: str = "2026-08-05T00:00:00Z") -> tuple[LLMTaskV1, Path]:
        validate_task(failed_task)
        if not validation_errors or any(not _token(item) for item in validation_errors):
            _fail("REPAIR_ERRORS_INVALID")
        prompt = "Repair only these validation errors: " + ", ".join(validation_errors)
        task = service.create_task(task_type=TaskType.REPAIR, project_id=failed_task.project_id, policy=policy, backend_mode=BackendMode.MANUAL_UI, prompt_template_ref=failed_task.prompt_template_ref, domain_pack_root=domain_pack_root, topic=topic, scope_tokens=scope_tokens, parent_task_id=failed_task.task_id, attempt=failed_task.attempt + 1, created_at=created_at, repair_prompt_text=prompt)
        path = TaskPackageBuilder().build(task=task, workspace_root=workspace_root, domain_pack_root=domain_pack_root, topic=topic, scope_tokens=scope_tokens, domain_profile=domain_profile, resolved_policy=resolved_policy, repair_prompt_text=prompt)
        response_dir = path / "response"
        response_dir.joinpath("original_response.json").write_bytes(original_response)
        response_dir.joinpath("validation_errors.json").write_bytes(encode_canonical_json_bytes({"errors": list(validation_errors)}))
        response_dir.joinpath("repair_prompt.md").write_text(prompt, encoding="utf-8")
        return task, path
