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
    BOX_BORDER = colors.HexColor("#cbd5e1")   # Border Light

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

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=8
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

    script_box_style = ParagraphStyle(
        'ScriptBoxText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=15,
        textColor=PRIMARY
    )

    pro_tip_style = ParagraphStyle(
        'ProTipText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
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
    story.append(Paragraph("The DM Sales Script", title_style))
    story.append(Paragraph("5 Copy-Paste Messages That Turn \"How Much?\" Into Bank Transfers (Without Getting Ghosted)", subtitle_style))
    story.append(Paragraph("<b>By Itoya David</b> | Founder, SCALE GROUP Execution Series", author_style))
    story.append(HRFlowable(width="100%", thickness=2, color=SECONDARY, spaceBefore=0, spaceAfter=15))

    # ── INTRODUCTION ────────────────────────────────────────────────────────
    intro_text = (
        "<b>The Core Problem:</b> Most service providers, creators, and freelancers lose 80% of their sales "
        "in direct messages because of one critical error: <i>replying with a price tag before establishing value.</i> "
        "When you state your price upfront, the prospect compares your price to their bank balance rather than the problem you solve. "
        "Use the 5 battle-tested scripts below to control the conversation, qualify buyers, and close deals effortlessly."
    )
    story.append(Paragraph(intro_text, body_style))
    story.append(Spacer(1, 10))

    # Helper function for Script Cards
    def make_script_card(title_text, purpose_text, script_text, tip_text):
        content = [
            Paragraph(f"<b>{title_text}</b>", script_label_style),
            Paragraph(f"<b>Goal:</b> {purpose_text}", body_style),
            Spacer(1, 4),
            Table(
                [[Paragraph(f"<b>COPY & PASTE THIS SCRIPT:</b><br/><br/>\"{script_text}\"", script_box_style)]],
                colWidths=[520],
                style=TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
                    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                    ('PADDING', (0,0), (-1,-1), 10),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ])
            ),
            Spacer(1, 6),
            Table(
                [[Paragraph(f"💡 <b>EXECUTION TIP:</b> {tip_text}", pro_tip_style)]],
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
    story.append(make_script_card(
        "SCRIPT 1: The 1 Budget-Qualification Question",
        "Filters out zero-budget time-wasters within 3 messages without being rude.",
        "Glad you reached out, [Name]! Before we talk numbers, what is your primary revenue or growth goal for this month? (I want to make sure we're built for what you actually need right now).",
        "If they reply with a real goal, they have intent. If they refuse to answer or demand a price only, they are window shopping."
    ))

    # ── SCRIPT 2 ─────────────────────────────────────────────────────────────
    story.append(make_script_card(
        "SCRIPT 2: The 'How Much Is It?' Value-Anchor Response",
        "Deflects premature price requests and anchors expected ROI first.",
        "Our clients typically see a 3x to 5x return on their investment within the first 30 days. To give you the exact tier price: are you looking for complete done-for-you execution, or step-by-step implementation guidance?",
        "Notice you answered their question with a choice of options. This shifts their mindset from 'how expensive' to 'which option fits me best'."
    ))

    # ── SCRIPT 3 ─────────────────────────────────────────────────────────────
    story.append(make_script_card(
        "SCRIPT 3: The 'Too Expensive' Objection Neutralizer",
        "Turns price pushback into an immediate deposit or retainer confirmation.",
        "I completely understand, [Name]. Compared to doing nothing and continuing to lose clients every week, this is a fraction of the cost. If budget is tight right now, we can split this into 2 structured payments of [50% Amount] so you start generating revenue this week. Does that work for you?",
        "Offering a split-pay structure removes financial friction while keeping your pricing integrity intact."
    ))

    # ── SCRIPT 4 ─────────────────────────────────────────────────────────────
    story.append(make_script_card(
        "SCRIPT 4: The 48-Hour Re-Engagement Trigger",
        "Revives ghosted DM leads who stopped replying without sounding needy or desperate.",
        "Hey [Name], I'm finalizing our client schedule for this week and have 1 slot remaining. Should I hold it for you, or did you decide to pause this project for now?",
        "This uses gentle takeaway scarcity. People hate losing an opportunity they almost had."
    ))

    # ── SCRIPT 5 ─────────────────────────────────────────────────────────────
    story.append(make_script_card(
        "SCRIPT 5: The Bank Transfer Assumptive Close",
        "Transitions the conversation smoothly from agreement to payment.",
        "Awesome! You can complete your deposit here: [Your Paystack Link or Bank Details]. Once done, reply with your payment screenshot and I'll send over your instant onboarding access immediately.",
        "Give them a clear 2-step directive (Click link $\rightarrow$ Send screenshot). Clear instructions increase completion rates by 40%."
    ))

    # ── CALL TO ACTION BOX ──────────────────────────────────────────────────
    cta_table = Table(
        [[
            Paragraph(
                "🚀 <b>READY TO SCALE YOUR BUSINESS & CLIENT ACQUISITION?</b>",
                cta_heading_style
            ),
        ], [
            Paragraph(
                "Access the full <b>Scale Group Execution Vault (30 Playbooks)</b> at:<br/>"
                "<b>https://edgepack.thescaleconference.com</b><br/><br/>"
                "Get step-by-step systems on Sales, Meta Ads, SOPs, and Business Automation.",
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
    print(f"✅ PDF successfully generated at: {output_filename}")

if __name__ == "__main__":
    pdf_path = "/Users/daviditoya/Downloads/final_project/pdfs/the_dm_sales_script.pdf"
    create_pdf(pdf_path)
