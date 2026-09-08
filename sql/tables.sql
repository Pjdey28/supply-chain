SET search_path TO supply_chain;

-- =========================
-- PRODUCT MASTER
-- =========================

CREATE TABLE IF NOT EXISTS products (
    sku VARCHAR(20) PRIMARY KEY,
    product VARCHAR(100) NOT NULL,
    pack_size VARCHAR(20) NOT NULL,
    base_price NUMERIC(12,2) NOT NULL
);

-- =========================
-- REGION MASTER
-- =========================

CREATE TABLE IF NOT EXISTS regions (
    region_id SERIAL PRIMARY KEY,
    region_name VARCHAR(50) UNIQUE NOT NULL
);

-- =========================
-- PLANT MASTER
-- =========================

CREATE TABLE IF NOT EXISTS plants (
    plant_id VARCHAR(20) PRIMARY KEY,
    plant_name VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    weekly_capacity_cases NUMERIC(14,2) NOT NULL
);

-- =========================
-- WAREHOUSE MASTER
-- =========================

CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id VARCHAR(30) PRIMARY KEY,
    warehouse_name VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    capacity_cases NUMERIC(14,2) NOT NULL
);

-- =========================
-- RAW MATERIAL MASTER
-- =========================

CREATE TABLE IF NOT EXISTS raw_materials (
    raw_material_id VARCHAR(20) PRIMARY KEY,
    raw_material_name VARCHAR(100) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    unit_cost NUMERIC(12,4) NOT NULL,
    lead_time_days INTEGER NOT NULL,
    safety_stock_days INTEGER NOT NULL,
    moq NUMERIC(14,2) NOT NULL
);

-- =========================
-- SUPPLIER MASTER
-- =========================

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id VARCHAR(20) PRIMARY KEY,
    supplier_name VARCHAR(100) NOT NULL,
    raw_material_id VARCHAR(20)
        REFERENCES raw_materials(raw_material_id),

    unit_cost NUMERIC(12,4) NOT NULL,
    lead_time_days INTEGER NOT NULL,
    moq NUMERIC(14,2) NOT NULL,
    supplier_capacity NUMERIC(14,2) NOT NULL,
    quality_rate NUMERIC(8,5) NOT NULL,
    on_time_rate NUMERIC(8,5) NOT NULL
);

-- =========================
-- BILL OF MATERIALS
-- =========================

CREATE TABLE IF NOT EXISTS bom (
    sku VARCHAR(20)
        REFERENCES products(sku),

    raw_material_id VARCHAR(20)
        REFERENCES raw_materials(raw_material_id),

    quantity_per_case NUMERIC(14,6) NOT NULL,

    PRIMARY KEY (
        sku,
        raw_material_id
    )
);

-- =========================
-- SALES FACT
-- =========================

CREATE TABLE IF NOT EXISTS sales (
    sale_date DATE NOT NULL,
    sku VARCHAR(20)
        REFERENCES products(sku),

    region VARCHAR(50) NOT NULL,

    units_sold NUMERIC(14,2) NOT NULL,
    price NUMERIC(12,2),
    promotion INTEGER,
    holiday INTEGER,

    PRIMARY KEY (
        sale_date,
        sku,
        region
    )
);

-- =========================
-- DEMAND FORECAST FACT
-- =========================

CREATE TABLE IF NOT EXISTS demand_forecasts (
    forecast_date DATE NOT NULL,

    sku VARCHAR(20)
        REFERENCES products(sku),

    region VARCHAR(50) NOT NULL,

    actual_units NUMERIC(14,2),
    forecast_units NUMERIC(14,2),
    forecast_error NUMERIC(14,2),

    promotion INTEGER,
    holiday INTEGER,

    PRIMARY KEY (
        forecast_date,
        sku,
        region
    )
);

-- =========================
-- INVENTORY POLICY
-- =========================

CREATE TABLE IF NOT EXISTS inventory_policy (
    sku VARCHAR(20)
        REFERENCES products(sku),

    region VARCHAR(50),

    average_daily_demand NUMERIC(14,2),
    demand_std NUMERIC(14,2),

    lead_time_days INTEGER,

    safety_stock NUMERIC(14,2),
    reorder_point NUMERIC(14,2),
    target_inventory NUMERIC(14,2),

    days_of_inventory NUMERIC(14,2),

    PRIMARY KEY (
        sku,
        region
    )
);

-- =========================
-- PRODUCTION PLAN
-- =========================

CREATE TABLE IF NOT EXISTS production_plan (
    week_start DATE NOT NULL,

    plant_id VARCHAR(20)
        REFERENCES plants(plant_id),

    sku VARCHAR(20)
        REFERENCES products(sku),

    region VARCHAR(50),

    production_cases NUMERIC(14,2) NOT NULL
);

-- =========================
-- RAW MATERIAL REQUIREMENTS
-- =========================

CREATE TABLE IF NOT EXISTS raw_material_requirements (
    week_start DATE NOT NULL,

    plant_id VARCHAR(20)
        REFERENCES plants(plant_id),

    raw_material_id VARCHAR(20)
        REFERENCES raw_materials(raw_material_id),

    raw_material_requirement NUMERIC(14,2)
        NOT NULL
);

-- =========================
-- PROCUREMENT PLAN
-- =========================

CREATE TABLE IF NOT EXISTS procurement_plan (
    week_start DATE NOT NULL,

    plant_id VARCHAR(20)
        REFERENCES plants(plant_id),

    raw_material_id VARCHAR(20)
        REFERENCES raw_materials(raw_material_id),

    raw_material_requirement NUMERIC(14,2),

    opening_inventory NUMERIC(14,2),

    safety_stock NUMERIC(14,2),

    planned_order_quantity NUMERIC(14,2),

    ending_inventory NUMERIC(14,2),

    unit_cost NUMERIC(14,4),

    purchase_cost NUMERIC(16,2)
);

-- =========================
-- DISTRIBUTION PLAN
-- =========================

CREATE TABLE IF NOT EXISTS distribution_plan (
    week_start DATE NOT NULL,

    plant_id VARCHAR(20)
        REFERENCES plants(plant_id),

    warehouse_id VARCHAR(30)
        REFERENCES warehouses(warehouse_id),

    sku VARCHAR(20)
        REFERENCES products(sku),

    shipment_cases NUMERIC(14,2),

    transport_cost_per_case NUMERIC(12,4),

    handling_cost_per_case NUMERIC(12,4),

    distribution_cost NUMERIC(16,2)
);

-- =========================
-- SUPPLIER PURCHASE PLAN
-- =========================

CREATE TABLE IF NOT EXISTS supplier_purchase_plan (
    week_start DATE NOT NULL,

    plant_id VARCHAR(20),

    raw_material_id VARCHAR(20),

    supplier_id VARCHAR(20)
        REFERENCES suppliers(supplier_id),

    required_quantity NUMERIC(14,2),

    purchase_quantity NUMERIC(14,2),

    unit_cost NUMERIC(14,4),

    lead_time_days INTEGER,

    supplier_score NUMERIC(10,6),

    purchase_cost NUMERIC(16,2)
);

-- =========================
-- INDEXES
-- =========================

CREATE INDEX IF NOT EXISTS idx_sales_sku_date
ON sales(sku, sale_date);

CREATE INDEX IF NOT EXISTS idx_sales_region_date
ON sales(region, sale_date);

CREATE INDEX IF NOT EXISTS idx_forecast_sku_date
ON demand_forecasts(sku, forecast_date);

CREATE INDEX IF NOT EXISTS idx_production_week
ON production_plan(week_start);

CREATE INDEX IF NOT EXISTS idx_procurement_week
ON procurement_plan(week_start);

CREATE INDEX IF NOT EXISTS idx_distribution_week
ON distribution_plan(week_start);
