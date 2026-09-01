"""Smoke tests over the read-only API surface.

The distinction these tests draw is the useful one: a 500 that names a missing
dependency is acceptable on a machine that lacks it, but a 500 carrying a bare
NameError or AttributeError is a defect that will reproduce everywhere. Before
the accompanying fix, GET /api/layers/calfire returned
``{"detail": "name 'Image' is not defined"}`` on every machine, installed
dependencies or not, because backend/services.py used PIL's Image without ever
binding the name.

These tests make no network calls of their own; the endpoints that reach live
services are exercised only for their status contract, and any that need an
absent package are allowed to say so.
"""

import os
import sys
import warnings

import pytest

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytest.importorskip("fastapi")

# starlette's TestClient is an httpx client underneath. Recent starlette
# prefers the `httpx2` distribution and warns when it finds plain `httpx`,
# but both work -- so ask whether a client can actually be built rather than
# naming one package and silently skipping every test on machines with the
# other.
try:
    from fastapi.testclient import TestClient  # noqa: E402
except ImportError as exc:  # pragma: no cover - depends on the environment
    pytest.skip(
        f"starlette's TestClient is unavailable ({exc}); "
        "install httpx or httpx2 to run the API tests",
        allow_module_level=True,
    )

from backend.main import app  # noqa: E402

READ_ONLY_ENDPOINTS = [
    "/api/health",
    "/api/layers/bellwether",
    "/api/layers/buildings",
    "/api/layers/calfire-perimeters",
    "/api/layers/firms-hotspots",
    "/api/layers/fuel-moisture",
    "/api/layers/terrain-slope",
    "/api/bellwether-regions",
    "/api/layers/calfire",
    "/api/weather/live",
    "/api/data-catalog",
    "/api/risk-factors",
]

# These are the markers of a programming error leaking through as a 500.
PROGRAMMING_ERRORS = ("is not defined", "NameError", "AttributeError", "has no attribute",
                      "TypeError", "KeyError", "IndexError")


@pytest.fixture(scope="module")
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("endpoint", READ_ONLY_ENDPOINTS)
def test_endpoint_does_not_leak_a_programming_error(client, endpoint):
    response = client.get(endpoint, timeout=90)
    if response.status_code < 500:
        return

    try:
        detail = str(response.json().get("detail", response.text))
    except ValueError:
        detail = response.text

    for marker in PROGRAMMING_ERRORS:
        assert marker not in detail, (
            f"GET {endpoint} returned {response.status_code} with {detail!r}. "
            "A 500 may report a missing dependency, but a bare interpreter error "
            "means the endpoint is broken on every machine."
        )


def test_health_endpoint_is_self_contained(client):
    """The health check must not depend on any optional package or network call."""
    response = client.get("/api/health", timeout=30)
    assert response.status_code == 200, response.text


def test_calfire_overlay_reports_pillow_rather_than_a_nameerror(client):
    """Regression guard for the specific defect this branch fixes."""
    response = client.get("/api/layers/calfire", timeout=90)
    if response.status_code == 200:
        assert response.json().get("success") is True
        return
    detail = str(response.json().get("detail", ""))
    assert "Image" not in detail or "Pillow" in detail, (
        f"expected either a rendered overlay or a message naming Pillow, got {detail!r}"
    )
