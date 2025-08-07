#!/bin/bash

# LM Studio MCP Configuration Script for FastMCP Server
# This script helps configure the URL Text Fetcher MCP server with LM Studio

echo "🔧 LM Studio MCP Configuration for URL Text Fetcher (FastMCP)"
echo "============================================================"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your API keys."
else
    echo "✅ Found existing .env file"
fi

# Display current directory for reference
CURRENT_DIR=$(pwd)
echo "📁 Current directory: $CURRENT_DIR"

# Get the Python interpreter path
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    PYTHON_PATH=$(which python)
fi

if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Python not found. Please install Python 3.13+"
    exit 1
fi

echo "🐍 Using Python: $PYTHON_PATH"

# Check if uv is available
UV_PATH=$(which uv)
if [ -n "$UV_PATH" ]; then
    echo "⚡ Using uv: $UV_PATH"
    PYTHON_CMD="uv run"
    SCRIPT_NAME="url-text-fetcher-fastmcp"
else
    echo "📦 uv not found, using direct Python execution"
    PYTHON_CMD="$PYTHON_PATH -m"
    SCRIPT_NAME="url_text_fetcher.server_fastmcp"
fi

echo ""
echo "📋 LM Studio Configuration"
echo "=========================="
echo ""
echo "Add this server configuration to your LM Studio settings:"
echo ""
echo "Server Name: URL Text Fetcher (FastMCP)"
echo "Command: $PYTHON_CMD"
echo "Arguments: $SCRIPT_NAME"
echo "Working Directory: $CURRENT_DIR"
echo ""

# Create JSON configuration for easy copying
cat << EOF
{
  "servers": {
    "url-text-fetcher-fastmcp": {
      "command": "$PYTHON_CMD",
      "args": ["$SCRIPT_NAME"],
      "cwd": "$CURRENT_DIR",
      "env": {}
    }
  }
}
EOF

echo ""
echo "🌟 Features Available:"
echo "- fetch_url_text: Download all visible text from a URL"
echo "- fetch_page_links: Extract all links from a web page"  
echo "- brave_search_and_fetch: Search web with Brave and fetch content from top results"
echo ""
echo "🔐 Security Features:"
echo "- SSRF protection against internal networks"
echo "- Input sanitization for URLs and queries"
echo "- Content size limits to prevent memory exhaustion"
echo "- Configurable rate limiting for Brave Search API"
echo ""
echo "⚙️  Environment Variables (edit .env file):"
echo "- BRAVE_API_KEY: Your Brave Search API key (required for search)"
echo "- BRAVE_RATE_LIMIT_RPS: Requests per second (1-50, default: 1)"
echo "- REQUEST_TIMEOUT: HTTP request timeout in seconds (default: 10)"
echo "- CONTENT_LENGTH_LIMIT: Max content length per response (default: 5000)"
echo "- MAX_RESPONSE_SIZE: Max HTTP response size in bytes (default: 10MB)"
echo ""
echo "🧪 Test the server:"
if [ -n "$UV_PATH" ]; then
    echo "uv run url-text-fetcher-fastmcp"
else
    echo "$PYTHON_PATH -m url_text_fetcher.server_fastmcp"
fi
echo ""
echo "📚 For more information, see README.md"
