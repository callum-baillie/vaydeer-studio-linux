# Firmware Format Research

This note records analysis only. Vaydeer Studio neither flashes firmware nor
ships firmware files.

The reviewed public update material uses a 32-byte wrapper. Evidence indicates
a CRC16-CCITT-FALSE checksum and an XOR key derived from the CRC bytes before
the embedded Cortex-M application can be decoded. Public metadata identifies a
JP-1011/key-9 update version `1.1.2`; the locally observed keypad used `1.0.2`.

Some wrapper/header fields remain uncertain and must not be treated as a
specification. No binary, extracted application, disassembly database, or
installer is included here. The only permitted source records are hashes, public
URLs, small explanatory byte sequences, and original methodology.
