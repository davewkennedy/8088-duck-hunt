"""labelcheck: is the flat sheet connected by DRAWN lines, not by labels?

    python labelcheck.py flat.kicad_sch system.net refmap.json

1. Copies the schematic with every label removed, exports its netlist with
   kicad-cli and checks that no non-bus net splits: each system net (other
   than the bus members A0-A19/D0-D7 and the VCC/GND power nets) must lie
   inside ONE net of the label-free copy.
2. Bus members (A*/D*) are joined by name at their bus entries (that is how
   KiCad names bus members), so they are checked geometrically: every member
   label sits on a stub wire that ends at a bus entry; each entry's far end
   lies on a bus line; and all bus lines of one bus (A or D) form ONE
   continuous drawn line (segments meeting end to end or end to side).
Exit 0 = pass.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netdiff import parse, sexpr, find  # noqa: E402

CLI = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'KiCad', '10.0', 'bin', 'kicad-cli.exe')


def strip_labels(text):
    out, i = [], 0
    for m in re.finditer(r'\n\s*\(label "', text):
        s = m.start()
        depth, j = 0, text.index('(', s)
        while True:
            c = text[j]
            depth += c == '('
            depth -= c == ')'
            j += 1
            if depth == 0:
                break
        out.append(text[i:s])
        i = j
    out.append(text[i:])
    return ''.join(out)


def xy(node):
    return (round(float(node[1]), 2), round(float(node[2]), 2))


def on_seg(p, a, b):
    if a[0] == b[0] == p[0]:
        return min(a[1], b[1]) - 0.01 <= p[1] <= max(a[1], b[1]) + 0.01
    if a[1] == b[1] == p[1]:
        return min(a[0], b[0]) - 0.01 <= p[0] <= max(a[0], b[0]) + 0.01
    return False


def bus_check(sch):
    root = sexpr(open(sch, encoding='utf-8').read())[0]
    wires = [tuple(xy(p) for p in find(find(w, 'pts')[0], 'xy')) for w in find(root, 'wire')]
    buses = [tuple(xy(p) for p in find(find(b, 'pts')[0], 'xy')) for b in find(root, 'bus')]
    entries = []
    for e in find(root, 'bus_entry'):
        a = xy(find(e, 'at')[0])
        sz = xy(find(e, 'size')[0])
        entries.append((a, (round(a[0] + sz[0], 2), round(a[1] + sz[1], 2))))
    # bus segments -> components (union-find)
    par = list(range(len(buses)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i, (a, b) in enumerate(buses):
        for j, (c, d) in enumerate(buses):
            if i < j and (on_seg(a, c, d) or on_seg(b, c, d) or on_seg(c, a, b) or on_seg(d, a, b)):
                par[f(i)] = f(j)
    bad, comp = 0, {'A': set(), 'D': set()}
    for lb in find(root, 'label'):
        name = lb[1]
        if not re.fullmatch(r'A\d+|D[0-7]', name):
            continue
        p = xy(find(lb, 'at')[0])
        stub = [w for w in wires if p in w]
        ent = [e for e in entries for w in stub if e[0] in w]
        if not ent:
            print(f'bus member {name} at {p}: stub does not reach a bus entry'); bad += 1
            continue
        far = ent[0][1]
        segs = [i for i, (a, b) in enumerate(buses) if on_seg(far, a, b)]
        if not segs:
            print(f'bus member {name} at {p}: entry does not land on a bus line'); bad += 1
            continue
        comp[name[0]].add(f(segs[0]))
    for k, cs in comp.items():
        if len(cs) != 1:
            print(f'bus {k}: {len(cs)} separate drawn pieces (should be 1)'); bad += 1
    if comp['A'] & comp['D']:
        print('buses A and D touch'); bad += 1
    print(f'buses: A members on {len(comp["A"])} line, D members on {len(comp["D"])} line')
    return bad


def main(sch, sysnet, mapfile):
    refmap = json.load(open(mapfile))
    tmp = tempfile.mkdtemp()
    # keep the project files next to the copy so symbols resolve
    src_dir = os.path.dirname(os.path.abspath(sch))
    for fn in os.listdir(src_dir):
        if fn in ('sym-lib-table', 'skeet8088.kicad_sym'):
            open(os.path.join(tmp, fn), 'w', encoding='utf-8').write(
                open(os.path.join(src_dir, fn), encoding='utf-8').read())
    cp = os.path.join(tmp, 'nolabels.kicad_sch')
    open(cp, 'w', encoding='utf-8', newline='\n').write(strip_labels(open(sch, encoding='utf-8').read()))
    net = os.path.join(tmp, 'nolabels.net')
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', net, cp],
                   check=True, capture_output=True)
    B = parse(net)
    where = {}
    for i, (_, nodes) in enumerate(B['nets']):
        for r, p, _ in nodes:
            where[(r, p)] = i
    A = parse(sysnet)
    bad, checked = 0, 0
    for name, nodes in A['nets']:
        name = name.replace('{slash}', '/')
        pins = [(refmap.get(r, r), p) for r, p, _ in nodes if not r.startswith('#')]
        if len(pins) < 2 or name in ('VCC', 'GND') or re.fullmatch(r'A\d+|D[0-7]', name):
            continue
        checked += 1
        pieces = {where.get(x) for x in pins}
        if len(pieces) > 1:
            print(f'net {name} splits into {len(pieces)} pieces without labels'); bad += 1
    print(f'{checked} non-bus nets checked with all labels removed: {checked - bad} whole, {bad} split')
    bad += bus_check(sch)
    print('PASS' if not bad else f'FAIL ({bad})')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
