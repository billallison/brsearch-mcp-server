# Copilot Instructions

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## MCP Server for URL Text Fetching and Web Search

This is a Model Context Protocol (MCP) server project that provides URL text fetching, web scraping, and web search capabilities.

### Project Overview
- **Purpose**: Fetch text content and links from web pages, plus search the web with Brave Search
- **Framework**: MCP (Model Context Protocol) using the official Python SDK
- **Dependencies**: requests, beautifulsoup4, mcp
- **Deployment**: Can be used with LM Studio and other MCP-compatible clients

### Key Features
- `fetch_url_text`: Downloads all visible text from a URL
- `fetch_page_links`: Extracts all links from a web page  
- `brave_search_and_fetch`: Searches the web using Brave Search API and automatically fetches content from top results
- Error handling for network requests and parsing failures
- Configurable timeout for web requests
- Content length limiting to avoid excessive responses

### API Requirements
- **Brave Search API Key**: Required for search functionality
  - Get free API key at https://api.search.brave.com/
  - 2,000 queries/month free tier, max 1 per second
  - Set as environment variable: `BRAVE_API_KEY`

### Development Guidelines
- Follow MCP server conventions for tool definitions
- Use proper error handling for web requests
- Keep tool responses in the expected MCP format
- Test with various URL types and edge cases

### References
- MCP Documentation: https://modelcontextprotocol.io/llms-full.txt
- Python SDK: https://github.com/modelcontextprotocol/create-python-server
