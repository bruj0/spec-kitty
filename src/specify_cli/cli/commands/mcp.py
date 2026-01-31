"""MCP server management commands."""

import signal
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.mcp.config import MCPConfig, PIDFileManager
from specify_cli.mcp.server import MCPServer

app = typer.Typer(help="MCP server management")
console = Console()


def _get_project_root() -> Path:
    """Get project root directory (contains .kittify/)."""
    cwd = Path.cwd()
    
    # Search upwards for .kittify/ directory
    current = cwd
    while current != current.parent:
        if (current / ".kittify").exists():
            return current
        current = current.parent
    
    # Not found - use current directory
    return cwd


def _setup_signal_handlers(pid_manager: PIDFileManager):
    """
    Setup signal handlers for graceful shutdown.
    
    Handles SIGTERM and SIGINT (Ctrl+C) to cleanup PID file and exit cleanly.
    """
    def signal_handler(signum, frame):
        console.print("\n[yellow]Shutting down MCP server...[/yellow]")
        pid_manager.remove()
        console.print("[green]Server stopped successfully[/green]")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


@app.command()
def start(
    host: str = typer.Option(None, help="Server host (SSE only, overrides config)"),
    port: int = typer.Option(None, help="Server port (SSE only, overrides config)"),
    transport: str = typer.Option(None, help="Transport: stdio or sse (overrides config)"),
    auth: bool = typer.Option(None, help="Enable API key authentication (overrides config)"),
    api_key: str = typer.Option(None, help="API key (if auth enabled, overrides config)"),
    config_file: bool = typer.Option(True, help="Load from .kittify/mcp-config.yaml"),
):
    """
    Start the MCP server.
    
    Configuration is loaded from .kittify/mcp-config.yaml if it exists.
    Command-line options override config file values.
    Environment variables override both config file and CLI options.
    
    Examples:
        # Start with stdio transport (uses config or defaults)
        spec-kitty mcp start
        
        # Start with SSE transport (override config)
        spec-kitty mcp start --transport sse --host 0.0.0.0 --port 8000
        
        # Start with authentication (override config)
        spec-kitty mcp start --auth --api-key YOUR_SECRET_KEY
        
        # Ignore config file (use CLI options only)
        spec-kitty mcp start --no-config-file --transport stdio
    """
    project_root = _get_project_root()
    
    try:
        # Load configuration
        if config_file:
            config = MCPConfig.load(project_root)
        else:
            config = MCPConfig()
        
        # Override config with CLI options (if provided)
        if host is not None:
            config.host = host
        if port is not None:
            config.port = port
        if transport is not None:
            config.transport = transport
        if auth is not None:
            config.auth_enabled = auth
        if api_key is not None:
            config.api_key = api_key
        
        # Setup PID file management
        pid_manager = PIDFileManager(config.pid_file or project_root / ".kittify" / ".mcp-server.pid")
        
        # Check if server already running
        try:
            pid_manager.write()
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
        
        # Setup signal handlers for graceful shutdown
        _setup_signal_handlers(pid_manager)
        
        # Create and configure server
        server = MCPServer(
            host=config.host,
            port=config.port,
            transport=config.transport,
            auth_enabled=config.auth_enabled,
            api_key=config.api_key,
        )
        
        console.print("[green]Starting MCP server...[/green]")
        console.print(f"Transport: {config.transport}")
        if config.transport == "sse":
            console.print(f"Listening on {config.host}:{config.port}")
        if config.auth_enabled:
            console.print("[yellow]Authentication enabled[/yellow]")
        console.print(f"PID file: {pid_manager.pid_file}")
        
        console.print("\n[dim]Press Ctrl+C to stop server[/dim]\n")
        
        server.start()
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    except RuntimeError as e:
        console.print(f"[red]Error starting server:[/red] {e}")
        # Cleanup PID file if server failed to start
        if 'pid_manager' in locals():
            pid_manager.remove()
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
        if 'pid_manager' in locals():
            pid_manager.remove()
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        # Cleanup PID file if server crashed
        if 'pid_manager' in locals():
            pid_manager.remove()
        raise typer.Exit(1)


@app.command()
def status():
    """
    Check if MCP server is running.
    
    Displays server status, PID, and configuration information.
    
    Examples:
        spec-kitty mcp status
    """
    project_root = _get_project_root()
    
    try:
        # Load configuration
        config = MCPConfig.load(project_root)
        pid_manager = PIDFileManager(config.pid_file or project_root / ".kittify" / ".mcp-server.pid")
        
        status_info = pid_manager.get_status()
        
        # Create status table
        table = Table(title="MCP Server Status", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value")
        
        if status_info["running"]:
            table.add_row("Status", "[green]Running[/green]")
            table.add_row("PID", str(status_info["pid"]))
        else:
            table.add_row("Status", "[red]Not running[/red]")
        
        table.add_row("PID File", status_info["pid_file"])
        table.add_row("Transport", config.transport)
        if config.transport == "sse":
            table.add_row("Host", config.host)
            table.add_row("Port", str(config.port))
        table.add_row("Auth Enabled", "Yes" if config.auth_enabled else "No")
        
        console.print(table)
        
        if not status_info["running"]:
            raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error checking status:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def stop(
    timeout: int = typer.Option(10, help="Seconds to wait for graceful shutdown"),
):
    """
    Stop the MCP server gracefully.
    
    Sends SIGTERM to the server process and waits for it to exit cleanly.
    Cleans up PID file after shutdown.
    
    Examples:
        # Stop server with default 10-second timeout
        spec-kitty mcp stop
        
        # Stop server with custom timeout
        spec-kitty mcp stop --timeout 30
    """
    project_root = _get_project_root()
    
    try:
        # Load configuration
        config = MCPConfig.load(project_root)
        pid_manager = PIDFileManager(config.pid_file or project_root / ".kittify" / ".mcp-server.pid")
        
        console.print("[yellow]Stopping MCP server...[/yellow]")
        
        success = pid_manager.stop_server(timeout=timeout)
        
        if success:
            console.print("[green]Server stopped successfully[/green]")
        else:
            console.print(
                f"[red]Server did not stop within {timeout} seconds.[/red]\n"
                "[yellow]Consider increasing timeout or manually killing the process.[/yellow]"
            )
            raise typer.Exit(1)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error stopping server:[/red] {e}")
        raise typer.Exit(1)
