import os
from dotenv import load_dotenv

load_dotenv()

def get_env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default

class Settings:
    # IXC API Configuration
    IXC_CONFIG = {
        'erp': {
            'base_url': os.getenv("IXC_BASE_URL", "https://ixc.squidtelecom.com.br"),
            'auth': {
                'user_id': os.getenv("IXC_USER_ID", "3"),
                'user_token': os.getenv("IXC_API_TOKEN", "")
            },
            'request_param': {
                'default_page_size': get_env_int("IXC_PAGE_SIZE", 100)
            }
        }
    }
    
    # Sincronização e Métricas
    SYNC_INTERVAL_MINUTES = get_env_int("IXC_SYNC_INTERVAL_MINUTES", 30)
    SYNC_CUSTOMERS_HOUR = get_env_int("IXC_SYNC_CUSTOMERS_HOUR", 7)
    REPORT_DAYS = get_env_int("IXC_REPORT_DAYS", 45)
    
    # Timeouts
    HTTP_TIMEOUT = get_env_int("IXC_HTTP_TIMEOUT", 120)
    
    # Storage Paths (TinyDB)
    
    STORAGE_PATH_CLIENTES = os.getenv("IXC_STORAGE_PATH_CLIENTES", "data/clientes.json")
    STORAGE_PATH_CONTRATOS = os.getenv("IXC_STORAGE_PATH_CONTRATOS", "data/contratos.json")
    STORAGE_PATH_BOLETOS = os.getenv("IXC_STORAGE_PATH_BOLETOS", "data/boletos.json")
    
    # API Configuration
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    # App Settings
    APP_NAME = "IXC Reporting Platform"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

settings = Settings()
