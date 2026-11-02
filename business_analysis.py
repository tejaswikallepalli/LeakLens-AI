from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("data")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def load_csv(name):
    path = DATA_DIR / name
    if not path.exists():
        # Also support CSVs stored directly in the project folder.
        path = Path(name)

    if not path.exists():
        raise FileNotFoundError(f"Could not find {name}")

    return pd.read_csv(path)


def save_report(df, filename):
    path = REPORT_DIR / filename
    df.to_csv(path, index=False)
    print(f"Saved: {path}")


def main():
    print("\n" + "=" * 60)
    print("LEAKLENS - AI - BUSINESS ANALYSIS")
    print("=" * 60)

    transactions = load_csv("transactions.csv")
    products = load_csv("products.csv")
    customers = load_csv("customers.csv")
    inventory = load_csv("inventory.csv")
    campaigns = load_csv("campaigns.csv")

    # Standardize column names.
    for df in [transactions, products, customers, inventory, campaigns]:
        df.columns = df.columns.str.strip().str.lower()

    # Parse timestamps without silently discarding invalid records.
    if "timestamp" in transactions.columns:
        transactions["timestamp"] = pd.to_datetime(
            transactions["timestamp"], errors="coerce"
        )
        print(
            "\nTransaction timestamps that could not be parsed:",
            int(transactions["timestamp"].isna().sum())
        )

    # 1. Transaction status summary.
    print("\n[1] TRANSACTION STATUS")
    if "status" in transactions.columns:
        status_summary = (
            transactions.groupby("status", dropna=False)
            .agg(transaction_count=("transaction_id", "count"))
            .reset_index()
        )
        status_summary["percentage"] = (
            status_summary["transaction_count"]
            / max(len(transactions), 1) * 100
        ).round(2)

        print(status_summary.to_string(index=False))
        save_report(status_summary, "transaction_status_summary.csv")

    # Calculate observed transaction value.
    required = {"quantity", "unit_price", "discount_pct"}
    if required.issubset(transactions.columns):
        transactions["gross_value"] = (
            transactions["quantity"] * transactions["unit_price"]
        )

        # Inspect discount values before calculating discounted amounts.
        discount = pd.to_numeric(
            transactions["discount_pct"], errors="coerce"
        )
        print(
            "\nDiscount percentage range:",
            discount.min(), "to", discount.max()
        )

        # Check discount format: decimal fraction (0 to 1) vs percentage (0 to 100)
        if discount.dropna().between(0, 1).all():
            print("Interpreting discount_pct as decimal fraction (0.0 to 1.0).")
            transactions["discount_fraction"] = discount
            transactions["discount_amount"] = (
                transactions["gross_value"] * transactions["discount_fraction"]
            )
            transactions["estimated_net_value"] = (
                transactions["gross_value"] - transactions["discount_amount"]
            )
        elif discount.dropna().between(0, 100).all():
            print("Interpreting discount_pct as percentage (0 to 100).")
            transactions["discount_fraction"] = discount / 100
            transactions["discount_amount"] = (
                transactions["gross_value"] * transactions["discount_fraction"]
            )
            transactions["estimated_net_value"] = (
                transactions["gross_value"] - transactions["discount_amount"]
            )
        else:
            transactions["estimated_net_value"] = np.nan
            print(
                "WARNING: discount_pct is outside the 0-100 range. "
                "Net value was not calculated."
            )

        print("\n[2] OBSERVED VALUE BY STATUS")
        if "status" in transactions.columns:
            value_summary = (
                transactions.groupby("status", dropna=False)
                .agg(
                    transaction_count=("transaction_id", "count"),
                    gross_value=("gross_value", "sum"),
                    discount_amount=("discount_amount", "sum"),
                    estimated_net_value=("estimated_net_value", "sum"),
                )
                .reset_index()
            )
            print(value_summary.to_string(index=False))
            save_report(value_summary, "value_by_status.csv")

    # 3. Product-level economics.
    print("\n[3] PRODUCT CATALOG CHECK")
    print("Product columns:", products.columns.tolist())

    product_candidates = [
        c for c in products.columns
        if any(word in c for word in ["price", "cost", "margin"])
    ]
    print("Potential price/cost fields:", product_candidates)

    # Print likely price/cost columns without assuming column names.
    if product_candidates:
        print(products[product_candidates].describe().to_string())

    # 4. Inventory overview.
    print("\n[4] INVENTORY CHECK")
    print("Inventory columns:", inventory.columns.tolist())

    inventory_candidates = [
        c for c in inventory.columns
        if any(word in c for word in [
            "stock", "quantity", "inventory", "reorder", "warehouse"
        ])
    ]
    print("Potential inventory fields:", inventory_candidates)

    # 5. Customer overview.
    print("\n[5] CUSTOMER TABLE")
    print("Rows:", len(customers))
    print("Columns:", customers.columns.tolist())

    # 6. Campaign overview.
    print("\n[6] CAMPAIGN TABLE")
    print("Rows:", len(campaigns))
    print("Columns:", campaigns.columns.tolist())

    # Do not claim campaign revenue attribution without a valid transaction link.
    possible_links = set(transactions.columns).intersection(campaigns.columns)
    print("Shared transaction/campaign column names:", sorted(possible_links))
    if not any("transaction" in c for c in possible_links):
        print(
            "NOTE: No obvious shared transaction key found. "
            "Do not attribute campaign spend or conversions to transactions "
            "without validating a legitimate join."
        )

    # 7. Export a cleaned transaction table for later experiments.
    # Keep all rows; do not remove pending, returned, or cancelled records.
    save_report(transactions, "transactions_enriched.csv")

    print("\nBusiness analysis finished.")
    print("Review the reports before drawing conclusions.")


if __name__ == "__main__":
    main()