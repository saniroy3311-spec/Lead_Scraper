import sys
import re
import urllib.parse
from playwright.sync_api import sync_playwright

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def scrape_gyms():
    query = "gym in Singur Hooghly"
    url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"
    print(f"Querying: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-IN"
        )
        page = context.new_page()
        page.goto(url, timeout=35000)
        page.wait_for_timeout(4000)
        
        feed = page.locator('div[role="feed"]')
        if feed.count() > 0:
            for _ in range(5):
                feed.evaluate("el => el.scrollBy(0, 1500)")
                page.wait_for_timeout(1500)
                
        articles = page.locator('div[role="feed"] > div > div[role="article"]').all()
        print(f"Total articles found: {len(articles)}")
        
        results = []
        for a in articles:
            text = a.inner_text()
            link_el = a.locator('a.hfpxzc').first
            maps_url = link_el.get_attribute('href') if link_el.count() > 0 else ''
            title = link_el.get_attribute('aria-label') if link_el.count() > 0 else ''
            
            # website button
            web_el = a.locator('a[aria-label*="website" i], a[data-value="Website"]').first
            website = web_el.get_attribute('href') if web_el.count() > 0 else ""
            
            if title:
                results.append({
                    "title": title,
                    "text": text,
                    "maps_url": maps_url,
                    "website": website
                })
        
        browser.close()
        return results

if __name__ == "__main__":
    items = scrape_gyms()
    print(f"Extracted {len(items)} gyms:")
    for i, it in enumerate(items, 1):
        print(f"--- Gym {i}: {it['title']} ---")
        print(f"Website: {it['website']}")
        print(f"Maps: {it['maps_url']}")
        print(f"Details:\n{it['text']}")
