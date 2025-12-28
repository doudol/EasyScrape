#!/usr/bin/env python3
"""
Example 07: Proxy Usage

Demonstrates how to route requests through a proxy server.
"""

import easyscrape as es

def main():
    # Configure a proxy (replace with your actual proxy)
    config = es.Config(
        proxy="http://user:pass@proxy.example.com:8080"
    )
    
    # All requests will go through the proxy
    result = es.scrape("https://httpbin.org/ip", config=config)
    
    print("Response through proxy:")
    print(result.text[:500])
    
    # Note: For SOCKS proxies, use:
    # config = es.Config(proxy="socks5://proxy.example.com:1080")


if __name__ == "__main__":
    print("Note: This example requires a valid proxy to work.")
    print("Uncomment and configure a proxy to test.")
    # main()
