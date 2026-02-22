import pytest
import pandas as pd
from datetime import datetime, timedelta
from processing.metrics import MetricCalculator

@pytest.fixture
def sample_financial_data():
    today = pd.Timestamp.now().normalize()
    data = [
        # Paid on time
        {"id": 1, "id_cliente": 101, "valor": 100.0, "status": "R", "data_vencimento": today - timedelta(days=5), "pagamento_data": today - timedelta(days=5), "bairro": "Centro", "tipo_cliente": "Residencial", "trust_unlock_active": "N"},
        # Paid late (Recovery)
        {"id": 2, "id_cliente": 102, "valor": 200.0, "status": "R", "data_vencimento": today - timedelta(days=10), "pagamento_data": today - timedelta(days=2), "bairro": "Centro", "tipo_cliente": "Residencial", "trust_unlock_active": "N"},
        # Open - Near Suspension (Day 5)
        {"id": 3, "id_cliente": 103, "valor": 150.0, "status": "A", "data_vencimento": today - timedelta(days=5), "pagamento_data": None, "bairro": "Serraria", "tipo_cliente": "Comercial", "trust_unlock_active": "N"},
        # Open - Critical Migration (Day 7)
        {"id": 4, "id_cliente": 104, "valor": 300.0, "status": "A", "data_vencimento": today - timedelta(days=7), "pagamento_data": None, "bairro": "Centro", "tipo_cliente": "Residencial", "trust_unlock_active": "N"},
        # Open - Chronic (> 9 days)
        {"id": 5, "id_cliente": 105, "valor": 500.0, "status": "A", "data_vencimento": today - timedelta(days=15), "pagamento_data": None, "bairro": "Antares", "tipo_cliente": "Residencial", "trust_unlock_active": "N"},
        # Pending (Not overdue)
        {"id": 6, "id_cliente": 106, "valor": 120.0, "status": "A", "data_vencimento": today + timedelta(days=5), "pagamento_data": None, "bairro": "Antares", "tipo_cliente": "Residencial", "trust_unlock_active": "N"},
        # Cancelled
        {"id": 7, "id_cliente": 107, "valor": 50.0, "status": "C", "data_vencimento": today - timedelta(days=1), "pagamento_data": None, "bairro": "Centro", "tipo_cliente": "Residencial", "trust_unlock_active": "N"}
    ]
    return pd.DataFrame(data)

def test_calculate_financial_summary(sample_financial_data):
    summary = MetricCalculator.calculate_financial_summary(sample_financial_data)
    assert summary["total_received"] == 300.0 # 100 + 200
    assert summary["total_pending"] == 120.0  # Id 6
    assert summary["total_overdue"] == 950.0  # 150 + 300 + 500 (Id 3, 4, 5)
    assert summary["total_cancelled"] == 50.0 # Id 7

def test_calculate_delinquency_metrics(sample_financial_data):
    metrics = MetricCalculator.calculate_delinquency_metrics(sample_financial_data)
    assert metrics["total_overdue_count"] == 3
    assert metrics["recovery_rate"] > 0
    assert "Centro" in metrics["neighborhood_stats"]
    assert "Residencial" in metrics["tipo_cliente_stats"]
    assert metrics["aging"]["1-15 days"] == 950.0 # 150 + 300 + 500
    assert metrics["aging"]["16-30 days"] == 0.0
    assert metrics["aging"]["60+ days"] == 0.0

def test_calculate_suspension_metrics(sample_financial_data):
    metrics = MetricCalculator.calculate_suspension_metrics(sample_financial_data)
    funnel = metrics["funnel"]
    assert funnel["Near Suspension (1-6d)"] == 150.0      # Id 3
    assert funnel["Recently Suspended (7-9d)"] == 300.0  # Id 4
    assert funnel["Chronic Suspension (>9d)"] == 500.0    # Id 5
    
    # Critical Migration List should have Id 4 (Day 7)
    critical_ids = [r["id"] for r in metrics["critical_migration_list"]]
    assert 4 in critical_ids
    
    # Prevention List should have Id 3 (Day 5)
    prevention_ids = [r["id"] for r in metrics["prevention_list"]]
    assert 3 in prevention_ids
