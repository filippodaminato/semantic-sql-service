#!/usr/bin/env python3
"""
Seed script to populate a test Datasource, Table, and Synonym to verify
vector search functionality (e.g. "merce" -> "merci").
"""

import sys
import os
import uuid
from sqlalchemy import text


# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from src.core.database import SessionLocal
from src.db.models import Datasource, TableNode, SemanticSynonym, SynonymTargetType, SQLEngineType

def seed_test_data():
    """Seed test data."""
    db: Session = SessionLocal()
    
    try:
        print("Testing RAW vector insert compatibility...", flush=True)
        # Verify vector ext is working by casting a small vector
        try:
            # SELECT '[1,2,3]'::vector
            # use 3 dims just to check type
            result = db.execute(text("SELECT '[1,2,3]'::vector")).scalar()
            print(f"✅ Vector type verified: {result} (Type: {type(result)})", flush=True)
        except Exception as e:
            print(f"❌ Vector type check failing: {e}", flush=True)
            if hasattr(e, 'orig'):
                print(f"  Original Error: {e.orig}", flush=True)
            # Try to create extension if missing (though we did it manually)
            try:
                db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                db.commit()
                print("  Re-created extension vector", flush=True)
            except:
                pass

        print("Seeding test data...", flush=True)
        
        # 1. Create Datasource
        ds_id = uuid.uuid4()
        ds = Datasource(
            id=ds_id,
            name="Test Retail DB",
            slug="test-retail-db",
            engine=SQLEngineType.POSTGRES,
            description="A test database for retail data."
        )
        db.add(ds)
        db.flush()
        
        # 2. Create Table "Products"
        table_id = uuid.uuid4()
        table = TableNode(
            id=table_id,
            datasource_id=ds_id,
            physical_name="products",
            slug="test-products",
            semantic_name="Products",
            description="Table containing list of merchandise and items for sale."
        )
        db.add(table)
        db.flush()
        
        # 3. Create Synonym "merci" -> Products
        synonym = SemanticSynonym(
            term="merci",
            target_type=SynonymTargetType.TABLE,
            target_id=table_id,
            slug="syn-merci-products"
        )
        db.add(synonym)
        db.commit()
        
        print("✅ Seeded successfully:")
        print(f"  - Datasource: {ds.name}")
        print(f"  - Table: {table.semantic_name}")
        print(f"  - Synonym: {synonym.term} (Target: {table.semantic_name})")
        
        # Refresh to check embedding
        db.refresh(synonym)
        if synonym.embedding is not None:
             print("  ✓ Synonym embedding generated automatically.")
        else:
             print("  ⚠️ Synonym embedding MISSING! Automatic generation might be disabled or failing.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")
        if hasattr(e, 'orig'):
            print(f"Original DB Error: {e.orig}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_data()
