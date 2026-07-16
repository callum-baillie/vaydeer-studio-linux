# Firmware and QMK Notes (Sanitized)

Firmware-package analysis found a compact wrapper, CRC16-CCITT-FALSE behavior,
and an XOR transform connected to CRC bytes before a Cortex-M image. No vendor
firmware data is retained. The APM32F103CBT6 is QMK-capable in general, but a
JP-1011 port and safe bootloader/recovery protocol were not established. The
application-base ambiguity remains unresolved; no replacement firmware action
is included in this project.
