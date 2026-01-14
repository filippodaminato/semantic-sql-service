#!/usr/bin/env python3
"""
Script to regenerate embeddings for existing SemanticSynonyms.
This is needed after enabling hybrid search mode for synonyms.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from src.core.database import SessionLocal
from src.db.models import SemanticSynonym

def regenerate_synonym_embeddings():
    """Regenerate embeddings for all semantic synonyms."""
    db: Session = SessionLocal()
    
    try:
        synonyms = db.query(SemanticSynonym).all()
        total = len(synonyms)
        
        if total == 0:
            print("No synonyms found in the database.")
            return
        
        print(f"Found {total} synonyms. Regenerating embeddings...")
        
        updated_count = 0
        for idx, synonym in enumerate(synonyms, 1):
            print(f"[{idx}/{total}] Processing: '{synonym.term}'")
            
            # Save old hash to check for changes
            old_hash = synonym.embedding_hash
            
            # Regenerate embedding if needed
            # Since we changed _search_mode in the class, calling this should now generate embeddings
            synonym.update_embedding_if_needed()
            
            if synonym.embedding_hash != old_hash:
                updated_count += 1
                print(f"  ✓ Embedding regenerated")
            else:
                # Force update if hash matches but embedding is missing (e.g. was fts_only)
                if synonym.embedding is None:
                    # Clear hash to force regeneration
                    synonym.embedding_hash = None
                    synonym.update_embedding_if_needed()
                    updated_count += 1
                    print(f"  ✓ Embedding generated (was missing)")
                else:
                    print(f"  - Embedding already up to date")
                    
        db.commit()
        print(f"\n✅ Completed! {updated_count}/{total} synonym embeddings regenerated.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during regeneration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    regenerate_synonym_embeddings()
