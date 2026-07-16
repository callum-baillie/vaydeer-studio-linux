# HID Protocol

## Framing

Host configuration requests are fixed HID reports:

```text
[0x00 report ID, command, payload length, payload bytes, XOR checksum, zero padding]
```

Device responses are:

```text
[command, data length, data bytes, XOR checksum, zero padding]
```

The XOR covers command, length, and payload/data. An invalid checksum or
unexpected response command is an error; callers do not continue with the
response. hidapi needs the report ID in the outgoing 65-byte buffer.

## Known commands

| Command | Meaning | Studio use |
| --- | --- | --- |
| `0x60` | Read device information | Stable read |
| `0x61` | Write key assignment | Stable only for verified payload classes |
| `0x62` | Read key assignment | Stable read |
| `0x63` | Read layer information | Stable read |
| `0x64` | Change active layer | Stable, capability gated |
| `0x65` | Write layer name | Stable, capability gated |
| `0x66` | Commit/finalize layer | Stable, capability gated |
| `0x67` | Read layer name | Stable read |
| `0xFD` | Initialization/handshake | Known but not required by the normal read flow |
| `0xFC` | Firmware update | Explicitly forbidden |

Normal configuration write flows use `0x61`, `0x65`, then `0x66`; Studio reads
the complete snapshot again afterwards. No raw packet console is exposed.

## Assignment types

The vendor application indicates these assignment families: `0` single key,
`1` key combination, `2` text (Unicode/GBK/software assisted), `3` host trigger
(file/directory/URL/application), `4` mouse, `5` macro (NoRepeat/PressRepeat/
Trigger/Sequence), `6` Vaydeer-specific action, and `7` special/unknown.

The investigated stable data covers simple keys, combinations, cleared keys,
and layer metadata. Studio serializes only packet forms it can read, write, and
read back safely. Other families remain typed, visible experimental records and
are blocked from physical writes until captured round-trip evidence is added.

## Vendor event reports

Interface 2 returns 16-byte asynchronous physical-key reports. Studio keeps the
handle open for keyboard activation; it does not record event bytes unless the
live tester or Linux-binding service explicitly enables event consumption.
