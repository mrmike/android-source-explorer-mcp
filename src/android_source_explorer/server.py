from mcp.server.fastmcp import FastMCP
from .config import config
import json
import fnmatch
from pathlib import Path
from .parser.tree_sitter_parser import parse_file, extract_method, extract_class_members, extract_class_hierarchy

# Create FastMCP server
mcp = FastMCP(
    "android-sources",
    dependencies=["mcp[cli]", "tree-sitter", "tree-sitter-java", "tree-sitter-kotlin", "httpx"]
)

@mcp.on_shutdown()
async def on_shutdown():
    """Ensure LSP processes are cleaned up on server shutdown."""
    if config.lsp_enabled:
        from .lsp.lsp_manager import lsp_manager
        await lsp_manager.shutdown()

def get_index() -> dict[str, str]:
    if not config.class_index_path.exists():
        raise RuntimeError("Class index not found. Please run 'android-source-explorer sync' first.")
    with open(config.class_index_path, "r", encoding="utf-8") as f:
        return json.load(f)

@mcp.tool()
def search_classes(pattern: str, limit: int = 20) -> list[str]:
    """Search for classes by glob pattern or substring (e.g. '*ViewModel*' or 'Activity')."""
    try:
        index = get_index()
    except RuntimeError as e:
        return [str(e)]
        
    results = []
    use_glob = "*" in pattern or "?" in pattern
    pattern_lower = pattern.lower()
    
    for fqcn in index.keys():
        class_simple_name = fqcn.split(".")[-1]
        
        if use_glob:
            match = fnmatch.fnmatch(class_simple_name.lower(), pattern_lower) or fnmatch.fnmatch(fqcn.lower(), pattern_lower)
        else:
            match = pattern_lower in fqcn.lower()
            
        if match:
            results.append(fqcn)
            if len(results) >= limit:
                break
                
    return results

@mcp.tool()
def lookup_class(class_name: str, max_lines: int = 500) -> str:
    """Retrieve the full source code for a given Android Framework or AndroidX class."""
    try:
        index = get_index()
    except RuntimeError as e:
        return str(e)
        
    if class_name not in index:
        return f"Class {class_name} not found. Try searching with search_classes."
        
    path = Path(index[class_name])
    if not path.exists():
        return f"File {path} not found on disk. Your cache may be incomplete."
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        if len(lines) > max_lines:
            return "".join(lines[:max_lines]) + f"\n\n... (truncated after {max_lines} lines)"
        return "".join(lines)
    except Exception as e:
        return f"Error reading file: {e}"

@mcp.tool()
async def lookup_method(class_name: str, method_name: str) -> str:
    """Look up a specific method's source code within a class."""
    try:
        index = get_index()
    except RuntimeError as e:
        return str(e)
        
    if class_name not in index:
        return f"Class {class_name} not found."
        
    file_path = Path(index[class_name])
    if not file_path.exists():
        return f"File {file_path} not found on disk."
        
    try:
        tree, source_code, language = parse_file(file_path)
        method_source = extract_method(tree, source_code, language, method_name, class_filter=class_name)
        
        if method_source:
            return method_source
        else:
            return f"Method {method_name} not found in {class_name}."
    except Exception as e:
        return f"Failed to parse or extract method: {e}"

@mcp.tool()
def list_class_members(class_name: str) -> list[str]:
    """List all method and field signatures for a given class."""
    try:
        index = get_index()
    except RuntimeError as e:
        return [str(e)]
        
    if class_name not in index:
        return [f"Class {class_name} not found."]
        
    file_path = Path(index[class_name])
    if not file_path.exists():
        return [f"File {file_path} not found on disk."]
        
    try:
        tree, source_code, language = parse_file(file_path)
        members = extract_class_members(tree, source_code, language, class_filter=class_name)
        return members if members else ["No members found or failed to parse."]
    except Exception as e:
        return [f"Failed to parse class: {e}"]

@mcp.tool()
def search_in_source(pattern: str, class_name: str = None, limit: int = 20) -> list[str]:
    """Search for a text/regex pattern within a specific class or across all synced files (if class_name is omitted)."""
    import re
    try:
        index = get_index()
    except RuntimeError as e:
        return [str(e)]
        
    results = []
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return [f"Invalid regex pattern: {e}"]
    
    files_to_search = []
    if class_name:
        if class_name in index:
            files_to_search.append((class_name, Path(index[class_name])))
        else:
            return [f"Class {class_name} not found."]
    else:
        for fqcn, path_str in index.items():
            files_to_search.append((fqcn, Path(path_str)))
            
    for fqcn, path in files_to_search:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    if regex.search(line):
                        results.append(f"{fqcn}:{line_num}: {line.strip()}")
                        if len(results) >= limit:
                            return results
        except Exception:
            continue
            
    return results if results else ["No matches found."]

@mcp.tool()
def list_available_versions(artifact: str = None) -> str:
    """List available versions for an AndroidX artifact (e.g. 'androidx.compose.runtime:runtime')."""
    from .sync.artifact_catalog import get_artifacts_in_group
    
    if not artifact or ":" not in artifact:
        return "Please provide an artifact in 'group:artifact' format, e.g. 'androidx.compose.runtime:runtime'."
        
    group, name = artifact.split(":", 1)
    artifacts = get_artifacts_in_group(group)
    
    if name in artifacts:
        versions = artifacts[name]
        return f"Available versions for {artifact}:\n" + "\n".join(versions)
    else:
        return f"Artifact {name} not found in group {group}."

@mcp.tool()
def get_class_hierarchy(class_name: str) -> str:
    """Get the inheritance hierarchy (superclass and interfaces) for a class."""
    try:
        index = get_index()
    except RuntimeError as e:
        return str(e)
        
    if class_name not in index:
        return f"Class {class_name} not found."
        
    file_path = Path(index[class_name])
    if not file_path.exists():
        return f"File {file_path} not found on disk."
        
    try:
        tree, source_code, language = parse_file(file_path)
        hierarchy = extract_class_hierarchy(tree, source_code, language, class_name=class_name)
        
        result = f"Hierarchy for {class_name}:\n"
        if hierarchy["superclass"]:
            result += f"Superclass: {hierarchy['superclass']}\n"
        if hierarchy["interfaces"]:
            result += f"Interfaces: {', '.join(hierarchy['interfaces'])}\n"
            
        if not hierarchy["superclass"] and not hierarchy["interfaces"]:
            result += "No explicit superclass or interfaces found."
            
        return result
    except Exception as e:
        return f"Failed to parse hierarchy: {e}"

@mcp.tool()
def check_integrity() -> str:
    """Check the integrity of the local source cache and index."""
    try:
        index = get_index()
    except RuntimeError as e:
        return str(e)
        
    total = len(index)
    missing = 0
    for path_str in index.values():
        if not Path(path_str).exists():
            missing += 1
            
    if missing == 0:
        return f"Integrity check passed: {total} classes indexed and all files exist on disk."
    else:
        return f"Integrity check failed: {missing} out of {total} indexed files are missing from disk. Run 'sync' to fix."

# LSP Tools (Optional, enabled by env var)

@mcp.tool()
async def goto_definition(class_name: str, line: int, character: int) -> str:
    """Resolve the definition of a symbol at a specific position (Requires LSP)."""
    if not config.lsp_enabled:
        return "LSP tools are not enabled. Set ANDROID_SOURCE_LSP=true to enable."
    
    from .lsp.lsp_manager import lsp_manager
    index = get_index()
    if class_name not in index:
        return f"Class {class_name} not found."
    
    file_path = Path(index[class_name])
    client = await lsp_manager.get_client_for_file(file_path)
    if not client:
        return f"No LSP server available for {file_path.suffix} files."
    
    response = await client.send_request("textDocument/definition", {
        "textDocument": {"uri": file_path.as_uri()},
        "position": {"line": line - 1, "character": character}
    })
    
    # Handle response (Location or Location[])
    result = response.get("result")
    if not result:
        return "Definition not found."
    
    if isinstance(result, list):
        result = result[0]
    
    uri = result["uri"]
    target_path = Path(uri.replace("file://", ""))
    target_range = result["range"]["start"]
    
    # Use Tree-sitter to show context at target
    try:
        tree, src, lang = parse_file(target_path)
        # Find the method or class at that position
        # For now, just return the file and line
        return f"Defined in {target_path} at line {target_range['line'] + 1}"
    except Exception:
        return f"Defined in {uri} at line {target_range['line'] + 1}"

@mcp.tool()
async def find_references(class_name: str, line: int, character: int) -> list[str]:
    """Find all references to a symbol at a specific position (Requires LSP)."""
    if not config.lsp_enabled:
        return ["LSP tools are not enabled. Set ANDROID_SOURCE_LSP=true to enable."]
    
    from .lsp.lsp_manager import lsp_manager
    index = get_index()
    if class_name not in index:
        return [f"Class {class_name} not found."]
    
    file_path = Path(index[class_name])
    client = await lsp_manager.get_client_for_file(file_path)
    if not client:
        return [f"No LSP server available for {file_path.suffix} files."]
    
    response = await client.send_request("textDocument/references", {
        "textDocument": {"uri": file_path.as_uri()},
        "position": {"line": line - 1, "character": character},
        "context": {"includeDeclaration": False}
    })
    
    results = []
    for ref in response.get("result", []):
        uri = ref["uri"]
        line_num = ref["range"]["start"]["line"] + 1
        results.append(f"{uri} at line {line_num}")
    
    return results if results else ["No references found."]

@mcp.tool()
async def get_type_info(class_name: str, line: int, character: int) -> str:
    """Get type information and documentation (hover) for a symbol (Requires LSP)."""
    if not config.lsp_enabled:
        return "LSP tools are not enabled. Set ANDROID_SOURCE_LSP=true to enable."
    
    from .lsp.lsp_manager import lsp_manager
    index = get_index()
    if class_name not in index:
        return f"Class {class_name} not found."
    
    file_path = Path(index[class_name])
    client = await lsp_manager.get_client_for_file(file_path)
    if not client:
        return f"No LSP server available for {file_path.suffix} files."
    
    response = await client.send_request("textDocument/hover", {
        "textDocument": {"uri": file_path.as_uri()},
        "position": {"line": line - 1, "character": character}
    })
    
    result = response.get("result")
    if not result:
        return "No type info available."
    
    contents = result.get("contents", "")
    if isinstance(contents, dict):
        return contents.get("value", str(contents))
    elif isinstance(contents, list):
        return "\n".join([str(c) if not isinstance(c, dict) else c.get("value", "") for c in contents])
    return str(contents)
