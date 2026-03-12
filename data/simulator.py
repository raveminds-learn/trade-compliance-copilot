import uuid, random, duckdb
from datetime import datetime
from config.settings import settings
from config.logger import get_logger

log = get_logger("SIMULATOR")

TRADERS     = ["TRD-001","TRD-002","TRD-003","TRD-004","TRD-005"]
INSTRUMENTS = ["AAPL","MSFT","GOOGL","AMZN","TSLA","JPM","GS"]
BASE_PRICES = {"AAPL":182,"MSFT":415,"GOOGL":178,"AMZN":195,"TSLA":245,"JPM":198,"GS":478}

def _normal_trade() -> dict:
    instr = random.choice(INSTRUMENTS)
    return {
        "trade_id":     f"T-{uuid.uuid4().hex[:8].upper()}",
        "trader_id":    random.choice(TRADERS),
        "instrument":   instr,
        "order_type":   random.choice(["buy","sell"]),
        "quantity":     random.randint(100, 500),
        "price":        round(BASE_PRICES[instr] * random.uniform(0.995, 1.005), 2),
        "order_status": random.choices(["executed","cancelled"], weights=[85,15])[0],
        "ts":           datetime.utcnow(),
    }

def _wash_pair(trader_id, instrument) -> list:
    price = round(BASE_PRICES[instrument] * random.uniform(0.999, 1.001), 2)
    base  = {"trader_id":trader_id,"instrument":instrument,"quantity":random.randint(400,800),
             "price":price,"order_status":"executed","ts":datetime.utcnow()}
    return [
        {**base, "trade_id": f"T-{uuid.uuid4().hex[:8].upper()}", "order_type": "buy"},
        {**base, "trade_id": f"T-{uuid.uuid4().hex[:8].upper()}", "order_type": "sell"},
    ]

def _spoof_seq(trader_id, instrument) -> list:
    p = BASE_PRICES[instrument]
    return [
        {"trade_id":f"T-{uuid.uuid4().hex[:8].upper()}","trader_id":trader_id,"instrument":instrument,
         "order_type":"buy","quantity":random.randint(2000,5000),"price":round(p*1.002,2),
         "order_status":"cancelled","ts":datetime.utcnow()},
        {"trade_id":f"T-{uuid.uuid4().hex[:8].upper()}","trader_id":trader_id,"instrument":instrument,
         "order_type":"sell","quantity":random.randint(200,600),"price":round(p*0.998,2),
         "order_status":"executed","ts":datetime.utcnow()},
    ]

def generate_batch(size: int = 5) -> list:
    trades, roll = [], random.random()
    if roll < 0.08:
        t, i = random.choice(TRADERS), random.choice(INSTRUMENTS)
        trades.extend(_wash_pair(t, i))
        log.info(f"injected wash trade — {t} {i}")
    elif roll < 0.15:
        t, i = random.choice(TRADERS), random.choice(INSTRUMENTS)
        trades.extend(_spoof_seq(t, i))
        log.info(f"injected spoof — {t} {i}")
    while len(trades) < size:
        trades.append(_normal_trade())
    return trades

def ingest_batch() -> list:
    trades = generate_batch()
    with duckdb.connect(str(settings.DUCKDB_PATH)) as con:
        con.executemany(
            "INSERT OR IGNORE INTO trades VALUES (?,?,?,?,?,?,?,?)",
            [(t["trade_id"],t["trader_id"],t["instrument"],t["order_type"],
              t["quantity"],t["price"],t["order_status"],t["ts"]) for t in trades]
        )
    log.info(f"ingested {len(trades)} trades")
    return trades
