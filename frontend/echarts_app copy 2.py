"""
IXC · Gestão de Inadimplência
-------------------------------
Fully self-contained Streamlit dashboard.
No external config/utils required — runs with: streamlit run app.py

Install deps:
    pip install streamlit streamlit-echarts httpx pandas loguru
"""

import streamlit as st
from datetime import datetime, timedelta
import httpx
import pandas as pd
from loguru import logger
import random

# ─── Inline Settings (replace with your real values) ───────────────────────────
import os

class Settings:
    API_BASE_URL     = os.environ.get("API_BASE_URL", "http://backend:8000")
    REPORT_DAYS      = int(os.environ.get("IXC_REPORT_DAYS", 30))
    CACHE_TTL        = int(os.environ.get("IXC_CACHE_TTL", 300))
    API_HTTP_TIMEOUT = int(os.environ.get("API_HTTP_TIMEOUT", 300))

settings = Settings()

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IXC · Gestão de Inadimplência",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Session State ───────────────────────────────────────────────────────────────
for key, default in [("report_data", None), ("selected_date", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Design System ──────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    font-family: 'DM Sans', sans-serif !important;
    background: #f0f2f5 !important;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem 4rem !important; max-width: 1400px !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #f8fafc !important; font-weight: 600 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.08) !important; }
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #64748b !important; font-size: 0.75rem !important; }
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary { color: #94a3b8 !important; }
[data-testid="stSidebar"] .stAlert { background: rgba(59,130,246,0.15) !important; border-color: rgba(59,130,246,0.3) !important; border-radius: 8px !important; }
[data-testid="stSidebar"] .stAlert p { color: #93c5fd !important; font-size: 0.8rem !important; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    height: 2.75rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 12px rgba(59,130,246,0.35) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(59,130,246,0.45) !important;
}

/* ── Page Header ── */
.page-header {
    display: flex; align-items: center; gap: 1rem; margin-bottom: 0.25rem;
}
.page-header-icon {
    width: 44px; height: 44px;
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    border-radius: 12px; display: flex; align-items: center;
    justify-content: center; font-size: 1.25rem;
    box-shadow: 0 4px 12px rgba(59,130,246,0.3); flex-shrink: 0;
}
.page-header h1 {
    font-size: 1.5rem !important; font-weight: 700 !important;
    color: #0f172a !important; margin: 0 !important; letter-spacing: -0.02em;
}
.page-header p { font-size: 0.8rem; color: #64748b; margin: 0; }

/* ── Metric Cards ── */
.metrics-row {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 1rem; margin: 1.5rem 0 2rem;
}
.metric-card {
    background: white; border-radius: 14px; padding: 1.25rem 1.5rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
    position: relative; overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.10); }
.metric-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 3px; border-radius: 14px 14px 0 0;
}
.metric-card.blue::before  { background: linear-gradient(90deg,#3b82f6,#60a5fa); }
.metric-card.red::before   { background: linear-gradient(90deg,#ef4444,#f87171); }
.metric-card.amber::before { background: linear-gradient(90deg,#f59e0b,#fbbf24); }
.metric-card.green::before { background: linear-gradient(90deg,#10b981,#34d399); }
.metric-label {
    font-size: 0.68rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 0.5rem;
}
.metric-value {
    font-size: 2.25rem; font-weight: 700; color: #0f172a;
    font-family: 'DM Mono', monospace; letter-spacing: -0.03em; line-height: 1;
}
.metric-sub { font-size: 0.72rem; color: #94a3b8; margin-top: 0.35rem; }

/* ── Section Headers ── */
.section-header {
    display: flex; align-items: center; gap: 0.75rem;
    padding: 1rem 1.25rem; background: white; border-radius: 10px;
    border: 1px solid #e2e8f0; margin: 1.75rem 0 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.section-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.15); flex-shrink: 0;
}
.section-title { font-size: 0.95rem; font-weight: 600; color: #1e293b; margin: 0; }
.section-meta  { margin-left: auto; font-size: 0.72rem; color: #94a3b8; font-family: 'DM Mono', monospace; }

/* ── Chart Container ── */
.chart-box {
    background: white; border-radius: 14px; border: 1px solid #e2e8f0;
    padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] label {
    font-size: 0.8rem !important; font-weight: 600 !important;
    color: #475569 !important; text-transform: uppercase !important; letter-spacing: 0.06em !important;
}
[data-testid="stSelectbox"] > div > div {
    border-radius: 8px !important; border-color: #e2e8f0 !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.85rem !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid #e2e8f0 !important; border-radius: 10px !important; overflow: hidden !important; }
[data-testid="stDataFrame"] th {
    background: #f8fafc !important; font-size: 0.72rem !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.06em !important; color: #64748b !important;
}
[data-testid="stDataFrame"] td { font-size: 0.82rem !important; }

/* ── Bottom st.metric ── */
[data-testid="metric-container"] { background: white; border-radius: 10px; padding: 1rem; border: 1px solid #e2e8f0; }
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    font-size: 0.72rem !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: 0.06em !important; color: #94a3b8 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.5rem !important; font-family: 'DM Mono', monospace !important; color: #0f172a !important;
}

/* ── Info box ── */
[data-testid="stInfo"] {
    background: #eff6ff !important; border: 1px solid #bfdbfe !important;
    border-radius: 8px !important; color: #1e40af !important;
}

hr { border-color: #e2e8f0 !important; }

/* ── Welcome ── */
.welcome-card {
    background: white; border-radius: 16px; padding: 3rem; text-align: center;
    border: 1px solid #e2e8f0; box-shadow: 0 4px 24px rgba(0,0,0,0.06); margin-top: 2rem;
}
.welcome-card h2 { color: #0f172a; font-size: 1.6rem; font-weight: 700; margin-bottom: 1rem; }
.welcome-card p  { color: #64748b; font-size: 0.95rem; line-height: 1.7; }
.welcome-step {
    background: #f8fafc; border-radius: 10px; padding: 1rem 1.25rem;
    margin: 0.75rem 0; text-align: left; border: 1px solid #e2e8f0;
    display: flex; align-items: center; gap: 1rem;
}
.step-num {
    width: 28px; height: 28px; min-width: 28px;
    background: linear-gradient(135deg,#3b82f6,#2563eb); color: white; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ─── Page Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-header-icon">📊</div>
    <div>
        <h1>Gestão de Inadimplência</h1>
        <p>Plataforma de Relatórios IXC · Análise de cobrança estratégica</p>
    </div>
</div>
<hr style="margin: 0.75rem 0 0.25rem;">
""", unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📋 Painel IXC")
    st.markdown("---")
    st.markdown("### 📅 Período")

    now        = datetime.now()
    end_date   = datetime.combine(now.date(), datetime.min.time())
    start_date = end_date - timedelta(days=settings.REPORT_DAYS)

    st.caption(f"🗓 {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}")
    st.caption(f"🕒 Atualizado: {now.strftime('%H:%M:%S')}")

    generate_btn = st.button("⟳  Gerar / Atualizar Dados")

    if st.session_state.report_data and "fetched_at" in st.session_state.report_data:
        try:
            fetched_at  = datetime.fromisoformat(st.session_state.report_data["fetched_at"])
            next_update = fetched_at + timedelta(seconds=settings.CACHE_TTL)
            remaining   = (next_update - datetime.now()).total_seconds()
            if remaining > 0:
                mins, secs = divmod(int(remaining), 60)
                st.info(f"🔄 Próxima atualização: {mins:02d}:{secs:02d}")
            else:
                st.warning("⚠️ Dados desatualizados.")
        except Exception:
            pass

    st.markdown("---")
    with st.expander("📖 Definições de Status"):
        st.markdown("""
**🟢 Em Dia** — faturas dentro do prazo  
**🟡 Vencimento Padrão** — 1–6 dias de atraso  
**🟠 Transição** — 7–9 dias (janela crítica)  
**🔴 Crônico** — mais de 9 dias de atraso  
**🔵 Desbloqueio** — desbloqueio de confiança ativo
        """)

# ─── Mock Data Generator ────────────────────────────────────────────────────────
def generate_mock_data() -> dict:
    """
    Generates realistic mock data matching the expected API response shape.
    Remove once your real FastAPI backend is connected.
    """
    random.seed(42)
    today = datetime.now().date()

    BAIRROS  = ["Tabuleiro do Pinto","Nova Satuká","Centro","Jardim América",
                "Vila Nova","São Pedro","Boa Vista","Poço","Mangabeiras"]
    CLIENTES = [
        "Erica Vanessa Monteiro","Jose Carlos Vasconcelos Costa","Gilson Carlos Nilo Cândido",
        "Rosineide Alves Ornelas","Sirlene Alves Nunes Ferreira","Walmyr Cardoso Pereira Filho",
        "Wellington Carlos dos Santos Silva","Wagner Correia","Cassia Carla dos Santos da Silva",
        "José Edson Bezerra de Omena","Maria Francisca Lima","Antonio Carlos Souza",
        "Fernanda Oliveira Ramos","Lucas Pereira da Costa","Ana Paula Silva Santos",
        "Roberto Mendes Ferreira","Claudia Regina Alves","Paulo Sérgio Gomes",
        "Juliana Martins Costa","Carlos Eduardo Nascimento","Beatriz Souza Oliveira",
        "Francisco das Chagas Lima","Raimunda Nonata Silva","Manoel José Santos",
    ]

    STATUSES_COLS = ["Desbloqueio de Confiança","Crônico","Transição","Vencimento Padrão","Em Dia"]
    summary_rows  = []
    full_rows     = []

    for offset in range(settings.REPORT_DAYS - 1, -1, -1):
        due_date = today - timedelta(days=offset)
        counts = {
            "Em Dia":                   random.randint(150, 350),
            "Vencimento Padrão":        random.randint(5,  30)  if offset <= 6       else 0,
            "Transição":                random.randint(2,  12)  if 7 <= offset <= 9  else 0,
            "Crônico":                  random.randint(1,  10)  if offset > 9        else 0,
            "Desbloqueio de Confiança": random.randint(1,   8)  if offset > 3        else 0,
        }
        summary_rows.append({"Vencimento": due_date.strftime("%Y-%m-%d"), **counts})

        n_open = (counts["Vencimento Padrão"] + counts["Transição"]
                  + counts["Crônico"] + counts["Desbloqueio de Confiança"])
        for _ in range(min(n_open, 15)):
            is_unlock = random.random() < 0.15
            full_rows.append({
                "data_vencimento":    due_date.strftime("%Y-%m-%d"),
                "status":             "A",
                "cliente":            random.choice(CLIENTES),
                "valor":              round(random.uniform(55, 250), 2),
                "telefone":           f"(82) 9{random.randint(8000,9999)}-{random.randint(1000,9999)}",
                "bairro":             random.choice(BAIRROS),
                "connection_status":  random.choice(["FA","OK","SU"]),
                "trust_unlock_active":"S" if is_unlock else "N",
            })
        for _ in range(random.randint(2, 6)):
            full_rows.append({
                "data_vencimento":    due_date.strftime("%Y-%m-%d"),
                "status":             "P",
                "cliente":            random.choice(CLIENTES),
                "valor":              round(random.uniform(55, 250), 2),
                "telefone":           f"(82) 9{random.randint(8000,9999)}-{random.randint(1000,9999)}",
                "bairro":             random.choice(BAIRROS),
                "connection_status":  "OK",
                "trust_unlock_active":"N",
            })

    return {
        "delinquency_summary": pd.DataFrame(summary_rows),
        "full_data":           pd.DataFrame(full_rows),
        "fetched_at":          datetime.now().isoformat(),
    }

# ─── Data Fetching ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=settings.CACHE_TTL, show_spinner="Buscando dados da API IXC...")
def fetch_report_data(start_str: str, end_str: str, refresh: bool = False) -> dict | None:
    """
    Tries the real FastAPI backend first; falls back to mock data if unreachable.
    Remove the except branch once your backend is live.
    """
    try:
        url     = f"{settings.API_BASE_URL}/reports/financial"
        payload = {"start_date": start_str, "end_date": end_str, "refresh": refresh}
        with httpx.Client(timeout=settings.API_HTTP_TIMEOUT) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if "full_data" in data and isinstance(data["full_data"], list):
                data["full_data"] = pd.DataFrame(data["full_data"])
            if "delinquency_summary" in data and isinstance(data["delinquency_summary"], list):
                data["delinquency_summary"] = pd.DataFrame(data["delinquency_summary"])
            return data
    except Exception as e:
        logger.warning(f"Backend unreachable at {url} ({e}), using mock data.")
        return generate_mock_data()


def is_valid_report_data(data: dict | None) -> bool:
    if not data or not isinstance(data, dict):
        return False
    summary = data.get("delinquency_summary")
    return summary is not None and not (isinstance(summary, pd.DataFrame) and summary.empty)


# ─── Load / Refresh ─────────────────────────────────────────────────────────────
if generate_btn:
    new_data = fetch_report_data(start_date.isoformat(), end_date.isoformat(), refresh=True)
    if is_valid_report_data(new_data):
        st.session_state.report_data = new_data
        st.toast("✅ Dados atualizados com sucesso!", icon="✅")
    else:
        st.error("Falha: dados inválidos ou vazios recebidos da API.")
elif st.session_state.report_data is None:
    new_data = fetch_report_data(start_date.isoformat(), end_date.isoformat(), refresh=False)
    if is_valid_report_data(new_data):
        st.session_state.report_data = new_data

# ─── Main Dashboard ──────────────────────────────────────────────────────────────
if st.session_state.report_data:
    report_data = st.session_state.report_data
    summary_df  = report_data.get("delinquency_summary", pd.DataFrame())

    STATUSES = ["Desbloqueio de Confiança","Crônico","Transição","Vencimento Padrão","Em Dia"]
    COLORS   = ["#3b82f6","#ef4444","#f59e0b","#fbbf24","#10b981"]

    if not summary_df.empty:

        def get_total(col: str) -> int:
            return int(summary_df[col].sum()) if col in summary_df.columns else 0

        total_open  = sum(get_total(s) for s in STATUSES[:-1])
        cronico     = get_total("Crônico")
        desbloqueio = get_total("Desbloqueio de Confiança")
        em_dia      = get_total("Em Dia")

        # ── Metric Cards ──────────────────────────────────────────────────────────
        st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-card blue">
                <div class="metric-label">📄 Total em Aberto</div>
                <div class="metric-value">{total_open:,}</div>
                <div class="metric-sub">faturas ativas no período</div>
            </div>
            <div class="metric-card red">
                <div class="metric-label">🛑 Crônico</div>
                <div class="metric-value">{cronico:,}</div>
                <div class="metric-sub">acima de 9 dias de atraso</div>
            </div>
            <div class="metric-card amber">
                <div class="metric-label">🔓 Desbloqueio</div>
                <div class="metric-value">{desbloqueio:,}</div>
                <div class="metric-sub">desbloqueio de confiança ativo</div>
            </div>
            <div class="metric-card green">
                <div class="metric-label">✅ Em Dia</div>
                <div class="metric-value">{em_dia:,}</div>
                <div class="metric-sub">clientes adimplentes</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Calendar Chart ────────────────────────────────────────────────────────
        fetched_str = report_data.get("fetched_at", "")
        meta_text   = ("🕒 " + fetched_str[:19].replace("T"," ")) if fetched_str else ""
        st.markdown(f"""
        <div class="section-header">
            <div class="section-dot"></div>
            <span class="section-title">📅 Tendência de Inadimplência por Vencimento</span>
            <span class="section-meta">{meta_text}</span>
        </div>
        """, unsafe_allow_html=True)

        cell_size  = [80, 80]
        pie_radius = 30

        all_dates      = pd.to_datetime(summary_df["Vencimento"]).sort_values()
        calendar_range = [all_dates.min().strftime("%Y-%m-%d"), all_dates.max().strftime("%Y-%m-%d")]

        scatter_data = []
        for _, row in summary_df.iterrows():
            date_str = pd.to_datetime(row["Vencimento"]).strftime("%Y-%m-%d")
            total    = sum(float(row.get(s, 0)) for s in STATUSES)
            scatter_data.append([date_str, total])

        pie_series = []
        for idx, row in summary_df.iterrows():
            date_str = pd.to_datetime(row["Vencimento"]).strftime("%Y-%m-%d")
            pie_data = [
                {"name": s, "value": float(row.get(s, 0)), "itemStyle": {"color": COLORS[i]}}
                for i, s in enumerate(STATUSES)
                if float(row.get(s, 0)) > 0
            ]
            if pie_data:
                pie_series.append({
                    "type": "pie",
                    "id":   f"pie-{idx}",
                    "center": date_str,
                    "radius": pie_radius,
                    "coordinateSystem": "calendar",
                    "label": {"formatter": "{c}", "position": "inside", "fontSize": 9, "color": "#fff"},
                    "data": pie_data,
                })

        try:
            from streamlit_echarts import st_echarts, JsCode
            day_fmt = JsCode("function(p){return new Date(p.value[0]).getDate();}")
            use_echarts = True
        except ImportError:
            use_echarts = False

        label_series = {
            "id": "label", "type": "scatter",
            "coordinateSystem": "calendar", "symbolSize": 0,
            "label": {
                "show": True,
                "formatter": day_fmt if use_echarts else "",
                "offset": [-(cell_size[0]/2)+10, -(cell_size[1]/2)+10],
                "fontSize": 12, "color": "#94a3b8",
            },
            "data": scatter_data,
        }

        echarts_options = {
            "backgroundColor": "#ffffff",
            "tooltip": {
                "trigger": "item",
                "backgroundColor": "#1e293b", "borderColor": "#334155",
                "textStyle": {"color": "#f1f5f9", "fontSize": 12},
            },
            "legend": {
                "data": STATUSES, "bottom": 16,
                "textStyle": {"color": "#475569", "fontSize": 12},
                "icon": "circle", "itemWidth": 8, "itemHeight": 8, "itemGap": 20,
            },
            "calendar": {
                "top": "middle", "left": "center",
                "orient": "vertical", "cellSize": cell_size,
                "yearLabel": {"show": False},
                "dayLabel": {
                    "margin": 20, "firstDay": 0,
                    "nameMap": ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"],
                    "color": "#64748b", "fontSize": 12,
                },
                "monthLabel": {"show": True, "color": "#374151", "fontSize": 13, "fontWeight": "bold"},
                "range": calendar_range,
                "itemStyle": {"borderWidth": 1, "borderColor": "#e2e8f0", "color": "#f8fafc"},
                "splitLine": {"show": True, "lineStyle": {"color": "#e2e8f0", "width": 1}},
            },
            "series": [label_series] + pie_series,
        }

        num_weeks    = ((all_dates.max() - all_dates.min()).days // 7) + 2
        chart_height = max(600, num_weeks * cell_size[1] + 250)

        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        if use_echarts:
            st_echarts(options=echarts_options, height=f"{chart_height}px")
        else:
            st.warning("streamlit-echarts não instalado. Execute: `pip install streamlit-echarts`")
            st.dataframe(summary_df, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Bar Chart: Current Month ──────────────────────────────────────────────
        current_month = now.month
        current_year  = now.year

        summary_df["_dt"] = pd.to_datetime(summary_df["Vencimento"])
        month_df = summary_df[
            (summary_df["_dt"].dt.month == current_month) &
            (summary_df["_dt"].dt.year  == current_year)
        ].copy()

        bar_statuses = ["Vencimento Padrão", "Transição", "Crônico", "Desbloqueio de Confiança"]
        bar_colors   = ["#fbbf24", "#f59e0b", "#ef4444", "#3b82f6"]
        bar_labels_pt= ["Venc. Padrão", "Transição", "Crônico", "Desbloqueio"]

        month_name_map = {
            1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
            7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"
        }
        month_label = f"{month_name_map[current_month]} {current_year}"

        st.markdown(f"""
        <div class="section-header">
            <div class="section-dot" style="background:#f59e0b;box-shadow:0 0 0 3px rgba(245,158,11,.15);"></div>
            <span class="section-title">📊 Inadimplência por Dia — {month_label}</span>
            <span class="section-meta">barras empilhadas · rótulos rotacionados</span>
        </div>
        """, unsafe_allow_html=True)

        if not month_df.empty:
            x_days = [str(pd.to_datetime(d).day) for d in month_df["Vencimento"]]

            bar_series = []
            for i, (status, color, short_label) in enumerate(
                zip(bar_statuses, bar_colors, bar_labels_pt)
            ):
                values = [int(row.get(status, 0)) for _, row in month_df.iterrows()]
                bar_series.append({
                    "name":  status,
                    "type":  "bar",
                    "stack": "total",
                    "itemStyle": {"color": color},
                    "label": {
                        "show":          True,
                        "position":      "inside",
                        "rotate":        90,
                        "align":         "left",
                        "verticalAlign": "middle",
                        "formatter":     f"{{c}} {short_label}",
                        "fontSize":      10,
                        "color":         "#fff",
                        "distance":      15,
                    },
                    "emphasis": {"focus": "series"},
                    "data": values,
                })

            # Invisible bar for the total label on top
            total_values = [
                sum(int(row.get(s, 0)) for s in bar_statuses)
                for _, row in month_df.iterrows()
            ]
            bar_series.append({
                "name":      "_total",
                "type":      "bar",
                "stack":     "total",
                "itemStyle": {"color": "transparent"},
                "label": {
                    "show":       True,
                    "position":   "top",
                    "formatter":  "{c}",
                    "fontSize":   11,
                    "fontWeight": "bold",
                    "color":      "#374151",
                },
                "emphasis":    {"focus": "series"},
                "data":        total_values,
                "legendHoverLink": False,
            })

            bar_options = {
                "backgroundColor": "#ffffff",
                "tooltip": {
                    "trigger":     "axis",
                    "axisPointer": {"type": "shadow"},
                    "backgroundColor": "#1e293b",
                    "borderColor":     "#334155",
                    "textStyle":       {"color": "#f1f5f9", "fontSize": 12},
                    "formatter": JsCode("""function(params) {
                        var date = params[0].axisValue;
                        var lines = ['<b>Dia ' + date + '/' + String(""" + str(current_month).zfill(2) + """).padStart(2,'0') + '</b>'];
                        var total = 0;
                        params.forEach(function(p) {
                            if (p.seriesName === '_total') return;
                            if (p.value > 0) {
                                lines.push(p.marker + ' ' + p.seriesName + ': <b>' + p.value + '</b>');
                                total += p.value;
                            }
                        });
                        lines.push('<hr style="margin:4px 0;border-color:#475569">Total: <b>' + total + '</b>');
                        return lines.join('<br>');
                    }""") if use_echarts else "",
                },
                "legend": {
                    "data":      bar_statuses,
                    "top":       12,
                    "right":     16,
                    "textStyle": {"color": "#475569", "fontSize": 11},
                    "icon":      "roundRect",
                    "itemWidth": 14, "itemHeight": 8, "itemGap": 16,
                },
                "grid": {
                    "left": "3%", "right": "4%",
                    "bottom": "10%", "top": "15%",
                    "containLabel": True,
                },
                "xAxis": {
                    "type": "category",
                    "data": x_days,
                    "axisLabel": {
                        "color":     "#64748b",
                        "fontSize":  11,
                        "formatter": f"Dia {{value}}",
                        "rotate":    30,
                    },
                    "axisLine":  {"lineStyle": {"color": "#e2e8f0"}},
                    "axisTick":  {"show": False},
                    "splitLine": {"show": False},
                },
                "yAxis": {
                    "type":      "value",
                    "name":      "Faturas",
                    "nameTextStyle": {"color": "#94a3b8", "fontSize": 11},
                    "axisLabel": {"color": "#64748b", "fontSize": 11},
                    "axisLine":  {"show": False},
                    "axisTick":  {"show": False},
                    "splitLine": {"lineStyle": {"color": "#f1f5f9", "type": "dashed"}},
                },
                "series": bar_series,
            }

            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            try:
                st_echarts(options=bar_options, height="440px")
            except Exception:
                st.dataframe(month_df, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info(f"Nenhum dado encontrado para {month_label}.")

        # ── Date Selector ─────────────────────────────────────────────────────────
        st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)
        dates = [pd.to_datetime(d).strftime("%Y-%m-%d") for d in summary_df["Vencimento"]]
        selected_date_val = st.selectbox(
            "📅 Selecione a Data de Vencimento para ver detalhes:",
            options=["— Selecione uma data —"] + dates,
        )
        if selected_date_val != "— Selecione uma data —":
            st.session_state.selected_date = selected_date_val

        # ── Detail Table ──────────────────────────────────────────────────────────
        if st.session_state.selected_date:
            st.markdown(f"""
            <div class="section-header">
                <div class="section-dot" style="background:#10b981;box-shadow:0 0 0 3px rgba(16,185,129,.15);"></div>
                <span class="section-title">📝 Detalhes · Vencimento {st.session_state.selected_date}</span>
            </div>
            """, unsafe_allow_html=True)

            full_df = report_data.get("full_data", pd.DataFrame())
            if not full_df.empty:
                full_df["data_vencimento"] = pd.to_datetime(full_df["data_vencimento"])
                target_date = pd.to_datetime(st.session_state.selected_date)
                details = full_df[
                    (full_df["data_vencimento"] == target_date) &
                    (full_df["status"] == "A")
                ].copy()

                if not details.empty:
                    today_ts = pd.Timestamp.normalize(pd.Timestamp.now())
                    details["atraso"] = (today_ts - details["data_vencimento"]).dt.days

                    def categorize_risk(row):
                        if row.get("trust_unlock_active") == "S":
                            return "🔵 Desbloqueio"
                        d = row["atraso"]
                        if d > 9:       return "🔴 Crônico"
                        if 7 <= d <= 9: return "🟠 Transição"
                        if d >= 1:      return "🟡 Vencido"
                        return "🟢 Em Dia"

                    details["risk_category"] = details.apply(categorize_risk, axis=1)

                    display_df = details[[
                        "risk_category","cliente","valor","atraso",
                        "telefone","bairro","connection_status"
                    ]].rename(columns={
                        "risk_category":    "Risco / Status",
                        "cliente":          "Nome do Cliente",
                        "valor":            "Valor da Fatura",
                        "atraso":           "Dias de Atraso",
                        "telefone":         "Telefone",
                        "bairro":           "Bairro",
                        "connection_status":"Conexão",
                    }).sort_values("Dias de Atraso", ascending=False)

                    def highlight_rows(row):
                        risk = row["Risco / Status"]
                        if "🔵" in risk:
                            return ["background-color:#eff6ff;color:#1e40af"] * len(row)
                        d = row["Dias de Atraso"]
                        if d > 9:       return ["background-color:#fef2f2;color:#991b1b"] * len(row)
                        if 7 <= d <= 9: return ["background-color:#fff7ed;color:#9a3412"] * len(row)
                        if d >= 1:      return ["background-color:#fefce8;color:#92400e"] * len(row)
                        return [""] * len(row)

                    st.dataframe(
                        display_df.style.apply(highlight_rows, axis=1),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Valor da Fatura": st.column_config.NumberColumn(format="R$ %.2f"),
                            "Dias de Atraso":  st.column_config.NumberColumn(format="%d dias"),
                        },
                    )

                    st.divider()
                    c1, c2, c3, c4, c5 = st.columns(5)
                    unlock_col = "trust_unlock_active"
                    n_unlock   = len(details[details[unlock_col] == "S"]) if unlock_col in details.columns else 0
                    c1.metric("🔴 Crônico",         len(details[details["atraso"] > 9]))
                    c2.metric("🟠 Transição",        len(details[(details["atraso"] >= 7) & (details["atraso"] <= 9)]))
                    c3.metric("🔵 Desbloqueio",     n_unlock)
                    c4.metric("💰 Valor Total",      f"R$ {details['valor'].sum():,.2f}")
                    c5.metric("📊 Média de Atraso",  f"{details['atraso'].mean():.1f} dias")
                else:
                    st.info("Nenhum registro em aberto encontrado para esta data.")
        else:
            st.markdown("""
            <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
                        padding:1rem 1.25rem;color:#1e40af;font-size:0.875rem;margin-top:0.5rem;">
                👆 Selecione uma data de vencimento acima para ver os detalhes dos clientes.
            </div>
            """, unsafe_allow_html=True)

# ─── Welcome Screen ──────────────────────────────────────────────────────────────
else:
    st.markdown(f"""
    <div class="welcome-card">
        <div style="font-size:3rem;margin-bottom:1rem;">📊</div>
        <h2>Bem-vindo à Plataforma IXC</h2>
        <p>Análise inteligente de inadimplência com dados em tempo real.</p>
        <div style="max-width:480px;margin:1.5rem auto 0;">
            <div class="welcome-step">
                <div class="step-num">1</div>
                <span>Os dados dos últimos <strong>{settings.REPORT_DAYS} dias</strong> são carregados automaticamente.</span>
            </div>
            <div class="welcome-step">
                <div class="step-num">2</div>
                <span>Clique em <strong>"Gerar / Atualizar Dados"</strong> na barra lateral para forçar uma atualização.</span>
            </div>
            <div class="welcome-step">
                <div class="step-num">3</div>
                <span>Analise tendências por vencimento e explore os detalhes por cliente.</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)