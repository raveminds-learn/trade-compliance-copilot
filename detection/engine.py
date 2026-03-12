import uuid
import duckdb
from datetime import datetime, timedelta

from config.settings import settings
from config.logger import get_logger
from detection.rules import wash_trade, spoofing
from detection.embeddings.store import embed_sequence, search_similar
from detection.explainer import generate_explanation

log = get_logger("DETECTOR")


def _get_recent_trades(trader_id: str, instrument: str) -> list[dict]:
    query = """
        SELECT trade_id, trader_id, instrument, order_type, quantity, price, order_status
        FROM trades
        WHERE trader_id = ? AND instrument = ?
          AND ts >= NOW() - INTERVAL '60 seconds'
        ORDER BY ts DESC LIMIT 20
    """
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        rows = con.execute(query, [trader_id, instrument]).fetchall()
    cols = ["trade_id", "trader_id", "instrument", "order_type", "quantity", "price", "order_status"]
    return [dict(zip(cols, r)) for r in rows]


def _compute_confidence(rule_score: int, similar: list[dict]) -> int:
    boost = sum(c["similarity"] * 10 for c in similar[:3])
    return min(int(rule_score + boost), 100)


def _route(confidence: int) -> str:
    if confidence < settings.AUTO_CLOSE_BELOW:
        return "auto_closed"
    if confidence >= settings.ESCALATE_ABOVE:
        return "escalated"
    return "queued"


def _sla_deadline(status: str) -> datetime:
    mins = (
        settings.ESCALATED_REVIEW_SLA_MINS
        if status == "escalated"
        else settings.STANDARD_REVIEW_SLA_MINS
    )
    return datetime.utcnow() + timedelta(minutes=mins)


def run_detection(trader_id: str, instrument: str, trade_id: str):
    rule_result = wash_trade.detect(trader_id, instrument) or spoofing.detect(trader_id, instrument)
    if not rule_result:
        return

    recent  = _get_recent_trades(trader_id, instrument)
    if not recent:
        return

    vector     = embed_sequence(recent)
    similar    = search_similar(vector)
    confidence = _compute_confidence(rule_result["rule_score"], similar)
    status     = _route(confidence)

    explanation = generate_explanation(
        pattern=rule_result["pattern"],
        trader_id=trader_id,
        instrument=instrument,
        evidence=rule_result["evidence"],
        confidence=confidence,
        similar_count=len(similar),
    )

    alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
    sla      = _sla_deadline(status) if status != "auto_closed" else None

    with duckdb.connect(str(settings.DUCKDB_PATH)) as con:
        con.execute(
            """INSERT INTO alerts
               (alert_id, trade_id, trader_id, instrument, pattern,
                confidence, explanation, status, sla_deadline, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [alert_id, trade_id, trader_id, instrument,
             rule_result["pattern"], confidence, explanation,
             status, sla, datetime.utcnow()],
        )

    log.info(f"alert {status} — {alert_id} {trader_id} {instrument} score={confidence}")
