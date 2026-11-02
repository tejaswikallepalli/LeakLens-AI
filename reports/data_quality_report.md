# LeakLens - AI — Verified Data Quality & Foundation Report

**Track 4: The Money Leak (DATATHON-2K26)**  
**Generated Date:** 2026-10-16  
**Auditor:** Lead Engineer, LeakLens - AI  

---

## 1. Executive Summary & Provenance

This dataset is a synthetic educational dataset created for DATATHON-2K26. As documented in `README.txt`, costs, prices, transactions, inventory, and campaigns were independently generated. Consequently, synthetic discrepancies exist in margins and catalog pricing. 

**Core Evidence Principle:**  
LeakLens - AI treats anomalies as **investigation candidates**, never as confirmed theft or audited financial losses without external verification.

---

## 2. Dataset Catalog & Structural Integrity

All 5 core CSV files were profiled across row counts, schema dimensions, null values, duplicate rows, and primary key uniqueness.

| File Name | Rows | Columns | Null Cells | Duplicate Rows | Primary Key | PK Uniqueness |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| `transactions.csv` | 18,000 | 10 | 0 | 0 | `transaction_id` | 100% Unique |
| `customers.csv` | 3,000 | 5 | 0 | 0 | `customer_id` | 100% Unique |
| `products.csv` | 250 | 5 | 0 | 0 | `product_id` | 100% Unique |
| `inventory.csv` | 5,000 | 7 | 0 | 0 | `inventory_record_id` | 100% Unique |
| `campaigns.csv` | 1,200 | 8 | 0 | 0 | `campaign_id` | 100% Unique |

### Key Integrity & Foreign-Key Coverage
- **`transactions.customer_id` $\rightarrow$ `customers.customer_id`**: 18,000 / 18,000 (100.0% match, 0 orphaned transactions).
- **`transactions.product_id` $\rightarrow$ `products.product_id`**: 18,000 / 18,000 (100.0% match, 0 orphaned transactions).
- **`inventory.product_id` $\rightarrow$ `products.product_id`**: 5,000 / 5,000 (100.0% match, 0 orphaned inventory records).
- **`campaigns.csv`**: Contains macro aggregate campaigns (totaling 895,411 conversions across channels). It does **not** share transaction or customer IDs. Campaign spend cannot be joined 1:1 with transactions.

---

## 3. Financial Calculations & Verified Status Breakdown

### Discount Representation
- Column: `discount_pct` in `transactions.csv`
- Observed domain: `[0.0, 0.05, 0.10, 0.15, 0.20, 0.25]`
- **Verified Unit:** Decimal fraction ($0.20 = 20\%$).
- **Formulas:**
  $$\text{Gross Value} = \text{quantity} \times \text{unit\_price}$$
  $$\text{Discount Amount} = \text{Gross Value} \times \text{discount\_pct}$$
  $$\text{Estimated Net Value} = \text{Gross Value} - \text{Discount Amount}$$

*(Note: Prior bugs in previous scripts divided `discount_pct` by 100, which undercalculated discounts by $99\%$ and distorted net value by nearly $\$600,000$. This has been corrected.)*

### Verified Breakdown by Transaction Status

| Status | Transactions | Share (%) | Gross Value ($) | Discount Amount ($) | Estimated Net Value ($) | Business Context |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Completed** | 13,962 | 77.57% | $7,907,358.01 | $605,659.76 | $7,301,698.25 | Realized revenue |
| **Cancelled** | 1,689 | 9.38% | $931,263.57 | $69,413.96 | $861,849.61 | Uncaptured orders / churn |
| **Returned** | 1,431 | 7.95% | $819,650.10 | $59,327.80 | $760,322.30 | Refund / restock exposure |
| **Pending** | 918 | 5.10% | $505,952.08 | $39,019.14 | $466,932.94 | In-flight / unconfirmed |
| **Total** | **18,000** | **100.0%** | **$10,164,223.76** | **$773,420.66** | **$9,390,803.10** | Dataset universe |

---

## 4. Anomalies vs. Confirmed Losses

1. **Negative Product Catalog Margins (76 / 250 products, 30.4%):**
   - 76 products have `list_price < unit_cost` in `products.csv`.
   - *Assessment:* Directly flagged by README as synthetic independence artifacts. Must not be claimed as actual cash embezzlement without proof of supplier overbilling.
2. **Dynamic Transaction Pricing (11,750 / 18,000 transactions):**
   - Transacted `unit_price` differs from catalog `list_price`. Represents channel pricing or dynamic discounting.
3. **Inventory Reorder Alerts (700 / 5,000 records):**
   - 700 records have `stock_on_hand < reorder_threshold`.
   - 760 records have `stockout_flag == 1`.
   - 10 records have `stock_on_hand == 0` (no negative stock detected).
   - *Assessment:* True operational supply-chain bottleneck signals.

---

## 5. Machine Learning Evaluation & Limitations

- **Task:** 3-class classification (`Completed`, `Cancelled`, `Returned`) on pre-outcome metadata.
- **Split:** Chronological holdout (80% Train: Jan 1 – Oct 17; 20% Test: Oct 17 – Dec 31).
- **Benchmark Results:**
  - `Baseline Most Frequent` (always predict `Completed`): **Accuracy 81.88%**, Macro-F1 0.3001.
  - `Random Forest`: **Accuracy 62.36%**, Macro-F1 0.3357.
  - `Logistic Regression`: **Accuracy 47.64%**, Macro-F1 0.2942.
- **Critical Conclusion:**
  Due to strong class imbalance (81.9% Completed in test set), candidate ML models have high false positive rates (~90%) on minority leak classes. The ML model should be presented strictly with its caveats, not as a definitive autonomous decision-maker.
