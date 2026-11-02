from pathlib import Path
import json
import warnings

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

DATA_DIR = Path("data")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def load_transactions():
    path = DATA_DIR / "transactions.csv"
    if not path.exists():
        path = Path("transactions.csv")
    if not path.exists():
        raise FileNotFoundError("transactions.csv was not found.")

    return pd.read_csv(path)


def main():
    print("=" * 65)
    print("LEAKLENS - AI - TRANSACTION STATUS MODEL EXPERIMENT")
    print("=" * 65)

    df = load_transactions()
    df.columns = df.columns.str.strip().str.lower()

    required = [
        "status",
        "timestamp",
        "quantity",
        "unit_price",
        "discount_pct",
        "channel",
        "payment_method",
    ]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"Required columns missing: {missing}")

    # Pending is excluded because its final outcome may not be known yet.
    df["status"] = df["status"].astype(str).str.strip()
    df = df[df["status"].isin(["Completed", "Cancelled", "Returned"])].copy()

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "status"])

    if len(df) < 30:
        raise ValueError("Not enough usable rows for a reliable experiment.")

    # Build features that could be available before the transaction outcome.
    # Do not include status, transaction IDs, or post-outcome information.
    df["transaction_month"] = df["timestamp"].dt.month
    df["transaction_dayofweek"] = df["timestamp"].dt.dayofweek
    df["transaction_hour"] = df["timestamp"].dt.hour

    numeric_features = [
        "quantity",
        "unit_price",
        "discount_pct",
        "transaction_month",
        "transaction_dayofweek",
        "transaction_hour",
    ]

    categorical_features = [
        "channel",
        "payment_method",
    ]

    # Include IDs only if present; these can help reveal repeated-entity
    # patterns, but may also encourage memorization.
    for col in ["customer_id", "product_id"]:
        if col in df.columns:
            categorical_features.append(col)

    features = numeric_features + categorical_features
    X = df[features].copy()
    y = df["status"].copy()

    for col in numeric_features:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    # Use a chronological holdout: earlier records for training,
    # later records for testing.
    order = df["timestamp"].sort_values().index
    split_position = int(len(order) * 0.8)

    train_idx = order[:split_position]
    test_idx = order[split_position:]

    X_train, X_test = X.loc[train_idx], X.loc[test_idx]
    y_train, y_test = y.loc[train_idx], y.loc[test_idx]

    if y_train.nunique() < 2:
        raise ValueError(
            "Training period contains fewer than two classes. "
            "A valid classification experiment cannot run."
        )

    print("\nRows used:", len(df))
    print("Training rows:", len(X_train))
    print("Testing rows:", len(X_test))
    print("Target class counts:")
    print(y.value_counts().to_string())
    print("\nFeature columns:", features)
    print("Train date range:",
          df.loc[train_idx, "timestamp"].min(),
          "to", df.loc[train_idx, "timestamp"].max())
    print("Test date range:",
          df.loc[test_idx, "timestamp"].min(),
          "to", df.loc[test_idx, "timestamp"].max())

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    preprocess = ColumnTransformer([
        ("numeric", numeric_pipeline, numeric_features),
        ("categorical", categorical_pipeline, categorical_features),
    ])

    models = {
        "Baseline most frequent": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": LogisticRegression(
            max_iter=1500,
            class_weight="balanced",
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),
    }

    results = []
    prediction_rows = []
    per_class_rows = []

    for name, classifier in models.items():
        print("\n" + "-" * 65)
        print("MODEL:", name)

        pipeline = Pipeline([
            ("preprocess", preprocess),
            ("model", classifier),
        ])

        pipeline.fit(X_train, y_train)
        
        train_predictions = pipeline.predict(X_train)
        train_accuracy = accuracy_score(y_train, train_predictions)
        train_macro_f1 = f1_score(
            y_train, train_predictions, average="macro", zero_division=0
        )

        test_predictions = pipeline.predict(X_test)
        test_accuracy = accuracy_score(y_test, test_predictions)
        test_macro_f1 = f1_score(
            y_test, test_predictions, average="macro", zero_division=0
        )

        results.append({
            "model": name,
            "train_accuracy": train_accuracy,
            "test_accuracy": test_accuracy,
            "train_macro_f1": train_macro_f1,
            "test_macro_f1": test_macro_f1,
            "accuracy": test_accuracy,
            "macro_f1": test_macro_f1,
            "train_rows": len(X_train),
            "test_rows": len(X_test),
        })

        print("Training Accuracy:", round(train_accuracy, 4))
        print("Training Macro-F1:", round(train_macro_f1, 4))
        print("Testing Accuracy: ", round(test_accuracy, 4))
        print("Testing Macro-F1: ", round(test_macro_f1, 4))
        print("\nTest Classification report:")
        rep_text = classification_report(
            y_test,
            test_predictions,
            zero_division=0,
        )
        print(rep_text)

        rep_dict = classification_report(
            y_test,
            test_predictions,
            output_dict=True,
            zero_division=0,
        )
        for cls_name in ["Cancelled", "Completed", "Returned", "macro avg", "weighted avg"]:
            if cls_name in rep_dict:
                per_class_rows.append({
                    "model": name,
                    "class": cls_name,
                    "precision": round(rep_dict[cls_name]["precision"], 4),
                    "recall": round(rep_dict[cls_name]["recall"], 4),
                    "f1_score": round(rep_dict[cls_name]["f1-score"], 4),
                    "support": int(rep_dict[cls_name]["support"]),
                })

        labels = sorted(y.unique())
        cm = confusion_matrix(y_test, test_predictions, labels=labels)
        cm_df = pd.DataFrame(
            cm,
            index=[f"actual_{label}" for label in labels],
            columns=[f"predicted_{label}" for label in labels],
        )
        safe_name = name.lower().replace(" ", "_")
        cm_df.to_csv(REPORT_DIR / f"confusion_{safe_name}.csv")

        if name != "Baseline most frequent":
            prediction_rows.append(pd.DataFrame({
                "row_index": X_test.index,
                "timestamp": df.loc[X_test.index, "timestamp"].values,
                "actual_status": y_test.values,
                "predicted_status": test_predictions,
                "model": name,
            }))

    results_df = pd.DataFrame(results).sort_values(
        "macro_f1", ascending=False
    )
    results_df.to_csv(REPORT_DIR / "model_comparison.csv", index=False)

    if per_class_rows:
        pd.DataFrame(per_class_rows).to_csv(REPORT_DIR / "per_class_metrics.csv", index=False)

    if prediction_rows:
        pd.concat(prediction_rows, ignore_index=True).to_csv(
            REPORT_DIR / "test_predictions.csv", index=False
        )

    metadata = {
        "experiment": "transaction_status_classification",
        "target": "status",
        "excluded_status": "Pending",
        "split": "chronological 80% train / 20% test",
        "features": features,
        "leakage_notes": (
            "Status, transaction_id, and post-outcome fields excluded. "
            "Customer/product IDs are included if present and may create "
            "memorization risk. Results indicate prediction, not causation."
        ),
        "best_model_by_macro_f1": results_df.iloc[0]["model"],
        "best_macro_f1": float(results_df.iloc[0]["macro_f1"]),
    }

    with open(REPORT_DIR / "model_experiment_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "=" * 65)
    print("MODEL COMPARISON")
    print("=" * 65)
    print(results_df.to_string(index=False))
    print("\nSaved reports in:", REPORT_DIR.resolve())
    print("Experiment completed.")


if __name__ == "__main__":
    main()