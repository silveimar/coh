"""Test configuration for COH API."""

import pytest


@pytest.fixture
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"
