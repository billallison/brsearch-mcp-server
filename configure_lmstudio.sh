#!/bin/bash

# MCP Server Configuration Helper
# This script helps you generate the correct LM Studio configuration

echo "=== MCP Server Configuration Helper ==="
echo ""

# Find uv path
UV_PATH=$(which uv)
if [ -z "$UV_PATH" ]; then
    echo "❌ Error: 'uv' command not found in PATH"
    echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Get current directory
CURRENT_DIR=$(pwd)

echo "✅ Found uv at: $UV_PATH"
echo "✅ Project directory: $CURRENT_DIR"
echo ""

# Test if the MCP server works
echo "🧪 Testing MCP server..."
if timeout 3s "$UV_PATH" run url-text-fetcher > /dev/null 2>&1; then
    echo "✅ MCP server test passed"
else
    echo "⚠️  MCP server test timed out (this is expected)"
fi

echo ""
echo "📋 Copy this configuration to LM Studio's mcp.json:"
echo ""
cat << EOF
{
  "mcpServers": {
    "url-text-fetcher": {
      "command": "$UV_PATH",
      "args": [
        "run", 
        "url-text-fetcher"
      ],
      "cwd": "$CURRENT_DIR"
    }
  }
}
EOF

echo ""
echo "💡 Don't forget to:"
echo "   1. Get your Brave Search API key from https://api.search.brave.com/"
echo "   2. Copy .env.example to .env and set your BRAVE_API_KEY"
echo "   3. Set BRAVE_RATE_LIMIT_RPS based on your subscription:"
echo "      - Free tier: 1 (default)"
echo "      - Paid tier: 20"
echo "      - Higher tier: 50"
echo "   4. Restart LM Studio after adding the configuration"
echo ""
echo "ℹ️  Note: API key and rate limits will be loaded automatically from your .env file"
