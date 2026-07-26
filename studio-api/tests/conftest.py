from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from engine.contracts import (
    DomainPackRegistry,
    DomainPolicyResolver,
    SchemaCatalog,
)
from kurgu_studio_api import create_app
from kurgu_studio_api.application.project_service import (
    ProjectApplicationService,
)
from kurgu_studio_api.infrastructure.contract_adapter import (
    EngineContractValidationAdapter,
)
from kurgu_studio_api.infrastructure.domain_resolution import (
    EngineDomainResolutionAdapter,
)
from kurgu_studio_api.infrastructure.in_memory_project_repository import (
    InMemoryProjectRepository,
)
from kurgu_studio_api.infrastructure.runtime import Runtime


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXED_TIME = "2026-07-26T10:00:00Z"
FIXED_PROJECT_ID = "prj_api_contract_001"


class FixedClock:
    def now_utc(self) -> str:
        return FIXED_TIME


class SequenceProjectIdFactory:
    def __init__(self, values: tuple[str, ...] = (FIXED_PROJECT_ID,)):
        self._values: Iterator[str] = iter(values)

    def new_project_id(self) -> str:
        return next(self._values)


def make_runtime(
    *,
    project_ids: tuple[str, ...] = (FIXED_PROJECT_ID,),
) -> Runtime:
    catalog = SchemaCatalog(REPO_ROOT / "schema" / "v3")
    validation = EngineContractValidationAdapter(catalog)
    registry = DomainPackRegistry([REPO_ROOT / "domain-packs"], catalog)
    registry.discover()
    resolution = EngineDomainResolutionAdapter(
        registry=registry,
        resolver=DomainPolicyResolver(catalog),
        contract_validation=validation,
    )
    repository = InMemoryProjectRepository()
    service = ProjectApplicationService(
        repository=repository,
        contract_validation=validation,
        domain_resolution=resolution,
        project_id_factory=SequenceProjectIdFactory(project_ids),
        clock=FixedClock(),
    )
    return Runtime(
        project_service=service,
        project_repository=repository,
        contract_validation=validation,
        domain_resolution=resolution,
    )


@pytest.fixture
def runtime() -> Runtime:
    return make_runtime()


@pytest.fixture
def client(runtime: Runtime) -> TestClient:
    return TestClient(create_app(runtime))


@pytest.fixture
def core_request() -> dict:
    return {
        "title": "API Contract Project",
        "domain": {"resolution_mode": "core_only"},
    }


@pytest.fixture
def business_request() -> dict:
    return {
        "title": "Business Technology Project",
        "domain": {
            "resolution_mode": "domain_pack",
            "domain_id": "business-tech",
            "domain_pack_version": "0.1.0",
            "profile": {
                "profile_id": "dpf_business_default",
                "enabled_extensions": [],
                "policy_overrides": {},
            },
        },
    }
