import asyncio
import re
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm_asyncio
import threading
import time

# ---------------- CONFIG ----------------
OPERA_PATH = r"C:\Users\User\AppData\Local\Programs\Opera GX\opera.exe"
PROFILE_DIR = Path(__file__).parent / "opera_profile"
SCROLL_DELAY = 1
TIMEOUT = 60000
# ---------------- CONFIG ----------------

stop_scraping = False

def safe_name(text):
    return re.sub(r'[^\w\-\.]', '_', text)

def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()

def folder_from_type(ct):
    if "image" in ct: return "images"
    if "video" in ct: return "videos"
    if "javascript" in ct: return "scripts"
    if "css" in ct: return "styles"
    if "json" in ct: return "data"
    if "font" in ct: return "fonts"
    if "html" in ct: return "html"
    return "other"

def listen_for_stop():
    global stop_scraping
    print("Press 's' + Enter to stop scraping...")
    while not stop_scraping:
        user_input = input()
        if user_input.lower() == "s":
            stop_scraping = True
            print("Stopping scraper...")

async def scrape_pinterest_page(url):
    global stop_scraping
    base_dir = Path(__file__).parent
    root = base_dir / safe_name(url)
    root.mkdir(exist_ok=True)

    folders = {}
    for f in ["images","videos","scripts","styles","data","fonts","html","other"]:
        path = root / f
        path.mkdir(exist_ok=True)
        folders[f] = path

    downloaded = set()
    download_queue = []

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            executable_path=OPERA_PATH,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = await context.new_page()

        async def handle_response(res):
            try:
                ct = res.headers.get("content-type", "")
                data = await res.body()
                if len(data) < 500:
                    return

                h = hash_url(res.url)
                if h in downloaded:
                    return
                downloaded.add(h)

                folder = folders.get(folder_from_type(ct), folders["other"])
                ext = Path(urlparse(res.url).path).suffix or ".bin"
                filename = safe_name(res.url)[:150] + ext
                (folder / filename).write_bytes(data)
                download_queue.append((filename, folder))
            except:
                pass

        page.on("response", handle_response)

        print(f"Opening page: {url}")
        await page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")

        pbar = tqdm_asyncio(total=0, unit="files", dynamic_ncols=True)

        while not stop_scraping:
            await page.evaluate("() => { window.scrollBy(0, 2000); }")
            await asyncio.sleep(SCROLL_DELAY)

            if download_queue:
                pbar.total = len(downloaded)
                pbar.update(len(download_queue))
                for fname, folder in download_queue:
                    print(f"Downloaded: {folder}/{fname}")
                download_queue.clear()

        pbar.close()
        print(f"\nScraping stopped! Total files downloaded: {len(downloaded)}")
        await context.close()

if __name__ == "__main__":
    url_input = input("Enter Pinterest URL to scrape: ").strip()
    threading.Thread(target=listen_for_stop, daemon=True).start()
    asyncio.run(scrape_pinterest_page(url_input))
