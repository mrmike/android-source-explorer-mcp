import json
import os
from pathlib import Path
from rich.console import Console

console = Console()

def build_index(framework_dir: Path, androidx_dir: Path, index_path: Path, local_sdk_path: Path | None = None):
    """Build a mapping from FQCN (Fully Qualified Class Name) to file paths."""
    
    index = {}
    
    # Prioritize local SDK if available
    if local_sdk_path and local_sdk_path.exists():
        console.print(f"[blue]Indexing local SDK sources at {local_sdk_path}...[/blue]")
        index_directory(local_sdk_path, index, source_type="framework_local")
    
    # Fallback/supplement with local framework cache
    if framework_dir.exists():
        console.print(f"[blue]Indexing downloaded framework sources at {framework_dir}...[/blue]")
        index_directory(framework_dir, index, source_type="framework_cache", skip_existing=True)
        
    # Index AndroidX cache
    if androidx_dir.exists():
        console.print(f"[blue]Indexing downloaded AndroidX sources at {androidx_dir}...[/blue]")
        index_directory(androidx_dir, index, source_type="androidx")
        
    # Save index
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
        
    console.print(f"[bold green]Index built successfully with {len(index)} classes.[/bold green]")
    return index

def index_directory(root_dir: Path, index: dict, source_type: str, skip_existing: bool = False):
    """Walk directory and add .java and .kt files to the index."""
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".java") or file.endswith(".kt"):
                file_path = Path(root) / file
                fqcn = guess_fqcn_from_path(file_path)
                
                if fqcn:
                    if skip_existing and fqcn in index:
                        continue
                    index[fqcn] = str(file_path)

def guess_fqcn_from_path(file_path: Path) -> str | None:
    """Attempt to guess the Fully Qualified Class Name from a file path."""
    # Read the package declaration from the file (most accurate)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("package "):
                    pkg = line.replace("package ", "").replace(";", "").strip()
                    class_name = file_path.stem
                    return f"{pkg}.{class_name}"
    except Exception:
        pass
        
    # Fallback to path heuristics
    path_str = str(file_path)
    for src_root in ["/java/", "/src/", "/androidMain/kotlin/", "/commonMain/kotlin/"]:
        if src_root in path_str:
            parts = path_str.split(src_root)
            if len(parts) > 1:
                rel_path = parts[-1]
                fqcn = rel_path.replace("/", ".").replace(".java", "").replace(".kt", "")
                return fqcn
    return None
