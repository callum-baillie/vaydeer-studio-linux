# Research Timeline

| Phase | Result |
| --- | --- |
| USB inventory | Identified four JP-1011 HID interfaces and their vendor/standard roles. |
| Read-only experiment | Demonstrated that opening interface 2 read-only restores normal keyboard behavior. |
| Open/close retests | Confirmed traffic while open and loss of traffic after close without vendor reads or writes. |
| Protocol review | Correlated simple read/write/layer commands across public implementations and captures. |
| Firmware review | Documented wrapper/CRC observations without retaining or using firmware binaries. |
| Product implementation | Added dynamic keepalive, strict packet gate, mock transport, backups/diffs, and conservative capability checks. |
| Live-device repair | Replaced an unusable hidapi command open with sysfs-selected native hidraw, corrected udev matching, and validated normal-user service access. |

The exact workstation timestamps, device serial values, and unneeded host logs
were removed from the public summaries.
