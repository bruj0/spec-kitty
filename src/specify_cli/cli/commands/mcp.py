"""MCP server management commands."""

import typer
from rich.console import Console

from specify_cli.mcp.server import MCPServer

app = typer.Typer(help="MCP server management")
console = Console()


@app.command()
def start(
    host: str = typer.Option("127.0.0.1", help="Server host (SSE only)"),
    port: int = typer.Option(8000, help="Server port (SSE only)"),
    transport: str = typer.Option("stdio", help="Transport: stdio or sse"),
    auth: bool = typer.Option(False, help="Enable API key authentication"),
    api_key: str = typer.Option(None, help="API key (if auth enabled)"),
):
    """
    Start the MCP server.
    
    Examples:
        # Start with stdio transport (for Claude Desktop, Cursor)
        spec-kitty mcp start
        
        # Start with SSE transport (for web clients)
        spec-kitty mcp start --transport sse --host 0.0.0.0 --port 8000
        
        # Start with authentication
        spec-kitty mcp start --auth --api-key YOUR_SECRET_KEY
    """
    try:
        server = MCPServer(
            host=host,
            port=port,
            transport=transport,
            auth_enabled=auth,
            api_key=api_key,
        )
        
        console.print("[green]Starting MCP server...[/green]")
        console.print(f"Transport: {transport}")
        if transport == "sse":
            console.print(f"Listening on {host}:{port}")
        if auth:
            console.print("[yellow]Authentication enabled[/yellow]")
        
        console.print("\n[dim]Press Ctrl+C to stop server[/dim]\n")
        
        server.start()
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)
    except RuntimeError as e:
        console.print(f"[red]Error starting server:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)
