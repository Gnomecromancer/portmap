"""Scan listening ports and map them to processes using psutil."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


@dataclass
class PortEntry:
    port: int
    protocol: str        # "tcp" | "tcp6" | "udp" | "udp6"
    host: str            # local address (e.g. "0.0.0.0", "127.0.0.1", "::")
    pid: int | None
    name: str | None     # process name
    cmdline: str | None  # truncated command line
    status: str          # "LISTEN" | "ESTABLISHED" | etc.

    @property
    def is_ipv6(self) -> bool:
        return "6" in self.protocol or ":" in self.host

    @property
    def display_host(self) -> str:
        if self.host in ("0.0.0.0", "::", "*"):
            return "*"
        return self.host


def has_psutil() -> bool:
    return _HAS_PSUTIL


def get_listening_ports(
    *,
    include_udp: bool = False,
    include_established: bool = False,
) -> list[PortEntry]:
    """Return a list of active listening (and optionally established) connections.

    Args:
        include_udp: If True, include UDP sockets.
        include_established: If True, include established connections in addition to LISTEN.
    """
    if not _HAS_PSUTIL:
        raise RuntimeError(
            "psutil is required: pip install portmap[full] or pip install psutil"
        )

    kinds = ["tcp", "tcp6"]
    if include_udp:
        kinds.extend(["udp", "udp6"])

    # Build pid→process info map
    pid_info: dict[int, tuple[str, str]] = {}
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            info = proc.info
            name = info.get("name") or ""
            cmdline = info.get("cmdline") or []
            cmd = " ".join(cmdline)[:120] if cmdline else ""
            pid_info[proc.pid] = (name, cmd)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    entries: list[PortEntry] = []
    seen: set[tuple[int, str]] = set()

    for kind in kinds:
        try:
            conns = psutil.net_connections(kind=kind)
        except psutil.AccessDenied:
            continue

        for conn in conns:
            status = getattr(conn, "status", "") or ""

            if not include_established and status not in ("LISTEN", "NONE", ""):
                continue
            if include_established and status not in ("LISTEN", "ESTABLISHED", "NONE", ""):
                continue

            laddr = conn.laddr
            if not laddr:
                continue

            port = laddr.port
            host = laddr.ip

            key = (port, kind)
            if key in seen:
                continue
            seen.add(key)

            pid = conn.pid
            name, cmd = pid_info.get(pid, (None, None)) if pid else (None, None)

            entries.append(
                PortEntry(
                    port=port,
                    protocol=kind,
                    host=host,
                    pid=pid,
                    name=name,
                    cmdline=cmd or None,
                    status=status or "LISTEN",
                )
            )

    return sorted(entries, key=lambda e: e.port)
