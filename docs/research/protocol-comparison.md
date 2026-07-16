# Protocol Comparison

| Source | Contribution to confidence | Studio decision |
| --- | --- | --- |
| Philipp Fischer's `vaydeer-macro-keyboard` | Python framing, layers, simple mappings, YAML direction, firmware codec observations | Behavioral reference only because no license file was present; no code copied. Firmware handling excluded. |
| Alex Savin's `go-vaydeer-ninepad-hid` | Command/event interface roles and nine-pad HID behavior | MIT source reviewed; independently implemented protocol facts only. |
| grfrost's `vaydeer-linux` | Historical HID-open Linux workaround | No code reused; supports the hold-open hypothesis. |
| TwinBlackbirds `Vaydeer-Keypad-Linux` | Historical Linux operational reference | No code reused. |
| Primis Linux-fix article | Public report that opening the HID device restores normal input | Corroborating public explanation. |
| Local investigation | Repeated controlled open/close retests, descriptor and kernel behavior | Primary activation evidence. |
| Official Vaydeer downloads/metadata | Public firmware versions and software distribution context | URLs/metadata only; no proprietary assets included. |

Agreement exists on simple configuration framing and the Linux workaround. It
does not establish undocumented macro, text, mouse, or host-trigger payload
formats. Studio uses that distinction to gate writes.
