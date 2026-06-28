"""Same-origin breadth-first crawler for multi-page audits.

Discovers internal links from each visited page (using the rendered DOM so it
follows client-rendered navigation too) and yields URLs up to a page/depth limit.
Stays on the start URL's origin to avoid wandering off-site.
"""

from __future__ import annotations

from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse

from playwright.async_api import Page


def _same_origin(a: str, b: str) -> bool:
    pa, pb = urlparse(a), urlparse(b)
    return (pa.scheme, pa.netloc) == (pb.scheme, pb.netloc)


def _normalise(url: str) -> str:
    # Drop fragments so #section variants aren't treated as distinct pages.
    return urldefrag(url)[0].rstrip("/") or url


async def extract_links(page: Page, base_url: str) -> list[str]:
    """Return absolute, same-origin links from the page's rendered DOM."""
    hrefs = await page.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.getAttribute('href'))"
    )
    links: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = _normalise(urljoin(base_url, href))
        if _same_origin(absolute, base_url) and absolute not in seen:
            seen.add(absolute)
            links.append(absolute)
    return links


class CrawlPlan:
    """Tracks the BFS frontier and visited set for a crawl.

    The crawl itself is driven by the caller (which owns the browser page and the
    auditing), so this class only manages which URLs to visit next. This keeps the
    audit/render concerns out of the crawl bookkeeping.
    """

    def __init__(self, start_url: str, max_pages: int, max_depth: int) -> None:
        self.start_url = _normalise(start_url)
        self.max_pages = max_pages
        self.max_depth = max_depth
        self._queue: deque[tuple[str, int]] = deque([(self.start_url, 0)])
        self._visited: set[str] = set()

    def next(self) -> tuple[str, int] | None:
        while self._queue:
            url, depth = self._queue.popleft()
            if url in self._visited:
                continue
            if len(self._visited) >= self.max_pages:
                return None
            self._visited.add(url)
            return url, depth
        return None

    def add_links(self, links: list[str], depth: int) -> None:
        if depth >= self.max_depth:
            return
        for link in links:
            norm = _normalise(link)
            if norm not in self._visited:
                self._queue.append((norm, depth + 1))

    @property
    def visited_count(self) -> int:
        return len(self._visited)
