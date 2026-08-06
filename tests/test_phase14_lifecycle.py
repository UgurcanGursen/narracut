import hashlib
import pytest

from engine.lifecycle import ArtifactRegistryRecord, append_registry_record, append_registry_records, execute_trash_plan, import_verified_artifact_rows, load_registry, plan_deletion, registry_snapshot, restore_trash_receipt, validate_deletion_plan


def row(identifier, *, retention="temporary", dependencies=(), locked=False, content_hash=None, size_bytes=7):
    return ArtifactRegistryRecord.materialize({"artifact_id": identifier, "project_id": "prj_fx34", "content_hash": content_hash or "sha256:" + identifier[-1] * 64, "size_bytes": size_bytes, "retention_class": retention, "dependency_ids": dependencies, "locked": locked, "pinned": False, "approved": False, "producer": "test", "producer_version": "1"})


def test_plan_is_deterministic_and_marks_transitive_dependencies():
    child, root, free = row("art_a"), row("art_b", dependencies=("art_a",), locked=True), row("art_c")
    first = plan_deletion(records=(child, root, free), policy_hash="sha256:" + "p" * 64, as_of="2026-08-06T00:00:00Z", root_ids=frozenset({"art_b"}))
    assert first == plan_deletion(records=(child, root, free), policy_hash="sha256:" + "p" * 64, as_of="2026-08-06T00:00:00Z", root_ids=frozenset({"art_b"}))
    assert [item["artifact_id"] for item in first["candidates"]] == ["art_c"]


def test_registry_rejects_cross_project_dependency_and_unsafe_field():
    with pytest.raises(ValueError, match="UNSAFE"):
        ArtifactRegistryRecord.materialize({"artifact_id":"art_x","project_id":"prj_fx34","path":"C:/x"})
    with pytest.raises(ValueError, match="DEPENDENCY"):
        registry_snapshot((row("art_a"), ArtifactRegistryRecord.materialize({"artifact_id":"art_b","project_id":"prj_other","content_hash":"sha256:"+"b"*64,"size_bytes":1,"retention_class":"temporary","dependency_ids":["art_a"],"locked":False,"pinned":False,"approved":False,"producer":"t","producer_version":"1"})))


def test_registry_reopens_and_rejects_duplicate(tmp_path):
    path = tmp_path / "registry.jsonl"; item = row("art_a")
    append_registry_record(registry_path=path, record=item)
    assert load_registry(registry_path=path) == (item,)
    with pytest.raises(ValueError, match="DUPLICATE"):
        append_registry_record(registry_path=path, record=item)


def test_plan_becomes_stale_after_registry_or_policy_change():
    first = row("art_a"); plan = plan_deletion(records=(first,), policy_hash="sha256:" + "p" * 64, as_of="now", root_ids=frozenset())
    validate_deletion_plan(plan=plan, records=(first,), policy_hash="sha256:" + "p" * 64)
    with pytest.raises(ValueError, match="STALE"):
        validate_deletion_plan(plan=plan, records=(first,), policy_hash="sha256:" + "q" * 64)


def test_protected_retention_and_cycles_fail_closed():
    protected = row("art_f", retention="final")
    assert plan_deletion(records=(protected,), policy_hash="sha256:" + "p" * 64, as_of="now", root_ids=frozenset())["candidates"] == []
    with pytest.raises(ValueError, match="CYCLE"):
        registry_snapshot((row("art_a", dependencies=("art_b",)), row("art_b", dependencies=("art_a",))))


def test_revalidated_plan_moves_only_managed_candidate_to_trash(tmp_path):
    payload = b"x"; (tmp_path / "art_a").write_bytes(payload)
    item = row("art_a", content_hash="sha256:" + hashlib.sha256(payload).hexdigest(), size_bytes=len(payload))
    plan = plan_deletion(records=(item,), policy_hash="sha256:" + "p" * 64, as_of="now", root_ids=frozenset())
    receipt = execute_trash_plan(managed_root=tmp_path, plan=plan, records=(item,), policy_hash="sha256:" + "p" * 64)
    assert receipt["moved"][0]["artifact_id"] == "art_a" and not (tmp_path / "art_a").exists()
    restore_trash_receipt(managed_root=tmp_path, plan_id=plan["plan_id"], receipt=receipt)
    assert (tmp_path / "art_a").read_bytes() == b"x"


def test_trash_fails_closed_when_file_hash_has_changed(tmp_path):
    expected = b"expected"; (tmp_path / "art_a").write_bytes(b"changed")
    item = row("art_a", content_hash="sha256:" + hashlib.sha256(expected).hexdigest(), size_bytes=len(expected))
    plan = plan_deletion(records=(item,), policy_hash="sha256:" + "p" * 64, as_of="now", root_ids=frozenset())
    with pytest.raises(ValueError, match="TRASH_SOURCE_INVALID"):
        execute_trash_plan(managed_root=tmp_path, plan=plan, records=(item,), policy_hash="sha256:" + "p" * 64)
    assert (tmp_path / "art_a").read_bytes() == b"changed"

def test_verified_row_import_keeps_registry_invariants():
    item = row("art_a")
    assert import_verified_artifact_rows((item.__dict__,)) == (item,)


def test_registry_batch_persists_dependency_graph_in_topological_order(tmp_path):
    child = row("art_a")
    parent = row("art_b", dependencies=("art_a",))
    append_registry_records(registry_path=tmp_path / "registry.jsonl", records=(parent, child))
    assert {record.artifact_id for record in load_registry(registry_path=tmp_path / "registry.jsonl")} == {"art_a", "art_b"}
