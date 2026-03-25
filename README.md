# portmap

Show which processes are listening on which ports — with filtering by port number or process name.

## Install

```bash
pip install portmap[full]
```

(`psutil` is required for process information. The base `pip install portmap` works but will prompt you to install it.)

## Usage

```bash
# Show all listening ports
portmap

# Show only specific ports
portmap 8080 3000 5432

# Filter by process name (partial match)
portmap --process node
portmap --process python

# Include UDP sockets
portmap --udp

# Show full command lines
portmap --cmd

# Include established connections, not just listeners
portmap --all
```

## Example output

```
PORT   PROTO  HOST  PID      PROCESS
────────────────────────────────────────────────────
  3000   tcp    *     41234    node
  5432   tcp    *     812      postgres
  8080   tcp    *     9876     uvicorn
  11434  tcp    lo    22980    ollama

4 ports shown.
```

## License

MIT
