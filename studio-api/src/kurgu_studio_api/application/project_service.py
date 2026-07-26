"""Project use cases with no FastAPI or Pydantic dependency."""

from __future__ import annotations

from .errors import ApplicationError, ApplicationIssue
from .models import (
    ArtifactCollectionView,
    CreateProjectCommand,
    ProjectAggregate,
    ProjectCreatedView,
    ProjectStatusView,
)
from .ports import (
    Clock,
    ContractValidationPort,
    DomainResolutionPort,
    ProjectIdFactory,
    ProjectRepository,
    RepositoryCollisionError,
)


class ProjectApplicationService:
    def __init__(
        self,
        *,
        repository: ProjectRepository,
        contract_validation: ContractValidationPort,
        domain_resolution: DomainResolutionPort,
        project_id_factory: ProjectIdFactory,
        clock: Clock,
    ):
        self.repository = repository
        self.contract_validation = contract_validation
        self.domain_resolution = domain_resolution
        self.project_id_factory = project_id_factory
        self.clock = clock

    def create_project(self, command: CreateProjectCommand) -> ProjectCreatedView:
        timestamp = self.clock.now_utc()
        domain = self.domain_resolution.resolve(
            command.domain,
            created_at=timestamp,
        )
        project_id = self.project_id_factory.new_project_id()
        project = {
            "schema_version": "3.0.0",
            "project_id": project_id,
            "title": command.title,
            "created_at": timestamp,
            "updated_at": timestamp,
            "domain_id": domain.domain_id,
            "domain_pack_version": domain.domain_pack_version,
            "policy_snapshot_id": domain.policy_snapshot_id,
            "status": "ready",
            "version": 1,
        }
        self.contract_validation.validate_project(project)
        aggregate = ProjectAggregate(project=project, domain=domain)
        try:
            self.repository.create(aggregate)
        except RepositoryCollisionError as exc:
            message = "The generated project identifier is already in use."
            raise ApplicationError(
                "PROJECT_ID_COLLISION",
                message,
                (
                    ApplicationIssue(
                        "PROJECT_ID_COLLISION",
                        "/project_id",
                        message,
                    ),
                ),
            ) from exc
        return ProjectCreatedView(project=project, domain=domain)

    def get_project_status(self, project_id: str) -> ProjectStatusView:
        aggregate = self._required_project(project_id)
        project = aggregate.project
        return ProjectStatusView(
            project_id=project["project_id"],
            status=project["status"],
            updated_at=project["updated_at"],
            version=project["version"],
            domain=aggregate.domain,
        )

    def list_project_artifacts(self, project_id: str) -> ArtifactCollectionView:
        self._required_project(project_id)
        items = self.repository.list_artifacts(project_id)
        if items is None:
            raise self._not_found(project_id)
        self.contract_validation.validate_artifacts(items, project_id=project_id)
        return ArtifactCollectionView(project_id=project_id, items=items)

    def _required_project(self, project_id: str) -> ProjectAggregate:
        aggregate = self.repository.get(project_id)
        if aggregate is None:
            raise self._not_found(project_id)
        return aggregate

    @staticmethod
    def _not_found(project_id: str) -> ApplicationError:
        message = "The requested project was not found."
        return ApplicationError(
            "PROJECT_NOT_FOUND",
            message,
            (ApplicationIssue("PROJECT_NOT_FOUND", "/project_id", message),),
        )
