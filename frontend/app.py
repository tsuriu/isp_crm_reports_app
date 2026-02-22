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
    </style>
    """, unsafe_allow_html=True)

# Cabeçalho da Aplicação
st.title("🚀 Plataforma de Relatórios IXC")
st.markdown("---")

# Sidebar - Configuração
with st.sidebar:
    st.header("🏢 Relatórios IXC")
    selected_dashboard = "📊 Gestão de Inadimplência"
    
    st.markdown("---")
    st.header("📅 Período do Relatório")
    
    # O intervalo agora é fixo pelas configurações
    end_date = datetime.now()
    start_date = end_date - timedelta(days=settings.REPORT_DAYS)
    
    st.caption(f"Intervalo: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')} ({settings.REPORT_DAYS} dias)")
    
    generate_btn = st.button("Gerar / Atualizar Dados")
    
    # 🕒 Live Cache Countdown
    if st.session_state.report_data and "fetched_at" in st.session_state.report_data:
        try:
            fetched_at = datetime.fromisoformat(st.session_state.report_data["fetched_at"])
            next_update_time = fetched_at + timedelta(seconds=settings.CACHE_TTL)
            
            counter_container = st.sidebar.empty()
            
            remaining_sec = (next_update_time - datetime.now()).total_seconds()
            if remaining_sec > 0:
                mins, secs = divmod(int(remaining_sec), 60)
                counter_container.info(f"🔄 Próxima Auto-Atualização em: {mins:02d}:{secs:02d}")
            else:
                counter_container.warning("⚠️ Dados desatualizados. Recomenda-se atualizar.")
        except Exception:
            pass

# Lógica de Busca de Dados (Cache)
@st.cache_data(ttl=settings.CACHE_TTL, show_spinner="Buscando dados mais recentes da API IXC...")
def fetch_report_data(start_str, end_str, refresh=False):
    """
    Cached wrapper for fetching report data from the FastAPI backend.
    """
    try:
        url = f"{settings.API_BASE_URL}/reports/financial"
        payload = {
            "start_date": start_str,
            "end_date": end_str,
            "refresh": refresh
        }
        
        with httpx.Client(timeout=settings.API_HTTP_TIMEOUT) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Post-process: Convert records back to DataFrames
            if "full_data" in data and isinstance(data["full_data"], list):
                data["full_data"] = pd.DataFrame(data["full_data"])
                
            if "delinquency_summary" in data and isinstance(data["delinquency_summary"], list):
                data["delinquency_summary"] = pd.DataFrame(data["delinquency_summary"])
            
            return data
    except Exception as e:
        logger.error(f"Erro em fetch_report_data: {e}")
        st.error(f"Erro de Conexão: Não foi possível alcançar o backend em {settings.API_BASE_URL}")
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

# Lógica de Busca de Dados
if generate_btn:
    new_data = fetch_report_data(start_date.isoformat(), end_date.isoformat(), refresh=True)
    if is_valid_report_data(new_data):
        st.session_state.report_data = new_data
        st.success("Dados atualizados com sucesso!")
    else:
        st.error("Falha na atualização: Recebidos dados inválidos ou vazios da API.")
elif st.session_state.report_data is None:
    # Carregamento automático ao atualizar (usa cache)
    new_data = fetch_report_data(start_date.isoformat(), end_date.isoformat(), refresh=False)
    if is_valid_report_data(new_data):
        st.session_state.report_data = new_data

# Main Dashboard Routing
if st.session_state.report_data:
    report_data = st.session_state.report_data
    summary_df = report_data.get('delinquency_summary', pd.DataFrame())
    
    if not summary_df.empty:
        # Seção: Inadimplência por Data de Vencimento
        st.markdown("""
            <div class="section-header">
                <h2 class="section-title">📅 Painel de Inadimplência</h2>
            </div>
            """, unsafe_allow_html=True)
        
        st.caption("Análise Estratégica (Clique em uma barra para ver detalhes)")
        
        # Prepara os dados para o gráfico
        chart_cols = ["Vencimento", "Desbloqueio de Confiança", "Crônico", "Transição", "Vencimento Padrão", "Em Dia"]
        chart_df = summary_df[chart_cols].copy()
        
        # Filtro: Mostrar apenas datas com registros de risco/inadimplência
        risk_mask = (
            (chart_df["Desbloqueio de Confiança"] > 0) | 
            (chart_df["Crônico"] > 0) | 
            (chart_df["Transição"] > 0) | 
            (chart_df["Vencimento Padrão"] > 0)
        )
        chart_df = chart_df[risk_mask]
        
        # Gráfico de barras vertical simples
        st.bar_chart(
            chart_df,
            x="Vencimento",
            y=["Desbloqueio de Confiança", "Crônico", "Transição", "Vencimento Padrão", "Em Dia"],
            color=["#1e88e5", "#e53935", "#fb8c00", "#fdd835", "#4caf50"],
            horizontal=False,
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
            
            full_df = report_data.get('full_data', pd.DataFrame())
            if not full_df.empty:
                full_df['data_vencimento'] = pd.to_datetime(full_df['data_vencimento'])
                target_date = pd.to_datetime(st.session_state.selected_date)
                
                details = full_df[
                    (full_df['data_vencimento'] == target_date) & 
                    (full_df['status'] == 'A') # Only open invoices in details
                ].copy()
                
                if not details.empty:
                    today = pd.Timestamp.normalize(pd.Timestamp.now())
                    details['atraso'] = (today - details['data_vencimento']).dt.days
                    
                    def categorize_risk(row):
                        days = row['atraso']
                        if row['trust_unlock_active'] == 'S': return '🔓 Desbloqueio'
                        if days > 9: return '🛑 Crônico'
                        elif 7 <= days <= 9: return '⚠️ Transição'
                        elif days >= 1: return '🟡 Vencido'
                        return '✅ Em Dia'
                    
                    details['risk_category'] = details.apply(categorize_risk, axis=1)
                    
                    display_df = details[[
                        'risk_category', 'cliente', 'valor', 'atraso', 'telefone', 'bairro', 'connection_status'
                    ]].rename(columns={
                        'risk_category': 'Risco / Status',
                        'cliente': 'Nome do Cliente',
                        'valor': 'Valor da Fatura',
                        'atraso': 'Dias de Atraso',
                        'telefone': 'Telefone',
                        'bairro': 'Bairro',
                        'connection_status': 'Status da Conexão'
                    })
                    
                    display_df = display_df.sort_values('Dias de Atraso', ascending=False)
                    
                    def highlight_rows(row):
                        risk = row['Risco / Status']
                        if '🔓' in risk: return ['background-color: #e3f2fd; color: black'] * len(row)
                        days = row['Dias de Atraso']
                        if days > 9: return ['background-color: #ffcccc; color: black'] * len(row)
                        elif 7 <= days <= 9: return ['background-color: #ffe5cc; color: black'] * len(row)
                        elif days >= 1: return ['background-color: #fff9c4; color: black'] * len(row)
                        return [''] * len(row)
                    
                    st.dataframe(
                        display_df.style.apply(highlight_rows, axis=1),
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
                    trust_unlock_count = len(details[details['trust_unlock_active'] == 'S'])
                    total_amount = details['valor'].sum()
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
            
    #     # Opções de Exportação
    #     st.markdown("---")
    #     st.subheader("📥 Exportar Relatórios")
    #     exp_col1, exp_col2 = st.columns(2)
        
    #     md_content = ReportExporter.to_markdown(report_data)
    #     html_content = ReportExporter.to_html(report_data)
        
    #     with exp_col1:
    #         st.download_button(
    #             label="Baixar Relatório Completo (Markdown)",
    #             data=md_content,
    #             file_name=f"relatorio_inadimplencia_{datetime.now().strftime('%Y%m%d')}.md",
    #             mime="text/markdown"
    #         )
    #     with exp_col2:
    #         st.download_button(
    #             label="Baixar Relatório Completo (HTML)",
    #             data=html_content,
    #             file_name=f"relatorio_inadimplencia_{datetime.now().strftime('%Y%m%d')}.html",
    #             mime="text/html"
    #         )
    # else:
    #     st.warning("No delinquency data available for this range.")
# Tratar Tela de Boas-vindas
else:
    st.write("### Bem-vindo à Plataforma de Relatórios IXC!")
    st.write(f"1. Os dados são buscados automaticamente para os últimos **{settings.REPORT_DAYS} dias**.")
    st.write("2. Clique em **'Gerar / Atualizar Dados'** para uma atualização imediata.")
    st.write("3. Analise tendências de inadimplência e exporte relatórios.")
    st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80", caption="Inteligência Estratégica de Dados")

# O contador de cache agora é gerenciado pelo Streamlit através do container estático
# Para atualizações live, o usuário deve atualizar a página ou aguardar o próximo rerun natural
