from pathlib import Path
import pandas as pd

# All CSV files are expected inside the data folder.
DATA_DIR = Path(".")

FILES = [
    "transactions.csv",
    "customers.csv",
    "products.csv",
    "inventory.csv",
    "campaigns.csv",
]


def load_csv(filename):
    for path in [Path("data") / filename, Path(filename)]:
        if path.exists():
            return pd.read_csv(path)
    raise FileNotFoundError(
        f"Cannot find {filename} in ./data or current directory."
    )


def main():
    tables = {}

    print("=" * 65)
    print("LEAKLENS - AI - DATA PROFILE")
    print("=" * 65)

    for filename in FILES:
        df = load_csv(filename)
        tables[filename] = df

        print(f"\n\nFILE: {filename}")
        print("-" * 65)
        print("Rows:", len(df))
        print("Columns:", len(df.columns))
        print("Column names:", list(df.columns))

        print("\nData types:")
        print(df.dtypes.to_string())

        print("\nMissing values:")
        missing = df.isna().sum()
        print(missing[missing > 0].to_string() if missing.any()
              else "No missing values detected.")

        print("\nDuplicate rows:", int(df.duplicated().sum()))

        print("\nSample records:")
        print(df.head(3).to_string(index=False))

    # Check transaction foreign keys if the expected columns exist.
    transactions = tables["transactions.csv"]
    customers = tables["customers.csv"]
    products = tables["products.csv"]

    print("\n\n" + "=" * 65)
    print("KEY INTEGRITY CHECKS")
    print("=" * 65)

    if "customer_id" in transactions.columns and "customer_id" in customers.columns:
        customer_ids = set(customers["customer_id"].dropna())
        missing_customers = ~transactions["customer_id"].isin(customer_ids)
        print(
            "Transactions with unmatched customer IDs:",
            int(missing_customers.sum())
        )
    else:
        print("Customer ID check skipped: expected column not found.")

    if "product_id" in transactions.columns and "product_id" in products.columns:
        product_ids = set(products["product_id"].dropna())
        missing_products = ~transactions["product_id"].isin(product_ids)
        print(
            "Transactions with unmatched product IDs:",
            int(missing_products.sum())
        )
    else:
        print("Product ID check skipped: expected column not found.")

    if "transaction_id" in transactions.columns:
        print(
            "Duplicate transaction IDs:",
            int(transactions["transaction_id"].duplicated().sum())
        )
    else:
        print("Transaction ID uniqueness check skipped.")

    # Save a reusable summary.
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)

    summary = []
    for filename, df in tables.items():
        summary.append({
            "file": filename,
            "rows": len(df),
            "columns": len(df.columns),
            "missing_cells": int(df.isna().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
        })

    pd.DataFrame(summary).to_csv(
        output_dir / "data_profile_summary.csv",
        index=False
    )

    print("\n\nSaved summary to reports/data_profile_summary.csv")
    print("Data profiling completed.")


if __name__ == "__main__":
    main()
