# System Operations MCP Tools

This document describes the system-level MCP tools for Spec Kitty, implemented in WP08.

## Overview

System operations provide health checks, project validation, mission listing, and server configuration tools for MCP clients. These tools enable clients to:

- Monitor server health and uptime
- Validate project structure before starting operations
- Discover available Spec Kitty missions
- Query server configuration (with sensitive values redacted)

## Tool: `system_operations`

### Operations

#### 1. `health_check`

Returns server status, uptime, and active projects count.

**Parameters**: None required

**Returns**:
```json
{
  "success": true,
  "message": "Server is healthy",
  "data": {
    "status": "healthy",
    "uptime_seconds": 3600,
    "active_projects": 2,
    "timestamp": "2026-01-31T15:00:00+00:00"
  }
}
```

**Use Case**: Monitor server availability, check how long server has been running, track number of active projects.

---

#### 2. `validate_project`

Validates project structure and checks for required files.

**Parameters**:
- `project_path` (required): Absolute path to project root directory

**Returns** (success):
```json
{
  "success": true,
  "message": "Project structure is valid",
  "data": {
    "project_path": "/Users/me/my-project",
    "is_valid": true,
    "checks": {
      "kittify_directory": true,
      "config_file": true,
      "specs_directory": true,
      "workspace_context_directory": true
    },
    "warnings": []
  }
}
```

**Returns** (failure):
```json
{
  "success": false,
  "message": "Not a valid Spec Kitty project (missing .kittify/ directory)",
  "errors": [
    "Missing .kittify/ directory",
    "Run 'spec-kitty init' in /path/to/project to initialize"
  ]
}
```

**Use Case**: Verify project initialization before executing operations, provide actionable error messages for setup issues.

**Validation Rules**:
- Project path must exist
- `.kittify/` directory must exist (REQUIRED)
- `config.yaml` is optional (warns if missing)
- `kitty-specs/` directory is optional (warns if missing)
- `.kittify/workspaces/` directory is optional (warns if missing)

---

#### 3. `list_missions`

Lists all available Spec Kitty missions from the package.

**Parameters**: None required

**Returns**:
```json
{
  "success": true,
  "message": "Found 3 available missions",
  "data": {
    "missions": [
      {
        "name": "software-dev",
        "display_name": "Software Dev Kitty",
        "description": "Build high-quality software with structured workflows",
        "domain": "software",
        "version": "1.0.0"
      },
      {
        "name": "research",
        "display_name": "Research Kitty",
        "description": "Conduct structured research with deliverables",
        "domain": "research",
        "version": "1.0.0"
      },
      {
        "name": "documentation",
        "display_name": "Documentation Kitty",
        "description": "Create comprehensive documentation following Divio",
        "domain": "documentation",
        "version": "1.0.0"
      }
    ]
  }
}
```

**Use Case**: Discover available missions for feature creation, show mission options during discovery interview.

---

#### 4. `server_config`

Returns server configuration with sensitive values redacted.

**Parameters**: None required

**Returns**:
```json
{
  "success": true,
  "message": "Server configuration retrieved",
  "data": {
    "config": {
      "host": "127.0.0.1",
      "port": 8000,
      "transport": "stdio",
      "auth_enabled": false,
      "api_key": "***REDACTED***"
    }
  }
}
```

**Use Case**: Debug server configuration, verify transport settings, check authentication status.

**Security Note**: API keys are always redacted in responses to prevent leakage.

---

## Implementation Details

### Architecture

System tools follow the MCP adapter pattern:

1. **Operation Functions**: Individual functions for each operation (e.g., `health_check_operation`)
2. **Handler Router**: `system_operations_handler` routes requests to appropriate operation
3. **Result Standardization**: All operations return `OperationResult` dataclass
4. **Server Registration**: Tool registered with FastMCP in `MCPServer._register_tools()`

### Dependencies

- `specify_cli.core.project_state.ProjectPaths`: Project path validation
- `specify_cli.mission`: Mission discovery (reads from `src/specify_cli/missions/`)
- `pathlib`: Cross-platform path handling
- `datetime`: Timestamp generation
- `time`: Uptime calculation

### Error Handling

All operations return structured errors:

```python
OperationResult(
    success=False,
    message="Human-readable error message",
    errors=["Detailed error 1", "Detailed error 2"]
)
```

This enables MCP clients to:
- Display user-friendly error messages
- Parse structured error details programmatically
- Provide actionable next steps

### Testing

Comprehensive tests in `tests/mcp/test_system_tools.py` cover:

- Health check with and without server instance
- Project validation (valid/invalid/missing components)
- Mission listing
- Server config with and without API key redaction
- Handler routing for all operations
- JSON Schema validation

---

## Usage Examples

### MCP Client (Python)

```python
from mcp import Client

client = Client("spec-kitty-mcp")

# Health check
result = client.call_tool("system_operations", {
    "operation": "health_check"
})
print(f"Server status: {result['data']['status']}")

# Validate project
result = client.call_tool("system_operations", {
    "operation": "validate_project",
    "project_path": "/path/to/project"
})
if not result["success"]:
    for error in result["errors"]:
        print(f"Error: {error}")

# List missions
result = client.call_tool("system_operations", {
    "operation": "list_missions"
})
for mission in result["data"]["missions"]:
    print(f"- {mission['name']}: {mission['description']}")
```

### Natural Language (via MCP Agent)

```
User: Is the server running?
Agent: [calls system_operations with operation=health_check]
       Server is healthy, running for 1 hour with 2 active projects.

User: Can I start working on /path/to/my-project?
Agent: [calls system_operations with operation=validate_project, project_path=/path/to/my-project]
       ✓ Project structure is valid. Ready to start!

User: What missions are available?
Agent: [calls system_operations with operation=list_missions]
       Available missions:
       - Software Dev Kitty: Build software with TDD
       - Research Kitty: Conduct structured research
       - Documentation Kitty: Create Divio-style docs
```

---

## Performance

- **health_check**: <10ms (simple in-memory data)
- **validate_project**: <100ms (file system checks only)
- **list_missions**: <200ms (reads YAML files from disk)
- **server_config**: <10ms (simple in-memory data)

All operations are synchronous and complete within acceptable MCP latency bounds (<500ms target).

---

## Security Considerations

1. **API Key Redaction**: `server_config` always redacts API keys using `***REDACTED***` placeholder
2. **Path Validation**: `validate_project` resolves paths to prevent directory traversal attacks
3. **No Shell Commands**: All operations use Python libraries (no subprocess calls)
4. **Read-Only**: System operations are read-only (no state modifications)

---

## Future Enhancements (Not in WP08)

- **health_check**: Add memory usage, CPU usage, and connection count metrics
- **validate_project**: Run custom validators (e.g., check git status, verify dependencies)
- **list_missions**: Filter missions by domain or include project-specific missions
- **server_config**: Return transport-specific configuration (SSE endpoint URL, etc.)

---

## Related Work Packages

- **WP01**: Core MCP server foundation (FastMCP, tool registration)
- **WP02**: Project context and state management (used by validate_project)
- **WP04**: CLI adapter layer (pattern followed by system_operations)
- **WP10**: Integration tests (end-to-end system_operations testing)
