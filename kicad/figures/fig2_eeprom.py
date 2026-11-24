"""Figure 2: Memory Subsystem - EEPROM (29010, 128 KB; 74LS138; red and
green LEDs). Scan: schematics/fig2.jpg.

CORRECTED FROM THE PRINTOUT (David, 2026-11-24): the printout joins the
EEPROM's ~{CE}, decoder outputs ~{Y2} and ~{Y7} and the green LED in one net.
skeet.asm puts the ROM at the top of memory (E0000H = Y7) and green_led_seg
at 4000H (40000H = Y2), so here ~{CE} is on ~{Y7} only and the green LED on
~{Y2} only. ~{Y0} now carries the RAM's chip select (Fig 3), which the
printout showed as an open stub. Also corrected: the duplicated "D4" (D5).
"""
from common import IC, LS138, Stock, P, X, Y, sheet, caption, save

A = [('12', 'A0'), ('11', 'A1'), ('10', 'A2'), ('9', 'A3'), ('8', 'A4'), ('7', 'A5'),
     ('6', 'A6'), ('5', 'A7'), ('27', 'A8'), ('26', 'A9'), ('23', 'A10'), ('25', 'A11'),
     ('4', 'A12'), ('28', 'A13'), ('29', 'A14'), ('3', 'A15'), ('2', 'A16')]
CTL = [('24', '~{OE}', 18, 'input'), ('31', '~{WE}', 19, 'input'),
       ('22', '~{CE}', 20, 'input'), ('32', 'VCC', 22, 'power_in')]
IO = [('13', 'I/O0'), ('14', 'I/O1'), ('15', 'I/O2'), ('17', 'I/O3'), ('18', 'I/O4'),
      ('19', 'I/O5'), ('20', 'I/O6'), ('21', 'I/O7')]
EE29010 = IC('29010', '29010',
             [(n, nm, 'L', i, 'input') for i, (n, nm) in enumerate(A)] +
             [(n, nm, 'L', slot, t) for n, nm, slot, t in CTL] +
             [(n, nm, 'R', i, 'bidirectional') for i, (n, nm) in enumerate(IO)],
             w=15.24, h=60.96)


def build():
    s = sheet(2, 'Memory Subsystem - EEPROM')
    led = Stock('Device', 'LED')
    gnd = Stock('power', 'GND')

    u1 = s.ic('U1', EE29010, *P(865, 233), ref_at=P(868, 215), val_at=P(865, 605))
    u2 = s.ic('U2', LS138, *P(452, 617), ref_at=P(455, 597), val_at=P(452, 770))

    # Address and control inputs from off-page connectors on the left.
    left = X(528)
    for n, nm in A:
        p = u1.pin(n)
        s.wire((left, p[1]), p)
        s.glabel(nm, (left, p[1]), side='L')
    for n, text in [('24', '245 Pin 12 /RD'), ('31', '245 Pin 13 /WR')]:
        p = u1.pin(n)
        s.wire((left, p[1]), p)
        s.glabel(text, (left, p[1]), side='L')

    # Data out to the right. The printout labels I/O5 "D4" (a typo): D5 here.
    right = X(1140)
    for i, (n, nm) in enumerate(IO):
        p = u1.pin(n)
        s.wire(p, (right, p[1]))
        s.glabel(f'D{i}', (right, p[1]), side='R')

    # 74LS138: A17-A19 on A, B, C; G1 from Vcc, ~G2A from IO/~M; ~G2B to ground.
    l138 = X(340)
    for n, text in [('1', 'A17'), ('2', 'A18'), ('3', 'A19'), ('6', 'Vcc'), ('4', 'IO/M')]:
        p = u2.pin(n)
        s.wire((l138, p[1]), p)
        s.glabel(text, (l138, p[1]), side='L')
    g2b = u2.pin('5')
    gx = X(408)
    s.wire(g2b, (gx, g2b[1]), (gx, Y(752)))
    s.power(gnd, (gx, Y(752)))

    # Unused decoder outputs: short stubs, as drawn.
    stub = X(580)
    for n in ['12', '11', '10', '9']:                # Y3, Y4, Y5, Y6
        p = u2.pin(n)
        s.wire(p, (stub, p[1]))
        s.noconnect((stub, p[1]))
    # ~Y0 selects the RAM (Fig 3): an off-page connector instead of a stub.
    y0 = u2.pin('15')
    s.wire(y0, (stub, y0[1]))
    s.glabel('138 Pin 15 - Y0', (stub, y0[1]), side='R')

    # ~CE down the vertical at x=652 to ~Y7 only (corrected, see docstring).
    ce = u1.pin('22')
    vx = X(652)
    y2, y7 = u2.pin('13'), u2.pin('7')
    s.wire(ce, (vx, ce[1]), (vx, y7[1]))
    s.wire(y7, (vx, y7[1]))

    # LEDs: cathodes on Y1 (red) and Y2 (green, drawn at the printout's spot
    # level with Y7); anodes to Vcc, which is also the EEPROM's VCC pin.
    ax = X(821)
    y1 = u2.pin('14')
    red = s.ic('D1', led, X(771), y1[1], value='RED', hide_ref=True,
               val_at=P(737, 660))
    green = s.ic('D2', led, X(771), y7[1], value='GREEN', hide_ref=True,
                 val_at=P(722, 745))
    # Series resistors (added: David confirmed the board had them; the value
    # wasn't recorded, so 220 ohm, as on Fig 4's LEDs). They sit on the
    # cathode side, between the decoder output and the LED.
    res = Stock('Device', 'R')

    def series_r(ref, led_part, y):
        k = led_part.pin('1')
        # Value as level text: a rotated part turns its own value field.
        r = s.ic(ref, res, k[0] - 5.08, y, angle=90, value='220', hide_ref=True,
                 hide_value=True)
        s.text('220', (k[0] - 6.35, y - 1.905))
        a, b = sorted([r.pin('1'), r.pin('2')])
        s.wire(b, k)
        return a

    s.wire(y1, series_r('R1', red, y1[1]))
    # Green LED on ~Y2 (corrected): across the ~CE vertical (no junction),
    # then down to the green LED where the printout drew it.
    gx2 = X(690)
    s.wire(y2, (gx2, y2[1]), (gx2, y7[1]), series_r('R2', green, y7[1]))
    vcc_pin = u1.pin('32')
    s.wire(vcc_pin, (ax, vcc_pin[1]), (ax, Y(812)))
    s.wire(red.pin('2'), (ax, y1[1]))
    s.wire(green.pin('2'), (ax, y7[1]))
    s.junction((ax, y1[1]), (ax, y7[1]))
    s.glabel('Vcc', (ax, Y(812)), side='B')

    s.text('Corrected from the 2007 printout: ~{CE} on ~{Y7} only, green LED on '
           '~{Y2} only, RAM select on ~{Y0}\n(the printout tied ~{CE}, ~{Y2} and '
           '~{Y7} together), per the addresses in skeet.asm; D5 label (printed as a second D4);\n'
           'LED series resistors (on the board but not the printout; value not recorded, '
           '220 ohm as on Fig 4).', P(160, 865))
    caption(s, 'Figure 2: Memory\nSubsystem - EEPROM', P(95, 915))
    return save(s, 'fig2-eeprom.kicad_sch')


if __name__ == '__main__':
    print(build())
