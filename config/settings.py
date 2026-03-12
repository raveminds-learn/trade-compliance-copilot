from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DUCKDB_PATH:   Path = BASE_DIR / "data" / "raw" / "trades.db"
    LANCEDB_PATH:  Path = BASE_DIR / "data" / "vectors"
    AUDIT_DB_PATH: Path = BASE_DIR / "data" / "audit" / "audit.db"

    OLLAMA_HOST:  str = "http://ollama:11434"
    OLLAMA_MODEL: str = "mistral"

    WASH_TRADE_WINDOW_SECS:    int   = 30
    WASH_TRADE_PRICE_TOLERANCE: float = 0.005
    SPOOF_CANCEL_WINDOW_SECS:  int   = 10
    SPOOF_MIN_ORDER_QTY:       int   = 1000

    AUTO_CLOSE_BELOW: int = 40
    ESCALATE_ABOVE:   int = 75

    INGEST_INTERVAL_SECS:    int = 30
    SLA_CHECK_INTERVAL_MINS: int = 15
    FEEDBACK_INTERVAL_HOURS: int = 168

    STANDARD_REVIEW_SLA_MINS:  int = 240
    ESCALATED_REVIEW_SLA_MINS: int = 60

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"

settings = Settings()
