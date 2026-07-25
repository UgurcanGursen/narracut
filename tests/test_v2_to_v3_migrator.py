from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from engine.contracts import DomainPackRegistry, SchemaCatalog, WorkspaceLoader
from engine.migration import (
    MigrationIOError,
    MigrationOptions,
    V2ToV3Migrator,
    migrate,
    migrate_file,
    source_leaf_pointers,
)
from engine.migration.io import write_outcome
from engine.migration.reporting import (
    render_inspection_summary,
    render_migration_report,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "schema" / "v3"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "migration"
PHASE0_FIXTURE = (
    REPO_ROOT / "baseline" / "fixtures" / "phase0_offline_full_render.json"
)
DEMO_ROOT = REPO_ROOT / "samples" / "migration" / "v2-to-v3"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def catalog() -> SchemaCatalog:
    return SchemaCatalog(SCHEMA_ROOT)


@pytest.fixture
def migrator(catalog: SchemaCatalog) -> V2ToV3Migrator:
    return V2ToV3Migrator(catalog)


@pytest.fixture
def valid_source() -> dict:
    return load_json(FIXTURE_ROOT / "valid_v2.json")


@pytest.fixture
def unsupported_source() -> dict:
    return load_json(FIXTURE_ROOT / "unsupported_v2.json")


@pytest.fixture
def phase0_source() -> dict:
    return load_json(PHASE0_FIXTURE)


@pytest.fixture
def business_registry(catalog: SchemaCatalog) -> DomainPackRegistry:
    registry = DomainPackRegistry([REPO_ROOT / "domain-packs"], catalog)
    registry.discover()
    return registry


def permissive() -> MigrationOptions:
    return MigrationOptions(mode="permissive", resolution_mode="core_only")


def strict() -> MigrationOptions:
    return MigrationOptions(mode="strict", resolution_mode="core_only")


def recursively_reverse(value):
    if isinstance(value, dict):
        return {
            key: recursively_reverse(value[key])
            for key in reversed(list(value))
        }
    if isinstance(value, list):
        return [recursively_reverse(item) for item in value]
    return value


def issue_codes(outcome) -> set[str]:
    return {item["code"] for item in outcome.result["issues"]}


def issue_for(outcome, code: str) -> dict:
    return next(
        item for item in outcome.result["issues"] if item["code"] == code
    )


def cli_command(source: Path, output: Path, *extra: str) -> list[str]:
    return [
        sys.executable,
        "-B",
        "-m",
        "engine.migration.cli",
        "migrate",
        "--input",
        str(source),
        "--output",
        str(output),
        *extra,
    ]


def run_cli(source: Path, output: Path, *extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        cli_command(source, output, *extra),
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


# Basic migration


def test_real_v2_fixture_migrates_permissively(
    migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    outcome = migrator.migrate(phase0_source, permissive())
    assert outcome.status == "SUCCESS_WITH_LOSS"
    assert outcome.workspace is not None


def test_workspace_passes_canonical_schema(
    catalog: SchemaCatalog, migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    outcome = migrator.migrate(valid_source, strict())
    result = catalog.validate(
        outcome.workspace, "workspace.schema.json", "workspace.json"
    )
    assert result.is_valid, result.issues


def test_workspace_passes_public_loader(
    catalog: SchemaCatalog, valid_source: dict, tmp_path: Path
) -> None:
    output = tmp_path / "output"
    migrate_file(
        FIXTURE_ROOT / "valid_v2.json",
        output,
        catalog=catalog,
        options=strict(),
    )
    loaded = WorkspaceLoader(catalog).load(output / "workspace.json")
    assert loaded.validation.is_valid, loaded.validation.issues


def test_result_passes_canonical_schema(
    catalog: SchemaCatalog, migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    outcome = migrator.migrate(phase0_source, permissive())
    result = catalog.validate(
        outcome.result, "migration_result.schema.json", "migration_result.json"
    )
    assert result.is_valid, result.issues


def test_input_mapping_is_not_mutated(
    migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    before = copy.deepcopy(phase0_source)
    migrator.migrate(phase0_source, permissive())
    assert phase0_source == before


def test_object_key_order_does_not_change_output(
    migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    first = migrator.migrate(phase0_source, permissive())
    second = migrator.migrate(
        recursively_reverse(phase0_source), permissive()
    )
    assert first == second


def test_two_core_migrations_are_object_identical(
    migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    assert migrator.migrate(
        phase0_source, permissive()
    ) == migrator.migrate(phase0_source, permissive())


def test_two_cli_migrations_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "one"
    second = tmp_path / "two"
    args = ("--mode", "strict", "--resolution-mode", "core_only")
    assert run_cli(FIXTURE_ROOT / "valid_v2.json", first, *args).returncode == 0
    assert run_cli(FIXTURE_ROOT / "valid_v2.json", second, *args).returncode == 0
    assert {
        path.name: path.read_bytes() for path in first.iterdir()
    } == {path.name: path.read_bytes() for path in second.iterdir()}


# Source-field coverage


def test_every_source_leaf_is_accounted_once(
    migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    outcome = migrator.migrate(phase0_source, permissive())
    mapped = Counter(
        item["source_pointer"]
        for item in outcome.result["mappings"]
        if item["source_pointer"]
    )
    assert set(mapped) == set(source_leaf_pointers(phase0_source))
    assert set(mapped.values()) == {1}


def test_unknown_root_field_is_unaccounted(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["mystery"] = "value"
    outcome = migrator.migrate(valid_source, permissive())
    issue = issue_for(outcome, "MIGRATION_UNACCOUNTED_SOURCE_FIELD")
    assert issue["source_pointer"] == "/mystery"
    assert outcome.status == "FAILED"


def test_nested_unknown_field_has_exact_pointer(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["runtime"] = {"retry": 3}
    outcome = migrator.migrate(valid_source, permissive())
    issue = issue_for(outcome, "MIGRATION_UNACCOUNTED_SOURCE_FIELD")
    assert issue["source_pointer"] == "/blocks/0/runtime/retry"


def test_unknown_list_field_preserves_index_pointer(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["visuals"][0]["mystery"] = [
        {"value": "x"}
    ]
    outcome = migrator.migrate(valid_source, permissive())
    issue = issue_for(outcome, "MIGRATION_UNACCOUNTED_SOURCE_FIELD")
    assert (
        issue["source_pointer"]
        == "/blocks/0/visuals/0/mystery/0/value"
    )


def test_empty_container_is_not_misreported_as_leaf(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["visuals"][0]["extra"]["empty"] = {}
    outcome = migrator.migrate(valid_source, strict())
    assert "MIGRATION_UNACCOUNTED_SOURCE_FIELD" not in issue_codes(outcome)


# Strict and permissive


def test_lossless_strict_migration_succeeds(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    outcome = migrator.migrate(valid_source, strict())
    assert outcome.status == "SUCCESS"
    assert outcome.result["lossy"] is False


def test_defaulted_value_is_safe_in_strict_mode(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["visuals"][0]["offset_end"] = "AUTO"
    outcome = migrator.migrate(valid_source, strict())
    assert outcome.status == "SUCCESS_WITH_LOSS"
    assert outcome.workspace is not None
    assert "MIGRATION_FIELD_DEFAULTED" in issue_codes(outcome)


def test_unsupported_field_fails_strict_mode(
    migrator: V2ToV3Migrator, unsupported_source: dict
) -> None:
    outcome = migrator.migrate(unsupported_source, strict())
    assert outcome.status == "FAILED"
    assert outcome.workspace is None
    assert "MIGRATION_FIELD_DROPPED" in issue_codes(outcome)


def test_safe_unsupported_field_is_permissive_loss(
    migrator: V2ToV3Migrator, unsupported_source: dict
) -> None:
    outcome = migrator.migrate(unsupported_source, permissive())
    assert outcome.status == "SUCCESS_WITH_LOSS"
    assert outcome.workspace is not None


def test_bgm_contract_is_reported_not_unaccounted(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["bgm"] = {
        "enabled": True,
        "track_id": "legacy_theme",
        "gain_db": -22.0,
        "fade_in": 1.0,
        "fade_out": 1.0,
    }
    outcome = migrator.migrate(valid_source, permissive())
    assert outcome.status == "SUCCESS_WITH_LOSS"
    assert "MIGRATION_FIELD_UNSUPPORTED" in issue_codes(outcome)
    assert "MIGRATION_UNACCOUNTED_SOURCE_FIELD" not in issue_codes(outcome)


@pytest.mark.parametrize("mode", ["strict", "permissive"])
def test_ambiguous_reference_fails_both_modes(
    migrator: V2ToV3Migrator, valid_source: dict, mode: str
) -> None:
    valid_source["blocks"][0]["visuals"][0]["extra"][
        "resolved_path"
    ] = "../escape.mp4"
    outcome = migrator.migrate(
        valid_source, MigrationOptions(mode=mode)
    )
    assert outcome.status == "FAILED"
    assert "MIGRATION_REFERENCE_AMBIGUOUS" in issue_codes(outcome)


class InvalidTargetMigrator(V2ToV3Migrator):
    def _workspace(self, *args, **kwargs):
        workspace = super()._workspace(*args, **kwargs)
        workspace["status"] = "not-valid"
        return workspace


@pytest.mark.parametrize("mode", ["strict", "permissive"])
def test_invalid_target_fails_both_modes(
    catalog: SchemaCatalog, valid_source: dict, mode: str
) -> None:
    outcome = InvalidTargetMigrator(catalog).migrate(
        valid_source, MigrationOptions(mode=mode)
    )
    assert outcome.status == "FAILED"
    assert "MIGRATION_TARGET_INVALID" in issue_codes(outcome)


# Identity and reference behavior


def test_stable_source_id_is_normalized(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    workspace = migrator.migrate(valid_source, strict()).workspace
    assert workspace["story"]["beats"][0]["beat_id"] == "beat_clean_intro"
    assert workspace["sequences"][0]["sequence_id"] == "seq_clean_intro"
    assert workspace["assets"][0]["asset_id"] == "ast_clean_intro_visual"


def test_missing_ids_are_deterministically_derived(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    del valid_source["blocks"][0]["block_id"]
    del valid_source["blocks"][0]["visuals"][0]["extra"]["asset_id"]
    first = migrator.migrate(valid_source, strict()).workspace
    second = migrator.migrate(valid_source, strict()).workspace
    assert first["sequences"][0]["sequence_id"] == second["sequences"][0][
        "sequence_id"
    ]
    assert first["assets"][0]["asset_id"] == second["assets"][0]["asset_id"]


def test_same_source_pointer_produces_same_id(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    del valid_source["blocks"][0]["visuals"][0]["extra"]["asset_id"]
    first = migrator.migrate(valid_source, strict()).workspace["assets"][0]
    second = migrator.migrate(valid_source, strict()).workspace["assets"][0]
    assert first["asset_id"] == second["asset_id"]


def test_id_collision_is_structured(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    duplicate = copy.deepcopy(valid_source["blocks"][0]["visuals"][0])
    valid_source["blocks"][0]["visuals"].append(duplicate)
    outcome = migrator.migrate(valid_source, permissive())
    issue = issue_for(outcome, "MIGRATION_ID_COLLISION")
    assert issue["details"]["proposed_target_id"] == "ast_clean_intro_visual"
    assert issue["details"]["target_collection"] == "assets"
    assert len(issue["details"]["source_pointers"]) == 2


def test_missing_visual_reference_is_structured(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["visuals"] = []
    outcome = migrator.migrate(valid_source, permissive())
    issue = issue_for(outcome, "MIGRATION_REFERENCE_MISSING")
    assert issue["source_pointer"] == "/blocks/0/visuals"
    assert outcome.workspace is None


def test_success_has_no_dangling_asset_or_track_reference(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    workspace = migrator.migrate(valid_source, strict()).workspace
    assets = {item["asset_id"] for item in workspace["assets"]}
    tracks = {
        item["track_id"] for item in workspace["tracks"]["tracks"]
    }
    for sequence in workspace["sequences"]:
        assert sequence["base_shot"]["asset_ref"] in assets
        assert set(sequence["track_refs"]) <= tracks
        for event in sequence["edit_events"]:
            assert event["target"]["target_id"] in assets
            assert event["track_ref"] in tracks


# Domain resolution


def test_core_only_needs_no_registry(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    outcome = migrator.migrate(valid_source, strict())
    assert outcome.workspace["domain"]["resolution_mode"] == "core_only"


def test_domain_pack_without_registry_is_rejected(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    outcome = migrator.migrate(
        valid_source,
        MigrationOptions(
            mode="permissive",
            resolution_mode="domain_pack",
            domain_id="business-tech",
            domain_pack_version="0.1.0",
            profile={},
        ),
    )
    assert "MIGRATION_DOMAIN_CONFIGURATION_REQUIRED" in issue_codes(outcome)
    assert outcome.status == "FAILED"


def test_domain_pack_uses_real_registry_and_resolver(
    catalog: SchemaCatalog,
    migrator: V2ToV3Migrator,
    valid_source: dict,
    business_registry: DomainPackRegistry,
) -> None:
    profile = load_json(
        REPO_ROOT / "samples/v3/business-tech/domain/profile.json"
    )
    options = MigrationOptions(
        mode="strict",
        resolution_mode="domain_pack",
        registry=business_registry,
        domain_id="business-tech",
        domain_pack_version="0.1.0",
        profile=profile,
    )
    outcome = migrator.migrate(valid_source, options)
    assert outcome.status == "SUCCESS"
    assert outcome.result["validation"]["workspace_loader_valid"]


def test_wrong_domain_version_is_rejected(
    migrator: V2ToV3Migrator,
    valid_source: dict,
    business_registry: DomainPackRegistry,
) -> None:
    profile = load_json(
        REPO_ROOT / "samples/v3/business-tech/domain/profile.json"
    )
    outcome = migrator.migrate(
        valid_source,
        MigrationOptions(
            mode="strict",
            resolution_mode="domain_pack",
            registry=business_registry,
            domain_id="business-tech",
            domain_pack_version="9.9.9",
            profile=profile,
        ),
    )
    assert outcome.status == "FAILED"
    assert "MIGRATION_DOMAIN_CONFIGURATION_REQUIRED" in issue_codes(outcome)


def test_resolved_snapshot_passes_file_loader_parity(
    catalog: SchemaCatalog,
    valid_source: dict,
    business_registry: DomainPackRegistry,
    tmp_path: Path,
) -> None:
    profile_path = REPO_ROOT / "samples/v3/business-tech/domain/profile.json"
    options = MigrationOptions(
        mode="strict",
        resolution_mode="domain_pack",
        registry=business_registry,
        domain_id="business-tech",
        domain_pack_version="0.1.0",
        profile=load_json(profile_path),
    )
    outcome = migrate_file(
        FIXTURE_ROOT / "valid_v2.json",
        tmp_path / "domain-output",
        catalog=catalog,
        options=options,
    )
    loaded = WorkspaceLoader(catalog, registry=business_registry).load(
        tmp_path / "domain-output/workspace.json"
    )
    assert outcome.status == "SUCCESS"
    assert loaded.validation.is_valid, loaded.validation.issues


def test_core_migrator_has_no_business_tech_literal() -> None:
    for path in (REPO_ROOT / "engine/migration").glob("*.py"):
        assert "business-tech" not in path.read_text(encoding="utf-8")


def test_dummy_domain_pack_needs_no_core_change(
    catalog: SchemaCatalog,
    migrator: V2ToV3Migrator,
    valid_source: dict,
) -> None:
    registry = DomainPackRegistry(
        [REPO_ROOT / "tests/fixtures/domain-packs"], catalog
    )
    registry.discover()
    profile = {
        "schema_version": "3.0.0",
        "profile_id": "dpf_dummy_default",
        "domain_id": "dummy-domain",
        "domain_pack_version": "1.0.0",
        "enabled_extensions": [],
        "policy_overrides": {},
        "status": "ready",
        "version": 1,
    }
    outcome = migrator.migrate(
        valid_source,
        MigrationOptions(
            mode="strict",
            resolution_mode="domain_pack",
            registry=registry,
            domain_id="dummy-domain",
            domain_pack_version="1.0.0",
            profile=profile,
        ),
    )
    assert outcome.status == "SUCCESS"
    assert outcome.workspace["domain"]["domain_id"] == "dummy-domain"


# Loss reporting


def test_defaulted_field_has_structured_entry(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["visuals"][0]["offset_end"] = "AUTO"
    issue = issue_for(
        migrator.migrate(valid_source, permissive()),
        "MIGRATION_FIELD_DEFAULTED",
    )
    assert issue["classification"] == "DEFAULTED"


def test_dropped_field_has_structured_entry(
    migrator: V2ToV3Migrator, unsupported_source: dict
) -> None:
    issue = issue_for(
        migrator.migrate(unsupported_source, permissive()),
        "MIGRATION_FIELD_DROPPED",
    )
    assert issue["source_pointer"].endswith("/fit_mode")


def test_unsupported_field_has_structured_entry(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["audio_file"] = "narration.wav"
    issue = issue_for(
        migrator.migrate(valid_source, permissive()),
        "MIGRATION_FIELD_UNSUPPORTED",
    )
    assert issue["source_pointer"] == "/blocks/0/audio_file"


def test_ambiguous_field_has_structured_entry(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["visuals"][0]["extra"][
        "resolved_path"
    ] = "../escape.mp4"
    issue = issue_for(
        migrator.migrate(valid_source, permissive()),
        "MIGRATION_REFERENCE_AMBIGUOUS",
    )
    assert issue["classification"] == "AMBIGUOUS"


def test_every_issue_has_source_pointer(
    migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    outcome = migrator.migrate(phase0_source, permissive())
    assert all("source_pointer" in item for item in outcome.result["issues"])


def test_issue_destination_is_preserved_when_available(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["visuals"][0]["offset_end"] = "AUTO"
    issue = issue_for(
        migrator.migrate(valid_source, permissive()),
        "MIGRATION_FIELD_DEFAULTED",
    )
    assert issue["destination_pointer"].endswith("/edit_events/0")


def test_counts_match_mapping_and_issue_lists(
    migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    result = migrator.migrate(phase0_source, permissive()).result
    assert sum(result["counts"]["classifications"].values()) == len(
        result["mappings"]
    )
    assert sum(result["counts"]["severities"].values()) == len(
        result["issues"]
    )


def test_markdown_report_matches_result(
    migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    outcome = migrator.migrate(phase0_source, permissive())
    report = render_migration_report(outcome)
    assert f"**{outcome.status}**" in report
    for name, count in outcome.result["counts"]["classifications"].items():
        assert f"| {name} | {count} |" in report


def test_inspection_summary_has_real_workspace_counts(
    migrator: V2ToV3Migrator, phase0_source: dict
) -> None:
    outcome = migrator.migrate(phase0_source, permissive())
    summary = render_inspection_summary(outcome)
    assert (
        "chapters=1, beats=2, sequences=2, assets=4, "
        "artifacts=4, tracks=2, events=4"
    ) in summary


# Schema and security


def test_malformed_v2_root_is_structured(
    catalog: SchemaCatalog,
) -> None:
    outcome = V2ToV3Migrator(catalog).migrate([], permissive())  # type: ignore[arg-type]
    assert outcome.status == "FAILED"
    assert "MIGRATION_SOURCE_INVALID" in issue_codes(outcome)
    validation = catalog.validate(
        outcome.result, "migration_result.schema.json", "result.json"
    )
    assert validation.is_valid, validation.issues


def test_wrong_source_block_type_is_rejected(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0] = "not-an-object"
    outcome = migrator.migrate(valid_source, permissive())
    assert outcome.status == "FAILED"
    assert "MIGRATION_SOURCE_INVALID" in issue_codes(outcome)


def test_secret_value_is_not_copied(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    secret = "sk-" + "super-secret-token"
    valid_source["api_key"] = secret
    outcome = migrator.migrate(valid_source, permissive())
    assert secret not in json.dumps(outcome.result, sort_keys=True)
    assert outcome.workspace is None


def test_secret_redaction_is_structured(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["authorization_token"] = "Bearer " + "abcdefghijklmnop"
    issue = issue_for(
        migrator.migrate(valid_source, permissive()),
        "MIGRATION_SECRET_REDACTED",
    )
    assert issue["severity"] == "ERROR"
    assert issue["source_pointer"] == "/authorization_token"


@pytest.mark.parametrize("mode", ["strict", "permissive"])
@pytest.mark.parametrize(
    ("uri", "pointer"),
    [
        (
            "https://audit-user:audit-password@example.invalid/path",
            "/blocks/0/visuals/0/url",
        ),
        (
            "https://audit-user@example.invalid/path",
            "/blocks/0/visuals/0/url",
        ),
        (
            "https://audit-user:audit-password@[invalid",
            "/blocks/0/visuals/0/url",
        ),
        (
            "https://example.invalid/path#auth=audit-fragment",
            "/blocks/0/visuals/0/url",
        ),
        (
            "https://example.invalid/path\n?view=public",
            "/blocks/0/visuals/0/url",
        ),
    ],
)
def test_uri_credentials_fail_closed_without_artifact_leakage(
    migrator: V2ToV3Migrator,
    valid_source: dict,
    mode: str,
    uri: str,
    pointer: str,
) -> None:
    valid_source["blocks"][0]["visuals"][0]["url"] = uri
    outcome = migrator.migrate(
        valid_source,
        MigrationOptions(mode=mode, source_path="security-input.json"),
    )
    rendered = "\n".join(
        (
            json.dumps(outcome.workspace, sort_keys=True),
            json.dumps(outcome.result, sort_keys=True),
            render_migration_report(outcome),
            render_inspection_summary(outcome),
        )
    )
    issue = issue_for(outcome, "MIGRATION_SECRET_REDACTED")
    assert outcome.status == "FAILED"
    assert outcome.workspace is None
    assert issue["source_pointer"] == pointer
    assert uri not in rendered
    assert "audit-password" not in rendered
    assert "audit-fragment" not in rendered


@pytest.mark.parametrize(
    "query_key",
    [
        "token",
        "access_token",
        "refresh-token",
        "IdToken",
        "auth",
        "authorization",
        "api_key",
        "Api-Key",
        "APIKEY",
        "client_secret",
        "password",
        "passwd",
        "pwd",
        "credential",
        "credentials",
        "signature",
        "sig",
        "X-Amz-Signature",
        "X-Amz-Credential",
        "X-Amz-Security-Token",
        "X-Goog-Signature",
        "X-Goog-Credential",
        "AWSAccessKeyId",
        "x-api-key",
    ],
)
def test_sensitive_uri_query_keys_fail_closed(
    migrator: V2ToV3Migrator,
    valid_source: dict,
    query_key: str,
) -> None:
    marker = "synthetic-audit-credential"
    uri = f"https://example.invalid/media?view=public&{query_key}={marker}"
    valid_source["blocks"][0]["visuals"][0]["url"] = uri
    outcome = migrator.migrate(valid_source, permissive())
    rendered = "\n".join(
        (
            json.dumps(outcome.workspace, sort_keys=True),
            json.dumps(outcome.result, sort_keys=True),
            render_migration_report(outcome),
            render_inspection_summary(outcome),
        )
    )
    issue = issue_for(outcome, "MIGRATION_SECRET_REDACTED")
    assert outcome.status == "FAILED"
    assert outcome.workspace is None
    assert issue["source_pointer"] == "/blocks/0/visuals/0/url"
    assert marker not in rendered
    assert uri not in rendered


@pytest.mark.parametrize(
    ("field", "value", "pointer"),
    [
        (
            "selected_asset_url",
            "https://audit-user:audit-password@example.invalid/media",
            "/blocks/0/visuals/0/selected_asset_url",
        ),
        (
            "query",
            "auth=synthetic-audit-credential",
            "/blocks/0/visuals/0/query",
        ),
        (
            "logo_url",
            "https://example.invalid/logo?api_key=synthetic-audit-credential",
            "/blocks/0/visuals/0/logo_url",
        ),
    ],
)
def test_all_visual_uri_paths_use_security_boundary(
    migrator: V2ToV3Migrator,
    valid_source: dict,
    field: str,
    value: str,
    pointer: str,
) -> None:
    visual = valid_source["blocks"][0]["visuals"][0]
    visual["extra"].pop("resolved_path")
    visual[field] = value
    outcome = migrator.migrate(valid_source, permissive())
    rendered = json.dumps(
        {
            "workspace": outcome.workspace,
            "result": outcome.result,
            "report": render_migration_report(outcome),
            "summary": render_inspection_summary(outcome),
        },
        sort_keys=True,
    )
    assert outcome.status == "FAILED"
    assert outcome.workspace is None
    assert issue_for(
        outcome, "MIGRATION_SECRET_REDACTED"
    )["source_pointer"] == pointer
    assert value not in rendered
    assert "synthetic-audit-credential" not in rendered
    assert "audit-password" not in rendered


def test_open_extra_uri_is_checked_for_credentials(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    value = "https://example.invalid/provider?signature=synthetic-signature"
    pointer = "/blocks/0/visuals/0/extra/provider_uri"
    valid_source["blocks"][0]["visuals"][0]["extra"]["provider_uri"] = value
    outcome = migrator.migrate(valid_source, permissive())
    assert outcome.status == "FAILED"
    assert outcome.workspace is None
    assert issue_for(
        outcome, "MIGRATION_SECRET_REDACTED"
    )["source_pointer"] == pointer
    assert value not in json.dumps(outcome.result, sort_keys=True)


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.invalid/media?view=public&language=tr",
        "https://example.invalid/media?monkey=capuchin&public_key=reference",
    ],
)
def test_safe_https_query_does_not_trigger_secret_detection(
    migrator: V2ToV3Migrator, valid_source: dict, uri: str
) -> None:
    visual = valid_source["blocks"][0]["visuals"][0]
    visual["extra"].pop("resolved_path")
    visual["url"] = uri
    outcome = migrator.migrate(valid_source, strict())
    assert outcome.status == "SUCCESS"
    assert outcome.workspace is not None
    assert outcome.workspace["assets"][0]["provenance"]["origin_uri"] == uri
    assert "MIGRATION_SECRET_REDACTED" not in issue_codes(outcome)


def test_failed_result_does_not_publish_target_metadata(
    catalog: SchemaCatalog,
    migrator: V2ToV3Migrator,
    unsupported_source: dict,
) -> None:
    outcome = migrator.migrate(unsupported_source, strict())
    result = outcome.result
    report = render_migration_report(outcome)
    summary = render_inspection_summary(outcome)
    assert outcome.status == "FAILED"
    assert outcome.workspace is None
    assert result["target_fingerprint"] is None
    assert result["workspace_id"] is None
    assert result["validation"]["workspace_schema_valid"] is False
    assert result["validation"]["workspace_loader_valid"] is False
    assert "Workspace published: **no**" in report
    assert "Target fingerprint: `not published`" in report
    assert "Workspace ID: `not published`" in report
    assert "target_workspace_id: not_published" in summary
    assert "workspace.json" not in summary
    validation = catalog.validate(
        result, "migration_result.schema.json", "failed-result.json"
    )
    assert validation.is_valid, validation.issues


@pytest.mark.parametrize("source_fixture", ["valid_v2.json", "unsupported_v2.json"])
def test_published_results_keep_target_metadata(
    catalog: SchemaCatalog,
    source_fixture: str,
) -> None:
    source = load_json(FIXTURE_ROOT / source_fixture)
    outcome = V2ToV3Migrator(catalog).migrate(source, permissive())
    assert outcome.status in {"SUCCESS", "SUCCESS_WITH_LOSS"}
    assert outcome.workspace is not None
    assert outcome.result["target_fingerprint"] is not None
    assert outcome.result["workspace_id"] == outcome.workspace["workspace_id"]


@pytest.mark.parametrize("mode", ["strict", "permissive"])
@pytest.mark.parametrize(
    ("container", "pointer"),
    [
        ("bgm", "/bgm/audit_unknown"),
        ("sfx", "/blocks/0/visuals/0/sfx/audit_unknown"),
    ],
)
def test_unknown_bgm_and_sfx_fields_fail_closed(
    migrator: V2ToV3Migrator,
    valid_source: dict,
    mode: str,
    container: str,
    pointer: str,
) -> None:
    if container == "bgm":
        valid_source["bgm"] = {"audit_unknown": False}
    else:
        valid_source["blocks"][0]["visuals"][0]["sfx"] = {
            "audit_unknown": 0
        }
    outcome = migrator.migrate(
        valid_source, MigrationOptions(mode=mode)
    )
    issue = issue_for(outcome, "MIGRATION_UNACCOUNTED_SOURCE_FIELD")
    assert outcome.status == "FAILED"
    assert outcome.workspace is None
    assert issue["severity"] == "ERROR"
    assert issue["source_pointer"] == pointer


@pytest.mark.parametrize(
    ("container", "pointer"),
    [
        ("bgm", "/bgm/enabled/audit_nested"),
        ("sfx", "/blocks/0/visuals/0/sfx/enabled/audit_nested"),
    ],
)
def test_nested_unknown_bgm_and_sfx_fields_have_exact_pointer(
    migrator: V2ToV3Migrator,
    valid_source: dict,
    container: str,
    pointer: str,
) -> None:
    if container == "bgm":
        valid_source["bgm"] = {"enabled": {"audit_nested": True}}
    else:
        valid_source["blocks"][0]["visuals"][0]["sfx"] = {
            "enabled": {"audit_nested": True}
        }
    outcome = migrator.migrate(valid_source, permissive())
    issue = issue_for(outcome, "MIGRATION_UNACCOUNTED_SOURCE_FIELD")
    assert outcome.status == "FAILED"
    assert issue["source_pointer"] == pointer


def test_known_sfx_fields_keep_structured_loss_behavior(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    valid_source["blocks"][0]["visuals"][0]["sfx"] = {
        "enabled": True,
        "asset_id": "legacy_sfx",
        "trigger_cue": "impact",
        "gain_db": -3.0,
        "max_duration": 1.0,
    }
    outcome = migrator.migrate(valid_source, permissive())
    assert outcome.status == "SUCCESS_WITH_LOSS"
    assert "MIGRATION_FIELD_UNSUPPORTED" in issue_codes(outcome)
    assert "MIGRATION_UNACCOUNTED_SOURCE_FIELD" not in issue_codes(outcome)


def test_failed_secret_cli_has_no_artifact_or_console_leakage(
    tmp_path: Path,
) -> None:
    secret_value = "synthetic-cli-audit-credential"
    raw_uri = (
        "https://example.invalid/media?access_token=" + secret_value
    )
    source_data = load_json(FIXTURE_ROOT / "valid_v2.json")
    source_data["blocks"][0]["visuals"][0]["url"] = raw_uri
    source = tmp_path / "secret-input.json"
    source.write_text(json.dumps(source_data), encoding="utf-8")
    output = tmp_path / "secret-output"
    result = run_cli(
        source,
        output,
        "--mode",
        "permissive",
        "--resolution-mode",
        "core_only",
    )
    artifact_payload = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(output.iterdir())
        if path.is_file()
    )
    combined = result.stdout + result.stderr + artifact_payload
    migration_result = load_json(output / "migration_result.json")
    assert result.returncode == 3
    assert migration_result["status"] == "FAILED"
    assert migration_result["target_fingerprint"] is None
    assert migration_result["workspace_id"] is None
    assert not (output / "workspace.json").exists()
    assert raw_uri not in combined
    assert secret_value not in combined


@pytest.mark.parametrize("mode", ["strict", "permissive"])
@pytest.mark.parametrize(
    ("field", "pointer"),
    [
        (
            "selected_asset_url",
            "/blocks/0/visuals/0/selected_asset_url",
        ),
        (
            "extra.resolved_path",
            "/blocks/0/visuals/0/extra/resolved_path",
        ),
        ("logo_url", "/blocks/0/visuals/0/logo_url"),
        (
            "extra.provider_uri",
            "/blocks/0/visuals/0/extra/provider_uri",
        ),
    ],
)
def test_secondary_provenance_credentials_fail_closed(
    catalog: SchemaCatalog,
    valid_source: dict,
    tmp_path: Path,
    mode: str,
    field: str,
    pointer: str,
) -> None:
    marker = "synthetic-secondary-credential"
    value = f"audit-user:{marker}@example.invalid/path"
    visual = valid_source["blocks"][0]["visuals"][0]
    visual["url"] = "https://example.invalid/safe-primary"
    if field.startswith("extra."):
        visual["extra"][field.removeprefix("extra.")] = value
    else:
        visual[field] = value

    outcome = V2ToV3Migrator(catalog).migrate(
        valid_source, MigrationOptions(mode=mode)
    )
    issue = issue_for(outcome, "MIGRATION_SECRET_REDACTED")
    rendered = json.dumps(
        {
            "workspace": outcome.workspace,
            "result": outcome.result,
            "report": render_migration_report(outcome),
            "summary": render_inspection_summary(outcome),
        },
        sort_keys=True,
    )
    assert outcome.status == "FAILED"
    assert outcome.workspace is None
    assert issue["severity"] == "ERROR"
    assert issue["source_pointer"] == pointer
    assert value not in rendered
    assert marker not in rendered
    assert outcome.result["target_fingerprint"] is None
    assert outcome.result["workspace_id"] is None
    assert "target_workspace_id: not_published" in rendered

    source = tmp_path / f"{field.replace('.', '-')}-{mode}.json"
    source.write_text(json.dumps(valid_source), encoding="utf-8")
    output = tmp_path / f"{field.replace('.', '-')}-{mode}-output"
    process = run_cli(
        source,
        output,
        "--mode",
        mode,
        "--resolution-mode",
        "core_only",
    )
    artifacts = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(output.iterdir())
        if path.is_file()
    )
    combined = process.stdout + process.stderr + artifacts
    cli_result = load_json(output / "migration_result.json")
    cli_issue = next(
        item
        for item in cli_result["issues"]
        if item["code"] == "MIGRATION_SECRET_REDACTED"
    )
    assert process.returncode == 3
    assert cli_result["status"] == "FAILED"
    assert cli_issue["source_pointer"] == pointer
    assert cli_issue["severity"] == "ERROR"
    assert not (output / "workspace.json").exists()
    assert cli_result["target_fingerprint"] is None
    assert cli_result["workspace_id"] is None
    assert "target_workspace_id: not_published" in artifacts
    assert "workspace.json" not in render_inspection_summary(outcome)
    assert value not in combined
    assert marker not in combined


@pytest.mark.parametrize(
    "value",
    [
        "audit-user:synthetic-password@example.invalid/path",
        "audit-user@example.invalid/path",
        "//audit-user:synthetic-password@example.invalid/path",
        "audit-user : synthetic-password @ example.invalid/path",
        "audit-user%3Asynthetic-password%40example.invalid/path",
    ],
)
def test_uri_context_rejects_scheme_less_user_info_variants(
    migrator: V2ToV3Migrator,
    valid_source: dict,
    value: str,
) -> None:
    visual = valid_source["blocks"][0]["visuals"][0]
    visual["url"] = "https://example.invalid/safe-primary"
    visual["selected_asset_url"] = value
    outcome = migrator.migrate(valid_source, permissive())
    issue = issue_for(outcome, "MIGRATION_SECRET_REDACTED")
    rendered = json.dumps(
        {"workspace": outcome.workspace, "result": outcome.result},
        sort_keys=True,
    )
    assert outcome.status == "FAILED"
    assert outcome.workspace is None
    assert issue["source_pointer"] == (
        "/blocks/0/visuals/0/selected_asset_url"
    )
    assert value not in rendered


def test_normal_text_email_and_colon_are_not_uri_false_positives(
    migrator: V2ToV3Migrator,
    valid_source: dict,
) -> None:
    valid_source["blocks"][0]["narration"] = (
        "Contact editor@example.invalid; label:value remains editorial text."
    )
    outcome = migrator.migrate(valid_source, strict())
    assert outcome.status == "SUCCESS"
    assert outcome.workspace is not None
    assert "MIGRATION_SECRET_REDACTED" not in issue_codes(outcome)


def test_safe_secondary_provenance_values_do_not_trigger_security_error(
    migrator: V2ToV3Migrator,
    valid_source: dict,
) -> None:
    visual = valid_source["blocks"][0]["visuals"][0]
    visual["url"] = "https://example.invalid/safe-primary"
    visual["selected_asset_url"] = "https://cdn.example.invalid/safe-secondary"
    visual["logo_url"] = "https://cdn.example.invalid/logo.png"
    visual["extra"]["resolved_path"] = r"C:\media\safe-clip.mp4"
    visual["extra"]["provider_uri"] = "provider.example.invalid/resource"
    outcome = migrator.migrate(valid_source, permissive())
    assert outcome.status == "SUCCESS_WITH_LOSS"
    assert outcome.workspace is not None
    assert "MIGRATION_SECRET_REDACTED" not in issue_codes(outcome)


def test_absolute_source_path_is_portably_encoded(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    absolute = r"C:\Users\person\media\clip.mp4"
    valid_source["blocks"][0]["visuals"][0]["extra"][
        "resolved_path"
    ] = absolute
    outcome = migrator.migrate(valid_source, strict())
    payload = json.dumps(
        {"workspace": outcome.workspace, "result": outcome.result}
    )
    assert absolute not in payload
    assert "urn:kurgu:v2-local:" in payload


def test_output_has_no_wall_clock_timestamp(
    migrator: V2ToV3Migrator, valid_source: dict
) -> None:
    outcome = migrator.migrate(valid_source, strict())
    payload = json.dumps(outcome.workspace)
    assert "1970-01-01T00:00:00Z" in payload
    assert "2026-07-25T" not in payload


def test_invalid_target_errors_are_transferred(
    catalog: SchemaCatalog, valid_source: dict
) -> None:
    outcome = InvalidTargetMigrator(catalog).migrate(
        valid_source, permissive()
    )
    issue = issue_for(outcome, "MIGRATION_TARGET_INVALID")
    assert issue["destination_pointer"] == "/status"
    assert outcome.result["validation"]["target_issues"]


# IO and CLI


def test_output_traversal_is_rejected(
    catalog: SchemaCatalog, valid_source: dict, tmp_path: Path
) -> None:
    outcome = migrate(valid_source, catalog=catalog, options=strict())
    with pytest.raises(MigrationIOError, match="traversal"):
        write_outcome(
            outcome,
            tmp_path / ".." / "escape",
            catalog=catalog,
            options=strict(),
        )


def test_nonempty_output_requires_overwrite(
    catalog: SchemaCatalog, tmp_path: Path
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "existing.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(MigrationIOError, match="not empty"):
        migrate_file(
            FIXTURE_ROOT / "valid_v2.json",
            output,
            catalog=catalog,
            options=strict(),
        )


def test_explicit_overwrite_is_safe(
    catalog: SchemaCatalog, tmp_path: Path
) -> None:
    output = tmp_path / "output"
    migrate_file(
        FIXTURE_ROOT / "valid_v2.json",
        output,
        catalog=catalog,
        options=strict(),
    )
    first = (output / "workspace.json").read_bytes()
    migrate_file(
        FIXTURE_ROOT / "valid_v2.json",
        output,
        catalog=catalog,
        options=strict(),
        overwrite=True,
    )
    assert (output / "workspace.json").read_bytes() == first


def test_failed_migration_leaves_no_workspace(
    catalog: SchemaCatalog, tmp_path: Path
) -> None:
    source = tmp_path / "failed.json"
    data = load_json(FIXTURE_ROOT / "valid_v2.json")
    data["unknown"] = True
    source.write_text(json.dumps(data), encoding="utf-8")
    output = tmp_path / "failed-output"
    outcome = migrate_file(
        source,
        output,
        catalog=catalog,
        options=permissive(),
    )
    assert outcome.status == "FAILED"
    assert not (output / "workspace.json").exists()
    assert (output / "migration_result.json").exists()
    assert (output / "migration_report.md").exists()


def test_cli_success_exit_code(tmp_path: Path) -> None:
    result = run_cli(
        FIXTURE_ROOT / "valid_v2.json",
        tmp_path / "success",
        "--mode",
        "strict",
        "--resolution-mode",
        "core_only",
    )
    assert result.returncode == 0, result.stderr
    assert "status: SUCCESS" in result.stdout


def test_cli_strict_rejection_exit_code(tmp_path: Path) -> None:
    result = run_cli(
        FIXTURE_ROOT / "unsupported_v2.json",
        tmp_path / "strict-rejected",
        "--mode",
        "strict",
        "--resolution-mode",
        "core_only",
    )
    assert result.returncode == 2, result.stderr
    assert "status: FAILED" in result.stdout


def test_cli_failed_exit_code(tmp_path: Path) -> None:
    source = tmp_path / "failed.json"
    data = load_json(FIXTURE_ROOT / "valid_v2.json")
    data["api_key"] = "sk-" + "super-secret-token"
    source.write_text(json.dumps(data), encoding="utf-8")
    result = run_cli(
        source,
        tmp_path / "failed",
        "--mode",
        "permissive",
        "--resolution-mode",
        "core_only",
    )
    assert result.returncode == 3, result.stderr


def test_cli_help_is_usable() -> None:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "engine.migration.cli", "--help"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Example:" in result.stdout
    assert "--resolution-mode" in result.stdout


def test_demo_command_reproduces_expected_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "demo"
    result = run_cli(
        DEMO_ROOT / "input_v2.json",
        output,
        "--mode",
        "permissive",
        "--resolution-mode",
        "core_only",
    )
    assert result.returncode == 0, result.stderr
    expected = DEMO_ROOT / "expected"
    assert {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in output.iterdir()
    } == {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in expected.iterdir()
    }
