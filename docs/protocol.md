# Protocol Notes

The vendor command channel uses a 64-byte HID report payload. The host submits
report ID `0x00`, command, payload length, payload, and XOR checksum; hidapi
therefore receives a 65-byte host buffer. Responses contain command, data
length, data, and the same XOR over those fields.

Stable known commands are `0x60` device info, `0x61` write assignment, `0x62`
read assignment, `0x63` layer info, `0x64` active layer, `0x65` write layer
name, `0x66` commit layer, `0x67` read layer name, and `0xFD` handshake.
`0xFC` is explicitly prohibited. See [research/hid-protocol.md](research/hid-protocol.md)
for packet examples and uncertainty boundaries.
