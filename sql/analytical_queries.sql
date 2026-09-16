-- BOM lookup: material requirement for one finished good.
SELECT
    p.product,
    b.raw_material_id,
    b.quantity_per_case
FROM supply_chain.bom b
JOIN supply_chain.products p
    ON b.sku = p.sku
WHERE b.sku = 'BB500';

-- Query 1: Monthly sales trend.
SELECT
    DATE_TRUNC('month', sale_date) AS month,
    SUM(units_sold) AS total_units
FROM supply_chain.sales
GROUP BY 1
ORDER BY 1;

-- Query 2: SKU performance.
SELECT
    p.sku,
    p.product,
    SUM(s.units_sold) AS total_units_sold,
    AVG(s.price) AS avg_price,
    AVG(s.promotion) AS promotion_rate
FROM supply_chain.sales s
JOIN supply_chain.products p
    ON s.sku = p.sku
GROUP BY p.sku, p.product
ORDER BY total_units_sold DESC;

-- Query 3: Forecast accuracy.
SELECT
    sku,
    SUM(ABS(forecast_error)) AS absolute_error,
    SUM(ABS(forecast_error))
        / NULLIF(SUM(actual_units), 0) AS wape
FROM supply_chain.demand_forecasts
GROUP BY sku
ORDER BY wape;

-- Query 4: Forecast bias.
SELECT
    sku,
    SUM(actual_units - forecast_units) AS forecast_bias
FROM supply_chain.demand_forecasts
GROUP BY sku
ORDER BY forecast_bias DESC;

-- Inventory health.
SELECT
    sku,
    region,
    ROUND(average_daily_demand, 2) AS avg_daily_demand,
    ROUND(safety_stock, 2) AS safety_stock,
    ROUND(reorder_point, 2) AS reorder_point,
    ROUND(target_inventory, 2) AS target_inventory,
    ROUND(days_of_inventory, 2) AS days_of_inventory
FROM supply_chain.inventory_policy
ORDER BY days_of_inventory DESC;

-- Production capacity utilization.
SELECT
    pp.week_start,
    pp.plant_id,
    SUM(pp.production_cases) AS production_cases,
    p.weekly_capacity_cases,
    ROUND(
        SUM(pp.production_cases)
        / NULLIF(p.weekly_capacity_cases, 0) * 100,
        2
    ) AS capacity_utilization_pct
FROM supply_chain.production_plan pp
JOIN supply_chain.plants p
    ON pp.plant_id = p.plant_id
GROUP BY pp.week_start, pp.plant_id, p.weekly_capacity_cases
ORDER BY pp.week_start, capacity_utilization_pct DESC;

-- Procurement spend.
SELECT
    rm.raw_material_name,
    SUM(pp.planned_order_quantity) AS purchase_quantity,
    SUM(pp.purchase_cost) AS purchase_spend
FROM supply_chain.procurement_plan pp
JOIN supply_chain.raw_materials rm
    ON pp.raw_material_id = rm.raw_material_id
GROUP BY rm.raw_material_name
ORDER BY purchase_spend DESC;

-- Supplier performance.
SELECT
    s.supplier_name,
    rm.raw_material_name,
    s.unit_cost,
    s.lead_time_days,
    s.quality_rate,
    s.on_time_rate,
    s.supplier_capacity
FROM supply_chain.suppliers s
JOIN supply_chain.raw_materials rm
    ON s.raw_material_id = rm.raw_material_id
ORDER BY s.raw_material_id, s.on_time_rate DESC;

-- Distribution cost analysis.
SELECT
    week_start,
    plant_id,
    warehouse_id,
    SUM(shipment_cases) AS shipped_cases,
    SUM(distribution_cost) AS total_distribution_cost,
    SUM(distribution_cost)
        / NULLIF(SUM(shipment_cases), 0) AS cost_per_case
FROM supply_chain.distribution_plan
GROUP BY week_start, plant_id, warehouse_id
ORDER BY week_start, total_distribution_cost DESC;

-- Executive-level supply-chain KPIs.
SELECT
    (
        SELECT SUM(units_sold)
        FROM supply_chain.sales
    ) AS total_demand_units,
    (
        SELECT
            SUM(ABS(forecast_error))
            / NULLIF(SUM(actual_units), 0)
        FROM supply_chain.demand_forecasts
    ) AS overall_wape,
    (
        SELECT SUM(purchase_cost)
        FROM supply_chain.procurement_plan
    ) AS procurement_spend,
    (
        SELECT SUM(distribution_cost)
        FROM supply_chain.distribution_plan
    ) AS distribution_spend,
    (
        SELECT SUM(production_cases)
        FROM supply_chain.production_plan
    ) AS production_cases;
