"""Tests for privacy_guard.py."""

from __future__ import annotations

import socket
import ssl
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from privacy_guard import NetworkBlockedError, PrivacyGuard


@pytest.fixture(autouse=True)
def _reset_privacy_guard():
    """Reset singleton state before each test."""
    PrivacyGuard._instance = None
    PrivacyGuard._enforced = False
    yield
    PrivacyGuard._instance = None
    PrivacyGuard._enforced = False


class TestNetworkBlockedError:
    def test_is_exception(self):
        with pytest.raises(NetworkBlockedError):
            raise NetworkBlockedError("blocked")

    def test_message(self):
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            raise NetworkBlockedError("blocked by privacy policy")


class TestPrivacyGuard:
    def test_singleton(self):
        g1 = PrivacyGuard()
        g2 = PrivacyGuard()
        assert g1 is g2

    def test_is_enforced_before(self):
        guard = PrivacyGuard()
        assert guard.is_enforced() is False

    def test_enforce_sets_flag(self):
        guard = PrivacyGuard()
        guard.enforce()
        assert guard.is_enforced() is True

    def test_enforce_is_idempotent(self):
        guard = PrivacyGuard()
        guard.enforce()
        guard.enforce()  # second call should not raise
        assert guard.is_enforced() is True

    def test_enforce_blocks_socket(self):
        guard = PrivacyGuard()
        guard.enforce()
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def test_enforce_blocks_urllib_urlopen(self):
        guard = PrivacyGuard()
        guard.enforce()
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            urllib.request.urlopen("http://127.0.0.1")

    def test_enforce_blocks_ssl_wrap_socket(self):
        if not hasattr(ssl, "wrap_socket"):
            pytest.skip("ssl.wrap_socket not available on this Python version")
        guard = PrivacyGuard()
        guard.enforce()
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            ssl.wrap_socket(None)  # type: ignore[arg-type]

    def test_socket_still_blocked_after_second_guard(self):
        guard1 = PrivacyGuard()
        guard1.enforce()
        guard2 = PrivacyGuard()
        with pytest.raises(NetworkBlockedError):
            socket.socket()

    def test_diagnostics_event_logged(self):
        diag = MagicMock()
        guard = PrivacyGuard(diagnostics=diag)
        guard.enforce()
        assert diag.event.called

    def test_qtnetwork_patch_when_available(self):
        """If PySide6.QtNetwork is available, QNetworkAccessManager ops are blocked."""
        try:
            import PySide6.QtNetwork as QtNetwork
        except ImportError:
            pytest.skip("PySide6.QtNetwork not available")

        guard = PrivacyGuard()
        guard.enforce()

        mgr = QtNetwork.QNetworkAccessManager()
        req = QtNetwork.QNetworkRequest()

        with pytest.raises(NetworkBlockedError):
            mgr.get(req)

        with pytest.raises(NetworkBlockedError):
            mgr.post(req, b"")

    def test_qtnetwork_no_error_when_not_imported(self):
        guard = PrivacyGuard()
        guard.enforce()
        # If QtNetwork is not available, enforcement still succeeds
        assert guard.is_enforced() is True
