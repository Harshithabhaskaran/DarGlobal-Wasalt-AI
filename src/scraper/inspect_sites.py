
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBSITES = {
    "DarGlobal": "https://darglobal.co.uk/",
    "Wasalt": "https://wasalt.sa/en"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"
}


def inspect_website(name, url):

    print("\n" + "=" * 60)
    print(f"WEBSITE: {name}")
    print("=" * 60)

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        print("Status code:", response.status_code)
        print("Final URL:", response.url)
        print("Content type:", response.headers.get("Content-Type"))

        soup = BeautifulSoup(response.text, "lxml")

        print("Page title:",
              soup.title.get_text(strip=True) if soup.title else "N/A")

        print("\nMain headings:")

        for heading in soup.find_all(["h1", "h2", "h3"])[:15]:
            print("-", heading.get_text(" ", strip=True))

        print("\nInternal links:")

        count = 0

        for link in soup.find_all("a", href=True):

            full_url = urljoin(response.url, link["href"])

            if full_url.startswith(url.split("/")[0] + "//"):
                print(
                    link.get_text(" ", strip=True)[:80],
                    "->",
                    full_url
                )
                count += 1

            if count >= 15:
                break

        print("\nRobots.txt:")

        robots_url = urljoin(response.url, "/robots.txt")
        robots_response = requests.get(
            robots_url,
            headers=HEADERS,
            timeout=20
        )

        print("Status:", robots_response.status_code)
        print(robots_response.text[:3000])

        print("\nSitemap:")

        sitemap_url = urljoin(response.url, "/sitemap.xml")
        sitemap_response = requests.get(
            sitemap_url,
            headers=HEADERS,
            timeout=20
        )

        print("Status:", sitemap_response.status_code)
        print(sitemap_response.text[:1500])

    except requests.RequestException as error:
        print("Website inspection error:", error)


if __name__ == "__main__":

    for name, url in WEBSITES.items():
        inspect_website(name, url)
