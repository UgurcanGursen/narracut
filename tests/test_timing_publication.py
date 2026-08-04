from __future__ import annotations

import ast
import dataclasses
import hashlib
import io
import inspect
import os
from pathlib import Path

import pytest

import engine.contracts.timing_publication as publication
from engine.contracts.alignment_result import serialize_alignment_result
from engine.contracts.caption_groups import serialize_caption_groups
from engine.contracts.emphasis_events import serialize_emphasis_events
from engine.contracts.word_to_frame import (
    TemporalFrameRate,
    compile_word_to_frame,
    serialize_word_to_frame,
)
from tests.test_word_to_frame import _fixture_values


EXPECTED_PATHS = (
    "timing/word_timeline.json",
    "timing/caption_groups.json",
    "timing/emphasis_events.json",
)
GOLDEN_RECEIPT_BYTES = b'{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","document_id":"nardoc_fx34","emphasis_events_hash":"e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d","emphasis_events_id":"emps_e6286517914a305715e42460d2709237","files":[{"byte_length":1764,"relative_path":"timing/word_timeline.json","sha256":"c2bab562863094ae6c1d29964a86316641dfc22cc5aa2d68dcc7542d9e4aef99"},{"byte_length":2300,"relative_path":"timing/caption_groups.json","sha256":"fec81a32ef81b7ac4fb785b059d1f713edb90ea91197f72cd8a22992941da942"},{"byte_length":2121,"relative_path":"timing/emphasis_events.json","sha256":"008e79e10b989f54377af498c269eca00df09b426b4d8a0ec86441e55a13111c"}],"hash_scope_version":"TIMING-PUBLICATION-HASH-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"TIMING-PUBLICATION-V1","timing_publication_hash":"a3904a7eb60ed1c31dcbb08e5039fb134f8086c9ddf183a6097ca998fa8c5fff","timing_publication_id":"tpub_a3904a7eb60ed1c31dcbb08e5039fb13","word_to_frame_hash":"285a114d06e92fe5c431ea1e51ebafd9be72476034a7093cc6ad0ca71b090374","word_to_frame_id":"w2f_285a114d06e92fe5c431ea1e51ebafd9"}'
GOLDEN_RECEIPT_ENVELOPE_SHA256 = "3f6848ab3ded076a79a18b9259a5b9cdb30d9ae7b60d3f862217b9b4cbb44182"
GOLDEN_RECEIPT_ID = "tpub_a3904a7eb60ed1c31dcbb08e5039fb13"


@pytest.fixture()
def fx():
    result, groups, events = _fixture_values()
    word_to_frame = compile_word_to_frame(
        alignment_result=result,
        caption_groups=groups,
        emphasis_events=events,
        frame_rate=TemporalFrameRate(30, 1),
    )
    return result, groups, events, word_to_frame


def _kwargs(fx, root: Path, **changes):
    result, groups, events, word_to_frame = fx
    values = {
        "alignment_result": result,
        "caption_groups": groups,
        "emphasis_events": events,
        "word_to_frame": word_to_frame,
        "project_root": root,
    }
    values.update(changes)
    return values


def _assert_error(exc, reason, pointer):
    assert type(exc.value) is publication.TimingPublicationContractError
    assert exc.value.reason is reason
    assert exc.value.pointer == pointer
    assert exc.value.issue_code is None
    assert str(exc.value) == f"Timing publication rejected: {reason.value}"


def _canonical(value):
    from engine.contracts._canonical_json import encode_canonical_json_bytes

    return encode_canonical_json_bytes(value)


def test_public_surface_models_enum_and_signature_are_exact():
    assert [
        publication.TIMING_PUBLICATION_V1,
        publication.TIMING_PUBLICATION_HASH_V1,
    ] == ["TIMING-PUBLICATION-V1", "TIMING-PUBLICATION-HASH-V1"]
    assert [item.value for item in publication.TimingPublicationRejectionReason] == [
        "STRUCTURE_INVALID",
        "DEPENDENCY_CONTENT_DRIFT",
        "DEPENDENCY_BINDING_INVALID",
        "PATH_INVALID",
        "TARGET_EXISTS",
        "WRITE_FAILED",
        "VERIFY_FAILED",
        "PROMOTION_FAILED",
        "IDENTITY_MISMATCH",
        "NOT_MATERIALIZED",
    ]
    assert [field.name for field in dataclasses.fields(publication.PublishedTimingFile)] == [
        "relative_path", "sha256", "byte_length"
    ]
    assert [field.name for field in dataclasses.fields(publication.TimingPublicationReceipt)] == [
        "schema_version", "hash_scope_version", "timing_publication_id",
        "timing_publication_hash", "project_id", "document_id",
        "narration_revision_id", "narration_revision_hash", "alignment_result_id",
        "alignment_result_hash", "caption_groups_id", "caption_groups_hash",
        "emphasis_events_id", "emphasis_events_hash", "word_to_frame_id",
        "word_to_frame_hash", "files",
    ]
    assert all(cls.__dataclass_params__.frozen for cls in (
        publication.PublishedTimingFile, publication.TimingPublicationReceipt
    ))
    assert list(inspect.signature(publication.publish_timing_artifacts).parameters) == [
        "alignment_result", "caption_groups", "emphasis_events", "word_to_frame", "project_root"
    ]
    assert list(inspect.signature(publication.serialize_timing_publication_receipt).parameters) == ["receipt"]


def test_success_publishes_exact_retained_canonical_bytes_and_registered_receipt(fx, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    receipt = publication.publish_timing_artifacts(**_kwargs(fx, root))
    expected = (
        serialize_alignment_result(fx[0]),
        serialize_caption_groups(fx[1]),
        serialize_emphasis_events(fx[2]),
    )
    assert tuple(item.relative_path for item in receipt.files) == EXPECTED_PATHS
    assert (root / "timing").is_dir()
    for item, payload in zip(receipt.files, expected, strict=True):
        path = root / Path(item.relative_path)
        assert path.read_bytes() == payload
        assert item.byte_length == len(payload)
        assert item.sha256 == hashlib.sha256(payload).hexdigest()
    envelope = publication.serialize_timing_publication_receipt(receipt)
    assert envelope == GOLDEN_RECEIPT_BYTES
    assert len(envelope) == 1488
    assert hashlib.sha256(envelope).hexdigest() == GOLDEN_RECEIPT_ENVELOPE_SHA256
    assert receipt.timing_publication_id == GOLDEN_RECEIPT_ID
    assert envelope == _canonical(dataclasses.asdict(receipt))
    projection = dict(dataclasses.asdict(receipt))
    projection.pop("timing_publication_id")
    projection.pop("timing_publication_hash")
    digest = hashlib.sha256(_canonical(projection)).hexdigest()
    assert receipt.timing_publication_hash == digest
    assert receipt.timing_publication_id == "tpub_" + digest[:32]


def test_independent_equivalent_chains_and_roots_have_identical_receipt_identity(tmp_path):
    left_fx = _fixture_values()
    right_fx = _fixture_values()
    left_w2f = compile_word_to_frame(
        alignment_result=left_fx[0], caption_groups=left_fx[1], emphasis_events=left_fx[2],
        frame_rate=TemporalFrameRate(30, 1),
    )
    right_w2f = compile_word_to_frame(
        alignment_result=right_fx[0], caption_groups=right_fx[1], emphasis_events=right_fx[2],
        frame_rate=TemporalFrameRate(30, 1),
    )
    left_root, right_root = tmp_path / "left", tmp_path / "right"
    left_root.mkdir(); right_root.mkdir()
    left = publication.publish_timing_artifacts(**_kwargs((*left_fx, left_w2f), left_root))
    right = publication.publish_timing_artifacts(**_kwargs((*right_fx, right_w2f), right_root))
    assert left == right
    assert publication.serialize_timing_publication_receipt(left) == publication.serialize_timing_publication_receipt(right)


@pytest.mark.parametrize("bad", ["root", object(), Path("relative")])
def test_project_root_type_or_absolute_path_is_rejected_before_dependency_or_io(fx, tmp_path, monkeypatch, bad):
    touched = []
    monkeypatch.setattr(publication, "serialize_alignment_result", lambda value: touched.append(value) or b"bad")
    with pytest.raises((TypeError, publication.TimingPublicationContractError)) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, bad))
    assert touched == []
    if type(bad) is Path:
        _assert_error(exc, publication.TimingPublicationRejectionReason.PATH_INVALID, "/project_root")


def test_absolute_parent_traversal_is_rejected_before_dependency_or_io(fx, tmp_path, monkeypatch):
    touched = []
    monkeypatch.setattr(publication, "serialize_alignment_result", lambda value: touched.append(value) or b"bad")
    root = (tmp_path / "project" / "..").absolute()
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.PATH_INVALID, "/project_root")
    assert touched == []


@pytest.mark.parametrize("hostile", ["root", "parent"])
def test_project_root_and_parent_reparse_are_path_invalid_before_target_preflight(fx, tmp_path, monkeypatch, hostile):
    root = tmp_path / "project"; root.mkdir()
    original = publication._path_state

    def simulated_reparse(path):
        if hostile == "root" and path == root:
            return True, True
        if hostile == "parent" and path == root.parent:
            return True, True
        return original(path)

    monkeypatch.setattr(publication, "_path_state", simulated_reparse)
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.PATH_INVALID, "/project_root")
    assert not (root / "timing").exists()


def test_real_project_root_symlink_is_path_invalid(fx, tmp_path):
    real_root = tmp_path / "real"; real_root.mkdir()
    linked_root = tmp_path / "linked"
    try:
        linked_root.symlink_to(real_root, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("symlink privilege is unavailable on this host")
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, linked_root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.PATH_INVALID, "/project_root")


@pytest.mark.parametrize(
    ("input_name", "serializer_name", "pointer"),
    [
        ("alignment_result", "serialize_alignment_result", "/alignment_result"),
        ("caption_groups", "serialize_caption_groups", "/caption_groups"),
        ("emphasis_events", "serialize_emphasis_events", "/emphasis_events"),
        ("word_to_frame", "serialize_word_to_frame", "/word_to_frame"),
    ],
)
def test_each_materialization_failure_precedes_filesystem(fx, tmp_path, monkeypatch, input_name, serializer_name, pointer):
    root = tmp_path / "project"; root.mkdir()
    def fail(_):
        raise ValueError("secret host path must not escape")
    monkeypatch.setattr(publication, serializer_name, fail)
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.DEPENDENCY_CONTENT_DRIFT, pointer)
    assert not (root / "timing").exists()


@pytest.mark.parametrize(
    ("dependency_index", "field", "pointer"),
    [
        (1, "project_id", "/caption_groups"),
        (2, "document_id", "/emphasis_events"),
        (2, "caption_groups_id", "/emphasis_events"),
        (3, "narration_revision_hash", "/word_to_frame"),
        (3, "caption_groups_hash", "/word_to_frame"),
        (3, "emphasis_events_hash", "/word_to_frame"),
    ],
)
def test_lineage_matrix_rows_reject_at_authoritative_right_pointer(fx, tmp_path, monkeypatch, dependency_index, field, pointer):
    root = tmp_path / "project"; root.mkdir()
    values = list(fx)
    values[dependency_index] = dataclasses.replace(values[dependency_index], **{field: "binding_mismatch"})
    # Isolate matrix precedence from provenance registries of the upstream contracts.
    monkeypatch.setattr(publication, "serialize_alignment_result", lambda _: b"alignment")
    monkeypatch.setattr(publication, "serialize_caption_groups", lambda _: b"captions")
    monkeypatch.setattr(publication, "serialize_emphasis_events", lambda _: b"emphasis")
    monkeypatch.setattr(publication, "serialize_word_to_frame", lambda _: b"frames")
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(tuple(values), root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.DEPENDENCY_BINDING_INVALID, pointer)
    assert not (root / "timing").exists()


@pytest.mark.parametrize(
    ("dependency_index", "first_field", "second_field", "pointer"),
    [
        (1, "project_id", "document_id", "/caption_groups"),
        (2, "project_id", "document_id", "/emphasis_events"),
        (2, "caption_groups_id", "caption_groups_hash", "/emphasis_events"),
        (3, "project_id", "document_id", "/word_to_frame"),
        (3, "caption_groups_id", "caption_groups_hash", "/word_to_frame"),
        (3, "emphasis_events_id", "emphasis_events_hash", "/word_to_frame"),
    ],
)
def test_lineage_matrix_all_six_rows_have_deterministic_first_field_precedence(
    fx, tmp_path, monkeypatch, dependency_index, first_field, second_field, pointer,
):
    root = tmp_path / "project"; root.mkdir()
    values = list(fx)
    values[dependency_index] = dataclasses.replace(
        values[dependency_index], **{
            first_field: "first_field_mismatch",
            second_field: "second_field_mismatch",
        }
    )
    for serializer_name in (
        "serialize_alignment_result", "serialize_caption_groups",
        "serialize_emphasis_events", "serialize_word_to_frame",
    ):
        monkeypatch.setattr(publication, serializer_name, lambda _: b"canonical")
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(tuple(values), root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.DEPENDENCY_BINDING_INVALID, pointer)
    assert not (root / "timing").exists()


def test_existing_target_and_owned_staging_are_fail_closed_without_overwrite(fx, tmp_path):
    root = tmp_path / "project"; root.mkdir()
    (root / "timing").mkdir()
    (root / "timing" / "unrelated.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.TARGET_EXISTS, "/timing")
    assert (root / "timing" / "unrelated.txt").read_text(encoding="utf-8") == "keep"


def test_owned_staging_exists_is_target_exists_before_any_write(fx, tmp_path):
    identity_root = tmp_path / "identity"; identity_root.mkdir()
    receipt = publication.publish_timing_artifacts(**_kwargs(fx, identity_root))
    root = tmp_path / "project"; root.mkdir()
    staging = root / f".timing-publication-{receipt.timing_publication_id}.staging"
    staging.mkdir()
    (staging / "unrelated.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.TARGET_EXISTS, "/timing")
    assert (staging / "unrelated.txt").read_text(encoding="utf-8") == "keep"
    assert not (root / "timing").exists()


@pytest.mark.parametrize("hostile", ["target", "staging"])
def test_reparse_precedes_existing_target_for_target_and_owned_staging(fx, tmp_path, monkeypatch, hostile):
    root = tmp_path / "project"; root.mkdir()
    original = publication._path_state

    def simulated_junction(path):
        if hostile == "target" and path == root / "timing":
            return True, True
        if hostile == "staging" and path.name.startswith(".timing-publication-"):
            return True, True
        return original(path)

    monkeypatch.setattr(publication, "_path_state", simulated_junction)
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.PATH_INVALID, "/timing")
    assert not (root / "timing").exists()


def test_real_symlink_target_is_path_invalid_before_target_exists(fx, tmp_path):
    root = tmp_path / "project"; root.mkdir()
    target = root / "timing"
    try:
        target.symlink_to(tmp_path / "outside", target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("symlink privilege is unavailable on this host")
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.PATH_INVALID, "/timing")


def test_write_fault_leaves_no_target_or_owned_staging(fx, tmp_path, monkeypatch):
    root = tmp_path / "project"; root.mkdir()
    real_fsync = os.fsync
    calls = 0

    def fail_first_fsync(fd):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("host detail must not escape")
        return real_fsync(fd)

    monkeypatch.setattr(publication.os, "fsync", fail_first_fsync)
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.WRITE_FAILED, "/timing/word_timeline.json")
    assert not (root / "timing").exists()
    assert not list(root.glob(".timing-publication-*.staging"))


def test_reread_payload_mismatch_is_verify_failed_and_cleans_owned_staging(fx, tmp_path, monkeypatch):
    root = tmp_path / "project"; root.mkdir()
    real_open = Path.open

    def corrupted_reread(path, mode="r", *args, **kwargs):
        if path.name == "word_timeline.json" and mode == "rb":
            return io.BytesIO(b"corrupt")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(publication.Path, "open", corrupted_reread)
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.VERIFY_FAILED, "/timing/word_timeline.json")
    assert not (root / "timing").exists()
    assert not list(root.glob(".timing-publication-*.staging"))


def test_promotion_fault_leaves_no_target_or_owned_staging(fx, tmp_path, monkeypatch):
    root = tmp_path / "project"; root.mkdir()

    def fail_no_replace(source, target):
        raise OSError("promotion host detail")

    monkeypatch.setattr(publication.os, "rename", fail_no_replace)
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.PROMOTION_FAILED, "/timing")
    assert not (root / "timing").exists()
    assert not list(root.glob(".timing-publication-*.staging"))


def test_no_replace_race_preserves_new_target_and_never_overwrites_it(fx, tmp_path, monkeypatch):
    root = tmp_path / "project"; root.mkdir()

    def race_creates_target(source, target):
        Path(target).mkdir()
        (Path(target) / "race-sentinel.txt").write_text("keep", encoding="utf-8")
        raise FileExistsError("target appeared")

    monkeypatch.setattr(publication.os, "rename", race_creates_target)
    with pytest.raises(publication.TimingPublicationContractError) as exc:
        publication.publish_timing_artifacts(**_kwargs(fx, root))
    _assert_error(exc, publication.TimingPublicationRejectionReason.PROMOTION_FAILED, "/timing")
    assert (root / "timing" / "race-sentinel.txt").read_text(encoding="utf-8") == "keep"
    assert not list(root.glob(".timing-publication-*.staging"))


def test_implementation_import_boundary_is_exact_and_has_no_forbidden_runtime_subsystems():
    source = Path(publication.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imported.add("." * node.level + (node.module or ""))
    assert imported == {
        "hashlib", "os", "stat", "weakref", "dataclasses", "enum", "pathlib", "typing",
        "._canonical_json", ".alignment_result", ".caption_groups", ".emphasis_events", ".word_to_frame",
    }
    forbidden = {"fastapi", "requests", "httpx", "ffmpeg", "moviepy", "remotion", "v2", "PIL", "sqlite3"}
    assert not any(name.split(".")[0] in forbidden for name in imported)


def test_receipt_serialization_rejects_caller_constructed_and_mutated_receipts(fx, tmp_path):
    root = tmp_path / "project"; root.mkdir()
    genuine = publication.publish_timing_artifacts(**_kwargs(fx, root))
    for forged in (
        dataclasses.replace(genuine),
        publication.TimingPublicationReceipt(**dataclasses.asdict(genuine)),
        dataclasses.replace(genuine, timing_publication_hash="0" * 64),
    ):
        with pytest.raises(publication.TimingPublicationContractError) as exc:
            publication.serialize_timing_publication_receipt(forged)
        assert exc.value.reason in {
            publication.TimingPublicationRejectionReason.NOT_MATERIALIZED,
            publication.TimingPublicationRejectionReason.IDENTITY_MISMATCH,
        }
