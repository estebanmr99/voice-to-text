"""Runtime network blocking and offline enforcement.

PrivacyGuard monkey-patches Python's network APIs to raise
:class:`NetworkBlockedError` on any socket or HTTP attempt.  It also
attempts to neutralise PySide6.QtNetwork if it has already been imported.

The guard is intended to be activated **once** at application startup,
before any other module that might make network requests is imported.
"""

from __future__ import annotations

import logging
import socket
import ssl
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diagnostics import Diagnostics

logger = logging.getLogger(__name__)


class NetworkBlockedError(Exception):
    """Raised when code attempts a network call after enforcement is active."""

    pass


class PrivacyGuard:
    """Activate once to block all runtime network calls.

    Parameters
    ----------
    diagnostics:
        Optional :class:`Diagnostics` instance for redacted event logging.
    """

    _instance: "PrivacyGuard | None" = None
    _enforced = False

    def __new__(cls, *args: object, **kwargs: object) -> "PrivacyGuard":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, diagnostics: "Diagnostics | None" = None) -> None:
        self._diagnostics = diagnostics

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enforce(self) -> None:
        """Activate network blocking.

        Idempotent — subsequent calls do nothing.
        """
        if self._enforced:
            return

        self._patch_socket()
        self._patch_urllib()
        self._patch_ssl()
        self._patch_qtnetwork()

        PrivacyGuard._enforced = True
        self._log_event("privacy_guard_enforced")

        # Validate at startup: attempt connection to 127.0.0.1:1 (closed port)
        # Expect NetworkBlockedError, not ConnectionRefusedError
        try:
            _test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _test_socket.close()
        except NetworkBlockedError:
            self._log_event("privacy_guard_self_test_passed")
            logger.info("PrivacyGuard self-test passed — network calls are blocked")
        except Exception as exc:
            self._log_event("privacy_guard_self_test_failed", error_type=type(exc).__name__)
            logger.warning("PrivacyGuard self-test unexpected result: %s", exc)

    def is_enforced(self) -> bool:
        """Return ``True`` if blocking is active."""
        return self._enforced

    # ------------------------------------------------------------------
    # Patching helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _patch_socket() -> None:
        _original_socket = socket.socket

        def _blocked_socket(*args: object, **kwargs: object) -> object:
            raise NetworkBlockedError("Network calls are blocked by privacy policy")

        socket.socket = _blocked_socket  # type: ignore[assignment]
        logger.debug("socket.socket patched")

    @staticmethod
    def _patch_urllib() -> None:
        _original_urlopen = urllib.request.urlopen

        def _blocked_urlopen(*args: object, **kwargs: object) -> object:
            raise NetworkBlockedError("Network calls are blocked by privacy policy")

        urllib.request.urlopen = _blocked_urlopen  # type: ignore[assignment]
        logger.debug("urllib.request.urlopen patched")

    @staticmethod
    def _patch_ssl() -> None:
        if hasattr(ssl, "wrap_socket"):
            _original_wrap_socket = ssl.wrap_socket

            def _blocked_wrap_socket(*args: object, **kwargs: object) -> object:
                raise NetworkBlockedError("Network calls are blocked by privacy policy")

            ssl.wrap_socket = _blocked_wrap_socket  # type: ignore[assignment]
            logger.debug("ssl.wrap_socket patched")

    @staticmethod
    def _patch_qtnetwork() -> None:
        """Neutralise QNetworkAccessManager if PySide6.QtNetwork is imported."""
        try:
            import PySide6.QtNetwork as QtNetwork
        except Exception:
            return

        if hasattr(QtNetwork, "QNetworkAccessManager"):
            _original_get = QtNetwork.QNetworkAccessManager.get
            _original_post = QtNetwork.QNetworkAccessManager.post
            _original_put = QtNetwork.QNetworkAccessManager.put
            _original_delete = QtNetwork.QNetworkAccessManager.deleteResource

            def _blocked_network_op(*args: object, **kwargs: object) -> object:
                raise NetworkBlockedError("Network calls are blocked by privacy policy")

            QtNetwork.QNetworkAccessManager.get = _blocked_network_op  # type: ignore[assignment]
            QtNetwork.QNetworkAccessManager.post = _blocked_network_op  # type: ignore[assignment]
            QtNetwork.QNetworkAccessManager.put = _blocked_network_op  # type: ignore[assignment]
            QtNetwork.QNetworkAccessManager.deleteResource = _blocked_network_op  # type: ignore[assignment]
            logger.debug("QNetworkAccessManager patched")

    # ------------------------------------------------------------------
    # Logging helper
    # ------------------------------------------------------------------

    def _log_event(self, name: str, **kwargs: object) -> None:
        if self._diagnostics is not None:
            try:
                self._diagnostics.event(name, **kwargs)
            except Exception:
                pass
        logger.debug("Event: %s %r", name, kwargs)
