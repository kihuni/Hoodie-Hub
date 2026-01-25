from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

class OrderReceiptGenerator:
    def __init__(self, order):
        self.order = order
        
    def generate(self):
        """Generate PDF receipt for order"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#FF6B35'),
            alignment=1
        )
        elements.append(Paragraph("HOODIEHUB ORDER RECEIPT", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Order details
        order_data = [
            ['Order ID:', str(self.order.id)[:8]],
            ['Customer:', self.order.customer_name],
            ['Phone:', self.order.phone_number],
            ['Delivery Location:', self.order.delivery_location],
            ['Order Date:', self.order.created_at.strftime('%Y-%m-%d %H:%M')],
            ['M-Pesa Receipt:', self.order.mpesa_receipt_number or 'N/A'],
            ['Status:', self.order.status],
        ]
        
        order_table = Table(order_data, colWidths=[2*inch, 4*inch])
        order_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FFE5D9')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        elements.append(order_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Items header
        elements.append(Paragraph("Order Items", styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Items table
        items_data = [['Item', 'Size', 'Qty', 'Price', 'Subtotal']]
        
        for item in self.order.items.all():
            items_data.append([
                item.hoodie_name,
                item.size,
                str(item.quantity),
                f'KES {item.price:,.2f}',
                f'KES {item.get_subtotal():,.2f}'
            ])
        
        # Total row
        items_data.append(['', '', '', 'TOTAL:', f'KES {self.order.total_amount:,.2f}'])
        
        items_table = Table(items_data, colWidths=[2.5*inch, 0.7*inch, 0.7*inch, 1*inch, 1.2*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF6B35')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -2), 1, colors.grey),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Footer
        footer_text = "Thank you for shopping with HoodieHub! 🎉"
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,
            textColor=colors.grey
        )
        elements.append(Paragraph(footer_text, footer_style))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer