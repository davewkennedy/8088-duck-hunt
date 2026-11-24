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


def sheet(fig, title):
    return Sheet(f'Figure {fig}: {title}', PROJECT, comments=[
        'David Kennedy - ECE 3710 Microprocessors, final project (Skeet Shoot)',
        'Redrawn in KiCad in 2026 from the printed 2007 original (OrCAD files lost)',
    ])


def caption(s, text, at):
    """The original's big rotated figure caption, bottom left."""
    s.text(text, at, size=3.0, angle=90, bold=True)


def save(s, name):
    os.makedirs(OUT, exist_ok=True)
    return s.save(os.path.join(OUT, name))
