# Android Source Explorer MCP Server

MCP server for exploring AOSP internals and Jetpack libraries.

<p align="center">
  <img src="project-logo.png" width="600" alt="Android Source Explorer Logo">
</p>

## Purpose

When building Android applications, AI tools often rely on outdated training data or incomplete summaries of the Android Framework. This MCP server provides **on-demand, precise access to the actual source code** (AOSP and AndroidX), enabling the AI to understand complex framework internals like the `Activity` lifecycle, `ViewModel` restoration, or `Compose` internals directly from the truth.

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- Git

### Installation Options

#### 1. Homebrew (Recommended for macOS/Linux)
You can install `android-source-explorer` directly using Homebrew:

```bash
brew tap mrmike/android-source-explorer-mcp
brew install android-source-explorer
```

#### 2. Manual Setup with uv
1. Clone the repository:
   ```bash
   git clone <repo-url> android-source-explorer
   cd android-source-explorer
   ```

2. Install dependencies and perform an initial sync:
   ```bash
   # Sync API 36 (Android 16) and common AndroidX packages
   uv run android-source-explorer sync --api-level 36 --androidx "compose,lifecycle,activity"
   
   # (Optional) Download LSP servers for cross-file features
   uv run android-source-explorer sync --lsp
   ```

3. Check sync status:
   ```bash
   uv run android-source-explorer status
   ```

---

## Startup

The project provides a unified CLI. To start the MCP server for an AI client, use the `serve` command:

```bash
uv run android-source-explorer serve
```

---

## Configuration

Add the server to your MCP client (e.g., Claude Desktop, Cursor, Gemini CLI).

### Basic Configuration
```json
{
  "mcpServers": {
    "android-sources": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/android-source-explorer", "android-source-explorer", "serve"]
    }
  }
}
```

### With LSP Features Enabled
```json
{
  "mcpServers": {
    "android-sources": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/android-source-explorer", "android-source-explorer", "serve"],
      "env": {
        "ANDROID_SOURCE_LSP": "true"
      }
    }
  }
}
```

---

## How It Works

### 1. Hybrid Architecture (Tree-sitter + LSP)
The server uses a **dual-engine approach** to balance speed and intelligence:
- **Tree-sitter (Surgical Engine):** Provides near-instant (sub-10ms) AST parsing of single files. It precisely extracts method bodies (including Javadoc and annotations), class members, and inheritance hierarchies without the overhead of a full compiler.
- **LSP (Global Engine):** Optionally leverages the **Eclipse JDT LS** (Java) and **Kotlin Language Server** for cross-file navigation. This enables finding references across millions of lines of code and resolving types that span multiple libraries.

### 2. Local Sync Strategy
To ensure all lookups are instant and offline-ready, the server uses a `sync` command to pre-fetch sources into a local cache (`~/.android-sources/`):
- **AOSP:** Fetches framework sources directly from `android.googlesource.com` using git sparse-checkouts.
- **AndroidX:** Downloads `-sources.jar` files from the Google Maven repository (`dl.google.com/dl/android/maven2/`).
- **Hybrid Indexing:** Prioritizes your local `$ANDROID_HOME` sources if available, supplemented by the downloaded cache.

---

## Available Tools

| Tool | Engine | Description |
|------|--------|-------------|
| `search_classes` | Index | Search for classes by glob pattern or substring. |
| `lookup_class` | FS | Retrieve the full source code for a specific class. |
| `lookup_method` | Tree-sitter | Extract a precise method body + its Javadoc/annotations. |
| `list_class_members` | Tree-sitter | List all method and field signatures in a class. |
| `get_class_hierarchy` | Tree-sitter | Get the inheritance chain (superclass + interfaces). |
| `search_in_source` | FS/Regex | Search for text/regex across the entire source tree. |
| `goto_definition`* | LSP | Resolve the cross-file definition of a symbol. |
| `find_references`* | LSP | Find all usages of a class/method across the whole tree. |
| `get_type_info`* | LSP | Get documentation and type info via hover data. |

*\*Requires `ANDROID_SOURCE_LSP=true`*

---

## License
Apache License 2.0
