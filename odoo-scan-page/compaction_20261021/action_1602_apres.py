def find_date(text):
    for i in range(len(text or '') - 9):
        c = text[i:i + 10]
        if c[2] == '/' and c[5] == '/':
            try:
                return datetime.datetime(int(c[6:10]), int(c[3:5]), int(c[0:2]))
            except Exception:
                pass
    return None

def find_bon_number(text):
    try:
        return float(text.split("n°")[1].split("|")[0].strip())   # float pour gérer "03006100.01"
    except Exception:
        return 999999

def normalize(text):
    t = (text or '').lower()
    for a, b in (('â', 'a'), ('è', 'e'), ('é', 'e'), ('ê', 'e'), ('-', ' '), ('_', ' ')):
        t = t.replace(a, b)
    return t

def get_type(section_name, line_names):
    t = normalize(section_name) + ' ' + ' '.join(normalize(n) for n in line_names)
    if 'solo' in t:
        return 0
    if 'duo' in t:
        return 1
    if 'fond' in t and 'mouvant' in t:
        return 2
    if 'inversion' in t or 'benne' in t:
        return 3
    return 4

def is_fixed_section(text):
    t = normalize(text)   # pas de générateur ici : safe_eval d'Odoo refuse les fermetures dans une fonction
    return find_date(text) is None and (('fond' in t and 'mouvant' in t) or 'solo' in t or 'duo' in t or 'inversion' in t or 'benne' in t)

SECTIONS_NOMS = {0: '- Solo -', 1: '- Duo -', 2: '- Fond-mouvant -', 3: '- Inversion de benne pate -'}
lignes = record.invoice_line_ids
types_presents = {get_type('', [l.name or '']) for l in lignes if l.display_type != 'line_section'} & set(SECTIONS_NOMS)
deja = {get_type(l.name, []) for l in lignes if l.display_type == 'line_section' and is_fixed_section(l.name)}
manquants = [(0, 0, {'display_type': 'line_section', 'name': SECTIONS_NOMS[t], 'sequence': 9999}) for t in types_presents if t not in deja]
if manquants:
    record.write({'invoice_line_ids': manquants})

fixed, groups, ungrouped, cur = {}, [], [], None
for l in record.invoice_line_ids.sorted('sequence'):
    if l.display_type == 'line_section':
        if cur is not None:
            groups.append(cur)
            cur = None
        if is_fixed_section(l.name):
            fixed[get_type(l.name, [])] = l
        else:
            cur = {'section': l, 'date': find_date(l.name or ''), 'bon': find_bon_number(l.name or ''), 'lines': []}
    elif cur is not None:
        cur['lines'].append(l)
    else:
        ungrouped.append(l)
if cur is not None:
    groups.append(cur)
for g in groups:
    g['type'] = get_type('', [l.name for l in g['lines']])   # type déterminé par les lignes produit, pas le nom de section
groups.sort(key=lambda g: (g['type'], g['date'] or datetime.datetime(9999, 12, 31), g['bon']))

ordre = list(ungrouped)
for t in sorted({g['type'] for g in groups}):
    if t in fixed:
        ordre.append(fixed[t])
    for g in groups:
        if g['type'] == t:
            ordre += [g['section']] + g['lines']
for i, l in enumerate(ordre):
    l.write({'sequence': 10 + 10 * i})
