"""
Affiliate Resource Package Generator Script
Generates professional, styled PDFs and packages product covers into affiliate_resources/
"""
import os
import sys
import shutil
from pathlib import Path
from PIL import Image

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "affiliate_resources"
COVERS_DIR = OUTPUT_DIR / "3. PRODUCT COVERS"
DOCS_MD_DIR = OUTPUT_DIR / "docs_markdown"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(COVERS_DIR, exist_ok=True)
os.makedirs(DOCS_MD_DIR, exist_ok=True)

# Import ReportLab modules
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.pdfgen import canvas

# Modern Palette
INK = colors.HexColor('#0c0e12')
PRIMARY_GOLD = colors.HexColor('#c9973a')
LIGHT_GOLD = colors.HexColor('#a87830')
DARK_BG = colors.HexColor('#1a1d24')
TEXT_DARK = colors.HexColor('#1f2937')
TEXT_MUTED = colors.HexColor('#4b5563')
BG_LIGHT = colors.HexColor('#f8fafc')
BORDER_COLOR = colors.HexColor('#e2e8f0')
ACCENT_GREEN = colors.HexColor('#15803d')

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(TEXT_MUTED)
        
        # Header (Top line)
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 36, 8.5 * 72 - 54, 11 * 72 - 36)
        self.drawString(54, 11 * 72 - 30, "The Academic Comeback Package — Official Affiliate Partner Resources")
        
        # Footer
        self.line(54, 45, 8.5 * 72 - 54, 45)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 30, page_text)
        self.drawString(54, 30, "Confidential — Partner Resource File")
        self.restoreState()

def create_doc_styles():
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=INK,
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=PRIMARY_GOLD,
        spaceAfter=20
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=INK,
        spaceBefore=16,
        spaceAfter=8
    )
    
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=LIGHT_GOLD,
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=TEXT_DARK,
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    quote_box = ParagraphStyle(
        'QuoteBoxText',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=14,
        textColor=INK
    )

    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'h1': h1_style,
        'h2': h2_style,
        'body': body_style,
        'bullet': bullet_style,
        'quote': quote_box
    }

def build_pdf(filename, title, subtitle, content_blocks):
    pdf_path = OUTPUT_DIR / filename
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = create_doc_styles()
    story = []
    
    # Header Title Banner
    story.append(Paragraph(title.upper(), styles['title']))
    story.append(Paragraph(subtitle, styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_GOLD, spaceBefore=0, spaceAfter=15))
    
    for block_type, data in content_blocks:
        if block_type == 'h1':
            story.append(Paragraph(data, styles['h1']))
        elif block_type == 'h2':
            story.append(Paragraph(data, styles['h2']))
        elif block_type == 'body':
            story.append(Paragraph(data, styles['body']))
        elif block_type == 'bullet':
            story.append(Paragraph(f"• {data}", styles['bullet']))
        elif block_type == 'quote':
            p = Paragraph(data, styles['quote'])
            t = Table([[p]], colWidths=[500])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
                ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
                ('LINELEFT', (0,0), (-1,-1), 3.5, PRIMARY_GOLD),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('LEFTPADDING', (0,0), (-1,-1), 14),
                ('RIGHTPADDING', (0,0), (-1,-1), 14),
            ]))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 8))
        elif block_type == 'box_alert':
            p = Paragraph(f"<b>IMPORTANT GUARANTEE NOTICE:</b><br/>{data}", styles['body'])
            t = Table([[p]], colWidths=[500])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fefce8')),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#fef08a')),
                ('LINELEFT', (0,0), (-1,-1), 4, PRIMARY_GOLD),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('LEFTPADDING', (0,0), (-1,-1), 14),
                ('RIGHTPADDING', (0,0), (-1,-1), 14),
            ]))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 8))
        elif block_type == 'space':
            story.append(Spacer(1, data))
            
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"✅ Built PDF: {filename}")

def build_markdown(filename, title, content_blocks):
    md_filename = filename.replace('.pdf', '.md')
    md_path = DOCS_MD_DIR / md_filename
    
    lines = [f"# {title}\n\n"]
    for block_type, data in content_blocks:
        if block_type == 'h1':
            lines.append(f"\n## {data}\n\n")
        elif block_type == 'h2':
            lines.append(f"\n### {data}\n\n")
        elif block_type == 'body':
            lines.append(f"{data}\n\n")
        elif block_type == 'bullet':
            lines.append(f"* {data}\n")
        elif block_type == 'quote' or block_type == 'box_alert':
            lines.append(f"> {data}\n\n")
        elif block_type == 'space':
            lines.append("\n")
            
    with open(md_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"📝 Created Markdown: {md_filename}")

# ─── 1. START HERE ─────────────────────────────────────────────────────────────
content_start_here = [
    ('h1', 'Welcome to The Academic Comeback Package Partner Network'),
    ('body', 'Thank you for choosing to partner with us. As an affiliate, you are playing a vital role in helping ambitious students across tertiary institutions break free from academic frustration, failing grades, and study burnout.'),
    ('body', 'Our mission is to arm students with proven cognitive learning systems that transform their academic results. We hold ourselves and our partners to the highest standards of integrity, authenticity, and direct value.'),

    ('h1', 'What Is The Academic Comeback Package?'),
    ('body', 'The Academic Comeback Package is a comprehensive 7-part digital learning transformation system. It is not just another theoretical textbook. It is a battle-tested blueprint that teaches students how to master memory retention, eliminate exam anxiety, structure high-scoring exam answers, and balance school with personal business or life demands.'),

    ('h1', 'Who Is This Package Designed For?'),
    ('bullet', 'Students struggling with low GPAs, carryovers, or grade plateaus.'),
    ('bullet', 'Students who spend 8+ hours cramming in the library yet still get disappointing exam results.'),
    ('bullet', 'Busy student-entrepreneurs who need to balance business, work, and school without letting their grades drop.'),
    ('bullet', 'Freshmen and returning undergraduates feeling overwhelmed by university exam pressure and heavy course workloads.'),

    ('h1', 'The Transformation It Delivers'),
    ('body', 'When a student implements this system, they move from anxiety, cramming, and exam panic to high retention, confident exam execution, and consistent top-tier GPA performance.'),

    ('h1', 'How to Promote Successfully'),
    ('bullet', '<b>Be Genuine & Relatable:</b> Talk to your audience like a friend. Share real problems students face every day.'),
    ('bullet', '<b>Focus on the Solution:</b> Highlight the transformation and peace of mind the student receives.'),
    ('bullet', '<b>Use Provided Materials:</b> Utilize the templates, hooks, and guides inside this resource folder to kickstart your campaign.'),

    ('h1', 'Promoting Honestly & Ethically'),
    ('body', 'We take pride in our product reputation. Affiliates must promote honestly. Never make unrealistic claims such as guaranteeing a 5.0 GPA without effort. Always position the package as a proven system that requires student implementation.'),

    ('h1', 'Support You Can Count On'),
    ('body', 'You are never alone. Our team provides fast verification, manual payout processing twice per month (Mid-month & End-of-month), and continuous updates to your affiliate assets.')
]

# ─── 2. ABOUT THE PACKAGE ──────────────────────────────────────────────────────
content_about = [
    ('h1', 'Product Master Breakdown'),
    ('body', 'The Academic Comeback Package was created because traditional education teaches students <i>what</i> to learn, but never teaches them <i>how the brain actually processes, retains, and retrieves complex information</i> under exam pressure.'),

    ('h1', 'The 7 Core Resources Included inside the Bundle'),
    
    ('h2', '1. How To Score High In Any Exam'),
    ('body', 'Deconstructs exam grading criteria, decoding exam questions, and structuring answers that markers reward with full marks.'),
    
    ('h2', '2. Get Good At Hard Things'),
    ('body', 'Eliminates procrastination and mental resistance when tackling complex formulas, difficult courses, or dense material.'),

    ('h2', '3. Results-Oriented Learning System'),
    ('body', 'Replaces 8-hour library marathons with active recall, spaced repetition, and 90-minute hyper-focused learning blocks.'),

    ('h2', '4. How To Balance Academics & Business'),
    ('body', 'Practical time-blocking and energy management systems for student entrepreneurs to run businesses without sacrificing their GPA.'),

    ('h2', '5. Exam Survival & Pressure Management Guide'),
    ('body', 'Step-by-step psychological protocols to eliminate pre-exam panic, brain freeze, and test anxiety on exam day.'),

    ('h2', '6. Deep Focus & Attention Architecture Template'),
    ('body', 'Defeats smartphone distraction and social media addiction, turning any room into a distraction-free deep work zone.'),

    ('h2', '7. 30-Day Academic Transformation Tracker'),
    ('body', 'Interactive daily habit and study progress log that keeps students consistent and accountable throughout the semester.'),

    ('h1', 'Common Problems Solved'),
    ('bullet', '<b>Memory Retention Failure:</b> Forgetting everything read 10 minutes into the exam.'),
    ('bullet', '<b>Library Marathon Burnout:</b> Studying for 10 hours continuously with zero retention.'),
    ('bullet', '<b>Exam Panic & Anxiety:</b> Freezing up when faced with tough exam questions.'),
    ('bullet', '<b>Grade Plateaus:</b> Staying stuck at 2.0 - 3.0 GPA despite maximum effort.')
]

# ─── 4. HOW TO TALK ABOUT THE PRODUCT ──────────────────────────────────────────
content_how_to_talk = [
    ('h1', 'Direct Response Copywriting & Content Guide'),
    ('body', 'The secret to converting prospects into sales is not hard-selling or spamming links. It is positioning yourself as an advisor who understands their exact struggle.'),

    ('h1', 'Different Marketing Angles to Use'),
    ('h2', 'Angle 1: The Library Marathon Trap'),
    ('quote', '"Studying 8 hours a day is not a badge of honor if you forget 80% of it in the exam hall. Here is the active recall system top students use instead..."'),

    ('h2', 'Angle 2: The Carryover & GPA Rescue Angle'),
    ('quote', '"Retaking a failed course costs time, tuition, and embarrassment. Preventing a carryover with a N5,000 proven study framework is the smartest investment you can make this semester."'),

    ('h2', 'Angle 3: The Busy Student-Entrepreneur Angle'),
    ('quote', '"You do not have to choose between making money and getting good grades. Here is how to structure your 24 hours so both thrive."'),

    ('h1', 'Curiosity Hooks Library'),
    ('bullet', '"Why reading your lecture notes 5 times is actually destroying your exam score (and what to do instead)."'),
    ('bullet', '"The 90-minute study rule used by first-class students to retain 3x more information."'),
    ('bullet', '"How to stop freezing in the exam hall when you see unexpected questions."'),

    ('h1', 'Social Media & WhatsApp Status Sequence Example'),
    ('body', '<b>Frame 1 (Pain Point):</b> "Hate the feeling of reading all night only to stare at an exam paper blankly?"'),
    ('body', '<b>Frame 2 (Insight):</b> "It is not your memory. It is your study method. Rote memorization fails under exam stress. Active recall never does."'),
    ('body', '<b>Frame 3 (Solution + Call to Action):</b> "The Academic Comeback Package details the exact step-by-step active recall blueprint. Click the link to grab your bundle now."' )
]

# ─── 5. THINGS YOU CAN SAFELY PROMISE ─────────────────────────────────────────
content_promises = [
    ('h1', 'The Creator Money-Back Guarantee (Critical Information)'),
    ('box_alert', 'Customers are protected by a 100% Money-Back Guarantee provided directly by the product owner.<br/><br/>• If a customer is genuinely unsatisfied, the refund is handled and guaranteed 100% by the creator.<br/>• The affiliate NEVER bears the cost of refunds.<br/>• Legitimate customer refunds DO NOT reduce, deduct, or cancel your earned affiliate commission balance.<br/>• You can confidently mention this guarantee in all your promotion!'),

    ('h1', 'Suggested Refund Wording You Can Copy'),
    ('quote', '"If you don\'t find the Academic Comeback Package valuable, your money will be refunded. The guarantee is provided directly by the creator, so you can purchase with total confidence."'),

    ('h1', 'What You Can Safely Promise'),
    ('bullet', 'Instant digital delivery to all 7 books and study frameworks immediately after payment.'),
    ('bullet', 'Access to proven active recall and exam preparation blueprints.'),
    ('bullet', 'Practical step-by-step guides on time management, focus, and exam question decoding.'),

    ('h1', 'What You MUST NOT Promise (Forbidden Statements)'),
    ('bullet', '<b>DO NOT</b> promise specific letter grades or GPAs (e.g., "Guaranteed 4.5 GPA without studying").'),
    ('bullet', '<b>DO NOT</b> promise that buying the book alone without applying the steps will pass their exams.'),
    ('bullet', '<b>DO NOT</b> create fake scarcity timers or misleading countdown claims on personal chats.')
]

# ─── 6. AFFILIATE GUIDELINES ──────────────────────────────────────────────────
content_guidelines = [
    ('h1', 'Partnership Terms & Operational Guidelines'),
    
    ('h2', 'Commission Structure'),
    ('body', 'Affiliates earn a generous <b>50% commission</b> on every successful customer sale generated through their unique referral link or referral code (N2,500 per N5,000 sale).'),

    ('h2', 'Sales Tracking Mechanism'),
    ('body', 'Sales are tracked seamlessly via browser cookie attribution and referral code locking at checkout. When a customer clicks your link, your attribution is locked to their transaction.'),

    ('h2', 'Payout Schedule & Processing'),
    ('body', 'Affiliate payout balances are processed <b>twice every month</b>:'),
    ('bullet', '<b>Mid-Month Payout:</b> Covers earnings accrued in the first half of the month.'),
    ('bullet', '<b>End-of-Month Payout:</b> Covers earnings accrued in the second half of the month.'),
    ('body', 'Payouts are transferred directly into your registered Nigerian bank account (Access, GTBank, Kuda, Zenith, OPay, Palmpay, UBA, etc.) as logged in your affiliate dashboard.'),

    ('h2', 'Expected Professional Conduct'),
    ('bullet', 'No spamming in official university group chats or unapproved forums.'),
    ('bullet', 'Maintain high ethical standards and represent the brand with excellence.')
]

# ─── 7. FREQUENTLY ASKED QUESTIONS ────────────────────────────────────────────
content_faq = [
    ('h1', 'Frequently Asked Questions (FAQ)'),
    
    ('h2', 'Q1: Who is the package for?'),
    ('body', 'It is for any student in tertiary institutions (university, polytechnic, college) who wants to improve their study efficiency, raise their GPA, and conquer exam anxiety.'),

    ('h2', 'Q2: How is the product delivered? Is it instant access?'),
    ('body', 'Yes! Access is 100% instant. As soon as the customer completes payment, they are immediately redirected to their digital library and an email with access credentials is sent to their inbox.'),

    ('h2', 'Q3: What if a customer wants a refund?'),
    ('body', 'The refund is 100% backed by the creator. Customers simply reach out to support. As an affiliate, you never bear refund costs, and earned commissions are not deducted.'),

    ('h2', 'Q4: How and when do affiliates get paid?'),
    ('body', 'Affiliate payouts are sent twice a month (Mid-month and End-of-month) directly to the bank account listed in your affiliate dashboard.'),

    ('h2', 'Q5: Can I promote on WhatsApp, Telegram, or social media?'),
    ('body', 'Yes! WhatsApp, Telegram, Instagram, TikTok, Facebook, and X (Twitter) are highly recommended channels.'),

    ('h2', 'Q6: Can I run paid ads?'),
    ('body', 'Yes, paid advertising (Meta Ads, Google Search, TikTok Ads) is permitted as long as guidelines and ethical promises are respected.')
]

def prepare_covers():
    # Clear existing files in COVERS_DIR to remove old bad filenames
    for old_file in COVERS_DIR.glob("*"):
        if old_file.is_file():
            old_file.unlink()

    source_images = BASE_DIR / "frontend" / "assets" / "images"
    image_mapping = [
        ("bookcoverlandscape.webp", "01_ACADEMIC_COMEBACK_BUNDLE_LANDSCAPE.png"),
        ("bookcover.webp", "02_GET_GOOD_AT_HARD_THINGS.png"),
        ("bookcover1.webp", "03_HOW_TO_SCORE_HIGH_IN_ANY_EXAM.png"),
        ("bookcover2.webp", "04_HOW_TO_BALANCE_ACADEMICS_AND_YOUR_BUSINESS.png"),
        ("bookcover3.webp", "05_RESULTS_ORIENTED_LEARNING_SYSTEM.png"),
    ]
    
    for src_name, dest_name in image_mapping:
        src_path = source_images / src_name
        dest_path = COVERS_DIR / dest_name
        if src_path.exists():
            try:
                with Image.open(src_path) as img:
                    img.convert("RGB").save(dest_path, "PNG")
                print(f"🖼️ Exported cover: {dest_name}")
            except Exception as e:
                print(f"⚠️ Error processing {src_name}: {e}")

def main():
    print("=" * 80)
    print("GENERATING OFFICIAL AFFILIATE RESOURCE PACKAGE")
    print("=" * 80)

    # Clean old files in OUTPUT_DIR
    for pdf in OUTPUT_DIR.glob("*.pdf"):
        pdf.unlink()

    # 1. Start Here
    build_pdf("1. START HERE.pdf", "1. START HERE", "Essential Welcome & Onboarding Guide for Affiliates", content_start_here)
    build_markdown("1. START HERE.pdf", "1. START HERE — Essential Welcome Guide", content_start_here)

    # 2. About The Package
    build_pdf("2. ABOUT THE ACADEMIC COMEBACK PACKAGE.pdf", "2. ABOUT THE ACADEMIC COMEBACK PACKAGE", "Detailed Product Breakdown & Module Guide", content_about)
    build_markdown("2. ABOUT THE ACADEMIC COMEBACK PACKAGE.pdf", "2. ABOUT THE ACADEMIC COMEBACK PACKAGE", content_about)

    # 3. Product Covers
    prepare_covers()

    # 4. How To Talk About The Product
    build_pdf("4. HOW TO TALK ABOUT THE PRODUCT.pdf", "4. HOW TO TALK ABOUT THE PRODUCT", "Copywriting, Content Frameworks & Marketing Angles", content_how_to_talk)
    build_markdown("4. HOW TO TALK ABOUT THE PRODUCT.pdf", "4. HOW TO TALK ABOUT THE PRODUCT", content_how_to_talk)

    # 5. Things You Can Safely Promise
    build_pdf("5. THINGS YOU CAN SAFELY PROMISE.pdf", "5. THINGS YOU CAN SAFELY PROMISE", "Money-Back Guarantee Protocols & Permitted Claims", content_promises)
    build_markdown("5. THINGS YOU CAN SAFELY PROMISE.pdf", "5. THINGS YOU CAN SAFELY PROMISE", content_promises)

    # 6. Affiliate Guidelines
    build_pdf("6. AFFILIATE GUIDELINES.pdf", "6. AFFILIATE GUIDELINES", "Commission Rules, Tracking & Twice-Monthly Payouts", content_guidelines)
    build_markdown("6. AFFILIATE GUIDELINES.pdf", "6. AFFILIATE GUIDELINES", content_guidelines)

    # 7. FAQ
    build_pdf("7. FREQUENTLY ASKED QUESTIONS.pdf", "7. FREQUENTLY ASKED QUESTIONS", "Complete Partner & Product FAQ Guide", content_faq)
    build_markdown("7. FREQUENTLY ASKED QUESTIONS.pdf", "7. FREQUENTLY ASKED QUESTIONS", content_faq)

    # Move docs_markdown outside of OUTPUT_DIR temporarily before zipping so ZIP is clean
    temp_md_storage = BASE_DIR / "docs_markdown_temp"
    if DOCS_MD_DIR.exists():
        shutil.move(str(DOCS_MD_DIR), str(temp_md_storage))

    # Create Zip File for single download containing ONLY the 7 core items
    archive_path = BASE_DIR / "frontend" / "assets" / "Academic_Comeback_Package_Affiliate_Resource_Folder.zip"
    shutil.make_archive(str(archive_path).replace('.zip', ''), 'zip', OUTPUT_DIR)
    print(f"📦 Created Clean Zip Package: {archive_path.name}")

    # Restore docs_markdown directory back into OUTPUT_DIR
    if temp_md_storage.exists():
        shutil.move(str(temp_md_storage), str(DOCS_MD_DIR))

    print("=" * 80)
    print("ALL AFFILIATE RESOURCE FILES CREATED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()
