from pathlib import Path
import json
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="MarginTrace Investigations",
    page_icon="🔎",
    layout="wide",
)

DATA_DIR = Path("data")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

CASES_FILE = REPORT_DIR / "investigation_cases.csv"


def load_csv(filename):
    path = DATA_DIR / filename
    if not path.exists():
        path = Path(filename)
    if not path.exists():
        return None
    return pd.read_csv(path)


def load_cases():
    if CASES_FILE.exists():
        return pd.read_csv(CASES_FILE).to_dict("records")
    return []


def save_cases(cases):
    pd.DataFrame(cases).to_csv(CASES_FILE, index=False)


st.title("🔎 MarginTrace — Investigation Center")
st.caption("Estimate exposure, document evidence, and track the next action.")

st.warning(
    "Scenario estimates are hypothetical decision-support figures. "
    "They are not confirmed losses or guaranteed recoveries."
)

transactions = load_csv("transactions.csv")

if transactions is None:
    st.error("transactions.csv not found.")
    st.stop()

transactions.columns = transactions.columns.str.strip().str.lower()

required = {
    "transaction_id", "status", "quantity", "unit_price", "discount_pct"
}
if not required.issubset(transactions.columns):
    st.error(f"Missing columns: {sorted(required - set(transactions.columns))}")
    st.stop()

transactions["quantity"] = pd.to_numeric(
    transactions["quantity"], errors="coerce"
)
transactions["unit_price"] = pd.to_numeric(
    transactions["unit_price"], errors="coerce"
)
transactions["discount_pct"] = pd.to_numeric(
    transactions["discount_pct"], errors="coerce"
)

discount = transactions["discount_pct"]

if discount.dropna().between(0, 1).all():
    transactions["discount_fraction"] = discount
elif discount.dropna().between(0, 100).all():
    transactions["discount_fraction"] = discount / 100
else:
    st.error("Unexpected discount values; validate the dataset documentation.")
    st.stop()

transactions["gross_value"] = (
    transactions["quantity"] * transactions["unit_price"]
)
transactions["discount_amount"] = (
    transactions["gross_value"] * transactions["discount_fraction"]
)
transactions["estimated_net_value"] = (
    transactions["gross_value"] - transactions["discount_amount"]
)

st.subheader("1. Exposure scenario calculator")

col1, col2 = st.columns(2)

with col1:
    exposure = st.number_input(
        "Potential exposure amount",
        min_value=0.0,
        value=10000.0,
        step=500.0,
        help="Enter an amount supported by your investigation evidence.",
    )

    recoverable_rate = st.slider(
        "Hypothetical recoverable share (%)",
        min_value=0,
        max_value=100,
        value=30,
        help="A scenario assumption, not a model prediction.",
    )

with col2:
    investigation_cost = st.number_input(
        "Estimated investigation / remediation cost",
        min_value=0.0,
        value=1000.0,
        step=100.0,
    )

    confidence = st.selectbox(
        "Evidence confidence",
        ["Low — needs validation", "Medium — partially supported",
         "High — directly verified"],
    )

estimated_recovery = exposure * recoverable_rate / 100
estimated_net_benefit = estimated_recovery - investigation_cost

m1, m2, m3 = st.columns(3)
m1.metric("Scenario exposure", f"{exposure:,.2f}")
m2.metric("Hypothetical recovery", f"{estimated_recovery:,.2f}")
m3.metric("Recovery less cost", f"{estimated_net_benefit:,.2f}")

st.caption(
    "Formula: hypothetical recovery = exposure × recoverable share. "
    "Net scenario benefit = hypothetical recovery − estimated costs. "
    "Actual recovery may be zero."
)

st.divider()

st.subheader("2. Create an investigation case")

transaction_ids = transactions["transaction_id"].dropna().astype(str).tolist()

with st.form("case_form"):
    selected_id = st.selectbox(
        "Related transaction",
        ["General investigation"] + transaction_ids,
    )

    issue_type = st.selectbox(
        "Issue category",
        [
            "Returned transaction review",
            "Cancelled transaction review",
            "Product price/cost anomaly",
            "Inventory anomaly",
            "Discount review",
            "Other",
        ],
    )

    evidence_note = st.text_area(
        "Evidence and calculation",
        placeholder="Describe the supporting records, formula, and caveats.",
    )

    next_action = st.text_input(
        "Next action",
        placeholder="Example: verify refund record with finance team",
    )

    owner = st.text_input(
        "Owner",
        placeholder="Team or role responsible",
    )

    priority = st.selectbox(
        "Priority",
        ["Low", "Medium", "High", "Urgent"],
        index=1,
    )

    submitted = st.form_submit_button("Save investigation case")

if submitted:
    if not evidence_note.strip():
        st.error("Add an evidence note before saving the case.")
    elif not next_action.strip():
        st.error("Add a next action before saving the case.")
    else:
        cases = load_cases()
        cases.append({
            "case_id": f"CASE-{len(cases) + 1:04d}",
            "transaction_id": selected_id,
            "issue_type": issue_type,
            "evidence_note": evidence_note.strip(),
            "next_action": next_action.strip(),
            "owner": owner.strip(),
            "priority": priority,
            "evidence_confidence": confidence,
            "scenario_exposure": exposure,
            "hypothetical_recovery": estimated_recovery,
            "investigation_cost": investigation_cost,
            "scenario_net_benefit": estimated_net_benefit,
            "status": "Open",
        })
        save_cases(cases)
        st.success("Investigation case saved.")
        st.rerun()

st.divider()

st.subheader("3. Investigation case tracker")

cases = load_cases()

if not cases:
    st.info("No cases yet. Create an investigation case above.")
else:
    cases_df = pd.DataFrame(cases)

    st.dataframe(cases_df, use_container_width=True, hide_index=True)

    case_ids = cases_df["case_id"].tolist()
    chosen_case = st.selectbox("Select a case to update", case_ids)

    current = next(c for c in cases if c["case_id"] == chosen_case)

    with st.form("update_case_form"):
        new_status = st.selectbox(
            "Case status",
            ["Open", "Investigating", "Action required", "Resolved", "Closed"],
            index=[
                "Open", "Investigating", "Action required",
                "Resolved", "Closed"
            ].index(current["status"])
            if current["status"] in [
                "Open", "Investigating", "Action required", "Resolved", "Closed"
            ] else 0,
        )

        new_action = st.text_input(
            "Updated next action",
            value=current["next_action"],
        )

        update = st.form_submit_button("Update selected case")

    if update:
        for case in cases:
            if case["case_id"] == chosen_case:
                case["status"] = new_status
                case["next_action"] = new_action.strip()
        save_cases(cases)
        st.success("Case updated.")
        st.rerun()

    st.download_button(
        "Export case tracker",
        data=cases_df.to_csv(index=False).encode("utf-8"),
        file_name="margintrace_investigation_cases.csv",
        mime="text/csv",
    )