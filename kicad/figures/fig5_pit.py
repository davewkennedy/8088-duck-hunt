"""Figure 5: Timer Subsystem - PIT (8253, 74LS138, 75452, 1k pot, speaker).
Scans: website .../img/8088/fig5.jpg (positions), schematics/fig5-full.jpg (print).
Redrawn by Bill, 2026-11-24.

CORRECTED FROM THE PRINTOUT (David's rule, 2026-11-24: real errors against
skeet.asm are fixed and noted on the sheet):
 1. 8253 A0/A1 (pins 19/20) were labelled A1/A2. skeet.asm uses four
    CONSECUTIVE ports: PIT_ToSpeaker_Port 40H (counter 0), PIT_ToPPI_Port 41H
    (counter 1), PIT_ToPIC_Port 42H (counter 2) and PIT_Command_Port 43H. With
    A1/A2 on the 8253, port 43H would select counter 1 and the command
    register would sit at 46H/47H, so the code could not program the timer.
    Here: CPU A0 -> 8253 A0, CPU A1 -> 8253 A1 (as Fig 6 does for the 8259).
 2. 8253 CLK1 (15) and CLK2 (18) were drawn open. skeet.asm runs counter 1
    (PIT_ToPPI_Word 70H; the delay loop polls it on PPI bit 40H = PC6, which
    is where OUT1 goes) and counter 2 (PIT_ToPIC_Word 0B6H, "30 msec at 2MHz
    Clock" on IR7, the only interrupt enabled). Neither counts without a
    clock, so here PCLK drives CLK0, CLK1 and CLK2 (the 30 ms figure assumes
    the same 2 MHz clock as the speaker notes on counter 0).

Checked and consistent with skeet.asm: 74LS138 on A4-A6 with IO/M enable puts
the PPI (00-03H) on Y0 and the PIT (40-43H) on Y4 (8253 CS); OUT0 drives the
speaker (counter 0, mode 3 square wave); OUT1 -> 8255 PC6 (pin 11); OUT2 ->
8259 IR7 (pin 25). Pin numbers match the 8253 and SN75452 datasheets.

Drawing quirks kept as drawn:
 - Two junction dots on the pot/Vcc line: the first (just right of the pot)
   sits on a straight run with no branch.
 - The pot is drawn as a plain two-terminal resistor labelled "Pot 1k" (no
   wiper drawn), so it is a stock resistor here.
 - The 8253's clock inputs have OrCAD clock triangles on the original; kgen
   draws plain pins.
 - Unused pins with stubs on the original (74LS138 Y1-Y3, Y5-Y7; 75452 2B, 2A,
   2Y) get the stub and a no-connect flag at its end.
"""
from common import IC, Stock, P, X, Y, LS138, PITCH, sheet, caption, save
from kgen import Placed, g

# 8253 as drawn: address/gate/clock/control on the left, OUTs and data right.
I8253 = IC('8253', '8253', [
    ('19', 'A0', 'L', 0, 'input'), ('20', 'A1', 'L', 1, 'input'),
    ('11', 'G0', 'L', 3, 'input'), ('14', 'G1', 'L', 4, 'input'), ('16', 'G2', 'L', 5, 'input'),
    ('9', 'CLK0', 'L', 7, 'input'), ('15', 'CLK1', 'L', 8, 'input'), ('18', 'CLK2', 'L', 9, 'input'),
    ('22', 'RD', 'L', 11, 'input'), ('23', 'WR', 'L', 12, 'input'), ('21', 'CS', 'L', 13, 'input'),
    ('10', 'OUT0', 'R', 0, 'output'), ('13', 'OUT1', 'R', 1, 'output'), ('17', 'OUT2', 'R', 2, 'output'),
] + [(str(8 - i), 'D%d' % i, 'R', 4 + i, 'bidirectional') for i in range(8)],
    w=17.78, h=38.1)

# SN75452 dual peripheral driver (NAND, open-collector outputs), as drawn.
SN75452 = IC('75452', '75452', [
    ('8', 'Vcc', 'L', 0, 'power_in'), ('7', '2B', 'L', 1, 'input'), ('6', '2A', 'L', 2, 'input'),
    ('5', '2Y', 'L', 3, 'open_collector'),
    ('1', '1A', 'R', 0, 'input'), ('2', '1B', 'R', 1, 'input'), ('3', '1Y', 'R', 2, 'open_collector'),
    ('4', 'GND', 'R', 3, 'power_in'),
], w=17.78, h=17.78)

GND = Stock('power', 'GND')
RES = Stock('Device', 'R')
SPK = Stock('Device', 'Speaker')


def at_pin(sym, pin, at, angle=0, mirror=None):
    """Symbol origin that puts `pin` on `at`."""
    tmp = Placed(None, '', sym, 0, 0, angle, mirror)
    px, py = tmp.pin(pin)
    return at[0] - px, at[1] - py


def stub(s, pin_pt, x):
    """An unused pin drawn with a stub on the original: stub + no-connect."""
    s.wire(pin_pt, (x, pin_pt[1]))
    s.noconnect((x, pin_pt[1]))


def build():
    s = sheet(5, 'Timer Subsystem - PIT')
    pit = s.ic('U1', I8253, *P(683, 258), hide_ref=True, val_at=P(683, 482))
    # Line the 138 up so its Y4 (pin 11) meets the 8253's CS (pin 21) straight.
    cs = pit.pin('21')
    dec = s.ic('U2', LS138, X(307), cs[1] - (1 + 4) * PITCH, hide_ref=True, val_at=P(307, 526))
    drv = s.ic('U3', SN75452, *P(725, 568), hide_ref=True, val_at=P(757, 676))

    lx = X(170)   # tip of the left-hand off-page connectors
    # CORRECTED: the printout labels these A1/A2; skeet.asm needs A0/A1 (see docstring).
    for txt, n in [('A0', '19'), ('A1', '20')]:
        p = pit.pin(n)
        s.glabel(txt, (lx, p[1]), side='L')
        s.wire((lx, p[1]), p)
    # Vcc ties G0, G1 and G2 high (two dots on the Vcc line, as drawn).
    g0, g1, g2 = pit.pin('11'), pit.pin('14'), pit.pin('16')
    j1, j2 = (X(611), g0[1]), (X(625), g0[1])
    s.glabel('Vcc', (lx, g0[1]), side='L')
    s.wire((lx, g0[1]), j1, j2, g0)
    s.wire(j1, (j1[0], g2[1]), g2)
    s.wire(j2, (j2[0], g1[1]), g1)
    s.junction(j1, j2)
    # PCLK, /RD, /WR come in above and drop down to CLK0, RD, WR.
    for txt, y, x, n in [('PCLK', 348, 585, '9'), ('/RD', 362, 570, '22'), ('/WR', 376, 556, '23')]:
        p = pit.pin(n)
        s.glabel(txt, (lx, Y(y)), side='L')
        s.wire((lx, Y(y)), (X(x), Y(y)), (X(x), p[1]), p)
    # CORRECTED: CLK1 and CLK2 were open on the printout; skeet.asm runs counters
    # 1 and 2, so the PCLK drop continues down to them (see docstring).
    c0, c1, c2 = pit.pin('9'), pit.pin('15'), pit.pin('18')
    px = X(585)
    s.wire((px, c0[1]), (px, c2[1]), c2)
    s.wire((px, c1[1]), c1)
    s.junction((px, c0[1]), (px, c1[1]))

    # 74LS138: A4-A6 select, IO/M enables, G2A/G2B grounded.
    for txt, n in [('A4', '1'), ('A5', '2'), ('A6', '3'), ('IO/M', '6')]:
        p = dec.pin(n)
        s.glabel(txt, (lx, p[1]), side='L')
        s.wire((lx, p[1]), p)
    g2a, g2b = dec.pin('4'), dec.pin('5')
    gx = X(237)
    s.wire(g2a, (gx, g2a[1]), (gx, Y(530)))
    s.wire(g2b, (gx, g2b[1]))
    s.junction((gx, g2b[1]))
    s.power(GND, (gx, Y(530)))
    y0 = dec.pin('15')
    s.wire(y0, (X(460), y0[1]))
    s.glabel('8255 #6:CS', (X(460), y0[1]), side='R')
    s.wire(dec.pin('11'), cs)   # Y4 -> 8253 CS
    for n in ['14', '13', '12', '10', '9', '7']:
        stub(s, dec.pin(n), X(432))

    # 8253 outputs and data bus.
    out0 = pit.pin('10')
    one_b = drv.pin('2')
    s.wire(out0, (X(1043), out0[1]), (X(1043), one_b[1]), one_b)
    for txt, n in [('8255: PC6 - Pin 11', '13'), ('8259: IR7 - Pin 25', '17')]:
        p = pit.pin(n)
        s.wire(p, (X(848), p[1]))
        s.glabel(txt, (X(848), p[1]), side='R')
    for i in range(8):
        p = pit.pin(str(8 - i))
        s.wire(p, (X(960), p[1]))
        s.glabel('D%d' % i, (X(960), p[1]), side='R')

    # Speaker driver: pot from Vcc to the speaker, 75452 gate 1 (1A = Vcc,
    # 1B = OUT0) pulls the speaker's + side low through 1Y.
    # The value would turn with the rotated resistor; the original prints it level, so: text.
    pot = s.ic('R1', RES, *at_pin(RES, '2', P(519, 527), angle=90), angle=90, hide_ref=True,
               value='Pot 1k', hide_value=True)
    s.text('Pot  1k', P(515, 506))
    pl, pr = pot.pin('2'), pot.pin('1')
    if pl[0] > pr[0]:
        pl, pr = pr, pl
    vj = (X(585), pr[1])
    s.wire(pr, (X(570), pr[1]), vj, (X(594), pr[1]))
    s.junction((X(570), pr[1]), vj)
    s.glabel('Vcc', (X(594), pr[1]), side='R')
    vcc = drv.pin('8')
    bj = (vj[0], Y(555))
    s.wire(vj, bj, (vj[0], vcc[1]), vcc)
    one_a = drv.pin('1')
    s.wire(bj, (X(833), bj[1]), (X(833), one_a[1]), one_a)
    s.junction(bj)
    gnd = drv.pin('4')
    s.wire(gnd, (X(833), gnd[1]), (X(833), Y(660)))
    s.power(GND, (X(833), Y(660)))
    for n in ['7', '6', '5']:
        stub(s, drv.pin(n), X(683))

    # Speaker terminals on its right: "-" above, "+" below (pins 1 and 2).
    spk = s.ic('LS1', SPK, *at_pin(SPK, '1', P(418, 613), mirror='y'), mirror='y',
               hide_ref=True, val_at=P(377, 666))
    minus, plus = spk.pin('1'), spk.pin('2')
    s.text('-', (minus[0] - 4.6, minus[1]))
    s.text('+', (plus[0] - 4.6, plus[1]))
    s.wire(minus, (X(460), minus[1]), (X(460), pl[1]), pl)
    sj = (X(460), plus[1])
    one_y = drv.pin('3')
    s.wire(plus, sj, (sj[0], Y(693)), (X(891), Y(693)), (X(891), one_y[1]), one_y)
    s.junction(sj)

    s.text('Corrected from the 2007 printout: 8253 A0/A1 on CPU A0/A1 (printed as A1/A2; '
           'skeet.asm uses ports 40H-43H,\ncommand at 43H), and CLK1/CLK2 on PCLK with CLK0 '
           '(printed open; skeet.asm runs counters 1 and 2).', P(160, 865))
    caption(s, 'Figure 5: Timer\nSubsystem - PIT', P(95, 990))
    return save(s, 'fig5-pit.kicad_sch')


if __name__ == '__main__':
    print(build())
