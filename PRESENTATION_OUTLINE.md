# 📊 LeakLens - AI — DATATHON Round 1 Presentation Outline
> **Track 4: The Money Leak**  
> **Official DATATHON Round 1 Idea PPT Aligned Content Outline**

---

### Slide 1: Title & Team Overview
- **Project Name:** LeakLens - AI
- **Tagline:** *"Find the leak. Prove the signal. Prioritize the fix."*
- **Competition Track:** DATATHON-2K26 — Track 4: The Money Leak
- **Team Name / Presenters:** Data Analytics & Investigation Taskforce
- **Date:** October 2026
- **Key Visual:** System architecture badge showing *"Verified Evidence Engine — 100% Local & ACID Compliant"*

---

### Slide 2: Problem Statement — The $10M Revenue Leak Challenge
- **Industry Context:** Retail and e-commerce enterprises hemorrhage margins through unexamined friction: chronic return loops, promotion abuse, checkout drops, and supplier delays.
- **The Core Dilemma:**
  - Standard BI dashboards show aggregate sales but fail to connect transaction drops to root causes.
  - Naive AI approaches fabricate ungrounded fraud allegations, resulting in customer churn and wasted operational audits.
- **The Dataset Universe (Verified Baseline):**
  - **18,000 transactions** across 2025 totaling **$10,164,223.76 in gross value**.
  - **$773,420.66** in promotional discounts applied (verified decimal scale $0.00$ to $0.25$).
  - **$9,390,803.10** in estimated net volume.
  - **17.3% non-completed volume:** 1,689 Cancelled ($861.8K net) and 1,431 Returned ($760.3K net).
- **Key Takeaway:** Uncaptured order value is operational friction, not proof of financial fraud.

---

### Slide 3: Proposed Solution — Evidence-First Financial Intelligence
- **Our Approach:** LeakLens - AI is an evidence-first investigation and case-management engine combining mathematical verification, transparent statistical rules, tri-scenario financial modeling, and ML governance.
- **Four Core Tenets:**
  1. **Zero Double-Counting:** Strict mathematical validation of gross, discount, net, and COGS with automated transaction deduplication.
  2. **Sample-Size Disclosed Heuristics:** Detection rules enforce statistical significance thresholds ($\ge 40$ orders, $\ge 4$ incidents) to prevent chasing noise.
  3. **Operational Follow-Through:** Native, ACID-compliant SQLite case tracker linking signals to owners, priorities, and audit trails.
  4. **Empirical ML Transparency:** Rigorous disclosures exposing model generalization gaps and false-positive limits.

---

### Slide 4: System Architecture & End-to-End Workflow
```
[ 5 Production CSV Datasets ]
(transactions, products, customers, inventory, campaigns)
               │
               ▼
[ 1. Ingestion & Validation Layer ]
• Flexible path discovery (./ or ./data/)
• Decimal discount normalization (0.0 - 0.25)
• Type coercion & null protection (zero dropped rows)
               │
               ▼
[ 2. Algorithmic Detection Engine ]
• 6 Targeted Candidate Rules
• 54-Transaction Overlap Deduplication Safeguard
               │
               ├──────────────────────────────────┐
               ▼                                  ▼
[ 3. Persistent Case Management ]     [ 4. Tri-Scenario Simulator ]
• SQLite DB (reports/leaklens_cases.db) • Conservative / Base / Optimistic
• Collision-Free IDs (CASE-YYYYMMDD-XXXXX)  • Remediation & Investigation Costs
• Duplicate Prevention Guardrails          • Defensible ROI Multipliers
               │                                  │
               └──────────────────────────────────┘
               │
               ▼
[ 5. Empirical Machine Learning & Governance ]
• Chronological 80/20 Holdout Split (3,417 test rows)
• Baseline vs Random Forest vs Logistic Regression
• Per-Class Precision/Recall & False-Alarm Disclosures
               │
               ▼
[ 6. Streamlit Interactive Dashboard (8 Unified Tabs) ]
```

---

### Slide 5: Core Technology Stack
- **Data Engineering:** Python 3.10+, Pandas 2.3+, NumPy 2.4+
- **Interactive UI & Visualization:** Streamlit 1.58+, Plotly 6.8+
- **Persistence & Storage:** SQLite3 (Python standard library, zero server configuration, ACID-compliant)
- **Machine Learning & Benchmarking:** Scikit-Learn 1.8+ (Stratified/Chronological Holdouts, Confusion Matrices)
- **Zero Cloud Footprint:** 100% local execution, zero paid APIs, zero external secrets or tokens required.

---

### Slide 6: Verified Empirical Evidence — 6 Core Investigation Findings

| Finding | Category | Affected Scope | Defensible Exposure | Verified Root Cause / Action |
| :--- | :--- | :---: | :---: | :--- |
| **1. Chronic Return SKUs** | Product Quality | 5 SKUs (54 returns) | **$37,310.88** | Return rates $\ge 15\%$ (PR0208 at 20%). Audit dimension charts & supplier SLAs. |
| **2. Repeat Leak Customers** | Policy Abuse | 53 Accounts (228 orders) | **$116,669.91** | Customers with $\ge 4$ cancellations/returns. Correlate with LTV; add soft checkout friction. |
| **3. Max 25% Discount Cluster** | Margin Erosion | 912 Transactions | **$102,195.66** | Ceiling discount tier ($80.5K on completed sales). Audit coupon authorization logs. |
| **4. Catalog Price < Cost** | Catalog Master Data | 76 SKUs (5,315 orders) | Synthetic Artifact | Catalog generated independently per README. Profile supplier ingestion, no fraud claims. |
| **5. Supply Chain Bottlenecks** | Inventory Risk | 229 Warehouse Records | **$25,000.00** | Stock below reorder with $\ge 14\text{d}$ delay. Expedite emergency purchase orders. |
| **6. Card Payment Friction** | Checkout Gateway | 360 Cancelled Orders | **$176,726.81** | Card cancellations at 9.93% vs 9.0% average. Audit 3DS timeouts and decline codes. |

> 🛡️ **Overlap Safeguard:** Across these findings, **54 transactions overlap** (e.g. Card cancellations placed by repeat-leak accounts). LeakLens - AI strictly deduplicates IDs to prevent double-counting corporate exposure.

---

### Slide 7: Defensible Business Impact & Tri-Scenario Financial Modeling
- **The Problem with Traditional Savings Claims:** Traditional pitches claim "100% of detected leakage will be recovered with zero cost." This is financially impossible.
- **LeakLens - AI's Tri-Scenario Modeling Formula:**
  $$\text{Net Benefit} = (\text{Exposure} \times \text{Recovery Rate}) - (\text{Investigation Cost} + \text{Remediation Cost})$$
- **Simulation Applied to Finding 1 (Chronic Return SKUs — $37,310.88 Exposure):**
  - **Conservative Scenario (10% Recovery):**
    - Gross Recovery: $3,731.09 | Audit Cost: $3,000 | Fix Cost: $5,000
    - **Net Benefit:** **`-$4,268.91`** $\rightarrow$ *Critical safeguard warning that low recoveries cannot justify heavy IT overhauls.*
  - **Base Case Scenario (25% Recovery):**
    - Gross Recovery: $9,327.72 | Audit Cost: $2,000 | Fix Cost: $3,000
    - **Net Benefit:** **`+$4,327.72`** | **ROI:** **`0.87x`**
  - **Optimistic Scenario (50% Recovery):**
    - Gross Recovery: $18,655.44 | Audit Cost: $1,500 | Fix Cost: $2,000
    - **Net Benefit:** **`+$15,155.44`** | **ROI:** **`3.03x`**
- **Actionable Decision-Making:** Gives CFOs and department heads realistic bounds before committing capital.

---

### Slide 8: Technical Limitations, Synthetic Disclosures & Ethical ML Governance
- **1. Synthetic Catalog Disclosures:**
  - As noted in `README.txt`, costs and prices were generated independently in the competition dataset, creating 76 SKUs where catalog price is lower than cost.
  - Rather than claiming "$1.21M in rogue employee discounting", we responsibly disclose this as a data generation artifact.
- **2. Missing Campaign Attribution:**
  - `campaigns.csv` has 1,200 records, but `transactions.csv` lacks a `campaign_id` foreign key.
  - We refuse to hallucinate deterministic marketing attribution where the underlying data schema does not support it.
- **3. The Machine Learning Generalization Gap & False-Alarm Audit:**
  - Evaluated on an **80/20 chronological holdout** (3,417 test rows):
    - Baseline (Guessing Majority `Completed`): **81.88% Accuracy**
    - Random Forest: **62.36% Accuracy** (**-17.43% Generalization Gap**)
    - Logistic Regression: **47.64% Accuracy**
  - **Minority Leak Class Performance:**
    - Cancelled Precision: **10.48%** (Recall: 18.85%) $\rightarrow$ **89.5% False-Alarm Rate**
    - Returned Precision: **9.02%** (Recall: 11.11%) $\rightarrow$ **91.0% False-Alarm Rate**
- **4. Predictions vs. Proof:**
  - High model scores indicate friction/hesitation patterns, NOT illicit conduct. Autonomous blocking would penalize 9 legitimate customers for every 1 true leak.

---

### Slide 9: Live Demonstration Highlights & Roadmap
- **Live Demo Flow:**
  1. Executive Overview: $10.16M gross, $773.4K discounts, status breakdown.
  2. Leak Engine: Dissect Finding 1 ($37.3K across 5 SKUs) and verify 54-transaction overlap safeguard.
  3. Case Management: Register formal case into persistent SQLite database (`leaklens_cases.db`).
  4. Scenario Calculator: Run tri-scenario recovery simulation with real cost constraints.
  5. ML Governance: Inspect confusion matrices and per-class false-positive limits.
- **Future Roadmap:**
  - Webhook integration with ERP systems (SAP, NetSuite) for automated PO expediting.
  - Granular marketing campaign attribution if transaction UTM tracking is introduced.
  - Customer lifetime value (LTV) weighting to protect high-tier VIP accounts from automated friction.
