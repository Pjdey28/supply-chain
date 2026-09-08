"""Optimize weekly beverage production across eligible plants."""

from pathlib import Path

import numpy as np
import pandas as pd
from pulp import LpMinimize, LpProblem, LpStatus, LpVariable, lpSum, value


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FORECAST_PATH = PROCESSED_DIR / "demand_forecasts.csv"
POLICY_PATH = PROCESSED_DIR / "inventory_policy.csv"
PACK_UNITS = {"250ml": 24, "500ml": 24, "1L": 12}


def load_inputs() -> tuple[pd.DataFrame, ...]:
    forecasts = pd.read_csv(FORECAST_PATH, parse_dates=["date"])
    products = pd.read_csv(RAW_DIR / "products.csv")
    plants = pd.read_csv(RAW_DIR / "plants.csv")
    capability = pd.read_csv(RAW_DIR / "plant_sku_capability.csv")
    costs = pd.read_csv(RAW_DIR / "production_costs.csv")
    transport = pd.read_csv(RAW_DIR / "transport_costs.csv")
    policy = pd.read_csv(POLICY_PATH)

    products["units_per_case"] = products["pack_size"].map(PACK_UNITS)
    if products["units_per_case"].isna().any():
        raise ValueError("Every product must have a supported pack size")

    required_forecast = {"date", "sku", "region", "ml_prediction"}
    missing = sorted(required_forecast.difference(forecasts.columns))
    if missing:
        raise ValueError(f"Forecast data is missing columns: {missing}")
    return forecasts, products, plants, capability, costs, transport, policy


def build_production_requirements(
    forecasts: pd.DataFrame,
    products: pd.DataFrame,
    policy: pd.DataFrame,
) -> pd.DataFrame:
    forecasts = forecasts.merge(
        products[["sku", "units_per_case"]],
        on="sku",
        how="left",
        validate="many_to_one",
    )
    forecasts["forecast_cases"] = (
        forecasts["ml_prediction"] / forecasts["units_per_case"]
    )
    forecasts["week_start"] = forecasts["date"] - pd.to_timedelta(
        forecasts["date"].dt.dayofweek, unit="D"
    )
    weekly_demand = (
        forecasts.groupby(["week_start", "sku", "region"], as_index=False)
        .agg(forecast_cases=("forecast_cases", "sum"))
    )

    policy = policy.merge(
        products[["sku", "units_per_case"]],
        on="sku",
        how="left",
        validate="many_to_one",
    )
    policy["target_inventory_cases"] = (
        policy["target_inventory"] / policy["units_per_case"]
    )
    policy["opening_inventory_cases"] = policy["target_inventory_cases"] * 0.80

    requirements = weekly_demand.merge(
        policy[
            [
                "sku",
                "region",
                "target_inventory_cases",
                "opening_inventory_cases",
            ]
        ],
        on=["sku", "region"],
        how="left",
        validate="many_to_one",
    )
    if requirements[["target_inventory_cases", "opening_inventory_cases"]].isna().any().any():
        raise ValueError("Every weekly demand row must have an inventory policy")
    requirements["required_production_cases"] = (
        requirements["forecast_cases"]
        + requirements["target_inventory_cases"]
        - requirements["opening_inventory_cases"]
    ).clip(lower=0)
    return requirements


def optimize_week(
    weekly_requirements: pd.DataFrame,
    plants: pd.DataFrame,
    production_costs: pd.DataFrame,
    transport_costs: pd.DataFrame,
    capabilities: pd.DataFrame,
) -> tuple[pd.DataFrame, str, float]:
    """Minimize production plus transport cost for one week."""
    model = LpProblem("Weekly_Beverage_Production", LpMinimize)
    required_keys = set(
        zip(weekly_requirements["sku"], weekly_requirements["region"])
    )
    required_skus = {sku for sku, _ in required_keys}
    required_regions = {region for _, region in required_keys}
    feasible = [
        (row["plant_id"], row["sku"], region)
        for _, row in capabilities.iterrows()
        if row["sku"] in required_skus
        for region in required_regions
        if (row["sku"], region) in required_keys
    ]
    feasible = list(dict.fromkeys(feasible))
    production = {
        key: LpVariable(
            f"prod_{key[0]}_{key[1]}_{key[2]}", lowBound=0
        )
        for key in feasible
    }

    production_cost_lookup = production_costs.set_index(
        ["plant_id", "sku"]
    )["production_cost_per_case"].to_dict()
    transport_cost_lookup = transport_costs.set_index(
        ["plant_id", "region"]
    )["cost_per_case"].to_dict()
    missing_costs = [
        key for key in feasible
        if (key[0], key[1]) not in production_cost_lookup
        or (key[0], key[2]) not in transport_cost_lookup
    ]
    if missing_costs:
        raise ValueError(f"Missing production or transport costs: {missing_costs[:5]}")

    model += lpSum(
        production[plant, sku, region]
        * (
            production_cost_lookup[(plant, sku)]
            + transport_cost_lookup[(plant, region)]
        )
        for plant, sku, region in feasible
    )

    for _, row in weekly_requirements.iterrows():
        sku = row["sku"]
        region = row["region"]
        required = row["required_production_cases"]
        model += (
            lpSum(
                production[plant, sku, region]
                for plant, candidate_sku, candidate_region in feasible
                if candidate_sku == sku and candidate_region == region
            )
            >= required,
            f"demand_{sku}_{region}",
        )

    for _, plant_row in plants.iterrows():
        plant = plant_row["plant_id"]
        model += (
            lpSum(
                production[candidate_plant, sku, region]
                for candidate_plant, sku, region in feasible
                if candidate_plant == plant
            )
            <= plant_row["weekly_capacity_cases"],
            f"capacity_{plant}",
        )

    model.solve()
    status = LpStatus[model.status]
    if status != "Optimal":
        return pd.DataFrame(), status, np.nan

    results = [
        {
            "plant_id": plant,
            "sku": sku,
            "region": region,
            "production_cases": variable.value(),
            "total_cost": variable.value()
            * (
                production_cost_lookup[(plant, sku)]
                + transport_cost_lookup[(plant, region)]
            ),
        }
        for (plant, sku, region), variable in production.items()
        if variable.value() and variable.value() > 0
    ]
    return pd.DataFrame(results), status, float(value(model.objective))


def main() -> None:
    (
        forecasts,
        products,
        plants,
        capabilities,
        costs,
        transport,
        policy,
    ) = load_inputs()
    requirements = build_production_requirements(forecasts, products, policy)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    requirements.to_csv(PROCESSED_DIR / "production_requirements.csv", index=False)

    plans = []
    weekly_summary = []
    for week in sorted(requirements["week_start"].unique()):
        week_requirements = requirements[requirements["week_start"] == week]
        plan, status, objective = optimize_week(
            week_requirements, plants, costs, transport, capabilities
        )
        if status != "Optimal":
            raise RuntimeError(f"Production model was {status} for week {week}")
        plan["week_start"] = week
        plans.append(plan)
        weekly_summary.append(
            {
                "week_start": week,
                "required_cases": week_requirements["required_production_cases"].sum(),
                "planned_cases": plan["production_cases"].sum(),
                "total_cost": objective,
                "optimization_status": status,
            }
        )

    production_plan = pd.concat(plans, ignore_index=True)
    weekly_summary = pd.DataFrame(weekly_summary)
    production_plan.to_csv(PROCESSED_DIR / "production_plan.csv", index=False)
    weekly_summary.to_csv(PROCESSED_DIR / "production_weekly_summary.csv", index=False)

    plant_production = (
        production_plan.groupby(["week_start", "plant_id"], as_index=False)
        .agg(production_cases=("production_cases", "sum"))
        .merge(plants[["plant_id", "weekly_capacity_cases"]], on="plant_id")
    )
    plant_production["capacity_utilization"] = (
        plant_production["production_cases"]
        / plant_production["weekly_capacity_cases"]
        * 100
    ).round(2)
    plant_production.to_csv(PROCESSED_DIR / "plant_production_utilization.csv", index=False)

    bottlenecks = plant_production[plant_production["capacity_utilization"] > 90]
    bottlenecks.to_csv(PROCESSED_DIR / "production_bottlenecks.csv", index=False)

    first_week = requirements["week_start"].min()
    first_plan = production_plan[production_plan["week_start"] == first_week]
    first_utilization = plant_production[plant_production["week_start"] == first_week]
    print(f"Weeks planned: {requirements['week_start'].nunique()}")
    print(f"Production plan rows: {len(production_plan):,}")
    print(f"First-week planned cases: {first_plan['production_cases'].sum():,.0f}")
    print("\nFirst-week plant utilization:")
    print(first_utilization.to_string(index=False))
    print(f"\nBottleneck plant-weeks (>90%): {len(bottlenecks)}")
    print(f"Saved outputs to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
