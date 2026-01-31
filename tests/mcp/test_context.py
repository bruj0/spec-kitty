"""Tests for ProjectContext."""

import subprocess
from pathlib import Path

import pytest
import yaml

from specify_cli.mcp.session.context import ProjectContext


@pytest.fixture
def valid_project(tmp_path):
    """Create a valid Spec Kitty project structure."""
    project_path = tmp_path / "valid-project"
    project_path.mkdir()
    
    # Create .kittify/ structure
    kittify_dir = project_path / ".kittify"
    kittify_dir.mkdir()
    
    (kittify_dir / "missions").mkdir()
    
    config_file = kittify_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "project_name": "test-project",
        "mission": "software-dev",
        "version": "0.13.0"
    }))
    
    # Create kitty-specs/ with features
    specs_dir = project_path / "kitty-specs"
    specs_dir.mkdir()
    
    (specs_dir / "001-feature-one").mkdir()
    (specs_dir / "002-feature-two").mkdir()
    
    return project_path


def test_project_context_creation(valid_project):
    """Test that ProjectContext can be created from valid project."""
    ctx = ProjectContext.from_path(valid_project)
    
    assert ctx.project_path == valid_project.resolve()
    assert ctx.kittify_dir == valid_project / ".kittify"
    assert ctx.session_dir == valid_project / ".kittify" / "mcp-sessions"
    assert ctx.lock_dir == valid_project / ".kittify"
    assert ctx.config["project_name"] == "test-project"


def test_project_context_creates_session_dir(valid_project):
    """Test that ProjectContext creates mcp-sessions/ directory if missing."""
    session_dir = valid_project / ".kittify" / "mcp-sessions"
    
    assert not session_dir.exists()
    
    ctx = ProjectContext.from_path(valid_project)
    
    assert session_dir.exists()
    assert session_dir.is_dir()


def test_project_context_rejects_relative_path(valid_project):
    """Test that ProjectContext validates absolute paths."""
    # from_path() converts to absolute, so test __post_init__ directly
    with pytest.raises(ValueError, match="must be absolute"):
        ProjectContext(
            project_path=Path("relative/path"),
            kittify_dir=Path(".kittify"),
            session_dir=Path(".kittify/mcp-sessions"),
            lock_dir=Path(".kittify"),
            config={}
        )


def test_project_context_missing_kittify(tmp_path):
    """Test that ProjectContext rejects project without .kittify/."""
    project_path = tmp_path / "no-kittify"
    project_path.mkdir()
    
    with pytest.raises(ValueError, match="Not a Spec Kitty project"):
        ProjectContext.from_path(project_path)


def test_project_context_missing_config(tmp_path):
    """Test that ProjectContext rejects project without config.yaml."""
    project_path = tmp_path / "no-config"
    project_path.mkdir()
    (project_path / ".kittify").mkdir()
    (project_path / ".kittify" / "missions").mkdir()
    
    with pytest.raises(ValueError, match="Missing .kittify/config.yaml"):
        ProjectContext.from_path(project_path)


def test_project_context_missing_missions(tmp_path):
    """Test that ProjectContext rejects project without missions/."""
    project_path = tmp_path / "no-missions"
    project_path.mkdir()
    kittify_dir = project_path / ".kittify"
    kittify_dir.mkdir()
    
    config_file = kittify_dir / "config.yaml"
    config_file.write_text("project_name: test\n")
    
    with pytest.raises(ValueError, match="Missing .kittify/missions/"):
        ProjectContext.from_path(project_path)


def test_project_context_corrupt_config(tmp_path):
    """Test that ProjectContext handles corrupt config.yaml."""
    project_path = tmp_path / "corrupt-config"
    project_path.mkdir()
    kittify_dir = project_path / ".kittify"
    kittify_dir.mkdir()
    (kittify_dir / "missions").mkdir()
    
    # Write invalid YAML
    config_file = kittify_dir / "config.yaml"
    config_file.write_text("invalid: yaml: syntax: error:")
    
    with pytest.raises(ValueError, match="Corrupt .kittify/config.yaml"):
        ProjectContext.from_path(project_path)


def test_project_context_list_features(valid_project):
    """Test that ProjectContext lists features correctly."""
    ctx = ProjectContext.from_path(valid_project)
    
    features = ctx.list_features()
    
    assert features == ["001-feature-one", "002-feature-two"]


def test_project_context_list_features_empty(valid_project):
    """Test that ProjectContext handles missing kitty-specs/ directory."""
    # Remove kitty-specs/
    import shutil
    shutil.rmtree(valid_project / "kitty-specs")
    
    ctx = ProjectContext.from_path(valid_project)
    
    features = ctx.list_features()
    
    assert features == []


def test_project_context_get_feature_dir(valid_project):
    """Test that ProjectContext returns correct feature directory path."""
    ctx = ProjectContext.from_path(valid_project)
    
    feature_dir = ctx.get_feature_dir("001-feature-one")
    
    assert feature_dir == valid_project / "kitty-specs" / "001-feature-one"


def test_project_context_get_active_feature_from_branch(valid_project, monkeypatch):
    """Test that ProjectContext detects active feature from git branch."""
    # Mock git command
    def mock_run(*args, **kwargs):
        class Result:
            stdout = "042-my-feature\n"
            returncode = 0
        return Result()
    
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    ctx = ProjectContext.from_path(valid_project)
    
    active = ctx.get_active_feature()
    
    assert active == "042-my-feature"


def test_project_context_get_active_feature_from_wp_branch(valid_project, monkeypatch):
    """Test that ProjectContext extracts feature from WP branch."""
    # Mock git command to return WP branch
    def mock_run(*args, **kwargs):
        class Result:
            stdout = "042-my-feature-WP01\n"
            returncode = 0
        return Result()
    
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    ctx = ProjectContext.from_path(valid_project)
    
    active = ctx.get_active_feature()
    
    # Should extract feature slug without WP suffix
    assert active == "042-my-feature"


def test_project_context_get_active_feature_main_branch(valid_project, monkeypatch):
    """Test that ProjectContext returns None on main branch."""
    # Mock git command to return main branch
    def mock_run(*args, **kwargs):
        class Result:
            stdout = "main\n"
            returncode = 0
        return Result()
    
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    ctx = ProjectContext.from_path(valid_project)
    
    active = ctx.get_active_feature()
    
    assert active is None


def test_project_context_get_active_feature_git_error(valid_project, monkeypatch):
    """Test that ProjectContext handles git errors gracefully."""
    # Mock git command to fail
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "git")
    
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    ctx = ProjectContext.from_path(valid_project)
    
    active = ctx.get_active_feature()
    
    assert active is None
