"""netdiff: compare the connectivity of two KiCad netlists (kicadsexpr).

    python netdiff.py A.net B.net [refmap.json]

refmap.json maps references in A to references in B (e.g. the system
project's U101 -> the flat sheet's U5). Nets are compared as SETS OF PINS
(ref, pin number), so net names don't matter; unconnected single pins are
compared too. Exit code 0 = same connectivity, 1 = differences (listed).

Also usable as a module: parse(path) -> {'comps': {ref: {...}},
'nets': [(name, [(ref, pin, pinfunction), ...]), ...]}.
"""
import json
import sys


def sexpr(text):
    """Minimal S-expression parser: returns nested lists of strings."""
    out, stack, i, n = [], [], 0, len(text)
    cur = out
    while i < n:
        c = text[i]
        if c == '(':
            new = []
            cur.append(new)
            stack.append(cur)
            cur = new
            i += 1
        elif c == ')':
            cur = stack.pop()
            i += 1
        elif c == '"':
            j, buf = i + 1, []
            while text[j] != '"':
                if text[j] == '\\':
                    j += 1
                buf.append(text[j])
                j += 1
            cur.append(''.join(buf))
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()':
                j += 1
            cur.append(text[i:j])
            i = j
    return out


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def val(node, key, default=None):
    f = find(node, key)
    return f[0][1] if f and len(f[0]) > 1 else default


def parse(path):
    root = sexpr(open(path, encoding='utf-8').read())[0]
    comps = {}
    for c in find(find(root, 'components')[0], 'comp'):
        lib = find(c, 'libsource')
        comps[val(c, 'ref')] = {
            'value': val(c, 'value'),
            'lib': val(lib[0], 'lib') if lib else None,
            'part': val(lib[0], 'part') if lib else None,
        }
    nets = []
    for nt in find(find(root, 'nets')[0], 'net'):
        nodes = [(val(nd, 'ref'), val(nd, 'pin'), val(nd, 'pinfunction', ''))
                 for nd in find(nt, 'node')]
        nets.append((val(nt, 'name'), nodes))
    return {'comps': comps, 'nets': nets}


def pinsets(nl, refmap=None):
    refmap = refmap or {}
    out = {}
    for name, nodes in nl['nets']:
        key = frozenset((refmap.get(r, r), p) for r, p, _ in nodes if not r.startswith('#'))
        if key:
            out[key] = name
    return out


def main(a, b, mapfile=None):
    refmap = json.load(open(mapfile)) if mapfile else {}
    A, B = parse(a), parse(b)
    pa, pb = pinsets(A, refmap), pinsets(B)
    ca = {refmap.get(r, r) for r in A['comps'] if not r.startswith('#')}
    cb = {r for r in B['comps'] if not r.startswith('#')}
    bad = 0
    for r in sorted(ca - cb):
        print('component only in A:', r); bad += 1
    for r in sorted(cb - ca):
        print('component only in B:', r); bad += 1
    for k in pa.keys() - pb.keys():
        print('net only in A:', pa[k], sorted(k)); bad += 1
    for k in pb.keys() - pa.keys():
        print('net only in B:', pb[k], sorted(k)); bad += 1
    print(f'A: {len(ca)} components, {len(pa)} nets; B: {len(cb)} components, {len(pb)} nets; '
          f'{"SAME connectivity" if not bad else str(bad) + " differences"}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
