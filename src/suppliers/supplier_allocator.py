import os
import math
import pandas as pd


PROCUREMENT_PATH = (
    "data/processed/procurement_plan.csv"
)

SUPPLIER_PATH = (
    "data/processed/supplier_scores.csv"
)

OUTPUT_PATH = (
    "data/processed/supplier_purchase_plan.csv"
)


def allocate_supplier(
    requirement,
    suppliers
):
    """
    Allocate a procurement requirement across
    suppliers using supplier ranking and capacity.
    """

    remaining = requirement
    allocations = []

    suppliers = suppliers.sort_values(
        "supplier_rank"
    )

    for _, supplier in suppliers.iterrows():

        if remaining <= 0:
            break

        capacity = supplier["supplier_capacity"]
        moq = supplier["moq"]

        allocation = min(
            remaining,
            capacity
        )

        if allocation > 0:

            allocation = (
                math.ceil(
                    allocation / moq
                ) * moq
            )

            allocation = min(
                allocation,
                capacity
            )

            if allocation > 0:

                allocations.append({
                    "supplier_id":
                        supplier["supplier_id"],

                    "supplier_name":
                        supplier["supplier_name"],

                    "raw_material_id":
                        supplier["raw_material_id"],

                    "unit_cost":
                        supplier["unit_cost"],

                    "lead_time_days":
                        supplier["lead_time_days"],

                    "supplier_score":
                        supplier["supplier_score"],

                    "purchase_quantity":
                        allocation
                })

                remaining -= allocation

    return allocations


def main():

    os.makedirs(
        "data/processed",
        exist_ok=True
    )

    procurement = pd.read_csv(
        PROCUREMENT_PATH
    )

    suppliers = pd.read_csv(
        SUPPLIER_PATH
    )

    procurement = procurement[
        procurement[
            "planned_order_quantity"
        ] > 0
    ].copy()

    all_allocations = []

    for _, requirement in procurement.iterrows():

        raw_material = (
            requirement[
                "raw_material_id"
            ]
        )

        quantity = (
            requirement[
                "planned_order_quantity"
            ]
        )

        matching_suppliers = suppliers[
            suppliers[
                "raw_material_id"
            ] == raw_material
        ].copy()

        allocations = allocate_supplier(
            quantity,
            matching_suppliers
        )

        for allocation in allocations:

            record = {
                "week_start":
                    requirement["week_start"],

                "plant_id":
                    requirement["plant_id"],

                "raw_material_id":
                    raw_material,

                "required_quantity":
                    quantity
            }

            record.update(allocation)

            record["purchase_cost"] = (
                record["purchase_quantity"]
                * record["unit_cost"]
            )

            all_allocations.append(record)

    result = pd.DataFrame(
        all_allocations
    )

    if not result.empty:

        result.to_csv(
            OUTPUT_PATH,
            index=False
        )

        print(
            f"Supplier purchase plan saved to "
            f"{OUTPUT_PATH}"
        )

        print("\nSupplier Summary:")

        summary = (
            result
            .groupby(
                [
                    "supplier_id",
                    "supplier_name"
                ],
                as_index=False
            )
            .agg(
                total_quantity=(
                    "purchase_quantity",
                    "sum"
                ),
                total_cost=(
                    "purchase_cost",
                    "sum"
                )
            )
            .sort_values(
                "total_cost",
                ascending=False
            )
        )

        print(
            summary.to_string(
                index=False
            )
        )

    else:

        print(
            "No procurement requirements found."
        )


if __name__ == "__main__":
    main()