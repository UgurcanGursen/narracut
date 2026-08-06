"""Fresh per-application runtime wiring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from uuid import uuid4

from engine.contracts import (
    DomainPackRegistry,
    DomainPolicyResolver,
    SchemaCatalog,
)

from ..application.project_service import ProjectApplicationService
from ..application.studio_workflow_service import StudioWorkflowService
from .contract_adapter import EngineContractValidationAdapter
from .domain_eligibility import PROJECT_API_DOMAIN_ELIGIBILITY
from .domain_resolution import EngineDomainResolutionAdapter
from .in_memory_project_repository import InMemoryProjectRepository
from .sqlite_project_repository import SQLiteProjectRepository
from .engine_manual_task_factory import EngineManualTaskFactory
from .preview_adapters import InMemoryPreviewDelivery, PersistedRenderInputResolver, ReplayPreviewExecutor


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
    project_repository: InMemoryProjectRepository | SQLiteProjectRepository
    contract_validation: EngineContractValidationAdapter
    domain_resolution: EngineDomainResolutionAdapter
    workflow_service: StudioWorkflowService | None = None


def build_runtime(*, database_path: Path | None = None) -> Runtime:
    repo_root = Path(__file__).resolve().parents[4]
    catalog = SchemaCatalog(repo_root / "schema" / "v3")
    contract_validation = EngineContractValidationAdapter(catalog)
    registry = DomainPackRegistry([repo_root / "domain-packs"], catalog)
    registry.discover()
    domain_resolution = EngineDomainResolutionAdapter(
        registry=registry,
        resolver=DomainPolicyResolver(catalog),
        contract_validation=contract_validation,
        eligibility=PROJECT_API_DOMAIN_ELIGIBILITY,
    )
    repository = SQLiteProjectRepository(
        database_path
        or Path(tempfile.gettempdir()) / "kurgu-studio" / "studio.sqlite3"
    )
    service = ProjectApplicationService(
        repository=repository,
        contract_validation=contract_validation,
        domain_resolution=domain_resolution,
        project_id_factory=UuidProjectIdFactory(),
        clock=SystemClock(),
    )
    workflow_service = StudioWorkflowService(
        projects=repository,
        workflow=repository,
        task_factory=EngineManualTaskFactory(
            domain_packs_root=repo_root / "domain-packs"
        ),
        clock=SystemClock(),
        render_inputs=PersistedRenderInputResolver(repository),
        preview_executor=ReplayPreviewExecutor(fixture_root=repo_root / "tests" / "fixtures" / "phase4a"),
        preview_jobs=repository,
        preview_delivery=InMemoryPreviewDelivery(),
    )
    return Runtime(
        project_service=service,
        project_repository=repository,
        contract_validation=contract_validation,
        domain_resolution=domain_resolution,
        workflow_service=workflow_service,
    )
