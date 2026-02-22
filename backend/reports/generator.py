from datetime import datetime
from typing import Dict, Any
from ixc.client import IxcClient
from processing.cleaner import DataCleaner
from processing.metrics import MetricCalculator
from config.settings import settings
from loguru import logger

class ReportGenerator:
    def __init__(self):
        self.ixc_client = IxcClient(settings.IXC_CONFIG)
        self.cleaner = DataCleaner()
        self.metrics = MetricCalculator()
        logger.info("Initialized ReportGenerator")

    async def generate_financial_report(self, start_date: str, end_date: str, refresh: bool = False) -> Dict[str, Any]:
        """
        Coordinates the full report generation process.
        """
        logger.info(f"Generating full financial report (refresh={refresh}): {start_date} to {end_date}")
        
        try:
            # 1. Fetch & Enrich Data
            raw_data = await self.ixc_client.get_financial_data(start_date, end_date, refresh=refresh)
            
            # 2. Clean Data
            df = self.cleaner.clean_financial_data(raw_data)
            
            # 3. Calculate All Metrics
            summary_metrics = self.metrics.calculate_financial_summary(df)
            delinquency_metrics = self.metrics.calculate_delinquency_metrics(df)
            suspension_metrics = self.metrics.calculate_suspension_metrics(df)
            delinquency_summary = self.metrics.calculate_delinquency_summary(df)
            
            return {
                "metrics": summary_metrics,
                "delinquency": delinquency_metrics,
                "suspension": suspension_metrics,
                "delinquency_summary": delinquency_summary,
                "period": f"{start_date} to {end_date}",
                "raw_summary": df.head().to_dict() if not df.empty else {},
                "full_data": df,
                "fetched_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise
