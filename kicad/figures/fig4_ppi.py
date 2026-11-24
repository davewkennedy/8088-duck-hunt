"""Figure 4: I/O Subsystem - PPI (8255, 74LS138, LN10204 10-LED bar, two
discrete LEDs, 74LS47 + 7-segment display, 4 DIP switch, Button2).
Scans: website .../img/8088/fig4.jpg (positions), schematics/fig4-full.jpg
(print). Title block of the original: "Lab 6: PPI", David Kennedy.
Redrawn by Boomhauer, 2026-11-24.

The scan is rotated about 1.9 degrees (right side low). Positions below were
read off a copy rotated back (u, v in the 1400 px frame, see U/V helpers),
then passed to P()/X()/Y(). Wires follow the original's routes.

CORRECTED FROM THE PRINTOUT (David's rule, 2026-11-24: real errors against
skeet.asm are fixed and noted on the sheet):
 1. The two discrete LEDs (driven by PB2 and PB3) were drawn with the anode
    on the PB wire and the cathode toward the 220 ohm / Vcc side (triangle
    pointing up to the bar at the top). skeet.asm drives them ACTIVE-LOW like
    the whole LED bar: on a shot it writes PB2 = 0 (bool_hit_rightLED = 08H
    -> 0BH) or PB3 = 0 (07H -> 07H), and every flight step writes 0DH/0EH/0FH
    nibbles with a 0 for the lit LED. With the printed polarity the PB pin
    would pull the anode LOW and the cathode sits at Vcc, so neither LED could
    ever light. Here the anode is on the 220 ohm / Vcc side and the cathode on
    the PB wire, exactly as the bar is drawn. Set FIX_LED_POLARITY = False to
    get the printed (reversed) orientation back.

Checked and consistent with skeet.asm: 74LS138 on A4-A6 with IO/M on G1 puts
the PPI (00-03H) on Y0 = 8255 CS; the 8255's A0/A1 (pins 9/8) are on CPU
A0/A1 (consecutive ports 00H, 01H, 02H, 03H; PPI_Command_Word 89H = A and
B out, port C in); PA0-7 and PB0-3 are the 12 flight LEDs (the sequence runs
bottom to top: PB1, PB0, PA7 ... PA0); PB4-7 -> 74LS47 D0-D3 is the score
(score << 4); DIP switches are pull-up to Vcc, closed = 0: PC0-2 are the speed
(the code XORs them with 07H) and PC3 is championship mode, which the code
takes as PC3 = 1, i.e. switch OPEN (not inverted); PC6 = 8253 OUT1 pin 13;
PC7 = Button2 (the ISR NOTs port C: pressed = 0). All 8255, 74LS138 and 74LS47
pin numbers match the datasheets.

Drawing quirks kept as drawn:
 - Power pins (8255 Vcc/GND, 138 and 47 Vcc/GND) are not drawn on the
   original, so they are not drawn here.
 - The 74LS47's LT, RBI and BI/RBO are all tied to Vcc through the verticals
   that run down to the right ends of the 10k resistors (and the display's
   two Vcc pins join the same rail), with a dot wherever the printout has
   one.
 - Open pins as printed get their stub and a no-connect flag: 74LS138
   Y1-Y7, 8255 PC4 and PC5, display LDP and RDP.
 - The 10k pull-ups, the 4 DIP switch, the display and the LED bar are
   custom symbols; the DIP switch is numbered 1-4 left, 5-8 right as printed.
 - The bar's LEDs have their anodes on the 220 ohm / Vcc side and their
   cathodes toward the PA/PB pins, as printed.
 - Stock symbols differ in look from OrCAD's: resistors are boxes, VCC is an
   arrow, GND a triangle, and their value text is level text (s.text) because
   rotated parts would turn it. The 10k and 220 labels overlap as printed.
 - The caption on the original reads top to bottom; common.caption() rotates
   it bottom to top.
"""
from common import IC, Stock, P, X, Y, LS138, PITCH, sheet, caption, save

# False = the printed (reversed) discrete-LED orientation. See docstring.
FIX_LED_POLARITY = True


class GIC(IC):
    """An IC with extra graphics drawn inside (the body rectangle stays)."""

    def __init__(self, *a, extra='', hide_numbers=False, **kw):
        super().__init__(*a, **kw)
        self.extra, self.hide_numbers = extra, hide_numbers

    def lib(self, libname):
        t = super().lib(libname)
        tail = '(fill (type background))))'
        assert tail in t
        t = t.replace(tail, '(fill (type background)))' + self.extra + ')', 1)
        if self.hide_numbers:
            t = t.replace(' (pin_names', ' (pin_numbers (hide yes)) (pin_names', 1)
        return t


def pl(*pts, fill='none', w=0.2):
    xy = ' '.join('(xy %.3f %.3f)' % p for p in pts)
    return f' (polyline (pts {xy}) (stroke (width {w}) (type default)) (fill (type {fill})))'


def rect(x0, y0, x1, y1, fill='none', w=0.2):
    return (f' (rectangle (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) '
            f'(stroke (width {w}) (type default)) (fill (type {fill})))')


# --- the 8255 as drawn: data, address, control left; PA, PB, PC right -------
PA = ['4', '3', '2', '1', '40', '39', '38', '37']
PB = ['18', '19', '20', '21', '22', '23', '24', '25']
PC = ['14', '15', '16', '17', '13', '12', '11', '10']
DPIN = ['34', '33', '32', '31', '30', '29', '28', '27']
I8255 = IC('8255', '8255',
           [(n, 'D%d' % i, 'L', i, 'bidirectional') for i, n in enumerate(DPIN)] +
           [('9', 'A0', 'L', 9, 'input'), ('8', 'A1', 'L', 10, 'input'),
            ('35', 'RESET', 'L', 12, 'input'), ('5', 'RD', 'L', 13, 'input'),
            ('36', 'WR', 'L', 14, 'input'), ('6', 'CS', 'L', 15, 'input')] +
           [(n, 'PA%d' % i, 'R', i, 'bidirectional') for i, n in enumerate(PA)] +
           [(n, 'PB%d' % i, 'R', 9 + i, 'bidirectional') for i, n in enumerate(PB)] +
           [(n, 'PC%d' % i, 'R', 18 + i, 'bidirectional') for i, n in enumerate(PC)],
           w=17.78, h=68.58, pin_len=7.62)

# --- 74LS47 BCD to 7-segment decoder/driver (open-collector outputs) --------
I74LS47 = IC('74LS47', '74LS47', [
    ('7', 'D0', 'L', 0, 'input'), ('1', 'D1', 'L', 1, 'input'),
    ('2', 'D2', 'L', 2, 'input'), ('6', 'D3', 'L', 3, 'input'),
    ('3', '~{LT}', 'L', 5, 'input'), ('5', '~{RBI}', 'L', 6, 'input'),
] + [(n, 'ABCDEFG'[i], 'R', i, 'open_collector') for i, n in enumerate(['13', '12', '11', '10', '9', '15', '14'])] + [
    ('4', '~{BI}/~{RBO}', 'R', 8, 'bidirectional')],
    w=20.32, h=25.4, pin_len=7.62)

# --- LN10204: ten LEDs in one body; pins 20,18..2 (cathodes) and 19,17..1 ---
LED_PINS_L = [str(20 - 2 * i) for i in range(10)]
LED_PINS_R = [str(19 - 2 * i) for i in range(10)]
_g = ''
for _k in range(10):
    _y = -PITCH * (1 + 2 * _k)
    _g += pl((0, _y), (5.08, _y)) + pl((7.62, _y), (10.16, _y)) + pl((5.08, _y + 1.9), (5.08, _y - 1.9))
    _g += pl((5.08, _y), (7.62, _y + 1.7), (7.62, _y - 1.7), (5.08, _y), fill='outline')
    for _tx, _ty in [(3.9, _y + 0.2), (4.7, _y + 0.5)]:      # the two light arrows
        _hx, _hy = _tx - 1.7, _ty + 1.3
        _g += pl((_tx, _ty), (_hx, _hy)) + pl((_hx + 0.9, _hy), (_hx, _hy), (_hx, _hy - 0.9))
LN10204 = GIC('LN10204', 'LN10204',
              [(n, n, 'L', 2 * i, 'passive') for i, n in enumerate(LED_PINS_L)] +
              [(n, n, 'R', 2 * i, 'passive') for i, n in enumerate(LED_PINS_R)],
              w=10.16, h=50.8, pin_len=7.62, prefix='D', show_pin_names=False, extra=_g)

# --- two-digit 7-segment display (common anode: two Vcc pins) ---------------
DISP2 = GIC('DISP2', 'DISP2',
            [(str(i + 1), 'ABCDEFG'[i], 'L', i, 'passive') for i in range(7)] +
            [('8', 'Vcc', 'R', 0, 'passive'), ('9', 'Vcc', 'R', 1, 'passive'),
             ('10', 'LDP', 'R', 5, 'passive'), ('11', 'RDP', 'R', 6, 'passive')],
            w=15.24, h=20.32, pin_len=7.62, prefix='DS', hide_numbers=True,
            extra=rect(5.1, -2.6, 10.3, -12.8) + pl((5.1, -7.7), (10.3, -7.7)))

# --- 4 DIP switch: 1-4 left, 5-8 right as printed ---------------------------
_g = ''
for _k in range(4):
    _y = -PITCH * (1 + _k)
    _g += rect(2.0, _y + 0.9, 10.7, _y - 0.9) + rect(5.4, _y + 0.9, 7.3, _y - 0.9, fill='outline')
DIP4 = GIC('DIP4', '4 DIP Switch',
           [(str(i + 1), str(i + 1), 'L', i, 'passive') for i in range(4)] +
           [(str(i + 5), str(i + 5), 'R', i, 'passive') for i in range(4)],
           w=12.7, h=12.7, pin_len=2.54, prefix='SW', show_pin_names=False, extra=_g)

RES = Stock('Device', 'R')
LED = Stock('Device', 'LED')
BTN = Stock('Switch', 'SW_Push')
VCC = Stock('power', 'VCC')
GND = Stock('power', 'GND')


def build():
    s = sheet(4, 'I/O Subsystem - PPI')
    # The original's own title block says "Lab 6: PPI" / "David Kennedy" (comment 2).
    s.comments.append('Original title block: Lab 6: PPI')
    nres = [0]

    def res(cx, cy, angle, value, val_at=None, hide_value=False):
        """A stock resistor. Its value text would turn with a rotated part and
        the original prints it level, so rotated ones print it with s.text."""
        nres[0] += 1
        rotated = angle % 180 != 0
        r = s.ic('R%d' % nres[0], RES, cx, cy, angle=angle, hide_ref=True, value=value,
                 val_at=val_at, hide_value=hide_value or rotated)
        if rotated and not hide_value and val_at:
            s.text(value, val_at)
        return r

    def vcc(at, angle, text_at):
        """Stock VCC; its value text turns or flips with the part, so level text."""
        p = s.power(VCC, at, angle=angle)
        p.hide_value = True
        s.text('VCC', text_at)
        return p

    def gnd(at, angle=0):
        p = s.power(GND, at, angle=angle)
        p.hide_value = True
        return p

    # ------------------------------------------------------------- 8255 (U1)
    u1 = s.ic('U1', I8255, *P(373.9, 115.4), ref_at=P(374, 97), val_at=P(373, 515))
    lx = X(120)                                  # tips of the left connectors
    for n, nm in zip(DPIN, ['D%d' % i for i in range(8)]):
        p = u1.pin(n)
        s.wire((lx, p[1]), p)
        s.glabel(nm, (lx, p[1]), side='L')
    for n, nm in [('9', 'A0'), ('8', 'A1'), ('35', 'RST'), ('5', '/RD'), ('36', '/WR')]:
        p = u1.pin(n)
        s.wire((lx, p[1]), p)
        s.glabel(nm, (lx, p[1]), side='L')
    cs = u1.pin('6')

    # ----------------------------------------------- 74LS138 (U2): PPI select
    # Top of the 138 level with the 8255's CS row, as drawn (Y0 jogs up one pitch).
    u2 = s.ic('U2', LS138, X(177.5), cs[1], ref_at=P(205, 360), val_at=P(162, 497))
    for n, nm in [('1', 'A4'), ('2', 'A5'), ('3', 'A6'), ('6', 'IO/M')]:
        p = u2.pin(n)
        s.wire((lx, p[1]), p)
        s.glabel(nm, (lx, p[1]), side='L')
    g2a, g2b = u2.pin('4'), u2.pin('5')
    gx, gy = X(107.7), Y(480)
    s.wire(g2a, (gx, g2a[1]), (gx, gy))
    s.wire(g2b, (gx, g2b[1]))
    s.junction((gx, g2b[1]))
    gnd((gx, gy))
    y0 = u2.pin('15')
    jx = X(318)
    s.wire(y0, (jx, y0[1]), (jx, cs[1]), cs)          # Y0 -> 8255 CS
    for n in ['14', '13', '12', '11', '10', '9', '7']:  # Y1-Y7: stubs as drawn
        p = u2.pin(n)
        s.wire(p, (p[0] + PITCH, p[1]))
        s.noconnect((p[0] + PITCH, p[1]))

    # ------------------------------------------------- LED bar D1 + resistors
    d1x = X(834.6)
    d1y = u1.pin('40')[1] - PITCH * 9            # pin 12 level with PA4: straight run
    d1 = s.ic('D1', LN10204, d1x, d1y, ref_at=P(835, 48), val_at=P(863, 51))
    busx = X(1015.9)
    rows = []
    for i in range(10):
        cat, an = d1.pin(LED_PINS_L[i]), d1.pin(LED_PINS_R[i])
        rows.append(an[1])
        r = res(X(961.3), an[1], 90, '220', val_at=(X(954), an[1] + PITCH))
        s.wire(an, r.pin('1'))
        s.wire(r.pin('2'), (busx, an[1]))
        # the PA/PB signal comes in on the cathode pin
    s.wire(*[(busx, y) for y in rows])
    s.junction(*[(busx, y) for y in rows[1:9]])
    vx = X(1044)
    s.wire((busx, rows[4]), (vx, rows[4]), (vx, Y(200.3)))
    vcc((vx, Y(200.3)), 180, (X(1031), Y(246.4)))

    # PA0-PA7, PB0, PB1 -> bar pins 20, 18, 16, 14, 12, 10, 8, 6, 4, 2.
    # Bend x positions (u) as drawn: up for the top four, straight for PA4,
    # down for the rest; they nest 1 pitch apart.
    bars = [('4', '20', 750.8), ('3', '18', 764.9), ('2', '16', 779.0), ('1', '14', 792.8),
            ('40', '12', None), ('39', '10', 792.8), ('38', '8', 779.0), ('37', '6', 764.9),
            ('18', '4', 750.8), ('19', '2', 736.5)]
    for sig, pin, bx in bars:
        a, b = u1.pin(sig), d1.pin(pin)
        if bx is None:
            s.wire(a, b)
        else:
            x = min(X(bx), b[0])
            s.wire(a, (x, a[1]), (x, b[1]), b)

    # ----------------------------------------- discrete LEDs on PB2 and PB3
    xl, xr = X(1114.3), X(1142.0)
    ytop = Y(114.5)
    cy = Y(169.4)
    r1 = res(xl, cy, 0, '220', val_at=(X(1086.6), cy))
    r2 = res(xr, cy, 0, '220', val_at=(X(1156.4), cy))
    vcc((xl, Y(99.8)), 0, (X(1100.2), Y(49.3)))
    s.wire((xl, Y(99.8)), (xl, ytop), r1.pin('1'))
    s.wire((xl, ytop), (xr, ytop), (xr, r2.pin('1')[1]), r2.pin('1'))
    s.junction((xl, ytop))
    ang = 90 if FIX_LED_POLARITY else 270        # 90: anode up (toward Vcc)
    ly = Y(261.3)
    leds = []
    for x, r in [(xl, r1), (xr, r2)]:
        d = s.ic('D%d' % (2 + len(leds)), LED, x, ly, angle=ang, hide_ref=True, hide_value=True)
        leds.append(d)
        top, bot = sorted([d.pin('1'), d.pin('2')], key=lambda p: p[1])
        s.wire(r.pin('2'), top)
    for (sig, bx, ylow), d in zip([('20', 722.4, 352.1), ('21', 708.7, 367.2)], leds):
        a = u1.pin(PB[int(sig) - 18])
        bot = max([d.pin('1'), d.pin('2')], key=lambda p: p[1])
        x = X(bx)
        s.wire(a, (x, a[1]), (x, Y(ylow)), (bot[0], Y(ylow)), bot)

    # --------------------------------------------------- 74LS47 (U3) + display
    u3y = Y(381.3)
    u3 = s.ic('U3', I74LS47, X(708.5), u3y, ref_at=P(751, 402), val_at=P(709, 515))
    ds = s.ic('DS1', DISP2, X(987.6), u3y, hide_ref=True, hide_value=True)
    # PB4-PB7 -> D0-D3 (pins 7, 1, 2, 6), nested bends 1 pitch apart.
    for sig, pin, bx in [('22', '7', None), ('23', '1', 652.8), ('24', '2', 639.3), ('25', '6', 625.7)]:
        a, b = u1.pin(sig), u3.pin(pin)
        x = b[0] if bx is None else X(bx)
        s.wire(a, (x, a[1]), (x, b[1]), b)
    # outputs A-G through 220 ohm resistors to the display.
    rc = X(904.9)
    for i, (n, dn) in enumerate(zip(['13', '12', '11', '10', '9', '15', '14'], range(1, 8))):
        a, b = u3.pin(n), ds.pin(str(dn))
        if i == 0:
            va, hv = P(891, 388), False
        elif i == 6:
            va, hv = P(897, 494), False
        else:
            va, hv = None, True
        r = res(rc, a[1], 90, '220', val_at=va, hide_value=hv)
        s.wire(a, r.pin('1'))
        s.wire(r.pin('2'), b)
    # display Vcc pins: both to the Vcc rail; LDP and RDP are open stubs.
    v0, v1 = ds.pin('8'), ds.pin('9')
    bi = u3.pin('4')
    xret, xd = X(1141.9), X(876.1)
    rail = Y(578.5)
    s.wire(v0, v1)
    s.wire(v1, (xret, v1[1]), (xret, bi[1]), (xd, bi[1]), (xd, rail))
    s.junction(v1)
    s.noconnect(ds.pin('10'))
    s.noconnect(ds.pin('11'))

    # ------------------------------------------------ pull-ups and the rail
    ry = [rail + PITCH * k for k in range(4)]
    rcx = X(771.4)
    rs = []
    for k in range(4):
        r = res(rcx, ry[k], 90, '10k', val_at=(X(767), ry[k] - PITCH / 2))
        rs.append(r)
    xR = [None, X(834.4), X(848.5), bi[0]]       # right-end verticals (R4 = pin end of BI/RBO)
    xv = X(890.7)
    s.wire(rs[0].pin('2'), (xR[1], ry[0]), (xR[2], ry[0]), (xR[3], ry[0]), (xd, ry[0]), (xv, ry[0]))
    s.junction((xR[1], ry[0]), (xR[2], ry[0]), (xR[3], ry[0]), (xd, ry[0]))
    vcc((xv, ry[0]), 270, (X(906), ry[0]))
    # LT, RBI and BI/RBO tie to Vcc down the verticals above the 10k right ends.
    lt, rbi = u3.pin('3'), u3.pin('5')
    s.wire(lt, (X(653.2), lt[1]), (X(653.2), Y(550.3)), (xR[1], Y(550.3)), (xR[1], ry[1]), rs[1].pin('2'))
    s.wire(rbi, (X(667.3), rbi[1]), (X(667.3), Y(536.2)), (xR[2], Y(536.2)), (xR[2], ry[2]), rs[2].pin('2'))
    s.wire(bi, (xR[3], bi[1]), (xR[3], ry[3]), rs[3].pin('2'))

    # ----------------------------------------------- PC0-PC3: DIP + pull-ups
    dip = s.ic('SW2', DIP4, X(778), Y(648.3), hide_ref=True, val_at=P(779, 725))
    jxs = [X(694.4), X(680.8), X(666.8), X(653.2)]
    pcx = [X(597.2), X(583.1), X(569.0), X(555.5)]
    for k in range(4):
        a = u1.pin(PC[k])
        jx_ = jxs[k]
        s.wire(a, (pcx[k], a[1]), (pcx[k], ry[k]), (jx_, ry[k]), rs[k].pin('1'))
        pin = dip.pin(str(k + 1))
        s.wire((jx_, ry[k]), (jx_, pin[1]), pin)
        s.junction((jx_, ry[k]))
    # DIP right side: pins 5-8 to one bus, which also takes the button's low side.
    bx = X(904.2)
    pr = [dip.pin(str(k + 5)) for k in range(4)]
    btnx = X(540.8)
    by = Y(732.8)
    for p in pr:
        s.wire(p, (bx, p[1]))
    s.wire(*[(bx, p[1]) for p in pr], (bx, by), (btnx, by))
    s.junction(*[(bx, p[1]) for p in pr[1:]])
    s.wire((bx, pr[3][1]), (X(945.6), pr[3][1]))
    gnd((X(945.6), pr[3][1]), 90)

    # ----------------------------------------- PC4/PC5 open, PC6, PC7 button
    for n in [PC[4], PC[5]]:
        s.noconnect(u1.pin(n))                   # the pin itself is the stub
    a6 = u1.pin(PC[6])
    y6 = Y(536.2)
    s.wire(a6, (X(541.4), a6[1]), (X(541.4), y6), (X(485), y6))
    s.glabel('To 8253 PIT: OUT1 - Pin 13', (X(485), y6), side='L')
    a7 = u1.pin(PC[7])
    x7 = X(527.3)
    xp = X(513.2)
    s.wire(a7, (x7, a7[1]), (x7, rail))
    s.junction((x7, rail))
    pu = res(xp, Y(658.7), 0, '10k', val_at=(X(486.5) - 1.27, Y(656)))
    btn = s.ic('SW1', BTN, btnx, Y(669.3), angle=90, hide_ref=True, value='Button2', hide_value=True)
    s.text('Button2', P(564, 656))
    btop, bbot = sorted([btn.pin('1'), btn.pin('2')], key=lambda p: p[1])
    s.wire((x7, rail), (xp, rail), pu.pin('1'))
    s.wire((x7, rail), (btnx, rail), btop)
    s.wire(bbot, (btnx, by))
    vy = Y(720.7)
    s.wire(pu.pin('2'), (xp, vy))
    vcc((xp, vy), 180, (X(499), Y(767)))

    s.text('Corrected from the 2007 printout: the two discrete LEDs (PB2, PB3) are now\n'
           'anode to the 220 ohm / Vcc side and cathode to the PB pin, like the LED bar.\n'
           'The printout had them reversed, so they could never light; skeet.asm drives\n'
           'both active-low (PB low = on).', P(160, 840))
    caption(s, 'Figure 4: I/O Subsystem - PPI', P(95, 915))
    return save(s, 'fig4-ppi.kicad_sch')


if __name__ == '__main__':
    print(build())
