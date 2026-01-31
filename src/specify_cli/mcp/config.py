"""
MCP server configuration and PID file management.

Handles server configuration file loading (.kittify/mcp-config.yaml) and
PID file operations for server lifecycle management.
"""

import os
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import yaml


@dataclass
class MCPConfig:
    """
    MCP server configuration loaded from .kittify/mcp-config.yaml.
    
    Attributes:
        host: Server bind address (default: "127.0.0.1")
        port: Server port for SSE transport (default: 8000)
        transport: Transport mode ("stdio" or "sse", default: "stdio")
        auth_enabled: Whether API key authentication is required (default: False)
        api_key: Server API key (if auth_enabled=True)
        pid_file: Path to PID file (default: .kittify/.mcp-server.pid)
    """
    
    host: str = "127.0.0.1"
    port: int = 8000
    transport: Literal["stdio", "sse"] = "stdio"
    auth_enabled: bool = False
    api_key: Optional[str] = None
    pid_file: Optional[Path] = None
    
    @classmethod
    def load(cls, project_path: Path) -> "MCPConfig":
        """
        Load MCP configuration from .kittify/mcp-config.yaml.
        
        Falls back to defaults if file doesn't exist. Environment variables
        override config file values.
        
        Args:
            project_path: Path to project root (contains .kittify/)
            
        Returns:
            MCPConfig instance with loaded/default values
            
        Raises:
            ValueError: If config file has invalid format
        """
        config_file = project_path / ".kittify" / "mcp-config.yaml"
        config_dict = {}
        
        # Load from config file if exists
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config_dict = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid mcp-config.yaml: {e}") from e
        
        # Environment variables override config file
        if "MCP_SERVER_HOST" in os.environ:
            config_dict["host"] = os.environ["MCP_SERVER_HOST"]
        
        if "MCP_SERVER_PORT" in os.environ:
            try:
                config_dict["port"] = int(os.environ["MCP_SERVER_PORT"])
            except ValueError:
                raise ValueError(
                    f"Invalid MCP_SERVER_PORT: {os.environ['MCP_SERVER_PORT']}. "
                    "Must be an integer."
                )
        
        if "MCP_SERVER_TRANSPORT" in os.environ:
            config_dict["transport"] = os.environ["MCP_SERVER_TRANSPORT"]
        
        if "MCP_SERVER_AUTH_ENABLED" in os.environ:
            config_dict["auth_enabled"] = os.environ["MCP_SERVER_AUTH_ENABLED"].lower() in ("true", "1", "yes")
        
        if "MCP_SERVER_API_KEY" in os.environ:
            config_dict["api_key"] = os.environ["MCP_SERVER_API_KEY"]
        
        # Set default PID file path if not specified
        if "pid_file" not in config_dict:
            config_dict["pid_file"] = project_path / ".kittify" / ".mcp-server.pid"
        else:
            config_dict["pid_file"] = Path(config_dict["pid_file"])
        
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__annotations__})
    
    def save(self, project_path: Path):
        """
        Save MCP configuration to .kittify/mcp-config.yaml.
        
        Does NOT save api_key (security: keys should come from env vars).
        
        Args:
            project_path: Path to project root (contains .kittify/)
        """
        config_file = project_path / ".kittify" / "mcp-config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = {
            "host": self.host,
            "port": self.port,
            "transport": self.transport,
            "auth_enabled": self.auth_enabled,
            # Do NOT save api_key (security concern)
        }
        
        with open(config_file, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)


class PIDFileManager:
    """
    Manages PID file for MCP server lifecycle.
    
    Prevents multiple server instances and enables graceful shutdown.
    """
    
    def __init__(self, pid_file: Path):
        """
        Initialize PID file manager.
        
        Args:
            pid_file: Path to PID file (e.g., .kittify/.mcp-server.pid)
        """
        self.pid_file = pid_file
    
    def write(self) -> None:
        """
        Write current process PID to PID file.
        
        Raises:
            RuntimeError: If PID file already exists and process is running
        """
        if self.pid_file.exists():
            # Check if existing PID is still running
            existing_pid = self.read()
            if existing_pid and self._is_process_running(existing_pid):
                raise RuntimeError(
                    f"MCP server already running (PID: {existing_pid}). "
                    f"Stop it first with: spec-kitty mcp stop"
                )
            # Stale PID file (process not running) - safe to overwrite
            self.pid_file.unlink()
        
        # Write current process PID
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(str(os.getpid()))
    
    def read(self) -> Optional[int]:
        """
        Read PID from PID file.
        
        Returns:
            Process ID if file exists and is valid, None otherwise
        """
        if not self.pid_file.exists():
            return None
        
        try:
            return int(self.pid_file.read_text().strip())
        except (ValueError, OSError):
            return None
    
    def remove(self) -> None:
        """
        Remove PID file.
        
        Safe to call even if file doesn't exist.
        """
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def _is_process_running(self, pid: int) -> bool:
        """
        Check if process with given PID is currently running.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if process is running, False otherwise
        """
        try:
            # Send signal 0 (does nothing but checks if process exists)
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            # Process does not exist
            return False
        except PermissionError:
            # Process exists but we can't send signals to it
            # (e.g., owned by another user)
            return True
        except OSError:
            # Other OS error (treat as not running)
            return False
    
    def stop_server(self, timeout: int = 10) -> bool:
        """
        Stop the MCP server gracefully by sending SIGTERM.
        
        Args:
            timeout: Seconds to wait for graceful shutdown before giving up
            
        Returns:
            True if server stopped successfully, False otherwise
            
        Raises:
            RuntimeError: If no server is running
        """
        pid = self.read()
        if not pid:
            raise RuntimeError(
                "No MCP server running. "
                "PID file not found or invalid."
            )
        
        if not self._is_process_running(pid):
            # Stale PID file - clean up and report
            self.remove()
            raise RuntimeError(
                f"MCP server (PID: {pid}) is not running. "
                "Cleaned up stale PID file."
            )
        
        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to exit (poll every 0.5s)
            import time
            for _ in range(timeout * 2):  # Poll twice per second
                if not self._is_process_running(pid):
                    self.remove()
                    return True
                time.sleep(0.5)
            
            # Timeout - process didn't exit gracefully
            return False
        except PermissionError:
            raise RuntimeError(
                f"Permission denied: Cannot stop server (PID: {pid}). "
                "It may be owned by another user."
            )
        except OSError as e:
            raise RuntimeError(f"Failed to stop server (PID: {pid}): {e}") from e
    
    def get_status(self) -> dict:
        """
        Get server status information.
        
        Returns:
            Dictionary with keys:
            - running: bool (True if server is running)
            - pid: int or None (process ID if running)
            - pid_file: str (path to PID file)
        """
        pid = self.read()
        running = pid is not None and self._is_process_running(pid)
        
        return {
            "running": running,
            "pid": pid if running else None,
            "pid_file": str(self.pid_file),
        }
