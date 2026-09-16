# End-to-End Supply Chain Optimization & Demand Forecasting Platform

## Optimizing the Supply Chain of an FMCG Beverage Company

An end-to-end supply chain analytics and optimization platform developed for a simulated FMCG beverage company.

The project integrates demand forecasting, inventory optimization, production planning, procurement planning, supplier analysis, distribution optimization, PostgreSQL analytics, Power BI business intelligence, and scenario analysis into a unified supply-chain decision-support system.

The objective is to demonstrate how data-driven methods can be used to improve demand visibility, inventory planning, manufacturing utilization, procurement decisions, supplier evaluation, and distribution efficiency.

---

## 1. Business Problem

FMCG beverage supply chains operate in a high-volume, time-sensitive environment where demand varies by:

* Product
* Pack size
* Region
* Season
* Promotion
* Weekday/weekend effects
* Holidays

At the same time, the supply chain must coordinate:

* Multiple manufacturing plants
* Limited production capacity
* Raw-material requirements
* Supplier lead times
* Minimum order quantities
* Supplier reliability
* Warehouse capacity
* Distribution costs
* Customer service levels

A decision made in one part of the supply chain can affect the rest of the network.

For example:

An increase in demand can create additional production requirements, increase raw-material consumption, increase procurement requirements, put pressure on plant capacity, and eventually affect distribution requirements.

Therefore, the project treats the supply chain as an interconnected system rather than analyzing each function independently.

---

## 2. Project Objective

The platform is designed to answer questions such as:

* How much demand should the business expect?
* Which SKUs and regions have the highest demand?
* How accurate are the forecasts?
* How much safety stock should be maintained?
* When should inventory be replenished?
* How should production be allocated across plants?
* Which raw materials need to be procured?
* Which suppliers provide the best balance of cost and reliability?
* How should products be distributed from plants to warehouses?
* Which plants are approaching capacity constraints?
* What happens if demand suddenly increases?
* What happens if a plant loses capacity?
* What happens if raw-material costs increase?
* What happens if supplier lead times increase?
* What is the trade-off between service level and inventory?

---

# 3. Supply Chain Scope

The simulated company manufactures and distributes 10 beverage SKUs across 5 regions.

### Products

| SKU    | Product      | Pack Size |
| ------ | ------------ | --------: |
| BB250  | Bharat Cola  |     250ml |
| BB500  | Bharat Cola  |     500ml |
| BB1000 | Bharat Cola  |        1L |
| LM250  | Lemon Blast  |     250ml |
| LM500  | Lemon Blast  |     500ml |
| OR500  | Orange Rush  |     500ml |
| OR1000 | Orange Rush  |        1L |
| EN250  | Energy Max   |     250ml |
| EN500  | Energy Max   |     500ml |
| WT1000 | Bharat Water |        1L |

### Regions

* North
* South
* East
* West
* Central

### Manufacturing Plants

| Plant | Region | Weekly Capacity |
| ----- | ------ | --------------: |
| P01   | North  |   180,000 cases |
| P02   | South  |   220,000 cases |
| P03   | East   |   160,000 cases |

### Distribution Warehouses

* Delhi
* Mumbai
* Kolkata
* Bangalore
* Hyderabad

---

# 4. End-to-End Architecture

```text
                    Historical Sales
                           |
                           v
                  Data Generation
                           |
                           v
                    EDA & Analysis
                           |
                           v
                 Demand Forecasting
                  XGBoost + Baseline
                           |
                           v
                Inventory Optimization
             Safety Stock / ROP / Simulation
                           |
                           v
                  Production Planning
                     PuLP Optimization
                           |
                           v
                  Procurement Planning
                       BOM Explosion
                           |
                           v
                   Supplier Analysis
                 Cost + Quality + OTD
                           |
                           v
                 Supplier Allocation
                           |
                           v
                 Distribution Planning
                     PuLP Optimization
                           |
                           v
                 PostgreSQL Data Layer
                           |
                           v
                 Power BI 
                           |
                           v
                  Scenario Analysis
                           |
                           v
                  Decision Support
```

---

# 5. Repository Structure

```text
beverage-supply-chain/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
│
├── notebooks/
│   ├── 01_data_generation.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_demand_forecasting.ipynb
│   ├── 04_inventory_optimization.ipynb
│   ├── 05_production_planning.ipynb
│   ├── 06_procurement_planning.ipynb
│   ├── 07_supplier_analysis.ipynb
│   ├── 08_distribution_optimization.ipynb
│   └── 09_scenario_analysis.ipynb
│
├── src/
│   ├── data/
│   ├── forecasting/
│   ├── inventory/
│   ├── production/
│   ├── procurement/
│   ├── suppliers/
│   ├── distribution/
│   └── utils/
│
├── sql/
│   ├── schema.sql
│   ├── tables.sql
│   └── analytical_queries.sql
│
├── powerbi/
│   └── README.md
│
├── config/
│   └── parameters.yaml
│
├── requirements.txt
└── README.md
```

---

# 6. Data Generation

The project uses a realistic synthetic dataset representing approximately three years of daily FMCG beverage demand.

The generated sales dataset covers:

* 2023–2025
* 10 SKUs
* 5 regions
* Daily observations
* Approximately 548,000 SKU-region-day records

The dataset contains:

* Date
* SKU
* Product
* Pack size
* Region
* Units sold
* Price
* Promotion
* Holiday

Demand generation incorporates:

* Weekly seasonality
* Weekend effects
* Summer seasonality
* Holiday effects
* Promotional demand uplift
* Promotional price discounts
* Long-term demand growth
* Regional demand differences
* Random demand variation

This provides a realistic foundation for downstream forecasting and optimization.

---

# 7. Exploratory Data Analysis

The EDA stage evaluates demand patterns before building predictive models.

Analysis includes:

* Daily demand trends
* Monthly demand trends
* SKU-level demand
* Regional demand
* Promotion impact
* Weekend impact
* Holiday impact
* Monthly seasonality
* SKU-region demand matrix
* Demand volatility
* Coefficient of variation

The analysis is used to identify patterns that can influence forecasting and supply-chain planning.

---

# 8. Demand Forecasting

The forecasting problem is modeled at the:

```text
SKU × Region × Day
```

level.

### Features

The forecasting dataset contains:

* Month
* Week
* Day of week
* Day of year
* Weekend indicator
* Price
* Promotion
* Holiday
* Lag 1
* Lag 7
* Lag 14
* Lag 28
* Rolling mean 7
* Rolling mean 14
* Rolling mean 28
* Rolling standard deviation 28
* SKU
* Region

Rolling features are calculated using historical observations only to prevent data leakage.

### Models

#### Baseline

Seasonal naïve forecasting using the previous week's demand:

```text
Forecast(t) = Demand(t - 7)
```

#### Machine Learning Model

XGBoost regression is used to model nonlinear relationships between demand and its historical, calendar, promotional and regional drivers.

### Evaluation

The dataset is split chronologically:

```text
Training:   Before 2025-01-01
Validation: 2025-01-01 to 2025-06-30
Test:       2025-07-01 onward
```

No random train-test split is used because this is a time-series forecasting problem.

Metrics include:

* MAE
* RMSE
* WAPE
* Forecast Bias

Forecast performance is also analyzed by SKU.

---

# 9. Inventory Optimization

The inventory module converts demand uncertainty into inventory policies.

For each SKU-region combination, the model calculates:

* Average daily demand
* Demand standard deviation
* Lead-time demand
* Safety stock
* Reorder point
* Target inventory
* Days of inventory

### Safety Stock

The safety-stock calculation follows:

```text
Safety Stock =
Z × Demand Standard Deviation × √Lead Time
```

For the default 95% service level:

```text
Z ≈ 1.645
```

### Reorder Point

```text
ROP =
Average Daily Demand × Lead Time
+ Safety Stock
```

### Target Inventory

```text
Target Inventory =
Average Daily Demand × (Lead Time + Review Period)
+ Safety Stock
```

### Inventory Simulation

A daily inventory simulation tracks:

* Beginning inventory
* Actual demand
* Received orders
* Fulfilled demand
* Lost sales
* Ending inventory
* Inventory position
* Replenishment orders
* Lead-time arrivals

The simulation is used to evaluate service level and stockout behavior.

---

# 10. Production Planning

The production planning module converts forecast and inventory requirements into weekly manufacturing requirements.

Forecast demand is converted from units into cases using SKU-specific pack configurations.

Production requirements are calculated using:

```text
Production Requirement =
Forecast Demand
+ Target Inventory
- Opening Inventory
```

Negative requirements are clipped to zero.

### Optimization Model

PuLP is used to formulate a linear optimization model.

Decision variable:

```text
Production[Plant, SKU, Region]
```

Objective:

```text
Minimize

Production Cost
+
Transportation Cost
```

Subject to:

* Regional demand requirements
* Plant weekly capacity
* Plant-SKU production capability

The optimization is performed separately for each week so that plant capacity resets every planning period.

---

# 11. Procurement Planning

The procurement module translates production requirements into raw-material requirements.

### Raw Materials

The model includes:

* Sugar
* Beverage concentrate
* CO2
* PET bottles
* Caps
* Labels
* Cartons
* Shrink film

### BOM Explosion

For each SKU:

```text
Production Cases
×
Raw Material Quantity per Case
=
Gross Raw Material Requirement
```

The system then considers:

* Opening inventory
* Safety stock
* Lead time
* MOQ
* Unit cost

The resulting procurement plan identifies when additional material should be ordered.

---

# 12. Supplier Analysis

Supplier performance is evaluated using multiple dimensions instead of purchase price alone.

Metrics include:

* Unit cost
* Lead time
* Quality rate
* On-time delivery rate
* Supplier capacity
* MOQ

A composite supplier score is calculated using:

```text
Cost             35%
Lead Time        20%
Quality          20%
On-Time Delivery 25%
```

Cost and lead time are normalized inversely, while quality and on-time delivery are normalized positively.

The supplier allocation module then assigns procurement quantities while considering:

* Supplier rank
* Supplier capacity
* MOQ

This demonstrates that procurement decisions should consider both economics and supply reliability.

---

# 13. Distribution Optimization

The distribution model determines how finished goods move from manufacturing plants to warehouses.

The network contains:

```text
Plants
   ↓
Warehouses
   ↓
Regional Demand
```

The model considers:

* Plant production availability
* Warehouse demand
* Warehouse capacity
* Plant-to-warehouse transportation cost
* Warehouse handling cost

Decision variable:

```text
Shipment[Plant, Warehouse, SKU]
```

Objective:

```text
Minimize

Transportation Cost
+
Warehouse Handling Cost
```

The model is optimized independently for each week.

---

# 14. PostgreSQL Data Layer

PostgreSQL is used as the centralized analytical database.

Database:

```text
supply_chain
```

Schema:

```text
supply_chain
```

Major tables include:

* products
* regions
* plants
* warehouses
* raw_materials
* suppliers
* bom
* sales
* demand_forecasts
* inventory_policy
* production_plan
* raw_material_requirements
* procurement_plan
* distribution_plan
* supplier_purchase_plan

SQL analytics are used to generate:

* Monthly sales trends
* SKU performance
* Forecast accuracy
* Forecast bias
* Inventory health
* Production utilization
* Procurement spend
* Supplier performance
* Distribution cost
* Executive supply-chain KPIs

---

# 15. Power BI 

The Power BI dashboard provides a management-level view of the supply chain.

## Page 1 — Executive Overview

KPIs:

* Total Sales Value
* Forecast WAPE
* Service Level
* Days of Inventory
* Capacity Utilization
* Procurement Spend

Visuals include:

* Demand trends
* Forecast performance
* Regional demand
* Plant utilization
* Inventory health
* Supply-chain cost

## Page 2 — Demand & Forecasting

Tracks:

* Actual vs forecast demand
* WAPE by SKU
* Forecast bias
* Regional demand
* Promotional effects

## Page 3 — Inventory Health

Tracks:

* Service level
* Lost sales
* Stockout days
* Average inventory
* Safety stock
* Reorder points
* Days of inventory

## Page 4 — Production & Capacity

Tracks:

* Production volume
* Plant utilization
* Production cost
* SKU production
* Weekly capacity utilization

## Page 5 — Procurement & Suppliers

Tracks:

* Procurement spend
* Raw-material requirements
* Supplier cost
* Lead time
* Quality
* On-time delivery
* Supplier score

## Page 6 — Distribution Network

Tracks:

* Distribution volume
* Distribution cost
* Plant-to-warehouse shipments
* Warehouse utilization
* Average distribution cost per case

---

# 16. Scenario / What-If Analysis

The scenario engine evaluates how supply-chain KPIs respond to operational shocks.

Supported scenarios include:

### Demand Shock

Example:

```text
Demand +15%
```

Evaluates the resulting increase in production requirements and capacity utilization.

### Plant Capacity Shock

Example:

```text
P01 Capacity -20%
```

Evaluates the effect of manufacturing capacity loss.

### Raw-Material Cost Shock

Example:

```text
PET Bottle Cost +10%
```

Evaluates the potential effect on procurement cost.

### Supplier Lead-Time Shock

Example:

```text
PET Bottle Lead Time +7 days
```

Evaluates the effect of longer replenishment times.

### Service-Level Scenario

Example:

```text
Service Level:
95% → 98%
```

Demonstrates the relationship between service requirements and safety stock.

### Scenario Comparison

The engine compares:

* Production quantity
* Procurement quantity
* Procurement spend
* Distribution cost
* Maximum plant utilization
* Inventory policy

The objective is to provide a structured way to evaluate supply-chain risks and trade-offs.

---

# 17. Key Supply Chain KPIs

The platform measures KPIs across the entire supply chain.

### Demand

* Total demand
* Forecast WAPE
* Forecast bias
* SKU-level forecast accuracy
* Regional demand

### Inventory

* Service level
* Lost sales
* Stockout days
* Average inventory
* Safety stock
* Reorder point
* Days of inventory

### Production

* Production cases
* Capacity utilization
* Plant-level utilization
* Production cost
* Bottleneck identification

### Procurement

* Procurement quantity
* Procurement spend
* Raw-material requirements
* Supplier spend

### Suppliers

* Supplier score
* Unit cost
* Lead time
* Quality rate
* On-time delivery

### Distribution

* Shipment volume
* Distribution cost
* Cost per case
* Warehouse utilization

---

# 18. Technology Stack

### Programming

* Python
* Pandas
* NumPy
* SciPy

### Machine Learning

* Scikit-learn
* XGBoost
* Statsmodels

### Optimization

* PuLP

### Database

* PostgreSQL
* SQL
* SQLAlchemy
* Psycopg2

### Analytics & Visualization

* Matplotlib
* Seaborn
* Power BI

### Data & Configuration

* CSV
* Excel
* YAML

### Development

* Jupyter Notebook
* VS Code
* Git/GitHub

---

# 19. Project Outputs

The project generates processed datasets including:

```text
data/processed/
│
├── forecast_dataset.csv
├── demand_forecasts.csv
├── forecast_performance_by_sku.csv
├── inventory_policy.csv
├── inventory_simulation.csv
├── inventory_kpis.csv
├── production_requirements.csv
├── production_plan.csv
├── raw_material_requirements.csv
├── procurement_plan.csv
├── supplier_scores.csv
├── supplier_purchase_plan.csv
├── distribution_plan.csv
└── scenario_comparison.csv
```

These outputs form the data pipeline consumed by SQL analytics and Power BI.

---

# 20. Business Value

The project demonstrates an integrated approach to supply-chain decision making.

Instead of treating forecasting, inventory, manufacturing, procurement and distribution as independent analytical tasks, the platform connects them sequentially.

The key business relationships are:

```text
Demand Forecast
      ↓
Inventory Requirement
      ↓
Production Requirement
      ↓
Raw Material Requirement
      ↓
Supplier Procurement
      ↓
Manufacturing Supply
      ↓
Distribution
      ↓
Customer Service
```

This creates a closed analytical loop from demand signals to supply decisions.

---

# 21. Important Modeling Assumptions

This is a simulated FMCG supply-chain environment.

Therefore, assumptions include:

* Synthetic historical demand
* Fixed plant capacities
* Predefined plant-SKU capabilities
* Fixed transportation costs
* Simplified warehouse structure
* Simplified supplier allocation
* Deterministic production costs
* Simplified inventory assumptions

These assumptions are intended to create a realistic analytical environment while keeping the project reproducible.

---

# 22. Limitations

The current model does not fully incorporate:

* Real company ERP data
* Real-time demand signals
* Detailed production changeover constraints
* Sequence-dependent setup costs
* Overtime production
* Detailed vehicle-routing optimization
* Actual supplier contracts
* Supplier disruption probabilities
* Multi-echelon inventory optimization
* Shelf-life constraints
* Product expiry
* Real-time warehouse stock
* Dynamic transportation rates

These are potential extensions for a production-grade implementation.

---

# 23. Future Enhancements

Potential future improvements include:

1. Multi-echelon inventory optimization
2. Stochastic production planning
3. Supplier risk simulation
4. Vehicle-routing optimization
5. Production changeover optimization
6. Dynamic pricing and promotion forecasting
7. Probabilistic demand forecasting
8. Real-time ERP integration
9. Automated Power BI refresh
10. Cloud deployment
11. Optimization under multiple disruption scenarios
12. Cost-to-serve modeling
13. Carbon/emissions optimization
14. Digital twin simulation of the supply chain

---

# 24. How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the dataset:

```bash
python src/data/generate_data.py
```

Run the analytical modules in sequence:

```text
01 Data Generation
02 EDA
03 Demand Forecasting
04 Inventory Optimization
05 Production Planning
06 Procurement Planning
07 Supplier Analysis
08 Distribution Optimization
09 Scenario Analysis
```

Load the generated datasets into PostgreSQL using:

```bash
python src/data/load_postgres.py
```

Then connect Power BI to:

```text
Database:
supply_chain

Schema:
supply_chain
```

---

# 25. Conclusion

The Supply Chain Optimization Platform demonstrates an end-to-end analytical approach to FMCG supply-chain management.

The project combines:

```text
Machine Learning
+
Statistical Analysis
+
Inventory Science
+
Operations Research
+
Procurement Analytics
+
Supplier Analytics
+
Distribution Optimization
+
SQL
+
Business Intelligence
+
Scenario Analysis
```

The result is a unified decision-support platform capable of connecting demand signals with downstream supply-chain decisions and evaluating the impact of operational changes through what-if analysis.
