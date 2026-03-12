import httpx
import xml.etree.ElementTree as ET
from rich.console import Console

console = Console()

MAVEN_GOOGLE_URL = "https://dl.google.com/dl/android/maven2"

def get_artifacts_in_group(group: str) -> dict[str, list[str]]:
    """Fetch artifacts and their available versions for a given group."""
    group_path = group.replace(".", "/")
    url = f"{MAVEN_GOOGLE_URL}/{group_path}/group-index.xml"
    
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code != 200:
            return {}
            
        root = ET.fromstring(response.text)
        artifacts = {}
        for child in root:
            if 'versions' in child.attrib:
                artifacts[child.tag] = child.attrib['versions'].split(",")
        return artifacts
    except Exception as e:
        console.print(f"[yellow]Failed to fetch index for {group} - {e}[/yellow]")
        return {}

def get_latest_stable_version(versions: list[str]) -> str | None:
    """Filter out alpha/beta/rc and return the latest stable version."""
    stables = [v for v in versions if "-" not in v]
    if not stables:
        # Fallback to the latest version even if unstable
        return versions[-1] if versions else None
    
    def parse_semver(v):
        parts = []
        for p in v.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return tuple(parts)
        
    return sorted(stables, key=parse_semver)[-1]
