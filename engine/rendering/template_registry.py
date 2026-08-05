"""Closed deterministic registry for the Phase 5 core template inventory."""

from __future__ import annotations

from dataclasses import dataclass

from engine.contracts.models import DomainPolicySnapshot

from .template_contract import (
    CORE_TEMPLATE_DEFINITIONS,
    TemplateContractError,
    TemplateContractRejectionReason,
    TemplateDefinition,
    TemplateId,
    TemplatePolicyV1,
    template_policy_from_policy_snapshot,
)


@dataclass(frozen=True)
class TemplateCandidateV1:
    template_id: TemplateId
    editorial_role: str


class TemplateSelectionError(ValueError):
    def __init__(self, reason: TemplateContractRejectionReason) -> None:
        super().__init__(f"Template selection rejected: {reason.value}")
        self.reason = reason


class TemplateRegistry:
    """A core-only registry; it never discovers or loads a domain pack."""

    def __init__(self) -> None:
        self._definitions = CORE_TEMPLATE_DEFINITIONS
        self._by_id = {item.template_id: item for item in self._definitions}

    def definitions(self) -> tuple[TemplateDefinition, ...]:
        return self._definitions

    def get(self, template_id: TemplateId) -> TemplateDefinition:
        if type(template_id) is not TemplateId:
            raise TypeError("template_id must be exact TemplateId")
        try:
            return self._by_id[template_id]
        except KeyError as exc:
            raise TemplateSelectionError(TemplateContractRejectionReason.UNSUPPORTED_TEMPLATE) from exc

    def select(
        self,
        *,
        editorial_role: str,
        candidates: tuple[TemplateCandidateV1, ...],
        policy_snapshot: DomainPolicySnapshot | None = None,
    ) -> TemplateDefinition:
        if type(editorial_role) is not str or not editorial_role:
            raise TemplateSelectionError(TemplateContractRejectionReason.STRUCTURE_INVALID)
        if type(candidates) is not tuple or not candidates:
            raise TemplateSelectionError(TemplateContractRejectionReason.STRUCTURE_INVALID)
        candidate_ids: list[TemplateId] = []
        for candidate in candidates:
            if type(candidate) is not TemplateCandidateV1 or candidate.editorial_role != editorial_role:
                raise TemplateSelectionError(TemplateContractRejectionReason.STRUCTURE_INVALID)
            if candidate.template_id not in self._by_id or candidate.template_id in candidate_ids:
                raise TemplateSelectionError(TemplateContractRejectionReason.UNSUPPORTED_TEMPLATE)
            candidate_ids.append(candidate.template_id)
        eligible = [item for item in candidate_ids if editorial_role in self._by_id[item].supported_editorial_roles]
        if policy_snapshot is None:
            if not eligible:
                raise TemplateSelectionError(TemplateContractRejectionReason.UNSUPPORTED_TEMPLATE)
            return self._by_id[sorted(eligible, key=lambda item: item.value)[0]]
        if type(policy_snapshot) is not DomainPolicySnapshot:
            raise TypeError("policy_snapshot must be exact DomainPolicySnapshot or None")
        try:
            policy = template_policy_from_policy_snapshot(policy_snapshot)
        except TemplateContractError as exc:
            raise TemplateSelectionError(exc.reason) from None
        return self._select_with_policy(editorial_role, eligible, policy)

    def _select_with_policy(
        self,
        editorial_role: str,
        eligible: list[TemplateId],
        policy: TemplatePolicyV1,
    ) -> TemplateDefinition:
        banned = set(policy.banned_template_ids)
        required = set(policy.required_template_ids)
        if required & banned:
            raise TemplateSelectionError(TemplateContractRejectionReason.POLICY_INVALID)
        required_for_role = {
            item for item in required
            if editorial_role in self._by_id[item].supported_editorial_roles
        }
        if required_for_role and not required_for_role.issubset(set(eligible)):
            raise TemplateSelectionError(TemplateContractRejectionReason.POLICY_INVALID)
        candidates = [item for item in eligible if item not in banned]
        if required_for_role:
            candidates = [item for item in candidates if item in required_for_role]
        if not candidates:
            raise TemplateSelectionError(TemplateContractRejectionReason.UNSUPPORTED_TEMPLATE)
        preferred = [item for item in policy.preferred_template_ids if item in candidates]
        chosen = preferred[0] if preferred else sorted(candidates, key=lambda item: item.value)[0]
        return self._by_id[chosen]
