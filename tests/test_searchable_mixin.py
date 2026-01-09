import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, Session
from src.core.searchable_mixin import SearchableMixin
from src.services.embedding_service import embedding_service

# Setup generic DB for testing
Base = declarative_base()

class MockModel(Base, SearchableMixin):
    __tablename__ = 'mock_models'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    
    # Configuration
    _search_mode = "hybrid"

    def get_search_content(self) -> str:
        return f"{self.name} {self.description}"

class FTSModel(Base, SearchableMixin):
    __tablename__ = 'fts_models'
    id = Column(Integer, primary_key=True)
    content = Column(String)
    
    _search_mode = "fts_only"
    
    def get_search_content(self) -> str:
        return self.content

@pytest.fixture
def mock_embedding_service():
    with patch('src.core.searchable_mixin.embedding_service') as mock:
        mock.generate_embedding.return_value = [0.1, 0.2, 0.3]
        yield mock

@pytest.fixture
def db_session():
    engine = create_engine('sqlite:///:memory:') # Use SQLite for unit testing logic
    # Note: pgvector/TSVECTOR won't work in SQLite, so we mock those column behaviors or skip DB-dependent integration tests
    # For unit tests of the Mixin LOGIC (python side), SQLite is fine if we don't assume PG specific columns exist physically.
    # However, SearchableMixin defines mapped_column(Vector(1536)). SQLite doesn't support generic types well with pgvector import.
    # We will test the Python logic `update_embedding_if_needed` directly.
    return MagicMock(spec=Session)

def test_embedding_generation_triggered(mock_embedding_service):
    """Verify embedding is generated when update_embedding_if_needed is called with new content."""
    model = MockModel(name="Test", description="Description")
    
    # Initial state
    assert model.embedding is None
    assert model.embedding_hash is None
    
    # Trigger update
    model.update_embedding_if_needed()
    
    # Verify
    mock_embedding_service.generate_embedding.assert_called_once_with("Test Description")
    assert model.embedding == [0.1, 0.2, 0.3]
    assert model.embedding_hash is not None

def test_embedding_caching(mock_embedding_service):
    """Verify embedding is NOT re-generated if content hash is same."""
    model = MockModel(name="Test", description="Description")
    model.update_embedding_if_needed() # First gen
    
    mock_embedding_service.generate_embedding.reset_mock()
    
    # Call again with same content
    model.update_embedding_if_needed()
    
    mock_embedding_service.generate_embedding.assert_not_called()

def test_embedding_update_on_change(mock_embedding_service):
    """Verify embedding IS re-generated if content changes."""
    model = MockModel(name="Test", description="Description")
    model.update_embedding_if_needed()
    
    mock_embedding_service.generate_embedding.reset_mock()
    
    # Change content
    model.description = "New Description"
    model.update_embedding_if_needed()
    
    mock_embedding_service.generate_embedding.assert_called_once_with("Test New Description")

def test_fts_only_mode(mock_embedding_service):
    """Verify NO embedding is generated for fts_only mode."""
    model = FTSModel(content="Some text")
    
    model.update_embedding_if_needed()
    
    mock_embedding_service.generate_embedding.assert_not_called()
    assert model.embedding is None
    assert model.embedding_hash is None
