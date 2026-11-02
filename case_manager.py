"""
case_manager.py - Persistent SQLite Investigation Case Management Layer for LeakLens - AI.
Provides ACID-compliant, persistent storage, input validation, duplicate prevention,
status lifecycle management, and audit tracking across application restarts.
"""

from pathlib import Path
import shutil
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
import pandas as pd

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)
DB_PATH = REPORT_DIR / "leaklens_cases.db"

# Legacy fallback / migration
_legacy_db = REPORT_DIR / "margintracer_cases.db"
if not DB_PATH.exists() and _legacy_db.exists():
    try:
        shutil.copy2(_legacy_db, DB_PATH)
    except Exception:
        pass


def get_db_connection() -> sqlite3.Connection:
    """Create a thread-safe connection to the SQLite database with row factory."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize cases table and required indexes if they do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS investigation_cases (
                case_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                evidence_reference TEXT,
                affected_record_count INTEGER DEFAULT 0,
                exposure_estimate REAL DEFAULT 0.0,
                priority TEXT NOT NULL CHECK(priority IN ('Critical', 'High', 'Medium', 'Low')),
                owner TEXT NOT NULL,
                next_action TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Open', 'Investigating', 'Resolved', 'Dismissed')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                notes TEXT,
                resolution_notes TEXT
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON investigation_cases(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_priority ON investigation_cases(priority);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_category ON investigation_cases(category);")
        conn.commit()


def generate_case_id() -> str:
    """Generate a clean, collision-free, date-prefixed case identifier."""
    date_str = time.strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:5].upper()
    return f"CASE-{date_str}-{short_uuid}"


def check_duplicate_case(title: str, evidence_ref: str) -> Optional[str]:
    """Check if an open or active case with identical title and evidence reference already exists."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT case_id FROM investigation_cases 
            WHERE LOWER(title) = LOWER(?) 
              AND LOWER(evidence_reference) = LOWER(?)
              AND status IN ('Open', 'Investigating');
            """,
            (title.strip(), evidence_ref.strip()),
        )
        row = cursor.fetchone()
        return row["case_id"] if row else None


def create_case(
    title: str,
    category: str,
    description: str,
    evidence_reference: str,
    affected_record_count: int,
    exposure_estimate: float,
    priority: str,
    owner: str,
    next_action: str,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Validate and insert a new investigation case.
    Returns dictionary with status and case_id or error message.
    """
    init_db()

    # Input validations
    if not title or not title.strip():
        return {"success": False, "error": "Case title is required."}
    if not next_action or not next_action.strip():
        return {"success": False, "error": "Immediate next action is required."}

    valid_priorities = ["Critical", "High", "Medium", "Low"]
    if priority not in valid_priorities:
        priority = "Medium"

    # Enforce non-negative exposure and count
    exposure_estimate = max(0.0, float(exposure_estimate or 0.0))
    affected_record_count = max(0, int(affected_record_count or 0))

    # Duplicate safeguard
    existing_id = check_duplicate_case(title, evidence_reference)
    if existing_id:
        return {
            "success": False,
            "error": f"An active investigation case ({existing_id}) already exists with this title and evidence reference.",
            "existing_id": existing_id,
        }

    case_id = generate_case_id()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO investigation_cases (
                case_id, title, category, description, evidence_reference,
                affected_record_count, exposure_estimate, priority, owner,
                next_action, status, created_at, updated_at, notes, resolution_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                case_id,
                title.strip(),
                category.strip(),
                description.strip() if description else "",
                evidence_reference.strip() if evidence_reference else "N/A",
                affected_record_count,
                exposure_estimate,
                priority,
                owner.strip() if owner else "Unassigned",
                next_action.strip(),
                "Open",
                now_str,
                now_str,
                notes.strip() if notes else "",
                "",
            ),
        )
        conn.commit()

    return {"success": True, "case_id": case_id}


def update_case(
    case_id: str,
    status: str,
    next_action: Optional[str] = None,
    owner: Optional[str] = None,
    priority: Optional[str] = None,
    additional_notes: str = "",
    resolution_notes: str = "",
) -> Dict[str, Any]:
    """Update case status, owner, next action, priority, and append audit notes."""
    init_db()

    valid_statuses = ["Open", "Investigating", "Resolved", "Dismissed"]
    if status not in valid_statuses:
        return {"success": False, "error": f"Invalid status: {status}"}

    valid_priorities = ["Critical", "High", "Medium", "Low"]

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM investigation_cases WHERE case_id = ?;", (case_id,))
        case = cursor.fetchone()
        if not case:
            return {"success": False, "error": f"Case {case_id} not found."}

        final_priority = priority if (priority and priority in valid_priorities) else case["priority"]
        final_owner = owner.strip() if (owner and owner.strip()) else case["owner"]
        final_next_action = next_action.strip() if (next_action and next_action.strip()) else case["next_action"]

        existing_notes = case["notes"] or ""
        updated_notes = existing_notes
        if additional_notes and additional_notes.strip():
            audit_entry = f"\n[{now_str} Update by {final_owner}]: {additional_notes.strip()}"
            updated_notes = (existing_notes + audit_entry).strip()

        cursor.execute(
            """
            UPDATE investigation_cases SET
                status = ?,
                next_action = ?,
                owner = ?,
                priority = ?,
                notes = ?,
                resolution_notes = CASE WHEN ? != '' THEN ? ELSE resolution_notes END,
                updated_at = ?
            WHERE case_id = ?;
            """,
            (
                status,
                final_next_action,
                final_owner,
                final_priority,
                updated_notes,
                resolution_notes.strip(),
                resolution_notes.strip(),
                now_str,
                case_id,
            ),
        )
        conn.commit()

    return {"success": True, "case_id": case_id}


def get_all_cases() -> pd.DataFrame:
    """Fetch all cases as a Pandas DataFrame safely."""
    init_db()
    with get_db_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM investigation_cases ORDER BY created_at DESC;", conn)
    return df


def get_case(case_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve details for a specific case ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM investigation_cases WHERE case_id = ?;", (case_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# Pre-configured findings templates from Phase 3 detection engine
DETECTED_FINDINGS = {
    "finding_1": {
        "title": "Finding 1: Chronic Product Return Outliers",
        "category": "Product Quality & Return Risk",
        "description": "5 products with return rates >= 15% (PR0208, PR0075, PR0066, PR0198, PR0138) with 54 returned orders out of 320 total orders across these SKUs.",
        "evidence_reference": "reports/leak_high_return_products.csv",
        "affected_record_count": 54,
        "exposure_estimate": 37310.88,
        "default_priority": "High",
        "default_next_action": "Audit storefront dimension charts, customer reviews, and supplier return SLAs for flagged SKUs.",
    },
    "finding_2": {
        "title": "Finding 2: Repeat Cancellation & Return Customer Accounts",
        "category": "Customer Policy Abuse & Churn Risk",
        "description": "53 customer accounts with >= 4 non-completed orders (Cancelled + Returned), totaling 228 leak orders.",
        "evidence_reference": "reports/leak_repeat_customers.csv",
        "affected_record_count": 228,
        "exposure_estimate": 116669.91,
        "default_priority": "Medium",
        "default_next_action": "Correlate return frequency with customer LTV and introduce checkout confirmation friction for accounts with >3 cancellations.",
    },
    "finding_3": {
        "title": "Finding 3: Maximum 25% Discount Outlier Cluster",
        "category": "Pricing Governance & Margin Erosion",
        "description": "912 transactions receiving maximum allowable 25% discount tier, totaling $102,195.66 in discount concessions ($80,565.40 on completed orders).",
        "evidence_reference": "reports/leak_max_discount_transactions.csv",
        "affected_record_count": 912,
        "exposure_estimate": 102195.66,
        "default_priority": "Medium",
        "default_next_action": "Audit coupon voucher authorization ledger to ensure 25% discounts were authorized promo codes.",
    },
    "finding_4": {
        "title": "Finding 4: Catalog Price < Unit Cost Inconsistencies",
        "category": "Catalog Master Data Inconsistency",
        "description": "76 catalog products where list_price < unit_cost across 5,315 completed sales ($1.21M theoretical shortfall; synthetic modeling artifact per README).",
        "evidence_reference": "reports/product_price_cost_anomalies.csv",
        "affected_record_count": 5315,
        "exposure_estimate": 1214115.50,
        "default_priority": "Low",
        "default_next_action": "Verify catalog master ingestion pipeline and review supplier cost formulas; do not allege employee fraud.",
    },
    "finding_5": {
        "title": "Finding 5: Supply Chain Bottlenecks & Critical Reorder Violations",
        "category": "Supply Chain & Stockout Vulnerability",
        "description": "229 warehouse records across 143 SKUs where stock on hand is below reorder threshold with supplier delay >= 14 days (10 SKUs at zero stock).",
        "evidence_reference": "reports/leak_critical_inventory.csv",
        "affected_record_count": 229,
        "exposure_estimate": 25000.00,
        "default_priority": "High",
        "default_next_action": "Expedite emergency POs with priority freight for the 229 flagged SKUs; trigger supplier contract penalty reviews.",
    },
    "finding_6": {
        "title": "Finding 6: Credit Card Payment Method Cancellation Spikes",
        "category": "Payment Instrument & Checkout Friction",
        "description": "360 credit card transactions cancelled at checkout (9.93% cancellation rate vs ~9% for UPI/Cash).",
        "evidence_reference": "reports/leak_card_cancellations.csv",
        "affected_record_count": 360,
        "exposure_estimate": 176726.81,
        "default_priority": "Low",
        "default_next_action": "Analyze payment gateway webhook response codes (3DS timeouts, decline reasons) to optimize retry prompts.",
    },
}


def create_case_from_finding_template(
    finding_key: str,
    owner: str = "Investigation Taskforce",
    priority: Optional[str] = None,
    custom_notes: str = "",
) -> Dict[str, Any]:
    """Helper to create an investigation case directly from a pre-configured finding."""
    if finding_key not in DETECTED_FINDINGS:
        return {"success": False, "error": f"Finding template '{finding_key}' not recognized."}

    template = DETECTED_FINDINGS[finding_key]
    case_priority = priority or template["default_priority"]
    notes = custom_notes if custom_notes else f"Auto-created from detected finding: {template['title']}."

    return create_case(
        title=template["title"],
        category=template["category"],
        description=template["description"],
        evidence_reference=template["evidence_reference"],
        affected_record_count=template["affected_record_count"],
        exposure_estimate=template["exposure_estimate"],
        priority=case_priority,
        owner=owner,
        next_action=template["default_next_action"],
        notes=notes,
    )


def delete_case(case_id: str) -> Dict[str, Any]:
    """Safely delete a case by case_id."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT case_id FROM investigation_cases WHERE case_id = ?;", (case_id,))
        if not cursor.fetchone():
            return {"success": False, "error": f"Case {case_id} not found."}
        cursor.execute("DELETE FROM investigation_cases WHERE case_id = ?;", (case_id,))
        conn.commit()
    return {"success": True, "case_id": case_id}


def get_case_statistics() -> Dict[str, Any]:
    """Return summary count metrics and exposure for the investigation case tracker."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total, SUM(exposure_estimate) AS total_exposure FROM investigation_cases;")
        tot_row = cursor.fetchone()
        total_cases = tot_row["total"] or 0
        total_exposure = tot_row["total_exposure"] or 0.0

        cursor.execute("SELECT status, COUNT(*) AS count FROM investigation_cases GROUP BY status;")
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT priority, COUNT(*) AS count FROM investigation_cases GROUP BY priority;")
        priority_counts = {row["priority"]: row["count"] for row in cursor.fetchall()}

    return {
        "total_cases": total_cases,
        "total_exposure": total_exposure,
        "open_count": status_counts.get("Open", 0),
        "investigating_count": status_counts.get("Investigating", 0),
        "resolved_count": status_counts.get("Resolved", 0),
        "dismissed_count": status_counts.get("Dismissed", 0),
        "status_counts": status_counts,
        "priority_counts": priority_counts,
    }


# Initialize on import
init_db()
