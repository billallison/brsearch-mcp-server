#!/usr/bin/env python3
"""
Test script to verify security fixes are working properly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from url_text_fetcher.server import is_safe_url, fetch_url_content

def test_url_validation():
    """Test SSRF prevention"""
    print("Testing URL validation...")
    
    # Safe URLs
    safe_urls = [
        "https://www.example.com",
        "http://example.org/page",
        "https://api.github.com/repos/test"
    ]
    
    # Unsafe URLs
    unsafe_urls = [
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://192.168.1.1",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "file:///etc/passwd",
        "ftp://internal.server.com"
    ]
    
    print("Safe URLs:")
    for url in safe_urls:
        result = is_safe_url(url)
        print(f"  {url}: {'✓' if result else '✗'}")
    
    print("\nUnsafe URLs:")
    for url in unsafe_urls:
        result = is_safe_url(url)
        print(f"  {url}: {'✗' if not result else '✓ (SHOULD BE BLOCKED!)'}")

def test_error_handling():
    """Test that errors don't leak sensitive information"""
    print("\nTesting error handling...")
    
    # Test with invalid URL
    result = fetch_url_content("http://localhost:8080/admin")
    print(f"Localhost access: {result}")
    
    # Test with non-existent domain
    result = fetch_url_content("https://thisdoesnotexist12345.com")
    print(f"Non-existent domain: {result}")

if __name__ == "__main__":
    test_url_validation()
    test_error_handling()
    print("\nSecurity test completed!")
