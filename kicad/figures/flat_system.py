"""The whole Skeet Shoot 8088 computer on ONE flat sheet, drawn as one system.

    python flat_system.py   ->  ../flat/skeet8088-flat.kicad_sch (+ .kicad_pro,
                                sym-lib-table, skeet8088.kicad_sym, refmap.json)

Connectivity comes from the hierarchical system project's own netlist
(kicad-cli export of ../system/skeet8088-system.kicad_sch), so the drawing
cannot drift from it; tools/netdiff.py checks the result (same nets, same pin
sets, through refmap.json: system ref -> flat ref) and tools/labelcheck.py
checks that it stays connected with every label removed.

How it is drawn (paper D)
  - TOP row: clock, 8088, latches and buffers, 8253 timer + speaker, 8259.
    BOTTOM row: I/O decode, 8255 + LED bar, display, switches; memory decode,
    EEPROM, RAM, LEDs.
  - Between the rows a corridor carries the two system buses as CONTINUOUS
    bus lines (A[0..19] and D[0..7], the "spine"). Every chip's bus pins have a
    stub, a bus entry and a local bus segment that drops onto the spine.
  - Every other connection is a drawn wire. Parts sit in columns; connected
    pins face each other across the channel between two columns: a straight
    wire when the rows line up, else a vertical trunk in the channel (track
    order is solved so no two nets touch; a global registry keeps trunks and
    bus lines on separate x where they overlap). Nets that span several
    channels join by a horizontal bridge: just below the parts they pass
    (8088 control lines to the latches) or in the corridor (system-wide
    signals such as /RD, /WR, IO/M, RESET, the chip selects).
  - Net labels stay on the wires of named signals and on bus stubs, as names.
  - VCC/GND are power symbols; PWR_FLAGs sit on the reset network's VCC and
    GND; pins the system leaves unused get no-connect flags. The crystal is
    routed by hand beside the 8284.
  - IC() definitions are imported from the figure modules (+ common.LS138,
    sys_clock.CLK8284); simple parts are KiCad stock symbols. References are
    renumbered top row then bottom row, left to right, top to bottom.

Run build_system.py first (this script exports its netlist with kicad-cli).
"""
import importlib
import json
import math
import os
import re
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import common  # noqa: E402
from kgen import IC, Stock, Sheet, g, rot, U, q, write_lib  # noqa: E402
from netdiff import parse  # noqa: E402

ROOT = os.path.join(HERE, '..')
SYS_SCH = os.path.join(ROOT, 'system', 'skeet8088-system.kicad_sch')
OUT = os.path.join(ROOT, 'flat')
PROJECT = 'skeet8088-flat'
CLI = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'KiCad', '10.0', 'bin', 'kicad-cli.exe')
P = 2.54
STUB = 2.54
BUSWIRE = {'D': 7.62, 'A': 12.7}     # bus stub length per bus (A further out: never collinear with D)
HAND_NETS = {'Net-(U701-X1)', 'Net-(U701-X2)'}
NAMED = {'/RD', '/WR', 'IO/M', 'RESET', '/PIT_CS', '/PIC_CS', '/PPI_CS', '/RAM_CS', 'PIT_OUT1',
         'PIT_OUT2', 'CLK', 'PCLK', 'READY', 'INTR', '/INTA'}
FLAGS = {('R701', '1'), ('C701', '2')}      # PWR_FLAG on these power stubs (VCC, GND)
FLAG_PARTS = {r for r, _ in FLAGS}
BOT_DY = 22.0                               # bottom row offset (room for the corridor)
XS = 1.3                                    # horizontal spread of the column layout (paper D)

# Parts: (sysref, x, y, angle, mirror), (x, y) = top-left of the pin/body box.
TOP = [
    [('SW701', 20, 112, 0, None), ('C701', 22, 99, 270, None), ('R701', 22, 86, 90, None)],
    [('U701', 58, 40, 0, None), ('U103', 68, 96, 0, 'y'), ('U104', 68, 136, 90, None)],
    [('U101', 158, 82, 0, None)],
    [('U106', 248, 82, 0, None), ('U105', 248, 124, 270, None)],
    [('U501', 332, 82, 0, None), ('LS501', 350, 130, 0, 'y')],
    [('U601', 422, 82, 0, None), ('U503', 422, 136, 0, 'y'), ('R501', 430, 162, 90, None)],
]
BOT = [
    [('U402', 70, 206, 0, None)],
    [('U401', 134, 206, 0, None)],
    [('D401', 224, 206, 0, None), ('D402', 226, 264, 0, None), ('D403', 226, 273, 0, None),
     ('U403', 222, 286, 0, None), ('SW402', 224, 322, 0, None),
     ('R420', 226, 344, 90, None), ('R421', 226, 352.89, 90, None), ('R422', 226, 361.78, 90, None),
     ('R423', 226, 370.67, 90, None), ('SW401', 226, 380, 180, None), ('R424', 226, 389, 90, None)],
    [],      # resistor column (row-aligned, placed below)
    [('DS401', 332, 286, 0, None)],
    [('U202', 430, 206, 0, None)],
    [('U201', 510, 206, 0, None), ('U301', 510, 276, 0, None),
     ('R201', 514, 336, 90, None), ('R202', 514, 348, 90, None)],
    [('D201', 556, 336, 0, None), ('D202', 556, 348, 0, None)],
]
RCOL_X = g(20 + (284 - 20) * 1.3)
REGIONS = [('TOP', TOP, 0.0), ('BOT', BOT, BOT_DY)]


def symbols():
    syms = {common.LS138.name: common.LS138}
    for mod in ['fig1_cpu', 'fig2_eeprom', 'fig3_ram', 'fig4_ppi', 'fig5_pit', 'fig6_pic', 'sys_clock']:
        for v in vars(importlib.import_module(mod)).values():
            if isinstance(v, IC):
                syms[v.name] = v
    return syms


def system_netlist():
    path = os.path.join(OUT, 'system.net')
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', path, SYS_SCH],
                   check=True, capture_output=True)
    return parse(path)


def unesc(s):
    return s.replace('{slash}', '/')


def box(sym, angle, mirror):
    pts = [rot(*sym.pin_geom(n)[0], angle, mirror) for n in sym.nums()]
    if isinstance(sym, IC):
        pts += [rot(0, 0, angle, mirror), rot(sym.w, -sym.h, angle, mirror)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def outward(part, num):
    _, a = part.sym.pin_geom(num)
    ox, oy = math.cos(math.radians(a + 180)), math.sin(math.radians(a + 180))
    dx, dy = rot(ox, oy, part.angle, part.mirror)
    return (round(dx), round(dy))


def textlen(t):
    return 1.0 * len(t) + 2.0


def overlap(a0, a1, b0, b1, m=1.27):
    return not (a1 + m < b0 or b1 + m < a0)


class Flat:
    def __init__(self):
        os.makedirs(OUT, exist_ok=True)
        self.nl = system_netlist()
        self.syms = symbols()
        self.pinnet = {}
        for name, nodes in self.nl['nets']:
            for r, p, _ in nodes:
                if not r.startswith('#'):
                    self.pinnet[(r, p)] = unesc(name)
        self.s = Sheet('Skeet Shoot 8088 Computer - Single-Sheet Schematic', PROJECT, paper='D', comments=[
            'David Kennedy - ECE 3710 Microprocessors, final project (Skeet Shoot)',
            'Single-sheet drawing (2026) of the system schematic: same netlist as the 8-sheet project',
            'Clock and reset (8284A) RECONSTRUCTED: not in the 2007 drawings',
        ])
        self.vcc, self.gnd = Stock('power', 'VCC'), Stock('power', 'GND')
        self.flag = Stock('power', 'PWR_FLAG')
        self.parts = {}            # sysref -> (Placed, region, col)
        self.warn = []
        self.segs = defaultdict(list)   # net -> [((x0, y0), (x1, y1))] for junctions
        self.vlines = []           # (x, y0, y1, owner) vertical wires and buses

    # ---------------- placement
    def place(self, ref, x, y, angle, mirror, region, col):
        c = self.nl['comps'][ref]
        sym = self.syms[c['part']] if c['lib'] == 'skeet8088' else Stock(c['lib'], c['part'])
        x0, x1, y0, y1 = box(sym, angle, mirror)
        ox, oy = g(x - x0), g(y - y0)
        if isinstance(sym, IC):
            p = self.s.ic(ref, sym, ox, oy, angle=angle, mirror=mirror, value=c['value'],
                          ref_at=(ox + x0 + 5.08, oy + y0 - 1.27), val_at=(ox + x0 + 5.08, oy + y1 + 2.54))
        else:
            hw = max(3.3, x1 - x0) / 2
            p = self.s.ic(ref, sym, ox, oy, angle=angle, mirror=mirror, value=c['value'],
                          ref_at=(ox - hw, oy - 2.6),
                          val_at=(ox + 1.27 if ref in FLAG_PARTS else ox - hw, oy + 3.6))
        self.parts[ref] = (p, region, col)
        return p

    def place_pin1(self, ref, pin, at, angle, region, col):
        c = self.nl['comps'][ref]
        sym = Stock(c['lib'], c['part'])
        (px, py), _ = sym.pin_geom(pin)
        dx, dy = rot(px, py, angle)
        # A uniform column (all 220 ohm): reference above, value hidden (still in the
        # part) and stated once above the column.
        p = self.s.ic(ref, sym, at[0] - dx, at[1] - dy, angle=angle, value=c['value'], hide_value=True,
                      ref_at=(at[0] - dx - 1.9, at[1] - dy - 1.9))
        self.parts[ref] = (p, region, col)

    def place_all(self):
        for region, cols, dy in REGIONS:
            for ci, col in enumerate(cols):
                for ref, x, y, a, m in col:
                    self.place(ref, 20 + (x - 20) * XS, y + dy, a, m, region, ci)
        bar, dec = self.parts['D401'][0], self.parts['U403'][0]
        for i, n in enumerate(['19', '17', '15', '13', '11', '9', '7', '5', '3', '1']):
            self.place_pin1(f'R{401 + i}', '1', (RCOL_X, bar.pin(n)[1]), 90, 'BOT', 3)
        for led, r in [('D402', 'R411'), ('D403', 'R412')]:
            self.place_pin1(r, '2', (RCOL_X, self.parts[led][0].pin('2')[1]), 270, 'BOT', 3)
        for i in range(7):
            self.place_pin1(f'R{413 + i}', '1', (RCOL_X, g(dec.pin('13')[1] + i * 5.08)), 90, 'BOT', 3)
        self.rcol = (RCOL_X, bar.pin('19')[1])

    # ---------------- helpers
    def kind(self, net):
        if net is None or net.startswith('unconnected-'):
            return 'nc'
        if net in ('VCC', 'GND'):
            return 'power'
        if re.fullmatch(r'A\d+|D[0-7]', net):
            return 'bus'
        if net in HAND_NETS:
            return 'hand'
        return 'route'

    def netname(self, name):
        m = re.match(r'Net-\((\w+)-(.*)\)$', name)
        if m:
            return f'{self.refmap.get(m.group(1), m.group(1))}-{m.group(2)}'
        return name

    def label(self, text, at, d):
        ang, just = {(1, 0): (0, 'left'), (-1, 0): (180, 'right'),
                     (0, -1): (90, 'left'), (0, 1): (270, 'right')}[d]
        self.s.items.append(f'(label {q(text)} (at {g(at[0])} {g(at[1])} {ang}) (fields_autoplaced yes) '
                            f'(effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid {q(U())}))')

    def w(self, net, *pts):
        pts = [(g(x), g(y)) for x, y in pts]
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.segs[net].append((a, b))
                if a[0] == b[0]:
                    self.vlines.append((a[0], min(a[1], b[1]), max(a[1], b[1]), net))
        return self.s.wire(*pts)

    def bus(self, a, b):
        a, b = (g(a[0]), g(a[1])), (g(b[0]), g(b[1]))
        self.s.items.append(f'(bus (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) '
                            f'(stroke (width 0) (type default)) (uuid {q(U())}))')

    def vfree(self, x, y0, y1, owner):
        for vx, a, b, o in self.vlines:
            if abs(vx - x) < 0.01 and o != owner and overlap(y0, y1, a, b):
                return False
        return True

    # ---------------- drawing
    def draw(self):
        s = self.s
        self.pins = []
        for r, (p, region, col) in self.parts.items():
            for num in p.sym.nums():
                net = self.pinnet.get((r, num))
                self.pins.append((r, num, p.pin(num), outward(p, num), net, self.kind(net)))
        occupied = {}
        self.bus_groups = defaultdict(list)
        for r, num, at, d, net, k in self.pins:
            _, region, col = self.parts[r]
            ext = 0.0
            if k == 'nc':
                s.noconnect(at)
            elif k == 'power':
                end = s.wire(at, (at[0] + d[0] * STUB, at[1] + d[1] * STUB))
                a = {'VCC': {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270},
                     'GND': {(0, 1): 0, (0, -1): 180, (-1, 0): 270, (1, 0): 90}}[net][d]
                s.power(self.vcc if net == 'VCC' else self.gnd, end, angle=a).hide_value = True
                if (r, num) in FLAGS:             # PWR_FLAG on the supply, beside the reset network
                    f = s.wire(end, (end[0], end[1] + 3.81))
                    s.power(self.flag, f, angle=180).hide_value = True
                ext = STUB + 5.5
            elif k == 'bus':
                L = BUSWIRE[net[0]]
                end = s.wire(at, (at[0] + d[0] * L, at[1]))
                self.label(net, at, d)
                self.bus_groups[(r, d, net[0])].append((at, end))
                ext = L + P + 2.0
            elif k == 'route' and net in NAMED:
                self.label(net, at, d)           # the signal's name, on its wire
            if d[0] and ext:
                key = (region, col, 'R' if d[0] > 0 else 'L')
                occupied[key] = max(occupied.get(key, 0), ext)
        self.occupied = occupied
        self.route()
        self.hand_crystal()

    # ---------------- router
    def route(self):
        s = self.s
        colx = defaultdict(lambda: [1e9, -1e9])
        colbottom = defaultdict(float)
        regbottom = defaultdict(float)
        regtop = defaultdict(lambda: 1e9)
        for r, (p, region, col) in self.parts.items():
            x0, x1, y0, y1 = box(p.sym, p.angle, p.mirror)
            c = colx[(region, col)]
            c[0], c[1] = min(c[0], p.x + x0), max(c[1], p.x + x1)
            colbottom[(region, col)] = max(colbottom[(region, col)], p.y + y1)
            regbottom[region] = max(regbottom[region], p.y + y1)
            regtop[region] = min(regtop[region], p.y + y0)
        ncols = {region: len(cols) for region, cols, _ in REGIONS}

        def chan_range(region, i):
            if i < 0:
                hi = colx[(region, 0)][0] - self.occupied.get((region, 0, 'L'), 0) - P
                return hi - 30, hi
            lo = colx[(region, i)][1] + self.occupied.get((region, i, 'R'), 0) + P
            if i + 1 < ncols[region] and (region, i + 1) in colx:
                hi = colx[(region, i + 1)][0] - self.occupied.get((region, i + 1, 'L'), 0) - P
            else:
                hi = lo + 30
            return lo, hi

        # attach points: net -> chan -> [(y, side, at)]
        att = defaultdict(lambda: defaultdict(list))
        for r, num, at, d, net, k in self.pins:
            if k != 'route':
                continue
            p, region, col = self.parts[r]
            if d[1] != 0:
                self.warn.append(f'{r}.{num} faces up/down: not routed')
                continue
            ch = col if d[0] > 0 else col - 1
            att[net][(region, ch)].append((at[1], 'L' if d[0] > 0 else 'R', at))
        rows_in = defaultdict(set)                    # (region, ch) -> attach rows
        for net, chans in att.items():
            for ch, pts in chans.items():
                for y, _, _ in pts:
                    rows_in[ch].add(g(y))

        # bridges: a horizontal joining the trunks of a net that spans channels
        corridor0 = g(regbottom['TOP'] + 7.62)
        used_rows = set()
        bridge_y = {}
        order = sorted((n for n in att if len(att[n]) > 1),
                       key=lambda n: (len({c[0] for c in att[n]}), min(c[1] for c in att[n])))
        for net in order:
            chans = list(att[net])
            regions = {c[0] for c in chans}
            if regions == {'TOP'}:
                lo_c, hi_c = min(c[1] for c in chans), max(c[1] for c in chans)
                spanned = [colbottom[('TOP', c)] for c in range(lo_c + 1, hi_c + 1)]
                base = g(max(spanned or [regbottom['TOP']]) + 3.81)
                rows = set().union(*(rows_in[('TOP', c)] for c in range(lo_c, hi_c + 1)))
            else:
                base, rows = corridor0, set()
            y = base
            while y in used_rows or any(abs(y - r) < 1.3 for r in rows):
                y = g(y + P)
            used_rows.add(y)
            bridge_y[net] = y
        spine = {'A': g(max(used_rows | {corridor0}) + 7.62)}
        spine['D'] = g(spine['A'] + 5.08)
        if spine['D'] + 7.62 > regtop['BOT']:
            self.warn.append(f'corridor overflow: spine D at {spine["D"]}, bottom row starts {regtop["BOT"]}')

        # buses: local segments with entries, dropped onto the spine lines
        drops = defaultdict(list)
        spans = {}                                   # (bx, letter) -> [ymin, ymax] of entries
        for (r, d, letter), lst in self.bus_groups.items():
            lst.sort(key=lambda t: t[1][1])
            bx = g(lst[0][1][0] + d[0] * P)
            for at, end in lst:
                s.items.append(f'(bus_entry (at {g(end[0])} {g(end[1])}) (size {g(d[0] * P)} {P}) '
                               f'(stroke (width 0) (type default)) (uuid {q(U())}))')
            sp = spans.setdefault((bx, letter), [1e9, -1e9])
            sp[0], sp[1] = min(sp[0], g(lst[0][1][1])), max(sp[1], g(lst[-1][1][1] + P))
        for (bx, letter), (y0, y1) in sorted(spans.items()):
            sy = spine[letter]
            a, b = (min(y0, sy), max(y1, sy))
            self.bus((bx, a), (bx, b))
            for vx, va, vb, o in self.vlines:
                if abs(vx - bx) < 0.01 and o != 'BUS' + letter and overlap(a, b, va, vb, 0):
                    self.warn.append(f'bus {letter} at x={bx} overlaps {o}')
            self.vlines.append((bx, a, b, 'BUS' + letter))
            drops[letter].append(bx)
            name = 'A[0..19]' if letter == 'A' else 'D[0..7]'
            ly = a if b == sy else b                 # the end away from the spine
            s.items.append(f'(label {q(name)} (at {bx} {ly} 90) (fields_autoplaced yes) '
                           f'(effects (font (size 1.27 1.27)) (justify {"left" if b == sy else "right"} bottom)) '
                           f'(uuid {q(U())}))')
        for letter, xs in drops.items():
            xs = sorted(set(xs))
            y = spine[letter]
            self.bus((xs[0], y), (xs[-1], y))
            for x in xs[1:-1]:
                s.junction((x, y))
            name = 'A[0..19]' if letter == 'A' else 'D[0..7]'
            s.items.append(f'(label {q(name)} (at {xs[0] - 15} {y} 0) (fields_autoplaced yes) '
                           f'(effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {q(U())}))')
            self.bus((xs[0] - 15, y), (xs[0], y))

        # tracks per channel
        chans = defaultdict(list)
        for net, cs in att.items():
            for ch in cs:
                chans[ch].append(net)
        bridge_xs = defaultdict(list)
        for ch, nets in sorted(chans.items()):
            lo, hi = chan_range(*ch)
            info = {}
            for net in nets:
                pts = att[net][ch]
                ys = [y for y, _, _ in pts]
                if net in bridge_y:
                    ys.append(bridge_y[net])
                straight = (net not in bridge_y and len(pts) == 2 and pts[0][0] == pts[1][0]
                            and {pts[0][1], pts[1][1]} == {'L', 'R'})
                info[net] = (min(ys), max(ys), straight)
            rowL, rowR = defaultdict(list), defaultdict(list)
            for net in nets:
                for y, side, _ in att[net][ch]:
                    (rowL if side == 'L' else rowR)[g(y)].append(net)
            before = defaultdict(set)
            for y in rowL:
                for a in rowL[y]:
                    for b in rowR.get(y, []):
                        if a != b:
                            before[b].add(a)
            straight = {m for m in nets if info[m][2]}
            track, used = {}, defaultdict(list)
            todo = sorted([n for n in nets if n not in straight], key=lambda n: (info[n][0], info[n][1]))
            done = set()
            while todo:
                ready = [n for n in todo if not (before[n] - done - straight)]
                if not ready:
                    self.warn.append(f'channel {ch}: ordering cycle among {todo}')
                    ready = todo[:1]
                n = ready[0]
                t = max([track[m] + 1 for m in before[n] if m in track] or [0])
                y0, y1, _ = info[n]
                while (any(overlap(y0, y1, a, b) for a, b in used[t])
                       or not self.vfree(g(lo + (t + 0.5) * P), y0, y1, n)):
                    t += 1
                track[n] = t
                used[t].append((y0, y1))
                self.vlines.append((g(lo + (t + 0.5) * P), y0, y1, n))
                done.add(n)
                todo.remove(n)
            ntr = max(track.values(), default=-1) + 1
            if lo + ntr * P > hi:
                self.warn.append(f'channel {ch}: {ntr} tracks need {ntr * P:.1f} mm, have {hi - lo:.1f}')
            for net in nets:
                pts = att[net][ch]
                if info[net][2]:
                    self.w(net, pts[0][2], pts[1][2])
                    continue
                x = g(lo + (track[net] + 0.5) * P)
                for y, side, at in pts:
                    self.w(net, at, (x, at[1]))
                self.w(net, (x, info[net][0]), (x, info[net][1]))
                if net in bridge_y:
                    bridge_xs[net].append(x)
        for net, xs in bridge_xs.items():
            xs = sorted(xs)
            self.w(net, (xs[0], bridge_y[net]), (xs[-1], bridge_y[net]))
        self.junctions()
        self.body_check()

    def body_check(self):
        """Geometric proof: no routed wire passes through a part's body."""
        for r, (p, _, _) in self.parts.items():
            x0, x1, y0, y1 = box(p.sym, p.angle, p.mirror)
            if isinstance(p.sym, IC):          # pin ends are 2.54 outside the body
                bx0, bx1, by0, by1 = p.x + x0 + P, p.x + x1 - P, p.y + y0, p.y + y1
            else:
                bx0, bx1, by0, by1 = p.x + x0, p.x + x1, p.y + y0, p.y + y1
            for net, segs in self.segs.items():
                for (ax, ay), (cx, cy) in segs:
                    if (min(ax, cx) < bx1 - 0.1 and max(ax, cx) > bx0 + 0.1
                            and min(ay, cy) < by1 - 0.1 and max(ay, cy) > by0 + 0.1):
                        self.warn.append(f'wire of {net} crosses {r}')

    def junctions(self):
        """A dot wherever three or more wire ends/passes of one net meet."""
        for net, segs in self.segs.items():
            pts = set()
            for a, b in segs:
                pts.add(a)
                pts.add(b)
            for p in pts:
                deg = 0
                for a, b in segs:
                    if p == a or p == b:
                        deg += 1
                    elif a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1]):
                        deg += 2
                    elif a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0]):
                        deg += 2
                if deg >= 3:
                    self.s.junction(p)

    # ---------------- crystal, routed by hand beside the 8284
    def hand_crystal(self):
        s = self.s
        u = self.parts['U701'][0]
        x1, x2 = u.pin('17'), u.pin('16')
        c = self.nl['comps']['Y701']
        xt = Stock(c['lib'], c['part'])
        cx, cy = g(x1[0] - 12.7), g(x1[1] - 7.62)
        y = self.s.ic('Y701', xt, cx, cy, value=c['value'], ref_at=(cx - 2.54, cy - 3.81),
                      val_at=(cx + 2.54, cy - 3.81))
        self.parts['Y701'] = (y, 'TOP', 0)
        p2, p1 = y.pin('2'), y.pin('1')
        xk = g(x1[0] - 5.08)
        s.wire(p2, (xk, p2[1]), (xk, x1[1]), x1)
        xl = g(p1[0] - 2.54)
        s.wire(p1, (xl, p1[1]), (xl, x2[1]), x2)

    def build(self):
        self.refmap = {}
        self.place_all()
        self.parts['Y701'] = (None, 'TOP', 0)
        rank = {'TOP': 0, 'BOT': 1}
        order = sorted(self.parts, key=lambda r: (rank[self.parts[r][1]], self.parts[r][2],
                                                  self.parts[r][0].y if self.parts[r][0] else 0,
                                                  self.parts[r][0].x if self.parts[r][0] else 0))
        counters = {}
        for r in order:
            pre = re.match(r'[A-Z]+', r).group(0)
            counters[pre] = counters.get(pre, 0) + 1
            self.refmap[r] = f'{pre}{counters[pre]}'
        del self.parts['Y701']
        self.draw()
        for r, (p, _, _) in self.parts.items():
            p.ref = self.refmap[r]
        s = self.s
        rx, ry = self.rcol
        s.text(f"{self.refmap['R401']}-{self.refmap['R419']}: 220 ohm", (rx - 5.08, ry - 7.62))
        s.text('Skeet Shoot 8088 computer on one sheet. Every connection is a drawn wire; the address and '
               'data buses are continuous bus lines across the middle (A[0..19], D[0..7]), each chip joining\n'
               'through bus entries (labels name the members). Top: clock, 8088, latches and buffers, '
               '8253 timer + speaker, 8259 interrupts. Bottom: I/O decode, 8255, LED bar, display, switches; memory.\n'
               'CLOCK AND RESET (8284A, 12 MHz crystal, RC reset) ARE RECONSTRUCTED (2026): not in the 2007 '
               'drawings. IC power pins are implied (VCC/GND) as on the printed figures.\n'
               'Includes the 2026 corrections listed on each figure sheet and in README.txt (wiring that differs '
               'from the 2007 printout).', (70, 24))
        path = s.save(os.path.join(OUT, PROJECT + '.kicad_sch'))
        upright_fields(path)
        json.dump(self.refmap, open(os.path.join(OUT, 'refmap.json'), 'w'), indent=1, sort_keys=True)
        json.dump({'meta': {'filename': PROJECT + '.kicad_pro', 'version': 1}},
                  open(os.path.join(OUT, PROJECT + '.kicad_pro'), 'w'), indent=2)
        write_lib(os.path.join(OUT, 'skeet8088.kicad_sym'), self.syms.values())
        libs = [('skeet8088', '${KIPRJMOD}/skeet8088.kicad_sym')] + [
            (n, '${KICAD10_SYMBOL_DIR}/' + n + '.kicad_sym') for n in ('power', 'Device', 'Switch')]
        open(os.path.join(OUT, 'sym-lib-table'), 'w', newline='\n').write(
            '(sym_lib_table\n  (version 7)\n' +
            ''.join(f'  (lib (name "{n}")(type "KiCad")(uri "{u}")(options "")(descr ""))\n' for n, u in libs) +
            ')\n')
        for w in self.warn:
            print('WARNING:', w)
        return path


def upright_fields(path):
    """kgen writes field angles of 0; KiCad turns fields with a rotated symbol,
    so on parts placed at 90/270 the reference and value read vertically. Give
    those fields the symbol's angle so they read horizontally."""
    text = open(path, encoding='utf-8').read()
    out, pos = [], 0
    for m in re.finditer(r'\(symbol \(lib_id "[^"]*"\) \(at [-\d.]+ [-\d.]+ (90|270)\)', text):
        start = m.start()
        end = text.find('(instances', start)
        block = text[start:end]
        block = re.sub(r'(\(property "(?:Reference|Value)" "[^"]*" \(at [-\d.]+ [-\d.]+) 0\)',
                       lambda mm: f'{mm.group(1)} {m.group(1)})', block)
        out.append(text[pos:start])
        out.append(block)
        pos = end
    out.append(text[pos:])
    open(path, 'w', encoding='utf-8', newline='\n').write(''.join(out))


def build():
    return Flat().build()


if __name__ == '__main__':
    print(build())
