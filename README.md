# 🔎 MarginTracer AI
> **"Find the leak. Prove the signal. Prioritize the fix."**  
> *DATATHON-2K26 — Track 4: The Money Leak*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58%2B-FF4B4B.svg)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Persistent%20ACID-003B57.svg)](https://sqlite.org/)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive-3F4F75.svg)](https://plotly.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Executive Summary

**MarginTracer AI** is an evidence-first financial investigation and case-management engine built to uncover operational friction, margin erosion, and revenue leakage in retail and e-commerce transactions. 

Rather than relying on black-box assumptions or fabricating ungrounded fraud claims, MarginTracer AI enforces:
1. **Mathematical Integrity**: Validated revenue and discount formulas with zero double-counting.
2. **Explainable Statistical Rules**: Transparent detection thresholds with sample size disclosures.
3. **Tri-Scenario Financial Modeling**: Conservative, Base, and Optimistic recovery simulations factoring in investigation and remediation costs.
4. **Persistent Case Management (Phase 5)**: ACID-compliant SQLite tracking linking detected signals to owners, priorities, lifecycle states (`Open`, `Investigating`, `Resolved`, `Dismissed`), and resolution justifications.
5. **Empirical Machine Learning Evaluation**: Transparent benchmarks exposing generalization gaps and false-positive limitations on minority leak classes.

---

## 📊 Dataset Universe & Verified Baseline

Profiling across all 18,000 transactions ($10.16M gross volume):

$$\text{Gross Value} = \text{Quantity} \times \text{Unit Price}$$
$$\text{Discount Amount} = \text{Gross Value} \times \text{Discount Fraction}$$
$$\text{Estimated Net Value} = \text{Gross Value} - \text{Discount Amount}$$

| Status | Transactions | Share (%) | Gross Value ($) | Discount Amount ($) | Estimated Net Value ($) | Business Context |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Completed** | 13,962 | 77.57% | $7,907,358.01 | $605,659.76 | $7,301,698.25 | Realized sales revenue |
| **Cancelled** | 1,689 | 9.38% | $931,263.57 | $69,413.96 | $861,849.61 | Uncaptured checkout drop-offs |
| **Returned** | 1,431 | 7.95% | $819,650.10 | $59,327.80 | $760,322.30 | Refund & inventory restock exposure |
| **Pending** | 918 | 5.10% | $505,952.08 | $39,019.14 | $466,932.94 | In-flight / unconfirmed orders |
| **Total** | **18,000** | **100.0%** | **$10,164,223.76** | **$773,420.66** | **$9,390,803.10** | Complete dataset universe |

---

## 🕵️ 6 Core Leak Investigation Findings

| Finding | Category | Severity | Affected Scope | Defensible Exposure | Recommended Operational Action |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **1. Chronic High-Return SKUs** | Product Quality | **High** | 5 Products (54 returns) | **$37,310.88** | Audit dimension charts and inspect vendor return SLAs for chargebacks. |
| **2. Repeat Leak Customers** | Policy Abuse | **Medium** | 53 Accounts (228 leak orders) | **$116,669.91** | Cross-reference with Customer LTV; introduce soft checkout confirmation. |
| **3. 25% Discount Outliers** | Margin Erosion | **Medium** | 912 Orders (713 completed) | **$102,195.66** | Audit coupon authorization logs to verify promo code compliance. |
| **4. Catalog Price < Cost** | Catalog Master Data | **Review** | 76 SKUs (5,315 orders) | Synthetic Artifact | Catalog model artifact per README; profile supplier ingestion pipeline. |
| **5. Critical Inventory Delays** | Supply Chain | **High** | 229 SKUs ($\text{delay} \ge 14\text{d}$) | Stockout Risk | Expedite emergency POs with priority freight; enforce supplier penalties. |
| **6. Card Payment Friction** | Checkout / Gateway | **Low** | 360 Cancelled Card Orders | **$176,726.81** | Review payment gateway response codes (3DS timeouts, decline codes). |

> ⚠️ **Overlap Safeguard:** Across the individual findings, **54 transactions overlap** (e.g. Card cancellations placed by repeat-leak accounts). MarginTracer AI strictly enforces transaction-ID deduplication to prevent double-counting corporate exposure.

---

## 📋 Phase 5: Persistent Investigation Case Management

MarginTracer AI includes a full lifecycle investigation tracker integrated directly into the dashboard:
- **1-Click Case Creation**: Pre-populate formal cases directly from detected findings in Tab 2 or Scenario Simulations in Tab 6.
- **Stable Unique Identifiers**: Collision-free IDs formatted as `CASE-YYYYMMDD-XXXXX`.
- **Persistent Local SQLite Database**: Cases stored safely in `reports/margintracer_cases.db` with ACID guarantees across app restarts.
- **Duplicate Prevention**: Guardrails prevent creating duplicate open cases for the same signal.
- **Lifecycle Management**: Track transitions from `Open` $\rightarrow$ `Investigating` $\rightarrow$ `Resolved` or `Dismissed` with mandatory root-cause justification.
- **Audit Logging**: Every update appends dated notes with user attribution.
- **Multi-field Filtering & CSV Export**: Filter by Status, Priority, Owner, and Category, with one-click CSV export.

---

## 🤖 Empirical Machine Learning Evaluation

Evaluated using an **80% Train / 20% Test chronological holdout**:

| Model | Training Accuracy | Testing Accuracy | Testing Macro-F1 | Evaluation Finding |
| :--- | :---: | :---: | :---: | :--- |
| **Baseline (Most Frequent)** | **81.70%** | **81.88%** | 0.3001 | Achieves high accuracy simply by predicting majority class (`Completed`). |
| **Random Forest** | 79.80% | 62.36% | **0.3357** | Exhibits ~90% false-positive rate on minority leak classes. |
| **Logistic Regression** | 63.96% | 47.64% | 0.2942 | Severely underperforms dummy baseline. |

*MarginTracer AI reports these limitations transparently, advising leadership to use predictive models as advisory triage signals rather than automated decision-makers.*

---

## 🚀 Quickstart & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/viswanath006/MarginTrace-AI.git
cd MarginTrace-AI
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Run Automated Verification Suite
```bash
python test_phase5_case_management.py
```

### 4. Launch the Dashboard
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 📂 Project Architecture

```
MarginTrace-AI/
├── app.py                            # Unified Streamlit Dashboard (8 unified tabs)
├── case_manager.py                   # Persistent SQLite Case Management Data Layer (Phase 5)
├── test_phase5_case_management.py    # Automated Verification Suite for Case Management
├── business_analysis.py              # Revenue, discount & status aggregation engine
├── leak_detection.py                 # Algorithmic anomaly & targeted evidence generator
├── model_experiment.py               # ML benchmark (holdout, confusion matrix, metrics)
├── profile_data.py                   # Data quality, null & key integrity profiler
├── requirements.txt                  # Python dependencies
├── README.md                         # Project documentation
├── transactions.csv                  # 18,000 transactions dataset
├── products.csv                      # 250 products catalog
├── customers.csv                     # 3,000 customer accounts
├── inventory.csv                     # 5,000 inventory records
├── campaigns.csv                     # 1,200 marketing campaign records
└── reports/                          # Verified reports, SQLite database & evidence packages
    ├── margintracer_cases.db         # Persistent SQLite database for investigation cases
    ├── data_quality_report.md
    ├── model_comparison.csv
    ├── leak_high_return_products.csv
    ├── leak_repeat_customers.csv
    ├── leak_max_discount_transactions.csv
    ├── leak_critical_inventory.csv
    └── leak_card_cancellations.csv
```

---

## 📜 License
Developed for DATATHON-2K26 (Track 4: The Money Leak). Released under the MIT License.

