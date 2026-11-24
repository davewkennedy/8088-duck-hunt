"""Figure 1: Microprocessor Subsystem (8088, minimum mode).
Scan: website/src/assets/img/8088/fig1.jpg (1400 px; positions read there).

Parts as drawn: U1 8088 (custom symbol, pins/numbers/sides as on the
printout), U3 and U6 74LS245, U4 and U5 74LS373 (drawn on their sides:
D pins on one long edge, Q pins on the other).

What it does (as drawn):
  - U3 (245) buffers AD0-AD7: A side on the multiplexed bus, B side to the
    other sheets; DIR <- DT/R (pin 27), G <- DEN (pin 26).
  - U4 (373) latches AD0-AD7 (taps with dots on each AD row); LE <- ALE,
    OE to ground.
  - U5 (373) latches A12-A19 (A16-A19 are multiplexed with S3-S6);
    LE <- ALE, OE to ground.
  - U6 (245) buffers A8-A11 (the DIAGONAL wires, kept) and IO/M, WR, RD;
    A7 tied to VCC; DIR to VCC (always A -> B), G to ground. Fig 3's
    "245 Pin 12 /RD" and "245 Pin 13 /WR" are U6 B6/B5.
  - MN/MX (pin 33) to VCC = minimum mode, so the max-mode pin names S0-S2,
    LOCK, QS0 carry their min-mode meaning written beside them (DEN, DT/R,
    IO/M, WR, ALE): kept as drawn.
  - NMI, RQ/GT0 (HOLD) and TEST tied to ground (INTR: see correction 3).

CORRECTED FROM THE 2007 PRINTOUT (David's rule: real wiring errors are
fixed and noted on the sheet):
  1. The vertical from U3 DIR (pin 1) up to DT/R crosses the eight A0-A7
     rows with a junction DOT on each, which would short DIR to the whole
     data bus (and all eight data lines to each other). The dots are
     removed: the wires only cross.
  2. U1 RST was labelled "8284 Pin 11". On the 8284A, pin 11 is the ~{RES}
     INPUT; the RESET OUTPUT that drives the 8088 is pin 10. Relabelled
     "8284 Pin 10".
  3. INTR (pin 18) was tied to the ground line with NMI, HOLD and TEST.
     Fig 6 sends the 8259's INT (pin 17) to "8088 Pin 18: INTR", and
     skeet.asm runs on the IR7 timer interrupt (OCW1 7FH): grounding INTR
     would kill every interrupt and short the 8259's output. INTR now
     leaves the ground line and gets the label "8259 Pin 17: INT"; the
     ground vertical starts at NMI (a corner, so no dot there any more).
  4. QS1 (pin 24) was an open stub. In minimum mode pin 24 is ~{INTA}, and
     Fig 6 expects "8088 Pin 24: QS1/INTA" to drive the 8259's INTA (pin
     26); without it the 8259 can never be acknowledged. The stub now ends
     in the label "8259 Pin 26: INTA". (The ALE jog just above it was
     lifted half a grid so the two rows can't touch.)

Quirks kept as drawn:
  - Pin 34 is named BHE (the 8086 name; on the 8088 it is SS0); open stub.
  - RQ/GT1 (pin 30) and BHE (34) end in short open wire stubs.
  - All B and Q pins (U3, U6 B0-B7; U4, U5 Q0-Q7) are open stubs: they go
    to the other sheets on the original, with no labels.
  - The 8088 CLK pin's clock-edge triangle is not reproduced (plain pin).

The scan is rotated about 1.4 degrees; D() undoes that before P().
"""
from common import IC, Stock, P, sheet, caption, save, PITCH

K = 0.024   # scan rotation: horizontals rise 0.024 px per px to the right


def D(x, y):
    """Scan pixel -> sheet mm, after undoing the scan's rotation."""
    return P(x - K * (y - 500), y + K * (x - 700))


def DX(x, y=500):
    return D(x, y)[0]


def DY(y, x=700):
    return D(x, y)[1]


# 8088 as drawn: left AD0-AD7, CLK, then the inputs; right A8-A19 and the
# status/control pins, with the printout's gaps between groups.
L = [('16', 'AD0', 0), ('15', 'AD1', 1), ('14', 'AD2', 2), ('13', 'AD3', 3),
     ('12', 'AD4', 4), ('11', 'AD5', 5), ('10', 'AD6', 6), ('9', 'AD7', 7),
     ('19', 'CLK', 9), ('18', 'INTR', 11), ('33', 'MX', 12), ('17', 'NMI', 13),
     ('22', 'READY', 14), ('31', 'RQ/GT0', 15), ('30', 'RQ/GT1', 16),
     ('21', 'RST', 17), ('23', 'TEST', 18)]
R = [('8', 'A8', 0), ('7', 'A9', 1), ('6', 'A10', 2), ('5', 'A11', 3), ('4', 'A12', 4),
     ('3', 'A13', 5), ('2', 'A14', 6), ('39', 'A15', 7), ('38', 'A16/S3', 9),
     ('37', 'A17/S4', 10), ('36', 'A18/S5', 11), ('35', 'A19/S6', 12),
     ('26', '~{S0}', 14), ('27', 'S1', 15), ('28', 'S2', 16), ('34', '~{BHE}', 18),
     ('29', 'LOCK', 19), ('25', 'QS0', 20), ('24', 'QS1', 21), ('32', 'RD', 22)]
LTYPE = {'AD': 'bidirectional'}
CPU8088 = IC('8088', '8088',
             [(n, nm, 'L', s, 'bidirectional' if nm.startswith('AD') else 'input') for n, nm, s in L] +
             [(n, nm, 'R', s, 'output') for n, nm, s in R],
             w=25.4, h=60.96)

# 74LS245 as drawn for U6 (A, DIR, G left; B right). U3 is its mirror image.
LS245 = IC('74LS245', '74LS245',
           [(str(2 + i), f'A{i}', 'L', i, 'bidirectional') for i in range(8)] +
           [('1', 'DIR', 'L', 9, 'input'), ('19', 'G', 'L', 10, 'input')] +
           [(str(18 - i), f'B{i}', 'R', i, 'bidirectional') for i in range(8)],
           w=15.24, h=30.48)

# 74LS373 drawn on its side as U5: Q0-Q7 along the top, D0-D7, LE, OE along
# the bottom. U4 is the same drawing flipped (D on top).
QN = ['2', '5', '6', '9', '12', '15', '16', '19']
DN = ['3', '4', '7', '8', '13', '14', '17', '18']
LS373 = IC('74LS373', '74LS373',
           [(QN[i], f'Q{i}', 'T', i, 'tri_state') for i in range(8)] +
           [(DN[i], f'D{i}', 'B', i, 'input') for i in range(8)] +
           [('11', 'LE', 'B', 9, 'input'), ('1', '~{OE}', 'B', 10, 'input')],
           w=30.48, h=15.24)


def build():
    s = sheet(1, 'Microprocessor Subsystem')
    vcc, gnd = Stock('power', 'VCC'), Stock('power', 'GND')

    u1x, u1y = D(570, 323)
    u1 = s.ic('U1', CPU8088, u1x, u1y, ref_at=D(570, 303), val_at=D(578, 688))
    # U3 mirrored: its origin is the body's top RIGHT corner; rows level with U1.
    u3 = s.ic('U3', LS245, DX(190, 336), u1y, mirror='y', ref_at=D(168, 315), val_at=D(140, 525))
    # U6 rows: WR (U1 slot 19) runs straight into A5 (slot 5) -> 14 pitches lower.
    u6 = s.ic('U6', LS245, DX(1210, 507), u1y + 14 * PITCH, ref_at=D(1207, 485), val_at=D(1212, 698))
    u5 = s.ic('U5', LS373, *D(945, 125), ref_at=D(1122, 130), val_at=D(1122, 148))
    # U4 flipped: origin is the body's bottom-left corner.
    u4 = s.ic('U4', LS373, *D(282, 800), mirror='x', ref_at=D(258, 722), val_at=D(224, 742))

    # --- AD bus: U3 A0-A7 straight to U1 AD0-AD7; taps with dots down to U4 D0-D7.
    for i in range(8):
        a, ad = u3.pin(str(2 + i)), u1.pin(L[i][0])
        s.wire(a, ad)
        d = u4.pin(DN[i])
        tap = (d[0], a[1])
        s.wire(tap, d)
        s.junction(tap)

    # --- U3 DIR <- DT/R (outer loop), G <- DEN (inner loop), over the top.
    # Correction 1: the DIR vertical CROSSES the A rows (no dots).
    ydir, yg = DY(292, 232), DY(306, 247)
    xdt, xden = DX(792, 400), DX(779, 400)
    dir3, g3 = u3.pin('1'), u3.pin('19')
    p27, p26 = u1.pin('27'), u1.pin('26')
    xv = DX(232, 400)
    s.wire(dir3, (xv, dir3[1]), (xv, ydir), (xdt, ydir), (xdt, p27[1]), p27)
    xg = DX(247, 400)
    s.wire(g3, (xg, g3[1]), (xg, yg), (xden, yg), (xden, p26[1]), p26)

    # --- 8284: CLK, READY, RST (correction 2: RESET is 8284 pin 10).
    rst = u1.pin('21')
    lx = DX(237, 580)
    y10, y5, y8 = rst[1], rst[1] - PITCH, rst[1] - 2 * PITCH
    s.wire(rst, (lx, y10))
    clk, rdy = u1.pin('19'), u1.pin('22')
    x460, x475 = DX(460, 510), DX(475, 555)
    s.wire(clk, (x460, clk[1]), (x460, y8), (lx, y8))
    s.wire(rdy, (x475, rdy[1]), (x475, y5), (lx, y5))
    for text, y in [('8284 Pin 8', y8), ('8284 Pin 5', y5), ('8284 Pin 10', y10)]:
        s.glabel(text, (lx, y), side='L')

    # --- Ground bus along the bottom.
    ybus = DY(823, 483)
    xg5 = DX(503, 650)
    # Correction 3: INTR comes from the 8259, not ground.
    intr = u1.pin('18')
    xint = DX(530, 494)
    s.wire(intr, (xint, intr[1]))
    s.glabel('8259 Pin 17: INT', (xint, intr[1]), side='L')
    nmi = u1.pin('17')                    # the ground vertical now starts here (corner)
    s.wire(nmi, (xg5, nmi[1]), (xg5, ybus))
    for n in ['31', '23']:                # RQ/GT0 (HOLD), TEST
        p = u1.pin(n)
        s.wire(p, (xg5, p[1]))
        s.junction((xg5, p[1]))
    xgnd = DX(552, 880)
    s.wire((xgnd, ybus), (xgnd, DY(930, 552)))
    s.power(gnd, (xgnd, DY(930, 552)))
    xbus_l, xr = DX(483, 780), DX(1370, 500)
    s.wire((xbus_l, ybus), (xr, ybus))
    s.junction((xg5, ybus), (xgnd, ybus))

    # U4 OE: up, right, down onto the bus's left end (inner loop).
    oe4 = u4.pin('1')
    y657 = DY(657, 450)
    s.wire(oe4, (oe4[0], y657), (xbus_l, y657), (xbus_l, ybus))
    # U5 OE: down, right to the right border, down to the bus.
    oe5 = u5.pin('1')
    y250 = DY(250, 1230)
    s.wire(oe5, (oe5[0], y250), (xr, y250), (xr, ybus))
    # U6 G: left, down, left, down onto the bus (dot).
    g6 = u6.pin('19')
    x1170, y709, x1071 = DX(1170, 690), DY(709, 1120), DX(1071, 760)
    s.wire(g6, (x1170, g6[1]), (x1170, y709), (x1071, y709), (x1071, ybus))
    s.junction((x1071, ybus))

    # --- VCC: top symbol down to MX (min mode); a dot feeds U6 A7.
    xv5 = DX(400, 400)
    vtop = (xv5, DY(110, 393))
    mx = u1.pin('33')
    s.power(vcc, vtop)
    s.wire(vtop, (xv5, mx[1]), mx)
    yv = DY(215, 397)
    xr7 = DX(897, 400)
    a7 = u6.pin('9')
    s.wire((xv5, yv), (xr7, yv), (xr7, a7[1]), a7)
    s.junction((xv5, yv))
    # U6 DIR <- VCC (the "VCC O-" at the bottom middle).
    d6 = u6.pin('1')
    x1070, y682 = DX(1070, 665), DY(682, 1030)
    vdir = (DX(993, 682), y682)
    s.wire(d6, (x1070, d6[1]), (x1070, y682), vdir)
    s.power(vcc, vdir, angle=90)

    # --- U1 right side.
    # A8-A11: the DIAGONAL wires to U6 A0-A3.
    xle5 = u5.pin('11')[0]
    for k, (n, m) in enumerate([('8', '2'), ('7', '3'), ('6', '4'), ('5', '5')]):
        p, t = u1.pin(n), u6.pin(m)
        xs = DX(758 - 6 * k, p[1])
        xe = max(DX(1090 + 5 * k, 530), xle5 + 2 * 1.27 + 1.27 * k)
        s.wire(p, (xs, p[1]), (xe, t[1]), t)
    # A12-A19 -> U5 D0-D7 (nested L shapes).
    for n, dn in zip(['4', '3', '2', '39', '38', '37', '36', '35'], DN):
        p, d = u1.pin(n), u5.pin(dn)
        s.wire(p, (d[0], p[1]), d)
    # IO/M -> U6 A4, WR -> U6 A5 (straight), RD -> U6 A6.
    x1040 = DX(1040, 600)
    p28, a4 = u1.pin('28'), u6.pin('6')
    s.wire(p28, (x1040, p28[1]), (x1040, a4[1]), a4)
    s.wire(u1.pin('29'), u6.pin('7'))
    p32, a6 = u1.pin('32'), u6.pin('8')
    s.wire(p32, (x1040, p32[1]), (x1040, a6[1]), a6)
    # ALE (pin 25): jog to the dot; up to U5 LE, down and round to U4 LE.
    ale = u1.pin('25')
    xa1, xj = DX(786, 625), DX(815, 600)
    ya = ale[1] + 1.27                    # half a grid below QS0: clear of the QS1/INTA row
    s.wire(ale, (xa1, ale[1]), (xa1, ya), (xj, ya))
    s.junction((xj, ya))
    ytop = u6.pin('2')[1] - 1.27          # just above U6 A0's row, as drawn
    s.wire((xj, ya), (xj, ytop), (xle5, ytop), u5.pin('11'))
    le4 = u4.pin('11')
    y715, x493, y643 = DY(715, 700), DX(493, 680), DY(643, 450)
    s.wire((xj, ya), (xj, y715), (x493, y715), (x493, y643), (le4[0], y643), le4)
    # Open stubs as drawn: RQ/GT1, BHE.
    for n, x in [('30', 533), ('34', 761)]:
        p = u1.pin(n)
        s.wire(p, (DX(x, 600), p[1]))
    # Correction 4: QS1 = ~{INTA} in minimum mode, to the 8259. The label sits
    # at the old stub's end: further right, this row is U6 A7's VCC row.
    qs1 = u1.pin('24')
    xinta = DX(761, 600)
    s.wire(qs1, (xinta, qs1[1]))
    s.glabel('8259 Pin 26: INTA', (xinta, qs1[1]), side='R')

    # Min-mode names written beside the max-mode pins, as on the printout.
    for text, (x, y) in [('~{DEN}', (742, 524)), ('DT/~{R}', (742, 538)),
                         ('~{IO}/M', (742, 552)), ('~{WR}', (752, 595)), ('ALE', (748, 609))]:
        s.text(text, D(x, y))

    s.text('Corrected from the 2007 printout:\n'
           '- U3 DIR line (from DT/R): the dots on all eight A0-A7\n'
           '  rows would short DIR to the data bus; removed.\n'
           '- RST from 8284 pin 10 (RESET out), not pin 11 (~{RES} in).\n'
           '- INTR (18) from 8259 INT (17), not ground; QS1/~{INTA} (24)\n'
           '  to 8259 INTA (26), not an open stub (Fig 6, IR7 timer\n'
           '  interrupt in skeet.asm).', D(140, 880))
    caption(s, 'Figure 1: Microprocessor\nSubsystem', D(80, 990))
    return save(s, 'fig1-cpu.kicad_sch')


if __name__ == '__main__':
    print(build())
