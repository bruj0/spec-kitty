"""Project context management for Spec Kitty MCP server."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ProjectContext:
    """Represents a single Spec Kitty project managed by MCP server."""
    
    project_path: Path
    kittify_dir: Path
    session_dir: Path
    lock_dir: Path
    config: Dict[str, Any]
    active_feature: Optional[str] = None
    mission: Optional[str] = None
    
    def __post_init__(self):
        """Validate paths are absolute."""
        if not self.project_path.is_absolute():
            raise ValueError(f"project_path must be absolute: {self.project_path}")
    
    @classmethod
    def from_path(cls, project_path: Path) -> "ProjectContext":
        """
        Create ProjectContext from project root path with validation.
        
        Args:
            project_path: Path to project root directory
            
        Returns:
            ProjectContext instance
            
        Raises:
            ValueError: If validation fails (missing .kittify/, config.yaml, etc.)
        """
        project_path = project_path.resolve()  # Convert to absolute
        kittify_dir = project_path / ".kittify"
        
        # Validation checklist (T008)
        _validate_project_structure(project_path, kittify_dir)
        
        # Load config
        config_file = kittify_dir / "config.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}
        
        session_dir = kittify_dir / "mcp-sessions"
        lock_dir = kittify_dir  # Locks stored directly in .kittify/
        
        # Create session_dir if needed (T009)
        session_dir.mkdir(exist_ok=True)
        
        return cls(
            project_path=project_path,
            kittify_dir=kittify_dir,
            session_dir=session_dir,
            lock_dir=lock_dir,
            config=config
        )
    
    def get_feature_dir(self, feature_slug: str) -> Path:
        """
        Get path to feature directory.
        
        Args:
            feature_slug: Feature identifier (e.g., "001-my-feature")
            
        Returns:
            Path to feature directory in kitty-specs/
        """
        return self.project_path / "kitty-specs" / feature_slug
    
    def list_features(self) -> List[str]:
        """
        List all feature slugs in kitty-specs/ directory.
        
        Returns:
            List of feature directory names, sorted alphabetically
        """
        specs_dir = self.project_path / "kitty-specs"
        if not specs_dir.exists():
            return []
        
        return sorted([
            d.name for d in specs_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])
    
    def get_active_feature(self) -> Optional[str]:
        """
        Detect active feature from git branch or metadata.
        
        Returns:
            Feature slug if detected, None otherwise
        """
        # Simple implementation: check current git branch
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            
            # Feature branches typically: NNN-feature-name or NNN-feature-name-WPNN
            if branch and branch[0].isdigit():
                # Extract feature slug (first 3 parts if WP suffix present)
                parts = branch.split("-")
                if len(parts) >= 2:
                    # Check if last part is WPNN
                    if parts[-1].startswith("WP"):
                        # Reconstruct without WP suffix
                        return "-".join(parts[:-1])
                    else:
                        return branch
            
            return None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None


def _validate_project_structure(project_path: Path, kittify_dir: Path):
    """
    Validate that project has required Spec Kitty structure (T008).
    
    Args:
        project_path: Path to project root
        kittify_dir: Path to .kittify directory
        
    Raises:
        ValueError: If validation fails with actionable error message
    """
    # Check 1: .kittify/ directory exists
    if not kittify_dir.exists():
        raise ValueError(
            f"Not a Spec Kitty project: {project_path}\n"
            f"Missing .kittify/ directory.\n"
            f"Initialize with: spec-kitty init"
        )
    
    # Check 2: config.yaml exists
    config_file = kittify_dir / "config.yaml"
    if not config_file.exists():
        raise ValueError(
            f"Invalid Spec Kitty project: {project_path}\n"
            f"Missing .kittify/config.yaml.\n"
            f"Re-initialize with: spec-kitty init"
        )
    
    # Check 3: missions/ directory exists
    missions_dir = kittify_dir / "missions"
    if not missions_dir.exists():
        raise ValueError(
            f"Invalid Spec Kitty project: {project_path}\n"
            f"Missing .kittify/missions/ directory.\n"
            f"Re-initialize with: spec-kitty init"
        )
    
    # Check 4: config.yaml is valid YAML
    try:
        with open(config_file) as f:
            config = yaml.safe_load(f)
            if config is None:
                raise ValueError("Empty config.yaml")
    except yaml.YAMLError as e:
        raise ValueError(
            f"Invalid Spec Kitty project: {project_path}\n"
            f"Corrupt .kittify/config.yaml: {e}\n"
            f"Fix the YAML syntax or re-initialize with: spec-kitty init"
        )
    except Exception as e:
        raise ValueError(
            f"Invalid Spec Kitty project: {project_path}\n"
            f"Cannot read .kittify/config.yaml: {e}"
        )
