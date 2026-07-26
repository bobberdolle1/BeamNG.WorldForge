"""
Documentation drift.

Docs rot in ways review does not catch: an install command for a dependency
that was dropped, an environment variable nobody reads any more, a link to a
file that got renamed. Every check here corresponds to something that was
actually wrong in this repository.

What this cannot do is notice that a paragraph now describes the old UI. That
still needs a human. What it can do is make the mechanical half automatic.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND = PROJECT_ROOT / "backend"
FRONTEND = PROJECT_ROOT / "frontend"

#: Every Markdown file that is part of the documentation.
DOCS = sorted(
    path
    for path in PROJECT_ROOT.glob("*.md")
    if path.name != "CHANGELOG.md"  # a changelog is history; it may name dead things
) + sorted(PROJECT_ROOT.glob("docs/*.md"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_code_fences(text: str) -> str:
    """Drop fenced blocks so a shell example is not mistaken for prose."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


# -- removed tooling ------------------------------------------------------------

#: (pattern, why it must not appear). Case-insensitive, searched in whole files
#: including code blocks - an install command in a fence is exactly the problem.
REMOVED_TOOLING = [
    (
        r"\bpoetry\b",
        "the project uses pip + requirements.txt; `poetry install` fails outright",
    ),
    (
        r"libgdal-dev|gdal-bin|gdal-devel|brew install .*\bgdal\b|pip\s+install\s+GDAL",
        "rasterio bundles GDAL in its wheels; the system packages are not needed "
        "and `pip install GDAL` fails on a clean machine",
    ),
    (
        r"code_generation|JBeam code|qwen3-coder|OLLAMA_CODER_MODEL",
        "LLM-generated JBeam/COLLADA was removed in favour of deterministic geometry",
    ),
    (
        r"np\.int0",
        "removed in NumPy 2; the code uses np.intp",
    ),
    (
        r"pylint",
        "linting is ruff",
    ),
]


#: Deliberate exceptions: ``(document, pattern) -> why it is allowed``.
#:
#: Explaining why something was removed is worth a mention of it. Each entry is
#: checked to still match, so an exemption cannot outlive the text it covers.
TOOLING_EXEMPTIONS = {
    (
        "docs/ARCHITECTURE.md",
        r"code_generation|JBeam code|qwen3-coder|OLLAMA_CODER_MODEL",
    ): "explains why level content is generated deterministically instead",
}


@pytest.mark.parametrize("doc", DOCS, ids=lambda path: str(path.relative_to(PROJECT_ROOT)))
@pytest.mark.parametrize("pattern,reason", REMOVED_TOOLING, ids=lambda value: value[:24])
def test_docs_do_not_reference_removed_tooling(doc, pattern, reason):
    relative = str(doc.relative_to(PROJECT_ROOT))
    if (relative, pattern) in TOOLING_EXEMPTIONS:
        pytest.skip(TOOLING_EXEMPTIONS[(relative, pattern)])

    matches = re.findall(pattern, read(doc), flags=re.IGNORECASE)
    assert not matches, f"{relative} mentions {matches[0]!r}: {reason}"


def test_no_exemption_outlives_its_text():
    """An exemption for text that is gone is dead weight - drop it."""
    for (relative, pattern), reason in TOOLING_EXEMPTIONS.items():
        text = read(PROJECT_ROOT / relative)
        assert re.search(pattern, text, re.IGNORECASE), (
            f"{relative} no longer matches {pattern!r} ({reason}); remove the exemption"
        )


def test_the_removed_tooling_check_would_notice_something():
    """
    Guard the guard.

    A typo in one of the patterns above turns the whole check into a no-op that
    passes forever, which is worse than not having it.
    """
    sample = "Run poetry install, then apt-get install libgdal-dev, then pylint."
    hits = [pattern for pattern, _ in REMOVED_TOOLING if re.search(pattern, sample, re.IGNORECASE)]

    assert len(hits) == 3


# -- environment variables ------------------------------------------------------


def known_environment_variables() -> set[str]:
    """
    Every environment variable the backend actually reads.

    Three sources: `Settings` field names, explicit `validation_alias` overrides
    (``OLLAMA_HOST`` is not ``OLLAMA_BASE_URL``), and the `os.getenv` calls in
    services that predate the settings object.
    """
    import sys

    sys.path.insert(0, str(BACKEND))
    from core.config import Settings

    names = set()
    for name, field in Settings.model_fields.items():
        names.add(name.upper())
        alias = getattr(field, "validation_alias", None)
        if isinstance(alias, str):
            names.add(alias.upper())

    for source in BACKEND.rglob("*.py"):
        names.update(re.findall(r"os\.getenv\(\s*[\"']([A-Z0-9_]+)[\"']", source.read_text()))
        names.update(re.findall(r"os\.environ\[\s*[\"']([A-Z0-9_]+)[\"']", source.read_text()))

    return names


def env_assignments(text: str) -> set[str]:
    """Names on the left of `=` in a dotenv-style block."""
    return set(re.findall(r"^([A-Z][A-Z0-9_]{2,})=", text, flags=re.MULTILINE))


def test_env_example_only_lists_variables_the_code_reads():
    """
    `OLLAMA_CODER_MODEL` sat here for two releases after the module that used it
    was deleted: settable, documented, and read by nothing.
    """
    declared = env_assignments(read(BACKEND / ".env.example"))
    unknown = sorted(declared - known_environment_variables())

    assert not unknown, f".env.example declares variables nothing reads: {unknown}"


def test_setup_documents_only_real_variables():
    setup = read(PROJECT_ROOT / "docs" / "SETUP.md")

    # Both shapes SETUP.md uses: `VAR` in a table cell, and VAR= in an env block.
    documented = env_assignments(setup) | {
        name
        for name in re.findall(r"`([A-Z][A-Z0-9_]{2,})`", setup)
        # Prose capitals that are not variables.
        if name not in {"API", "DEM", "GDAL", "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
    }
    # Read by the frontend build, not by Python.
    documented -= {"VITE_API_URL"}

    unknown = sorted(documented - known_environment_variables())
    assert not unknown, f"docs/SETUP.md documents variables nothing reads: {unknown}"


def test_every_server_variable_is_documented():
    """The reverse direction: a new setting has to be written down somewhere."""
    import sys

    sys.path.insert(0, str(BACKEND))
    from core.config import Settings

    documented = read(PROJECT_ROOT / "docs" / "SETUP.md") + read(BACKEND / ".env.example")

    # Internal knobs with no reason to appear in user-facing docs.
    internal = {"api_reload", "static_dir", "http_timeout_seconds", "ollama_timeout_seconds"}

    missing = [
        name.upper()
        for name in Settings.model_fields
        if name not in internal
        and name.upper() not in documented
        and str(
            getattr(Settings.model_fields[name], "validation_alias", "") or ""
        ).upper() not in documented
    ]

    assert not missing, f"undocumented settings: {missing}"


# -- links and paths ------------------------------------------------------------


@pytest.mark.parametrize("doc", DOCS, ids=lambda path: str(path.relative_to(PROJECT_ROOT)))
def test_relative_links_resolve(doc):
    """A renamed file leaves a dead link in every doc that pointed at it."""
    broken = []
    for target in re.findall(r"\]\(([^)#]+?)(?:#[^)]*)?\)", read(doc)):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if not (doc.parent / target).exists():
            broken.append(target)

    assert not broken, f"{doc.relative_to(PROJECT_ROOT)} links to missing files: {broken}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda path: str(path.relative_to(PROJECT_ROOT)))
def test_referenced_source_files_exist(doc):
    """
    Backticked repository paths must resolve.

    Only paths under a known top-level directory are checked, and only those
    with a file extension, so `output/<map>.zip` and prose in backticks are not
    mistaken for source references. Files the app creates at runtime are
    excluded: documenting where the encrypted settings land does not mean a
    checkout contains them.
    """
    text = read(doc)
    candidates = set(
        re.findall(
            r"`((?:backend|frontend|tests|docs|scripts)/[\w./-]+\.\w{2,4})`",
            text,
        )
    )
    # Created at runtime or supplied by the user; never present in a checkout.
    generated = {
        "backend/config/settings.key",
        "backend/config/user_settings.enc",
        "backend/config/gee-key.json",
    }

    missing = sorted(
        path for path in candidates - generated if not (PROJECT_ROOT / path).exists()
    )
    assert not missing, f"{doc.relative_to(PROJECT_ROOT)} references missing files: {missing}"


# -- the API reference ----------------------------------------------------------


def test_api_reference_documents_only_real_endpoints():
    """
    Every endpoint API.md documents must exist on the app.

    `test_api_contract.py` pins the *frontend* to the backend's routes. Nothing
    pinned the reference documentation, so a renamed path would have been caught
    in the UI and stayed wrong on this page.
    """
    import sys

    sys.path.insert(0, str(BACKEND))
    from main import app

    real = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    documented = re.findall(
        r"^###\s+`(GET|POST|PUT|DELETE)\s+(/[^`]*)`",
        read(PROJECT_ROOT / "docs" / "API.md"),
        flags=re.MULTILINE,
    )
    assert documented, "docs/API.md no longer uses the heading format this test reads"

    missing = [f"{method} {path}" for method, path in documented if (method, path) not in real]
    assert not missing, f"docs/API.md documents endpoints that do not exist: {missing}"


def test_api_reference_covers_every_public_endpoint():
    """The reverse: a new public endpoint has to be written down."""
    import sys

    sys.path.insert(0, str(BACKEND))
    from main import app

    api_reference = read(PROJECT_ROOT / "docs" / "API.md")
    undocumented = sorted(
        f"{method} {route.path}"
        for route in app.routes
        if getattr(route, "include_in_schema", False) and route.path.startswith("/api")
        for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
        if f"`{method} {route.path}`" not in api_reference
    )

    assert not undocumented, f"endpoints missing from docs/API.md: {undocumented}"


# -- claims with numbers in them ------------------------------------------------


def test_localization_key_count_is_current():
    """
    A hand-written count is a promise to update it.

    LOCALIZATION.md claimed "~150 strings" while the locale files held 112, and
    then 109 once the dead stage labels went.
    """
    keys = json.loads((FRONTEND / "src/i18n/locales/en.json").read_text(encoding="utf-8"))

    def count(node) -> int:
        return sum(count(value) if isinstance(value, dict) else 1 for value in node.values())

    actual = count(keys)
    documented = re.findall(
        r"^\| (?:English|Русский) \| `\w+` \| (\d+) \|",
        read(PROJECT_ROOT / "docs" / "LOCALIZATION.md"),
        flags=re.MULTILINE,
    )

    assert documented, "LOCALIZATION.md no longer has the key-count table this test reads"
    assert all(int(value) == actual for value in documented), (
        f"LOCALIZATION.md says {documented}, en.json has {actual} keys"
    )


def test_documented_area_limit_matches_the_backend():
    """The 400 km² cap appears in the UI guide, the frontend and the model."""
    import sys

    sys.path.insert(0, str(BACKEND))
    from models.map_request import MAX_AREA_KM2

    ui_guide = read(PROJECT_ROOT / "docs" / "UI_GUIDE.md")
    frontend_panel = (FRONTEND / "src/components/GenerationPanel.tsx").read_text()

    limit = int(MAX_AREA_KM2)
    assert f"{limit} км²" in ui_guide, "UI_GUIDE.md states a different area limit"
    assert f"MAX_AREA_KM2 = {limit}" in frontend_panel
