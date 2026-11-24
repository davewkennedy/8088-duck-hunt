"""Figure 6: Interrupt Subsystem - PIC (8259A, 74LS138).
Scans: website .../img/8088/fig6.jpg (positions), schematics/fig6-full.jpg (print).
Redrawn by Bill, 2026-11-24.

CORRECTED FROM THE PRINTOUT (David's rule, 2026-11-24: real errors against
skeet.asm are fixed and noted on the sheet):
 1. The off-page label on IR7 (pin 25) read "8255 Pin17: CLK2". IR7 is fed by
    the 8253's counter 2: skeet.asm programs counter 2 (PIT_ToPIC_Port 42H,
    "30 msec Timer Interrupt") and enables IR7 only (PIC_OCW1 7FH, vector
    27H), and Fig 5 sends the 8253's OUT2 (pin 17) to "8259: IR7 - Pin 25".
    Pin 17 of the 8253 is OUT2 (CLK2 is pin 18, and pin 17 of the 8255 is
    PC4). Here: "8253 Pin17: OUT2".

Checked and consistent with skeet.asm: 74LS138 on A4-A6 with IO/M enable puts
the PIC (50H/51H) on Y5 (8259 CS); 8259 A0 on CPU A0 (ports 50H/51H); IR0-IR6
grounded (only IR7 is enabled); SP/EN to Vcc (master; ICW1 13H says single
mode, so it is not used); INT -> 8088 INTR (pin 18); INTA from 8088 pin 24.
Pin numbers match the 8259A datasheet.

Drawing quirks kept as drawn:
 - The pin names RD, WR, CS, INTA, SP/EN print without overbars.
 - CAS0-CAS2 drawn as stubs (no-connect flags at their ends here); the
   74LS138's Y1-Y3, Y6, Y7 likewise.
"""
from common import IC, Stock, P, X, Y, LS138, PITCH, sheet, caption, save

# 8259A as drawn: IR0-IR7, A0 and the bus controls on the left; data, CAS,
# SP/EN and INT on the right.
I8259 = IC('8259A', '8259A',
           [(str(18 + i), 'IR%d' % i, 'L', i, 'input') for i in range(8)] + [
               ('27', 'A0', 'L', 9, 'input'), ('26', 'INTA', 'L', 11, 'input'),
               ('3', 'RD', 'L', 12, 'input'), ('2', 'WR', 'L', 13, 'input'), ('1', 'CS', 'L', 14, 'input'),
           ] + [(str(11 - i), 'D%d' % i, 'R', i, 'bidirectional') for i in range(8)] + [
               ('12', 'CAS0', 'R', 9, 'bidirectional'), ('13', 'CAS1', 'R', 10, 'bidirectional'),
               ('15', 'CAS2', 'R', 11, 'bidirectional'), ('16', 'SP/EN', 'R', 13, 'input'),
               ('17', 'INT', 'R', 15, 'output'),
           ], w=17.78, h=43.18)

GND = Stock('power', 'GND')


def stub(s, pin_pt, x):
    """An unused pin drawn with a stub on the original: stub + no-connect."""
    s.wire(pin_pt, (x, pin_pt[1]))
    s.noconnect((x, pin_pt[1]))


def build():
    s = sheet(6, 'Interrupt Subsystem - PIC')
    pic = s.ic('U1', I8259, *P(666, 170), hide_ref=True, val_at=P(664, 436))
    dec = s.ic('U2', LS138, *P(385, 417), hide_ref=True, val_at=P(397, 572))

    # IR0-IR6 tied together and grounded (dots on IR1-IR5, as drawn).
    bx = X(611)
    irs = [pic.pin(str(18 + i)) for i in range(7)]
    for p in irs:
        s.wire((bx, p[1]), p)
    s.wire((bx, irs[0][1]), (bx, irs[6][1]))
    s.junction(*[(bx, p[1]) for p in irs[1:6]])
    gy = irs[3][1]   # IR3 row
    s.wire((bx, gy), (X(527), gy))
    s.power(GND, (X(527), gy), angle=270)

    lx = X(455)   # tip of the left-hand off-page connectors
    # CORRECTED: printed "8255 Pin17: CLK2"; the source is the 8253's OUT2 (pin 17).
    for txt, n in [('8253 Pin17: OUT2', '25'), ('A0', '27'), ('8088 Pin 24: QS1/INTA', '26'),
                   ('/RD', '3'), ('/WR', '2')]:
        p = pic.pin(n)
        s.glabel(txt, (lx, p[1]), side='L')
        s.wire((lx, p[1]), p)
    # CS from the 74LS138's Y5 (pin 10), up the left of the 8259.
    cs, y5 = pic.pin('1'), dec.pin('10')
    s.wire(cs, (X(625), cs[1]), (X(625), y5[1]), y5)

    rx = X(947)
    for i in range(8):
        p = pic.pin(str(11 - i))
        s.wire(p, (rx, p[1]))
        s.glabel('D%d' % i, (rx, p[1]), side='R')
    for n in ['12', '13', '15']:
        stub(s, pic.pin(n), X(805))
    for txt, n in [('Vcc - To Make Master', '16'), ('8088 Pin 18: INTR', '17')]:
        p = pic.pin(n)
        s.wire(p, (rx, p[1]))
        s.glabel(txt, (rx, p[1]), side='R')

    # 74LS138: A4-A6 select, IO/M enables, G2A/G2B grounded.
    dx = X(313)
    for txt, n in [('A4', '1'), ('A5', '2'), ('A6', '3'), ('IO/M', '6')]:
        p = dec.pin(n)
        s.glabel(txt, (dx, p[1]), side='L')
        s.wire((dx, p[1]), p)
    g2a, g2b = dec.pin('4'), dec.pin('5')
    gx = X(273)
    s.wire(g2a, (gx, g2a[1]), (gx, Y(535)))
    s.wire(g2b, (gx, g2b[1]))
    s.junction((gx, g2b[1]))
    s.power(GND, (gx, Y(535)))
    for txt, n in [('8255 #6: CS', '15'), ('8253 #21: CS', '11')]:
        p = dec.pin(n)
        s.wire(p, (X(527), p[1]))
        s.glabel(txt, (X(527), p[1]), side='R')
    for n in ['14', '13', '12', '9', '7']:
        stub(s, dec.pin(n), X(512))

    s.text('Corrected from the 2007 printout: the IR7 label read "8255 Pin17: CLK2"; '
           'it is the 8253\'s OUT2 (pin 17),\nas on Fig 5 and in skeet.asm (counter 2 = '
           'the 30 ms interrupt on IR7, the only one enabled).', P(160, 865))
    caption(s, 'Figure 6: Interrupt\nSubsystem - PIC', P(95, 950))
    return save(s, 'fig6-pic.kicad_sch')


if __name__ == '__main__':
    print(build())
