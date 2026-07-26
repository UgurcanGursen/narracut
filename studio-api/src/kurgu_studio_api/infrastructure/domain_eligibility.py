"""Immutable public Project API domain eligibility policy."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping


class DomainEligibilityConfigurationError(RuntimeError):
    """The application-owned eligibility declaration is invalid."""


class DomainNotEligibleError(LookupError):
    """The selected domain/version is not eligible for public creation."""


class DomainProfileNotEligibleError(LookupError):
    """The selected profile is not bound to the eligible domain/version."""


@dataclass(frozen=True)
class EligibleDomainPack:
    domain_id: str
    domain_pack_version: str
    allowed_profile_ids: tuple[str, ...]


@dataclass(frozen=True, init=False)
class DomainEligibilityPolicy:
    """Fail-closed domain/profile bindings fixed by application wiring."""

    _entries: Mapping[tuple[str, str], frozenset[str]]

    def __init__(self, declarations: Iterable[EligibleDomainPack]):
        entries: dict[tuple[str, str], frozenset[str]] = {}
        for declaration in declarations:
            if not isinstance(declaration, EligibleDomainPack):
                raise DomainEligibilityConfigurationError(
                    "Invalid project domain eligibility declaration."
                )
            key = (
                declaration.domain_id,
                declaration.domain_pack_version,
            )
            profile_ids = declaration.allowed_profile_ids
            if (
                not all(
                    isinstance(value, str)
                    and value
                    and value == value.strip()
                    for value in key
                )
                or not isinstance(profile_ids, tuple)
                or not profile_ids
                or not all(
                    isinstance(profile_id, str)
                    and profile_id
                    and profile_id == profile_id.strip()
                    for profile_id in profile_ids
                )
                or len(set(profile_ids)) != len(profile_ids)
            ):
                raise DomainEligibilityConfigurationError(
                    "Invalid project domain eligibility declaration."
                )
            if key in entries:
                raise DomainEligibilityConfigurationError(
                    "Duplicate project domain eligibility declaration."
                )
            entries[key] = frozenset(profile_ids)
        object.__setattr__(self, "_entries", MappingProxyType(entries))

    def require_eligible(
        self,
        domain_id: str,
        domain_pack_version: str,
        profile_id: str,
    ) -> None:
        profile_ids = self._entries.get((domain_id, domain_pack_version))
        if profile_ids is None:
            raise DomainNotEligibleError
        if profile_id not in profile_ids:
            raise DomainProfileNotEligibleError


PROJECT_API_DOMAIN_ELIGIBILITY = DomainEligibilityPolicy(
    (
        EligibleDomainPack(
            domain_id="business-tech",
            domain_pack_version="0.1.0",
            allowed_profile_ids=("dpf_business_default",),
        ),
    )
)
