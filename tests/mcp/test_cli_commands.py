"""
Tests for MCP CLI commands (start, status, stop).

Tests cover:
- spec-kitty mcp start command with various options
- spec-kitty mcp status command
- spec-kitty mcp stop command
- Configuration loading and override precedence
- PID file management during server lifecycle
- Error handling (port conflicts, missing PID, etc.)
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.mcp import app
from specify_cli.mcp.config import MCPConfig, PIDFileManager

runner = CliRunner()


class TestMCPStartCommand:
    """Test `spec-kitty mcp start` command."""
    
    @patch("specify_cli.cli.commands.mcp.MCPServer")
    def test_start_default(self, mock_server_class, tmp_path, monkeypatch):
        """Test starting server with default options."""
        # Setup project directory
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".kittify").mkdir()
        
        monkeypatch.chdir(project_path)
        
        # Mock server start method
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        result = runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        assert "Starting MCP server" in result.stdout
        assert "Transport: stdio" in result.stdout
        mock_server.start.assert_called_once()
    
    @patch("specify_cli.cli.commands.mcp.MCPServer")
    def test_start_with_sse_transport(self, mock_server_class, tmp_path, monkeypatch):
        """Test starting server with SSE transport."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".kittify").mkdir()
        
        monkeypatch.chdir(project_path)
        
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        result = runner.invoke(app, ["start", "--transport", "sse", "--host", "0.0.0.0", "--port", "9000"])
        
        assert result.exit_code == 0
        assert "Transport: sse" in result.stdout
        assert "Listening on 0.0.0.0:9000" in result.stdout
        
        # Verify server created with correct config
        mock_server_class.assert_called_once()
        args, kwargs = mock_server_class.call_args
        assert kwargs.get("host") == "0.0.0.0" or args[0] == "0.0.0.0"
        assert kwargs.get("port") == 9000 or args[1] == 9000
        assert kwargs.get("transport") == "sse" or args[2] == "sse"
    
    @patch("specify_cli.cli.commands.mcp.MCPServer")
    def test_start_with_auth(self, mock_server_class, tmp_path, monkeypatch):
        """Test starting server with authentication enabled."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".kittify").mkdir()
        
        monkeypatch.chdir(project_path)
        
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        result = runner.invoke(app, ["start", "--auth", "--api-key", "secret123"])
        
        assert result.exit_code == 0
        assert "Authentication enabled" in result.stdout
        
        # Verify server created with auth config
        mock_server_class.assert_called_once()
        call_kwargs = mock_server_class.call_args.kwargs
        assert call_kwargs["auth_enabled"] is True
        assert call_kwargs["api_key"] == "secret123"
    
    @patch("specify_cli.cli.commands.mcp.MCPServer")
    def test_start_loads_config_file(self, mock_server_class, tmp_path, monkeypatch):
        """Test that start command loads config from .kittify/mcp-config.yaml."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # Create config file
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "10.0.0.1"
port: 7000
transport: "sse"
""")
        
        monkeypatch.chdir(project_path)
        
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        result = runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        
        # Verify config file values used
        call_kwargs = mock_server_class.call_args.kwargs
        assert call_kwargs["host"] == "10.0.0.1"
        assert call_kwargs["port"] == 7000
        assert call_kwargs["transport"] == "sse"
    
    @patch("specify_cli.cli.commands.mcp.MCPServer")
    def test_start_cli_overrides_config_file(self, mock_server_class, tmp_path, monkeypatch):
        """Test that CLI options override config file values."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # Create config file
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "10.0.0.1"
port: 7000
transport: "sse"
""")
        
        monkeypatch.chdir(project_path)
        
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        result = runner.invoke(app, ["start", "--transport", "stdio"])
        
        assert result.exit_code == 0
        
        # Verify CLI option overrides config file
        call_kwargs = mock_server_class.call_args.kwargs
        assert call_kwargs["transport"] == "stdio"  # CLI override
        assert call_kwargs["host"] == "10.0.0.1"  # From config file
    
    def test_start_duplicate_server_error(self, tmp_path, monkeypatch):
        """Test error when trying to start server that's already running."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # Write PID file for "running" server (use current process as fake server)
        pid_file = kittify_dir / ".mcp-server.pid"
        pid_file.write_text(str(os.getpid()))
        
        monkeypatch.chdir(project_path)
        
        result = runner.invoke(app, ["start"])
        
        assert result.exit_code == 1
        assert "already running" in result.stdout.lower()
    
    @patch("specify_cli.cli.commands.mcp.MCPServer")
    def test_start_cleanup_on_error(self, mock_server_class, tmp_path, monkeypatch):
        """Test PID file is cleaned up if server fails to start."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        monkeypatch.chdir(project_path)
        
        # Mock server start to raise error
        mock_server = MagicMock()
        mock_server.start.side_effect = RuntimeError("Port unavailable")
        mock_server_class.return_value = mock_server
        
        pid_file = kittify_dir / ".mcp-server.pid"
        
        result = runner.invoke(app, ["start"])
        
        assert result.exit_code == 1
        assert "Error starting server" in result.stdout
        # PID file should be cleaned up
        assert not pid_file.exists()


class TestMCPStatusCommand:
    """Test `spec-kitty mcp status` command."""
    
    def test_status_server_running(self, tmp_path, monkeypatch):
        """Test status when server is running."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # Write PID file for "running" server (use current process)
        pid_file = kittify_dir / ".mcp-server.pid"
        pid_file.write_text(str(os.getpid()))
        
        # Create config file
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "127.0.0.1"
port: 8000
transport: "stdio"
""")
        
        monkeypatch.chdir(project_path)
        
        result = runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        assert "Running" in result.stdout
        assert str(os.getpid()) in result.stdout
        assert "Transport" in result.stdout
    
    def test_status_server_not_running(self, tmp_path, monkeypatch):
        """Test status when server is not running."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # No PID file (server not running)
        
        # Create config file
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "127.0.0.1"
port: 8000
transport: "stdio"
""")
        
        monkeypatch.chdir(project_path)
        
        result = runner.invoke(app, ["status"])
        
        assert result.exit_code == 1
        assert "Not running" in result.stdout
    
    def test_status_stale_pid_file(self, tmp_path, monkeypatch):
        """Test status when PID file is stale (process not running)."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # Write stale PID file
        pid_file = kittify_dir / ".mcp-server.pid"
        pid_file.write_text("999999")  # Nonexistent PID
        
        # Create config file
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "127.0.0.1"
port: 8000
transport: "stdio"
""")
        
        monkeypatch.chdir(project_path)
        
        result = runner.invoke(app, ["status"])
        
        assert result.exit_code == 1
        assert "Not running" in result.stdout


class TestMCPStopCommand:
    """Test `spec-kitty mcp stop` command."""
    
    def test_stop_server_success(self, tmp_path, monkeypatch):
        """Test stopping a running server."""
        import subprocess
        
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # Start a dummy process
        proc = subprocess.Popen(["sleep", "30"])
        
        # Write PID file
        pid_file = kittify_dir / ".mcp-server.pid"
        pid_file.write_text(str(proc.pid))
        
        # Create config file
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "127.0.0.1"
port: 8000
transport: "stdio"
""")
        
        monkeypatch.chdir(project_path)
        
        try:
            result = runner.invoke(app, ["stop"])
            
            assert result.exit_code == 0
            assert "stopped successfully" in result.stdout.lower()
            assert not pid_file.exists()
        finally:
            # Cleanup
            try:
                proc.kill()
            except:
                pass
    
    def test_stop_server_not_running(self, tmp_path, monkeypatch):
        """Test stopping when server is not running."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # No PID file
        
        # Create config file
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "127.0.0.1"
port: 8000
transport: "stdio"
""")
        
        monkeypatch.chdir(project_path)
        
        result = runner.invoke(app, ["stop"])
        
        assert result.exit_code == 1
        assert "No MCP server running" in result.stdout
    
    def test_stop_server_stale_pid(self, tmp_path, monkeypatch):
        """Test stopping when PID file is stale (process not running)."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # Write stale PID file
        pid_file = kittify_dir / ".mcp-server.pid"
        pid_file.write_text("999999")  # Nonexistent PID
        
        # Create config file
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "127.0.0.1"
port: 8000
transport: "stdio"
""")
        
        monkeypatch.chdir(project_path)
        
        result = runner.invoke(app, ["stop"])
        
        assert result.exit_code == 1
        assert "is not running" in result.stdout
        # Stale PID file should be cleaned up
        assert not pid_file.exists()


class TestMCPCommandIntegration:
    """Integration tests for MCP commands."""
    
    @patch("specify_cli.cli.commands.mcp.MCPServer")
    def test_full_lifecycle(self, mock_server_class, tmp_path, monkeypatch):
        """Test complete server lifecycle: start → status → stop."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        monkeypatch.chdir(project_path)
        
        # Mock server
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        # Start server
        result_start = runner.invoke(app, ["start"])
        assert result_start.exit_code == 0
        assert "Starting MCP server" in result_start.stdout
        
        # Check status
        result_status = runner.invoke(app, ["status"])
        assert result_status.exit_code == 0
        assert "Running" in result_status.stdout
        
        # Stop server (note: in real scenario, server would be running in separate process)
        # For testing, we'll manually clean up PID file
        pid_file = kittify_dir / ".mcp-server.pid"
        if pid_file.exists():
            pid_file.unlink()
        
        result_status_after = runner.invoke(app, ["status"])
        assert result_status_after.exit_code == 1
        assert "Not running" in result_status_after.stdout
