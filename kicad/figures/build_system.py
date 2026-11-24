"""Build the system schematic: one KiCad project whose top sheet holds a
block per subsystem, with the six figures (plus the reconstructed clock and
reset sheet) as child sheets joined by signal name.
    python build_system.py      -> ../system/skeet8088-system.kicad_pro
"""
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import common  # noqa: E402
from kgen import IC, Sheet, write_lib  # noqa: E402

# (key, block name, file, script module, block position mm, block size mm)
SHEETS = [
    (7, 'Clock and Reset (reconstructed)', 'clock-reset.kicad_sch', 'sys_clock',
     (25, 40), (45, 25)),
    (1, 'Fig 1 - Microprocessor', 'fig1-cpu.kicad_sch', 'fig1_cpu', (95, 40), (50, 25)),
    (2, 'Fig 2 - Memory - EEPROM', 'fig2-eeprom.kicad_sch', 'fig2_eeprom',
     (170, 30), (45, 20)),
    (3, 'Fig 3 - Memory - RAM', 'fig3-ram.kicad_sch', 'fig3_ram', (170, 65), (45, 20)),
    (4, 'Fig 4 - I/O - PPI', 'fig4-ppi.kicad_sch', 'fig4_ppi', (25, 110), (45, 25)),
    (5, 'Fig 5 - Timer - PIT', 'fig5-pit.kicad_sch', 'fig5_pit', (95, 110), (45, 25)),
    (6, 'Fig 6 - Interrupts - PIC', 'fig6-pic.kicad_sch', 'fig6_pic', (170, 110), (45, 25)),
]

# What each block holds, written inside it on the top sheet.
CONTENTS = {
    7: '8284A clock generator\n12 MHz crystal\nCLK 4 MHz, PCLK 2 MHz\npower-on reset + button',
    1: '8088 CPU (minimum mode)\n2x 74LS373 address latches\n74LS245 data buffer\n'
       '74LS245 address/control buffer',
    2: '29010 EEPROM, 128 KB (E0000H)\n74LS138 memory decoder\nred and green LEDs',
    3: '6264 RAM, 8 KB (00000H)',
    4: '8255 PPI (00H), 74LS138 I/O decoder\n12 LEDs, 74LS47 + 7-seg score\n'
       '4 DIP switches, fire button',
    5: '8253 PIT (40H)\n75452 driver, speaker\n1k volume pot',
    6: '8259A PIC (50H)\nIR7 = 30 ms timer tick',
}


def main():
    out = common.SYSTEM_OUT
    os.makedirs(out, exist_ok=True)
    root = Sheet('Skeet Shoot 8088 Computer - System', common.SYSTEM_PROJECT, comments=[
        'David Kennedy - ECE 3710 Microprocessors, final project (Skeet Shoot)',
        'System schematic (2026): the six 2007 figures joined by signal name',
        'Clock and reset sheet reconstructed (not in the 2007 drawings)',
    ])
    paths = {}
    present = []
    for page, (key, name, fname, mod, at, size) in enumerate(SHEETS, 2):
        if not os.path.exists(os.path.join(HERE, mod + '.py')):
            print('skipping (no script yet):', mod)
            continue
        paths[key] = root.subsheet(name, fname, at, size, page)
        present.append((key, fname, mod))
        root.text(CONTENTS[key], (at[0] + 2.54, at[1] + 5.08))
    root.text('Address bus A0-A19 and data bus D0-D7 come from Fig 1 (latches '
              'and buffers); /RD, /WR and IO/M from its 74LS245.\n'
              'Memory decode (Fig 2): A17-A19 -> RAM 00000H (Y0), red LED '
              '20000H (Y1), green LED 40000H (Y2), EEPROM E0000H (Y7).\n'
              'I/O decode (Fig 4): A4-A6 -> PPI 00H (Y0), PIT 40H (Y4), '
              'PIC 50H (Y5).', (25, 150))
    root.text('IC power is implied, not drawn (as on the 2007 figures):\n'
              '  8088: VCC 40, GND 1 20        8284A: VCC 18, GND 9\n'
              '  8255: VCC 26, GND 7           8253: VCC 24, GND 12\n'
              '  8259A: VCC 28, GND 14         6264: VCC 28, GND 14\n'
              '  29010: VCC 32 (drawn), GND 16 74LS373 / 74LS245: VCC 20, GND 10\n'
              '  74LS138 / 74LS47: VCC 16, GND 8   75452: VCC 8, GND 4 (drawn)',
              (25, 166))

    common.SYSTEM = {'paths': paths}
    syms = {}
    for key, fname, mod in present:
        m = importlib.import_module(mod)
        path = m.build()
        assert os.path.basename(path) == fname, (path, fname)
        print(path)
        for v in vars(m).values():
            if isinstance(v, IC):
                syms[v.name] = v
    syms[common.LS138.name] = common.LS138
    common.SYSTEM = None

    print(root.save(os.path.join(out, common.SYSTEM_PROJECT + '.kicad_sch')))
    pro = os.path.join(out, common.SYSTEM_PROJECT + '.kicad_pro')
    json.dump({'meta': {'filename': os.path.basename(pro), 'version': 1}},
              open(pro, 'w'), indent=2)
    write_lib(os.path.join(out, 'skeet8088.kicad_sym'), syms.values())
    # Project library table: the custom parts plus KiCad's stock libraries,
    # so the project opens (and ERC runs) without a global setup.
    libs = [('skeet8088', '${KIPRJMOD}/skeet8088.kicad_sym')] + [
        (n, '${KICAD10_SYMBOL_DIR}/%s.kicad_sym' % n) for n in ('power', 'Device', 'Switch')]
    with open(os.path.join(out, 'sym-lib-table'), 'w', newline='\n') as f:
        f.write('(sym_lib_table\n  (version 7)\n')
        for n, uri in libs:
            f.write(f'  (lib (name "{n}")(type "KiCad")(uri "{uri}")(options "")(descr ""))\n')
        f.write(')\n')


if __name__ == '__main__':
    main()
