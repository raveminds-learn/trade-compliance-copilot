import duckdb
from config.settings import settings

def detect(trader_id: str, instrument: str) -> dict | None:
    window = settings.WASH_TRADE_WINDOW_SECS
    tol    = settings.WASH_TRADE_PRICE_TOLERANCE
    query = """
        WITH recent AS (
            SELECT order_type, price FROM trades
            WHERE trader_id=? AND instrument=? AND order_status='executed'
              AND ts >= NOW() - INTERVAL (? || ' seconds')
        ),
        buys  AS (SELECT price FROM recent WHERE order_type='buy'),
        sells AS (SELECT price FROM recent WHERE order_type='sell')
        SELECT COUNT(*) AS pairs,
               AVG(ABS(b.price-s.price)/b.price) AS avg_diff
        FROM buys b JOIN sells s ON ABS(b.price-s.price)/b.price < ?
    """
    with duckdb.connect(str(settings.DUCKDB_PATH), read_only=True) as con:
        row = con.execute(query, [trader_id, instrument, str(window), tol]).fetchone()
    if not row or row[0] == 0:
        return None
    pairs, avg_diff = row
    return {
        "pattern":    "wash_trade",
        "rule_score": min(40 + pairs * 15, 95),
        "evidence":   f"{pairs} buy/sell pair(s) within {window}s, avg diff {avg_diff:.4f}",
    }
