import asyncio
import os
import platform
from pathlib import Path
from .lsp_client import LSPClient
from ..config import config
from rich.console import Console

console = Console()

class LSPManager:
    def __init__(self):
        self.java_client = None
        self.kotlin_client = None

    async def get_client_for_file(self, file_path: Path) -> LSPClient | None:
        if file_path.suffix == '.java':
            if not self.java_client:
                self.java_client = await self._start_java_lsp()
            return self.java_client
        elif file_path.suffix == '.kt':
            if not self.kotlin_client:
                self.kotlin_client = await self._start_kotlin_lsp()
            return self.kotlin_client
        return None

    async def _start_java_lsp(self) -> LSPClient:
        java_lsp_dir = config.lsp_dir / "java"
        
        # Find the launcher JAR
        plugins_dir = java_lsp_dir / "plugins"
        try:
            launcher_jar = next(plugins_dir.glob("org.eclipse.equinox.launcher_*.jar"))
        except StopIteration:
            raise RuntimeError(f"Could not find Eclipse JDT LS launcher JAR in {plugins_dir}")

        # Determine the configuration directory based on OS
        system = platform.system().lower()
        if system == "darwin":
            config_name = "config_mac"
        elif system == "linux":
            config_name = "config_linux"
        elif system == "windows":
            config_name = "config_win"
        else:
            config_name = "config_linux" # Fallback

        config_dir = java_lsp_dir / config_name
        
        # JAVA_HOME check
        java_bin = "java"
        if "JAVA_HOME" in os.environ:
            java_bin = str(Path(os.environ["JAVA_HOME"]) / "bin" / "java")

        command = [
            java_bin,
            "-Declipse.application=org.eclipse.jdt.ls.core.id1",
            "-Dosgi.bundles.defaultStartLevel=4",
            "-Declipse.product=org.eclipse.jdt.ls.core.product",
            "-Dlog.level=ALL",
            "-Xmx1G",
            "--add-modules=ALL-SYSTEM",
            "--add-opens", "java.base/java.util=ALL-UNNAMED",
            "--add-opens", "java.base/java.lang=ALL-UNNAMED",
            "-jar", str(launcher_jar),
            "-configuration", str(config_dir),
            "-data", str(config.lsp_dir / "java_data")
        ]
        
        console.print("[dim]Starting Java Language Server...[/dim]")
        client = LSPClient(command, config.source_dir.as_uri())
        await client.start()
        return client

    async def _start_kotlin_lsp(self) -> LSPClient:
        kotlin_lsp_bin = config.lsp_dir / "kotlin" / "server" / "bin" / "kotlin-language-server"
        if not kotlin_lsp_bin.exists():
            raise RuntimeError(f"Kotlin Language Server binary not found at {kotlin_lsp_bin}. Run 'sync --lsp' first.")
            
        command = [str(kotlin_lsp_bin)]
        
        console.print("[dim]Starting Kotlin Language Server...[/dim]")
        client = LSPClient(command, config.source_dir.as_uri())
        await client.start()
        return client

    async def shutdown(self):
        if self.java_client:
            await self.java_client.stop()
        if self.kotlin_client:
            await self.kotlin_client.stop()

lsp_manager = LSPManager()
