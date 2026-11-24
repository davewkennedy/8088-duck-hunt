"""Figure 3: Memory Subsystem - RAM (6264, 8 KB). Scan: schematics/fig3.jpg.

CORRECTED FROM THE PRINTOUT (David, 2026-11-24): the printout labels ~{CS1}
"138 Pin 7 - Y7", the EEPROM's select. skeet.asm puts RAM at 00000H (reset
code: DS=SS=ES=0, SP=1FFEH; .bss at 0), which is ~{Y0}, pin 15. Also
corrected: the duplicated "D4" label (D5).
"""
from common import IC, P, X, Y, sheet, caption, save

# 6264 as drawn: address and control pins on the left, data on the right.
A = [('10', 'A0'), ('9', 'A1'), ('8', 'A2'), ('7', 'A3'), ('6', 'A4'), ('5', 'A5'),
     ('4', 'A6'), ('3', 'A7'), ('25', 'A8'), ('24', 'A9'), ('21', 'A10'),
     ('23', 'A11'), ('2', 'A12')]
CTL = [('22', '~{OE}', 14), ('27', '~{WE}', 15), ('20', '~{CS1}', 16), ('26', 'CS2', 17)]
D = [('11', 'D0'), ('12', 'D1'), ('13', 'D2'), ('15', 'D3'), ('16', 'D4'), ('17', 'D5'),
     ('18', 'D6'), ('19', 'D7')]
RAM6264 = IC('6264', '6264',
             [(n, nm, 'L', i, 'input') for i, (n, nm) in enumerate(A)] +
             [(n, nm, 'L', slot, 'input') for n, nm, slot in CTL] +
             [(n, nm, 'R', i, 'bidirectional') for i, (n, nm) in enumerate(D)],
             w=15.24, h=48.26)


def build():
    s = sheet(3, 'Memory Subsystem - RAM')
    u1 = s.ic('U1', RAM6264, *P(737, 358), ref_at=P(737, 340), val_at=P(737, 652))
    left = X(513)
    for n, nm in A:
        p = u1.pin(n)
        s.wire((left, p[1]), p)
        s.glabel(nm, (left, p[1]), side='L')
    for n, text in [('22', '245 Pin 12 /RD'), ('27', '245 Pin 13 /WR'),
                    ('20', '138 Pin 15 - Y0'), ('26', 'Vcc')]:
        p = u1.pin(n)
        s.wire((left, p[1]), p)
        s.glabel(text, (left, p[1]), side='L')
    right = X(925)
    # The printout labels the D5 pin "D4" (a typo); corrected here to D5.
    for n, nm in D:
        p = u1.pin(n)
        s.wire(p, (right, p[1]))
        s.glabel(nm, (right, p[1]), side='R')
    s.text('Corrected from the 2007 printout: ~{CS1} from 138 ~{Y0} (printed as '
           '"138 Pin 7 - Y7"), per skeet.asm (RAM at 00000H);\nD5 label (printed as a second D4).', P(160, 940))
    caption(s, 'Figure 3: Memory\nSubsystem - RAM', P(95, 990))
    return save(s, 'fig3-ram.kicad_sch')


if __name__ == '__main__':
    print(build())
