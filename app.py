import time
import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from data.schema import init_db
from data.simulator import ingest_batch
from detection.engine import run_detection
from alert_queue.manager import check_sla_breaches
from feedback.processor import run_feedback
from config.settings import settings
from config.logger import get_logger
from api.main import app

log = get_logger("APP")


def ingest_and_detect():
    trades = ingest_batch()
    for t in trades:
        run_detection(t["trader_id"], t["instrument"], t["trade_id"])


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(ingest_and_detect,  "interval", seconds=settings.INGEST_INTERVAL_SECS)
    scheduler.add_job(check_sla_breaches, "interval", minutes=settings.SLA_CHECK_INTERVAL_MINS)
    scheduler.add_job(run_feedback,       "interval", hours=settings.FEEDBACK_INTERVAL_HOURS)
    scheduler.start()
    log.info("scheduler started — ingest, SLA watchdog, feedback loop")
    return scheduler


if __name__ == "__main__":
    init_db()
    log.info("database initialised")

    # wait for Ollama to be ready
    import requests
    for attempt in range(12):
        try:
            requests.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=3)
            log.info("Ollama ready")
            break
        except Exception:
            log.info(f"waiting for Ollama ({attempt + 1}/12)")
            time.sleep(5)

    scheduler = start_scheduler()

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="warning",
    )
