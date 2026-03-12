import subprocess
import shutil
import re
from pathlib import Path
from rich.console import Console

console = Console()

# Mapping major API levels to their internal Android version prefix
API_TO_VERSION = {
    "36": "16.0.0",
    "35": "15.0.0",
    "34": "14.0.0",
    "33": "13.0.0",
    "32": "12.1.0",
    "31": "12.0.0",
    "30": "11.0.0",
    "29": "10.0.0",
    "28": "9.0.0",
}

def find_latest_tag(api_level: str) -> str:
    """Query AOSP to find the highest revision tag for this API level."""
    version_prefix = API_TO_VERSION.get(api_level, f"{int(api_level)-20}.0.0")
    repo_url = "https://android.googlesource.com/platform/frameworks/base"
    
    try:
        # Get remote tags
        result = subprocess.run(
            ["git", "ls-remote", "--tags", repo_url],
            capture_output=True, text=True, check=True
        )
        
        # Pattern: android-16.0.0_r4
        pattern = re.compile(rf"refs/tags/android-{version_prefix}_r(\d+)$")
        
        tags = []
        for line in result.stdout.splitlines():
            match = pattern.search(line)
            if match:
                revision = int(match.group(1))
                tags.append((revision, f"android-{version_prefix}_r{revision}"))
        
        if tags:
            # Return the tag with the highest revision number
            latest_revision, latest_tag = max(tags, key=lambda x: x[0])
            return latest_tag
            
    except Exception as e:
        console.print(f"[dim yellow]Warning: Could not query latest tag, using default: {e}[/dim yellow]")
    
    # Fallback to r1 if discovery fails
    return f"android-{version_prefix}_r1"

def sync_framework_sources(api_level: str, dest_dir: Path):
    """Clone Android framework sources using git sparse-checkout."""
    tag = find_latest_tag(api_level)
    repo_url = "https://android.googlesource.com/platform/frameworks/base"
    
    target_dir = dest_dir / f"android-{api_level}"
    if target_dir.exists():
        console.print(f"[yellow]Framework sources for API {api_level} already exist. Skipping clone.[/yellow]")
        return target_dir

    with console.status(f"[bold blue]Fetching Framework API {api_level} ({tag})...") as status:
        # We use a temporary directory for cloning
        temp_dir = dest_dir / f"android-{api_level}_tmp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            
        try:
            # Initialize an empty repository
            status.update("[dim]Initializing local repository...[/dim]")
            subprocess.run(["git", "init", str(temp_dir)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(temp_dir), "remote", "add", "origin", repo_url], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(temp_dir), "config", "core.sparseCheckout", "true"], check=True, capture_output=True)
            
            sparse_paths = ["core/java/", "graphics/java/", "location/java/", "media/java/", "opengl/java/", "telecomm/java/", "telephony/java/", "wifi/java/", "keystore/java/", "rs/java/"]
            sparse_config_path = temp_dir / ".git" / "info" / "sparse-checkout"
            with open(sparse_config_path, "w") as f:
                for path in sparse_paths:
                    f.write(path + "\n")
                    
            status.update(f"[blue]Downloading {tag} from AOSP (this may take a few minutes)...[/blue]")
            # Fetch using the specific tag reference
            subprocess.run(
                ["git", "-C", str(temp_dir), "fetch", "--depth", "1", "origin", f"refs/tags/{tag}:refs/tags/{tag}"], 
                check=True, capture_output=True
            )
            
            status.update("[dim]Checking out files...[/dim]")
            subprocess.run(["git", "-C", str(temp_dir), "checkout", tag], check=True, capture_output=True)
            
            # Remove .git folder
            shutil.rmtree(temp_dir / ".git")
            
            # Rename tmp to final
            temp_dir.rename(target_dir)
            
            console.print(f"[bold green]✓ Framework API {api_level} synced.[/bold green]")
            return target_dir
            
        except Exception as e:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise e
