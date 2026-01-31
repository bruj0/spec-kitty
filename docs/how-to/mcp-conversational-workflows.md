# MCP Conversational Workflows

**Master conversational interaction with the Spec Kitty MCP server**

This guide demonstrates advanced conversational patterns for using Spec Kitty through natural language, replacing traditional slash commands with intuitive AI-driven workflows.

---

## Core Workflow Patterns

### Pattern 1: Feature Creation from Idea to Specification

**Traditional workflow** (slash commands):
```
/spec-kitty.specify
> Answer discovery interview questions manually
> Review generated spec.md
```

**Conversational workflow**:

```
User: I want to build a multi-tenant SaaS billing system with Stripe integration,
      usage metering, and tiered pricing plans.

AI: I'll help you create a specification for the billing system.
    Let me ask a few questions to understand the requirements better.

    1. What pricing tiers do you envision? (e.g., Free, Pro, Enterprise)

User: Free (up to 100 API calls/month), Pro ($29/month, 10K calls),
      Enterprise (custom pricing, unlimited calls).

AI: 2. How should usage metering work? Real-time tracking or periodic aggregation?

User: Real-time tracking with daily aggregation for billing reports.

AI: 3. Should the system support proration for mid-cycle upgrades/downgrades?

User: Yes, prorate based on days remaining in billing cycle.

AI: Great! I have enough information to generate the specification.

    [MCP server creates kitty-specs/021-saas-billing-system/spec.md]

    I've created the specification in kitty-specs/021-saas-billing-system/spec.md.
    
    Key highlights:
    - User Story 1: Tiered pricing (Free/Pro/Enterprise)
    - User Story 2: Real-time usage metering with daily aggregation
    - User Story 3: Proration for plan changes
    - Success Criteria: Accurate billing, <500ms metering latency
    
    Would you like me to create a technical plan next?
```

**MCP tools invoked**:
1. `feature_operations` (operation: "specify")
   - Conducts discovery interview (multi-turn)
   - Validates inputs against mission requirements
   - Generates spec.md with user stories, success criteria, risks

---

### Pattern 2: Technical Planning with Interactive Refinement

**Traditional workflow**:
```
/spec-kitty.plan for feature 021
> Review generated plan.md
> Manually edit if changes needed
```

**Conversational workflow**:

```
User: Create a technical plan for the billing system.

AI: I'll analyze the specification and propose an implementation approach.

    [MCP server generates plan.md]

    I've created a technical plan. Here's the proposed approach:

    - **Architecture**: Event-driven with background workers for metering
    - **Tech stack**: FastAPI + Celery + Redis + PostgreSQL + Stripe SDK
    - **Storage**: 
      - PostgreSQL: User plans, subscriptions, billing history
      - Redis: Real-time usage counters
    - **Work packages**:
      - WP01: Database schema and models (6 subtasks)
      - WP02: Stripe integration (API keys, webhooks) (8 subtasks)
      - WP03: Usage metering service (real-time tracking) (9 subtasks)
      - WP04: Billing engine (proration, invoicing) (11 subtasks)
      - WP05: Admin dashboard (plan management) (7 subtasks)

    Does this approach work for you, or would you like to adjust anything?

User: The approach looks good, but I'd like to add a WP for audit logging
      (track all billing events for compliance).

AI: Great idea! I'll add WP06 for audit logging.

    [MCP server updates plan.md]

    Updated plan:
    - WP06: Audit logging and compliance (6 subtasks)
      - Log all billing events (plan changes, payments, refunds)
      - Immutable append-only log
      - Compliance exports (CSV, JSON)
      - 7-year retention policy

    Ready to generate detailed tasks?

User: Yes, create the tasks.

AI: [MCP server generates tasks.md and tasks/*.md]

    Tasks created! 6 work packages, 47 subtasks total.
    
    Critical path: WP01 → WP02 → WP03 → WP04
    Parallelizable: WP05 and WP06 can run alongside WP04.
    
    Would you like to start implementing, or review the task breakdown first?
```

**MCP tools invoked**:
1. `feature_operations` (operation: "plan")
   - Generates plan.md with technical approach
   - Returns structured plan summary
2. `feature_operations` (operation: "tasks")
   - Parses plan.md into work packages
   - Generates task files with dependencies
   - Validates dependency graph (no cycles)

---

### Pattern 3: Parallel Development Coordination

**Traditional workflow**:
```bash
# Agent 1:
spec-kitty implement WP01
# Agent 2: waits...
spec-kitty implement WP02 --base WP01
# Agent 3: waits...
spec-kitty implement WP03 --base WP02
```

**Conversational workflow**:

```
User: Show me which work packages can be started now.

AI: [MCP server analyzes dependencies]

    Available to start (no dependencies):
    - WP01: Database schema and models
    
    Once WP01 completes, these can run in parallel:
    - WP02: Stripe integration (depends on WP01)
    - WP05: Admin dashboard (depends on WP01)
    - WP06: Audit logging (depends on WP01)

User: Start WP01 for me.

AI: [MCP server creates .worktrees/021-billing-WP01/]

    Worktree created at: .worktrees/021-billing-WP01/
    Branch: 021-saas-billing-system-WP01
    
    To continue implementation:
    cd .worktrees/021-billing-WP01/
    # Work on WP01...
    git commit -m "feat(WP01): Database schema"
    
    When done, say "Move WP01 to review"

[... Agent implements WP01, commits changes ...]

User: Move WP01 to review.

AI: [MCP server moves WP01 to for_review lane]

    WP01 moved to for_review. Activity log updated.
    
    Next available work packages (now unblocked):
    - WP02: Stripe integration (ready)
    - WP05: Admin dashboard (ready)
    - WP06: Audit logging (ready)
    
    Would you like to start multiple in parallel?

User: Yes, start WP02, WP05, and WP06 for three different agents.

AI: [MCP server creates 3 worktrees]

    Created 3 worktrees:
    1. .worktrees/021-billing-WP02/ (Agent A)
    2. .worktrees/021-billing-WP05/ (Agent B)
    3. .worktrees/021-billing-WP06/ (Agent C)
    
    All branched from WP01's branch (021-saas-billing-system-WP01).
    
    Agents can now work in parallel without conflicts!
```

**MCP tools invoked**:
1. `task_operations` (operation: "query_status")
   - Parses dependencies from frontmatter
   - Builds inverse dependency graph
   - Returns WPs with no unmet dependencies
2. `workspace_operations` (operation: "create_worktree")
   - Creates isolated worktree for each WP
   - Branches from base WP if specified
   - Updates WP status to "doing"
3. `task_operations` (operation: "move_task")
   - Validates lane transition
   - Acquires lock (prevents concurrent moves)
   - Updates frontmatter and activity log

---

### Pattern 4: Cross-Project Context Switching

**Traditional workflow**:
```bash
# Terminal 1:
cd /path/to/project1
spec-kitty agent tasks status

# Terminal 2:
cd /path/to/project2
spec-kitty agent tasks status
```

**Conversational workflow**:

```
User: Show me features in /Users/me/projects/api-gateway

AI: [MCP server switches to api-gateway project]

    Features in api-gateway project:
    1. 005-rate-limiting (done)
    2. 007-authentication (for_review)
    3. 009-circuit-breaker (doing)
    4. 012-observability (planned)

User: What's the status of the authentication feature?

AI: [MCP server reads kitty-specs/007-authentication/tasks/]

    Feature: 007-authentication
    Progress: 5/6 work packages complete (83%)
    
    Status:
    - WP01: OAuth2 implementation ✓ done
    - WP02: JWT token service ✓ done
    - WP03: Role-based access control ✓ done
    - WP04: API key management ✓ done
    - WP05: Audit logging ✓ done
    - WP06: Integration tests 🔍 for_review (assigned to Agent Bob)
    
    Last activity: WP06 moved to for_review 2 hours ago by Agent Bob

User: Now show me features in /Users/me/projects/billing-service

AI: [MCP server switches to billing-service project]

    Features in billing-service project:
    1. 021-saas-billing-system (doing)
    2. 024-payment-retries (planned)

User: For the billing-service project, which tasks are blocked?

AI: [MCP server analyzes dependencies in billing-service]

    Blocked tasks in billing-service:
    - WP04: Billing engine (waiting for WP02, WP03 to complete)
    - WP05: Admin dashboard (waiting for WP01, WP02 to complete)
    
    Currently in progress:
    - WP02: Stripe integration (Agent Alice, 30% complete)
    - WP03: Usage metering (Agent Charlie, 50% complete)
    
    Once WP02 and WP03 are done, WP04 and WP05 can start in parallel.
```

**MCP tools invoked**:
1. `system_operations` (operation: "validate_project")
   - Checks for `.kittify/` directory
   - Loads project configuration
   - Switches active project context
2. `feature_operations` (operation: "list_features")
   - Scans `kitty-specs/` directory
   - Returns feature metadata (status, progress)
3. `task_operations` (operation: "query_status")
   - Parses dependencies from all WPs
   - Identifies blocked vs. ready tasks
   - Returns dependency chains

---

## Advanced Conversational Patterns

### Pattern 5: Intelligent Discovery Interview

**Traditional approach**: Fixed question set from template

**Conversational approach**: Adaptive questioning based on previous answers

```
User: Create a feature for real-time collaborative editing.

AI: I'll help you spec this out. Let me understand the requirements.

    1. What type of content will users be collaborating on?
       (e.g., text documents, code files, spreadsheets, diagrams)

User: Rich text documents (like Google Docs).

AI: Got it. For rich text, I'll need to know about formatting capabilities.

    2. What formatting features should be supported?
       - Basic (bold, italic, lists)
       - Advanced (tables, images, comments)
       - Full (custom styles, templates, version history)

User: Advanced formatting with comments, but no custom styles or templates.

AI: Makes sense. Now about real-time sync architecture:

    3. How many concurrent editors do you expect per document?
       (affects architecture: WebSockets vs. CRDT vs. Operational Transform)

User: Up to 10 concurrent editors typically, max 50.

AI: Perfect. Operational Transform should work well for that scale.

    4. Should changes be visible character-by-character (Google Docs style),
       or should there be a small delay to batch updates?

User: Character-by-character for immediate feedback.

AI: Last question about conflict resolution:

    5. If two users edit the same text simultaneously, how should conflicts
       be resolved? (last-write-wins, manual merge, automatic merge)

User: Automatic merge with operational transform (intention preservation).

AI: Excellent! I have everything I need.

    [MCP server creates spec.md with 5 user stories]

    Specification created for: 030-collaborative-rich-text-editor
    
    Key decisions recorded:
    - Rich text with advanced formatting (tables, images, comments)
    - Operational Transform for concurrent editing (10-50 users)
    - Character-by-character sync (WebSocket transport)
    - Automatic conflict resolution (intention-preserving OT)
    
    Success criteria include:
    - <100ms edit-to-display latency (SC-001)
    - No data loss during concurrent edits (SC-002)
    - 50 concurrent editors without degradation (SC-003)
    
    Ready to plan the implementation?
```

**Intelligence**:
- AI adapts question 2 based on answer 1 (rich text → formatting options)
- Question 3 scales suggestion based on typical use cases
- Question 4 informed by scalability answer (real-time for 10-50 users)
- Question 5 follows from architecture choice (OT for conflict resolution)

**MCP tool behavior**:
- `feature_operations` (specify) stores conversation state in `.kittify/mcp-sessions/<session-id>.json`
- Resumes interview if interrupted (e.g., connection lost, user navigates away)
- Validates completeness before generating spec.md

---

### Pattern 6: Conversational Merge Workflow

**Traditional workflow**:
```bash
spec-kitty merge --feature 021 --dry-run
# Review conflicts manually
spec-kitty merge --feature 021
# Resolve conflicts manually
git commit
```

**Conversational workflow**:

```
User: I'm done with all work packages for the billing feature. Can I merge it?

AI: Let me check if the feature is ready for merge.

    [MCP server runs preflight checks]

    Preflight results for 021-saas-billing-system:
    
    ✓ All 6 work packages complete
    ✓ No uncommitted changes in worktrees
    ✓ Target branch (main) is up-to-date
    ✗ Potential conflicts detected in 3 files:
      - src/billing/stripe_client.py (WP02, WP04)
      - src/billing/models.py (WP01, WP03, WP04)
      - tests/test_billing.py (WP02, WP03, WP05)
    
    Conflict forecast:
    - stripe_client.py: Auto-resolvable (different functions)
    - models.py: Manual resolution required (overlapping schema changes)
    - test_billing.py: Auto-resolvable (different test classes)
    
    Would you like to proceed with the merge? I can handle auto-resolvable
    conflicts, but you'll need to resolve models.py manually.

User: Yes, proceed with the merge.

AI: [MCP server begins merge workflow]

    Merging work packages in dependency order:
    
    [1/6] Merging WP01: Database schema ✓
    [2/6] Merging WP02: Stripe integration ✓
    [3/6] Merging WP03: Usage metering ✓
    [4/6] Merging WP04: Billing engine ⚠️  Conflict in models.py
    
    Conflict detected in src/billing/models.py:
    
    <<<<<<< WP01
    class Subscription(BaseModel):
        plan: Plan
        status: SubscriptionStatus
    =======
    class Subscription(BaseModel):
        plan: Plan
        user: User
        status: SubscriptionStatus
        usage_credits: int = 0
    >>>>>>> WP04
    
    Both WPs added fields to Subscription. WP01 kept it minimal, WP04 added
    user and usage_credits. The correct resolution is likely to combine both,
    keeping all fields:
    
    class Subscription(BaseModel):
        plan: Plan
        user: User
        status: SubscriptionStatus
        usage_credits: int = 0
    
    Should I apply this resolution?

User: Yes, that looks correct.

AI: [MCP server resolves conflict and continues]

    [4/6] Merging WP04: Billing engine ✓ (conflict resolved)
    [5/6] Merging WP05: Admin dashboard ✓
    [6/6] Merging WP06: Audit logging ✓
    
    All work packages merged successfully!
    
    Final actions:
    - Merged 6 work packages (47 commits)
    - Resolved 1 manual conflict
    - Ran tests: 98 passed, 0 failed
    - Updated CHANGELOG.md
    
    The feature is now on main branch. Worktrees can be cleaned up:
    rm -rf .worktrees/021-billing-*
    
    Would you like me to create a GitHub pull request?

User: Yes, create a PR.

AI: [MCP server creates PR via GitHub API]

    Pull request created: #142
    Title: "feat: Multi-tenant SaaS billing system with Stripe"
    
    https://github.com/yourorg/yourrepo/pull/142
    
    PR description includes:
    - Feature overview (from spec.md)
    - Work packages completed (6/6)
    - Testing coverage (98 tests)
    - Breaking changes (none)
    - Migration guide (if any)
    
    Ready to ship! 🚀
```

**MCP tools invoked**:
1. `workspace_operations` (operation: "merge", dry_run: true)
   - Runs preflight validation
   - Predicts conflicts using diff analysis
   - Classifies conflicts as auto-resolvable vs. manual
2. `workspace_operations` (operation: "merge", dry_run: false)
   - Executes merge in dependency order
   - Applies auto-resolution rules (context-aware)
   - Pauses for manual resolution when needed
3. [Future] `github_operations` (operation: "create_pr")
   - Generates PR description from spec and plan
   - Adds reviewers based on CODEOWNERS
   - Links related issues

---

### Pattern 7: Multi-Agent Coordination

**Scenario**: 3 agents working on different WPs in parallel

**Conversational coordination**:

```
Agent A: I'm starting WP02 (Stripe integration).

AI: [MCP server assigns WP02 to Agent A]

    WP02 assigned to Agent A.
    Worktree: .worktrees/021-billing-WP02/
    Status: doing
    
    Note: WP04 (Billing engine) depends on WP02. Please notify when complete.

Agent B: What can I work on while Agent A does WP02?

AI: [MCP server checks availability]

    Available work packages (no blockers):
    - WP05: Admin dashboard (depends on WP01, which is complete)
    - WP06: Audit logging (depends on WP01, which is complete)
    
    WP03 (Usage metering) is also available but depends on WP02 (Agent A's work).
    
    I recommend WP05 or WP06 to avoid waiting on Agent A.

Agent B: I'll take WP05.

AI: [MCP server assigns WP05 to Agent B]

    WP05 assigned to Agent B.
    Worktree: .worktrees/021-billing-WP05/
    Status: doing

Agent C: I'll take WP06.

AI: [MCP server assigns WP06 to Agent C]

    WP06 assigned to Agent C.
    Worktree: .worktrees/021-billing-WP06/
    Status: doing

[... Agents work in parallel ...]

Agent A: WP02 is done and in review.

AI: [MCP server moves WP02 to for_review]

    WP02 moved to for_review.
    
    🔔 Notification: WP03 is now unblocked!
    
    Available for next agent:
    - WP03: Usage metering (depends on WP02 ✓)

Agent D: I'll take WP03.

AI: [MCP server creates WP03 worktree from WP02]

    WP03 assigned to Agent D.
    Worktree: .worktrees/021-billing-WP03/
    Branched from: 021-billing-WP02 (includes Agent A's Stripe code)
    Status: doing
    
    Note: WP04 (Billing engine) depends on both WP02 and WP03. Agent D,
    please coordinate with Agent A to ensure no conflicts.

[... All agents complete their WPs ...]

AI: [MCP server analyzes completion status]

    All work packages complete! 🎉
    
    Summary:
    - Agent A: WP02 (Stripe integration) ✓
    - Agent B: WP05 (Admin dashboard) ✓
    - Agent C: WP06 (Audit logging) ✓
    - Agent D: WP03 (Usage metering) ✓
    - Agent E: WP04 (Billing engine) ✓ (depended on A & D)
    - Agent F: WP01 (Database schema) ✓ (done first)
    
    Total time: 8 hours (parallel) vs. estimated 24 hours (sequential)
    Speedup: 3x 🚀
    
    Ready to merge?
```

**Coordination features**:
- Dependency-aware assignment recommendations
- Automatic blocking/unblocking notifications
- Conflict warnings for overlapping files
- Real-time progress tracking across agents

**MCP tools**:
- `task_operations` (query_status, move_task, add_history)
- `workspace_operations` (create_worktree, list_worktrees)
- Locking ensures no simultaneous moves to same lane

---

## Best Practices for Conversational Workflows

### 1. Be Explicit About Context

**Good**:
```
Show me features in /Users/me/projects/billing-service
```

**Bad**:
```
Show me features
[MCP server doesn't know which project]
```

---

### 2. Use Natural Language, Not Command Syntax

**Good**:
```
I'm starting work on WP01
Move WP01 to review when I'm done
```

**Bad**:
```
spec-kitty agent tasks move-task WP01 --to doing
[MCP server prefers conversational commands]
```

---

### 3. Ask for Explanations

**Good**:
```
Why is WP04 blocked?
[AI explains dependencies: waiting for WP02, WP03]

What files will conflict when I merge this?
[AI runs dry-run, forecasts conflicts]
```

---

### 4. Leverage Multi-Turn Conversations

**Good**:
```
Create a feature for X
[AI asks clarifying questions]
[You answer]
[AI generates spec]
Now create a plan
[AI generates plan from previous context]
```

**Bad**:
```
Create a feature for X with Y and Z requirements
[Too much info upfront, AI may miss nuances]
```

---

### 5. Use Conversational Checkpoints

**Good**:
```
Before I merge, check for conflicts
[AI runs preflight, forecasts issues]

Show me which tasks are ready
[AI analyzes dependencies]
```

---

## Troubleshooting Conversational Workflows

### Issue: AI misinterprets intent

**Solution**: Be more explicit
```
❌ "Do the thing with WP01"
✅ "Move WP01 to the doing lane"
✅ "Create a worktree for WP01"
```

---

### Issue: Conversation state lost

**Solution**: Check session persistence
```bash
ls -la .kittify/mcp-sessions/
# Sessions auto-saved every turn
# If missing, restart conversation
```

---

### Issue: Multi-project confusion

**Solution**: Always specify project path explicitly
```
✅ "In /Users/me/projects/app1, show features"
✅ "For the billing-service project, what's the status?"
```

---

## Next Steps

**You're ready to master conversational workflows!**

**Learn more**:
- [MCP Tool Reference](../reference/mcp-tools.md) - Complete list of available operations
- [MCP Server Architecture](../explanation/mcp-server-architecture.md) - How conversation state works
- [Troubleshooting](../how-to/troubleshoot-mcp.md) - Solutions to common issues

---

*Last updated: 2026-01-31*  
*Spec Kitty version: 0.14.0+*
