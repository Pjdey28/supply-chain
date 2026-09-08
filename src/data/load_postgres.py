import os

import pandas as pd
from sqlalchemy import create_engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/supply_chain",
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def get_engine():
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )


def load_csv(
    engine,
    file_path,
    table_name,
    schema="supply_chain",
):
    df = pd.read_csv(file_path)

    df.to_sql(
        table_name,
        engine,
        schema=schema,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000,
    )

    print(
        f"Loaded {len(df):,} rows into "
        f"{schema}.{table_name}"
    )


def main():
    engine = get_engine()

    files = {
        "products": "data/raw/products.csv",
        "sales": "data/raw/sales_history.csv",
        "plants": "data/raw/plants.csv",
        "warehouses": "data/raw/warehouses.csv",
        "raw_materials": "data/raw/raw_materials.csv",
        "bom": "data/raw/bom.csv",
        "suppliers": "data/raw/suppliers.csv",
        "demand_forecasts": "data/processed/demand_forecasts.csv",
        "inventory_policy": "data/processed/inventory_policy.csv",
        "production_plan": "data/processed/production_plan.csv",
        "raw_material_requirements": "data/processed/raw_material_requirements.csv",
        "procurement_plan": "data/processed/procurement_plan.csv",
        "distribution_plan": "data/processed/distribution_plan.csv",
        "supplier_purchase_plan": "data/processed/supplier_purchase_plan.csv",
    }

    for table_name, relative_path in files.items():
        file_path = os.path.join(PROJECT_ROOT, relative_path)

        if not os.path.exists(file_path):
            print(f"Skipping missing file: {relative_path}")
            continue

        load_csv(
            engine,
            file_path,
            table_name,
        )


if __name__ == "__main__":
    main()
