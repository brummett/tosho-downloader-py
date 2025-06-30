from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from toshodl.DownloadSourceBase import DownloadSourceBase, XTryAnotherSource

class BuzzHeavierDownloader(DownloadSourceBase):

    async def download_from_url(self):
        response = await self.exception_retry(lambda: self.client.get(self.url))
        dl_link = await self.get_download_link(response)

        if dl_link:
            async with self.client.stream('GET', dl_link, timeout=30.0) as response:
                await self.save_stream_response(response)

    async def get_download_link(self, response):
        dom = BeautifulSoup(BytesIO(response.content), features='html.parser')

        # There's a link 'Download: <a hx-get="/hashhash/download">Download</a>'
        # Do a get() on that URL with some headers:
        #   * HX-Current-URL: self.url
        #   * HX-Request: true
        #   * Referer: self.url
        # You get a response with header "hx-redirect: /dl/6CeuijOH...?v=987123kjhfkjh"
        # Do a get() on that url (maybe without the ?v=...) to download.  It seems that
        # the DL links are one-time-only use

        link = dom.select_one('a.link-button')
        if not link:
            self.print('did not find download link at { self.url }')
            raise XTryAnotherSource()

        #self.print(f"Found link { link }\n")
        link_url = urljoin(self.url, link.get('hx-get'))
        #self.print(f"link url { link_url }\n")
        response = await self.client.get(link_url,
                            headers={ 'HX-Current-URL': self.url,
                                      'HX-Request': 'true',
                                      'Referer': self.url })

        dl_url = urljoin(self.url, response.headers['hx-redirect'])
        #self.print(f"{ self.url } => { dl_url })")

        return dl_url
