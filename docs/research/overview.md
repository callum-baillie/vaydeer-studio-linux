# Research Overview

This project consolidates public protocol references and a local, repeatable
JP-1011 investigation. The central conclusion is operational rather than
speculative: retaining a read-only file descriptor for the vendor event HID
interface keeps the keypad's normal Linux keyboard reports active. No vendor
request, event read, or write is required for activation.

The primary device examined was a JP-1011 with PCB marking `JP1E0111-V1.2`,
firmware `1.0.2`, bootloader `0.2.1`, VID:PID `0483:5752`, nine physical keys,
and up to six reported layers. Findings are deliberately separated into stable
protocol facts, useful observations, and unknowns. Neither vendor installers
nor firmware binaries are stored in this repository.

The compact sanitized source summaries are in
[../../research/sanitized-reports](../../research/sanitized-reports). They omit
host paths, user names, serial values, and irrelevant system logs.

The live-device repair that turned the investigation into an installed,
normal-user application path is documented in
[live-device-detection-debug.md](live-device-detection-debug.md). It covers
the incomplete hidapi metadata observed during validation, the sysfs fallback,
the corrected udev match, and the read-only test boundary.
