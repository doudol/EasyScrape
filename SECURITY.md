# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by emailing the maintainers directly rather than opening a public issue.

**Please include:**
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you to resolve the issue.

## Security Features

EasyScrape includes several built-in security protections:

### SSRF Protection
All URLs are validated by default to prevent Server-Side Request Forgery attacks:
- Blocks requests to private IP ranges (10.x, 172.16-31.x, 192.168.x)
- Blocks localhost and loopback addresses
- Blocks link-local addresses (169.254.x)
- Can be disabled with `allow_localhost=True` for development

### Safe Link Extraction
The `safe_links()` method filters out potentially dangerous URLs:
- Blocks `javascript:` URLs
- Blocks `data:` URLs
- Returns only HTTP/HTTPS links

### SSL Verification
SSL certificate verification is enabled by default. Disable only in development:
```python
config = Config(verify_ssl=False)  # Not recommended for production
```

## Best Practices

1. **Never disable SSRF protection in production**
2. **Always validate user-provided URLs before scraping**
3. **Use rate limiting to avoid being blocked**
4. **Respect robots.txt when scraping**
