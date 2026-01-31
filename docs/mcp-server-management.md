# MCP Server Management

This document describes the MCP (Model Context Protocol) server lifecycle management commands added in WP12.

## Overview

The MCP server provides a conversational interface to Spec Kitty workflows. Server management includes:

- **Starting** the server with configurable transport (stdio/SSE)
- **Checking status** to see if server is running
- **Stopping** the server gracefully

## Commands

### `spec-kitty mcp start`

Start the MCP server with specified configuration.

**Usage:**
```bash
spec-kitty mcp start [OPTIONS]
```

**Options:**
- `--host TEXT`: Server host for SSE transport (default: "127.0.0.1")
- `--port INTEGER`: Server port for SSE transport (default: 8000)
- `--transport TEXT`: Transport mode - "stdio" or "sse" (default: "stdio")
- `--auth / --no-auth`: Enable API key authentication (default: no-auth)
- `--api-key TEXT`: API key if auth enabled
- `--config-file / --no-config-file`: Load from .kittify/mcp-config.yaml (default: config-file)

**Configuration Precedence:**
1. Environment variables (`MCP_SERVER_HOST`, `MCP_SERVER_PORT`, etc.)
2. Command-line options
3. `.kittify/mcp-config.yaml` file
4. Built-in defaults

**Examples:**

Start with stdio transport (for Claude Desktop, Cursor):
```bash
spec-kitty mcp start
```

Start with SSE transport (for web-based clients):
```bash
spec-kitty mcp start --transport sse --host 0.0.0.0 --port 8000
```

Start with authentication:
```bash
export MCP_SERVER_API_KEY="your-secret-key"
spec-kitty mcp start --auth
```

Ignore config file (use CLI options only):
```bash
spec-kitty mcp start --no-config-file --transport stdio
```

**PID File:**
The server writes its process ID to `.kittify/.mcp-server.pid` on startup. This prevents multiple server instances and enables status checking and graceful shutdown.

**Signal Handling:**
The server handles `SIGTERM` and `SIGINT` (Ctrl+C) signals gracefully:
- Cleans up PID file
- Closes open connections
- Exits cleanly

**Error Handling:**
- If port is unavailable (SSE transport), server will fail to start with clear error message
- If another server instance is running, start will fail with PID of running process
- On startup failure, PID file is automatically cleaned up

---

### `spec-kitty mcp status`

Check if MCP server is running and display configuration.

**Usage:**
```bash
spec-kitty mcp status
```

**Output:**
Displays a table with:
- Server status (Running/Not running)
- Process ID (if running)
- PID file path
- Transport mode
- Host and port (if SSE transport)
- Authentication status

**Examples:**

Check server status:
```bash
$ spec-kitty mcp status
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property     ┃ Value                         ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Status       │ Running                       │
│ PID          │ 12345                         │
│ PID File     │ .kittify/.mcp-server.pid      │
│ Transport    │ stdio                         │
│ Auth Enabled │ No                            │
└──────────────┴───────────────────────────────┘
```

**Exit Codes:**
- `0`: Server is running
- `1`: Server is not running

**Use Cases:**
- Health checks in monitoring scripts
- Verify server started successfully
- Troubleshoot connection issues

---

### `spec-kitty mcp stop`

Stop the MCP server gracefully.

**Usage:**
```bash
spec-kitty mcp stop [OPTIONS]
```

**Options:**
- `--timeout INTEGER`: Seconds to wait for graceful shutdown (default: 10)

**Examples:**

Stop server with default 10-second timeout:
```bash
spec-kitty mcp stop
```

Stop server with custom timeout:
```bash
spec-kitty mcp stop --timeout 30
```

**Process:**
1. Read PID from `.kittify/.mcp-server.pid`
2. Send `SIGTERM` to server process
3. Poll every 0.5s to check if process exited
4. If process exits within timeout, clean up PID file and report success
5. If timeout expires, report failure (process may need manual cleanup)

**Error Handling:**
- If PID file doesn't exist, reports "No MCP server running"
- If PID file is stale (process not running), cleans up and reports status
- If permission denied, reports error (server may be owned by another user)

**Stale PID Files:**
The command automatically detects and cleans up stale PID files (where the process ID exists in the file but the process is not running).

**Exit Codes:**
- `0`: Server stopped successfully
- `1`: Server not running, timeout expired, or other error

---

## Configuration File

### Location
`.kittify/mcp-config.yaml`

### Format
```yaml
# Server bind address (SSE only)
host: "127.0.0.1"

# Server port (SSE only)
port: 8000

# Transport: "stdio" or "sse"
transport: "stdio"

# Enable authentication
auth_enabled: false

# DO NOT store API keys in config file!
# Use MCP_SERVER_API_KEY environment variable instead
```

### Example File
See `.kittify/mcp-config.yaml.example` for a complete example with comments.

### Security Notes
- **NEVER** store API keys in the config file
- Use `MCP_SERVER_API_KEY` environment variable instead
- The config loader ignores `api_key` field if present (for security)
- For production deployments, use environment variables for all sensitive values

---

## Environment Variables

All configuration can be set via environment variables, which take highest precedence:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `MCP_SERVER_HOST` | Server bind address | `127.0.0.1` |
| `MCP_SERVER_PORT` | Server port | `8000` |
| `MCP_SERVER_TRANSPORT` | Transport mode | `stdio` |
| `MCP_SERVER_AUTH_ENABLED` | Enable auth | `false` |
| `MCP_SERVER_API_KEY` | API key | (none) |

**Example:**
```bash
export MCP_SERVER_HOST="0.0.0.0"
export MCP_SERVER_PORT="9000"
export MCP_SERVER_TRANSPORT="sse"
export MCP_SERVER_AUTH_ENABLED="true"
export MCP_SERVER_API_KEY="your-secret-key"

spec-kitty mcp start
```

---

## Process Management

### PID File

**Location:** `.kittify/.mcp-server.pid`

**Format:** Single line containing process ID (integer)

**Purpose:**
- Prevents multiple server instances
- Enables status checking without connecting to server
- Enables graceful shutdown via `spec-kitty mcp stop`

**Lifecycle:**
1. Created on `spec-kitty mcp start`
2. Read by `spec-kitty mcp status` and `spec-kitty mcp stop`
3. Deleted on `spec-kitty mcp stop` or server exit (SIGTERM/SIGINT)

**Stale Detection:**
If PID file exists but process is not running (e.g., server crashed), the commands automatically:
- Detect stale condition (via `os.kill(pid, 0)`)
- Clean up stale PID file
- Report appropriate status

### Signal Handlers

The server registers handlers for graceful shutdown:

**SIGTERM:**
- Sent by `spec-kitty mcp stop`
- Triggers cleanup and exit

**SIGINT (Ctrl+C):**
- Sent by user pressing Ctrl+C in terminal
- Triggers cleanup and exit

**Cleanup Actions:**
- Close open MCP connections
- Release file locks
- Save conversation state
- Remove PID file
- Exit with status 0

---

## Troubleshooting

### Server won't start

**Problem:** "MCP server already running"
**Solution:** Check if server is actually running with `spec-kitty mcp status`. If not, delete stale PID file: `rm .kittify/.mcp-server.pid`

**Problem:** "Port 8000 already in use" (SSE transport)
**Solution:** Use different port: `spec-kitty mcp start --port 9000`

**Problem:** "Configuration error: Invalid transport"
**Solution:** Use "stdio" or "sse": `spec-kitty mcp start --transport stdio`

### Server won't stop

**Problem:** `spec-kitty mcp stop` times out
**Solution:** Increase timeout: `spec-kitty mcp stop --timeout 60`

**Problem:** Process ID in PID file doesn't exist
**Solution:** Command automatically cleans up stale PID file. If you see this message, the server was not running.

**Problem:** Permission denied
**Solution:** Server may be owned by another user. Use `sudo` or kill process manually with root permissions.

### Configuration not loading

**Problem:** Changes to `mcp-config.yaml` not taking effect
**Solution:** 
1. Check if environment variables are overriding config file
2. Verify YAML syntax is correct (use `yamllint` or online validator)
3. Use `--no-config-file` flag to test without config file

**Problem:** API key not working
**Solution:** 
1. Verify `--auth` flag is set
2. Set `MCP_SERVER_API_KEY` environment variable (config file is ignored for security)
3. Check server logs for authentication errors

---

## Testing

Tests for server management commands are located in:
- `tests/mcp/test_config.py` - Configuration loading and PID file management
- `tests/mcp/test_cli_commands.py` - CLI command integration tests

**Run tests:**
```bash
pytest tests/mcp/test_config.py -v
pytest tests/mcp/test_cli_commands.py -v
```

**Test coverage:**
- Configuration loading from file and environment
- PID file creation, reading, removal
- Stale PID file detection
- Process existence checking
- Server lifecycle (start, status, stop)
- Error handling (duplicate start, missing PID, etc.)
