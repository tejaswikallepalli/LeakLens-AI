from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("data")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def load_csv(filename):
    path = DATA_DIR / filename
    if not path.exists():
        path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Cannot find {filename}")
    return pd.read_csv(path)


def find_column(df, candidates):
    """Find a column by matching common names."""
    normalized = {c.lower().strip(): c for c in df.columns}

    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]

    return None


def save_report(df, filename):
    path = REPORT_DIR / filename
    df.to_csv(path, index=False)
    print(f"Saved {path} ({len(df)} rows)")


def main():
    print("=" * 65)
    print("LEAKLENS - AI - DATA VALIDATION AND LEAK CANDIDATES")
    print("=" * 65)

    transactions = load_csv("transactions.csv")
    products = load_csv("products.csv")
    inventory = load_csv("inventory.csv")

    for df in (transactions, products, inventory):
        df.columns = df.columns.str.strip().str.lower()

    # -------------------------------
    # 1. Correctly interpret discount
    # -------------------------------
    discount_col = find_column(transactions, ["discount_pct", "discount"])
    price_col = find_column(transactions, ["unit_price", "price"])
    quantity_col = find_column(transactions, ["quantity", "qty"])
    status_col = find_column(transactions, ["status"])
    transaction_id_col = find_column(transactions, ["transaction_id"])

    if not all([discount_col, price_col, quantity_col, status_col]):
        raise ValueError(
            "Required transaction columns not found. "
            f"Available: {transactions.columns.tolist()}"
        )

    discount = pd.to_numeric(transactions[discount_col], errors="coerce")
    price = pd.to_numeric(transactions[price_col], errors="coerce")
    quantity = pd.to_numeric(transactions[quantity_col], errors="coerce")

    print("\nDiscount range:", discount.min(), "to", discount.max())

    if discount.dropna().between(0, 1).all():
        print("Discount interpretation: decimal fraction (e.g. 0.25 = 25%)")
        discount_fraction = discount
    elif discount.dropna().between(0, 100).all():
        print("Discount interpretation: percentage points (e.g. 25 = 25%)")
        discount_fraction = discount / 100
    else:
        raise ValueError(
            "Discount values fall outside expected ranges. Check README."
        )

    transactions["gross_value"] = quantity * price
    transactions["discount_fraction"] = discount_fraction
    transactions["discount_amount"] = (
        transactions["gross_value"] * discount_fraction
    )
    transactions["estimated_net_value"] = (
        transactions["gross_value"] - transactions["discount_amount"]
    )

    print("Total gross transaction value:", round(
        transactions["gross_value"].sum(), 2
    ))
    print("Estimated discount amount:", round(
        transactions["discount_amount"].sum(), 2
    ))
    print("Estimated net transaction value:", round(
        transactions["estimated_net_value"].sum(), 2
    ))

    # -------------------------------
    # 2. Status-based value summary
    # -------------------------------
    status_summary = (
        transactions.groupby(status_col, dropna=False)
        .agg(
            transaction_count=(status_col, "size"),
            gross_value=("gross_value", "sum"),
            discount_amount=("discount_amount", "sum"),
            estimated_net_value=("estimated_net_value", "sum"),
        )
        .reset_index()
    )

    status_summary["transaction_share_pct"] = (
        status_summary["transaction_count"]
        / max(len(transactions), 1) * 100
    ).round(2)

    print("\nValue by transaction status:")
    print(status_summary.to_string(index=False))
    save_report(status_summary, "corrected_value_by_status.csv")

    # -------------------------------
    # 3. Product cost/price validation
    # -------------------------------
    product_id_col = find_column(products, ["product_id", "productid"])
    transaction_product_col = find_column(
        transactions, ["product_id", "productid"]
    )
    cost_col = find_column(
        products, ["unit_cost", "cost", "cost_price", "purchase_cost"]
    )
    catalog_price_col = find_column(
        products, ["list_price", "unit_price", "selling_price", "price"]
    )

    if product_id_col and transaction_product_col:
        if products[product_id_col].duplicated().any():
            print(
                "\nWARNING: Product IDs are duplicated in the catalog. "
                "Resolve product grain before joining."
            )
        else:
            product_info = products.copy()

            if cost_col:
                product_info[cost_col] = pd.to_numeric(
                    product_info[cost_col], errors="coerce"
                )
            if catalog_price_col:
                product_info[catalog_price_col] = pd.to_numeric(
                    product_info[catalog_price_col], errors="coerce"
                )

            if cost_col and catalog_price_col:
                product_info["catalog_price_minus_cost"] = (
                    product_info[catalog_price_col] - product_info[cost_col]
                )

                suspicious = product_info[
                    product_info["catalog_price_minus_cost"] < 0
                ].copy()

                print("\nProducts with catalog price below recorded cost:",
                      len(suspicious))
                print(
                    "Caution: this is a data anomaly candidate, not proof "
                    "of a realized loss."
                )
                save_report(suspicious, "product_price_cost_anomalies.csv")

            # Join product attributes to transactions for analysis.
            # Only join when the product catalog has unique product IDs.
            columns_to_add = [product_id_col]
            for col in [cost_col, catalog_price_col]:
                if col and col not in columns_to_add:
                    columns_to_add.append(col)

            merged = transactions.merge(
                product_info[columns_to_add],
                left_on=transaction_product_col,
                right_on=product_id_col,
                how="left",
                validate="many_to_one",
                indicator=True,
                suffixes=("", "_catalog")
            )

            unmatched = merged[merged["_merge"] == "left_only"]
            print("\nTransactions with no matching product:", len(unmatched))
            save_report(unmatched, "unmatched_product_transactions.csv")

            if cost_col:
                merged["estimated_unit_cost"] = pd.to_numeric(
                    merged[cost_col], errors="coerce"
                )
                merged["estimated_product_cost"] = (
                    merged["estimated_unit_cost"] * merged[quantity_col]
                )
                merged["estimated_value_minus_cost"] = (
                    merged["estimated_net_value"]
                    - merged["estimated_product_cost"]
                )

                # This is a proxy, not audited profit:
                # fees, shipping, returns, and overhead are not included.
                save_report(merged, "transaction_product_analysis.csv")
    else:
        print(
            "\nProduct join skipped: could not identify product ID columns."
        )

    # -------------------------------
    # 4. Inventory data checks
    # -------------------------------
    print("\nInventory columns:", inventory.columns.tolist())

    stock_col = find_column(
        inventory, ["stock_on_hand", "stock_quantity", "quantity", "stock", "inventory_level"]
    )
    reorder_col = find_column(
        inventory, ["reorder_threshold", "reorder_level", "reorder_point", "minimum_stock"]
    )

    if stock_col:
        inventory[stock_col] = pd.to_numeric(
            inventory[stock_col], errors="coerce"
        )

        print("Rows with missing/unparseable stock:",
              int(inventory[stock_col].isna().sum()))
        print("Rows with negative stock:",
              int((inventory[stock_col] < 0).sum()))

        if reorder_col:
            inventory[reorder_col] = pd.to_numeric(
                inventory[reorder_col], errors="coerce"
            )
            low_stock = inventory[
                inventory[stock_col].notna()
                & inventory[reorder_col].notna()
                & (inventory[stock_col] < inventory[reorder_col])
            ].copy()

            print("Inventory rows below reorder level:", len(low_stock))
            save_report(low_stock, "low_stock_candidates.csv")
        else:
            print("No recognized reorder threshold column found.")
    else:
        print("Could not identify a stock quantity column.")

    # -------------------------------
    # 5. Targeted Leak Candidate Reports
    # -------------------------------
    print("\n--- Generating Targeted Investigation Evidence ---")

    # 5A. High-return products (>=15% return rate, min 40 orders)
    pr_agg = transactions.groupby(transaction_product_col).agg(
        total_orders=(transaction_id_col, "count"),
        returned_orders=(status_col, lambda s: (s.str.lower() == "returned").sum()),
        cancelled_orders=(status_col, lambda s: (s.str.lower() == "cancelled").sum()),
        returned_net_value=("estimated_net_value", lambda v: v[transactions.loc[v.index, status_col].str.lower() == "returned"].sum()),
    )
    pr_agg["return_rate"] = (pr_agg["returned_orders"] / pr_agg["total_orders"]).round(4)
    high_return_products = pr_agg[(pr_agg["return_rate"] >= 0.15) & (pr_agg["total_orders"] >= 40)].sort_values("return_rate", ascending=False).reset_index()
    save_report(high_return_products, "leak_high_return_products.csv")

    # 5B. Chronic repeat-leak customers (>=4 cancelled or returned transactions)
    customer_id_col = find_column(transactions, ["customer_id", "customerid"])
    if customer_id_col:
        cu_agg = transactions.groupby(customer_id_col).agg(
            total_orders=(transaction_id_col, "count"),
            cancelled_orders=(status_col, lambda s: (s.str.lower() == "cancelled").sum()),
            returned_orders=(status_col, lambda s: (s.str.lower() == "returned").sum()),
            leak_net_exposure=("estimated_net_value", lambda v: v[transactions.loc[v.index, status_col].str.lower().isin(["cancelled", "returned"])].sum()),
        )
        cu_agg["leak_orders_count"] = cu_agg["cancelled_orders"] + cu_agg["returned_orders"]
        repeat_leak_customers = cu_agg[cu_agg["leak_orders_count"] >= 4].sort_values("leak_orders_count", ascending=False).reset_index()
        save_report(repeat_leak_customers, "leak_repeat_customers.csv")

    # 5C. Maximum discount transactions (25% discount)
    max_disc_txns = transactions[transactions[discount_col] == 0.25].copy()
    save_report(max_disc_txns, "leak_max_discount_transactions.csv")

    # 5D. Critical inventory stockout vulnerability (below reorder AND supplier delay >= 14 days)
    delay_col = find_column(inventory, ["supplier_delay_days", "supplier_lead_days", "delay_days"])
    if stock_col and reorder_col and delay_col:
        critical_inventory = inventory[
            (inventory[stock_col] < inventory[reorder_col])
            & (pd.to_numeric(inventory[delay_col], errors="coerce") >= 14)
        ].copy()
        save_report(critical_inventory, "leak_critical_inventory.csv")

    # 5E. Credit card payment cancellations
    payment_col = find_column(transactions, ["payment_method", "payment"])
    if payment_col:
        card_cancels = transactions[
            (transactions[payment_col].str.lower() == "card")
            & (transactions[status_col].str.lower() == "cancelled")
        ].copy()
        save_report(card_cancels, "leak_card_cancellations.csv")

    # Save corrected transaction calculations.
    save_report(transactions, "transactions_with_corrected_discounts.csv")

    print("\nFinished. Review each report and its caveats.")
    print("No candidate is automatically labelled a confirmed loss.")


if __name__ == "__main__":
    main()