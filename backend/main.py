from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from reports.generator import ReportGenerator
from config.settings import settings
from loguru import logger
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import pandas as pd
import asyncio

generator = ReportGenerator()

async def scheduled_report_generation():
    """
    Tarefa agendada para pré-gerar o relatório e manter o cache atualizado.
    """
    logger.info("Iniciando geração de relatório agendada (proativo)...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=settings.REPORT_DAYS)
    
    try:
        await generator.generate_financial_report(
            start_date.isoformat(),
            end_date.isoformat(),
            refresh=True  # Força a atualização do cache
        )
        logger.info("Relatório agendado gerado com sucesso.")
    except Exception as e:
        logger.error(f"Erro na geração de relatório agendada: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa o agendador
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_report_generation, 
        'interval', 
        seconds=settings.CACHE_TTL,
        next_run_time=datetime.now() # Executa imediatamente na inicialização
    )
    scheduler.start()
    logger.info(f"🚀 Agendador APScheduler iniciado. Intervalo: {settings.CACHE_TTL}s")
    
    yield
    
    # Encerra o agendador ao desligar a aplicação
    scheduler.shutdown()
    logger.info("🛑 Agendador APScheduler encerrado.")

app = FastAPI(title="IXC Reporting API", lifespan=lifespan)

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

@app.post("/reports/financial")
async def generate_financial_report(request: ReportRequest):
    """
    Endpoint to generate financial reports from IXC data.
    """
    logger.info(f"API Request: Financial Report from {request.start_date} to {request.end_date}")
    try:
        # Generate report data
        report_data = await generator.generate_financial_report(
            request.start_date, 
            request.end_date,
            refresh=request.refresh
        )
        
        # Serialize all nested DataFrames (full_data, delinquency_summary, etc.)
        serialized_result = serialize_data(report_data)
        
        return serialized_result
    except Exception as e:
        logger.error(f"API Error during report generation: {e}")
        # Provide more context in the error detail
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
