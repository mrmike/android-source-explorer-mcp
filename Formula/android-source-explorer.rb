class AndroidSourceExplorer < Formula
  include Language::Python::Virtualenv

  desc "MCP server for exploring AOSP internals and Jetpack libraries"
  homepage "https://github.com/mrmike/android-source-explorer-mcp"
  url "https://github.com/mrmike/android-source-explorer-mcp/archive/refs/tags/v0.1.1.tar.gz"
  sha256 "81064d193efa269e94276a174ac7b38022fc176a03678357b459e889c0365147" # Placeholder
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
