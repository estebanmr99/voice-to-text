"""Pytest fixtures and configuration."""

import pytest


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication singleton for the test session.

    Creates the QApplication if it does not already exist.
    This avoids conflicts with PySide6/Qt singleton requirements.
    """
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PySide6 not available")

    app = QApplication.instance()
    if app is None:
        app = QApplication(["test"])
    yield app
    # Do not call app.quit() here — session-scoped singleton
    # must remain alive for the full test session.
