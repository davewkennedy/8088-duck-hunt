THE SCHEMATICS, REDRAWN IN KICAD (2026)
==============================================================================
The original OrCAD/PSpice files from 2007 are lost; only the printed report
survived (scans in ../scans/schematics/). In 2026 the six figures were
redrawn in KiCad 10, keeping the original layout as closely as reasonable:
parts where they sat, wires along the same routes, the same off-page
labels, custom symbols drawn with the original pin order.

  sheets/fig1-cpu.kicad_sch      Figure 1: Microprocessor Subsystem
  sheets/fig2-eeprom.kicad_sch   Figure 2: Memory Subsystem - EEPROM
  sheets/fig3-ram.kicad_sch      Figure 3: Memory Subsystem - RAM
  sheets/fig4-ppi.kicad_sch      Figure 4: I/O Subsystem - PPI
  sheets/fig5-pit.kicad_sch      Figure 5: Timer Subsystem - PIT
  sheets/fig6-pic.kicad_sch      Figure 6: Interrupt Subsystem - PIC
  sheets/skeet8088.kicad_sym     the custom symbols (8088, 8253, 8255, ...)
  sheets/export/                 PDF and SVG of each sheet

Open any .kicad_sch directly in KiCad 10 (File > Open in the schematic
editor); the symbols are embedded in each file.

------------------------------------------------------------------------------
CORRECTIONS
------------------------------------------------------------------------------
The figures were drawn while each subsystem was being built and tested on
its own, before they were all wired together, so a few show a stage of the
build rather than the finished board. Where a printed figure disagrees with
skeet.asm or a datasheet, the redraw follows the code, and each sheet has a
note saying what changed:

 Fig 1  INTR (pin 18) was tied to ground; now from the 8259's INT (the game
        runs on the IR7 timer interrupt). Pin 24 (INTA) now goes to the
        8259's INTA; it was an open stub. RESET comes from 8284 pin 10
        (the RESET output), not pin 11 (the RES input). The junction dots
        where the 245's DIR wire crosses the data bus are removed: they
        would short DIR to the bus.
 Fig 2  The EEPROM's /CE and the green LED were both tied to decoder
        outputs Y2 and Y7. Now /CE is on Y7 (E0000H) and the green LED on
        Y2 (40000H), matching the code. Y0 now selects the RAM.
 Fig 3  The RAM's /CS1 was labelled "138 Pin 7 - Y7" (the EEPROM's
        select); the code puts RAM at 00000H, so it's Y0 (pin 15).
 Fig 4  The two discrete LEDs on PB2/PB3 were drawn reversed and could
        never light; the code drives them active-low, like the LED bar.
 Fig 5  The 8253's A0/A1 were on CPU A1/A2; the code's ports 40H-43H are
        consecutive, so they're on A0/A1 (as Fig 6 does for the 8259).
        CLK1 and CLK2 were open; the code uses both counters, so PCLK now
        drives all three.
 Fig 6  The IR7 label read "8255 Pin17: CLK2"; it's 8253 pin 17, OUT2.
 Figs 2 and 3: a data label printed as a second "D4" is D5.

Harmless drawing quirks are kept as printed (for example, BHE as the name
of 8088 pin 34, no overbars on some active-low pins, unused outputs drawn
as stubs).

The sheets are standalone, like the printed figures: Fig 1's latch and
buffer outputs are unlabelled stubs, so the six files don't join into one
netlist. KiCad's ERC on a single sheet reports the usual items for that
(labels used once, inputs driven from off the sheet).

------------------------------------------------------------------------------
THE SYSTEM SCHEMATIC
------------------------------------------------------------------------------
  system/skeet8088-system.kicad_pro   open this project in KiCad 10
  system/export/skeet8088-system.pdf  all eight pages in one PDF

One KiCad project that ties the whole computer together: a top sheet with
a block per subsystem, the six figures as its child sheets, and a seventh
sheet for the clock and reset. The printed off-page notes ("245 Pin 12
/RD", "8088 Pin 18: INTR", ...) become real signal names (/RD, INTR, ...),
so the sheets join into one netlist. Parts are numbered by sheet (U101 is
the 8088, U701 the 8284A).

Gaps closed beyond the per-figure corrections:
 - Fig 1's latch and buffer outputs drive the address bus A0-A19, the data
   bus D0-D7 and /RD, /WR, IO/M (stubs on the printout).
 - Figs 4, 5 and 6 each drew the same I/O decoder; the system has one
   (Fig 4's), with /PPI_CS, /PIT_CS and /PIC_CS going to the other sheets.
 - The 8284A clock and reset, which the figures only show as pin labels,
   is RECONSTRUCTED (not in the 2007 drawings): a 12 MHz crystal gives the
   8088 a 4 MHz CLK and the 8253 a 2 MHz PCLK (the code's note values and
   its 30 ms timer tick both work out at 2 MHz), an RC power-on reset plus
   a reset button, and READY always asserted.

KiCad's ERC on the whole project reports three items, all harmless: two
pins tied to VCC as printed (a spare 74LS245 input; the 74LS47's BI/RBO)
and the stock speaker symbol not counting the 75452 as a driver.

Design properties, as built (not errors):
 - Partial decoding: memory decodes A17-A19 only, so the 8 KB RAM repeats
   through the first 128 KB; I/O decodes A4-A6 only, so ports repeat every
   80H.
 - The EEPROM's /WE is on /WR, so the CPU can write to it.
 - 8255 PC4/PC5 are unused inputs with no pull-ups; the code masks them.
 - IC power pins are implied, not drawn, as on the 2007 figures; the top
   sheet lists them.

------------------------------------------------------------------------------
HOW THEY WERE MADE
------------------------------------------------------------------------------
The sheets are generated by small Python scripts (no dependencies beyond
Python 3 and KiCad 10): positions are read off the scans, and each
connection was checked against the scan, the datasheets and skeet.asm by
exporting KiCad's netlist.

  tools/kgen.py         writes .kicad_sch / .kicad_sym files
  figures/common.py     scan-to-sheet mapping, shared 74LS138, title block
  figures/figN_*.py     one script per figure
  figures/build_all.py  regenerate every sheet and the symbol library
  figures/build_system.py  the system project (same figure scripts,
                        built as child sheets; sys_clock.py is sheet 7)
  tools/render.sh       export PDF/SVG and run ERC (Git Bash, Windows)

Redrawn with the help of Claude (an AI assistant).
