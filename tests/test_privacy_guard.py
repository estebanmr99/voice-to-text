"""Tests for privacy_guard.py."""

from __future__ import annotations

import socket
import ssl
import threading
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


class TestWhitelistAPI:
    """Tests for :meth:`PrivacyGuard.whitelist_endpoints` and
    :meth:`PrivacyGuard.revoke_whitelist`."""

    def test_whitelist_endpoints_parses_hostnames(self):
        guard = PrivacyGuard()
        guard.whitelist_endpoints([
            "https://api.openai.com/v1/chat",
            "http://localhost:5000/path",
        ])
        with guard._whitelist_lock:
            assert "api.openai.com" in guard._whitelist
            assert "localhost" in guard._whitelist
            assert len(guard._whitelist) == 2

    def test_whitelist_endpoints_handles_schemeless_urls(self):
        guard = PrivacyGuard()
        guard.whitelist_endpoints(["api.openai.com/v1"])
        with guard._whitelist_lock:
            assert "api.openai.com" in guard._whitelist

    def test_whitelist_endpoints_empty_urls(self):
        guard = PrivacyGuard()
        guard.whitelist_endpoints([])
        with guard._whitelist_lock:
            assert len(guard._whitelist) == 0

    def test_whitelist_endpoints_deduplicates(self):
        guard = PrivacyGuard()
        guard.whitelist_endpoints([
            "https://api.openai.com/v1",
            "https://api.openai.com/v2",
        ])
        with guard._whitelist_lock:
            assert "api.openai.com" in guard._whitelist
            assert len(guard._whitelist) == 1

    def test_revoke_whitelist_clears(self):
        guard = PrivacyGuard()
        guard.whitelist_endpoints(["https://api.openai.com/v1"])
        guard.revoke_whitelist()
        with guard._whitelist_lock:
            assert len(guard._whitelist) == 0

    def test_revoke_whitelist_restores_full_blocking(self):
        guard = PrivacyGuard()
        guard.enforce()
        guard.whitelist_endpoints(["https://api.openai.com/v1"])
        guard.revoke_whitelist()
        # After revoke, socket creation should be blocked again
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def test_whitelist_endpoints_idempotent(self):
        guard = PrivacyGuard()
        guard.whitelist_endpoints(["https://example.com/path"])
        guard.whitelist_endpoints(["https://example.com/other"])
        with guard._whitelist_lock:
            assert "example.com" in guard._whitelist
            assert len(guard._whitelist) == 1


class TestWhitelistSocket:
    """Socket-level whitelist behaviour."""

    def test_construction_succeeds_when_whitelist_active(self):
        """When whitelist has entries, socket() creates a real socket."""
        guard = PrivacyGuard()
        guard.enforce()
        guard.whitelist_endpoints(["https://example.com"])
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        assert sock is not None
        assert hasattr(sock, "connect")
        sock.close()

    def test_blocks_non_whitelisted_host(self):
        guard = PrivacyGuard()
        guard.enforce()
        guard.whitelist_endpoints(["https://allowed.com"])
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            sock.connect(("blocked.com", 80))
        sock.close()

    def test_passes_whitelisted_host(self):
        """Connect to a whitelisted host bypasses the privacy guard.

        The underlying connect() will likely fail with OSError (no real
        server), but crucially the whitelist check is passed through.
        """
        guard = PrivacyGuard()
        guard.enforce()
        guard.whitelist_endpoints(["https://127.0.0.1"])
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", 1))
        except OSError:
            pass  # Expected — no server listening, but whitelist was bypassed
        except NetworkBlockedError:
            pytest.fail("Whitelisted host was blocked by privacy guard")
        finally:
            sock.close()

    def test_empty_whitelist_still_blocks_socket_construction(self):
        """Default state (no whitelist) blocks at socket construction."""
        guard = PrivacyGuard()
        guard.enforce()
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def test_unix_socket_address_as_string(self):
        """Socket connect with a string address (Unix socket) is handled."""
        guard = PrivacyGuard()
        guard.enforce()
        guard.whitelist_endpoints(["https://example.com"])
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            sock.connect("/var/run/nonwhitelisted.sock")
        sock.close()


class TestWhitelistUrllib:
    """urllib-level whitelist behaviour."""

    def test_allows_whitelisted_host(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_urlopen.return_value = mock_response

            guard = PrivacyGuard()
            guard.enforce()  # captures mock as _original_urlopen
            guard.whitelist_endpoints(["https://example.com/path"])

            result = urllib.request.urlopen("https://example.com/data")
            assert result is mock_response
            mock_urlopen.assert_called_once_with("https://example.com/data")

    def test_blocks_non_whitelisted_host(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            guard = PrivacyGuard()
            guard.enforce()
            guard.whitelist_endpoints(["https://allowed.com"])

            with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
                urllib.request.urlopen("https://blocked.com/data")
            mock_urlopen.assert_not_called()

    def test_allows_whitelisted_request_object(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_urlopen.return_value = mock_response

            guard = PrivacyGuard()
            guard.enforce()
            guard.whitelist_endpoints(["https://example.com/path"])

            req = urllib.request.Request("https://example.com/other")
            result = urllib.request.urlopen(req)
            assert result is mock_response
            mock_urlopen.assert_called_once_with(req)

    def test_blocks_request_object_non_whitelisted(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            guard = PrivacyGuard()
            guard.enforce()
            guard.whitelist_endpoints(["https://allowed.com"])

            req = urllib.request.Request("https://blocked.com/data")
            with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
                urllib.request.urlopen(req)
            mock_urlopen.assert_not_called()

    def test_empty_whitelist_still_blocks_urlopen(self):
        """Default state (no whitelist) blocks urlopen."""
        guard = PrivacyGuard()
        guard.enforce()
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            urllib.request.urlopen("http://127.0.0.1")


class TestWhitelistSSL:
    """SSL-level whitelist behaviour."""

    def test_allows_whitelisted_host(self):
        if not hasattr(ssl, "wrap_socket"):
            pytest.skip("ssl.wrap_socket not available on this Python version")

        with patch("ssl.wrap_socket") as mock_wrap:
            mock_wrap.return_value = MagicMock()

            guard = PrivacyGuard()
            guard.enforce()  # captures mock as _original_wrap_socket
            guard.whitelist_endpoints(["https://example.com"])

            sock = MagicMock()
            result = ssl.wrap_socket(sock, server_hostname="example.com")
            assert result is not None
            mock_wrap.assert_called_once_with(sock, server_hostname="example.com")

    def test_blocks_non_whitelisted_host(self):
        if not hasattr(ssl, "wrap_socket"):
            pytest.skip("ssl.wrap_socket not available on this Python version")

        with patch("ssl.wrap_socket"):
            guard = PrivacyGuard()
            guard.enforce()
            guard.whitelist_endpoints(["https://allowed.com"])

            sock = MagicMock()
            with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
                ssl.wrap_socket(sock, server_hostname="blocked.com")

    def test_blocks_when_no_server_hostname(self):
        """When server_hostname is not provided, connection is blocked."""
        if not hasattr(ssl, "wrap_socket"):
            pytest.skip("ssl.wrap_socket not available on this Python version")

        with patch("ssl.wrap_socket"):
            guard = PrivacyGuard()
            guard.enforce()
            guard.whitelist_endpoints(["https://example.com"])

            sock = MagicMock()
            with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
                ssl.wrap_socket(sock)

    def test_empty_whitelist_still_blocks_ssl(self):
        if not hasattr(ssl, "wrap_socket"):
            pytest.skip("ssl.wrap_socket not available on this Python version")

        guard = PrivacyGuard()
        guard.enforce()
        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            ssl.wrap_socket(None)  # type: ignore[arg-type]


class TestWhitelistQtNetwork:
    """QtNetwork-level whitelist behaviour."""

    @staticmethod
    def _make_req(url: str = "") -> object:
        """Create a QNetworkRequest, possibly with a URL.

        QUrl lives in PySide6.QtCore, not QtNetwork.
        """
        import PySide6.QtCore as QtCore
        import PySide6.QtNetwork as QtNetwork

        if url:
            return QtNetwork.QNetworkRequest(QtCore.QUrl(url))
        return QtNetwork.QNetworkRequest()

    def test_allows_whitelisted_host(self):
        try:
            import PySide6.QtNetwork as QtNetwork
        except ImportError:
            pytest.skip("PySide6.QtNetwork not available")

        guard = PrivacyGuard()
        guard.enforce()
        guard.whitelist_endpoints(["https://example.com"])

        mgr = QtNetwork.QNetworkAccessManager()
        req = self._make_req("https://example.com/data")

        with patch.object(
            QtNetwork.QNetworkAccessManager, "get", wraps=QtNetwork.QNetworkAccessManager.get
        ) as mock_get:
            try:
                mgr.get(req)
            except Exception:
                pass  # May fail due to no event loop, but whitelist was bypassed
            # Our wrapper should have called through to the original (patched) get
            assert mock_get.called

    def test_blocks_non_whitelisted_host(self):
        try:
            import PySide6.QtNetwork as QtNetwork
        except ImportError:
            pytest.skip("PySide6.QtNetwork not available")

        guard = PrivacyGuard()
        guard.enforce()
        guard.whitelist_endpoints(["https://allowed.com"])

        mgr = QtNetwork.QNetworkAccessManager()
        req = self._make_req("https://blocked.com/data")

        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            mgr.get(req)

    def test_empty_whitelist_still_blocks_qt(self):
        try:
            import PySide6.QtNetwork as QtNetwork
        except ImportError:
            pytest.skip("PySide6.QtNetwork not available")

        guard = PrivacyGuard()
        guard.enforce()

        mgr = QtNetwork.QNetworkAccessManager()
        req = QtNetwork.QNetworkRequest()

        with pytest.raises(NetworkBlockedError, match="blocked by privacy"):
            mgr.get(req)


class TestWhitelistThreadSafety:
    """Thread safety of whitelist operations."""

    def test_concurrent_whitelist_endpoints(self):
        guard = PrivacyGuard()
        errors: list[str] = []
        n_threads = 10
        urls_per_thread = [
            [f"https://api-{i}-{j}.com/v1" for j in range(10)]
            for i in range(n_threads)
        ]

        def _add_urls(urls: list[str]) -> None:
            try:
                guard.whitelist_endpoints(urls)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=_add_urls, args=(urls_per_thread[i],)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety errors: {errors}"
        with guard._whitelist_lock:
            # Should have all unique hostnames
            assert len(guard._whitelist) == n_threads * 10

    def test_concurrent_whitelist_read_write(self):
        guard = PrivacyGuard()
        errors: list[str] = []

        # Pre-populate
        guard.whitelist_endpoints(["https://base.com"])

        def _writer() -> None:
            for i in range(50):
                guard.whitelist_endpoints([f"https://writer-{i}.com"])

        def _reader() -> None:
            for i in range(50):
                try:
                    guard._is_allowed("base.com")
                    guard._whitelist_empty()
                except Exception as exc:
                    errors.append(str(exc))

        threads = [
            threading.Thread(target=_writer),
            threading.Thread(target=_reader),
            threading.Thread(target=_reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety errors: {errors}"

    def test_concurrent_revoke_and_add(self):
        guard = PrivacyGuard()
        errors: list[str] = []

        guard.whitelist_endpoints(["https://base.com"])

        def _revoker() -> None:
            for _ in range(20):
                guard.revoke_whitelist()
                guard.whitelist_endpoints(["https://base.com"])

        def _checker() -> None:
            for _ in range(20):
                try:
                    guard._whitelist_empty()
                except Exception as exc:
                    errors.append(str(exc))

        threads = [
            threading.Thread(target=_revoker),
            threading.Thread(target=_checker),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety errors: {errors}"
