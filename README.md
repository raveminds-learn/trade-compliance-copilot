# Trade Compliance Copilot

AI-assisted trade surveillance for detecting wash trading and spoofing. Compliance officers review AI-flagged alerts, make decisions with mandatory reasoning, and the system learns from those decisions over time. 100% local, zero API cost.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | 4.x+ | https://docker.com/products/docker-desktop |
| RAM | 8 GB minimum | required for Mistral 7B |
| Disk | 10 GB free | for model + data storage |

---

## Quick Start

```bash
git clone https://github.com/raveminds-learn/trade-compliance-copilot.git
cd trade-compliance-copilot

# start everything — first run downloads Mistral (~4 GB)
docker-compose up

# stop
docker-compose down

# wipe all data and restart fresh
docker-compose down -v && docker-compose up
```

| Service   | URL |
|-----------|-----|
| Dashboard | http://localhost:8501 |
| API docs  | http://localhost:8000/docs |
| Ollama    | http://localhost:11434 |

First startup: 3–5 min (model download). Subsequent starts: ~20 sec.

---

## Project Structure

```
trade-compliance-copilot/
├── app.py                     # entry point — API + scheduler
├── config/
│   ├── settings.py            # all config via env vars
│   └── logger.py              # shared logger
├── data/
│   ├── schema.py              # DuckDB schema + init
│   └── simulator.py           # trade stream generator
├── detection/
│   ├── engine.py              # detection orchestrator
│   ├── explainer.py           # Mistral explanation via Ollama
│   ├── rules/
│   │   ├── wash_trade.py      # buy/sell pair rule
│   │   └── spoofing.py        # large cancel + execution rule
│   └── embeddings/
│       └── store.py           # LanceDB vector operations
├── queue/
│   └── manager.py             # alert lifecycle + audit writes
├── api/
│   └── main.py                # FastAPI endpoints
├── ui/
│   └── dashboard.py           # Streamlit dashboard
├── feedback/
│   └── processor.py           # weekly calibration job
├── docker-compose.yml
├── Dockerfile.app
├── Dockerfile.ui
├── requirements.app.txt
├── requirements.ui.txt
└── .env
```

---

## How It Works

1. **Ingest** — trades generated every 8s, stored in DuckDB
2. **Detect** — rules + embeddings score each trade cluster (0–100)
3. **Route** — `< 40` auto-close · `40–75` queue · `> 75` escalate
4. **Review** — officer sees alert, AI explanation, trader history; submits decision with mandatory reason
5. **Audit** — every decision written to immutable audit trail
6. **Feedback** — weekly job calibrates scoring from officer decisions; confirmed cases added to LanceDB

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `mistral` | LLM model |
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama URL |
| `INGEST_INTERVAL_SECS` | `8` | Simulation tick |
| `AUTO_CLOSE_BELOW` | `40` | Auto-close threshold |
| `ESCALATE_ABOVE` | `75` | Escalation threshold |
| `WASH_TRADE_WINDOW_SECS` | `30` | Wash trade detection window |
| `SPOOF_CANCEL_WINDOW_SECS` | `10` | Spoofing detection window |
| `STANDARD_REVIEW_SLA_MINS` | `240` | Standard review SLA (4h) |
| `ESCALATED_REVIEW_SLA_MINS` | `60` | Escalated review SLA (1h) |

---

## Manual Setup (no Docker)

```bash
# install Ollama — https://ollama.com
ollama pull mistral

# set local Ollama host in .env
OLLAMA_HOST=http://localhost:11434

# terminal 1 — API + scheduler
pip install -r requirements.app.txt
python app.py

# terminal 2 — dashboard
pip install -r requirements.ui.txt
streamlit run ui/dashboard.py
```

---

*RaveMinds Series 2 · Chapter 5 · Practical Local AI for Fintech*
