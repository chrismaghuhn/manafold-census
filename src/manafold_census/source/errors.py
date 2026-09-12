"""Shared failure type for fail-closed source operations."""


class SourceAcquisitionError(RuntimeError):
    """Raised when source discovery or acquisition cannot complete safely."""
