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
            page = await browser.new_page()
            await page.goto(self.url)
            self.print(f"Loaded { self.url }\n")

            form = page.locator('#dl-form')
            dl_button = form.locator('button[type="submit"]')

            async with page.expect_download() as download_info:
                await dl_button.click()
                self.print(f"Clicked download for { self.url }\n")

            download = await download_info.value
            dl_url = download.url
            await download.cancel()
            await page.close()

        return dl_url
