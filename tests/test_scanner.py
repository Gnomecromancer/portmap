"""Tests for portmap.scanner."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from portmap.scanner import get_listening_ports, PortEntry


def _mock_conn(port, host="0.0.0.0", status="LISTEN", pid=1234, kind="tcp"):
    conn = MagicMock()
    conn.laddr = MagicMock()
    conn.laddr.port = port
    conn.laddr.ip = host
    conn.status = status
    conn.pid = pid
    return conn


def _mock_proc(pid, name, cmdline=None):
    proc = MagicMock()
    proc.pid = pid
    proc.info = {"pid": pid, "name": name, "cmdline": cmdline or [name]}
    return proc


def test_get_listening_returns_sorted(tmp_path):
    conns = [_mock_conn(8080), _mock_conn(3000), _mock_conn(443)]
    proc = _mock_proc(1234, "python")

    with patch("portmap.scanner.psutil.net_connections", return_value=conns), \
         patch("portmap.scanner.psutil.process_iter", return_value=[proc]):
        entries = get_listening_ports()

    ports = [e.port for e in entries]
    assert ports == sorted(ports)


def test_get_listening_maps_process_name():
    conns = [_mock_conn(8080, pid=999)]
    proc = _mock_proc(999, "uvicorn", ["uvicorn", "app:main"])

    with patch("portmap.scanner.psutil.net_connections", return_value=conns), \
         patch("portmap.scanner.psutil.process_iter", return_value=[proc]):
        entries = get_listening_ports()

    assert entries[0].name == "uvicorn"
    assert entries[0].pid == 999


def test_get_listening_no_process_for_pid():
    conns = [_mock_conn(8080, pid=None)]

    with patch("portmap.scanner.psutil.net_connections", return_value=conns), \
         patch("portmap.scanner.psutil.process_iter", return_value=[]):
        entries = get_listening_ports()

    assert entries[0].name is None
    assert entries[0].pid is None


def test_get_listening_excludes_established_by_default():
    conns = [
        _mock_conn(8080, status="LISTEN"),
        _mock_conn(8081, status="ESTABLISHED"),
    ]

    with patch("portmap.scanner.psutil.net_connections", return_value=conns), \
         patch("portmap.scanner.psutil.process_iter", return_value=[]):
        entries = get_listening_ports(include_established=False)

    ports = [e.port for e in entries]
    assert 8080 in ports
    assert 8081 not in ports


def test_get_listening_includes_established_when_requested():
    conns = [
        _mock_conn(8080, status="LISTEN"),
        _mock_conn(8081, status="ESTABLISHED"),
    ]

    with patch("portmap.scanner.psutil.net_connections", return_value=conns), \
         patch("portmap.scanner.psutil.process_iter", return_value=[]):
        entries = get_listening_ports(include_established=True)

    ports = [e.port for e in entries]
    assert 8080 in ports
    assert 8081 in ports


def test_deduplicates_same_port_and_protocol():
    # Two identical tcp connections on the same port — should collapse to one entry
    conns = [_mock_conn(8080, kind="tcp"), _mock_conn(8080, kind="tcp")]

    def _net_connections(kind):
        return conns if kind == "tcp" else []

    with patch("portmap.scanner.psutil.net_connections", side_effect=_net_connections), \
         patch("portmap.scanner.psutil.process_iter", return_value=[]):
        entries = get_listening_ports()

    assert len([e for e in entries if e.port == 8080 and e.protocol == "tcp"]) == 1


def test_display_host_wildcard():
    e = PortEntry(port=80, protocol="tcp", host="0.0.0.0", pid=1, name="n", cmdline=None, status="LISTEN")
    assert e.display_host == "*"

    e2 = PortEntry(port=80, protocol="tcp6", host="::", pid=1, name="n", cmdline=None, status="LISTEN")
    assert e2.display_host == "*"

    e3 = PortEntry(port=80, protocol="tcp", host="127.0.0.1", pid=1, name="n", cmdline=None, status="LISTEN")
    assert e3.display_host == "127.0.0.1"
