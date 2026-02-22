# 📊 Plataforma de Relatórios IXC

Um painel profissional de relatórios financeiros para provedores de internet (ISP) que integra dados reais através da **API do IXC Provedor**.

## 🚀 Funcionalidades

- **Integração Real com IXC**: Utiliza o endpoint `fn_areceber` para monitoramento financeiro preciso.
- **Filtragem Avançada**: Filtros de data executados no lado do servidor usando o `grid_param` do IXC.
- **Controle Estratégico de Inadimplência**:
  - **Distribuição por Atraso (Aging)**: Visualização clara da dívida em intervalos de tempo.
  - **Monitoramento de Roll Rate**: Mede a progressão dos clientes para estágios críticos de dívida.
  - **Gestão Integrada de Suspensão**: Funil baseado na regra de 7 dias (1-6d, 7-9d, 9d+) monitorando o `status_internet`.
  - **Eficácia de Cobrança (CEI)**: Índice preciso calculado com base nas datas reais de pagamento.
- **Hub Operacional**: Listas priorizadas para equipes de cobrança:
  - **🔴 Migração Crítica**: Clientes que atingem exatamente 7 dias de atraso hoje.
  - **🟠 Prevenção**: Janela de aviso final para clientes com 5-6 dias de atraso.
- **Segmentação Comportamental**: Análise de inadimplência por **Bairro** e **Tipo de Cliente (PF/PJ)**.
- **Capacidades de Exportação**: Gere relatórios profissionais em formatos Markdown e HTML.

## 📉 Definições de Status de Inadimplência

Para facilitar a cobrança estratégica, o painel categoriza os clientes com base no atraso e status no IXC:

- **🟢 Em Dia**: Pagamentos realizados ou faturas ainda não vencidas.
- **🟡 Vencimento Padrão**: 1 a 6 dias de atraso. Esta é a janela de "lembrete".
- **🟠 Transição**: 7 a 9 dias de atraso. Janela crítica para gestão de suspensão.
- **🔴 Crônico**: Mais de 9 dias de atraso. Contas de alto risco que exigem cobrança intensiva.
- **🔵 Desbloqueio de Confiança**: Clientes com um "Desbloqueio de Confiança" ativo no IXC. Estes são acompanhados separadamente por representarem um evento operacional específico.

---

## 🛠️ Instalação

### 1. Pré-requisitos
- **Python 3.10+**
- **Token da API IXC** (com acesso aos webservices `fn_areceber`, `cliente`, `tipo_cliente` e `cliente_contrato`)

### 2. Configuração e Dependências
```bash
# Instalar dependências
pip install -r requirements.txt
```

### 3. Configurar Ambiente
Crie um arquivo `.env` na raiz do projeto:
```bash
cp .env.example .env
```

#### 🏢 Credenciais da API IXC
Preencha os detalhes do seu IXC no arquivo `.env`:
```env
IXC_BASE_URL=https://seu-dominio.com.br
IXC_USER_ID=seu_id_de_usuario
IXC_API_TOKEN=seu_token_aqui
```

---

## 🖥️ Uso

### ⚙️ Iniciar a Aplicação
Inicie o painel Streamlit:
```bash
streamlit run app.py
```

### 📈 Gerando Relatórios
1. **Configuração**: O painel carrega automaticamente os últimos 45 dias (configurável).
2. **Atualizar Dados**: Clique em "Gerar / Atualizar Dados" para forçar uma nova sincronização com a API.
3. **Analisar**: Revise os KPIs e gráficos calculados.
4. **Exportar**: Use os botões de download ao final da página para salvar seu relatório.

---

## 🐳 Implantação com Docker

A maneira mais rápida de rodar a plataforma é usando o **Docker Compose**.

### 1. Iniciar os Containers
Certifique-se de que seu arquivo `.env` está configurado corretamente e execute:
```bash
docker-compose up -d --build
```

### 2. Acessar os Painéis
- **Frontend (Streamlit)**: `http://localhost:8501`
- **Backend (FastAPI)**: `http://localhost:8000`

### 3. Parar e Limpar
```bash
docker-compose down
```

---

## 📂 Estrutura do Projeto

- `backend/ixc/`: Cliente da API e modelos de dados.
- `backend/processing/`: Limpeza de dados e cálculos de métricas (Pandas).
- `backend/reports/`: Orquestração da lógica de geração de relatórios.
- `frontend/`: Interface Streamlit e exportadores.

---

## 🔐 Segurança e Privacidade

- **Armazenamento de Credenciais**: Utiliza variáveis de ambiente (.env) para gestão segura de segredos.
- **Cache Local**: O cache persistente é armazenado em `data/cache.json` para reduzir a carga na API IXC.

---

## 📝 Licença
Este projeto é de uso interno. Consulte a documentação da IXC Soft para termos de serviço da API.
