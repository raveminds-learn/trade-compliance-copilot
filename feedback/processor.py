import duckdb
from config.settings import settings
from config.logger import get_logger
from detection.embeddings.store import store_confirmed

log = get_logger("FEEDBACK")


def run_feedback():
    log.info("feedback run started")

    with duckdb.connect(str(settings.AUDIT_DB_PATH), read_only=True) as con:
        rows = con.execute("""
            SELECT alert_id, trader_id, instrument, pattern,
                   decision, confidence_at_decision
            FROM audit_trail
            WHERE recorded_at >= NOW() - INTERVAL '7 days'
        """).fetchall()

    if not rows:
        log.info("feedback run — no records in window")
        return

    false_positives  = [r for r in rows if r[4] == "false_positive"  and r[5] >= settings.AUTO_CLOSE_BELOW]
    missed_detections = [r for r in rows if r[4] == "confirmed"       and r[5] < settings.AUTO_CLOSE_BELOW]
    confirmed        = [r for r in rows if r[4] == "confirmed"]

    log.info(f"feedback — {len(confirmed)} confirmed, {len(false_positives)} FP, {len(missed_detections)} missed")

    # store confirmed cases back into LanceDB to grow the pattern library
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        for r in confirmed:
            alert_id, trader_id, instrument, pattern = r[0], r[1], r[2], r[3]
            trades = con.execute(
                """SELECT trade_id, trader_id, instrument, order_type,
                          quantity, price, order_status
                   FROM trades
                   WHERE trader_id = ? AND instrument = ?
                     AND ts >= (SELECT created_at FROM alerts WHERE alert_id = ?) - INTERVAL '60 seconds'
                     AND ts <= (SELECT created_at FROM alerts WHERE alert_id = ?) + INTERVAL '60 seconds'
                   LIMIT 20""",
                [trader_id, instrument, alert_id, alert_id]
            ).fetchall()

            if trades:
                cols = ["trade_id","trader_id","instrument","order_type","quantity","price","order_status"]
                trade_dicts = [dict(zip(cols, t)) for t in trades]
                store_confirmed(alert_id, pattern, trade_dicts, "confirmed")

    # log calibration signals for manual threshold review
    if false_positives:
        avg_fp_score = sum(r[5] for r in false_positives) / len(false_positives)
        log.warning(f"calibration signal — avg false positive score: {avg_fp_score:.1f} (consider raising AUTO_CLOSE_BELOW)")

    if missed_detections:
        avg_miss_score = sum(r[5] for r in missed_detections) / len(missed_detections)
        log.warning(f"calibration signal — avg missed detection score: {avg_miss_score:.1f} (consider lowering ESCALATE_ABOVE)")

    log.info("feedback run complete")
