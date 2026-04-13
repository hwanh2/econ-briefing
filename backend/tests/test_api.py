"""API integration tests using TestClient with the real DB schema."""
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app import models

# Use the same PostgreSQL instance but a separate test database
TEST_DATABASE_URL = "postgresql://briefing:briefing@postgres:5432/briefing_test"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """Create the test database and tables once per session."""
    # Connect to the default DB to create the test DB
    default_engine = create_engine(
        "postgresql://briefing:briefing@postgres:5432/briefing",
        isolation_level="AUTOCOMMIT",
    )
    with default_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname='briefing_test'")
        ).fetchone()
        if not exists:
            conn.execute(text("CREATE DATABASE briefing_test"))
    default_engine.dispose()

    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables():
    """Truncate all tables before each test."""
    with engine.begin() as conn:
        for table in reversed(models.Base.metadata.sorted_tables):
            conn.execute(table.delete())
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_pipeline_state():
    import app.routers.pipeline as p
    p._is_running = False
    p._last_run = None
    yield
    p._is_running = False
    p._last_run = None


client = TestClient(app, raise_server_exceptions=False)


# --- Reports ---

def test_list_reports_empty():
    resp = client.get("/api/reports")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_report_not_found():
    resp = client.get("/api/reports/999")
    assert resp.status_code == 404


# --- Pipeline ---

def test_pipeline_run_starts():
    with patch("app.routers.pipeline._run_pipeline", new_callable=AsyncMock):
        resp = client.post("/api/pipeline/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"


def test_pipeline_run_already_running():
    import app.routers.pipeline as p
    p._is_running = True
    resp = client.post("/api/pipeline/run")
    assert resp.status_code == 409


def test_pipeline_status_idle():
    with patch("app.main.scheduler", None):
        resp = client.get("/api/pipeline/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "idle"
    assert data["last_run"] is None
    assert data["next_run"] is None


def test_pipeline_status_running():
    import app.routers.pipeline as p
    p._is_running = True
    with patch("app.main.scheduler", None):
        resp = client.get("/api/pipeline/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


# --- Subscribers round-trip ---

def test_subscribers_roundtrip():
    resp = client.post("/api/subscribers", json={"email": "test@example.com", "name": "Test"})
    assert resp.status_code == 201
    created = resp.json()
    assert created["email"] == "test@example.com"

    resp = client.get("/api/subscribers")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["email"] == "test@example.com"


def test_subscriber_duplicate_email():
    client.post("/api/subscribers", json={"email": "dup@example.com"})
    resp = client.post("/api/subscribers", json={"email": "dup@example.com"})
    assert resp.status_code == 409
