"""Draws the conceptual and logical ERDs for the A1.1 report as SVG.

Usage (standard library only):
    MONO=1 python3 scripts/draw_erd.py diagrams/source     # grayscale, no title (as used in the report)
    python3 scripts/draw_erd.py diagrams/source            # color version with titles
Convert to PNG with any SVG tool, e.g. on macOS:
    sips -s format png diagrams/source/figure1_conceptual_model.svg --out diagrams/figure1_conceptual_model.png
"""
import math
import sys
from xml.sax.saxutils import escape

OUTDIR = sys.argv[1]
W_CARD, HEAD, ROW = 250, 36, 22
import os
MONO = os.environ.get('MONO') == '1'      # grayscale, no built-in title (APA 7 figures)
NAVY, LINE, MUTED = ('#222222', '#222222', '#555555') if MONO else ('#1F3B57', '#333333', '#5D6670')
NOTE_C = '#444444' if MONO else '#7A3E9D'
BOLD = "font-family=\"Helvetica-Bold, Arial-BoldMT, Helvetica\""
REG = "font-family=\"Helvetica, Arial\""


def card_h(rows):
    return HEAD + len(rows) * ROW + 10


def svg_card(x, y, title, rows, w=W_CARD, fill=None):
    fill = fill or ('#EFEFEF' if MONO else '#E8EEF6')
    h = card_h(rows)
    o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#FFFFFF" stroke="{NAVY}" stroke-width="1.6"/>',
         f'<path d="M{x} {y + 8} Q{x} {y} {x + 8} {y} L{x + w - 8} {y} Q{x + w} {y} {x + w} {y + 8} L{x + w} {y + HEAD} L{x} {y + HEAD} Z" fill="{NAVY}"/>',
         f'<text x="{x + w / 2}" y="{y + 24}" font-size="16" fill="#FFFFFF" text-anchor="middle" {BOLD}>{escape(title)}</text>']
    for i, (tag, name, typ) in enumerate(rows):
        ry = y + HEAD + 6 + i * ROW
        if i % 2:
            o.append(f'<rect x="{x + 1}" y="{ry - 2}" width="{w - 2}" height="{ROW}" fill="{fill}"/>')
        ty = ry + 15
        if tag:
            color = '#222222' if MONO else ('#B4561E' if 'FK' in tag and 'PK' not in tag else ('#7A3E9D' if 'PK' in tag and 'FK' in tag else NAVY))
            o.append(f'<text x="{x + 10}" y="{ty}" font-size="12" fill="{color}" {BOLD}>{escape(tag)}</text>')
        o.append(f'<text x="{x + 58}" y="{ty}" font-size="14" fill="#111" {BOLD if tag and "PK" in tag else REG}>{escape(name)}</text>')
        if typ:
            o.append(f'<text x="{x + w - 10}" y="{ty}" font-size="12" fill="{MUTED}" text-anchor="end" {REG}>{escape(typ)}</text>')
    return o, (x, y, w, h)


def clip(rect, cx, cy, dx, dy):
    x, y, w, h = rect
    tx = (w / 2) / abs(dx) if dx else 1e9
    ty = (h / 2) / abs(dy) if dy else 1e9
    t = min(tx, ty)
    return cx + dx * t, cy + dy * t


def center(rect):
    x, y, w, h = rect
    return x + w / 2, y + h / 2


def edge(a, b, la, lb, verb=None, bold=False, note=None, a_pt=None, b_pt=None):
    (ax, ay), (bx, by) = a_pt or center(a), b_pt or center(b)
    dx, dy = bx - ax, by - ay
    p1 = clip(a, ax, ay, dx, dy) if not a_pt else (ax, ay)
    p2 = clip(b, bx, by, -dx, -dy) if not b_pt else (bx, by)
    o = [f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" stroke="{LINE}" stroke-width="{3 if bold else 1.8}"/>']
    L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    ux, uy = (p2[0] - p1[0]) / L, (p2[1] - p1[1]) / L
    nx, ny = -uy, ux
    if ny > 0 or (abs(ny) < 1e-9 and nx < 0):
        nx, ny = -nx, -ny
    d_end = 26 if L < 200 else 44
    for dist, s in ((d_end, la), (L - d_end, lb)):
        x = p1[0] + ux * dist + nx * 14
        y = p1[1] + uy * dist + ny * 14 + 5
        o.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="15" fill="#111" text-anchor="middle" {BOLD}>{escape(s)}</text>')
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    if verb:
        w = len(verb) * 8 + 16
        o.append(f'<rect x="{mx - w / 2:.1f}" y="{my - 12:.1f}" width="{w}" height="24" fill="#FFFFFF"/>')
        o.append(f'<text x="{mx:.1f}" y="{my + 5:.1f}" font-size="15" font-style="italic" fill="#111" text-anchor="middle" {REG}>{escape(verb)}</text>')
    if note:
        for k, line in enumerate(note):
            o.append(f'<text x="{mx:.1f}" y="{my + 32 + k * 17:.1f}" font-size="12.5" fill="{NOTE_C}" text-anchor="middle" {REG}>{escape(line)}</text>')
    return o


def write(name, width, height, title, subtitle, parts, legend):
    top = 70 if MONO else 0     # crop the title band in APA mode
    head = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width * 2}" height="{(height - top) * 2}" viewBox="0 {top} {width} {height - top}">',
            f'<rect y="{top}" width="{width}" height="{height}" fill="#FFFFFF"/>']
    if not MONO:
        head += [f'<text x="30" y="40" font-size="24" fill="{NAVY}" {BOLD}>{escape(title)}</text>',
                 f'<text x="30" y="64" font-size="14" fill="{MUTED}" {REG}>{escape(subtitle)}</text>']
    lx, ly = legend
    leg = [f'<rect x="{lx}" y="{ly}" width="300" height="118" rx="8" fill="#FFFFFF" stroke="#999"/>',
           f'<text x="{lx + 14}" y="{ly + 24}" font-size="14" fill="#222" {BOLD}>Multiplicity</text>']
    for i, s in enumerate(['1 = exactly one', '0..* = zero or more', '1..* = one or more', 'Read each end as "how many of this box"']):
        leg.append(f'<text x="{lx + 14}" y="{ly + 46 + i * 19}" font-size="13" fill="#222" {REG}>{escape(s)}</text>')
    open(f'{OUTDIR}/{name}.svg', 'w').write('\n'.join(head + parts + leg + ['</svg>']))


# ------------------------------------------------------------------ conceptual
C = {
    'CLIENT': (40, 100, [('ID', 'client_id', ''), ('', 'first_name', ''), ('', 'last_name', ''), ('', 'email', ''),
                         ('', 'date_of_birth', ''), ('', 'risk_profile', ''), ('', 'onboard_date', '')]),
    'PORTFOLIO': (520, 100, [('ID', 'portfolio_id', ''), ('', 'portfolio_name', ''), ('', 'account_type', ''),
                             ('', 'strategy', ''), ('', 'fee_pct', ''), ('', 'open_date', ''), ('', 'status', '')]),
    'PORTFOLIO MANAGER': (1000, 100, [('ID', 'manager_id', ''), ('', 'first_name', ''), ('', 'last_name', ''), ('', 'email', ''),
                                      ('', 'desk', ''), ('', 'hire_date', ''), ('', 'base_salary', ''), ('', 'profit_share_pct', '')]),
    'CASH FLOW': (40, 500, [('ID', 'flow_id', ''), ('', 'flow_date', ''), ('', 'flow_type', ''), ('', 'amount', '')]),
    'TRADE': (520, 500, [('ID', 'trade_id', ''), ('', 'confirmation_no', ''), ('', 'trade_date', ''), ('', 'side', ''),
                         ('', 'quantity', ''), ('', 'price', ''), ('', 'settlement_date', '')]),
    'SECURITY': (280, 840, [('ID', 'security_id', ''), ('', 'ticker', ''), ('', 'security_name', ''), ('', 'asset_class', ''),
                            ('', 'sector', ''), ('', 'current_price', ''), ('', 'price_date', '')]),
    'BROKER': (760, 840, [('ID', 'broker_id', ''), ('', 'broker_name', ''), ('', 'contact_email', ''),
                          ('', 'commission_rate', ''), ('', 'is_active', '')]),
}
parts, R = [], {}
cards = []
for n, (x, y, rows) in C.items():
    o, R[n] = svg_card(x, y, n, rows)
    cards += o
parts += edge(R['CLIENT'], R['PORTFOLIO'], '1..*', '1..*', 'owns', bold=True,
              note=['many-to-many', 'carries: ownership %, added date'])
parts += edge(R['PORTFOLIO MANAGER'], R['PORTFOLIO'], '1', '0..*', 'manages')
parts += edge(R['CLIENT'], R['CASH FLOW'], '1', '0..*', 'makes')
parts += edge(R['PORTFOLIO'], R['CASH FLOW'], '1', '0..*', 'receives')
parts += edge(R['PORTFOLIO'], R['TRADE'], '1', '0..*', 'records')
parts += edge(R['SECURITY'], R['TRADE'], '1', '0..*', 'is traded in')
parts += edge(R['BROKER'], R['TRADE'], '1', '0..*', 'executes')
write('figure1_conceptual_model', 1290, 1080, 'Figure 1. Royal Point Capital: conceptual data model',
      'Entities, their attributes and relationships as the business sees them. ID = identifier. No foreign keys or junction tables.',
      parts + cards, (985, 530))

# ------------------------------------------------------------------ logical
X = [30, 370, 710, 1050]
L = {
    'client': (X[0], 100, [('PK', 'client_id', 'INTEGER'), ('', 'first_name', 'TEXT'), ('', 'last_name', 'TEXT'),
                           ('UQ', 'email', 'TEXT'), ('', 'date_of_birth', 'TEXT'), ('', 'risk_profile', 'TEXT'),
                           ('', 'onboard_date', 'TEXT')]),
    'portfolio_owner': (X[1], 100, [('PK FK', 'portfolio_id', 'INTEGER'), ('PK FK', 'client_id', 'INTEGER'),
                                    ('', 'ownership_pct', 'REAL'), ('', 'added_date', 'TEXT')]),
    'portfolio': (X[2], 100, [('PK', 'portfolio_id', 'INTEGER'), ('FK', 'manager_id', 'INTEGER'), ('', 'portfolio_name', 'TEXT'),
                              ('', 'account_type', 'TEXT'), ('', 'strategy', 'TEXT'), ('', 'fee_pct', 'REAL'),
                              ('', 'open_date', 'TEXT'), ('', 'status', 'TEXT')]),
    'portfolio_manager': (X[3], 100, [('PK', 'manager_id', 'INTEGER'), ('', 'first_name', 'TEXT'), ('', 'last_name', 'TEXT'),
                                      ('UQ', 'email', 'TEXT'), ('', 'desk', 'TEXT'), ('', 'hire_date', 'TEXT'),
                                      ('', 'base_salary', 'REAL'), ('', 'profit_share_pct', 'REAL')]),
    'cash_flow': (X[1], 470, [('PK', 'flow_id', 'INTEGER'), ('FK*', 'portfolio_id', 'INTEGER'), ('FK*', 'client_id', 'INTEGER'),
                              ('', 'flow_date', 'TEXT'), ('', 'flow_type', 'TEXT'), ('', 'amount', 'REAL')]),
    'trade': (X[2], 470, [('PK', 'trade_id', 'INTEGER'), ('UQ', 'confirmation_no', 'TEXT'), ('FK', 'portfolio_id', 'INTEGER'),
                          ('FK', 'security_id', 'INTEGER'), ('FK', 'broker_id', 'INTEGER'), ('', 'trade_date', 'TEXT'),
                          ('', 'side', 'TEXT'), ('', 'quantity', 'INTEGER'), ('', 'price', 'REAL'),
                          ('', 'settlement_date', 'TEXT')]),
    'security': (X[1] + 60, 880, [('PK', 'security_id', 'INTEGER'), ('UQ', 'ticker', 'TEXT'), ('', 'security_name', 'TEXT'),
                                  ('', 'asset_class', 'TEXT'), ('', 'sector', 'TEXT'), ('', 'current_price', 'REAL'),
                                  ('', 'price_date', 'TEXT')]),
    'broker': (X[3], 880, [('PK', 'broker_id', 'INTEGER'), ('UQ', 'broker_name', 'TEXT'), ('', 'contact_email', 'TEXT'),
                           ('', 'commission_rate', 'REAL'), ('', 'is_active', 'INTEGER')]),
}
parts, R = [], {}
cards = []
for n, (x, y, rows) in L.items():
    o, R[n] = svg_card(x, y, n, rows)
    cards += o


def side_pt(rect, side, frac=0.5):
    x, y, w, h = rect
    return {'left': (x, y + h * frac), 'right': (x + w, y + h * frac),
            'top': (x + w * frac, y), 'bottom': (x + w * frac, y + h)}[side]


cy = 100 + HEAD + 2 * ROW
parts += edge(R['client'], R['portfolio_owner'], '1', '1..*', a_pt=(X[0] + W_CARD, cy), b_pt=(X[1], cy))
parts += edge(R['portfolio'], R['portfolio_owner'], '1', '1..*', a_pt=(X[2], cy), b_pt=(X[1] + W_CARD, cy))
parts += edge(R['portfolio_manager'], R['portfolio'], '1', '0..*', a_pt=(X[3], cy), b_pt=(X[2] + W_CARD, cy))
parts += edge(R['portfolio_owner'], R['cash_flow'], '1', '0..*', a_pt=side_pt(R['portfolio_owner'], 'bottom'),
              b_pt=side_pt(R['cash_flow'], 'top'))
parts += edge(R['portfolio'], R['trade'], '1', '0..*', a_pt=side_pt(R['portfolio'], 'bottom'), b_pt=side_pt(R['trade'], 'top'))
parts += edge(R['security'], R['trade'], '1', '0..*', a_pt=side_pt(R['security'], 'top', 0.7),
              b_pt=side_pt(R['trade'], 'bottom', 0.3))
parts += edge(R['broker'], R['trade'], '1', '0..*', a_pt=side_pt(R['broker'], 'top', 0.3),
              b_pt=side_pt(R['trade'], 'bottom', 0.75))
key = [f'<rect x="30" y="880" width="330" height="140" rx="8" fill="#FFFFFF" stroke="#999"/>',
       f'<text x="44" y="904" font-size="14" fill="#222" {BOLD}>Keys</text>']
for i, (t, s, c) in enumerate([('PK', 'primary key', NAVY), ('FK', 'foreign key', NAVY if MONO else '#B4561E'),
                               ('PK FK', 'part of a composite primary key', NAVY if MONO else '#7A3E9D'),
                               ('FK*', 'one composite FK: (portfolio_id, client_id)', NAVY if MONO else '#B4561E'),
                               ('UQ', 'unique', NAVY)]):
    key.append(f'<text x="44" y="{926 + i * 19}" font-size="12" fill="{c}" {BOLD}>{t}</text>')
    key.append(f'<text x="98" y="{926 + i * 19}" font-size="13" fill="#222" {REG}>{escape(s)}</text>')
write('figure2_logical_model', 1330, 1175, 'Figure 2. Royal Point Capital: normalized (3NF) logical data model',
      '8 tables, 55 columns. The client-portfolio many-to-many is resolved by portfolio_owner; cash_flow references it.',
      parts + cards + key, (30, 1035 - 0))
