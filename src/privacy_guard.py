"""Runtime network blocking and offline enforcement.

PrivacyGuard monkey-patches Python's network APIs to raise
:class:`NetworkBlockedError` on any socket or HTTP attempt.  It also
attempts to neutralise PySide6.QtNetwork if it has already been imported.

The guard is intended to be activated **once** at application startup,
before any other module that might make network requests is imported.

Whitelist support
-----------------
Call :meth:`whitelist_endpoints` after :meth:`enforce` to selectively allow
connections to specific hosts while blocking all others.  Call
:meth:`revoke_whitelist` to restore full blocking.

When the whitelist is non-empty, only the listed hostnames are permitted.
When the whitelist is empty (the default), **all** network calls are blocked.
"""

from __future__ import annotations

import logging
import socket
import ssl
import threading
import urllib.request
from typing import TYPE_CHECKING
from urllib.parse import urlparse

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
        # Guard against re-initialisation via singleton __init__ replay.
        # _patch_* closures call PrivacyGuard() to fetch the singleton,
        # which would otherwise reset the whitelist on every socket call.
        if not hasattr(self, "_whitelist_lock"):
            self._whitelist: set[str] = set()
            self._whitelist_lock = threading.Lock()

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

    def whitelist_endpoints(self, urls: list[str]) -> None:
        """Allow connections to the given endpoints.

        Parses hostnames from *urls* and adds them to the allow-list.
        When the whitelist is non-empty, only the listed hostnames are
        permitted through the guard.  Call :meth:`revoke_whitelist` to
        restore full blocking.

        Parameters
        ----------
        urls:
            List of URL strings
            (e.g. ``["https://api.openai.com/v1/chat/completions"]``).
        """
        hostnames: set[str] = set()
        for url in urls:
            hostname = self._parse_hostname(url)
            if hostname:
                hostnames.add(hostname)
        if not hostnames:
            return
        with self._whitelist_lock:
            self._whitelist.update(hostnames)
        self._log_event("whitelist_updated", count=len(hostnames))

    def revoke_whitelist(self) -> None:
        """Clear the whitelist and restore full network blocking."""
        with self._whitelist_lock:
            self._whitelist.clear()
        self._log_event("whitelist_revoked")

    # ------------------------------------------------------------------
    # Whitelist helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_hostname(url: str) -> str | None:
        """Extract a hostname from *url*.

        Handles URLs with and without a scheme (e.g.
        ``"https://api.example.com/path"`` and ``"api.example.com/path"``).

        Returns ``None`` if no hostname can be determined.
        """
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            # Try with ``//`` prefix for schemeless URLs.
            if not url.startswith(("http://", "https://", "//")):
                parsed = urlparse(f"//{url}")
                hostname = parsed.hostname
        return hostname

    def _whitelist_empty(self) -> bool:
        """Return ``True`` when the whitelist has no entries (block all)."""
        with self._whitelist_lock:
            return not self._whitelist

    def _is_allowed(self, hostname: str | None) -> bool:
        """Check whether *hostname* is permitted through the guard.

        Returns ``False`` when the whitelist is empty (block all).
        Returns ``False`` when *hostname* is ``None`` (unknown target).
        Thread-safe.
        """
        with self._whitelist_lock:
            if not self._whitelist:
                return False
            if hostname is None:
                return False
            return hostname in self._whitelist

    def _check_or_raise(self, hostname: str | None) -> None:
        """Raise :class:`NetworkBlockedError` if *hostname* is not permitted.

        Thread-safe — acquires the whitelist lock internally.
        """
        with self._whitelist_lock:
            if not self._whitelist:
                raise NetworkBlockedError("Network calls are blocked by privacy policy")
            if hostname is None or hostname not in self._whitelist:
                raise NetworkBlockedError(
                    f"Network call to '{hostname}' is blocked by privacy policy"
                )

    # ------------------------------------------------------------------
    # Patching helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _patch_socket() -> None:
        _original_socket = socket.socket

        # Subclass the original socket so we can intercept connect().
        # Python C-level socket objects have a read-only ``connect``
        # attribute, so instance-level monkey-patching is not possible.
        class _WhitelistSocket(_original_socket):  # type: ignore[valid-type]
            def __init__(self, *args: object, **kwargs: object) -> None:
                guard = PrivacyGuard()
                # Fast path: empty whitelist means full block (existing behaviour).
                if guard._whitelist_empty():
                    raise NetworkBlockedError(
                        "Network calls are blocked by privacy policy"
                    )
                super().__init__(*args, **kwargs)
                self._pg_guard = guard

            def connect(self, address: object, **kwargs: object) -> None:  # type: ignore[override]
                hostname: str | None = (
                    address[0] if isinstance(address, tuple) else str(address)
                )
                self._pg_guard._check_or_raise(hostname)
                return super().connect(address, **kwargs)

        socket.socket = _WhitelistSocket  # type: ignore[assignment]
        logger.debug("socket.socket patched (whitelist-aware)")

    @staticmethod
    def _patch_urllib() -> None:
        _original_urlopen = urllib.request.urlopen

        def _whitelist_aware_urlopen(url: object, *args: object, **kwargs: object) -> object:
            guard = PrivacyGuard()
            hostname: str | None
            if isinstance(url, urllib.request.Request):
                hostname = url.host  # type: ignore[union-attr]
            else:
                hostname = guard._parse_hostname(str(url))
            guard._check_or_raise(hostname)
            return _original_urlopen(url, *args, **kwargs)

        urllib.request.urlopen = _whitelist_aware_urlopen  # type: ignore[assignment]
        logger.debug("urllib.request.urlopen patched (whitelist-aware)")

    @staticmethod
    def _patch_ssl() -> None:
        if not hasattr(ssl, "wrap_socket"):
            return

        _original_wrap_socket = ssl.wrap_socket

        def _whitelist_aware_wrap_socket(sock: object, *args: object, **kwargs: object) -> object:
            guard = PrivacyGuard()
            server_hostname: str | None = kwargs.get("server_hostname") if kwargs else None
            guard._check_or_raise(server_hostname)
            return _original_wrap_socket(sock, *args, **kwargs)

        ssl.wrap_socket = _whitelist_aware_wrap_socket  # type: ignore[assignment]
        logger.debug("ssl.wrap_socket patched (whitelist-aware)")

    @staticmethod
    def _patch_qtnetwork() -> None:
        """Neutralise QNetworkAccessManager if PySide6.QtNetwork is imported."""
        try:
            import PySide6.QtNetwork as QtNetwork
        except Exception:
            return

        if not hasattr(QtNetwork, "QNetworkAccessManager"):
            return

        _original_get = QtNetwork.QNetworkAccessManager.get
        _original_post = QtNetwork.QNetworkAccessManager.post
        _original_put = QtNetwork.QNetworkAccessManager.put
        _original_delete = QtNetwork.QNetworkAccessManager.deleteResource

        def _make_qtnetwork_wrapper(  # type: ignore[misc]
            original_method: object,
        ) -> object:
            def _wrapper(self_: object, request: object, *args: object, **kwargs: object) -> object:
                guard = PrivacyGuard()
                hostname: str | None = None
                if hasattr(request, "url"):
                    url_obj = request.url()  # type: ignore[union-attr]
                    if hasattr(url_obj, "host"):
                        hostname = url_obj.host()  # type: ignore[union-attr]
                guard._check_or_raise(hostname)
                return original_method(self_, request, *args, **kwargs)  # type: ignore[operator]

            return _wrapper

        QtNetwork.QNetworkAccessManager.get = _make_qtnetwork_wrapper(_original_get)  # type: ignore[assignment]
        QtNetwork.QNetworkAccessManager.post = _make_qtnetwork_wrapper(_original_post)  # type: ignore[assignment]
        QtNetwork.QNetworkAccessManager.put = _make_qtnetwork_wrapper(_original_put)  # type: ignore[assignment]
        QtNetwork.QNetworkAccessManager.deleteResource = _make_qtnetwork_wrapper(_original_delete)  # type: ignore[assignment]
        logger.debug("QNetworkAccessManager patched (whitelist-aware)")

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
