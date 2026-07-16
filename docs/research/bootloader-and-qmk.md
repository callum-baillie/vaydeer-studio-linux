# Bootloader and QMK

The APM32F103CBT6 is capable of running QMK-class firmware; other keyboards use
the same MCU family. That fact is not a JP-1011 QMK port. No established
JP-1011 QMK target, board definition, matrix mapping, bootloader handoff, or
recovery path was found during this research.

The vendor bootloader remains proprietary. Analysis left an unresolved
application-base disagreement around `0x08007000` versus `0x08008000`.
Any replacement-firmware attempt still needs a known-good SWD recovery plan
before changing the device. Firmware replacement, bootloader modification, and
option-byte/protection changes are out of scope for Vaydeer Studio.
