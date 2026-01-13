#!/usr/bin/env python3
"""
Script per rigenerare gli embedding dei golden_sql esistenti.

Questo script:
1. Carica tutti i golden_sql dal database
2. Rigenera gli embedding per ciascuno usando update_embedding_if_needed()
3. Salva le modifiche nel database

Uso:
    python scripts/regenerate_golden_sql_embeddings.py
"""

import sys
import os

# Aggiungi il path del progetto per importare i moduli
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from src.core.database import SessionLocal
from src.db.models import GoldenSQL

def regenerate_embeddings():
    """Rigenera gli embedding per tutti i golden_sql."""
    db: Session = SessionLocal()
    
    try:
        # Carica tutti i golden_sql
        golden_sqls = db.query(GoldenSQL).all()
        total = len(golden_sqls)
        
        if total == 0:
            print("Nessun golden_sql trovato nel database.")
            return
        
        print(f"Trovati {total} golden_sql. Rigenerazione embedding...")
        
        updated_count = 0
        for idx, gsql in enumerate(golden_sqls, 1):
            print(f"[{idx}/{total}] Processing: {gsql.id} - '{gsql.prompt_text[:50]}...'")
            
            # Salva l'hash corrente per verificare se cambia
            old_hash = gsql.embedding_hash
            
            # Rigenera l'embedding se necessario
            gsql.update_embedding_if_needed()
            
            # Se l'hash è cambiato, significa che l'embedding è stato rigenerato
            if gsql.embedding_hash != old_hash:
                updated_count += 1
                print(f"  ✓ Embedding rigenerato")
            else:
                print(f"  - Embedding già aggiornato (cache hit)")
        
        # Salva tutte le modifiche
        db.commit()
        print(f"\n✅ Completato! {updated_count}/{total} embedding rigenerati.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Errore durante la rigenerazione: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    regenerate_embeddings()
