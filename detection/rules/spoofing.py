import duckdb
from config.settings import settings

def detect(trader_id: str, instrument: str) -> dict | None:
    window  = settings.SPOOF_CANCEL_WINDOW_SECS
    min_qty = settings.SPOOF_MIN_ORDER_QTY
    query = """
        WITH cancelled AS (
            SELECT ts FROM trades
            WHERE trader_id=? AND instrument=? AND order_status='cancelled'
              AND quantity >= ? AND ts >= NOW() - INTERVAL (? || ' seconds')
        ),
        following AS (
            SELECT t.trade_id FROM trades t
            JOIN cancelled c ON t.trader_id=? AND t.instrument=?
              AND t.order_status='executed'
              AND t.ts > c.ts
              AND t.ts <= c.ts + INTERVAL (? || ' seconds')
        )
        SELECT COUNT(*) FROM following
    """
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        row = con.execute(query, [
            trader_id, instrument, min_qty, str(window),
            trader_id, instrument, str(window)
        ]).fetchone()
    if not row or row[0] == 0:
        return None
    count = row[0]
    return {
        "pattern":    "spoofing",
        "rule_score": min(50 + count * 20, 98),
        "evidence":   f"{count} large cancel(s) followed by execution within {window}s",
    }
