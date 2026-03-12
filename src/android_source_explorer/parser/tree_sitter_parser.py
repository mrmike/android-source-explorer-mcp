import tree_sitter
import tree_sitter_java
import tree_sitter_kotlin
from pathlib import Path

JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
KOTLIN_LANGUAGE = tree_sitter.Language(tree_sitter_kotlin.language())

def parse_file(file_path: Path) -> tuple[tree_sitter.Tree, bytes, tree_sitter.Language]:
    """Parse a Java or Kotlin file and return the AST, source bytes, and language."""
    if file_path.suffix == '.java':
        language = JAVA_LANGUAGE
    elif file_path.suffix == '.kt':
        language = KOTLIN_LANGUAGE
    else:
        raise ValueError(f"Unsupported file extension: {file_path.suffix}")
        
    parser = tree_sitter.Parser(language)
    with open(file_path, "rb") as f:
        source_code = f.read()
    return parser.parse(source_code), source_code, language

def extract_method(tree: tree_sitter.Tree, source_code: bytes, language: tree_sitter.Language, method_name: str, class_filter: str = None) -> str | None:
    """Extract a specific method's source code by its name, optionally filtering by class."""
    
    # If the user provides a nested class name like "WindowManager.LayoutParams",
    # we need to find the right class first.
    target_class = None
    if class_filter and "." in class_filter:
        target_class = class_filter.split(".")[-1]

    def walk(node, current_class=None):
        if node.type in ['class_declaration', 'interface_declaration', 'object_declaration']:
            name_node = node.child_by_field_name('name')
            if name_node:
                current_class = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8', errors='ignore')

        if node.type in ['method_declaration', 'constructor_declaration', 'function_declaration']:
            if target_class and current_class != target_class:
                return None
                
            name_node = node.child_by_field_name('name')
            if name_node:
                name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8', errors='ignore')
                if name == method_name:
                    start_byte = node.start_byte
                    prev = node.prev_sibling
                    while prev and prev.type in ['line_comment', 'block_comment', 'annotation', 'modifiers']:
                        start_byte = prev.start_byte
                        prev = prev.prev_sibling
                    return source_code[start_byte:node.end_byte].decode('utf-8', errors='ignore')
        
        for child in node.children:
            res = walk(child, current_class)
            if res:
                return res
        return None

    return walk(tree.root_node)

def extract_class_members(tree: tree_sitter.Tree, source_code: bytes, language: tree_sitter.Language, class_filter: str = None) -> list[str]:
    """Extract method and field signatures from a class, optionally filtering for inner classes."""
    members = []
    target_class = class_filter.split(".")[-1] if class_filter else None
    
    def walk(node, current_class=None):
        is_class = node.type in ['class_declaration', 'interface_declaration', 'object_declaration']
        if is_class:
            name_node = node.child_by_field_name('name')
            if name_node:
                current_class = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8', errors='ignore')

        # If we are looking for a specific inner class, don't collect members until we find it
        if target_class and current_class != target_class:
            for child in node.children:
                walk(child, current_class)
            return

        if node.type in ['method_declaration', 'field_declaration', 'constructor_declaration', 'function_declaration', 'property_declaration']:
            text = source_code[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')
            signature = text.split('{')[0].split('=')[0].strip()
            signature = " ".join(signature.split())
            members.append(signature)
        
        # Don't recurse into methods for speed, but recurse into everything else
        if node.type not in ['method_declaration', 'function_declaration']:
            for child in node.children:
                walk(child, current_class)

    walk(tree.root_node)
    return members

def extract_class_hierarchy(tree: tree_sitter.Tree, source_code: bytes, language: tree_sitter.Language, class_name: str = None) -> dict:
    """Extract superclass and implemented interfaces for a specific class."""
    hierarchy = {"superclass": None, "interfaces": []}
    target_class = class_name.split(".")[-1] if class_name else None
    
    def walk(node):
        if node.type == 'class_declaration':
            name_node = node.child_by_field_name('name')
            current_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8', errors='ignore') if name_node else None
            
            if target_class and current_name != target_class:
                # Keep searching in children (inner classes)
                for child in node.children:
                    if walk(child): return True
                return False

            # Found the target class
            superclass_node = node.child_by_field_name('superclass')
            if superclass_node:
                for child in superclass_node.children:
                    if child.type in ['type_identifier', 'generic_type', 'scoped_type_identifier']:
                        hierarchy["superclass"] = source_code[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
                        break
            
            interfaces_node = node.child_by_field_name('interfaces')
            if interfaces_node:
                # In Java, 'interfaces' is the super_interfaces node
                for child in interfaces_node.children:
                    if child.type in ['type_list', 'user_type', 'type_identifier']:
                        if child.type == 'type_list':
                            for intf in child.children:
                                if intf.type in ['type_identifier', 'generic_type', 'scoped_type_identifier']:
                                    hierarchy["interfaces"].append(source_code[intf.start_byte:intf.end_byte].decode('utf-8', errors='ignore'))
                        else:
                            hierarchy["interfaces"].append(source_code[child.start_byte:child.end_byte].decode('utf-8', errors='ignore'))
            return True
        
        for child in node.children:
            if walk(child):
                return True
        return False

    walk(tree.root_node)
    return hierarchy
