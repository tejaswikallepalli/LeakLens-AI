# 🎙️ LeakLens - AI — DATATHON-2K26 Live Demonstration Walkthrough

> **"Find the leak. Prove the signal. Prioritize the fix."**  
> *DATATHON-2K26 — Track 4: The Money Leak*  
> *Live Demo Guide (5 to 7 Minutes)*

---

## ⏱️ Demo Time Allocation & Structure

| Phase | Section | Time | Target Tab | Key Message |
| :---: | :--- | :---: | :--- | :--- |
| **1** | **The Business Problem** | 1.0 min | Title / Header | Differentiate real operational friction from fabricated fraud. |
| **2** | **Verified Dataset Baseline** | 1.0 min | `📊 Executive Overview` | Establish the $10.16M transaction universe and status breakdown. |
| **3** | **Evidence-Backed Finding Deep-Dive** | 1.5 min | `🕵️ Leak Investigation Engine` | Dissect Finding 1 (Chronic Return SKUs) and the overlap safeguard. |
| **4** | **Persistent Case Creation** | 1.0 min | `📋 Case Management Workflow` | Transition from detection to action with SQLite ACID persistence. |
| **5** | **Hypothetical Financial Scenario** | 1.0 min | `🧮 Exposure & Scenario Calculator` | Tri-scenario simulation factoring in real investigation costs. |
| **6** | **Empirical ML Governance Review** | 1.0 min | `🤖 ML Insights & Evaluation` | Expose the 90% false-positive rate and explain predictions vs proof. |

---

## 🎬 Step-by-Step Speaker Script & Screen Actions

### Step 1: The Business Problem (1:00)
- **Screen Action:** Open `http://localhost:8501`. Show the application header with the **`VERIFIED EVIDENCE ENGINE`** badge.
- **Speaker Script:**
  > *"Judges and fellow data practitioners, in retail and e-commerce, the single biggest drain on profitability is not sensational cyber-theft—it is systemic operational friction: chronic product returns, payment checkout drops, unchecked discount stacking, and inventory bottlenecks.  
  > Many data science solutions fall into the trap of black-box models that invent ungrounded fraud allegations or claim millions in imaginary savings. LeakLens - AI takes the opposite approach: **evidence-first, mathematically defensible, and fully auditable**. We find the leak, prove the signal, and prioritize the fix."*

---

### Step 2: Exploring Verified Dataset Insights (1:00)
- **Screen Action:** Navigate to **`📊 Executive Overview`** (Tab 1). Point out the 4 primary KPI metric cards at the top and the Gross Value by Status bar chart.
- **Key Metrics to Highlight:**
  - **Complete Transaction Universe:** 18,000 transactions across 2025.
  - **Gross Recorded Volume:** **$10,164,223.76** ($quantity \times unit\_price$).
  - **Applied Promotional Concessions:** **$773,420.66** (verified decimal discounts $0.00$ to $0.25$).
  - **Estimated Realized Volume:** **$9,390,803.10**.
  - **Status Breakdown:**
    - `Completed`: 13,962 transactions (77.57% / $7.30M net)
    - `Cancelled`: 1,689 transactions (9.38% / $861.8K net) — checkout drop-offs
    - `Returned`: 1,431 transactions (7.95% / $760.3K net) — refund & restock exposure
    - `Pending`: 918 transactions (5.10% / $466.9K net) — in-flight orders
- **Speaker Script:**
  > *"Our data pipeline validates every mathematical identity with zero double-counting. Look at the status breakdown: cancelled and returned orders represent nearly $1.62M in uncaptured net volume. But rather than treating all cancellations as fraud, LeakLens - AI isolates specific, addressable friction patterns."*

---

### Step 3: Opening One Evidence-Backed Candidate Finding (1:30)
- **Screen Action:** Switch to **`🕵️ Leak Investigation Engine`** (Tab 2). Scroll down through the 6 candidate finding cards, then stop at the **Overlap Safeguard Banner** and open **Finding 1: Chronic Product Return Outliers**.
- **Evidence Details to Highlight:**
  - **Candidate Selection:** 5 specific SKUs have return rates $\ge 15\%$ (with minimum 40 orders each):
    - `PR0208` (20.00% return rate, 10 returns, $7,025.04 net returned)
    - `PR0075` (18.00% return rate, 9 returns, $7,906.50 net returned)
    - `PR0066` (17.50% return rate, 7 returns, $5,556.60 net returned)
    - `PR0198` (15.56% return rate, 14 returns, $9,235.10 net returned)
    - `PR0138` (15.38% return rate, 14 returns, $7,587.64 net returned)
  - **Combined Exposure:** Exactly **$37,310.88** across 54 returned orders.
  - **Overlap Safeguard:** Explain the **54-transaction overlap** detected across candidate findings (e.g., credit card cancellations placed by repeat-leak accounts). LeakLens - AI deduplicates transaction IDs to prevent inflated exposure claims.
- **Speaker Script:**
  > *"Here in Tab 2, we present 6 targeted algorithmic investigations. Let's inspect Finding 1: Chronic Return Outliers. Across the 250 products in the catalog, these 5 SKUs consistently trigger return rates above 15%—more than double the baseline rate.  
  > This represents $37,310.88 in returned merchandise. Rather than assuming buyer remorse, this points directly to physical sizing discrepancies, misleading web descriptions, or supplier batch defects."*

---

### Step 4: Creating a Persistent Investigation Case (1:00)
- **Screen Action:** Within the Finding 1 card in Tab 2, expand **`📋 Create Persistent Investigation Case from Finding 1`**. Fill out the form:
  - Assignee: `Sourcing & Quality Taskforce`
  - Priority: `High`
  - Immediate Action: `Audit dimension charts and inspect vendor return SLAs for chargebacks`
  - Click **`🚀 Register Case for Finding 1`**.
  - Show the confirmation message with the generated Case ID (e.g., `CASE-20261016-XXXXX`).
  - Switch to **`📋 Case Management Workflow`** (Tab 3) and locate the newly registered case in the active ledger.
- **Speaker Script:**
  > *"Data science without operational follow-through produces shelfware. In LeakLens - AI, every finding can be converted with 1-click into an active investigation case.  
  > This case is not stored in ephemeral session state; it is committed to an ACID-compliant local SQLite database (`reports/leaklens_cases.db`). It features collision-free IDs, duplicate creation prevention, and status lifecycle tracking from Open to Investigating to Resolved with mandatory justification notes."*

---

### Step 5: Adjusting a Hypothetical Financial Scenario (1:00)
- **Screen Action:** Navigate to **`🧮 Exposure & Scenario Calculator`** (Tab 6). 
  - Select `Finding 1: Chronic Return Outliers ($37,311)` from the exposure dropdown.
  - Set the **Target Recovery Rate** slider to **`25.0%`**.
  - Review the default or custom cost inputs:
    - Investigation Cost: **`$2,000.00`** (analyst audit time)
    - Implementation Cost: **`$3,000.00`** (storefront photo/dimension overhaul)
    - Total Cost: **`$5,000.00`**
  - Highlight the calculated results:
    - **Gross Recovery:** **`$9,327.72`**
    - **Net Benefit:** **`+$4,327.72`**
    - **Defensible ROI:** **`0.87x`** (86.6% net return on cost)
  - Show the **Tri-Scenario Comparative Matrix**:
    - *Conservative (10% recovery):* Net **`-$4,268.91`** (caution: warns leadership that small recoveries cannot justify excessive remediation spending)
    - *Base Case (25% recovery):* Net **`+$4,327.72`**
    - *Optimistic (50% recovery):* Net **`+$15,155.44`** (3.03x ROI)
- **Speaker Script:**
  > *"Executives often ask: 'If we spend money fixing this, what is our return?' Tab 6 answers that rigorously. We simulate conservative, base, and optimistic outcomes while explicitly factoring in investigation and remediation costs.  
  > Notice that at a 10% recovery rate, our net benefit is negative $4,268. Our tool honestly discloses when an operational fix costs more than it recovers, preventing unprofitable company initiatives."*

---

### Step 6: Empirical Machine Learning Governance Review (1:00)
- **Screen Action:** Switch to **`🤖 ML Insights & Evaluation`** (Tab 7). 
  - Point to the **Model Benchmark Comparison Table** and the **3x3 Confusion Matrix** for Random Forest.
  - Direct the judges' attention to the **Per-Class Metrics**:
    - Baseline (Most Frequent `Completed`): **81.88% Accuracy** | Macro-F1: **0.3001**
    - Random Forest: **62.36% Accuracy** | Macro-F1: **0.3357** | **-17.43% Generalization Gap**
    - Logistic Regression: **47.64% Accuracy**
  - Highlight the **Minority Class Performance**:
    - Cancelled Precision: **10.48%** (Recall: 18.85%) $\rightarrow$ **89.5% False-Alarm Rate**
    - Returned Precision: **9.02%** (Recall: 11.11%) $\rightarrow$ **91.0% False-Alarm Rate**
- **Speaker Script:**
  > *"Finally, we present our empirical machine learning audit. In high-stakes financial environments, transparency is paramount.  
  > Notice that a naive dummy baseline predicting 'Completed' achieves 81.88% accuracy, while our Random Forest achieves 62.36%. More importantly, the Random Forest has an ~90% false-alarm rate on cancelled and returned orders.  
  > Our ethical governance takeaway is crystal clear: **predictive models on transactional data are advisory triage filters, NOT proof of fraud.** If an e-commerce platform automatically blocked shoppers flagged by this model, it would harass 9 innocent customers for every 1 true leak. LeakLens - AI preserves human oversight."*

---

## 🏁 Conclusion & Handoff (0:30)
- **Speaker Script:**
  > *"LeakLens - AI delivers a complete, end-to-end financial intelligence system: verified math, transparent rules, persistent case management, realistic financial modeling, and audited machine learning governance.  
  > The app runs 100% locally with zero cloud dependencies or external API keys. Thank you, and we welcome your questions!"*
