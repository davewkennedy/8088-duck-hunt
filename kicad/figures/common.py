"""Shared bits for the figure scripts: the scan-to-sheet mapping, the part
definitions that appear on more than one figure, and the title block."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from kgen import IC, Stock, Sheet, g, PITCH  # noqa: E402,F401

OUT = os.path.join(os.path.dirname(__file__), '..', 'sheets')
PROJECT = '8088-duck-hunt'

# Positions are read off the cleaned scans (1400 px wide, the web versions in
# G:\dave\project\8088\schematics). The originals use a 0.1 inch pin pitch,
# which is 14.2 px on those scans, so 1 px = 2.54 / 14.2 mm.
SCALE = 2.54 / 14.2


def P(x, y, x0=38, y0=33):
    """Scan pixel (on the 1400 px figure) -> sheet mm, snapped to grid."""
    return (g(21 + (x - x0) * SCALE), g(19.6 + (y - y0) * SCALE))


def X(x, x0=38):
    return g(21 + (x - x0) * SCALE)


def Y(y, y0=33):
    return g(19.6 + (y - y0) * SCALE)


# 74LS138 3-to-8 decoder, drawn the same way on Figs 2, 4, 5 and 6: A, B, C
# at the top left, the enables below them, Y0-Y7 down the right side.
LS138 = IC('74LS138', '74LS138', [
    ('1', 'A', 'L', 0, 'input'), ('2', 'B', 'L', 1, 'input'), ('3', 'C', 'L', 2, 'input'),
    ('6', 'G1', 'L', 4, 'input'), ('4', '~{G2A}', 'L', 5, 'input'),
    ('5', '~{G2B}', 'L', 6, 'input'),
] + [(str(15 - i) if i < 7 else '7', '~{Y%d}' % i, 'R', i, 'output')
     for i in range(8)],   # Y0..Y6 = pins 15..9, Y7 = pin 7 (pin 8 is GND)
    w=15.24, h=22.86)


# --------------------------------------------------------------------------
# System mode: the same figure scripts, built as child sheets of one KiCad
# project (system/skeet8088-system.kicad_pro) that ties the six subsystems
# together. build_system.py sets SYSTEM; figure scripts check
# `if common.SYSTEM:` for the few structural changes the integrated design
# needs (see ../README.txt). Everything else is shared.
# --------------------------------------------------------------------------
SYSTEM = None      # set by build_system.py: {'paths': {fig: inst_path}}
SYSTEM_PROJECT = 'skeet8088-system'
SYSTEM_OUT = os.path.join(os.path.dirname(__file__), '..', 'system')

# The printed off-page labels -> the system's signal names.
NETMAP = {
    'Vcc': 'VCC', 'Vcc - To Make Master': 'VCC',
    '245 Pin 12 /RD': '/RD', '245 Pin 13 /WR': '/WR',
    '138 Pin 15 - Y0': '/RAM_CS',
    'RST': 'RESET', '8284 Pin 10': 'RESET',
    '8284 Pin 5': 'READY', '8284 Pin 8': 'CLK',
    '8259 Pin 17: INT': 'INTR', '8088 Pin 18: INTR': 'INTR',
    '8259 Pin 26: INTA': '/INTA', '8088 Pin 24: QS1/INTA': '/INTA',
    'To 8253 PIT: OUT1 - Pin 13': 'PIT_OUT1', '8255: PC6 - Pin 11': 'PIT_OUT1',
    '8259: IR7 - Pin 25': 'PIT_OUT2', '8253 Pin17: OUT2': 'PIT_OUT2',
    '8255 #6:CS': '/PPI_CS', '8255 #6: CS': '/PPI_CS', '8253 #21: CS': '/PIT_CS',
}


def sheet(fig, title):
    comments = [
        'David Kennedy - ECE 3710 Microprocessors, final project (Skeet Shoot)',
        'Redrawn in KiCad in 2026 from the printed 2007 original (OrCAD files lost)',
    ]
    if not SYSTEM:
        return Sheet(f'Figure {fig}: {title}', PROJECT, comments=comments)
    comments.append('System schematic: all six figures joined by signal name; '
                    'build-stage gaps closed (see kicad/README.txt)')
    s = Sheet(f'Figure {fig}: {title}', SYSTEM_PROJECT, comments=comments,
              inst_path=SYSTEM['paths'][fig], netmap=NETMAP,
              pwr_base=fig * 100, ref_offset=fig * 100)
    s.power_labels = {'VCC': Stock('power', 'VCC')}
    return s


def caption(s, text, at):
    """The original's big rotated figure caption, bottom left."""
    s.text(text, at, size=3.0, angle=90, bold=True)


def save(s, name):
    out = SYSTEM_OUT if SYSTEM else OUT
    os.makedirs(out, exist_ok=True)
    return s.save(os.path.join(out, name))
