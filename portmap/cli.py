"""CLI for portmap."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from .scanner import get_listening_ports, has_psutil, PortEntry


def _bold(s: str) -> str:
    return f"\033[1m{s}\033[0m"


def _cyan(s: str) -> str:
    return f"\033[36m{s}\033[0m"


def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m"


def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m"


def _dim(s: str) -> str:
    return f"\033[2m{s}\033[0m"


def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m"


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("ports", nargs=-1, type=int)
@click.option(
    "--process", "-p",
    default=None,
    metavar="NAME",
    help="Filter by process name (partial match).",
)
@click.option(
    "--udp", "include_udp",
    is_flag=True, default=False,
    help="Include UDP sockets.",
)
@click.option(
    "--all", "include_established",
    is_flag=True, default=False,
    help="Include established connections, not just listeners.",
)
@click.option(
    "--no-color", is_flag=True, default=False,
    help="Disable ANSI color output.",
)
@click.option(
    "--cmd", is_flag=True, default=False,
    help="Show full command line for each process.",
)
@click.version_option(package_name="whoport")
def main(
    ports: tuple[int, ...],
    process: str | None,
    include_udp: bool,
    include_established: bool,
    no_color: bool,
    cmd: bool,
) -> None:
    """Show which processes are listening on which ports.

    Optionally filter by specific port numbers or process name.

    \b
    Examples:
      portmap                  # all listening ports
      portmap 8080 3000        # only these ports
      portmap --process node   # only node processes
      portmap --udp            # include UDP sockets
      portmap --cmd            # show full command lines
    """
    if not has_psutil():
        click.echo(
            "psutil is required. Install it with:\n"
            "  pip install portmap[full]\n"
            "  or: pip install psutil",
            err=True,
        )
        sys.exit(1)

    bold = (lambda s: s) if no_color else _bold
    cyan = (lambda s: s) if no_color else _cyan
    green = (lambda s: s) if no_color else _green
    yellow = (lambda s: s) if no_color else _yellow
    dim = (lambda s: s) if no_color else _dim
    red = (lambda s: s) if no_color else _red

    try:
        entries = get_listening_ports(
            include_udp=include_udp,
            include_established=include_established,
        )
    except PermissionError:
        click.echo(
            red("Permission denied. Try running with elevated privileges."),
            err=True,
        )
        sys.exit(1)

    # Apply filters
    if ports:
        entries = [e for e in entries if e.port in ports]
    if process:
        proc_lower = process.lower()
        entries = [
            e for e in entries
            if (e.name and proc_lower in e.name.lower())
            or (e.cmdline and proc_lower in e.cmdline.lower())
        ]

    if not entries:
        click.echo(dim("No matching ports found."))
        return

    # Column layout
    port_w = max(len(str(e.port)) for e in entries)
    proto_w = max(len(e.protocol) for e in entries)
    host_w = max(len(e.display_host) for e in entries)
    name_w = max((len(e.name or "?") for e in entries), default=10)
    name_w = min(name_w, 20)

    header = (
        f"  {'PORT'.ljust(port_w)}  {'PROTO'.ljust(proto_w)}  "
        f"{'HOST'.ljust(host_w)}  {'PID'.ljust(7)}  {'PROCESS'.ljust(name_w)}"
    )
    if cmd:
        header += "  COMMAND"
    click.echo(bold(header))
    click.echo(dim("─" * max(len(header), 60)))

    for e in entries:
        port_str = cyan(str(e.port).ljust(port_w))
        proto_str = dim(e.protocol.ljust(proto_w))
        host_str = dim(e.display_host.ljust(host_w))
        pid_str = str(e.pid or "?").ljust(7)
        name_str = (e.name or dim("?")).ljust(name_w)

        line = f"  {port_str}  {proto_str}  {host_str}  {pid_str}  {name_str}"

        if cmd and e.cmdline:
            line += f"  {dim(e.cmdline[:80])}"

        click.echo(line)

    click.echo(dim(f"\n{len(entries)} port{'s' if len(entries) != 1 else ''} shown."))
