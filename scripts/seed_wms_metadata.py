
import logging
import sys
import os
from uuid import uuid4
from typing import Dict, List, Tuple
import random
from datetime import datetime, timedelta
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import SessionLocal
from src.db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge, 
    SemanticMetric, SemanticSynonym, ColumnContextRule, 
    LowCardinalityValue, SQLEngineType, RelationshipType, SynonymTargetType,
    GoldenSQL
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA DEFINITIONS
# ============================================================================

# Structure: Table Name -> 
#   description: str
#   columns: List[Tuple[Name, Type, Description, ContextNote]]
WMS_SCHEMA = {
    "batch": {
        "description": "Registry of production batches, tracking expiration and incoming dates.",
        "columns": [
            ("batch_id", "INT8", "Unique internal identifier for the batch record.", "Primary Key. Auto-increment integer."),
            ("batch_code", "VARCHAR(100)", "Business code identifying the specific batch (e.g. lot number).", "Often printed on physical labels. Used for traceability."),
            ("expire_date", "TIMESTAMP", "Date and time when the batch expires.", "Critical for FEFO (First Expired First Out) logic. If NULL, batch does not expire."),
            ("incoming_date", "TIMESTAMP", "Date and time when the batch was received.", "Used for aging reports and FIFO logic."),
            ("supplier_batch_code", "VARCHAR(100)", "Original batch code provided by the supplier.", "Used for vendor quality tracking and recalls."),
            ("is_blocked", "INT2", "Blocking flag.", "1 = Blocked (Quarantined), 0 = Available. blocked batches cannot be reserved."),
            ("product_id", "INT8", "Foreign key referencing the associated product.", "Links to ai.product table."),
            ("product_code", "VARCHAR(100)", "Code of the product associated with this batch.", "Redundant/Denormalized for performance."),
            ("product_description", "VARCHAR(255)", "Description/name of the product associated with this batch.", "Redundant/Denormalized for performance."),
        ]
    },
    "product": {
        "description": "Master catalog of products managed in the warehouse.",
        "columns": [
            ("product_id", "INT8", "Unique internal identifier for the product.", "Primary Key."),
            ("product_code", "VARCHAR(100)", "Unique SKU or business code identifying the product.", "The main identifier used by operators."),
            ("product_description", "VARCHAR(255)", "Full commercial name and description of the product.", "Includes size/color variants if applicable."),
        ]
    },
    "shipmission_done": {
        "description": "Historical record of completed shipping missions and fulfilled orders.",
        "columns": [
            ("mission_id", "INT8", "Unique identifier for the shipping mission.", "Primary Key component or indexing key."),
            ("mission_name", "VARCHAR(100)", "Human-readable name or code assigned to the mission.", "Often corresponds to the Customer Order Number."),
            ("mission_date", "TIMESTAMP", "Date and time when the mission was created.", "Creation timestamp."),
            ("account_id", "INT8", "Identifier of the client account.", "Links to external Customer/Account table (not in this schema)."),
            ("account_type", "INT2", "Type classification of the account.", "Enum: 1=Retail, 2=Wholesale, 3=Internal."),
            ("account_code", "VARCHAR(100)", "Business code of the client account.", "Customer ERP Code."),
            ("account_name", "VARCHAR(255)", "Full name of the client/account.", "Name used on shipping labels."),
            ("delivery_date", "TIMESTAMP", "Expected or actual date of delivery.", "SLA target date."),
            ("product_id", "INT8", "Foreign key to the product being shipped.", "Links to ai.product."),
            ("product_code", "VARCHAR(100)", "Code of the product shipped.", "Snapshot at time of shipping."),
            ("product_description", "VARCHAR(255)", "Description of the product shipped.", "Snapshot at time of shipping."),
            ("quantity_to_ship", "NUMERIC(20, 10)", "Target quantity requested for shipment.", "Original order quantity."),
            ("shipped_quantity", "NUMERIC(20, 10)", "Actual quantity that was shipped.", "Should match quantity_to_ship unless shortages occurred."),
            ("measure_unit", "VARCHAR(20)", "Unit of measure for the quantity.", "e.g., KG, PZ, L. Must match product base UoM."),
            ("package_quantity_to_ship", "NUMERIC(38, 7)", "Number of packages expected.", "Calculated based on palletization rules."),
            ("package_quantity_shipped", "NUMERIC(38, 7)", "Actual number of packages shipped.", "Count of physical cartons/pallets."),
            ("total_weight_to_ship", "NUMERIC(38, 17)", "Estimated total weight.", "Theoretical weight based on product master data."),
            ("total_weight_shipped", "NUMERIC(38, 17)", "Actual total weight.", "Measured weight from scale or sum of items."),
            ("shipper_id", "INT8", "Identifier of the shipping carrier.", "Foreign Key to Carrier table (external)."),
            ("shipper_code", "VARCHAR(100)", "Code of the shipping carrier.", "Carrier service code."),
            ("shipper_name", "VARCHAR(100)", "Name of the shipping carrier.", "e.g. DHL, UPS, FedEx."),
            ("shipping_zone", "VARCHAR(255)", "Geographic zone or route.", "Used for logistics planning and sorting."),
            ("shipping_state", "VARCHAR(100)", "State or region of the destination.", "Address component."),
            ("shipping_province", "VARCHAR(100)", "Province or district of the destination.", "Address component."),
            ("operator_name", "VARCHAR(10)", "Name or ID of the operator.", "User who finalized the shipment."),
            ("shipping_date", "TIMESTAMP", "Timestamp when goods left warehouse.", "Actual Ship Date."),
            ("row_is_shipped", "INT4", "Status flag.", "1 = Shipped, 0 = Pending/Cancelled."),
            ("capacity_quantity", "NUMERIC(20, 10)", "Volume or capacity metric.", "Used for truck load planning."),
            ("conversionfactor_1to2", "NUMERIC(20, 10)", "Conversion factor.", "Multiplier between primary and secondary UoM."),
        ]
    },
    "shipmission_todo": {
        "description": "Queue of pending shipping missions waiting to be processed.",
        "columns": [
            ("mission_id", "INT8", "Unique identifier for the shipping mission.", "Primary Key."),
            ("mission_name", "VARCHAR(100)", "Name or code of the planned mission.", "Order Reference."),
            ("mission_date", "TIMESTAMP", "Date when the mission was scheduled.", "Order Date."),
            ("delivery_date", "TIMESTAMP", "Requested delivery date.", "Customer Request Date (CRD)."),
            ("account_id", "INT8", "Identifier of the customer account.", "Customer ID."),
            ("account_type", "INT2", "Type classification of the customer account.", "Customer Class."),
            ("account_code", "VARCHAR(100)", "Code of the customer account.", "Customer Code."),
            ("account_name", "VARCHAR(255)", "Name of the customer account.", "Customer Name."),
            ("product_id", "INT8", "Foreign key to the product to be shipped.", "Links to ai.product."),
            ("product_code", "VARCHAR(100)", "Code of the product to be shipped.", "SKU."),
            ("product_description", "VARCHAR(255)", "Description of the product to be shipped.", "Product Name."),
            ("quantity", "NUMERIC(20, 10)", "Quantity requested for this order line.", "Order Qty."),
            ("measure_unit", "VARCHAR(20)", "Unit of measure for the quantity.", "UoM."),
            ("package_quantity", "NUMERIC(38, 7)", "Number of packages expected.", "Handling Units."),
            ("total_weight", "NUMERIC(38, 17)", "Total estimated weight.", "Gross Weight."),
            ("shipper_id", "INT8", "Identifier of the assigned carrier.", "Carrier ID."),
            ("shipper_code", "VARCHAR(100)", "Code of the assigned carrier.", "Carrier Code."),
            ("shipper_name", "VARCHAR(100)", "Name of the assigned carrier.", "Carrier Name."),
            ("shipping_zone", "VARCHAR(255)", "Destination zone/route.", "Logistics Zone."),
            ("shipping_state", "VARCHAR(100)", "Destination state/region.", "Ship-to State."),
            ("shipping_province", "VARCHAR(100)", "Destination province.", "Ship-to Province."),
        ]
    },
    "warehouse": {
        "description": "Physical warehouse facilities.",
        "columns": [
            ("warehouse_id", "INT8", "Unique identifier for the warehouse facility.", "Primary Key."),
            ("warehouse_name", "VARCHAR(100)", "Name of the warehouse.", "e.g. 'Main DC', 'Overflow Storage'."),
            ("warehouse_description", "VARCHAR(255)", "Description or location details.", "Physical address or notes."),
        ]
    },
    "warehouse_locations": {
        "description": "Mapping of physical storage locations (bins, shelves) within the warehouse.",
        "columns": [
            ("location_id", "INT8", "Unique identifier for the specific location.", "Primary Key."),
            ("location_code", "VARCHAR(100)", "Barcode or human-readable code.", "Format: ZONE-AISLE-BAY-LEVEL (e.g. A-01-02-1)."),
            ("warehouse_id", "INT8", "Foreign key to the warehouse.", "Links to ai.warehouse."),
            ("warehouse_name", "VARCHAR(100)", "Name of the warehouse.", "Denormalized name."),
            ("shelf_code", "VARCHAR(100)", "Code identifying the specific shelf.", "Grouping for location hierarchy."),
            ("floor_code", "VARCHAR(20)", "Code identifying the floor level.", "Height level identifier."),
            ("box_code", "VARCHAR(20)", "Code identifying the specific box or bin.", "Smallest addressable unit."),
            ("location_behavior", "VARCHAR(12)", "Behavioral type of the location.", "Values: PICKING, BUFFER, QUARANTINE."),
        ]
    },
    "warehouse_movements": {
        "description": "Log of all stock movements (inbound, outbound, internal transfers).",
        "columns": [
            ("movement_date", "TIMESTAMP", "Timestamp when the movement occurred.", "Transaction time."),
            ("movement_user_name", "VARCHAR(10)", "User ID of the operator.", "Who performed the action."),
            ("warehouse_id", "INT8", "Warehouse where the movement took place.", "Site ID."),
            ("warehouse_name", "VARCHAR(100)", "Name of the warehouse.", "Site Name."),
            ("location_id", "INT8", "Location ID associated with the movement.", "Source or Destination Location depending on sign."),
            ("location_code", "VARCHAR(100)", "Location code involved.", "Location Barcode."),
            ("product_id", "INT8", "Product involved in the movement.", "Product ID."),
            ("product_code", "VARCHAR(100)", "Code of the product moved.", "Product SKU."),
            ("product_description", "VARCHAR(255)", "Description of the product moved.", "Product Name."),
            ("batch_id", "INT8", "Batch ID of the product moved.", "Links to ai.batch."),
            ("batch_code", "VARCHAR(100)", "Batch code.", "Lot Number."),
            ("batch_expire_date", "TIMESTAMP", "Expiration date of the batch.", "Expiry."),
            ("cause_description", "VARCHAR(255)", "Reason or cause for the movement.", "Transaction Reason Code."),
            ("movement_type", "INT4", "Code representing the type of movement.", "101=Receipt, 201=Issue, 301=Transfer."),
            ("movement_sign", "INT2", "Direction of stock change.", "1 = Increase (Inbound), -1 = Decrease (Outbound)."),
            ("movement_quantity", "NUMERIC(20, 10)", "Quantity of product moved.", "Always positive; sign determines direction."),
            ("measure_unit", "VARCHAR(20)", "Unit of measure for the movement.", "UoM."),
            ("movement_package_quantit", "NUMERIC(38, 7)", "Number of packages moved.", "Package Count."),
            ("account_type", "INT2", "Type of account related to the movement.", "Entity type."),
            ("account_code", "VARCHAR(100)", "Account code related to the movement.", "Entity Code."),
            ("account_name", "VARCHAR(255)", "Account name related to the movement.", "Entity Name."),
        ]
    },
    "warehouse_stock": {
        "description": "Current snapshot of inventory levels by location and batch.",
        "columns": [
            ("warehouse_id", "INT8", "Warehouse identifier.", "Site ID."),
            ("warehouse_name", "VARCHAR(100)", "Name of the warehouse.", "Site Name."),
            ("location_id", "INT8", "Location identifier where stock is held.", "Bin ID."),
            ("location_code", "VARCHAR(100)", "Code of the location.", "Bin Code."),
            ("product_id", "INT8", "Product identifier.", "Item ID."),
            ("product_code", "VARCHAR(100)", "Product code.", "Item SKU."),
            ("product_description", "VARCHAR(255)", "Product description.", "Item Name."),
            ("product_hasbatch", "INT4", "Flag indicating if the product is batch-managed.", "1=Yes, 0=No."),
            ("batch_id", "INT8", "Batch identifier.", "Lot ID."),
            ("batch_code", "VARCHAR(100)", "Batch code.", "Lot Number."),
            ("batch_expire_date", "TIMESTAMP", "Batch expiration date.", "Expiry."),
            ("stock_quantity", "NUMERIC(38, 10)", "Current quantity available.", "On-hand Quantity."),
            ("measure_unit", "VARCHAR(20)", "Unit of measure for the stock.", "Base UoM."),
        ]
    }
}

# (SourceTable, SourceColumn) -> (TargetTable, TargetColumn, RelationshipType, Description)
WMS_EDGES = [
    ("batch", "product_id", "product", "product_id", RelationshipType.ONE_TO_MANY, "Associates a batch with its product definition."),
    ("shipmission_done", "product_id", "product", "product_id", RelationshipType.ONE_TO_MANY, "Links shipped items to the product catalog."),
    ("shipmission_todo", "product_id", "product", "product_id", RelationshipType.ONE_TO_MANY, "Links planned items to the product catalog."),
    ("warehouse_locations", "warehouse_id", "warehouse", "warehouse_id", RelationshipType.ONE_TO_MANY, "Locations belong to a specific warehouse."),
    ("warehouse_stock", "product_id", "product", "product_id", RelationshipType.ONE_TO_MANY, "Stock availability refers to a product."),
    ("warehouse_stock", "batch_id", "batch", "batch_id", RelationshipType.ONE_TO_MANY, "Stock availability links to a specific batch."),
    ("warehouse_stock", "location_id", "warehouse_locations", "location_id", RelationshipType.ONE_TO_MANY, "Stock is stored in a specific location."),
    ("warehouse_movements", "product_id", "product", "product_id", RelationshipType.ONE_TO_MANY, "Movements involve specific products."),
    ("warehouse_movements", "batch_id", "batch", "batch_id", RelationshipType.ONE_TO_MANY, "Movements involve specific batches."),
    ("warehouse_movements", "location_id", "warehouse_locations", "location_id", RelationshipType.ONE_TO_MANY, "Movements occur at a specific location."),
]

# (TableName, ColumnName, RuleText, Slug)
WMS_CONTEXT_RULES = [
    ("batch", "is_blocked", "If 1, the batch is quarantined and cannot be shipped. If 0, it is available.", "rule_batch_blocked"),
    ("batch", "expire_date", "Do not ship batches that are past their expiration date. FEFO (First Expired First Out) applies.", "rule_batch_expired"),
    ("shipmission_todo", "delivery_date", "Urgent missions are those with delivery_date <= CURDATE() + 1.", "rule_urgent_delivery"),
    ("shipmission_done", "row_is_shipped", "Must be 1 for the shipment to be considered fully completed and out the door.", "rule_shipped_status"),
]

# (TableName, ColumnName, ValueRaw, ValueLabel, Slug)
WMS_NOMINAL_VALUES = [
    ("warehouse_locations", "location_behavior", "PICKING", "Picking Area - Active retrieval zone", "val_behavior_picking"),
    ("warehouse_locations", "location_behavior", "BUFFER", "Buffer Area - Reserve storage", "val_behavior_buffer"),
    ("warehouse_locations", "location_behavior", "QUARANTINE", "Quarantine - Blocked stock area", "val_behavior_quarantine"),
    ("warehouse_movements", "movement_sign", "1", "Inbound/Increase", "val_sign_in"),
    ("warehouse_movements", "movement_sign", "-1", "Outbound/Decrease", "val_sign_out"),
    ("batch", "is_blocked", "1", "Blocked/Quarantined", "val_batch_blocked"),
    ("batch", "is_blocked", "0", "Available", "val_batch_avail"),
]

# (Name, Description, SQL, Slug)
WMS_METRICS = [
    ("Total Shipped Quantity", "Total quantity of goods shipped historically.", "SUM(shipmission_done.shipped_quantity)", "metric_total_shipped"),
    ("Current Stock Level", "Total quantity of items currently in stock across all warehouses.", "SUM(warehouse_stock.stock_quantity)", "metric_total_stock"),
    ("Pending Mission Count", "Number of shipping missions waiting to be processed.", "COUNT(shipmission_todo.mission_id)", "metric_pending_missions"),
    ("Expired Batch Count", "Number of batches currently in stock that have passed their expiration date.", "COUNT(batch.batch_id)", "metric_expired_batches"),
    # New Metrics
    ("Order Fulfillment Rate", "Percentage of ordered quantity that was actually shipped.", "SUM(shipmission_done.shipped_quantity) / NULLIF(SUM(shipmission_done.quantity_to_ship), 0) * 100", "metric_fulfillment_rate"),
    ("Quarantined Stock Percentage", "Percentage of stock currently held in quarantine/blocked batches.", "SUM(CASE WHEN batch.is_blocked = 1 THEN warehouse_stock.stock_quantity ELSE 0 END) / NULLIF(SUM(warehouse_stock.stock_quantity), 0) * 100", "metric_quarantined_pct"),
    ("Daily Movement Volume", "Average quantity of items moved per day.", "AVG(warehouse_movements.movement_quantity)", "metric_avg_daily_movement"),
    ("Stockout Risk Items", "Count of products with stock level below 10 units.", "COUNT(DISTINCT CASE WHEN warehouse_stock.stock_quantity < 10 THEN warehouse_stock.product_id END)", "metric_stockout_risk"),
]

# (Term, TargetType, TargetName, Slug)
# TargetName is TableName or ColumnName (Table.Column) or MetricName
WMS_SYNONYMS = [
    ("Item", SynonymTargetType.TABLE, "product", "syn_item_product"),
    ("Merchandise", SynonymTargetType.TABLE, "product", "syn_merch_product"),
    ("Lot", SynonymTargetType.TABLE, "batch", "syn_lot_batch"),
    ("Order", SynonymTargetType.TABLE, "shipmission_todo", "syn_order_mission"),
    ("Inventory", SynonymTargetType.TABLE, "warehouse_stock", "syn_inv_stock"),
    ("Facility", SynonymTargetType.TABLE, "warehouse", "syn_facility_warehouse"),
    ("SKU", SynonymTargetType.COLUMN, "product.product_code", "syn_sku_pcode"),
    ("Expiry", SynonymTargetType.COLUMN, "batch.expire_date", "syn_expiry_date"),
    ("Consignment", SynonymTargetType.TABLE, "shipmission_done", "syn_consignment_done"),
    ("Shipment", SynonymTargetType.TABLE, "shipmission_done", "syn_shipment_done"),
    ("Carrier", SynonymTargetType.COLUMN, "shipmission_done.shipper_name", "syn_carrier_shipper"),
]



def seed_physical_wms_data():
    """
    Seeds physical data into the 'ai' schema tables to support analytical queries.
    Refreshes schema, creates tables from DDL, and populates with synthetic data.
    """
    logger.info("Starting Physical WMS Data Seeding...")
    session = SessionLocal()
    try:
        # 1. Initialize Schema and Tables
        session.execute(text("CREATE SCHEMA IF NOT EXISTS ai;"))
        
        # Drop existing tables to start clean to avoid foreign key or stale data issues
        # Order matters for drops if FKs existed, but here we just drop cascade to be safe
        tables = [
            "warehouse_stock", "warehouse_movements", "warehouse_locations",
            "shipmission_todo", "shipmission_done", "batch", "product", "warehouse"
        ]
        for t in tables:
            session.execute(text(f"DROP TABLE IF EXISTS ai.{t} CASCADE"))
        session.commit()
            
        # Execute DDL
        ddl_path = os.path.join(os.path.dirname(__file__), 'wms_ddl.txt')
        if os.path.exists(ddl_path):
            with open(ddl_path, 'r') as f:
                raw_ddl = f.read()
                stmts = raw_ddl.split(';')
                for stmt in stmts:
                    if stmt.strip():
                        session.execute(text(stmt))
        session.commit()
        logger.info("Schema and Tables created.")
        
        # 2. Generate Base Data
        # Warehouses
        warehouses = [
            (1, "Main DC", "Central Distribution Center"),
            (2, "Regional Hub North", "North Region Support"),
            (3, "Overflow Storage", "Seasonal Buffer")
        ]
        for w in warehouses:
            session.execute(text("INSERT INTO ai.warehouse (warehouse_id, warehouse_name, warehouse_description) VALUES (:id, :name, :desc)"), 
                            {"id": w[0], "name": w[1], "desc": w[2]})
            
        # Products (50 items) - Assign ABC categories implicitly by ID range
        # 1-10: Class A (High Volume) -> We will skew movements towards these
        # 11-30: Class B (Medium Volume)
        # 31-50: Class C (Low Volume)
        products = []
        for i in range(1, 51):
            p_code = f"P{i:03d}"
            adjectives = ["Super", "Ultra", "Eco", "Smart", "Pro", "Max", "Mini"]
            nouns = ["Widget", "Gadget", "Device", "Module", "Sensor", "Controller", "Panel"]
            desc = f"{random.choice(adjectives)} {random.choice(nouns)} {i}"
            products.append((i, p_code, desc))
            session.execute(text("INSERT INTO ai.product (product_id, product_code, product_description) VALUES (:id, :code, :desc)"),
                            {"id": i, "code": p_code, "desc": desc})
            
        # Locations (Bins)
        locations = []
        loc_id_counter = 1
        for w in warehouses:
            w_id = w[0]
            # Generate about 60 locations per warehouse
            for zone in ['A', 'B', 'C']:
                for aisle in range(1, 6): # 5 aisles
                    for bay in range(1, 5): # 4 bays
                         curr_id = loc_id_counter
                         loc_code = f"{zone}-{aisle:02d}-{bay:02d}"
                         behavior = "PICKING" if zone == 'A' else "BUFFER"
                         if zone == 'C': behavior = "QUARANTINE"
                         
                         locations.append((curr_id, loc_code, w_id, w[1], behavior))
                         session.execute(text("""
                            INSERT INTO ai.warehouse_locations 
                            (location_id, location_code, warehouse_id, warehouse_name, location_behavior, shelf_code, floor_code, box_code)
                            VALUES (:id, :code, :wid, :wname, :beh, :shelf, :floor, :box)
                         """), {
                             "id": curr_id, "code": loc_code, "wid": w_id, "wname": w[1], "beh": behavior,
                             "shelf": f"{zone}-{aisle:02d}", "floor": "0", "box": str(bay)
                         })
                         loc_id_counter += 1
                         
        # Batches
        batches = []
        batch_id_counter = 1
        for p in products:
            # Create 2-5 batches per product
            for _ in range(random.randint(2, 5)):
                b_id = batch_id_counter
                b_code = f"LOT-{datetime.now().year}-{b_id:04d}"
                # Mix of expiry dates
                is_expired = random.random() < 0.1 # 10% chance expired
                if is_expired:
                    exp_date = datetime.now() - timedelta(days=random.randint(10, 300))
                else:
                    exp_date = datetime.now() + timedelta(days=random.randint(30, 600))
                
                incoming = datetime.now() - timedelta(days=random.randint(50, 400))
                is_blocked = 1 if (is_expired or random.random() < 0.05) else 0
                
                batches.append((b_id, b_code, exp_date, incoming, is_blocked, p[0], p[1], p[2]))
                session.execute(text("""
                    INSERT INTO ai.batch 
                    (batch_id, batch_code, expire_date, incoming_date, is_blocked, product_id, product_code, product_description)
                    VALUES (:id, :code, :exp, :inc, :blk, :pid, :pcode, :pdesc)
                """), {
                    "id": b_id, "code": b_code, "exp": exp_date, "inc": incoming, "blk": is_blocked,
                    "pid": p[0], "pcode": p[1], "pdesc": p[2]
                })
                batch_id_counter += 1
        session.commit()
                
        # 3. Stock Snapshot (Current State)
        count_stock = 0
        for w in warehouses:
            # Pick locations in this warehouse
            w_locs = [l for l in locations if l[2] == w[0]]
            for p in products:
                # Randomly place product in this warehouse
                if random.random() < 0.7:
                    p_batches = [b for b in batches if b[5] == p[0]]
                    for b in p_batches:
                        if random.random() < 0.6: # Batch is present
                            qty = random.randint(5, 500)
                            # C Class items (id > 30) - some have very high stock (High Availability)
                            if p[0] > 30 and random.random() < 0.3: 
                                qty = random.randint(1000, 2000)
                            
                            # Stockout risk (<10 items) scenarios
                            if random.random() < 0.15: 
                                qty = random.randint(0, 9)
                            
                            loc = random.choice(w_locs)
                            
                            session.execute(text("""
                                INSERT INTO ai.warehouse_stock
                                (warehouse_id, warehouse_name, location_id, location_code, 
                                 product_id, product_code, product_description, 
                                 batch_id, batch_code, batch_expire_date, stock_quantity, measure_unit)
                                VALUES (:wid, :wname, :lid, :lcode, :pid, :pcode, :pdesc, :bid, :bcode, :bexp, :qty, 'PZ')
                            """), {
                                "wid": w[0], "wname": w[1], "lid": loc[0], "lcode": loc[1],
                                "pid": p[0], "pcode": p[1], "pdesc": p[2],
                                "bid": b[0], "bcode": b[1], "bexp": b[2], "qty": qty
                            })
                            count_stock += 1
        session.commit()
                            
        # 4. Movements History (Last 18 months)
        # To answer: "Movements per day", "Top 3 moved products semester compare", "Locations most moved"
        start_date = datetime.now() - timedelta(days=540)
        curr_date = start_date
        
        movements_count = 0
        while curr_date < datetime.now():
            daily_moves = random.randint(5, 25)
            
            for _ in range(daily_moves):
                # Pick a product. Bias towards Class A (1-10) for ABC analysis
                r = random.random()
                if r < 0.6: pid = random.randint(1, 10) # 60% of moves are top 10 products
                elif r < 0.9: pid = random.randint(11, 30)
                else: pid = random.randint(31, 50)
                
                # Verify product exists in our list (it should)
                p_list = [x for x in products if x[0] == pid]
                if not p_list: continue
                p = p_list[0]
                
                p_batches = [b for b in batches if b[5] == pid]
                if not p_batches: continue
                b = random.choice(p_batches)
                
                w = random.choice(warehouses)
                w_locs = [l for l in locations if l[2] == w[0]]
                if not w_locs: continue
                loc = random.choice(w_locs)
                
                move_qty = random.randint(1, 50)
                
                # Seasonality for semester comparison (Top products)
                # If product is 1, 2, or 3 -> Make them move more in different semesters
                month = curr_date.month
                if pid == 1: # High in Semester 1
                    if month <= 6: move_qty *= 2
                elif pid == 2: # High in Semester 2
                    if month > 6: move_qty *= 2
                    
                sign = 1 if random.random() < 0.5 else -1 # In or Out
                # Logic for "Stock drops in last 12 weeks"
                # Last 12 weeks: 12 * 7 = 84 days
                days_ago = (datetime.now() - curr_date).days
                if days_ago < 84 and random.random() < 0.3:
                     sign = -1 # Force more drops
                     
                m_type = 101 if sign == 1 else 201
                
                session.execute(text("""
                    INSERT INTO ai.warehouse_movements
                    (movement_date, warehouse_id, warehouse_name, location_id, location_code,
                     product_id, product_code, product_description, batch_id, batch_code,
                     movement_type, movement_sign, movement_quantity, measure_unit, movement_user_name)
                    VALUES (:date, :wid, :wname, :lid, :lcode, :pid, :pcode, :pdesc, :bid, :bcode, :type, :sign, :qty, 'PZ', 'OpBot')
                """), {
                    "date": curr_date + timedelta(hours=random.randint(8, 17), minutes=random.randint(0, 59)),
                    "wid": w[0], "wname": w[1], "lid": loc[0], "lcode": loc[1],
                    "pid": p[0], "pcode": p[1], "pdesc": p[2],
                    "bid": b[0], "bcode": b[1],
                    "type": m_type, "sign": sign, "qty": move_qty
                })
                movements_count += 1
                
            curr_date += timedelta(days=1)
        session.commit()
            
        # 5. Shipping Missions (Completed)
        # For: "Missions per shipping zone month by month"
        zones = ["North-East", "West-Coast", "Central", "South", "International"]
        mission_date = datetime.now() - timedelta(days=365) # Last year
        mission_id = 1
        
        missions_count = 0
        while mission_date < datetime.now():
            if random.random() < 0.7: # 70% chance of missions on a day
                for _ in range(random.randint(1, 5)):
                    zone = random.choice(zones)
                    p = random.choice(products)
                    qty = random.randint(10, 100)
                    
                    session.execute(text("""
                        INSERT INTO ai.shipmission_done
                        (mission_id, mission_name, mission_date, delivery_date, shipping_date,
                         product_id, product_code, product_description, quantity_to_ship, shipped_quantity,
                         shipping_zone, shipping_state, row_is_shipped, shipper_name)
                        VALUES (:mid, :mname, :mdate, :ddate, :sdate, :pid, :pcode, :pdesc, :qty, :qty, :zone, 'State', 1, 'DHL')
                    """), {
                        "mid": mission_id, "mname": f"ORD-{mission_id}", 
                        "mdate": mission_date, "ddate": mission_date + timedelta(days=2), "sdate": mission_date + timedelta(days=1),
                        "pid": p[0], "pcode": p[1], "pdesc": p[2], "qty": qty, "zone": zone
                    })
                    mission_id += 1
                    missions_count += 1
            mission_date += timedelta(days=1)
            
        # 6. Current Pending Missions
        for i in range(1, 21):
             p = random.choice(products)
             zone = random.choice(zones)
             session.execute(text("""
                INSERT INTO ai.shipmission_todo
                (mission_id, mission_name, mission_date, delivery_date, product_id, product_code, product_description, quantity, shipping_zone)
                VALUES (:mid, :mname, NOW(), NOW() + INTERVAL '2 days', :pid, :pcode, :pdesc, :qty, :zone)
             """), {
                 "mid": mission_id + i, "mname": f"PEND-{i}", 
                 "pid": p[0], "pcode": p[1], "pdesc": p[2],
                 "qty": random.randint(10, 100), "zone": zone
             })
        session.commit()
             
        logger.info(f"Data Generation Summary: {len(products)} products, {count_stock} stock entries, {movements_count} movements, {missions_count} completed missions.")
        logger.info("--- Physical Data Seeding Completed ---")

    except Exception as e:
        session.rollback()
        logger.error(f"Seeding Failed: {e}")
        raise
    finally:
        session.close()

# ============================================================================
# LOGIC
# ============================================================================


def seed_wms_metadata():
    session = SessionLocal()
    try:
        # 0. Cleanup existing Datasource
        existing_ds = session.query(Datasource).filter(Datasource.slug == "wms_prod").first()
        if existing_ds:
            logger.info(f"Removing existing Datasource: {existing_ds.name}")
            
            # Manually delete related entities that might not cascade automatically
            session.query(SemanticMetric).filter(SemanticMetric.datasource_id == existing_ds.id).delete()
            session.query(GoldenSQL).filter(GoldenSQL.datasource_id == existing_ds.id).delete()
            
            # Cleanup Synonyms (they don't have datasource_id and don't cascade)
            syn_slugs = [s[3] for s in WMS_SYNONYMS]
            if syn_slugs:
                session.query(SemanticSynonym).filter(SemanticSynonym.slug.in_(syn_slugs)).delete(synchronize_session=False)

            session.delete(existing_ds)
            session.commit()

        # 1. Create Datasource
        datasource = Datasource(
            id=uuid4(),
            name="WMS Production (AI)",
            slug="wms_prod",
            engine=SQLEngineType.POSTGRES,
            description="Main Warehouse Management System database containing inventory, missions, and movements.",
            context_signature="warehouse, logistics, supply chain, inventory management, shipping, receiving, fulfillment"
        )
        session.add(datasource)
        session.flush()
        logger.info(f"Created Datasource: {datasource.name}")

        # 1.5 Parse DDL from file
        ddl_map = {}
        ddl_path = os.path.join(os.path.dirname(__file__), 'wms_ddl.txt')
        if os.path.exists(ddl_path):
            with open(ddl_path, 'r') as f:
                raw_ddl = f.read()
                # Simple parsing: split by semicolon and find "CREATE TABLE"
                statements = raw_ddl.split(';')
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt.upper().startswith("CREATE TABLE"):
                        # Extract table name: CREATE TABLE schema.table (
                        try:
                            # Remove "CREATE TABLE "
                            rest = stmt[12:].strip()
                            # Split by open parenthesis to get name part
                            name_part = rest.split('(')[0].strip()
                            # Handle schema prefix if present (ai.table)
                            if "." in name_part:
                                table_name = name_part.split('.')[-1].strip()
                            else:
                                table_name = name_part.strip()
                            
                            ddl_map[table_name] = stmt + ";"

                        except Exception as e:
                            logger.warning(f"Error parsing DDL statement: {e}")

        # 2. Create Tables and Columns
        # Keep track of IDs for linking
        table_map: Dict[str, TableNode] = {}
        column_map: Dict[str, ColumnNode] = {} # Key: "table.column"

        for table_name, table_info in WMS_SCHEMA.items():
            table = TableNode(
                id=uuid4(),
                datasource_id=datasource.id,
                physical_name=table_name,
                slug=f"wms_{table_name}",
                semantic_name=table_name.replace("_", " ").title(),
                description=table_info["description"],
                ddl_context=ddl_map.get(table_name)  # Populate DDL context
            )
            session.add(table)
            session.flush()
            table_map[table_name] = table
            logger.info(f"  Created Table: {table.physical_name}")
            if table.ddl_context:
                logger.info(f"    Added DDL context ({len(table.ddl_context)} chars)")

            for col_raw in table_info["columns"]:
                # UPDATED: Now unpacking 4 values
                col_name, col_type, col_desc, col_context = col_raw
                column = ColumnNode(
                    id=uuid4(),
                    table_id=table.id,
                    name=col_name,
                    slug=f"wms_{table_name}_{col_name}",
                    semantic_name=col_name.replace("_", " ").title(),
                    data_type=col_type,
                    description=col_desc,
                    context_note=col_context,  # Added Context Note
                    is_primary_key="Primary Key" in col_context
                )
                session.add(column)
                session.flush()
                column_map[f"{table_name}.{col_name}"] = column
        
        # 3. Create Schema Edges
        for src_tbl, src_col, tgt_tbl, tgt_col, rel_type, desc in WMS_EDGES:
            s_key = f"{src_tbl}.{src_col}"
            t_key = f"{tgt_tbl}.{tgt_col}"
            
            if s_key in column_map and t_key in column_map:
                edge = SchemaEdge(
                    id=uuid4(),
                    source_column_id=column_map[s_key].id,
                    target_column_id=column_map[t_key].id,
                    relationship_type=rel_type,
                    is_inferred=True,
                    description=desc
                )
                session.add(edge)
                logger.info(f"    Edge: {s_key} -> {t_key}")
            else:
                logger.warning(f"    Skipping Edge: {s_key} -> {t_key} (Column not found)")

        # 4. Create Context Rules
        for tbl, col, rule, slug in WMS_CONTEXT_RULES:
            key = f"{tbl}.{col}"
            if key in column_map:
                c_idx = column_map[key].id
                cr = ColumnContextRule(
                    id=uuid4(),
                    column_id=c_idx,
                    slug=slug,
                    rule_text=rule
                )
                session.add(cr)
                logger.info(f"    Rule: {slug} on {key}")

        # 5. Create Nominal Values
        for tbl, col, val_raw, val_lbl, slug in WMS_NOMINAL_VALUES:
            key = f"{tbl}.{col}"
            if key in column_map:
                nv = LowCardinalityValue(
                    id=uuid4(),
                    column_id=column_map[key].id,
                    value_raw=val_raw,
                    value_label=val_lbl,
                    slug=slug
                )
                session.add(nv)
                logger.info(f"    Value: {val_raw} ({val_lbl}) on {key}")

        # 6. Create Semantic Metrics
        for m_name, m_desc, m_sql, m_slug in WMS_METRICS:
            metric = SemanticMetric(
                id=uuid4(),
                datasource_id=datasource.id,
                name=m_name,
                slug=m_slug,
                description=m_desc,
                calculation_sql=m_sql
            )
            session.add(metric)
            logger.info(f"    Metric: {m_name}")

        # 7. Create Synonyms
        for term, tgt_type, tgt_name, syn_slug in WMS_SYNONYMS:
            target_id = None
            
            if tgt_type == SynonymTargetType.TABLE:
                if tgt_name in table_map:
                    target_id = table_map[tgt_name].id
            elif tgt_type == SynonymTargetType.COLUMN:
                # Handle Table.Column format for synonyms
                if "." in tgt_name and tgt_name in column_map:
                    target_id = column_map[tgt_name].id
            
            if target_id:
                syn = SemanticSynonym(
                    id=uuid4(),
                    term=term,
                    slug=syn_slug,
                    target_type=tgt_type,
                    target_id=target_id
                )
                session.add(syn)
                logger.info(f"    Synonym: {term} -> {tgt_name}")
            else:
                logger.warning(f"    Skipping Synonym: {term} (Target {tgt_name} not found)")

        session.commit()
        logger.info("WMS Full Metadata Seeding Completed Successfully.")

        session.commit()
        session.commit()
        logger.info("WMS Full Metadata Seeding Completed Successfully.")

        # 8. Refresh Table Embeddings to include Synonyms via RRF/Search Content
        # Since tables were created before synonyms, their embeddings didn't include them.
        # Now that synonyms exist, we force an update check.
        logger.info("Refreshing Table Embeddings to include Synonyms...")
        tables = session.query(TableNode).filter(TableNode.datasource_id == datasource.id).all()
        count_updated = 0
        for table in tables:
            # This triggers get_search_content(), which now finds the synonyms
            # The hash check in update_embedding_if_needed will see the change
            # and regenerate the embedding.
            old_hash = table.embedding_hash
            table.update_embedding_if_needed()
            if table.embedding_hash != old_hash:
                count_updated += 1
                logger.info(f"  Updated embedding for table: {table.physical_name}")
        
        if count_updated > 0:
            session.commit()
            logger.info(f"Refreshed {count_updated} table embeddings.")
        else:
            logger.info("No table embeddings needed updating (hashes matched).")

        logger.info("Refreshing Column Embeddings to include Synonyms...")
        # Join with TableNode to filter by datasource if needed, or just refresh all columns for this datasource's tables
        columns = session.query(ColumnNode).join(TableNode).filter(TableNode.datasource_id == datasource.id).all()
        count_col_updated = 0
        for column in columns:
            old_hash = column.embedding_hash
            column.update_embedding_if_needed()
            if column.embedding_hash != old_hash:
                count_col_updated += 1
                # Log only every 10th update to avoid noise, or log all if few
                if count_col_updated % 10 == 0:
                    logger.info(f"  Updated embedding for column: {column.name}")
        
        if count_col_updated > 0:
            session.commit()
            logger.info(f"Refreshed {count_col_updated} column embeddings.")
        else:
            logger.info("No column embeddings needed updating.")

        logger.info("WMS Full Metadata Seeding Completed Successfully.")
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding metadata: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed_physical_wms_data()
    seed_wms_metadata()
