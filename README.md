# 🔎 LeakLens - AI
> **"Find the leak. Prove the signal. Prioritize the fix."**  
> *DATATHON-2K26 — Track 4: The Money Leak*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58%2B-FF4B4B.svg)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Persistent%20ACID-003B57.svg)](https://sqlite.org/)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive-3F4F75.svg)](https://plotly.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-Audited%20ML-F7931E.svg)](https://scikit-learn.org/)
[![Status](https://img.shields.io/badge/Validation-10%2F10%20PASS-success.svg)](test_phase7_stabilization.py)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Executive Summary

**LeakLens - AI** is an evidence-first financial investigation and case-management engine engineered to uncover operational friction, margin erosion, and revenue leakage across retail and e-commerce transactions.

Unlike speculative tools that fabricate ungrounded fraud claims or claim unmeasured millions in phantom savings, LeakLens - AI enforces strict scientific and financial integrity:
1. **Mathematical Rigor**: Fully validated revenue, discount, and COGS calculations with zero double-counting.
2. **Transparent Detection Rules**: Sample-size disclosed heuristics ($\ge 40$ orders, $\ge 4$ incidents) with a **54-transaction overlap safeguard**.
3. **Persistent Case Management**: Native, ACID-compliant local SQLite storage (`reports/leaklens_cases.db`) tracking signals through lifecycle states (`Open`, `Investigating`, `Resolved`, `Dismissed`) with audit trails.
4. **Tri-Scenario Financial Modeling**: Conservative (10%), Base (25%), and Optimistic (50%) recovery simulations explicitly factoring in investigation and remediation expenses.
5. **Empirical ML Governance**: Honest benchmarks exposing that ML models suffer an ~90% false-alarm rate on minority leak classes, proving that predictions are **operational friction triage signals, NOT proof of fraud**.

---

## 📊 Dataset Universe & Verified Baseline

Profiling across the complete dataset of **18,000 transactions** ($10.16M gross volume):

$$\text{Gross Value} = \text{Quantity} \times \text{Unit Price}$$
$$\text{Discount Amount} = \text{Gross Value} \times \text{Discount Fraction}$$
$$\text{Estimated Net Value} = \text{Gross Value} - \text{Discount Amount}$$

| Status | Transactions | Share (%) | Gross Value ($) | Discount Amount ($) | Estimated Net Value ($) | Business Context |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Completed** | 13,962 | 77.57% | $7,907,358.01 | $605,659.76 | $7,301,698.25 | Realized customer sales revenue |
| **Cancelled** | 1,689 | 9.38% | $931,263.57 | $69,413.96 | $861,849.61 | Uncaptured checkout drop-offs & payment friction |
| **Returned** | 1,431 | 7.95% | $819,650.10 | $59,327.80 | $760,322.30 | Refund & inventory restock exposure |
| **Pending** | 918 | 5.10% | $505,952.08 | $39,019.14 | $466,932.94 | In-flight / unconfirmed orders |
| **Total** | **18,000** | **100.0%** | **$10,164,223.76** | **$773,420.66** | **$9,390,803.10** | Complete dataset universe |

---

## 🕵️ 6 Core Leak Investigation Findings

| Finding | Category | Severity | Affected Scope | Defensible Exposure | Recommended Operational Action |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **1. Chronic High-Return SKUs** | Product Quality | **High** | 5 Products (54 returns) | **$37,310.88** | Audit dimension charts, customer reviews, and supplier return SLAs. |
| **2. Repeat Leak Customers** | Policy Abuse | **Medium** | 53 Accounts (228 leak orders) | **$116,669.91** | Cross-reference with Customer LTV; introduce soft checkout confirmation. |
| **3. 25% Discount Outliers** | Margin Erosion | **Medium** | 912 Orders (713 completed) | **$102,195.66** | Audit coupon authorization logs to verify promo code compliance. |
| **4. Catalog Price < Cost** | Catalog Master Data | **Review** | 76 SKUs (5,315 orders) | Synthetic Artifact | Catalog model artifact per README; profile supplier ingestion pipeline. |
| **5. Critical Inventory Delays** | Supply Chain | **High** | 229 Records ($\text{delay} \ge 14\text{d}$) | **$25,000.00** Risk | Expedite emergency POs with priority freight; enforce supplier penalties. |
| **6. Card Payment Friction** | Checkout Gateway | **Low** | 360 Cancelled Card Orders | **$176,726.81** | Review payment gateway response codes (3DS timeouts, decline codes). |

> 🛡️ **Overlap Safeguard:** Across the individual findings, **54 transactions overlap** (e.g. Card cancellations placed by repeat-leak accounts). LeakLens - AI strictly enforces transaction-ID deduplication to prevent double-counting corporate exposure.

---

## 🏗️ System Architecture

LeakLens - AI is engineered as a modular, decoupled 6-layer architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        1. DATA INGESTION & LOADING                     │
│  locate_file() checks root './' and './data/' for 5 production CSVs    │
│  (transactions.csv, products.csv, customers.csv, inventory, campaigns) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                  2. MATHEMATICAL VALIDATION & CLEANING                 │
│  • Decimal discount normalization: 0.25 = 25% (protects 100x errors)   │
│  • Coercion with zero row loss; ZeroDivision protections               │
│  • Financial identities: Gross = Qty * Price, Net = Gross - Discount   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                    3. RULE-BASED DETECTION ENGINE                      │
│  • 6 statistical detectors with minimum sample thresholds              │
│  • Overlap detection safeguard (54 deduplicated intersection records)  │
│  • Exportable evidence packages in reports/*.csv                       │
└─────────────────┬──────────────────────────────────┬───────────────────┘
                  │                                  │
┌─────────────────▼─────────────────┐┌───────────────▼───────────────────┐
│     4. PERSISTENT CASE STORAGE    ││   5. TRI-SCENARIO SIMULATION      │
│  • SQLite (leaklens_cases.db)     ││  • Conservative (10%), Base (25%) │
│  • Collision-free IDs             ││    Optimistic (50%)               │
│  • ACID state lifecycle           ││  • Investigation & fix costs      │
│  • Audit trail & duplicate blocks ││  • Defensible ROI calculations    │
└─────────────────┬─────────────────┘└───────────────┬───────────────────┘
                  │                                  │
┌─────────────────▼──────────────────────────────────▼───────────────────┐
│                   6. EMPIRICAL ML EVALUATION & GOVERNANCE              │
│  • Chronological 80/20 holdout (3,417 test rows)                       │
│  • Baseline (81.88%) vs Random Forest (62.36%) vs LogReg (47.64%)     │
│  • 90% False-Positive rate disclosure on minority leak classes         │
│  • Predictions vs. Proof governance principle                          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                   7. STREAMLIT UNIFIED USER INTERFACE                  │
│  8 cohesive tabs with Plotly charts, multi-field filters, and export   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Dataset Placement & Supported Schema

The application automatically discovers data files in either the workspace root (`./`) or the `./data/` subdirectory via `locate_file()`:

| Dataset | Expected File | Rows | Grain | Key Columns |
| :--- | :--- | :---: | :--- | :--- |
| **Transactions** | `transactions.csv` | 18,000 | Order Item | `transaction_id`, `customer_id`, `product_id`, `quantity`, `unit_price`, `discount_pct`, `status`, `channel`, `payment_method`, `timestamp` |
| **Products** | `products.csv` | 250 | Catalog SKU | `product_id`, `product_name`, `category`, `unit_cost`, `list_price` |
| **Customers** | `customers.csv` | 3,000 | Account | `customer_id`, `customer_name`, `segment`, `signup_date` |
| **Inventory** | `inventory.csv` | 5,000 | Warehouse Stock | `inventory_record_id`, `product_id`, `stock_on_hand`, `reorder_threshold`, `supplier_delay_days` |
| **Campaigns** | `campaigns.csv` | 1,200 | Promo Campaign | `campaign_id`, `campaign_name`, `channel`, `category`, `discount_pct`, `start_date`, `end_date` |

> 📁 **Placement Flexibility:** Place all CSV files directly in `LeakLens-AI/` or in `LeakLens-AI/data/`. Both locations are automatically detected.

---

## 🚀 Setup, Dependencies & Quickstart

### Prerequisites
- Python **3.10** or higher (tested on Python 3.10, 3.11, 3.12, 3.13)
- Windows, macOS, or Linux

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/tejaswikallepalli/LeakLens-AI.git
cd LeakLens-AI

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.venv\Scripts\activate.bat
# On macOS/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*Dependencies are 100% local and lightweight:*
- `streamlit>=1.30.0` (UI framework)
- `pandas>=2.0.0` (data manipulation)
- `numpy>=1.24.0` (numerical operations)
- `plotly>=5.18.0` (interactive visualizations)
- `scikit-learn>=1.3.0` (ML benchmarking)
- `sqlite3` (built into Python standard library)

### 3. Run Automated Verification Suites
Execute the automated test suites to verify data integrity, case management, ML pipelines, and full system stabilization:
```bash
# Verify Phase 5: SQLite Case Management & Persistence
python test_phase5_case_management.py

# Verify Phase 6: Empirical ML Evaluation & Governance
python test_phase6_ml_insights.py

# Verify Phase 7: Complete End-to-End Validation (10/10 PASS)
python test_phase7_stabilization.py
```

### 4. Launch the Live Application
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 🧭 Application Navigation (8 Unified Tabs)

LeakLens - AI integrates the entire financial investigation lifecycle into 8 purpose-built tabs:

1. **`📊 Executive Overview` (Tab 1)**:
   - High-level KPI cards: Gross Volume, Discounts Applied, Estimated Net Volume, Transaction Count.
   - Status distribution visualizer: Completed, Cancelled, Returned, and Pending shares.
   - Daily volume time-series and discount depth charts.

2. **`🕵️ Leak Investigation Engine` (Tab 2)**:
   - Interactive investigation cards for all 6 core findings.
   - Expandable data evidence tables with one-click CSV export.
   - **54-Transaction Overlap Safeguard Banner** preventing double-counted exposure.
   - **In-place Case Creation Form**: Convert any finding into an active investigation case instantly.

3. **`📋 Case Management Workflow` (Tab 3)**:
   - Live SQLite-backed case ledger (`reports/leaklens_cases.db`).
   - Summary statistics: Total Cases, Active Exposure, Status counts (`Open`, `Investigating`, `Resolved`, `Dismissed`).
   - Multi-field filtering (by Status, Priority, Category, Owner) and full CSV ledger export.
   - In-app status updater with mandatory root-cause justification notes.

4. **`🔎 Transaction Explorer` (Tab 4)**:
   - Searchable transaction ledger with instant lookup by Transaction ID, Customer ID, or Product ID.
   - Status quick-filters and configurable pagination.
   - Detailed single-transaction audit modal showing applied discount, COGS, and estimated gross margin.

5. **`📈 Channel & Status Analytics` (Tab 5)**:
   - Performance breakdown across sales channels (Web, Mobile App, Store, Marketplace).
   - Payment method friction analysis (Card, UPI, Cash on Delivery, Net Banking).
   - Cancellation and return rate cross-tabulations.

6. **`🧮 Exposure & Scenario Calculator` (Tab 6)**:
   - Interactive financial recovery simulator with real-time sliders.
   - Pre-populate exposure from detected findings or test hypothetical corporate amounts.
   - Realistic cost inputs: Analyst Investigation Cost ($) + Operational Remediation Cost ($).
   - **Tri-Scenario Output**: Side-by-side Conservative (10%), Base (25%), and Optimistic (50%) net benefit and defensible ROI.
   - Direct integration: Register a scenario directly into the SQLite Case Management tracker.

7. **`🤖 ML Insights & Evaluation` (Tab 7)**:
   - Chronological 80/20 holdout evaluation (3,417 test records).
   - Benchmark comparison: Dummy Baseline (81.88%) vs Random Forest (62.36%) vs Logistic Regression (47.64%).
   - Interactive 3x3 Confusion Matrices.
   - Per-Class Precision/Recall metrics exposing the **~90% false-positive rate** on minority leak classes.
   - Ethical governance disclosure: Why predictions are triage signals, not proof of fraud.

8. **`🛡️ Data Quality & Verification` (Tab 8)**:
   - Comprehensive data profiling across all 5 CSV datasets.
   - Null rate analysis, type integrity, and foreign key orphan checks.
   - Full rendered view of `reports/data_quality_report.md`.

---

## ⚠️ Limitations, Risks & Governance Disclosures

In compliance with DATATHON-2K26 standards, LeakLens - AI strictly documents its boundaries:

1. **Synthetic / Independently Generated Catalog Margins:**
   - As documented in `README.txt`, catalog list prices and unit costs were generated independently, creating **76 products where list price is less than unit cost** ($1.21M theoretical discrepancy).
   - **Governance stance:** We disclose this transparently as a synthetic modeling artifact. We explicitly advise leadership **NOT** to treat this as rogue employee discounting or employee fraud.

2. **Uncertainty in Estimated Financial Exposure:**
   - Exposure values represent recorded gross volume or discount concessions at risk, **NOT realized cash losses**.
   - Net cash recovery depends on customer re-order behavior, supplier salvage agreements, and restitution SLAs.

3. **Missing Direct Campaign Attribution:**
   - While `campaigns.csv` provides 1,200 marketing records across dates, channels, and categories, `transactions.csv` lacks a direct `campaign_id` foreign key.
   - **Governance stance:** We refuse to hallucinate deterministic marketing campaign attribution where the underlying transactional grain does not support it.

4. **Predictions vs. Proof (The ML Governance Principle):**
   - High machine learning anomaly scores indicate **operational friction** (e.g., checkout hesitation, sizing uncertainty, payment gateway timeouts).
   - **They are NEVER proof of malicious fraud or embezzlement.**
   - Given the ~90% false-positive rate on minority classes, autonomous account blocking would penalize 9 innocent customers for every 1 true leak. Models must serve as advisory triage filters for human investigators.

---

## 🛠️ Troubleshooting Guide

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **Port 8501 in use** | Another Streamlit or web service is running on port 8501. | Run with an alternative port: `streamlit run app.py --server.port 8502` |
| **Missing CSV Error Banner** | `transactions.csv` or other datasets not found in current directory. | Verify files are located in root `./` or in `./data/`. Check `dir *.csv` in terminal. |
| **UnicodeEncodeError on Windows** | Terminal encoding defaults to CP1252 instead of UTF-8 when printing unicode icons. | All test scripts use safe ASCII output tags (`[PASS]`, `[FAIL]`). Run scripts normally. |
| **Database Lock / Busy** | SQLite locked by another active process. | The case manager includes a 15-second busy timeout. Restart the app if a lock persists. |
| **Streamlit Cache Stale** | In-memory cached dataset needs refreshing. | Press `C` in the Streamlit browser window to clear cache, or click `R` to rerun. |

---

## ✅ Final Startup & Local Verification Checklist

Use this checklist before presenting to ensure 100% operational readiness:

- [x] **Zero External Cloud Services**: Runs entirely on localhost; requires zero internet connection after pip install.
- [x] **Zero API Keys or Paid Tokens**: No OpenAI, Anthropic, or Gemini API keys needed.
- [x] **ACID Storage Verified**: SQLite database (`reports/leaklens_cases.db`) persists across restarts.
- [x] **All 5 Datasets Present**: 18,000 transactions, 250 products, 3,000 customers, 5,000 inventory, 1,200 campaigns.
- [x] **Phase 5 Verification Passed**: `python test_phase5_case_management.py` $\rightarrow$ 9/9 PASS.
- [x] **Phase 6 Verification Passed**: `python test_phase6_ml_insights.py` $\rightarrow$ 7/7 PASS.
- [x] **Phase 7 Verification Passed**: `python test_phase7_stabilization.py` $\rightarrow$ 10/10 PASS.
- [x] **Live Server HTTP 200 OK**: Responding on `http://localhost:8501`.

---

## 📚 Datathon Presentation Resources

- 🎙️ **Live Speaker Script & Walkthrough:** [`DEMO_WALKTHROUGH.md`](DEMO_WALKTHROUGH.md) (Complete 5-7 minute timed demonstration guide).
- 📊 **Official PPT Content Outline:** [`PRESENTATION_OUTLINE.md`](PRESENTATION_OUTLINE.md) (Aligned to the DATATHON Round 1 Idea PPT template).
- 🛡️ **Data Quality Audit Report:** [`reports/data_quality_report.md`](reports/data_quality_report.md).

---

## 📜 License & Credits

Developed for **DATATHON-2K26** (Track 4: The Money Leak).  
Released under the [MIT License](LICENSE).
