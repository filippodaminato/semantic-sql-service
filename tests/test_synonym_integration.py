import pytest
from uuid import uuid4
from src.db.models import Datasource, TableNode, ColumnNode, SemanticSynonym, SynonymTargetType, SQLEngineType
from sqlalchemy.orm import Session

def test_table_synonym_in_embedding_content(db_session: Session):
    # 1. Setup Datasource & Table
    ds = Datasource(
        name="Synonym Test DS",
        slug="syn-test-ds",
        engine=SQLEngineType.POSTGRES,
        description="DS for synonym test"
    )
    db_session.add(ds)
    db_session.flush()

    table = TableNode(
        datasource_id=ds.id,
        physical_name="t_products",
        slug="t-products-syn-test",
        semantic_name="Products",
        description="A table of items"
    )
    db_session.add(table)
    db_session.flush()

    # 2. Verify initial search content (no synonyms)
    initial_content = table.get_search_content()
    assert "Products" in initial_content
    assert "items" in initial_content
    assert "Synonyms" not in initial_content

    # 3. Add Synonym
    syn = SemanticSynonym(
        term="Merchandise",
        slug="syn-merchandise",
        target_type=SynonymTargetType.TABLE,
        target_id=table.id
    )
    db_session.add(syn)
    db_session.commit()
    
    # 4. Refresh table to ensure it's attached and sees the new data
    # Note: get_search_content queries the DB, so we need the commit.
    db_session.refresh(table)

    # 5. Verify search content NOW includes synonym
    new_content = table.get_search_content()
    print(f"DEBUG: Content after synonym: {new_content}")
    
    assert "Products" in new_content
    assert "Merchandise" in new_content
    assert "Synonyms: Merchandise" in new_content

def test_column_synonym_in_embedding_content(db_session: Session):
    # 1. Setup Datasource, Table, Column
    ds = Datasource(
        name="Synonym Test DS Col",
        slug="syn-test-ds-col",
        engine=SQLEngineType.POSTGRES,
        description="DS for synonym column test"
    )
    db_session.add(ds)
    db_session.flush()

    table = TableNode(
        datasource_id=ds.id,
        physical_name="t_users",
        slug="t-users-syn-test",
        semantic_name="Users",
        description="User table"
    )
    db_session.add(table)
    db_session.flush()

    col = ColumnNode(
        table_id=table.id,
        name="full_name",
        slug="col-full-name",
        semantic_name="Full Name",
        data_type="VARCHAR",
        description="Name of the user"
    )
    db_session.add(col)
    db_session.flush()

    # 2. Add Synonym
    syn = SemanticSynonym(
        term="Anagrafica",
        slug="syn-anagrafica",
        target_type=SynonymTargetType.COLUMN,
        target_id=col.id
    )
    db_session.add(syn)
    db_session.commit()
    
    db_session.refresh(col)

    # 3. Verify content
    content = col.get_search_content()
    print(f"DEBUG: Column Content: {content}")
    assert "Full Name" in content
    assert "Synonyms: Anagrafica" in content
