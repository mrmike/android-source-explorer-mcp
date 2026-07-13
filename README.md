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
- [uv](https://github.com/astral-sh/uv) (Recommended) or Python 3.11+
- Git

### Recommended Installation (via uv)

The easiest way to install and keep `android-source-explorer` up to date is using `uv`. It handles dependencies (including native ones like Tree-sitter and Cryptography) reliably across platforms.

```bash
uv tool install git+https://github.com/mrmike/android-source-explorer-mcp
```

This will make the `android-source-explorer` command available globally in your PATH.

### Initial Sync

After installation, you need to perform an initial sync to fetch the Android source code:

```bash
# Sync API 36 (Android 16) and common AndroidX packages
android-source-explorer sync --api-level 36 --androidx "compose,lifecycle,activity"

# (Optional) Download LSP servers for cross-file features
android-source-explorer sync --lsp
```

Check sync status:
```bash
android-source-explorer status
```

### Keeping Sources Up-to-Date

To check for and download the latest available Android Framework revisions (AOSP tags) and newer stable versions of your synced AndroidX packages, run:

```bash
# Update all synced framework APIs and AndroidX packages, then rebuild the index
android-source-explorer update

# (Optional) Clean up older versions of updated AndroidX packages
android-source-explorer update --clean

# Update only a specific API level or AndroidX package
android-source-explorer update --api-level 36
android-source-explorer update --androidx activity-compose
```

---

## Configuration

Add the MCP server to your configuration file (e.g., Claude Desktop, Cursor, Gemini CLI).

### Global Usage (Recommended)
If installed via `uv tool install`, the tool is available globally.

**Basic Setup:**
```json
{
  "mcpServers": {
    "android-sources": {
      "command": "android-source-explorer",
      "args": ["serve"]
    }
  }
}
```

**With LSP Features Enabled:**
```json
{
  "mcpServers": {
    "android-sources": {
      "command": "android-source-explorer",
      "args": ["serve"],
      "env": {
        "ANDROID_SOURCE_LSP": "true"
      }
    }
  }
}
```

### Development Usage
If you cloned the repository and want to run it from the source:

```json
{
  "mcpServers": {
    "android-sources": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/android-source-explorer", "android-source-explorer", "serve"]
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
To ensure all lookups are instant and offline-ready, the server uses a `sync` or `update` command to manage sources in a local cache (`~/.android-sources/`):
- **AOSP:** Fetches framework sources directly from `android.googlesource.com` using git sparse-checkouts.
- **AndroidX:** Downloads `-sources.jar` files from the Google Maven repository (`dl.google.com/dl/android/maven2/`).
- **Hybrid Indexing:** Prioritizes your local `$ANDROID_HOME` sources if available, supplemented by the downloaded cache.
- **Automatic Updates:** The `update` command queries remote endpoints (AOSP Git tags & Google Maven indexes) for updates, downloads newer revisions/versions, and rebuilds the class index.

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
