import streamlit as st
import asyncio
import time
from datetime import datetime, timedelta
import httpx
from utils.exporters import ReportExporter
from config.settings import settings
from loguru import logger
import pandas as pd

# Page Config
st.set_page_config(
    page_title="Plataforma de Relatórios IXC",
    page_icon="📊",
    layout="wide"
)

# Initialize Session State
if 'report_data' not in st.session_state:
    st.session_state.report_data = None

if 'selected_date' not in st.session_state:
    st.session_state.selected_date = None

# Custom CSS for Premium Look
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .report-card {
        padding: 20px;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    /* Section headers (from alternative) */
    .section-header {
        background-color: #1f2937;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin: 1.5rem 0 1rem 0;
        border-left: 3px solid #60a5fa;
    }
    .section-title {
        color: #e5e7eb;
        font-size: 1rem;
        font-weight: 500;
        margin: 0;
    }
    .metric-card {
        padding: 15px;
        border-radius: 8px;
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-label { font-size: 0.85rem; color: #586069; margin-bottom: 5px; }
    .metric-value { font-size: 1.5rem; font-weight: 600; color: #24292e; }
    </style>
    """, unsafe_allow_html=True)

# Cabeçalho da Aplicação
st.title("🚀 Plataforma de Relatórios IXC")
st.markdown("---")

# Sidebar - Configuração
with st.sidebar:
    st.header("🏢 Relatórios IXC")
    selected_dashboard = st.selectbox(
        "Selecione o Dashboard",
        ["📊 Gestão de Inadimplência", "📉 Métricas de Inadimplência (Real-time)"]
    )
    
    st.markdown("---")
    st.header("📅 Período do Relatório")
    
    # O intervalo agora é fixo pelas configurações
    end_date = datetime.now()
    start_date = end_date - timedelta(days=settings.REPORT_DAYS)
    
    st.caption(f"Intervalo: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')} ({settings.REPORT_DAYS} dias)")
    
    generate_btn = st.sidebar.button("📊 Gerar Relatório Histórico", type="primary")
    
    st.markdown("---")
    with st.expander("🔄 Sincronização Forçada"):
        sync_option = st.radio("Selecione o que sincronizar:", ["Tudo", "Clientes", "Contratos", "Boletos"])
        if st.button("Executar Sincronização"):
            service_map = {
                "Tudo": "all", 
                "Clientes": "customers", 
                "Contratos": "contracts",
                "Boletos": "bills"
            }
            try:
                sync_url = f"{settings.API_BASE_URL}/sync"
                with httpx.Client(timeout=10) as client:
                    resp = client.post(sync_url, params={"services": service_map[sync_option]})
                    resp.raise_for_status()
                    st.success(f"Sincronização de '{sync_option}' iniciada!")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao sincronizar: {e}")

    st.markdown("---")
    with st.expander("📉 Definições de Status"):
        st.markdown("""
        Para facilitar a cobrança estratégica, o painel categoriza os clientes com base no atraso e status no IXC:
        
        - 🟢 **Em Dia**: Pagamentos realizados ou faturas ainda não vencidas.
        - 🟡 **Vencimento Padrão**: 1 a 6 dias de atraso. Janela de "lembrete".
        - 🟠 **Transição**: 7 a 9 dias de atraso. Janela crítica para gestão de suspensão.
        - 🔴 **Crônico**: Mais de 9 dias de atraso. Contas de alto risco.
        - 🔵 **Desbloqueio de Confiança**: Clientes com desbloqueio ativo no IXC.
        """)

# Lógica de Busca de Dados (Cache)
def fetch_delinquency_metrics(view="by_date"):
    """Fetches real-time delinquency metrics."""
    try:
        url = f"{settings.API_BASE_URL}/financial/inadiplencia"
        params = {"view": view}
        with httpx.Client(timeout=10) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching delinquency metrics: {e}")
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

def is_valid_report_data(data):
    """Checks if the data dictionary contains the required keys and non-empty results."""
    if not data or not isinstance(data, dict):
        return False
    # Validate required structures
    summary = data.get('delinquency_summary')
    if summary is None or (isinstance(summary, pd.DataFrame) and summary.empty):
        return False
    return True

def render_metric_cards(selected_metrics):
    """Helper to render standardized metric cards."""
    if not selected_metrics:
        return
        
    st.markdown(f"**Data da Amostra:** {selected_metrics['date']}")
    
    # High Level Counters
    col_total, col_empty = st.columns(2)
    col_total.metric("Total de Boletos", selected_metrics['total_boletos'])
    
    status = selected_metrics.get('status', {})
    
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col4, m_col5, _ = st.columns(3)
    
    with m_col1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">✅ Pagos</div>
            <div class="metric-value" style="color: #28a745;">{status.get('pagos', 0)}</div>
        </div>""", unsafe_allow_html=True)
        
    with m_col2:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">🟡 Atrasados (1-6d)</div>
            <div class="metric-value" style="color: #ffc107;">{status.get('atrasados', 0)}</div>
        </div>""", unsafe_allow_html=True)
        
    with m_col3:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">🟠 Bloqueados (7-10d)</div>
            <div class="metric-value" style="color: #fd7e14;">{status.get('bloqueados', 0)}</div>
        </div>""", unsafe_allow_html=True)
        
    with m_col4:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">🔴 Possíveis Cancel. (+11d)</div>
            <div class="metric-value" style="color: #dc3545;">{status.get('possiveis_cancelamentos', 0)}</div>
        </div>""", unsafe_allow_html=True)
        
    with m_col5:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">🔓 Desbloq. Confiança</div>
            <div class="metric-value" style="color: #007bff;">{status.get('desbloqueio_confianca', 0)}</div>
        </div>""", unsafe_allow_html=True)

# Lógica de Busca de Dados
# Lógica de Inicialização
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = 0

if generate_btn or (time.time() - st.session_state.last_refresh > 300): # 5 min default or button
    st.cache_data.clear()
    st.session_state.last_refresh = time.time()

# Main Dashboard Routing
if selected_dashboard == "📊 Gestão de Inadimplência":
    metrics_list = fetch_delinquency_metrics(view="by_date")
    
    if metrics_list:
        # Seção: Inadimplência por Data de Vencimento
        st.markdown("""
            <div class="section-header">
                <h2 class="section-title">📅 Painel de Inadimplência (Histórico)</h2>
            </div>
            """, unsafe_allow_html=True)
        
        st.caption("Análise Estratégica (Métricas consolidadas por data de vencimento)")
        
        # Prepara os dados para o gráfico
        chart_data = []
        for m in metrics_list:
            chart_data.append({
                "Vencimento": m["date"],
                "Desbloqueio de Confiança": m["status"]["desbloqueio_confianca"],
                "Crônico": m["status"]["possiveis_cancelamentos"], # Maps back correctly
                "Transição": m["status"]["bloqueados"],
                "Vencimento Padrão": m["status"]["atrasados"],
                "Pagos": m["status"]["pagos"]
            })
            
        chart_df = pd.DataFrame(chart_data)
        chart_df["_dt"] = pd.to_datetime(chart_df["Vencimento"], dayfirst=True)
        chart_df = chart_df.sort_values("_dt")
        
        # Gráfico de barras vertical
        st.bar_chart(
            chart_df,
            x="Vencimento",
            y=["Desbloqueio de Confiança", "Crônico", "Transição", "Vencimento Padrão", "Pagos"],
            color=["#1e88e5", "#e53935", "#fb8c00", "#fdd835", "#4caf50"],
            height=400
        )
        
        selected_date_val = st.selectbox(
            "📅 Selecione a Data de Vencimento para ver detalhes:", 
            options=["---"] + list(chart_df["Vencimento"].unique())
        )
        
        if selected_date_val != "---":
            st.session_state.selected_date = selected_date_val
            
        # Seção: Detalhes para a Data Selecionada
        if st.session_state.selected_date:
            st.markdown(f"""
                <div class="section-header">
                    <h2 class="section-title">📝 Detalhes para o Vencimento: {st.session_state.selected_date}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            details_list = fetch_bill_details(st.session_state.selected_date)
            if details_list:
                details = pd.DataFrame(details_list)
                
                # Transform data for display
                today = pd.Timestamp.now().normalize()
                details['venc_dt'] = pd.to_datetime(details['data_vencimento'], dayfirst=True, errors='coerce')
                details['atraso'] = (today - details['venc_dt']).dt.days
                
                def categorize_risk_v2(row):
                    days = row['atraso']
                    if row.get('desbloqueio_ativo') == 'S': return '🔓 Desbloqueio'
                    if days > 9: return '🛑 Crônico'
                    elif 7 <= days <= 9: return '⚠️ Transição'
                    elif days >= 1: return '🟡 Vencido'
                    return '✅ Em Dia'
                
                details['risk_category'] = details.apply(categorize_risk_v2, axis=1)
                
                display_df = details[[
                    'risk_category', 'cliente_nome', 'valor', 'atraso', 'status_internet'
                ]].rename(columns={
                    'risk_category': 'Risco / Status',
                    'cliente_nome': 'Nome do Cliente',
                    'valor': 'Valor da Fatura',
                    'atraso': 'Dias de Atraso',
                    'status_internet': 'Status Internet'
                })
                
                display_df = display_df.sort_values('Dias de Atraso', ascending=False)
                
                def highlight_rows_v2(row):
                    risk = row['Risco / Status']
                    if '🔓' in risk: return ['background-color: #e3f2fd; color: black'] * len(row)
                    days = row['Dias de Atraso']
                    if days > 9: return ['background-color: #ffcccc; color: black'] * len(row)
                    elif 7 <= days <= 9: return ['background-color: #ffe5cc; color: black'] * len(row)
                    elif days >= 1: return ['background-color: #fff9c4; color: black'] * len(row)
                    return [''] * len(row)
                
                st.dataframe(
                    display_df.style.apply(highlight_rows_v2, axis=1),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Valor da Fatura": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Dias de Atraso": st.column_config.NumberColumn(format="%d dias")
                    }
                )
                
                # Totais para a data selecionada
                st.divider()
                col1, col2, col3, col4, col5 = st.columns(5)
                
                chronic_count = len(details[details['atraso'] > 9])
                transition_count = len(details[(details['atraso'] >= 7) & (details['atraso'] <= 9)])
                trust_unlock_count = len(details[details.get('desbloqueio_ativo') == 'S'])
                total_amount = details['valor'].astype(float).sum()
                avg_days = details['atraso'].mean()
                
                col1.metric("🛑 Crônico", chronic_count)
                col2.metric("⚠️ Transição", transition_count)
                col3.metric("🔓 Desbloqueio", trust_unlock_count)
                col4.metric("💰 Valor Total", f"R$ {total_amount:,.2f}")
                col5.metric("📊 Média de Atraso", f"{avg_days:.1f} dias")
            else:
                st.info("Nenhum registro em aberto encontrado para esta data.")
        else:
            st.info("👆 Selecione uma data de vencimento no gráfico acima para ver os detalhes")
    else:
        st.warning("Não foi possível carregar os dados financeiros.")
    else:
        st.write("### Bem-vindo à Plataforma de Relatórios IXC!")
        st.write(f"1. Os dados são buscados automaticamente para os últimos **{settings.REPORT_DAYS} dias**.")
        st.write("2. Clique em **'Gerar / Atualizar Dados'** para uma atualização imediata.")
        st.write("3. Analise tendências de inadimplência e exporte relatórios.")
        st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80", caption="Inteligência Estratégica de Dados")

elif selected_dashboard == "📉 Métricas de Inadimplência (Real-time)":
    st.markdown("""
        <div class="section-header">
            <h2 class="section-title">📉 Métricas de Inadimplência (Atualizado a cada 15 min)</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Refresh Logic
    refresh_key = "last_metrics_refresh"
    if refresh_key not in st.session_state:
        st.session_state[refresh_key] = time.time()
    
    current_time = time.time()
    # Check if 15 minutes (900 seconds) have passed
    if current_time - st.session_state[refresh_key] > 900:
        st.cache_data.clear() # Clear cache for these specific metrics
        st.session_state[refresh_key] = current_time
        st.rerun()

    # View Selection
    view_option = st.radio("Escolha a Visualização:", ["📅 Histórico Diário", "📊 Consolidado (Total)"], horizontal=True)
    view_type = "by_date" if "Histórico" in view_option else "total"
    
    metrics_result = fetch_delinquency_metrics(view=view_type)
    
    if view_type == "by_date":
        if metrics_result and isinstance(metrics_result, list):
            # 1. Summary Chart
            df_metrics = pd.DataFrame([
                {
                    "Data": m["date"],
                    "Pagos": m["status"]["pagos"],
                    "Atrasados": m["status"]["atrasados"],
                    "Bloqueados": m["status"]["bloqueados"],
                    "Possíveis Cancel.": m["status"]["possiveis_cancelamentos"],
                    "Desbloq. Confiança": m["status"]["desbloqueio_confianca"]
                }
                for m in metrics_result
            ])
            
            df_metrics['date_dt'] = pd.to_datetime(df_metrics['Data'], format='%d-%m-%Y')
            df_metrics = df_metrics.sort_values('date_dt')
            
            st.subheader("📊 Tendência de Inadimplência (Últimos Dias)")
            st.area_chart(
                df_metrics,
                x="Data",
                y=["Pagos", "Atrasados", "Bloqueados", "Possíveis Cancel.", "Desbloq. Confiança"],
                color=["#28a745", "#ffc107", "#fd7e14", "#dc3545", "#007bff"]
            )
            
            st.markdown("---")
            
            # 2. Detailed View for a specific date
            selected_m_date = st.selectbox(
                "📅 Ver detalhes para a data:",
                options=[m["date"] for m in metrics_result]
            )
            
            selected_metrics = next((m for m in metrics_result if m["date"] == selected_m_date), None)
            render_metric_cards(selected_metrics)
        else:
            st.warning("Nenhum dado histórico encontrado para exibição.")
    else:
        # Total View
        if metrics_result and isinstance(metrics_result, dict):
            st.subheader(f"📍 Resumo Consolidado (Últimos {settings.REPORT_DAYS} dias)")
            render_metric_cards(metrics_result)
        else:
            st.error("Não foi possível carregar o resumo consolidado.")
            
    st.markdown("---")
    st.info(f"🔄 Próxima atualização em {int((900 - (current_time - st.session_state[refresh_key]))/60)} minutos.")

# O contador de cache agora é gerenciado pelo Streamlit através do container estático
# Para atualizações live, o usuário deve atualizar a página ou aguardar o próximo rerun natural
