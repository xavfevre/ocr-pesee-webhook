# -*- coding: utf-8 -*-
"""Tableau de bord RELANCES (spreadsheet.dashboard 39, groupe Finance) : reconstruction depuis le paramètre Odoo
`relances.board_data` (JSON écrit par la lecture de la comptabilité Sage : ALL, CATEG, PRODS, INV, SRC).
Porté sur le relais le 21/10/2026 depuis l'action serveur 2139 « RELANCES - Mise a jour du board » (236 lignes de
code Python facturées dans Odoo) ; le calcul est repris tel quel. L'action 2139 devient « Créer un enregistrement »
x_relais_tache nommé relances_board (clé de tâche ci-dessous, suffixe :test = calcul sans écriture)."""
import json

DASHBOARD_ID = 39
PARAM = 'relances.board_data'


def construire(d):
    """d = contenu JSON du paramètre -> (spreadsheet_data JSON, résumé)."""
    ALL = d['ALL']
    CATEG = d['CATEG']
    PRODS = d['PRODS']
    INV = d['INV']
    SRC = d['SRC']
    acc = []
    idx = {}
    for row in ALL:
        code = row[1]
        if code not in idx:
            idx[code] = len(acc)
            acc.append([code, row[0], []])
        acc[idx[code]][2].append(row)
    ROWS = []
    AVOIRS = []
    SOLDES = []
    for code, name, lines in acc:
        deb = sum([l[5] for l in lines])
        cre = sum([l[6] for l in lines])
        due = round(deb - cre, 2)
        if due > 0.05:
            for l in lines:
                ROWS.append([l[0], l[2], l[3], l[4], l[5], l[6]])
        elif due < -0.05:
            AVOIRS.append([name, round(-due, 2)])
        else:
            SOLDES.append([name, round(deb, 2)])
    DOUT_PREFIX = "Cr"
    first = 10
    NROWS = len(ROWS)
    last = first + NROWS - 1
    ncli = len(set([r[0] for r in ROWS]))
    NCLI = ncli + 6
    lastc = first + NCLI - 1
    n1 = last + 2
    a_sect = lastc + 3
    a_hdr = a_sect + 1
    a_first = a_hdr + 1
    a_last = a_first + len(AVOIRS) - 1
    s_sect = a_last + 2
    s_hdr = s_sect + 1
    s_first = s_hdr + 1
    s_last = s_first + len(SOLDES) - 1
    c_sect = s_last + 3
    c_hdr = c_sect + 1
    c_first = c_hdr + 1
    c_last = c_first + len(CATEG) - 1
    c_tot = c_last + 1
    c_note = c_tot + 2
    bi_sect = n1 + 3
    bi_hdr = bi_sect + 1
    bi_first = bi_hdr + 1
    cells = []
    cells.append('"A1":"RELANCES — Suivi des règlements clients"')
    cells.append('"A2":"Source : comptabilité SAGE (%s) · %d clients avec un reste à encaisser · classement alphabétique · le retard se recalcule chaque jour"' % (SRC, ncli))
    cells.append('"A4":"RESTE À ENCAISSER"')
    cells.append('"A5":"=SUM(N%d:N%d)-SUM(O%d:O%d)"' % (first, last, first, last))
    cells.append('"A6":"factures - règlements des comptes à relancer"')
    cells.append('"C4":"FACTURES ÉCHUES"')
    cells.append('"C5":"=SUMIFS(N%d:N%d,Q%d:Q%d,\\">0\\")"' % (first, last, first, last))
    cells.append('"C6":"montant facturé, échéance dépassée"')
    cells.append('"E4":"ÉCHUES DEPUIS + DE 30 J"')
    cells.append('"E5":"=SUMIFS(N%d:N%d,Q%d:Q%d,\\">30\\")"' % (first, last, first, last))
    cells.append('"E6":"relance 2 / mise en demeure"')
    cells.append('"I4":"CLIENTS À RELANCER"')
    cells.append('"I5":"=COUNTIF(A%d:A%d,\\"?*\\")"' % (first, lastc))
    cells.append('"I6":"avec au moins une facture échue"')
    cells.append('"L4":"Reste à encaisser = factures - règlements du compte client (lettrage SAGE). N° de facture, échéance et retard = facture échue la plus ancienne du client, (+n) = autres factures échues. Acomptes seuls, comptes à zéro et ventilation par catégorie en bas à gauche ; export SAGE complet en bas à droite. Mise à jour par lecture directe de la comptabilité Sage."')
    cells.append('"A8":"CLIENTS À RELANCER  ·  échéances dépassées  ·  ordre alphabétique"')
    cells.append('"I8":"DÉTAIL DES ÉCRITURES DES COMPTES À RELANCER  ·  par client puis par date"')
    for addr, lbl in [("A9", "Client"), ("B9", "Facturé"), ("C9", "Réglé / acomptes"), ("D9", "Reste dû"), ("E9", "N° facture échue la + ancienne"), ("F9", "Échéance"), ("G9", "Retard (j)"), ("I9", "Client"), ("J9", "Date écriture"), ("K9", "Échéance"), ("L9", "N° de pièce"), ("M9", "Retard (j)"), ("N9", "Débit"), ("O9", "Crédit"), ("P9", "Solde dû"), ("Q9", "retard num")]:
        cells.append('"%s":"%s"' % (addr, lbl))
    rI = '$I$%d:$I$%d' % (first, last)
    rK = '$K$%d:$K$%d' % (first, last)
    rL = '$L$%d:$L$%d' % (first, last)
    rN = '$N$%d:$N$%d' % (first, last)
    rO = '$O$%d:$O$%d' % (first, last)
    rQ = '$Q$%d:$Q$%d' % (first, last)
    for i in range(1, NCLI + 1):
        r = first + i - 1
        cells.append('"A%d":"=IFERROR(INDEX(UNIQUE(FILTER(%s,%s>0)),%d,1),\\"\\")"' % (r, rI, rQ, i))
        cells.append('"B%d":"=IF(A%d=\\"\\",\\"\\",SUMIFS(%s,%s,A%d))"' % (r, r, rN, rI, r))
        cells.append('"C%d":"=IF(A%d=\\"\\",\\"\\",SUMIFS(%s,%s,A%d))"' % (r, r, rO, rI, r))
        cells.append('"D%d":"=IF(A%d=\\"\\",\\"\\",B%d-C%d)"' % (r, r, r, r))
        cnt = 'COUNTIFS(%s,A%d,%s,\\">0\\")' % (rI, r, rQ)
        cells.append('"E%d":"=IF(A%d=\\"\\",\\"\\",IFERROR(INDEX(FILTER(%s,(%s=A%d)*(%s=F%d)*(%s>0)),1,1),\\"\\")&IF(%s>1,\\" (+\\"&(%s-1)&\\")\\",\\"\\"))"' % (r, r, rL, rI, r, rK, r, rN, cnt, cnt))
        cells.append('"F%d":"=IF(A%d=\\"\\",\\"\\",MINIFS(%s,%s,A%d,%s,\\">0\\"))"' % (r, r, rK, rI, r, rQ))
        cells.append('"G%d":"=IF(OR(F%d=\\"\\",F%d=0),\\"\\",TODAY()-F%d)"' % (r, r, r, r))
    for i in range(NROWS):
        r = first + i
        nm, d1, d2, pc, db, cr = ROWS[i]
        cells.append('"I%d":"%s"' % (r, nm))
        cells.append('"J%d":"%d"' % (r, d1))
        if d2:
            cells.append('"K%d":"%d"' % (r, d2))
        cells.append('"L%d":"%s"' % (r, pc))
        cells.append('"M%d":"=IF(OR(K%d=\\"\\",N%d=0),\\"\\",TODAY()-K%d)"' % (r, r, r, r))
        cells.append('"N%d":"%s"' % (r, db))
        cells.append('"O%d":"%s"' % (r, cr))
        cells.append('"P%d":"=N%d-O%d"' % (r, r, r))
        cells.append('"Q%d":"=IF(M%d=\\"\\",0,M%d)"' % (r, r, r))
    cells.append('"I%d":"Source : comptabilité Sage 100, base MAQUIGNON (%s), comptes clients non lettrés. Retard = aujourd\'hui - échéance, calculé sur les lignes de facture ; négatif = pas encore échue. Solde dû = débit - crédit."' % (n1, SRC))
    cells.append('"A%d":"ACOMPTES, TROP-PERÇUS ET AVOIRS  ·  rien à relancer"' % a_sect)
    cells.append('"A%d":"Client"' % a_hdr)
    cells.append('"B%d":"En faveur du client"' % a_hdr)
    for i in range(len(AVOIRS)):
        r = a_first + i
        cells.append('"A%d":"%s"' % (r, AVOIRS[i][0]))
        cells.append('"B%d":"%s"' % (r, AVOIRS[i][1]))
    cells.append('"A%d":"COMPTES À ZÉRO NON LETTRÉS  ·  à lettrer en comptabilité"' % s_sect)
    cells.append('"A%d":"Client"' % s_hdr)
    cells.append('"B%d":"Montant à lettrer"' % s_hdr)
    for i in range(len(SOLDES)):
        r = s_first + i
        cells.append('"A%d":"%s"' % (r, SOLDES[i][0]))
        cells.append('"B%d":"%s"' % (r, SOLDES[i][1]))
    cells.append('"A%d":"RESTE À ENCAISSER PAR CATÉGORIE D\'ARTICLES  ·  ventilation des factures à relancer  ·  cliquez sur une catégorie pour ouvrir les lignes de factures dans Odoo"' % c_sect)
    cells.append('"A%d":"Catégorie"' % c_hdr)
    cells.append('"B%d":"Reste à encaisser"' % c_hdr)
    cells.append('"C%d":"Part"' % c_hdr)
    cells.append('"D%d":"Nb factures"' % c_hdr)
    dout_rows = []
    for i in range(len(CATEG)):
        r = c_first + i
        name = CATEG[i][0]
        if name in PRODS:
            desc = {"viewType": "list", "action": {"modelName": "account.move.line", "views": [[False, "list"], [False, "pivot"]], "domain": [["move_name", "in", INV], ["product_id", "in", PRODS[name]], ["display_type", "=", "product"]], "context": {"group_by": ["partner_id"]}}, "name": "Relances · %s · lignes de factures Odoo" % name}
            cells.append('"A%d":%s' % (r, json.dumps('[%s](odoo://view/%s)' % (name, json.dumps(desc, ensure_ascii=False)), ensure_ascii=False)))
        else:
            cells.append('"A%d":"%s"' % (r, name))
            if name.startswith(DOUT_PREFIX):
                dout_rows.append(r)
        cells.append('"B%d":"%s"' % (r, CATEG[i][1]))
        cells.append('"C%d":"=B%d/$B$%d"' % (r, r, c_tot))
        cells.append('"D%d":"%d"' % (r, CATEG[i][2]))
    cells.append('"A%d":"TOTAL"' % c_tot)
    cells.append('"B%d":"=SUM(B%d:B%d)"' % (c_tot, c_first, c_last))
    cells.append('"C%d":"=SUM(C%d:C%d)"' % (c_tot, c_first, c_last))
    cells.append('"D%d":"=SUM(D%d:D%d)"' % (c_tot, c_first, c_last))
    cells.append('"A%d":"Méthode : pour chaque compte client, les règlements et acomptes SAGE sont imputés aux factures les plus anciennes ; le reste dû de chaque facture est ventilé selon ses lignes d\'articles dans Odoo (proportion HT), une facture d\'acompte suivant la facture finale du même client. Pierre = pierres et taille · Transport = transports, locations de camions, indexation gasoil · Négoce / Décharge = graviers, sables, terre de gobetage, décharge · TP = travaux et locations TP · Autre = emballages, éco-contribution. Les factures antérieures à Odoo (FA0xxxxx, SFM, Destrebecq) sont affectées manuellement (CANDAT et Sft Sud à parts égales Négoce / Transport) ; JRTP et MAGNEIN sont isolés en créances douteuses. Les liens n\'ouvrent que les factures présentes dans Odoo."' % c_note)
    cells.append('"I%d":"EXPORT SAGE COMPLET  ·  tous les comptes clients non lettrés  ·  ordre alphabétique  ·  solde = crédit - débit comme dans SAGE"' % bi_sect)
    for addr, lbl in [("I", "Tiers - Nom"), ("J", "Date Ecriture"), ("K", "Date Echéance"), ("L", "N° de Pièce"), ("M", "dif"), ("N", "Débit"), ("O", "Crédit"), ("P", "Solde")]:
        cells.append('"%s%d":"%s"' % (addr, bi_hdr, lbl))
    r = bi_first
    prev = None
    fl = None
    tot_rows = []
    for row in ALL:
        nm, code, d1, d2, pc, db, cr = row
        if prev is not None and code != prev:
            cells.append('"I%d":"Total %s"' % (r, prev))
            cells.append('"N%d":"=SUM(N%d:N%d)"' % (r, fl, r - 1))
            cells.append('"O%d":"=SUM(O%d:O%d)"' % (r, fl, r - 1))
            cells.append('"P%d":"=SUM(P%d:P%d)"' % (r, fl, r - 1))
            tot_rows.append(r)
            r += 2
            fl = None
        if fl is None:
            fl = r
        cells.append('"I%d":"%s"' % (r, nm))
        cells.append('"J%d":"%d"' % (r, d1))
        if d2:
            cells.append('"K%d":"%d"' % (r, d2))
        cells.append('"L%d":"%s"' % (r, pc))
        cells.append('"M%d":"=IF(K%d=\\"\\",\\"\\",TODAY()-K%d)"' % (r, r, r))
        cells.append('"N%d":"%s"' % (r, db))
        cells.append('"O%d":"%s"' % (r, cr))
        cells.append('"P%d":"=O%d-N%d"' % (r, r, r))
        prev = code
        r += 1
    cells.append('"I%d":"Total %s"' % (r, prev))
    cells.append('"N%d":"=SUM(N%d:N%d)"' % (r, fl, r - 1))
    cells.append('"O%d":"=SUM(O%d:O%d)"' % (r, fl, r - 1))
    cells.append('"P%d":"=SUM(P%d:P%d)"' % (r, fl, r - 1))
    tot_rows.append(r)
    bi_last = r
    gt = r + 2
    cells.append('"I%d":"TOTAL GÉNÉRAL"' % gt)
    cells.append('"N%d":"=SUM(N%d:N%d)/2"' % (gt, bi_first, bi_last))
    cells.append('"O%d":"=SUM(O%d:O%d)/2"' % (gt, bi_first, bi_last))
    cells.append('"P%d":"=SUM(P%d:P%d)/2"' % (gt, bi_first, bi_last))
    tot_styles = ','.join(['"I%d:P%d":"bitot"' % (t, t) for t in tot_rows])
    dout_styles = ''.join([',"A%d:D%d":"dout"' % (t, t) for t in dout_rows])
    styles = ('"A1:P1":"title","A2:P2":"sub","A4:B4":"kl_teal","A5:B5":"kv_teal","A6:B6":"kcap",'
        '"C4:D4":"kl_red","C5:D5":"kv_red","C6:D6":"kcap","E4:F4":"kl_amber","E5:F5":"kv_amber","E6:F6":"kcap",'
        '"I4:J4":"kl_slate","I5:J5":"kv_slate","I6:J6":"kcap","L4:P6":"note","A8:G8":"sect","I8:P8":"sect","A9:G9":"lhdr","I9:P9":"lhdr","Q9:Q%d":"hid",'
        '"A%d:A%d":"txt","E%d:E%d":"txt","I%d:I%d":"txt","I%d":"note",'
        '"A%d:D%d":"sect","A%d:B%d":"lhdr","A%d:A%d":"txt","A%d:D%d":"sect","A%d:B%d":"lhdr","A%d:A%d":"txt",'
        '"A%d:G%d":"sect","A%d:D%d":"lhdr","A%d:A%d":"txt","A%d:D%d":"ctot","A%d":"note",'
        '"I%d:P%d":"sect","I%d:P%d":"bihdr","I%d:I%d":"txt","L%d:L%d":"txt","M%d:M%d":"dif","I%d:P%d":"bigt",%s%s') % (last, first, lastc, first, lastc, first, last, n1, a_sect, a_sect, a_hdr, a_hdr, a_first, a_last, s_sect, s_sect, s_hdr, s_hdr, s_first, s_last, c_sect, c_sect, c_hdr, c_hdr, c_first, c_last, c_tot, c_tot, c_note, bi_sect, bi_sect, bi_hdr, bi_hdr, bi_first, bi_last, bi_first, bi_last, bi_first, bi_last, gt, gt, tot_styles, dout_styles)
    formats = ('"A5:B5":"eur2","C5:D5":"eur2","E5:F5":"eur2","I5:J5":"num",'
        '"B%d:D%d":"eur2","F%d:F%d":"date","G%d:G%d":"num",'
        '"J%d:K%d":"date","M%d:M%d":"num","N%d:P%d":"eur2","B%d:B%d":"eur2","B%d:B%d":"eur2",'
        '"B%d:B%d":"eur2","C%d:C%d":"pct","D%d:D%d":"num",'
        '"J%d:K%d":"date","M%d:M%d":"num","N%d:P%d":"eur2"') % (first, lastc, first, lastc, first, lastc, first, last, first, last, first, last, a_first, a_last, s_first, s_last, c_first, c_tot, c_first, c_tot, c_first, c_tot, bi_first, bi_last, bi_first, bi_last, bi_first, gt)
    cf = ('[{"id":"cf_red","ranges":["G%d:G%d","M%d:M%d"],"rule":{"type":"CellIsRule","operator":"isGreaterThan","values":["90"],"style":{"fillColor":"#F9E4E5","textColor":"#B4232A","bold":true}}},'
        '{"id":"cf_amber","ranges":["G%d:G%d","M%d:M%d"],"rule":{"type":"CellIsRule","operator":"isGreaterThan","values":["30"],"style":{"fillColor":"#FBEBD3","textColor":"#B45309","bold":true}}},'
        '{"id":"cf_yellow","ranges":["G%d:G%d","M%d:M%d"],"rule":{"type":"CellIsRule","operator":"isGreaterThan","values":["0"],"style":{"fillColor":"#FFF8DB","textColor":"#7A5B00"}}},'
        '{"id":"cf_neg","ranges":["P%d:P%d"],"rule":{"type":"CellIsRule","operator":"isLessThan","values":["0"],"style":{"textColor":"#1C6DA6","italic":true}}}]') % (first, lastc, first, last, first, lastc, first, last, first, lastc, first, last, first, last)
    data = ('{"version":"18.5.10","sheets":[{"id":"dash","name":"Dashboard","colNumber":18,"rowNumber":%d,'
        '"rows":{"0":{"size":44},"1":{"size":22},"3":{"size":20},"4":{"size":42},"5":{"size":16},"7":{"size":30},"%d":{"size":30},"%d":{"size":30},"%d":{"size":30},"%d":{"size":30},"%d":{"size":92}},'
        '"cols":{"0":{"size":290},"1":{"size":110},"2":{"size":125},"3":{"size":110},"4":{"size":150},"5":{"size":110},"6":{"size":80},"7":{"size":24},"8":{"size":290},"9":{"size":100},"10":{"size":100},"11":{"size":110},"12":{"size":80},"13":{"size":110},"14":{"size":110},"15":{"size":110},"16":{"size":40,"isHidden":true}},'
        '"merges":["A1:P1","A2:P2","A4:B4","A5:B5","A6:B6","C4:D4","C5:D5","C6:D6","E4:F4","E5:F5","E6:F6","I4:J4","I5:J5","I6:J6","L4:P6","A8:G8","I8:P8","I%d:P%d","A%d:D%d","A%d:D%d","A%d:G%d","A%d:G%d","I%d:P%d"],'
        '"cells":{%s},"styles":{%s},"formats":{%s},"borders":{},"conditionalFormats":%s,'
        '"dataValidationRules":[],"figures":[],"tables":[],"areGridLinesVisible":false,"isVisible":true,"headerGroups":{},"comments":{}}],'
        '"styles":{"title":{"bold":true,"fontSize":24,"textColor":"#FFFFFF","fillColor":"#01666B","verticalAlign":"middle"},'
        '"sub":{"italic":true,"fontSize":11,"textColor":"#BFE0E0","fillColor":"#013E42","verticalAlign":"middle"},'
        '"sect":{"bold":true,"fontSize":12,"textColor":"#FFFFFF","fillColor":"#01666B","verticalAlign":"middle"},'
        '"lhdr":{"bold":true,"fontSize":10,"textColor":"#FFFFFF","fillColor":"#4C5A67","verticalAlign":"middle"},'
        '"bihdr":{"bold":true,"fontSize":10,"textColor":"#FFFFFF","fillColor":"#A5A5A5","verticalAlign":"middle"},'
        '"bitot":{"bold":true,"fontSize":10,"textColor":"#FF0000","fillColor":"#DCDCDC","verticalAlign":"middle"},'
        '"bigt":{"bold":true,"fontSize":11,"textColor":"#FFFFFF","fillColor":"#A5A5A5","verticalAlign":"middle"},'
        '"dif":{"bold":true,"fontSize":10,"textColor":"#FF0000","align":"center"},'
        '"ctot":{"bold":true,"fontSize":11,"textColor":"#0E2E31","fillColor":"#D7E7E7","verticalAlign":"middle"},'
        '"dout":{"italic":true,"textColor":"#B4232A","fillColor":"#FBEBD3","verticalAlign":"middle"},'
        '"kcap":{"italic":true,"fontSize":9,"textColor":"#7A8791","align":"center","verticalAlign":"middle"},'
        '"note":{"italic":true,"fontSize":9,"textColor":"#5B6B78","verticalAlign":"middle","wrapping":"wrap"},'
        '"txt":{"align":"left"},"hid":{"fontSize":7,"textColor":"#CCCCCC"},'
        '"kl_teal":{"bold":true,"fontSize":10,"textColor":"#FFFFFF","fillColor":"#01666B","align":"center","verticalAlign":"middle"},'
        '"kv_teal":{"bold":true,"fontSize":22,"textColor":"#01666B","fillColor":"#E4F1F1","align":"center","verticalAlign":"middle"},'
        '"kl_red":{"bold":true,"fontSize":10,"textColor":"#FFFFFF","fillColor":"#B4232A","align":"center","verticalAlign":"middle"},'
        '"kv_red":{"bold":true,"fontSize":22,"textColor":"#B4232A","fillColor":"#F9E4E5","align":"center","verticalAlign":"middle"},'
        '"kl_amber":{"bold":true,"fontSize":10,"textColor":"#FFFFFF","fillColor":"#B45309","align":"center","verticalAlign":"middle"},'
        '"kv_amber":{"bold":true,"fontSize":22,"textColor":"#B45309","fillColor":"#FBEBD3","align":"center","verticalAlign":"middle"},'
        '"kl_slate":{"bold":true,"fontSize":10,"textColor":"#FFFFFF","fillColor":"#4C5A67","align":"center","verticalAlign":"middle"},'
        '"kv_slate":{"bold":true,"fontSize":22,"textColor":"#4C5A67","fillColor":"#EBEFF3","align":"center","verticalAlign":"middle"}},'
        '"formats":{"eur2":"#,##0.00 \\\\€","num":"#,##0","pct":"0.0%%","date":"dd/mm/yyyy"},'
        '"borders":{},"revisionId":"START_REVISION","uniqueFigureIds":true,'
        '"settings":{"locale":{"name":"French / Français","code":"fr_FR","thousandsSeparator":" ","decimalSeparator":",","dateFormat":"dd/mm/yyyy","timeFormat":"hh:mm:ss","formulaArgSeparator":";","weekStart":1}},'
        '"pivots":{},"pivotNextId":1,"customTableStyles":{},"globalFilters":[],"lists":{},"listNextId":1,"chartOdooMenusReferences":{}}') % (gt + 5, a_sect - 1, s_sect - 1, c_sect - 1, bi_sect - 1, c_note - 1, n1, n1, a_sect, a_sect, s_sect, s_sect, c_sect, c_sect, c_note, c_note, bi_sect, bi_sect, ','.join(cells), styles, formats, cf)

    resume = {'cells': data.count('":'), 'ncli': ncli, 'rows': NROWS, 'avoirs': len(AVOIRS), 'soldes': len(SOLDES), 'all': len(ALL), 'categ': len(CATEG), 'bi_last': bi_last, 'src': SRC}
    return data, resume


def maj(call, option=''):
    """Tâche relais « relances_board » : lit le paramètre, reconstruit le tableau de bord 39 et le relit pour contrôle.
    Garde-fou : si le tableau a été écrit APRÈS le paramètre (lecture Sage plus récente poussée directement, comme le
    20/10/2026), on ne l'écrase pas avec des données plus anciennes (option « force » pour passer outre)."""
    prm = call('ir.config_parameter', 'search_read', [['key', '=', PARAM]], ['value', 'write_date'])
    brut = (prm[0]['value'] if prm else '') or ''
    if not brut:
        raise ValueError('paramètre %s vide' % PARAM)
    tableau = call('spreadsheet.dashboard', 'read', [DASHBOARD_ID], ['write_date', 'name'])[0]
    data, resume = construire(json.loads(brut))
    resume['parametre_du'] = prm[0]['write_date']
    resume['tableau_du'] = tableau['write_date']
    if option == 'test':
        resume['ecrit'] = False
        return resume
    if tableau['write_date'] > prm[0]['write_date'] and option != 'force':
        resume['ecrit'] = False
        resume['motif'] = 'tableau plus récent que le paramètre : rien écrit (relancer avec relances_board:force pour écraser)'
        return resume
    call('spreadsheet.dashboard', 'write', [DASHBOARD_ID], {'spreadsheet_data': data})
    relu = json.loads(call('spreadsheet.dashboard', 'read', [DASHBOARD_ID], ['spreadsheet_data'])[0]['spreadsheet_data'])
    resume['cells'] = len(relu['sheets'][0]['cells'])
    resume['ecrit'] = True
    return resume
