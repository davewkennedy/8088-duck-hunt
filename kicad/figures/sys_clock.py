"""Clock and Reset (RECONSTRUCTED, 2026): the 8284A clock generator for the
system schematic. Not in the 2007 drawings: the six printed figures only
show the 8088 side ("8284 Pin 8/5/10"), so this sheet is a reconstruction
from the 8284A datasheet and skeet.asm, built for the system project.

  - 12 MHz crystal on X1/X2, F/~C low (crystal mode): CLK = 12/3 = 4 MHz to
    the 8088, PCLK = CLK/2 = 2 MHz to the 8253 (the timing skeet.asm uses).
  - EFI and CSYNC low (not used with a crystal). OSC unused (no-connect).
  - Always ready: RDY1 high with ~AEN1 low enables bus 1; RDY2 low and
    ~AEN2 high disable bus 2. ~ASYNC low (two-stage synchronisation; my
    choice, the spec doesn't name it, and with READY constant it doesn't
    matter, but an input must not float).
  - ~RES: power-on RC (10k to VCC, 10uF to GND, about 100 ms) with a reset
    push button to GND. RESET (pin 10) goes to the 8088 (and the 8255).
  - Outputs as global labels: CLK, PCLK, READY, RESET.
  - Power pins (VCC 18, GND 9) are left off the symbol, as on the printed
    figures; the top sheet lists them. PWR_FLAGs on VCC and GND here.
"""
from common import IC, Stock, sheet, save
from kgen import rot, g

# Left side grouped by what each pin is tied to: crystal, the ground ties,
# the VCC ties, then ~RES (this is a new drawing, so the order is ours).
PIN_L = [('17', 'X1', 0), ('16', 'X2', 1),
         ('13', 'F/~{C}', 3), ('14', 'EFI', 4), ('1', 'CSYNC', 5), ('15', '~{ASYNC}', 6),
         ('3', '~{AEN1}', 7), ('6', 'RDY2', 8),
         ('4', 'RDY1', 11), ('7', '~{AEN2}', 12),
         ('11', '~{RES}', 14)]
PIN_R = [('8', 'CLK', 0), ('2', 'PCLK', 1), ('12', 'OSC', 3), ('5', 'READY', 5),
         ('10', 'RESET', 7)]
CLK8284 = IC('8284A', '8284A',
             [(n, nm, 'L', sl, 'input') for n, nm, sl in PIN_L] +
             [(n, nm, 'R', sl, 'output') for n, nm, sl in PIN_R],
             w=25.4, h=43.18)


def place(s, ref, sym, pin, at, angle=0, **kw):
    """Place a stock part so that its pin `pin` lands exactly on `at`."""
    (px, py), _ = sym.pin_geom(pin)
    dx, dy = rot(px, py, angle)
    return s.ic(ref, sym, at[0] - dx, at[1] - dy, angle=angle, **kw)


def build():
    s = sheet(7, 'Clock and Reset (reconstructed)')
    vcc, gnd, flag = Stock('power', 'VCC'), Stock('power', 'GND'), Stock('power', 'PWR_FLAG')
    xtal, res = Stock('Device', 'Crystal'), Stock('Device', 'R')
    cap, sw = Stock('Device', 'C_Polarized'), Stock('Switch', 'SW_Push')

    u = s.ic('U1', CLK8284, 140, 60, ref_at=(140, 56), val_at=(140, 103))
    xl = u.pin('17')[0]                   # left pin ends
    xr = u.pin('8')[0]                    # right pin ends

    # 12 MHz crystal between X1 and X2 (vertical, left of the chip).
    x1, x2 = u.pin('17'), u.pin('16')
    xc = g(xl - 15.24)
    y1 = place(s, 'Y1', xtal, '1', (xc, x2[1]), angle=90, value='12 MHz',
               ref_at=(xc - 7.62, x2[1] - 5.08), val_at=(xc - 10.16, x2[1] - 2.54))
    s.wire(x2, y1.pin('1'))
    top = y1.pin('2')
    xj = g(xc + 5.08)
    s.wire(x1, (xj, x1[1]), (xj, top[1]), top)

    # Ground ties on one rail (F/C, EFI, CSYNC, ASYNC, AEN1, RDY2), one GND
    # symbol below it with the GND PWR_FLAG beside it.
    xg_ = g(xl - 5.08)
    gpins = [u.pin(n) for n in ['13', '14', '1', '15', '3', '6']]
    for p in gpins:
        s.wire(p, (xg_, p[1]))
    s.junction(*[(xg_, p[1]) for p in gpins[1:-1]])
    gbot = (xg_, g(gpins[-1][1] + 2.54))
    s.wire((xg_, gpins[0][1]), gbot)
    s.junction((xg_, gpins[-1][1]))
    s.power(gnd, gbot)

    # VCC ties on a second rail further left (RDY1, ~AEN2), VCC symbol on top.
    xv_ = g(xl - 10.16)
    vp = [u.pin('4'), u.pin('7')]
    for p in vp:
        s.wire(p, (xv_, p[1]))
    vtop = (xv_, g(vp[0][1] - 2.54))
    s.wire(vtop, (xv_, vp[1][1]))
    s.junction((xv_, vp[0][1]))
    s.power(vcc, vtop)

    # ~RES: power-on RC plus a reset push button. R1's top joins the VCC rail
    # (at RDY1's row) and carries the VCC PWR_FLAG.
    rp = u.pin('11')
    xn, xcap, xsw = g(xl - 17.78), g(xl - 30.48), g(xl - 45.72)
    s.wire(rp, (xn, rp[1]), (xcap, rp[1]), (xsw, rp[1]))
    s.junction((xn, rp[1]), (xcap, rp[1]))
    r1 = place(s, 'R1', res, '1', (xn, vp[0][1]), value='10k',
               ref_at=(xn - 7.62, vp[0][1] + 3.81), val_at=(xn - 7.62, vp[0][1] + 6.35))
    s.wire(r1.pin('1'), (xv_, vp[0][1]))
    s.wire(r1.pin('2'), (xn, rp[1]))
    s.power(flag, r1.pin('1')).hide_value = True            # PWR_FLAG on VCC
    c1 = place(s, 'C1', cap, '1', (xcap, rp[1]), value='10uF',
               ref_at=(xcap + 2.54, rp[1] + 2.54), val_at=(xcap + 2.54, rp[1] + 5.08))
    s.power(gnd, c1.pin('2'))
    s.power(flag, s.wire(c1.pin('2'), (g(xcap + 10.16), c1.pin('2')[1])), angle=180).hide_value = True  # GND flag
    sw1 =place(s, 'SW1', sw, '2', (xsw, rp[1]), angle=90, value='RESET',
                ref_at=(xsw - 7.62, rp[1] + 3.81), val_at=(xsw - 10.16, rp[1] + 3.81))
    s.power(gnd, sw1.pin('1'))

    # Outputs to the rest of the system; OSC unused.
    for n, name in [('8', 'CLK'), ('2', 'PCLK'), ('5', 'READY'), ('10', 'RESET')]:
        p = u.pin(n)
        end = s.wire(p, (g(xr + 7.62), p[1]))
        s.glabel(name, end, side='R', shape='output')
    s.noconnect(u.pin('12'))

    s.text('RECONSTRUCTED 2026: not in the 2007 drawings.', (25, 30), size=3.0, bold=True)
    s.text('The 2007 figures show only the 8088 side of the 8284 (Fig 1: "8284 Pin 8, 5, 10").\n'
           'This sheet is rebuilt from the 8284A datasheet and skeet.asm:\n'
           '  12 MHz crystal, F/~{C} low: CLK = 4 MHz (8088), PCLK = 2 MHz (8253 clocks).\n'
           '  Always ready: RDY1 high + ~{AEN1} low; RDY2 low + ~{AEN2} high. ~{ASYNC} low.\n'
           '  ~{RES}: 10k / 10uF power-on reset (about 100 ms) plus a reset button.\n'
           '  Power pins (VCC 18, GND 9) not drawn, as on the 2007 figures.', (25, 130))
    return save(s, 'clock-reset.kicad_sch')


if __name__ == '__main__':
    print(build())
