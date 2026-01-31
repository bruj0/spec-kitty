"""
Tests for MCP server configuration and PID file management.

Tests cover:
- Configuration loading from file and environment variables
- PID file creation, reading, and removal
- Process existence checking
- Server lifecycle (start, status, stop)
- Stale PID file cleanup
"""

import os
import signal
import time
from pathlib import Path

import pytest

from specify_cli.mcp.config import MCPConfig, PIDFileManager


class TestMCPConfig:
    """Test MCP configuration loading and saving."""
    
    def test_default_config(self, tmp_path):
        """Test default configuration values."""
        config = MCPConfig()
        
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.transport == "stdio"
        assert config.auth_enabled is False
        assert config.api_key is None
        assert config.pid_file is None
    
    def test_load_config_file_not_exists(self, tmp_path):
        """Test loading config when file doesn't exist (uses defaults)."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".kittify").mkdir()
        
        config = MCPConfig.load(project_path)
        
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.transport == "stdio"
        assert config.auth_enabled is False
        assert config.pid_file == project_path / ".kittify" / ".mcp-server.pid"
    
    def test_load_config_from_file(self, tmp_path):
        """Test loading configuration from .kittify/mcp-config.yaml."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "0.0.0.0"
port: 9000
transport: "sse"
auth_enabled: true
""")
        
        config = MCPConfig.load(project_path)
        
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.transport == "sse"
        assert config.auth_enabled is True
    
    def test_env_vars_override_config_file(self, tmp_path, monkeypatch):
        """Test environment variables override config file values."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "127.0.0.1"
port: 8000
transport: "stdio"
""")
        
        monkeypatch.setenv("MCP_SERVER_HOST", "192.168.1.1")
        monkeypatch.setenv("MCP_SERVER_PORT", "7000")
        monkeypatch.setenv("MCP_SERVER_TRANSPORT", "sse")
        
        config = MCPConfig.load(project_path)
        
        assert config.host == "192.168.1.1"
        assert config.port == 7000
        assert config.transport == "sse"
    
    def test_invalid_port_env_var(self, tmp_path, monkeypatch):
        """Test error handling for invalid port environment variable."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".kittify").mkdir()
        
        monkeypatch.setenv("MCP_SERVER_PORT", "not-a-number")
        
        with pytest.raises(ValueError, match="Invalid MCP_SERVER_PORT"):
            MCPConfig.load(project_path)
    
    def test_save_config(self, tmp_path):
        """Test saving configuration to file."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".kittify").mkdir()
        
        config = MCPConfig(
            host="10.0.0.1",
            port=5000,
            transport="sse",
            auth_enabled=True,
            api_key="secret123",  # Should NOT be saved
        )
        
        config.save(project_path)
        
        # Load saved config
        loaded_config = MCPConfig.load(project_path)
        
        assert loaded_config.host == "10.0.0.1"
        assert loaded_config.port == 5000
        assert loaded_config.transport == "sse"
        assert loaded_config.auth_enabled is True
        assert loaded_config.api_key is None  # API key not saved


class TestPIDFileManager:
    """Test PID file management for server lifecycle."""
    
    def test_write_pid_file(self, tmp_path):
        """Test writing PID file."""
        pid_file = tmp_path / ".mcp-server.pid"
        manager = PIDFileManager(pid_file)
        
        manager.write()
        
        assert pid_file.exists()
        assert pid_file.read_text() == str(os.getpid())
    
    def test_write_when_file_exists_stale(self, tmp_path):
        """Test writing PID file when existing PID is stale (process not running)."""
        pid_file = tmp_path / ".mcp-server.pid"
        
        # Write fake stale PID (999999 unlikely to be running)
        pid_file.write_text("999999")
        
        manager = PIDFileManager(pid_file)
        manager.write()
        
        # Should overwrite stale PID
        assert pid_file.read_text() == str(os.getpid())
    
    def test_write_when_file_exists_running(self, tmp_path):
        """Test error when trying to write PID file for running process."""
        pid_file = tmp_path / ".mcp-server.pid"
        
        # Write current process PID (guaranteed to be running)
        pid_file.write_text(str(os.getpid()))
        
        manager = PIDFileManager(pid_file)
        
        with pytest.raises(RuntimeError, match="MCP server already running"):
            manager.write()
    
    def test_read_pid_file(self, tmp_path):
        """Test reading PID from file."""
        pid_file = tmp_path / ".mcp-server.pid"
        pid_file.write_text("12345")
        
        manager = PIDFileManager(pid_file)
        pid = manager.read()
        
        assert pid == 12345
    
    def test_read_pid_file_not_exists(self, tmp_path):
        """Test reading PID when file doesn't exist."""
        pid_file = tmp_path / ".mcp-server.pid"
        manager = PIDFileManager(pid_file)
        
        pid = manager.read()
        
        assert pid is None
    
    def test_read_invalid_pid_file(self, tmp_path):
        """Test reading invalid PID file (non-numeric content)."""
        pid_file = tmp_path / ".mcp-server.pid"
        pid_file.write_text("not-a-number")
        
        manager = PIDFileManager(pid_file)
        pid = manager.read()
        
        assert pid is None
    
    def test_remove_pid_file(self, tmp_path):
        """Test removing PID file."""
        pid_file = tmp_path / ".mcp-server.pid"
        pid_file.write_text("12345")
        
        manager = PIDFileManager(pid_file)
        manager.remove()
        
        assert not pid_file.exists()
    
    def test_remove_pid_file_not_exists(self, tmp_path):
        """Test removing PID file when it doesn't exist (should be safe)."""
        pid_file = tmp_path / ".mcp-server.pid"
        manager = PIDFileManager(pid_file)
        
        # Should not raise error
        manager.remove()
    
    def test_is_process_running_current(self, tmp_path):
        """Test checking if current process is running."""
        pid_file = tmp_path / ".mcp-server.pid"
        manager = PIDFileManager(pid_file)
        
        # Current process should be running
        assert manager._is_process_running(os.getpid()) is True
    
    def test_is_process_running_nonexistent(self, tmp_path):
        """Test checking if nonexistent process is running."""
        pid_file = tmp_path / ".mcp-server.pid"
        manager = PIDFileManager(pid_file)
        
        # PID 999999 unlikely to exist
        assert manager._is_process_running(999999) is False
    
    def test_stop_server_no_pid_file(self, tmp_path):
        """Test stopping server when PID file doesn't exist."""
        pid_file = tmp_path / ".mcp-server.pid"
        manager = PIDFileManager(pid_file)
        
        with pytest.raises(RuntimeError, match="No MCP server running"):
            manager.stop_server()
    
    def test_stop_server_stale_pid(self, tmp_path):
        """Test stopping server when PID file is stale (process not running)."""
        pid_file = tmp_path / ".mcp-server.pid"
        pid_file.write_text("999999")  # Nonexistent PID
        
        manager = PIDFileManager(pid_file)
        
        with pytest.raises(RuntimeError, match="is not running"):
            manager.stop_server()
        
        # Stale PID file should be cleaned up
        assert not pid_file.exists()
    
    def test_stop_server_success(self, tmp_path):
        """Test stopping a running server process."""
        import subprocess
        
        pid_file = tmp_path / ".mcp-server.pid"
        
        # Start a dummy long-running process
        proc = subprocess.Popen(["sleep", "30"])
        pid_file.write_text(str(proc.pid))
        
        try:
            manager = PIDFileManager(pid_file)
            success = manager.stop_server(timeout=5)
            
            assert success is True
            assert not pid_file.exists()
            
            # Verify process actually stopped
            assert not manager._is_process_running(proc.pid)
        finally:
            # Cleanup in case test fails
            try:
                proc.kill()
            except:
                pass
    
    def test_get_status_running(self, tmp_path):
        """Test getting status when server is running."""
        pid_file = tmp_path / ".mcp-server.pid"
        
        # Write current process PID (guaranteed running)
        pid_file.write_text(str(os.getpid()))
        
        manager = PIDFileManager(pid_file)
        status = manager.get_status()
        
        assert status["running"] is True
        assert status["pid"] == os.getpid()
        assert status["pid_file"] == str(pid_file)
    
    def test_get_status_not_running(self, tmp_path):
        """Test getting status when server is not running."""
        pid_file = tmp_path / ".mcp-server.pid"
        manager = PIDFileManager(pid_file)
        
        status = manager.get_status()
        
        assert status["running"] is False
        assert status["pid"] is None
        assert status["pid_file"] == str(pid_file)
    
    def test_get_status_stale_pid(self, tmp_path):
        """Test getting status when PID file is stale."""
        pid_file = tmp_path / ".mcp-server.pid"
        pid_file.write_text("999999")  # Nonexistent PID
        
        manager = PIDFileManager(pid_file)
        status = manager.get_status()
        
        assert status["running"] is False
        assert status["pid"] is None


class TestMCPConfigIntegration:
    """Integration tests for config and PID file management together."""
    
    def test_full_lifecycle_with_config(self, tmp_path):
        """Test complete server lifecycle with configuration."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        kittify_dir = project_path / ".kittify"
        kittify_dir.mkdir()
        
        # Create config file
        config_file = kittify_dir / "mcp-config.yaml"
        config_file.write_text("""
host: "127.0.0.1"
port: 8000
transport: "stdio"
""")
        
        # Load config
        config = MCPConfig.load(project_path)
        
        # Create PID manager
        pid_manager = PIDFileManager(config.pid_file)
        
        # Write PID (simulate server start)
        pid_manager.write()
        
        # Check status
        status = pid_manager.get_status()
        assert status["running"] is True
        
        # Remove PID (simulate server stop)
        pid_manager.remove()
        
        # Check status again
        status = pid_manager.get_status()
        assert status["running"] is False
