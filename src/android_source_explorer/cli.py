import click
from rich.console import Console
from .config import config, setup_directories
from .sync.framework_sync import sync_framework_sources
from .sync.androidx_sync import sync_androidx
from .sync.index_builder import build_index
import json

console = Console()

@click.group()
def main():
    """Android Source Explorer MCP Server CLI
    
    Provides tools to sync and explore Android framework and AndroidX source code locally.
    """
    pass

@main.command()
@click.option('--api-level', default=config.api_level, help='Android API level to sync (e.g., 35)')
@click.option('--androidx', default='compose,lifecycle,navigation', help='AndroidX artifact groups to sync, comma-separated, or "all"')
@click.option('--lsp', is_flag=True, help='Download LSP server binaries (JDT LS and Kotlin LS)')
def sync(api_level: str, androidx: str, lsp: bool):
    """Sync Android framework and AndroidX sources to local cache."""
    setup_directories()
    
    if lsp:
        console.print("[bold blue]Installing LSP server binaries...[/bold blue]")
        from .lsp.lsp_installer import install_lsp_servers
        install_lsp_servers(config.lsp_dir)

    console.print(f"[bold green]Starting sync for API level {api_level}...[/bold green]")
    console.print(f"[bold blue]Target AndroidX groups:[/bold blue] {androidx}")
    
    try:
        # Sync Framework
        sync_framework_sources(api_level, config.framework_dir)
        
        # Sync AndroidX
        sync_androidx(androidx, config.androidx_dir)
        
        # Build Index
        console.print("[bold green]Building index...[/bold green]")
        local_sdk = config.get_local_sdk_sources(api_level)
        build_index(
            framework_dir=config.framework_dir / f"android-{api_level}",
            androidx_dir=config.androidx_dir,
            index_path=config.class_index_path,
            local_sdk_path=local_sdk
        )
        
        console.print("[bold green]Sync completed successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Sync failed: {e}[/bold red]")

@main.command()
def index():
    """Build or rebuild the class index from synced files and local SDK."""
    setup_directories()
    console.print("[bold green]Building index...[/bold green]")
    local_sdk = config.get_local_sdk_sources(config.api_level)
    if local_sdk:
        console.print(f"Found local SDK sources at: {local_sdk}")
        
    try:
        build_index(
            framework_dir=config.framework_dir / f"android-{config.api_level}",
            androidx_dir=config.androidx_dir,
            index_path=config.class_index_path,
            local_sdk_path=local_sdk
        )
    except Exception as e:
        console.print(f"[bold red]Index build failed: {e}[/bold red]")

@main.command()
def serve():
    """Start the MCP server to provide tools to AI clients."""
    from .server import mcp
    console.print("[bold green]Starting Android Source Explorer MCP server...[/bold green]")
    mcp.run()

@main.command()
def status():
    """Show the current sync and index status."""
    console.print(f"[bold]Source directory:[/bold] {config.source_dir}")
    if config.android_home:
        console.print(f"[bold]Local SDK ($ANDROID_HOME):[/bold] {config.android_home}")
        sdk_path = config.get_local_sdk_sources(config.api_level)
        if sdk_path:
            console.print(f"[bold green]✓ Available SDK sources for API {config.api_level}[/bold green]")
        else:
            console.print(f"[yellow]✗ SDK sources for API {config.api_level} not found in $ANDROID_HOME/sources[/yellow]")
    else:
        console.print("[yellow]Local SDK ($ANDROID_HOME) not set.[/yellow]")
        
    if config.class_index_path.exists():
        try:
            with open(config.class_index_path, "r") as f:
                index_data = json.load(f)
            console.print(f"[bold green]✓ Index built with {len(index_data)} classes.[/bold green]")
        except Exception:
            console.print("[bold red]✗ Failed to read index.[/bold red]")
    else:
        console.print("[yellow]✗ Index not built yet. Run 'sync' or 'index'.[/yellow]")

@main.command(name="list-androidx")
def list_androidx():
    """List all available AndroidX artifact groups from Google Maven."""
    from .sync.artifact_catalog import get_all_androidx_groups
    console.print("[bold blue]Fetching available AndroidX groups...[/bold blue]")
    groups = get_all_androidx_groups()
    if groups:
        for g in groups:
            console.print(f"  {g}")
        console.print(f"\n[bold green]Total: {len(groups)} artifact groups found.[/bold green]")
    else:
        console.print("[red]No AndroidX groups found.[/red]")
    
if __name__ == '__main__':
    main()
