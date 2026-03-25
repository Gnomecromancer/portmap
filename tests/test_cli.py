"""Tests for portmap CLI."""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from portmap.cli import main
from portmap.scanner import PortEntry


def _entry(port=8080, name="python", pid=1234, protocol="tcp", host="0.0.0.0",
           cmdline="python -m uvicorn"):
    return PortEntry(
        port=port, protocol=protocol, host=host,
        pid=pid, name=name, cmdline=cmdline, status="LISTEN"
    )


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_no_psutil_exits_one():
    runner = CliRunner()
    with patch("portmap.cli.has_psutil", return_value=False):
        result = runner.invoke(main, [])
    assert result.exit_code == 1


def test_shows_entries():
    entries = [_entry(8080, "uvicorn"), _entry(3000, "node")]
    runner = CliRunner()
    with patch("portmap.cli.has_psutil", return_value=True), \
         patch("portmap.cli.get_listening_ports", return_value=entries):
        result = runner.invoke(main, ["--no-color"])
    assert "8080" in result.output
    assert "uvicorn" in result.output
    assert "3000" in result.output
    assert result.exit_code == 0


def test_filter_by_port():
    entries = [_entry(8080, "uvicorn"), _entry(3000, "node")]
    runner = CliRunner()
    with patch("portmap.cli.has_psutil", return_value=True), \
         patch("portmap.cli.get_listening_ports", return_value=entries):
        result = runner.invoke(main, ["8080", "--no-color"])
    assert "8080" in result.output
    assert "3000" not in result.output


def test_filter_by_process():
    entries = [_entry(8080, "uvicorn"), _entry(3000, "node")]
    runner = CliRunner()
    with patch("portmap.cli.has_psutil", return_value=True), \
         patch("portmap.cli.get_listening_ports", return_value=entries):
        result = runner.invoke(main, ["--process", "node", "--no-color"])
    assert "3000" in result.output
    assert "8080" not in result.output


def test_no_matches():
    entries = [_entry(8080, "uvicorn")]
    runner = CliRunner()
    with patch("portmap.cli.has_psutil", return_value=True), \
         patch("portmap.cli.get_listening_ports", return_value=entries):
        result = runner.invoke(main, ["9999", "--no-color"])
    assert "No matching" in result.output
    assert result.exit_code == 0


def test_cmd_shows_cmdline():
    entries = [_entry(8080, "uvicorn", cmdline="uvicorn app:main --reload")]
    runner = CliRunner()
    with patch("portmap.cli.has_psutil", return_value=True), \
         patch("portmap.cli.get_listening_ports", return_value=entries):
        result = runner.invoke(main, ["--cmd", "--no-color"])
    assert "uvicorn app:main" in result.output
