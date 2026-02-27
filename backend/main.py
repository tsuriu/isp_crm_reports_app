from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
from config.settings import settings
from loguru import logger
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import pandas as pd
import asyncio
from ixc.sync import sync_customers, sync_contracts_and_bills
from utils.storage import get_storage

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa o agendador
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        sync_contracts_and_bills, 
        'interval', 
        minutes=settings.SYNC_INTERVAL_MINUTES
    )
    scheduler.add_job(
        sync_customers,
        'cron',
        hour=settings.SYNC_CUSTOMERS_HOUR,
        minute=0
    )
    scheduler.start()
    logger.info(f"🚀 Agendador APScheduler iniciado. Sincronização IXC ativa (Clie: {settings.SYNC_CUSTOMERS_HOUR}h, Cont/Bol: {settings.SYNC_INTERVAL_MINUTES}m).")
    
    # 🔄 Verificação proativa na inicialização
    bills_storage = get_storage(settings.STORAGE_PATH_BOLETOS)
    contracts_storage = get_storage(settings.STORAGE_PATH_CONTRATOS)
    customers_storage = get_storage(settings.STORAGE_PATH_CLIENTES)
    
    if not bills_storage.get_all() or not contracts_storage.get_all() or not customers_storage.get_all():
        logger.warning("Dados não encontrados. Iniciando sincronização forçada de inicialização.")
        asyncio.create_task(sync_customers())
        asyncio.create_task(sync_contracts_and_bills())
    else:
        logger.info("Dados locais encontrados. Aguardando próximo agendamento ou comando manual.")
    
    yield
    
    # Encerra o agendador ao desligar a aplicação
    scheduler.shutdown()
    logger.info("🛑 Agendador APScheduler encerrado.")

app = FastAPI(title="IXC Reporting API", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits access from Grafana and local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReportRequest(BaseModel):
    start_date: str
    end_date: str
    refresh: bool = False

def serialize_data(data: Any) -> Any:
    """
    Recursively converts DataFrames to JSON-serializable formats (lists of dicts).
    """
    if isinstance(data, pd.DataFrame):
        return data.to_dict(orient="records")
    elif isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_data(i) for i in data]
    return data

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/sync")
async def force_sync(services: str = "all"):
    """
    Endpoint to manually trigger IXC data synchronization.
    Accepts a 'services' parameter: 'all', 'customers', 'contracts', or a comma-separated list.
    """
    logger.info(f"API Request: Force Sync triggered for services: {services}")
    try:
        requested = [s.strip().lower() for s in services.split(",")]
        
        sync_all = "all" in requested
        sync_customers_flag = sync_all or "customers" in requested
        sync_contracts_flag = sync_all or "contracts" in requested
        sync_bills_flag = sync_all or "bills" in requested or "boletos" in requested
        
        if sync_customers_flag:
            asyncio.create_task(sync_customers())
        if sync_contracts_flag or sync_bills_flag:
            # Note: Both are handled by the same background task
            asyncio.create_task(sync_contracts_and_bills())
            
        if not any([sync_customers_flag, sync_contracts_flag, sync_bills_flag]):
            raise HTTPException(status_code=400, detail=f"Invalid services requested: {services}. Available: all, customers, contracts, bills")
            
        return {
            "message": "Sync started in background",
            "services_triggered": {
                "customers": sync_customers_flag,
                "contracts": sync_contracts_flag,
                "bills": sync_bills_flag
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering force sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/financial/inadiplencia")
async def get_delinquency_metrics(view: str = "by_date"):
    """
    Returns specific delinquency metrics based on stored IXC data.
    - view='by_date': Returns an array with daily breakdown.
    - view='total': Returns a single object with aggregated totals.
    """
    logger.info(f"API Request: /financial/inadiplencia?view={view}")
    try:
        # 1. Load data from TinyDB
        bills_storage = get_storage(settings.STORAGE_PATH_BOLETOS)
        contracts_storage = get_storage(settings.STORAGE_PATH_CONTRATOS)
        
        bills_data = bills_storage.get_all()
        contracts_data = contracts_storage.get_all()
        
        if not bills_data or not contracts_data:
            logger.warning("Acesso ao endpoint /financial/inadiplencia sem dados. Iniciando sincronização em background.")
            asyncio.create_task(sync_customers())
            asyncio.create_task(sync_contracts_and_bills())
            return [] if view == "by_date" else {}
            
        df_bills = pd.DataFrame(bills_data)
        df_contracts = pd.DataFrame(contracts_data)
        
        # 2. Setup dates and calculate days late
        today = pd.Timestamp.now().normalize()
        df_bills['data_vencimento'] = pd.to_datetime(df_bills['data_vencimento'], errors='coerce')
        df_bills['days_late'] = (today - df_bills['data_vencimento']).dt.days
        
        # Get unique clients with trust unlock
        trust_unlock_clients = set()
        if not df_contracts.empty and 'desbloqueio_confianca_ativo' in df_contracts.columns:
            trust_unlock_clients = set(df_contracts[df_contracts['desbloqueio_confianca_ativo'] == 'S']['id_cliente'].astype(str).unique())

        # Get mapping of client_id to internet_status
        client_internet_status = {}
        if not df_contracts.empty and 'id_cliente' in df_contracts.columns and 'status_internet' in df_contracts.columns:
            # Ensure index is string for consistent mapping
            client_internet_status = df_contracts.copy()
            client_internet_status['id_cliente'] = client_internet_status['id_cliente'].astype(str)
            client_internet_status = client_internet_status.set_index('id_cliente')['status_internet'].to_dict()

        df_bills['category'] = 'em_dia'
        overdue_mask = (df_bills['status'] == 'A') & (df_bills['days_late'] >= 1)
        trust_mask = df_bills['id_cliente'].astype(str).isin(trust_unlock_clients)
        
        df_bills.loc[overdue_mask & trust_mask, 'category'] = 'desbloqueio_confianca'
        non_trust_overdue = overdue_mask & ~trust_mask
        
        df_bills.loc[non_trust_overdue & (df_bills['days_late'] >= 1) & (df_bills['days_late'] <= 6), 'category'] = 'vencimento_padrao'
        df_bills.loc[non_trust_overdue & (df_bills['days_late'] >= 7) & (df_bills['days_late'] <= 10), 'category'] = 'transicao'
        df_bills.loc[non_trust_overdue & (df_bills['days_late'] >= 11), 'category'] = 'cronico'

        if view == "total":
            return {
                "date": today.strftime("%d-%m-%Y"),
                "total_boletos": len(df_bills),
                "report_days": settings.REPORT_DAYS,
                "status": {
                    "em_dia": int((df_bills['category'] == 'em_dia').sum()),
                    "vencimento_padrao": int((df_bills['category'] == 'vencimento_padrao').sum()),
                    "transicao": int((df_bills['category'] == 'transicao').sum()),
                    "cronico": int((df_bills['category'] == 'cronico').sum()),
                    "desbloqueio_confianca": int((df_bills['category'] == 'desbloqueio_confianca').sum())
                }
            }

        # Default: by_date
        results = []
        for i in range(settings.REPORT_DAYS + 1):
            target_date = today - timedelta(days=i)
            target_date_str = target_date.strftime("%d-%m-%Y")
            
            date_mask = df_bills['data_vencimento'].dt.normalize() == target_date
            df_date = df_bills[date_mask]
            
            if df_date.empty:
                continue
            
            results.append({
                "date": target_date_str,
                "total_boletos": len(df_date),
                "status": {
                    "em_dia": int((df_date['category'] == 'em_dia').sum()),
                    "vencimento_padrao": int((df_date['category'] == 'vencimento_padrao').sum()),
                    "transicao": int((df_date['category'] == 'transicao').sum()),
                    "cronico": int((df_date['category'] == 'cronico').sum()),
                    "desbloqueio_confianca": int((df_date['category'] == 'desbloqueio_confianca').sum())
                }
            })
            
        return results
    except Exception as e:
        logger.error(f"Error calculating delinquency metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/financial/detalhes")
async def get_bill_details(date: str):
    """
    Returns detailed open bill records for a specific date (dd-mm-yyyy).
    Enriches with customer name and internet status.
    """
    logger.info(f"API Request: /financial/detalhes?date={date}")
    try:
        # 1. Load data
        bills_storage = get_storage(settings.STORAGE_PATH_BOLETOS)
        contracts_storage = get_storage(settings.STORAGE_PATH_CONTRATOS)
        customers_storage = get_storage(settings.STORAGE_PATH_CLIENTES)
        
        bills_data = bills_storage.get_all()
        contracts_data = contracts_storage.get_all()
        customers_data = customers_storage.get_all()
        
        if not bills_data:
            return []
            
        df_bills = pd.DataFrame(bills_data)
        
        # 2. Filter by date and status 'A' (Open)
        df_bills['data_vencimento_dt'] = pd.to_datetime(df_bills['data_vencimento'], errors='coerce')
        target_dt = pd.to_datetime(date, format="%d-%m-%Y", errors='coerce')
        
        if pd.isna(target_dt):
            raise HTTPException(status_code=400, detail="Invalid date format. Use dd-mm-yyyy")
            
        mask = (df_bills['data_vencimento_dt'].dt.normalize() == target_dt.normalize()) & (df_bills['status'] == 'A')
        df_filtered = df_bills[mask].copy()
        
        if df_filtered.empty:
            return []
            
        # 3. Enrich with Customer Names
        if customers_data:
            df_cust = pd.DataFrame(customers_data)
            if 'id' in df_cust.columns and 'razao' in df_cust.columns:
                cust_map = df_cust.set_index('id')['razao'].to_dict()
                df_filtered['cliente_nome'] = df_filtered['id_cliente'].astype(str).map(lambda x: cust_map.get(x, "Desconhecido"))
        
        # 4. Enrich with Internet Status and Trust Unlock
        df_contracts = pd.DataFrame()
        if contracts_data:
            df_cont = pd.DataFrame(contracts_data)
            df_contracts = df_cont.copy()
            if 'id_cliente' in df_cont.columns:
                cont_status_map = df_cont.set_index('id_cliente')['status_internet'].to_dict()
                trust_map = df_cont.set_index('id_cliente')['desbloqueio_confianca_ativo'].to_dict()
                
                df_filtered['status_internet'] = df_filtered['id_cliente'].astype(str).map(lambda x: cont_status_map.get(x, "N/A"))
                df_filtered['desbloqueio_confianca_ativo'] = df_filtered['id_cliente'].astype(str).map(lambda x: trust_map.get(x, "N"))

        # 5. Enrich with Phone and Neighborhood
        if customers_data:
            df_cust = pd.DataFrame(customers_data)
            if 'id' in df_cust.columns:
                phone_map = df_cust.set_index('id')['telefone_celular'].to_dict()
                # fallback to fone if celular is empty
                fone_map = df_cust.set_index('id')['fone'].to_dict()
                bairro_map = df_cust.set_index('id')['bairro'].to_dict()
                
                def get_phone(x):
                    cel = phone_map.get(x, "")
                    return cel if cel else fone_map.get(x, "")
                
                df_filtered['telefone'] = df_filtered['id_cliente'].astype(str).map(get_phone)
                df_filtered['bairro'] = df_filtered['id_cliente'].astype(str).map(lambda x: bairro_map.get(x, ""))

        # Calculate days_late exactly as in the inadiplencia endpoint
        today = pd.Timestamp.now().normalize()
        df_filtered['days_late'] = (today - df_filtered['data_vencimento_dt'].dt.normalize()).dt.days

        # Define category exactly as in the inadiplencia endpoint for the UI status mapping
        df_filtered['category'] = 'em_dia'
        
        # Get mapping variables for trust
        trust_unlock_clients = set()
        if not df_contracts.empty and 'desbloqueio_confianca_ativo' in df_contracts.columns:
            trust_unlock_clients = set(df_contracts[df_contracts['desbloqueio_confianca_ativo'] == 'S']['id_cliente'].astype(str).unique())

        client_internet_status = {}
        if not df_contracts.empty and 'id_cliente' in df_contracts.columns and 'status_internet' in df_contracts.columns:
            client_internet_status = df_contracts.drop_duplicates('id_cliente').set_index('id_cliente')['status_internet'].to_dict()

        # Vectorized status categorization
        if not df_filtered.empty:
            overdue_mask = df_filtered['days_late'] > 0
            
            # Helper to check trust unlock
            df_filtered['has_trust'] = df_filtered['id_cliente'].astype(str).isin(trust_unlock_clients)
            df_filtered['conn_status'] = df_filtered['id_cliente'].astype(str).map(client_internet_status)
            
            trust_mask = (df_filtered['has_trust'] == True) & (df_filtered['conn_status'] == 'A') & overdue_mask
            df_filtered.loc[trust_mask, 'category'] = 'desbloqueio_confianca'
            
            # Non-trust overdue logic
            non_trust_overdue = overdue_mask & ~trust_mask
            
            df_filtered.loc[non_trust_overdue & (df_filtered['days_late'] >= 1) & (df_filtered['days_late'] <= 6), 'category'] = 'vencimento_padrao'
            df_filtered.loc[non_trust_overdue & (df_filtered['days_late'] >= 7) & (df_filtered['days_late'] <= 10), 'category'] = 'transicao'
            df_filtered.loc[non_trust_overdue & (df_filtered['days_late'] >= 11), 'category'] = 'cronico'

        # Structure final output to exact specifications
        final_results = []
        for index, row in df_filtered.iterrows():
            final_results.append({
                "status": row.get('category', 'em_dia'), # E.g., 'em_dia', 'vencimento_padrao', 'transicao', etc.
                "Nome do Cliente": row.get('cliente_nome', 'Desconhecido'),
                "Dias de Atraso": row.get('days_late', 0),
                "Telefone": row.get('telefone', ''),
                "Bairro": row.get('bairro', ''),
                "Status da Conexão": row.get('status_internet', 'N/A')
            })

        return final_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bill details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
