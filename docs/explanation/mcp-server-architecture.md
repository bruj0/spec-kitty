# MCP Server Architecture

**Understanding how the Spec Kitty MCP server works internally**

This document explains the architecture, design decisions, and implementation patterns of the Spec Kitty MCP server. It's intended for contributors, advanced users, and anyone interested in how conversational AI workflows are implemented.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Client Layer                          │
│  (Claude Desktop, Cursor, VS Code, Web Clients)                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │ MCP Protocol (JSON-RPC)
                            │ Transport: stdio or SSE
┌───────────────────────────▼─────────────────────────────────────┐
│                      FastMCP Framework                           │
│  • Protocol handling (JSON-RPC messages)                         │
│  • Tool registration and discovery                              │
│  • Transport abstraction (stdio/SSE/HTTP)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    MCP Tool Router                               │
│  • feature_operations → FeatureToolsHandler                     │
│  • task_operations → TaskToolsHandler                           │
│  • workspace_operations → WorkspaceToolsHandler                 │
│  • system_operations → SystemToolsHandler                       │
└─────────┬──────────────┬──────────────┬─────────────┬──────────┘
          │              │              │             │
          ▼              ▼              ▼             ▼
┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────┐
│  Feature    │  │    Task     │  │ Workspace│  │  System   │
│   Tools     │  │   Tools     │  │  Tools   │  │   Tools   │
└──────┬──────┘  └──────┬──────┘  └─────┬────┘  └─────┬─────┘
       │                │               │             │
       └────────────────┴───────────────┴─────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │   CLI Adapter    │
                   │  (Thin Wrapper)  │
                   └────────┬─────────┘
                            │ Direct Python imports
                            ▼
       ┌────────────────────────────────────────────┐
       │      Existing CLI Modules (Reused)        │
       │  • src/specify_cli/cli/commands/          │
       │  • src/specify_cli/agent_utils/           │
       │  • src/specify_cli/core/                  │
       │  • src/specify_cli/merge/                 │
       └────────────────────────────────────────────┘
                            │
                            ▼
       ┌────────────────────────────────────────────┐
       │         Project State Layer                │
       │  • .kittify/mcp-sessions/ (Conversation)   │
       │  • .kittify/.lock-* (Resource locks)       │
       │  • kitty-specs/ (Features, tasks)          │
       │  • .worktrees/ (Isolated workspaces)       │
       └────────────────────────────────────────────┘
```

---

## Core Principles

### 1. Thin Wrapper Architecture

**Principle**: MCP server does NOT duplicate business logic. It wraps existing CLI code.

**Rationale**:
- Avoid code duplication and drift
- Maintain single source of truth
- CLI improvements automatically benefit MCP interface
- Reduces maintenance burden

**Implementation**:
```python
# ❌ BAD: Duplicating business logic
def create_feature_handler(feature_slug: str):
    # ... 200 lines of feature creation logic ...
    pass

# ✅ GOOD: Wrapping existing CLI code
def create_feature_handler(feature_slug: str):
    from specify_cli.cli.commands import specify
    return specify.create_feature(feature_slug)  # Reuse CLI code
```

---

### 2. Adapter Pattern

**Principle**: CLIAdapter provides consistent interface for MCP tools without modifying CLI code.

**Architecture**:
```python
# CLI modules remain unchanged
from specify_cli.cli.commands import specify

# Adapter wraps CLI and returns standardized OperationResult
class CLIAdapter:
    def create_feature(self, feature_slug: str) -> OperationResult:
        try:
            result = specify.create_feature(feature_slug)
            return OperationResult(
                success=True,
                message="Feature created",
                data={"feature_slug": feature_slug},
                artifacts=[f"kitty-specs/{feature_slug}/spec.md"],
                errors=[]
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message="Failed to create feature",
                data=None,
                artifacts=[],
                errors=[str(e)]
            )
```

**Benefits**:
- CLI exceptions → structured errors
- Consistent return format (OperationResult)
- MCP-specific metadata (artifacts, structured data)
- Graceful degradation (never crash server)

---

### 3. Session State Persistence

**Principle**: Conversation state stored in project-local `.kittify/mcp-sessions/`.

**State Schema**:
```json
{
  "session_id": "uuid-1234-5678",
  "project_path": "/path/to/project",
  "created_at": "2026-01-31T10:00:00Z",
  "updated_at": "2026-01-31T10:15:00Z",
  "conversation_history": [
    {
      "turn": 1,
      "user_message": "Create a feature for billing",
      "tool_invocation": "feature_operations",
      "operation": "specify",
      "result": { "success": true, "feature_slug": "021-billing" }
    },
    {
      "turn": 2,
      "user_message": "Create a plan for it",
      "tool_invocation": "feature_operations",
      "operation": "plan",
      "context": { "feature_slug": "021-billing" }
    }
  ],
  "discovery_interview": {
    "feature_slug": "021-billing",
    "questions_asked": 5,
    "answers": { ... }
  }
}
```

**Persistence strategy**:
- Atomic writes (write to `.tmp`, then rename)
- JSON format (human-readable, debuggable)
- Per-project storage (isolated contexts)
- Indefinite retention (no 24-hour limit)

---

### 4. Pessimistic Locking

**Principle**: File-level locks prevent concurrent modifications across MCP clients.

**Lock Hierarchy**:
```
Global locks:
  .kittify/.lock-config          # Config file writes

Feature locks:
  .kittify/.lock-021-billing     # Feature-level operations

Work package locks:
  .kittify/.lock-WP01            # Task status changes
  .kittify/.lock-WP02
```

**Lock Lifecycle**:
```python
from filelock import FileLock
import psutil

def move_task(wp_id: str, to_lane: str):
    lock_file = f".kittify/.lock-{wp_id}"
    lock = FileLock(lock_file, timeout=300)  # 5 min timeout
    
    try:
        with lock:
            # Critical section: update frontmatter, activity log
            update_wp_frontmatter(wp_id, lane=to_lane)
            add_activity_log_entry(wp_id, f"Moved to {to_lane}")
            git_commit(f"chore: Move {wp_id} to {to_lane}")
    except Timeout:
        # Check if process still exists
        lock_info = read_lock_file(lock_file)
        if not psutil.pid_exists(lock_info["pid"]):
            # Stale lock, remove and retry
            lock_file.unlink()
            return move_task(wp_id, to_lane)  # Retry
        else:
            raise LockError(f"WP locked by PID {lock_info['pid']}")
```

**Stale lock detection**:
- Lock files include PID and timestamp
- On timeout, check if PID exists (`psutil.pid_exists`)
- Auto-remove stale locks (process died)
- Manual cleanup: `rm .kittify/.lock-*`

---

## Component Deep Dive

### FastMCP Integration

**Role**: Handles MCP protocol (JSON-RPC), transport abstraction, tool registration.

**Key APIs used**:
```python
from fastmcp import FastMCP

app = FastMCP("Spec Kitty MCP Server")

# Tool registration (decorator-based)
@app.tool(
    name="feature_operations",
    description="Handle feature specification, planning, and implementation"
)
def feature_operations_handler(
    project_path: str,
    operation: str,
    feature_slug: str = None,
    arguments: dict = None
) -> dict:
    # Route to appropriate handler
    pass

# Server startup
app.run(transport="stdio")  # or transport="sse", host="127.0.0.1", port=8000
```

**Transport modes**:
- **Stdio**: JSON-RPC over stdin/stdout (Claude Desktop, Cursor)
- **SSE**: Server-Sent Events over HTTP (web clients, legacy)
- **HTTP**: (Future) Standard HTTP REST API with JSON payloads

---

### CLI Adapter Layer

**Purpose**: Translate MCP tool invocations → CLI function calls → OperationResult.

**Structure**:
```python
# src/specify_cli/mcp/adapters/cli_adapter.py

class CLIAdapter:
    """Thin wrapper around existing CLI modules."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.repo_root = find_git_root(project_path)
    
    # Feature operations
    def create_feature(self, description: str) -> OperationResult:
        from specify_cli.cli.commands import specify
        # Wrap CLI code, return OperationResult
    
    def create_plan(self, feature_slug: str) -> OperationResult:
        from specify_cli.cli.commands import plan
        # Wrap CLI code
    
    # Task operations
    def list_tasks(self, feature_slug: str, lane: str = None) -> OperationResult:
        from specify_cli.agent_utils import tasks
        # Wrap CLI code
    
    def move_task(self, feature_slug: str, wp_id: str, to_lane: str, note: str) -> OperationResult:
        from specify_cli.agent_utils import tasks
        # Acquire lock, wrap CLI code, release lock
    
    # Workspace operations
    def create_worktree(self, feature_slug: str, wp_id: str, base_wp: str = None) -> OperationResult:
        from specify_cli.core import worktree
        # Wrap CLI code
    
    # System operations
    def validate_project(self) -> OperationResult:
        # Check for .kittify/, config.yaml, etc.
```

**Error handling strategy**:
```python
def some_operation(...) -> OperationResult:
    try:
        result = cli_module.function(...)
        return OperationResult(success=True, ...)
    except SpecKittyError as e:
        # Known CLI error
        return OperationResult(
            success=False,
            message=str(e),
            errors=[e.details]
        )
    except Exception as e:
        # Unexpected error
        logger.exception("Unexpected error in MCP adapter")
        return OperationResult(
            success=False,
            message="Internal server error",
            errors=[f"Unexpected: {type(e).__name__}: {str(e)}"]
        )
```

---

### Session State Management

**Purpose**: Enable multi-turn conversations with context retention.

**Implementation**:
```python
# src/specify_cli/mcp/session/state.py

@dataclass
class ConversationState:
    session_id: str
    project_path: str
    created_at: datetime
    updated_at: datetime
    conversation_history: list[ConversationTurn]
    discovery_interview: Optional[DiscoveryInterview] = None
    
    def to_json(self) -> dict:
        """Serialize to JSON for persistence."""
        return {
            "session_id": self.session_id,
            "project_path": str(self.project_path),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "conversation_history": [t.to_dict() for t in self.conversation_history],
            "discovery_interview": self.discovery_interview.to_dict() if self.discovery_interview else None
        }
    
    @classmethod
    def from_json(cls, data: dict) -> "ConversationState":
        """Deserialize from JSON."""
        return cls(
            session_id=data["session_id"],
            project_path=Path(data["project_path"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            conversation_history=[ConversationTurn.from_dict(t) for t in data["conversation_history"]],
            discovery_interview=DiscoveryInterview.from_dict(data["discovery_interview"]) if data.get("discovery_interview") else None
        )
    
    def save(self, session_dir: Path):
        """Atomically write state to JSON file."""
        session_file = session_dir / f"{self.session_id}.json"
        tmp_file = session_dir / f"{self.session_id}.json.tmp"
        
        with open(tmp_file, "w") as f:
            json.dump(self.to_json(), f, indent=2)
        
        tmp_file.rename(session_file)  # Atomic rename
```

**Session directory structure**:
```
.kittify/mcp-sessions/
├── uuid-1234-5678.json       # Session state
├── uuid-2345-6789.json
└── .cleanup-last-run         # Timestamp of last cleanup
```

**Cleanup policy**:
- Sessions older than `MCP_SESSION_TIMEOUT` (default: 24 hours) → deleted
- Runs on server startup and every hour
- Configurable via environment variable

---

### Resource Locking

**Purpose**: Prevent concurrent modifications across multiple MCP clients.

**Implementation**:
```python
# src/specify_cli/mcp/session/locking.py

@dataclass
class ResourceLock:
    resource_id: str
    lock_dir: Path
    timeout: int = 300  # seconds
    
    def acquire(self) -> FileLock:
        """Acquire lock with timeout."""
        lock_file = self.lock_dir / f".lock-{self.resource_id}"
        lock = FileLock(lock_file, timeout=self.timeout)
        
        try:
            lock.acquire()
            # Write PID and timestamp to lock file
            with open(lock_file, "w") as f:
                json.dump({
                    "pid": os.getpid(),
                    "created_at": datetime.now().isoformat()
                }, f)
            return lock
        except Timeout:
            # Check for stale lock
            if self._is_stale(lock_file):
                lock_file.unlink()
                return self.acquire()  # Retry
            raise LockTimeoutError(f"Timeout acquiring lock for {self.resource_id}")
    
    def _is_stale(self, lock_file: Path) -> bool:
        """Check if lock is held by dead process."""
        try:
            with open(lock_file) as f:
                lock_info = json.load(f)
            return not psutil.pid_exists(lock_info["pid"])
        except Exception:
            return True  # Corrupt lock file → consider stale
```

**Lock granularity**:
- **Work package locks**: One lock per WP (`.lock-WP01`, `.lock-WP02`)
- **Feature locks**: One lock per feature (`.lock-021-billing`)
- **Config locks**: One lock for `.kittify/config.yaml` writes

**Why pessimistic locking?**:
- Simpler than optimistic locking (no conflict resolution)
- Git commits atomic, but frontmatter edits are not
- Multiple MCP clients editing same WP → must serialize
- Lock timeout prevents deadlocks (default: 5 minutes)

---

## Performance Considerations

### Latency Targets

| Operation | Target | Actual (Measured) |
|-----------|--------|-------------------|
| Server startup | <2s | ~500ms |
| Read operation (list_tasks) | <500ms | ~200ms |
| Write operation (move_task) | <2s | ~800ms (includes git commit) |
| Worktree creation | <5s | ~2-3s |
| Merge (6 WPs) | <30s | ~15s |

---

### Concurrency Model

**Max concurrent tool invocations**: 10 (configurable)

**Implementation**:
```python
# src/specify_cli/mcp/server.py

from concurrent.futures import ThreadPoolExecutor

class MCPServer:
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_operations = 0
    
    async def handle_tool_call(self, tool_name: str, params: dict):
        if self.active_operations >= self.max_workers:
            raise TooManyRequestsError("Server at capacity")
        
        self.active_operations += 1
        try:
            future = self.executor.submit(self._execute_tool, tool_name, params)
            result = await asyncio.wrap_future(future)
            return result
        finally:
            self.active_operations -= 1
```

**Why threading, not asyncio?**:
- CLI operations are CPU-bound (git operations, file I/O)
- No benefit from async/await (blocking I/O)
- ThreadPoolExecutor simpler for wrapping existing CLI code

---

### Memory Management

**Session cleanup**:
- Old sessions deleted after 24 hours
- Max 100 concurrent sessions (configurable)
- LRU eviction if max reached

**Lock cleanup**:
- Stale locks auto-detected and removed
- Manual cleanup: `spec-kitty mcp stop` removes all locks

---

## Security Considerations

### API Key Authentication

**When enabled**:
- API key passed in MCP connection headers
- Server validates using constant-time comparison (`hmac.compare_digest`)
- 401 Unauthorized if invalid

**Implementation**:
```python
# src/specify_cli/mcp/auth/api_key.py

import hmac

def validate_api_key(provided_key: str, expected_key: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    if not provided_key or not expected_key:
        return False
    return hmac.compare_digest(provided_key, expected_key)
```

**Key requirements**:
- Minimum 32 characters
- High entropy (use `secrets.token_urlsafe(32)`)
- Stored in environment variable, NOT config file

---

### Input Validation

**Project path validation**:
```python
def validate_project_path(path: str) -> Path:
    """Ensure path is absolute, exists, and contains .kittify/."""
    p = Path(path).resolve()  # Absolute path
    
    if not p.exists():
        raise ValueError(f"Path does not exist: {path}")
    
    if not (p / ".kittify").is_dir():
        raise ValueError(f"Not a Spec Kitty project: {path}")
    
    return p
```

**Feature slug validation**:
```python
def validate_feature_slug(slug: str) -> str:
    """Ensure slug matches ###-feature-name format."""
    if not re.match(r"^\d{3}-[a-z0-9-]+$", slug):
        raise ValueError(f"Invalid feature slug: {slug}")
    return slug
```

---

### File System Isolation

**Restrictions**:
- All operations scoped to project path
- No access to parent directories
- Symlinks resolved before validation

---

## Design Decisions & Trade-Offs

### Decision 1: Thin Wrapper vs. Full Reimplementation

**Options**:
- A) Thin wrapper around existing CLI code (chosen)
- B) Full reimplementation of business logic in MCP layer

**Trade-offs**:
- **A** (chosen):
  - ✅ No code duplication
  - ✅ CLI improvements auto-benefit MCP
  - ✅ Faster implementation
  - ❌ Adapter layer overhead
- **B**:
  - ✅ MCP-optimized implementation
  - ❌ Code duplication and drift
  - ❌ Maintenance burden

**Decision**: Thin wrapper for maintainability and parity.

---

### Decision 2: Pessimistic vs. Optimistic Locking

**Options**:
- A) Pessimistic locking (filelock) (chosen)
- B) Optimistic locking (conflict detection + retry)

**Trade-offs**:
- **A** (chosen):
  - ✅ Simple implementation
  - ✅ No conflict resolution needed
  - ✅ Works with git commits (atomic)
  - ❌ Blocking (agents wait for locks)
- **B**:
  - ✅ Non-blocking
  - ❌ Complex conflict resolution
  - ❌ Retry logic needed
  - ❌ Git commits not easily retryable

**Decision**: Pessimistic for simplicity. Lock timeout (5 min) prevents deadlocks.

---

### Decision 3: JSON vs. Database for Session State

**Options**:
- A) JSON files (chosen)
- B) SQLite database

**Trade-offs**:
- **A** (chosen):
  - ✅ Simple, no schema migrations
  - ✅ Human-readable (debuggable)
  - ✅ Per-project isolation (no shared DB)
  - ❌ Slower queries (but sessions small <1KB)
- **B**:
  - ✅ Faster queries
  - ✅ ACID guarantees
  - ❌ Schema migrations needed
  - ❌ Shared DB complicates multi-project support

**Decision**: JSON for simplicity and debuggability.

---

## Future Enhancements

### Planned Features

1. **HTTP Transport**: Standard REST API (replace SSE)
2. **Streaming Responses**: Server-sent events for long operations
3. **Webhooks**: Notify external systems on task completion
4. **Multi-Project Dashboard**: Web UI for managing multiple projects
5. **Audit Logging**: Compliance-friendly activity logs

---

## Next Steps

**For contributors**:
- Read [CONTRIBUTING.md](../../CONTRIBUTING.md) for development setup
- Review [MCP Tools Reference](../reference/mcp-tools.md) for API contracts
- Check [GitHub Issues](https://github.com/Priivacy-ai/spec-kitty/issues) for open tasks

**For users**:
- [MCP Server Quickstart](../tutorials/mcp-server-quickstart.md) - Get started
- [MCP Conversational Workflows](../how-to/mcp-conversational-workflows.md) - Usage patterns
- [Troubleshooting](../how-to/troubleshoot-mcp.md) - Common issues

---

*Last updated: 2026-01-31*  
*Spec Kitty version: 0.14.0+*
