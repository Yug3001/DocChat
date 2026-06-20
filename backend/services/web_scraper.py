"""
web_scraper.py
──────────────
Scrapes a website URL, extracts clean readable text, and optionally
crawls a limited number of internal links from the same domain.

Returns a single combined text blob with page title and URL markers
so the existing chunker pipeline can process it like any other document.

HYBRID STRATEGY (fast-path first, Playwright fallback):
────────────────────────────────────────────────────────
1. Fast path  — requests + BeautifulSoup (cheap, in-process, no browser).
               Works on most traditional server-rendered pages.
2. Playwright  — headless Chromium browser (SYNC API). Only launched when the fast
               path returns suspiciously little text (< _MIN_TEXT_CHARS),
               gets a 403/challenge response, or when an iframe is
               detected that likely holds the real content (e.g. Hugging
               Face Spaces, Streamlit, Gradio embeds).

IMPORTANT: launching a headless browser is significantly heavier than
an HTTP request (~200-400 MB RAM, several seconds startup). It must only
be used as a last resort, never on every request by default.

DEPENDENCIES:
  Fast path  :  pip install requests beautifulsoup4 lxml
  Playwright :  pip install playwright
                python -m playwright install chromium   ← one-time step!
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# ── Fast-path dependencies ─────────────────────────────────────────────────────
try:
    import requests
    from bs4 import BeautifulSoup
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False
    logger.warning(
        "[WebScraper] requests / beautifulsoup4 not installed. "
        "Install: pip install requests beautifulsoup4 lxml"
    )

# ── Playwright (optional — only imported at runtime, not at module load) ───────
#    We do NOT import playwright at the top level to avoid crashing the entire
#    backend if playwright is not yet installed. It is imported lazily inside
#    _playwright_fetch() only when the fallback is actually needed.

# ── Tuneable constants ─────────────────────────────────────────────────────────
_TIMEOUT            = 15        # seconds per HTTP request (fast path)
_PLAYWRIGHT_TIMEOUT = 20_000    # milliseconds per page load (Playwright)
_DELAY              = 0.5       # polite delay (seconds) between crawled pages
_MAX_TEXT_PER_PAGE  = 50_000    # characters per page before truncation

# If fast-path extracts fewer than this many characters of actual text,
# we consider the page possibly JS-rendered and trigger Playwright fallback.
_MIN_TEXT_CHARS     = 200

# HTTP status codes that strongly suggest a bot-challenge / WAF block.
_CHALLENGE_CODES    = {403, 429, 503}

# Common Hugging Face / Streamlit / Gradio iframe URL patterns.
# If the outer page contains an <iframe src="..."> whose URL matches any of
# these patterns, we load that iframe URL directly with Playwright instead of
# trying to parse the outer shell.
_IFRAME_PATTERNS = [
    r"huggingface\.co",
    r"hf\.space",
    r"\.hf\.space",
    r"streamlit\.app",
    r"gradio\.app",
    r"gradio\.live",
]

# ── Domains that cannot be scraped — fail fast with a clear message ────────────
# These platforms actively block all automated access (bot detection, CAPTCHA,
# legal restrictions, login walls). Attempting to scrape them wastes time and
# always fails — so we reject them immediately with a helpful explanation.
#
# Key: the netloc suffix to match (matched as "ends with" on the domain).
# Value: human-readable reason shown to the user.
_BLOCKED_DOMAINS: dict[str, str] = {
    # ── Search engines ─────────────────────────────────────────────────────────
    "google.com":       "Google Search results cannot be scraped. Google uses "
                        "aggressive bot detection and its Terms of Service "
                        "prohibit automated access. Try pasting the URL of an "
                        "individual webpage from the search results instead.",
    "google.co.in":     "Google Search (India) cannot be scraped. Paste the URL "
                        "of the actual article or page you want to chat with.",
    "bing.com":         "Bing Search results cannot be scraped. Paste the URL "
                        "of an individual result page instead.",
    "search.yahoo.com": "Yahoo Search results cannot be scraped. Paste the URL "
                        "of an individual result page instead.",
    "duckduckgo.com":   "DuckDuckGo Search results cannot be scraped. Paste the "
                        "URL of an individual result page instead.",
    # ── Social / login-walled platforms ────────────────────────────────────────
    "twitter.com":      "Twitter/X requires a login to view most content and "
                        "blocks all automated access.",
    "x.com":            "Twitter/X requires a login to view most content and "
                        "blocks all automated access.",
    "facebook.com":     "Facebook requires login and blocks all automated "
                        "scraping. Public pages are also restricted.",
    "instagram.com":    "Instagram requires login and blocks all automated access.",
    "linkedin.com":     "LinkedIn actively blocks scrapers and requires login for "
                        "most content.",
    "reddit.com":       "Reddit blocks automated scrapers. Use the Reddit API "
                        "(old.reddit.com) or a specific post URL may work better.",
}

# Tags whose contents we always strip out entirely during BSoup parsing.
_STRIP_TAGS = {
    "script", "style", "noscript", "nav", "footer", "header",
    "aside", "form", "button", "svg", "meta", "link",
    "[document]", "head",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ══════════════════════════════════════════════════════════════════════════════
# Internal helpers — availability checks
# ══════════════════════════════════════════════════════════════════════════════

def _check_requests_available() -> None:
    if not _REQUESTS_AVAILABLE:
        raise RuntimeError(
            "requests and beautifulsoup4 are not installed. "
            "Run: pip install requests beautifulsoup4 lxml"
        )


def _check_playwright_available() -> None:
    """Lazy-check: try importing playwright to give a clear error if missing."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "playwright is not installed. "
            "Run: pip install playwright && python -m playwright install chromium"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Fast path — requests + BeautifulSoup
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_html_fast(url: str) -> tuple[Optional[str], int]:
    """
    Fetch raw HTML via requests.
    Returns (html_text, http_status_code).
    On connection error returns (None, 0).
    """
    try:
        resp = requests.get(
            url, headers=_HEADERS, timeout=_TIMEOUT, allow_redirects=True
        )
        status = resp.status_code
        ct = resp.headers.get("Content-Type", "")
        if "html" not in ct:
            logger.debug(
                "[WebScraper:fast] Skipping non-HTML response at %s (Content-Type: %s)",
                url, ct,
            )
            return None, status
        # Do NOT raise_for_status yet — let the caller decide based on status
        return resp.text, status
    except Exception as exc:
        logger.warning("[WebScraper:fast] Fetch failed for %s: %s", url, exc)
        return None, 0


def _extract_text_from_html(html: str) -> tuple[str, str]:
    """
    Parse HTML with BeautifulSoup and return (title, clean_text).
    Strips navigation, scripts, footers, etc.
    """
    soup = BeautifulSoup(html, "lxml")

    # Extract page title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled Page"

    # Remove noisy tags entirely
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    # Extract visible text
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)          # collapse blank lines
    text = re.sub(r"[ \t]{3,}", "  ", text)          # collapse inline whitespace

    if len(text) > _MAX_TEXT_PER_PAGE:
        text = text[:_MAX_TEXT_PER_PAGE] + "\n\n[... content truncated for length ...]"

    return title, text.strip()


def _get_internal_links(html: str, base_url: str, domain: str) -> list[str]:
    """
    Extract href links from HTML that belong to the same domain.
    Returns a deduplicated list of absolute URLs.
    """
    soup = BeautifulSoup(html, "lxml")
    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        if parsed.scheme in ("http", "https") and parsed.netloc == domain:
            clean = abs_url.split("#")[0].rstrip("/")
            if clean:
                links.add(clean)
    return list(links)


def _detect_embedded_iframe(html: str) -> Optional[str]:
    """
    Look for an <iframe src="..."> whose URL matches known embedded-app
    patterns (Hugging Face Spaces, Streamlit, Gradio, etc.).

    Returns the iframe src URL if found, otherwise None.

    WHY: Hugging Face Spaces pages typically contain a single <iframe> that
    wraps the actual Gradio/Streamlit UI. The outer page has almost no text.
    The real content lives at the iframe's src URL. We detect this pattern
    and hand the iframe URL directly to Playwright, skipping the useless
    outer shell entirely.
    """
    soup = BeautifulSoup(html, "lxml")
    iframe_pattern = re.compile("|".join(_IFRAME_PATTERNS), re.IGNORECASE)
    for iframe in soup.find_all("iframe", src=True):
        src = iframe["src"].strip()
        if iframe_pattern.search(src):
            logger.info("[WebScraper] Detected embedded iframe: %s", src)
            return src
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Playwright fallback — headless Chromium (SYNCHRONOUS API)
# ══════════════════════════════════════════════════════════════════════════════

def _playwright_fetch(url: str) -> tuple[str, str]:
    """
    Launch headless Chromium via Playwright's SYNCHRONOUS API, navigate to url,
    wait for network idle, then extract (title, clean_text) from the rendered DOM.

    WHY SYNC, NOT ASYNC:
    ─────────────────────────────────────────────────────────────────────────
    On Windows, Python's asyncio uses SelectorEventLoop inside threads spawned
    by uvicorn/FastAPI. SelectorEventLoop does NOT support subprocess creation
    (asyncio.create_subprocess_exec raises NotImplementedError on Windows).
    Playwright's async API internally calls asyncio.create_subprocess_exec to
    launch the Chromium browser process, which means async_playwright always
    crashes on Windows in this context with NotImplementedError.

    Playwright's SYNCHRONOUS API (sync_playwright) uses subprocess.Popen
    directly — no asyncio involvement at all — so it works correctly on
    Windows regardless of which event loop policy is active.
    ─────────────────────────────────────────────────────────────────────────

    NOTE: This is resource-intensive. Each call spins up a full Chromium
    process (~200-400 MB RAM, a few seconds startup). It should only be
    invoked as a fallback, never on every request by default.
    """
    _check_playwright_available()
    try:
        from playwright.sync_api import sync_playwright  # lazy import — sync API

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",  # important in Docker/CI environments
                    "--disable-gpu",
                ],
            )
            context = browser.new_context(
                user_agent=_HEADERS["User-Agent"],
                locale="en-US",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            try:
                # Primary strategy: wait for all network requests to settle so
                # JS-rendered content is fully present in the DOM.
                page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=_PLAYWRIGHT_TIMEOUT,
                )
            except Exception:
                # "networkidle" can time-out on very chatty apps (e.g. live-updating
                # Gradio UIs that stream data continuously). Fall back to
                # "domcontentloaded" and give JS a short extra window to render.
                try:
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=_PLAYWRIGHT_TIMEOUT,
                    )
                    page.wait_for_timeout(3000)  # 3 s for JS to paint the page
                except Exception as exc2:
                    logger.warning(
                        "[WebScraper:playwright] Navigation failed for %s: %s",
                        url, exc2,
                    )
                    browser.close()
                    return "Untitled Page", ""

            title = page.title() or "Untitled Page"
            # Grab fully-rendered HTML and re-use the same BSoup parser
            html = page.content()
            browser.close()

        _, clean_text = _extract_text_from_html(html)
        logger.info(
            "[WebScraper:playwright] Extracted %d chars from %s", len(clean_text), url
        )
        return title, clean_text

    except Exception as exc:
        logger.error(
            "[WebScraper:playwright] Unexpected error for %s: %s", url, exc
        )
        return "Untitled Page", ""


# ══════════════════════════════════════════════════════════════════════════════
# Core hybrid scrape function — called per URL
# ══════════════════════════════════════════════════════════════════════════════

def _scrape_single_page(url: str) -> tuple[str, str, str]:
    """
    Scrape a single page using the hybrid strategy.

    Returns (title, clean_text, html_for_link_extraction).

    Decision logic:
    ─────────────────────────────────────────────────────────────────────────
    Step 1 — Fast path (requests + BeautifulSoup):
      • Fetch the URL with requests.
      • If we get a challenge/bot-block HTTP code (403/429/503) → go to Step 3.
      • Parse the HTML with BeautifulSoup.
      • If extracted text is >= _MIN_TEXT_CHARS characters → we're done (fast).

    Step 2 — Iframe detection:
      • If the fast-path HTML contains an <iframe> matching known SPA-embed
        patterns (Hugging Face, Gradio, Streamlit), load that iframe URL
        directly with Playwright instead of the outer shell.

    Step 3 — Playwright fallback:
      • Headless Chromium renders the page with full JS execution.
      • Wait for networkidle (or domcontentloaded + 3 s timeout as safety net).
      • Extract text from the fully-rendered DOM.
    ─────────────────────────────────────────────────────────────────────────
    """
    raw_html_for_links = ""  # used for internal-link extraction

    # ── Step 1: Fast path ─────────────────────────────────────────────────────
    html, status = _fetch_html_fast(url)

    if status in _CHALLENGE_CODES:
        logger.info(
            "[WebScraper] Fast path got HTTP %d for %s — triggering Playwright fallback",
            status, url,
        )
        title, text = _playwright_fetch(url)
        return title, text, ""

    if html:
        raw_html_for_links = html  # save for link crawling

        # ── Step 2: Iframe detection ──────────────────────────────────────────
        iframe_src = _detect_embedded_iframe(html)
        if iframe_src:
            logger.info(
                "[WebScraper] Iframe detected → loading iframe src with Playwright: %s",
                iframe_src,
            )
            title, text = _playwright_fetch(iframe_src)
            if text and len(text) >= _MIN_TEXT_CHARS:
                return title, text, raw_html_for_links
            # If iframe load also yielded nothing, fall through to Step 3
            logger.warning(
                "[WebScraper] Iframe Playwright fetch returned short text (%d chars) "
                "for %s — will also try the outer URL with Playwright",
                len(text), iframe_src,
            )

        # ── Check fast-path text quality ──────────────────────────────────────
        title, text = _extract_text_from_html(html)

        if len(text) >= _MIN_TEXT_CHARS:
            logger.info(
                "[WebScraper:fast] OK — %d chars extracted from %s", len(text), url
            )
            return title, text, raw_html_for_links

        logger.info(
            "[WebScraper] Fast path returned only %d chars for %s "
            "(threshold: %d) — triggering Playwright fallback",
            len(text), url, _MIN_TEXT_CHARS,
        )

    else:
        logger.info(
            "[WebScraper] Fast path returned no HTML for %s — trying Playwright",
            url,
        )

    # ── Step 3: Playwright fallback ───────────────────────────────────────────
    logger.info("[WebScraper:playwright] Launching headless Chromium for %s", url)
    title, text = _playwright_fetch(url)
    return title, text, raw_html_for_links


# ══════════════════════════════════════════════════════════════════════════════
# Public API — same signature as before; website.py needs ZERO changes
# ══════════════════════════════════════════════════════════════════════════════

def scrape_website(
    url: str,
    crawl_links: bool = True,
    max_pages: int = 5,
) -> tuple[str, str, int]:
    """
    Scrape a website and return (page_title, combined_text, total_pages_scraped).

    SIGNATURE IS UNCHANGED from the original implementation — website.py and
    the rest of the ingestion pipeline require zero modification.

    Parameters
    ----------
    url         : The starting URL to scrape.
    crawl_links : Whether to follow same-domain internal links after the
                  first page (uses fast-path HTML for link extraction).
    max_pages   : Maximum number of pages to scrape (including start page).

    Returns
    -------
    (site_title, combined_text, pages_scraped)
        site_title    — title of the first successfully scraped page
        combined_text — all pages joined, each wrapped in === PAGE: ... ===
                        markers so the chunker can process it normally
        pages_scraped — how many pages were successfully extracted
    """
    _check_requests_available()

    parsed_start = urlparse(url)
    domain = parsed_start.netloc
    if not domain:
        raise ValueError(f"Invalid URL: {url!r} — could not extract domain.")

    # ── Fast-fail: reject known-unscrappable domains immediately ───────────────
    # Strip "www." prefix for matching so both google.com and www.google.com hit.
    bare_domain = domain.lstrip("www.") if domain.startswith("www.") else domain
    for blocked, reason in _BLOCKED_DOMAINS.items():
        if bare_domain == blocked or bare_domain.endswith("." + blocked):
            raise ValueError(reason)

    visited:  set[str]  = set()
    to_visit: list[str] = [url]
    pages:    list[str] = []
    site_title: str     = domain   # fallback; overwritten by first page

    while to_visit and len(pages) < max_pages:
        current_url = to_visit.pop(0)
        norm = current_url.rstrip("/")
        if norm in visited:
            continue
        visited.add(norm)

        # ── Hybrid scrape of this single page ─────────────────────────────────
        page_title, page_text, raw_html = _scrape_single_page(current_url)

        if not page_text.strip():
            logger.warning(
                "[WebScraper] No text extracted for %s (skipping)", current_url
            )
            continue

        # First successfully scraped page provides the document title
        if len(pages) == 0:
            site_title = page_title

        # Build the page block with markers for the chunker
        page_block = (
            f"=== PAGE: {page_title} ===\n"
            f"URL: {current_url}\n"
            f"{'-' * 60}\n"
            f"{page_text}\n"
        )
        pages.append(page_block)
        logger.info("[WebScraper] Scraped page %d: %s", len(pages), current_url)

        # ── Internal link crawling (only uses fast-path HTML to find links) ───
        if crawl_links and len(pages) < max_pages and raw_html:
            internal_links = _get_internal_links(raw_html, current_url, domain)
            for link in internal_links:
                norm_link = link.rstrip("/")
                if norm_link not in visited and link not in to_visit:
                    to_visit.append(link)

        # Polite crawl delay between pages
        if len(pages) < max_pages and _DELAY > 0:
            time.sleep(_DELAY)

    if not pages:
        raise ValueError(
            f"No readable content could be extracted from {url}. "
            "The page may be behind a login wall, aggressive bot protection, "
            "or contain no text content."
        )

    combined_text = "\n\n".join(pages)
    return site_title, combined_text, len(pages)
