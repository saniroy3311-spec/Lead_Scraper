from playwright.sync_api import sync_playwright
import urllib.parse
import time
import re

def inspect_feed(query="businesses in Banjara Hills Hyderabad"):
    url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-IN"
        )
        page = context.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)
        
        feed = page.locator('div[role="feed"]')
        # scroll 2 times
        for _ in range(2):
            feed.evaluate("el => el.scrollBy(0, 1000)")
            page.wait_for_timeout(1500)
            
        articles = page.locator('div[role="feed"] > div > div[role="article"]').all()
        print(f"Articles found: {len(articles)}")
        
        results = []
        for a in articles[:5]:
            text = a.inner_text()
            link_el = a.locator('a.hfpxzc').first
            maps_url = link_el.get_attribute('href') if link_el.count() > 0 else ""
            title = link_el.get_attribute('aria-label') if link_el.count() > 0 else ""
            results.append({
                "title": title,
                "maps_url": maps_url,
                "text_lines": text.split("\n")
            })
            
        print("Sample extracted:", json.dumps(results, indent=2))
        browser.close()

if __name__ == "__main__":
    import json
    inspect_feed()
