"""
test_phase6_ml_insights.py
Automated end-to-end verification suite for LeakLens - AI Phase 6:
Integration of Empirical ML Experiments, Outputs, and Governance Audit.
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

REPORT_DIR = Path("reports")

def run_tests():
    print("=" * 70)
    print("RUNNING LEAKLENS - AI - PHASE 6 ML INTEGRATION VERIFICATION SUITE")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # TEST 1: ARTIFACT PRESENCE & INTEGRITY
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Checking Required ML Artifact Files on Disk...")
    expected_artifacts = [
        "model_comparison.csv",
        "model_experiment_metadata.json",
        "per_class_metrics.csv",
        "test_predictions.csv",
        "confusion_baseline_most_frequent.csv",
        "confusion_logistic_regression.csv",
        "confusion_random_forest.csv",
    ]
    for art in expected_artifacts:
        art_path = REPORT_DIR / art
        assert art_path.exists(), f"Missing required artifact: {art}"
        assert art_path.stat().st_size > 0, f"Artifact is empty: {art}"
        print(f"  -> Verified on disk: {art} ({art_path.stat().st_size:,} bytes)")
    print("  -> Passed: All 7 core ML artifact files exist and are populated.")

    # -------------------------------------------------------------------------
    # TEST 2: MODEL COMPARISON METRICS ACCURACY
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Verifying Model Benchmark Accuracy & Macro-F1...")
    comp_df = pd.read_csv(REPORT_DIR / "model_comparison.csv")
    required_cols = ["model", "train_accuracy", "test_accuracy", "train_macro_f1", "test_macro_f1", "train_rows", "test_rows"]
    for c in required_cols:
        assert c in comp_df.columns, f"Missing column {c} in model_comparison.csv"

    # Verify Baseline most frequent
    base_row = comp_df[comp_df["model"].str.contains("Baseline", case=False)]
    assert not base_row.empty, "Baseline most frequent model not found"
    base_acc = base_row["test_accuracy"].iloc[0]
    base_f1 = base_row["test_macro_f1"].iloc[0]
    assert 0.818 <= base_acc <= 0.820, f"Baseline test accuracy should be ~81.88%, got {base_acc}"
    assert 0.299 <= base_f1 <= 0.302, f"Baseline test Macro-F1 should be ~0.3001, got {base_f1}"
    print(f"  -> Baseline Most Frequent: Test Accuracy = {base_acc*100:.2f}%, Test Macro-F1 = {base_f1:.4f}")

    # Verify Random Forest
    rf_row = comp_df[comp_df["model"].str.contains("Random Forest", case=False)]
    assert not rf_row.empty, "Random Forest model not found"
    rf_acc = rf_row["test_accuracy"].iloc[0]
    rf_f1 = rf_row["test_macro_f1"].iloc[0]
    rf_train_acc = rf_row["train_accuracy"].iloc[0]
    assert 0.620 <= rf_acc <= 0.630, f"Random Forest test accuracy should be ~62.36%, got {rf_acc}"
    assert 0.330 <= rf_f1 <= 0.340, f"Random Forest test Macro-F1 should be ~0.3357, got {rf_f1}"
    assert rf_train_acc > rf_acc, "Expected generalization gap (train acc > test acc)"
    print(f"  -> Random Forest: Train Acc = {rf_train_acc*100:.2f}%, Test Acc = {rf_acc*100:.2f}% (Gap: {(rf_train_acc - rf_acc)*100:+.2f}%), Test Macro-F1 = {rf_f1:.4f}")

    # Verify Logistic Regression
    lr_row = comp_df[comp_df["model"].str.contains("Logistic Regression", case=False)]
    assert not lr_row.empty, "Logistic Regression model not found"
    lr_acc = lr_row["test_accuracy"].iloc[0]
    lr_f1 = lr_row["test_macro_f1"].iloc[0]
    assert 0.470 <= lr_acc <= 0.480, f"Logistic Regression test accuracy should be ~47.64%, got {lr_acc}"
    print(f"  -> Logistic Regression: Test Acc = {lr_acc*100:.2f}%, Test Macro-F1 = {lr_f1:.4f}")

    # Honest assessment assertion: Baseline must beat Random Forest on accuracy
    assert base_acc > rf_acc, "Baseline must achieve higher accuracy than Random Forest due to 81.88% class imbalance!"
    print("  -> Passed: Empirical results accurately confirm Baseline > Random Forest on accuracy.")

    # -------------------------------------------------------------------------
    # TEST 3: PER-CLASS PERFORMANCE & MINORITY VULNERABILITY
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Verifying Per-Class Metrics & Minority Class Limitations...")
    pc_df = pd.read_csv(REPORT_DIR / "per_class_metrics.csv")
    rf_pc = pc_df[pc_df["model"] == "Random Forest"]
    assert not rf_pc.empty

    cancelled_row = rf_pc[rf_pc["class"] == "Cancelled"].iloc[0]
    returned_row = rf_pc[rf_pc["class"] == "Returned"].iloc[0]
    completed_row = rf_pc[rf_pc["class"] == "Completed"].iloc[0]

    print(f"  -> RF Cancelled: Precision = {cancelled_row['precision']*100:.2f}%, Recall = {cancelled_row['recall']*100:.2f}%, Support = {cancelled_row['support']}")
    print(f"  -> RF Returned:  Precision = {returned_row['precision']*100:.2f}%, Recall = {returned_row['recall']*100:.2f}%, Support = {returned_row['support']}")
    print(f"  -> RF Completed: Precision = {completed_row['precision']*100:.2f}%, Recall = {completed_row['recall']*100:.2f}%, Support = {completed_row['support']}")

    # Check minority precision is low (exposing ~90% false positive rate)
    assert cancelled_row["precision"] < 0.15, f"Cancelled precision should be ~10%, got {cancelled_row['precision']}"
    assert returned_row["precision"] < 0.15, f"Returned precision should be ~9%, got {returned_row['precision']}"
    print("  -> Passed: Minority class false-positive rates (~90%) accurately reflected in per-class metrics.")

    # -------------------------------------------------------------------------
    # TEST 4: CONFUSION MATRICES ROW AND COLUMN SUM CONSISTENCY
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Verifying Confusion Matrices Integrity...")
    for model_name, safe_name in [("Baseline", "baseline_most_frequent"), ("Random Forest", "random_forest"), ("Logistic Regression", "logistic_regression")]:
        cm_path = REPORT_DIR / f"confusion_{safe_name}.csv"
        cm = pd.read_csv(cm_path, index_col=0)
        assert cm.shape == (3, 3), f"Confusion matrix for {model_name} must be 3x3"
        total_test_instances = cm.values.sum()
        assert total_test_instances == 3417, f"Total test instances must be 3,417, got {total_test_instances}"
        # Row sums must match actual class support (Cancelled=313, Completed=2798, Returned=306)
        assert cm.loc["actual_Cancelled"].sum() == 313
        assert cm.loc["actual_Completed"].sum() == 2798
        assert cm.loc["actual_Returned"].sum() == 306
        print(f"  -> {model_name} confusion matrix verified: 3x3, exactly 3,417 test records.")
    print("  -> Passed: All confusion matrices have correct dimensionalities and row sums.")

    # -------------------------------------------------------------------------
    # TEST 5: HELD-OUT TEST PREDICTIONS EXPLORER DATA
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Verifying Test Predictions Ledger...")
    preds_df = pd.read_csv(REPORT_DIR / "test_predictions.csv")
    assert len(preds_df) == 6834, f"Expected 6,834 prediction rows (3,417 * 2 models), got {len(preds_df)}"
    assert set(preds_df["model"].unique()) == {"Random Forest", "Logistic Regression"}
    assert {"row_index", "timestamp", "actual_status", "predicted_status", "model"}.issubset(preds_df.columns)
    rf_preds = preds_df[preds_df["model"] == "Random Forest"]
    rf_errors = (rf_preds["actual_status"] != rf_preds["predicted_status"]).sum()
    rf_err_rate = rf_errors / len(rf_preds)
    assert abs(rf_err_rate - (1.0 - 0.623646)) < 0.001
    print(f"  -> Random Forest Test Errors: {rf_errors:,} / {len(rf_preds):,} ({rf_err_rate*100:.2f}% error rate)")
    print("  -> Passed: Test prediction records match exact holdout evaluation outputs.")

    # -------------------------------------------------------------------------
    # TEST 6: EXPERIMENT METADATA AUDIT
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Verifying Metadata Audit Schema...")
    meta = json.loads((REPORT_DIR / "model_experiment_metadata.json").read_text(encoding="utf-8"))
    assert meta["target"] == "status"
    assert meta["excluded_status"] == "Pending"
    assert "chronological" in meta["split"].lower()
    assert len(meta["features"]) == 10
    assert "leakage_notes" in meta
    print(f"  -> Target: {meta['target']} | Excluded: {meta['excluded_status']} | Split: {meta['split']}")
    print(f"  -> Verified Features ({len(meta['features'])}): {meta['features']}")
    print("  -> Passed: Metadata schema and leakage disclosures fully validated.")

    # -------------------------------------------------------------------------
    # TEST 7: APP HELPER FUNCTION INTEGRATION
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Verifying app.py Helper Function Integration...")
    import app
    assert hasattr(app, "load_or_calc_per_class_metrics"), "app.py must have load_or_calc_per_class_metrics"
    rf_app_pc = app.load_or_calc_per_class_metrics("Random Forest")
    assert not rf_app_pc.empty
    assert "Cancelled" in rf_app_pc["class"].values
    assert "Completed" in rf_app_pc["class"].values
    assert "Returned" in rf_app_pc["class"].values
    print("  -> Passed: app.py helper function successfully returns per-class metrics.")

    print("\n" + "=" * 70)
    print("ALL 7 PHASE 6 ML VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
