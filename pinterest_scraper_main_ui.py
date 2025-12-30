import asyncio
import re
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm_asyncio
import threading
import tkinter as tk
from tkinter import ttk, filedialog

# ---------------- CONFIG ----------------
OPERA_PATH = r"C:\Users\User\AppData\Local\Programs\Opera GX\opera.exe"
PROFILE_DIR = Path(__file__).parent / "opera_profile"
SCROLL_DELAY = 1
TIMEOUT = 60000
# ---------------- CONFIG ----------------

stop_scraping = False
download_folder = Path(__file__).parent
progress_var = None
status_var = None

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

def update_status(text):
    if status_var:
        status_var.set(text)

def update_progress(total, completed):
    if progress_var:
        progress_var['maximum'] = total
        progress_var['value'] = completed

async def scrape_pinterest_page(url):
    global stop_scraping, download_folder
    root = download_folder / safe_name(url)
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

        update_status(f"Opening page: {url}")
        await page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")

        pbar_total = 0
        while not stop_scraping:
            await page.evaluate("() => { window.scrollBy(0, 2000); }")
            await asyncio.sleep(SCROLL_DELAY)

            if download_queue:
                pbar_total = len(downloaded)
                update_progress(pbar_total, pbar_total)
                for fname, folder in download_queue:
                    update_status(f"Downloaded: {folder}/{fname}")
                download_queue.clear()

        update_status(f"Scraping stopped! Total files downloaded: {len(downloaded)}")
        await context.close()

def start_scraper_thread(url):
    global stop_scraping
    stop_scraping = False
    asyncio.run(scrape_pinterest_page(url))

def start_scraping():
    url = url_entry.get().strip()
    if not url:
        update_status("Please enter a URL!")
        return
    threading.Thread(target=start_scraper_thread, args=(url,), daemon=True).start()

def stop_scraping_func():
    global stop_scraping
    stop_scraping = True
    update_status("Stopping scraper...")

def choose_folder():
    global download_folder
    folder = filedialog.askdirectory()
    if folder:
        download_folder = Path(folder)
        folder_label.config(text=str(download_folder))

root = tk.Tk()
root.title("Pinterest Scraper GUI")
root.geometry("600x200")

tk.Label(root, text="Pinterest URL:").pack(pady=5)
url_entry = tk.Entry(root, width=80)
url_entry.pack()

folder_btn = tk.Button(root, text="Choose Download Folder", command=choose_folder)
folder_btn.pack(pady=5)
folder_label = tk.Label(root, text=str(download_folder))
folder_label.pack()

start_btn = tk.Button(root, text="Start Scraping", command=start_scraping)
start_btn.pack(pady=5)

stop_btn = tk.Button(root, text="Stop Scraping", command=stop_scraping_func)
stop_btn.pack(pady=5)

status_var = tk.StringVar()
status_label = tk.Label(root, textvariable=status_var, wraplength=580)
status_label.pack(pady=5)

progress_var = ttk.Progressbar(root, orient='horizontal', length=580, mode='determinate')
progress_var.pack(pady=5)

root.mainloop()
