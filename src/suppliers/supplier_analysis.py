import os
import pandas as pd
import numpy as np


SUPPLIER_PATH = "data/raw/suppliers.csv"
OUTPUT_PATH = "data/processed/supplier_scores.csv"


def min_max_inverse(series):
    """
    Lower value is better.
    Converts values to a 0-1 score where
    lower original values receive higher scores.
    """
    min_value = series.min()
    max_value = series.max()

    if max_value == min_value:
        return pd.Series(
            1.0,
            index=series.index
        )

    return 1 - (
        (series - min_value)
        / (max_value - min_value)
    )


def min_max_positive(series):
    """
    Higher value is better.
    Converts values to a 0-1 score.
    """
    min_value = series.min()
    max_value = series.max()

    if max_value == min_value:
        return pd.Series(
            1.0,
            index=series.index
        )

    return (
        (series - min_value)
        / (max_value - min_value)
    )


def calculate_supplier_scores(suppliers):

    suppliers = suppliers.copy()

    suppliers["cost_score"] = (
        suppliers
        .groupby("raw_material_id")["unit_cost"]
        .transform(min_max_inverse)
    )

    suppliers["lead_time_score"] = (
        suppliers
        .groupby("raw_material_id")["lead_time_days"]
        .transform(min_max_inverse)
    )

    suppliers["quality_score"] = (
        suppliers
        .groupby("raw_material_id")["quality_rate"]
        .transform(min_max_positive)
    )

    suppliers["on_time_score"] = (
        suppliers
        .groupby("raw_material_id")["on_time_rate"]
        .transform(min_max_positive)
    )

    # Weighted supplier score
    suppliers["supplier_score"] = (
        0.35 * suppliers["cost_score"]
        + 0.20 * suppliers["lead_time_score"]
        + 0.20 * suppliers["quality_score"]
        + 0.25 * suppliers["on_time_score"]
    )

    suppliers["supplier_rank"] = (
        suppliers
        .groupby("raw_material_id")["supplier_score"]
        .rank(
            ascending=False,
            method="dense"
        )
    )

    return suppliers


def main():

    os.makedirs(
        "data/processed",
        exist_ok=True
    )

    suppliers = pd.read_csv(
        SUPPLIER_PATH
    )

    supplier_scores = (
        calculate_supplier_scores(
            suppliers
        )
    )

    supplier_scores = supplier_scores.sort_values(
        [
            "raw_material_id",
            "supplier_rank"
        ]
    )

    supplier_scores.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(
        f"Supplier analysis saved to {OUTPUT_PATH}"
    )

    print("\nTop Supplier by Raw Material:")

    top_suppliers = (
        supplier_scores[
            supplier_scores["supplier_rank"] == 1
        ][
            [
                "raw_material_id",
                "supplier_id",
                "supplier_name",
                "unit_cost",
                "lead_time_days",
                "supplier_score"
            ]
        ]
    )

    print(top_suppliers.to_string(index=False))


if __name__ == "__main__":
    main()