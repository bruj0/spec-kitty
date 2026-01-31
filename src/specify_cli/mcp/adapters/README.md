# CLI Adapter Layer

The CLI adapter layer provides a consistent interface for MCP tools to invoke existing CLI functionality without duplicating business logic.

## Architecture

```
MCP Tools → CLIAdapter → Existing CLI/Core Modules → OperationResult
```

### Key Design Principles

1. **No Business Logic Duplication**: The adapter wraps existing functionality, never reimplements it
2. **Direct Python Imports**: Uses Python imports, NOT subprocess calls
3. **Standardized Results**: All operations return `OperationResult` with success/error status
4. **Comprehensive Error Handling**: All exceptions caught and converted to structured errors

## Components

### OperationResult

Standardized result format for all operations:

```python
@dataclass
class OperationResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    artifacts: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
```

**Factory methods:**
- `OperationResult.success_result(message, data, artifacts)` - Create success result
- `OperationResult.error_result(message, errors)` - Create error result

**Serialization:**
- `to_dict()` - Convert to dictionary for MCP responses (paths converted to strings)

### CLIAdapter

Main adapter class that wraps CLI operations:

```python
class CLIAdapter:
    def __init__(self, project_context: ProjectContext):
        """Initialize adapter with project context."""
        self.project_context = project_context
        self.project_path = project_context.project_path
        self.kittify_dir = project_context.kittify_dir
```

## Operations

### Feature Operations

**create_feature(slug, description)** - Create new feature specification
- Creates feature directory structure
- Uses `get_next_feature_number()` from core
- Returns: Feature path and metadata

**setup_plan(feature_slug)** - Generate technical plan
- Creates `plan.md` file
- Returns: Plan file path

**create_tasks(feature_slug)** - Generate work package breakdown
- Creates `tasks.md` and tasks directory
- Returns: Tasks directory path

### Task Operations

**list_tasks(feature_slug, lane=None)** - List tasks for feature
- Reads WP files from `tasks/` directory
- Parses YAML frontmatter
- Optional lane filtering
- Returns: List of task metadata

**move_task(feature_slug, task_id, lane, note=None)** - Move task between lanes
- Updates frontmatter `lane:` field
- Appends history entry
- Returns: Old/new lane info

**add_history(feature_slug, task_id, note)** - Add history entry to task
- Appends to frontmatter `history:` array
- Timestamps automatically added
- Returns: Confirmation

**mark_subtask_status(feature_slug, task_id, subtask_ids, status)** - Mark subtask status
- *Note: Placeholder implementation*
- Future: Update subtask status in frontmatter

### Workspace Operations

**create_worktree(feature_slug, wp_id, base_wp=None)** - Create git worktree
- Creates git worktree for work package
- Optional base WP for dependencies
- Returns: Worktree path

**list_worktrees()** - List all active worktrees
- Scans `.worktrees/` directory
- Returns: List of worktree metadata

### System Operations

**validate_project()** - Validate project structure
- Checks for required directories
- Returns: Validation status

**get_missions()** - List available missions
- Scans `.kittify/missions/` directory
- Returns: List of mission names

## Error Handling

All operations use the `@handle_cli_errors` decorator:

```python
@handle_cli_errors
def some_operation(self, ...):
    # Implementation
    pass
```

This decorator:
- Catches all exceptions
- Logs full traceback for debugging
- Returns `OperationResult.error_result()` with structured errors
- Prevents crashes in MCP server

## Usage Example

```python
from specify_cli.mcp.session.context import ProjectContext
from specify_cli.mcp.adapters import CLIAdapter

# Initialize adapter
context = ProjectContext.from_path(Path("/path/to/project"))
adapter = CLIAdapter(context)

# Create feature
result = adapter.create_feature("user-auth", "Implement user authentication")
if result.success:
    print(f"Feature created: {result.data['feature_slug']}")
else:
    print(f"Error: {result.message}")
    for error in result.errors:
        print(f"  - {error}")

# List tasks
result = adapter.list_tasks("001-user-auth", lane="doing")
for task in result.data["tasks"]:
    print(f"{task['work_package_id']}: {task['title']}")
```

## Testing

### Contract Tests

Tests verify adapter delegates to existing CLI code:

```python
def test_create_feature_uses_core_functions(adapter, tmp_path):
    """Verify adapter uses core worktree functions."""
    result = adapter.create_feature("test-feature", "Description")
    
    assert result.success
    # Verify artifacts created on disk
    assert (tmp_path / "kitty-specs" / "001-test-feature").exists()
```

Run contract tests:
```bash
pytest tests/mcp/test_cli_adapter.py -v
```

### Integration Tests

End-to-end tests with real project fixtures:

```bash
pytest tests/mcp/test_cli_adapter_integration.py -v
```

## Architecture Decisions

### AC-001: Wrap Existing CLI Code

The adapter extracts core logic from CLI commands where possible, but some operations (like feature creation) reimplement the essential logic due to CLI structure.

**Future Refactoring:**
- Extract CLI command logic into `src/specify_cli/core/` modules
- Have both CLI commands and adapter use the same core functions
- See: `architecture/adrs/2026-01-XX-cli-core-separation.md` (future)

### AC-002: MCP Independence

The MCP implementation is architecturally independent from CLI:
- MCP tools route through adapter
- Adapter can be used standalone (no MCP dependency)
- CLI commands remain unchanged
- Future: Both MCP and CLI use same core library

## Known Limitations

1. **Worktree creation** - Simplified implementation without full dependency tracking
2. **Subtask status marking** - Placeholder implementation
3. **CLI command extraction** - Some logic still embedded in Typer commands

## Future Work

- [ ] Extract core logic into `src/specify_cli/core/` modules
- [ ] Refactor CLI commands to use extracted core functions
- [ ] Implement full subtask status marking
- [ ] Add comprehensive worktree dependency tracking
- [ ] Add more granular error categorization (validation, not found, permission, etc.)

## See Also

- [data-model.md](../../kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/data-model.md) - Entity definitions
- [plan.md](../../kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/plan.md) - Technical design
- [ProjectContext](../session/README.md) - Session management
