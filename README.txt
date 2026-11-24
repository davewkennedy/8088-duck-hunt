8088 DUCK HUNT: x86 ASSEMBLY FOR A HAND-BUILT INTEL 8088 COMPUTER (2007)
==============================================================================
The firmware for my final project in ECE 3710 (Microprocessors), December
2007: a rudimentary "Duck Hunt"-like game (called "Skeet Shoot" in the
source) for an Intel 8088 computer that I designed and wire-wrapped by
hand. Written for NASM 0.99.04, flat binary, burned to EEPROM.

  Write-up and photos: https://davidwkennedy.com/blog/8088-microcomputer/

  skeet.asm     the complete program (one file)
  schematics/   the six original schematics (PSpice, December 2007),
                scanned from the printed report and cleaned up
  kicad/        the six schematics redrawn in KiCad (2026), with the
                corrections listed in kicad/README.txt
  scans/        the raw scans: source/ (the 17-page source printout) and
                schematics/ (the six figures, before cleanup)

------------------------------------------------------------------------------
THE GAME, AS THE CODE PLAYS IT
------------------------------------------------------------------------------
 - Press the button and, after a random delay, a "skeet" flies across a
   row of twelve LEDs, one LED per step, with a rising note at each step.
 - Press again to fire: a gunshot noise plays. It's a hit only if you
   fire while the skeet is at one particular position.
 - A 7-segment digit shows the score. Ten hits plays a victory tune; running
   out of shots (25, or 11 in "championship" mode) plays a sad one.
 - DIP switches set the speed (8 settings) and championship mode: 16
   combinations in all.

------------------------------------------------------------------------------
THE HARDWARE (see schematics/)
------------------------------------------------------------------------------
 fig1  8088, 8284 clock (12 MHz crystal), 74LS373 latches, 74LS245 buffers
 fig2  29010 EEPROM, 128 KB, decoded by a 74LS138 on A17-A19; two spare
       decoder outputs light a red and a green LED
 fig3  6264 RAM, 8 KB
 fig4  8255 PPI: 12 LEDs (a 10-LED bar + 2), a 74LS47 driving the
       7-segment score digit, 4 DIP switches, the push button
 fig5  8253 PIT: speaker via a 75452 driver and a 1k volume pot
 fig6  8259A PIC, master, IR7 from the timer
 I/O ports are decoded by a 74LS138 on A4-A6: PPI 00H, PIT 40H, PIC 50H.

As the code uses it:
 - 8255 PPI at ports 00H-03H: port A and B drive the LEDs and the score
   digit, port C reads the button, the DIP switches and a timer output.
 - 8253 PIT at ports 40H-43H, clocked at 2 MHz:
     timer 0  square wave to the speaker (the notes and the gunshot)
     timer 1  one-shot used by the delay loop (polled through port C)
     timer 2  a 30 ms tick into the PIC
 - 8259 PIC at ports 50H-51H: IR7 -> interrupt vector 27H, a 30 ms timer
   interrupt that reads the button (edge detection) and runs the random
   delay counter.
 - The program sits at the top of the 1 MB address space; the last 16
   bytes are the reset code the 8088 runs at power-up.

------------------------------------------------------------------------------
ABOUT THIS COPY
------------------------------------------------------------------------------
The only surviving copy was a printout dated 3 February 2008. In 2026 it
was scanned and transcribed with the help of Claude (an AI assistant) and
checked: every name the code uses is defined; the note values, divided into
the 2 MHz timer clock, give the right pitches; the LED patterns step one
position at a time. It has not been assembled or run since 2008.

Transcribed as printed, including the original comments and typos, apart
from one loop label renamed for clarity (blacked out on the page 6 scan).
The ";-----" separator lines and column alignment are approximate, and
comments the printer wrapped are joined into one line.

Known quirks in the original:
 - "B5 equ 3407" is actually a D5 (587 Hz). playB5 is never called.
 - The "mediaryGunShotJump" trampolines exist because the 8088's
   conditional jumps reach only -128..+127 bytes. The comments there are
   2007-me being hard on 2007-me.

------------------------------------------------------------------------------
LICENSE
------------------------------------------------------------------------------
MIT (see LICENSE). Copyright (c) 2007 David Kennedy.
