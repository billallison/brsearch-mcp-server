#!/usr/bin/env python3
"""
Simple test script to verify Brave Search API connectivity
"""
import os
import requests
from pathlib import Path

# Load environment variables from .env file
def load_env():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        print(f"Loading .env from: {env_path}")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if value and key not in os.environ:
                        os.environ[key] = value
                        print(f"Set {key} = {value[:10]}...")
    else:
        print(f"No .env file found at: {env_path}")

load_env()

# Get API key
api_key = os.getenv('BRAVE_API_KEY', '')
print(f"API Key present: {'Yes' if api_key else 'No'}")
print(f"API Key length: {len(api_key)}")

if not api_key:
    print("❌ Error: BRAVE_API_KEY not found in environment")
    exit(1)

# Test the API
url = "https://api.search.brave.com/res/v1/web/search"
headers = {
    'User-Agent': 'Mozilla/5.0 (compatible; MCP-URL-Fetcher/1.0)',
    'X-Subscription-Token': api_key
}
params = {
    'q': 'test search',
    'count': 1,
    'search_lang': 'en',
    'country': 'US',
    'safesearch': 'moderate'
}

print(f"\nTesting API endpoint: {url}")
print(f"Query: {params['q']}")

try:
    response = requests.get(url, headers=headers, params=params, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response keys: {list(data.keys())}")
        
        if 'web' in data and 'results' in data['web']:
            results = data['web']['results']
            print(f"✅ Success! Found {len(results)} results")
            if results:
                first = results[0]
                print(f"First result: {first.get('title', 'No title')}")
                print(f"URL: {first.get('url', 'No URL')}")
        else:
            print(f"⚠️ Unexpected response structure: {data}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")
