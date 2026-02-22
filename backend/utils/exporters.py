import markdown
from typing import Dict, Any

class ReportExporter:
    @staticmethod
    def to_markdown(report_data: Dict[str, Any]) -> str:
        md = f"# IXC Financial Report\n\n"
        md += f"**Period:** {report_data['period']}\n\n"
        
        md += "## Financial Summary\n"
        metrics = report_data['metrics']
        md += f"- **Total Received:** R$ {metrics['total_received']:,.2f}\n"
        md += f"- **Total Pending:** R$ {metrics['total_pending']:,.2f}\n"
        md += f"- **Total Overdue:** R$ {metrics['total_overdue']:,.2f}\n"
        md += f"- **Total Cancelled:** R$ {metrics['total_cancelled']:,.2f}\n\n"

        md += "## Strategic Delinquency Control\n"
        delinquency = report_data.get('delinquency', {})
        md += f"- **Avg Overdue Ticket:** R$ {delinquency.get('avg_overdue_ticket', 0):,.2f}\n"
        md += f"- **Roll Rate (1-30 to 31+):** {delinquency.get('roll_rate', 0):,.2f}%\n"
        md += f"- **Collection Effectiveness (CEI):** {delinquency.get('cei', 0):,.2f}%\n"
        md += f"- **Recovery Rate (Late Payments):** {delinquency.get('recovery_rate', 0):,.2f}%\n\n"

        md += "### Aging Analysis\n"
        aging = delinquency.get('aging', {})
        md += "| Stage | Amount |\n| --- | --- |\n"
        for stage, amount in aging.items():
            md += f"| {stage} | R$ {amount:,.2f} |\n"
        md += "\n"

        md += "### Delinquency by Customer Type\n"
        tipo_stats = delinquency.get('tipo_cliente_stats', {})
        md += "| Type ID | Overdue Amount |\n| --- | --- |\n"
        for tid, amount in tipo_stats.items():
            md += f"| {tid} | R$ {amount:,.2f} |\n"
        md += "\n"
        
        md += "## Integrated Suspension Management\n"
        suspension = report_data.get('suspension', {})
        md += f"- **Conversion Rate (Lockout):** {suspension.get('conversion_rate', 0):,.2f}%\n"
        md += f"- **Self-Healing Rate:** {suspension.get('self_healing_rate', 0):,.2f}%\n"
        md += f"- **Avg Recovery Time:** {suspension.get('avg_recovery_time', 0):,.1f} days\n\n"

        md += "### Suspension Funnel\n"
        funnel = suspension.get('funnel', {})
        md += "| Stage | Amount |\n| --- | --- |\n"
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
