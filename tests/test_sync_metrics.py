import pytest
from datetime import datetime, timedelta
import pandas as pd
import json

def calculate_metrics(bills_data, contracts_data):
    if not bills_data:
        return {
            "date": datetime.now().strftime("%d-%m-%Y"),
            "total_boletos": 0,
            "status": {
                "pagos": 0,
                "atrasados": 0,
                "bloqueados": 0,
                "possiveis_cancelamentos": 0,
                "desbloqueio_confianca": 0
            }
        }
        
    df_bills = pd.DataFrame(bills_data)
    df_contracts = pd.DataFrame(contracts_data)
    
    today = pd.Timestamp.now().normalize()
    df_bills['data_vencimento'] = pd.to_datetime(df_bills['data_vencimento'], errors='coerce')
    df_bills['days_late'] = (today - df_bills['data_vencimento']).dt.days
    
    pagos = len(df_bills[df_bills['status'] == 'R'])
    open_bills = df_bills[df_bills['status'] == 'A']
    
    atrasados = len(open_bills[(open_bills['days_late'] >= 1) & (open_bills['days_late'] <= 6)])
    bloqueados = len(open_bills[(open_bills['days_late'] >= 7) & (open_bills['days_late'] <= 10)])
    possiveis_cancelamentos = len(open_bills[open_bills['days_late'] >= 11])
    
    desbloqueio_confianca = 0
    if not df_contracts.empty and 'desbloqueio_confianca_ativo' in df_contracts.columns:
        desbloqueio_confianca = len(df_contracts[df_contracts['desbloqueio_confianca_ativo'] == 'S'])
        
    return {
        "date": datetime.now().strftime("%d-%m-%Y"),
        "total_boletos": len(df_bills),
        "status": {
            "pagos": pagos,
            "atrasados": atrasados,
            "bloqueados": bloqueados,
            "possiveis_cancelamentos": possiveis_cancelamentos,
            "desbloqueio_confianca": desbloqueio_confianca
        }
    }

def test_metrics_calculation():
    # Mock data
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    eight_days_ago_str = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d")
    twelve_days_ago_str = (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d")
    
    bills_data = [
        {"id": 1, "status": "R", "data_vencimento": today_str}, # Pago
        {"id": 2, "status": "A", "data_vencimento": yesterday_str}, # Atrasado (2 days)
        {"id": 3, "status": "A", "data_vencimento": eight_days_ago_str}, # Bloqueado (8 days)
        {"id": 4, "status": "A", "data_vencimento": twelve_days_ago_str}, # Possível Cancelamento (12 days)
        {"id": 5, "status": "A", "data_vencimento": today_str}, # Em dia (0 days late)
    ]
    
    contracts_data = [
        {"id": 101, "desbloqueio_confianca_ativo": "S"},
        {"id": 102, "desbloqueio_confianca_ativo": "N"},
    ]
    
    result = calculate_metrics(bills_data, contracts_data)
    
    assert result["total_boletos"] == 5
    assert result["status"]["pagos"] == 1
    assert result["status"]["atrasados"] == 1
    assert result["status"]["bloqueados"] == 1
    assert result["status"]["possiveis_cancelamentos"] == 1
    assert result["status"]["desbloqueio_confianca"] == 1
