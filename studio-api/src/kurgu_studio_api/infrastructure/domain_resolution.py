"""Core-only and registry-backed domain resolution adapters."""

from __future__ import annotations

from engine.contracts import (
    DomainPackError,
    DomainPackRegistry,
    DomainPolicyResolver,
    policy_snapshot_hash,
)

from ..application.errors import ApplicationError, ApplicationIssue
from ..application.models import (
    CoreOnlyDomainCommand,
    DomainCommand,
    DomainPackDomainCommand,
    ResolvedDomainSelection,
)
from ..application.ports import ContractValidationPort


class EngineDomainResolutionAdapter:
    def __init__(
        self,
        *,
        registry: DomainPackRegistry,
        resolver: DomainPolicyResolver,
        contract_validation: ContractValidationPort,
    ):
        self.registry = registry
        self.resolver = resolver
        self.contract_validation = contract_validation

    def resolve(
        self,
        command: DomainCommand,
        *,
        created_at: str,
    ) -> ResolvedDomainSelection:
        if isinstance(command, CoreOnlyDomainCommand):
            return self._resolve_core_only(created_at)
        if isinstance(command, DomainPackDomainCommand):
            return self._resolve_domain_pack(command)
        raise ApplicationError(
            "DOMAIN_CONFIGURATION_REQUIRED",
            "A supported domain configuration is required.",
        )

    def _resolve_core_only(self, created_at: str) -> ResolvedDomainSelection:
        profile = {
            "schema_version": "3.0.0",
            "profile_id": "dpf_core_default",
            "domain_id": "core-generic",
            "domain_pack_version": "0.0.0",
            "enabled_extensions": [],
            "policy_overrides": {},
            "status": "ready",
            "version": 1,
        }
        hash_payload = {
            "schema_version": "3.0.0",
            "domain_id": "core-generic",
            "domain_pack_version": "0.0.0",
            "profile_id": "dpf_core_default",
            "manifest_hash": "sha256:" + ("0" * 64),
            "resolved_policy": {},
            "immutable": True,
            "created_at": created_at,
            "version": 1,
        }
        canonical_hash = policy_snapshot_hash(hash_payload)
        snapshot = {
            **hash_payload,
            "snapshot_id": "dps_" + canonical_hash.removeprefix("sha256:")[:20],
            "canonical_hash": canonical_hash,
        }
        self.contract_validation.validate_profile(profile)
        self.contract_validation.validate_policy_snapshot(snapshot)
        return ResolvedDomainSelection(
            resolution_mode="core_only",
            domain_id="core-generic",
            domain_pack_version="0.0.0",
            profile_id=profile["profile_id"],
            policy_snapshot_id=snapshot["snapshot_id"],
            profile=profile,
            policy_snapshot=snapshot,
        )

    def _resolve_domain_pack(
        self,
        command: DomainPackDomainCommand,
    ) -> ResolvedDomainSelection:
        profile = {
            "schema_version": "3.0.0",
            "profile_id": command.profile.profile_id,
            "domain_id": command.domain_id,
            "domain_pack_version": command.domain_pack_version,
            "enabled_extensions": [
                dict(item) for item in command.profile.enabled_extensions
            ],
            "policy_overrides": dict(command.profile.policy_overrides),
            "status": "ready",
            "version": 1,
        }
        self.contract_validation.validate_profile(profile)
        try:
            pack = self.registry.get(
                command.domain_id,
                command.domain_pack_version,
            )
            _, snapshot = self.resolver.resolve(pack, profile)
        except DomainPackError as exc:
            raise self._sanitized_domain_error(exc) from exc
        self.contract_validation.validate_policy_snapshot(snapshot)
        return ResolvedDomainSelection(
            resolution_mode="domain_pack",
            domain_id=command.domain_id,
            domain_pack_version=command.domain_pack_version,
            profile_id=command.profile.profile_id,
            policy_snapshot_id=snapshot["snapshot_id"],
            profile=profile,
            policy_snapshot=snapshot,
        )

    @staticmethod
    def _sanitized_domain_error(exc: DomainPackError) -> ApplicationError:
        codes = {issue.code for issue in exc.issues}
        if "DOMAIN_UNKNOWN" in codes:
            code = "DOMAIN_UNKNOWN"
            pointer = "/domain/domain_id"
            message = "The requested domain or version is not available."
        elif "DOMAIN_PROFILE_MISMATCH" in codes:
            code = "DOMAIN_PROFILE_MISMATCH"
            pointer = "/domain/profile"
            message = "The profile does not match the selected domain pack."
        else:
            code = "DOMAIN_CONFIGURATION_REQUIRED"
            pointer = "/domain"
            message = "The domain configuration could not be resolved."
        return ApplicationError(
            code,
            message,
            (ApplicationIssue(code, pointer, message),),
        )
