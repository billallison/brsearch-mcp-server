# URL Text Fetcher MCP Server

A Model Context Protocol (MCP) server that provides URL text fetching, web scraping, and web search capabilities for use with LM Studio and other MCP-compatible clients.

## Features

This MCP server enables AI models to:
- **Fetch text content** from any URL by extracting all visible text
- **Extract links** from web pages to discover related resources
- **Search the web** using Brave Search and automatically fetch content from top results
- **Handle errors gracefully** with proper timeout and exception handling

## Tools

The server provides three main tools:

### `fetch_url_text`
- **Description**: Downloads all visible text from a URL
- **Parameters**: 
  - `url` (string, required): The URL to fetch text from
- **Returns**: Clean text content from the webpage

### `fetch_page_links`
- **Description**: Extracts all links from a web page
- **Parameters**: 
  - `url` (string, required): The URL to fetch links from  
- **Returns**: List of all href links found on the page

### `brave_search_and_fetch`
- **Description**: Search the web using Brave Search and automatically fetch content from the top results
- **Parameters**: 
  - `query` (string, required): The search query
  - `max_results` (integer, optional): Maximum number of results to fetch content for (default: 3, max: 10)
- **Returns**: Search results with full text content from each result URL

## Prerequisites

### Brave Search API Key
To use the search functionality, you'll need a free Brave Search API key:

1. Visit [Brave Search API](https://api.search.brave.com/)
2. Sign up for a free account (2,000 queries/month, max 1 per second)
3. Get your API key
4. Copy `.env.example` to `.env` and add your API key:
   ```bash
   cp .env.example .env
   # Edit .env and set: BRAVE_API_KEY=your_actual_api_key
   ```

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   uv sync --dev --all-extras
   ```
3. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env file and set your BRAVE_API_KEY
   ```

## Usage

### With LM Studio

1. Open LM Studio and navigate to the Integrations section
2. Click "Install" then "Edit mcp.json"
3. **Option A: Use the configuration helper script**
   ```bash
   ./configure_lmstudio.sh
   ```
   This will generate the correct configuration with the right paths for your system.

4. **Option B: Manual configuration** - Add the server configuration:

```json
{
  "mcpServers": {
    "url-text-fetcher": {
      "command": "/Users/wallison/.local/bin/uv",
      "args": [
        "run", 
        "url-text-fetcher"
      ],
      "cwd": "/Users/wallison/TechProjects/mcp-server"
    }
  }
```

**Note:** The API key will be automatically loaded from your `.env` file in the project directory.

5. Save the configuration and restart LM Studio
6. The server will appear in the Integrations section

### Standalone Usage

You can also run the server directly:

```bash
# Make sure your .env file has BRAVE_API_KEY set
uv run url-text-fetcher
```

## Examples

Once configured with LM Studio, you can ask the AI to:

- "Fetch the text content from https://example.com"
- "Get all the links from https://news.example.com" 
- "Search for 'Python web scraping' and show me the content from the top 3 results"
- "What's the latest news about AI? Search and get the full articles"
- "Find information about MCP servers and fetch the detailed content"

## Dependencies

- `mcp>=1.12.3` - Model Context Protocol framework
- `requests>=2.31.0` - HTTP library for web requests and Brave Search API
- `beautifulsoup4>=4.12.0` - HTML parsing and text extraction

## Configuration

The server can be configured via the `.env` file:

```bash
# Required: Brave Search API Key
BRAVE_API_KEY=your_api_key_here

# Brave Search API Rate Limit (requests per second)
# Free tier: 1 request per second (default)
# Paid tier: 20 requests per second  
# Higher tier: 50 requests per second
# Set this to match your subscription level
BRAVE_RATE_LIMIT_RPS=1

# Optional: Request timeout in seconds (default: 10)
REQUEST_TIMEOUT=10

# Optional: Content length limit in characters (default: 5000)
CONTENT_LENGTH_LIMIT=5000

# Optional: Maximum response size in bytes (default: 10MB)
MAX_RESPONSE_SIZE=10485760
```

### Brave Search Subscription Tiers

The server automatically adjusts its rate limiting based on your Brave Search subscription:

- **Free Tier**: 1 request per second (`BRAVE_RATE_LIMIT_RPS=1`)
- **Paid Tier**: 20 requests per second (`BRAVE_RATE_LIMIT_RPS=20`)
- **Higher Tier**: 50 requests per second (`BRAVE_RATE_LIMIT_RPS=50`)

The server will enforce the configured rate limit across all concurrent requests to ensure you stay within your API quota.

See `.env.example` for a template.

## Development

This project uses:
- **Python 3.13+**
- **uv** for dependency management
- **MCP SDK** for protocol implementation

To set up for development:
1. Clone the repository
2. Run `uv sync --dev --all-extras`
3. Make your changes
4. Test with MCP-compatible clients

## Troubleshooting

### LM Studio Configuration Issues

If you see errors like "Failed to spawn: `url-text-fetcher`" in LM Studio logs:

1. **Run the configuration helper:**
   ```bash
   ./configure_lmstudio.sh
   ```

2. **Make sure you're using full paths:**
   - Use the full path to `uv` (e.g., `/Users/username/.local/bin/uv`)
   - Include the `cwd` (current working directory) in your configuration
   - Set the `BRAVE_API_KEY` environment variable

3. **Test the server manually:**
   ```bash
   uv run url-text-fetcher
   ```
   The server should start and wait for input (press Ctrl+C to exit).

4. **Check your API key:**
   ```bash
   # Check if your .env file has the API key set
   cat .env | grep BRAVE_API_KEY
   ```

   Or test manually:
   ```bash
   export BRAVE_API_KEY=your_actual_api_key
   echo $BRAVE_API_KEY  # Should show your key
   ```

### Common Issues

- **"BRAVE_API_KEY environment variable is required"**: Make sure your `.env` file contains `BRAVE_API_KEY=your_actual_api_key`
- **"Network error"**: Check your internet connection and API key validity
- **"Content truncated"**: Normal behavior for very long web pages (content is limited to 5000 characters by default)

## Error Handling

The server includes robust error handling for:
- Network timeouts (10-second default)
- Invalid URLs
- HTTP errors (4xx, 5xx responses)
- Parsing failures
- Missing API keys
- General exceptions

All errors are returned as descriptive text messages to help users understand what went wrong.

## Development

This project uses:
- **Python 3.13+**
- **uv** for dependency management
- **MCP SDK** for protocol implementation

To set up for development:
1. Clone the repository
2. Run `uv sync --dev --all-extras`
3. Make your changes
4. Test with MCP-compatible clients

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /Users/wallison/TechProjects/mcp-server run url-text-fetcher
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

## License

MIT License - see LICENSE file for details