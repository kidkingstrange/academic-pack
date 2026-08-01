import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

def create_pdf(output_filename):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#0f172a")      # Dark Slate/Navy
    SECONDARY = colors.HexColor("#4f46e5")    # Indigo Accent
    GOLD = colors.HexColor("#d97706")         # Gold/Amber
    TEXT_DARK = colors.HexColor("#1e293b")    # Slate Body Text
    BG_LIGHT = colors.HexColor("#f8fafc")     # Light Grey Card Background

    # Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=PRIMARY,
        alignment=TA_LEFT,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=SECONDARY,
        alignment=TA_LEFT,
        spaceAfter=15
    )

    author_style = ParagraphStyle(
        'CoverAuthor',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        alignment=TA_LEFT,
        spaceAfter=20
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=TEXT_DARK,
        alignment=TA_LEFT,
        spaceAfter=10
    )

    script_label_style = ParagraphStyle(
        'ScriptLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=SECONDARY,
        spaceBefore=4,
        spaceAfter=4
    )

    track_title_style = ParagraphStyle(
        'TrackTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=PRIMARY
    )

    script_box_style = ParagraphStyle(
        'ScriptBoxText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=14.5,
        textColor=PRIMARY
    )

    pro_tip_style = ParagraphStyle(
        'ProTipText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#854d0e")
    )

    cta_heading_style = ParagraphStyle(
        'CTAHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#854d0e"),
        alignment=TA_CENTER,
        spaceAfter=6
    )

    cta_body_style = ParagraphStyle(
        'CTABody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#713f12"),
        alignment=TA_CENTER
    )

    story = []

    # ── HEADER & TITLE SECTION ──────────────────────────────────────────────
    story.append(Paragraph("SCALE GROUP EXECUTION SERIES", ParagraphStyle('Tag', fontName='Helvetica-Bold', fontSize=9, textColor=GOLD, spaceAfter=4)))
    story.append(Paragraph("The DM Sales Script Guide", title_style))
    story.append(Paragraph("5 Copy-Paste Messages That Turn \"How Much?\" Into Bank Transfers (For Physical Products & High-Ticket Services)", subtitle_style))
    story.append(Paragraph("<b>By Itoya David</b> | Founder, SCALE GROUP Execution Series", author_style))
    story.append(HRFlowable(width="100%", thickness=2, color=SECONDARY, spaceBefore=0, spaceAfter=15))

    # ── INTRODUCTION ────────────────────────────────────────────────────────
    intro_text = (
        "<b>The Universal DM Problem:</b> Whether you sell <b>physical products</b> (fashion, gadgets, skincare, hair, food) "
        "or <b>high-ticket services</b> (freelancing, consulting, agency work), 80% of sales die in direct messages "
        "because of one mistake: <i>replying with a raw price tag in your very first message.</i><br/><br/>"
        "When you state a price upfront without context, buyers compare your price tag to their bank balance — rather than the value, quality, or solution you offer. "
        "Below are <b>dual-track scripts</b> customized for both <b>🛒 Physical Product Sellers</b> and <b>💼 High-Ticket Service Providers</b>."
    )
    story.append(Paragraph(intro_text, body_style))
    story.append(Spacer(1, 10))

    # Helper function for Dual-Track Script Cards
    def make_dual_script_card(step_num, title_text, purpose_text, prod_script, service_script, tip_text):
        content = [
            Paragraph(f"<b>SCRIPT {step_num}: {title_text}</b>", script_label_style),
            Paragraph(f"<b>Goal:</b> {purpose_text}", body_style),
            Spacer(1, 4),
            
            # Track A: Physical Products
            Table(
                [[
                    Paragraph("<b>🛒 TRACK A: Physical Products & Commodities</b> (Fashion, Gadgets, Skincare, Hair, Food)", track_title_style)
                ], [
                    Paragraph(f"\"{prod_script}\"", script_box_style)
                ]],
                colWidths=[520],
                style=TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
                    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                    ('PADDING', (0,0), (-1,-1), 8),
                ])
            ),
            Spacer(1, 6),

            # Track B: Services
            Table(
                [[
                    Paragraph("<b>💼 TRACK B: High-Ticket Services & Consulting</b> (Agencies, Freelancers, Services)", track_title_style)
                ], [
                    Paragraph(f"\"{service_script}\"", script_box_style)
                ]],
                colWidths=[520],
                style=TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
                    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                    ('PADDING', (0,0), (-1,-1), 8),
                ])
            ),
            Spacer(1, 6),

            # Tip Box
            Table(
                [[Paragraph(f"💡 <b>EXECUTION STRATEGY:</b> {tip_text}", pro_tip_style)]],
                colWidths=[520],
                style=TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fefce8")),
                    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#fde047")),
                    ('PADDING', (0,0), (-1,-1), 8),
                ])
            ),
            Spacer(1, 14)
        ]
        return KeepTogether(content)

    # ── SCRIPT 1 ─────────────────────────────────────────────────────────────
    story.append(make_dual_script_card(
        1, "The Quick Need-Qualification Opening",
        "Opens an engaging conversation and matches the exact right option before stating price.",
        "Hey [Name]! Glad you love this piece! Are you buying this for daily use or for a special occasion coming up (e.g. wedding/photoshoot/event)? I want to make sure I recommend the exact right size/bundle for you!",
        "Glad you reached out, [Name]! Before we discuss pricing, what is your primary revenue or growth goal for this month? (I want to ensure we're built for what you actually need right now).",
        "For products, asking about their event/usage establishes personal connection and lets you recommend matching accessories or bundles."
    ))

    # ── SCRIPT 2 ─────────────────────────────────────────────────────────────
    story.append(make_dual_script_card(
        2, "The Value-Anchor & Bundle Presentation",
        "Anchors extra value (free delivery, care kits, warranties, bonus options) before stating the cost.",
        "Our [Product Name] is made with premium [Material/Quality Grade] that lasts 3+ years without fading. The single piece is ₦15,000, but our 3-Piece Combo Bundle is ₦35,000 (saves ₦10,000 + includes Free Doorstep Delivery). Which option would you like me to prepare for you?",
        "Our clients typically see a 3x to 5x return on investment within 30 days. Are you looking for complete done-for-you execution, or step-by-step implementation guidance?",
        "For commodities, framing price as a choice between Single vs Discounted Bundle increases your Average Order Value (AOV) by 35%."
    ))

    # ── SCRIPT 3 ─────────────────────────────────────────────────────────────
    story.append(make_dual_script_card(
        3, "The 'Is That Last Price?' Objection Neutralizer",
        "Overcomes price resistance and haggling without cutting your margin.",
        "I completely understand! Because of our high quality [Material/Import Standard], we don't cut corners on production. However, if you order today before 4 PM, I can include a complimentary [Bonus Care Kit / Free Nationwide Delivery] to save you money!",
        "I completely understand, [Name]. Compared to doing nothing and continuing to lose revenue every week, this is a fraction of the cost. If budget is tight, we can split this into 2 structured payments so you start generating results this week.",
        "Never just discount cash off your price. Instead, add bonus perceived value (free gift, free shipping, or split payments) to protect your profit margin."
    ))

    # ── SCRIPT 4 ─────────────────────────────────────────────────────────────
    story.append(make_dual_script_card(
        4, "The Stock Availability Re-Engagement Trigger",
        "Revives buyers who asked for price and stopped replying (ghosted).",
        "Hey [Name]! Quick update — we have only 2 pieces left of the [Size/Color] in current stock before our next shipment next month. Would you like me to reserve one for you before it sells out?",
        "Hey [Name], I'm finalizing our client schedule for this week and have 1 slot remaining. Should I hold it for you, or did you decide to pause this project for now?",
        "Genuine stock scarcity (limited quantities/sizes) gives ghosted shoppers a logical reason to complete their purchase immediately."
    ))

    # ── SCRIPT 5 ─────────────────────────────────────────────────────────────
    story.append(make_dual_script_card(
        5, "The Assumptive Bank Transfer Close",
        "Transitions smoothly from customer agreement to payment & address confirmation.",
        "Awesome! Please drop your Full Name, Phone Number, and Delivery Address here. Once sent, tap here to complete transfer: [Paystack Link / Bank Details]. We ship out immediately upon receipt!",
        "Awesome! You can complete your deposit here: [Paystack Link / Bank Details]. Once done, reply with your payment screenshot and I'll send over your instant onboarding access immediately.",
        "Give a clear 2-step directive: (1) Send Delivery Details $\rightarrow$ (2) Complete Transfer. Structured instructions speed up checkout completion."
    ))

    # ── CALL TO ACTION BOX ──────────────────────────────────────────────────
    cta_table = Table(
        [[
            Paragraph(
                "🚀 <b>READY TO SCALE YOUR E-COMMERCE & BUSINESS SALES?</b>",
                cta_heading_style
            ),
        ], [
            Paragraph(
                "Access the full <b>Scale Group Execution Vault (30 Playbooks)</b> at:<br/>"
                "<b>https://edgepack.thescaleconference.com</b><br/><br/>"
                "Get step-by-step systems on Meta Ads, Sales Conversion, Business SOPs, and Cash Flow Automation.",
                cta_body_style
            )
        ]],
        colWidths=[520],
        style=TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fefce8")),
            ('BOX', (0,0), (-1,-1), 2, GOLD),
            ('PADDING', (0,0), (-1,-1), 16),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ])
    )
    story.append(Spacer(1, 10))
    story.append(cta_table)

    doc.build(story)
    print(f"✅ Dual-Track PDF successfully generated at: {output_filename}")

if __name__ == "__main__":
    pdf_path = "/Users/daviditoya/Downloads/final_project/pdfs/the_dm_sales_script.pdf"
    create_pdf(pdf_path)
