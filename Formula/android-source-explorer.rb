class AndroidSourceExplorer < Formula
  desc "MCP server for exploring AOSP internals and Jetpack libraries"
  homepage "https://github.com/mrmike/android-source-explorer-mcp"
  url "https://github.com/mrmike/android-source-explorer-mcp/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "4aaabf4d664ea56174e41f070e4c4a544f49539369e134c0d88db1451d509860"
  license "Apache-2.0"

  depends_on "python@3.12"
  depends_on "uv" => :build

  def install
    venv = libexec/".venv"
    
    # Create an isolated virtualenv using Homebrew's python
    system "uv", "venv", venv, "--python", Formula["python@3.12"].opt_bin/"python3.12"
    
    # Install the package using uv. 
    # uv handles binary wheels (like cryptography and tree-sitter) perfectly.
    system "uv", "pip", "install", "--python", venv/"bin/python", "--no-cache", "."

    # Create a wrapper script in the bin directory
    (bin/"android-source-explorer").write_env_script venv/"bin/android-source-explorer", {}
  end

  test do
    system "#{bin}/android-source-explorer", "--help"
  end
end
