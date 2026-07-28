from __future__ import annotations

import copy
import dataclasses
import hashlib
import pickle

import pytest

import engine.contracts.temporal as temporal_contracts
from engine.contracts import (
    CanonicalRawPackage,
    STABLE_ISSUE_CODES,
    RawPackageRejectionReason,
    TemporalRawPackageError,
    canonicalize_temporal_raw_package,
    load_temporal_raw_package,
    validate_issue_codes,
)


FX20_PACKAGE = {
    "schema_version": "TRP-RAW-V1",
    "run_id": "run_fx20",
    "raw_id": "raw_fx20",
    "payload": {
        "tokens": [
            {"text": "A", "start_us": 0, "index": 0, "end_us": 1_000_000},
            {
                "text": "clear",
                "start_us": 1_000_000,
                "index": 1,
                "end_us": 2_000_000,
            },
            {
                "text": "result",
                "start_us": 2_000_000,
                "index": 2,
                "end_us": 3_000_000,
            },
        ],
        "language": "en",
    },
    "payload_byte_hash": (
        "sha256:492acc757b2708c21663a294117c418351e1037b"
        "afce0259c409eda2b17c0db5"
    ),
    "media_type": "application/vnd.kurgu.temporal-raw+json",
    "issue_codes": [],
}
FX20_PAYLOAD_BYTES = (
    b'{"language":"en","tokens":[{"end_us":1000000,"index":0,'
    b'"start_us":0,"text":"A"},{"end_us":2000000,"index":1,'
    b'"start_us":1000000,"text":"clear"},{"end_us":3000000,"index":2,'
    b'"start_us":2000000,"text":"result"}]}'
)
FX20_CANONICAL_BYTES = (
    b'{"issue_codes":[],"media_type":"application/vnd.kurgu.temporal-raw+json",'
    b'"payload":{"language":"en","tokens":[{"end_us":1000000,"index":0,'
    b'"start_us":0,"text":"A"},{"end_us":2000000,"index":1,'
    b'"start_us":1000000,"text":"clear"},{"end_us":3000000,"index":2,'
    b'"start_us":2000000,"text":"result"}]},"payload_byte_hash":'
    b'"sha256:492acc757b2708c21663a294117c418351e1037bafce0259c409eda2b17c0db5",'
    b'"raw_id":"raw_fx20",'
    b'"run_id":"run_fx20","schema_version":"TRP-RAW-V1"}'
)
FX20_CANONICAL_HASH = (
    "sha256:4c33882460f8cd26bd773a939bfd3e789edea04b"
    "28eaad88974b0e808754983e"
)


def canonicalize_fx20(
    package: dict | None = None,
    *,
    payload_bytes: bytes = FX20_PAYLOAD_BYTES,
):
    return canonicalize_temporal_raw_package(
        FX20_PACKAGE if package is None else package,
        payload_bytes=payload_bytes,
    )


def test_fx20_has_exact_canonical_bytes_and_hash() -> None:
    result = canonicalize_fx20()

    assert FX20_PACKAGE["payload_byte_hash"] == (
        "sha256:" + hashlib.sha256(FX20_PAYLOAD_BYTES).hexdigest()
    )
    assert result.canonical_bytes == FX20_CANONICAL_BYTES
    assert result.canonical_hash == FX20_CANONICAL_HASH
    assert not result.canonical_bytes.startswith(b"\xef\xbb\xbf")
    assert not result.canonical_bytes.endswith(b"\n")
    assert result.canonical_hash == (
        "sha256:" + hashlib.sha256(result.canonical_bytes).hexdigest()
    )
    assert temporal_contracts._is_materialized_raw_package(result)


def test_independent_materialization_paths_are_byte_and_hash_equal() -> None:
    source = (
        b'{ "run_id": "run_fx20", "schema_version": "TRP-RAW-V1",'
        b' "payload": {"tokens": ['
        b'{"text":"A","start_us":0,"index":0,"end_us":1000000},'
        b'{"text":"clear","start_us":1000000,"index":1,"end_us":2000000},'
        b'{"text":"result","start_us":2000000,"index":2,"end_us":3000000}'
        b'], "language":"en"}, "raw_id":"raw_fx20", "issue_codes":[],'
        b' "media_type":"application/vnd.kurgu.temporal-raw+json",'
        b' "payload_byte_hash":'
        b'"sha256:492acc757b2708c21663a294117c418351e1037bafce0259c409eda2b17c0db5" }'
    )

    logical = canonicalize_fx20()
    parsed = load_temporal_raw_package(
        source,
        payload_bytes=FX20_PAYLOAD_BYTES,
    )

    assert parsed.canonical_bytes == logical.canonical_bytes
    assert parsed.canonical_hash == logical.canonical_hash
    assert temporal_contracts._is_materialized_raw_package(logical)
    assert temporal_contracts._is_materialized_raw_package(parsed)


def test_object_insertion_order_does_not_change_bytes() -> None:
    reversed_root = dict(reversed(list(FX20_PACKAGE.items())))

    assert (
        canonicalize_fx20(reversed_root).canonical_bytes
        == FX20_CANONICAL_BYTES
    )


def test_semantic_array_order_changes_bytes_and_hash() -> None:
    first = copy.deepcopy(FX20_PACKAGE)
    second = copy.deepcopy(FX20_PACKAGE)
    first["alternatives"] = ["alpha", "beta"]
    second["alternatives"] = ["beta", "alpha"]

    first_result = canonicalize_fx20(first)
    second_result = canonicalize_fx20(second)

    assert first_result.canonical_bytes != second_result.canonical_bytes
    assert first_result.canonical_hash != second_result.canonical_hash


def test_nfc_equivalent_inputs_have_equal_bytes_and_hashes() -> None:
    composed = copy.deepcopy(FX20_PACKAGE)
    decomposed = copy.deepcopy(FX20_PACKAGE)
    composed["label"] = "caf\u00e9"
    decomposed["label"] = "cafe\u0301"

    assert canonicalize_fx20(composed) == canonicalize_fx20(decomposed)


def test_nfc_key_collision_is_rejected() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["labels"] = {
        "caf\u00e9": "composed",
        "cafe\u0301": "decomposed",
    }

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_fx20(package)

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.NORMALIZED_KEY_COLLISION
    )


@pytest.mark.parametrize("value", ["\ud800", "\ufdd0"])
def test_forbidden_unicode_values_are_rejected(value: str) -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["label"] = value

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_fx20(package)

    assert exc_info.value.reason is RawPackageRejectionReason.INVALID_UNICODE


def test_string_escaping_uses_exact_contract_forms() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["escaped"] = '"\\/\n\t'

    result = canonicalize_fx20(package)

    assert b'"\\"\\\\/\\u000a\\u0009"' in result.canonical_bytes
    assert b"\\n" not in result.canonical_bytes
    assert b"\\t" not in result.canonical_bytes


def test_integer_boolean_and_null_forms_are_exact() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["forms"] = {
        "integer": -42,
        "boolean": True,
        "nullable": None,
    }

    result = canonicalize_fx20(package)

    assert (
        b'"forms":{"boolean":true,"integer":-42,"nullable":null}'
        in result.canonical_bytes
    )


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        (
            b"\xef\xbb\xbf" + FX20_CANONICAL_BYTES,
            RawPackageRejectionReason.BOM_FORBIDDEN,
        ),
        (
            FX20_CANONICAL_BYTES.replace(b'"raw_fx20"', b'"\xff"'),
            RawPackageRejectionReason.INVALID_UTF8,
        ),
    ],
)
def test_invalid_byte_encodings_are_rejected(
    source: bytes,
    reason: RawPackageRejectionReason,
) -> None:
    with pytest.raises(TemporalRawPackageError) as exc_info:
        load_temporal_raw_package(
            source,
            payload_bytes=FX20_PAYLOAD_BYTES,
        )

    assert exc_info.value.reason is reason
    assert not hasattr(exc_info.value, "canonical_hash")
    assert not hasattr(exc_info.value, "canonical_bytes")


def test_duplicate_key_is_rejected_before_hash() -> None:
    source = FX20_CANONICAL_BYTES.replace(
        b'"raw_id":"raw_fx20"',
        b'"raw_id":"raw_fx20","raw_id":"duplicate"',
    )

    with pytest.raises(TemporalRawPackageError) as exc_info:
        load_temporal_raw_package(
            source,
            payload_bytes=FX20_PAYLOAD_BYTES,
        )

    assert exc_info.value.reason is RawPackageRejectionReason.DUPLICATE_KEY
    assert not hasattr(exc_info.value, "canonical_hash")


@pytest.mark.parametrize("literal", [b"NaN", b"Infinity", b"-Infinity"])
def test_nonfinite_numbers_are_rejected(literal: bytes) -> None:
    source = FX20_CANONICAL_BYTES.replace(
        b'"language":"en"',
        b'"confidence":' + literal + b',"language":"en"',
    )

    with pytest.raises(TemporalRawPackageError) as exc_info:
        load_temporal_raw_package(
            source,
            payload_bytes=FX20_PAYLOAD_BYTES,
        )

    assert exc_info.value.reason is RawPackageRejectionReason.FLOAT_FORBIDDEN


def test_finite_float_and_negative_zero_are_rejected() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["confidence"] = 0.5
    with pytest.raises(TemporalRawPackageError) as float_error:
        canonicalize_fx20(package)
    assert (
        float_error.value.reason
        is RawPackageRejectionReason.FLOAT_FORBIDDEN
    )

    source = FX20_CANONICAL_BYTES.replace(
        b'"start_us":0',
        b'"start_us":-0',
        1,
    )
    with pytest.raises(TemporalRawPackageError) as zero_error:
        load_temporal_raw_package(
            source,
            payload_bytes=FX20_PAYLOAD_BYTES,
        )
    assert (
        zero_error.value.reason
        is RawPackageRejectionReason.NEGATIVE_ZERO_FORBIDDEN
    )


@pytest.mark.parametrize(
    "code",
    [
        "uri_user_info",
        "URI-USER-INFO",
        "URI_USER_INF0",
        "WORD_RANGE_OOB",
    ],
)
def test_unknown_alias_case_and_spelling_variants_are_rejected(
    code: str,
) -> None:
    with pytest.raises(TemporalRawPackageError) as exc_info:
        validate_issue_codes([code])

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.UNKNOWN_ISSUE_CODE
    )


def test_unknown_issue_code_rejects_package_before_hash() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["issue_codes"] = ["NOT_IN_THE_INVENTORY"]

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_fx20(package)

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.UNKNOWN_ISSUE_CODE
    )
    assert not hasattr(exc_info.value, "canonical_hash")


def test_cor002_codes_are_canonical_inventory_members() -> None:
    cor002_codes = (
        "URI_USER_INFO",
        "URI_SENSITIVE_COMPONENT",
        "WORD_RANGE_OUT_OF_BOUNDS",
        "WORD_RANGE_REVERSED",
        "WORD_RANGE_REVISION_MISMATCH",
    )

    assert validate_issue_codes(cor002_codes) == cor002_codes
    assert set(cor002_codes).issubset(STABLE_ISSUE_CODES)


def test_stable_issue_inventory_view_is_closed_and_deterministic() -> None:
    assert len(STABLE_ISSUE_CODES) == len(set(STABLE_ISSUE_CODES))
    assert STABLE_ISSUE_CODES == tuple(sorted(STABLE_ISSUE_CODES))
    assert validate_issue_codes(STABLE_ISSUE_CODES) == STABLE_ISSUE_CODES


def test_token_arrays_require_strictly_ascending_indices() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["payload"]["tokens"][1]["index"] = 0
    payload_bytes = FX20_PAYLOAD_BYTES.replace(
        b'"end_us":2000000,"index":1',
        b'"end_us":2000000,"index":0',
    )
    package["payload_byte_hash"] = (
        "sha256:" + hashlib.sha256(payload_bytes).hexdigest()
    )

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_fx20(package, payload_bytes=payload_bytes)

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.TOKEN_ORDER_INVALID
    )


def test_required_structure_is_rejected_before_hash() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    del package["raw_id"]

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_fx20(package)

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.STRUCTURE_INVALID
    )
    assert not hasattr(exc_info.value, "canonical_hash")


def test_payload_byte_hash_is_required_before_canonical_hash() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    del package["payload_byte_hash"]

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_fx20(package)

    assert exc_info.value.reason is RawPackageRejectionReason.STRUCTURE_INVALID
    assert not hasattr(exc_info.value, "canonical_bytes")
    assert not hasattr(exc_info.value, "canonical_hash")


@pytest.mark.parametrize(
    "declared_hash",
    [
        "not-a-sha256",
        "492acc757b2708c21663a294117c418351e1037bafce0259c409eda2b17c0db5",
        "sha256:492acc75",
        (
            "sha256:492ACC757B2708C21663A294117C418351E1037B"
            "AFCE0259C409EDA2B17C0DB5"
        ),
        (
            "SHA256:492acc757b2708c21663a294117c418351e1037b"
            "afce0259c409eda2b17c0db5"
        ),
    ],
)
def test_payload_byte_hash_requires_exact_syntax(
    declared_hash: str,
) -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["payload_byte_hash"] = declared_hash

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_fx20(package)

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.PAYLOAD_HASH_INVALID
    )
    assert not hasattr(exc_info.value, "canonical_hash")


def test_payload_byte_hash_must_match_exact_raw_bytes() -> None:
    changed_payload_bytes = FX20_PAYLOAD_BYTES.replace(
        b'"result"',
        b'"Result"',
    )

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_fx20(payload_bytes=changed_payload_bytes)

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.PAYLOAD_HASH_MISMATCH
    )
    assert not hasattr(exc_info.value, "canonical_bytes")
    assert not hasattr(exc_info.value, "canonical_hash")


def test_raw_and_logical_paths_validate_the_same_payload_bytes() -> None:
    logical = canonicalize_fx20()
    loaded = load_temporal_raw_package(
        FX20_CANONICAL_BYTES,
        payload_bytes=FX20_PAYLOAD_BYTES,
    )

    assert loaded == logical

    for materialize in (
        lambda: canonicalize_fx20(payload_bytes=FX20_PAYLOAD_BYTES + b" "),
        lambda: load_temporal_raw_package(
            FX20_CANONICAL_BYTES,
            payload_bytes=FX20_PAYLOAD_BYTES + b" ",
        ),
    ):
        with pytest.raises(TemporalRawPackageError) as exc_info:
            materialize()
        assert (
            exc_info.value.reason
            is RawPackageRejectionReason.PAYLOAD_HASH_MISMATCH
        )
        assert not hasattr(exc_info.value, "canonical_hash")


def test_opaque_nested_tokens_are_preserved_without_alignment_validation() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["payload"]["metadata"] = {
        "tokens": ["not", "alignment", "tokens"],
        "nested": {"tokens": {"provider": "opaque"}},
    }
    payload_bytes = (
        b'{"language":"en","metadata":{"nested":{"tokens":{"provider":"opaque"}},'
        b'"tokens":["not","alignment","tokens"]},"tokens":'
        b'[{"end_us":1000000,"index":0,"start_us":0,"text":"A"},'
        b'{"end_us":2000000,"index":1,"start_us":1000000,"text":"clear"},'
        b'{"end_us":3000000,"index":2,"start_us":2000000,"text":"result"}]}'
    )
    package["payload_byte_hash"] = (
        "sha256:" + hashlib.sha256(payload_bytes).hexdigest()
    )

    result = canonicalize_fx20(package, payload_bytes=payload_bytes)

    assert b'"tokens":["not","alignment","tokens"]' in result.canonical_bytes
    assert b'"tokens":{"provider":"opaque"}' in result.canonical_bytes


def test_valid_alignment_token_indices_need_only_be_strictly_ascending() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["payload"]["tokens"][0]["index"] = -2
    package["payload"]["tokens"][1]["index"] = 4
    package["payload"]["tokens"][2]["index"] = 9
    payload_bytes = (
        FX20_PAYLOAD_BYTES.replace(b'"index":0', b'"index":-2')
        .replace(b'"index":1', b'"index":4')
        .replace(b'"index":2', b'"index":9')
    )
    package["payload_byte_hash"] = (
        "sha256:" + hashlib.sha256(payload_bytes).hexdigest()
    )

    assert canonicalize_fx20(
        package,
        payload_bytes=payload_bytes,
    ).canonical_hash.startswith("sha256:")


def _raw_package_from_fields() -> CanonicalRawPackage:
    return CanonicalRawPackage(FX20_CANONICAL_BYTES, FX20_CANONICAL_HASH)


def _raw_package_from_new() -> CanonicalRawPackage:
    value = object.__new__(CanonicalRawPackage)
    object.__setattr__(value, "canonical_bytes", FX20_CANONICAL_BYTES)
    object.__setattr__(value, "canonical_hash", FX20_CANONICAL_HASH)
    return value


def _assert_non_genuine_raw_package(value: object) -> None:
    assert not temporal_contracts._is_materialized_raw_package(value)
    if type(value) is CanonicalRawPackage:
        with pytest.raises(
            ValueError,
            match="^canonical raw package must be genuine$",
        ):
            value.canonical_bytes
        with pytest.raises(
            ValueError,
            match="^canonical raw package must be genuine$",
        ):
            value.canonical_hash


@pytest.mark.parametrize(
    "factory",
    [
        _raw_package_from_fields,
        _raw_package_from_new,
        lambda: CanonicalRawPackage(
            **{
                "canonical_bytes": FX20_CANONICAL_BYTES,
                "canonical_hash": FX20_CANONICAL_HASH,
            }
        ),
        lambda: CanonicalRawPackage(
            **vars(canonicalize_fx20()),
        ),
        lambda: CanonicalRawPackage(
            **{
                field.name: object.__getattribute__(
                    canonicalize_fx20(), field.name
                )
                for field in dataclasses.fields(CanonicalRawPackage)
            }
        ),
        lambda: dataclasses.replace(canonicalize_fx20()),
    ],
)
def test_reconstructed_raw_packages_are_not_genuine(factory) -> None:
    original = canonicalize_fx20()
    reconstructed = factory()

    _assert_non_genuine_raw_package(reconstructed)
    assert temporal_contracts._is_materialized_raw_package(original)
    assert original.canonical_bytes == FX20_CANONICAL_BYTES
    assert original.canonical_hash == FX20_CANONICAL_HASH


def test_marker_subclass_proxy_and_lookalike_do_not_transfer_raw_provenance() -> None:
    original = canonicalize_fx20()

    class MarkerSubclass(CanonicalRawPackage):
        _materialized = True

    class Proxy:
        def __init__(self, target):
            self._target = target

        def __getattr__(self, name: str):
            return getattr(self._target, name)

    class Lookalike:
        canonical_bytes = FX20_CANONICAL_BYTES
        canonical_hash = FX20_CANONICAL_HASH

    forged = _raw_package_from_fields()
    object.__setattr__(forged, "_materialized", True)
    values = [
        MarkerSubclass(FX20_CANONICAL_BYTES, FX20_CANONICAL_HASH),
        forged,
        Proxy(original),
        Lookalike(),
    ]

    for value in values:
        _assert_non_genuine_raw_package(value)
    assert temporal_contracts._is_materialized_raw_package(original)


def test_raw_package_copy_and_pickle_do_not_mint_provenance() -> None:
    original = canonicalize_fx20()

    for copied in (copy.copy(original), copy.deepcopy(original)):
        if copied is original:
            assert temporal_contracts._is_materialized_raw_package(copied)
        else:
            _assert_non_genuine_raw_package(copied)
        assert temporal_contracts._is_materialized_raw_package(original)

    restored = pickle.loads(pickle.dumps(original))
    assert restored is not original
    _assert_non_genuine_raw_package(restored)
    assert temporal_contracts._is_materialized_raw_package(original)


def test_raw_package_passive_introspection_preserves_stored_values_and_shape() -> None:
    original = canonicalize_fx20()
    reconstructed = _raw_package_from_fields()

    assert repr(original) == (
        "CanonicalRawPackage("
        f"canonical_bytes={FX20_CANONICAL_BYTES!r}, "
        f"canonical_hash={FX20_CANONICAL_HASH!r})"
    )
    assert repr(reconstructed) == repr(original)
    assert vars(original) == {
        "canonical_bytes": FX20_CANONICAL_BYTES,
        "canonical_hash": FX20_CANONICAL_HASH,
    }
    assert original.__dict__ == vars(original)
    assert [field.name for field in dataclasses.fields(original)] == [
        "canonical_bytes",
        "canonical_hash",
    ]
    assert reconstructed == original
    assert hash(reconstructed) == hash(original)
    assert pickle.loads(pickle.dumps(original)).__dict__ == vars(original)
    _assert_non_genuine_raw_package(reconstructed)
    assert temporal_contracts._is_materialized_raw_package(original)
