import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def test_client():
    """
    Create a test client for the FastAPI application.
    """
    client = TestClient(app)
    yield client

# Add other fixtures here, e.g., for a test database session
# from app.db.base import SessionLocal, engine, Base