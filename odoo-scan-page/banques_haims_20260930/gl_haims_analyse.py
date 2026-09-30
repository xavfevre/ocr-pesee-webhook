# -*- coding: utf-8 -*-
"""Lecture seule : analyse du grand-livre des tiers Sage de Haims (Downloads/GL.xlsx) avec le programme d'import du relais
(export_compta/app.py) sans rien appliquer : lecture, détection, groupes lettrés, propositions et anomalies."""
import io, os, sys, importlib.util
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('ODOO_URL', 'https://maquignon.odoo.com'); os.environ.setdefault('ODOO_DB', 'maquignon')
os.environ['ODOO_PASSWORD'] = os.environ.get('ODOO_PASSWORD') or os.environ.get('ODOO_PWD', '')
spec = importlib.util.spec_from_file_location('ec', 'ocr/export_compta/app.py'); ec = importlib.util.module_from_spec(spec); spec.loader.exec_module(ec)
chemin = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\xavfe\Downloads\GL.xlsx'
buf = io.BytesIO(open(chemin, 'rb').read())
print('grand-livre des tiers détecté :', ec._gl_detecte(buf)); buf.seek(0)
clients = ec._gl_parse(buf)
n_ecr = sum(len(cl['ecritures']) for cl in clients)
lettres = Counter(bool(e['lettre']) for cl in clients for e in cl['ecritures'])
journaux = Counter(e['journal'] for cl in clients for e in cl['ecritures'])
print('%d clients, %d écritures | lettrées %s | journaux %s' % (len(clients), n_ecr, dict(lettres), dict(journaux)))
for cl in clients[:3]:
    print('  ', cl['code'], cl['nom'][:25], [(e['date'], e['journal'], e['piece'], e['lib'][:28], e['lettre'], e['debit'], e['credit']) for e in cl['ecritures'][:3]])
props, anomalies, deja = ec._gl_analyse(4, clients)
print('\npropositions : %d | types %s | déjà à jour : %d | anomalies : %d' % (len(props), dict(Counter(p['type'] for p in props)), deja, len(anomalies)))
for p in props[:40]:
    l = p['ligne']
    print('  %-16s %s %9.2f  %-52s %s' % (p['type'], l['date'], l['debit'], l['lib'][:52], ' | '.join(p['detail'])[:110]))
for a in anomalies[:25]:
    print('  ⚠', a[:150])
