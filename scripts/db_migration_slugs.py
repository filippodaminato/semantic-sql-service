import sqlalchemy
from sqlalchemy import create_engine, text

DB_CONNECTION_STRING = "postgresql://admin:secret@localhost:5432/cloudbill_dwh"

def migrate():
    engine = create_engine(DB_CONNECTION_STRING)
    with engine.connect() as conn:
        print("🔌 Connected to database.")
        
        # List of tables to update
        tables = [
            "table_nodes",
            "column_nodes",
            "semantic_metrics",
            "semantic_synonyms",
            "column_context_rules",
            "low_cardinality_values",
            "golden_sql"
        ]
        
        # 1. Add columns (nullable first)
        for table in tables:
            try:
                print(f"   Adding slug to {table}...")
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS slug VARCHAR(255)"))
                print(f"   ✅ Added slug to {table}")
            except Exception as e:
                print(f"   ⚠️ Error adding column to {table}: {e}")
        
        # 2. Truncate tables to allow setting NOT NULL / Unique without conflicts
        # We are re-seeding anyway.
        # We need to truncate cascadingly or in order.
        # Ideally, we truncate everything to be clean.
        print("\n🗑️ Truncating tables to clean up...")
        try:
            # Order matters or CASCADE
            conn.execute(text("TRUNCATE TABLE golden_sql CASCADE"))
            conn.execute(text("TRUNCATE TABLE low_cardinality_values CASCADE"))
            conn.execute(text("TRUNCATE TABLE column_context_rules CASCADE"))
            conn.execute(text("TRUNCATE TABLE semantic_synonyms CASCADE"))
            conn.execute(text("TRUNCATE TABLE semantic_metrics CASCADE"))
            conn.execute(text("TRUNCATE TABLE schema_edges CASCADE"))
            conn.execute(text("TRUNCATE TABLE column_nodes CASCADE"))
            conn.execute(text("TRUNCATE TABLE table_nodes CASCADE"))
            # Datasources?
            # conn.execute(text("TRUNCATE TABLE datasources CASCADE")) 
            # Check if we should keep datasources. Seed script tries to delete specific one.
            # Let's truncate everything to be safe for unique constraints.
            conn.execute(text("TRUNCATE TABLE datasources CASCADE"))
            
            print("   ✅ Tables truncated.")
        except Exception as e:
             print(f"   ⚠️ Error truncating: {e}")

        # 3. Add Constraints
        print("\n🔒 Adding constraints...")
        for table in tables:
            try:
                # Add Unique Index
                conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table}_slug ON {table} (slug)"))
                # Set Not Null (now valid since empty)
                conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN slug SET NOT NULL"))
                print(f"   ✅ Constraints added for {table}")
            except Exception as e:
                print(f"   ⚠️ Error adding constraints to {table}: {e}")
                
        conn.commit()
        print("\n✨ Migration complete.")

if __name__ == "__main__":
    migrate()
