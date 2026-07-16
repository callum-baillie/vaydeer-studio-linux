# Linux Activation Retest (Sanitized)

Controlled trials varied opening, reading, writing, and closing the interface-2
file descriptor. Opening alone consistently correlated with normal keyboard
traffic. No read, write, vendor packet, or handshake was required. Closing the
descriptor stopped the behavior. The likely mechanism is Linux hidraw retaining
interrupt-IN polling while an open file exists; this is an inference from the
observed behavior and kernel-path review, not a vendor statement.
