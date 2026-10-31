from playwright.sync_api import sync_playwright
import urllib.parse
import sys

def test_maps(query="businesses in Banjara Hills Hyderabad"):
    url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"
    print(f"Navigating to {url}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-IN"
        )
        page = context.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_timeout(4000)
        
        # Check consent dialog or title
        print("Page title:", page.title())
        
        # Check elements
        links = page.locator('a[href*="/maps/place/"]').all()
        print(f"Found {len(links)} place links directly.")
        
        feed = page.locator('div[role="feed"]')
        print(f"Feed present: {feed.count() > 0}")
        
        browser.close()

if __name__ == "__main__":
    test_maps()
