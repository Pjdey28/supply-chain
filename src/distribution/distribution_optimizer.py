import os
import pandas as pd
from pulp import (
    LpProblem,
    LpMinimize,
    LpVariable,
    lpSum,
    LpStatus,
    LpContinuous
)


FORECAST_PATH = (
    "data/processed/demand_forecasts.csv"
)

PRODUCTION_PATH = (
    "data/processed/production_plan.csv"
)

WAREHOUSE_PATH = (
    "data/raw/warehouses.csv"
)

TRANSPORT_PATH = (
    "data/raw/plant_warehouse_transport.csv"
)

WAREHOUSE_COST_PATH = (
    "data/raw/warehouse_costs.csv"
)

OUTPUT_PATH = (
    "data/processed/distribution_plan.csv"
)

def calculate_warehouse_demand(forecast):
    """
    Convert regional daily demand forecasts
    into weekly warehouse requirements.
    """

    forecast["date"] = pd.to_datetime(
        forecast["date"]
    )

    forecast["week_start"] = (
        forecast["date"]
        - pd.to_timedelta(
            forecast["date"].dt.dayofweek,
            unit="D"
        )
    )

    region_to_warehouse = {
        "North": "WH_Delhi",
        "West": "WH_Mumbai",
        "East": "WH_Kolkata",
        "South": "WH_Bangalore",
        "Central": "WH_Hyderabad"
    }

    forecast["warehouse_id"] = (
        forecast["region"]
        .map(region_to_warehouse)
    )

    demand = (
        forecast
        .groupby(
            [
                "week_start",
                "sku",
                "warehouse_id"
            ],
            as_index=False
        )["ml_prediction"]
        .sum()
    )

    # Convert units to cases
    pack_units = {
        "BB250": 24,
        "BB500": 24,
        "BB1000": 12,
        "LM250": 24,
        "LM500": 24,
        "OR500": 24,
        "OR1000": 12,
        "EN250": 24,
        "EN500": 24,
        "WT1000": 12
    }

    demand["units_per_case"] = (
        demand["sku"].map(pack_units)
    )

    demand["demand_cases"] = (
        demand["ml_prediction"]
        / demand["units_per_case"]
    )

    return demand[
        [
            "week_start",
            "sku",
            "warehouse_id",
            "demand_cases"
        ]
    ]

def calculate_plant_supply(production):
    """
    Aggregate production plan into
    weekly plant-SKU supply.
    """

    production["week_start"] = pd.to_datetime(
        production["week_start"]
    )

    supply = (
        production
        .groupby(
            [
                "week_start",
                "plant_id",
                "sku"
            ],
            as_index=False
        )["production_cases"]
        .sum()
    )

    return supply

def optimize_distribution(
    week_demand,
    week_supply,
    warehouses,
    transport_costs,
    warehouse_costs
):

    model = LpProblem(
        "Finished_Goods_Distribution",
        LpMinimize
    )

    plants = week_supply[
        "plant_id"
    ].unique()

    skus = week_demand[
        "sku"
    ].unique()

    warehouse_ids = warehouses[
        "warehouse_id"
    ].unique()

    feasible_routes = []

    for plant in plants:
        for warehouse in warehouse_ids:
            for sku in skus:

                plant_available = week_supply[
                    (
                        week_supply["plant_id"]
                        == plant
                    )
                    &
                    (
                        week_supply["sku"]
                        == sku
                    )
                ]

                warehouse_required = week_demand[
                    (
                        week_demand["warehouse_id"]
                        == warehouse
                    )
                    &
                    (
                        week_demand["sku"]
                        == sku
                    )
                ]

                if (
                    not plant_available.empty
                    and not warehouse_required.empty
                ):
                    feasible_routes.append(
                        (
                            plant,
                            warehouse,
                            sku
                        )
                    )

    shipment = {
        route: LpVariable(
            f"ship_{route[0]}_{route[1]}_{route[2]}",
            lowBound=0,
            cat=LpContinuous
        )
        for route in feasible_routes
    }

    transport_lookup = {
        (
            row["plant_id"],
            row["warehouse_id"]
        ):
            row["cost_per_case"]
        for _, row in transport_costs.iterrows()
    }

    handling_lookup = {
        row["warehouse_id"]:
            row["handling_cost_per_case"]
        for _, row in warehouse_costs.iterrows()
    }

    # Objective:
    # Transportation + warehouse handling
    model += lpSum(
        shipment[p, w, s]
        * (
            transport_lookup[(p, w)]
            + handling_lookup[w]
        )
        for p, w, s in feasible_routes
    )

    # Demand fulfillment
    for _, row in week_demand.iterrows():

        warehouse = row["warehouse_id"]
        sku = row["sku"]
        required = row["demand_cases"]

        relevant_routes = [
            shipment[p, w, s]
            for p, w, s in feasible_routes
            if w == warehouse and s == sku
        ]

        if relevant_routes:

            model += (
                lpSum(relevant_routes)
                >= required
            )

    # Plant-SKU supply constraint
    for _, row in week_supply.iterrows():

        plant = row["plant_id"]
        sku = row["sku"]
        available = row["production_cases"]

        relevant_routes = [
            shipment[p, w, s]
            for p, w, s in feasible_routes
            if p == plant and s == sku
        ]

        if relevant_routes:

            model += (
                lpSum(relevant_routes)
                <= available
            )

    # Warehouse capacity
    for _, row in warehouses.iterrows():

        warehouse = row["warehouse_id"]
        capacity = row["capacity_cases"]

        relevant_routes = [
            shipment[p, w, s]
            for p, w, s in feasible_routes
            if w == warehouse
        ]

        if relevant_routes:

            model += (
                lpSum(relevant_routes)
                <= capacity
            )

    model.solve()

    if LpStatus[
        model.status
    ] != "Optimal":

        print(
            "Warning: distribution model status =",
            LpStatus[model.status]
        )

    results = []

    for (
        plant,
        warehouse,
        sku
    ), variable in shipment.items():

        quantity = variable.value()

        if quantity is not None and quantity > 0:

            results.append({
                "plant_id": plant,
                "warehouse_id": warehouse,
                "sku": sku,
                "shipment_cases": quantity,
                "transport_cost_per_case":
                    transport_lookup[
                        (plant, warehouse)
                    ],
                "handling_cost_per_case":
                    handling_lookup[
                        warehouse
                    ]
            })

    return pd.DataFrame(results)


def calculate_distribution_kpis(
    distribution_plan
):

    total_cases = (
        distribution_plan[
            "shipment_cases"
        ].sum()
    )

    total_cost = (
        distribution_plan[
            "distribution_cost"
        ].sum()
    )

    avg_cost_per_case = (
        total_cost / total_cases
        if total_cases > 0
        else 0
    )

    plant_summary = (
        distribution_plan
        .groupby("plant_id")
        .agg(
            cases_shipped=(
                "shipment_cases",
                "sum"
            ),
            distribution_cost=(
                "distribution_cost",
                "sum"
            )
        )
        .reset_index()
    )

    warehouse_summary = (
        distribution_plan
        .groupby("warehouse_id")
        .agg(
            cases_received=(
                "shipment_cases",
                "sum"
            ),
            distribution_cost=(
                "distribution_cost",
                "sum"
            )
        )
        .reset_index()
    )

    return (
        total_cases,
        total_cost,
        avg_cost_per_case,
        plant_summary,
        warehouse_summary
    )


def main():

    os.makedirs(
        "data/processed",
        exist_ok=True
    )

    forecast = pd.read_csv(
        FORECAST_PATH
    )

    production = pd.read_csv(
        PRODUCTION_PATH
    )

    warehouses = pd.read_csv(
        WAREHOUSE_PATH
    )

    transport_costs = pd.read_csv(
        TRANSPORT_PATH
    )

    warehouse_costs = pd.read_csv(
        WAREHOUSE_COST_PATH
    )

    demand = calculate_warehouse_demand(
        forecast
    )

    supply = calculate_plant_supply(
        production
    )

    all_plans = []

    weeks = sorted(
        demand["week_start"]
        .unique()
    )

    for week in weeks:

        week_demand = demand[
            demand["week_start"] == week
        ].copy()

        week_supply = supply[
            supply["week_start"] == week
        ].copy()

        if week_supply.empty:
            continue

        plan = optimize_distribution(
            week_demand=week_demand,
            week_supply=week_supply,
            warehouses=warehouses,
            transport_costs=transport_costs,
            warehouse_costs=warehouse_costs
        )

        if not plan.empty:

            plan["week_start"] = week

            all_plans.append(plan)

    if not all_plans:

        print(
            "No distribution plan generated."
        )
        return

    distribution_plan = pd.concat(
        all_plans,
        ignore_index=True
    )

    distribution_plan[
        "distribution_cost"
    ] = (
        distribution_plan[
            "shipment_cases"
        ]
        * (
            distribution_plan[
                "transport_cost_per_case"
            ]
            +
            distribution_plan[
                "handling_cost_per_case"
            ]
        )
    )

    distribution_plan.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(
        "Distribution plan saved to:",
        OUTPUT_PATH
    )

    print("\nTotal Distribution Cost:")

    print(
        distribution_plan[
            "distribution_cost"
        ].sum()
    )

    (
        total_cases,
        total_cost,
        avg_cost_per_case,
        plant_summary,
        warehouse_summary
    ) = calculate_distribution_kpis(
        distribution_plan
    )

    print("\nDistribution KPIs:")
    print("Total cases shipped:", round(total_cases, 2))
    print("Total distribution cost:", round(total_cost, 2))
    print("Average cost per case:", round(avg_cost_per_case, 2))

    print("\nPlant summary:")
    print(plant_summary.to_string(index=False))

    print("\nWarehouse summary:")
    print(warehouse_summary.to_string(index=False))


if __name__ == "__main__":
    main()