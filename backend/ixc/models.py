from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class FinancialRecord(BaseModel):
    id: int
    data_emissao: datetime
    data_vencimento: datetime
    pagamento_data: Optional[datetime] = None
    valor: float
    status: str
    cliente: str

class Customer(BaseModel):
    id: int
    razao: str
    cnpj_cpf: str
    ativo: Optional[str] = "S"
    bairro: Optional[str] = None
    id_tipo_cliente: Optional[str] = None
    telefone_celular: Optional[str] = None
    data_cadastro: Optional[datetime] = None

class Contract(BaseModel):
    id: int
    id_cliente: int
    status_internet: str
    bloqueio_automatico: str # 'S' or 'N'
    conexao_status: Optional[str] = None # e.g., 'Ativo', 'Bloqueado'

class FinancialSummary(BaseModel):
    total_recebido: float
    total_pendente: float
    total_vencido: float
    data_inicio: datetime
    data_fim: datetime
