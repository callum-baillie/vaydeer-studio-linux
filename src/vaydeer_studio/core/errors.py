"""Domain exceptions with messages suitable for a UI or CLI."""


class VaydeerStudioError(Exception):
    """Base application exception."""


class ProtocolError(VaydeerStudioError):
    """Malformed, rejected, or failed HID protocol operation."""


class ForbiddenCommandError(ProtocolError):
    """A caller attempted to create a prohibited command."""


class DeviceError(VaydeerStudioError):
    """Device discovery or I/O failure."""


class CapabilityError(VaydeerStudioError):
    """The detected device cannot safely perform a requested operation."""


class UnsupportedActionError(VaydeerStudioError):
    """The selected action has no stable, verified on-device serializer."""


class SafetyConfirmationRequired(VaydeerStudioError):
    """An apply request was not explicitly confirmed."""


class VerificationError(VaydeerStudioError):
    """Read-back did not match the intended configuration."""


class PartialWriteError(VaydeerStudioError):
    """A configuration write stopped after some changes were accepted."""
