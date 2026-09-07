import os
import numpy as np
import pandas as pd


RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)


DATA_DIR = "data/raw"
os.makedirs(DATA_DIR, exist_ok=True)


products = pd.DataFrame([
    ["BB250", "Bharat Cola", "250ml", 24],
    ["BB500", "Bharat Cola", "500ml", 35],
    ["BB1000", "Bharat Cola", "1L", 55],
    ["LM250", "Lemon Blast", "250ml", 22],
    ["LM500", "Lemon Blast", "500ml", 32],
    ["OR500", "Orange Rush", "500ml", 34],
    ["OR1000", "Orange Rush", "1L", 52],
    ["EN250", "Energy Max", "250ml", 48],
    ["EN500", "Energy Max", "500ml", 72],
    ["WT1000", "Bharat Water", "1L", 20],
], columns=[
    "sku",
    "product",
    "pack_size",
    "base_price"
])


regions = {
    "North": 1.00,
    "South": 1.10,
    "East": 0.95,
    "West": 1.15,
    "Central": 0.90
}


dates = pd.date_range(
    start="2023-01-01",
    end="2025-12-31",
    freq="D"
)

holiday_dates = set(pd.to_datetime([
    "2023-01-26",
    "2023-08-15",
    "2023-10-24",
    "2023-11-12",
    "2023-12-25",

    "2024-01-26",
    "2024-08-15",
    "2024-10-12",
    "2024-11-01",
    "2024-12-25",

    "2025-01-26",
    "2025-08-15",
    "2025-10-02",
    "2025-10-20",
    "2025-12-25",
]))



sku_demand = {
    "BB250": 450,
    "BB500": 650,
    "BB1000": 400,
    "LM250": 350,
    "LM500": 500,
    "OR500": 420,
    "OR1000": 300,
    "EN250": 280,
    "EN500": 200,
    "WT1000": 700,
}


records = []


for date in dates:

    day_of_week = date.dayofweek
    month = date.month

    # Weekend effect
    weekend_factor = 1.15 if day_of_week >= 5 else 1.0

    # Summer effect
    summer_factor = 1.0

    if month in [4, 5, 6]:
        summer_factor = 1.30
    elif month in [3, 7]:
        summer_factor = 1.15

    # Festival / holiday effect
    holiday_factor = 1.20 if date in holiday_dates else 1.0

    for _, product in products.iterrows():

        sku = product["sku"]

        for region, region_factor in regions.items():

            base = sku_demand[sku]

            # Long-term growth
            days_from_start = (date - dates[0]).days
            growth_factor = 1 + 0.0003 * days_from_start

            # Promotion probability
            promotion = 1 if rng.random() < 0.08 else 0

            promotion_factor = 1.25 if promotion else 1.0

            # Random demand variation
            noise = rng.normal(1.0, 0.10)

            demand = (
                base
                * region_factor
                * weekend_factor
                * summer_factor
                * holiday_factor
                * promotion_factor
                * growth_factor
                * noise
            )

            demand = max(0, int(round(demand)))

            price = product["base_price"]

            # Promotional discount
            if promotion:
                price *= 0.90

            records.append([
                date,
                sku,
                product["product"],
                product["pack_size"],
                region,
                demand,
                round(price, 2),
                promotion,
                int(date in holiday_dates),
            ])


sales = pd.DataFrame(records, columns=[
    "date",
    "sku",
    "product",
    "pack_size",
    "region",
    "units_sold",
    "price",
    "promotion",
    "is_holiday",
])


sales.to_csv(
    f"{DATA_DIR}/sales_history.csv",
    index=False
)

products.to_csv(
    f"{DATA_DIR}/products.csv",
    index=False
)


print("Dataset generation complete.")
print(f"Rows generated: {len(sales):,}")
print(f"Date range: {sales['date'].min()} → {sales['date'].max()}")
print(f"SKUs: {sales['sku'].nunique()}")
print(f"Regions: {sales['region'].nunique()}")