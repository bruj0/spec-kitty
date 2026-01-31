"""CLI adapter for MCP tool invocation."""

import logging
from functools import wraps
from pathlib import Path
from typing import List, Optional

from specify_cli.mcp.session.context import ProjectContext

from . import OperationResult

logger = logging.getLogger(__name__)


def handle_cli_errors(method):
    """Decorator to catch CLI exceptions and convert to OperationResult."""
    @wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception as e:
            # Log full exception for debugging
            logger.exception(f"CLI adapter error in {method.__name__}")
            
            # Return structured error
            return OperationResult.error_result(
                message=f"Operation failed: {str(e)}",
                errors=[
                    str(e),
                    f"Method: {method.__name__}",
                    "See logs for full traceback"
                ]
            )
    return wrapper


class CLIAdapter:
    """Wraps existing CLI modules for MCP tool invocation."""
    
    def __init__(self, project_context: ProjectContext):
        """Initialize adapter with project context."""
        self.project_context = project_context
        self.project_path = project_context.project_path
        self.kittify_dir = project_context.kittify_dir
    
    # ========================================================================
    # Feature operations (T022)
    # ========================================================================
    
    @handle_cli_errors
    def create_feature(self, slug: str, description: str) -> OperationResult:
        """
        Create new feature specification.
        
        NOTE: Core logic embedded in CLI command (feature.py::create_feature).
        This implementation extracts the essential logic.
        Future refactoring should extract into src/specify_cli/core/features.py
        """
        try:
            from specify_cli.core.worktree import get_next_feature_number
            
            # Get next feature number
            feature_number = get_next_feature_number(self.project_path)
            feature_slug_formatted = f"{feature_number:03d}-{slug}"
            
            # Create feature directory in main repo
            feature_dir = self.project_path / "kitty-specs" / feature_slug_formatted
            feature_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            (feature_dir / "checklists").mkdir(exist_ok=True)
            (feature_dir / "research").mkdir(exist_ok=True)
            tasks_dir = feature_dir / "tasks"
            tasks_dir.mkdir(exist_ok=True)
            (tasks_dir / ".gitkeep").touch()
            
            # Create spec.md placeholder
            spec_path = feature_dir / "spec.md"
            spec_path.write_text(
                f"# {feature_slug_formatted}\n\n{description}\n\n"
                "TODO: Add detailed specification\n"
            )
            
            return OperationResult.success_result(
                message=f"Feature {feature_slug_formatted} created successfully",
                data={
                    "feature_slug": feature_slug_formatted,
                    "feature_path": str(feature_dir),
                    "description": description
                },
                artifacts=[feature_dir]
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to create feature: {str(e)}",
                errors=[str(e)]
            )
    
    @handle_cli_errors
    def setup_plan(self, feature_slug: str) -> OperationResult:
        """
        Generate technical plan for feature.
        
        NOTE: Core logic embedded in CLI command (feature.py::setup_plan).
        This creates a minimal plan.md file.
        """
        try:
            feature_dir = self.project_context.get_feature_dir(feature_slug)
            plan_path = feature_dir / "plan.md"
            
            if not feature_dir.exists():
                raise FileNotFoundError(f"Feature directory not found: {feature_dir}")
            
            # Create minimal plan template
            plan_path.write_text(
                f"# Technical Plan: {feature_slug}\n\n"
                "## Overview\n\nTODO: Add technical design\n\n"
                "## Architecture\n\nTODO: Add architecture details\n\n"
                "## Implementation Strategy\n\nTODO: Add implementation plan\n"
            )
            
            return OperationResult.success_result(
                message=f"Plan created for {feature_slug}",
                data={
                    "feature_slug": feature_slug,
                    "plan_path": str(plan_path)
                },
                artifacts=[plan_path]
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to create plan: {str(e)}",
                errors=[str(e)]
            )
    
    @handle_cli_errors
    def create_tasks(self, feature_slug: str) -> OperationResult:
        """
        Generate work package breakdown.
        
        NOTE: Core logic embedded in CLI command (feature.py).
        This creates minimal tasks.md structure.
        """
        try:
            feature_dir = self.project_context.get_feature_dir(feature_slug)
            tasks_file = feature_dir / "tasks.md"
            tasks_dir = feature_dir / "tasks"
            
            if not feature_dir.exists():
                raise FileNotFoundError(f"Feature directory not found: {feature_dir}")
            
            # Ensure tasks directory exists
            tasks_dir.mkdir(exist_ok=True)
            
            # Create minimal tasks.md
            tasks_file.write_text(
                f"# Tasks: {feature_slug}\n\n"
                "## Work Packages\n\nTODO: Add work package breakdown\n"
            )
            
            return OperationResult.success_result(
                message=f"Tasks created for {feature_slug}",
                data={
                    "feature_slug": feature_slug,
                    "tasks_file": str(tasks_file),
                    "tasks_dir": str(tasks_dir)
                },
                artifacts=[tasks_file, tasks_dir]
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to create tasks: {str(e)}",
                errors=[str(e)]
            )
    
    # ========================================================================
    # Task operations (T023)
    # ========================================================================
    
    @handle_cli_errors
    def list_tasks(
        self,
        feature_slug: str,
        lane: Optional[str] = None
    ) -> OperationResult:
        """List tasks for feature, optionally filtered by lane."""
        try:
            from specify_cli.tasks_support import split_frontmatter, extract_scalar
            
            feature_dir = self.project_context.get_feature_dir(feature_slug)
            tasks_dir = feature_dir / "tasks"
            
            if not tasks_dir.exists():
                return OperationResult.error_result(
                    message=f"Tasks directory not found: {tasks_dir}",
                    errors=[f"Directory does not exist: {tasks_dir}"]
                )
            
            tasks = []
            for task_file in tasks_dir.glob("WP*.md"):
                if task_file.name.lower() == "readme.md":
                    continue
                
                content = task_file.read_text(encoding="utf-8-sig")
                frontmatter, _, _ = split_frontmatter(content)
                
                task_lane = extract_scalar(frontmatter, "lane") or "planned"
                task_wp_id = extract_scalar(frontmatter, "work_package_id") or task_file.stem
                task_title = extract_scalar(frontmatter, "title") or ""
                
                # Filter by lane if specified
                if lane and task_lane != lane:
                    continue
                
                tasks.append({
                    "work_package_id": task_wp_id,
                    "title": task_title,
                    "lane": task_lane,
                    "path": str(task_file)
                })
            
            # Sort by work package ID
            tasks.sort(key=lambda t: t["work_package_id"])
            
            return OperationResult.success_result(
                message=f"Found {len(tasks)} tasks for {feature_slug}",
                data={
                    "feature_slug": feature_slug,
                    "tasks": tasks,
                    "lane_filter": lane
                }
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to list tasks: {str(e)}",
                errors=[str(e)]
            )
    
    @handle_cli_errors
    def move_task(
        self,
        feature_slug: str,
        task_id: str,
        lane: str,
        note: Optional[str] = None
    ) -> OperationResult:
        """
        Move task between lanes.
        
        NOTE: Full logic in CLI command (tasks.py::move_task).
        This is a simplified implementation.
        For production, extract logic to src/specify_cli/core/tasks.py
        """
        try:
            from specify_cli.tasks_support import split_frontmatter
            from ruamel.yaml import YAML
            from datetime import datetime, timezone
            
            feature_dir = self.project_context.get_feature_dir(feature_slug)
            tasks_dir = feature_dir / "tasks"
            
            # Find task file
            task_file = None
            for f in tasks_dir.glob("WP*.md"):
                if task_id in f.stem:
                    task_file = f
                    break
            
            if not task_file:
                return OperationResult.error_result(
                    message=f"Task {task_id} not found",
                    errors=[f"No file matching {task_id} in {tasks_dir}"]
                )
            
            # Read and parse frontmatter
            content = task_file.read_text(encoding="utf-8-sig")
            frontmatter_str, sep, body = split_frontmatter(content)
            
            # Parse YAML
            yaml = YAML()
            yaml.preserve_quotes = True
            frontmatter = yaml.load(frontmatter_str)
            
            # Update lane
            old_lane = frontmatter.get("lane", "planned")
            frontmatter["lane"] = lane
            
            # Add history entry
            if "history" not in frontmatter:
                frontmatter["history"] = []
            
            history_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "lane": lane,
                "agent": "mcp-adapter",
                "shell_pid": "",
                "action": note or f"Moved from {old_lane} to {lane}"
            }
            frontmatter["history"].append(history_entry)
            
            # Write back
            import io
            stream = io.StringIO()
            yaml.dump(frontmatter, stream)
            new_frontmatter = stream.getvalue()
            
            new_content = f"---\n{new_frontmatter}---\n{body}"
            task_file.write_text(new_content, encoding="utf-8")
            
            return OperationResult.success_result(
                message=f"Task {task_id} moved to {lane}",
                data={
                    "feature_slug": feature_slug,
                    "task_id": task_id,
                    "old_lane": old_lane,
                    "new_lane": lane,
                    "note": note
                }
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to move task: {str(e)}",
                errors=[str(e)]
            )
    
    @handle_cli_errors
    def add_history(
        self,
        feature_slug: str,
        task_id: str,
        note: str
    ) -> OperationResult:
        """Add history entry to task."""
        try:
            from specify_cli.tasks_support import split_frontmatter
            from ruamel.yaml import YAML
            from datetime import datetime, timezone
            
            feature_dir = self.project_context.get_feature_dir(feature_slug)
            tasks_dir = feature_dir / "tasks"
            
            # Find task file
            task_file = None
            for f in tasks_dir.glob("WP*.md"):
                if task_id in f.stem:
                    task_file = f
                    break
            
            if not task_file:
                return OperationResult.error_result(
                    message=f"Task {task_id} not found",
                    errors=[f"No file matching {task_id} in {tasks_dir}"]
                )
            
            # Read and parse frontmatter
            content = task_file.read_text(encoding="utf-8-sig")
            frontmatter_str, sep, body = split_frontmatter(content)
            
            # Parse YAML
            yaml = YAML()
            yaml.preserve_quotes = True
            frontmatter = yaml.load(frontmatter_str)
            
            # Add history entry
            if "history" not in frontmatter:
                frontmatter["history"] = []
            
            history_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "lane": frontmatter.get("lane", "planned"),
                "agent": "mcp-adapter",
                "shell_pid": "",
                "action": note
            }
            frontmatter["history"].append(history_entry)
            
            # Write back
            import io
            stream = io.StringIO()
            yaml.dump(frontmatter, stream)
            new_frontmatter = stream.getvalue()
            
            new_content = f"---\n{new_frontmatter}---\n{body}"
            task_file.write_text(new_content, encoding="utf-8")
            
            return OperationResult.success_result(
                message=f"History added to {task_id}",
                data={
                    "feature_slug": feature_slug,
                    "task_id": task_id,
                    "note": note
                }
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to add history: {str(e)}",
                errors=[str(e)]
            )
    
    @handle_cli_errors
    def mark_subtask_status(
        self,
        feature_slug: str,
        task_id: str,
        subtask_ids: List[str],
        status: str
    ) -> OperationResult:
        """
        Mark subtasks with status (done/blocked/etc).
        
        NOTE: Full implementation would update frontmatter subtask status.
        This is a placeholder for now.
        """
        try:
            return OperationResult.success_result(
                message=f"Marked {len(subtask_ids)} subtasks as {status}",
                data={
                    "feature_slug": feature_slug,
                    "task_id": task_id,
                    "subtask_ids": subtask_ids,
                    "status": status
                },
                warnings=["Subtask status marking not fully implemented yet"]
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to mark subtasks: {str(e)}",
                errors=[str(e)]
            )
    
    # ========================================================================
    # Workspace operations (T024)
    # ========================================================================
    
    @handle_cli_errors
    def create_worktree(
        self,
        feature_slug: str,
        wp_id: str,
        base_wp: Optional[str] = None
    ) -> OperationResult:
        """
        Create git worktree for work package.
        
        NOTE: The full WP worktree creation logic is complex (see implement.py).
        This is a simplified implementation.
        For full support with dependency tracking, use the CLI command.
        """
        try:
            import subprocess
            
            # Generate branch name: feature-slug-WPID
            branch_name = f"{feature_slug}-{wp_id}"
            if base_wp:
                base_branch = f"{feature_slug}-{base_wp}"
            else:
                base_branch = "main"
            
            # Worktree path
            worktree_path = self.project_path / ".worktrees" / branch_name
            worktree_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create worktree
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), "-b", branch_name, base_branch],
                cwd=self.project_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            return OperationResult.success_result(
                message=f"Worktree created for {wp_id}",
                data={
                    "wp_id": wp_id,
                    "worktree_path": str(worktree_path),
                    "branch_name": branch_name,
                    "base_branch": base_branch if base_wp else "main"
                },
                artifacts=[worktree_path],
                warnings=["This is a simplified worktree creation. Use CLI for full dependency tracking."]
            )
        except subprocess.CalledProcessError as e:
            return OperationResult.error_result(
                message=f"Failed to create worktree: {e.stderr}",
                errors=[e.stderr or str(e)]
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to create worktree: {str(e)}",
                errors=[str(e)]
            )
    
    @handle_cli_errors
    def list_worktrees(self) -> OperationResult:
        """List all active worktrees."""
        try:
            worktrees_dir = self.project_path / ".worktrees"
            
            if not worktrees_dir.exists():
                return OperationResult.success_result(
                    message="No worktrees found",
                    data={"worktrees": []}
                )
            
            worktrees = []
            for d in worktrees_dir.iterdir():
                if d.is_dir() and not d.name.startswith("."):
                    # Check if it's a valid worktree
                    git_file = d / ".git"
                    if git_file.exists():
                        worktrees.append({
                            "name": d.name,
                            "path": str(d)
                        })
            
            return OperationResult.success_result(
                message=f"Found {len(worktrees)} worktrees",
                data={"worktrees": worktrees}
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to list worktrees: {str(e)}",
                errors=[str(e)]
            )
    
    # ========================================================================
    # System operations (T025)
    # ========================================================================
    
    @handle_cli_errors
    def validate_project(self) -> OperationResult:
        """Validate project structure."""
        try:
            # ProjectContext already validates on construction
            # Additional checks can be added here
            errors = []
            
            # Check kitty-specs directory exists
            specs_dir = self.project_path / "kitty-specs"
            if not specs_dir.exists():
                errors.append("Missing kitty-specs/ directory")
            
            # Check .kittify/missions exists
            missions_dir = self.kittify_dir / "missions"
            if not missions_dir.exists():
                errors.append("Missing .kittify/missions/ directory")
            
            if errors:
                return OperationResult.error_result(
                    message="Project validation failed",
                    errors=errors
                )
            
            return OperationResult.success_result(
                message="Project structure is valid"
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Validation error: {str(e)}",
                errors=[str(e)]
            )
    
    @handle_cli_errors
    def get_missions(self) -> OperationResult:
        """List available missions."""
        try:
            missions_dir = self.kittify_dir / "missions"
            
            if not missions_dir.exists():
                return OperationResult.success_result(
                    message="No missions configured",
                    data={"missions": []}
                )
            
            missions = [
                d.name for d in missions_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
            
            return OperationResult.success_result(
                message=f"Found {len(missions)} missions",
                data={"missions": missions}
            )
        except Exception as e:
            return OperationResult.error_result(
                message=f"Failed to list missions: {str(e)}",
                errors=[str(e)]
            )
