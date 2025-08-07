"""
MCP Server for URL Text Fetching and Web Search - FastMCP Implementation

This implementation follows MCP best practices using FastMCP patterns.
"""

import asyncio
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import os
from pathlib import Path
import time
import threading
import logging
from urllib.parse import urlparse
import ipaddress
import sys

from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field

# Configure logging to stderr only (never stdout for stdio servers)
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,  # Explicitly use stderr to comply with MCP requirements
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Configuration from environment variables with validation
def get_int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid {key} value, using default: {default}")
        return default

# Environment configuration
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY', '')
BRAVE_RATE_LIMIT_RPS = get_int_env('BRAVE_RATE_LIMIT_RPS', 1)  # Default to free tier
REQUEST_TIMEOUT = get_int_env('REQUEST_TIMEOUT', 10)
CONTENT_LENGTH_LIMIT = get_int_env('CONTENT_LENGTH_LIMIT', 5000)
MAX_RESPONSE_SIZE = get_int_env('MAX_RESPONSE_SIZE', 10485760)  # 10MB default

# Validate rate limit configuration
if BRAVE_RATE_LIMIT_RPS < 1:
    logger.warning(f"Invalid BRAVE_RATE_LIMIT_RPS ({BRAVE_RATE_LIMIT_RPS}), using default: 1")
    BRAVE_RATE_LIMIT_RPS = 1
elif BRAVE_RATE_LIMIT_RPS > 50:
    logger.warning(f"Rate limit ({BRAVE_RATE_LIMIT_RPS}) exceeds maximum tier (50), capping at 50")
    BRAVE_RATE_LIMIT_RPS = 50

# Calculate minimum interval between requests (in seconds)
MIN_REQUEST_INTERVAL = 1.0 / BRAVE_RATE_LIMIT_RPS

logger.info(f"Brave Search rate limit configured: {BRAVE_RATE_LIMIT_RPS} requests/second (interval: {MIN_REQUEST_INTERVAL:.3f}s)")

# Standard HTTP headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; MCP-URL-Fetcher/1.0)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# Thread-safe rate limiting for Brave Search API
rate_limit_lock = threading.Lock()
last_brave_request = [0]  # Using list for mutable reference

# Create FastMCP server instance
mcp = FastMCP("url-text-fetcher")

def sanitize_query(query: str) -> str:
    """
    Sanitize search query to prevent injection attacks and malformed requests.
    """
    if not query or not isinstance(query, str):
        return ""
    
    # Remove null bytes and control characters
    query = ''.join(char for char in query if ord(char) >= 32 or char in '\t\n\r')
    
    # Limit query length to prevent abuse
    max_query_length = 500
    if len(query) > max_query_length:
        query = query[:max_query_length]
        logger.warning(f"Query truncated to {max_query_length} characters")
    
    # Remove potentially dangerous patterns
    dangerous_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if pattern in query_lower:
            logger.warning(f"Potentially dangerous pattern detected in query: {pattern}")
            query = query.replace(pattern, '')
    
    return query.strip()

def sanitize_url(url: str) -> str:
    """
    Basic URL sanitization and normalization.
    """
    if not url or not isinstance(url, str):
        return ""
    
    # Remove whitespace and control characters
    url = ''.join(char for char in url if ord(char) >= 32 or char in '\t\n\r')
    url = url.strip()
    
    # Ensure URL has protocol
    if url and not url.startswith(('http://', 'https://')):
        # Don't auto-add protocol for security reasons
        logger.warning(f"URL missing protocol: {url}")
        return ""
    
    return url

def is_safe_url(url: str) -> bool:
    """
    Validate URL is safe to fetch - prevents SSRF attacks.
    """
    try:
        parsed = urlparse(url)
        
        # Only allow http/https
        if parsed.scheme not in ['http', 'https']:
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
            
        # Block common internal/metadata hostnames
        blocked_hostnames = [
            'localhost', 'metadata.google.internal',
            '169.254.169.254',  # AWS/GCP metadata
            'metadata'
        ]
        
        if hostname.lower() in blocked_hostnames:
            return False
            
        # Try to resolve hostname to IP to check for internal addresses
        try:
            import socket
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)
            
            # Block private/internal IP ranges
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                return False
                
        except socket.gaierror:
            # DNS resolution failed - domain doesn't exist or network issue
            # For legitimate domains, this could be a temporary DNS issue
            # But for safety in production, we should block unknown domains
            return False
        except ValueError:
            # Invalid IP address format
            return False
            
        return True
        
    except Exception:
        # Any other parsing error - block to be safe
        return False

def fetch_url_content(url: str) -> str:
    """
    Helper function to fetch text content from a URL with safety checks.
    Returns the text content or an error message.
    """
    # Validate URL safety first
    if not is_safe_url(url):
        logger.warning(f"SECURITY: Blocked unsafe URL: {url}")
        return "Error: URL not allowed for security reasons"
    
    try:
        # Log request for monitoring
        logger.info(f"REQUEST: Fetching content from {url}")
        
        # Make request with streaming to check size
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
        resp.raise_for_status()
        
        # Log response details
        logger.info(f"RESPONSE: {resp.status_code} from {url}, Content-Type: {resp.headers.get('Content-Type', 'unknown')}")
        
        # Check content length header
        content_length = resp.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_RESPONSE_SIZE:
            logger.warning(f"SECURITY: Content too large: {content_length} bytes for {url}")
            return f"Error: Content too large ({content_length} bytes, max {MAX_RESPONSE_SIZE})"

        # Read content with size limit
        content_chunks = []
        total_size = 0
        
        try:
            for chunk in resp.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:  # filter out keep-alive new chunks
                    total_size += len(chunk)
                    if total_size > MAX_RESPONSE_SIZE:
                        logger.warning(f"SECURITY: Content exceeded size limit for {url}")
                        return f"Error: Content exceeded size limit ({MAX_RESPONSE_SIZE} bytes)"
                    content_chunks.append(chunk)
        except UnicodeDecodeError:
            # If we can't decode as text, it's probably binary content
            logger.warning(f"CONTENT: Unable to decode content as text from {url}")
            return "Error: Unable to decode content as text"
        
        html_content = ''.join(content_chunks)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text_content = soup.get_text(separator="\n", strip=True)
        
        # Limit final content length
        if len(text_content) > CONTENT_LENGTH_LIMIT:
            logger.info(f"CONTENT: Truncating content from {url} ({len(text_content)} -> {CONTENT_LENGTH_LIMIT} chars)")
            text_content = text_content[:CONTENT_LENGTH_LIMIT] + "... [Content truncated]"
        
        logger.info(f"SUCCESS: Fetched {len(text_content)} characters from {url}")
        return text_content
        
    except requests.RequestException as e:
        logger.error(f"REQUEST_ERROR: Failed to fetch {url}: {e}")
        return "Error: Unable to fetch URL content"
    except Exception as e:
        logger.error(f"UNEXPECTED_ERROR: Processing {url}: {e}", exc_info=True)
        return "Error: An unexpected error occurred while processing the URL"

def brave_search(query: str, count: int = 10) -> List[dict]:
    """
    Perform a Brave search and return results.
    Respects the configurable request rate limit with thread safety.
    """
    if not BRAVE_API_KEY:
        logger.error("Brave Search API key not configured")
        raise ValueError("BRAVE_API_KEY environment variable is required")
    
    # Thread-safe rate limiting: ensure minimum interval between requests
    with rate_limit_lock:
        current_time = time.time()
        time_since_last_request = current_time - last_brave_request[0]
        if time_since_last_request < MIN_REQUEST_INTERVAL:
            sleep_time = MIN_REQUEST_INTERVAL - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.3f} seconds (limit: {BRAVE_RATE_LIMIT_RPS} req/s)")
            time.sleep(sleep_time)
        last_brave_request[0] = time.time()
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        **HEADERS,
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": count,
        "search_lang": "en",
        "country": "US",
        "safesearch": "moderate"
    }
    
    try:
        logger.info(f"SEARCH_REQUEST: Making Brave Search for '{query}' (count={count})")
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
        
        logger.info(f"SEARCH_SUCCESS: Found {len(results)} results for '{query}'")
        return results
    except requests.HTTPError as e:
        logger.error(f"Brave Search API error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 422:
            raise Exception("Search request was rejected - please check your query")
        elif e.response.status_code == 429:
            raise Exception("Rate limit exceeded - please wait before making another request")
        else:
            raise Exception("Search service temporarily unavailable")
    except requests.RequestException as e:
        logger.error(f"Network error during search: {e}")
        raise Exception("Network error occurred during search")
    except Exception as e:
        logger.error(f"Unexpected error in brave_search: {e}", exc_info=True)
        raise Exception("An unexpected error occurred during search")

# MCP Tools using FastMCP decorators

@mcp.tool()
def fetch_url_text(url: str = Field(description="The URL to fetch text from")) -> str:
    """Download all visible text from a URL"""
    # Sanitize URL input
    url = sanitize_url(url)
    if not url:
        return "Error: Invalid URL format"
        
    logger.info(f"Fetching URL text: {url}")
    content = fetch_url_content(url)
    
    return f"Text content from {url}:\n\n{content}"

@mcp.tool()
def fetch_page_links(url: str = Field(description="The URL to fetch links from")) -> str:
    """Return a list of all links on the page"""
    # Sanitize URL input
    url = sanitize_url(url)
    if not url:
        return "Error: Invalid URL format"
    
    # Validate URL safety
    if not is_safe_url(url):
        logger.warning(f"Blocked unsafe URL for link fetching: {url}")
        return "Error: URL not allowed for security reasons"
        
    try:
        logger.info(f"Fetching page links: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
        resp.raise_for_status()
        
        # Check content length
        content_length = resp.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_RESPONSE_SIZE:
            return f"Error: Page too large ({content_length} bytes)"
        
        # Read content with size limit
        content_chunks = []
        total_size = 0
        
        for chunk in resp.iter_content(chunk_size=8192, decode_unicode=True):
            if chunk:
                total_size += len(chunk)
                if total_size > MAX_RESPONSE_SIZE:
                    return "Error: Page content too large"
                content_chunks.append(chunk)
        
        html_content = ''.join(content_chunks)
        soup = BeautifulSoup(html_content, "html.parser")
        links = [a.get('href') for a in soup.find_all('a', href=True) if a.get('href')]
        
        # Filter and clean links
        valid_links = []
        for link in links:
            if link.startswith(('http://', 'https://', '/')):
                valid_links.append(link)

        links_text = "\n".join(f"- {link}" for link in valid_links[:100])  # Limit to 100 links
        
        return f"Links found on {url} ({len(valid_links)} total, showing first 100):\n\n{links_text}"
        
    except requests.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")
        return "Error: Unable to fetch page"
    except Exception as e:
        logger.error(f"Unexpected error fetching links from {url}: {e}", exc_info=True)
        return "Error: Unable to process page"

@mcp.tool()
async def brave_search_and_fetch(
    ctx: Context,
    query: str = Field(description="The search query"),
    max_results: int = Field(
        default=3,
        description="Maximum number of results to fetch content for",
        ge=1,
        le=10
    )
) -> str:
    """Search the web using Brave Search and automatically fetch content from the top results"""
    
    # Use context for logging
    await ctx.info(f"Starting search for: {query}")
    
    # Sanitize query input
    query = sanitize_query(query)
    if not query:
        return "Error: Invalid or empty search query"
    
    max_results = max(1, min(10, max_results))  # Clamp between 1-10
    
    try:
        await ctx.info(f"Performing Brave search: {query}")
        search_results = brave_search(query, count=max_results * 2)
        
        if not search_results:
            return f"No search results found for query: {query}"
        
        # Build response with search results and content
        response_parts = [f"Search Results for: {query}", "=" * 50, ""]
        
        fetched_count = 0
        for result in search_results:
            if fetched_count >= max_results:
                break
                
            title = result.get('title', 'No title')
            url = result.get('url', '')
            description = result.get('description', 'No description')
            
            response_parts.append(f"{fetched_count + 1}. {title}")
            response_parts.append(f"   URL: {url}")
            response_parts.append(f"   Description: {description}")
            
            # Report progress
            progress = (fetched_count + 1) / max_results
            await ctx.report_progress(
                progress=progress,
                total=1.0,
                message=f"Fetching content from result {fetched_count + 1} of {max_results}"
            )
            
            # Fetch content from this URL
            if url:
                content = fetch_url_content(url)
                # Limit content per result
                max_content_per_result = CONTENT_LENGTH_LIMIT // max_results
                if len(content) > max_content_per_result:
                    content = content[:max_content_per_result] + "... [Truncated]"
                response_parts.append(f"   Content: {content}")
                fetched_count += 1
            else:
                response_parts.append("   Content: No URL available")
            
            response_parts.append("")  # Add spacing
        
        final_response = "\n".join(response_parts)
        
        # Final length check
        if len(final_response) > CONTENT_LENGTH_LIMIT:
            final_response = final_response[:CONTENT_LENGTH_LIMIT] + "... [Response truncated]"
        
        await ctx.info(f"Search completed successfully: {fetched_count} results fetched")
        return final_response
        
    except Exception as e:
        await ctx.error(f"Search operation failed: {str(e)}")
        logger.error(f"Search operation failed: {e}", exc_info=True)
        # Don't leak internal error details
        return "Error: Search operation failed"

def main():
    """Entry point for the FastMCP server."""
    logger.info("Starting URL Text Fetcher MCP Server (FastMCP)")
    mcp.run()

if __name__ == "__main__":
    main()
