# MCP Server Quickstart Guide

**Get started with the Spec Kitty MCP Server in 5 minutes**

This tutorial walks you through installing the Spec Kitty MCP server, configuring an MCP client (Claude Desktop or Cursor), and running your first conversational workflow command.

---

## Prerequisites

- **Spec Kitty CLI installed** (v0.14.0+): `pip install spec-kitty-cli`
- **A Spec Kitty project initialized**: Run `spec-kitty init` in your project directory
- **An MCP client**: [Claude Desktop](https://claude.ai/download) or [Cursor](https://cursor.sh) (recommended for first-time users)
- **Python 3.11+**: Check with `python --version`

---

## Step 1: Install Dependencies

The MCP server requires FastMCP and filelock. These are automatically installed with spec-kitty v0.14.0+:

```bash
# Verify installation
pip show spec-kitty-cli | grep Version

# If older than 0.14.0, upgrade:
pip install --upgrade spec-kitty-cli
```

**Dependencies included**:
- `fastmcp>=1.0.0,<2.0.0` - MCP protocol framework
- `filelock>=3.0.0` - Concurrency control for multi-client access

---

## Step 2: Configure the MCP Server

### Option A: Stdio Transport (Recommended for Local Development)

**Best for**: Claude Desktop, Cursor, local MCP clients

**Configuration**:
- No network binding required (uses stdin/stdout)
- Ideal for trusted local environments
- No authentication needed for single-user setups

### Option B: SSE Transport (Legacy)

**Best for**: Web-based MCP clients (legacy)

**Note**: SSE transport is considered legacy. For new projects, use HTTP transport (not yet implemented in Spec Kitty MCP server). For local development, use stdio transport.

**Configuration**:
- Binds to `host:port` (default: `127.0.0.1:8000`)
- Requires port availability
- Supports optional API key authentication

---

## Step 3: Configure Your MCP Client

### Claude Desktop Configuration

1. **Locate Claude Desktop config file**:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Add Spec Kitty MCP server**:

```json
{
  "mcpServers": {
    "spec-kitty": {
      "command": "spec-kitty",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "PROJECT_PATH": "/absolute/path/to/your/spec-kitty-project"
      }
    }
  }
}
```

3. **Restart Claude Desktop** to load the new configuration.

4. **Verify connection**: Open a new chat and type "list features in my project" - Claude should invoke the MCP server.

---

### Cursor Configuration

1. **Open Cursor Settings**: `Cmd/Ctrl+Shift+P` → "Preferences: Open Settings (JSON)"

2. **Add MCP server configuration**:

```json
{
  "mcp": {
    "servers": {
      "spec-kitty": {
        "command": "spec-kitty",
        "args": ["mcp", "start", "--transport", "stdio"],
        "env": {
          "PROJECT_PATH": "/absolute/path/to/your/spec-kitty-project"
        }
      }
    }
  }
}
```

3. **Reload Cursor**: `Cmd/Ctrl+Shift+P` → "Developer: Reload Window"

4. **Verify connection**: In the AI chat, ask "show me the features in this project" - Cursor should use the MCP tool.

---

### Other MCP Clients

**VS Code (with MCP extension)**:

```json
{
  "mcp.servers": [
    {
      "name": "spec-kitty",
      "command": "spec-kitty",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "PROJECT_PATH": "/absolute/path/to/your/project"
      }
    }
  ]
}
```

**MCP Inspector (Testing Tool)**:

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Connect to Spec Kitty MCP server
mcp-inspector spec-kitty mcp start --transport stdio
```

---

## Step 4: Start Using Conversational Commands

Once your MCP client is configured, you can interact with Spec Kitty using natural language instead of slash commands!

### Example 1: Create a Feature Specification

**Old way (slash command)**:
```
/spec-kitty.specify
[Answer discovery interview questions]
```

**New way (conversational)**:
```
I want to build a user authentication system with email/password login and JWT tokens
```

**What happens**:
- MCP server receives your description
- Conducts discovery interview (asks clarifying questions)
- Generates `kitty-specs/###-user-authentication/spec.md`
- Returns the generated specification

---

### Example 2: Create a Technical Plan

**Old way**:
```
/spec-kitty.plan for feature 020
```

**New way**:
```
Create a technical plan for the user authentication feature
```

**What happens**:
- MCP server identifies the feature from context
- Generates `plan.md` with technical approach
- Proposes work package breakdown
- Returns the plan for review

---

### Example 3: Manage Tasks

**Old way**:
```
spec-kitty agent tasks move-task WP01 --to doing --note "Starting work"
```

**New way**:
```
I'm starting work on WP01
```

**What happens**:
- MCP server moves WP01 to "doing" lane
- Updates activity log with timestamp
- Returns confirmation and current status

---

### Example 4: Create a Worktree

**Old way**:
```
spec-kitty implement WP01
```

**New way**:
```
Start implementing WP01
```

**What happens**:
- MCP server creates `.worktrees/###-feature-WP01/`
- Creates isolated git branch
- Returns worktree path and next steps

---

## Step 5: Verify Everything Works

**Test the MCP server with this conversation flow**:

1. **Create a feature**:
   ```
   Create a new feature for API rate limiting
   ```

2. **List features**:
   ```
   Show me all features in this project
   ```

3. **Check task status**:
   ```
   What tasks are ready to work on?
   ```

4. **Show health status**:
   ```
   Is the MCP server working correctly?
   ```

**Expected behavior**: Each command should trigger the MCP server, execute the corresponding CLI operation, and return structured results.

---

## Server Configuration Options

### Environment Variables

Configure the MCP server behavior using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_HOST` | `127.0.0.1` | Server bind address (SSE only) |
| `MCP_SERVER_PORT` | `8000` | Server port (SSE only) |
| `MCP_AUTH_ENABLED` | `false` | Enable API key authentication |
| `MCP_API_KEY` | `""` | API key for authentication (if enabled) |
| `PROJECT_PATH` | (required) | Absolute path to your Spec Kitty project |

**Example with authentication**:

```json
{
  "mcpServers": {
    "spec-kitty": {
      "command": "spec-kitty",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "PROJECT_PATH": "/path/to/project",
        "MCP_AUTH_ENABLED": "true",
        "MCP_API_KEY": "your-secure-api-key-here"
      }
    }
  }
}
```

---

## Authentication Configuration

### When to Enable Authentication

**Enable authentication** (`MCP_AUTH_ENABLED=true`) if:
- Multiple users access the MCP server
- Server is network-accessible (SSE transport)
- Project contains sensitive data

**Disable authentication** (default) if:
- Single-user local development
- Trusted local environment
- Using stdio transport (stdin/stdout only)

### Generating a Secure API Key

```bash
# Option 1: Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 2: OpenSSL
openssl rand -base64 32

# Option 3: /dev/urandom (Linux/macOS)
head -c 32 /dev/urandom | base64
```

**Minimum requirements**:
- 32+ characters
- High entropy (random generation)
- Stored securely (environment variable, secrets manager)

---

## Troubleshooting

### Issue: "No such command 'mcp'"

**Cause**: Spec Kitty version < 0.14.0

**Solution**:
```bash
pip install --upgrade spec-kitty-cli
spec-kitty --version  # Should show 0.14.0+
```

---

### Issue: "Port 8000 already in use"

**Cause**: Another service is using port 8000 (SSE transport only)

**Solution**:
```bash
# Option 1: Use a different port
spec-kitty mcp start --transport sse --port 8001

# Option 2: Switch to stdio transport (recommended)
spec-kitty mcp start --transport stdio
```

---

### Issue: "API key authentication enabled but no API key provided"

**Cause**: `MCP_AUTH_ENABLED=true` but `MCP_API_KEY` is not set

**Solution**:
```bash
# Generate and set API key
export MCP_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
spec-kitty mcp start --transport stdio
```

---

### Issue: "Invalid project path: /path/to/project"

**Cause**: Project path does not contain `.kittify/` directory

**Solution**:
```bash
# Initialize Spec Kitty in the project
cd /path/to/project
spec-kitty init --ai claude

# Verify .kittify/ directory exists
ls -la .kittify/
```

---

### Issue: MCP client can't connect to server

**Debugging steps**:

1. **Test server manually**:
   ```bash
   cd /path/to/your/project
   spec-kitty mcp start --transport stdio
   # Should output: "MCP server started successfully"
   ```

2. **Check client logs**:
   - **Claude Desktop**: `~/Library/Logs/Claude/` (macOS)
   - **Cursor**: Help → Toggle Developer Tools → Console tab
   - Look for MCP connection errors

3. **Verify project path**:
   ```bash
   # In your client config, ensure PROJECT_PATH is absolute:
   "PROJECT_PATH": "/Users/you/projects/my-app"  # ✅ Correct
   "PROJECT_PATH": "~/projects/my-app"           # ❌ Wrong (not expanded)
   "PROJECT_PATH": "../my-app"                    # ❌ Wrong (relative)
   ```

4. **Check file permissions**:
   ```bash
   ls -la /path/to/project/.kittify/
   # Should be readable/writable by your user
   ```

---

### Issue: "Lock timeout: Resource locked by another process"

**Cause**: Another MCP client is modifying the same resource

**Solution**:
- Wait for the other operation to complete (default timeout: 5 minutes)
- If stale lock (orphaned process), kill the process:
  ```bash
  # Find PID from lock file
  cat .kittify/.lock-WP01
  # Kill the process
  kill <PID>
  ```

---

### Issue: Conversational commands not working

**Debugging steps**:

1. **Verify MCP tools are registered**:
   ```bash
   # In MCP Inspector or client console:
   # Should show: feature_operations, task_operations, workspace_operations, system_operations
   ```

2. **Test with explicit tool name**:
   ```
   Use the feature_operations tool to list all features
   ```

3. **Check server logs**:
   - MCP server logs tool invocations to stdout
   - Look for "Error:" messages

4. **Validate project structure**:
   ```bash
   ls -la .kittify/
   # Should contain: config.yaml, active-mission, mcp-sessions/
   ```

---

## Example Conversational Workflows

### Workflow 1: Complete Feature from Scratch

```
User: Create a new feature for user profile management with avatar upload

[MCP conducts discovery interview]

User: Plan the implementation for this feature

[MCP generates plan.md with work packages]

User: Create tasks for this feature

[MCP generates tasks/ directory with work package files]

User: Start implementing WP01

[MCP creates worktree and branches]

User: Move WP01 to review

[MCP updates task lane, adds activity log entry]
```

---

### Workflow 2: Multi-Project Management

```
User: Show me all features in /Users/you/projects/app1

[MCP lists features from app1]

User: Now show features in /Users/you/projects/app2

[MCP switches context, lists features from app2]

User: In app1, what tasks are in the doing lane?

[MCP returns to app1 context, lists doing tasks]
```

---

### Workflow 3: Parallel Development

```
User: Which work packages can I start working on?

[MCP analyzes dependencies, returns WPs with no blockers]

User: Start implementing WP02, WP03, and WP04 in parallel

[MCP creates 3 worktrees with appropriate base branches]

User: Show me the status of all work packages

[MCP returns kanban board with current lanes]
```

---

## Next Steps

**You're ready to use Spec Kitty conversationally!** 🎉

**Explore more**:
- [MCP Server Architecture](../explanation/mcp-server-architecture.md) - How the MCP server works internally
- [MCP Tool Reference](../reference/mcp-tools.md) - Complete list of available tools and parameters
- [Conversational Workflows](../how-to/mcp-conversational-workflows.md) - Advanced patterns and best practices
- [MCP Server Configuration](../reference/mcp-server-configuration.md) - Advanced configuration options

**Troubleshooting**:
- [Common MCP Issues](../how-to/troubleshoot-mcp.md) - Solutions to frequent problems
- [MCP Client Setup](../reference/mcp-clients.md) - Detailed setup for each client type

**Get help**:
- [GitHub Issues](https://github.com/Priivacy-ai/spec-kitty/issues) - Report bugs or request features
- [Discussions](https://github.com/Priivacy-ai/spec-kitty/discussions) - Ask questions and share tips

---

*Last updated: 2026-01-31*  
*Spec Kitty version: 0.14.0+*
