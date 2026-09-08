"""Calculate inventory policies and simulate replenishment decisions."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy.stats import norm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "parameters.yaml"
FORECAST_PATH = PROJECT_ROOT / "data" / "processed" / "demand_forecasts.csv"
PRODUCT_PATH = PROJECT_ROOT / "data" / "raw" / "products.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_forecasts(path: Path = FORECAST_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing forecast file: {path}")
    forecasts = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "sku", "region", "units_sold", "ml_prediction"}
    missing = sorted(required.difference(forecasts.columns))
    if missing:
        raise ValueError(f"Forecast data is missing columns: {missing}")
    return forecasts.sort_values(["sku", "region", "date"]).reset_index(drop=True)


def load_product_prices(path: Path = PRODUCT_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing product file: {path}")
    products = pd.read_csv(path, usecols=["sku", "base_price"])
    if products["sku"].duplicated().any():
        raise ValueError("Product file contains duplicate SKU prices")
    return products


def calculate_inventory_policy(
    forecasts: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    inventory_config = config["inventory"]
    lead_times = config["lead_times"]
    service_level = inventory_config["default_service_level"]
    review_period = inventory_config["review_period_days"]

    demand_stats = (
        forecasts.groupby(["sku", "region"])
        .agg(
            average_daily_demand=("ml_prediction", "mean"),
            demand_std=("ml_prediction", "std"),
            actual_average_demand=("units_sold", "mean"),
        )
        .reset_index()
    )
    demand_stats["demand_std"] = demand_stats["demand_std"].fillna(0)
    demand_stats["lead_time_days"] = demand_stats["region"].map(lead_times)
    if demand_stats["lead_time_days"].isna().any():
        unknown_regions = sorted(
            demand_stats.loc[demand_stats["lead_time_days"].isna(), "region"].unique()
        )
        raise ValueError(f"No lead time configured for regions: {unknown_regions}")

    z_score = norm.ppf(service_level)
    demand_stats["safety_stock"] = (
        z_score
        * demand_stats["demand_std"]
        * np.sqrt(demand_stats["lead_time_days"])
    ).clip(lower=0).round()
    demand_stats["lead_time_demand"] = (
        demand_stats["average_daily_demand"] * demand_stats["lead_time_days"]
    )
    demand_stats["reorder_point"] = (
        demand_stats["lead_time_demand"] + demand_stats["safety_stock"]
    ).round()
    demand_stats["target_inventory"] = (
        demand_stats["average_daily_demand"]
        * (demand_stats["lead_time_days"] + review_period)
        + demand_stats["safety_stock"]
    ).round()
    demand_stats["days_of_inventory"] = (
        demand_stats["target_inventory"] / demand_stats["average_daily_demand"]
    ).replace([np.inf, -np.inf], np.nan).round(1)

    return demand_stats[
        [
            "sku",
            "region",
            "average_daily_demand",
            "demand_std",
            "actual_average_demand",
            "lead_time_days",
            "lead_time_demand",
            "safety_stock",
            "reorder_point",
            "target_inventory",
            "days_of_inventory",
        ]
    ]


def simulate_inventory(
    demand_series: pd.DataFrame,
    reorder_point: float,
    target_inventory: float,
    lead_time: int,
) -> pd.DataFrame:
    """Simulate continuous-review replenishment with lost sales."""
    inventory = float(target_inventory)
    pipeline_orders: list[dict] = []
    records = []

    for _, row in demand_series.sort_values("date").iterrows():
        date = row["date"]
        demand = float(row["units_sold"])
        received_quantity = sum(
            order["quantity"]
            for order in pipeline_orders
            if order["arrival_date"] <= date
        )
        pipeline_orders = [
            order for order in pipeline_orders if order["arrival_date"] > date
        ]
        inventory += received_quantity
        beginning_inventory = inventory

        fulfilled = min(inventory, demand)
        lost_sales = max(demand - inventory, 0)
        inventory -= fulfilled

        pipeline_quantity = sum(order["quantity"] for order in pipeline_orders)
        inventory_position = inventory + pipeline_quantity
        order_quantity = 0.0
        if inventory_position <= reorder_point:
            order_quantity = max(target_inventory - inventory_position, 0)
            if order_quantity > 0:
                pipeline_orders.append(
                    {
                        "order_date": date,
                        "arrival_date": date + pd.Timedelta(days=lead_time),
                        "quantity": order_quantity,
                    }
                )

        records.append(
            {
                "date": date,
                "beginning_inventory": beginning_inventory,
                "demand": demand,
                "fulfilled": fulfilled,
                "lost_sales": lost_sales,
                "ending_inventory": inventory,
                "inventory_position": inventory_position,
                "order_quantity": order_quantity,
                "received_quantity": received_quantity,
            }
        )

    return pd.DataFrame(records)


def calculate_kpis(
    simulation: pd.DataFrame,
    products: pd.DataFrame,
    holding_cost_rate: float,
) -> pd.DataFrame:
    kpis = (
        simulation.groupby(["sku", "region"])
        .agg(
            total_demand=("demand", "sum"),
            fulfilled_demand=("fulfilled", "sum"),
            lost_sales=("lost_sales", "sum"),
            average_inventory=("ending_inventory", "mean"),
            max_inventory=("ending_inventory", "max"),
            stockout_days=("lost_sales", lambda values: (values > 0).sum()),
            replenishment_orders=(
                "order_quantity",
                lambda values: (values > 0).sum(),
            ),
        )
        .reset_index()
    )
    kpis["service_level"] = (
        kpis["fulfilled_demand"] / kpis["total_demand"] * 100
    ).round(2)
    kpis["stockout_rate"] = (
        kpis["lost_sales"] / kpis["total_demand"] * 100
    ).round(2)
    kpis = kpis.merge(products, on="sku", how="left", validate="many_to_one")
    if kpis["base_price"].isna().any():
        missing_skus = sorted(kpis.loc[kpis["base_price"].isna(), "sku"].unique())
        raise ValueError(f"No product price configured for SKUs: {missing_skus}")
    annualization_factor = 365 / simulation["date"].nunique()
    kpis["average_inventory_value"] = (
        kpis["average_inventory"] * kpis["base_price"]
    ).round(2)
    kpis["annual_demand_value"] = (
        kpis["total_demand"] * annualization_factor * kpis["base_price"]
    ).round(2)
    kpis["inventory_turns"] = (
        kpis["annual_demand_value"] / kpis["average_inventory_value"]
    ).replace([np.inf, -np.inf], np.nan).round(2)
    kpis["annual_holding_cost"] = (
        kpis["average_inventory_value"] * holding_cost_rate
    ).round(2)
    kpis = kpis.drop(columns=["base_price"])
    return kpis


def save_sample_plot(
    simulation: pd.DataFrame,
    policy: pd.DataFrame,
    output_path: Path,
) -> None:
    sample = simulation[
        (simulation["sku"] == "BB500") & (simulation["region"] == "West")
    ]
    sample_policy = policy[
        (policy["sku"] == "BB500") & (policy["region"] == "West")
    ]
    if sample.empty or sample_policy.empty:
        return

    row = sample_policy.iloc[0]
    plt.figure(figsize=(14, 5))
    plt.plot(sample["date"], sample["ending_inventory"], label="Ending Inventory")
    plt.axhline(row["reorder_point"], linestyle="--", label="Reorder Point")
    plt.axhline(row["safety_stock"], linestyle=":", label="Safety Stock")
    plt.title("Inventory Simulation - BB500 / West")
    plt.xlabel("Date")
    plt.ylabel("Units")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def main() -> None:
    config = load_config()
    forecasts = load_forecasts()
    products = load_product_prices()
    policy = calculate_inventory_policy(forecasts, config)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    policy.to_csv(OUTPUT_DIR / "inventory_policy.csv", index=False)

    simulations = []
    for _, policy_row in policy.iterrows():
        demand = forecasts[
            (forecasts["sku"] == policy_row["sku"])
            & (forecasts["region"] == policy_row["region"])
        ][["date", "units_sold"]]
        result = simulate_inventory(
            demand,
            policy_row["reorder_point"],
            policy_row["target_inventory"],
            int(policy_row["lead_time_days"]),
        )
        result["sku"] = policy_row["sku"]
        result["region"] = policy_row["region"]
        simulations.append(result)

    inventory_simulation = pd.concat(simulations, ignore_index=True)
    inventory_kpis = calculate_kpis(
        inventory_simulation,
        products,
        config["inventory"]["holding_cost_rate"],
    )
    inventory_simulation.to_csv(
        OUTPUT_DIR / "inventory_simulation.csv", index=False
    )
    inventory_kpis.to_csv(OUTPUT_DIR / "inventory_kpis.csv", index=False)
    save_sample_plot(
        inventory_simulation,
        policy,
        OUTPUT_DIR / "inventory_simulation_bb500_west.png",
    )

    print(f"Service level target: {config['inventory']['default_service_level']:.0%}")
    print(f"Z-score: {norm.ppf(config['inventory']['default_service_level']):.3f}")
    print(f"Policy rows: {len(policy):,}")
    print(f"Simulation rows: {len(inventory_simulation):,}")
    print("\nInventory KPI summary:")
    print(inventory_kpis.to_string(index=False))
    print(f"\nSaved outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
