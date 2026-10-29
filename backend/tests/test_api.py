import pytest
from httpx import AsyncClient
from app.main import app
import uuid

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}

@pytest.mark.asyncio
async def test_auth_flow():
    email = f"test-{uuid.uuid4()}@example.com"
    password = "password123"
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Register
        reg_response = await ac.post("/api/auth/register", json={"email": email, "password": password})
        assert reg_response.status_code == 201
        token_data = reg_response.json()
        assert "access_token" in token_data
        
        # Login
        login_response = await ac.post("/api/auth/login", json={"email": email, "password": password})
        assert login_response.status_code == 200
        assert login_response.json()["access_token"] == token_data["access_token"]

@pytest.mark.asyncio
async def test_protected_routes_unauthorized():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/analytics/dashboard")
    assert response.status_code == 401
