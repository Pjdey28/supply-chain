from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "forecast_dataset.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
TARGET = "units_sold"

NUMERIC_FEATURES = [
    "month",
    "week",
    "day_of_week",
    "day_of_year",
    "is_weekend",
    "price",
    "promotion",
    "is_holiday",
    "lag_1",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_mean_28",
    "rolling_std_28",
]
CATEGORICAL_FEATURES = ["sku", "region"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def wape(y_true: pd.Series, y_pred: pd.Series) -> float:
    """Return weighted absolute percentage error."""
    denominator = np.sum(np.abs(y_true))
    if denominator == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denominator)


def evaluate_model(y_true: pd.Series, y_pred: pd.Series) -> dict[str, float]:
    """Calculate the error metrics used for model comparison."""
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "WAPE": wape(y_true, y_pred),
    }


def load_data(path: Path = INPUT_PATH) -> pd.DataFrame:
    """Load and validate the feature-engineered modeling data."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing input dataset: {path}. Run the EDA feature-engineering notebook first."
        )

    data = pd.read_csv(path, parse_dates=["date"])
    required_columns = {"date", TARGET, *FEATURES}
    missing_columns = sorted(required_columns.difference(data.columns))
    if missing_columns:
        raise ValueError(f"Input dataset is missing columns: {missing_columns}")

    return data.sort_values(["date", "sku", "region"]).reset_index(drop=True)


def build_model() -> Pipeline:
    """Build the preprocessing and XGBoost regression pipeline."""
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
            ("numeric", "passthrough", NUMERIC_FEATURES),
        ]
    )

    xgb_model = XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=8,
        min_child_weight=5,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", xgb_model),
        ]
    )


def add_predictions(
    frame: pd.DataFrame,
    model: Pipeline,
) -> pd.DataFrame:
    """Add non-negative model predictions to a copy of a data split."""
    result = frame.copy()
    result["ml_prediction"] = np.maximum(model.predict(result[FEATURES]), 0)
    return result


def sku_metrics(test: pd.DataFrame) -> pd.DataFrame:
    """Calculate forecast performance for each SKU."""
    rows = []
    for sku, group in test.groupby("sku"):
        rows.append(
            {
                "sku": sku,
                "actual_demand": group[TARGET].sum(),
                "forecast_demand": group["ml_prediction"].sum(),
                "MAE": mean_absolute_error(group[TARGET], group["ml_prediction"]),
                "WAPE": wape(group[TARGET], group["ml_prediction"]),
            }
        )
    return pd.DataFrame(rows).sort_values("WAPE").reset_index(drop=True)


def save_sample_plot(test: pd.DataFrame, output_path: Path) -> None:
    """Save an actual-versus-forecast plot for BB500 in the West region."""
    sample = test[(test["sku"] == "BB500") & (test["region"] == "West")]
    if sample.empty:
        return

    plt.figure(figsize=(14, 5))
    plt.plot(sample["date"], sample[TARGET], label="Actual")
    plt.plot(sample["date"], sample["ml_prediction"], label="Forecast")
    plt.title("Actual vs Forecast - BB500 / West")
    plt.xlabel("Date")
    plt.ylabel("Units Sold")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def main() -> None:
    df = load_data()

    train = df[df["date"] < "2025-01-01"].copy()
    validation = df[
        (df["date"] >= "2025-01-01") & (df["date"] < "2025-07-01")
    ].copy()
    test = df[df["date"] >= "2025-07-01"].copy()

    print(f"Dataset: {df.shape}")
    print(f"Train: {train.shape}")
    print(f"Validation: {validation.shape}")
    print(f"Test: {test.shape}")

    validation["baseline_prediction"] = validation["lag_7"]
    test["baseline_prediction"] = test["lag_7"]

    baseline_validation_metrics = evaluate_model(
        validation[TARGET], validation["baseline_prediction"]
    )
    baseline_test_metrics = evaluate_model(test[TARGET], test["baseline_prediction"])

    model = build_model()
    model.fit(train[FEATURES], train[TARGET])

    validation = add_predictions(validation, model)
    ml_validation_metrics = evaluate_model(
        validation[TARGET], validation["ml_prediction"]
    )
    validation_comparison = pd.DataFrame(
        [
            {"Model": "Seasonal Naive", **baseline_validation_metrics},
            {"Model": "XGBoost", **ml_validation_metrics},
        ]
    )

    test = add_predictions(test, model)
    ml_test_metrics = evaluate_model(test[TARGET], test["ml_prediction"])
    test_comparison = pd.DataFrame(
        [
            {"Model": "Seasonal Naive", **baseline_test_metrics},
            {"Model": "XGBoost", **ml_test_metrics},
        ]
    )

    test["forecast_error"] = test[TARGET] - test["ml_prediction"]
    performance = sku_metrics(test)
    bias = test.groupby("sku")["forecast_error"].mean().sort_values()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    test[
        [
            "date",
            "sku",
            "region",
            TARGET,
            "ml_prediction",
            "forecast_error",
            "promotion",
            "is_holiday",
        ]
    ].to_csv(OUTPUT_DIR / "demand_forecasts.csv", index=False)
    performance.to_csv(OUTPUT_DIR / "forecast_performance_by_sku.csv", index=False)
    save_sample_plot(test, OUTPUT_DIR / "actual_vs_forecast_bb500_west.png")

    print("\nValidation comparison:")
    print(validation_comparison.to_string(index=False))
    print("\nTest comparison:")
    print(test_comparison.to_string(index=False))
    print(f"\nTest WAPE: {ml_test_metrics['WAPE']:.4f}")
    print(f"Approximate forecast accuracy: {(1 - ml_test_metrics['WAPE']) * 100:.2f}%")
    print("\nSKU performance:")
    print(performance.to_string(index=False))
    print("\nForecast bias by SKU:")
    print(bias.to_string())
    print(f"\nSaved outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
