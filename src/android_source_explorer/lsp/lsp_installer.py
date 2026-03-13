import httpx
import zipfile
import tarfile
import io
import os
import shutil
from pathlib import Path
from rich.console import Console

console = Console()

KOTLIN_LS_URL = "https://github.com/fwcd/kotlin-language-server/releases/latest/download/server.zip"
JDT_LS_URL = "https://download.eclipse.org/jdtls/milestones/1.57.0/jdt-language-server-1.57.0-202602261110.tar.gz"

def install_lsp_servers(lsp_dir: Path):
    """Download and extract Kotlin and Java LSP servers."""
    install_kotlin_ls(lsp_dir / "kotlin")
    install_jdt_ls(lsp_dir / "java")

def install_kotlin_ls(target_dir: Path):
    if target_dir.exists() and any(target_dir.iterdir()):
        console.print("[yellow]Kotlin Language Server already installed.[/yellow]")
        return

    console.print("[blue]Downloading Kotlin Language Server...[/blue]")
    try:
        response = httpx.get(KOTLIN_LS_URL, follow_redirects=True, timeout=60.0)
        if response.status_code == 200:
            target_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall(target_dir)
            
            # Make the binary executable
            bin_path = target_dir / "server" / "bin" / "kotlin-language-server"
            if bin_path.exists():
                os.chmod(bin_path, 0o755)
            console.print("[green]Kotlin Language Server installed successfully.[/green]")
        else:
            console.print(f"[red]Failed to download Kotlin LS: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]Error installing Kotlin LS: {e}[/red]")

def install_jdt_ls(target_dir: Path):
    if target_dir.exists() and any(target_dir.iterdir()):
        console.print("[yellow]Eclipse JDT Language Server already installed.[/yellow]")
        return

    console.print("[blue]Downloading Eclipse JDT Language Server...[/blue]")
    try:
        response = httpx.get(JDT_LS_URL, follow_redirects=True, timeout=120.0)
        if response.status_code == 200:
            target_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
                tar.extractall(target_dir)
            console.print("[green]JDT Language Server installed successfully.[/green]")
        else:
            console.print(f"[red]Failed to download JDT LS: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]Error installing JDT LS: {e}[/red]")
