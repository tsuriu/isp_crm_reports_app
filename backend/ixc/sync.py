import asyncio
from typing import List, Dict, Any
from loguru import logger
from ixc.client import IxcClient
from config.settings import settings
from utils.storage import get_storage

async def sync_customers():
    """Syncs customers from IXC to TinyDB."""
    logger.info("Starting customer sync...")
    client = IxcClient(settings.IXC_CONFIG)
    try:
        customers = await client.list_customers(refresh=True)
        storage = get_storage(settings.STORAGE_PATH_CLIENTES)
        storage.save_all(customers)
        logger.success(f"Synced {len(customers)} customers.")
    except Exception as e:
        logger.error(f"Error syncing customers: {e}")

async def sync_contracts_and_bills():
    """Syncs contracts and bills from IXC to TinyDB."""
    logger.info("Starting contracts and bills sync...")
    client = IxcClient(settings.IXC_CONFIG)
    try:
        # Fetch data in parallel
        tasks = [
            client.list_contracts(refresh=True),
            client.list_bills(refresh=True)
        ]
        contracts, bills = await asyncio.gather(*tasks)
        
        # Save contracts
        contracts_storage = get_storage(settings.STORAGE_PATH_CONTRATOS)
        contracts_storage.save_all(contracts)
        
        # Save bills
        bills_storage = get_storage(settings.STORAGE_PATH_BOLETOS)
        bills_storage.save_all(bills)
        
        logger.success(f"Synced {len(contracts)} contracts and {len(bills)} bills.")
    except Exception as e:
        logger.error(f"Error syncing contracts and bills: {e}")
