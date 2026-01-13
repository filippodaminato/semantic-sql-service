"""
Seed script for multi-datasource testing.

This script creates two distinct datasources with different domains:
1. E-commerce datasource: Products, Orders, Customers, Payments
2. HR datasource: Employees, Departments, Salaries, Attendance

This allows testing retrieval and discovery APIs with multiple datasources.
"""

import json
import time
import urllib.request
import urllib.error
import sys

# CONFIGURATION
API_URL = "http://localhost:8000/api/v1/admin"
DB_CONNECTION_STRING_ECOMMERCE = "postgresql://admin:secret@localhost:5432/ecommerce_dwh"
DB_CONNECTION_STRING_HR = "postgresql://admin:secret@localhost:5432/hr_dwh"


def make_request(method, endpoint, data=None):
    """
    Helper for HTTP requests without external dependencies (no requests library).
    
    Args:
        method: HTTP method (GET, POST, DELETE)
        endpoint: API endpoint path
        data: Optional JSON data for POST requests
    
    Returns:
        Parsed JSON response or None on error
    """
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
        # Ignore 404 on DELETE or 409 on CREATE (Idempotency)
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
    """Clean up existing data to avoid dirty duplicates."""
    print("\n🧹 Cleaning up existing metadata...")
    
    # Get all datasources
    datasources = make_request("GET", "/datasources")
    target_ds_ids = []
    
    if datasources:
        for ds in datasources:
            if ds.get('name') in ["E-commerce_DWH", "HR_DWH"] or ds.get('slug') in ["ecommerce_prod", "hr_prod"]:
                target_ds_ids.append(ds['id'])
    
    # Clean up Golden SQL for target datasources
    for ds_id in target_ds_ids:
        print(f"   Checking for Golden SQL in datasource {ds_id}...")
        gsql = make_request("GET", f"/golden-sql?datasource_id={ds_id}")
        if gsql:
            print(f"   Deleting {len(gsql)} Golden SQL examples...")
            for g in gsql:
                make_request("DELETE", f"/golden-sql/{g['id']}")
    
    # Delete datasources (cascades to tables and columns)
    for ds_id in target_ds_ids:
        print(f"   Deleting datasource: {ds_id}")
        make_request("DELETE", f"/datasources/{ds_id}")
    
    # Clean up Metrics
    metrics = make_request("GET", "/metrics")
    if metrics:
        for m in metrics:
            print(f"   Deleting metric: {m['name']}")
            make_request("DELETE", f"/metrics/{m['id']}")
    
    # Clean up Synonyms
    synonyms = make_request("GET", "/synonyms")
    if synonyms:
        print(f"   Deleting {len(synonyms)} synonyms...")
        for s in synonyms:
            make_request("DELETE", f"/synonyms/{s['id']}")
    
    print("✅ Cleanup complete.")


def seed_ecommerce_ontology():
    """Seed E-commerce datasource with products, orders, customers, payments."""
    print("\n🏗️  Seeding E-commerce Datasource (E-commerce_DWH)...")
    
    # 1. Create Datasource
    ds_payload = {
        "name": "E-commerce_DWH",
        "slug": "ecommerce_prod",
        "description": "E-commerce Data Warehouse. Handles products, orders, customers, and payment transactions. Source of truth for sales and inventory.",
        "engine": "postgres",
        "connection_string": DB_CONNECTION_STRING_ECOMMERCE,
        "context_signature": "E-commerce, Products, Orders, Customers, Payments, Sales, Inventory"
    }
    ds = make_request("POST", "/datasources", ds_payload)
    if not ds:
        print("❌ Failed to create E-commerce datasource. Aborting.")
        return None, None
        
    ds_id = ds["id"]
    print(f"✅ Created Datasource: {ds['name']} ({ds_id})")
    
    # 2. Create Tables & Columns
    table_map = {}
    
    tables_def = [
        {
            "physical_name": "products",
            "semantic_name": "Products",
            "slug": "products",
            "description": "Product catalog with pricing, inventory, and categorization.",
            "ddl_context": "CREATE TABLE products (id UUID PRIMARY KEY, name VARCHAR(255), price DECIMAL(10,2), category_id UUID, stock_quantity INTEGER, created_at TIMESTAMP);",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Product ID", "description": "Unique identifier for the product"},
                {"name": "name", "data_type": "VARCHAR", "semantic_name": "Product Name", "description": "Product display name", "context_note": "Used in search and listings"},
                {"name": "price", "data_type": "DECIMAL", "semantic_name": "Price", "description": "Current selling price", "context_note": "In EUR, excluding VAT"},
                {"name": "category_id", "data_type": "UUID", "semantic_name": "Category ID", "description": "Reference to product category"},
                {"name": "stock_quantity", "data_type": "INTEGER", "semantic_name": "Stock Quantity", "description": "Available inventory", "context_note": "NULL means unlimited stock"},
                {"name": "created_at", "data_type": "TIMESTAMP", "semantic_name": "Created At", "description": "Product creation timestamp"}
            ]
        },
        {
            "physical_name": "customers",
            "semantic_name": "Customers",
            "slug": "customers",
            "description": "Customer master data with contact information and preferences.",
            "ddl_context": "CREATE TABLE customers (id UUID PRIMARY KEY, email VARCHAR(255), first_name VARCHAR(100), last_name VARCHAR(100), country VARCHAR(2), registration_date TIMESTAMP);",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Customer ID", "description": "Unique identifier for the customer"},
                {"name": "email", "data_type": "VARCHAR", "semantic_name": "Email", "description": "Customer email address", "context_note": "Used for login and notifications"},
                {"name": "first_name", "data_type": "VARCHAR", "semantic_name": "First Name", "description": "Customer first name"},
                {"name": "last_name", "data_type": "VARCHAR", "semantic_name": "Last Name", "description": "Customer last name"},
                {"name": "country", "data_type": "VARCHAR", "semantic_name": "Country Code", "description": "ISO country code", "context_note": "2-letter code (e.g., IT, US, DE)"},
                {"name": "registration_date", "data_type": "TIMESTAMP", "semantic_name": "Registration Date", "description": "When customer registered"}
            ]
        },
        {
            "physical_name": "orders",
            "semantic_name": "Orders",
            "slug": "orders",
            "description": "Customer orders with line items and status tracking.",
            "ddl_context": "CREATE TABLE orders (id UUID PRIMARY KEY, customer_id UUID REFERENCES customers(id), order_date TIMESTAMP, total_amount DECIMAL(10,2), status VARCHAR(50));",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Order ID", "description": "Unique identifier for the order"},
                {"name": "customer_id", "data_type": "UUID", "semantic_name": "Customer ID", "description": "Foreign key to customer"},
                {"name": "order_date", "data_type": "TIMESTAMP", "semantic_name": "Order Date", "description": "When the order was placed"},
                {"name": "total_amount", "data_type": "DECIMAL", "semantic_name": "Total Amount", "description": "Order total including tax", "context_note": "Includes shipping and VAT"},
                {"name": "status", "data_type": "VARCHAR", "semantic_name": "Order Status", "description": "Current order status", "context_note": "PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED"}
            ]
        },
        {
            "physical_name": "order_items",
            "semantic_name": "Order Items",
            "slug": "order-items",
            "description": "Line items for each order with product details and quantities.",
            "ddl_context": "CREATE TABLE order_items (id UUID PRIMARY KEY, order_id UUID REFERENCES orders(id), product_id UUID REFERENCES products(id), quantity INTEGER, unit_price DECIMAL(10,2));",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Item ID", "description": "Unique identifier for the order item"},
                {"name": "order_id", "data_type": "UUID", "semantic_name": "Order ID", "description": "Foreign key to order"},
                {"name": "product_id", "data_type": "UUID", "semantic_name": "Product ID", "description": "Foreign key to product"},
                {"name": "quantity", "data_type": "INTEGER", "semantic_name": "Quantity", "description": "Number of units ordered"},
                {"name": "unit_price", "data_type": "DECIMAL", "semantic_name": "Unit Price", "description": "Price per unit at time of order", "context_note": "May differ from current product price"}
            ]
        },
        {
            "physical_name": "payments",
            "semantic_name": "Payments",
            "slug": "payments",
            "description": "Payment transactions linked to orders.",
            "ddl_context": "CREATE TABLE payments (id UUID PRIMARY KEY, order_id UUID REFERENCES orders(id), amount DECIMAL(10,2), payment_method VARCHAR(50), status VARCHAR(50), processed_at TIMESTAMP);",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Payment ID", "description": "Unique identifier for the payment"},
                {"name": "order_id", "data_type": "UUID", "semantic_name": "Order ID", "description": "Foreign key to order"},
                {"name": "amount", "data_type": "DECIMAL", "semantic_name": "Amount", "description": "Payment amount", "context_note": "Should match order total_amount"},
                {"name": "payment_method", "data_type": "VARCHAR", "semantic_name": "Payment Method", "description": "Payment method used", "context_note": "CREDIT_CARD, PAYPAL, BANK_TRANSFER"},
                {"name": "status", "data_type": "VARCHAR", "semantic_name": "Payment Status", "description": "Payment processing status", "context_note": "PENDING, PROCESSING, COMPLETED, FAILED, REFUNDED"},
                {"name": "processed_at", "data_type": "TIMESTAMP", "semantic_name": "Processed At", "description": "When payment was processed"}
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
        ("customers", "id", "orders", "customer_id", "ONE_TO_MANY", "Customer -> Orders"),
        ("orders", "id", "order_items", "order_id", "ONE_TO_MANY", "Order -> Order Items"),
        ("products", "id", "order_items", "product_id", "ONE_TO_MANY", "Product -> Order Items"),
        ("orders", "id", "payments", "order_id", "ONE_TO_MANY", "Order -> Payments")
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


def seed_hr_ontology():
    """Seed HR datasource with employees, departments, salaries, attendance."""
    print("\n🏗️  Seeding HR Datasource (HR_DWH)...")
    
    # 1. Create Datasource
    ds_payload = {
        "name": "HR_DWH",
        "slug": "hr_prod",
        "description": "Human Resources Data Warehouse. Handles employees, departments, salaries, and attendance tracking. Source of truth for workforce data.",
        "engine": "postgres",
        "connection_string": DB_CONNECTION_STRING_HR,
        "context_signature": "HR, Employees, Departments, Salaries, Attendance, Workforce, Payroll"
    }
    ds = make_request("POST", "/datasources", ds_payload)
    if not ds:
        print("❌ Failed to create HR datasource. Aborting.")
        return None, None
        
    ds_id = ds["id"]
    print(f"✅ Created Datasource: {ds['name']} ({ds_id})")
    
    # 2. Create Tables & Columns
    table_map = {}
    
    tables_def = [
        {
            "physical_name": "departments",
            "semantic_name": "Departments",
            "slug": "departments",
            "description": "Organizational departments and divisions.",
            "ddl_context": "CREATE TABLE departments (id UUID PRIMARY KEY, name VARCHAR(255), manager_id UUID, budget DECIMAL(12,2), location VARCHAR(100));",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Department ID", "description": "Unique identifier for the department"},
                {"name": "name", "data_type": "VARCHAR", "semantic_name": "Department Name", "description": "Department name", "context_note": "e.g., 'Engineering', 'Sales', 'Marketing'"},
                {"name": "manager_id", "data_type": "UUID", "semantic_name": "Manager ID", "description": "Reference to department manager (employee)"},
                {"name": "budget", "data_type": "DECIMAL", "semantic_name": "Annual Budget", "description": "Department annual budget", "context_note": "In EUR"},
                {"name": "location", "data_type": "VARCHAR", "semantic_name": "Location", "description": "Office location", "context_note": "City or office name"}
            ]
        },
        {
            "physical_name": "employees",
            "semantic_name": "Employees",
            "slug": "employees",
            "description": "Employee master data with personal information and employment details.",
            "ddl_context": "CREATE TABLE employees (id UUID PRIMARY KEY, employee_code VARCHAR(50), first_name VARCHAR(100), last_name VARCHAR(100), email VARCHAR(255), department_id UUID, hire_date DATE, status VARCHAR(50));",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Employee ID", "description": "Unique identifier for the employee"},
                {"name": "employee_code", "data_type": "VARCHAR", "semantic_name": "Employee Code", "description": "Human-readable employee identifier", "context_note": "e.g., 'EMP-001'"},
                {"name": "first_name", "data_type": "VARCHAR", "semantic_name": "First Name", "description": "Employee first name"},
                {"name": "last_name", "data_type": "VARCHAR", "semantic_name": "Last Name", "description": "Employee last name"},
                {"name": "email", "data_type": "VARCHAR", "semantic_name": "Email", "description": "Work email address"},
                {"name": "department_id", "data_type": "UUID", "semantic_name": "Department ID", "description": "Foreign key to department"},
                {"name": "hire_date", "data_type": "DATE", "semantic_name": "Hire Date", "description": "Employment start date"},
                {"name": "status", "data_type": "VARCHAR", "semantic_name": "Employment Status", "description": "Current employment status", "context_note": "ACTIVE, ON_LEAVE, TERMINATED"}
            ]
        },
        {
            "physical_name": "salaries",
            "semantic_name": "Salaries",
            "slug": "salaries",
            "description": "Employee salary records with compensation details.",
            "ddl_context": "CREATE TABLE salaries (id UUID PRIMARY KEY, employee_id UUID REFERENCES employees(id), base_salary DECIMAL(10,2), bonus DECIMAL(10,2), effective_from DATE, effective_to DATE);",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Salary ID", "description": "Unique identifier for the salary record"},
                {"name": "employee_id", "data_type": "UUID", "semantic_name": "Employee ID", "description": "Foreign key to employee"},
                {"name": "base_salary", "data_type": "DECIMAL", "semantic_name": "Base Salary", "description": "Annual base salary", "context_note": "In EUR, gross amount"},
                {"name": "bonus", "data_type": "DECIMAL", "semantic_name": "Bonus", "description": "Annual bonus amount", "context_note": "Can be NULL if no bonus"},
                {"name": "effective_from", "data_type": "DATE", "semantic_name": "Effective From", "description": "Salary effective start date"},
                {"name": "effective_to", "data_type": "DATE", "semantic_name": "Effective To", "description": "Salary effective end date", "context_note": "NULL if currently active"}
            ]
        },
        {
            "physical_name": "attendance",
            "semantic_name": "Attendance",
            "slug": "attendance",
            "description": "Employee attendance and time tracking records.",
            "ddl_context": "CREATE TABLE attendance (id UUID PRIMARY KEY, employee_id UUID REFERENCES employees(id), date DATE, check_in TIME, check_out TIME, hours_worked DECIMAL(4,2), status VARCHAR(50));",
            "columns": [
                {"name": "id", "data_type": "UUID", "is_primary_key": True, "semantic_name": "Attendance ID", "description": "Unique identifier for the attendance record"},
                {"name": "employee_id", "data_type": "UUID", "semantic_name": "Employee ID", "description": "Foreign key to employee"},
                {"name": "date", "data_type": "DATE", "semantic_name": "Date", "description": "Attendance date"},
                {"name": "check_in", "data_type": "TIME", "semantic_name": "Check In", "description": "Check-in time", "context_note": "NULL if absent"},
                {"name": "check_out", "data_type": "TIME", "semantic_name": "Check Out", "description": "Check-out time", "context_note": "NULL if absent or still working"},
                {"name": "hours_worked", "data_type": "DECIMAL", "semantic_name": "Hours Worked", "description": "Total hours worked", "context_note": "Calculated from check_in/check_out"},
                {"name": "status", "data_type": "VARCHAR", "semantic_name": "Status", "description": "Attendance status", "context_note": "PRESENT, ABSENT, SICK_LEAVE, VACATION"}
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
        ("departments", "id", "employees", "department_id", "ONE_TO_MANY", "Department -> Employees"),
        ("employees", "id", "salaries", "employee_id", "ONE_TO_MANY", "Employee -> Salary Records"),
        ("employees", "id", "attendance", "employee_id", "ONE_TO_MANY", "Employee -> Attendance Records"),
        ("employees", "id", "departments", "manager_id", "ONE_TO_ONE", "Employee -> Department (as Manager)")
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


def seed_ecommerce_semantics(datasource_id, table_map):
    """Seed semantic layer for E-commerce datasource."""
    print("\n🧠 Seeding E-commerce Semantic Layer...")
    
    # Metrics
    metrics = [
        {
            "datasource_id": datasource_id,
            "name": "Total Revenue",
            "slug": "total-revenue",
            "description": "Total revenue from completed orders.",
            "sql_expression": "SUM(orders.total_amount)",
            "filter_condition": "orders.status = 'DELIVERED'",
            "required_table_ids": [table_map["orders"]["id"]]
        },
        {
            "datasource_id": datasource_id,
            "name": "Average Order Value",
            "slug": "avg-order-value",
            "description": "Average value per order.",
            "sql_expression": "AVG(orders.total_amount)",
            "filter_condition": "orders.status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')",
            "required_table_ids": [table_map["orders"]["id"]]
        },
        {
            "datasource_id": datasource_id,
            "name": "Active Customers",
            "slug": "active-customers",
            "description": "Count of customers who placed orders in the last 30 days.",
            "sql_expression": "COUNT(DISTINCT orders.customer_id)",
            "filter_condition": "orders.order_date >= CURRENT_DATE - INTERVAL '30 days'",
            "required_table_ids": [table_map["orders"]["id"]]
        }
    ]
    
    for m in metrics:
        res = make_request("POST", "/metrics", m)
        if res:
            print(f"   Created Metric: {m['name']}")
    
    # Synonyms
    syn_def = [
        ("products", ["Prodotti", "Articoli", "Merci", "Items", "SKU"]),
        ("orders", ["Ordini", "Acquisti", "Transazioni", "Purchases"]),
        ("customers", ["Clienti", "Utenti", "Buyers", "Consumers"]),
        ("payments", ["Pagamenti", "Transazioni Pagamento", "Payments"])
    ]
    
    for t_name, terms in syn_def:
        payload = {
            "target_id": table_map[t_name]["id"],
            "target_type": "TABLE",
            "terms": terms
        }
        res = make_request("POST", "/synonyms/bulk", payload)
        if res:
            print(f"   Created Synonyms for {t_name}")


def seed_hr_semantics(datasource_id, table_map):
    """Seed semantic layer for HR datasource."""
    print("\n🧠 Seeding HR Semantic Layer...")
    
    # Metrics
    metrics = [
        {
            "datasource_id": datasource_id,
            "name": "Total Payroll",
            "slug": "total-payroll",
            "description": "Total annual payroll cost including base salaries and bonuses.",
            "sql_expression": "SUM(salaries.base_salary + COALESCE(salaries.bonus, 0))",
            "filter_condition": "salaries.effective_to IS NULL",
            "required_table_ids": [table_map["salaries"]["id"]]
        },
        {
            "datasource_id": datasource_id,
            "name": "Active Employees",
            "slug": "active-employees",
            "description": "Count of currently active employees.",
            "sql_expression": "COUNT(*)",
            "filter_condition": "employees.status = 'ACTIVE'",
            "required_table_ids": [table_map["employees"]["id"]]
        },
        {
            "datasource_id": datasource_id,
            "name": "Average Salary",
            "slug": "avg-salary",
            "description": "Average base salary for active employees.",
            "sql_expression": "AVG(salaries.base_salary)",
            "filter_condition": "employees.status = 'ACTIVE' AND salaries.effective_to IS NULL",
            "required_table_ids": [table_map["employees"]["id"], table_map["salaries"]["id"]]
        }
    ]
    
    for m in metrics:
        res = make_request("POST", "/metrics", m)
        if res:
            print(f"   Created Metric: {m['name']}")
    
    # Synonyms
    syn_def = [
        ("employees", ["Dipendenti", "Lavoratori", "Staff", "Workforce", "Personnel"]),
        ("departments", ["Dipartimenti", "Reparti", "Divisioni", "Units"]),
        ("salaries", ["Stipendi", "Compensi", "Retribuzioni", "Wages"]),
        ("attendance", ["Presenze", "Timbrature", "Time Tracking", "Timesheets"])
    ]
    
    for t_name, terms in syn_def:
        payload = {
            "target_id": table_map[t_name]["id"],
            "target_type": "TABLE",
            "terms": terms
        }
        res = make_request("POST", "/synonyms/bulk", payload)
        if res:
            print(f"   Created Synonyms for {t_name}")


def seed_ecommerce_context(table_map):
    """Seed context and values for E-commerce datasource."""
    print("\n📜 Seeding E-commerce Context & Values...")
    
    # Context Rules
    rules = [
        ("orders", "status", "Only 'DELIVERED' orders count as revenue. 'CANCELLED' orders should be excluded from sales metrics."),
        ("payments", "status", "Only 'COMPLETED' payments are considered successful. 'FAILED' or 'REFUNDED' payments should be excluded."),
        ("products", "stock_quantity", "If stock_quantity is NULL, product has unlimited stock. If 0, product is out of stock.")
    ]
    
    for t_name, c_name, text in rules:
        try:
            col_id = table_map[t_name]["cols"][c_name]
            rule_hash = str(hash(text))[-6:]
            payload = {
                "column_id": col_id,
                "rule_text": text,
                "slug": f"rule-{t_name}-{c_name}-{rule_hash}"
            }
            make_request("POST", "/context-rules", payload)
            print(f"   Added Rule to {t_name}.{c_name}")
        except KeyError:
            pass
    
    # Nominal Values
    values_map = [
        ("orders", "status", [
            {"raw": "PENDING", "label": "In Attesa"},
            {"raw": "CONFIRMED", "label": "Confermato"},
            {"raw": "SHIPPED", "label": "Spedito"},
            {"raw": "DELIVERED", "label": "Consegnato"},
            {"raw": "CANCELLED", "label": "Annullato"}
        ]),
        ("payments", "payment_method", [
            {"raw": "CREDIT_CARD", "label": "Carta di Credito"},
            {"raw": "PAYPAL", "label": "PayPal"},
            {"raw": "BANK_TRANSFER", "label": "Bonifico Bancario"}
        ]),
        ("payments", "status", [
            {"raw": "PENDING", "label": "In Attesa"},
            {"raw": "PROCESSING", "label": "In Elaborazione"},
            {"raw": "COMPLETED", "label": "Completato"},
            {"raw": "FAILED", "label": "Fallito"},
            {"raw": "REFUNDED", "label": "Rimborsato"}
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
        except KeyError:
            pass


def seed_hr_context(table_map):
    """Seed context and values for HR datasource."""
    print("\n📜 Seeding HR Context & Values...")
    
    # Context Rules
    rules = [
        ("employees", "status", "Only 'ACTIVE' employees are included in headcount. 'TERMINATED' employees are historical records."),
        ("salaries", "effective_to", "If effective_to is NULL, this is the current active salary. Historical salaries have both effective_from and effective_to dates."),
        ("attendance", "status", "'PRESENT' means employee worked. 'SICK_LEAVE' and 'VACATION' are paid time off types.")
    ]
    
    for t_name, c_name, text in rules:
        try:
            col_id = table_map[t_name]["cols"][c_name]
            rule_hash = str(hash(text))[-6:]
            payload = {
                "column_id": col_id,
                "rule_text": text,
                "slug": f"rule-{t_name}-{c_name}-{rule_hash}"
            }
            make_request("POST", "/context-rules", payload)
            print(f"   Added Rule to {t_name}.{c_name}")
        except KeyError:
            pass
    
    # Nominal Values
    values_map = [
        ("employees", "status", [
            {"raw": "ACTIVE", "label": "Attivo"},
            {"raw": "ON_LEAVE", "label": "In Permesso"},
            {"raw": "TERMINATED", "label": "Terminato"}
        ]),
        ("attendance", "status", [
            {"raw": "PRESENT", "label": "Presente"},
            {"raw": "ABSENT", "label": "Assente"},
            {"raw": "SICK_LEAVE", "label": "Malattia"},
            {"raw": "VACATION", "label": "Ferie"}
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
        except KeyError:
            pass


def seed_ecommerce_golden_sql(ds_id):
    """Seed Golden SQL examples for E-commerce datasource."""
    print("\n🌟 Seeding E-commerce Golden SQL...")
    
    examples = [
        {
            "prompt_text": "Show total revenue for last month",
            "sql_query": "SELECT SUM(total_amount) FROM orders WHERE status = 'DELIVERED' AND order_date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') AND order_date < date_trunc('month', CURRENT_DATE);",
            "complexity": 2
        },
        {
            "prompt_text": "List top 10 customers by total orders",
            "sql_query": "SELECT c.first_name, c.last_name, COUNT(o.id) as order_count FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.id, c.first_name, c.last_name ORDER BY order_count DESC LIMIT 10;",
            "complexity": 3
        },
        {
            "prompt_text": "Find products with low stock",
            "sql_query": "SELECT name, stock_quantity FROM products WHERE stock_quantity IS NOT NULL AND stock_quantity < 10 ORDER BY stock_quantity ASC;",
            "complexity": 1
        }
    ]
    
    for ex in examples:
        ex["datasource_id"] = ds_id
        res = make_request("POST", "/golden-sql", ex)
        if res:
            print(f"   Created Golden SQL: {ex['prompt_text'][:30]}...")


def seed_hr_golden_sql(ds_id):
    """Seed Golden SQL examples for HR datasource."""
    print("\n🌟 Seeding HR Golden SQL...")
    
    examples = [
        {
            "prompt_text": "Calculate total payroll cost",
            "sql_query": "SELECT SUM(base_salary + COALESCE(bonus, 0)) FROM salaries WHERE effective_to IS NULL;",
            "complexity": 2
        },
        {
            "prompt_text": "List employees by department with their salaries",
            "sql_query": "SELECT d.name as department, e.first_name, e.last_name, s.base_salary FROM employees e JOIN departments d ON e.department_id = d.id JOIN salaries s ON e.id = s.employee_id WHERE e.status = 'ACTIVE' AND s.effective_to IS NULL ORDER BY d.name, e.last_name;",
            "complexity": 3
        },
        {
            "prompt_text": "Show attendance summary for current month",
            "sql_query": "SELECT e.first_name, e.last_name, COUNT(*) as days_present FROM attendance a JOIN employees e ON a.employee_id = e.id WHERE a.date >= date_trunc('month', CURRENT_DATE) AND a.status = 'PRESENT' GROUP BY e.id, e.first_name, e.last_name ORDER BY days_present DESC;",
            "complexity": 3
        }
    ]
    
    for ex in examples:
        ex["datasource_id"] = ds_id
        res = make_request("POST", "/golden-sql", ex)
        if res:
            print(f"   Created Golden SQL: {ex['prompt_text'][:30]}...")


if __name__ == "__main__":
    try:
        cleanup()
        
        # Seed E-commerce datasource
        ecommerce_ds_id, ecommerce_table_map = seed_ecommerce_ontology()
        if ecommerce_table_map and ecommerce_ds_id:
            seed_ecommerce_semantics(ecommerce_ds_id, ecommerce_table_map)
            seed_ecommerce_context(ecommerce_table_map)
            seed_ecommerce_golden_sql(ecommerce_ds_id)
        
        # Seed HR datasource
        hr_ds_id, hr_table_map = seed_hr_ontology()
        if hr_table_map and hr_ds_id:
            seed_hr_semantics(hr_ds_id, hr_table_map)
            seed_hr_context(hr_table_map)
            seed_hr_golden_sql(hr_ds_id)
        
        print("\n✨ Multi-Datasource Seed Finished Successfully!")
        print(f"\n📊 Created Datasources:")
        print(f"   - E-commerce_DWH (slug: ecommerce_prod)")
        print(f"   - HR_DWH (slug: hr_prod)")
        print(f"\n💡 You can now test retrieval APIs with multiple datasources!")
        
    except KeyboardInterrupt:
        print("\n🛑 Seed Aborted.")
    except Exception as e:
        print(f"\n❌ Error during seed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
