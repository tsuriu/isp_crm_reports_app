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
from streamlit_echarts import st_echarts, JsCode
import os

# ─── Must be FIRST Streamlit call ──────────────────────────────────────────────
st.set_page_config(
    page_title="IXC · Gestão de Inadimplência",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


class Settings:
    API_BASE_URL     = os.environ.get("API_BASE_URL", "http://backend:8000")
    REPORT_DAYS      = int(os.environ.get("IXC_REPORT_DAYS", 30))
    CACHE_TTL        = int(os.environ.get("IXC_CACHE_TTL", 300))
    API_HTTP_TIMEOUT = int(os.environ.get("API_HTTP_TIMEOUT", 300))


settings = Settings()

# ─── Session state ─────────────────────────────────────────────────────────────
for key, default in [("report_data", None), ("selected_date", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    font-family: 'Sora', sans-serif !important;
    background: #0b0f1a !important;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.75rem 2.5rem 4rem !important; max-width: 1700px !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] * { color: #8b95a8 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #e2e8f0 !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.07) !important; }
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #4a5568 !important; font-size: 0.73rem !important; }
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary { color: #718096 !important; }
[data-testid="stSidebar"] .stAlert {
    background: rgba(99,102,241,0.12) !important;
    border-color: rgba(99,102,241,0.25) !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] .stAlert p { color: #a5b4fc !important; font-size: 0.78rem !important; }

/* ── Sidebar brand ── */
.sidebar-brand {
    display: flex; align-items: center; gap: 0.75rem;
    padding: 0.25rem 0 1.25rem;
}
.sidebar-brand-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    border-radius: 10px; display: flex; align-items: center;
    justify-content: center; font-size: 1rem;
    box-shadow: 0 0 20px rgba(99,102,241,0.4);
}
.sidebar-brand-text { font-size: 0.9rem; font-weight: 700; color: #e2e8f0 !important; letter-spacing: -0.01em; }
.sidebar-brand-sub  { font-size: 0.68rem; color: #4a5568 !important; margin-top: 1px; }

/* ── Button ── */
.stButton > button {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    font-family: 'Sora', sans-serif !important; font-weight: 600 !important;
    font-size: 0.825rem !important; height: 2.6rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 16px rgba(99,102,241,0.35) !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(99,102,241,0.5) !important;
}

/* ── Page header ── */
.page-header {
    display: flex; align-items: center; gap: 1rem;
    margin-bottom: 1.5rem; padding: 1.5rem 2rem;
    background: linear-gradient(135deg, #0d1117 0%, #111827 50%, #0d1117 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    position: relative; overflow: hidden;
}
.page-header::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 20% 50%, rgba(99,102,241,0.08) 0%, transparent 60%),
                radial-gradient(ellipse at 80% 50%, rgba(16,185,129,0.05) 0%, transparent 60%);
    pointer-events: none;
}
.page-header-icon {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    border-radius: 14px; display: flex; align-items: center;
    justify-content: center; font-size: 1.5rem;
    box-shadow: 0 0 30px rgba(99,102,241,0.4); flex-shrink: 0;
}
.page-header h1 {
    font-size: 1.45rem !important; font-weight: 800 !important;
    color: #f1f5f9 !important; margin: 0 !important;
    letter-spacing: -0.03em;
}
.page-header p { font-size: 0.78rem; color: #4a5568; margin: 0.2rem 0 0; }
.page-header-badge {
    margin-left: auto;
    background: rgba(16,185,129,0.12);
    border: 1px solid rgba(16,185,129,0.25);
    border-radius: 20px; padding: 0.3rem 0.9rem;
    font-size: 0.7rem; font-weight: 600; color: #34d399;
    letter-spacing: 0.05em; text-transform: uppercase;
    display: flex; align-items: center; gap: 0.4rem;
}
.live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #10b981;
    animation: pulse-dot 2s ease-in-out infinite;
    box-shadow: 0 0 6px #10b981;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}

/* ── Metric cards ── */
.metrics-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem; margin: 0 0 1.75rem;
}
.metric-card {
    background: #0d1117;
    border-radius: 16px; padding: 1.4rem 1.6rem;
    border: 1px solid rgba(255,255,255,0.07);
    position: relative; overflow: hidden;
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-3px);
    border-color: rgba(255,255,255,0.14);
}
.metric-card-glow {
    position: absolute; top: -30px; right: -30px;
    width: 120px; height: 120px; border-radius: 50%;
    filter: blur(40px); opacity: 0.15; pointer-events: none;
}
.metric-card.blue  .metric-card-glow { background: #6366f1; }
.metric-card.red   .metric-card-glow { background: #ef4444; }
.metric-card.amber .metric-card-glow { background: #f59e0b; }
.metric-card.green .metric-card-glow { background: #10b981; }
.metric-card-accent {
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    border-radius: 16px 16px 0 0;
}
.metric-card.blue  .metric-card-accent { background: linear-gradient(90deg, #6366f1, #818cf8); }
.metric-card.red   .metric-card-accent { background: linear-gradient(90deg, #ef4444, #f87171); }
.metric-card.amber .metric-card-accent { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.metric-card.green .metric-card-accent { background: linear-gradient(90deg, #10b981, #34d399); }
.metric-icon {
    font-size: 1.1rem; margin-bottom: 0.6rem; display: block;
}
.metric-label {
    font-size: 0.64rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #4a5568; margin-bottom: 0.5rem;
}
.metric-value {
    font-size: 2.4rem; font-weight: 800; color: #f1f5f9;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -0.04em; line-height: 1;
}
.metric-card.blue  .metric-value { color: #818cf8; }
.metric-card.red   .metric-value { color: #f87171; }
.metric-card.amber .metric-value { color: #fbbf24; }
.metric-card.green .metric-value { color: #34d399; }
.metric-sub { font-size: 0.7rem; color: #374151; margin-top: 0.4rem; }

/* ── Section header ── */
.section-header {
    display: flex; align-items: center; gap: 0.875rem;
    padding: 0.9rem 1.25rem;
    background: #0d1117;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; margin: 0 0 1rem;
}
.section-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #6366f1;
    box-shadow: 0 0 8px rgba(99,102,241,0.6);
    flex-shrink: 0;
}
.section-title { font-size: 0.88rem; font-weight: 700; color: #cbd5e1; margin: 0; letter-spacing: -0.01em; }
.section-meta  { margin-left: auto; font-size: 0.7rem; color: #374151; font-family: 'JetBrains Mono', monospace; }

/* ── Chart box ── */
.chart-box {
    background: #0d1117;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.07);
    padding: 1.75rem 1.5rem;
    box-shadow: 0 4px 40px rgba(0,0,0,0.4);
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] label {
    font-size: 0.72rem !important; font-weight: 700 !important;
    color: #4a5568 !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
[data-testid="stSelectbox"] > div > div {
    border-radius: 10px !important;
    border-color: rgba(255,255,255,0.1) !important;
    background: #0d1117 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    color: #cbd5e1 !important;
}

/* ── DataFrame ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important; overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
    background: #111827 !important;
    font-size: 0.68rem !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.08em !important;
    color: #4a5568 !important;
}
[data-testid="stDataFrame"] td { font-size: 0.82rem !important; }

/* ── Streamlit metrics ── */
[data-testid="metric-container"] {
    background: #0d1117; border-radius: 12px; padding: 1rem;
    border: 1px solid rgba(255,255,255,0.07);
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    font-size: 0.68rem !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.08em !important; color: #4a5568 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.5rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    color: #f1f5f9 !important;
}

[data-testid="stInfo"] {
    background: rgba(99,102,241,0.08) !important;
    border: 1px solid rgba(99,102,241,0.2) !important;
    border-radius: 10px !important; color: #a5b4fc !important;
}
hr { border-color: rgba(255,255,255,0.07) !important; }

/* ── Welcome card ── */
.welcome-card {
    background: #0d1117; border-radius: 20px; padding: 3.5rem;
    text-align: center; border: 1px solid rgba(255,255,255,0.07);
    box-shadow: 0 8px 40px rgba(0,0,0,0.4); margin-top: 2rem;
    position: relative; overflow: hidden;
}
.welcome-card::before {
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.08) 0%, transparent 60%);
    pointer-events: none;
}
.welcome-card h2 { color: #f1f5f9; font-size: 1.7rem; font-weight: 800; margin-bottom: 0.75rem; letter-spacing: -0.03em; }
.welcome-card p  { color: #4a5568; font-size: 0.92rem; line-height: 1.7; }
.welcome-step {
    background: rgba(255,255,255,0.03);
    border-radius: 12px; padding: 1rem 1.25rem; margin: 0.6rem 0;
    text-align: left; border: 1px solid rgba(255,255,255,0.06);
    display: flex; align-items: center; gap: 1rem;
    color: #8b95a8;
}
.step-num {
    width: 28px; height: 28px; min-width: 28px;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: white; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700;
    box-shadow: 0 0 12px rgba(99,102,241,0.4);
}

/* ── Detail highlight banner ── */
.date-detail-banner {
    display: flex; align-items: center; gap: 1rem;
    background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(79,70,229,0.05));
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 12px; padding: 1rem 1.5rem;
    margin-bottom: 1.25rem;
}
.date-detail-banner .date-badge {
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: white; border-radius: 8px; padding: 0.35rem 0.85rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem; font-weight: 600;
    box-shadow: 0 4px 12px rgba(99,102,241,0.35);
}
.date-detail-banner .date-label {
    font-size: 0.85rem; font-weight: 600; color: #cbd5e1;
}
.date-detail-banner .date-sub {
    font-size: 0.72rem; color: #4a5568;
}

/* ── Hint box ── */
.hint-box {
    background: rgba(99,102,241,0.06);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 12px; padding: 1rem 1.25rem;
    color: #818cf8; font-size: 0.85rem; margin-top: 0.5rem;
    display: flex; align-items: center; gap: 0.75rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─── Page Header ───────────────────────────────────────────────────────────────
now = datetime.now()
st.markdown(
    f"""
<div class="page-header">
    <div class="page-header-icon">📊</div>
    <div>
        <h1>Gestão de Inadimplência</h1>
        <p>Plataforma de Relatórios IXC · Análise de cobrança estratégica</p>
    </div>
    <div class="page-header-badge">
        <span class="live-dot"></span>
        {now.strftime('%d/%m/%Y %H:%M')}
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class="sidebar-brand">
    <div class="sidebar-brand-icon">📊</div>
    <div>
        <div class="sidebar-brand-text">IXC Painel</div>
        <div class="sidebar-brand-sub">Inadimplência</div>
    </div>
</div>
""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📅 Período")

    end_date   = datetime.combine(now.date(), datetime.min.time())
    start_date = end_date - timedelta(days=settings.REPORT_DAYS)

    st.caption(f"🗓 {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}")
    st.caption(f"🕒 Atualizado: {now.strftime('%H:%M:%S')}")

    generate_btn = st.button("⟳  Gerar / Atualizar Dados", use_container_width=True)

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
        st.markdown(
            """
**🟢 Em Dia** — faturas dentro do prazo  
**🟡 Vencimento Padrão** — 1–6 dias de atraso  
**🟠 Transição** — 7–9 dias (janela crítica)  
**🔴 Crônico** — mais de 9 dias de atraso  
**🔵 Desbloqueio** — desbloqueio de confiança ativo  
"""
        )

# ─── Color / Status palette ────────────────────────────────────────────────────
STATUSES   = ["Desbloqueio de Confiança", "Crônico", "Transição", "Vencimento Padrão", "Em Dia"]
COLORS     = ["#6366f1", "#ef4444", "#f97316", "#eab308", "#22c55e"]
DELINQUENT = ["Desbloqueio de Confiança", "Crônico", "Transição", "Vencimento Padrão"]

STATUS_COLORS_MAP = {
    "Desbloqueio de Confiança": "#6366f1",
    "Crônico":                  "#ef4444",
    "Transição":                "#f97316",
    "Vencimento Padrão":        "#eab308",
    "Em Dia":                   "#22c55e",
}


# ─── Mock Data ─────────────────────────────────────────────────────────────────
def generate_mock_data() -> dict:
    random.seed(42)
    today = datetime.now().date()

    BAIRROS = [
        "Tabuleiro do Pinto", "Nova Satuká", "Centro", "Jardim América",
        "Vila Nova", "São Pedro", "Boa Vista", "Poço", "Mangabeiras",
    ]
    CLIENTES = [
        "Erica Vanessa Monteiro", "Jose Carlos Vasconcelos Costa", "Gilson Carlos Nilo Cândido",
        "Rosineide Alves Ornelas", "Sirlene Alves Nunes Ferreira", "Walmyr Cardoso Pereira Filho",
        "Wellington Carlos dos Santos Silva", "Wagner Correia", "Cassia Carla dos Santos da Silva",
        "José Edson Bezerra de Omena", "Maria Francisca Lima", "Antonio Carlos Souza",
        "Fernanda Oliveira Ramos", "Lucas Pereira da Costa", "Ana Paula Silva Santos",
        "Roberto Mendes Ferreira", "Claudia Regina Alves", "Paulo Sérgio Gomes",
        "Juliana Martins Costa", "Carlos Eduardo Nascimento", "Beatriz Souza Oliveira",
        "Francisco das Chagas Lima", "Raimunda Nonata Silva", "Manoel José Santos",
    ]

    summary_rows = []
    full_rows    = []

    for offset in range(settings.REPORT_DAYS - 1, -1, -1):
        due_date = today - timedelta(days=offset)
        counts = {
            "Em Dia":                   random.randint(150, 350),
            "Vencimento Padrão":        random.randint(5, 30)   if offset <= 6      else 0,
            "Transição":                random.randint(2, 12)   if 7 <= offset <= 9 else 0,
            "Crônico":                  random.randint(1, 10)   if offset > 9       else 0,
            "Desbloqueio de Confiança": random.randint(1, 8)    if offset > 3       else 0,
        }
        summary_rows.append({"Vencimento": due_date.strftime("%Y-%m-%d"), **counts})

        n_open = (
            counts["Vencimento Padrão"] + counts["Transição"]
            + counts["Crônico"] + counts["Desbloqueio de Confiança"]
        )
        for _ in range(min(n_open, 15)):
            is_unlock = random.random() < 0.15
            full_rows.append({
                "data_vencimento":     due_date.strftime("%Y-%m-%d"),
                "status":              "A",
                "cliente":             random.choice(CLIENTES),
                "valor":               round(random.uniform(55, 250), 2),
                "telefone":            f"(82) 9{random.randint(8000,9999)}-{random.randint(1000,9999)}",
                "bairro":              random.choice(BAIRROS),
                "connection_status":   random.choice(["FA", "OK", "SU"]),
                "trust_unlock_active": "S" if is_unlock else "N",
            })
        for _ in range(random.randint(2, 6)):
            full_rows.append({
                "data_vencimento":     due_date.strftime("%Y-%m-%d"),
                "status":              "P",
                "cliente":             random.choice(CLIENTES),
                "valor":               round(random.uniform(55, 250), 2),
                "telefone":            f"(82) 9{random.randint(8000,9999)}-{random.randint(1000,9999)}",
                "bairro":              random.choice(BAIRROS),
                "connection_status":   "OK",
                "trust_unlock_active": "N",
            })

    return {
        "delinquency_summary": pd.DataFrame(summary_rows),
        "full_data":           pd.DataFrame(full_rows),
        "fetched_at":          datetime.now().isoformat(),
    }


# ─── Data Fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=settings.CACHE_TTL, show_spinner="Buscando dados da API IXC...")
def fetch_report_data_raw() -> list | None:
    try:
        url = f"{settings.API_BASE_URL}/financial/inadiplencia"
        params = {"view": "by_date"}
        with httpx.Client(timeout=settings.API_HTTP_TIMEOUT) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.warning(f"Backend unreachable ({e}), using mock data.")
        return None

def fetch_bill_details(date_str):
    """Fetches bill details for a specific date."""
    try:
        url = f"{settings.API_BASE_URL}/financial/detalhes"
        params = {"date": date_str}
        with httpx.Client(timeout=15) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching bill details: {e}")
        return None

def process_metrics_to_legacy_format(metrics_list):
    """Maps the new backend fields to the format expected by the ECharts logic."""
    if not metrics_list:
        return pd.DataFrame()
        
    mapped = []
    for m in metrics_list:
        mapped.append({
            "Vencimento": m["date"],
            "Desbloqueio de Confiança": m["status"]["desbloqueio_confianca"],
            "Crônico": m["status"]["possiveis_cancelamentos"],
            "Transição": m["status"]["bloqueados"],
            "Vencimento Padrão": m["status"]["atrasados"],
            "Em Dia": m["status"]["pagos"]
        })
    return pd.DataFrame(mapped)


def is_valid_report_data(data: dict | None) -> bool:
    if not data or not isinstance(data, dict):
        return False
    summary = data.get("delinquency_summary")
    return summary is not None and not (isinstance(summary, pd.DataFrame) and summary.empty)


# ─── Load / Refresh ────────────────────────────────────────────────────────────
# ─── Load / Refresh ────────────────────────────────────────────────────────────
if generate_btn:
    st.cache_data.clear()
    raw_metrics = fetch_report_data_raw()
    if raw_metrics:
        st.session_state.report_data = {"delinquency_summary": process_metrics_to_legacy_format(raw_metrics), "fetched_at": datetime.now().isoformat()}
        st.toast("✅ Dados atualizados!", icon="✅")
    else:
        st.session_state.report_data = generate_mock_data()
elif st.session_state.report_data is None:
    raw_metrics = fetch_report_data_raw()
    if raw_metrics:
        st.session_state.report_data = {"delinquency_summary": process_metrics_to_legacy_format(raw_metrics), "fetched_at": datetime.now().isoformat()}
    else:
        st.session_state.report_data = generate_mock_data()


# ─── Semi-donut chart builder ──────────────────────────────────────────────────
#
# Strategy: use PIXEL-based center + radius so donuts never scale with canvas.
# Canvas width is fixed at ~1200px (matches Streamlit wide layout minus sidebar).
# Each donut slot is SLOT_W × SLOT_H px.  Radius is a fixed px value.
# Labels are positioned in absolute px via the graphic layer.

COLUMNS  = 10      # donuts per row (30 days → 3 rows)
SLOT_W   = 140     # px — SLOT_W > 2*OUTER_R+20 prevents horizontal overlap
SLOT_H   = 110     # px — SLOT_H > OUTER_R + 28(label) + 16 prevents vertical overlap
LEG_H    = 48      # px legend strip
OUTER_R  = 46      # px outer radius
INNER_R  = 27      # px inner radius (hole)
PAD_L    = 20      # px side padding


def build_semi_donut_chart(all_df: pd.DataFrame) -> tuple[dict, int]:
    rows_data  = all_df.sort_values("Vencimento").to_dict("records")
    n          = len(rows_data)
    n_rows     = (n + COLUMNS - 1) // COLUMNS

    # Total canvas dimensions (px)
    canvas_w   = PAD_L * 2 + COLUMNS * SLOT_W
    # cy_px = LEG_H + row_i*SLOT_H + OUTER_R + 10
    # Slot bottom = LEG_H + (row_i+1)*SLOT_H
    # Space below flat edge: SLOT_H - OUTER_R - 10 = 110 - 46 - 10 = 54px  ✓
    canvas_h   = LEG_H + n_rows * SLOT_H + 4

    series   = []
    graphics = []

    for idx, row in enumerate(rows_data):
        col_i = idx % COLUMNS
        row_i = idx // COLUMNS

        # cy_px: centre of the semi-circle within its slot.
        # The arc top = cy_px - OUTER_R.  We need cy_px - OUTER_R >= LEG_H + row_i*SLOT_H + 8
        # → cy_px >= OUTER_R + 8.  Place at OUTER_R + 10 below the slot top.
        cx_px = PAD_L + col_i * SLOT_W + SLOT_W // 2
        cy_px = LEG_H + row_i * SLOT_H + OUTER_R + 10

        date_str = pd.to_datetime(row["Vencimento"], dayfirst=True).strftime("%d/%m")
        total    = sum(int(row.get(s, 0)) for s in STATUSES)

        pie_data = [
            {
                "name":      s,
                "value":     float(row.get(s, 0)),
                "itemStyle": {"color": STATUS_COLORS_MAP[s]},
            }
            for s in STATUSES
            if float(row.get(s, 0)) > 0
        ]

        # Main arc
        series.append({
            "type":        "pie",
            "radius":      [INNER_R, OUTER_R],   # px integers, not %
            "center":      [cx_px, cy_px],        # px integers
            "startAngle":  180,
            "endAngle":    360,
            "label":       {"show": False},
            "labelLine":   {"show": False},
            "itemStyle":   {"borderWidth": 1.5, "borderColor": "#0b0f1a"},
            "emphasis": {
                "label": {
                    "show":       True,
                    "formatter":  "{b}: {c} ({d}%)",
                    "fontSize":   11,
                    "color":      "#f1f5f9",
                    "fontFamily": "Sora, sans-serif",
                },
                "itemStyle": {"shadowBlur": 8, "shadowColor": "rgba(255,255,255,0.15)"},
            },
            "data": pie_data,
        })

        # Inner fill (hole cover)
        series.append({
            "type":       "pie",
            "radius":     [0, INNER_R - 2],
            "center":     [cx_px, cy_px],
            "startAngle": 180,
            "endAngle":   360,
            "silent":     True,
            "label":      {"show": False},
            "labelLine":  {"show": False},
            "data": [{"value": 1, "itemStyle": {"color": "#0d1117"}}],
        })

        # Date label — sits just below the flat bottom edge of the arc (cy_px itself)
        graphics.append({
            "type":  "text",
            "left":  cx_px,
            "top":   cy_px + 8,
            "style": {
                "text":       date_str,
                "textAlign":  "center",
                "fill":       "#64748b",
                "fontSize":   9,
                "fontWeight": "600",
                "fontFamily": "Sora, sans-serif",
            },
        })
        # Total count label — one line below the date
        graphics.append({
            "type":  "text",
            "left":  cx_px,
            "top":   cy_px + 22,
            "style": {
                "text":       f"{total:,}",
                "textAlign":  "center",
                "fill":       "#94a3b8",
                "fontSize":   10,
                "fontWeight": "700",
                "fontFamily": "'JetBrains Mono', monospace",
            },
        })

    legend = {
        "data": [
            {"name": s, "itemStyle": {"color": STATUS_COLORS_MAP[s]}}
            for s in STATUSES
        ],
        "top":        4,
        "left":       "center",
        "icon":       "circle",
        "itemWidth":  8,
        "itemHeight": 8,
        "itemGap":    20,
        "textStyle":  {"color": "#64748b", "fontSize": 11, "fontFamily": "Sora, sans-serif"},
    }

    opts = {
        "backgroundColor": "#0d1117",
        "tooltip": {
            "trigger":         "item",
            "backgroundColor": "#111827",
            "borderColor":     "rgba(255,255,255,0.1)",
            "textStyle":       {"color": "#f1f5f9", "fontSize": 12, "fontFamily": "Sora, sans-serif"},
            "formatter":       "{b}: <b>{c}</b> ({d}%)",
        },
        "legend":  legend,
        "graphic": graphics,
        "series":  series,
    }
    return opts, canvas_h


# ─── Main Dashboard ────────────────────────────────────────────────────────────
if st.session_state.report_data:
    report_data = st.session_state.report_data
    summary_df  = report_data.get("delinquency_summary", pd.DataFrame())

    if not summary_df.empty:

        def get_total(col: str) -> int:
            return int(summary_df[col].sum()) if col in summary_df.columns else 0

        total_open  = sum(get_total(s) for s in DELINQUENT)
        cronico     = get_total("Crônico")
        desbloqueio = get_total("Desbloqueio de Confiança")
        em_dia      = get_total("Em Dia")

        # ── Metric Cards ──────────────────────────────────────────────────────
        st.markdown(
            f"""
<div class="metrics-row">
    <div class="metric-card blue">
        <div class="metric-card-accent"></div>
        <div class="metric-card-glow"></div>
        <span class="metric-icon">📄</span>
        <div class="metric-label">Total em Aberto</div>
        <div class="metric-value">{total_open:,}</div>
        <div class="metric-sub">faturas inadimplentes no período</div>
    </div>
    <div class="metric-card red">
        <div class="metric-card-accent"></div>
        <div class="metric-card-glow"></div>
        <span class="metric-icon">🛑</span>
        <div class="metric-label">Crônico</div>
        <div class="metric-value">{cronico:,}</div>
        <div class="metric-sub">acima de 9 dias de atraso</div>
    </div>
    <div class="metric-card amber">
        <div class="metric-card-accent"></div>
        <div class="metric-card-glow"></div>
        <span class="metric-icon">🔓</span>
        <div class="metric-label">Desbloqueio</div>
        <div class="metric-value">{desbloqueio:,}</div>
        <div class="metric-sub">desbloqueio de confiança ativo</div>
    </div>
    <div class="metric-card green">
        <div class="metric-card-accent"></div>
        <div class="metric-card-glow"></div>
        <span class="metric-icon">✅</span>
        <div class="metric-label">Em Dia</div>
        <div class="metric-value">{em_dia:,}</div>
        <div class="metric-sub">clientes adimplentes</div>
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        # ── Section header ────────────────────────────────────────────────────
        fetched_str = report_data.get("fetched_at", "")
        meta_text   = ("🕒 " + fetched_str[:19].replace("T", " ")) if fetched_str else ""
        st.markdown(
            f"""
<div class="section-header">
    <div class="section-dot"></div>
    <span class="section-title">📅 Tendência de Inadimplência por Vencimento</span>
    <span class="section-meta">{meta_text}</span>
</div>
""",
            unsafe_allow_html=True,
        )

        # ── Single unified semi-donut chart for all days ─────────────────────
        summary_df = summary_df.copy()
        summary_df["_dt"] = pd.to_datetime(summary_df["Vencimento"], dayfirst=True)
        summary_df = summary_df.sort_values("_dt").drop(columns=["_dt"])

        opts, chart_height = build_semi_donut_chart(summary_df)
        canvas_w = PAD_L * 2 + COLUMNS * SLOT_W

        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st_echarts(options=opts, height=f"{chart_height}px", width=f"{canvas_w}px")
        st.markdown("</div>", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════════════
        # DATE SELECTOR + DETAIL TABLE
        # ══════════════════════════════════════════════════════════════════════
        st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

        dates = [d for d in summary_df["Vencimento"]] # They already come as dd-mm-yyyy from backend
        selected_date_val = st.selectbox(
            "📅 Selecione a Data de Vencimento para ver detalhes:",
            options=["— Selecione uma data —"] + dates,
        )
        if selected_date_val != "— Selecione uma data —":
            st.session_state.selected_date = selected_date_val

        if st.session_state.selected_date:
            # Format date for display (selected_date is dd-mm-yyyy)
            display_date = st.session_state.selected_date.replace("-", "/")
            st.markdown(
                f"""
<div class="date-detail-banner">
    <div class="date-badge">{display_date}</div>
    <div>
        <div class="date-label">📝 Detalhes do Vencimento</div>
        <div class="date-sub">Clientes com faturas em aberto nesta data</div>
    </div>
</div>
""",
                unsafe_allow_html=True,
            )

            details_list = fetch_bill_details(st.session_state.selected_date)
            if details_list:
                details = pd.DataFrame(details_list)
                
                if not details.empty:
                    today_ts = pd.Timestamp.normalize(pd.Timestamp.now())
                    details["venc_dt"] = pd.to_datetime(details["data_vencimento"])
                    details["atraso"] = (today_ts - details["venc_dt"]).dt.days

                    def categorize_risk_v2(row):
                        if row.get("desbloqueio_ativo") == "S":
                            return "🔵 Desbloqueio"
                        d = row["atraso"]
                        if d > 9:       return "🔴 Crônico"
                        if 7 <= d <= 9: return "🟠 Transição"
                        if d >= 1:      return "🟡 Vencido"
                        return "🟢 Em Dia"

                    details["risk_category"] = details.apply(categorize_risk_v2, axis=1)
                    display_df = (
                        details[[
                            "risk_category", "cliente_nome", "valor", "atraso", "status_internet"
                        ]]
                        .rename(columns={
                            "risk_category":     "Risco / Status",
                            "cliente_nome":      "Nome do Cliente",
                            "valor":             "Valor da Fatura",
                            "atraso":            "Dias de Atraso",
                            "status_internet":   "Internet",
                        })
                        .sort_values("Dias de Atraso", ascending=False)
                    )

                    def highlight_rows_v2(row):
                        risk = row["Risco / Status"]
                        if "🔵" in risk:
                            return ["background-color:#1e1b4b;color:#a5b4fc"] * len(row)
                        d = row["Dias de Atraso"]
                        if d > 9:       return ["background-color:#1f0f0f;color:#fca5a5"] * len(row)
                        if 7 <= d <= 9: return ["background-color:#1a1208;color:#fdba74"] * len(row)
                        if d >= 1:      return ["background-color:#1a1700;color:#fde047"] * len(row)
                        return [""] * len(row)

                    st.dataframe(
                        display_df.style.apply(highlight_rows_v2, axis=1),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Valor da Fatura": st.column_config.NumberColumn(format="R$ %.2f"),
                            "Dias de Atraso":  st.column_config.NumberColumn(format="%d dias"),
                        },
                    )

                    st.divider()
                    c1, c2, c3, c4, c5 = st.columns(5)
                    n_unlock = len(details[details.get("desbloqueio_ativo") == "S"])
                    c1.metric("🔴 Crônico",        len(details[details["atraso"] > 9]))
                    c2.metric("🟠 Transição",       len(details[(details["atraso"] >= 7) & (details["atraso"] <= 9)]))
                    c3.metric("🔵 Desbloqueio",     n_unlock)
                    c4.metric("💰 Valor Total",     f"R$ {details['valor'].astype(float).sum():,.2f}")
                    c5.metric("📊 Média de Atraso", f"{details['atraso'].mean():.1f} dias")
                else:
                    st.info("Nenhum registro em aberto encontrado para esta data.")
        else:
            st.markdown(
                """
<div class="hint-box">
    <span style="font-size:1.2rem;">👆</span>
    Selecione uma data de vencimento acima para explorar os detalhes dos clientes.
</div>
""",
                unsafe_allow_html=True,
            )

# ─── Welcome Screen ────────────────────────────────────────────────────────────
else:
    st.markdown(
        f"""
<div class="welcome-card">
    <div style="font-size:3.5rem;margin-bottom:1rem;">📊</div>
    <h2>Bem-vindo à Plataforma IXC</h2>
    <p>Análise inteligente de inadimplência com dados em tempo real.</p>
    <div style="max-width:480px;margin:1.5rem auto 0;">
        <div class="welcome-step">
            <div class="step-num">1</div>
            <span>Os dados dos últimos <strong style="color:#a5b4fc;">{settings.REPORT_DAYS} dias</strong> são carregados automaticamente.</span>
        </div>
        <div class="welcome-step">
            <div class="step-num">2</div>
            <span>Clique em <strong style="color:#a5b4fc;">"Gerar / Atualizar Dados"</strong> na barra lateral para forçar uma atualização.</span>
        </div>
        <div class="welcome-step">
            <div class="step-num">3</div>
            <span>Analise tendências por vencimento e explore os detalhes por cliente.</span>
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )