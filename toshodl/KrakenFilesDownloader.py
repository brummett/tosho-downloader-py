from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright

from toshodl.DownloadSourceBase import DownloadSourceBase,XTryAnotherSource

class KrakenFilesDownloader(DownloadSourceBase):


    async def download_from_url(self):
        dl_link = await self.get_download_link()

        if dl_link:
            async with self.client.stream('GET', dl_link, timeout=30.0) as response:
                await self.save_stream_response(response)

    async def get_download_link(self):
        self.print(f"Attempting DL from { self.url }\n")
        async with async_playwright() as p:
            browser = await p.firefox.launch()
            ctx = await browser.new_context()
            page = await ctx.new_page()

            # Their ad stuff often redirects to a sponsor page the first
            # time, then gets to the right place on the second attempt,
            # but give it 5 attempt just because.  Note that it is _not_
            # opening new pages/tabs.
            i = 0
            while i < 5 and page.url != self.url:
                i += 1
                self.print(f"Navigating to { self.url }\n")
                await page.goto(self.url)
                self.print(f"Nav result { self.url } => { page.url }\n")
                self.print(f"ctx has { len(ctx.pages) } pages\n")
            if page.url != self.url:
                raise XTryAnotherSource

            self.print(f"Loaded { self.url }\n")
            form = page.locator('#dl-form')
            dl_button = form.locator('button[type="submit"]')

            try:
                async with page.expect_download() as download_info:
                    await dl_button.click()
            except Exception as e:
                self.print(f"*** Caught { type(e) }\n")
                self.print(f"*** exception { e }\n")
                self.print(f"after clicking download at { page.url }\n")
                await asyncio.sleep(5)
                raise e
            self.print(f"Clicked download for { self.url }\n")

            download = await download_info.value
            dl_url = download.url
            await download.cancel()
            await ctx.close()

        return dl_url
