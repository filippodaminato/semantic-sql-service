import json
import time
import urllib.request
import urllib.error
import sys

# CONFIGURAZIONE
API_URL = "http://localhost:8000/api/v1/admin"
DB_CONNECTION_STRING = "postgresql://admin:secret@localhost:5432/cloudbill_dwh"

def make_request(method, endpoint, data=None):
    """Helper per chiamate HTTP senza dipendenze esterne (no requests)"""
    url = f"{API_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header('Content-Type', 'application/json')
    
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.data = json_data

    try:
        with urllib.request.urlopen(req) as response:
            if 200 <= response.status < 300:
                response_data = response.read()
                return json.loads(response_data) if response_data else {}
    except urllib.error.HTTPError as e:
        # Ignora 404 su DELETE o 409 su CREATE (Idempotenza)
        if method == "DELETE" and e.code == 404:
            return None
        if method == "POST" and e.code == 409:
            print(f"   ⚠️  Resource already exists at {endpoint}")
            return None
            
        try:
            body = e.read().decode()
        except:
            body = "<no body>"
        print(f"❌ HTTP Error {e.code} for {method} {endpoint}: {body}")
        return None
    except Exception as e:
        print(f"❌ Request Error: {e}")
        return None

def cleanup():
    """Pulisce i dati esistenti per evitare duplicati sporchi"""
    print("\n🧹 Cleaning up existing metadata...")
    
    datasources = make_request("GET", "/datasources")
    target_ds_id = None
    if datasources:
        for ds in datasources:
            if ds.get('name') == "CloudBill_DWH" or ds.get('slug') == "cloudbill_prod":
                target_ds_id = ds['id']
                break
    
    # 0. Golden SQL (Explicit cleanup to be safe)
    if target_ds_id:
        print(f"   Checking for Golden SQL in datasource {target_ds_id}...")
        gsql = make_request("GET", f"/golden-sql?datasource_id={target_ds_id}")
        if gsql:
            print(f"   Deleting {len(gsql)} Golden SQL examples...")
            for g in gsql:
                make_request("DELETE", f"/golden-sql/{g['id']}")

    # 1. Datasources (Cascata su tabelle e colonne)
    if target_ds_id:
        print(f"   Deleting datasource: CloudBill_DWH ({target_ds_id})")
        make_request("DELETE", f"/datasources/{target_ds_id}")

    # 2. Metrics (Pulizia Semantica)
    metrics = make_request("GET", "/metrics")
    if metrics:
        for m in metrics:
            print(f"   Deleting metric: {m['name']}")
            make_request("DELETE", f"/metrics/{m['id']}")

    # 3. Synonyms
    synonyms = make_request("GET", "/synonyms")
    if synonyms:
        # Cancellazione massiva non disponibile, facciamo loop
        print(f"   Deleting {len(synonyms)} synonyms...")
        for s in synonyms:
             make_request("DELETE", f"/synonyms/{s['id']}")

    print("✅ Cleanup complete.")

def seed_ontology():
    print("\n🏗️  Seeding Physical Ontology (CloudBill_DWH)...")
    
    # 1. Create Datasource
    ds_payload = {
        "name": "CloudBill_DWH",
        "slug": "cloudbill_prod",
        "description": "SaaS Billing Data Warehouse. Handles organizations, subscriptions, usage events (JSON), and invoices. Source of truth for revenue.",
        "engine": "postgres",
        "connection_string": DB_CONNECTION_STRING,
        "context_signature": "Production Invoice & Usage Data"
    }
    ds = make_request("POST", "/datasources", ds_payload)
    if not ds:
        print("❌ Failed to create datasource. Aborting.")
        return None, None
        
    ds_id = ds["id"]
    print(f"✅ Created Datasource: {ds['name']} ({ds_id})")

    # 2. Create Tables & Columns
    # Mappa per salvare gli ID generati e usarli per le relazioni
    table_map = {} 

    tables_def = [
        {
            "physical_name": "organizations",
            "semantic_name": "Organizations",
            "slug": "organizations",
            "description": "Hierarchical B2B customers and resellers. Contains company details and status.",
            "ddl_context": "CREATE TABLE organizations (id UUID PRIMARY KEY, name VARCHAR(255), status VARCHAR(50), region VARCHAR(10), parent_org_id UUID REFERENCES organizations(id), settings JSONB);",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Organization ID", "description": "Unique identifier for the organization"},
                {"name": "name", "data_type": "VARCHAR", "semantic_name": "Organization Name", "description": "Legal name of the company", "context_note": "As registered in the business registry"},
                {"name": "status", "data_type": "VARCHAR", "semantic_name": "Account Status", "description": "Current status of the account", "context_note": "Values: ACTIVE, SUSPENDED, ARCHIVED"},
                {"name": "region", "data_type": "VARCHAR", "semantic_name": "Region Code", "description": "Geographic region code", "context_note": "ISO Code (e.g., LOM, EMR, LAZ)"},
                {"name": "parent_org_id", "data_type": "UUID", "semantic_name": "Parent Organization ID", "description": "Reference to parent organization if reseller", "context_note": "Recursive hierarchy for channel partners"},
                {"name": "settings", "data_type": "JSONB", "semantic_name": "Configuration Settings", "description": "JSON object containing preferences", "context_note": "Keys: timezone, currency, locale"}
            ]
        },
        {
            "physical_name": "plans",
            "semantic_name": "Price Plans",
            "slug": "plans",
            "description": "Product catalog and pricing tiers definitions.",
            "ddl_context": "CREATE TABLE plans (id UUID PRIMARY KEY, name VARCHAR(100), type VARCHAR(50), amount DECIMAL(10,2), valid_from TIMESTAMP, valid_to TIMESTAMP);",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Plan ID", "description": "Unique identifier for the pricing plan"},
                {"name": "name", "data_type": "VARCHAR", "semantic_name": "Plan Name", "description": "Marketing name of the plan", "context_note": "e.g., 'Pro', 'Enterprise', 'Starter'"},
                {"name": "type", "data_type": "VARCHAR", "semantic_name": "Pricing Model", "description": "Type of pricing model applied", "context_note": "FLAT (recurring) vs USAGE (pay-as-you-go)"},
                {"name": "amount", "data_type": "DECIMAL", "semantic_name": "Base Amount", "description": "Monthly base cost", "context_note": "Currency defined in organization settings (usually EUR)"},
                {"name": "valid_from", "data_type": "TIMESTAMP", "semantic_name": "Valid From", "description": "Date when this plan version became active"},
                {"name": "valid_to", "data_type": "TIMESTAMP", "semantic_name": "Valid To", "description": "Date when this plan version expires", "context_note": "NULL if currently active"}
            ]
        },
        {
            "physical_name": "subscriptions",
            "semantic_name": "Subscriptions",
            "slug": "subscriptions",
            "description": "Active and past customer subscriptions linking organizations to plans.",
            "ddl_context": "CREATE TABLE subscriptions (id UUID PRIMARY KEY, organization_id UUID REFERENCES organizations(id), plan_id UUID REFERENCES plans(id), status VARCHAR(50), current_period_end TIMESTAMP);",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Subscription ID", "description": "Unique identifier for the subscription"},
                {"name": "organization_id", "data_type": "UUID", "semantic_name": "Subscriber Org ID", "description": "Foreign key to the organization"},
                {"name": "plan_id", "data_type": "UUID", "semantic_name": "Plan ID", "description": "Foreign key to the plan"},
                {"name": "status", "data_type": "VARCHAR", "semantic_name": "Lifecycle Status", "description": "Current state of the subscription", "context_note": "TRIALING, ACTIVE, PAUSED, CANCELED, UNPAID"},
                {"name": "current_period_end", "data_type": "TIMESTAMP", "semantic_name": "Renewal Date", "description": "End of the current billing cycle", "context_note": "Used for churn calculation"}
            ]
        },
        {
            "physical_name": "usage_events",
            "semantic_name": "Usage Events",
            "slug": "usage-events",
            "description": "High-volume stream of metered usage events for billing.",
            "ddl_context": "CREATE TABLE usage_events (id UUID PRIMARY KEY, subscription_id UUID, event_type VARCHAR(100), metadata JSONB, timestamp TIMESTAMP);",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Event ID", "description": "Unique identifier for the event"},
                {"name": "subscription_id", "data_type": "UUID", "semantic_name": "Subscription ID", "description": "Attribution to a subscription"},
                {"name": "event_type", "data_type": "VARCHAR", "semantic_name": "Event Type", "description": "Category of usage", "context_note": "e.g., 'api_call', 'storage_gb_hour', 'active_user'"},
                {"name": "metadata", "data_type": "JSONB", "semantic_name": "Event Payload", "description": "Raw JSON payload of the event", "context_note": "Schema flexible. 'api_call' has 'endpoint', 'storage' has 'bucket_name'"},
                {"name": "timestamp", "data_type": "TIMESTAMP", "semantic_name": "Event Time", "description": "UTC timestamp of occurrence"}
            ]
        },
        {
            "physical_name": "invoices",
            "semantic_name": "Invoices",
            "slug": "invoices",
            "description": "Monthly generated invoices containing charges and tax info.",
            "ddl_context": "CREATE TABLE invoices (id UUID PRIMARY KEY, subscription_id UUID, amount_due DECIMAL(10,2), status VARCHAR(50), created_at TIMESTAMP);",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Invoice ID", "description": "Unique identifier for the invoice"},
                {"name": "subscription_id", "data_type": "UUID", "semantic_name": "Subscription ID", "description": "Linked subscription"},
                {"name": "amount_due", "data_type": "DECIMAL", "semantic_name": "Amount Due", "description": "Total amount to be paid including tax", "context_note": "Positive values only"},
                {"name": "status", "data_type": "VARCHAR", "semantic_name": "Payment Status", "description": "Current payment status", "context_note": "DRAFT, OPEN, PAID, VOID, UNCOLLECTIBLE"},
                {"name": "created_at", "data_type": "TIMESTAMP", "semantic_name": "Invoice Date", "description": "Date of invoice generation"}
            ]
        }
    ]

    for t_def in tables_def:
        t_def["datasource_id"] = ds_id
        res = make_request("POST", "/tables", t_def)
        if res:
            print(f"   Created table: {t_def['physical_name']}")
            cols_map = {c["name"]: c["id"] for c in res["columns"]}
            table_map[t_def["physical_name"]] = {"id": res["id"], "cols": cols_map}

    # 3. Create Relationships
    print("   Linking Relationships...")
    rels = [
        ("organizations", "id", "organizations", "parent_org_id", "ONE_TO_MANY", "Reseller hierarchy: Parent Org -> Child Orgs"),
        ("organizations", "id", "subscriptions", "organization_id", "ONE_TO_MANY", "Customer -> Subscriptions ownership"),
        ("plans", "id", "subscriptions", "plan_id", "ONE_TO_MANY", "Plan definition -> Subscription instances"),
        ("subscriptions", "id", "usage_events", "subscription_id", "ONE_TO_MANY", "Subscription -> Metered events stream"),
        ("subscriptions", "id", "invoices", "subscription_id", "ONE_TO_MANY", "Subscription -> Monthly invoices")
    ]
    
    for src_t, src_c, tgt_t, tgt_c, type_, desc in rels:
        try:
            payload = {
                "source_column_id": table_map[src_t]["cols"][src_c],
                "target_column_id": table_map[tgt_t]["cols"][tgt_c],
                "relationship_type": type_,
                "is_inferred": False,
                "description": desc
            }
            make_request("POST", "/relationships", payload)
        except KeyError as e:
            print(f"   ⚠️ Skipping rel {src_t}->{tgt_t}: Missing key {e}")

    return ds_id, table_map

def seed_semantics(datasource_id, table_map):
    print("\n🧠 Seeding Semantic Layer...")
    
    # 1. Metrics
    metrics = [
        {
            "datasource_id": datasource_id,
            "name": "MRR",
            "slug": "mrr",
            "description": "Monthly Recurring Revenue based on paid invoices (excluding tax).",
            "sql_expression": "SUM(invoices.amount_due)",
            "filter_condition": "invoices.status = 'PAID'",
            "required_table_ids": [table_map["invoices"]["id"]]
        },
        {
            "datasource_id": datasource_id,
            "name": "Churn Rate",
            "slug": "churn-rate",
            "description": "Percentage of canceled subscriptions relative to total subscriptions.",
            "sql_expression": "COUNT(CASE WHEN status='CANCELED' THEN 1 END) * 100.0 / COUNT(*)",
            "required_table_ids": [table_map["subscriptions"]["id"]]
        },
         {
            "datasource_id": datasource_id,
            "name": "Active Subscriptions",
            "slug": "active-subscriptions",
            "description": "Count of subscriptions that are currently active or trialing.",
            "sql_expression": "COUNT(*)",
            "filter_condition": "subscriptions.status IN ('ACTIVE', 'TRIALING')",
            "required_table_ids": [table_map["subscriptions"]["id"]]
        }
    ]
    
    for m in metrics:
        res = make_request("POST", "/metrics", m)
        if res: print(f"   Created Metric: {m['name']}")

    # 2. Synonyms (Bulk)
    syn_def = [
        ("organizations", ["Clienti", "Aziende", "Tenants", "Accounts", "Resellers"]),
        ("invoices", ["Bollette", "Fatture", "Pagamenti", "Receipts"]),
        ("usage_events", ["Consumo", "Traffico", "Log", "Metered Data"]),
        ("plans", ["Listino", "Pricing", "Tiers", "Offerte"])
    ]
    
    for t_name, terms in syn_def:
        payload = {
            "target_id": table_map[t_name]["id"],
            "target_type": "TABLE",
            "terms": terms
        }
        res = make_request("POST", "/synonyms/bulk", payload)
        if res: print(f"   Created Synonyms for {t_name}")

def seed_context(table_map):
    print("\n📜 Seeding Context & Values...")

    # 1. Context Rules (Soft Delete & Logic)
    rules = [
        ("invoices", "status", "ATTENZIONE: Ignora sempre fatture con status 'DRAFT' o 'VOID'. Considera solo 'PAID' per revenue."),
        ("usage_events", "metadata", "Se event_type='storage', leggi key 'bucket'. Se 'api', leggi 'endpoint' per distinguere il servizio."),
        ("organizations", "parent_org_id", "Se populated, questa organizzazione è un 'Child' (cliente finale) gestito da un Reseller.")
    ]
    
    for t_name, c_name, text in rules:
        try:
            col_id = table_map[t_name]["cols"][c_name]
            # Use part of rule text hash for stable slug
            rule_hash = str(hash(text))[-6:]
            payload = {
                "column_id": col_id, 
                "rule_text": text,
                "slug": f"rule-{t_name}-{c_name}-{rule_hash}"
            }
            make_request("POST", "/context-rules", payload)
            print(f"   Added Rule to {t_name}.{c_name}")
        except KeyError: pass

    # 2. Nominal Values (Mapping Enums)
    values_map = [
        ("organizations", "region", [
            {"raw": "LOM", "label": "Lombardia"}, 
            {"raw": "LAZ", "label": "Lazio"},
            {"raw": "VEN", "label": "Veneto"},
            {"raw": "CAM", "label": "Campania"}
        ]),
        ("plans", "type", [
            {"raw": "FLAT", "label": "Canone Fisso"}, 
            {"raw": "USAGE", "label": "A Consumo"}
        ]),
        ("subscriptions", "status", [
            {"raw": "ACTIVE", "label": "Attivo"},
            {"raw": "CANCELED", "label": "Cancellato"},
            {"raw": "TRIALING", "label": "In Prova"},
            {"raw": "UNPAID", "label": "Insoluto"}
        ])
    ]
    
    for t_name, c_name, vals in values_map:
        try:
            col_id = table_map[t_name]["cols"][c_name]
            for v in vals:
                payload = {
                    "raw": v["raw"], 
                    "label": v["label"],
                    "slug": f"val-{t_name}-{c_name}-{v['raw'].lower()}"
                }
                make_request("POST", f"/columns/{col_id}/values/manual", payload)
            print(f"   Mapped Values for {t_name}.{c_name}")
        except KeyError: pass

def seed_golden_sql(ds_id):
    print("\n🌟 Seeding Golden SQL...")
    
    examples = [
        {
            "prompt_text": "Calculate the total MRR for last month",
            "sql_query": "SELECT SUM(amount_due) FROM invoices WHERE status = 'PAID' AND created_at >= date_trunc('month', now() - interval '1 month') AND created_at < date_trunc('month', now());",
            "complexity": 2
        },
        {
            "prompt_text": "List all active subscriptions in Lombardia region",
            "sql_query": "SELECT s.id, o.name FROM subscriptions s JOIN organizations o ON s.organization_id = o.id WHERE s.status = 'ACTIVE' AND o.region = 'LOM';",
            "complexity": 3
        },
        {
            "prompt_text": "Count usage events per organization in 2024",
            "sql_query": "SELECT o.name, COUNT(u.id) FROM usage_events u JOIN subscriptions s ON u.subscription_id = s.id JOIN organizations o ON s.organization_id = o.id WHERE u.timestamp >= '2024-01-01' AND u.timestamp < '2025-01-01' GROUP BY o.name;",
            "complexity": 3
        },
        {
            "prompt_text": "Show me the top 5 customers by revenue",
            "sql_query": "SELECT o.name, SUM(i.amount_due) as total_revenue FROM invoices i JOIN subscriptions s ON i.subscription_id = s.id JOIN organizations o ON s.organization_id = o.id WHERE i.status = 'PAID' GROUP BY o.name ORDER BY total_revenue DESC LIMIT 5;",
            "complexity": 2
        }
    ]
    
    for ex in examples:
        ex["datasource_id"] = ds_id
        res = make_request("POST", "/golden-sql", ex)
        if res: print(f"   Created Golden SQL: {ex['prompt_text'][:30]}...")

if __name__ == "__main__":
    try:
        cleanup()
        ds_id, t_map = seed_ontology()
        if t_map and ds_id:
            seed_semantics(ds_id, t_map)
            seed_context(t_map)
            seed_golden_sql(ds_id)
        print("\n✨ Seed Finished Successfully!")
    except KeyboardInterrupt:
        print("\n🛑 Seed Aborted.")
