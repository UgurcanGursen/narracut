from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from kurgu_studio_api.application.models import (
    ProjectAggregate,
    ResolvedDomainSelection,
)
from kurgu_studio_api.application.ports import RepositoryCollisionError
from kurgu_studio_api.infrastructure.in_memory_project_repository import (
    InMemoryProjectRepository,
)


def _aggregate(project_id: str = "prj_repository_001") -> ProjectAggregate:
    domain = ResolvedDomainSelection(
        resolution_mode="core_only",
        domain_id="core-generic",
        domain_pack_version="0.0.0",
        profile_id="dpf_core_default",
        policy_snapshot_id="dps_repository_snapshot",
        profile={},
        policy_snapshot={},
    )
    return ProjectAggregate(
        project={
            "project_id": project_id,
            "status": "ready",
            "updated_at": "2026-07-26T10:00:00Z",
            "version": 1,
        },
        domain=domain,
        artifacts=({"artifact_id": "art_defensive_001"},),
    )


def test_collision_is_atomic_and_does_not_overwrite() -> None:
    repository = InMemoryProjectRepository()
    first = _aggregate()
    repository.create(first)
    with pytest.raises(RepositoryCollisionError):
        repository.create(
            ProjectAggregate(
                project={**first.project, "status": "blocked"},
                domain=first.domain,
            )
        )
    assert repository.get("prj_repository_001").project["status"] == "ready"


def test_concurrent_collision_has_exactly_one_success() -> None:
    repository = InMemoryProjectRepository()

    def create() -> str:
        try:
            repository.create(_aggregate())
        except RepositoryCollisionError:
            return "collision"
        return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create(), range(2)))
    assert sorted(results) == ["collision", "created"]


def test_instances_are_isolated_and_artifacts_are_defensive_copies() -> None:
    first = InMemoryProjectRepository()
    second = InMemoryProjectRepository()
    source = _aggregate()
    first.create(source)
    source.project["status"] = "blocked"
    returned = first.get("prj_repository_001")
    returned.project["status"] = "archived"
    artifacts = list(first.list_artifacts("prj_repository_001"))
    artifacts[0]["artifact_id"] = "art_mutated_001"
    assert first.get("prj_repository_001").project["status"] == "ready"
    assert first.list_artifacts("prj_repository_001")[0]["artifact_id"] == (
        "art_defensive_001"
    )
    assert second.get("prj_repository_001") is None
