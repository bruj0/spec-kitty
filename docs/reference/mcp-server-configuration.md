# MCP Server Configuration Reference

**Complete guide to configuring the Spec Kitty MCP server**

This reference documents all configuration options for the MCP server, including environment variables, command-line flags, and client configuration.

---

## Configuration Methods

The MCP server can be configured through:

1. **Environment variables** - Set before starting server
2. **Command-line flags** - Passed to `spec-kitty mcp start`
3. **Config file** - `.kittify/mcp-config.yaml` (optional)
4. **Client configuration** - MCP client config files

**Priority order** (highest to lowest):
1. Command-line flags (override everything)
2. Environment variables
3. Config file (`.kittify/mcp-config.yaml`)
4. Default values

---

## Environment Variables

### Core Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PROJECT_PATH` | string | (required) | Absolute path to Spec Kitty project |
| `MCP_SERVER_HOST` | string | `127.0.0.1` | Server bind address (SSE only) |
| `MCP_SERVER_PORT` | integer | `8000` | Server port (SSE only) |
| `MCP_TRANSPORT` | enum | `stdio` | Transport mode: `stdio` or `sse` |

**Example**:
```bash
export PROJECT_PATH="/Users/me/projects/billing-service"
export MCP_TRANSPORT="stdio"
spec-kitty mcp start
```

---

### Authentication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MCP_AUTH_ENABLED` | boolean | `false` | Enable API key authentication |
| `MCP_API_KEY` | string | `""` | API key for authentication (if enabled) |

**Example**:
```bash
export MCP_AUTH_ENABLED="true"
export MCP_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
spec-kitty mcp start
```

---

### Logging & Debugging

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MCP_LOG_LEVEL` | enum | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `MCP_LOG_FILE` | string | `""` | Log file path (stdout if empty) |

**Example**:
```bash
export MCP_LOG_LEVEL="DEBUG"
export MCP_LOG_FILE=".kittify/mcp-server.log"
spec-kitty mcp start
```

---

### Session Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MCP_SESSION_DIR` | string | `.kittify/mcp-sessions/` | Conversation state storage directory |
| `MCP_SESSION_TIMEOUT` | integer | `86400` | Session timeout in seconds (24 hours) |
| `MCP_MAX_SESSIONS` | integer | `100` | Maximum concurrent sessions |

**Example**:
```bash
export MCP_SESSION_TIMEOUT="43200"  # 12 hours
spec-kitty mcp start
```

---

### Locking Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MCP_LOCK_TIMEOUT` | integer | `300` | Lock acquisition timeout in seconds (5 min) |
| `MCP_LOCK_DIR` | string | `.kittify/` | Lock file directory |

**Example**:
```bash
export MCP_LOCK_TIMEOUT="600"  # 10 minutes
spec-kitty mcp start
```

---

## Command-Line Flags

### spec-kitty mcp start

**Synopsis**:
```bash
spec-kitty mcp start [OPTIONS]
```

**Options**:

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--transport` | enum | `stdio` | Transport mode: `stdio` or `sse` |
| `--host` | string | `127.0.0.1` | Server bind address (SSE only) |
| `--port` | integer | `8000` | Server port (SSE only) |
| `--auth / --no-auth` | boolean | `false` | Enable/disable authentication |
| `--api-key` | string | `""` | API key (if --auth enabled) |
| `--log-level` | enum | `INFO` | Log level |
| `--config` | string | `.kittify/mcp-config.yaml` | Config file path |

**Examples**:

```bash
# Start with stdio transport (default, recommended for local dev)
spec-kitty mcp start

# Start with SSE transport on custom port
spec-kitty mcp start --transport sse --port 8001

# Start with authentication enabled
spec-kitty mcp start --auth --api-key "your-secure-key-here"

# Start with debug logging
spec-kitty mcp start --log-level DEBUG

# Start with custom config file
spec-kitty mcp start --config /path/to/custom-config.yaml
```

---

### spec-kitty mcp status

**Synopsis**:
```bash
spec-kitty mcp status [OPTIONS]
```

**Options**:

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--json` | boolean | `false` | Output status as JSON |

**Examples**:

```bash
# Human-readable status
spec-kitty mcp status

# JSON output (for scripting)
spec-kitty mcp status --json
```

**Output**:
```
MCP Server Status
─────────────────
Status: Running
PID: 12345
Uptime: 2 hours, 15 minutes
Transport: stdio
Authentication: Disabled
Active Projects: 2
Active Sessions: 1
```

---

### spec-kitty mcp stop

**Synopsis**:
```bash
spec-kitty mcp stop [OPTIONS]
```

**Options**:

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--force` | boolean | `false` | Force kill server (skip graceful shutdown) |
| `--timeout` | integer | `30` | Graceful shutdown timeout (seconds) |

**Examples**:

```bash
# Graceful shutdown (wait for operations to complete)
spec-kitty mcp stop

# Force shutdown (kill immediately)
spec-kitty mcp stop --force

# Graceful shutdown with 60s timeout
spec-kitty mcp stop --timeout 60
```

---

## Config File Format

### .kittify/mcp-config.yaml

**Optional configuration file** for persistent server settings.

**Location**: `.kittify/mcp-config.yaml` in your project root

**Format**:
```yaml
# Transport configuration
transport: stdio  # or 'sse'
host: 127.0.0.1
port: 8000

# Authentication
auth:
  enabled: false
  api_key: ""  # Set via environment variable instead

# Logging
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  file: ""  # Empty = stdout, or path like '.kittify/mcp-server.log'

# Session management
sessions:
  directory: .kittify/mcp-sessions/
  timeout: 86400  # seconds (24 hours)
  max_sessions: 100

# Locking
locking:
  timeout: 300  # seconds (5 minutes)
  directory: .kittify/

# Performance
performance:
  max_workers: 10  # Concurrent tool invocations
  request_timeout: 60  # seconds
```

**Usage**:
```bash
# Use default config file
spec-kitty mcp start

# Use custom config file
spec-kitty mcp start --config /path/to/config.yaml
```

**Note**: API keys should NOT be stored in config files (use environment variables instead).

---

## Client Configuration

### Claude Desktop

**Location**:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Format**:
```json
{
  "mcpServers": {
    "spec-kitty": {
      "command": "spec-kitty",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "PROJECT_PATH": "/absolute/path/to/your/project",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**With authentication**:
```json
{
  "mcpServers": {
    "spec-kitty": {
      "command": "spec-kitty",
      "args": ["mcp", "start", "--transport", "stdio", "--auth"],
      "env": {
        "PROJECT_PATH": "/absolute/path/to/your/project",
        "MCP_API_KEY": "your-secure-api-key-here"
      }
    }
  }
}
```

---

### Cursor

**Location**: Cursor Settings JSON (`Cmd/Ctrl+Shift+P` → "Preferences: Open Settings (JSON)")

**Format**:
```json
{
  "mcp": {
    "servers": {
      "spec-kitty": {
        "command": "spec-kitty",
        "args": ["mcp", "start", "--transport", "stdio"],
        "env": {
          "PROJECT_PATH": "/absolute/path/to/your/project"
        }
      }
    }
  }
}
```

---

### VS Code (with MCP extension)

**Location**: `.vscode/settings.json` in your project

**Format**:
```json
{
  "mcp.servers": [
    {
      "name": "spec-kitty",
      "command": "spec-kitty",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "PROJECT_PATH": "${workspaceFolder}"
      }
    }
  ]
}
```

---

## Transport Configuration

### Stdio Transport (Recommended)

**Use case**: Local development with Claude Desktop, Cursor, or other local MCP clients

**Advantages**:
- No network binding required
- No port conflicts
- Ideal for single-user local development
- Lower latency (no HTTP overhead)

**Configuration**:
```bash
spec-kitty mcp start --transport stdio
```

**Client config** (Claude Desktop):
```json
{
  "command": "spec-kitty",
  "args": ["mcp", "start", "--transport", "stdio"]
}
```

---

### SSE Transport (Legacy)

**Use case**: Web-based MCP clients (legacy support only)

**Note**: SSE transport is considered legacy. For new projects, use stdio transport for local clients or wait for HTTP transport support (coming soon).

**Configuration**:
```bash
spec-kitty mcp start --transport sse --host 127.0.0.1 --port 8000
```

**Client config** (web client):
```javascript
const client = new MCPClient({
  transport: "sse",
  url: "http://127.0.0.1:8000"
});
```

**Port availability check**:
```bash
# Check if port is available
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Use different port if needed
spec-kitty mcp start --transport sse --port 8001
```

---

## Authentication Configuration

### When to Enable Authentication

**Enable authentication** if:
- Multiple users access the MCP server
- Server is network-accessible (SSE transport on non-localhost)
- Project contains sensitive data
- Compliance requirements (audit trails)

**Disable authentication** if:
- Single-user local development
- Trusted local environment (stdio transport)
- No sensitive data

---

### Generating Secure API Keys

**Requirements**:
- Minimum 32 characters
- High entropy (cryptographically random)
- Never commit to version control

**Generation methods**:

```bash
# Method 1: Python secrets module (recommended)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Method 2: OpenSSL
openssl rand -base64 32

# Method 3: /dev/urandom (Linux/macOS)
head -c 32 /dev/urandom | base64

# Method 4: Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

---

### API Key Storage

**❌ NEVER**:
```yaml
# DON'T store API key in config file (version controlled)
auth:
  api_key: "my-secret-key"  # ❌ BAD
```

**✅ ALWAYS**:
```bash
# Store in environment variable
export MCP_API_KEY="your-secret-key"

# Or in client config (not version controlled)
{
  "env": {
    "MCP_API_KEY": "your-secret-key"
  }
}

# Or use secrets manager
export MCP_API_KEY=$(aws secretsmanager get-secret-value --secret-id mcp-api-key --query SecretString --output text)
```

---

## Performance Tuning

### Concurrent Requests

**Default**: 10 concurrent tool invocations

**Increase for high load**:
```yaml
# .kittify/mcp-config.yaml
performance:
  max_workers: 50
```

**Note**: Higher concurrency increases memory usage.

---

### Session Cleanup

**Default**: 24-hour session timeout, max 100 sessions

**Aggressive cleanup** (low memory):
```yaml
sessions:
  timeout: 3600  # 1 hour
  max_sessions: 20
```

**Lenient cleanup** (high memory):
```yaml
sessions:
  timeout: 604800  # 7 days
  max_sessions: 500
```

---

### Lock Timeout

**Default**: 5 minutes

**Short timeout** (fast-paced development):
```yaml
locking:
  timeout: 60  # 1 minute
```

**Long timeout** (slow operations):
```yaml
locking:
  timeout: 900  # 15 minutes
```

---

## Troubleshooting Configuration

### Issue: Environment variables not recognized

**Cause**: Variables not exported or wrong shell

**Solution**:
```bash
# Verify variables are set
echo $MCP_API_KEY

# Export variables (bash/zsh)
export MCP_API_KEY="your-key"

# PowerShell
$env:MCP_API_KEY = "your-key"

# Verify server sees them
spec-kitty mcp start --log-level DEBUG
# Should log: "Loaded MCP_API_KEY from environment"
```

---

### Issue: Config file not loaded

**Cause**: File not at default location or invalid YAML

**Solution**:
```bash
# Verify file exists
ls -la .kittify/mcp-config.yaml

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('.kittify/mcp-config.yaml'))"

# Specify config file explicitly
spec-kitty mcp start --config .kittify/mcp-config.yaml
```

---

### Issue: Client can't connect

**Cause**: PROJECT_PATH not absolute or doesn't exist

**Solution**:
```json
❌ WRONG:
{
  "env": {
    "PROJECT_PATH": "~/projects/app"  // Not expanded
  }
}

✅ CORRECT:
{
  "env": {
    "PROJECT_PATH": "/Users/me/projects/app"  // Absolute
  }
}
```

---

## Configuration Examples

### Example 1: Local Development (Default)

```bash
# Minimal configuration for local dev
spec-kitty mcp start
```

**Client config** (Claude Desktop):
```json
{
  "mcpServers": {
    "spec-kitty": {
      "command": "spec-kitty",
      "args": ["mcp", "start"],
      "env": {
        "PROJECT_PATH": "/Users/me/projects/app"
      }
    }
  }
}
```

---

### Example 2: Multi-User Server (SSE + Authentication)

```bash
# Server configuration
export MCP_AUTH_ENABLED="true"
export MCP_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
spec-kitty mcp start --transport sse --host 0.0.0.0 --port 8000
```

**Client config**:
```javascript
const client = new MCPClient({
  transport: "sse",
  url: "http://server-hostname:8000",
  headers: {
    "Authorization": `Bearer ${process.env.MCP_API_KEY}`
  }
});
```

---

### Example 3: Debug Mode

```bash
# Enable verbose logging
export MCP_LOG_LEVEL="DEBUG"
export MCP_LOG_FILE=".kittify/mcp-debug.log"
spec-kitty mcp start --log-level DEBUG
```

---

## Next Steps

**Explore more**:
- [MCP Server Quickstart](../tutorials/mcp-server-quickstart.md) - Get started quickly
- [MCP Tools Reference](../reference/mcp-tools.md) - Available operations
- [Troubleshooting](../how-to/troubleshoot-mcp.md) - Common issues

---

*Last updated: 2026-01-31*  
*Spec Kitty version: 0.14.0+*
