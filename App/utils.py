import asyncio
import csv
import json
import re
import sys
from playwright.async_api import async_playwright
from asgiref.sync import sync_to_async

class Webscraper:
    def __init__(self, query: str, headless: bool = True, output_format: str = 'csv', max_pages: int = 1):
        self.query = query
        self.headless = headless
        self.output_format = output_format
        self.max_pages = max_pages
        self.playwright = None
        self.browser = None

    async def _init_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        # Context with a real User-Agent to stay under the radar
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()

    def save_results(self, data, filename: str = None):
        if not filename:
            filename = f"results/{self.__class__.__name__.lower()}_results.{self.output_format}"
        if not data:
            print("No data found to save.")
            return
            
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if self.output_format == 'csv':
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            else:
                json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(data)} items to {filename}")


class AmazonScraper(Webscraper):
    def __init__(self, query: str, headless: bool = False, output_format: str = 'csv', max_pages: int = 1):
        super().__init__(query, headless, output_format, max_pages)

    async def scrape(self):
        await self._init_browser()
        results = []
        try:
            for page_num in range(1, self.max_pages + 1):
                search_url = f"https://www.amazon.fr/s?k={self.query.replace(' ', '+')}&page={page_num}"
                print(f"Loading Amazon Page {page_num}...")
                await self.page.goto(search_url, wait_until="domcontentloaded")
                
                await self.page.wait_for_selector('div[data-component-type="s-search-result"]')

                # ONE ROUND-TRIP EXTRACTION
                page_data = await self.page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('div[data-component-type="s-search-result"]')).map(el => {
                        const titleEl = el.querySelector('h2 a span') || el.querySelector('h2 span');
                        const priceW = el.querySelector('span.a-price-whole');
                        const priceF = el.querySelector('span.a-price-fraction');
                        const symbol = el.querySelector('span.a-price-symbol');
                        const linkEl = el.querySelector('a.a-link-normal');
                        const imgEl = el.querySelector('img.s-image');

                        return {
                            title: titleEl ? titleEl.innerText : null,
                            priceWhole: priceW ? priceW.innerText : null,
                            priceFraction: priceF ? priceF.innerText : "00",
                            currency: symbol ? symbol.innerText : "€",
                            url: linkEl ? linkEl.href : "N/A",
                            img: imgEl ? imgEl.src : "N/A"
                        };
                    });
                }''')

                print(f"Found {len(page_data)} products on page {page_num} on Amazon")

                for item in page_data:
                    if not item['title'] or not item['priceWhole']:
                        continue

                    try:
                        # Fast cleaning in Python
                        pw = "".join(filter(str.isdigit, item['priceWhole']))
                        pf = "".join(filter(str.isdigit, item['priceFraction']))
                        results.append({
                            'title': item['title'].strip(),
                            'price': float(f"{pw}.{pf}"),
                            'currency': item['currency'].strip(),
                            'source': 'Amazon',
                            'url': item['url'],
                            'img': item['img']
                        })
                    except: continue
        finally:
            await self.browser.close()
            await self.playwright.stop()
        return results

class EbayScraper(Webscraper):
    # Placeholder for eBay scraper implementation
    def __init__(self, query, headless = False, output_format = 'csv', max_pages = 1):
        super().__init__(query, headless, output_format, max_pages)
    
    async def scrape(self):
        await self._init_browser()
        results = []
        try:
            for page_num in range(1, self.max_pages + 1):
                search_url = f"https://www.ebay.fr/sch/i.html?_nkw={self.query.replace(' ', '+')}&_pgn={page_num}"
                print(f"Loading eBay Page {page_num}...")
                await self.page.goto(search_url, wait_until="domcontentloaded")
                
                await self.page.wait_for_selector('.su-card-container')

                # ONE ROUND-TRIP EXTRACTION
                page_data = await self.page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('.su-card-container')).map(el => {
                        const titleEl = el.querySelector('.s-card__title span.primary');
                        const priceEl = el.querySelector('.s-card__price');
                        const linkEl = el.querySelector('a.s-card__link');
                        const imgEl = el.querySelector('img');

                        return {
                            title: titleEl ? titleEl.innerText : null,
                            priceRaw: priceEl ? priceEl.innerText : null,
                            url: linkEl ? linkEl.href : "N/A",
                            img: imgEl ? imgEl.src : "N/A"
                        };
                    });
                }''')

                print(f"Found {len(page_data)} products on page {page_num} on eBay")

                for item in page_data:
                    if not item['title'] or not item['priceRaw']:
                        continue

                    try:
                        price_digits = "".join(filter(lambda x: x.isdigit() or x == ',', item['priceRaw']))
                        results.append({
                            'title': item['title'].strip(),
                            'price': float(price_digits.replace(',', '.')),
                            'currency': '€',
                            'source': 'eBay',
                            'url': item['url'],
                            'img': item['img']
                        })
                    except: continue
        finally:
            await self.browser.close()
            await self.playwright.stop()
        return results[2:]

class CdiscountScraper(Webscraper):
    def __init__(self, query, headless = False, output_format = 'csv', max_pages = 1):
        super().__init__(query, headless, output_format, max_pages)

    async def scrape(self):
        await self._init_browser()
        results = []
        try:
            for page_num in range(1, self.max_pages + 1):
                search_url = f"https://www.cdiscount.com/search/10/{self.query.replace(' ', '+')}.html?page={page_num}"
                print(f"Loading Cdiscount Page {page_num}...")
                
                # Use "commit" or "domcontentloaded" for faster initial load
                await self.page.goto(search_url, wait_until="domcontentloaded")
                
                # --- SPEED-OPTIMIZED SCROLL ---
                # Instead of viewport-by-viewport, we take 4 large jumps.
                # 3000px jumps cover most of Cdiscount's 60-item grid in ~1.2 seconds.
                for _ in range(4):
                    await self.page.evaluate("window.scrollBy(0, 3000)")
                    await asyncio.sleep(0.3) # Short sleep to trigger React hydration
                
                # Jump back to top so early items are definitely in memory
                await self.page.evaluate("window.scrollTo(0, 0)")
                # ------------------------------

                # Reduced timeout: if it's not there in 5s, it's not there.
                try:
                    await self.page.wait_for_selector('article[data-e2e="offer-item"]', timeout=5000)
                except:
                    break

                products = await self.page.query_selector_all('article[data-e2e="offer-item"]')
                
                # Optimization: Extract data using JavaScript in one go for all items 
                # to avoid multiple slow Python-to-Browser roundtrips.
                page_data = await self.page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('article[data-e2e="offer-item"]')).map(el => {
                        const titleEl = el.querySelector('[data-e2e="lplr-title"]');
                        const priceEl = el.querySelector('.price span') || el.querySelector('[data-e2e="lplr-price"] span');
                        const imgEl = el.querySelector('img');
                        const linkEl = titleEl ? titleEl.closest('a') : el.querySelector('a');
                        
                        return {
                            title: titleEl ? titleEl.innerText : null,
                            priceRaw: priceEl ? priceEl.innerText : null,
                            url: linkEl ? linkEl.href : "N/A",
                            img: imgEl ? (imgEl.src || imgEl.getAttribute('data-src')) : "N/A"
                        };
                    });
                }''')
                print(f"Found {len(page_data)} products on page {page_num} on Cdiscount")
                for item in page_data:
                    if not item['title'] or not item['priceRaw']:
                        continue

                    # Fast cleaning in Python
                    try:
                        clean_price = re.sub(r'[^\d,]', '', item['priceRaw']).replace(',', '.')
                        price = float(clean_price)
                        
                        # Protocol fix
                        img = item['img']
                        if img.startswith('//'): img = f"https:{img}"

                        results.append({
                            'title': item['title'].strip(),
                            'price': price,
                            'currency': '€',
                            'source': 'Cdiscount',
                            'url': item['url'],
                            'img': img
                        })
                    except:
                        continue
                
        finally:
            await self.browser.close()
            await self.playwright.stop()
            
        return results


if __name__ == "__main__":
    # Run all scrapers simultaneously for testing
    query = 'rtx 4060'
    async def run_all_scrapers():
        amazon_scraper = AmazonScraper(query, headless=True, output_format='csv', max_pages=2)
        ebay_scraper = EbayScraper(query, headless=True, output_format='csv', max_pages=2)
        cdiscount_scraper = CdiscountScraper(query, headless=True, output_format='csv', max_pages=2)

        tasks = [
            amazon_scraper.scrape(),
            ebay_scraper.scrape(),
            cdiscount_scraper.scrape()
        ]

        all_results = await asyncio.gather(*tasks)

        # Save results
        amazon_scraper.save_results(all_results[0])
        ebay_scraper.save_results(all_results[1])
        cdiscount_scraper.save_results(all_results[2])

    asyncio.run(run_all_scrapers())

async def run_parallel_scrapers(query):
    """Triggers all scrapers at once."""
    amazon = AmazonScraper(query, headless=True)
    ebay = EbayScraper(query, headless=True)
    cdiscount = CdiscountScraper(query, headless=True)

    tasks = [amazon.scrape(), ebay.scrape(), cdiscount.scrape()]
    raw_results = await asyncio.gather(*tasks)
    
    # Flatten list of lists into one list
    return [item for sublist in raw_results for item in sublist]

def threaded_wrapper(query):
    """FIX: Creates a Proactor Loop in a new thread for Windows compatibility."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_parallel_scrapers(query))
    finally:
        loop.close()

# The View will call this
get_results_safe = sync_to_async(threaded_wrapper, thread_sensitive=False)