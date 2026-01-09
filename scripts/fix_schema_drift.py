
import os
import sys
from sqlalchemy import create_engine, text

# Adjust path to import config if needed, or just use hardcoded URL for local docker
DATABASE_URL = "postgresql://semantic_user:semantic_pass@db:5432/semantic_sql"

def fix_schema():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Applying schema fixes...")
        
        # 1. Add columns to Datasource (already exists usually, but check)
        # embedding_hash and search_vector are likely missing if not auto-added
        # But User reported `slug` missing on metrics specifically.
        
        # 2. Add columns to SemanticMetric
        try:
            conn.execute(text("ALTER TABLE semantic_metrics ADD COLUMN IF NOT EXISTS datasource_id UUID REFERENCES datasources(id);"))
            print("Added datasource_id to semantic_metrics")
        except Exception as e:
            print(f"Error adding datasource_id: {e}")

        # 3. Ensure slug exists on all tables (User added slug to models)
        # Tables: datasources, table_nodes, column_nodes, semantic_metrics, semantic_synonyms, column_context_rules, low_cardinality_values, golden_sql
        
        tables_with_slug = [
            "datasources", 
            "table_nodes", 
            "column_nodes", 
            "semantic_metrics", 
            "semantic_synonyms", 
            "column_context_rules", 
            "low_cardinality_values", 
            "golden_sql"
        ]
        
        for table in tables_with_slug:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS slug VARCHAR(255);"))
                # Unique constraint might fail if duplicates exist, so add column first
                print(f"Added slug to {table}")
            except Exception as e:
                print(f"Error adding slug to {table}: {e}")

        # 4. Add SearchableMixin columns (embedding_hash)
        for table in tables_with_slug:
             try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS embedding_hash VARCHAR(64);"))
                print(f"Added embedding_hash to {table}")
             except Exception as e:
                print(f"Error adding embedding_hash to {table}: {e}")

        conn.commit()
        print("Schema fixes applied successfully.")

if __name__ == "__main__":
    fix_schema()
