import os
import math
import pandas as pd


PRODUCTION_PLAN_PATH = "data/processed/production_plan.csv"
BOM_PATH = "data/raw/bom.csv"
RAW_MATERIAL_PATH = "data/raw/raw_materials.csv"
RM_INVENTORY_PATH = "data/raw/raw_material_inventory.csv"

OUTPUT_REQUIREMENTS = "data/processed/raw_material_requirements.csv"
OUTPUT_PLAN = "data/processed/procurement_plan.csv"


def load_data():
    production = pd.read_csv(PRODUCTION_PLAN_PATH)
    bom = pd.read_csv(BOM_PATH)
    raw_materials = pd.read_csv(RAW_MATERIAL_PATH)
    inventory = pd.read_csv(RM_INVENTORY_PATH)

    production["week_start"] = pd.to_datetime(
        production["week_start"]
    )

    return production, bom, raw_materials, inventory


def calculate_raw_material_requirements(
    production,
    bom
):
    """
    Explode finished-goods production
    into raw-material requirements.
    """

    exploded = production.merge(
        bom,
        on="sku",
        how="left"
    )

    exploded["raw_material_requirement"] = (
        exploded["production_cases"]
        * exploded["quantity_per_case"]
    )

    requirements = (
        exploded
        .groupby(
            [
                "week_start",
                "plant_id",
                "raw_material_id"
            ],
            as_index=False
        )["raw_material_requirement"]
        .sum()
    )

    return requirements


def calculate_safety_stock(
    requirements,
    raw_materials
):
    """
    Safety stock based on average weekly
    requirement and safety-stock days.
    """

    weekly_avg = (
        requirements
        .groupby(
            ["plant_id", "raw_material_id"],
            as_index=False
        )["raw_material_requirement"]
        .mean()
        .rename(
            columns={
                "raw_material_requirement":
                "average_weekly_requirement"
            }
        )
    )

    result = weekly_avg.merge(
        raw_materials[
            [
                "raw_material_id",
                "safety_stock_days"
            ]
        ],
        on="raw_material_id",
        how="left"
    )

    result["average_daily_requirement"] = (
        result["average_weekly_requirement"] / 7
    )

    result["safety_stock"] = (
        result["average_daily_requirement"]
        * result["safety_stock_days"]
    )

    return result[
        [
            "plant_id",
            "raw_material_id",
            "safety_stock"
        ]
    ]


def create_procurement_plan(
    requirements,
    raw_materials,
    inventory,
    safety_stock
):
    """
    Convert gross requirements into
    planned purchase orders.
    """

    plan = requirements.merge(
        raw_materials,
        on="raw_material_id",
        how="left"
    )

    plan = plan.merge(
        inventory,
        on=["plant_id", "raw_material_id"],
        how="left"
    )

    plan = plan.merge(
        safety_stock,
        on=["plant_id", "raw_material_id"],
        how="left"
    )

    plan["opening_inventory"] = (
        plan["opening_inventory"].fillna(0)
    )

    plan["safety_stock"] = (
        plan["safety_stock"].fillna(0)
    )

    plan = plan.sort_values(
        [
            "plant_id",
            "raw_material_id",
            "week_start"
        ]
    )

    plan["projected_inventory_before_receipt"] = 0.0
    plan["planned_order_quantity"] = 0.0
    plan["ending_inventory"] = 0.0

    for (
        plant,
        raw_material
    ), group in plan.groupby(
        ["plant_id", "raw_material_id"]
    ):

        current_inventory = (
            group.iloc[0]["opening_inventory"]
        )

        for idx in group.index:

            requirement = (
                plan.loc[
                    idx,
                    "raw_material_requirement"
                ]
            )

            safety = (
                plan.loc[
                    idx,
                    "safety_stock"
                ]
            )

            projected_before = (
                current_inventory - requirement
            )

            if projected_before < safety:

                required_order = (
                    safety - projected_before
                )

                moq = plan.loc[idx, "moq"]

                planned_order = (
                    math.ceil(
                        required_order / moq
                    ) * moq
                )

            else:
                planned_order = 0

            ending_inventory = (
                projected_before
                + planned_order
            )

            plan.loc[
                idx,
                "projected_inventory_before_receipt"
            ] = projected_before

            plan.loc[
                idx,
                "planned_order_quantity"
            ] = planned_order

            plan.loc[
                idx,
                "ending_inventory"
            ] = ending_inventory

            current_inventory = ending_inventory

    plan["purchase_cost"] = (
        plan["planned_order_quantity"]
        * plan["unit_cost"]
    )

    return plan


def main():

    os.makedirs(
        "data/processed",
        exist_ok=True
    )

    (
        production,
        bom,
        raw_materials,
        inventory
    ) = load_data()

    requirements = (
        calculate_raw_material_requirements(
            production,
            bom
        )
    )

    safety_stock = calculate_safety_stock(
        requirements,
        raw_materials
    )

    procurement_plan = create_procurement_plan(
        requirements,
        raw_materials,
        inventory,
        safety_stock
    )

    requirements.to_csv(
        OUTPUT_REQUIREMENTS,
        index=False
    )

    procurement_plan.to_csv(
        OUTPUT_PLAN,
        index=False
    )

    print(
        "Raw-material requirements saved to:",
        OUTPUT_REQUIREMENTS
    )

    print(
        "Procurement plan saved to:",
        OUTPUT_PLAN
    )

    print("\nProcurement Summary:")

    summary = (
        procurement_plan
        .groupby("raw_material_id")
        .agg(
            total_requirement=(
                "raw_material_requirement",
                "sum"
            ),
            total_purchase_quantity=(
                "planned_order_quantity",
                "sum"
            ),
            total_purchase_cost=(
                "purchase_cost",
                "sum"
            )
        )
        .reset_index()
    )

    print(summary)


if __name__ == "__main__":
    main()