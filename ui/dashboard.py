import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

API = "http://api:8000"
LOGO_PATH = Path(__file__).parent / "rm_logo_transparent.png"

st.set_page_config(
    page_title="Trade Compliance Copilot",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #060d14; }
[data-testid="stSidebar"]          { background: #0b1520; border-right: 1px solid #1a2d42; }
.stButton > button                 { background: #1b7fe0; color: white; border: none; border-radius: 3px; font-weight: 600; }
.stButton > button:hover           { background: #1569c7; }
h1,h2,h3   { color: #eef4fa !important; }
p, label   { color: #c8daea; }
.stTextArea textarea { background: #0b1520; color: #c8daea; border: 1px solid #1a2d42; }
hr { border-color: #1a2d42; }
</style>
""", unsafe_allow_html=True)


def api_get(path):
    try:
        r = requests.get(f"{API}{path}", timeout=5)
        return r.json() if r.ok else None
    except Exception:
        return None


def api_post(path, payload):
    try:
        r = requests.post(f"{API}{path}", json=payload, timeout=10)
        if r.ok:
            return r.json() if r.text else {}
        try:
            err = r.json()
            return {"_error": err.get("detail", r.text or "Request failed")}
        except Exception:
            return {"_error": r.text or f"Error {r.status_code}"}
    except Exception as e:
        return {"_error": str(e)}


def score_color(score):
    if score >= 75: return "#e05555"
    if score >= 40: return "#f5a623"
    return "#3dd68c"


def confidence_gauge(score):
    color = score_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis":  {"range": [0, 100], "tickcolor": "#3a5068"},
            "bar":   {"color": color},
            "bgcolor": "#0b1520",
            "bordercolor": "#1a2d42",
            "steps": [
                {"range": [0, 40],   "color": "#0d1e0d"},
                {"range": [40, 75],  "color": "#1e1800"},
                {"range": [75, 100], "color": "#1e0808"},
            ],
        },
        number={"font": {"color": color, "size": 40}},
    ))
    fig.update_layout(
        height=180, margin=dict(t=10, b=10, l=20, r=20),
        paper_bgcolor="#060d14", font_color="#c8daea",
    )
    return fig


# ── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=100)
    st.markdown("### ⚖ Compliance Copilot")
    st.markdown("---")
    officer_id = st.text_input("Officer ID", value="officer-01")
    st.markdown("---")
    page = st.radio("View", ["Alert Queue", "Review Alert", "Audit Trail", "Statistics", "Admin"])
    st.markdown("---")
    stats = api_get("/stats") or {}
    col_a, col_b = st.columns(2)
    col_a.metric("Open",  stats.get("open", "—"))
    col_b.metric("Closed", stats.get("closed", "—"))


# ── alert queue ───────────────────────────────────────────────────────────────
if page == "Alert Queue":
    st.markdown("## Alert Queue")
    alerts = api_get("/alerts") or []

    if not alerts:
        st.info("No open alerts.")
    else:
        for a in alerts:
            c1, c2, c3, c4, c5 = st.columns([2.5, 2, 2, 1, 1])
            with c1:
                st.markdown(f"**{a['alert_id']}**")
                st.caption(f"{a['trader_id']} · {a['instrument']}")
            with c2:
                st.code(a["pattern"].replace("_", " ").upper(), language=None)
            with c3:
                color = {"escalated": "#e05555", "under_review": "#1b7fe0"}.get(a["status"], "#f5a623")
                st.markdown(f'<span style="color:{color};font-weight:700">{a["status"].upper()}</span>', unsafe_allow_html=True)
            with c4:
                c = score_color(a["confidence"])
                st.markdown(f'<span style="color:{c};font-size:22px;font-weight:700">{a["confidence"]}</span>', unsafe_allow_html=True)
            with c5:
                if st.button("Review", key=a["alert_id"]):
                    st.session_state["selected_alert"] = a["alert_id"]
                    st.rerun()
            st.divider()


# ── review alert ──────────────────────────────────────────────────────────────
elif page == "Review Alert":
    # Load open alerts for dropdown selection
    alerts_for_select = api_get("/alerts") or []
    options = [a["alert_id"] for a in alerts_for_select]

    default_alert = st.session_state.get("selected_alert")
    index = options.index(default_alert) if default_alert in options else 0 if options else None

    col_sel, col_input = st.columns([2, 1])
    with col_sel:
        selected_from_list = st.selectbox(
            "Select Alert",
            options,
            index=index if index is not None else 0,
            format_func=lambda aid: next(
                (f"{aid} · {a['trader_id']} · {a['instrument']}" for a in alerts_for_select if a["alert_id"] == aid),
                aid,
            ) if alerts_for_select else aid,
        ) if options else None
    with col_input:
        manual_id = st.text_input("Or enter Alert ID", value=default_alert or "")

    alert_id = selected_from_list or manual_id.strip()

    if not alert_id:
        st.info("Select an alert from the queue or choose one above.")
        st.stop()

    alert = api_get(f"/alerts/{alert_id}")
    if not alert:
        st.error("Alert not found.")
        st.stop()

    if alert["status"] in ("queued", "escalated"):
        api_post(f"/alerts/{alert_id}/assign", {"officer_id": officer_id})

    st.markdown(f"## {alert_id}")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Trader:** `{alert['trader_id']}`")
        st.markdown(f"**Instrument:** `{alert['instrument']}`")
        st.markdown(f"**Pattern:** `{alert['pattern'].replace('_', ' ').upper()}`")
    with c2:
        sc = {"escalated": "#e05555", "under_review": "#1b7fe0"}.get(alert["status"], "#f5a623")
        st.markdown(f"**Status:** <span style='color:{sc};font-weight:700'>{alert['status'].upper()}</span>", unsafe_allow_html=True)
        if alert.get("sla_deadline"):
            st.caption(f"SLA: {alert['sla_deadline']}")
    with c3:
        st.plotly_chart(confidence_gauge(alert["confidence"]), use_container_width=True)

    st.divider()
    st.markdown("#### AI Analysis")
    st.markdown(
        f'<div style="background:#0b1520;border:1px solid #1a2d42;border-left:3px solid #1b7fe0;'
        f'padding:14px 18px;border-radius:4px;line-height:1.8;color:#c8daea">'
        f'{alert.get("explanation","No explanation available.")}</div>',
        unsafe_allow_html=True
    )

    st.divider()
    st.markdown("#### Trader History")
    history = api_get(f"/traders/{alert['trader_id']}/history") or []
    if history:
        df = pd.DataFrame(history)[["alert_id","instrument","pattern","confidence","status","decision"]]
        st.dataframe(df, use_container_width=True, hide_index=True)

    if alert["status"] == "closed":
        dcolor = "#3dd68c" if alert["decision"] == "false_positive" else "#e05555"
        st.markdown(f'<div style="background:#0b1520;border:1px solid #1a2d42;border-left:3px solid {dcolor};'
                    f'padding:12px 16px;border-radius:4px;margin-top:16px">'
                    f'<strong style="color:{dcolor}">{alert["decision"].replace("_"," ").upper()}</strong> — {alert["decision_reason"]}</div>',
                    unsafe_allow_html=True)
        st.stop()

    st.divider()
    st.markdown("#### Submit Decision")
    st.caption("Decision is permanent and recorded in the audit trail.")

    decision = st.selectbox("Decision", ["confirmed", "false_positive", "escalated"], format_func=lambda x: {
        "confirmed":      "✗  Confirmed — Real Manipulation",
        "false_positive": "✓  False Positive — Clear Alert",
        "escalated":      "↑  Escalate — Needs Senior Review",
    }[x])
    reason = st.text_area("Reasoning (required)", placeholder="Explain your decision clearly...", height=100)

    if st.button("Submit Decision", disabled=not reason.strip()):
        result = api_post(f"/alerts/{alert_id}/decision", {
            "officer_id": officer_id, "decision": decision, "reason": reason
        })
        if result and result.get("_error"):
            st.error(result["_error"])
        elif result and result.get("status") == "recorded":
            st.success("Decision recorded.")
            st.session_state.pop("selected_alert", None)
            st.rerun()
        else:
            st.error("Failed to record. Try again.")


# ── audit trail ───────────────────────────────────────────────────────────────
elif page == "Audit Trail":
    st.markdown("## Audit Trail")
    st.caption("Immutable record of all compliance decisions.")
    records = api_get("/audit") or []
    if not records:
        st.info("No audit records yet.")
    else:
        df = pd.DataFrame(records)
        df["recorded_at"] = pd.to_datetime(df["recorded_at"]).dt.strftime("%Y-%m-%d %H:%M")
        df["time_to_decision_secs"] = df["time_to_decision_secs"].apply(lambda x: f"{x}s" if x else "—")
        cols = ["alert_id", "trader_id", "instrument", "pattern",
                "confidence_at_decision", "decision", "officer_id",
                "time_to_decision_secs", "recorded_at"]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)


# ── statistics ────────────────────────────────────────────────────────────────
elif page == "Statistics":
    st.markdown("## Statistics")
    stats = api_get("/stats") or {}

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Alerts", stats.get("total", 0))
    c2.metric("Open",         stats.get("open",  0))
    c3.metric("Closed",       stats.get("closed",0))

    by_pattern = stats.get("by_pattern", {})
    if by_pattern:
        st.markdown("#### Alerts by Pattern")
        keys = list(by_pattern.keys())
        vals = list(by_pattern.values())
        colors = ["#1b7fe0", "#00c9b1", "#f5a623"]
        fig = go.Figure(go.Bar(
            x=vals,
            y=keys,
            orientation="h",
            marker_color=[colors[i % len(colors)] for i in range(len(keys))],
        ))
        fig.update_layout(
            paper_bgcolor="#060d14", plot_bgcolor="#0b1520",
            font_color="#c8daea", height=max(200, 60 * len(keys)),
            xaxis=dict(title="Count", gridcolor="#1a2d42", dtick=1),
            yaxis=dict(title="", gridcolor="#1a2d42", categoryorder="total ascending"),
            margin=dict(t=10, b=40, l=120),
        )
        st.plotly_chart(fig, use_container_width=True)


# ── admin / data reset ────────────────────────────────────────────────────────
elif page == "Admin":
    st.markdown("## Admin")
    st.caption("Danger zone — local demo only.")

    st.markdown(
        "- **Reset all data**: deletes trades, alerts, audit trail, and the vector store.\n"
        "- Intended for **local testing**; does not affect any external systems."
    )
    st.divider()

    confirm = st.checkbox("I understand this will permanently delete all local data.")
    if st.button("Reset all data", disabled=not confirm):
        resp = api_post("/admin/reset", {})
        if resp and resp.get("status") == "reset":
            st.success("All data cleared. The system has been reinitialised.")
        else:
            st.error("Failed to reset data. Check API logs.")
