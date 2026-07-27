from __future__ import annotations

import copy
import hashlib

import pytest

from engine.contracts import (
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
    "media_type": "application/vnd.kurgu.temporal-raw+json",
    "issue_codes": [],
}
FX20_CANONICAL_BYTES = (
    b'{"issue_codes":[],"media_type":"application/vnd.kurgu.temporal-raw+json",'
    b'"payload":{"language":"en","tokens":[{"end_us":1000000,"index":0,'
    b'"start_us":0,"text":"A"},{"end_us":2000000,"index":1,'
    b'"start_us":1000000,"text":"clear"},{"end_us":3000000,"index":2,'
    b'"start_us":2000000,"text":"result"}]},"raw_id":"raw_fx20",'
    b'"run_id":"run_fx20","schema_version":"TRP-RAW-V1"}'
)
FX20_CANONICAL_HASH = (
    "sha256:9911573528876b3bffda8cef2293ea3f02b193fc"
    "fec61ffeeb4f9cd7cdcac85b"
)


def test_fx20_has_exact_canonical_bytes_and_hash() -> None:
    result = canonicalize_temporal_raw_package(FX20_PACKAGE)

    assert result.canonical_bytes == FX20_CANONICAL_BYTES
    assert result.canonical_hash == FX20_CANONICAL_HASH
    assert not result.canonical_bytes.startswith(b"\xef\xbb\xbf")
    assert not result.canonical_bytes.endswith(b"\n")
    assert result.canonical_hash == (
        "sha256:" + hashlib.sha256(result.canonical_bytes).hexdigest()
    )


def test_independent_materialization_paths_are_byte_and_hash_equal() -> None:
    source = (
        b'{ "run_id": "run_fx20", "schema_version": "TRP-RAW-V1",'
        b' "payload": {"tokens": ['
        b'{"text":"A","start_us":0,"index":0,"end_us":1000000},'
        b'{"text":"clear","start_us":1000000,"index":1,"end_us":2000000},'
        b'{"text":"result","start_us":2000000,"index":2,"end_us":3000000}'
        b'], "language":"en"}, "raw_id":"raw_fx20", "issue_codes":[],'
        b' "media_type":"application/vnd.kurgu.temporal-raw+json" }'
    )

    logical = canonicalize_temporal_raw_package(FX20_PACKAGE)
    parsed = load_temporal_raw_package(source)

    assert parsed.canonical_bytes == logical.canonical_bytes
    assert parsed.canonical_hash == logical.canonical_hash


def test_object_insertion_order_does_not_change_bytes() -> None:
    reversed_root = dict(reversed(list(FX20_PACKAGE.items())))

    assert (
        canonicalize_temporal_raw_package(reversed_root).canonical_bytes
        == FX20_CANONICAL_BYTES
    )


def test_semantic_array_order_changes_bytes_and_hash() -> None:
    first = copy.deepcopy(FX20_PACKAGE)
    second = copy.deepcopy(FX20_PACKAGE)
    first["payload"]["alternatives"] = ["alpha", "beta"]
    second["payload"]["alternatives"] = ["beta", "alpha"]

    first_result = canonicalize_temporal_raw_package(first)
    second_result = canonicalize_temporal_raw_package(second)

    assert first_result.canonical_bytes != second_result.canonical_bytes
    assert first_result.canonical_hash != second_result.canonical_hash


def test_nfc_equivalent_inputs_have_equal_bytes_and_hashes() -> None:
    composed = copy.deepcopy(FX20_PACKAGE)
    decomposed = copy.deepcopy(FX20_PACKAGE)
    composed["payload"]["label"] = "caf\u00e9"
    decomposed["payload"]["label"] = "cafe\u0301"

    assert canonicalize_temporal_raw_package(
        composed
    ) == canonicalize_temporal_raw_package(decomposed)


def test_nfc_key_collision_is_rejected() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["payload"]["labels"] = {
        "caf\u00e9": "composed",
        "cafe\u0301": "decomposed",
    }

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_temporal_raw_package(package)

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.NORMALIZED_KEY_COLLISION
    )


@pytest.mark.parametrize("value", ["\ud800", "\ufdd0"])
def test_forbidden_unicode_values_are_rejected(value: str) -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["payload"]["label"] = value

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_temporal_raw_package(package)

    assert exc_info.value.reason is RawPackageRejectionReason.INVALID_UNICODE


def test_string_escaping_uses_exact_contract_forms() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["payload"]["escaped"] = '"\\/\n\t'

    result = canonicalize_temporal_raw_package(package)

    assert b'"\\"\\\\/\\u000a\\u0009"' in result.canonical_bytes
    assert b"\\n" not in result.canonical_bytes
    assert b"\\t" not in result.canonical_bytes


def test_integer_boolean_and_null_forms_are_exact() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["payload"]["forms"] = {
        "integer": -42,
        "boolean": True,
        "nullable": None,
    }

    result = canonicalize_temporal_raw_package(package)

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
        load_temporal_raw_package(source)

    assert exc_info.value.reason is reason
    assert not hasattr(exc_info.value, "canonical_hash")
    assert not hasattr(exc_info.value, "canonical_bytes")


def test_duplicate_key_is_rejected_before_hash() -> None:
    source = FX20_CANONICAL_BYTES.replace(
        b'"raw_id":"raw_fx20"',
        b'"raw_id":"raw_fx20","raw_id":"duplicate"',
    )

    with pytest.raises(TemporalRawPackageError) as exc_info:
        load_temporal_raw_package(source)

    assert exc_info.value.reason is RawPackageRejectionReason.DUPLICATE_KEY
    assert not hasattr(exc_info.value, "canonical_hash")


@pytest.mark.parametrize("literal", [b"NaN", b"Infinity", b"-Infinity"])
def test_nonfinite_numbers_are_rejected(literal: bytes) -> None:
    source = FX20_CANONICAL_BYTES.replace(
        b'"language":"en"',
        b'"confidence":' + literal + b',"language":"en"',
    )

    with pytest.raises(TemporalRawPackageError) as exc_info:
        load_temporal_raw_package(source)

    assert exc_info.value.reason is RawPackageRejectionReason.FLOAT_FORBIDDEN


def test_finite_float_and_negative_zero_are_rejected() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    package["payload"]["confidence"] = 0.5
    with pytest.raises(TemporalRawPackageError) as float_error:
        canonicalize_temporal_raw_package(package)
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
        load_temporal_raw_package(source)
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
        canonicalize_temporal_raw_package(package)

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

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_temporal_raw_package(package)

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.TOKEN_ORDER_INVALID
    )


def test_required_structure_is_rejected_before_hash() -> None:
    package = copy.deepcopy(FX20_PACKAGE)
    del package["raw_id"]

    with pytest.raises(TemporalRawPackageError) as exc_info:
        canonicalize_temporal_raw_package(package)

    assert (
        exc_info.value.reason
        is RawPackageRejectionReason.STRUCTURE_INVALID
    )
    assert not hasattr(exc_info.value, "canonical_hash")
