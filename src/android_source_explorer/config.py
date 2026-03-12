import os
from pathlib import Path
from dataclasses import dataclass

DEFAULT_API_LEVEL = "35"
ANDROID_SOURCE_DIR = Path(os.environ.get("ANDROID_SOURCE_DIR", Path.home() / ".android-sources"))

@dataclass
class Config:
    source_dir: Path = ANDROID_SOURCE_DIR
    api_level: str = os.environ.get("ANDROID_SOURCE_API_LEVEL", DEFAULT_API_LEVEL)
    android_home: Path | None = Path(os.environ["ANDROID_HOME"]) if "ANDROID_HOME" in os.environ else None
    
    @property
    def framework_dir(self) -> Path:
        return self.source_dir / "framework"
        
    @property
    def androidx_dir(self) -> Path:
        return self.source_dir / "androidx"
        
    @property
    def index_dir(self) -> Path:
        return self.source_dir / "index"
        
    @property
    def class_index_path(self) -> Path:
        return self.index_dir / "class_index.json"

    @property
    def lsp_dir(self) -> Path:
        return self.source_dir / "lsp"

    @property
    def lsp_enabled(self) -> bool:
        return os.environ.get("ANDROID_SOURCE_LSP", "false").lower() == "true"

    def get_local_sdk_sources(self, api_level: str) -> Path | None:
        """Return the path to the local SDK sources for a given API level, if it exists."""
        if self.android_home:
            sdk_path = self.android_home / "sources" / f"android-{api_level}"
            if sdk_path.exists() and sdk_path.is_dir():
                return sdk_path
        return None

config = Config()

def setup_directories():
    """Create necessary directories in the local source cache."""
    config.framework_dir.mkdir(parents=True, exist_ok=True)
    config.androidx_dir.mkdir(parents=True, exist_ok=True)
    config.index_dir.mkdir(parents=True, exist_ok=True)
    config.lsp_dir.mkdir(parents=True, exist_ok=True)
