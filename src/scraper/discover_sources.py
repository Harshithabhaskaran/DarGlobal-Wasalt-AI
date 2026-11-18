
import requests
import gzip
import xml.etree.ElementTree as ET

from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BOT_NAME = "DarGlobalResearchBot"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; "
        "DarGlobalResearchBot/1.0)"
    )
}

SITEMAPS = {
    "DarGlobal": [
        "https://darglobal.co.uk/sitemap.xml"
    ],
    "Wasalt": [
        "https://cdn.wasalt.sa/sitemap/static_sitemap_en_sa.xml.gz",
        "https://cdn.wasalt.sa/sitemap/category_sitemap_en_sa.xml.gz",
        "https://cdn.wasalt.sa/sitemap/product_sitemap_en_sa.xml.gz"
    ]
}

ROBOTS_PATHS = [
    "/",
    "/about",
    "/projects",
    "/blog",
    "/search",
    "/cdn-cgi/rum"
]

# Explicit restrictions confirmed from Wasalt robots.txt.
EXPLICIT_BLOCKED_PATHS = {
    "wasalt.sa": [
        "/search",
        "/cdn-cgi/rum"
    ]
}

TIMEOUT = 30

session = requests.Session()
session.headers.update(HEADERS)

robots_cache = {}


# --------------------------------------------------
# HELPER: DOMAIN
# --------------------------------------------------

def get_domain(base_url):
    return urlparse(base_url).netloc.lower()


# --------------------------------------------------
# 1. INSPECT ROBOTS.TXT
# --------------------------------------------------

def inspect_robots(base_url):

    robots_url = urljoin(base_url, "/robots.txt")
    domain = get_domain(base_url)

    print("\n" + "=" * 60)
    print("ROBOTS CHECK:", base_url)
    print("=" * 60)

    try:
        response = session.get(
            robots_url,
            timeout=TIMEOUT
        )

        print("HTTP status:", response.status_code)
        print("Robots URL:", robots_url)

        if response.status_code != 200:
            print("Could not retrieve robots.txt.")
            robots_cache[domain] = None
            return

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if "text/html" in content_type:
            print("Robots URL returned HTML, not robots.txt.")
            robots_cache[domain] = None
            return

        print("\nRaw robots.txt:")
        print(response.text)

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())

        # Refresh parser's internal parsed state.
        parser.modified()

        robots_cache[domain] = parser

        print("\nPath permissions:")

        for path in ROBOTS_PATHS:

            full_url = urljoin(base_url, path)

            allowed = is_allowed(
                domain,
                full_url
            )

            status = "ALLOWED" if allowed else "BLOCKED"

            print(f"{path}: {status}")

    except requests.RequestException as error:

        print("Robots error:", error)
        robots_cache[domain] = None


# --------------------------------------------------
# 2. CHECK EXPLICIT RESTRICTIONS
# --------------------------------------------------

def is_explicitly_blocked(domain, url):

    path = urlparse(url).path.lower()

    blocked_paths = EXPLICIT_BLOCKED_PATHS.get(
        domain,
        []
    )

    for blocked_path in blocked_paths:

        if (
            path == blocked_path
            or path.startswith(blocked_path + "/")
        ):
            return True

    return False


# --------------------------------------------------
# 3. CHECK ROBOTS PERMISSION
# --------------------------------------------------

def is_allowed(domain, url):

    # Apply explicit restrictions first.
    if is_explicitly_blocked(domain, url):
        return False

    parser = robots_cache.get(domain)

    # Fail closed if robots.txt was unavailable.
    if parser is None:
        return False

    return parser.can_fetch(
        BOT_NAME,
        url
    )


# --------------------------------------------------
# 4. READ SITEMAP
# --------------------------------------------------

def get_sitemap_urls(sitemap_url):

    print("\nReading sitemap:", sitemap_url)

    try:

        response = session.get(
            sitemap_url,
            timeout=60
        )

        print("HTTP status:", response.status_code)
        print(
            "Content type:",
            response.headers.get("Content-Type")
        )

        response.raise_for_status()

        content = response.content

        print(
            "First 10 bytes:",
            repr(content[:10])
        )

        # Detect actual gzip content.
        if content.startswith(b"\x1f\x8b"):
            content = gzip.decompress(content)

        # Do not parse security challenge HTML.
        preview = content.lstrip()[:100].lower()

        if (
            preview.startswith(b"<!doctype html")
            or preview.startswith(b"<html")
        ):
            print(
                "Sitemap returned HTML/challenge page. "
                "Skipping."
            )
            return []

        root = ET.fromstring(content)

        urls = []

        for element in root.iter():

            if element.tag.endswith("loc") and element.text:
                urls.append(element.text.strip())

        print("URLs found:", len(urls))

        for url in urls[:10]:
            print("-", url)

        return urls

    except Exception as error:

        print("Sitemap error:", error)
        return []


# --------------------------------------------------
# 5. INSPECT INDIVIDUAL WEB PAGES
# --------------------------------------------------

def inspect_page(url):

    domain = get_domain(url)

    print("\n" + "-" * 60)
    print("PAGE INSPECTION")
    print("-" * 60)

    print("URL:", url)

    if not is_allowed(domain, url):
        print("BLOCKED: robots policy does not permit this URL.")
        return

    try:

        response = session.get(
            url,
            timeout=TIMEOUT
        )

        print("Status:", response.status_code)
        print(
            "Content type:",
            response.headers.get("Content-Type")
        )
        print("HTML length:", len(response.text))

        if response.status_code in (401, 403, 429):
            print("Access restricted. Skipping.")
            return

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if "text/html" not in content_type:
            print("Not an HTML page. Skipping.")
            return

        html = response.text
        lower_html = html[:15000].lower()

        challenge_markers = [
            "just a moment",
            "cf_chl_opt",
            "incapsula",
            "request unsuccessful",
            "challenge-platform"
        ]

        if any(
            marker in lower_html
            for marker in challenge_markers
        ):
            print(
                "Security challenge detected. "
                "Not attempting to bypass."
            )
            return

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        title = (
            soup.title.get_text(strip=True)
            if soup.title
            else "Missing"
        )

        headings = [
            heading.get_text(" ", strip=True)
            for heading in soup.find_all("h1")[:5]
        ]

        print("Final URL:", response.url)
        print("Title:", title)
        print("H1 headings:", headings)
        print(
            "Script count:",
            len(soup.find_all("script"))
        )

        print("\nHTML preview:")
        print(repr(html[:1000]))

    except requests.RequestException as error:

        print("Page inspection error:", error)


# --------------------------------------------------
# 6. DEBUG DARGLOBAL HOMEPAGE
# --------------------------------------------------

def debug_darglobal():

    url = "https://darglobal.co.uk/"

    print("\n" + "=" * 60)
    print("DEBUGGING DARGLOBAL HOMEPAGE")
    print("=" * 60)

    if not is_allowed(
        "darglobal.co.uk",
        url
    ):
        print("DarGlobal homepage blocked by robots policy.")
        return

    try:

        response = session.get(
            url,
            timeout=TIMEOUT
        )

        print("Status:", response.status_code)
        print("Final URL:", response.url)
        print(
            "Content type:",
            response.headers.get("Content-Type")
        )
        print("HTML length:", len(response.text))

        print("\nResponse headers:")

        for key, value in response.headers.items():
            print(f"{key}: {value}")

        preview = response.text[:15000].lower()

        if (
            "incapsula" in preview
            or "request unsuccessful" in preview
        ):
            print(
                "\nIncapsula security page detected. "
                "Skipping content extraction."
            )
            return

        print("\nHTML preview:")
        print(repr(response.text[:3000]))

    except requests.RequestException as error:

        print("DarGlobal diagnostic error:", error)


# --------------------------------------------------
# 7. MAIN EXECUTION
# --------------------------------------------------

if __name__ == "__main__":

    # Load robots policies first.
    inspect_robots("https://darglobal.co.uk")
    inspect_robots("https://wasalt.sa")

    all_sitemap_urls = {}

    for company, sitemap_list in SITEMAPS.items():

        print("\n" + "=" * 60)
        print("SITEMAP:", company)
        print("=" * 60)

        company_urls = []

        for sitemap in sitemap_list:

            urls = get_sitemap_urls(sitemap)
            company_urls.extend(urls)

        # Remove duplicates.
        company_urls = list(
            dict.fromkeys(company_urls)
        )

        all_sitemap_urls[company] = company_urls

        print(
            "\nTotal unique URLs:",
            len(company_urls)
        )

        inspected = 0

        for url in company_urls:

            if inspected >= 2:
                break

            inspect_page(url)
            inspected += 1

    # DarGlobal diagnostic.
    debug_darglobal()

    print("\n" + "=" * 60)
    print("SOURCE DISCOVERY COMPLETED")
    print("=" * 60)

    for company, urls in all_sitemap_urls.items():

        print(
            f"{company}: {len(urls)} unique URLs"
        )
