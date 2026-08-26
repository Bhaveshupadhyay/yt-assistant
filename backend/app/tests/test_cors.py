"""Integration tests for Cross-Origin Resource Sharing (CORS) policies."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cors_preflight_lennyai_clientmanger(async_client: AsyncClient):
    """Verify OPTIONS preflight request from https://lennyai.clientmanger.tech succeeds with CORS headers."""
    response = await async_client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://lennyai.clientmanger.tech",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://lennyai.clientmanger.tech"
    assert response.headers.get("access-control-allow-credentials") == "true"
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods or "*" in allow_methods


@pytest.mark.asyncio
async def test_cors_simple_request_lennyai_clientmanger(async_client: AsyncClient):
    """Verify GET request from https://lennyai.clientmanger.tech returns proper CORS headers."""
    response = await async_client.get(
        "/api/v1/health",
        headers={"Origin": "https://lennyai.clientmanger.tech"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://lennyai.clientmanger.tech"
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_regex_subdomains(async_client: AsyncClient):
    """Verify wildcard/subdomain matching via CORS_ORIGIN_REGEX."""
    test_origins = [
        "https://staging.clientmanger.tech",
        "https://app.clientmanger.tech",
        "https://bhaveshupadhyay.github.io",
        "https://my-preview.vercel.app",
    ]

    for origin in test_origins:
        response = await async_client.get(
            "/api/v1/health",
            headers={"Origin": origin},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin, f"Failed for origin: {origin}"
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_disallowed_origin(async_client: AsyncClient):
    """Verify disallowed origins do not receive CORS authorization headers."""
    response = await async_client.get(
        "/api/v1/health",
        headers={"Origin": "https://malicious-unauthorized-site.com"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
