"""
Contract test: every endpoint the frontend calls must exist in the backend.

This exists because of a real break. A previous change moved
``POST /api/settings/validate/{service}`` from a query parameter to a JSON
body and renamed several response fields, but `SettingsPage.tsx` was not
updated. Nothing failed at build time - TypeScript cannot see across the HTTP
boundary, and the backend tests only ever talk to the backend - so the Verify
button silently returned 422 for every provider.

The test parses the frontend's API client for the paths it calls and checks
each one against the backend's generated OpenAPI schema. It cannot catch a
payload-shape mismatch (the Vitest suite in `frontend/src` covers that), but it
does catch a renamed, removed or newly-added route.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_CLIENT = PROJECT_ROOT / "frontend" / "src" / "services" / "api.ts"

#: Matches `api.get<Type>('/path')` / `api.post(\`/path/${id}\`, body)` and
#: captures the HTTP method plus the raw path literal.
CALL_PATTERN = re.compile(
    r"""api\.(get|post|put|delete|patch)      # HTTP method
        (?:<[^>]*>)?                          # optional TS type argument
        \(\s*                                 # opening paren
        ['"`]([^'"`]+)['"`]                   # the path literal
    """,
    re.VERBOSE,
)

#: Frontend template placeholders (`${jobId}`) mapped onto the OpenAPI path
#: parameter names the backend declares.
PLACEHOLDER_TO_PARAM = {
    "jobId": "job_id",
    "service": "service",
}


def normalise_path(raw_path: str) -> str:
    """
    Turn a frontend path literal into the OpenAPI path it should match.

    ``/status/${jobId}`` becomes ``/api/status/{job_id}``.
    """
    def replace(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        return "{" + PLACEHOLDER_TO_PARAM.get(name, name) + "}"

    path = re.sub(r"\$\{([^}]+)\}", replace, raw_path)
    return f"/api{path}"


def frontend_calls() -> list[tuple[str, str]]:
    """Return ``(method, openapi_path)`` for every call the API client makes."""
    source = API_CLIENT.read_text(encoding="utf-8")
    return [
        (method.lower(), normalise_path(raw_path))
        for method, raw_path in CALL_PATTERN.findall(source)
    ]


@pytest.fixture(scope="module")
def openapi_schema() -> dict:
    """The backend's generated OpenAPI schema."""
    import main

    return main.app.openapi()


def test_the_api_client_actually_makes_calls():
    """Guard the regex: a silent zero-match would make this whole file vacuous."""
    calls = frontend_calls()
    assert len(calls) >= 6, f"Only found {len(calls)} API calls - has the client been restructured?"


@pytest.mark.parametrize(("method", "path"), frontend_calls(), ids=lambda value: str(value))
def test_frontend_endpoint_exists_in_backend(method, path, openapi_schema):
    """Every path the frontend calls is declared by the backend."""
    paths = openapi_schema["paths"]

    assert path in paths, (
        f"The frontend calls {method.upper()} {path}, which the backend does not serve. "
        f"Known paths: {sorted(paths)}"
    )
    assert method in paths[path], (
        f"The frontend calls {method.upper()} {path}, but the backend only accepts "
        f"{sorted(paths[path])} there."
    )


def test_validate_endpoint_takes_a_request_body(openapi_schema):
    """
    Credentials must be a body parameter, never a query parameter.

    A query parameter would put the secret into access logs, proxy logs and
    browser history - which is exactly what the original implementation did.
    """
    operation = openapi_schema["paths"]["/api/settings/validate/{service}"]["post"]

    assert "requestBody" in operation, "validate must accept a JSON body"

    query_parameters = [
        parameter["name"]
        for parameter in operation.get("parameters", [])
        if parameter.get("in") == "query"
    ]
    assert query_parameters == [], f"secrets must not travel as query params: {query_parameters}"


def test_generate_returns_the_slug_it_assigned(openapi_schema):
    """
    The frontend displays `map_name` from the create response.

    The backend slugifies whatever name was submitted, so without this field
    the UI would show a name that does not match the archive on disk.
    """
    schemas = openapi_schema["components"]["schemas"]
    assert "map_name" in schemas["MapGenerationResponse"]["properties"]


def test_job_status_exposes_every_field_the_ui_renders(openapi_schema):
    """Fields consumed by GenerationPanel must be part of the status contract."""
    properties = openapi_schema["components"]["schemas"]["JobStatusResponse"]["properties"]

    for field in ("job_id", "status", "progress", "message", "error", "stats"):
        assert field in properties, f"JobStatusResponse is missing {field!r}"
