import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

OPERA_PATH = r"C:\Users\User\AppData\Local\Programs\Opera GX\opera.exe"
USER_DATA = Path(__file__).parent / "opera_profile"

async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA,
            executable_path=OPERA_PATH,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )

        page = await context.new_page()

        print("Opening Pinterest login...")
        await page.goto(
            "https://www.pinterest.com/login/",
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("Log in manually in Opera GX.")
        input("Press ENTER here AFTER you are fully logged in...")

        await context.close()
        print("Opera GX session saved successfully.")

asyncio.run(main())
