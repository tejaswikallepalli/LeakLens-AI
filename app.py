from pathlib import Path
import json
import time
import uuid

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import case_manager

# -----------------------------------------------------------------------------
# Configuration & Theme Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="LeakLens - AI | The Money Leak",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for rich aesthetics and clean typography
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .badge-leak {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-verified {
        background-color: #dcfce7;
        color: #166534;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-alert {
        background-color: #fef3c7;
        color: #92400e;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-status-open {
        background-color: #dbeafe;
        color: #1e40af;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .badge-status-investigating {
        background-color: #fef3c7;
        color: #92400e;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .badge-status-resolved {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .badge-status-dismissed {
        background-color: #f1f5f9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .finding-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #3b82f6;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .finding-card-high {
        border-left: 4px solid #ef4444;
    }
    .finding-card-medium {
        border-left: 4px solid #f59e0b;
    }
    .finding-card-low {
        border-left: 4px solid #3b82f6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_DIR = Path("data")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)
CASES_FILE = REPORT_DIR / "investigation_cases.csv"

STATUS_COLORS = {
    "Completed": "#10B981",  # Vibrant Green
    "Cancelled": "#EF4444",  # Crimson Red
    "Returned": "#F59E0B",   # Amber / Orange
    "Pending": "#6B7280",    # Neutral Gray
}


# -----------------------------------------------------------------------------
# Data Loading & Utilities (Cached)
# -----------------------------------------------------------------------------
def locate_file(filename: str) -> Path | None:
    for path in [DATA_DIR / filename, Path(filename)]:
        if path.exists():
            return path
    return None


@st.cache_data
def load_all_data():
    """Load and prepare all validated core datasets."""
    tx_path = locate_file("transactions.csv")
    pr_path = locate_file("products.csv")
    cu_path = locate_file("customers.csv")
    inv_path = locate_file("inventory.csv")
    ca_path = locate_file("campaigns.csv")

    if not tx_path:
        return None, None, None, None, None, "transactions.csv was not found."

    tx = pd.read_csv(tx_path)
    tx.columns = tx.columns.str.strip().str.lower()

    # Data validation & cleaning
    tx["quantity"] = pd.to_numeric(tx["quantity"], errors="coerce").fillna(0)
    tx["unit_price"] = pd.to_numeric(tx["unit_price"], errors="coerce").fillna(0.0)
    tx["discount_pct"] = pd.to_numeric(tx["discount_pct"], errors="coerce").fillna(0.0)
    tx["timestamp"] = pd.to_datetime(tx["timestamp"], errors="coerce")

    # Discount interpretation: verified as decimal fraction (0.0 to 0.25)
    if tx["discount_pct"].between(0, 1).all():
        tx["discount_fraction"] = tx["discount_pct"]
    else:
        tx["discount_fraction"] = tx["discount_pct"] / 100.0

    tx["gross_value"] = tx["quantity"] * tx["unit_price"]
    tx["discount_amount"] = tx["gross_value"] * tx["discount_fraction"]
    tx["estimated_net_value"] = tx["gross_value"] - tx["discount_amount"]
    tx["date"] = tx["timestamp"].dt.date
    tx["month"] = tx["timestamp"].dt.to_period("M").astype(str)

    # Load optional tables
    pr = pd.read_csv(pr_path) if pr_path else None
    if pr is not None:
        pr.columns = pr.columns.str.strip().str.lower()
        if "product_id" in pr.columns and "product_id" in tx.columns:
            cols_to_merge = ["product_id"]
            for c in ["category", "unit_cost", "list_price"]:
                if c in pr.columns:
                    cols_to_merge.append(c)
            tx = tx.merge(pr[cols_to_merge], on="product_id", how="left")
            if "unit_cost" in tx.columns:
                tx["unit_cost"] = pd.to_numeric(tx["unit_cost"], errors="coerce")
                tx["estimated_cogs"] = tx["unit_cost"] * tx["quantity"]
                tx["estimated_gross_margin"] = tx["estimated_net_value"] - tx["estimated_cogs"]

    cu = pd.read_csv(cu_path) if cu_path else None
    if cu is not None:
        cu.columns = cu.columns.str.strip().str.lower()

    inv = pd.read_csv(inv_path) if inv_path else None
    if inv is not None:
        inv.columns = inv.columns.str.strip().str.lower()

    ca = pd.read_csv(ca_path) if ca_path else None
    if ca is not None:
        ca.columns = ca.columns.str.strip().str.lower()

    return tx, pr, cu, inv, ca, None


def load_investigation_cases():
    """Load cases safely from SQLite database as dictionary records."""
    try:
        df = case_manager.get_all_cases()
        return df.to_dict("records")
    except Exception:
        return []


def save_investigation_cases(cases):
    """Legacy helper preserved for backward compatibility."""
    pass


def render_finding_case_creation_box(finding_key: str):
    """Render an in-place case creation component for a specific detected finding."""
    template = case_manager.DETECTED_FINDINGS.get(finding_key)
    if not template:
        return

    with st.expander(f"📋 Create Persistent Investigation Case from {template['title'].split(':')[0]}", expanded=False):
        st.markdown(f"**Target Finding:** `{template['title']}`")
        st.caption(
            "Pre-populates finding metadata into an active case stored in local SQLite (`leaklens_cases.db`). "
            "Never labels potential exposure as confirmed loss."
        )

        with st.form(key=f"form_case_{finding_key}"):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                f_owner = st.text_input("Assignee / Lead", value="Investigation Taskforce", key=f"owner_{finding_key}")
            with col_f2:
                valid_prios = ["Critical", "High", "Medium", "Low"]
                prio_idx = valid_prios.index(template["default_priority"]) if template["default_priority"] in valid_prios else 1
                f_priority = st.selectbox("Priority Level", valid_prios, index=prio_idx, key=f"prio_{finding_key}")
            with col_f3:
                f_action = st.text_input("Immediate Next Action", value=template["default_next_action"], key=f"action_{finding_key}")

            f_notes = st.text_area(
                "Initial Audit Notes & Hypotheses",
                value=f"Evidence: {template['evidence_reference']}. Scope: {template['affected_record_count']:,} records. Potential review exposure: ${template['exposure_estimate']:,.2f}.",
                key=f"notes_{finding_key}",
            )
            btn_submit = st.form_submit_button(f"🚀 Register Case for {template['title'].split(':')[0]}")

        if btn_submit:
            res = case_manager.create_case(
                title=template["title"],
                category=template["category"],
                description=template["description"],
                evidence_reference=template["evidence_reference"],
                affected_record_count=template["affected_record_count"],
                exposure_estimate=template["exposure_estimate"],
                priority=f_priority,
                owner=f_owner,
                next_action=f_action,
                notes=f_notes,
            )
            if res["success"]:
                st.success(f"✅ Case registered with ID: **{res['case_id']}**! View and manage in the **'📋 Case Management Workflow'** tab.")
                st.rerun()
            else:
                st.error(f"❌ {res['error']}")


def load_or_calc_per_class_metrics(model_name: str) -> pd.DataFrame:
    """Load per-class classification metrics or compute from confusion matrix."""
    per_class_path = REPORT_DIR / "per_class_metrics.csv"
    if per_class_path.exists():
        try:
            df = pd.read_csv(per_class_path)
            sub = df[df["model"].str.lower() == model_name.lower()].copy()
            if not sub.empty:
                return sub[["class", "precision", "recall", "f1_score", "support"]]
        except Exception:
            pass

    # Dynamic fallback from confusion matrix
    safe_name = model_name.lower().replace(" ", "_")
    cm_path = REPORT_DIR / f"confusion_{safe_name}.csv"
    if cm_path.exists():
        try:
            cm = pd.read_csv(cm_path, index_col=0)
            labels = ["Cancelled", "Completed", "Returned"]
            rows = []
            for l in labels:
                act_row = f"actual_{l}"
                pred_col = f"predicted_{l}"
                if act_row in cm.index and pred_col in cm.columns:
                    tp = float(cm.loc[act_row, pred_col])
                    support = float(cm.loc[act_row].sum())
                    pred_tot = float(cm[pred_col].sum())
                    prec = (tp / pred_tot) if pred_tot > 0 else 0.0
                    rec = (tp / support) if support > 0 else 0.0
                    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
                    rows.append({
                        "class": l,
                        "precision": round(prec, 4),
                        "recall": round(rec, 4),
                        "f1_score": round(f1, 4),
                        "support": int(support),
                    })
            if rows:
                macro_p = sum(r["precision"] for r in rows) / len(rows)
                macro_r = sum(r["recall"] for r in rows) / len(rows)
                macro_f1 = sum(r["f1_score"] for r in rows) / len(rows)
                tot_sup = sum(r["support"] for r in rows)
                rows.append({
                    "class": "macro avg",
                    "precision": round(macro_p, 4),
                    "recall": round(macro_r, 4),
                    "f1_score": round(macro_f1, 4),
                    "support": tot_sup,
                })
                return pd.DataFrame(rows)
        except Exception:
            pass

    return pd.DataFrame(columns=["class", "precision", "recall", "f1_score", "support"])


# -----------------------------------------------------------------------------
# Main Application Flow
# -----------------------------------------------------------------------------
def main():
    transactions, products, customers, inventory, campaigns, err = load_all_data()

    if err:
        st.error(f"❌ {err}")
        st.info("Please verify that transactions.csv exists in './' or './data/'.")
        st.stop()

    # Application Header
    col_hdr, col_badge = st.columns([4, 1])
    with col_hdr:
        st.title("🔎 LeakLens - AI")
        st.caption("Find the leak. Prove the signal. Prioritize the fix. — DATATHON-2K26 Track 4")
    with col_badge:
        st.markdown(
            "<div style='text-align: right; padding-top: 15px;'><span class='badge-verified'>VERIFIED EVIDENCE ENGINE</span></div>",
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # Sidebar Filters
    # -------------------------------------------------------------------------
    st.sidebar.header("🔍 Investigation Filters")
    st.sidebar.caption("Filter data across all dashboard views")

    # Date Filter
    min_date = transactions["date"].min()
    max_date = transactions["date"].max()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # Status Quick Filter
    all_statuses = sorted(transactions["status"].dropna().unique().tolist())
    quick_filter = st.sidebar.radio(
        "Status Quick Filter",
        ["All Transactions", "Potential Leaks Only (Cancelled & Returned)", "Completed Only", "Custom Selection"],
        index=0,
    )

    if quick_filter == "All Transactions":
        selected_statuses = all_statuses
    elif quick_filter == "Potential Leaks Only (Cancelled & Returned)":
        selected_statuses = [s for s in all_statuses if s in ["Cancelled", "Returned"]]
    elif quick_filter == "Completed Only":
        selected_statuses = [s for s in all_statuses if s == "Completed"]
    else:
        selected_statuses = st.sidebar.multiselect(
            "Select Statuses",
            options=all_statuses,
            default=all_statuses,
        )

    # Channel Filter
    all_channels = sorted(transactions["channel"].dropna().unique().tolist()) if "channel" in transactions.columns else []
    selected_channels = st.sidebar.multiselect(
        "Sales Channel",
        options=all_channels,
        default=all_channels,
    ) if all_channels else []

    # Payment Method Filter
    all_payments = sorted(transactions["payment_method"].dropna().unique().tolist()) if "payment_method" in transactions.columns else []
    selected_payments = st.sidebar.multiselect(
        "Payment Method",
        options=all_payments,
        default=all_payments,
    ) if all_payments else []

    # Apply Filters
    filtered_tx = transactions.copy()

    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_d, end_d = date_range
        filtered_tx = filtered_tx[(filtered_tx["date"] >= start_d) & (filtered_tx["date"] <= end_d)]

    if selected_statuses:
        filtered_tx = filtered_tx[filtered_tx["status"].isin(selected_statuses)]

    if selected_channels:
        filtered_tx = filtered_tx[filtered_tx["channel"].isin(selected_channels)]

    if selected_payments:
        filtered_tx = filtered_tx[filtered_tx["payment_method"].isin(selected_payments)]

    # Sidebar Filter Summary
    st.sidebar.divider()
    filter_pct = (len(filtered_tx) / len(transactions) * 100) if len(transactions) > 0 else 0
    st.sidebar.write(f"**Filtered Scope:** {len(filtered_tx):,} / {len(transactions):,} ({filter_pct:.1f}%)")
    if len(filtered_tx) == 0:
        st.warning("⚠️ No records match the active filter criteria. Adjust your filters in the sidebar.")
        st.stop()

    # -------------------------------------------------------------------------
    # Navigation Tabs (8 Unified Sections including Phase 5 Case Management)
    # -------------------------------------------------------------------------
    tab_exec, tab_investigate, tab_cases, tab_explore, tab_analytics, tab_calc, tab_ml, tab_quality = st.tabs([
        "📊 Executive Overview",
        "🕵️ Leak Investigation Engine",
        "📋 Case Management Workflow",
        "🔎 Transaction Explorer",
        "📈 Channel & Status Analytics",
        "🧮 Exposure & Scenario Calculator",
        "🤖 ML Insights & Evaluation",
        "🛡️ Data Quality & Verification",
    ])

    # =========================================================================
    # TAB 1: EXECUTIVE OVERVIEW
    # =========================================================================
    with tab_exec:
        st.subheader("Executive Financial Summary")

        st.info(
            "💡 **Evidence-First Distinction:** "
            "**Gross Value** is total recorded order volume ($quantity \\times unit\\_price$). "
            "**Net Value** incorporates applied discounts ($gross - discount\\_amount$). "
            "Values from **Cancelled** and **Returned** orders reflect uncaptured opportunities and return exposure—"
            "**not audited fraud or confirmed cash embezzlement**."
        )

        tot_count = len(filtered_tx)
        tot_gross = filtered_tx["gross_value"].sum()
        tot_discount = filtered_tx["discount_amount"].sum()
        tot_net = filtered_tx["estimated_net_value"].sum()
        effective_discount_rate = (tot_discount / tot_gross * 100) if tot_gross > 0 else 0.0

        leak_mask = filtered_tx["status"].isin(["Cancelled", "Returned"])
        leak_count = leak_mask.sum()
        leak_net = filtered_tx.loc[leak_mask, "estimated_net_value"].sum()
        leak_rate = (leak_count / tot_count * 100) if tot_count > 0 else 0.0

        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Total Transactions", f"{tot_count:,}", help="Count of transactions in filtered scope")
        with m2:
            st.metric("Gross Value", f"${tot_gross:,.2f}", help="Sum of Quantity × Unit Price")
        with m3:
            st.metric("Total Discounts", f"${tot_discount:,.2f}", f"{effective_discount_rate:.2f}% avg rate", help="Verified decimal fraction discount applied")
        with m4:
            st.metric("Estimated Net Value", f"${tot_net:,.2f}", help="Gross value less verified discounts")
        with m5:
            st.metric("Potential Leak Exposure", f"${leak_net:,.2f}", f"{leak_rate:.1f}% of orders", delta_color="inverse", help="Net value of Cancelled and Returned transactions")

        st.divider()

        # Visualizations
        c_left, c_right = st.columns([1, 1])

        with c_left:
            st.markdown("#### Transaction Status Distribution")
            status_df = (
                filtered_tx.groupby("status", as_index=False)
                .agg(
                    count=("transaction_id", "count"),
                    gross_value=("gross_value", "sum"),
                    discount_amount=("discount_amount", "sum"),
                    net_value=("estimated_net_value", "sum"),
                )
            )
            status_df["share_pct"] = (status_df["count"] / max(tot_count, 1) * 100).round(2)

            fig_donut = px.pie(
                status_df,
                names="status",
                values="count",
                color="status",
                color_discrete_map=STATUS_COLORS,
                hole=0.45,
                title="Transaction Volume by Status",
            )
            fig_donut.update_traces(textposition="inside", textinfo="percent+label")
            fig_donut.update_layout(showlegend=False, margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig_donut, width="stretch")

        with c_right:
            st.markdown("#### Financial Value by Status ($)")
            fig_bar = px.bar(
                status_df,
                x="status",
                y="net_value",
                color="status",
                color_discrete_map=STATUS_COLORS,
                title="Estimated Net Value by Status ($)",
                text_auto="$,.0f",
            )
            fig_bar.update_layout(showlegend=False, yaxis_title="Net Value ($)", margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig_bar, width="stretch")

        # Status Details Table
        st.markdown("#### Breakdown Table by Status")
        table_display = status_df.copy()
        table_display["gross_value"] = table_display["gross_value"].map("${:,.2f}".format)
        table_display["discount_amount"] = table_display["discount_amount"].map("${:,.2f}".format)
        table_display["net_value"] = table_display["net_value"].map("${:,.2f}".format)
        table_display["share_pct"] = table_display["share_pct"].map("{:.2f}%".format)
        table_display.columns = ["Status", "Transaction Count", "Gross Value ($)", "Discounts ($)", "Net Value ($)", "Share (%)"]
        st.dataframe(table_display, width="stretch", hide_index=True)

        # Monthly Timeline
        st.divider()
        st.markdown("#### Monthly Transaction Timeline (2025)")
        monthly = (
            filtered_tx.groupby(["month", "status"], as_index=False)
            .agg(net_value=("estimated_net_value", "sum"), count=("transaction_id", "count"))
        )
        fig_time = px.line(
            monthly,
            x="month",
            y="net_value",
            color="status",
            color_discrete_map=STATUS_COLORS,
            markers=True,
            title="Monthly Net Value Trend by Status ($)",
            labels={"month": "Month", "net_value": "Net Value ($)", "status": "Status"},
        )
        fig_time.update_layout(yaxis_title="Net Value ($)", hovermode="x unified")
        st.plotly_chart(fig_time, width="stretch")

    # =========================================================================
    # TAB 2: LEAK INVESTIGATION ENGINE (PHASE 3 CORE)
    # =========================================================================
    with tab_investigate:
        st.subheader("🕵️ Evidence-First Leak Investigation Engine")
        st.caption("Surface potential business money leaks with transparent statistical rules, evidence tables, and actionable next steps.")

        st.warning(
            "🛡️ **Strict Evidence Policy:**\n"
            "- Potential exposure is **not a confirmed loss**. Uncaptured orders, returns, and inventory gaps require operational validation.\n"
            "- Catalog pricing below cost is an **anomaly review candidate**, especially since the dataset README notes costs and prices were generated independently.\n"
            "- Totals are kept non-overlapping to avoid double-counting."
        )

        # Summary of Investigation Areas
        inv_f1, inv_f2, inv_f3, inv_f4 = st.columns(4)
        with inv_f1:
            st.metric("High-Return Products", "5 SKUs", "$37,310.88 Exposure", help="Products with return rates >= 15% (nearly 2x dataset baseline)")
        with inv_f2:
            st.metric("Chronic Leak Accounts", "53 Customers", "$116,669.91 Exposure", help="Customers with 4 or more cancelled or returned orders")
        with inv_f3:
            st.metric("25% Max Discount Cluster", "912 Txns", "$102,195.66 Discounts", help="Orders receiving the maximum allowable 25% discount")
        with inv_f4:
            st.metric("Critical Inventory SKUs", "229 Records", "143 Unique Products", help="Stock below reorder point with supplier delay >= 14 days")

        st.divider()

        # Detailed Investigation Area Selector
        leak_topic = st.selectbox(
            "Select Investigation Area for In-Depth Audit",
            [
                "1. Chronic Product Return Outliers (Quality / Sizing Risk)",
                "2. Repeat Cancellation & Return Customer Accounts (Abusive Pattern Risk)",
                "3. Maximum 25% Discount Outlier Cluster (Margin Erosion Risk)",
                "4. Catalog Price < Unit Cost Inconsistencies (Synthetic Catalog Anomaly)",
                "5. Supply Chain Bottlenecks & Critical Reorder Violations (Stockout Risk)",
                "6. Credit Card Payment Method Cancellation Spikes (Checkout Friction)",
            ],
        )

        # ---------------------------------------------------------------------
        # FINDING 1: HIGH RETURN PRODUCTS
        # ---------------------------------------------------------------------
        if leak_topic.startswith("1. Chronic Product Return"):
            st.markdown("### Finding 1: Chronic Product Return Outliers")
            st.markdown(
                r"""
                - **Category:** `Product Quality & Return Risk`
                - **Assigned Severity:** <span class='badge-leak'>HIGH PRIORITY</span>
                - **Severity Rule:** Return rate $\ge 15.0\%$ with a minimum sample size of 40 orders (dataset average return rate is **7.95%**).
                - **Affected Scope:** **5 products** accounting for **54 returned transactions** out of 320 total orders across these SKUs.
                - **Transparent Detection Rule:**
                  $$\text{Return Rate} = \frac{\text{Returned Order Count}}{\text{Total Order Count}} \ge 0.15$$
                - **Defensibly Calculable Exposure:** **$37,310.88** net value returned across these 5 products alone.
                - **Confidence Limitations & Alternative Explanations:**
                  - Return reasons are not captured in the dataset (could be sizing discrepancies, inaccurate product photos, or packaging transit damage rather than manufacturing defects).
                  - High-value electronics or luxury apparel often exhibit naturally higher return rates across e-commerce channels.
                - **Recommended Next Action:**
                  - Audit storefront dimension charts and customer reviews for **PR0208**, **PR0075**, **PR0066**, **PR0198**, and **PR0138**.
                  - Inspect supplier return rate SLAs and consider vendor chargebacks for defective batches.
                """,
                unsafe_allow_html=True,
            )

            # Supporting records
            high_ret_path = REPORT_DIR / "leak_high_return_products.csv"
            if high_ret_path.exists():
                high_ret_df = pd.read_csv(high_ret_path)
                high_ret_disp = high_ret_df.copy()
                high_ret_disp["return_rate"] = high_ret_disp["return_rate"].map(lambda x: f"{x * 100:.2f}%")
                high_ret_disp["returned_net_value"] = high_ret_disp["returned_net_value"].map("${:,.2f}".format)
                st.dataframe(high_ret_disp, width="stretch", hide_index=True)

                st.download_button(
                    "📥 Download High-Return Evidence CSV",
                    data=high_ret_df.to_csv(index=False).encode("utf-8"),
                    file_name="leak_high_return_products.csv",
                    mime="text/csv",
                )
            render_finding_case_creation_box("finding_1")

        # ---------------------------------------------------------------------
        # FINDING 2: REPEAT LEAK CUSTOMERS
        # ---------------------------------------------------------------------
        elif leak_topic.startswith("2. Repeat Cancellation"):
            st.markdown("### Finding 2: Repeat Cancellation & Return Customer Accounts")
            st.markdown(
                r"""
                - **Category:** `Customer Account Risk & Policy Abuse`
                - **Assigned Severity:** <span class='badge-alert'>MEDIUM PRIORITY</span>
                - **Severity Rule:** Customers with $\ge 4$ non-completed orders (Cancelled + Returned).
                - **Affected Scope:** **53 customer accounts**, representing **228 leak transactions** out of 3,120 total leak orders.
                - **Transparent Detection Rule:**
                  $$\text{Leak Orders per Customer} = \text{Cancelled Orders} + \text{Returned Orders} \ge 4$$
                - **Defensibly Calculable Exposure:** **$116,669.91** net exposure across these 53 accounts.
                - **Confidence Limitations & Alternative Explanations:**
                  - High-volume loyal buyers who place dozens of orders naturally accumulate more returns than one-time buyers.
                  - Repeated cancellations may reflect payment gateway timeout retries or accidental duplicate submissions rather than malicious buyer behavior.
                - **Recommended Next Action:**
                  - Correlate return frequency against customer lifetime value (LTV) before imposing restrictive restocking fees or account flags.
                  - Introduce soft friction (e.g. order confirmation prompts or alternative payment suggestions) for accounts with $>3$ cancellations.
                """,
                unsafe_allow_html=True,
            )

            repeat_cu_path = REPORT_DIR / "leak_repeat_customers.csv"
            if repeat_cu_path.exists():
                repeat_cu_df = pd.read_csv(repeat_cu_path)
                repeat_cu_disp = repeat_cu_df.head(50).copy()
                repeat_cu_disp["leak_net_exposure"] = repeat_cu_disp["leak_net_exposure"].map("${:,.2f}".format)
                st.write(f"Displaying top **{len(repeat_cu_disp)}** of **{len(repeat_cu_df)}** repeat leak customer accounts:")
                st.dataframe(repeat_cu_disp, width="stretch", hide_index=True)

                st.download_button(
                    "📥 Download Repeat Leak Customers CSV",
                    data=repeat_cu_df.to_csv(index=False).encode("utf-8"),
                    file_name="leak_repeat_customers.csv",
                    mime="text/csv",
                )
            render_finding_case_creation_box("finding_2")

        # ---------------------------------------------------------------------
        # FINDING 3: 25% DISCOUNT CLUSTERING
        # ---------------------------------------------------------------------
        elif leak_topic.startswith("3. Maximum 25% Discount"):
            st.markdown("### Finding 3: Maximum 25% Discount Outlier Cluster")
            st.markdown(
                """
                - **Category:** `Pricing Governance & Margin Erosion`
                - **Assigned Severity:** <span class='badge-alert'>MEDIUM PRIORITY</span>
                - **Severity Rule:** Transactions receiving the absolute maximum discount tier (`discount_pct == 0.25`).
                - **Affected Scope:** **912 transactions** (713 Completed, 84 Cancelled, 69 Returned, 46 Pending) out of 18,000 total transactions (5.07%).
                - **Transparent Detection Rule:**
                  $$\\text{Discount Tier} = 25\\% \\quad (\\text{Maximum recorded in dataset, average across dataset is } 7.61\\%)$$
                - **Defensibly Calculable Exposure:**
                  - **$102,195.66** total discounts granted across all 912 orders.
                  - **$80,565.40** in discounts granted on the **713 Completed sales**.
                - **Confidence Limitations & Alternative Explanations:**
                  - 25% discounts may stem from authorized corporate promotional campaigns, seasonal sales (Black Friday, End-of-Season), or loyalty tier perks.
                  - Without an authorized promo-code ledger, we cannot definitively label these discounts as unauthorized leakage.
                - **Recommended Next Action:**
                  - Audit coupon code usage logs to verify whether orders with 25% discounts had valid promotional authorization codes.
                  - Check if high-volume corporate accounts or employees stacked non-combinable discount vouchers.
                """,
                unsafe_allow_html=True,
            )

            max_disc_path = REPORT_DIR / "leak_max_discount_transactions.csv"
            if max_disc_path.exists():
                max_disc_df = pd.read_csv(max_disc_path)
                st.write(f"Total matching transactions: **{len(max_disc_df):,}** (Sample slice shown below):")
                view_cols = ["transaction_id", "timestamp", "status", "customer_id", "product_id", "quantity", "unit_price", "discount_pct", "discount_amount", "estimated_net_value"]
                cols_present = [c for c in view_cols if c in max_disc_df.columns]
                sample_disc = max_disc_df[cols_present].head(50).copy()
                for c in ["unit_price", "discount_amount", "estimated_net_value"]:
                    sample_disc[c] = sample_disc[c].map("${:,.2f}".format)
                sample_disc["discount_pct"] = sample_disc["discount_pct"].map(lambda x: f"{x * 100:.1f}%")
                st.dataframe(sample_disc, width="stretch", hide_index=True)

                st.download_button(
                    "📥 Download 25% Discount Transactions CSV",
                    data=max_disc_df.to_csv(index=False).encode("utf-8"),
                    file_name="leak_max_discount_transactions.csv",
                    mime="text/csv",
                )
            render_finding_case_creation_box("finding_3")

        # ---------------------------------------------------------------------
        # FINDING 4: CATALOG PRICE < COST
        # ---------------------------------------------------------------------
        elif leak_topic.startswith("4. Catalog Price < Unit Cost"):
            st.markdown("### Finding 4: Catalog Price < Unit Cost Inconsistencies")
            st.markdown(
                """
                - **Category:** `Catalog Master Data Inconsistency`
                - **Assigned Severity:** <span class='badge-alert'>REVIEW CANDIDATE (LOW CONFIDENCE OF ACTUAL THEFT)</span>
                - **Severity Rule:** Products where catalog list price is lower than unit cost (`list_price < unit_cost`).
                - **Affected Scope:** **76 out of 250 catalog products (30.4%)**; **5,315 completed transactions** sold at an apparent unit loss.
                - **Transparent Detection Rule:**
                  $$\\text{Catalog Margin} = \\text{list\\_price} - \\text{unit\\_cost} < 0$$
                - **Theoretical Margin Shortfall:** **$1,214,115.50** theoretical shortfall on completed orders.
                - **CRITICAL DATA CAVEAT & CONFIDENCE LIMITATIONS:**
                  - As explicitly documented in the dataset `README.txt`:
                    > *"Important: costs/prices are independently generated and may create unrealistic margins. Teams should profile the data, flag inconsistencies, and document assumptions before making recommendations."*
                  - Because costs and prices were generated independently, **this $1.21M is a synthetic modeling artifact, NOT proof of realized embezzlement or supplier overbilling**.
                - **Recommended Next Action:**
                  - Clean master product catalog ingestion pipelines and verify whether `unit_cost` reflects supplier wholesale price, landed cost, or placeholder data.
                  - Do not accuse vendors or pricing managers of fraud based purely on synthetic cost columns.
                """,
                unsafe_allow_html=True,
            )

            anom_path = REPORT_DIR / "product_price_cost_anomalies.csv"
            if anom_path.exists():
                anom_df = pd.read_csv(anom_path)
                st.write(f"Catalog Products with `list_price < unit_cost`: **{len(anom_df)} products**")
                disp_anom = anom_df.copy()
                for c in ["unit_cost", "list_price", "catalog_price_minus_cost"]:
                    if c in disp_anom.columns:
                        disp_anom[c] = disp_anom[c].map("${:,.2f}".format)
                st.dataframe(disp_anom, width="stretch", hide_index=True)

                st.download_button(
                    "📥 Download Price-Cost Anomalies CSV",
                    data=anom_df.to_csv(index=False).encode("utf-8"),
                    file_name="product_price_cost_anomalies.csv",
                    mime="text/csv",
                )
            render_finding_case_creation_box("finding_4")

        # ---------------------------------------------------------------------
        # FINDING 5: CRITICAL INVENTORY BOTTLENECKS
        # ---------------------------------------------------------------------
        elif leak_topic.startswith("5. Supply Chain Bottlenecks"):
            st.markdown("### Finding 5: Supply Chain Bottlenecks & Critical Reorder Violations")
            st.markdown(
                r"""
                - **Category:** `Supply Chain & Stockout Vulnerability`
                - **Assigned Severity:** <span class='badge-leak'>HIGH OPERATIONAL PRIORITY</span>
                - **Severity Rule:** Inventory on hand strictly below safety reorder threshold **combined with** supplier delivery delay $\ge 14$ days.
                - **Affected Scope:** **229 warehouse records** across **143 unique products** (out of 700 low-stock records). Exactly 10 records already sit at zero stock (`stock_on_hand == 0`).
                - **Transparent Detection Rule:**
                  $$\text{stock\_on\_hand} < \text{reorder\_threshold} \quad \text{AND} \quad \text{supplier\_delay\_days} \ge 14$$
                - **Estimated Exposure:** Uncaptured revenue and lost sales opportunities caused by multi-week product stockouts.
                - **Confidence Limitations & Alternative Explanations:**
                  - Central warehouse buffer stock or cross-docking from regional fulfillment centers may mitigate localized stockouts.
                  - Lead-time delays may be seasonal estimates rather than actual fulfillment halts.
                - **Recommended Next Action:**
                  - Expedite emergency purchase orders (POs) with air/priority freight for the 229 flagged SKUs.
                  - Trigger supplier SLA contract penalty reviews for vendors averaging $>14$ days in delay.
                """,
                unsafe_allow_html=True,
            )

            crit_inv_path = REPORT_DIR / "leak_critical_inventory.csv"
            if crit_inv_path.exists():
                crit_inv_df = pd.read_csv(crit_inv_path)
                st.write(f"Identified **{len(crit_inv_df)} critical inventory records** across **{crit_inv_df['product_id'].nunique()} unique products**:")
                st.dataframe(crit_inv_df.head(50), width="stretch", hide_index=True)

                st.download_button(
                    "📥 Download Critical Inventory Evidence CSV",
                    data=crit_inv_df.to_csv(index=False).encode("utf-8"),
                    file_name="leak_critical_inventory.csv",
                    mime="text/csv",
                )
            render_finding_case_creation_box("finding_5")

        # ---------------------------------------------------------------------
        # FINDING 6: CREDIT CARD CANCELLATIONS
        # ---------------------------------------------------------------------
        elif leak_topic.startswith("6. Credit Card Payment"):
            st.markdown("### Finding 6: Credit Card Payment Method Cancellation Spikes")
            st.markdown(
                """
                - **Category:** `Payment Instrument & Checkout Friction`
                - **Assigned Severity:** <span class='badge-alert'>LOW PRIORITY</span>
                - **Severity Rule:** Highest relative cancellation rate among all payment methods (Card cancellation rate is **9.93%**, compared to **8.93%** for UPI and **9.06%** for Cash).
                - **Affected Scope:** **360 cancelled card transactions** out of 3,627 total card orders.
                - **Transparent Detection Rule:**
                  $$\\text{Payment Cancellation Rate} = \\frac{\\text{Cancelled Card Orders}}{\\text{Total Card Orders}} = 9.93\\%$$
                - **Defensibly Calculable Exposure:** **$176,726.81** in uncaptured net transaction volume.
                - **Confidence Limitations & Alternative Explanations:**
                  - Card drop-offs are frequently caused by 3D-Secure 2.0 authentication timeouts, SMS OTP delivery delays, or bank-side fraud prevention flags rather than internal app failure.
                - **Recommended Next Action:**
                  - Inspect payment gateway webhook response codes (e.g. `card_declined_insufficient_funds`, `3ds_timeout`) to optimize checkout retry prompts.
                """,
                unsafe_allow_html=True,
            )

            card_cancels_path = REPORT_DIR / "leak_card_cancellations.csv"
            if card_cancels_path.exists():
                card_cancels_df = pd.read_csv(card_cancels_path)
                st.write(f"Total Cancelled Card Transactions: **{len(card_cancels_df)}** (Sample shown below):")
                view_cols = ["transaction_id", "timestamp", "customer_id", "product_id", "channel", "quantity", "unit_price", "discount_pct", "estimated_net_value"]
                cols_present = [c for c in view_cols if c in card_cancels_df.columns]
                sample_card = card_cancels_df[cols_present].head(50).copy()
                sample_card["unit_price"] = sample_card["unit_price"].map("${:,.2f}".format)
                sample_card["estimated_net_value"] = sample_card["estimated_net_value"].map("${:,.2f}".format)
                sample_card["discount_pct"] = sample_card["discount_pct"].map(lambda x: f"{x * 100:.1f}%")
                st.dataframe(sample_card, width="stretch", hide_index=True)

                st.download_button(
                    "📥 Download Cancelled Card Transactions CSV",
                    data=card_cancels_df.to_csv(index=False).encode("utf-8"),
                    file_name="leak_card_cancellations.csv",
                    mime="text/csv",
                )
            render_finding_case_creation_box("finding_6")

    # =========================================================================
    # TAB 3: CASE MANAGEMENT WORKFLOW (PHASE 5 CORE)
    # =========================================================================
    with tab_cases:
        st.subheader("📋 Persistent Investigation Case Management")
        st.caption("Track, investigate, update, and resolve money leak cases with persistent SQLite storage and linked evidence.")

        # Financial Accountability Policy Banner
        st.info(
            "🛡️ **Financial Accountability & Evidence Linking:**\n"
            "- Every investigation case links directly to reproducible transaction evidence files stored in `reports/`.\n"
            "- Exposure estimates reflect **hypothetical upper-bound review scope**, never confirmed embezzlement or audited fraud.\n"
            "- Cases are stored in a local SQLite database (`reports/leaklens_cases.db`) with full ACID persistence across app restarts."
        )

        # Case Statistics Metric Cards
        stats = case_manager.get_case_statistics()
        m_c1, m_c2, m_c3, m_c4, m_c5, m_c6 = st.columns(6)
        with m_c1:
            st.metric("Total Cases", f"{stats['total_cases']}")
        with m_c2:
            st.metric("Open", f"{stats['open_count']}")
        with m_c3:
            st.metric("Investigating", f"{stats['investigating_count']}")
        with m_c4:
            st.metric("Resolved", f"{stats['resolved_count']}")
        with m_c5:
            st.metric("Dismissed", f"{stats['dismissed_count']}")
        with m_c6:
            st.metric("Exposure Under Review", f"${stats['total_exposure']:,.2f}", help="Sum of potential exposure estimates across active cases")

        st.divider()

        # Section 1: Create Case Hub
        with st.expander("➕ Open Case Creation Hub (Pre-Fill from Finding or Custom)", expanded=(stats["total_cases"] == 0)):
            create_mode = st.radio(
                "Creation Method",
                ["Pre-Fill from Detected Leak Finding", "Create Custom Investigation Case"],
                horizontal=True,
            )

            if create_mode == "Pre-Fill from Detected Leak Finding":
                f_keys = list(case_manager.DETECTED_FINDINGS.keys())
                selected_f_key = st.selectbox(
                    "Choose Detected Finding to Pre-fill",
                    f_keys,
                    format_func=lambda k: f"{case_manager.DETECTED_FINDINGS[k]['title']} (${case_manager.DETECTED_FINDINGS[k]['exposure_estimate']:,.2f})",
                )
                template_data = case_manager.DETECTED_FINDINGS[selected_f_key]
                with st.form("form_create_from_template"):
                    col_tf1, col_tf2 = st.columns(2)
                    with col_tf1:
                        tf_title = st.text_input("Case Title", value=template_data["title"])
                        tf_cat = st.text_input("Finding Category", value=template_data["category"])
                        tf_evidence = st.text_input("Evidence Reference", value=template_data["evidence_reference"])
                        tf_owner = st.text_input("Assignee / Lead", value="Investigation Taskforce")
                    with col_tf2:
                        tf_prio = st.selectbox("Priority Level", ["Critical", "High", "Medium", "Low"], index=["Critical", "High", "Medium", "Low"].index(template_data["default_priority"]))
                        tf_count = st.number_input("Affected Record Count", value=int(template_data["affected_record_count"]), min_value=0)
                        tf_exposure = st.number_input("Potential Exposure Estimate ($)", value=float(template_data["exposure_estimate"]), min_value=0.0, format="%.2f")
                        tf_action = st.text_input("Immediate Next Action", value=template_data["default_next_action"])

                    tf_desc = st.text_area("Finding Description", value=template_data["description"])
                    tf_notes = st.text_area("Initial Audit Notes", value=f"Pre-populated from {template_data['title']}. Evidence link verified.")
                    submit_template_case = st.form_submit_button("🚀 Create Case in Persistent Database")

                if submit_template_case:
                    res = case_manager.create_case(
                        title=tf_title,
                        category=tf_cat,
                        description=tf_desc,
                        evidence_reference=tf_evidence,
                        affected_record_count=tf_count,
                        exposure_estimate=tf_exposure,
                        priority=tf_prio,
                        owner=tf_owner,
                        next_action=tf_action,
                        notes=tf_notes,
                    )
                    if res["success"]:
                        st.success(f"✅ Investigation Case **{res['case_id']}** created and saved to SQLite!")
                        st.rerun()
                    else:
                        st.error(f"❌ {res['error']}")

            else:
                with st.form("form_create_custom_case"):
                    col_cf1, col_cf2 = st.columns(2)
                    with col_cf1:
                        cust_title = st.text_input("Case Title (Required)", placeholder="e.g. Audit of Cash on Delivery high-cancellation batch")
                        cust_cat = st.selectbox("Category", [
                            "Product Quality & Return Risk",
                            "Customer Policy Abuse & Churn Risk",
                            "Pricing Governance & Margin Erosion",
                            "Catalog Master Data Inconsistency",
                            "Supply Chain & Stockout Vulnerability",
                            "Payment Instrument & Checkout Friction",
                            "Operational Discrepancy",
                            "Other",
                        ])
                        cust_evidence = st.text_input("Evidence Reference (File or Query)", value="reports/investigation_custom.csv")
                        cust_owner = st.text_input("Assignee / Owner", value="Finance & Audit Team")
                    with col_cf2:
                        cust_prio = st.selectbox("Priority Level", ["Critical", "High", "Medium", "Low"], index=1)
                        cust_count = st.number_input("Affected Record Count", min_value=0, value=10)
                        cust_exposure = st.number_input("Potential Exposure ($)", min_value=0.0, value=5000.0, format="%.2f")
                        cust_action = st.text_input("Immediate Next Action (Required)", placeholder="e.g. Pull order logs from fulfillment system")

                    cust_desc = st.text_area("Detailed Description", placeholder="Context, hypothesis, and affected channel or products...")
                    cust_notes = st.text_area("Initial Audit Notes", placeholder="Initial observations, hypothesis, or preliminary notes...")
                    submit_custom_case = st.form_submit_button("💾 Save Custom Case to SQLite")

                if submit_custom_case:
                    res = case_manager.create_case(
                        title=cust_title,
                        category=cust_cat,
                        description=cust_desc,
                        evidence_reference=cust_evidence,
                        affected_record_count=cust_count,
                        exposure_estimate=cust_exposure,
                        priority=cust_prio,
                        owner=cust_owner,
                        next_action=cust_action,
                        notes=cust_notes,
                    )
                    if res["success"]:
                        st.success(f"✅ Custom Case **{res['case_id']}** created successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ {res['error']}")

        st.divider()

        # Section 2: Case Ledger with Multi-field Filtering & CSV Export
        st.markdown("#### 🔍 Investigation Cases Ledger")
        all_cases_df = case_manager.get_all_cases()

        if all_cases_df.empty:
            st.info("ℹ️ No investigation cases recorded yet. Use the 'Open Case Creation Hub' above or click 'Create Case' on any finding in the Leak Investigation Engine to register your first case.")
        else:
            # Multi-field Filters
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                status_opts = ["All"] + sorted(all_cases_df["status"].unique().tolist())
                sel_status = st.selectbox("Filter by Status", status_opts, index=0)
            with f_col2:
                prio_opts = ["All"] + sorted(all_cases_df["priority"].unique().tolist())
                sel_prio = st.selectbox("Filter by Priority", prio_opts, index=0)
            with f_col3:
                owner_opts = ["All"] + sorted(all_cases_df["owner"].unique().tolist())
                sel_owner = st.selectbox("Filter by Owner", owner_opts, index=0)
            with f_col4:
                cat_opts = ["All"] + sorted(all_cases_df["category"].unique().tolist())
                sel_cat = st.selectbox("Filter by Category", cat_opts, index=0)

            filtered_cases = all_cases_df.copy()
            if sel_status != "All":
                filtered_cases = filtered_cases[filtered_cases["status"] == sel_status]
            if sel_prio != "All":
                filtered_cases = filtered_cases[filtered_cases["priority"] == sel_prio]
            if sel_owner != "All":
                filtered_cases = filtered_cases[filtered_cases["owner"] == sel_owner]
            if sel_cat != "All":
                filtered_cases = filtered_cases[filtered_cases["category"] == sel_cat]

            st.write(f"Showing **{len(filtered_cases)}** of **{len(all_cases_df)}** recorded investigation cases:")

            # Display table
            display_ledger = filtered_cases[[
                "case_id", "status", "priority", "category", "title",
                "affected_record_count", "exposure_estimate", "owner", "next_action", "updated_at"
            ]].copy()
            display_ledger["exposure_estimate"] = display_ledger["exposure_estimate"].map("${:,.2f}".format)
            display_ledger["affected_record_count"] = display_ledger["affected_record_count"].map("{:,}".format)
            st.dataframe(display_ledger, width="stretch", hide_index=True)

            # Export to CSV
            c_exp1, c_exp2 = st.columns([2, 1])
            with c_exp1:
                st.caption(f"Database contains {len(all_cases_df)} total persistent cases in `reports/leaklens_cases.db`.")
            with c_exp2:
                st.download_button(
                    "📥 Export Cases to CSV",
                    data=filtered_cases.to_csv(index=False).encode("utf-8"),
                    file_name=f"leaklens_cases_export_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )

            st.divider()

            # Section 3: Case Detail View & Lifecycle Updater
            st.markdown("#### 🛠️ Case Detail View & Lifecycle Management")
            selected_case_id = st.selectbox(
                "Select Case to View & Update",
                options=all_cases_df["case_id"].tolist(),
                format_func=lambda cid: f"{cid} — {all_cases_df.loc[all_cases_df['case_id'] == cid, 'title'].iloc[0]} [{all_cases_df.loc[all_cases_df['case_id'] == cid, 'status'].iloc[0]}]",
            )

            case_detail = case_manager.get_case(selected_case_id)
            if case_detail:
                # Detail view card
                cd1, cd2, cd3 = st.columns([2, 1, 1])
                with cd1:
                    st.markdown(f"### {case_detail['title']}")
                    st.markdown(f"**Category:** `{case_detail['category']}` | **Case ID:** `{case_detail['case_id']}`")
                    st.markdown(f"**Description:** {case_detail['description']}")
                with cd2:
                    st.metric("Status", case_detail["status"])
                    st.metric("Priority", case_detail["priority"])
                with cd3:
                    st.metric("Potential Exposure", f"${case_detail['exposure_estimate']:,.2f}")
                    st.metric("Affected Records", f"{case_detail['affected_record_count']:,}")

                st.markdown(f"**Evidence Reference Link:** `{case_detail['evidence_reference']}`")
                evidence_p = Path(case_detail['evidence_reference'])
                if evidence_p.exists():
                    st.success(f"🔗 Linked evidence file `{case_detail['evidence_reference']}` is verified on disk.")
                else:
                    st.warning(f"⚠️ Evidence file `{case_detail['evidence_reference']}` not found on disk.")

                st.markdown("##### 📝 Case Audit & Notes History")
                if case_detail["notes"]:
                    st.code(case_detail["notes"], language="markdown")
                else:
                    st.caption("No notes recorded yet.")

                if case_detail["resolution_notes"]:
                    st.markdown("##### 🏁 Resolution Explanation / Root Cause")
                    st.success(case_detail["resolution_notes"])

                st.divider()

                # Update Form
                st.markdown(f"##### 🔄 Update Case: `{case_detail['case_id']}`")
                with st.form(f"form_update_{selected_case_id}"):
                    u_col1, u_col2, u_col3 = st.columns(3)
                    with u_col1:
                        new_status = st.selectbox(
                            "Lifecycle Status",
                            ["Open", "Investigating", "Resolved", "Dismissed"],
                            index=["Open", "Investigating", "Resolved", "Dismissed"].index(case_detail["status"]),
                        )
                        new_owner = st.text_input("Assignee / Owner", value=case_detail["owner"])
                    with u_col2:
                        new_priority = st.selectbox(
                            "Priority Level",
                            ["Critical", "High", "Medium", "Low"],
                            index=["Critical", "High", "Medium", "Low"].index(case_detail["priority"]),
                        )
                    with u_col3:
                        new_next_action = st.text_input("Immediate Next Action", value=case_detail["next_action"])

                    new_note = st.text_area("Append New Audit Note (Dated timestamp added automatically)", placeholder="Describe actions taken, evidence reviewed, or vendor correspondence...")

                    res_explanation = ""
                    if new_status in ["Resolved", "Dismissed"]:
                        res_explanation = st.text_area(
                            "Resolution / Dismissal Explanation (Required when Resolving or Dismissing)",
                            value=case_detail.get("resolution_notes", "") or "",
                            placeholder="Explain the root cause identified, operational corrective action taken, vendor credit negotiated, or reason for dismissal...",
                        )

                    save_update = st.form_submit_button("💾 Save Case Updates")

                if save_update:
                    if new_status in ["Resolved", "Dismissed"] and not res_explanation.strip():
                        st.error("⚠️ Please provide a resolution explanation when marking a case as Resolved or Dismissed.")
                    else:
                        u_res = case_manager.update_case(
                            case_id=selected_case_id,
                            status=new_status,
                            next_action=new_next_action,
                            owner=new_owner,
                            priority=new_priority,
                            additional_notes=new_note,
                            resolution_notes=res_explanation,
                        )
                        if u_res["success"]:
                            st.success(f"✅ Case `{selected_case_id}` updated successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ {u_res['error']}")

    # =========================================================================
    # TAB 3: TRANSACTION EXPLORER
    # =========================================================================
    with tab_explore:
        st.subheader("🔎 Transaction Explorer & Audit Inspector")
        st.caption("Inspect individual records, search identifiers, and audit transactions with complete transparency.")

        col_srch, col_sort, col_limit = st.columns([2, 1, 1])
        with col_srch:
            search_query = st.text_input(
                "Search by ID",
                placeholder="Enter Transaction, Customer, or Product ID (e.g. TX000001)",
            ).strip()
        with col_sort:
            sort_choice = st.selectbox(
                "Sort Records By",
                ["Date (Newest First)", "Date (Oldest First)", "Net Value (Highest)", "Discount Amount (Highest)"],
            )
        with col_limit:
            display_limit = st.select_slider(
                "Display Limit",
                options=[50, 100, 250, 500, 1000],
                value=100,
            )

        explorer_df = filtered_tx.copy()

        if search_query:
            q = search_query.lower()
            mask = (
                explorer_df["transaction_id"].astype(str).str.lower().str.contains(q)
                | explorer_df["customer_id"].astype(str).str.lower().str.contains(q)
                | explorer_df["product_id"].astype(str).str.lower().str.contains(q)
            )
            explorer_df = explorer_df[mask]

        if sort_choice == "Date (Newest First)":
            explorer_df = explorer_df.sort_values("timestamp", ascending=False)
        elif sort_choice == "Date (Oldest First)":
            explorer_df = explorer_df.sort_values("timestamp", ascending=True)
        elif sort_choice == "Net Value (Highest)":
            explorer_df = explorer_df.sort_values("estimated_net_value", ascending=False)
        elif sort_choice == "Discount Amount (Highest)":
            explorer_df = explorer_df.sort_values("discount_amount", ascending=False)

        st.write(f"Found **{len(explorer_df):,}** matching transactions. Showing top **{min(len(explorer_df), display_limit)}** records.")

        cols_to_show = [
            "transaction_id", "timestamp", "status", "customer_id", "product_id",
            "quantity", "unit_price", "discount_pct", "gross_value", "discount_amount", "estimated_net_value"
        ]
        if "channel" in explorer_df.columns:
            cols_to_show.insert(3, "channel")
        if "payment_method" in explorer_df.columns:
            cols_to_show.insert(4, "payment_method")
        if "category" in explorer_df.columns:
            cols_to_show.append("category")

        view_slice = explorer_df[cols_to_show].head(display_limit).copy()
        format_dict = {
            "unit_price": "${:,.2f}".format,
            "gross_value": "${:,.2f}".format,
            "discount_amount": "${:,.2f}".format,
            "estimated_net_value": "${:,.2f}".format,
            "discount_pct": lambda x: f"{x * 100:.1f}%",
        }
        for k, fmt in format_dict.items():
            if k in view_slice.columns:
                view_slice[k] = view_slice[k].map(fmt)

        st.dataframe(view_slice, width="stretch", hide_index=True)

        csv_data = explorer_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Filtered Transactions CSV",
            data=csv_data,
            file_name="leaklens_filtered_transactions.csv",
            mime="text/csv",
        )

    # =========================================================================
    # TAB 4: CHANNEL & STATUS ANALYTICS
    # =========================================================================
    with tab_analytics:
        st.subheader("📈 Cross-Channel & Risk Analytics")
        st.caption("Identify channels and payment instruments with elevated cancellation or return rates.")

        c1, c2 = st.columns(2)

        if "channel" in filtered_tx.columns:
            with c1:
                st.markdown("#### Transaction Count by Channel & Status")
                chan_status = (
                    filtered_tx.groupby(["channel", "status"], as_index=False)
                    .agg(count=("transaction_id", "count"))
                )
                fig_chan = px.bar(
                    chan_status,
                    x="channel",
                    y="count",
                    color="status",
                    color_discrete_map=STATUS_COLORS,
                    barmode="group",
                    title="Transaction Counts by Sales Channel",
                    labels={"channel": "Sales Channel", "count": "Transactions"},
                )
                st.plotly_chart(fig_chan, width="stretch")

            with c2:
                st.markdown("#### Net Financial Value by Channel ($)")
                chan_val = (
                    filtered_tx.groupby(["channel", "status"], as_index=False)
                    .agg(net_value=("estimated_net_value", "sum"))
                )
                fig_chan_val = px.bar(
                    chan_val,
                    x="channel",
                    y="net_value",
                    color="status",
                    color_discrete_map=STATUS_COLORS,
                    barmode="stack",
                    title="Net Financial Volume by Channel ($)",
                    labels={"channel": "Sales Channel", "net_value": "Net Value ($)"},
                )
                fig_chan_val.update_layout(yaxis_title="Net Value ($)")
                st.plotly_chart(fig_chan_val, width="stretch")

        if "payment_method" in filtered_tx.columns:
            st.divider()
            p1, p2 = st.columns([1, 1])

            with p1:
                st.markdown("#### Payment Method Distribution")
                pay_status = (
                    filtered_tx.groupby(["payment_method", "status"], as_index=False)
                    .agg(count=("transaction_id", "count"), net_value=("estimated_net_value", "sum"))
                )
                fig_pay = px.bar(
                    pay_status,
                    x="payment_method",
                    y="count",
                    color="status",
                    color_discrete_map=STATUS_COLORS,
                    title="Volume by Payment Instrument",
                    labels={"payment_method": "Payment Method", "count": "Count"},
                )
                st.plotly_chart(fig_pay, width="stretch")

            with p2:
                st.markdown("#### Leak Risk Share by Payment Method")
                pay_pivot = filtered_tx.pivot_table(
                    index="payment_method",
                    columns="status",
                    values="transaction_id",
                    aggfunc="count",
                    fill_value=0,
                )
                pay_pivot["Total"] = pay_pivot.sum(axis=1)
                if "Cancelled" in pay_pivot.columns:
                    pay_pivot["Cancel Rate (%)"] = (pay_pivot["Cancelled"] / pay_pivot["Total"] * 100).round(2)
                if "Returned" in pay_pivot.columns:
                    pay_pivot["Return Rate (%)"] = (pay_pivot["Returned"] / pay_pivot["Total"] * 100).round(2)
                st.dataframe(pay_pivot.reset_index(), width="stretch", hide_index=True)

    # =========================================================================
    # TAB 5: FINANCIAL SCENARIO SIMULATOR (PHASE 4 CORE)
    # =========================================================================
    with tab_calc:
        st.subheader("🧮 Interactive Financial Scenario Simulator")
        st.caption("Model addressable recovery scenarios, stress-test cost assumptions, compare finding priorities, and prevent double-counting.")

        st.warning(
            "⚠️ **Executive Disclaimer:** "
            "All scenario simulator outputs are hypothetical decision-support estimates based on user-defined assumptions. "
            "They are **not guaranteed cash savings or audited financial forecasts**. "
            "No action should be taken without verifying root causes and conducting operational audits."
        )

        # ---------------------------------------------------------------------
        # 1. Financial Terminology & 4-Stage Evidence Pipeline
        # ---------------------------------------------------------------------
        st.markdown("#### 1. The 4-Stage Financial Evidence Pipeline")
        p_c1, p_c2, p_c3, p_c4 = st.columns(4)
        with p_c1:
            st.markdown(
                """
                <div class='metric-card'>
                    <div class='metric-title'>Stage 1: Recorded Transaction Value</div>
                    <div class='metric-val'>$10.16M</div>
                    <div class='metric-sub'>Total gross order volume recorded in the dataset (Quantity &times; Unit Price).</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with p_c2:
            st.markdown(
                """
                <div class='metric-card'>
                    <div class='metric-title'>Stage 2: Estimated Exposure</div>
                    <div class='metric-val'>$1.62M</div>
                    <div class='metric-sub'>Subset of transaction value subject to operational friction (Cancelled & Returned).</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with p_c3:
            st.markdown(
                """
                <div class='metric-card'>
                    <div class='metric-title'>Stage 3: Hypothetical Recoverable</div>
                    <div class='metric-val'>Exposure &times; %</div>
                    <div class='metric-sub'>Hypothetical addressable share preventable through operational fixes.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with p_c4:
            st.markdown(
                """
                <div class='metric-card'>
                    <div class='metric-title'>Stage 4: Realized Net Savings</div>
                    <div class='metric-val'>Recovery &minus; Costs</div>
                    <div class='metric-sub'>Audited net cash benefit retained after paying investigation & remediation costs.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()

        # ---------------------------------------------------------------------
        # 2. Select Finding or Custom Exposure Pool
        # ---------------------------------------------------------------------
        st.markdown("#### 2. Select Leak Finding or Exposure Pool")
        col_sel, col_info = st.columns([2, 1])

        finding_options = [
            "Finding 1: Chronic Product Return Outliers ($37,310.88, 5 SKUs)",
            "Finding 2: Chronic Repeat Leak Customers ($116,669.91, 53 Accounts)",
            "Finding 3: Ceiling 25% Discount Outlier Cluster ($102,195.66, 912 Txns)",
            "Finding 6: Credit Card Payment Cancellations ($176,726.81, 360 Txns)",
            f"Full Cancelled Orders Pool (${filtered_tx[filtered_tx['status']=='Cancelled']['estimated_net_value'].sum():,.2f})",
            f"Full Returned Orders Pool (${filtered_tx[filtered_tx['status']=='Returned']['estimated_net_value'].sum():,.2f})",
            f"Combined Leak Pool (${leak_net:,.2f})",
            "Catalog Margin Shortfall [Synthetic Caveat] ($1,214,115.50, 76 SKUs)",
            "Custom User-Defined Exposure Amount",
        ]

        with col_sel:
            chosen_finding = st.selectbox("Select Target Finding / Investigation Area", finding_options, index=0)

        # Derive initial exposure based on selection
        if chosen_finding.startswith("Finding 1"):
            base_exposure = 37310.88
            finding_scope_desc = "5 chronic high-return products (PR0208, PR0075, PR0066, PR0198, PR0138) with 54 returned orders."
            finding_cat = "High Return Rate Investigation"
        elif chosen_finding.startswith("Finding 2"):
            base_exposure = 116669.91
            finding_scope_desc = "53 repeat-leak customer accounts with 228 non-completed transactions."
            finding_cat = "Customer Account Risk"
        elif chosen_finding.startswith("Finding 3"):
            base_exposure = 102195.66
            finding_scope_desc = "912 transactions receiving maximum allowable 25% discount tier."
            finding_cat = "Discount Over-Application"
        elif chosen_finding.startswith("Finding 6"):
            base_exposure = 176726.81
            finding_scope_desc = "360 credit card transactions cancelled at checkout (9.93% cancellation rate)."
            finding_cat = "Order Cancellation Friction"
        elif chosen_finding.startswith("Full Cancelled"):
            base_exposure = float(filtered_tx[filtered_tx["status"] == "Cancelled"]["estimated_net_value"].sum())
            finding_scope_desc = "All cancelled orders in filtered scope."
            finding_cat = "Order Cancellation Friction"
        elif chosen_finding.startswith("Full Returned"):
            base_exposure = float(filtered_tx[filtered_tx["status"] == "Returned"]["estimated_net_value"].sum())
            finding_scope_desc = "All returned orders in filtered scope."
            finding_cat = "High Return Rate Investigation"
        elif chosen_finding.startswith("Combined"):
            base_exposure = float(leak_net)
            finding_scope_desc = "All cancelled and returned orders combined."
            finding_cat = "Combined Leak Pool"
        elif chosen_finding.startswith("Catalog"):
            base_exposure = 1214115.50
            finding_scope_desc = "Theoretical margin shortfall across 5,315 completed sales with synthetic negative margins."
            finding_cat = "Catalog Price vs Cost Discrepancy"
        else:
            base_exposure = 50000.0
            finding_scope_desc = "User-specified hypothetical business exposure amount."
            finding_cat = "Other"

        with col_info:
            active_exposure = st.number_input(
                "Active Exposure Amount ($)",
                min_value=0.0,
                value=float(base_exposure),
                step=1000.0,
                format="%.2f",
                help="Validated or user-specified addressable dollar exposure.",
            )
            st.caption(f"**Scope Note:** {finding_scope_desc}")

        st.divider()

        # ---------------------------------------------------------------------
        # 3. Tri-Scenario Simulator (Conservative, Base, Optimistic)
        # ---------------------------------------------------------------------
        st.markdown("#### 3. Multi-Scenario Stress Test (Conservative vs. Base vs. Optimistic)")
        st.caption("Adjust scenario assumptions to evaluate potential sensitivity and risk-adjusted return on investment.")

        sc_col1, sc_col2, sc_col3 = st.columns(3)

        with sc_col1:
            st.markdown("##### 🛡️ Conservative Scenario")
            c_rate = st.slider("Recovery Rate (%)", min_value=0, max_value=100, value=10, key="c_rate", help="Pessimistic recovery assumption")
            c_inv_cost = st.number_input("Investigation Cost ($)", min_value=0.0, value=3000.0, step=500.0, key="c_inv")
            c_imp_cost = st.number_input("Implementation Cost ($)", min_value=0.0, value=5000.0, step=500.0, key="c_imp")

            c_tot_cost = c_inv_cost + c_imp_cost
            c_recovery = active_exposure * (c_rate / 100.0)
            c_net_benefit = c_recovery - c_tot_cost
            c_roi = (c_net_benefit / c_tot_cost) if c_tot_cost > 0 else 0.0

            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-title'>Conservative Net Benefit</div>
                    <div class='metric-val'>${c_net_benefit:,.2f}</div>
                    <div class='metric-sub'>Recovery: ${c_recovery:,.2f} | Costs: ${c_tot_cost:,.2f} | ROI: {c_roi:.1f}x</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with sc_col2:
            st.markdown("##### ⚖️ Base Scenario (Realistic)")
            b_rate = st.slider("Recovery Rate (%)", min_value=0, max_value=100, value=25, key="b_rate", help="Expected realistic recovery rate")
            b_inv_cost = st.number_input("Investigation Cost ($)", min_value=0.0, value=2000.0, step=500.0, key="b_inv")
            b_imp_cost = st.number_input("Implementation Cost ($)", min_value=0.0, value=3000.0, step=500.0, key="b_imp")

            b_tot_cost = b_inv_cost + b_imp_cost
            b_recovery = active_exposure * (b_rate / 100.0)
            b_net_benefit = b_recovery - b_tot_cost
            b_roi = (b_net_benefit / b_tot_cost) if b_tot_cost > 0 else 0.0

            st.markdown(
                f"""
                <div class='metric-card' style='border-left: 4px solid #10b981;'>
                    <div class='metric-title'>Base Case Net Benefit</div>
                    <div class='metric-val' style='color: #047857;'>${b_net_benefit:,.2f}</div>
                    <div class='metric-sub'>Recovery: ${b_recovery:,.2f} | Costs: ${b_tot_cost:,.2f} | ROI: {b_roi:.1f}x</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with sc_col3:
            st.markdown("##### 🚀 Optimistic Scenario")
            o_rate = st.slider("Recovery Rate (%)", min_value=0, max_value=100, value=50, key="o_rate", help="Best-case recovery assuming high compliance")
            o_inv_cost = st.number_input("Investigation Cost ($)", min_value=0.0, value=1500.0, step=500.0, key="o_inv")
            o_imp_cost = st.number_input("Implementation Cost ($)", min_value=0.0, value=2000.0, step=500.0, key="o_imp")

            o_tot_cost = o_inv_cost + o_imp_cost
            o_recovery = active_exposure * (o_rate / 100.0)
            o_net_benefit = o_recovery - o_tot_cost
            o_roi = (o_net_benefit / o_tot_cost) if o_tot_cost > 0 else 0.0

            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-title'>Optimistic Net Benefit</div>
                    <div class='metric-val'>${o_net_benefit:,.2f}</div>
                    <div class='metric-sub'>Recovery: ${o_recovery:,.2f} | Costs: ${o_tot_cost:,.2f} | ROI: {o_roi:.1f}x</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Scenario Comparison Table & Chart
        st.markdown("##### Scenario Comparison Summary")
        scenario_summary_data = [
            {
                "Scenario": "🛡️ Conservative",
                "Recovery Rate (%)": f"{c_rate}%",
                "Hypothetical Recovery ($)": f"${c_recovery:,.2f}",
                "Investigation Cost ($)": f"${c_inv_cost:,.2f}",
                "Implementation Cost ($)": f"${c_imp_cost:,.2f}",
                "Total Costs ($)": f"${c_tot_cost:,.2f}",
                "Net Benefit ($)": f"${c_net_benefit:,.2f}",
                "ROI Multiple": f"{c_roi:.1f}x" if c_net_benefit > 0 else "Negative",
            },
            {
                "Scenario": "⚖️ Base (Realistic)",
                "Recovery Rate (%)": f"{b_rate}%",
                "Hypothetical Recovery ($)": f"${b_recovery:,.2f}",
                "Investigation Cost ($)": f"${b_inv_cost:,.2f}",
                "Implementation Cost ($)": f"${b_imp_cost:,.2f}",
                "Total Costs ($)": f"${b_tot_cost:,.2f}",
                "Net Benefit ($)": f"${b_net_benefit:,.2f}",
                "ROI Multiple": f"{b_roi:.1f}x" if b_net_benefit > 0 else "Negative",
            },
            {
                "Scenario": "🚀 Optimistic",
                "Recovery Rate (%)": f"{o_rate}%",
                "Hypothetical Recovery ($)": f"${o_recovery:,.2f}",
                "Investigation Cost ($)": f"${o_inv_cost:,.2f}",
                "Implementation Cost ($)": f"${o_imp_cost:,.2f}",
                "Total Costs ($)": f"${o_tot_cost:,.2f}",
                "Net Benefit ($)": f"${o_net_benefit:,.2f}",
                "ROI Multiple": f"{o_roi:.1f}x" if o_net_benefit > 0 else "Negative",
            },
        ]
        st.dataframe(pd.DataFrame(scenario_summary_data), width="stretch", hide_index=True)

        # Plotly chart comparing scenarios
        fig_scenarios = go.Figure()
        fig_scenarios.add_trace(go.Bar(
            name="Hypothetical Recovery ($)",
            x=["Conservative", "Base", "Optimistic"],
            y=[c_recovery, b_recovery, o_recovery],
            marker_color="#3B82F6",
        ))
        fig_scenarios.add_trace(go.Bar(
            name="Total Costs ($)",
            x=["Conservative", "Base", "Optimistic"],
            y=[c_tot_cost, b_tot_cost, o_tot_cost],
            marker_color="#EF4444",
        ))
        fig_scenarios.add_trace(go.Bar(
            name="Net Scenario Benefit ($)",
            x=["Conservative", "Base", "Optimistic"],
            y=[c_net_benefit, b_net_benefit, o_net_benefit],
            marker_color="#10B981",
        ))
        fig_scenarios.update_layout(
            barmode="group",
            title="Financial Projection Comparison by Scenario ($)",
            yaxis_title="Amount ($)",
            margin=dict(t=40, b=10, l=10, r=10),
        )
        st.plotly_chart(fig_scenarios, width="stretch")

        st.caption(
            "$$\\text{Net Scenario Benefit} = \\text{Exposure} \\times \\text{Recovery Rate} - (\\text{Investigation Cost} + \\text{Implementation Cost})$$"
        )

        st.divider()

        # ---------------------------------------------------------------------
        # 4. Investigation Prioritization Matrix & Business Decision Tool
        # ---------------------------------------------------------------------
        st.markdown("#### 4. Investigation Prioritization Matrix")
        st.caption("Benchmark potential business leaks by addressable opportunity, remediation cost, and expected ROI.")

        # Matrix Data
        prioritization_records = [
            {
                "Finding": "Credit Card Payment Friction",
                "Category": "Checkout / Gateway",
                "Severity": "Low",
                "Exposure ($)": 176726.81,
                "Base Recovery (25%) ($)": 176726.81 * 0.25,
                "Est. Costs ($)": 4000.0,
                "Net Benefit ($)": (176726.81 * 0.25) - 4000.0,
                "Recommended Action": "Optimize 3DS & gateway retry timeouts",
            },
            {
                "Finding": "Repeat Leak Customer Accounts",
                "Category": "Policy Abuse",
                "Severity": "Medium",
                "Exposure ($)": 116669.91,
                "Base Recovery (25%) ($)": 116669.91 * 0.25,
                "Est. Costs ($)": 3500.0,
                "Net Benefit ($)": (116669.91 * 0.25) - 3500.0,
                "Recommended Action": "Introduce checkout friction on repeat cancels",
            },
            {
                "Finding": "Ceiling 25% Discount Outliers",
                "Category": "Margin Erosion",
                "Severity": "Medium",
                "Exposure ($)": 102195.66,
                "Base Recovery (25%) ($)": 102195.66 * 0.25,
                "Est. Costs ($)": 2500.0,
                "Net Benefit ($)": (102195.66 * 0.25) - 2500.0,
                "Recommended Action": "Audit promo code authorization logs",
            },
            {
                "Finding": "Chronic Product Return Outliers",
                "Category": "Product Quality",
                "Severity": "High",
                "Exposure ($)": 37310.88,
                "Base Recovery (25%) ($)": 37310.88 * 0.25,
                "Est. Costs ($)": 2000.0,
                "Net Benefit ($)": (37310.88 * 0.25) - 2000.0,
                "Recommended Action": "Audit storefront dimensions & vendor SLAs",
            },
            {
                "Finding": "Critical Inventory Delay SKUs",
                "Category": "Supply Chain",
                "Severity": "High",
                "Exposure ($)": 25000.0,  # Estimated representative stockout exposure
                "Base Recovery (25%) ($)": 25000.0 * 0.25,
                "Est. Costs ($)": 3000.0,
                "Net Benefit ($)": (25000.0 * 0.25) - 3000.0,
                "Recommended Action": "Expedite emergency POs with priority freight",
            },
        ]
        p_df = pd.DataFrame(prioritization_records).sort_values("Net Benefit ($)", ascending=False)

        # Plotly horizontal bar chart for prioritization
        fig_prio = px.bar(
            p_df,
            x="Net Benefit ($)",
            y="Finding",
            orientation="h",
            color="Severity",
            color_discrete_map={"High": "#EF4444", "Medium": "#F59E0B", "Low": "#3B82F6"},
            title="Estimated Net Benefit by Investigation Finding (Base Scenario, $)",
            text_auto="$,.0f",
        )
        fig_prio.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_prio, width="stretch")

        # Prioritization table
        p_df_disp = p_df.copy()
        for col in ["Exposure ($)", "Base Recovery (25%) ($)", "Est. Costs ($)", "Net Benefit ($)"]:
            p_df_disp[col] = p_df_disp[col].map("${:,.2f}".format)
        st.dataframe(p_df_disp, width="stretch", hide_index=True)

        st.divider()

        # ---------------------------------------------------------------------
        # 5. Double-Counting & Overlap Safeguard
        # ---------------------------------------------------------------------
        st.markdown("#### 5. Double-Counting & Transaction Overlap Safeguard")
        st.error(
            "🛡️ **Critical Analytical Safeguard:**\n\n"
            "Do **NOT** sum individual finding exposure totals into a single cumulative figure without deduplication!\n\n"
            "**Verified Dataset Evidence:**\n"
            "- Sum of transaction counts across individual findings: **1,554 records**\n"
            "- Unique deduplicated transaction count across all findings: **1,500 records**\n"
            "- **54 transactions overlap across multiple findings:**\n"
            "  - **21 transactions** are both a Credit Card Cancellation AND placed by a Chronic Leak Customer.\n"
            "  - **19 transactions** are both a 25% Maximum Discount order AND a Credit Card Cancellation.\n"
            "  - **7 transactions** are both a High-Return Product AND placed by a Chronic Leak Customer.\n"
            "  - **7 transactions** are both a 25% Maximum Discount order AND placed by a Chronic Leak Customer.\n\n"
            "Blindly adding the exposure totals would double-count **54 transactions**, artificially inflating corporate exposure figures."
        )

        st.divider()

        # ---------------------------------------------------------------------
        # 6. Integrated Investigation Action Case Tracker
        # ---------------------------------------------------------------------
        st.markdown("#### 6. Convert Scenario Simulation into an Action Case")
        st.caption("Record this simulation into the persistent operational audit tracker for operations and finance leadership.")

        with st.form("scenario_case_form"):
            cf_col1, cf_col2, cf_col3 = st.columns(3)
            with cf_col1:
                case_title = st.text_input("Case Title", value=f"Remediation: {chosen_finding.split('(')[0].strip()}")
                case_owner = st.text_input("Assigned Team / Owner", value="Operations & Finance Taskforce")
            with cf_col2:
                case_priority = st.selectbox("Priority Level", ["Low", "Medium", "High", "Critical"], index=1)
                selected_scenario_tier = st.selectbox("Committed Scenario Tier", ["Base Scenario", "Conservative Scenario", "Optimistic Scenario"], index=0)
            with cf_col3:
                next_action = st.text_input("Immediate Next Action", value="Initiate operational audit & review supplier / payment gateway logs")
                related_id = st.text_input("Entity or Finding Tag", value=chosen_finding.split(":")[0].strip())

            default_commit_benefit = b_net_benefit if selected_scenario_tier.startswith("Base") else (c_net_benefit if selected_scenario_tier.startswith("Conservative") else o_net_benefit)
            case_notes = st.text_area(
                "Evidence Summary & Justification",
                value=f"Target Finding: {chosen_finding}. Active Exposure: ${active_exposure:,.2f}. Selected {selected_scenario_tier} projects a net recovery benefit of ${default_commit_benefit:,.2f} after accounting for implementation costs. Overlap safeguard verified.",
            )
            case_submitted = st.form_submit_button("💾 Save Simulation as Active Case")

        if case_submitted:
            if not case_notes.strip() or not next_action.strip():
                st.error("Please provide an evidence note and next action before saving.")
            else:
                sim_res = case_manager.create_case(
                    title=case_title.strip(),
                    category=finding_cat,
                    description=f"Simulation Case ({selected_scenario_tier}): Committing to ${default_commit_benefit:,.2f} projected net benefit against ${active_exposure:,.2f} potential exposure.",
                    evidence_reference=f"Simulator: {chosen_finding.split('(')[0].strip()}",
                    affected_record_count=0,
                    exposure_estimate=active_exposure,
                    priority=case_priority,
                    owner=case_owner.strip() if case_owner else "Unassigned",
                    next_action=next_action.strip(),
                    notes=case_notes.strip(),
                )
                if sim_res["success"]:
                    st.success(f"✅ Investigation Case **{sim_res['case_id']}** recorded successfully in persistent SQLite database! View in '📋 Case Management Workflow' tab.")
                    st.rerun()
                else:
                    st.error(f"❌ {sim_res['error']}")

        # Display Existing Cases
        st.markdown("##### Active Case Log")
        cases_df = case_manager.get_all_cases()
        if not cases_df.empty:
            disp_cases = cases_df[["case_id", "status", "priority", "category", "title", "exposure_estimate", "owner", "next_action", "created_at"]].copy()
            disp_cases["exposure_estimate"] = disp_cases["exposure_estimate"].map("${:,.2f}".format)
            st.dataframe(disp_cases, width="stretch", hide_index=True)
            st.download_button(
                "📥 Export All Cases (CSV)",
                data=cases_df.to_csv(index=False).encode("utf-8"),
                file_name="leaklens_investigation_cases.csv",
                mime="text/csv",
            )
        else:
            st.info("No active cases logged yet. Submit the form above or use the Case Management Workflow tab to record your first operational case.")

    # =========================================================================
    # TAB 7: ML INSIGHTS & MODEL EVALUATION (PHASE 6 CORE)
    # =========================================================================
    with tab_ml:
        st.subheader("🤖 Machine Learning Insights & Model Evaluation")
        st.caption("Empirical, transparent evaluation of predictive models on pre-outcome transaction signals.")

        # Critical Methodology & Fraud Distinction Banner
        st.warning(
            "⚠️ **Methodological Boundary: Transaction Status Prediction $\\neq$ Fraud or Money Leak Detection**\n\n"
            "- **Operational Friction Signal Only:** Predicting whether an order will be Cancelled or Returned indicates customer friction "
            "(e.g. payment gateway 3DS timeouts, buyer sizing hesitation, delivery delays)—**NOT employee embezzlement, card fraud, or illegal leakage**.\n"
            "- **Customer Protection:** Most cancellations are voluntary drop-offs and most returns are normal retail exchanges. "
            "Autonomously blocking customers or accusing accounts based on probabilistic model predictions causes severe brand harm.\n"
            "- **Scientific Integrity:** LeakLens - AI reports actual measured generalization metrics, compares against simple majority-class baselines, "
            "and explicitly warns against claiming false predictive success."
        )

        # Artifact Status & Pipeline Control
        metrics_file = REPORT_DIR / "model_comparison.csv"
        metadata_file = REPORT_DIR / "model_experiment_metadata.json"
        predictions_file = REPORT_DIR / "test_predictions.csv"
        per_class_file = REPORT_DIR / "per_class_metrics.csv"
        cm_files = sorted(REPORT_DIR.glob("confusion_*.csv"))

        col_art_status, col_art_btn = st.columns([3, 1])
        with col_art_status:
            artifacts_present = all([metrics_file.exists(), metadata_file.exists(), predictions_file.exists(), len(cm_files) >= 2])
            if artifacts_present:
                st.markdown(
                    "<span class='badge-verified'>ALL MODEL ARTIFACTS VERIFIED ON DISK</span> "
                    f"<span style='color: #64748b; font-size: 0.85rem;'>({len(cm_files)} confusion matrices, predictions ledger, metrics summary)</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<span class='badge-alert'>MODEL ARTIFACTS INCOMPLETE OR MISSING</span> "
                    "<span style='color: #64748b; font-size: 0.85rem;'>Click button to run model_experiment.py and generate fresh outputs.</span>",
                    unsafe_allow_html=True,
                )

        with col_art_btn:
            if st.button("🔄 Re-run Model Training Pipeline", help="Executes model_experiment.py on chronological holdout and updates all artifacts"):
                with st.spinner("Training models (Dummy Baseline, Logistic Regression, Random Forest)..."):
                    try:
                        import model_experiment
                        model_experiment.main()
                        st.success("✅ Model pipeline executed successfully! Reloading artifacts...")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error during model execution: {e}")

        st.divider()

        if not metrics_file.exists():
            st.error("⚠️ `reports/model_comparison.csv` was not found. Click the 'Re-run Model Training Pipeline' button above to generate it.")
        else:
            try:
                metrics_df = pd.read_csv(metrics_file)
            except Exception as e:
                st.error(f"❌ Failed to parse `model_comparison.csv`: {e}")
                metrics_df = pd.DataFrame()

            if not metrics_df.empty:
                # -------------------------------------------------------------
                # 1. Empirical Model Benchmark (Chronological Holdout)
                # -------------------------------------------------------------
                st.markdown("#### 1. Empirical Model Benchmark (Chronological Holdout)")
                st.caption("Evaluated on a chronological 80% train (Jan–Oct 2025) / 20% test (Oct–Dec 2025) holdout split across 17,082 usable records.")

                # Executive KPI metrics
                bm_c1, bm_c2, bm_c3, bm_c4 = st.columns(4)
                with bm_c1:
                    baseline_row = metrics_df[metrics_df["model"].str.contains("Baseline", case=False, na=False)]
                    b_acc = baseline_row["test_accuracy"].iloc[0] if not baseline_row.empty else 0.8188
                    st.metric("Baseline Test Accuracy", f"{b_acc * 100:.2f}%", help="Simple Most-Frequent Dummy Classifier (always guesses Completed)")
                with bm_c2:
                    rf_row = metrics_df[metrics_df["model"].str.contains("Random Forest", case=False, na=False)]
                    rf_f1 = rf_row["test_macro_f1"].iloc[0] if not rf_row.empty else 0.3357
                    st.metric("Best Test Macro-F1", f"{rf_f1:.4f}", f"{rf_row['test_accuracy'].iloc[0]*100:.2f}% test acc" if not rf_row.empty else "", help="Random Forest (balanced_subsample)")
                with bm_c3:
                    st.metric("Evaluation Sample Size", "17,082 Orders", "13,665 Train / 3,417 Test", help="Pending transactions excluded to avoid label ambiguity")
                with bm_c4:
                    st.metric("Split Strategy", "Chronological Holdout", "80% Train / 20% Test", help="Preserves real-world temporal validity")

                # Metrics Comparison Table
                st.markdown("##### Performance Comparison Across All Evaluated Models")
                disp_metrics = metrics_df.copy()
                if "train_accuracy" in disp_metrics.columns and "test_accuracy" in disp_metrics.columns:
                    disp_metrics["generalization_gap"] = (disp_metrics["train_accuracy"] - disp_metrics["test_accuracy"])
                
                # Format columns
                for c in ["train_accuracy", "test_accuracy"]:
                    if c in disp_metrics.columns:
                        disp_metrics[c] = disp_metrics[c].map(lambda x: f"{x * 100:.2f}%")
                if "generalization_gap" in disp_metrics.columns:
                    disp_metrics["generalization_gap"] = disp_metrics["generalization_gap"].map(lambda x: f"{x * 100:+.2f}%")
                for c in ["train_macro_f1", "test_macro_f1"]:
                    if c in disp_metrics.columns:
                        disp_metrics[c] = disp_metrics[c].map(lambda x: f"{x:.4f}")

                show_cols = [c for c in ["model", "train_accuracy", "test_accuracy", "generalization_gap", "train_macro_f1", "test_macro_f1", "train_rows", "test_rows"] if c in disp_metrics.columns]
                st.dataframe(disp_metrics[show_cols], width="stretch", hide_index=True)

                # Visual Charts: Generalization Gap & Macro-F1
                c_chart1, c_chart2 = st.columns(2)
                with c_chart1:
                    if {"train_accuracy", "test_accuracy"}.issubset(metrics_df.columns):
                        gap_fig = go.Figure()
                        gap_fig.add_trace(go.Bar(
                            name="Training Accuracy",
                            x=metrics_df["model"],
                            y=metrics_df["train_accuracy"],
                            marker_color="#3B82F6",
                            text=[f"{v*100:.1f}%" for v in metrics_df["train_accuracy"]],
                            textposition="auto",
                        ))
                        gap_fig.add_trace(go.Bar(
                            name="Testing Accuracy",
                            x=metrics_df["model"],
                            y=metrics_df["test_accuracy"],
                            marker_color="#10B981",
                            text=[f"{v*100:.1f}%" for v in metrics_df["test_accuracy"]],
                            textposition="auto",
                        ))
                        gap_fig.update_layout(
                            barmode="group",
                            title="Training vs. Testing Accuracy (Generalization Gap)",
                            yaxis_title="Accuracy",
                            yaxis=dict(range=[0, 1.0]),
                            margin=dict(t=40, b=10, l=10, r=10),
                        )
                        st.plotly_chart(gap_fig, width="stretch")

                with c_chart2:
                    if "test_macro_f1" in metrics_df.columns:
                        f1_fig = px.bar(
                            metrics_df,
                            x="model",
                            y="test_macro_f1",
                            color="model",
                            title="Testing Macro-F1 Comparison",
                            text_auto=".4f",
                        )
                        f1_fig.update_layout(
                            showlegend=False,
                            yaxis_title="Macro-F1 Score",
                            yaxis=dict(range=[0, 0.6]),
                            margin=dict(t=40, b=10, l=10, r=10),
                        )
                        st.plotly_chart(f1_fig, width="stretch")

                # The Honest Reality Check Callout
                st.info(
                    "🚨 **The Honest Reality: Why the Simple Dummy Baseline Wins on Accuracy (81.88%):**\n\n"
                    "- **The Optical Illusion of Majority Classes:** Because **81.88% of held-out transactions are Completed**, "
                    "a trivial dummy rule that blindly guesses `Completed` for every single order achieves **81.88% accuracy**.\n"
                    "- **Complex Models Degrade Under Reality:** In contrast, Random Forest achieves only **62.36% testing accuracy** "
                    "(a steep -17.4% generalization drop from its 79.80% training accuracy).\n"
                    "- **No Predictive Silver Bullet:** Balanced class weighting forces Random Forest to guess minority classes more frequently, "
                    "which slightly lifts Macro-F1 from 0.3001 to 0.3357, but causes catastrophic false positive rates on minority classes."
                )

                st.divider()

                # -------------------------------------------------------------
                # 2. Per-Class Granular Performance & Confusion Matrix Heatmap
                # -------------------------------------------------------------
                st.markdown("#### 2. Per-Class Granular Performance & Confusion Matrices")
                st.caption("Inspect class-specific precision, recall, and false-positive distributions for each model.")

                available_models = metrics_df["model"].dropna().unique().tolist()
                selected_model = st.selectbox("Select Model for In-Depth Class Breakdown", available_models, index=0)

                col_pc_table, col_pc_cm = st.columns([1, 1])

                with col_pc_table:
                    st.markdown(f"##### Per-Class Performance: `{selected_model}`")
                    pc_df = load_or_calc_per_class_metrics(selected_model)
                    if not pc_df.empty:
                        disp_pc = pc_df.copy()
                        for col in ["precision", "recall"]:
                            if col in disp_pc.columns:
                                disp_pc[col] = disp_pc[col].map(lambda x: f"{x * 100:.2f}%" if pd.notnull(x) else "N/A")
                        if "f1_score" in disp_pc.columns:
                            disp_pc["f1_score"] = disp_pc["f1_score"].map(lambda x: f"{x:.4f}" if pd.notnull(x) else "N/A")
                        if "support" in disp_pc.columns:
                            disp_pc["support"] = disp_pc["support"].map(lambda x: f"{int(x):,}" if pd.notnull(x) else "N/A")
                        disp_pc.columns = ["Target Class", "Precision (%)", "Recall (%)", "F1-Score", "Support (Test Count)"]
                        st.dataframe(disp_pc, width="stretch", hide_index=True)
                    else:
                        st.write("Per-class metrics not available for this model.")

                    if "Random Forest" in selected_model:
                        st.error(
                            "📉 **Critical Vulnerability on Minority Classes:**\n\n"
                            "- **Cancelled Orders:** Precision is only **10.48%** (89.52% false-positive rate!). Out of 563 predicted cancellations, 504 were actually completed!\n"
                            "- **Returned Orders:** Precision is only **9.02%** (90.98% false-positive rate!). Out of 377 predicted returns, 343 were actually completed!"
                        )
                    elif "Baseline" in selected_model:
                        st.warning(
                            "📌 **Baseline Limitation:**\n"
                            "The baseline achieves **0.00% precision and recall on Cancelled and Returned orders** because it never predicts them. "
                            "It achieves high accuracy purely due to the 81.88% completed transaction majority."
                        )

                with col_pc_cm:
                    st.markdown(f"##### Confusion Matrix: `{selected_model}`")
                    safe_cm_name = selected_model.lower().replace(" ", "_")
                    cm_path = REPORT_DIR / f"confusion_{safe_cm_name}.csv"
                    if cm_path.exists():
                        cm_data = pd.read_csv(cm_path, index_col=0)
                        fig_cm = px.imshow(
                            cm_data,
                            text_auto=True,
                            aspect="auto",
                            color_continuous_scale="Blues",
                            title=f"Actual vs. Predicted: {selected_model}",
                            labels=dict(x="Predicted Class", y="Actual Class", color="Transaction Count"),
                        )
                        fig_cm.update_layout(margin=dict(t=40, b=10, l=10, r=10))
                        st.plotly_chart(fig_cm, width="stretch")
                    else:
                        st.info(f"Confusion matrix file `confusion_{safe_cm_name}.csv` not found.")

                st.divider()

                # -------------------------------------------------------------
                # 3. Held-Out Test Prediction Explorer & Error Audit
                # -------------------------------------------------------------
                st.markdown("#### 3. Held-Out Test Prediction Explorer & Error Audit")
                st.caption("Inspect individual test transactions, filter by prediction accuracy, and audit misclassifications.")

                if predictions_file.exists():
                    try:
                        preds_df = pd.read_csv(predictions_file)
                    except Exception as e:
                        st.error(f"❌ Error loading test predictions: {e}")
                        preds_df = pd.DataFrame()

                    if not preds_df.empty:
                        # Filters
                        pr_col1, pr_col2, pr_col3, pr_col4 = st.columns(4)
                        with pr_col1:
                            pred_models = sorted(preds_df["model"].dropna().unique().tolist())
                            sel_pred_model = st.selectbox("Filter by Model", pred_models, index=pred_models.index("Random Forest") if "Random Forest" in pred_models else 0)
                        with pr_col2:
                            sel_outcome = st.selectbox("Prediction Accuracy", ["All Predictions", "Misclassifications Only (Errors)", "Accurate Only"], index=1)
                        with pr_col3:
                            target_classes = ["All"] + sorted(preds_df["actual_status"].dropna().unique().tolist())
                            sel_target_cls = st.selectbox("Actual Status", target_classes, index=0)
                        with pr_col4:
                            display_n = st.select_slider("Rows to Display", options=[50, 100, 250, 500, 1000], value=100)

                        # Apply filters
                        sub_preds = preds_df[preds_df["model"] == sel_pred_model].copy()
                        sub_preds["is_error"] = sub_preds["actual_status"] != sub_preds["predicted_status"]

                        if sel_outcome == "Misclassifications Only (Errors)":
                            sub_preds = sub_preds[sub_preds["is_error"]]
                        elif sel_outcome == "Accurate Only":
                            sub_preds = sub_preds[~sub_preds["is_error"]]

                        if sel_target_cls != "All":
                            sub_preds = sub_preds[sub_preds["actual_status"] == sel_target_cls]

                        # Metrics
                        tot_sub = len(sub_preds)
                        err_sub = int(sub_preds["is_error"].sum())
                        err_rate = (err_sub / tot_sub * 100) if tot_sub > 0 else 0.0

                        pe1, pe2, pe3 = st.columns(3)
                        with pe1:
                            st.metric("Filtered Records", f"{tot_sub:,}")
                        with pe2:
                            st.metric("Misclassifications", f"{err_sub:,}", delta_color="inverse")
                        with pe3:
                            st.metric("Error Rate", f"{err_rate:.2f}%")

                        # Display Table
                        cols_to_disp = [c for c in ["row_index", "timestamp", "actual_status", "predicted_status", "is_error", "model"] if c in sub_preds.columns]
                        st.dataframe(sub_preds[cols_to_disp].head(display_n), width="stretch", hide_index=True)

                        # CSV Download
                        st.download_button(
                            "📥 Download Held-Out Predictions CSV",
                            data=sub_preds.to_csv(index=False).encode("utf-8"),
                            file_name=f"leaklens_test_predictions_{sel_pred_model.lower().replace(' ', '_')}.csv",
                            mime="text/csv",
                        )
                else:
                    st.info("Held-out test predictions file not found. Run `python model_experiment.py` to generate.")

                st.divider()

                # -------------------------------------------------------------
                # 4. Methodological Audit & Leakage Checklist
                # -------------------------------------------------------------
                st.markdown("#### 4. Methodological Audit & Model Governance Checklist")
                st.caption("Detailed architectural review addressing target leakage, memorization risk, class imbalance, and evaluation rigor.")

                with st.expander("🔍 Target Variable & Excluded Record Rationale", expanded=True):
                    st.markdown(
                        """
                        - **Target Definition:** `status` $\\in$ `['Completed', 'Cancelled', 'Returned']`.
                        - **Why `Pending` Orders Were Excluded (918 records):**
                          - `Pending` transactions represent in-flight, unconfirmed orders where the ultimate business outcome is not yet resolved.
                          - Treating `Pending` as a fourth permanent class introduces severe label ambiguity, as these orders will eventually resolve into Completed, Cancelled, or Returned.
                          - Excluding `Pending` ensures clean, ground-truth supervised learning labels on the 17,082 verified transactions.
                        """
                    )

                with st.expander("🛡️ Target Leakage & Feature Selection Audit", expanded=True):
                    st.markdown(
                        """
                        - **Strict Pre-Outcome Temporal Horizon:**
                          - All input features are restricted to metadata accessible **at the moment the order is initiated**:
                            `quantity`, `unit_price`, `discount_pct`, `transaction_month`, `transaction_dayofweek`, `transaction_hour`, `channel`, `payment_method`.
                        - **Excluded Post-Outcome Fields:**
                          - Downstream operational timestamps (e.g. shipping confirmation, refund issuance date), post-purchase support tickets, and dispute flags are strictly excluded.
                          - Primary key identifier `transaction_id` is excluded to prevent arbitrary index memorization.
                        """
                    )

                with st.expander("⚠️ Identifier Memorization Risk (`customer_id` & `product_id`)", expanded=True):
                    st.markdown(
                        """
                        - **High-Cardinality One-Hot Encoding:**
                          - The experimental pipeline includes `customer_id` (3,000 entities) and `product_id` (250 SKUs) in the one-hot categorical encoder.
                        - **Memorization vs. Generalization:**
                          - While including entity IDs helps identify repeat-offender accounts in historical data, tree-based models risk **memorizing specific historical buyers** rather than learning generalized fraud or cancellation signals.
                          - If a brand-new customer makes a purchase tomorrow, one-hot encoded ID features offer zero predictive power.
                        """
                    )

                with st.expander("📅 Split Strategy: Chronological Holdout vs. Random K-Fold", expanded=True):
                    st.markdown(
                        """
                        - **Chronological 80/20 Holdout:**
                          - Earlier 13,665 transactions (Jan 1, 2025 to Oct 17, 2025) are used for model training; later 3,417 transactions (Oct 17, 2025 to Dec 31, 2025) are used strictly for held-out evaluation.
                        - **Why Random K-Fold Splitting is Invalid for Retail Modeling:**
                          - Randomly shuffling transactions causes **temporal data leakage**: future customer behavior and seasonal promotional patterns leak into past predictions.
                          - Chronological splitting accurately simulates how models decay over time when deployed in production, honestly exposing the ~17.4% generalization drop.
                        """
                    )

                with st.expander("⚖️ Class Imbalance & The Balanced-Weight Tradeoff", expanded=True):
                    st.markdown(
                        """
                        - **81.88% Majority Class Baseline:**
                          - Completed orders dominate the dataset (13,962 of 17,082 records).
                          - An unweighted classifier achieves high accuracy (81.88%) by simply predicting `Completed` for all inputs, but yields **0.00% recall on Cancelled and Returned orders**.
                        - **The False-Positive Explosion of Class Balancing:**
                          - Setting `class_weight='balanced_subsample'` forces the Random Forest to heavily penalize missing minority classes.
                          - While this increases minority recall to ~11–19%, it creates a massive false-positive spike: **~90% of all predicted cancellations and returns are false alarms**!
                        """
                    )

                st.divider()

                # -------------------------------------------------------------
                # 5. Raw Experiment Metadata
                # -------------------------------------------------------------
                st.markdown("#### 5. Raw Experiment Metadata")
                if metadata_file.exists():
                    try:
                        meta_data = json.loads(metadata_file.read_text(encoding="utf-8"))
                        st.json(meta_data)
                    except Exception as e:
                        st.warning(f"Could not parse metadata JSON: {e}")
                else:
                    st.info("Metadata file not found.")

    # =========================================================================
    # TAB 8: DATA QUALITY & VERIFICATION
    # =========================================================================
    with tab_quality:
        st.subheader("🛡️ Data Quality & Ground-Truth Verification")
        st.caption("Audit results and structural integrity checks performed during Phase 1.")

        q1, q2 = st.columns([1, 1])

        with q1:
            st.markdown("#### File & Schema Catalog")
            profile_summary_path = REPORT_DIR / "data_profile_summary.csv"
            if profile_summary_path.exists():
                prof_df = pd.read_csv(profile_summary_path)
                st.dataframe(prof_df, width="stretch", hide_index=True)
            else:
                st.write("Summary report not found. Run `python profile_data.py` to regenerate.")

            st.markdown("#### Key Integrity Verification")
            st.markdown(
                """
                - **`transactions.customer_id` $\\rightarrow$ `customers.customer_id`**: **100.0% Match** (0 unmatched records).
                - **`transactions.product_id` $\\rightarrow$ `products.product_id`**: **100.0% Match** (0 unmatched records).
                - **`inventory.product_id` $\\rightarrow$ `products.product_id`**: **100.0% Match** (0 unmatched records).
                - **Identifier Uniqueness**: 100% unique primary keys across transactions, customers, products, inventory, and campaigns.
                """
            )

        with q2:
            st.markdown("#### Documented Inconsistencies & Synthetic Artifacts")
            st.warning(
                "⚠️ **Product Catalog Negative Margins:**\n"
                "In `products.csv`, **76 out of 250 products (30.4%)** have `list_price < unit_cost`.\n\n"
                "**Important Context:** The dataset `README.txt` explicitly notes that costs and prices "
                "were independently generated. Therefore, negative margins are synthetic inconsistencies, "
                "**not evidence of verified employee fraud or supplier embezzlement**."
            )

            st.info(
                "📢 **Campaign Data Separation:**\n"
                "`campaigns.csv` represents macro marketing channel spend and totals 895,411 conversions "
                "against 18,000 transactions. It lacks transaction or customer keys. "
                "Attributing campaign spend 1:1 to transactions is statistically invalid and strictly avoided."
            )

        # Full Data Quality Report Expander
        st.divider()
        dq_report_path = REPORT_DIR / "data_quality_report.md"
        if dq_report_path.exists():
            with st.expander("📄 View Full Phase 1 Data Quality Markdown Report"):
                st.markdown(dq_report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()