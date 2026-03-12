import subprocess
import shutil
from pathlib import Path
from rich.console import Console

console = Console()

API_TO_TAG = {
    "35": "android-15.0.0_r1",
    "34": "android-14.0.0_r1",
    "33": "android-13.0.0_r1",
    "32": "android-12.1.0_r1",
    "31": "android-12.0.0_r1",
    "30": "android-11.0.0_r1",
    "29": "android-10.0.0_r1",
    "28": "android-9.0.0_r1",
}

def get_aosp_tag(api_level: str) -> str:
    return API_TO_TAG.get(api_level, f"android-{api_level}.0.0_r1")

def sync_framework_sources(api_level: str, dest_dir: Path):
    """Clone Android framework sources using git sparse-checkout."""
    tag = get_aosp_tag(api_level)
    repo_url = "https://android.googlesource.com/platform/frameworks/base"
    
    target_dir = dest_dir / f"android-{api_level}"
    if target_dir.exists():
        console.print(f"[yellow]Framework sources for API {api_level} already exist. Skipping clone.[/yellow]")
        return target_dir

    with console.status(f"[bold blue]Fetching framework sources for API {api_level} (tag: {tag})...") as status:
        # We use a temporary directory for cloning
        temp_dir = dest_dir / f"android-{api_level}_tmp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            
        try:
            # Initialize an empty repository
            status.update("[dim]Initializing local git repository...[/dim]")
            subprocess.run(["git", "init", str(temp_dir)], check=True, capture_output=True)
            
            # Add remote
            subprocess.run(["git", "-C", str(temp_dir), "remote", "add", "origin", repo_url], check=True, capture_output=True)
            
            # Enable sparse checkout
            subprocess.run(["git", "-C", str(temp_dir), "config", "core.sparseCheckout", "true"], check=True, capture_output=True)
            
            # Configure sparse checkout paths
            sparse_paths = [
                "core/java/",
                "graphics/java/",
                "location/java/",
                "media/java/",
                "opengl/java/",
                "telecomm/java/",
                "telephony/java/",
                "wifi/java/",
                "keystore/java/",
                "rs/java/"
            ]
            
            sparse_config_path = temp_dir / ".git" / "info" / "sparse-checkout"
            with open(sparse_config_path, "w") as f:
                for path in sparse_paths:
                    f.write(path + "\n")
                    
            # Fetch specific tag with depth 1
            status.update("[blue]Downloading files from AOSP (this may take a few minutes)...[/blue]")
            subprocess.run(["git", "-C", str(temp_dir), "fetch", "--depth", "1", "origin", "tag", tag], check=True, capture_output=True)
            
            # Checkout
            status.update("[dim]Checking out files...[/dim]")
            subprocess.run(["git", "-C", str(temp_dir), "checkout", "FETCH_HEAD"], check=True, capture_output=True)
            
            # Remove .git
            shutil.rmtree(temp_dir / ".git")
            temp_dir.rename(target_dir)
            
            console.print(f"[bold green]✓ Framework API {api_level} synced.[/bold green]")
            return target_dir
            
        except Exception as e:
            console.print(f"[bold red]Failed to fetch framework: {e}[/bold red]")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise
