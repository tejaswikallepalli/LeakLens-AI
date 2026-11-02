from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="LeakLens - AI ML Insights",
    page_icon="🤖",
    layout="wide",
)

REPORT_DIR = Path("reports")

st.title("🤖 LeakLens - AI — ML Insights")
st.caption("Measured model performance, transparent evidence, no fabricated scores.")

metrics_path = REPORT_DIR / "model_comparison.csv"
metadata_path = REPORT_DIR / "model_experiment_metadata.json"
predictions_path = REPORT_DIR / "test_predictions.csv"

if not metrics_path.exists():
    st.error(
        "Model results were not found. Run `python model_experiment.py` first."
    )
    st.stop()

metrics = pd.read_csv(metrics_path)

if metrics.empty or "macro_f1" not in metrics.columns:
    st.error("The model comparison file is empty or has an unexpected format.")
    st.stop()

st.subheader("1. Model comparison")

display_cols = [
    col for col in [
        "model", "accuracy", "macro_f1", "train_rows", "test_rows"
    ]
    if col in metrics.columns
]
st.dataframe(metrics[display_cols], use_container_width=True, hide_index=True)

if "model" in metrics.columns and "macro_f1" in metrics.columns:
    fig = px.bar(
        metrics,
        x="model",
        y="macro_f1",
        title="Macro-F1 by model",
        range_y=[0, 1],
        text_auto=".3f",
    )
    st.plotly_chart(fig, use_container_width=True)

best = metrics.sort_values("macro_f1", ascending=False).iloc[0]
st.metric("Highest measured Macro-F1", f"{best['macro_f1']:.3f}")
st.write("Model:", best["model"])

st.info(
    "Macro-F1 gives equal weight to each class. A high score is not proof "
    "that a model will generalize to new businesses. Compare it with the "
    "baseline and review per-class metrics before selecting a model."
)

st.divider()
st.subheader("2. Confusion matrices")

confusion_files = sorted(REPORT_DIR.glob("confusion_*.csv"))

if not confusion_files:
    st.warning("No confusion matrices found. Rerun the model experiment.")
else:
    selected_file = st.selectbox(
        "Select model",
        confusion_files,
        format_func=lambda path: path.stem.replace("confusion_", "").replace(
            "_", " "
        ).title(),
    )
    cm = pd.read_csv(selected_file, index_col=0)

    fig = px.imshow(
        cm,
        text_auto=True,
        aspect="auto",
        title="Actual vs predicted classes",
        labels={
            "x": "Predicted class",
            "y": "Actual class",
            "color": "Count",
        },
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("3. Held-out test predictions")

if predictions_path.exists():
    predictions = pd.read_csv(predictions_path)

    st.write(f"Prediction records: {len(predictions):,}")

    if "model" in predictions.columns:
        model_choice = st.selectbox(
            "Prediction model",
            sorted(predictions["model"].dropna().unique()),
        )
        predictions = predictions[predictions["model"] == model_choice]

    if {"actual_status", "predicted_status"}.issubset(predictions.columns):
        errors = predictions[
            predictions["actual_status"] != predictions["predicted_status"]
        ]
        st.metric("Incorrect predictions in displayed test set", len(errors))

    st.dataframe(predictions, use_container_width=True, hide_index=True)

    st.download_button(
        "Download test predictions",
        data=predictions.to_csv(index=False).encode("utf-8"),
        file_name="leaklens_test_predictions.csv",
        mime="text/csv",
    )
else:
    st.warning("Test predictions file not found.")

st.divider()
st.subheader("4. Experiment notes")

if metadata_path.exists():
    st.json(__import__("json").loads(metadata_path.read_text(encoding="utf-8")))
else:
    st.warning("Experiment metadata not found.")