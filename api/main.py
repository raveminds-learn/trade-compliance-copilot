from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from alert_queue.manager import (
    get_open_alerts, get_alert_detail, assign_alert,
    submit_decision, get_trader_history, check_sla_breaches
)
from data.schema import init_db
from config.logger import get_logger

log = get_logger("API")

app = FastAPI(title="Trade Compliance Copilot", docs_url="/docs")


@app.on_event("startup")
def startup():
    init_db()
    log.info("API started — db initialised")


class DecisionPayload(BaseModel):
    officer_id: str
    decision:   str   # confirmed | false_positive | escalated
    reason:     str


class AssignPayload(BaseModel):
    officer_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/alerts")
def list_alerts():
    return get_open_alerts()


@app.get("/alerts/{alert_id}")
def alert_detail(alert_id: str):
    alert = get_alert_detail(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="alert not found")
    return alert


@app.post("/alerts/{alert_id}/assign")
def assign(alert_id: str, payload: AssignPayload):
    assign_alert(alert_id, payload.officer_id)
    return {"status": "assigned"}


@app.post("/alerts/{alert_id}/decision")
def decide(alert_id: str, payload: DecisionPayload):
    if not payload.reason.strip():
        raise HTTPException(status_code=400, detail="reason is required")
    submit_decision(alert_id, payload.officer_id, payload.decision, payload.reason)
    return {"status": "recorded"}


@app.get("/traders/{trader_id}/history")
def trader_history(trader_id: str):
    return get_trader_history(trader_id)


@app.post("/sla/check")
def sla_check():
    check_sla_breaches()
    return {"status": "checked"}


@app.post("/admin/reset")
def admin_reset():
    """
    Danger: wipe all trades, alerts, audit trail and vector store.
    Intended for local demos only.
    """
    import shutil
    from pathlib import Path
    from config.settings import settings
    # remove DuckDB files if they exist
    for p in [settings.DUCKDB_PATH, settings.AUDIT_DB_PATH]:
        path = Path(p)
        if path.exists():
            path.unlink()
    # remove LanceDB directory
    lancedb_path = Path(settings.LANCEDB_PATH)
    if lancedb_path.exists():
        shutil.rmtree(lancedb_path)
    # recreate schema and directories
    init_db()
    log.warning("admin reset — all data cleared and schema reinitialised")
    return {"status": "reset"}


@app.get("/audit")
def audit_log(limit: int = 50):
    import duckdb
    from config.settings import settings
    with duckdb.connect(str(settings.AUDIT_DB_PATH), read_only=True) as con:
        rows = con.execute(
            "SELECT * FROM audit_trail ORDER BY recorded_at DESC LIMIT ?", [limit]
        ).fetchall()
        cols = [d[0] for d in con.description]
    return [dict(zip(cols, r)) for r in rows]


@app.get("/stats")
def stats():
    import duckdb
    from config.settings import settings
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        total   = con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        open_   = con.execute("SELECT COUNT(*) FROM alerts WHERE status IN ('queued','escalated','under_review')").fetchone()[0]
        closed  = con.execute("SELECT COUNT(*) FROM alerts WHERE status = 'closed'").fetchone()[0]
        by_pat  = con.execute("SELECT pattern, COUNT(*) FROM alerts GROUP BY pattern").fetchall()
    return {
        "total": total, "open": open_, "closed": closed,
        "by_pattern": {r[0]: r[1] for r in by_pat},
    }
