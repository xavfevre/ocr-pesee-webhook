def find_date(text):
    if not text:
        return None
    for i in range(len(text) - 9):
        chunk = text[i:i+10]
        if chunk[2] == '/' and chunk[5] == '/':
            try:
                d = int(chunk[0:2])
                m = int(chunk[3:5])
                y = int(chunk[6:10])
                return datetime.datetime(y, m, d)
            except Exception:
                pass
    return None

def find_bon_number(text):
    # FIX 1 : parse depuis "n°", pas depuis text[10:]
    try:
        after = text.split("n°")[1]
        num_str = after.split("|")[0].strip()
        return float(num_str)   # float pour gérer "03006100.01"
    except Exception:
        return 999999

def normalize(text):
    t = (text or '').lower()
    t = t.replace('â', 'a').replace('è', 'e').replace('é', 'e').replace('ê', 'e')
    t = t.replace('-', ' ').replace('_', ' ')
    return t

def get_type(section_name, line_names):
    all_text = normalize(section_name or '') + ' ' + ' '.join([normalize(n or '') for n in line_names])
    if 'solo' in all_text:
        return 0
    if 'duo' in all_text:
        return 1
    if 'fond' in all_text and 'mouvant' in all_text:
        return 2
    if 'inversion' in all_text or 'benne' in all_text:
        return 3
    return 4

def is_fixed_section(text):
    t = normalize(text or '')
    if find_date(text) is not None:
        return False
    if 'fond' in t and 'mouvant' in t:
        return True
    for kw in ['solo', 'duo', 'inversion', 'benne']:
        if kw in t:
            return True
    return False

SECTIONS_NOMS = {
    0: '- Solo -',
    1: '- Duo -',
    2: '- Fond-mouvant -',
    3: '- Inversion de benne pate -',
}

types_presents = set()
for line in record.invoice_line_ids:
    if line.display_type != 'line_section':
        t = get_type('', [line.name or ''])
        if t in SECTIONS_NOMS:
            types_presents.add(t)

for t in types_presents:
    nom = SECTIONS_NOMS[t]
    existe = False
    for line in record.invoice_line_ids:
        if line.display_type == 'line_section' and is_fixed_section(line.name) and get_type(line.name, []) == t:
            existe = True
            break
    if not existe:
        record.write({
            'invoice_line_ids': [(0, 0, {
                'display_type': 'line_section',
                'name': nom,
                'sequence': 9999,
            })]
        })

lines = record.invoice_line_ids.sorted('sequence')

fixed_sections = {}
dated_groups = []
ungrouped = []
current_group = None

for line in lines:
    if line.display_type == 'line_section':
        if current_group is not None:
            dated_groups.append(current_group)
            current_group = None
        if is_fixed_section(line.name):
            t = get_type(line.name, [])
            fixed_sections[t] = line
        else:
            current_group = {
                'section': line,
                'date': find_date(line.name or ''),
                'bon': find_bon_number(line.name or ''),
                'lines': [],
                'type': None
            }
    else:
        if current_group is not None:
            current_group['lines'].append(line)
        else:
            ungrouped.append(line)

if current_group is not None:
    dated_groups.append(current_group)

for g in dated_groups:
    line_names = [l.name for l in g['lines']]
    # FIX 2 : type déterminé UNIQUEMENT par les lignes produit, pas le nom de section
    g['type'] = get_type('', line_names)

dated_groups.sort(key=lambda g: (g['type'], g['date'] or datetime.datetime(9999, 12, 31), g['bon']))

by_type = {}
for g in dated_groups:
    t = g['type']
    if t not in by_type:
        by_type[t] = []
    by_type[t].append(g)

seq = 10

for line in ungrouped:
    line.write({'sequence': seq})
    seq += 10

for t in sorted(by_type.keys()):
    if t in fixed_sections:
        fixed_sections[t].write({'sequence': seq})
        seq += 10
    for g in by_type[t]:
        if g['section']:
            g['section'].write({'sequence': seq})
            seq += 10
        for line in g['lines']:
            line.write({'sequence': seq})
            seq += 10