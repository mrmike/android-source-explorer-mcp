import httpx
import zipfile
import io
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from .artifact_catalog import get_artifacts_in_group, get_latest_stable_version

console = Console()

MAVEN_GOOGLE_URL = "https://dl.google.com/dl/android/maven2"

# Common aliases for user-friendly --androidx arguments
GROUP_ALIASES = {
    "compose": [
        "androidx.compose.runtime", 
        "androidx.compose.ui", 
        "androidx.compose.foundation", 
        "androidx.compose.material3", 
        "androidx.compose.animation"
    ],
    "lifecycle": ["androidx.lifecycle"],
    "navigation": ["androidx.navigation"],
    "room": ["androidx.room"],
    "activity": ["androidx.activity"],
    "fragment": ["androidx.fragment"],
    "core": ["androidx.core"],
}

def sync_androidx(groups_arg: str, dest_dir: Path):
    """Sync AndroidX sources based on comma-separated group list."""
    if not groups_arg or groups_arg.lower() == "none":
        return
        
    targets = []
    for g in groups_arg.split(","):
        g = g.strip().lower()
        if g == "all":
            for groups in GROUP_ALIASES.values():
                targets.extend(groups)
        elif g in GROUP_ALIASES:
            targets.extend(GROUP_ALIASES[g])
        else:
            targets.append(g if g.startswith("androidx.") else f"androidx.{g}")
            
    # Remove duplicates
    targets = list(set(targets))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        group_task = progress.add_task("[blue]Fetching group indexes...", total=len(targets))
        
        all_artifacts = []
        for group in targets:
            artifacts = get_artifacts_in_group(group)
            if artifacts:
                for artifact, versions in artifacts.items():
                    version = get_latest_stable_version(versions)
                    if version:
                        all_artifacts.append((group, artifact, version))
            progress.advance(group_task)
            
        download_task = progress.add_task("[green]Downloading sources...", total=len(all_artifacts))
        for group, artifact, version in all_artifacts:
            progress.update(download_task, description=f"[green]Downloading {artifact}...")
            download_artifact_sources(group, artifact, version, dest_dir)
            progress.advance(download_task)

def download_artifact_sources(group: str, artifact: str, version: str, dest_dir: Path):
    group_path = group.replace(".", "/")
    url = f"{MAVEN_GOOGLE_URL}/{group_path}/{artifact}/{version}/{artifact}-{version}-sources.jar"
    
    target_dir = dest_dir / f"{group}.{artifact}" / version
    if target_dir.exists() and any(target_dir.iterdir()):
        return
        
    try:
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        if response.status_code == 200:
            target_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall(target_dir)
    except Exception:
        pass
