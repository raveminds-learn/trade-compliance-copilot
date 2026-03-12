import uuid
import duckdb
from datetime import datetime
from config.settings import settings
from config.logger import get_logger

log = get_logger("QUEUE")


def get_open_alerts() -> list[dict]:
    query = """
        SELECT alert_id, trader_id, instrument, pattern, confidence,
               status, assigned_to, created_at, sla_deadline
        FROM alerts
        WHERE status IN ('queued', 'escalated', 'under_review')
        ORDER BY confidence DESC, created_at ASC
    """
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        rows = con.execute(query).fetchall()
    cols = ["alert_id", "trader_id", "instrument", "pattern", "confidence",
            "status", "assigned_to", "created_at", "sla_deadline"]
    return [dict(zip(cols, r)) for r in rows]


def get_alert_detail(alert_id: str) -> dict | None:
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        row = con.execute(
            "SELECT * FROM alerts WHERE alert_id = ?", [alert_id]
        ).fetchone()
    if not row:
        return None
    cols = [d[0] for d in con.description] if False else [
        "alert_id", "trade_id", "trader_id", "instrument", "pattern",
        "confidence", "explanation", "status", "assigned_to", "assigned_at",
        "decided_at", "decision", "decision_reason", "created_at", "sla_deadline"
    ]
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        row = con.execute("SELECT * FROM alerts WHERE alert_id = ?", [alert_id]).fetchone()
    return dict(zip(cols, row)) if row else None


def assign_alert(alert_id: str, officer_id: str):
    with duckdb.connect(str(settings.DUCKDB_PATH)) as con:
        con.execute(
            """UPDATE alerts
               SET status = 'under_review', assigned_to = ?, assigned_at = ?
               WHERE alert_id = ? AND status IN ('queued', 'escalated')""",
            [officer_id, datetime.utcnow(), alert_id],
        )
    log.info(f"alert assigned — {alert_id} → {officer_id}")


def submit_decision(alert_id: str, officer_id: str, decision: str, reason: str):
    now = datetime.utcnow()

    with duckdb.connect(str(settings.DUCKDB_PATH)) as con:
        row = con.execute(
            "SELECT trade_id, trader_id, instrument, pattern, confidence, assigned_at FROM alerts WHERE alert_id = ?",
            [alert_id]
        ).fetchone()

        if not row:
            raise ValueError(f"alert {alert_id} not found")

        trade_id, trader_id, instrument, pattern, confidence, assigned_at = row
        elapsed = int((now - assigned_at).total_seconds()) if assigned_at else 0

        con.execute(
            """UPDATE alerts
               SET status = 'closed', decision = ?, decision_reason = ?, decided_at = ?
               WHERE alert_id = ?""",
            [decision, reason, now, alert_id],
        )

    # write immutable audit record
    with duckdb.connect(str(settings.AUDIT_DB_PATH)) as con:
        con.execute(
            """INSERT INTO audit_trail
               (id, alert_id, trade_id, trader_id, instrument, officer_id, decision,
                decision_reason, confidence_at_decision, pattern,
                time_to_decision_secs, recorded_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [f"AUD-{uuid.uuid4().hex[:8].upper()}", alert_id, trade_id,
             trader_id, instrument, officer_id, decision, reason, confidence,
             pattern, elapsed, now],
        )

    log.info(f"decision recorded — {alert_id} {decision} by {officer_id} in {elapsed}s")


def get_trader_history(trader_id: str, limit: int = 20) -> list[dict]:
    query = """
        SELECT alert_id, instrument, pattern, confidence, status, decision, created_at
        FROM alerts
        WHERE trader_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        rows = con.execute(query, [trader_id, limit]).fetchall()
    cols = ["alert_id", "instrument", "pattern", "confidence", "status", "decision", "created_at"]
    return [dict(zip(cols, r)) for r in rows]


def check_sla_breaches():
    query = """
        SELECT alert_id, status, sla_deadline
        FROM alerts
        WHERE status IN ('queued', 'escalated', 'under_review')
          AND sla_deadline IS NOT NULL
          AND sla_deadline < NOW()
    """
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        rows = con.execute(query).fetchall()

    for alert_id, status, deadline in rows:
        if status != "escalated":
            with duckdb.connect(str(settings.DUCKDB_PATH)) as con:
                con.execute(
                    "UPDATE alerts SET status = 'escalated' WHERE alert_id = ?",
                    [alert_id]
                )
            log.warning(f"SLA breached — {alert_id} escalated")
