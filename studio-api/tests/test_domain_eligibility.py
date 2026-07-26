from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from kurgu_studio_api.infrastructure.domain_eligibility import (
    DomainEligibilityConfigurationError,
    DomainEligibilityPolicy,
    DomainNotEligibleError,
    DomainProfileNotEligibleError,
    EligibleDomainPack,
    PROJECT_API_DOMAIN_ELIGIBILITY,
)


def test_eligible_domain_version_and_profile_pass() -> None:
    PROJECT_API_DOMAIN_ELIGIBILITY.require_eligible(
        "business-tech",
        "0.1.0",
        "dpf_business_default",
    )


def test_eligible_domain_with_wrong_real_profile_fails_closed() -> None:
    with pytest.raises(DomainProfileNotEligibleError):
        PROJECT_API_DOMAIN_ELIGIBILITY.require_eligible(
            "business-tech",
            "0.1.0",
            "dpf_core_default",
        )


@pytest.mark.parametrize(
    ("domain_id", "domain_pack_version"),
    [
        ("unknown-domain", "0.1.0"),
        ("business-tech", "9.9.9"),
        ("true-crime-legal", "0.0.1-contract"),
    ],
)
def test_noneligible_domain_or_version_fails_closed(
    domain_id: str,
    domain_pack_version: str,
) -> None:
    with pytest.raises(DomainNotEligibleError):
        PROJECT_API_DOMAIN_ELIGIBILITY.require_eligible(
            domain_id,
            domain_pack_version,
            "dpf_any_valid_profile",
        )


def test_policy_storage_is_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        PROJECT_API_DOMAIN_ELIGIBILITY._entries = {}
    with pytest.raises(TypeError):
        PROJECT_API_DOMAIN_ELIGIBILITY._entries[
            ("true-crime-legal", "0.0.1-contract")
        ] = frozenset({"dpf_true_crime_default"})


@pytest.mark.parametrize(
    "declarations",
    [
        (
            EligibleDomainPack(
                "",
                "0.1.0",
                ("dpf_business_default",),
            ),
        ),
        (
            EligibleDomainPack(
                "business-tech",
                "",
                ("dpf_business_default",),
            ),
        ),
        (EligibleDomainPack("business-tech", "0.1.0", ()),),
        (
            EligibleDomainPack(
                "business-tech",
                "0.1.0",
                ("dpf_business_default", "dpf_business_default"),
            ),
        ),
        (
            EligibleDomainPack(
                "business-tech",
                "0.1.0",
                ("dpf_business_default",),
            ),
            EligibleDomainPack(
                "business-tech",
                "0.1.0",
                ("dpf_business_alternate",),
            ),
        ),
    ],
)
def test_duplicate_or_malformed_policy_declaration_fails_closed(
    declarations: tuple[EligibleDomainPack, ...],
) -> None:
    with pytest.raises(DomainEligibilityConfigurationError):
        DomainEligibilityPolicy(declarations)
