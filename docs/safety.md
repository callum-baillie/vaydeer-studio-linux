# Safety

Firmware command `0xFC` is forbidden at the protocol boundary. Unknown command
IDs are rejected. A configuration write requires a supported capability, a fresh
read, a timestamped backup, a diff, explicit confirmation, and read-back
verification.
