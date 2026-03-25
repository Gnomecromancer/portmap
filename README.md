# whoport

Show which processes are listening on which ports — with filtering by port number or process name.

## Install

```bash
pip install whoport[full]
```

(`psutil` is required for process information. The base `pip install whoport` works but will prompt you to install it.)

## Usage

```bash
# Show all listening ports
whoport

# Show only specific ports
whoport 8080 3000 5432

# Filter by process name (partial match)
whoport --process node
whoport --process python

# Include UDP sockets
whoport --udp

# Show full command lines
whoport --cmd

# Include established connections, not just listeners
whoport --all
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
