"""Fresh per-application runtime wiring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from engine.contracts import (
    DomainPackRegistry,
    DomainPolicyResolver,
    SchemaCatalog,
)

from ..application.project_service import ProjectApplicationService
from .contract_adapter import EngineContractValidationAdapter
from .domain_resolution import EngineDomainResolutionAdapter
from .in_memory_project_repository import InMemoryProjectRepository


class SystemClock:
    def now_utc(self) -> str:
        return (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )


class UuidProjectIdFactory:
    def new_project_id(self) -> str:
        return "prj_" + uuid4().hex


@dataclass(frozen=True)
class Runtime:
    project_service: ProjectApplicationService
    project_repository: InMemoryProjectRepository
    contract_validation: EngineContractValidationAdapter
    domain_resolution: EngineDomainResolutionAdapter


def build_runtime() -> Runtime:
    repo_root = Path(__file__).resolve().parents[4]
    catalog = SchemaCatalog(repo_root / "schema" / "v3")
    contract_validation = EngineContractValidationAdapter(catalog)
    registry = DomainPackRegistry([repo_root / "domain-packs"], catalog)
    registry.discover()
    domain_resolution = EngineDomainResolutionAdapter(
        registry=registry,
        resolver=DomainPolicyResolver(catalog),
        contract_validation=contract_validation,
    )
    repository = InMemoryProjectRepository()
    service = ProjectApplicationService(
        repository=repository,
        contract_validation=contract_validation,
        domain_resolution=domain_resolution,
        project_id_factory=UuidProjectIdFactory(),
        clock=SystemClock(),
    )
    return Runtime(
        project_service=service,
        project_repository=repository,
        contract_validation=contract_validation,
        domain_resolution=domain_resolution,
    )
