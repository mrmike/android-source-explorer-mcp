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

@main.command()
@click.option('--clean', is_flag=True, help='Clean up older versions of updated AndroidX artifacts.')
@click.option('--api-level', help='Explicitly update only this API level (e.g., 36).')
@click.option('--androidx', help='Explicitly update only this AndroidX group or artifact.')
def update(clean: bool, api_level: str | None, androidx: str | None):
    """Check for and download updates for Android Framework and AndroidX sources."""
    setup_directories()
    
    # 1. Update Framework
    framework_updated = False
    if androidx is None: # If only androidx is specified, skip framework update
        api_levels_to_update = []
        if api_level:
            api_levels_to_update = [api_level]
        else:
            # Auto-detect synced api levels
            if config.framework_dir.exists():
                import re
                for item in config.framework_dir.iterdir():
                    if item.is_dir() and item.name.startswith("android-"):
                        match = re.search(r"android-(\d+)", item.name)
                        if match:
                            api_levels_to_update.append(match.group(1))
                            
        if api_levels_to_update:
            console.print(f"[bold blue]Checking updates for Framework API levels: {', '.join(api_levels_to_update)}...[/bold blue]")
            for api in api_levels_to_update:
                try:
                    # Check if latest tag matches what we have
                    from .sync.framework_sync import find_latest_tag
                    latest_tag = find_latest_tag(api)
                    metadata_path = config.framework_dir / f"android-{api}" / ".metadata.json"
                    
                    is_up_to_date = False
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, "r") as f:
                                meta = json.load(f)
                            if meta.get("tag") == latest_tag:
                                is_up_to_date = True
                        except Exception:
                            pass
                            
                    if is_up_to_date:
                        console.print(f"[green]Framework API {api} is already up to date ({latest_tag}).[/green]")
                    else:
                        console.print(f"[yellow]Framework API {api} has an update available: {latest_tag}. Updating...[/yellow]")
                        sync_framework_sources(api, config.framework_dir, force=True)
                        framework_updated = True
                except Exception as e:
                    console.print(f"[bold red]Failed to update Framework API {api}: {e}[/bold red]")
        else:
            console.print("[yellow]No local Android Framework sources found to update. Run 'sync' first.[/yellow]")
            
    # 2. Update AndroidX
    androidx_updated_count = 0
    if api_level is None: # If only api_level is specified, skip androidx update
        console.print("[bold blue]Checking updates for AndroidX libraries...[/bold blue]")
        try:
            from .sync.androidx_sync import update_androidx
            androidx_updated_count = update_androidx(config.androidx_dir, clean=clean, target_androidx=androidx)
            if androidx_updated_count > 0:
                console.print(f"[bold green]Updated {androidx_updated_count} AndroidX libraries successfully.[/bold green]")
            else:
                console.print("[green]All AndroidX libraries are up to date.[/green]")
        except Exception as e:
            console.print(f"[bold red]Failed to update AndroidX libraries: {e}[/bold red]")
            
    # 3. Rebuild index if any updates occurred
    if framework_updated or androidx_updated_count > 0:
        console.print("[bold green]Updates applied. Rebuilding index...[/bold green]")
        try:
            local_sdk = config.get_local_sdk_sources(config.api_level)
            build_index(
                framework_dir=config.framework_dir / f"android-{config.api_level}",
                androidx_dir=config.androidx_dir,
                index_path=config.class_index_path,
                local_sdk_path=local_sdk
            )
        except Exception as e:
            console.print(f"[bold red]Index rebuild failed: {e}[/bold red]")
    else:
        console.print("[green]No updates were applied. Index is up to date.[/green]")

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
