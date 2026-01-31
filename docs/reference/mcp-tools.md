# MCP Tools Reference

**Complete reference for all Spec Kitty MCP tools and operations**

The Spec Kitty MCP server exposes 4 main tools, each providing multiple operations. This reference documents parameters, return types, and examples for every operation.

---

## Tool Categories

| Tool | Operations | Purpose |
|------|------------|---------|
| `feature_operations` | 6 operations | Feature workflow (specify, plan, tasks, implement, review, accept) |
| `task_operations` | 4 operations | Task management (list, move, history, status) |
| `workspace_operations` | 3 operations | Git worktree management (create, list, merge) |
| `system_operations` | 4 operations | Server health and project validation |

---

## feature_operations

**Description**: Handle feature specification, planning, task generation, and implementation workflows.

### Parameters (Common)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_path` | string | Yes | Absolute path to Spec Kitty project |
| `operation` | enum | Yes | One of: specify, plan, tasks, implement, review, accept |
| `feature_slug` | string | Conditional | Required for all ops except specify |
| `arguments` | object | No | Operation-specific parameters (see below) |

---

### Operation: specify

**Create a new feature specification through discovery interview**

**Arguments**:
```json
{
  "description": "Brief feature description (triggers discovery interview)"
}
```

**Returns**:
```json
{
  "success": true,
  "message": "Feature specification created",
  "data": {
    "feature_slug": "021-saas-billing-system",
    "spec_path": "/path/to/kitty-specs/021-saas-billing-system/spec.md",
    "user_stories": 5,
    "success_criteria": 8
  },
  "artifacts": [
    "kitty-specs/021-saas-billing-system/spec.md"
  ],
  "errors": []
}
```

**Example (conversational)**:
```
User: I want to build a real-time collaborative text editor

[AI uses feature_operations with operation="specify", conducts interview]
```

---

### Operation: plan

**Generate technical implementation plan for a feature**

**Arguments**:
```json
{
  "feature_slug": "021-saas-billing-system"
}
```

**Returns**:
```json
{
  "success": true,
  "message": "Technical plan created",
  "data": {
    "plan_path": "/path/to/kitty-specs/021-saas-billing-system/plan.md",
    "work_packages_proposed": 6,
    "technologies": ["FastAPI", "Celery", "Redis", "PostgreSQL", "Stripe SDK"]
  },
  "artifacts": [
    "kitty-specs/021-saas-billing-system/plan.md"
  ],
  "errors": []
}
```

**Example (conversational)**:
```
User: Create a technical plan for the billing system
```

---

### Operation: tasks

**Break down plan into work packages and subtasks**

**Arguments**:
```json
{
  "feature_slug": "021-saas-billing-system"
}
```

**Returns**:
```json
{
  "success": true,
  "message": "Tasks generated",
  "data": {
    "work_packages": 6,
    "subtasks": 47,
    "tasks_path": "/path/to/kitty-specs/021-saas-billing-system/tasks/",
    "dependency_graph": {
      "WP01": [],
      "WP02": ["WP01"],
      "WP03": ["WP01"],
      "WP04": ["WP02", "WP03"],
      "WP05": ["WP01"],
      "WP06": ["WP01"]
    }
  },
  "artifacts": [
    "kitty-specs/021-saas-billing-system/tasks.md",
    "kitty-specs/021-saas-billing-system/tasks/WP01-database-schema.md",
    "..."
  ],
  "errors": []
}
```

**Example (conversational)**:
```
User: Generate tasks for the billing feature
```

---

### Operation: implement

**Create worktree for work package implementation**

**Arguments**:
```json
{
  "feature_slug": "021-saas-billing-system",
  "wp_id": "WP01",
  "base_wp": null  // Optional: branch from another WP
}
```

**Returns**:
```json
{
  "success": true,
  "message": "Worktree created for WP01",
  "data": {
    "worktree_path": "/path/to/.worktrees/021-saas-billing-system-WP01",
    "branch_name": "021-saas-billing-system-WP01",
    "base_branch": "main",
    "wp_status": "doing"
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: Start implementing WP01
User: Implement WP02 based on WP01
[AI uses base_wp="WP01" for WP02]
```

---

### Operation: review

**Move work package to review lane**

**Arguments**:
```json
{
  "feature_slug": "021-saas-billing-system",
  "wp_id": "WP01",
  "note": "Ready for review: All tests passing"
}
```

**Returns**:
```json
{
  "success": true,
  "message": "WP01 moved to for_review",
  "data": {
    "wp_id": "WP01",
    "previous_lane": "doing",
    "new_lane": "for_review",
    "timestamp": "2026-01-31T15:30:00Z"
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: WP01 is ready for review
```

---

### Operation: accept

**Accept reviewed work package and move to done**

**Arguments**:
```json
{
  "feature_slug": "021-saas-billing-system",
  "wp_id": "WP01",
  "reviewer": "Agent Bob",
  "note": "LGTM, all tests passing"
}
```

**Returns**:
```json
{
  "success": true,
  "message": "WP01 accepted and moved to done",
  "data": {
    "wp_id": "WP01",
    "previous_lane": "for_review",
    "new_lane": "done",
    "reviewed_by": "Agent Bob",
    "timestamp": "2026-01-31T16:00:00Z"
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: Approve WP01, looks good
```

---

## task_operations

**Description**: Manage work package status, dependencies, and activity logs.

### Parameters (Common)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_path` | string | Yes | Absolute path to Spec Kitty project |
| `operation` | enum | Yes | One of: list_tasks, move_task, add_history, query_status |
| `feature_slug` | string | Yes | Feature identifier |
| `arguments` | object | Varies | Operation-specific parameters |

---

### Operation: list_tasks

**List all work packages for a feature, optionally filtered by lane**

**Arguments**:
```json
{
  "lane": "doing"  // Optional: planned, doing, for_review, done
}
```

**Returns**:
```json
{
  "success": true,
  "message": "Found 2 tasks",
  "data": {
    "tasks": [
      {
        "wp_id": "WP02",
        "title": "Stripe integration",
        "lane": "doing",
        "assignee": "Agent Alice",
        "dependencies": ["WP01"],
        "subtasks": ["T008", "T009", "T010"]
      },
      {
        "wp_id": "WP03",
        "title": "Usage metering",
        "lane": "doing",
        "assignee": "Agent Charlie",
        "dependencies": ["WP01"],
        "subtasks": ["T011", "T012", "T013"]
      }
    ]
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: What tasks are currently being worked on?
User: Show me all planned tasks
```

---

### Operation: move_task

**Move work package between lanes (planned → doing → for_review → done)**

**Arguments**:
```json
{
  "wp_id": "WP01",
  "to_lane": "doing",
  "note": "Starting implementation",
  "agent": "Agent Alice"
}
```

**Returns**:
```json
{
  "success": true,
  "message": "WP01 moved from planned to doing",
  "data": {
    "wp_id": "WP01",
    "previous_lane": "planned",
    "new_lane": "doing",
    "assignee": "Agent Alice",
    "timestamp": "2026-01-31T10:00:00Z",
    "lock_acquired": true
  },
  "artifacts": [],
  "errors": []
}
```

**Error cases**:
- Lock timeout (another agent moving same WP)
- Invalid lane transition (e.g., planned → done)
- Uncommitted changes (move to for_review requires clean worktree)

**Example (conversational)**:
```
User: I'm starting work on WP01
User: Move WP01 to review
```

---

### Operation: add_history

**Add entry to work package activity log without changing lane**

**Arguments**:
```json
{
  "wp_id": "WP01",
  "note": "Implemented database schema, added tests",
  "agent": "Agent Alice"
}
```

**Returns**:
```json
{
  "success": true,
  "message": "Activity log updated",
  "data": {
    "wp_id": "WP01",
    "timestamp": "2026-01-31T11:30:00Z",
    "agent": "Agent Alice"
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: Log a progress update for WP01: "Database schema complete, 80% test coverage"
```

---

### Operation: query_status

**Get detailed status for a work package, including dependencies and blockers**

**Arguments**:
```json
{
  "wp_id": "WP04"
}
```

**Returns**:
```json
{
  "success": true,
  "message": "WP04 status retrieved",
  "data": {
    "wp_id": "WP04",
    "title": "Billing engine",
    "lane": "planned",
    "dependencies": ["WP02", "WP03"],
    "dependency_status": {
      "WP02": "for_review",  // ⚠️  Blocking
      "WP03": "doing"         // ⚠️  Blocking
    },
    "is_blocked": true,
    "blockers": ["WP02", "WP03"],
    "can_start": false,
    "dependents": ["WP05"],  // WP05 depends on WP04
    "activity_log": [
      {
        "timestamp": "2026-01-31T09:00:00Z",
        "action": "created",
        "agent": "system"
      }
    ]
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: Why is WP04 blocked?
User: What's the status of WP01?
```

---

## workspace_operations

**Description**: Manage git worktrees for parallel development.

### Parameters (Common)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_path` | string | Yes | Absolute path to Spec Kitty project |
| `operation` | enum | Yes | One of: create_worktree, list_worktrees, merge |
| `feature_slug` | string | Yes | Feature identifier |
| `arguments` | object | Varies | Operation-specific parameters |

---

### Operation: create_worktree

**Create isolated git worktree for work package**

**Arguments**:
```json
{
  "wp_id": "WP02",
  "base_wp": "WP01"  // Optional: branch from another WP's branch
}
```

**Returns**:
```json
{
  "success": true,
  "message": "Worktree created for WP02",
  "data": {
    "worktree_path": "/path/to/.worktrees/021-saas-billing-system-WP02",
    "branch_name": "021-saas-billing-system-WP02",
    "base_branch": "021-saas-billing-system-WP01",
    "git_status": "clean"
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: Create a workspace for WP02 based on WP01
```

---

### Operation: list_worktrees

**List all active worktrees for feature**

**Arguments**: None (uses feature_slug from common params)

**Returns**:
```json
{
  "success": true,
  "message": "Found 3 worktrees",
  "data": {
    "worktrees": [
      {
        "wp_id": "WP01",
        "path": "/path/.worktrees/021-saas-billing-system-WP01",
        "branch": "021-saas-billing-system-WP01",
        "status": "clean",
        "commits_ahead": 5
      },
      {
        "wp_id": "WP02",
        "path": "/path/.worktrees/021-saas-billing-system-WP02",
        "branch": "021-saas-billing-system-WP02",
        "status": "modified",
        "commits_ahead": 2
      },
      {
        "wp_id": "WP03",
        "path": "/path/.worktrees/021-saas-billing-system-WP03",
        "branch": "021-saas-billing-system-WP03",
        "status": "clean",
        "commits_ahead": 8
      }
    ]
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: Show me all worktrees for the billing feature
```

---

### Operation: merge

**Merge feature into target branch with preflight validation**

**Arguments**:
```json
{
  "target_branch": "main",
  "dry_run": false,
  "strategy": "merge"  // merge, squash, or rebase
}
```

**Returns (dry_run=true)**:
```json
{
  "success": true,
  "message": "Preflight checks passed with warnings",
  "data": {
    "preflight": {
      "all_wps_complete": true,
      "all_worktrees_clean": true,
      "target_up_to_date": true,
      "conflicts_predicted": [
        {
          "file": "src/billing/models.py",
          "conflicting_wps": ["WP01", "WP04"],
          "auto_resolvable": false
        }
      ]
    },
    "merge_order": ["WP01", "WP02", "WP03", "WP04", "WP05", "WP06"],
    "estimated_conflicts": 1
  },
  "artifacts": [],
  "errors": []
}
```

**Returns (dry_run=false)**:
```json
{
  "success": true,
  "message": "Feature merged successfully",
  "data": {
    "merged_wps": 6,
    "total_commits": 47,
    "conflicts_resolved": 1,
    "tests_run": 98,
    "tests_passed": 98
  },
  "artifacts": [
    "CHANGELOG.md"
  ],
  "errors": []
}
```

**Example (conversational)**:
```
User: Check if I can merge the billing feature
[AI uses dry_run=true]
User: Go ahead and merge it
[AI uses dry_run=false]
```

---

## system_operations

**Description**: Server health checks, project validation, and system information.

### Parameters (Common)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_path` | string | Conditional | Required for validate_project, optional for others |
| `operation` | enum | Yes | One of: health_check, validate_project, list_missions, server_config |
| `arguments` | object | No | Operation-specific parameters |

---

### Operation: health_check

**Check MCP server health and status**

**Arguments**: None

**Returns**:
```json
{
  "success": true,
  "message": "Server healthy",
  "data": {
    "status": "healthy",
    "uptime_seconds": 3600,
    "active_projects": 2,
    "active_sessions": 1,
    "version": "0.14.0",
    "transport": "stdio",
    "auth_enabled": false
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: Is the MCP server working?
User: How long has the server been running?
```

---

### Operation: validate_project

**Validate Spec Kitty project structure**

**Arguments**:
```json
{
  "project_path": "/path/to/project"
}
```

**Returns**:
```json
{
  "success": true,
  "message": "Project valid",
  "data": {
    "project_path": "/path/to/project",
    "has_kittify_dir": true,
    "has_config": true,
    "mission": "software-dev",
    "features_count": 12,
    "worktrees_count": 3
  },
  "artifacts": [],
  "errors": []
}
```

**Error cases**:
- Missing `.kittify/` directory
- Missing `config.yaml`
- Invalid mission configuration

**Example (conversational)**:
```
User: Is this project set up correctly for Spec Kitty?
```

---

### Operation: list_missions

**List available missions and their configurations**

**Arguments**: None

**Returns**:
```json
{
  "success": true,
  "message": "Found 3 missions",
  "data": {
    "missions": [
      {
        "name": "software-dev",
        "description": "Full-stack software development mission",
        "features": ["specify", "plan", "tasks", "implement", "review", "accept"]
      },
      {
        "name": "documentation",
        "description": "Divio documentation mission",
        "features": ["specify", "plan", "generate", "validate"]
      },
      {
        "name": "research",
        "description": "Research and investigation mission",
        "features": ["specify", "research", "synthesize"]
      }
    ]
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: What missions are available?
```

---

### Operation: server_config

**Get server configuration (API key redacted)**

**Arguments**: None

**Returns**:
```json
{
  "success": true,
  "message": "Server configuration retrieved",
  "data": {
    "host": "127.0.0.1",
    "port": 8000,
    "transport": "stdio",
    "auth_enabled": true,
    "api_key": "************",  // Redacted for security
    "version": "0.14.0"
  },
  "artifacts": [],
  "errors": []
}
```

**Example (conversational)**:
```
User: What are the server settings?
```

---

## Common Return Types

### OperationResult

All MCP tools return this structure:

```typescript
interface OperationResult {
  success: boolean;            // Operation succeeded
  message: string;              // Human-readable summary
  data: object | null;          // Structured result data
  artifacts: string[];          // Paths to created/modified files
  errors: string[];             // Error messages (if any)
}
```

---

## Error Handling

### Common Error Patterns

**Lock timeout**:
```json
{
  "success": false,
  "message": "Failed to acquire lock",
  "data": null,
  "artifacts": [],
  "errors": [
    "Lock timeout after 300 seconds. Resource WP01 is locked by process 12345.",
    "Kill the process or wait for operation to complete."
  ]
}
```

**Invalid project**:
```json
{
  "success": false,
  "message": "Invalid project path",
  "data": null,
  "artifacts": [],
  "errors": [
    "Directory does not contain .kittify/",
    "Run 'spec-kitty init' to initialize project"
  ]
}
```

**Dependency not satisfied**:
```json
{
  "success": false,
  "message": "Cannot start WP04",
  "data": {
    "wp_id": "WP04",
    "missing_dependencies": ["WP02", "WP03"]
  },
  "artifacts": [],
  "errors": [
    "WP04 depends on WP02 (status: doing) and WP03 (status: planned)",
    "Complete dependencies before starting WP04"
  ]
}
```

---

## Best Practices

### 1. Always Provide Absolute Paths

```json
✅ CORRECT:
{
  "project_path": "/Users/me/projects/billing-service"
}

❌ WRONG:
{
  "project_path": "~/projects/billing-service"  // Not expanded
  "project_path": "../billing-service"          // Relative path
}
```

---

### 2. Check Status Before Operations

```
Before moving WP to review:
1. query_status → check dependencies satisfied
2. list_worktrees → check worktree clean
3. move_task → proceed
```

---

### 3. Use Dry-Run for Destructive Operations

```
Before merging:
1. merge with dry_run=true → forecast conflicts
2. Review conflicts
3. merge with dry_run=false → execute
```

---

### 4. Handle Lock Timeouts Gracefully

```
If lock timeout:
1. Check if process still exists (ps aux | grep <PID>)
2. Kill stale process or wait
3. Retry operation
```

---

## Next Steps

**Explore more**:
- [MCP Conversational Workflows](../how-to/mcp-conversational-workflows.md) - Usage patterns and examples
- [MCP Server Architecture](../explanation/mcp-server-architecture.md) - How tools are implemented
- [Troubleshooting](../how-to/troubleshoot-mcp.md) - Common issues and solutions

---

*Last updated: 2026-01-31*  
*Spec Kitty version: 0.14.0+*
