"""kgen: write KiCad schematics (.kicad_sch) from short Python descriptions.

Used to redraw David Kennedy's 2007 8088 schematics (scanned printouts; the
original OrCAD files are lost) as editable KiCad files, keeping the original
layout. Each figure is a script in ../figures that builds a Sheet and saves it.

Coordinates are in schematic millimetres, y pointing DOWN (KiCad's sheet
convention). Everything snaps to the 1.27 mm grid; IC pins are 2.54 mm apart,
like the originals (0.1 inch).

  s = Sheet('Figure 3: Memory Subsystem - RAM')
  ram = s.ic('U1', RAM6264, x, y)        # place a symbol (body top-left)
  s.wire(label_pt, ram.pin('10'))        # wire between points / pins
  s.glabel('A0', label_pt, side='L')     # off-page connector, like OrCAD's
  s.save(path)

Symbols are defined with IC(...) (custom, matching the originals' pin order
and sides) or taken from KiCad's stock library with Stock(...).
"""
import os
import re
import uuid as _uuid

GRID = 1.27
PITCH = 2.54


def g(v):
    """Snap to the 1.27 mm grid."""
    return round(round(v / GRID) * GRID, 4)


def U():
    return str(_uuid.uuid4())


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


FONT = '(effects (font (size 1.27 1.27)))'
FONT_HIDE = '(effects (font (size 1.27 1.27)) (hide yes))'


# --------------------------------------------------------------------------
# Symbols
# --------------------------------------------------------------------------
class IC:
    """A rectangular part. pins: list of (number, name, side, slot, type).
    side: 'L', 'R', 'T', 'B'. slot: position along that side in pitches,
    counted from the top (L/R) or from the left (T/B). Names may use KiCad
    overbar syntax ~{OE}. type: input, output, bidirectional, passive,
    power_in, tri_state, open_collector."""

    def __init__(self, name, value, pins, w, h, pin_len=5.08, prefix='U',
                 pad=PITCH, show_pin_names=True):
        self.name, self.value, self.pins = name, value, pins
        self.w, self.h, self.pin_len, self.prefix, self.pad = w, h, pin_len, prefix, pad
        self.show_pin_names = show_pin_names

    # pin electrical end, in symbol coordinates (y up), and its angle
    def pin_geom(self, num):
        for n, name, side, slot, typ in self.pins:
            if n == num:
                L, p = self.pin_len, self.pad + slot * PITCH
                if side == 'L':
                    return (-L, -p), 0
                if side == 'R':
                    return (self.w + L, -p), 180
                if side == 'T':
                    return (p, L), 270
                if side == 'B':
                    return (p, -self.h - L), 90
        raise KeyError(f'{self.name}: no pin {num}')

    def lib(self, libname):
        nm = f'{libname}:{self.name}'
        out = [f'(symbol {q(nm)}']
        if not self.show_pin_names:
            out.append(' (pin_names (hide yes))')
        else:
            out.append(' (pin_names (offset 0.762))')
        out.append(' (exclude_from_sim no) (in_bom yes) (on_board yes)')
        out.append(f' (property "Reference" {q(self.prefix)} (at 0 2.54 0) {FONT})')
        out.append(f' (property "Value" {q(self.value)} (at 0 {-self.h - 2.54} 0) {FONT})')
        out.append(f' (property "Footprint" "" (at 0 0 0) {FONT_HIDE})')
        out.append(f' (property "Datasheet" "" (at 0 0 0) {FONT_HIDE})')
        out.append(f' (symbol {q(self.name + "_0_1")} (rectangle (start 0 0) '
                   f'(end {self.w} {-self.h}) (stroke (width 0.254) (type default)) '
                   f'(fill (type background))))')
        out.append(f' (symbol {q(self.name + "_1_1")}')
        for n, name, side, slot, typ in self.pins:
            (x, y), a = self.pin_geom(n)
            out.append(f'  (pin {typ} line (at {x} {y} {a}) (length {self.pin_len}) '
                       f'(name {q(name)} {FONT}) (number {q(n)} {FONT}))')
        out.append(' ))')
        return ''.join(out)

    def nums(self):
        return [p[0] for p in self.pins]


class Stock:
    """A symbol copied from KiCad's installed library, e.g. Stock('Device', 'R').
    Pin ends are read from the library so wires land exactly."""
    LIBDIR = None

    def __init__(self, lib, name, prefix=None):
        self.libname, self.name = lib, name
        text = open(os.path.join(Stock.libdir(), lib + '.kicad_sym'), encoding='utf-8').read()
        self.body = extract_symbol(text, name)
        if 'extends' in self.body[:300]:
            raise ValueError(f'{lib}:{name} extends another symbol; pick its parent')
        self.prefix = prefix or re.search(r'\(property "Reference" "([^"]*)"', self.body).group(1)
        self.value = re.search(r'\(property "Value" "([^"]*)"', self.body).group(1)
        self._pins = {}
        for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)'
                             r'.*?\(number "([^"]*)"', self.body, re.S):
            self._pins[m.group(4)] = ((float(m.group(1)), float(m.group(2))), float(m.group(3) or 0))

    @staticmethod
    def libdir():
        if Stock.LIBDIR:
            return Stock.LIBDIR
        for base in [os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'KiCad'),
                     r'C:\Program Files\KiCad']:
            if os.path.isdir(base):
                for v in sorted(os.listdir(base), reverse=True):
                    d = os.path.join(base, v, 'share', 'kicad', 'symbols')
                    if os.path.isdir(d):
                        Stock.LIBDIR = d
                        return d
        raise FileNotFoundError('KiCad symbol library not found')

    def pin_geom(self, num):
        return self._pins[num]

    def lib(self, libname=None):
        body = self.body.replace(f'(symbol "{self.name}"', f'(symbol "{self.libname}:{self.name}"', 1)
        return body

    def nums(self):
        return list(self._pins)


def extract_symbol(text, name):
    i = text.find(f'(symbol "{name}"')
    if i < 0:
        raise KeyError(name)
    depth, j = 0, i
    while True:
        c = text[j]
        if c == '"':
            j = text.index('"', j + 1)
            while text[j - 1] == '\\':
                j = text.index('"', j + 1)
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
        j += 1


def rot(x, y, angle, mirror=None):
    """Symbol coords (y up) -> sheet offset (y down) for a placed symbol."""
    a = angle % 360
    if mirror == 'y':
        x = -x
    if mirror == 'x':
        y = -y
    if a == 0:
        rx, ry = x, y
    elif a == 90:
        rx, ry = -y, x
    elif a == 180:
        rx, ry = -x, -y
    else:
        rx, ry = y, -x
    return rx, -ry


class Placed:
    def __init__(self, sheet, ref, sym, x, y, angle=0, mirror=None, value=None,
                 ref_at=None, val_at=None, hide_value=False, hide_ref=False, fields=None):
        self.sheet, self.ref, self.sym = sheet, ref, sym
        self.x, self.y, self.angle, self.mirror = g(x), g(y), angle, mirror
        self.value = value or sym.value
        self.ref_at, self.val_at, self.hide_value = ref_at, val_at, hide_value
        self.hide_ref = hide_ref
        self.fields = fields or {}

    def pin(self, num):
        (px, py), _ = self.sym.pin_geom(num)
        dx, dy = rot(px, py, self.angle, self.mirror)
        return (g(self.x + dx), g(self.y + dy))

    def sexpr(self, libname, inst_path, project):
        lib_id = f'{libname}:{self.sym.name}' if isinstance(self.sym, IC) else \
            f'{self.sym.libname}:{self.sym.name}'
        mirror = f' (mirror {self.mirror})' if self.mirror else ''
        rx, ry = self.ref_at or (self.x, self.y - 3.81)
        vx, vy = self.val_at or (self.x, self.y + 3.81)
        power = self.sym.prefix.startswith('#')
        out = [f'(symbol (lib_id {q(lib_id)}) (at {self.x} {self.y} {self.angle}){mirror} (unit 1)',
               ' (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)',
               f' (uuid {q(U())})',
               f' (property "Reference" {q(self.ref)} (at {g(rx)} {g(ry)} 0) '
               + (FONT_HIDE if power or self.hide_ref else
                  '(effects (font (size 1.27 1.27)) (justify left))') + ')',
               f' (property "Value" {q(self.value)} (at {g(vx)} {g(vy)} 0) '
               + (FONT_HIDE if self.hide_value else '(effects (font (size 1.27 1.27)) (justify left))') + ')',
               f' (property "Footprint" "" (at {self.x} {self.y} 0) {FONT_HIDE})',
               f' (property "Datasheet" "" (at {self.x} {self.y} 0) {FONT_HIDE})']
        for k, v in self.fields.items():
            out.append(f' (property {q(k)} {q(v)} (at {self.x} {self.y} 0) {FONT_HIDE})')
        for n in self.sym.nums():
            out.append(f' (pin {q(n)} (uuid {q(U())}))')
        out.append(f' (instances (project {q(project)} (path {q(inst_path)} '
                   f'(reference {q(self.ref)}) (unit 1)))))')
        return '\n'.join(out)


# --------------------------------------------------------------------------
# Sheet
# --------------------------------------------------------------------------
class Sheet:
    def __init__(self, title, project, libname='skeet8088', date='Sunday, December 09, 2007',
                 comments=None, paper='A', inst_path=None, netmap=None, pwr_base=0,
                 ref_offset=0):
        """inst_path: for a child sheet in a hierarchy, "/<root uuid>/<sheet
        block uuid>"; None for a standalone/root sheet. netmap: global label
        text -> net name (the system schematic renames the printed off-page
        labels to real signal names). pwr_base: offset for #PWR refs so they
        stay unique across the sheets of a hierarchy."""
        self.title, self.project, self.libname = title, project, libname
        self.inst_path, self.netmap = inst_path, netmap or {}
        self.ref_offset = ref_offset     # U1 -> U101 on sheet 1 of a system
        self.date, self.comments, self.paper = date, comments or [], paper
        self.items, self.parts, self.uuid = [], [], U()
        self.syms = {}
        self.npower = pwr_base

    def _sym(self, sym):
        key = sym.name if isinstance(sym, IC) else f'{sym.libname}:{sym.name}'
        self.syms[key] = sym

    def ic(self, ref, sym, x, y, **kw):
        self._sym(sym)
        if self.ref_offset:
            pre = ref.rstrip('0123456789')
            if pre != ref:
                ref = pre + str(self.ref_offset + int(ref[len(pre):]))
        p = Placed(self, ref, sym, x, y, **kw)
        self.parts.append(p)
        return p

    def power(self, sym, at, angle=0, value=None):
        """Power symbols (VCC/GND): placed so their pin lands on `at`."""
        self._sym(sym)
        self.npower += 1
        (px, py), _ = sym.pin_geom(sym.nums()[0])
        dx, dy = rot(px, py, angle)
        p = Placed(self, f'#PWR{self.npower:03d}', sym, at[0] - dx, at[1] - dy, angle,
                   value=value, val_at=None)
        self.parts.append(p)
        return p

    def wire(self, *pts):
        pts = [(g(x), g(y)) for x, y in pts]
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.items.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) '
                                  f'(stroke (width 0) (type default)) (uuid {q(U())}))')
        return pts[-1]

    def junction(self, *pts):
        for x, y in pts:
            self.items.append(f'(junction (at {g(x)} {g(y)}) (diameter 0) (color 0 0 0 0) '
                              f'(uuid {q(U())}))')

    def noconnect(self, pt):
        self.items.append(f'(no_connect (at {g(pt[0])} {g(pt[1])}) (uuid {q(U())}))')

    def glabel(self, text, at, side='L', shape='input'):
        """Off-page connector. side: where the label sits relative to its wire
        end ('L' = label to the left, wire leaves to the right)."""
        text = self.netmap.get(text, text)
        if text in getattr(self, 'power_labels', {}):
            # System mode: a supply label becomes a real power symbol.
            self.power(self.power_labels[text], at)
            return
        ang, just = {'L': (180, 'right'), 'R': (0, 'left'), 'T': (90, 'left'),
                     'B': (270, 'right')}[side]
        self.items.append(
            f'(global_label {q(text)} (shape {shape}) (at {g(at[0])} {g(at[1])} {ang}) '
            f'(fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just})) '
            f'(uuid {q(U())}) (property "Intersheetrefs" "${{INTERSHEET_REFS}}" '
            f'(at {g(at[0])} {g(at[1])} 0) {FONT_HIDE}))')

    def label(self, text, at, angle=0):
        self.items.append(f'(label {q(text)} (at {g(at[0])} {g(at[1])} {angle}) '
                          f'(fields_autoplaced yes) (effects (font (size 1.27 1.27)) '
                          f'(justify left bottom)) (uuid {q(U())}))')

    def text(self, s, at, size=1.27, angle=0, bold=False, justify='left'):
        b = ' (bold yes)' if bold else ''
        self.items.append(f'(text {q(s)} (exclude_from_sim no) (at {g(at[0])} {g(at[1])} {angle}) '
                          f'(effects (font (size {size} {size}){b}) (justify {justify})) '
                          f'(uuid {q(U())}))')

    def subsheet(self, name, filename, at, size, page):
        """A hierarchical sheet block (root sheet only). Returns the child's
        instance path, to pass to the child Sheet as inst_path."""
        u = U()
        x, y = g(at[0]), g(at[1])
        w, h = g(size[0]), g(size[1])
        self.items.append(
            f'(sheet (at {x} {y}) (size {w} {h}) (exclude_from_sim no) (in_bom yes) '
            f'(on_board yes) (dnp no) (fields_autoplaced yes) '
            f'(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) '
            f'(uuid {q(u)})'
            f' (property "Sheetname" {q(name)} (at {x} {g(y - 0.7)} 0) '
            f'(effects (font (size 1.27 1.27)) (justify left bottom)))'
            f' (property "Sheetfile" {q(filename)} (at {x} {g(y + h + 0.6)} 0) '
            f'(effects (font (size 1.27 1.27)) (justify left top)))'
            f' (instances (project {q(self.project)} (path {q("/" + self.uuid)} '
            f'(page {q(str(page))})))))')
        return f'/{self.uuid}/{u}'

    def save(self, path):
        lib = '\n'.join(s.lib(self.libname) for s in self.syms.values())
        tb = [f'(title {q(self.title)})', f'(date {q(self.date)})']
        for i, c in enumerate(self.comments, 1):
            tb.append(f'(comment {i} {q(c)})')
        ipath = self.inst_path or '/' + self.uuid
        parts = '\n'.join(p.sexpr(self.libname, ipath, self.project) for p in self.parts)
        si = '' if self.inst_path else '\n(sheet_instances (path "/" (page "1")))'
        body = (f'(kicad_sch (version 20231120) (generator "kgen") (generator_version "1.0")\n'
                f'(uuid {q(self.uuid)})\n(paper {q(self.paper)})\n'
                f'(title_block {" ".join(tb)})\n'
                f'(lib_symbols\n{lib}\n)\n' + '\n'.join(self.items) + '\n' + parts +
                si + '\n)\n')
        open(path, 'w', encoding='utf-8', newline='\n').write(body)
        return path


def write_lib(path, syms, libname='skeet8088'):
    """A project symbol library with the custom parts, for editing later."""
    body = '(kicad_symbol_lib (version 20231120) (generator "kgen") (generator_version "1.0")\n'
    for s in syms:
        body += s.lib(libname).replace(f'(symbol "{libname}:{s.name}"', f'(symbol "{s.name}"', 1) + '\n'
    open(path, 'w', encoding='utf-8', newline='\n').write(body + ')\n')
