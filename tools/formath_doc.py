#!/usr/bin/env python3
"""
ForMath Pipeline — Technische Documentatie
Gegenereerd via ReportLab
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import Flowable

# ─── Kleuren ──────────────────────────────────────────────────────────────────
BLAUW      = colors.HexColor('#1a3a5c')
LICHTBLAUW = colors.HexColor('#e8f0f8')
ACCENTBLAUW= colors.HexColor('#2176AE')
GRIJS      = colors.HexColor('#f4f6f9')
DONKERGRIJS= colors.HexColor('#444444')
GROEN      = colors.HexColor('#1e6b3a')
LICHTGROEN = colors.HexColor('#eafaf1')
ORANJE     = colors.HexColor('#cc5500')
LICHTROOD  = colors.HexColor('#fdecea')

# ─── Stijlen ──────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def make_styles():
    s = {}

    s['doc_title'] = ParagraphStyle('doc_title',
        fontSize=26, fontName='Helvetica-Bold',
        textColor=BLAUW, alignment=TA_CENTER,
        spaceAfter=6)

    s['doc_subtitle'] = ParagraphStyle('doc_subtitle',
        fontSize=13, fontName='Helvetica',
        textColor=DONKERGRIJS, alignment=TA_CENTER,
        spaceAfter=4)

    s['doc_meta'] = ParagraphStyle('doc_meta',
        fontSize=10, fontName='Helvetica',
        textColor=colors.grey, alignment=TA_CENTER,
        spaceAfter=2)

    s['h1'] = ParagraphStyle('h1',
        fontSize=16, fontName='Helvetica-Bold',
        textColor=BLAUW, spaceBefore=18, spaceAfter=8,
        borderPad=4)

    s['h2'] = ParagraphStyle('h2',
        fontSize=13, fontName='Helvetica-Bold',
        textColor=ACCENTBLAUW, spaceBefore=12, spaceAfter=6)

    s['h3'] = ParagraphStyle('h3',
        fontSize=11, fontName='Helvetica-Bold',
        textColor=DONKERGRIJS, spaceBefore=8, spaceAfter=4)

    s['body'] = ParagraphStyle('body',
        fontSize=10, fontName='Helvetica',
        textColor=DONKERGRIJS, spaceAfter=5,
        leading=15, alignment=TA_JUSTIFY)

    s['bullet'] = ParagraphStyle('bullet',
        fontSize=10, fontName='Helvetica',
        textColor=DONKERGRIJS, spaceAfter=3,
        leading=14, leftIndent=16, bulletIndent=4)

    s['code'] = ParagraphStyle('code',
        fontSize=8.5, fontName='Courier',
        textColor=colors.HexColor('#1a1a1a'),
        backColor=GRIJS, spaceAfter=4,
        leading=13, leftIndent=10, rightIndent=10,
        borderPad=6)

    s['toc_entry'] = ParagraphStyle('toc_entry',
        fontSize=10, fontName='Helvetica',
        textColor=DONKERGRIJS, spaceAfter=3, leading=14)

    s['toc_h2'] = ParagraphStyle('toc_h2',
        fontSize=10, fontName='Helvetica',
        textColor=DONKERGRIJS, spaceAfter=2,
        leading=13, leftIndent=16)

    s['caption'] = ParagraphStyle('caption',
        fontSize=9, fontName='Helvetica-Oblique',
        textColor=colors.grey, alignment=TA_CENTER,
        spaceAfter=8)

    s['term'] = ParagraphStyle('term',
        fontSize=10, fontName='Helvetica-Bold',
        textColor=BLAUW, spaceAfter=1)

    s['definition'] = ParagraphStyle('definition',
        fontSize=10, fontName='Helvetica',
        textColor=DONKERGRIJS, spaceAfter=6,
        leading=14, leftIndent=16)

    s['warning'] = ParagraphStyle('warning',
        fontSize=10, fontName='Helvetica',
        textColor=ORANJE, spaceAfter=4,
        leading=14, leftIndent=8)

    s['page_num'] = ParagraphStyle('page_num',
        fontSize=9, fontName='Helvetica',
        textColor=colors.grey, alignment=TA_CENTER)

    return s

S = make_styles()

def P(text, style='body'): return Paragraph(text, S[style])
def SP(h=0.3): return Spacer(1, h*cm)
def HR(): return HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=8)
def HR_bold(): return HRFlowable(width='100%', thickness=2, color=ACCENTBLAUW, spaceAfter=10)

def colored_box(text, bg=LICHTBLAUW, style='body'):
    data = [[Paragraph(text, S[style])]]
    t = Table(data, colWidths=[16.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    return t

def pipeline_table(rows, col_widths=None):
    if col_widths is None:
        col_widths = [4*cm, 4*cm, 4*cm, 4.5*cm]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLAUW),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRIJS]),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8.5),
        ('TEXTCOLOR', (0,1), (-1,-1), DONKERGRIJS),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    return t

# ─── Paginanummering ──────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0]/2, 1.5*cm, f"ForMath Pipeline — Technische Documentatie  |  pagina {doc.page}")
    canvas.setStrokeColor(colors.HexColor('#dddddd'))
    canvas.setLineWidth(0.5)
    canvas.line(2*cm, 1.8*cm, A4[0]-2*cm, 1.8*cm)
    canvas.restoreState()

def on_first_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BLAUW)
    canvas.rect(0, A4[1]-3.5*cm, A4[0], 3.5*cm, fill=1, stroke=0)
    canvas.restoreState()

# ─── Document opbouw ──────────────────────────────────────────────────────────
def build_doc():
    path = '/mnt/user-data/outputs/ForMath_Pipeline_Documentatie.pdf'
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
        title='ForMath Pipeline — Technische Documentatie',
        author='ForMath Project'
    )

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # TITELBLAD
    # ══════════════════════════════════════════════════════════════════════════
    story.append(SP(4))
    story.append(P('ForMath Pipeline', 'doc_title'))
    story.append(SP(1.2))
    story.append(P('Technische Documentatie', 'doc_subtitle'))
    story.append(SP(0.5))
    story.append(HR_bold())
    story.append(SP(0.3))
    story.append(P('Architectuur &middot; Input/Output &middot; Ontwerpbeslissingen &middot; Bestandsdocumentatie', 'doc_subtitle'))
    story.append(SP(0.5))
    story.append(P('Versie 1.0 &nbsp;&nbsp;|&nbsp;&nbsp; Maart 2026 &nbsp;&nbsp;|&nbsp;&nbsp; Auteur: H.N. Lensing', 'doc_meta'))
    story.append(SP(2))

    story.append(colored_box(
        'Dit document beschrijft de ForMath pipeline — een systeem dat wiskundige expressies '
        'omzet naar gestructureerde JSON-bestanden en SVG-visualisaties. Het dient als '
        'technische referentie voor ontwikkelaars die werken aan de invoertool of de studenttool.',
        bg=LICHTBLAUW
    ))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # INHOUDSOPGAVE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(P('Inhoudsopgave', 'h1'))
    story.append(HR())

    toc = [
        ('1', 'Projectoverzicht', '3'),
        ('2', 'Input en Output', '4'),
        ('3', 'Pipeline Architectuur', '5'),
        ('4', 'Bestandsdocumentatie', '7'),
        ('', '4.1  expression_parser.py', '7'),
        ('', '4.2  ast_normalizer.py', '8'),
        ('', '4.3  manifold_detector.py', '9'),
        ('', '4.4  manifold_converter.py', '10'),
        ('', '4.5  tak_allocator.py', '10'),
        ('', '4.6  step_calculator.py', '11'),
        ('', '4.7  ast_visualizer.py', '11'),
        ('', '4.8  ast_to_mathjson.py', '12'),
        ('', '4.9  json_generator_v2.py', '13'),
        ('', '4.10 json_exporter.py', '13'),
        ('', '4.11 server.py', '14'),
        ('', '4.12 index.html', '15'),
        ('5', 'JSON Outputformaat', '16'),
        ('6', 'Grootste Problemen en Oplossingen', '18'),
        ('7', 'Verklarende Woordenlijst', '21'),
        ('8', 'Gebruikte Afkortingen', '23'),
    ]

    # Inhoudsopgave als tabel: titel links, paginanummer rechts uitgelijn
    toc_style_h1 = ParagraphStyle('toc_h1_t', fontSize=10, fontName='Helvetica-Bold',
        textColor=BLAUW, leading=14)
    toc_style_body = ParagraphStyle('toc_body_t', fontSize=10, fontName='Helvetica',
        textColor=DONKERGRIJS, leading=14)
    toc_style_sub = ParagraphStyle('toc_sub_t', fontSize=10, fontName='Helvetica',
        textColor=DONKERGRIJS, leading=13, leftIndent=14)
    toc_style_pag = ParagraphStyle('toc_pag_t', fontSize=10, fontName='Helvetica',
        textColor=DONKERGRIJS, alignment=TA_LEFT, leading=14)

    toc_rows = []
    for nr, titel, pag in toc:
        if nr:
            toc_rows.append([
                Paragraph(f'<b>{nr}&nbsp;&nbsp;</b>{titel}', toc_style_h1),
                Paragraph(pag, toc_style_pag)
            ])
        else:
            toc_rows.append([
                Paragraph(f'&nbsp;&nbsp;&nbsp;&nbsp;{titel}', toc_style_sub),
                Paragraph(pag, toc_style_pag)
            ])

    toc_table = Table(toc_rows, colWidths=[15*cm, 1.5*cm])
    toc_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('LEFTPADDING', (1,0), (1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, colors.HexColor('#e0e0e0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (0,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(toc_table)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 1. PROJECTOVERZICHT
    # ══════════════════════════════════════════════════════════════════════════
    story.append(P('1. Projectoverzicht', 'h1'))
    story.append(HR())

    story.append(P(
        'ForMath is een interactief systeem voor wiskundeonderwijs dat bestaat uit twee '
        'gekoppelde tools: een <b>invoertool</b> voor de docent en een <b>studenttool</b>. '
        'De docent voert een wiskundige opgave in via een webinterface. De ForMath pipeline '
        'verwerkt deze invoer stap voor stap naar een gestructureerd JSON-bestand en een '
        'SVG-visualisatie. De studenttool gebruikt de JSON om de student interactief door '
        'de oplossing te begeleiden.'))

    story.append(SP(0.3))
    story.append(P('Doelstelling', 'h2'))
    story.append(P(
        'De pipeline ontleedt een wiskundige expressie volledig: welke bewerkingen er zijn, '
        'in welke volgorde ze uitgevoerd moeten worden, welke tussenuitkomsten er zijn, en hoe '
        'de bewerkingen in een visuele boom-structuur zijn georganiseerd. Dit levert de '
        'studenttool de informatie die nodig is om een gepersonaliseerde oefenomgeving te bieden.'))

    story.append(SP(0.3))
    story.append(P('Systeemgrenzen', 'h2'))

    rows = [
        ['Component', 'Verantwoordelijkheid', 'Technologie'],
        ['Invoertool (browser)', 'Expressie invoeren, JSON + SVG opvragen', 'HTML + MathLive + JavaScript'],
        ['Web server', 'HTTP-verzoeken afhandelen, pipeline aanroepen', 'Python (http.server)'],
        ['ForMath pipeline', 'Expressie verwerken naar JSON + SVG', 'Python (10 modules)'],
        ['Studenttool', 'JSON inlezen, interactieve weergave', 'Extern systeem'],
    ]
    story.append(pipeline_table(rows, [4*cm, 7*cm, 5*cm]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 2. INPUT EN OUTPUT
    # ══════════════════════════════════════════════════════════════════════════
    story.append(P('2. Input en Output', 'h1'))
    story.append(HR())

    story.append(P('Input', 'h2'))
    story.append(P(
        'De docent voert een wiskundige expressie in via het MathLive-invoerveld of het '
        'tekstveld in de browser. De expressie wordt verstuurd als ascii-math string naar '
        'de server. Voorbeelden van geldige expressies:'))

    for ex in [
        '1 + [(10:2)*6 + (15:3) - 3] : (4*2) - [(3*5):5 + 2]',
        '(2 - 3/5 - 33/15)^2',
        '[(3^2)*(12-9)^3] : (9-6)^3 : (-3) * [(-6)^2] : 3^4 + (-2)^3',
        '(2-(3)/(5)-(33)/(15)) + (1+(4)/(3)-(1)/(2):3-1+(1)/(6))^3 : (5)/(27)',
    ]:
        story.append(P(f'&bull; <font name="Courier">{ex}</font>', 'bullet'))

    story.append(SP(0.3))
    story.append(P('Ondersteunde operatoren', 'h3'))
    rows = [
        ['Symbool', 'Betekenis', 'Voorbeeld'],
        ['+', 'Optelling', '3 + 4'],
        ['-', 'Aftrekking / negatie', '7 - 2, -5'],
        ['x (of *)', 'Vermenigvuldiging', '3x4'],
        [':', 'Deling (rekenstap)', '10:2'],
        ['/', 'Breuk (teller/noemer)', '3/5'],
        ['^', 'Machtsverheffing', '3^2'],
        ['( )', 'Haakjes (prioriteit)', '(3+4):2'],
        ['[ ]', 'Vierkante haakjes', '[3+4]*2'],
    ]
    story.append(pipeline_table(rows, [3*cm, 7*cm, 6*cm]))

    story.append(SP(0.4))
    story.append(P('Output', 'h2'))
    story.append(P('De pipeline produceert twee outputs per opgave:'))

    story.append(SP(0.2))
    story.append(P('<b>1. SVG-visualisatie</b> — een boomdiagram van de expressiestructuur:', 'h3'))
    for item in [
        'Operatieblokken (blauw) met hun block ID (bijv. A1, B2)',
        'Externe inputs (wit): getallen en breuken als invoerblokjes',
        'Horizontale stap-indeling: stap 1 onderaan, root bovenaan',
        'Manifold-nodes (oranje) voor commutatieve ketens',
        'Machtsverheffen als aparte node met exponent als label',
    ]:
        story.append(P(f'&bull; {item}', 'bullet'))

    story.append(SP(0.2))
    story.append(P('<b>2. JSON-bestand</b> — de gestructureerde opgavebeschrijving:', 'h3'))
    for item in [
        'metadata.expressie.tekst — de verwerkte ascii-math string',
        'metadata.expressie.latex_display — LaTeX voor weergave in de studenttool',
        'metadata.expressie.ast — MathJSON boom + node_map',
        'mathblocks — alle rekenstappen met inputs, output, stap en block ID',
        'externe_inputs — alle externe invoerwaarden',
        'steps — overzicht per stap welke mathblocks erin zitten',
        'duo_verzameling — DUO (Due Operations) per stap: hoog en laag prioriteit',
    ]:
        story.append(P(f'&bull; {item}', 'bullet'))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 3. PIPELINE ARCHITECTUUR
    # ══════════════════════════════════════════════════════════════════════════
    story.append(P('3. Pipeline Architectuur', 'h1'))
    story.append(HR())

    story.append(P(
        'De ForMath pipeline bestaat uit tien Python-modules die sequentieel worden uitgevoerd. '
        'Elke module ontvangt de AST van de vorige module, verrijkt deze met aanvullende '
        'informatie, en geeft de verrijkte AST door aan de volgende module.'))

    story.append(SP(0.4))

    # Pipeline flow tabel op landscape pagina
    from reportlab.platypus import NextPageTemplate
    from reportlab.platypus.frames import Frame
    from reportlab.platypus import BaseDocTemplate, PageTemplate

    # Gebruik een speciale landschapspagina voor de brede tabel
    story.append(PageBreak())

    # Maak de flow-tabel met Paragraph-cellen zodat tekst omloopt
    ts = ParagraphStyle('flow_cell', fontSize=8, fontName='Helvetica',
        textColor=DONKERGRIJS, leading=11)
    ts_h = ParagraphStyle('flow_head', fontSize=8.5, fontName='Helvetica-Bold',
        textColor=colors.white, leading=11)

    def fc(txt, header=False):
        return Paragraph(txt, ts_h if header else ts)

    flow_data = [
        [fc('Stap',True), fc('Module',True), fc('Input',True), fc('Output',True), fc('Kernbewerking',True)],
        [fc('1'), fc('expression_parser'), fc('ascii-math string'), fc('AST dict'), fc('Lexer + recursive descent parser. Herkent breuken, operatoren, haakjes, machten.')],
        [fc('2'), fc('ast_normalizer'), fc('AST'), fc('Genormaliseerde AST'), fc('a-b → a+(-b), is_negative vlag, FRACTION vereenvoudiging, POWER recursie')],
        [fc('3'), fc('manifold_detector'), fc('Norm. AST'), fc('Geannoteerde AST + statistieken'), fc('Detecteer commutatieve ketens van 3+ operanden. Annoteer nodes met _node_id.')],
        [fc('4'), fc('manifold_converter'), fc('Geannoteerde AST'), fc('Geconverteerde AST'), fc('Vervang aaneengesloten binaire ketens door MANIFOLD_OP nodes met operands-lijst.')],
        [fc('5'), fc('tak_allocator'), fc('Geconv. AST'), fc('AST + _tak_name'), fc('Ken horizontale tak-namen toe: root = A, kinderen A.1, A.2, B, B.1 enzovoort.')],
        [fc('6'), fc('step_calculator'), fc('AST + takken'), fc('AST + _step_number'), fc('Ken verticale stap-nummers toe (top-down: root = max, bladeren = 0).')],
        [fc('7'), fc('ast_visualizer'), fc('Volledig AST'), fc('SVG ElementTree'), fc('Bereken layout, teken boom met block IDs, stap-lijnen, manifold- en POWER-nodes.')],
        [fc('8'), fc('ast_to_mathjson'), fc('Geconv. AST + block IDs'), fc('MathJSON tree + node_map'), fc('Serialiseer AST naar MathJSON. Genereer node_map met pad → block ID koppeling.')],
        [fc('9'), fc('json_generator_v2'), fc('Volledig AST'), fc('JSON dict'), fc('Genereer steps, inputs, outputs, LaTeX-velden, output_latex, reduced_expression_latex.')],
        [fc('10'), fc('json_exporter'), fc('Geconv. AST + metadata'), fc('JSON bestand op schijf'), fc('Schrijf volledige opgave JSON naar ~/Desktop/JSON_files_ForMath/.')],
    ]

    # Landscape breedte: A4 gedraaid = 297mm - 4cm marges = 25.7cm
    flow_table = Table(flow_data, colWidths=[1.2*cm, 3.8*cm, 3.5*cm, 4*cm, 11.7*cm],
                       repeatRows=1)
    flow_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLAUW),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRIJS]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    # Landscape wrapper
    from reportlab.lib.pagesizes import landscape
    LS = landscape(A4)  # (841.89, 595.28)

    class LandscapePage(Flowable):
        def __init__(self, table):
            Flowable.__init__(self)
            self.table = table
            self.width = LS[0] - 4*cm
            self.height = 0

        def wrap(self, availW, availH):
            w, h = self.table.wrap(self.width, availH)
            self.height = h
            return w, h

        def draw(self):
            self.table.drawOn(self.canv, 0, 0)

    # Genereer landscape pagina via canvas transform
    class RotatedTable(Flowable):
        """Tabel op een landscape-georiënteerde pagina."""
        def __init__(self, table, title_text=''):
            Flowable.__init__(self)
            self.table = table
            self.title_text = title_text
            # Afmetingen: breedte = landscape breedte minus marges
            self.ls_w = LS[0]
            self.ls_h = LS[1]
            self.margin = 2*cm

        def wrap(self, availW, availH):
            # We nemen een hele pagina in beslag (portrait hoogte = landscape breedte)
            return availW, availH

        def draw(self):
            c = self.canv
            c.saveState()

            # Portrait pagina: breedte=595, hoogte=842
            # Tabel staat landscape gedraaid binnen de portrait pagina
            # Marges: 1cm van bovenkant, 2cm van linkerkant
            #
            # Bewezen methode (getest):
            #   translate(2cm, 842-1cm)  → origin op linksboven hoek van tabel
            #   rotate(-90)               → x-as loopt omlaag, y-as loopt naar rechts
            #   wrapOn(c, tbl_breedte, tbl_hoogte_max)
            #   drawOn(c, 0, 0)           → tabel begint linksboven

            portrait_w = A4[0]   # 595
            portrait_h = A4[1]   # 842
            margin_left = 2 * cm
            margin_top  = 2 * cm

            # Tabel breedte loopt verticaal in portrait = portrait hoogte - marges
            tbl_w = portrait_h - margin_top - 1 * cm
            # Tabel hoogte loopt horizontaal in portrait = portrait breedte - marges
            tbl_h_max = portrait_w - margin_left - 1 * cm

            tw, th = self.table.wrapOn(c, tbl_w, tbl_h_max)

            # rotate(-90): origin=(links, boven) in portrait
            # margin_left=5cm, margin_top=2cm
            # 180 graden t.o.v. rotate(-90):
            # Origin naar rechtsonder hoek van tabel, dan rotate(90)
            # margin_top = 1cm van boven paginarand
            # margin_top=1cm van boven paginarand (boven = kant waar tabel-header staat)
            # Na rotate(90): y-as loopt van rechtsonder naar rechtsboven in portrait
            # Tabel tekst staat rechtop als je pagina 90 graden rechtsom draait
            c.translate(margin_left + th, portrait_h - 4.5*cm - tw)
            c.rotate(90)
            self.table.drawOn(c, 0, 0)

            # Titel net boven de tabel (negatieve y = boven de tabel na rotate(90))
            c.setFont('Helvetica-Bold', 11)
            c.setFillColor(colors.HexColor('#1a3a5c'))
            c.drawString(0, -0.5 * cm, self.title_text)

            c.restoreState()

    story.append(RotatedTable(flow_table, 'Pipeline Architectuur — Overzicht van alle stappen'))

    story.append(SP(0.5))
    story.append(P('AST — Abstract Syntax Tree', 'h2'))
    story.append(P(
        'De AST is een geneste Python dict die de expressiestructuur representeert. '
        'Elke node heeft minimaal een <font name="Courier">type</font>-sleutel. '
        'Naarmate de pipeline vordert worden extra sleutels toegevoegd:'))

    rows = [
        ['Na stap', 'Nieuwe sleutels op nodes'],
        ['1 — parser', 'type, value/numerator/denominator, operator, left, right, base, exponent'],
        ['2 — normalizer', 'is_negative, _via_subtraction, _bracketed'],
        ['3 — detector', '_node_id, _chain_candidate, _chain_size'],
        ['4 — converter', 'MANIFOLD_OP nodes met operands-lijst; _node_id bewaard'],
        ['5 — tak_allocator', '_tak_name, _tak_direction'],
        ['6 — step_calculator', '_step_number'],
    ]
    story.append(pipeline_table(rows, [3.5*cm, 13*cm]))

    story.append(SP(0.4))
    story.append(P('Node typen', 'h2'))
    rows = [
        ['Type', 'Beschrijving', 'Sleutels'],
        ['NUMBER', 'Geheel getal', 'value'],
        ['FRACTION', 'Breuk p/q (niet deelbaar)', 'numerator, denominator'],
        ['BINARY_OP', 'Binaire operatie (+, -, x, :)', 'operator, left, right'],
        ['MANIFOLD_OP', 'Commutatieve keten (3+ operanden)', 'operator, operands, operand_count'],
        ['POWER', 'Machtsverheffing', 'base, exponent'],
    ]
    story.append(pipeline_table(rows, [3*cm, 6*cm, 7.5*cm]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 4. BESTANDSDOCUMENTATIE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(P('4. Bestandsdocumentatie', 'h1'))
    story.append(HR())

    # ── 4.1 expression_parser.py ──────────────────────────────────────────────
    story.append(P('4.1  expression_parser.py', 'h2'))
    story.append(P('<b>Rol:</b> Zet een ascii-math expressiestring om naar een AST.', 'body'))
    story.append(P('<b>Architectuur:</b> Bestaat uit drie klassen en twee hulpfuncties:', 'body'))
    for item in [
        '<font name="Courier">Lexer</font> — tokeniseert de invoerstring: getallen, operatoren, haakjes. Herkent breuken (p/q zonder spatie) als FRACTION-token.',
        '<font name="Courier">Parser</font> — recursive descent parser met voorrangsregels: haakjes &gt; macht &gt; x/: &gt; +/-.',
        '<font name="Courier">_preprocess_expression()</font> — pre-processing voor MathLive ascii-math: zet (3)/(5) om naar 3/5 zodat de lexer het als FRACTION herkent.',
        '<font name="Courier">parse_expression()</font> — publieke API, roept pre-processing en parser aan.',
    ]:
        story.append(P(f'&bull; {item}', 'bullet'))

    story.append(P('<b>Breuk vs. deling:</b>', 'h3'))
    story.append(P(
        'De lexer maakt onderscheid tussen een breuk (FRACTION-token, bijv. 3/5) en een '
        'deling (BINARY_OP(:), bijv. 10:2). De regel: <font name="Courier">p/q</font> zonder '
        'haakjes ervoor is een FRACTION-token. Na de normalizer wordt een FRACTION waarbij '
        'de teller een veelvoud is van de noemer (bijv. 6/2) omgezet naar BINARY_OP(:).'))

    story.append(SP(0.2))
    story.append(P('<b>Pre-processing stappen:</b>', 'h3'))
    rows = [
        ['Patroon', 'Resultaat', 'Reden'],
        ['(3)/(5)', '3/5', 'MathLive notatie voor breuk'],
        ['(33)/(15)', '33/15', 'MathLive notatie voor breuk'],
        ['a:(5)/(27)', 'a:(5/27)', 'Deling door breuk = vermenigvuldiging met omgekeerde'],
    ]
    story.append(pipeline_table(rows, [4*cm, 4*cm, 8.5*cm]))

    story.append(SP(0.3))

    # ── 4.2 ast_normalizer.py ─────────────────────────────────────────────────
    story.append(P('4.2  ast_normalizer.py', 'h2'))
    story.append(P('<b>Rol:</b> Normaliseert de AST voor eenvoudiger manifold-detectie.', 'body'))
    story.append(P('<b>Transformaties:</b>', 'h3'))
    rows = [
        ['Transformatie', 'Van', 'Naar'],
        ['Aftrekking eliminatie', 'BINARY_OP(-)', 'BINARY_OP(+) met is_negative=True op right'],
        ['Dubbele negatie', '-(-a)', 'a'],
        ['Negatie integratie', 'UNARY_OP(-) om node', 'node met is_negative=True'],
        ['FRACTION vereenvoudiging', 'FRACTION(6,2)', 'BINARY_OP(:) want 6 deelbaar door 2'],
        ['POWER recursie', 'POWER met BINARY_OP als base', 'Base wordt genormaliseerd'],
        ['_bracketed bewaren', 'Haakjesgroepen', '_bracketed=True vlag op node'],
        ['_via_subtraction', 'Negatief via aftrekking', '_via_subtraction=True voor MathJSON paden'],
    ]
    story.append(pipeline_table(rows, [4.5*cm, 5*cm, 7*cm]))

    story.append(SP(0.3))

    # ── 4.3 manifold_detector.py ──────────────────────────────────────────────
    story.append(P('4.3  manifold_detector.py', 'h2'))
    story.append(P(
        '<b>Rol:</b> Detecteert commutatieve ketens van 3 of meer operanden die geschikt zijn '
        'voor omzetting naar een MANIFOLD_OP node.', 'body'))
    story.append(P('<b>Werkwijze:</b>', 'h3'))
    for item in [
        'Annoteer elke node met een uniek _node_id via _annotate_node_ids() — ook POWER-nodes.',
        'Doorzoek de boom bottom-up voor aaneengesloten ketens van dezelfde commutieve operator (+, x).',
        'Een keten met 3+ operanden wordt gemarkeerd als kandidaat voor manifold-conversie.',
        '_bracketed nodes zijn altijd atomisch naar buiten — de keten stopt aan de haakjesgrens.',
        'POWER-nodes zijn altijd atomisch — hun base wordt apart onderzocht.',
    ]:
        story.append(P(f'&bull; {item}', 'bullet'))

    story.append(SP(0.3))

    # ── 4.4 manifold_converter.py ─────────────────────────────────────────────
    story.append(P('4.4  manifold_converter.py', 'h2'))
    story.append(P(
        '<b>Rol:</b> Vervangt gedetecteerde commutatieve ketens door MANIFOLD_OP nodes '
        'met een operands-lijst.', 'body'))
    story.append(P(
        'Een MANIFOLD_OP bundelt alle operanden van een keten in één node: '
        '<font name="Courier">1 + 4/3 - 1/2 - 1</font> wordt '
        '<font name="Courier">MANIFOLD_OP(+, [1, 4/3, -1/2, -1])</font>. '
        'Dit maakt de stap-indeling en de DUO-berekening eenvoudiger.', 'body'))

    story.append(SP(0.3))

    # ── 4.5 tak_allocator.py ──────────────────────────────────────────────────
    story.append(P('4.5  tak_allocator.py', 'h2'))
    story.append(P(
        '<b>Rol:</b> Kent horizontale tak-namen toe aan elke node. '
        'De root krijgt altijd tak A. Kinderen krijgen subnamen: A.1, A.2, B, B.1, enzovoort.', 'body'))
    story.append(P('<b>Regels:</b>', 'h3'))
    for item in [
        'Root = altijd TAK A.',
        'Elk kind van een BINARY_OP of MANIFOLD_OP krijgt een eigen tak of erft de ouder-tak.',
        'POWER-nodes geven hun tak door aan de base (exponent is een parameter, geen tak).',
        '_bracketed nodes zijn atomisch — hun interne structuur krijgt geen aparte tak.',
    ]:
        story.append(P(f'&bull; {item}', 'bullet'))

    story.append(SP(0.3))

    # ── 4.6 step_calculator.py ────────────────────────────────────────────────
    story.append(P('4.6  step_calculator.py', 'h2'))
    story.append(P(
        '<b>Rol:</b> Kent verticale stap-nummers toe. Bladeren (externe inputs) krijgen '
        'stap 0. De root krijgt het hoogste stap-nummer. De stap van een node is '
        'gelijk aan de diepte van de deelboom onder hem.', 'body'))
    story.append(P(
        'De top-down toewijzing zorgt dat block IDs als A1, A2, ... overeenkomen met de '
        'volgorde van uitvoering: A1 eerst, dan A2, dan A3 enzovoort.', 'body'))

    story.append(SP(0.3))

    # ── 4.7 ast_visualizer.py ─────────────────────────────────────────────────
    story.append(P('4.7  ast_visualizer.py', 'h2'))
    story.append(P(
        '<b>Rol:</b> Genereert een SVG-boomdiagram van de AST en berekent block IDs. '
        'Dit is de grootste en meest complexe module in de pipeline.', 'body'))
    story.append(P('<b>Kernfuncties:</b>', 'h3'))

    tc = ParagraphStyle('tc', fontSize=8.5, fontName='Courier', textColor=DONKERGRIJS, leading=12)
    tb = ParagraphStyle('tb', fontSize=8.5, fontName='Helvetica', textColor=DONKERGRIJS, leading=12)
    th = ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, leading=12)

    kf_data = [
        [Paragraph('Functie', th), Paragraph('Beschrijving', th)],
        [Paragraph('evaluate(node)', tc), Paragraph('Berekent de numerieke uitkomst als Fraction (exact). Ondersteunt NUMBER, FRACTION, BINARY_OP, MANIFOLD_OP en POWER inclusief negatieve exponenten.', tb)],
        [Paragraph('compute_node_depth(node)', tc), Paragraph('Berekent de maximale diepte van een node (0 = leaf). POWER telt als 1 niveau boven zijn base; de base-diepte telt mee.', tb)],
        [Paragraph('compute_layout(node)', tc), Paragraph('Berekent de x/y-positie van elke node voor de SVG via recursive descent. Geeft een layout-tree terug met x, y, children en node.', tb)],
        [Paragraph('assign_block_ids(layout, max_depth)', tc), Paragraph('Kent block IDs toe (bijv. A1, B3) op basis van stap-nummer en x-positie in de layout. Verwerkt ook POWER.base nodes.', tb)],
        [Paragraph('generate_ast_svg(ast)', tc), Paragraph('Genereert de volledige SVG ElementTree met nodes, verbindingslijnen, stap-lijnen, block ID labels en uitkomsten boven de nodes.', tb)],
        [Paragraph('visualize(expr, path)', tc), Paragraph('Publieke API: doorloopt de volledige pipeline (parser → normalizer → detector → converter) en schrijft de SVG naar het opgegeven pad.', tb)],
    ]

    kf_table = Table(kf_data, colWidths=[5.5*cm, 11*cm])
    kf_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLAUW),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRIJS]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(kf_table)
    story.append(SP(0.3))
    story.append(P(
        '<b>Block ID formaat:</b> Een block ID bestaat uit een taksymbool gevolgd door het '
        'stap-nummer. Voorbeelden: A1 (tak A, stap 1), B3 (tak B, stap 3), C2 (tak C, stap 2). '
        'De tak-letter geeft de horizontale positie aan; het stap-nummer de verticale volgorde.', 'body'))

    story.append(SP(0.3))

    # ── 4.8 ast_to_mathjson.py ────────────────────────────────────────────────
    story.append(P('4.8  ast_to_mathjson.py', 'h2'))
    story.append(P(
        '<b>Rol:</b> Serialiseert de AST naar MathJSON formaat voor de studenttool. '
        'MathJSON is een gestandaardiseerd formaat voor wiskundige expressies als JSON.', 'body'))
    story.append(P('<b>MathJSON mapping:</b>', 'h3'))

    tm = ParagraphStyle('tm', fontSize=8.5, fontName='Courier', textColor=DONKERGRIJS, leading=12)
    tb3 = ParagraphStyle('tb3', fontSize=8.5, fontName='Helvetica', textColor=DONKERGRIJS, leading=12)
    th3 = ParagraphStyle('th3', fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, leading=12)

    mj_data = [
        [Paragraph('Intern type', th3), Paragraph('MathJSON', th3), Paragraph('Voorbeeld', th3)],
        [Paragraph('NUMBER(5)', tm), Paragraph('5', tb3), Paragraph('5', tb3)],
        [Paragraph('NUMBER(5) is_negative', tm), Paragraph('-5', tb3), Paragraph('-5', tb3)],
        [Paragraph('FRACTION(3,5)', tm), Paragraph('["Rational", 3, 5]', tm), Paragraph('Breuk 3/5', tb3)],
        [Paragraph('BINARY_OP(+)', tm), Paragraph('["Add", left, right]', tm), Paragraph('Optelling', tb3)],
        [Paragraph('BINARY_OP(x)', tm), Paragraph('["Multiply", left, right]', tm), Paragraph('Vermenigvuldiging', tb3)],
        [Paragraph('BINARY_OP(:)', tm), Paragraph('["Divide", left, right]', tm), Paragraph('Deling als rekenstap', tb3)],
        [Paragraph('MANIFOLD_OP(+)', tm), Paragraph('["Add", op1, op2, op3, ...]', tm), Paragraph('Commutatieve keten optelling', tb3)],
        [Paragraph('POWER', tm), Paragraph('["Power", base, exp]', tm), Paragraph('Machtsverheffing', tb3)],
        [Paragraph('is_negative=True', tm), Paragraph('["Negate", inner]', tm), Paragraph('Negatieve waarde of operatie', tb3)],
    ]

    mj_table = Table(mj_data, colWidths=[4.5*cm, 5.5*cm, 6.5*cm])
    mj_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLAUW),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRIJS]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('WORDWRAP', (0,0), (-1,-1), True),
    ]))
    story.append(mj_table)

    story.append(SP(0.2))
    story.append(P(
        'Naast de <font name="Courier">tree</font> genereert deze module ook de '
        '<font name="Courier">node_map</font>: een array die elk pad in de MathJSON-boom '
        'koppelt aan het bijbehorende block ID. Dit stelt de studenttool in staat om '
        'een specifiek getal of operator in de boom te markeren.', 'body'))

    story.append(SP(0.3))

    # ── 4.9 json_generator_v2.py ──────────────────────────────────────────────
    story.append(P('4.9  json_generator_v2.py', 'h2'))
    story.append(P(
        '<b>Rol:</b> Genereert de JSON-structuur met steps, mathblocks, inputs en '
        'gereduceerde expressies. Dit is een alternatieve JSON-generator die naast '
        'json_exporter.py bestaat.', 'body'))
    story.append(P('<b>Sleutelvelden in de output:</b>', 'h3'))
    for item in [
        'steps[0].values — externe inputs met type, waarde en latex-veld',
        'steps[0].reduced_expression_latex — LaTeX string van alle inputs',
        'mathBlocks[].output — numerieke uitkomst als string (bijv. "-4/5")',
        'mathBlocks[].output_latex — LaTeX versie (bijv. "-\\frac{4}{5}")',
        'steps[N].reduced_expression_latex — LaTeX van de tussenuitkomsten',
        'metadata.expressie.ast — MathJSON tree + node_map (via ast_to_mathjson)',
    ]:
        story.append(P(f'&bull; {item}', 'bullet'))

    story.append(SP(0.3))

    # ── 4.10 json_exporter.py ─────────────────────────────────────────────────
    story.append(P('4.10  json_exporter.py', 'h2'))
    story.append(P(
        '<b>Rol:</b> De primaire JSON-exporteur. Genereert de volledige ForMath JSON '
        'en slaat deze op in ~/Desktop/JSON_files_ForMath/ met een automatisch gegenereerd ID '
        '(formaat: YYYYMMDD_NNN).', 'body'))
    story.append(P('<b>Secties in de gegenereerde JSON:</b>', 'h3'))
    rows = [
        ['Sectie', 'Beschrijving'],
        ['metadata', 'ID, auteur, expressie (tekst, latex_display, MathML, AST), bewerkingsaantallen'],
        ['mathblocks', 'Alle rekenstappen gesorteerd op stap en volgorde, met inputs, output en operatie-info'],
        ['externe_inputs', 'Alle externe invoerwaarden met verwijzing naar de mathblocks die ze gebruiken'],
        ['steps', 'Per stap een lijst van mathblock IDs'],
        ['duo_verzameling', 'Per stap: hoog (verplicht) en laag (optioneel uitvoerbaar) mathblocks, plus expressie-rendering'],
    ]
    story.append(pipeline_table(rows, [4.5*cm, 12*cm]))

    story.append(SP(0.3))

    # ── 4.11 server.py ────────────────────────────────────────────────────────
    story.append(P('4.11  server.py', 'h2'))
    story.append(P(
        '<b>Rol:</b> Python HTTP-server (geen Flask/FastAPI, maar de ingebouwde '
        '<font name="Courier">http.server</font> module). Serveert de HTML-pagina en '
        'verwerkt API-verzoeken van de browser.', 'body'))
    story.append(P('<b>Endpoints:</b>', 'h3'))
    rows = [
        ['Endpoint', 'Methode', 'Beschrijving'],
        ['/', 'GET', 'Serveert index.html'],
        ['/api/process', 'POST', 'Verwerkt expressie: LaTeX → expressie → AST → SVG. Geeft SVG + AST + latex_display terug.'],
        ['/api/export_json', 'POST', 'Verwerkt expressie en slaat JSON + SVG op via json_exporter.py.'],
    ]
    story.append(pipeline_table(rows, [4*cm, 2.5*cm, 10*cm]))

    story.append(SP(0.2))
    story.append(P('<b>Sleutelfuncties:</b>', 'h3'))

    tc2 = ParagraphStyle('tc2', fontSize=8.5, fontName='Courier', textColor=DONKERGRIJS, leading=12)
    tb2 = ParagraphStyle('tb2', fontSize=8.5, fontName='Helvetica', textColor=DONKERGRIJS, leading=12)
    th2 = ParagraphStyle('th2', fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, leading=12)

    sf_data = [
        [Paragraph('Functie', th2), Paragraph('Beschrijving', th2)],
        [Paragraph('latex_to_expression(latex)', tc2), Paragraph('Converteert MathLive LaTeX naar ascii-math string. Verwerkt \\frac, \\times, \\div, machten (^{}) en alle haakjesnotaties (\\left(, \\right), \\lbrack enzovoort).', tb2)],
        [Paragraph('_replace_frac(s)', tc2), Paragraph('Vervangt \\frac{a}{b} iteratief: getal/getal → a/b (FRACTION), complex/getal → (a)/b, getal/complex → a/(b), complex/complex → (a)/(b). Ondersteunt geneste fracties.', tb2)],
        [Paragraph('_node_to_latex(node)', tc2), Paragraph('Converteert een interne AST-node naar LaTeX display string. FRACTION → \\frac{t}{n}. BINARY_OP(:) waarbij beide kinderen _bracketed=True → \\frac{teller}{noemer}. Gewone deling → :.', tb2)],
        [Paragraph('ast_to_latex_display(ast)', tc2), Paragraph('Publieke API: genereert de volledige latex_display string vanuit de geconverteerde AST. Wordt aangeroepen door beide API-endpoints na de pipeline.', tb2)],
    ]

    sf_table = Table(sf_data, colWidths=[5.5*cm, 11*cm])
    sf_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLAUW),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRIJS]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(sf_table)

    story.append(SP(0.3))

    # ── 4.12 index.html ───────────────────────────────────────────────────────
    story.append(P('4.12  index.html', 'h2'))
    story.append(P(
        '<b>Rol:</b> De browserinterface voor de docent. Bevat het MathLive-invoerveld, '
        'knoppen voor verwerking en JSON-export, en het SVG-resultaatgebied.', 'body'))
    story.append(P('<b>Functionaliteit:</b>', 'h3'))
    for item in [
        'MathLive-invoerveld voor wiskundige expressies met wiskundige notatie.',
        'Tekstveld-modus (knop ✏️ Tekst): gewoon tekstveld voor plakken van expressies.',
        'OK-knop: verwerkt de expressie, toont SVG en de latex_display string.',
        'JSON-knop: exporteert het JSON-bestand en de SVG naar Desktop/JSON_files_ForMath/.',
        'Zoom-controls op het SVG-resultaat (inzoomen, uitzoomen, passend maken).',
        'Drag-to-pan op het SVG-resultaat.',
        'Balkje onder invoerveld toont de latex_display string die in de JSON terechtkomt.',
    ]:
        story.append(P(f'&bull; {item}', 'bullet'))

    story.append(P(
        '<b>getExpression():</b> haalt de ascii-math string op via '
        '<font name="Courier">mathField.getValue(\'ascii-math\')</font> of het tekstveld. '
        'De server genereert de latex_display zelf vanuit de AST — de browser hoeft '
        'geen LaTeX door te sturen.', 'body'))

    story.append(SP(0.5))

    # ══════════════════════════════════════════════════════════════════════════
    # 5. JSON OUTPUTFORMAAT
    # ══════════════════════════════════════════════════════════════════════════
    story.append(P('5. JSON Outputformaat', 'h1'))
    story.append(HR())

    story.append(P(
        'Hieronder de topstructuur van een gegenereerd JSON-bestand '
        '(opgave_YYYYMMDD_NNN.json):', 'body'))

    story.append(SP(0.2))

    json_ex = '''{
  "metadata": {
    "id": "20260325_001",
    "auteur": "H.N.Lensing",
    "expressie": {
      "tekst": "2-3/5-33/15",
      "latex_display": "2-\\frac{3}{5}-\\frac{33}{15}",
      "mathml": "...",
      "ast": {
        "tree": ["Add", 2, ["Negate",["Rational",3,5]], ["Negate",["Rational",33,15]]],
        "node_map": [
          { "path": [], "mathblock_id": "A1", "type": "operation" },
          { "path": [0], "mathblock_id": "A1", "type": "input", "waarde": "2" }
        ]
      }
    },
    "aantal_mathblocks": 1,
    "bewerkingen": { "optelling": 1, "deling": 0, ... },
    "aantal_steps": 1
  },
  "mathblocks": [
    {
      "id": "A1",
      "step": 1,
      "operatie": { "symbool": "+", "beschrijving": "optelling" },
      "input": [
        { "type": "extern", "waarde": "2" },
        { "type": "extern", "waarde": "-3/5" }
      ],
      "output": "-4/5"
    }
  ],
  "externe_inputs": [ { "waarde": "2", "mathblock_ids": ["A1"] } ],
  "steps": [ { "step": 1, "mathblocks": ["A1"] } ],
  "duo_verzameling": [
    {
      "step": 1,
      "hoog": ["A1"],
      "laag": [],
      "input_expressie": "2-3/5-33/15",
      "output_high": "-4/5"
    }
  ]
}'''

    story.append(colored_box(
        f'<font name="Courier" size="8">{json_ex.replace(chr(10), "<br/>").replace(" ", "&nbsp;")}</font>',
        bg=GRIJS
    ))

    story.append(SP(0.4))
    story.append(P('MathJSON AST velden', 'h2'))

    ta = ParagraphStyle('ta', fontSize=8.5, fontName='Courier', textColor=DONKERGRIJS, leading=12)
    tb4 = ParagraphStyle('tb4', fontSize=8.5, fontName='Helvetica', textColor=DONKERGRIJS, leading=12)
    th4 = ParagraphStyle('th4', fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, leading=12)
    tb4b = ParagraphStyle('tb4b', fontSize=8.5, fontName='Helvetica-Bold', textColor=DONKERGRIJS, leading=12)

    ast_data = [
        [Paragraph('Veld', th4), Paragraph('Type', th4), Paragraph('Beschrijving', th4)],
        [Paragraph('ast.tree', ta), Paragraph('Array', tb4), Paragraph('Volledige expressie als MathJSON boom. Bevat Add, Negate, Multiply, Divide, Rational en Power als geneste arrays.', tb4)],
        [Paragraph('ast.node_map', ta), Paragraph('Array', tb4), Paragraph('Koppelt elk pad in de boom aan een block ID. Per entry: path (int[]), mathblock_id (string), type ("operation" of "input"), en optioneel waarde.', tb4)],
        [Paragraph('node_map[].path', ta), Paragraph('int[]', tb4), Paragraph('Pad in de MathJSON boom als array van indices. Bijv. [1, 0, 2] = tweede element van root, eerste kind, derde element.', tb4)],
        [Paragraph('node_map[].type', ta), Paragraph('string', tb4), Paragraph('"operation" voor operatie-nodes (mathblocks). "input" voor externe invoerwaarden (getallen en breuken).', tb4)],
        [Paragraph('node_map[].waarde', ta), Paragraph('string', tb4), Paragraph('Leesbare waarde voor input-entries. Bijv. "2", "-3/5", "-33/15". Alleen aanwezig bij type = "input".', tb4)],
        [Paragraph('node_map[].waarde_latex', ta), Paragraph('string', tb4), Paragraph('LaTeX versie van de waarde. Bijv. "-\\\\frac{3}{5}". Alleen aanwezig bij type = "input".', tb4)],
    ]

    ast_table = Table(ast_data, colWidths=[3.5*cm, 2*cm, 11*cm])
    ast_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLAUW),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRIJS]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(ast_table)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 6. GROOTSTE PROBLEMEN EN OPLOSSINGEN
    # ══════════════════════════════════════════════════════════════════════════
    story.append(P('6. Grootste Problemen en Oplossingen', 'h1'))
    story.append(HR())

    problemen = [
        (
            'Breuk vs. deling: dezelfde notatie, verschillende betekenis',
            'ascii-math gebruikt "/" voor zowel breuken (3/5) als deling (10:2). '
            'De lexer moest onderscheid maken op basis van context: is de teller een '
            'veelvoud van de noemer, dan is het een rekenstap (:), anders een breuk (FRACTION). '
            'MathLive compliceerde dit verder door breuken als (3)/(5) te sturen — met haakjes '
            'om teller en noemer. Dit leidde tot foutieve parsing als twee delingstekens.',
            'Pre-processing stap toegevoegd in _preprocess_expression(): '
            '(getal)/(getal) wordt omgezet naar getal/getal vóór het parsen. '
            'In de normalizer: FRACTION(p,q) waarbij p deelbaar is door q wordt BINARY_OP(:).'
        ),
        (
            'POWER nodes: ontbrekende ondersteuning door de hele pipeline',
            'De parser herkende al ^ als POWER, maar alle volgende modules (normalizer, '
            'detector, converter, tak_allocator, step_calculator, json_generator) hadden '
            'geen code voor POWER-nodes. Dit leidde tot KeyError, None-outputs en '
            'ontbrekende block IDs.',
            'Elke module systematisch uitgebreid: POWER wordt recursief verwerkt in base '
            'en exponent, POWER is atomisch in manifold-ketens (kan niet worden opengebroken), '
            '_annotate_node_ids() bezoekt ook POWER.base en POWER.exponent.'
        ),
        (
            'POWER met complexe base: block ID ontbreekt',
            'Wanneer de base van een POWER een operatie-node is (bijv. (12-9)^3), '
            'kregen de base-nodes geen block ID. Dit was zichtbaar in de SVG als lege labels. '
            'De oorzaak: collect_nodes() en assign_steps() in ast_visualizer liepen niet '
            'via POWER.base.',
            'collect_nodes() en assign_steps() uitgebreid om ook POWER.base te bezoeken. '
            'Top-down stap-toewijzing zorgt dat (12-9) stap 1 krijgt, POWER(^3) stap 2.'
        ),
        (
            'Manifold-detectie crasht bij POWER: KeyError _node_id',
            'De manifold-detector annoteerde nodes met _node_id via _annotate_node_ids(), '
            'maar bezocht POWER.base en POWER.exponent niet. Bij een expressie als '
            '(2-3/5-33/15)^2 crashte de detectie met KeyError: \'_node_id\'.',
            '_annotate_node_ids() uitgebreid: elif node[\'type\'] == \'POWER\': '
            'annoteer base en exponent recursief.'
        ),
        (
            'Deling door breuk: (3+4):(5/27) werd verkeerd geparsed',
            'Een deling door een breuk, zoals a:(5/27), werd als twee opeenvolgende '
            'delingen geparsed: a:5:27. De pre-processing herkende het patroon niet '
            'omdat de stap-2 regel alleen werkte voor getallen, niet voor expressies.',
            'Pre-processing stap 2 uitgebreid: :(expr)/(expr) → :(expr/expr). '
            'Hierdoor wordt (3+4):(5)/(27) correct als (3+4):(5/27) geparsed.'
        ),
        (
            'LaTeX display: breuken als : in de JSON',
            'De latex_display string in de JSON toonde ":" voor breuken als (3+4)/(5*2) '
            'in plaats van \\frac{3+4}{5*2}. De oorzaak: de AST maakt intern geen '
            'onderscheid tussen een gewone deling en een breuk met complexe teller/noemer. '
            'Bovendien genereerde de oude server de latex_display niet zelf, maar wachtte '
            'op de browser — die de ascii-math string terugstuurde.',
            'Twee fixes: (1) De server genereert latex_display nu zelf vanuit de AST via '
            'ast_to_latex_display(). (2) In _node_to_latex(): een BINARY_OP(:) waarbij '
            'BEIDE kinderen _bracketed=True zijn, wordt weergegeven als \\frac{}{}. '
            'De _bracketed-vlag markeert nodes die oorspronkelijk tussen haakjes stonden — '
            'precies het patroon dat _replace_frac() genereert voor \\frac{complex}{complex}.'
        ),
        (
            'MathBlock zonder tak: "1&unknown" in de JSON',
            'MANIFOLD_OP-nodes die de base zijn van een POWER-node kregen geen tak-naam '
            'toegewezen. Dit leidde tot "1&unknown" als block ID in de JSON.',
            'Openstaand punt — de berekeningen kloppen wel, de tak-allocator kent de '
            'MANIFOLD-base van POWER nog geen tak toe. Dit heeft lage prioriteit omdat '
            'het de werking niet beïnvloedt.'
        ),
        (
            'Invoerveld geblokkeerd na OK-klik',
            'Na het klikken op OK was het MathLive-invoerveld geblokkeerd: de gebruiker '
            'kon er niet meer in typen. Oorzaak: de SVG-container had position:absolute '
            'en nam de volledige hoogte in, inclusief het invoerveld eronder.',
            'max-height: calc(100vh - 220px) toegevoegd aan #svg-wrapper zodat de '
            'SVG-container nooit over het invoerveld heen groeit. Tevens focus-herstel '
            'na verwerking via setTimeout().'
        ),
    ]

    for i, (titel, probleem, oplossing) in enumerate(problemen, 1):
        story.append(KeepTogether([
            P(f'6.{i}  {titel}', 'h2'),
            colored_box(f'<b>Probleem:</b> {probleem}', bg=LICHTROOD),
            SP(0.15),
            colored_box(f'<b>Oplossing:</b> {oplossing}', bg=LICHTGROEN),
            SP(0.3),
        ]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 7. VERKLARENDE WOORDENLIJST
    # ══════════════════════════════════════════════════════════════════════════
    story.append(P('7. Verklarende Woordenlijst', 'h1'))
    story.append(HR())

    termen = [
        ('AST', 'Abstract Syntax Tree. Een geneste boomstructuur die de syntactische '
         'opbouw van een wiskundige expressie representeert. Elke node is een Python dict '
         'met minimaal een "type"-sleutel.'),
        ('ascii-math', 'Een tekstnotatie voor wiskundige expressies die leesbaar is '
         'voor zowel mens als machine. Gebruikt gewone tekens: +, -, *, :, ^, /. '
         'MathLive gebruikt ascii-math als tussenformaat.'),
        ('Block ID', 'Een unieke identificator voor een mathblock, samengesteld uit '
         'taksymbool + stap-nummer. Bijv. A1 = tak A, stap 1. Zichtbaar in de SVG en '
         'gebruikt als referentie in de JSON.'),
        ('_bracketed', 'Een vlag op een AST-node die aangeeft dat de node oorspronkelijk '
         'tussen haakjes stond in de expressie. Haakjesgroepen zijn atomisch: ze worden '
         'niet opengebroken door manifold-detectie.'),
        ('DUO', 'Due Operations. Het begrip dat beschrijft welke mathblocks in een '
         'bepaalde stap kunnen worden uitgevoerd. Hoog: verplicht in deze stap. '
         'Laag: optioneel uitvoerbaar, afhankelijk van de hoog-blokken.'),
        ('Externe input', 'Een waarde in de expressie die geen eigen berekening vereist: '
         'een getal (NUMBER) of een echte breuk (FRACTION). Wordt weergegeven als een '
         'los invoerblokje in de SVG.'),
        ('FRACTION', 'Een intern AST-node type voor een echte breuk p/q waarbij p niet '
         'deelbaar is door q. Bijv. 3/5, 33/15. Wordt weergegeven als \frac{3}{5} in LaTeX.'),
        ('is_negative', 'Een boolean vlag op een AST-node die aangeeft dat de waarde '
         'negatief is. Vervangt het UNARY_OP(-) node-type na normalisatie.'),
        ('LaTeX', 'Opmaaktaal voor wiskundige notatie. Gebruikt door de studenttool om '
         'expressies correct te renderen. Bijv. \frac{3}{5} voor een breuk.'),
        ('Manifold', 'Een MANIFOLD_OP node: een commutatieve keten van 3 of meer '
         'operanden met dezelfde operator (+  of x). Bijv. 1 + 2 + 3 + 4 wordt '
         'MANIFOLD_OP(+, [1, 2, 3, 4]).'),
        ('MathJSON', 'Een gestandaardiseerd JSON-formaat voor wiskundige expressies. '
         'Gebruikt geneste arrays: ["Add", 1, 2] = 1+2, ["Rational", 3, 5] = 3/5.'),
        ('MathLive', 'Een JavaScript-bibliotheek voor wiskundige invoer in de browser. '
         'Biedt een interactief invoerveld dat LaTeX en ascii-math kan produceren.'),
        ('Mathblock', 'Een rekenstap in de expressie: een BINARY_OP, MANIFOLD_OP of '
         'POWER node met een of meer inputs en een output. Krijgt een block ID.'),
        ('node_map', 'Een array in de JSON die elk pad in de MathJSON-boom koppelt aan '
         'een block ID. Stelt de studenttool in staat nodes in de boom te markeren.'),
        ('POWER', 'Een intern AST-node type voor machtsverheffing. Heeft een base en '
         'een exponent. De exponent is altijd een getal (parameter), de base kan een '
         'complexe expressie zijn.'),
        ('Stap', 'Een verticaal niveau in de boomvisualisatie. Stap 0 = externe inputs '
         '(bladeren). Stap 1 = eerste rekenstappen. Hogere stappen = dieper in de boom. '
         'De root heeft het hoogste stap-nummer.'),
        ('Tak', 'Een horizontaal spoor in de boomvisualisatie. De root heeft tak A. '
         'Subbomen krijgen namen als A.1, A.2, B, B.1, enzovoort.'),
        ('_via_subtraction', 'Een vlag die aangeeft dat een negatieve waarde is ontstaan '
         'door aftrekking (a-b → a+(-b)). Beïnvloedt het pad in de MathJSON node_map.'),
    ]

    for term, definitie in termen:
        story.append(P(term, 'term'))
        story.append(P(definitie, 'definition'))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 8. GEBRUIKTE AFKORTINGEN
    # ══════════════════════════════════════════════════════════════════════════
    story.append(P('8. Gebruikte Afkortingen', 'h1'))
    story.append(HR())

    afkortingen = [
        ('AST', 'Abstract Syntax Tree'),
        ('API', 'Application Programming Interface'),
        ('CSS', 'Cascading Style Sheets'),
        ('DOM', 'Document Object Model'),
        ('DUO', 'Due Operations'),
        ('HTML', 'HyperText Markup Language'),
        ('HTTP', 'HyperText Transfer Protocol'),
        ('ID', 'Identifier'),
        ('JSON', 'JavaScript Object Notation'),
        ('LaTeX', 'Lamport TeX — opmaaktaal voor wetenschappelijke documenten'),
        ('MathJSON', 'Mathematical JSON — gestandaardiseerd formaat voor wiskunde'),
        ('MathLive', 'JavaScript bibliotheek voor wiskundige invoer'),
        ('MathML', 'Mathematical Markup Language'),
        ('POST', 'HTTP POST-methode'),
        ('SVG', 'Scalable Vector Graphics'),
        ('TCP', 'Transmission Control Protocol'),
        ('URL', 'Uniform Resource Locator'),
    ]

    rows = [['Afkorting', 'Voluit']] + afkortingen
    story.append(pipeline_table(rows, [4*cm, 12.5*cm]))

    story.append(SP(1))
    story.append(HR())
    story.append(P(
        '<i>Einde van de documentatie. ForMath Pipeline — versie 1.0, maart 2026.</i>',
        'caption'))

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
    print(f"PDF gegenereerd: {path}")

build_doc()
