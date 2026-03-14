class AndroidSourceExplorer < Formula
  include Language::Python::Virtualenv

  desc "MCP server for exploring AOSP internals and Jetpack libraries"
  homepage "https://github.com/mrmike/android-source-explorer-mcp"
  url "https://github.com/mrmike/android-source-explorer-mcp/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000" # Placeholder
  license "Apache-2.0"

  depends_on "python@3.12"

  # [RESOURCES_START]
  # [RESOURCES_END]

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/android-source-explorer", "--help"
  end
end
