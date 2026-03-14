import tomllib
from pathlib import Path

def generate_resources():
    lock_path = Path("uv.lock")
    if not lock_path.exists():
        print("uv.lock not found")
        return

    with open(lock_path, "rb") as f:
        lock_data = tomllib.load(f)

    packages = lock_data.get("package", [])
    
    # We want to find all dependencies of our project
    # and their recursive dependencies.
    # For simplicity, since Homebrew's virtualenv_install_with_resources 
    # expects all required non-project packages as resources:
    
    project_name = "android-source-explorer"
    
    resources = []
    for pkg in packages:
        name = pkg.get("name")
        if name == project_name:
            continue
            
        version = pkg.get("version")
        sdist = pkg.get("sdist")
        
        if not sdist:
            # Some packages might only have wheels in uv.lock if sdist isn't available
            # but usually uv prefers sdists for the lock if it can.
            # If no sdist, we'll skip for now or handle wheels if absolutely necessary.
            # Homebrew virtualenv_install_with_resources prefers sdists.
            continue
            
        url = sdist.get("url")
        sha256 = sdist.get("hash")
        
        # uv hashes are often prefixed with sha256:
        if sha256.startswith("sha256:"):
            sha256 = sha256[7:]
            
        resource_block = f'  resource "{name}" do\n'
        resource_block += f'    url "{url}"\n'
        resource_block += f'    sha256 "{sha256}"\n'
        resource_block += '  end\n'
        resources.append(resource_block)
        
    return "\n".join(resources)

if __name__ == "__main__":
    print(generate_resources())
