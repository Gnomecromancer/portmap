"""CLI for portmap."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
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
@click.option(
    "--json", "output_json", is_flag=True, default=False,
    help="Output results as JSON (machine-readable).",
)
@click.option(
    "--watch", "-w", default=0, metavar="SECONDS", show_default=False,
    help="Refresh every N seconds (live view). 0 = run once.",
)
@click.version_option(package_name="whoport")
def main(
    ports: tuple[int, ...],
    process: str | None,
    include_udp: bool,
    include_established: bool,
    no_color: bool,
    cmd: bool,
    output_json: bool,
    watch: int,
) -> None:
    """Show which processes are listening on which ports.

    Optionally filter by specific port numbers or process name.

    \b
    Examples:
      whoport                  # all listening ports
      whoport 8080 3000        # only these ports
      whoport --process node   # only node processes
      whoport --udp            # include UDP sockets
      whoport --cmd            # show full command lines
      whoport --json           # machine-readable JSON
      whoport --watch 2        # refresh every 2 seconds
    """
    if not has_psutil():
        click.echo(
            "psutil is required. Install it with:\n"
            "  pip install whoport[full]\n"
            "  or: pip install psutil",
            err=True,
        )
        sys.exit(1)

    no_color = no_color or output_json
    bold = (lambda s: s) if no_color else _bold
    cyan = (lambda s: s) if no_color else _cyan
    dim = (lambda s: s) if no_color else _dim
    red = (lambda s: s) if no_color else _red

    def _fetch() -> list[PortEntry]:
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
        if ports:
            entries = [e for e in entries if e.port in ports]
        if process:
            proc_lower = process.lower()
            entries = [
                e for e in entries
                if (e.name and proc_lower in e.name.lower())
                or (e.cmdline and proc_lower in e.cmdline.lower())
            ]
        return entries

    def _print(entries: list[PortEntry]) -> None:
        if not entries:
            click.echo(dim("No matching ports found."))
            return

        port_w = max(len(str(e.port)) for e in entries)
        proto_w = max(len(e.protocol) for e in entries)
        host_w = max(len(e.display_host) for e in entries)
        name_w = min(max((len(e.name or "?") for e in entries), default=10), 20)

        header = (
            f"  {'PORT'.ljust(port_w)}  {'PROTO'.ljust(proto_w)}  "
            f"{'HOST'.ljust(host_w)}  {'PID'.ljust(7)}  {'PROCESS'.ljust(name_w)}"
        )
        if cmd:
            header += "  COMMAND"
        click.echo(bold(header))
        sep_char = "\u2500" if (sys.stdout.encoding or "").lower().startswith("utf") else "-"
        click.echo(dim(sep_char * max(len(header), 60)))

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

    if output_json:
        entries = _fetch()
        click.echo(json.dumps({
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "ports": [
                {
                    "port": e.port,
                    "protocol": e.protocol,
                    "host": e.display_host,
                    "pid": e.pid,
                    "name": e.name,
                    "cmdline": e.cmdline,
                }
                for e in entries
            ],
        }, indent=2))
        return

    if watch > 0:
        try:
            while True:
                click.clear()
                click.echo(dim(f"whoport — refreshing every {watch}s  (Ctrl+C to quit)"))
                click.echo(dim(f"updated: {datetime.now().strftime('%H:%M:%S')}\n"))
                _print(_fetch())
                time.sleep(watch)
        except KeyboardInterrupt:
            pass
        return

    _print(_fetch())
