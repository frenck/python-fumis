"""Exceptions for the Fumis WiRCU API."""


class FumisError(Exception):
    """Generic Fumis exception."""


class FumisConnectionError(FumisError):
    """Fumis connection exception (base for all connectivity issues)."""


class FumisConnectionTimeoutError(FumisConnectionError):
    """Fumis connection timeout."""


class FumisResponseError(FumisError):
    """Fumis unexpected/error HTTP response from the API."""


class FumisAuthenticationError(FumisError):
    """Fumis authentication exception (invalid MAC/PIN)."""


class FumisStoveOfflineError(FumisError):
    """Fumis stove offline exception (WiRCU not connected to cloud)."""
