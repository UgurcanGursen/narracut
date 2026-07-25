from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.contracts import (
    ArtifactRecord,
    DomainPackError,
    DomainPackRegistry,
    DomainPolicyResolver,
    EditorialSequence,
    RetentionPolicy,
    SchemaCatalog,
    Workspace,
    WorkspaceLoader,
    canonical_json,
    policy_snapshot_hash,
    validate_artifact_graph,
    validate_retention_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "schema" / "v3"
SAMPLE_ROOT = REPO_ROOT / "samples" / "v3"
DOMAIN_ROOT = REPO_ROOT / "domain-packs"
DUMMY_ROOT = REPO_ROOT / "tests" / "fixtures" / "domain-packs"


@pytest.fixture(scope="module")
def catalog() -> SchemaCatalog:
    return SchemaCatalog(SCHEMA_ROOT)


@pytest.fixture()
def domain_registry(catalog: SchemaCatalog) -> DomainPackRegistry:
    registry = DomainPackRegistry([DOMAIN_ROOT], catalog)
    registry.discover()
    return registry


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sample_path(name: str) -> Path:
    return SAMPLE_ROOT / name / "workspace.json"


@pytest.mark.parametrize(
    "sample_name", ["minimal", "business-tech", "split-long-form"]
)
def test_sample_workspace_is_valid(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    sample_name: str,
) -> None:
    registry = domain_registry if sample_name != "minimal" else None
    loaded = WorkspaceLoader(catalog, registry=registry).load(
        sample_path(sample_name)
    )
    assert loaded.validation.is_valid, loaded.validation.issues
    assert loaded.workspace is not None


def test_split_workspace_is_document_based(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry
) -> None:
    loaded = WorkspaceLoader(catalog, registry=domain_registry).load(
        sample_path("split-long-form")
    )
    assert loaded.validation.is_valid
    assert loaded.data["layout"] == "split"
    kinds = [item["kind"] for item in loaded.data["documents"]]
    assert kinds.count("chapter") == 2
    assert kinds.count("beat") == 2
    assert kinds.count("sequence") == 2
    assert "asset_manifest" in kinds
    assert "artifact_manifest" in kinds


def test_dummy_domain_loads_without_core_changes(catalog: SchemaCatalog) -> None:
    registry = DomainPackRegistry([DUMMY_ROOT], catalog)
    packs = registry.discover()
    assert [(pack.manifest.domain_id, pack.manifest.domain_pack_version) for pack in packs] == [
        ("dummy-domain", "1.0.0")
    ]


def test_unknown_domain_is_rejected(catalog: SchemaCatalog) -> None:
    registry = DomainPackRegistry([DOMAIN_ROOT], catalog)
    registry.discover()
    with pytest.raises(DomainPackError) as exc_info:
        registry.get("unknown-domain", "1.0.0")
    assert exc_info.value.issues[0].code == "DOMAIN_UNKNOWN"


def test_invalid_manifest_is_rejected(
    catalog: SchemaCatalog, tmp_path: Path
) -> None:
    pack_dir = tmp_path / "invalid"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text(
        '{"schema_version":"3.0.0","domain_id":"invalid"}',
        encoding="utf-8",
    )
    with pytest.raises(DomainPackError) as exc_info:
        DomainPackRegistry([tmp_path], catalog).discover()
    assert any(issue.code == "SCHEMA_REQUIRED" for issue in exc_info.value.issues)


def test_duplicate_domain_version_is_rejected(
    catalog: SchemaCatalog, tmp_path: Path
) -> None:
    source = DUMMY_ROOT / "dummy"
    shutil.copytree(source, tmp_path / "one")
    shutil.copytree(source, tmp_path / "two")
    with pytest.raises(DomainPackError) as exc_info:
        DomainPackRegistry([tmp_path], catalog).discover()
    assert exc_info.value.issues[0].code == "DOMAIN_DUPLICATE_VERSION"


def test_domain_pack_path_traversal_is_rejected(
    catalog: SchemaCatalog, tmp_path: Path
) -> None:
    manifest = load_json(DUMMY_ROOT / "dummy" / "manifest.json")
    manifest["policy_bundle_refs"] = ["../outside.json"]
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(DomainPackError) as exc_info:
        DomainPackRegistry([tmp_path], catalog).discover()
    assert any(
        issue.code in {"SCHEMA_PATTERN", "DOMAIN_PATH_TRAVERSAL"}
        for issue in exc_info.value.issues
    )


def test_policy_snapshot_is_deterministic(catalog: SchemaCatalog) -> None:
    registry = DomainPackRegistry([DOMAIN_ROOT], catalog)
    registry.discover()
    pack = registry.get("business-tech", "0.1.0")
    profile = load_json(sample_path("business-tech"))["domain"]["profile"]
    resolver = DomainPolicyResolver(catalog)
    first_model, first_data = resolver.resolve(pack, profile)
    second_model, second_data = resolver.resolve(pack, profile)
    assert first_model == second_model
    assert canonical_json(first_data) == canonical_json(second_data)
    assert first_data["canonical_hash"] == second_data["canonical_hash"]
    assert first_data["immutable"] is True
    assert (
        first_data
        == load_json(sample_path("business-tech"))["domain"]["policy_snapshot"]
    )


def test_pack_version_is_preserved_in_workspace(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry
) -> None:
    data = load_json(sample_path("business-tech"))
    assert WorkspaceLoader(catalog, registry=domain_registry).load(
        sample_path("business-tech")
    ).validation.is_valid
    data["project"]["domain_pack_version"] = "9.9.9"
    schema_result = catalog.validate(
        data, "workspace.schema.json", "<version-mismatch>"
    )
    assert schema_result.is_valid
    issues: list = []
    WorkspaceLoader(catalog)._validate_consistency(
        Path("<version-mismatch>"), data, {}, issues
    )
    assert any(issue.code == "WORKSPACE_PACK_VERSION_MISMATCH" for issue in issues)


def test_policy_snapshot_tampering_is_rejected(catalog: SchemaCatalog) -> None:
    data = load_json(sample_path("business-tech"))
    data["domain"]["policy_snapshot"]["resolved_policy"]["overrides"] = {
        "business-tech:tone.level": "changed"
    }
    issues: list = []
    WorkspaceLoader(catalog)._validate_consistency(
        Path("<tampered-snapshot>"), data, {}, issues
    )
    assert any(
        issue.code == "WORKSPACE_SNAPSHOT_HASH_MISMATCH" for issue in issues
    )


def test_editorial_sequence_supports_multiple_edit_events() -> None:
    data = load_json(sample_path("business-tech"))
    sequence_data = data["sequences"][0]
    assert len(sequence_data["edit_events"]) >= 2


def test_sequence_supports_multiple_video_and_audio_tracks() -> None:
    data = load_json(sample_path("business-tech"))
    tracks = data["tracks"]["tracks"]
    assert sum(track["track_type"] == "video" for track in tracks) >= 2
    assert sum(track["track_type"] == "audio" for track in tracks) >= 2
    assert set(data["sequences"][0]["track_refs"]) == {
        track["track_id"] for track in tracks
    }


def test_asset_type_and_editorial_role_are_independent(
    catalog: SchemaCatalog,
) -> None:
    asset = load_json(sample_path("business-tech"))["assets"][0]
    asset["asset_type"] = "document"
    asset["editorial_role"] = "establishing"
    result = catalog.validate(asset, "asset.schema.json", "<asset>")
    assert result.is_valid, result.issues


def test_core_contract_has_no_business_tech_mandatory_field() -> None:
    for path in sorted(SCHEMA_ROOT.glob("*.json")):
        assert "business-tech" not in path.read_text(encoding="utf-8")
    for path in sorted((REPO_ROOT / "engine").rglob("*.py")):
        assert "business-tech" not in path.read_text(encoding="utf-8")


def artifact(
    artifact_id: str,
    dependencies: list[str] | None = None,
    **overrides,
) -> dict:
    value = {
        "schema_version": "3.0.0",
        "artifact_id": artifact_id,
        "artifact_type": "source_media",
        "project_id": "prj_artifact_test",
        "sequence_id": "seq_artifact_test",
        "created_at": "2026-07-25T00:00:00Z",
        "last_accessed_at": "2026-07-25T00:00:00Z",
        "content_hash": "sha256:" + "a" * 64,
        "size_bytes": 1,
        "retention_class": "temporary",
        "dependency_ids": dependencies or [],
        "locked": False,
        "pinned": False,
        "approved": False,
        "cleanup_candidate": False,
        "producer": "test",
        "producer_version": "1.0.0",
        "job_id": None,
        "status": "ready",
        "version": 1,
    }
    value.update(overrides)
    return value


def artifact_codes(values: list[dict], catalog: SchemaCatalog) -> set[str]:
    result = validate_artifact_graph(
        values,
        catalog=catalog,
        project_ids={"prj_artifact_test"},
        sequence_ids={"seq_artifact_test"},
    )
    return {issue.code for issue in result.issues}


def test_missing_artifact_dependency_is_rejected(
    catalog: SchemaCatalog,
) -> None:
    assert "ARTIFACT_MISSING_DEPENDENCY" in artifact_codes(
        [artifact("art_test_one", ["art_missing_dep"])], catalog
    )


def test_self_dependency_is_rejected(catalog: SchemaCatalog) -> None:
    assert "ARTIFACT_SELF_DEPENDENCY" in artifact_codes(
        [artifact("art_test_self", ["art_test_self"])], catalog
    )


def test_dependency_cycle_is_rejected(catalog: SchemaCatalog) -> None:
    assert "ARTIFACT_DEPENDENCY_CYCLE" in artifact_codes(
        [
            artifact("art_cycle_one", ["art_cycle_two"]),
            artifact("art_cycle_two", ["art_cycle_one"]),
        ],
        catalog,
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"locked": True, "cleanup_candidate": True},
        {"pinned": True, "cleanup_candidate": True},
        {
            "retention_class": "final",
            "approved": True,
            "cleanup_candidate": True,
        },
    ],
)
def test_protected_artifact_cleanup_is_rejected(
    overrides: dict, catalog: SchemaCatalog
) -> None:
    assert "ARTIFACT_PROTECTED_FROM_CLEANUP" in artifact_codes(
        [artifact("art_protected_one", **overrides)], catalog
    )


def test_orphan_output_is_rejected(catalog: SchemaCatalog) -> None:
    assert "ORPHAN_OUTPUT" in artifact_codes(
        [artifact("art_output_one", artifact_type="output")], catalog
    )


def test_orphan_sequence_reference_is_rejected(
    catalog: SchemaCatalog,
) -> None:
    assert "ORPHAN_ARTIFACT" in artifact_codes(
        [artifact("art_orphan_one", sequence_id="seq_unknown_value")],
        catalog,
    )


def test_protected_retention_ttl_is_rejected(
    catalog: SchemaCatalog,
) -> None:
    policy = load_json(SAMPLE_ROOT / "retention_policy.json")
    policy["rules"][4]["ttl_days"] = 10
    policy["rules"][4]["cleanup_eligible"] = True
    result = validate_retention_policy(policy, catalog=catalog)
    assert "RETENTION_PROTECTED_TTL" in {
        issue.code for issue in result.issues
    }


def test_valid_raw_artifact_graph_uses_schema_and_semantic_validation(
    catalog: SchemaCatalog,
) -> None:
    result = validate_artifact_graph(
        [artifact("art_valid_raw")],
        catalog=catalog,
        source_file="artifact-manifest.json",
        project_ids={"prj_artifact_test"},
        sequence_ids={"seq_artifact_test"},
    )
    assert result.is_valid, result.issues


@pytest.mark.parametrize(
    ("mutation", "expected_code", "expected_pointer"),
    [
        (
            lambda value: value.update(artifact_id="invalid"),
            "SCHEMA_PATTERN",
            "/artifacts/0/artifact_id",
        ),
        (
            lambda value: value.update(content_hash="invalid"),
            "SCHEMA_PATTERN",
            "/artifacts/0/content_hash",
        ),
        (
            lambda value: value.pop("producer"),
            "SCHEMA_REQUIRED",
            "/artifacts/0",
        ),
        (
            lambda value: value.update(status="invalid"),
            "SCHEMA_ENUM",
            "/artifacts/0/status",
        ),
    ],
)
def test_schema_invalid_raw_artifact_is_rejected_before_semantics(
    catalog: SchemaCatalog,
    mutation,
    expected_code: str,
    expected_pointer: str,
) -> None:
    value = artifact("art_schema_invalid", artifact_type="output")
    mutation(value)
    result = validate_artifact_graph(
        [value],
        catalog=catalog,
        source_file="artifact-manifest.json",
    )
    issue = next(item for item in result.issues if item.code == expected_code)
    assert issue.source_file == "artifact-manifest.json"
    assert issue.json_pointer == expected_pointer
    assert "ORPHAN_OUTPUT" not in {item.code for item in result.issues}


def test_raw_artifact_graph_requires_explicit_schema_catalog() -> None:
    with pytest.raises(TypeError, match="requires catalog=SchemaCatalog"):
        validate_artifact_graph([artifact("art_catalog_required")])


def test_valid_raw_retention_policy_passes_schema_and_semantics(
    catalog: SchemaCatalog,
) -> None:
    policy = load_json(SAMPLE_ROOT / "retention_policy.json")
    result = validate_retention_policy(
        policy,
        catalog=catalog,
        source_file="retention-policy.json",
    )
    assert result.is_valid, result.issues


@pytest.mark.parametrize(
    ("mutation", "expected_code", "expected_pointer"),
    [
        (
            lambda value: value.update(schema_version="2.0.0"),
            "SCHEMA_CONST",
            "/schema_version",
        ),
        (
            lambda value: value.update(version=0),
            "SCHEMA_MINIMUM",
            "/version",
        ),
        (
            lambda value: value.update(status="invalid"),
            "SCHEMA_ENUM",
            "/status",
        ),
        (
            lambda value: value.pop("policy_id"),
            "SCHEMA_REQUIRED",
            "",
        ),
        (
            lambda value: value["rules"][0].update(
                retention_class="invalid"
            ),
            "SCHEMA_ENUM",
            "/rules/0/retention_class",
        ),
    ],
)
def test_schema_invalid_raw_retention_is_rejected_before_semantics(
    catalog: SchemaCatalog,
    mutation,
    expected_code: str,
    expected_pointer: str,
) -> None:
    policy = load_json(SAMPLE_ROOT / "retention_policy.json")
    policy["rules"][4]["ttl_days"] = 10
    policy["rules"][4]["cleanup_eligible"] = True
    mutation(policy)
    result = validate_retention_policy(
        policy,
        catalog=catalog,
        source_file="retention-policy.json",
    )
    issue = next(item for item in result.issues if item.code == expected_code)
    assert issue.source_file == "retention-policy.json"
    assert issue.json_pointer == expected_pointer
    assert "RETENTION_PROTECTED_TTL" not in {
        item.code for item in result.issues
    }


def test_raw_retention_policy_requires_explicit_schema_catalog() -> None:
    policy = load_json(SAMPLE_ROOT / "retention_policy.json")
    with pytest.raises(TypeError, match="requires catalog=SchemaCatalog"):
        validate_retention_policy(policy)


def test_private_artifact_factories_are_not_public_ingestion_api() -> None:
    assert not hasattr(ArtifactRecord, "from_dict")
    assert not hasattr(RetentionPolicy, "from_dict")


def test_negative_size_has_structured_error(catalog: SchemaCatalog) -> None:
    value = artifact("art_negative_size", size_bytes=-1)
    value["schema_version"] = "3.0.0"
    result = catalog.validate(value, "artifact.schema.json", "artifact.json")
    assert not result.is_valid
    assert any(
        issue.code == "SCHEMA_MINIMUM"
        and issue.source_file == "artifact.json"
        and issue.json_pointer == "/size_bytes"
        for issue in result.issues
    )


def test_invalid_content_hash_is_rejected(catalog: SchemaCatalog) -> None:
    value = artifact("art_invalid_hash", content_hash="not-a-hash")
    value["schema_version"] = "3.0.0"
    result = catalog.validate(value, "artifact.schema.json", "artifact.json")
    assert any(issue.code == "SCHEMA_PATTERN" for issue in result.issues)


def test_workspace_path_traversal_is_rejected(
    catalog: SchemaCatalog, tmp_path: Path
) -> None:
    data = load_json(sample_path("split-long-form"))
    data["documents"][0]["path"] = "../outside.json"
    root = tmp_path / "workspace.json"
    root.write_text(json.dumps(data), encoding="utf-8")
    result = WorkspaceLoader(catalog).load(root).validation
    assert not result.is_valid
    assert any(issue.code == "SCHEMA_PATTERN" for issue in result.issues)


def test_missing_critical_field_is_structured(catalog: SchemaCatalog) -> None:
    data = load_json(sample_path("minimal"))
    del data["workspace_id"]
    result = catalog.validate(data, "workspace.schema.json", "workspace.json")
    assert not result.is_valid
    issue = next(item for item in result.issues if item.code == "SCHEMA_REQUIRED")
    assert issue.source_file == "workspace.json"
    assert issue.json_pointer == ""
    assert "workspace_id" in issue.message


def walk_keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_keys(nested)


def test_phase2_numeric_timing_fields_are_not_in_contract() -> None:
    forbidden = {
        "frame",
        "frame_start",
        "frame_end",
        "timestamp",
        "timestamp_ms",
        "word_timeline",
        "forced_alignment",
    }
    keys = set()
    for path in (
        SCHEMA_ROOT / "sequence.schema.json",
        SCHEMA_ROOT / "events.schema.json",
        sample_path("business-tech"),
    ):
        keys.update(walk_keys(load_json(path)))
    assert keys.isdisjoint(forbidden)


def test_all_schemas_are_draft_2020_12(catalog: SchemaCatalog) -> None:
    for schema_name in catalog.schema_names:
        schema = catalog.schema(schema_name)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].startswith("https://schemas.kurgu.engine/v3/")
        assert schema["x-schema-version"] == "3.0.0"
        Draft202012Validator.check_schema(schema)


def test_format_checker_is_applied(catalog: SchemaCatalog) -> None:
    project = load_json(sample_path("minimal"))["project"]
    project["created_at"] = "not-a-date-time"
    result = catalog.validate(project, "project.schema.json", "project.json")
    assert any(issue.code == "SCHEMA_FORMAT" for issue in result.issues)


def test_true_crime_contract_example_validates(catalog: SchemaCatalog) -> None:
    path = DOMAIN_ROOT / "true-crime-legal" / "manifest.json"
    result = catalog.validate_file(path, "domain_pack.schema.json")
    assert result.is_valid, result.issues


def test_namespaced_domain_event_uses_extension_parameters(
    catalog: SchemaCatalog,
) -> None:
    event = load_json(sample_path("business-tech"))["sequences"][0][
        "audio_events"
    ][0]
    result = catalog.validate(
        event,
        "events.schema.json",
        "event.json",
    )
    assert result.is_valid, result.issues
    sequence = load_json(sample_path("business-tech"))["sequences"][0]
    assert catalog.validate(
        sequence, "sequence.schema.json", "sequence.json"
    ).is_valid


def test_undeclared_domain_event_is_rejected(catalog: SchemaCatalog) -> None:
    data = load_json(sample_path("business-tech"))
    data["sequences"][0]["audio_events"][0][
        "event_type"
    ] = "business-tech:not_declared"
    issues: list = []
    WorkspaceLoader(catalog)._validate_consistency(
        Path("<undeclared-event>"), data, {}, issues
    )
    assert any(
        issue.code == "WORKSPACE_UNDECLARED_DOMAIN_EVENT" for issue in issues
    )


def test_migration_boundary_reports_loss_explicitly(catalog: SchemaCatalog) -> None:
    contract = {
        "source_schema_version": "2.2.0",
        "target_schema_version": "3.0.0",
        "source_path": "legacy/timeline.json",
        "target_path": "workspace/project.json",
        "lossy": True,
        "unknown_fields": ["blocks[0].extra"],
        "issues": [
            {
                "severity": "warning",
                "code": "MIGRATION_UNKNOWN_FIELD",
                "message": "Unknown field requires review.",
                "source_path": "/blocks/0/extra",
            }
        ],
    }
    result = catalog.validate(
        contract, "migration_result.schema.json", "migration.json"
    )
    assert result.is_valid, result.issues


def copy_split_workspace(tmp_path: Path) -> Path:
    target = tmp_path / "split-workspace"
    shutil.copytree(SAMPLE_ROOT / "split-long-form", target)
    return target


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def load_split_copy(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    root: Path,
):
    return WorkspaceLoader(catalog, registry=domain_registry).load(
        root / "workspace.json"
    )


def test_manifest_kind_matches_correct_split_documents(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry, tmp_path: Path
) -> None:
    loaded = load_split_copy(catalog, domain_registry, copy_split_workspace(tmp_path))
    assert loaded.validation.is_valid, loaded.validation.issues


@pytest.mark.parametrize(
    ("document_kind", "replacement"),
    [
        ("asset_manifest", "artifacts/manifest.json"),
        ("track_manifest", "timing/manifest.json"),
    ],
)
def test_manifest_kind_mismatch_is_fail_closed(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
    document_kind: str,
    replacement: str,
) -> None:
    root = copy_split_workspace(tmp_path)
    workspace = load_json(root / "workspace.json")
    document = next(item for item in workspace["documents"] if item["kind"] == document_kind)
    if document_kind == "track_manifest":
        wrong_path = root / "tracks" / "wrong-manifest.json"
        wrong_path.write_text(
            (root / "timing" / "manifest.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        replacement = "tracks/wrong-manifest.json"
    document["path"] = replacement
    write_json(root / "workspace.json", workspace)
    issues = load_split_copy(catalog, domain_registry, root).validation.issues
    assert any(issue.code == "MANIFEST_KIND_MISMATCH" for issue in issues)


def test_missing_profile_document_is_rejected(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry, tmp_path: Path
) -> None:
    root = copy_split_workspace(tmp_path)
    workspace = load_json(root / "workspace.json")
    workspace["documents"] = [
        item for item in workspace["documents"] if item["kind"] != "domain_profile"
    ]
    write_json(root / "workspace.json", workspace)
    codes = {issue.code for issue in load_split_copy(catalog, domain_registry, root).validation.issues}
    assert "DOMAIN_PROFILE_NOT_FOUND" in codes


def test_missing_policy_snapshot_reference_is_rejected(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry, tmp_path: Path
) -> None:
    root = copy_split_workspace(tmp_path)
    workspace = load_json(root / "workspace.json")
    workspace["domain"]["policy_snapshot_ref"] = "domain/missing.json"
    write_json(root / "workspace.json", workspace)
    codes = {issue.code for issue in load_split_copy(catalog, domain_registry, root).validation.issues}
    assert "POLICY_SNAPSHOT_NOT_FOUND" in codes


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("root_profile", "DOMAIN_PROFILE_ID_MISMATCH"),
        ("snapshot_profile", "POLICY_SNAPSHOT_PROFILE_MISMATCH"),
        ("snapshot_domain", "POLICY_SNAPSHOT_DOMAIN_MISMATCH"),
        ("snapshot_pack", "POLICY_SNAPSHOT_PACK_VERSION_MISMATCH"),
    ],
)
def test_domain_resolution_identity_mismatches_are_rejected(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    root = copy_split_workspace(tmp_path)
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)
    snapshot_path = root / "domain" / "policy_snapshot.json"
    snapshot = load_json(snapshot_path)
    if mutation == "root_profile":
        workspace["domain"]["profile_id"] = "dpf_other_profile"
        write_json(workspace_path, workspace)
    elif mutation == "snapshot_profile":
        snapshot["profile_id"] = "dpf_other_profile"
        write_json(snapshot_path, snapshot)
    elif mutation == "snapshot_domain":
        snapshot["domain_id"] = "other-domain"
        write_json(snapshot_path, snapshot)
    else:
        snapshot["domain_pack_version"] = "9.9.9"
        write_json(snapshot_path, snapshot)
    codes = {issue.code for issue in load_split_copy(catalog, domain_registry, root).validation.issues}
    assert expected_code in codes


def test_split_snapshot_is_resolver_generated(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry
) -> None:
    root = SAMPLE_ROOT / "split-long-form"
    profile = load_json(root / "domain" / "profile.json")
    snapshot = load_json(root / "domain" / "policy_snapshot.json")
    _, resolved = DomainPolicyResolver(catalog).resolve(
        domain_registry.get("business-tech", "0.1.0"), profile
    )
    assert canonical_json(resolved) == canonical_json(snapshot)


@pytest.mark.parametrize("mutation", ["payload", "hash"])
def test_snapshot_resolver_parity_rejects_tampering(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
    mutation: str,
) -> None:
    root = copy_split_workspace(tmp_path)
    snapshot_path = root / "domain" / "policy_snapshot.json"
    snapshot = load_json(snapshot_path)
    if mutation == "payload":
        snapshot["resolved_policy"]["overrides"] = {"business-tech:tone": "changed"}
    else:
        snapshot["canonical_hash"] = "sha256:" + "0" * 64
    write_json(snapshot_path, snapshot)
    codes = {issue.code for issue in load_split_copy(catalog, domain_registry, root).validation.issues}
    assert "POLICY_SNAPSHOT_RESOLUTION_MISMATCH" in codes


def test_resolver_hash_is_deterministic_and_path_independent(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry, tmp_path: Path
) -> None:
    source = DOMAIN_ROOT / "business-tech"
    first_root = tmp_path / "packs-one"
    second_root = tmp_path / "packs-two"
    shutil.copytree(source, first_root / "business-tech")
    shutil.copytree(source, second_root / "business-tech")
    profile = load_json(SAMPLE_ROOT / "split-long-form" / "domain" / "profile.json")
    snapshots = []
    for root in (first_root, second_root):
        registry = DomainPackRegistry([root], catalog)
        registry.discover()
        _, snapshot = DomainPolicyResolver(catalog).resolve(
            registry.get("business-tech", "0.1.0"), profile
        )
        snapshots.append(snapshot)
    assert canonical_json(snapshots[0]) == canonical_json(snapshots[1])


def test_typed_event_target_resolution_and_compatibility(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry, tmp_path: Path
) -> None:
    root = tmp_path / "business-tech"
    shutil.copytree(SAMPLE_ROOT / "business-tech", root)
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)
    event = workspace["sequences"][0]["edit_events"][0]
    event["target"] = {
        "target_type": "video_track",
        "target_id": "trk_video_business_base",
    }
    write_json(workspace_path, workspace)
    assert WorkspaceLoader(catalog, registry=domain_registry).load(workspace_path).validation.is_valid

    event["target"]["target_id"] = "trk_video_missing"
    write_json(workspace_path, workspace)
    issues = WorkspaceLoader(catalog, registry=domain_registry).load(workspace_path).validation.issues
    missing = next(issue for issue in issues if issue.code == "EVENT_TARGET_NOT_FOUND")
    assert missing.json_pointer.endswith("/target/target_id")


@pytest.mark.parametrize(
    ("target", "expected_code"),
    [
        ({"target_type": "video_track", "target_id": "trk_audio_business_effects"}, "EVENT_TARGET_NOT_FOUND"),
        ({"target_type": "video_track", "target_id": "trk_video_business_base"}, "EVENT_TARGET_TYPE_MISMATCH"),
        ({"target_type": "unknown-domain:opaque", "target_id": "anything"}, "EVENT_TARGET_TYPE_INVALID"),
    ],
)
def test_invalid_event_targets_are_rejected(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
    target: dict,
    expected_code: str,
) -> None:
    root = tmp_path / "business-tech"
    shutil.copytree(SAMPLE_ROOT / "business-tech", root)
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)
    event_group = "audio_events" if expected_code == "EVENT_TARGET_TYPE_MISMATCH" else "edit_events"
    workspace["sequences"][0][event_group][0]["target"] = target
    write_json(workspace_path, workspace)
    codes = {issue.code for issue in WorkspaceLoader(catalog, registry=domain_registry).load(workspace_path).validation.issues}
    assert expected_code in codes


def test_absolute_and_symlink_workspace_boundaries_are_fail_closed(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry, tmp_path: Path
) -> None:
    root = copy_split_workspace(tmp_path)
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)
    workspace["documents"][0]["path"] = "C:\\outside.json"
    write_json(workspace_path, workspace)
    codes = {issue.code for issue in load_split_copy(catalog, domain_registry, root).validation.issues}
    assert "SCHEMA_PATTERN" in codes

    root = copy_split_workspace(tmp_path / "symlink")
    outside = tmp_path / "outside-project.json"
    outside.write_text((root / "project.json").read_text(encoding="utf-8"), encoding="utf-8")
    link = root / "outside-link.json"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink capability unavailable: {exc}")
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)
    workspace["documents"][0]["path"] = "outside-link.json"
    write_json(workspace_path, workspace)
    codes = {issue.code for issue in load_split_copy(catalog, domain_registry, root).validation.issues}
    assert "WORKSPACE_PATH_TRAVERSAL" in codes


def test_workspace_typed_view_requires_validation(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry
) -> None:
    raw = load_json(sample_path("business-tech"))
    with pytest.raises(TypeError):
        Workspace.from_dict(raw)
    loaded = WorkspaceLoader(catalog, registry=domain_registry).load(
        sample_path("business-tech")
    )
    assert loaded.workspace is not None
    assert loaded.workspace.schema_version == "3.0.0"


def test_core_only_workspace_loads_without_domain_registry(
    catalog: SchemaCatalog,
) -> None:
    loaded = WorkspaceLoader(catalog).load(sample_path("minimal"))
    assert loaded.validation.is_valid, loaded.validation.issues
    assert loaded.data["domain"]["resolution_mode"] == "core_only"


def test_domain_pack_workspace_requires_registry(catalog: SchemaCatalog) -> None:
    loaded = WorkspaceLoader(catalog).load(sample_path("business-tech"))
    issue = next(
        item
        for item in loaded.validation.issues
        if item.code == "DOMAIN_REGISTRY_REQUIRED"
    )
    assert issue.json_pointer == "/domain/resolution_mode"
    assert loaded.workspace is None


def test_self_consistent_forged_snapshot_cannot_bypass_registry(
    catalog: SchemaCatalog, tmp_path: Path
) -> None:
    root = tmp_path / "business-tech"
    shutil.copytree(SAMPLE_ROOT / "business-tech", root)
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)
    snapshot = workspace["domain"]["policy_snapshot"]
    snapshot["resolved_policy"]["overrides"] = {
        "business-tech:tone.level": "forged"
    }
    canonical_hash = policy_snapshot_hash(snapshot)
    snapshot_id = "dps_" + canonical_hash.removeprefix("sha256:")[:20]
    snapshot["canonical_hash"] = canonical_hash
    snapshot["snapshot_id"] = snapshot_id
    workspace["domain"]["policy_snapshot_id"] = snapshot_id
    workspace["project"]["policy_snapshot_id"] = snapshot_id
    write_json(root / "domain" / "policy_snapshot.json", snapshot)
    write_json(workspace_path, workspace)

    loaded = WorkspaceLoader(catalog).load(workspace_path)
    codes = {issue.code for issue in loaded.validation.issues}
    assert "DOMAIN_REGISTRY_REQUIRED" in codes
    assert "WORKSPACE_SNAPSHOT_HASH_MISMATCH" not in codes


def test_rehashed_forged_snapshot_fails_registry_resolver_parity(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
) -> None:
    root = tmp_path / "business-tech-forged-registry"
    shutil.copytree(SAMPLE_ROOT / "business-tech", root)
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)
    snapshot = workspace["domain"]["policy_snapshot"]
    snapshot["resolved_policy"]["overrides"] = {
        "business-tech:tone.level": "forged"
    }
    canonical_hash = policy_snapshot_hash(snapshot)
    snapshot_id = "dps_" + canonical_hash.removeprefix("sha256:")[:20]
    snapshot["canonical_hash"] = canonical_hash
    snapshot["snapshot_id"] = snapshot_id
    workspace["domain"]["policy_snapshot_id"] = snapshot_id
    workspace["project"]["policy_snapshot_id"] = snapshot_id
    write_json(root / "domain" / "policy_snapshot.json", snapshot)
    write_json(workspace_path, workspace)

    loaded = WorkspaceLoader(catalog, registry=domain_registry).load(
        workspace_path
    )
    issue = next(
        item
        for item in loaded.validation.issues
        if item.code == "POLICY_SNAPSHOT_RESOLUTION_MISMATCH"
        and item.json_pointer == "/domain/policy_snapshot"
    )
    assert issue.source_file == str(workspace_path.resolve())
    assert "WORKSPACE_SNAPSHOT_HASH_MISMATCH" not in {
        item.code for item in loaded.validation.issues
    }


def test_domain_pack_workspace_passes_with_correct_registry(
    catalog: SchemaCatalog, domain_registry: DomainPackRegistry
) -> None:
    loaded = WorkspaceLoader(catalog, registry=domain_registry).load(
        sample_path("business-tech")
    )
    assert loaded.validation.is_valid, loaded.validation.issues


@pytest.mark.parametrize(
    ("group_name", "wrong_track"),
    [
        ("edit_events", "trk_audio_business_effects"),
        ("overlay_events", "trk_audio_business_effects"),
        ("text_emphasis_events", "trk_audio_business_effects"),
        ("audio_events", "trk_video_business_base"),
    ],
)
def test_event_group_track_routing_is_enforced(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
    group_name: str,
    wrong_track: str,
) -> None:
    root = tmp_path / group_name
    shutil.copytree(SAMPLE_ROOT / "business-tech", root)
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)
    sequence = workspace["sequences"][0]
    if group_name == "text_emphasis_events":
        text_event = copy.deepcopy(sequence["overlay_events"][0])
        text_event["event_id"] = "evt_business_text_emphasis"
        sequence[group_name].append(text_event)
    sequence[group_name][0]["track_ref"] = wrong_track
    write_json(workspace_path, workspace)

    issues = WorkspaceLoader(catalog, registry=domain_registry).load(
        workspace_path
    ).validation.issues
    issue = next(
        item for item in issues if item.code == "EVENT_TRACK_TYPE_MISMATCH"
    )
    assert issue.json_pointer.endswith(f"/{group_name}/0/track_ref")
    assert wrong_track in issue.message


def test_base_shot_requires_video_track(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
) -> None:
    root = tmp_path / "base-shot"
    shutil.copytree(SAMPLE_ROOT / "business-tech", root)
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)
    workspace["sequences"][0]["base_shot"][
        "track_ref"
    ] = "trk_audio_business_narration"
    write_json(workspace_path, workspace)

    issues = WorkspaceLoader(catalog, registry=domain_registry).load(
        workspace_path
    ).validation.issues
    issue = next(
        item
        for item in issues
        if item.code == "BASE_SHOT_TRACK_TYPE_MISMATCH"
    )
    assert issue.json_pointer == "/sequences/0/base_shot/track_ref"


@pytest.mark.parametrize(
    ("mutation", "expected_code", "expected_pointer"),
    [
        (
            "missing_chapter",
            "SEQUENCE_CHAPTER_NOT_FOUND",
            "/sequences/0/chapter_id",
        ),
        (
            "missing_beat",
            "SEQUENCE_BEAT_NOT_FOUND",
            "/sequences/0/beat_id",
        ),
        (
            "wrong_chapter_beat",
            "SEQUENCE_BEAT_CHAPTER_MISMATCH",
            "/sequences/0/beat_id",
        ),
        (
            "chapter_membership",
            "CHAPTER_BEAT_MEMBERSHIP_MISMATCH",
            "/story/chapters/0/beat_ids/0",
        ),
    ],
)
def test_split_story_hierarchy_is_enforced(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
    mutation: str,
    expected_code: str,
    expected_pointer: str,
) -> None:
    root = copy_split_workspace(tmp_path)
    sequence_path = root / "sequences" / "sequence_01.json"
    sequence = load_json(sequence_path)
    if mutation == "missing_chapter":
        sequence["chapter_id"] = "chp_split_missing"
        write_json(sequence_path, sequence)
    elif mutation == "missing_beat":
        sequence["beat_id"] = "beat_split_missing"
        write_json(sequence_path, sequence)
    elif mutation == "wrong_chapter_beat":
        sequence["beat_id"] = "beat_split_effect"
        write_json(sequence_path, sequence)
    else:
        chapter_path = root / "story" / "chapters" / "chapter_01.json"
        chapter = load_json(chapter_path)
        chapter["beat_ids"][0] = "beat_split_effect"
        write_json(chapter_path, chapter)

    issues = load_split_copy(
        catalog, domain_registry, root
    ).validation.issues
    issue = next(item for item in issues if item.code == expected_code)
    assert issue.json_pointer == expected_pointer


def test_beat_sequence_membership_is_enforced(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
) -> None:
    root = copy_split_workspace(tmp_path)
    beat_path = root / "story" / "beats" / "beat_01.json"
    beat = load_json(beat_path)
    beat["sequence_ids"][0] = "seq_split_consequence"
    write_json(beat_path, beat)
    issues = load_split_copy(
        catalog, domain_registry, root
    ).validation.issues
    assert any(
        issue.code == "BEAT_SEQUENCE_MEMBERSHIP_MISMATCH"
        and issue.json_pointer == "/story/beats/0/sequence_ids/0"
        for issue in issues
    )


def test_public_raw_editorial_sequence_factory_is_unavailable() -> None:
    invalid_sequence = {
        "sequence_id": "invalid",
        "chapter_id": "missing",
    }
    assert not hasattr(EditorialSequence, "from_dict")
    with pytest.raises(AttributeError):
        getattr(EditorialSequence, "from_dict")(invalid_sequence)


def test_duplicate_workspace_ids_are_rejected_with_structured_codes(
    catalog: SchemaCatalog,
    domain_registry: DomainPackRegistry,
    tmp_path: Path,
) -> None:
    root = tmp_path / "duplicates"
    shutil.copytree(SAMPLE_ROOT / "business-tech", root)
    workspace_path = root / "workspace.json"
    workspace = load_json(workspace_path)

    duplicate_chapter = copy.deepcopy(workspace["story"]["chapters"][0])
    duplicate_chapter["title"] = "Duplicate chapter"
    workspace["story"]["chapters"].append(duplicate_chapter)
    duplicate_beat = copy.deepcopy(workspace["story"]["beats"][0])
    duplicate_beat["narrative_goal"] = "Duplicate beat"
    workspace["story"]["beats"].append(duplicate_beat)
    duplicate_sequence = copy.deepcopy(workspace["sequences"][0])
    duplicate_sequence["narrative_goal"] = "Duplicate sequence"
    workspace["sequences"].append(duplicate_sequence)
    duplicate_asset = copy.deepcopy(workspace["assets"][0])
    duplicate_asset["editorial_role"] = "duplicate"
    workspace["assets"].append(duplicate_asset)
    duplicate_artifact = copy.deepcopy(workspace["artifacts"][0])
    duplicate_artifact["size_bytes"] += 1
    workspace["artifacts"].append(duplicate_artifact)
    duplicate_track = copy.deepcopy(workspace["tracks"]["tracks"][0])
    duplicate_track["role"] = "duplicate"
    workspace["tracks"]["tracks"].append(duplicate_track)
    duplicate_event = copy.deepcopy(
        workspace["sequences"][0]["audio_events"][0]
    )
    duplicate_event["parameters"]["values"]["intensity"] = "duplicate"
    workspace["sequences"][0]["audio_events"].append(duplicate_event)
    write_json(workspace_path, workspace)

    issues = WorkspaceLoader(catalog, registry=domain_registry).load(
        workspace_path
    ).validation.issues
    codes = {issue.code for issue in issues}
    assert {
        "DUPLICATE_CHAPTER_ID",
        "DUPLICATE_BEAT_ID",
        "DUPLICATE_SEQUENCE_ID",
        "DUPLICATE_ASSET_ID",
        "DUPLICATE_ARTIFACT_ID",
        "DUPLICATE_TRACK_ID",
        "DUPLICATE_EVENT_ID",
    } <= codes
    duplicate_issue = next(
        issue for issue in issues if issue.code == "DUPLICATE_TRACK_ID"
    )
    assert duplicate_issue.json_pointer == "/tracks/tracks/4/track_id"
    assert "first occurrence" in duplicate_issue.message
    assert "second occurrence" in duplicate_issue.message
