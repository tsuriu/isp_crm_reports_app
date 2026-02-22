import markdown
from typing import Dict, Any

class ReportExporter:
    @staticmethod
    def to_markdown(report_data: Dict[str, Any]) -> str:
        md = f"# Relatório Financeiro IXC\n\n"
        md += f"**Período:** {report_data['period']}\n\n"
        
        md += "## Resumo Financeiro\n"
        metrics = report_data['metrics']
        md += f"- **Total Recebido:** R$ {metrics['total_received']:,.2f}\n"
        md += f"- **Total Pendente:** R$ {metrics['total_pending']:,.2f}\n"
        md += f"- **Total Vencido:** R$ {metrics['total_overdue']:,.2f}\n"
        md += f"- **Total Cancelado:** R$ {metrics['total_cancelled']:,.2f}\n\n"

        md += "## Controle Estratégico de Inadimplência\n"
        delinquency = report_data.get('delinquency', {})
        md += f"- **Ticket Médio Vencido:** R$ {delinquency.get('avg_overdue_ticket', 0):,.2f}\n"
        md += f"- **Taxa de Rolagem (1-30 para 31+):** {delinquency.get('roll_rate', 0):,.2f}%\n"
        md += f"- **Eficácia de Cobrança (CEI):** {delinquency.get('cei', 0):,.2f}%\n"
        md += f"- **Taxa de Recuperação (Pagamentos em Atraso):** {delinquency.get('recovery_rate', 0):,.2f}%\n\n"

        md += "### Análise de Aging (Vencimento)\n"
        aging = delinquency.get('aging', {})
        md += "| Faixa | Valor |\n| --- | --- |\n"
        for stage, amount in aging.items():
            md += f"| {stage} | R$ {amount:,.2f} |\n"
        md += "\n"

        md += "### Inadimplência por Tipo de Cliente\n"
        tipo_stats = delinquency.get('tipo_cliente_stats', {})
        md += "| Tipo | Valor Vencido |\n| --- | --- |\n"
        for tid, amount in tipo_stats.items():
            md += f"| {tid} | R$ {amount:,.2f} |\n"
        md += "\n"
        
        md += "## Gestão Integrada de Suspensão\n"
        suspension = report_data.get('suspension', {})
        md += f"- **Taxa de Conversão (Bloqueio):** {suspension.get('conversion_rate', 0):,.2f}%\n"
        md += f"- **Taxa de Autocura (Self-Healing):** {suspension.get('self_healing_rate', 0):,.2f}%\n"
        md += f"- **Tempo Médio de Recuperação:** {suspension.get('avg_recovery_time', 0):,.1f} dias\n\n"

        md += "### Funil de Suspensão\n"
        funnel = suspension.get('funnel', {})
        md += "| Faixa | Valor |\n| --- | --- |\n"
        for stage, amount in funnel.items():
            md += f"| {stage} | R$ {amount:,.2f} |\n"
        md += "\n"

        return md

    @staticmethod
    def to_html(report_data: Dict[str, Any]) -> str:
        md_content = ReportExporter.to_markdown(report_data)
        return markdown.markdown(md_content)
        
    @staticmethod
    def to_pdf(report_data: Dict[str, Any], output_path: str):
        # Requires pdfkit and wkhtmltopdf
        # This is a placeholder since wkhtmltopdf might not be installed
        html_content = ReportExporter.to_html(report_data)
        # pdfkit.from_string(html_content, output_path)
        pass
