# -*- coding: utf-8 -*-
"""Mailing « tarifs pierres 2027 » aux clients pro, avec grille personnalisée (15/10/2026, demande Xavier).
Sources : le tableau de validation (feuille « Validation », colonnes PRO 1er nov. / PRO 1er janv.) et les onglets clients de
v3.xlsx (prix négociés 2026, maintenus). Cible : clients pro (liste Pro 2026 ou liste propre) ayant acheté de la pierre
en 2025-2026 chez SARL Maquignon, avec e-mail.
   python mailing_tarifs_pro.py exemples              -> 3 PDF d'exemple (pro standard, Cazy, Lefèvre 56) dans Desktop/Maquignon/Mailing_tarifs_2027/
   python mailing_tarifs_pro.py pdfs                  -> un PDF par client cible + liste_cible.xlsx (rien n'est envoyé)
   python mailing_tarifs_pro.py test <adresse>        -> envoie UN e-mail de test (PDF du premier client d'exemple) à l'adresse donnée, via Odoo
   python mailing_tarifs_pro.py envoi                 -> envoie à tous les clients cibles (message dans le fil de chaque client + e-mail) ; demande « OUI »
Identifiants attendus dans l'environnement : ODOO_USER, ODOO_PWD."""
import os, sys, re, json, base64, xmlrpc.client
from collections import defaultdict
from datetime import date
sys.stdout.reconfigure(encoding='utf-8')
from openpyxl import load_workbook, Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

ICI = os.path.dirname(os.path.abspath(__file__))
MODE = (sys.argv[1] if len(sys.argv) > 1 else 'exemples').lower()
VALIDATION = r"C:\Users\xavfe\Desktop\Maquignon\Tarifs_pierres_2027_validation_2026-10-15.xlsx"
DOSSIER = r"C:\Users\xavfe\Desktop\Maquignon\Mailing_tarifs_2027"
os.makedirs(DOSSIER, exist_ok=True)
SOC = 1
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common').authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object')
CTX = {'allowed_company_ids': [SOC], 'company_id': SOC, 'active_test': False}
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context=dict(CTX, **k.pop('context', {}))))
one = lambda v: v[0] if isinstance(v, list) else v
nombre = lambda v: v if isinstance(v, (int, float)) else None

# ---------------------------------------------------------------- 1. grille validée
wv = load_workbook(VALIDATION, data_only=True)['Validation']
titres = {str(wv.cell(4, c).value or '').strip(): c for c in range(1, wv.max_column + 1)}
col = lambda deb: next(c for t, c in titres.items() if t.startswith(deb))
cF, cG, cV = col('PRO 1er nov'), col('PRO 1er janv'), col('Validé')
pierres, cat = [], None
for r in range(5, wv.max_row + 1):
    code, nom, unite = (wv.cell(r, c).value for c in (1, 2, 3))
    if nom and not unite and not code:
        continue
    if not nom and code and not unite:          # ligne de catégorie (fusionnée)
        cat = code; continue
    if not nom or not unite:
        continue
    v = wv.cell(r, cV).value
    if isinstance(v, str) and v.strip().lower().startswith('n'):
        continue
    pierres.append({'code': code or '', 'nom': nom, 'cat': cat or '', 'unite': unite, 'v1': nombre(wv.cell(r, cF).value), 'v2': nombre(wv.cell(r, cG).value)})
pierres = [q for q in pierres if q['v1'] and q['v2']]
print('grille : %d pierres validées' % len(pierres))

# ---------------------------------------------------------------- 2. prix négociés (onglets clients de v3.xlsx, prix 2026 maintenus)
wb = load_workbook(os.path.join(ICI, 'v3.xlsx'), data_only=False)
nom_net = lambda s: re.sub(r'^\[[^\]]+\] ', '', s).replace(' (archivé)', '').strip()
negocies = {}      # nom d'onglet -> {nom_net(article): prix 2026}
for s in wb.sheetnames:
    if s in ('Grille 2027', 'Grille 2027 (2)', 'Méthode', 'Remarques', 'Remises', 'Lisez-moi'):
        continue
    ws = wb[s]; d = {}
    for r in range(2, ws.max_row + 1):
        a = ws.cell(r, 1).value; p26 = nombre(ws.cell(r, 4).value)
        if isinstance(a, str) and not a.startswith('CA 2026') and p26:
            d[nom_net(a)] = round(p26, 2)
    if d:
        negocies[s.strip()] = d


def partenaire_onglet(onglet):
    c = x('res.partner', 'search_read', [['name', '=ilike', onglet + '%'], ['is_company', '=', True]], fields=['name'], limit=5)
    if not c:
        c = x('res.partner', 'search_read', [['name', 'ilike', onglet[:20]], ['parent_id', '=', False]], fields=['name'], limit=5)
    if len(c) > 1:
        c = sorted(c, key=lambda pp: -x('account.move', 'search_count', [['partner_id', 'child_of', pp['id']], ['move_type', '=', 'out_invoice'], ['state', '=', 'posted'], ['invoice_date', '>=', '2026-01-01']]))[:1]
    return c[0]['id'] if c else None


nego_par_id = {}
for onglet, d in negocies.items():
    pid = partenaire_onglet(onglet)
    if pid:
        nego_par_id[pid] = d
print('prix négociés : %d clients (%s)' % (len(nego_par_id), ', '.join(o[:22] for o in negocies)))

# ---------------------------------------------------------------- 3. cible
cats = [c['id'] for c in x('product.category', 'search_read', [['complete_name', 'ilike', 'pierre']], fields=['id'])]
g = x('account.move.line', 'read_group', [['move_id.move_type', '=', 'out_invoice'], ['move_id.state', '=', 'posted'], ['move_id.invoice_date', '>=', '2025-01-01'], ['company_id', '=', SOC], ['product_id.categ_id', 'in', cats]], ['price_subtotal:sum'], ['partner_id'], lazy=False)
cp_de = {q['id']: q['commercial_partner_id'][0] for q in x('res.partner', 'read', [r['partner_id'][0] for r in g if r['partner_id']], ['commercial_partner_id'])}
ca = defaultdict(float)
for r in g:
    if r['partner_id']:
        ca[cp_de[r['partner_id'][0]]] += r['price_subtotal']
cibles = []
for q in x('res.partner', 'read', list(ca), ['name', 'email', 'specific_property_product_pricelist', 'lang']):
    l = q['specific_property_product_pricelist'] and q['specific_property_product_pricelist'][0]
    if l and l != 302 and q['email']:
        cibles.append({'id': q['id'], 'nom': q['name'], 'email': q['email'], 'liste': q['specific_property_product_pricelist'][1], 'ca': round(ca[q['id']]), 'nego': nego_par_id.get(q['id'], {})})
cibles.sort(key=lambda c: -c['ca'])
print('cible : %d clients pro acheteurs de pierre avec e-mail (CA pierre 2025-2026 %.0f €)' % (len(cibles), sum(c['ca'] for c in cibles)))

# ---------------------------------------------------------------- 4. PDF personnalisé
INK = colors.HexColor('#0f172a'); GREY = colors.HexColor('#475569'); BLUE = colors.HexColor('#1d4ed8'); LIGHT = colors.HexColor('#eef2ff'); LINE = colors.HexColor('#cbd5e1'); NEGO = colors.HexColor('#fff4e0')
H1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=INK, spaceAfter=2)
P = ParagraphStyle('p', fontName='Helvetica', fontSize=9.6, leading=13, textColor=INK)
SMALL = ParagraphStyle('s', parent=P, fontSize=8, leading=10.5, textColor=GREY)
CELL = ParagraphStyle('c', parent=P, fontSize=8.8, leading=11)
CELLB = ParagraphStyle('cb', parent=CELL, fontName='Helvetica-Bold')
SOCIETE = x('res.company', 'read', [SOC], ['name', 'street', 'zip', 'city', 'phone', 'email', 'website'])[0]


def fmt(v):
    return ('%s' % (int(v) if float(v).is_integer() else ('%.2f' % v).replace('.', ','))).replace(',00', '')


def pdf_client(c, chemin):
    nego = c['nego']
    doc = SimpleDocTemplate(chemin, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title='Tarifs pierres 2027', author=SOCIETE['name'])
    s = [Paragraph('%s' % SOCIETE['name'], SMALL), Paragraph('Tarifs pierres 2027 : %s' % c['nom'], H1),
         Paragraph('Prix hors taxes, départ carrière, applicables en deux étapes : du <b>1er novembre au 31 décembre 2026</b>, puis à partir du <b>1er janvier 2027</b>. '
                   'Unités : m² pour les pierres d\'épaisseur, m³ pour les massifs, tranches et blocs, tonne pour l\'enrochement. Édité le %s.' % date.today().strftime('%d/%m/%Y'), P), Spacer(1, 4)]
    if nego:
        s.append(Paragraph('Les lignes sur fond orangé sont <b>vos prix négociés</b> : ils sont maintenus tels quels sur les deux périodes.', P)); s.append(Spacer(1, 4))
    tete = ['Pierre', 'Unité', 'Du 1er nov. au 31 déc. 2026', 'À partir du 1er janv. 2027']
    if nego:
        tete.append('Votre prix négocié')
    lignes = [[Paragraph(t, CELLB) for t in tete]]; styles = [('BACKGROUND', (0, 0), (-1, 0), LIGHT), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LINEBELOW', (0, 0), (-1, -1), 0.3, LINE), ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5)]
    cat_cour = None
    for q in pierres:
        if q['cat'] != cat_cour:
            cat_cour = q['cat']; lignes.append([Paragraph('<b>%s</b>' % cat_cour, CELL), '', '', ''] + ([''] if nego else [])); styles.append(('SPAN', (0, len(lignes) - 1), (-1, len(lignes) - 1))); styles.append(('BACKGROUND', (0, len(lignes) - 1), (-1, len(lignes) - 1), colors.HexColor('#f8fafc')))
        pn = nego.get(q['nom'])
        row = [Paragraph(q['nom'], CELL), Paragraph(q['unite'], CELL), Paragraph(fmt(pn) if pn else fmt(q['v1']), CELL), Paragraph(fmt(pn) if pn else fmt(q['v2']), CELL)]
        if nego:
            row.append(Paragraph(('<b>%s</b>' % fmt(pn)) if pn else '', CELL))
            if pn:
                styles.append(('BACKGROUND', (0, len(lignes)), (-1, len(lignes)), NEGO))
        lignes.append(row)
    larg = [86 * mm, 12 * mm, 38 * mm, 38 * mm] if not nego else [72 * mm, 12 * mm, 33 * mm, 33 * mm, 30 * mm]
    t = Table(lignes, colWidths=larg, repeatRows=1); t.setStyle(TableStyle(styles + [('ALIGN', (2, 1), (-1, -1), 'RIGHT')]))
    s.append(t); s.append(Spacer(1, 6))
    s.append(Paragraph('Les autres articles (transport, palettes, sciage, prestations) ne changent pas. Prix valables pour toute commande livrée ou enlevée à compter de la date indiquée. '
                       'Votre contact : %s, %s.' % (SOCIETE['phone'] or '', SOCIETE['email'] or ''), SMALL))
    doc.build(s)


EXEMPLES_IDS = {'cazy': 15721, 'lefevre56': 15891}
if MODE == 'exemples':
    std = next(c for c in cibles if not c['nego'])
    ex = [std] + [c for c in cibles if c['id'] in EXEMPLES_IDS.values()]
    for c in ex:
        f = os.path.join(DOSSIER, 'Exemple_%s.pdf' % re.sub(r'[^A-Za-z0-9]+', '_', c['nom'])[:40])
        pdf_client(c, f); print('exemple :', f, '| négocié :', len(c['nego']), 'lignes', '| CA pierre', c['ca'])
    sys.exit()
if MODE == 'pdfs':
    wb2 = Workbook(); ws2 = wb2.active; ws2.title = 'Cible'; ws2.append(['Client', 'E-mail', 'Liste de prix', 'CA pierre 2025-2026', 'Lignes négociées', 'PDF'])
    for c in cibles:
        f = os.path.join(DOSSIER, 'Tarifs_pierres_2027_%s.pdf' % re.sub(r'[^A-Za-z0-9]+', '_', c['nom'])[:50])
        pdf_client(c, f); c['pdf'] = f; ws2.append([c['nom'], c['email'], c['liste'], c['ca'], len(c['nego']), os.path.basename(f)])
    wb2.save(os.path.join(DOSSIER, 'liste_cible.xlsx')); print('%d PDF dans %s + liste_cible.xlsx' % (len(cibles), DOSSIER)); sys.exit()

SUJET = 'Carrières Maquignon : vos tarifs pierres 2027'
CORPS = """<p>Bonjour,</p>
<p>Vous trouverez ci-joint votre grille de tarifs pierres pour 2027. Elle s'applique en deux étapes : une première du <b>1er novembre au 31 décembre 2026</b>, puis la grille définitive à partir du <b>1er janvier 2027</b>.</p>
<p>{NEGO}Les autres articles (transport, palettes, prestations) ne changent pas. Nos équipes restent à votre disposition pour vos devis et vos chantiers.</p>
<p>Bien cordialement,<br/>SARL Maquignon</p>"""
NEGO_TXT = 'Vos prix négociés sont maintenus tels quels sur les deux périodes ; ils apparaissent sur fond orangé dans la grille. '


def envoyer(c, email_to=None):
    chemin = os.path.join(DOSSIER, 'Tarifs_pierres_2027_%s.pdf' % re.sub(r'[^A-Za-z0-9]+', '_', c['nom'])[:50]); pdf_client(c, chemin)
    att = one(x('ir.attachment', 'create', [{'name': os.path.basename(chemin), 'datas': base64.b64encode(open(chemin, 'rb').read()).decode(), 'res_model': 'res.partner', 'res_id': c['id'], 'mimetype': 'application/pdf'}]))
    corps = CORPS.replace('{NEGO}', NEGO_TXT if c['nego'] else '')
    if email_to:   # test : simple e-mail, rien dans le fil du client
        mid = one(x('mail.mail', 'create', [{'subject': '[TEST] ' + SUJET, 'body_html': corps, 'email_to': email_to, 'attachment_ids': [[6, 0, [att]]], 'model': 'res.partner', 'res_id': c['id']}]))
        x('mail.mail', 'send', [mid]); return mid
    return x('res.partner', 'message_post', [c['id']], subject=SUJET, body=corps, message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[c['id']], attachment_ids=[att])


if MODE == 'test':
    adresse = sys.argv[2]; c = next(c for c in cibles if c['id'] == EXEMPLES_IDS['cazy'])
    print('e-mail de test envoyé à', adresse, ':', envoyer(c, email_to=adresse)); sys.exit()
if MODE == 'envoi':
    print('ENVOI RÉEL à %d clients. Taper OUI pour confirmer :' % len(cibles))
    if input().strip() != 'OUI':
        print('annulé'); sys.exit()
    fait = []
    for c in cibles:
        try:
            envoyer(c); fait.append(c['nom']); print('envoyé :', c['nom'], c['email'])
        except Exception as e:
            print('ERREUR', c['nom'], str(e)[:200])
    json.dump(fait, open(os.path.join(DOSSIER, 'envoyes.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%d envoyés' % len(fait))
