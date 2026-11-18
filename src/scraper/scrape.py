
import gzip
import json
import random
import time
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


# =========================================================
# PROJECT PATHS AND CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = RAW_DIR / "scraped_pages.json"
ERROR_FILE = RAW_DIR / "scrape_errors.json"
INVENTORY_FILE = RAW_DIR / "sitemap_inventory.json"

BOT_NAME = "DarGlobalResearchBot"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; DarGlobalResearchBot/1.0; "
        "+https://example.com/research)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.5

MAX_STATIC_PAGES = 8
MAX_CATEGORY_PAGES = 12
MAX_PRODUCT_PAGES = 15

MAX_CONTENT_LENGTH = 15000

SITEMAPS = {
    "wasalt": {
        "static": (
            "https://cdn.wasalt.sa/sitemap/"
            "static_sitemap_en_sa.xml.gz"
        ),
        "category": (
            "https://cdn.wasalt.sa/sitemap/"
            "category_sitemap_en_sa.xml.gz"
        ),
        "product": (
            "https://cdn.wasalt.sa/sitemap/"
            "product_sitemap_en_sa.xml.gz"
        ),
    },
    "darglobal": {
        "main": "https://darglobal.co.uk/sitemap.xml",
    },
}

ROBOTS_URLS = {
    "wasalt": "https://wasalt.sa/robots.txt",
    "darglobal": "https://darglobal.co.uk/robots.txt",
}

EXCLUDED_PATHS = [
    "/search",
    "/cdn-cgi/rum",
]

NOISE_KEYWORDS = [
    "breadcrumb",
    "navigation",
    "navbar",
    "footer",
    "header",
    "sidebar",
    "related",
    "recommend",
    "suggested",
    "similar-property",
    "similar-properties",
    "pagination",
    "filter",
    "cookie",
    "social-share",
    "share-buttons",
]


# =========================================================
# SESSION
# =========================================================

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# =========================================================
# LOGGING
# =========================================================

def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


# =========================================================
# ERROR HANDLING
# =========================================================

ERRORS = []


def record_error(url, error):
    ERRORS.append({
        "url": url,
        "error": str(error),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })


# =========================================================
# ROBOTS.TXT
# =========================================================

def load_robots_policy(website, robots_url):

    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        response = SESSION.get(
            robots_url,
            timeout=REQUEST_TIMEOUT,
        )

        log(f"Robots check: {robots_url} -> {response.status_code}")

        if response.status_code != 200:
            log(f"Robots policy unavailable for {website}")
            return None

        content = response.text.strip()

        # Do not interpret HTML challenge pages as robots.txt.
        if "<html" in content.lower() or "<!doctype html" in content.lower():
            log(f"Invalid robots.txt response for {website}")
            return None

        parser.parse(content.splitlines())

        log(f"Robots policy loaded for {website}")

        return parser

    except requests.RequestException as error:
        log(f"Robots request failed for {website}: {error}")
        return None


def is_allowed(url, robots_policy):

    if robots_policy is None:
        return False

    parsed = urlparse(url)
    path = parsed.path.lower()

    for blocked_path in EXCLUDED_PATHS:
        if path.startswith(blocked_path):
            return False

    try:
        return robots_policy.can_fetch(BOT_NAME, url)
    except Exception:
        return False


# =========================================================
# HTTP REQUEST
# =========================================================

def fetch_url(url):

    response = SESSION.get(
        url,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )

    return response


# =========================================================
# SITEMAP EXTRACTION
# =========================================================

def fetch_sitemap_urls(sitemap_url):

    log(f"Sitemap: {sitemap_url}")

    try:
        response = fetch_url(sitemap_url)

        response.raise_for_status()

        content = response.content

        # Detect gzip using file signature.
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)

        text_content = content.decode(
            "utf-8",
            errors="replace",
        )

        if "<html" in text_content[:1000].lower():
            raise ValueError("Sitemap returned HTML instead of XML")

        root = ET.fromstring(content)

        urls = []

        for element in root.iter():
            if element.tag.endswith("loc"):
                if element.text:
                    urls.append(element.text.strip())

        log(f"URLs found: {len(urls)}")

        return urls

    except Exception as error:
        log(f"Sitemap error: {sitemap_url} -> {error}")
        record_error(sitemap_url, error)
        return []


# =========================================================
# SELECT WASALT URLS
# =========================================================

def select_wasalt_urls(sitemap_data):

    selected = []

    static_urls = sitemap_data.get("static", [])
    category_urls = sitemap_data.get("category", [])
    product_urls = sitemap_data.get("product", [])

    selected.extend(static_urls[:MAX_STATIC_PAGES])

    selected.extend(category_urls[:MAX_CATEGORY_PAGES])

    selected.extend(product_urls[:MAX_PRODUCT_PAGES])

    # Remove duplicates while preserving order.
    selected = list(dict.fromkeys(selected))

    return selected


# =========================================================
# JSON-LD EXTRACTION
# =========================================================

def extract_json_ld(soup):

    structured_data = []

    for script in soup.find_all(
        "script",
        type="application/ld+json",
    ):

        try:
            raw_json = script.string or script.get_text()

            if not raw_json:
                continue

            parsed_json = json.loads(raw_json)

            structured_data.append(parsed_json)

        except (json.JSONDecodeError, TypeError):
            continue

    return structured_data


# =========================================================
# SAFE CLASS AND ID EXTRACTION
# =========================================================

def get_element_classes_and_id(element):

    classes = element.get("class") or []
    element_id = element.get("id") or ""

    class_text = " ".join(classes).lower()
    id_text = str(element_id).lower()

    return f"{class_text} {id_text}"


# =========================================================
# CLEAN HTML CONTENT
# =========================================================

def extract_clean_content(soup):

    # Remove clearly irrelevant HTML tags.
    for tag in soup.find_all([
        "script",
        "style",
        "noscript",
        "svg",
        "footer",
        "nav",
        "header",
        "aside",
        "form",
        "iframe",
        "button",
    ]):

        if tag.parent is not None:
            tag.decompose()

    # Remove noisy elements.
    # Only remove top-level matching elements so that
    # descendants of already-removed elements are not processed.
    matching_elements = []

    for element in soup.find_all(True):

        if element.parent is None:
            continue

        combined = get_element_classes_and_id(element)

        if any(
            keyword in combined
            for keyword in NOISE_KEYWORDS
        ):
            matching_elements.append(element)

    matching_set = set(matching_elements)

    for element in matching_elements:

        # If a parent is already scheduled for removal,
        # do not attempt to remove its child separately.
        parent = element.parent
        parent_is_matching = False

        while parent is not None:

            if parent in matching_set:
                parent_is_matching = True
                break

            parent = parent.parent

        if not parent_is_matching and element.parent is not None:
            element.decompose()

    # Prefer article or main content.
    main_content = soup.find("article")

    if main_content is None:
        main_content = soup.find("main")

    if main_content is None:
        main_content = soup.body

    if main_content is None:
        main_content = soup

    # Remove containers dominated by links.
    for element in list(main_content.find_all(
        ["div", "section", "ul", "ol"]
    )):

        if element.parent is None:
            continue

        element_text = element.get_text(" ", strip=True)

        if len(element_text) < 150:
            continue

        link_text = " ".join(
            link.get_text(" ", strip=True)
            for link in element.find_all("a")
        )

        if not element_text:
            continue

        link_ratio = len(link_text) / max(len(element_text), 1)

        if link_ratio > 0.75 and element.parent is not None:
            element.decompose()

    # Extract meaningful text elements.
    text_elements = main_content.find_all([
        "h1",
        "h2",
        "h3",
        "h4",
        "p",
        "li",
        "dt",
        "dd",
        "tr",
    ])

    lines = []

    for element in text_elements:

        if element.parent is None:
            continue

        text = element.get_text(" ", strip=True)

        text = " ".join(text.split())

        if len(text) < 2:
            continue

        lines.append(text)

    # Fallback if semantic elements were not found.
    if not lines:

        fallback_text = main_content.get_text(
            "\n",
            strip=True,
        )

        lines = [
            " ".join(line.split())
            for line in fallback_text.splitlines()
            if len(line.strip()) >= 2
        ]

    # Remove adjacent duplicate lines.
    cleaned_lines = []

    for line in lines:

        if not cleaned_lines or line != cleaned_lines[-1]:
            cleaned_lines.append(line)

    content = "\n".join(cleaned_lines)

    return content[:MAX_CONTENT_LENGTH]


# =========================================================
# SAFE META EXTRACTION
# =========================================================

def get_meta_content(soup, **attrs):

    tag = soup.find("meta", attrs=attrs)

    if tag is None:
        return ""

    return (tag.get("content") or "").strip()


# =========================================================
# PAGE EXTRACTION
# =========================================================

def extract_page(url, website, robots_policy):

    if not is_allowed(url, robots_policy):
        raise PermissionError(
            "URL is not permitted by the available robots policy"
        )

    response = fetch_url(url)

    log(f"Page: {response.status_code} {url}")

    response.raise_for_status()

    # Do not continue after restricted or suspicious responses.
    if response.status_code in [401, 403, 429]:
        raise PermissionError(
            f"Access restricted: HTTP {response.status_code}"
        )

    content_type = response.headers.get(
        "Content-Type",
        "",
    ).lower()

    if "html" not in content_type:
        raise ValueError(
            f"Not an HTML page: {content_type}"
        )

    final_url = response.url

    if not is_allowed(final_url, robots_policy):
        raise PermissionError(
            "Final redirected URL is not permitted by robots.txt"
        )

    html = response.text

    # Detect challenge pages.
    challenge_markers = [
        "cf-browser-verification",
        "cf-challenge",
        "just a moment...",
        "checking your browser",
    ]

    lower_html = html.lower()

    if any(
        marker in lower_html
        for marker in challenge_markers
    ):
        raise PermissionError(
            "Possible anti-bot challenge detected; page not processed"
        )

    soup = BeautifulSoup(html, "lxml")

    # Extract structured data before modifying the soup.
    json_ld = extract_json_ld(soup)

    # Safely extract title.
    title_tag = soup.find("title")

    title = (
        title_tag.get_text(" ", strip=True)
        if title_tag
        else ""
    )

    # Safely extract description.
    meta_description = (
        get_meta_content(soup, name="description")
        or get_meta_content(soup, property="og:description")
    )

    # Extract clean content.
    content = extract_clean_content(soup)

    # Extract headings from the cleaned soup.
    headings = [
        heading.get_text(" ", strip=True)
        for heading in soup.find_all([
            "h1",
            "h2",
            "h3",
            "h4",
        ])
        if heading.get_text(strip=True)
    ]

    # Determine page type.
    page_path = urlparse(final_url).path.lower()

    page_type = (
        "property"
        if "/property/" in page_path
        else "general"
    )

    return {
        "website": website,
        "url": final_url,
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "content": content,
        "json_ld": json_ld,
        "page_type": page_type,
        "scraped_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# =========================================================
# SAVE JSON
# =========================================================

def save_json(data, filepath):

    with open(
        filepath,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )


# =========================================================
# MAIN EXECUTION
# =========================================================

def main():

    log("=" * 60)
    log("DarGlobal + Wasalt data collection started")
    log("=" * 60)

    scraped_pages = []

    # -----------------------------------------------------
    # LOAD ROBOTS POLICIES
    # -----------------------------------------------------

    robots_policies = {}

    for website, robots_url in ROBOTS_URLS.items():

        robots_policies[website] = load_robots_policy(
            website,
            robots_url,
        )

    # -----------------------------------------------------
    # FETCH WASALT SITEMAPS
    # -----------------------------------------------------

    wasalt_sitemap_data = {}

    for sitemap_type, sitemap_url in SITEMAPS["wasalt"].items():

        wasalt_sitemap_data[sitemap_type] = fetch_sitemap_urls(
            sitemap_url
        )

    # -----------------------------------------------------
    # FETCH DARGLOBAL SITEMAP
    # -----------------------------------------------------

    darglobal_urls = fetch_sitemap_urls(
        SITEMAPS["darglobal"]["main"]
    )

    # -----------------------------------------------------
    # SAVE INVENTORY
    # -----------------------------------------------------

    inventory = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "wasalt": {
            "static_url_count": len(
                wasalt_sitemap_data.get("static", [])
            ),

            "category_url_count": len(
                wasalt_sitemap_data.get("category", [])
            ),

            "product_url_count": len(
                wasalt_sitemap_data.get("product", [])
            ),
        },

        "darglobal_url_count": len(darglobal_urls),
    }

    save_json(inventory, INVENTORY_FILE)

    log(f"Inventory saved: {INVENTORY_FILE}")

    # -----------------------------------------------------
    # SELECT WASALT URLS
    # -----------------------------------------------------

    selected_urls = select_wasalt_urls(
        wasalt_sitemap_data
    )

    log(f"Selected Wasalt URLs: {len(selected_urls)}")

    wasalt_robots = robots_policies.get("wasalt")

    # -----------------------------------------------------
    # SCRAPE WASALT
    # -----------------------------------------------------

    for index, url in enumerate(selected_urls, start=1):

        log(
            f"Wasalt page {index}/{len(selected_urls)}"
        )

        try:

            page = extract_page(
                url=url,
                website="Wasalt",
                robots_policy=wasalt_robots,
            )

            scraped_pages.append(page)

            log(
                f"Successfully extracted: {page['title'][:80]}"
            )

        except Exception as error:

            log(f"Page extraction error: {error}")

            record_error(url, error)

        time.sleep(
            REQUEST_DELAY + random.uniform(0, 0.5)
        )

    # -----------------------------------------------------
    # DARGLOBAL SCRAPING POLICY
    # -----------------------------------------------------

    darglobal_robots = robots_policies.get("darglobal")

    if darglobal_robots is not None:

        log(
            "DarGlobal robots policy loaded. "
            "No DarGlobal pages selected in this initial run."
        )

    else:

        log(
            "DarGlobal robots policy could not be verified. "
            "Skipping DarGlobal page scraping."
        )

    # -----------------------------------------------------
    # SAVE SCRAPED DATA AND ERRORS
    # -----------------------------------------------------

    save_json(
        scraped_pages,
        OUTPUT_FILE,
    )

    save_json(
        ERRORS,
        ERROR_FILE,
    )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    wasalt_count = sum(
        1
        for page in scraped_pages
        if page["website"] == "Wasalt"
    )

    property_count = sum(
        1
        for page in scraped_pages
        if page["page_type"] == "property"
    )

    log("=" * 60)
    log("SCRAPING SUMMARY")
    log("=" * 60)

    log(f"Wasalt pages scraped: {wasalt_count}")
    log(f"Property pages scraped: {property_count}")
    log(f"DarGlobal sitemap URLs discovered: {len(darglobal_urls)}")
    log(f"Errors recorded: {len(ERRORS)}")

    log(f"Scraped data: {OUTPUT_FILE}")
    log(f"Errors: {ERROR_FILE}")

    log("=" * 60)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
