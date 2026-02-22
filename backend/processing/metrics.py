import pandas as pd
from typing import Dict, Any
from loguru import logger

class MetricCalculator:
    @staticmethod
    def calculate_financial_summary(df: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Calculating financial summary metrics")
        if df.empty:
            logger.warning("Empty DataFrame provided for metrics calculation")
            return {
                "total_received": 0.0,
                "total_pending": 0.0,
                "total_overdue": 0.0,
                "total_cancelled": 0.0
            }
            
        # IXC status codes: R = Recebido (Paid), A = Aberto (Open), C = Cancelado
        # Overdue is 'A' where data_vencimento < today
        today = pd.Timestamp.now().normalize()
        
        # Ensure 'valor' is numeric
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
        
        summary = {
            "total_received": df[df['status'] == 'R']['valor'].sum(),
            "total_pending": df[(df['status'] == 'A') & (df['data_vencimento'] >= today)]['valor'].sum(),
            "total_overdue": df[(df['status'] == 'A') & (df['data_vencimento'] < today)]['valor'].sum(),
            "total_cancelled": df[df['status'] == 'C']['valor'].sum()
        }
        return summary

    @staticmethod
    def calculate_delinquency_metrics(df: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Calculating advanced delinquency metrics")
        if df.empty:
            return {}

        today = pd.Timestamp.now().normalize()
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
        df['data_vencimento'] = pd.to_datetime(df['data_vencimento'], errors='coerce')
        
        # 1. Aging Analysis
        overdue_df = df[(df['status'].isin(['A'])) & (df['data_vencimento'] < today)].copy()
        overdue_df['days_overdue'] = (today - overdue_df['data_vencimento']).dt.days
        
        aging = {
            "1-15 dias": overdue_df[overdue_df['days_overdue'] <= 15]['valor'].sum(),
            "16-30 dias": overdue_df[(overdue_df['days_overdue'] > 15) & (overdue_df['days_overdue'] <= 30)]['valor'].sum(),
            "31-60 dias": overdue_df[(overdue_df['days_overdue'] > 30) & (overdue_df['days_overdue'] <= 60)]['valor'].sum(),
            "60+ dias": overdue_df[overdue_df['days_overdue'] > 60]['valor'].sum()
        }

        # 2. Average Overdue Ticket
        avg_overdue_ticket = overdue_df['valor'].mean() if not overdue_df.empty else 0.0

        # 3. Roll Rate (Proxy: clients moving from 1-30 to 31+ days)
        initial_stage_count = overdue_df[overdue_df['days_overdue'] <= 30]['id_cliente'].nunique()
        critical_stage_count = overdue_df[overdue_df['days_overdue'] > 30]['id_cliente'].nunique()
        roll_rate = (critical_stage_count / initial_stage_count * 100) if initial_stage_count > 0 else 0.0

        # 4. CEI (Collection Effectiveness Index)
        # Refined: (Amounts paid / Total due in period)
        total_due_in_period = df[(df['status'] != 'C')]['valor'].sum()
        total_paid_in_period = df[df['status'] == 'R']['valor'].sum()
        cei = (total_paid_in_period / total_due_in_period * 100) if total_due_in_period > 0 else 0.0

        # 4b. Recovery Rate (Paid after due date)
        paid_after_due = df[(df['status'] == 'R') & (df['pagamento_data'] > df['data_vencimento'])]['valor'].sum()
        recovery_rate = (paid_after_due / total_due_in_period * 100) if total_due_in_period > 0 else 0.0

        # 5. Neighborhood Segmentation (Top 10)
        neighborhood_stats = overdue_df.groupby('bairro')['valor'].sum().sort_values(ascending=False).head(10).to_dict()

        # 6. Customer Type Segmentation
        tipo_cliente_stats = overdue_df.groupby('tipo_cliente')['valor'].sum().sort_values(ascending=False).to_dict()

        return {
            "aging": aging,
            "avg_overdue_ticket": avg_overdue_ticket,
            "roll_rate": roll_rate,
            "cei": cei,
            "recovery_rate": recovery_rate,
            "neighborhood_stats": neighborhood_stats,
            "tipo_cliente_stats": tipo_cliente_stats,
            "total_overdue_count": len(overdue_df)
        }

    @staticmethod
    def calculate_suspension_metrics(df: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Calculating suspension management metrics")
        if df.empty:
            return {}

        today = pd.Timestamp.now().normalize()
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
        df['data_vencimento'] = pd.to_datetime(df['data_vencimento'], errors='coerce')
        
        # Only active/open debts matter for the funnel
        open_debts = df[df['status'] == 'A'].copy()
        open_debts['days_late'] = (today - open_debts['data_vencimento']).dt.days

        # 1. Suspension Funnel
        funnel = {
            "Próximo à Suspensão (1-6d)": open_debts[(open_debts['days_late'] >= 1) & (open_debts['days_late'] <= 6)]['valor'].sum(),
            "Suspenso Recentemente (7-9d)": open_debts[(open_debts['days_late'] >= 7) & (open_debts['days_late'] <= 9)]['valor'].sum(),
            "Suspensão Crônica (>9d)": open_debts[open_debts['days_late'] > 9]['valor'].sum()
        }

        # 2. Key Rates
        near_count = open_debts[(open_debts['days_late'] >= 1) & (open_debts['days_late'] <= 6)]['id_cliente'].nunique()
        suspended_count = open_debts[(open_debts['days_late'] >= 7) & (open_debts['days_late'] <= 9)]['id_cliente'].nunique()
        
        conversion_rate = (suspended_count / (near_count + suspended_count) * 100) if (near_count + suspended_count) > 0 else 0.0
        
        # Self-Healing Rate (Paid before lockout) - Requires historical perspective or current month proxy
        # We'll proxy it as: (Paid with 1-6d delay) / (Paid 1-6d + Still open 1-6d)
        paid_early = df[(df['status'] == 'R') & 
                        ((df['pagamento_data'] - df['data_vencimento']).dt.days <= 6) &
                        ((df['pagamento_data'] - df['data_vencimento']).dt.days >= 0)]['id_cliente'].nunique()
        self_healing_rate = (paid_early / (paid_early + near_count) * 100) if (paid_early + near_count) > 0 else 0.0

        # 3. Operational Lists
        # 🔴 Critical Migration List (Day 7)
        critical_list = open_debts[open_debts['days_late'] == 7].sort_values('data_vencimento').head(50).to_dict('records')
        
        # 🟠 Prevention List (Days 5-6)
        prevention_list = open_debts[(open_debts['days_late'] >= 5) & (open_debts['days_late'] <= 6)].sort_values('data_vencimento').head(50).to_dict('records')

        # 3. Trust Unlock Metrics
        active_trust_unlocks = df[df['trust_unlock_active'] == 'S']['id_cliente'].nunique()

        return {
            "funnel": funnel,
            "conversion_rate": conversion_rate,
            "self_healing_rate": self_healing_rate,
            "active_trust_unlocks": active_trust_unlocks,
            "critical_migration_list": critical_list,
            "prevention_list": prevention_list,
            "avg_recovery_time": (df[df['status'] == 'R']['pagamento_data'] - df[df['status'] == 'R']['data_vencimento']).dt.days.mean()
        }

    @staticmethod
    def calculate_delinquency_summary(df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates a summary DataFrame grouped by Due Date for the Delinquency Dashboard.
        Columns: Due Date, Total Customers, Total Overdue, Transition (7-9d), Chronic (9d+)
        """
        logger.info("Calculating delinquency summary by due date")
        if df.empty:
            return pd.DataFrame()

        today = pd.Timestamp.now().normalize()
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
        df['data_vencimento'] = pd.to_datetime(df['data_vencimento'], errors='coerce')
        
        # Calculate days late for all records to be safe, though mostly relevant for Open ones
        # For counting "Total Customers" per due date, we count all Unique IDs associated with that date
        
        # Group by Date
        grouped = []
        unique_dates = df['data_vencimento'].dropna().unique()
        
        for date in unique_dates:
            d_df = df[df['data_vencimento'] == date].copy()
            
            # Total Customers: All unique clients with a bill on this date
            total_customers = d_df['id_cliente'].nunique()
            
            # Calculate segments for the new chart (Mutually Exclusive)
            # 1. Trust Unlock (Priority)
            d_df['days_late'] = (today - date).days
            trust_ids = d_df[d_df['trust_unlock_active'] == 'S']['id_cliente'].unique()
            trust_unlock_count = len(trust_ids)
            
            # 2. Others (excluding Trust Unlocks)
            other_df = d_df[~d_df['id_cliente'].isin(trust_ids)].copy()
            open_other_df = other_df[other_df['status'] == 'A']
            
            chronic_exclusive = open_other_df[open_other_df['days_late'] > 9]['id_cliente'].nunique()
            transition_exclusive = open_other_df[(open_other_df['days_late'] >= 7) & (open_other_df['days_late'] <= 9)]['id_cliente'].nunique()
            overdue_exclusive = open_other_df[(open_other_df['days_late'] >= 1) & (open_other_df['days_late'] <= 6)]['id_cliente'].nunique()
            
            # 3. Current (Total - Sum of late/trust)
            current_count = total_customers - (trust_unlock_count + chronic_exclusive + transition_exclusive + overdue_exclusive)
            
            # Keep original counts for backward compatibility/table view
            open_all_df = d_df[d_df['status'] == 'A']
            total_overdue = open_all_df[open_all_df['days_late'] >= 1]['id_cliente'].nunique()
            chronic_all = open_all_df[open_all_df['days_late'] > 9]['id_cliente'].nunique()
            transition_all = open_all_df[(open_all_df['days_late'] >= 7) & (open_all_df['days_late'] <= 9)]['id_cliente'].nunique()
            grouped.append({
                "Vencimento": date.strftime('%Y-%m-%d'),
                "Total de Clientes": total_customers,
                "Em Dia": current_count,
                "Vencimento Padrão": overdue_exclusive,
                "Transição": transition_exclusive,
                "Crônico": chronic_exclusive,
                "Desbloqueio de Confiança": trust_unlock_count
            })
            
        summary_df = pd.DataFrame(grouped).sort_values("Vencimento", ascending=False)
        return summary_df
