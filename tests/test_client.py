"""Client tests."""

from pathlib import Path

import pytest

from wyoming.client import (
    AsyncClient,
    AsyncStdioClient,
    AsyncTcpClient,
    AsyncUnixClient,
)


def test_from_uri() -> None:
    """Test AsyncClient.from_uri"""
    # Bad scheme
    with pytest.raises(ValueError):
        AsyncClient.from_uri("ftp://127.0.0.1:5000")

    # Missing hostname
    with pytest.raises(ValueError):
        AsyncClient.from_uri("tcp://:5000")

    # Missing port
    with pytest.raises(ValueError):
        AsyncClient.from_uri("tcp://127.0.0.1")

    stdio_client = AsyncClient.from_uri("stdio://")
    assert isinstance(stdio_client, AsyncStdioClient)

    tcp_client = AsyncClient.from_uri("tcp://127.0.0.1:5000")
    assert isinstance(tcp_client, AsyncTcpClient)
    assert tcp_client.host == "127.0.0.1"
    assert tcp_client.port == 5000

    unix_client = AsyncClient.from_uri("unix:///path/to/socket")
    assert isinstance(unix_client, AsyncUnixClient)
    assert unix_client.socket_path == Path("/path/to/socket")
