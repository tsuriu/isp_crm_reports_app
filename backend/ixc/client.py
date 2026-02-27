import httpx
import time
import base64
import json
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta

from config.settings import settings

class IxcClient:
    """
    Enhanced IXC Client with support for pagination, rate limiting, 
    and advanced data enrichment.
    """
    
    # IXC Contract Status Mappings
    CONTRACT_STATUS_MAP = {
        'A': 'Active', 
        'B': 'Blocked', 
        'D': 'Disabled', 
        'F': 'Financial Delay', 
        'I': 'Inactive',
        'CA': 'Cancelled',
        'CM': 'Check Status'
    }

    def __init__(self, instance_config: Dict[str, Any]):
        self.config = instance_config
        self.erp = instance_config.get('erp', {})
        self.base_url = self.erp.get('base_url')
        self.auth = self.erp.get('auth', {})
        self.user_id = self.auth.get('user_id')
        self.token = self.auth.get('user_token')
        self.default_page_size = self.erp.get('request_param', {}).get('default_page_size', 100)
        
        self.last_request_time = 0
        self.min_delay = 0.1  # 100ms
        
        
        logger.info(f"Initialized IxcClient for {self.base_url}")

    def _get_headers(self) -> Dict[str, str]:
        """Generate authentication headers."""
        credentials = f"{self.user_id}:{self.token}"
        encoded_auth = base64.b64encode(credentials.encode()).decode()
        return {
            "ixcsoft": "listar",
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json"
        }

    async def _rate_limit(self):
        """Non-blocking rate limiting to avoid hitting API thresholds."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()

    async def _fetch_page(self, endpoint: str, query_params: Dict[str, Any], page: int) -> Dict[str, Any]:
        """Fetch a single page from the IXC API."""
        params = query_params.copy()
        params['page'] = str(page)
        if 'rp' not in params:
            params['rp'] = str(self.default_page_size)
            
        await self._rate_limit()
        url = f"{self.base_url}/webservice/v1/{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
                response = await client.post(url, headers=self._get_headers(), json=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching {endpoint} page {page}: {type(e).__name__}: {e}")
            return {}

    async def list_all(self, endpoint: str, query_params: Dict[str, Any], refresh: bool = False) -> List[Dict[str, Any]]:
        # Fetching always from API now, caching is handled by the sync process
        all_records = []
        page = 1
        total_records = None
        
        while True:
            data = await self._fetch_page(endpoint, query_params, page)
            records = data.get('registros', [])
            if not records:
                break
                
            all_records.extend(records)
            
            if total_records is None:
                total_records = int(data.get('total', 0))
                logger.debug(f"Expecting {total_records} records from {endpoint}")
            
            if len(all_records) >= total_records:
                break
            
            page += 1
                
        logger.success(f"Fetched {len(all_records)} total records from {endpoint}")
        return all_records

    # Data Retrieval Methods
    
    async def list_customers(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """List all customers (PF/PJ), excluding filial 3."""
        params = {
            "qtype": "cliente.id",
            "query": "0",
            "oper": ">",
            "sortname": "cliente.id",
            "sortorder": "asc",
            "grid_param": json.dumps([
                {"TB": "cliente.id", "OP": "!=", "P": "1"},
                {"TB": "cliente.filial_id", "OP": "!=", "P": "3"}
            ])
        }
        return await self.list_all("cliente", params, refresh=refresh)

    async def get_customers(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """Deprecated: Use list_customers instead."""
        return await self.list_customers(refresh=refresh)

    async def list_bills(self, start_date: Optional[str] = None, end_date: Optional[str] = None, refresh: bool = False) -> List[Dict[str, Any]]:
        """List open bills within a date range."""
        today = datetime.now()
        
        d_format = "%d/%m/%Y"
        end_str = end_date or today.strftime(d_format)
        if start_date:
            try:
                start_str = datetime.fromisoformat(start_date).strftime(d_format)
            except ValueError:
                start_str = start_date
        else:
            start_str = (today - timedelta(days=settings.REPORT_DAYS)).strftime(d_format)
        
        params = {
            "qtype": "fn_areceber.data_vencimento",
            "query": end_str,
            "oper": "<",
            "sortname": "fn_areceber.data_vencimento",
            "sortorder": "asc",
            "grid_param": json.dumps([
                {"TB": "fn_areceber.liberado", "OP": "=", "P": "S"},
                # {"TB": "fn_areceber.status", "OP": "=", "P": "A"},
                {"TB": "fn_areceber.filial_id", "OP": "!=", "P": "3"},
                {"TB": "fn_areceber.data_vencimento", "OP": ">", "P": start_str}
            ])
        }
        return await self.list_all("fn_areceber", params, refresh=refresh)

    async def list_contracts(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """List all active contracts."""
        params = {
            "qtype": "cliente_contrato.id",
            "query": "0",
            "oper": ">",
            "sortname": "cliente_contrato.id",
            "sortorder": "asc",
            "grid_param": json.dumps([
                {"TB": "cliente_contrato.id_filial", "OP": "!=", "P": "3"}
            ])
        }
        return await self.list_all("cliente_contrato", params, refresh=refresh)

    async def list_client_types(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """Retrieve client types."""
        params = {
            "qtype": "tipo_cliente.id",
            "query": "1",
            "oper": ">=",
            "sortname": "tipo_cliente.id",
            "sortorder": "desc"
        }
        return await self.list_all("tipo_cliente", params, refresh=refresh)

    async def list_blocked_contracts(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """List contracts that are currently blocked or in check-status."""
        params = {
            "qtype": "cliente_contrato.status", 
            "query": "A", 
            "oper": "=",
            "rp": "600", 
            "sortname": "cliente_contrato.id", 
            "sortorder": "asc",
            "grid_param": json.dumps([
                {"TB":"cliente_contrato.id_filial","OP":"!=","P":"3"},
                {"TB":"cliente_contrato.status_internet","OP":"!=","P":"A"}
            ])
        }
        return await self.list_all("cliente_contrato", params, refresh=refresh)

    # Core Reporting Method
    
    async def get_financial_data(self, start_date: str, end_date: str, include_customers: bool = True, refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieves financial data and optionally enriches it with customer/contract info.
        """
        logger.info(f"Generating financial report data ({start_date} to {end_date}) | refresh={refresh}")
        
        # Convert ISO to DD/MM/YYYY for IXC
        s_dt = datetime.fromisoformat(start_date).strftime("%d/%m/%Y")
        e_dt = datetime.fromisoformat(end_date).strftime("%d/%m/%Y")
        
        params = {
            "qtype": "fn_areceber.id",
            "query": "0",
            "oper": ">",
            "sortname": "fn_areceber.id",
            "sortorder": "desc",
            "grid_param": json.dumps([
                {"TB": "fn_areceber.liberado", "OP": "=", "P": "S"},
                {"TB": "fn_areceber.data_vencimento", "OP": "BE", "P": s_dt, "P2": e_dt},
                {"TB": "fn_areceber.filial_id", "OP": "!=", "P": "3"}
            ])
        }
        
        records = await self.list_all("fn_areceber", params, refresh=refresh)
        
        if include_customers and records:
            records = await self._enrich_records(records, refresh=refresh)
            
        return records

    async def _enrich_records(self, records: List[Dict[str, Any]], refresh: bool = False) -> List[Dict[str, Any]]:
        """Enriches financial records with customer, type, and contract mapping in parallel."""
        logger.info(f"Enriching records with related data... | refresh={refresh}")
        
        # Fetch related data in parallel
        tasks = [
            self.list_customers(refresh=refresh),
            self.list_client_types(refresh=refresh),
            self.list_contracts(refresh=refresh)
        ]
        customers, c_types, contracts = await asyncio.gather(*tasks)
        
        # Create lookup maps
        cust_map = {str(c['id']): c for c in customers}
        type_map = {str(t['id']): t.get('tipo_cliente', 'N/A') for t in c_types}
        cont_map = {str(ct['id_cliente']): ct for ct in contracts}
        
        for r in records:
            c_id = str(r.get('id_cliente'))
            cust = cust_map.get(c_id, {})
            
            # Customer Info (with fallbacks)
            r['cliente'] = cust.get('razao') or cust.get('fantasia') or 'N/A'
            r['bairro'] = cust.get('bairro', 'N/A')
            
            # Try multiple phone fields
            phone = cust.get('telefone_celular') or cust.get('telefone_comercial') or cust.get('telefone_residencial') or 'N/A'
            r['telefone'] = phone
            
            # Client Type Info
            t_id = str(cust.get('id_tipo_cliente', ''))
            r['tipo_cliente'] = type_map.get(t_id, 'N/A')
            
            # Contract Info
            cont = cont_map.get(c_id, {})
            r['contract_status'] = cont.get('status_internet', 'N/A')
            r['connection_status'] = self.CONTRACT_STATUS_MAP.get(r['contract_status'], r['contract_status'])
            
            # Trust Unlock Tracking
            r['trust_unlock_active'] = cont.get('desbloqueio_confianca_ativo', 'N')
            r['trust_unlock_enabled'] = cont.get('desbloqueio_confianca', 'P')
            
        return records
