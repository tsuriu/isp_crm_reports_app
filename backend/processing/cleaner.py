import pandas as pd
from typing import List, Dict, Any
from loguru import logger

class DataCleaner:
    @staticmethod
    def clean_financial_data(data: List[Dict[str, Any]]) -> pd.DataFrame:
        logger.info(f"Cleaning financial data with {len(data)} records")
        if not data:
            logger.warning("No financial data to clean")
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        
        # Convert date columns to datetime
        date_cols = ['data_emissao', 'data_vencimento', 'pagamento_data']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                
        # Fill missing values
        if 'valor' in df.columns:
            df['valor'] = df['valor'].fillna(0.0)
            
        return df

    @staticmethod
    def clean_customer_data(data: List[Dict[str, Any]]) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        if 'data_cadastro' in df.columns:
            df['data_cadastro'] = pd.to_datetime(df['data_cadastro'])
            
        return df
