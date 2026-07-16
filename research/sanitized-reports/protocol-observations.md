# Protocol Observations (Sanitized)

Configuration framing uses command, length, payload, XOR checksum, and fixed
report padding. Observed request/response reads covered device information,
layer information, layer names, and assignments. Simple single-key and
combination structures were consistent enough to model and test. The vendor
application exposed broader category labels, but their on-wire structures were
not fully validated and are not emitted by this project.
