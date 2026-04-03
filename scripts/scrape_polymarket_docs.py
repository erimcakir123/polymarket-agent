"""
Polymarket API Docs Scraper
Fetches all endpoint pages from docs.polymarket.com and produces a single MD file.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

OUTPUT_FILE = "polymarket-full-api-reference.md"

SECTIONS = {
    "Overview": [
        "https://docs.polymarket.com/api-reference/introduction",
        "https://docs.polymarket.com/api-reference/authentication",
        "https://docs.polymarket.com/api-reference/rate-limits",
        "https://docs.polymarket.com/api-reference/clients-sdks",
        "https://docs.polymarket.com/api-reference/geoblock",
    ],
    "Events": [
        "https://docs.polymarket.com/api-reference/events/list-events",
        "https://docs.polymarket.com/api-reference/events/get-event-by-id",
        "https://docs.polymarket.com/api-reference/events/get-event-by-slug",
        "https://docs.polymarket.com/api-reference/events/get-event-tags",
    ],
    "Markets": [
        "https://docs.polymarket.com/api-reference/markets/list-markets",
        "https://docs.polymarket.com/api-reference/markets/get-market-by-id",
        "https://docs.polymarket.com/api-reference/markets/get-market-by-slug",
        "https://docs.polymarket.com/api-reference/markets/get-market-tags-by-id",
        "https://docs.polymarket.com/api-reference/core/get-top-holders-for-markets",
        "https://docs.polymarket.com/api-reference/misc/get-open-interest",
        "https://docs.polymarket.com/api-reference/misc/get-live-volume-for-an-event",
    ],
    "Orderbook & Pricing": [
        "https://docs.polymarket.com/api-reference/market-data/get-order-book",
        "https://docs.polymarket.com/api-reference/market-data/get-order-books-request-body",
        "https://docs.polymarket.com/api-reference/market-data/get-market-price",
        "https://docs.polymarket.com/api-reference/market-data/get-market-prices-query-parameters",
        "https://docs.polymarket.com/api-reference/market-data/get-market-prices-request-body",
        "https://docs.polymarket.com/api-reference/data/get-midpoint-price",
        "https://docs.polymarket.com/api-reference/market-data/get-midpoint-prices-query-parameters",
        "https://docs.polymarket.com/api-reference/market-data/get-midpoint-prices-request-body",
        "https://docs.polymarket.com/api-reference/market-data/get-spread",
        "https://docs.polymarket.com/api-reference/market-data/get-spreads",
        "https://docs.polymarket.com/api-reference/market-data/get-last-trade-price",
        "https://docs.polymarket.com/api-reference/market-data/get-last-trade-prices-query-parameters",
        "https://docs.polymarket.com/api-reference/market-data/get-last-trade-prices-request-body",
        "https://docs.polymarket.com/api-reference/markets/get-prices-history",
        "https://docs.polymarket.com/api-reference/market-data/get-fee-rate",
        "https://docs.polymarket.com/api-reference/market-data/get-fee-rate-by-path-parameter",
        "https://docs.polymarket.com/api-reference/market-data/get-tick-size",
        "https://docs.polymarket.com/api-reference/market-data/get-tick-size-by-path-parameter",
        "https://docs.polymarket.com/api-reference/data/get-server-time",
    ],
    "Orders": [
        "https://docs.polymarket.com/api-reference/trade/post-a-new-order",
        "https://docs.polymarket.com/api-reference/trade/cancel-single-order",
        "https://docs.polymarket.com/api-reference/trade/get-single-order-by-id",
        "https://docs.polymarket.com/api-reference/trade/post-multiple-orders",
        "https://docs.polymarket.com/api-reference/trade/get-user-orders",
        "https://docs.polymarket.com/api-reference/trade/cancel-multiple-orders",
        "https://docs.polymarket.com/api-reference/trade/cancel-all-orders",
        "https://docs.polymarket.com/api-reference/trade/cancel-orders-for-a-market",
        "https://docs.polymarket.com/api-reference/trade/get-order-scoring-status",
        "https://docs.polymarket.com/api-reference/trade/send-heartbeat",
    ],
    "Trades": [
        "https://docs.polymarket.com/api-reference/trade/get-trades",
        "https://docs.polymarket.com/api-reference/trade/get-builder-trades",
    ],
    "CLOB Markets": [
        "https://docs.polymarket.com/api-reference/markets/get-simplified-markets",
        "https://docs.polymarket.com/api-reference/markets/get-sampling-markets",
        "https://docs.polymarket.com/api-reference/markets/get-sampling-simplified-markets",
    ],
    "Rebates": [
        "https://docs.polymarket.com/api-reference/rebates/get-current-rebated-fees-for-a-maker",
    ],
    "Rewards": [
        "https://docs.polymarket.com/api-reference/rewards/get-current-active-rewards-configurations",
        "https://docs.polymarket.com/api-reference/rewards/get-raw-rewards-for-a-specific-market",
        "https://docs.polymarket.com/api-reference/rewards/get-multiple-markets-with-rewards",
        "https://docs.polymarket.com/api-reference/rewards/get-earnings-for-user-by-date",
        "https://docs.polymarket.com/api-reference/rewards/get-total-earnings-for-user-by-date",
        "https://docs.polymarket.com/api-reference/rewards/get-reward-percentages-for-user",
        "https://docs.polymarket.com/api-reference/rewards/get-user-earnings-and-markets-configuration",
    ],
    "Profile": [
        "https://docs.polymarket.com/api-reference/profiles/get-public-profile-by-wallet-address",
        "https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user",
        "https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user",
        "https://docs.polymarket.com/api-reference/core/get-user-activity",
        "https://docs.polymarket.com/api-reference/core/get-total-value-of-a-users-positions",
        "https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets",
        "https://docs.polymarket.com/api-reference/misc/get-total-markets-a-user-has-traded",
        "https://docs.polymarket.com/api-reference/core/get-positions-for-a-market",
        "https://docs.polymarket.com/api-reference/misc/download-an-accounting-snapshot-zip-of-csvs",
    ],
    "Leaderboard": [
        "https://docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings",
    ],
    "Builders": [
        "https://docs.polymarket.com/api-reference/builders/get-aggregated-builder-leaderboard",
        "https://docs.polymarket.com/api-reference/builders/get-daily-builder-volume-time-series",
    ],
    "Search": [
        "https://docs.polymarket.com/api-reference/search/search-markets-events-and-profiles",
    ],
    "Tags": [
        "https://docs.polymarket.com/api-reference/tags/list-tags",
        "https://docs.polymarket.com/api-reference/tags/get-tag-by-id",
        "https://docs.polymarket.com/api-reference/tags/get-tag-by-slug",
        "https://docs.polymarket.com/api-reference/tags/get-related-tags-relationships-by-tag-id",
        "https://docs.polymarket.com/api-reference/tags/get-related-tags-relationships-by-tag-slug",
        "https://docs.polymarket.com/api-reference/tags/get-tags-related-to-a-tag-id",
        "https://docs.polymarket.com/api-reference/tags/get-tags-related-to-a-tag-slug",
    ],
    "Series": [
        "https://docs.polymarket.com/api-reference/series/list-series",
        "https://docs.polymarket.com/api-reference/series/get-series-by-id",
    ],
    "Comments": [
        "https://docs.polymarket.com/api-reference/comments/list-comments",
        "https://docs.polymarket.com/api-reference/comments/get-comments-by-comment-id",
        "https://docs.polymarket.com/api-reference/comments/get-comments-by-user-address",
    ],
    "Sports": [
        "https://docs.polymarket.com/api-reference/sports/get-sports-metadata-information",
        "https://docs.polymarket.com/api-reference/sports/get-valid-sports-market-types",
        "https://docs.polymarket.com/api-reference/sports/list-teams",
    ],
    "Bridge": [
        "https://docs.polymarket.com/api-reference/bridge/get-supported-assets",
        "https://docs.polymarket.com/api-reference/bridge/create-deposit-addresses",
        "https://docs.polymarket.com/api-reference/bridge/get-a-quote",
        "https://docs.polymarket.com/api-reference/bridge/get-transaction-status",
        "https://docs.polymarket.com/api-reference/bridge/create-withdrawal-addresses",
    ],
    "Relayer": [
        "https://docs.polymarket.com/api-reference/relayer/submit-a-transaction",
        "https://docs.polymarket.com/api-reference/relayer/get-a-transaction-by-id",
        "https://docs.polymarket.com/api-reference/relayer/get-recent-transactions-for-a-user",
        "https://docs.polymarket.com/api-reference/relayer/get-current-nonce-for-a-user",
        "https://docs.polymarket.com/api-reference/relayer/get-relayer-address-and-nonce",
        "https://docs.polymarket.com/api-reference/relayer/check-if-a-safe-is-deployed",
        "https://docs.polymarket.com/api-reference/relayer-api-keys/get-all-relayer-api-keys",
    ],
    "WebSocket": [
        "https://docs.polymarket.com/api-reference/wss/market",
        "https://docs.polymarket.com/api-reference/wss/user",
        "https://docs.polymarket.com/api-reference/wss/sports",
    ],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_page(url: str, max_retries: int = 3) -> str | None:
    """Fetch a URL with retries and delay."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                return resp.text
            print(f"  [WARN] {url} returned {resp.status_code} (attempt {attempt+1})")
        except Exception as e:
            print(f"  [ERROR] {url} exception: {e} (attempt {attempt+1})")
        if attempt < max_retries - 1:
            time.sleep(2)
    return None


def slugify(text: str) -> str:
    """Create anchor-compatible slug from text."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    return text


def extract_main_content(html: str) -> str:
    """Extract the main documentation content from HTML and convert to markdown."""
    soup = BeautifulSoup(html, "html.parser")

    # Polymarket docs use Mintlify - try to find main content area
    # Try various selectors that Mintlify-based docs use
    content_el = None
    for selector in ["main", "article", "[class*='content']", "[class*='docs']", "#content"]:
        content_el = soup.select_one(selector)
        if content_el:
            break

    if not content_el:
        # Fallback: use body but remove nav/header/footer
        content_el = soup.body or soup
        for tag in content_el.select("nav, header, footer, script, style, [class*='sidebar'], [class*='nav']"):
            tag.decompose()

    # Convert to markdown
    content_md = md(str(content_el), heading_style="ATX", code_language="", strip=["img"])

    # Clean up excessive whitespace
    content_md = re.sub(r'\n{4,}', '\n\n\n', content_md)
    content_md = content_md.strip()

    return content_md


def parse_endpoint_page(html: str, url: str, section: str) -> str:
    """Parse a single endpoint page and format it according to the template."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract title from h1 or title tag
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else url.split("/")[-1].replace("-", " ").title()

    # Get full markdown content
    content_md = extract_main_content(html)

    # Build the formatted section
    output = f"\n---\n\n## {section} — {title}\n\n"
    output += f"> **Source:** {url}\n\n"
    output += content_md
    output += "\n\n"

    return output


def build_toc(sections: dict, results: dict) -> str:
    """Build Table of Contents with anchor links."""
    toc = "# Polymarket Full API Reference\n\n"
    toc += "> Auto-generated from https://docs.polymarket.com/api-reference/\n"
    toc += f"> Generated on: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
    toc += "## Table of Contents\n\n"

    for section, urls in sections.items():
        section_slug = slugify(section)
        toc += f"### [{section}](#{section_slug})\n\n"
        for url in urls:
            if url in results and results[url]:
                # Extract title from the result
                title_match = re.search(r'^## .+ — (.+)$', results[url], re.MULTILINE)
                ep_title = title_match.group(1) if title_match else url.split("/")[-1].replace("-", " ").title()
                anchor = slugify(f"{section} — {ep_title}")
                toc += f"- [{ep_title}](#{anchor})\n"
            else:
                ep_title = url.split("/")[-1].replace("-", " ").title()
                toc += f"- ~~{ep_title}~~ (fetch failed)\n"
        toc += "\n"

    return toc


def main():
    total_urls = sum(len(urls) for urls in SECTIONS.values())
    print(f"=== Polymarket API Docs Scraper ===")
    print(f"Total URLs to fetch: {total_urls}")
    print()

    results = {}
    success_count = 0
    fail_count = 0
    failed_urls = []

    for section, urls in SECTIONS.items():
        print(f"\n--- Section: {section} ({len(urls)} endpoints) ---")
        for url in urls:
            print(f"  Fetching: {url}")
            html = fetch_page(url)
            if html:
                parsed = parse_endpoint_page(html, url, section)
                results[url] = parsed
                success_count += 1
                print(f"  OK ({len(parsed)} chars)")
            else:
                results[url] = None
                fail_count += 1
                failed_urls.append(url)
                print(f"  FAILED")
            time.sleep(1.5)  # Rate limiting

    # Build TOC
    toc = build_toc(SECTIONS, results)

    # Assemble full document
    full_doc = toc + "\n"
    for section, urls in SECTIONS.items():
        full_doc += f"\n# {section}\n\n"
        for url in urls:
            if results.get(url):
                full_doc += results[url]

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(full_doc)

    # Summary
    print(f"\n\n=== SUMMARY ===")
    print(f"Total URLs: {total_urls}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    if failed_urls:
        print(f"Failed URLs:")
        for u in failed_urls:
            print(f"  - {u}")
    print(f"\nOutput: {OUTPUT_FILE} ({len(full_doc)} chars, ~{full_doc.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
