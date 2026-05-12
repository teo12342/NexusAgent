"""Web tools for nexus_agent Agent — search, fetch, scrape."""

import structlog
from typing import Dict, Any

logger = structlog.get_logger()


def register_web_tools(registry: Dict):

    def web_search(query: str, count: int = 5) -> Dict:
        """Search the web using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=count))
            return {"success": True, "query": query, "results": results}
        except ImportError:
            return {"success": False, "error": "duckduckgo_search not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def web_fetch(url: str, max_chars: int = 5000) -> Dict:
        """Fetch a URL and extract readable content."""
        try:
            import httpx
            resp = httpx.get(url, timeout=15, follow_redirects=True)
            resp.raise_for_status()

            # Simple content extraction
            from urllib.parse import urlparse
            content_type = resp.headers.get("content-type", "")
            if "text/html" in content_type:
                # Simple HTML stripping
                import re
                text = re.sub(r'<[^>]+>', ' ', resp.text)
                text = re.sub(r'\s+', ' ', text).strip()
                text = text[:max_chars]
                return {
                    "success": True,
                    "url": url,
                    "title": urlparse(url).netloc,
                    "content": text,
                    "status_code": resp.status_code,
                }
            else:
                return {
                    "success": True,
                    "url": url,
                    "content": resp.text[:max_chars],
                    "content_type": content_type,
                    "status_code": resp.status_code,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def web_get_headers(url: str) -> Dict:
        """Get HTTP headers for a URL."""
        try:
            import httpx
            resp = httpx.head(url, timeout=10, follow_redirects=True)
            return {"success": True, "url": url, "headers": dict(resp.headers)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    tools = {
        "web_search": web_search,
        "web_fetch": web_fetch,
        "web_get_headers": web_get_headers,
    }
    registry.update(tools)