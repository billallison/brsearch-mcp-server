#!/usr/bin/env python3
"""
Test script to reproduce the brave_search_and_fetch issue
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from url_text_fetcher.server import brave_search_and_fetch

async def test_search():
    """Test the brave_search_and_fetch function directly"""
    query = "Mesozoic Era dinosaurs Triassic Jurassic Cretaceous"
    max_results = 3
    
    print(f"Testing query: '{query}' with max_results={max_results}")
    
    try:
        result = await brave_search_and_fetch(query, max_results)
        print(f"Result length: {len(result)} characters")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())
