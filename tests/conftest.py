"""Pytest configuration and fixtures"""
import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import Base, get_db
from src.main import app
from src.db.models import Datasource, SQLEngineType
import uuid
from unittest.mock import MagicMock, patch
from src.services.embedding_service import embedding_service


# Test database (use separate test database)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://semantic_user:semantic_pass@localhost:5432/semantic_sql_test"
)

engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_datasource(db_session):
    """Create a sample datasource for testing"""
    datasource = Datasource(
        id=uuid.uuid4(),
        name="test_datasource",
        slug="test_datasource_slug",
        engine=SQLEngineType.POSTGRES
    )
    db_session.add(datasource)
    db_session.commit()
    db_session.refresh(datasource)
    return datasource


@pytest.fixture
def sample_datasource_id(sample_datasource):
    """Get datasource ID"""
    return sample_datasource.id


@pytest.fixture(autouse=True)
def mock_embedding_service():
    """Mock embedding service to avoid API calls"""
    with patch("src.services.embedding_service.embedding_service.generate_embedding") as mock_generate, \
         patch("src.services.embedding_service.embedding_service.generate_embeddings_batch") as mock_generate_batch:
        
        # Mock responses
        mock_generate.return_value = [0.1] * 1536
        
        def batch_side_effect(texts):
            return [[0.1] * 1536] * len(texts)
        mock_generate_batch.side_effect = batch_side_effect
        
        yield
