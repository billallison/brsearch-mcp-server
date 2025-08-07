import asyncio
import requests
from bs4 import BeautifulSoup
from typing import List
import os
from pathlib import Path

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio

# Load environment variables from .env file if it exists
def load_env():
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if value and key not in os.environ:
                        os.environ[key] = value

load_env()

# Configuration from environment variables
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))
CONTENT_LENGTH_LIMIT = int(os.getenv('CONTENT_LENGTH_LIMIT', '5000'))

server = Server("url-text-fetcher")

def fetch_url_content(url: str) -> str:
    """
    Helper function to fetch text content from a URL.
    Returns the text content or an error message.
    """
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text_content = soup.get_text(separator="\n", strip=True)
        
        # Limit content length to avoid extremely long responses
        if len(text_content) > CONTENT_LENGTH_LIMIT:
            text_content = text_content[:CONTENT_LENGTH_LIMIT] + "... [Content truncated]"
            
        return text_content
    except Exception as e:
        return f"Error fetching content: {str(e)}"

def brave_search(query: str, count: int = 10) -> List[dict]:
    """
    Perform a Brave search and return results.
    """
    api_key = os.getenv('BRAVE_API_KEY')
    if not api_key:
        raise ValueError("BRAVE_API_KEY environment variable is required")
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": query,
        "count": count,
        "search_lang": "en",
        "country": "US",
        "safesearch": "moderate"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        results = []
        if 'web' in data and 'results' in data['web']:
            for result in data['web']['results']:
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'description': result.get('description', ''),
                })
        
        return results
    except Exception as e:
        raise Exception(f"Brave search failed: {str(e)}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="fetch_url_text",
            description="Download all visible text from a URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch text from"
                    },
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="fetch_page_links",
            description="Return a list of all links on the page",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch links from"
                    },
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="brave_search_and_fetch",
            description="Search the web using Brave Search and automatically fetch content from the top results",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to fetch content for (default: 3)",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 10
                    },
                },
                "required": ["query"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can fetch text content or links from web pages, or search and fetch.
    """
    if not arguments:
        raise ValueError("Missing arguments")

    try:
        if name == "fetch_url_text":
            url = arguments.get("url")
            if not url:
                raise ValueError("Missing URL")
                
            # Download all visible text from a URL
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            text_content = soup.get_text(separator="\n", strip=True)
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Text content from {url}:\n\n{text_content}",
                )
            ]
            
        elif name == "fetch_page_links":
            url = arguments.get("url")
            if not url:
                raise ValueError("Missing URL")
                
            # Return a list of all links on the page
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            
            links_text = "\n".join(f"- {link}" for link in links)
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Links found on {url}:\n\n{links_text}",
                )
            ]
            
        elif name == "brave_search_and_fetch":
            query = arguments.get("query")
            if not query:
                raise ValueError("Missing search query")
                
            max_results = arguments.get("max_results", 3)
            
            # Perform Brave search
            search_results = brave_search(query, count=max_results * 2)  # Get more results to account for failed fetches
            
            if not search_results:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No search results found for query: {query}",
                    )
                ]
            
            # Build response with search results and content
            response_parts = [f"Search Results for: {query}\n" + "="*50 + "\n"]
            
            fetched_count = 0
            for i, result in enumerate(search_results):
                if fetched_count >= max_results:
                    break
                    
                title = result.get('title', 'No title')
                url = result.get('url', '')
                description = result.get('description', 'No description')
                
                response_parts.append(f"\n{fetched_count + 1}. {title}")
                response_parts.append(f"URL: {url}")
                response_parts.append(f"Description: {description}")
                response_parts.append("-" * 40)
                
                # Fetch content from this URL
                if url:
                    content = fetch_url_content(url)
                    response_parts.append(f"Content:\n{content}")
                    response_parts.append("=" * 50)
                    fetched_count += 1
                else:
                    response_parts.append("No URL available for content fetching")
                    response_parts.append("=" * 50)
            
            final_response = "\n".join(response_parts)
            
            return [
                types.TextContent(
                    type="text",
                    text=final_response,
                )
            ]
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except requests.RequestException as e:
        return [
            types.TextContent(
                type="text",
                text=f"Network error: {str(e)}",
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}",
            )
        ]

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="url-text-fetcher",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )