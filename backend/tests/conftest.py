"""
Pytest configuration and global fixtures for Deadline Rescue test suite.
Configures in-process ASGI HTTP transport for MCPClientBridge during tests.
"""
import pytest
from httpx import ASGITransport
from app.main import app
from app.services.mcp_client import MCPClientBridge


@pytest.fixture(autouse=True)
def setup_mcp_test_transport():
    transport = ASGITransport(app=app)
    MCPClientBridge.set_transport(transport)
    yield
    MCPClientBridge.set_transport(None)
