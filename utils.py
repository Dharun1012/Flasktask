from reportlab.lib.pagesizes import letter, A4 # type: ignore
from reportlab.lib import colors # type: ignore
from reportlab.lib.units import inch # type: ignore
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle # type: ignore
from io import BytesIO
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def generate_report_pdf(balance_data):
    """Generate PDF report of inventory balance"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=30,
        alignment=1  # Center
    )
    title = Paragraph("Inventory Balance Report", title_style)
    elements.append(title)
    
    # Date
    date_text = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    date_para = Paragraph(date_text, styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 0.3*inch))
    
    # Table data
    data = [['Product ID', 'Product Name', 'Location', 'Quantity']]
    for item in balance_data:
        data.append([
            item['product_id'],
            item['product_name'],
            item['location_name'],
            str(item['qty'])
        ])
    
    # Create table
    table = Table(data, colWidths=[1.5*inch, 2.5*inch, 2*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')])
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def send_low_stock_alert(product_name, product_id, location, qty, admin_email, config):
    """Send email alert for low stock"""
    try:
        msg = MIMEMultipart()
        msg['From'] = config['MAIL_USERNAME']
        msg['To'] = admin_email
        msg['Subject'] = f'⚠️ Low Stock Alert: {product_name}'
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #dc2626;">Low Stock Alert</h2>
            <p>The following product is running low on stock:</p>
            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; font-weight: bold;">Product:</td>
                    <td style="padding: 8px;">{product_name} ({product_id})</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold;">Location:</td>
                    <td style="padding: 8px;">{location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold;">Current Quantity:</td>
                    <td style="padding: 8px; color: #dc2626; font-weight: bold;">{qty}</td>
                </tr>
            </table>
            <p style="color: #666;">Please restock this item soon.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(config['MAIL_SERVER'], config['MAIL_PORT'])
        server.starttls()
        server.login(config['MAIL_USERNAME'], config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def calculate_balance():
    """Calculate current stock balance for all products in all locations"""
    from models import Product, Location, ProductMovement, db
    
    balance = {}
    movements = ProductMovement.query.all()
    
    for movement in movements:
        key_from = (movement.product_id, movement.from_location) if movement.from_location else None
        key_to = (movement.product_id, movement.to_location) if movement.to_location else None
        
        if key_from:
            if key_from not in balance:
                balance[key_from] = 0
            balance[key_from] -= movement.qty
        
        if key_to:
            if key_to not in balance:
                balance[key_to] = 0
            balance[key_to] += movement.qty
    
    # Format for display
    result = []
    for (product_id, location_id), qty in balance.items():
        if qty > 0:  # Only show positive balances
            product = Product.query.get(product_id)
            location = Location.query.get(location_id)
            if product and location:
                result.append({
                    'product_id': product_id,
                    'product_name': product.name,
                    'location_id': location_id,
                    'location_name': location.name,
                    'qty': qty
                })
    
    return sorted(result, key=lambda x: (x['product_name'], x['location_name']))