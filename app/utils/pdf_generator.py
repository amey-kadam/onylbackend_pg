import os
import uuid
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from dateutil.relativedelta import relativedelta

def generate_rent_agreement(
    tenant_name: str,
    tenant_address: str,
    owner_name: str,
    owner_address: str,
    pg_name: str,
    pg_address: str,
    room_number: str,
    bed_number: str,
    start_date: date,
    monthly_rent: float,
    security_deposit: float,
    notice_period: int,
    agreement_period: int,
    city: str = "Pune",  # Defaulting to Pune or we can extract from address
) -> str:
    """
    Generates a Leave and License Agreement PDF and returns the saved file path.
    """
    if not os.path.exists("uploads/agreements"):
        os.makedirs("uploads/agreements")

    filename = f"agreement_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join("uploads/agreements", filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=14,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontSize=11,
        spaceAfter=12,
        leading=16,
        fontName='Helvetica'
    )

    list_style = ParagraphStyle(
        'ListStyle',
        parent=normal_style,
        leftIndent=20,
        firstLineIndent=-20,
        spaceAfter=10
    )

    bold_style = ParagraphStyle(
        'BoldStyle',
        parent=normal_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # Format Dates
    agreement_date_str = datetime.now().strftime("%d %B %Y")
    start_date_str = start_date.strftime("%d %B %Y")
    
    end_date = start_date + relativedelta(months=agreement_period)
    end_date_str = end_date.strftime("%d %B %Y")

    # Title
    story.append(Paragraph("RENT / LEAVE AND LICENSE AGREEMENT", title_style))

    # Introduction
    intro_text = f"This Agreement is made and executed on this {agreement_date_str} at {city}."
    story.append(Paragraph(intro_text, normal_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("BETWEEN", bold_style))
    
    owner_text = f"<b>{owner_name}</b>, residing at {owner_address or '___________________'}, hereinafter referred to as the \"Licensor/Owner\" (which expression shall, unless repugnant to the context or meaning thereof, be deemed to include his/her heirs, successors, legal representatives, and assigns) of the ONE PART;"
    story.append(Paragraph(owner_text, normal_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("AND", bold_style))

    tenant_text = f"<b>{tenant_name}</b>, having permanent address at {tenant_address or '___________________'} and holding valid identity proof, hereinafter referred to as the \"Licensee/Tenant\" (which expression shall, unless repugnant to the context or meaning thereof, be deemed to include his/her heirs, successors, and permitted assigns) of the OTHER PART."
    story.append(Paragraph(tenant_text, normal_style))
    story.append(Spacer(1, 10))

    whereas_text = f"WHEREAS the Licensor is the lawful owner of the premises situated at <b>{pg_address or '___________________'}</b> and has agreed to grant the Licensee the right to use and occupy a portion of the said premises on leave and license basis."
    story.append(Paragraph(whereas_text, normal_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("NOW THIS AGREEMENT WITNESSETH AS UNDER:", bold_style))

    # Terms
    terms = [
        f"The Licensor hereby grants to the Licensee the license to use and occupy the premises described as {pg_name}, Room No. {room_number or '___'}, Bed No. {bed_number or '___'}, for residential purposes only.",
        f"The term of this Agreement shall be for a period commencing from {start_date_str} and ending on {end_date_str}, unless terminated earlier in accordance with the terms contained herein.",
        f"The Licensee shall pay to the Licensor a monthly license fee/rent of ₹{monthly_rent} payable on or before 5th of each month. The Licensee has paid a refundable security deposit of ₹{security_deposit}.",
        "The Licensee agrees to use the premises solely for residential purposes and shall not carry on any commercial or unlawful activities therein.",
        "The Licensee shall maintain the premises in good condition and shall not cause any damage to the property. In case of any damage, the cost of repair shall be borne by the Licensee.",
        "The Licensee shall comply with all rules and regulations as prescribed by the Licensor from time to time regarding use of the premises, discipline, and maintenance.",
        "The Licensee shall not sublet, assign, or transfer the premises or any part thereof to any third party without the prior written consent of the Licensor.",
        f"Either party may terminate this Agreement by giving {notice_period} days' prior written notice to the other party.",
        "Upon termination or expiry of this Agreement, the Licensee shall vacate the premises and hand over peaceful possession to the Licensor. The security deposit shall be refunded after adjusting any dues or damages.",
        "In case of default in payment of rent or breach of any terms of this Agreement, the Licensor shall have the right to terminate this Agreement and take possession of the premises.",
        "The Licensee agrees to provide all necessary documents for police verification and comply with local laws and regulations.",
        f"This Agreement shall be governed by and construed in accordance with the laws of India, and the courts at {city} shall have exclusive jurisdiction."
    ]

    for idx, term in enumerate(terms, start=1):
        story.append(Paragraph(f"{idx}. {term}", list_style))

    story.append(Spacer(1, 20))
    
    witness_text = "IN WITNESS WHEREOF, the parties hereto have set their hands on the day, month, and year first above written."
    story.append(Paragraph(witness_text, normal_style))

    story.append(Spacer(1, 40))

    signature_style = ParagraphStyle(
        'SignatureStyle',
        parent=normal_style,
        leading=30
    )

    story.append(Paragraph("Licensor/Owner Signature: ______________________", signature_style))
    story.append(Paragraph("Licensee/Tenant Signature: ______________________", signature_style))

    doc.build(story)
    
    return f"/{filepath.replace(os.sep, '/')}"
