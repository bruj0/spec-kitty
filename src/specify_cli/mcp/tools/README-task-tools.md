## Task Operations MCP Tools (WP06)

Provides MCP tools for managing Spec Kitty work package tasks through conversational AI interfaces.

### Operations

#### 1. `list_tasks`
Lists all work packages for a feature, optionally filtered by lane.

**Parameters:**
- `project_path` (required): Absolute path to Spec Kitty project root
- `feature_slug` (required): Feature identifier (e.g., "099-mcp-server-for-conversational-spec-kitty-workflow")
- `lane` (optional): Filter by lane ("planned", "doing", "for_review", "done")

**Returns:**
```json
{
  "success": true,
  "message": "Found 10 tasks for 099-mcp-server",
  "data": {
    "feature_slug": "099-mcp-server-for-conversational-spec-kitty-workflow",
    "tasks": [
      {
        "work_package_id": "WP01",
        "title": "Core MCP Server Foundation",
        "lane": "done",
        "path": "/path/to/tasks/WP01-core-mcp-server-foundation.md"
      },
      ...
    ],
    "lane_filter": "done"
  }
}
```

#### 2. `move_task`
Moves a work package between lanes with pessimistic locking.

**Parameters:**
- `project_path` (required): Absolute path to Spec Kitty project root
- `feature_slug` (required): Feature identifier
- `task_id` (required): Work package ID (e.g., "WP01")
- `lane` (required): Target lane ("planned", "doing", "for_review", "done")
- `note` (optional): Activity log note

**Locking:**
- Acquires lock on work package before modification
- Timeout: 5 minutes (300 seconds)
- Auto-cleanup of stale locks
- Returns error if lock held by another client

**Returns:**
```json
{
  "success": true,
  "message": "Task WP01 moved to doing",
  "data": {
    "feature_slug": "099-mcp-server-for-conversational-spec-kitty-workflow",
    "task_id": "WP01",
    "old_lane": "planned",
    "new_lane": "doing",
    "note": "Starting implementation"
  }
}
```

#### 3. `add_history`
Adds activity log entry to a work package.

**Parameters:**
- `project_path` (required): Absolute path to Spec Kitty project root
- `feature_slug` (required): Feature identifier
- `task_id` (required): Work package ID
- `note` (required): Activity log message

**Locking:**
- Acquires lock before modifying history
- Timeout: 5 minutes

**Returns:**
```json
{
  "success": true,
  "message": "History added to WP01",
  "data": {
    "feature_slug": "099-mcp-server-for-conversational-spec-kitty-workflow",
    "task_id": "WP01",
    "note": "Completed subtask T001"
  }
}
```

#### 4. `query_status`
Retrieves task status including lane, dependencies, and completion state.

**Parameters:**
- `project_path` (required): Absolute path to Spec Kitty project root
- `feature_slug` (required): Feature identifier
- `task_id` (required): Work package ID

**Returns:**
```json
{
  "success": true,
  "message": "Retrieved status for WP01",
  "data": {
    "task_id": "WP01",
    "title": "Core MCP Server Foundation",
    "lane": "doing",
    "dependencies": [],
    "subtasks": ["T001", "T002", "T003"],
    "assignee": "claude",
    "agent": "cursor",
    "review_status": "",
    "is_done": false,
    "has_dependencies": false,
    "history_count": 3,
    "path": "/path/to/tasks/WP01-core-mcp-server-foundation.md"
  }
}
```

### Error Handling

All operations return structured errors:

```json
{
  "success": false,
  "message": "Failed to move task: resource locked",
  "data": null,
  "errors": [
    "Lock timeout: WP01 is currently being modified by another client",
    "Retry in a moment or increase timeout (current: 300s)"
  ]
}
```

### Concurrency Control

The `move_task` and `add_history` operations use pessimistic file-level locking (via `ResourceLock` from WP03) to prevent concurrent modifications:

- Lock files: `.kittify/.locks/.lock-WP-{task_id}`
- Timeout: 300 seconds (5 minutes)
- Auto-cleanup: Stale locks (older than 2x timeout) are automatically removed
- Context manager: Lock released automatically after operation completes

Example locking flow:
```python
lock = ResourceLock.for_work_package(lock_dir, task_id, timeout_seconds=300)

try:
    with lock.acquire():
        # Perform operation with exclusive access
        result = cli_adapter.move_task(...)
except LockTimeout:
    # Return error to client
    return OperationResult.error_result(...)
```

### Integration with CLI Adapter (WP04)

All operations delegate to `CLIAdapter` methods:
- `list_tasks()` → reads WP files from `kitty-specs/{feature}/tasks/`
- `move_task()` → updates frontmatter lane and history
- `add_history()` → appends entry to frontmatter history
- Query status reads frontmatter directly (no CLIAdapter method)

### Registration with MCP Server

```python
from specify_cli.mcp.tools.task_tools import register_task_operations_tool

# During server initialization
register_task_operations_tool(mcp_server)
```

This registers a single MCP tool `task_operations` with operation routing based on the `operation` parameter.

### JSON Schema

The tool parameters are validated against the JSON Schema defined in `TASK_OPERATIONS_SCHEMA`:

```python
{
  "type": "object",
  "required": ["project_path", "operation"],
  "properties": {
    "project_path": {"type": "string"},
    "operation": {
      "type": "string",
      "enum": ["list_tasks", "move_task", "add_history", "query_status"]
    },
    "feature_slug": {"type": "string"},
    "task_id": {"type": "string"},
    "lane": {
      "type": "string",
      "enum": ["planned", "doing", "for_review", "done"]
    },
    "note": {"type": "string"}
  }
}
```

### Testing

- **Unit tests**: `tests/mcp/test_task_tools.py` - Tests each operation in isolation
- **Integration tests**: `tests/mcp/test_task_tools_integration.py` - Tests complete workflows

Run tests:
```bash
pytest tests/mcp/test_task_tools*.py -v
```

### Dependencies

- **WP03**: `ResourceLock` for pessimistic locking
- **WP04**: `CLIAdapter` for CLI integration
- **WP02**: `ProjectContext` for project validation

### Implementation Notes

1. All operations validate `project_path` by creating `ProjectContext`
2. Locking is only used for write operations (`move_task`, `add_history`)
3. Read operations (`list_tasks`, `query_status`) do not acquire locks
4. Activity log entries include agent="mcp-adapter" to track MCP-initiated changes
5. Task files remain in flat `tasks/` directory - lane is tracked in frontmatter only
