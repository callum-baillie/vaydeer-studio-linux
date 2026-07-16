# USB Read-only Investigation (Sanitized)

The device presented VID:PID `0483:5752` with four HID interfaces. The vendor
asynchronous event collection was identified as USB interface 2, usage page
`0xFF00`, usage `0x0002`, and 16-byte input reports. Retaining an `O_RDONLY`
descriptor on the dynamically selected hidraw node was sufficient to restore
standard keyboard events. The report records used to establish this result
contained device-specific and host-specific data, which are omitted here.
