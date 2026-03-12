import json, lancedb, numpy as np
from sentence_transformers import SentenceTransformer
from config.settings import settings
from config.logger import get_logger

log = get_logger("EMBEDDINGS")
_model = None
_TABLE = "trade_patterns"

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model

def embed_sequence(trades: list[dict]) -> np.ndarray:
    text = " | ".join(
        f"{t['order_type']} {t['instrument']} qty={t['quantity']} price={t['price']} status={t['order_status']}"
        for t in trades
    )
    return _get_model().encode(text)

def search_similar(vector: np.ndarray, top_k: int = 5) -> list[dict]:
    db = lancedb.connect(str(settings.LANCEDB_PATH))
    if _TABLE not in db.table_names():
        return []
    results = db.open_table(_TABLE).search(vector.tolist()).limit(top_k).to_list()
    return [
        {"alert_id": r.get("alert_id"), "pattern": r.get("pattern"),
         "similarity": round(1 - r.get("_distance", 1), 3)}
        for r in results if r.get("_distance", 1) < 0.5
    ]

def store_confirmed(alert_id: str, pattern: str, trades: list[dict], outcome: str):
    vector = embed_sequence(trades)
    db     = lancedb.connect(str(settings.LANCEDB_PATH))
    record = {"vector": vector.tolist(), "alert_id": alert_id,
              "pattern": pattern, "outcome": outcome,
              "metadata": json.dumps({"count": len(trades)})}
    if _TABLE in db.table_names():
        db.open_table(_TABLE).add([record])
    else:
        db.create_table(_TABLE, data=[record])
    log.info(f"pattern stored — {alert_id} {pattern}")
