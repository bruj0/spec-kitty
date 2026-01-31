# Troubleshooting MCP Server Issues

**Solutions to common MCP server problems**

This guide covers frequent issues when using the Spec Kitty MCP server, organized by symptom and solution.

---

## Installation & Setup Issues

### "No such command 'mcp'"

**Symptom**: Running `spec-kitty mcp start` returns "No such command 'mcp'"

**Cause**: Spec Kitty version < 0.14.0 (MCP server added in 0.14.0)

**Solution**:
```bash
# Check current version
spec-kitty --version

# Upgrade to latest version
pip install --upgrade spec-kitty-cli

# Verify MCP command exists
spec-kitty mcp --help
```

**Expected output**:
```
Usage: spec-kitty mcp [OPTIONS] COMMAND [ARGS]...

  MCP server management commands.

Commands:
  start   Start the MCP server
  status  Check MCP server status
  stop    Stop the MCP server
```

---

### "Module 'fastmcp' not found"

**Symptom**: Server fails to start with `ModuleNotFoundError: No module named 'fastmcp'`

**Cause**: Dependencies not installed or using older spec-kitty version

**Solution**:
```bash
# Reinstall with all dependencies
pip install --upgrade --force-reinstall spec-kitty-cli

# Verify fastmcp installed
pip show fastmcp

# Expected: fastmcp>=1.0.0,<2.0.0
```

---

### "Invalid project path: /path/to/project"

**Symptom**: MCP server rejects project path with validation error

**Cause**: Project directory missing `.kittify/` (not initialized)

**Solution**:
```bash
# Navigate to your project
cd /path/to/project

# Initialize Spec Kitty
spec-kitty init --ai claude

# Verify .kittify/ exists
ls -la .kittify/
# Should contain: config.yaml, active-mission, meta.json

# Now start MCP server
spec-kitty mcp start --transport stdio
```

---

## Connection Issues

### MCP Client Can't Connect to Server

**Symptom**: MCP client shows "connection failed" or "server not responding"

**Debugging steps**:

1. **Test server manually**:
   ```bash
   cd /path/to/your/project
   spec-kitty mcp start --transport stdio
   ```
   
   Expected output:
   ```
   MCP server started successfully
   Transport: stdio
   Authentication: disabled
   ```

2. **Check client configuration**:
   - Ensure `PROJECT_PATH` is **absolute** (not relative or `~` expanded)
   - Verify command path: `which spec-kitty` (should be in PATH)
   - Check environment variables are set correctly

3. **Review client logs**:
   - **Claude Desktop**: `~/Library/Logs/Claude/mcp.log`
   - **Cursor**: Help → Toggle Developer Tools → Console tab
   - **VS Code**: Output panel → MCP extension

4. **Common config mistakes**:

   ```json
   ❌ WRONG:
   {
     "command": "spec-kitty",
     "args": ["mcp", "start"],  // Missing --transport flag
     "env": {
       "PROJECT_PATH": "~/projects/app"  // Relative path, not expanded
     }
   }

   ✅ CORRECT:
   {
     "command": "spec-kitty",
     "args": ["mcp", "start", "--transport", "stdio"],
     "env": {
       "PROJECT_PATH": "/Users/you/projects/app"  // Absolute path
     }
   }
   ```

---

### "Connection reset by peer" (SSE Transport)

**Symptom**: Server starts but client connection immediately drops

**Cause**: Port already in use or firewall blocking connection

**Solution**:
```bash
# Check if port is in use
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Option 1: Use different port
spec-kitty mcp start --transport sse --port 8001

# Option 2: Switch to stdio (recommended for local dev)
spec-kitty mcp start --transport stdio

# Option 3: Stop conflicting service
kill <PID>  # From lsof/netstat output
```

---

## Authentication Issues

### "API key authentication enabled but no API key provided"

**Symptom**: Server fails to start with authentication error

**Cause**: `MCP_AUTH_ENABLED=true` but `MCP_API_KEY` not set

**Solution**:
```bash
# Generate secure API key
export MCP_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Or set in client config:
{
  "env": {
    "MCP_AUTH_ENABLED": "true",
    "MCP_API_KEY": "your-secure-key-here"
  }
}

# Start server
spec-kitty mcp start --transport stdio
```

---

### "Unauthorized: Invalid API key"

**Symptom**: MCP client connects but all tool calls fail with 401 error

**Cause**: API key mismatch between server and client

**Solution**:
1. **Verify server API key**:
   ```bash
   echo $MCP_API_KEY
   ```

2. **Verify client API key** in config matches server:
   ```json
   {
     "env": {
       "MCP_API_KEY": "exact-same-key-as-server"
     }
   }
   ```

3. **Restart both**:
   ```bash
   spec-kitty mcp stop
   spec-kitty mcp start --transport stdio
   # Then restart MCP client (Claude Desktop, Cursor, etc.)
   ```

---

## Runtime Issues

### "Lock timeout: Resource locked by another process"

**Symptom**: Operations fail with lock timeout error (default: 5 minutes)

**Cause**: Another MCP client or process is modifying the same resource

**Diagnosis**:
```bash
# Check for lock files
ls -la .kittify/.lock-*

# View lock details
cat .kittify/.lock-WP01
# Shows: {"pid": 12345, "created_at": "2026-01-31T10:00:00Z"}
```

**Solutions**:

1. **Wait for operation to complete** (if legitimate concurrent access)

2. **Kill stale process** (if orphaned):
   ```bash
   # Check if process still exists
   ps aux | grep <PID>

   # If not found, remove lock file manually
   rm .kittify/.lock-WP01

   # If found, kill it (be careful!)
   kill <PID>
   ```

3. **Restart MCP server** (cleans up stale locks):
   ```bash
   spec-kitty mcp stop
   spec-kitty mcp start --transport stdio
   ```

---

### "Session state corrupted: Invalid JSON"

**Symptom**: MCP server fails to load conversation state

**Cause**: Interrupted write operation or manual file edit

**Solution**:
```bash
# Locate corrupted session file
ls -la .kittify/mcp-sessions/

# Backup and remove corrupted file
mv .kittify/mcp-sessions/<session-id>.json{,.backup}

# Or validate JSON manually
cat .kittify/mcp-sessions/<session-id>.json | python -m json.tool

# Restart server (creates new session)
spec-kitty mcp start --transport stdio
```

---

### "Git worktree creation failed"

**Symptom**: `create_worktree` operation fails with git error

**Cause**: Dirty working directory or missing base branch

**Solutions**:

1. **Check working directory status**:
   ```bash
   git status
   # Commit or stash uncommitted changes
   git stash
   ```

2. **Verify base branch exists**:
   ```bash
   git branch -a
   # If base WP branch missing, implement dependency first:
   spec-kitty implement WP01  # Then WP02 --base WP01
   ```

3. **Check git permissions**:
   ```bash
   ls -la .git/
   # Should be writable by your user
   ```

---

## Performance Issues

### "Server startup takes >10 seconds"

**Symptom**: MCP server slow to start

**Cause**: Large project with many features/tasks

**Solutions**:

1. **Profile startup**:
   ```bash
   time spec-kitty mcp start --transport stdio
   ```

2. **Check project size**:
   ```bash
   du -sh kitty-specs/
   find kitty-specs/ -name '*.md' | wc -l
   ```

3. **Optimize** (if >100 features):
   - Archive completed features: Move to `kitty-specs/archive/`
   - Clean up old worktrees: `spec-kitty worktree clean`
   - Reduce log verbosity: `MCP_LOG_LEVEL=ERROR`

---

### "Tool invocation timeout"

**Symptom**: MCP operations time out (>30 seconds)

**Cause**: Large file operations or git conflicts

**Solutions**:

1. **Increase timeout in client config**:
   ```json
   {
     "timeout": 60000  // 60 seconds (milliseconds)
   }
   ```

2. **Check for large files**:
   ```bash
   find . -type f -size +10M
   # Add to .gitignore if not needed
   ```

3. **Resolve git conflicts**:
   ```bash
   git status
   # Resolve any pending merges or conflicts
   ```

---

## Error Messages

### "OperationResult.success=False"

**Symptom**: MCP tool returns success=False with error message

**Diagnosis**: Check `errors` field in result:
```json
{
  "success": false,
  "message": "Failed to create feature",
  "errors": ["Feature slug already exists: 020-my-feature"],
  "data": null
}
```

**Solutions** (depends on specific error):

- **"Feature slug already exists"**: Choose different feature name
- **"Work package not found"**: Verify WP ID in `kitty-specs/*/tasks/`
- **"Invalid lane transition"**: Check task workflow (planned → doing → for_review → done)
- **"Dependency not satisfied"**: Implement base WP first

---

### "FastMCP protocol error"

**Symptom**: MCP client shows "invalid message format" or "protocol violation"

**Cause**: FastMCP version incompatibility

**Solution**:
```bash
# Check FastMCP version
pip show fastmcp

# Upgrade to compatible version
pip install --upgrade 'fastmcp>=1.0.0,<2.0.0'

# Restart server
spec-kitty mcp stop && spec-kitty mcp start --transport stdio
```

---

## Debugging Tips

### Enable Verbose Logging

**Server-side logging**:
```bash
# Set log level
export MCP_LOG_LEVEL=DEBUG

# Start server with verbose output
spec-kitty mcp start --transport stdio --verbose
```

**Client-side logging**:
- **Claude Desktop**: Logs to `~/Library/Logs/Claude/`
- **Cursor**: Help → Toggle Developer Tools → Console
- **VS Code**: Output panel → MCP Server (select from dropdown)

---

### Test with MCP Inspector

**Install MCP Inspector**:
```bash
npm install -g @modelcontextprotocol/inspector
```

**Connect to Spec Kitty**:
```bash
mcp-inspector spec-kitty mcp start --transport stdio
```

**Benefits**:
- See raw MCP protocol messages (JSON-RPC)
- Test tool invocations manually
- Inspect tool schemas and parameters
- Debug without relying on AI client interpretation

---

### Check Health Status

**Use system_operations tool**:
```bash
# In MCP client (Claude, Cursor, etc.):
"Check the health of the MCP server"
```

**Returns**:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "active_projects": 2,
  "active_sessions": 1,
  "version": "0.14.0"
}
```

---

## Platform-Specific Issues

### macOS: "Operation not permitted"

**Symptom**: File operations fail with permission error

**Cause**: macOS Gatekeeper or SIP restrictions

**Solution**:
```bash
# Grant Terminal/Cursor/Claude full disk access:
System Preferences → Security & Privacy → Privacy → Full Disk Access
→ Add Terminal.app (or Cursor.app, Claude.app)

# Or run with elevated permissions (not recommended):
sudo spec-kitty mcp start
```

---

### Windows: "FileNotFoundError: [WinError 2]"

**Symptom**: Server can't find `spec-kitty` command

**Cause**: Python Scripts directory not in PATH

**Solution**:
```powershell
# Add Python Scripts to PATH
$env:Path += ";$env:LOCALAPPDATA\Programs\Python\Python311\Scripts"

# Or reinstall with --user flag
pip install --user spec-kitty-cli

# Verify
where.exe spec-kitty
```

---

### Linux: "Address already in use"

**Symptom**: SSE server fails to bind to port

**Cause**: Port in use by another service

**Solution**:
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>

# Or use different port
spec-kitty mcp start --transport sse --port 8001

# Or switch to stdio (recommended)
spec-kitty mcp start --transport stdio
```

---

## Getting More Help

**Still stuck?**

1. **Check GitHub Issues**: [spec-kitty/issues](https://github.com/Priivacy-ai/spec-kitty/issues)
   - Search for similar problems
   - Report new bugs with detailed logs

2. **GitHub Discussions**: [spec-kitty/discussions](https://github.com/Priivacy-ai/spec-kitty/discussions)
   - Ask questions
   - Share workarounds

3. **Include diagnostic info**:
   ```bash
   # Gather diagnostic info
   spec-kitty --version
   python --version
   pip show fastmcp filelock
   uname -a  # OS info
   
   # Attach MCP server logs (redact sensitive data!)
   ```

---

*Last updated: 2026-01-31*  
*Spec Kitty version: 0.14.0+*
