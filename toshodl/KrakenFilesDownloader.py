from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from toshodl.DownloadSourceBase import DownloadSourceBase,XTryAnotherSource

class KrakenFilesDownloader(DownloadSourceBase):

    # magic string needed to submit the download form
    wk_boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'

    async def download_from_url(self):
        response = await self.exception_retry(lambda: self.client.get(self.url))
        dl_link = await self.get_download_link(response)

        if dl_link:
            async with self.client.stream('GET', dl_link, timeout=30.0) as response:
                await self.save_stream_response(response)

    async def get_download_link(self, response):
        dom = BeautifulSoup(BytesIO(response.content), features='html.parser')

        # There's a form with a download button inside.  Submit the form and get
        # back a bit of JSON with a URL of the file\

        form = dom.select_one('#dl-form')
        dl_token = form.select_one('#dl-token').get('value') # hidden input
        file_hash = dom.select_one('div[data-file-hash]').get('data-file-hash')

        form_action = urljoin(self.url, form.get('action'))

        # I expected httpx to properly handle a custom boundary
        # given structured data like this: data = { 'token': file_hash }
        # https://github.com/encode/httpx/pull/2278
        # Maybe the version I'm using doesn't have the change in that PR?
        payload = f'--{self.wk_boundary}\r\nContent-Disposition: form-data; name="token"\r\n\r\n{dl_token}\r\n--{self.wk_boundary}--'
        form_response = await self.client.post(form_action,
                                headers={ 'Content-Type': f'multipart/form-data; boundary={ self.wk_boundary }',
                                          'cache-control': 'no-cache',
                                          'hash': file_hash },
                                data=payload,
                        )

        dl_info = form_response.json()
        if dl_info['status'] != 'ok':
            self.print(f"*** Bad status processing { self.url }: { dl_info }\n")
            raise XTryAnotherSource

        return dl_info['url']
