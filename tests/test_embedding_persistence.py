import pytest
from uuid import uuid4
from src.db.models import Datasource, SQLEngineType
from sqlalchemy.orm import Session

def test_embedding_text_persistence(db_session: Session):
    # 1. Create Datasource
    ds = Datasource(
        name="Embedding Text Test DS",
        slug="emb-text-test-ds",
        engine=SQLEngineType.POSTGRES,
        description="Initial description"
    )
    db_session.add(ds)
    db_session.commit()
    
    db_session.refresh(ds)
    
    # 2. Verify embedding_text is saved
    assert ds.embedding is not None, "Embedding should be generated"
    assert ds.embedding_hash is not None
    assert ds.embedding_text is not None
    assert "Initial description" in ds.embedding_text
    
    initial_text = ds.embedding_text
    initial_hash = ds.embedding_hash

    # 3. Update description
    ds.description = "Updated description for test"
    db_session.commit()
    db_session.refresh(ds)

    # 4. Verify embedding_text is updated
    assert ds.embedding_text != initial_text
    assert "Updated description" in ds.embedding_text
    assert ds.embedding_hash != initial_hash

def test_cache_hit_persistence(db_session: Session):
    # Test that embedding_text is preserved/backfilled on cache hit
    # Note: mocking hash collision is hard without mocking the service,
    # but we can test that saving with same content doesn't clear it.
    
    ds = Datasource(
        name="Cache Hit Test DS",
        slug="cache-hit-test-ds",
        engine=SQLEngineType.POSTGRES,
        description="Stable description"
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)
    
    current_hash = ds.embedding_hash
    current_text = ds.embedding_text
    
    # "Touch" the object (no content change)
    ds.name = "Cache Hit Test DS Renamed" 
    # context_signature uses name? No, Datasource embedding uses description + context_signature.
    # Name change should NOT trigger embedding update if context didn't change.
    
    db_session.commit()
    db_session.refresh(ds)
    
    assert ds.embedding_hash == current_hash
    assert ds.embedding_text == current_text
    assert ds.embedding_text is not None
