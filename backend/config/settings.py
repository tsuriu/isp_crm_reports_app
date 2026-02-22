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
    
    # Caching
    CACHE_TTL = get_env_int("IXC_CACHE_TTL", 3600) # Default 1 hour
    
    # Reports
    REPORT_DAYS = get_env_int("IXC_REPORT_DAYS", 45)
    
    # Timeouts
    HTTP_TIMEOUT = get_env_int("IXC_HTTP_TIMEOUT", 120)
    
    # Persistent Caching (TinyDB)
    PERSISTENT_CACHE_TTL_HOURS = get_env_int("IXC_DATA_CACHE_TTL_HOURS", 24)
    PERSISTENT_CACHE_PATH = os.getenv("IXC_DATA_CACHE_PATH", "data/cache.json")
    
    # API Configuration
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    # App Settings
    APP_NAME = "IXC Reporting Platform"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

settings = Settings()
