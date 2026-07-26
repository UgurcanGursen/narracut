from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "studio-api" / "src" / "kurgu_studio_api"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            values.add(node.module)
    return values


def test_route_module_has_no_engine_domain_filesystem_or_media_imports() -> None:
    route = PACKAGE / "api" / "v1" / "projects.py"
    imports = _imports(route)
    forbidden = {
        "engine",
        "engine.contracts",
        "pathlib",
        "os",
        "sqlite3",
        "subprocess",
        "v2",
        "moviepy",
    }
    assert imports.isdisjoint(forbidden)


def test_application_layer_has_no_fastapi_or_pydantic_imports() -> None:
    imports = set()
    for path in (PACKAGE / "application").glob("*.py"):
        imports.update(_imports(path))
    assert not any(
        value == "fastapi"
        or value.startswith("fastapi.")
        or value == "pydantic"
        or value.startswith("pydantic.")
        for value in imports
    )


def test_repository_has_no_filesystem_or_http_imports() -> None:
    imports = _imports(
        PACKAGE / "infrastructure" / "in_memory_project_repository.py"
    )
    assert imports.isdisjoint(
        {"pathlib", "os", "fastapi", "pydantic", "sqlite3"}
    )


def test_route_functions_do_not_implement_schema_or_domain_discovery() -> None:
    source = (PACKAGE / "api" / "v1" / "projects.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    forbidden_calls = {
        "SchemaCatalog",
        "DomainPackRegistry",
        "DomainPolicyResolver",
        "policy_snapshot_hash",
        "json.loads",
        "open",
    }
    called = {
        ast.unparse(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert called.isdisjoint(forbidden_calls)
