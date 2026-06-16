"""
Fixtures comuns dos testes. Força MOCK_MODE + auth antes de importar a app.
"""
import os
os.environ["MOCK_MODE"] = "true"
os.environ["ENABLE_JWT_AUTH"] = "true"
os.environ["JWT_SECRET"] = "test-secret-key-with-enough-length-1234567890"
os.environ["ADMIN_EMAIL"] = "admin@gol.com"

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.store import get_store

ASSOC = "machine_learning_associate"
PROF = "machine_learning_professional"


@pytest.fixture(scope="session", autouse=True)
def _force_mock():
    get_settings.cache_clear()
    s = get_settings()
    assert s.MOCK_MODE is True, "Testes devem rodar em MOCK_MODE"
    assert s.ENABLE_JWT_AUTH is True
    yield


@pytest.fixture()
def client():
    """Cliente sem autenticação."""
    return TestClient(app)


def _auth_client(email: str, name: str, password: str) -> TestClient:
    c = TestClient(app)
    # registra (idempotente: se já existe, faz login)
    r = c.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": email, "password": password})
    token = r.json()["access_token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture()
def auth_client():
    """Cliente autenticado como usuário comum."""
    return _auth_client("trainee@gol.com", "Trainee GOL", "senha123")


@pytest.fixture()
def admin_client():
    """Cliente autenticado como admin (ADMIN_EMAIL)."""
    return _auth_client("admin@gol.com", "Admin GOL", "admin123")


@pytest.fixture()
def store():
    return get_store()
