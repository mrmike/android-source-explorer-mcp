import httpx
import zipfile
import io
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn
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
        # Use fixed width for the description to prevent jumping
        TextColumn("[progress.description]{task.description: <40}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        console=console,
        expand=False
    ) as progress:
        group_task = progress.add_task("[blue]Fetching indexes...", total=len(targets))
        
        all_artifacts = []
        for group in targets:
            artifacts = get_artifacts_in_group(group)
            if artifacts:
                for artifact, versions in artifacts.items():
                    version = get_latest_stable_version(versions)
                    if version:
                        all_artifacts.append((group, artifact, version))
            progress.advance(group_task)
            
        download_task = progress.add_task("[green]Syncing artifacts...", total=len(all_artifacts))
        for group, artifact, version in all_artifacts:
            # Update description with fixed-width name
            progress.update(download_task, description=f"[green]Syncing {artifact}")
            download_artifact_sources(group, artifact, version, dest_dir)
            progress.advance(download_task)

def download_artifact_sources(group: str, artifact: str, version: str, dest_dir: Path):
    group_path = group.replace(".", "/")
    url = f"{MAVEN_GOOGLE_URL}/{group_path}/{artifact}/{version}/{artifact}-{version}-sources.jar"
    
    target_dir = dest_dir / f"{group}.{artifact}" / version
    if target_dir.exists() and any(target_dir.iterdir()):
        # Ensure metadata file exists even if the version is already downloaded
        metadata_path = target_dir.parent / ".metadata.json"
        if not metadata_path.exists():
            try:
                import json
                import datetime
                metadata = {
                    "group": group,
                    "artifact": artifact,
                    "last_updated": datetime.datetime.now().isoformat()
                }
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
            except Exception:
                pass
        return
        
    try:
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        if response.status_code == 200:
            target_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall(target_dir)
                
            # Write metadata file in parent folder
            import json
            import datetime
            metadata_path = target_dir.parent / ".metadata.json"
            metadata = {
                "group": group,
                "artifact": artifact,
                "last_updated": datetime.datetime.now().isoformat()
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
    except Exception:
        pass

def get_local_androidx_libraries(androidx_dir: Path) -> list[dict]:
    """Scan local androidx directory and return information about stored artifacts."""
    libraries = []
    if not androidx_dir.exists():
        return libraries
        
    import json
    from .artifact_catalog import get_all_androidx_groups
    
    # Cache all_groups to avoid fetching it repeatedly if multiple metadata files are missing
    all_groups = None
    
    for item in androidx_dir.iterdir():
        if item.is_dir() and "." in item.name:
            metadata_path = item / ".metadata.json"
            group = None
            artifact = None
            
            if metadata_path.exists():
                try:
                    with open(metadata_path, "r") as f:
                        meta = json.load(f)
                    group = meta.get("group")
                    artifact = meta.get("artifact")
                except Exception:
                    pass
            
            # Fallback to prefix matching against master index if metadata is missing
            if not group or not artifact:
                try:
                    if all_groups is None:
                        all_groups = get_all_androidx_groups()
                    
                    # Find the longest group name that is a prefix of item.name
                    matching_group = None
                    for g in all_groups:
                        if item.name.startswith(g + "."):
                            if not matching_group or len(g) > len(matching_group):
                                matching_group = g
                    
                    if matching_group:
                        group = matching_group
                        artifact = item.name[len(matching_group) + 1:]
                    else:
                        # Generic fallback: split on last dot
                        parts = item.name.rsplit(".", 1)
                        if len(parts) == 2:
                            group, artifact = parts
                        else:
                            continue
                except Exception:
                    # If fetching master index fails, do a best-effort split
                    parts = item.name.rsplit(".", 1)
                    if len(parts) == 2:
                        group, artifact = parts
                    else:
                        continue
            
            # Find all stored versions
            versions = []
            for v_dir in item.iterdir():
                if v_dir.is_dir() and not v_dir.name.startswith(".") and any(v_dir.iterdir()):
                    versions.append(v_dir.name)
            
            if versions:
                libraries.append({
                    "dir_name": item.name,
                    "group": group,
                    "artifact": artifact,
                    "versions": versions,
                    "path": item
                })
                
    return libraries

def update_androidx(androidx_dir: Path, clean: bool = False, target_androidx: str | None = None) -> int:
    """Scan and update existing local AndroidX libraries to their latest stable version.
    
    Returns the number of updated libraries.
    """
    libraries = get_local_androidx_libraries(androidx_dir)
    if not libraries:
        console.print("[yellow]No local AndroidX libraries found to update.[/yellow]")
        return 0
        
    # If target_androidx is specified, filter the libraries list
    if target_androidx:
        target_androidx = target_androidx.strip().lower()
        target_prefixes = []
        if target_androidx in GROUP_ALIASES:
            target_prefixes = [g.lower() for g in GROUP_ALIASES[target_androidx]]
        else:
            target_prefixes = [target_androidx]
            if not target_androidx.startswith("androidx."):
                target_prefixes.append(f"androidx.{target_androidx}")
            
        filtered_libraries = []
        for lib in libraries:
            lib_full = f"{lib['group']}.{lib['artifact']}".lower()
            matched = False
            for prefix in target_prefixes:
                if (lib['group'].lower() == prefix or 
                    lib_full.startswith(prefix) or 
                    prefix in lib_full or 
                    prefix in lib['artifact'].lower()):
                    matched = True
                    break
            if matched:
                filtered_libraries.append(lib)
        libraries = filtered_libraries
        
    if not libraries:
        console.print("[yellow]No matching local AndroidX libraries found for the filter.[/yellow]")
        return 0

    import shutil
    from .artifact_catalog import get_artifacts_in_group, get_latest_stable_version
    
    # Cache group catalogs to minimize API requests
    group_catalogs = {}
    updated_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description: <40}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        console=console,
        expand=False
    ) as progress:
        task = progress.add_task("[blue]Checking updates...", total=len(libraries))
        
        for lib in libraries:
            group = lib["group"]
            artifact = lib["artifact"]
            local_versions = lib["versions"]
            
            # Sort local versions using semver key
            def parse_semver(v):
                parts = []
                for p in v.split("."):
                    try:
                        parts.append(int(p))
                    except ValueError:
                        parts.append(0)
                return tuple(parts)
            
            latest_local = sorted(local_versions, key=parse_semver)[-1]
            
            progress.update(task, description=f"[blue]Checking {artifact}...")
            
            # Get group artifacts catalog
            if group not in group_catalogs:
                group_catalogs[group] = get_artifacts_in_group(group)
            
            artifacts_in_group = group_catalogs[group]
            if artifact in artifacts_in_group:
                remote_versions = artifacts_in_group[artifact]
                latest_remote = get_latest_stable_version(remote_versions)
                
                if latest_remote and parse_semver(latest_remote) > parse_semver(latest_local):
                    progress.update(task, description=f"[green]Updating {artifact} to {latest_remote}")
                    download_artifact_sources(group, artifact, latest_remote, androidx_dir)
                    updated_count += 1
                    
                    if clean:
                        # Clean up older versions
                        for old_v in local_versions:
                            if old_v != latest_remote:
                                old_dir = lib["path"] / old_v
                                if old_dir.exists():
                                    try:
                                        shutil.rmtree(old_dir)
                                    except Exception:
                                        pass
                else:
                    # Already up to date
                    pass
            
            progress.advance(task)
            
    return updated_count
