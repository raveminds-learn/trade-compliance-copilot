import duckdb
from config.settings import settings

TRADES_DDL = """
CREATE TABLE IF NOT EXISTS trades (
    trade_id     VARCHAR PRIMARY KEY,
    trader_id    VARCHAR NOT NULL,
    instrument   VARCHAR NOT NULL,
    order_type   VARCHAR NOT NULL,
    quantity     INTEGER NOT NULL,
    price        DOUBLE NOT NULL,
    order_status VARCHAR NOT NULL,
    ts           TIMESTAMP NOT NULL
)"""

ALERTS_DDL = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id        VARCHAR PRIMARY KEY,
    trade_id        VARCHAR NOT NULL,
    trader_id       VARCHAR NOT NULL,
    instrument      VARCHAR NOT NULL,
    pattern         VARCHAR NOT NULL,
    confidence      INTEGER NOT NULL,
    explanation     TEXT,
    status          VARCHAR DEFAULT 'queued',
    assigned_to     VARCHAR,
    assigned_at     TIMESTAMP,
    decided_at      TIMESTAMP,
    decision        VARCHAR,
    decision_reason TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sla_deadline    TIMESTAMP
)"""

AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS audit_trail (
    id                      VARCHAR PRIMARY KEY,
    alert_id                VARCHAR NOT NULL,
    trade_id                VARCHAR NOT NULL,
    trader_id               VARCHAR NOT NULL,
    instrument              VARCHAR NOT NULL,
    officer_id              VARCHAR NOT NULL,
    decision                VARCHAR NOT NULL,
    decision_reason         TEXT NOT NULL,
    confidence_at_decision  INTEGER NOT NULL,
    pattern                 VARCHAR NOT NULL,
    time_to_decision_secs   INTEGER,
    recorded_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

def init_db():
    settings.DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings.AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings.LANCEDB_PATH.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(settings.DUCKDB_PATH)) as con:
        con.execute(TRADES_DDL)
        con.execute(ALERTS_DDL)

    with duckdb.connect(str(settings.AUDIT_DB_PATH)) as con:
        con.execute(AUDIT_DDL)
        cols = [r[0] for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'audit_trail'"
        ).fetchall()]
        if "instrument" not in cols:
            con.execute("ALTER TABLE audit_trail ADD COLUMN instrument VARCHAR DEFAULT ''")
