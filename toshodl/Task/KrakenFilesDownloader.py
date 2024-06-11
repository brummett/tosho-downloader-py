from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

from toshodl.FileDownloader import FileDownloader

logger = logging.getLogger(__name__)

class KrakenFilesDownloader(FileDownloader):
    # magic string needed to submit the download form
    wk_boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'

    #def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)

    async def task_impl(self):
        response = await self.timeout_retry(lambda: self.client.get(self.url))
        dl_link = await self.get_download_link(response)

        if dl_link:
            async with self.client.stream('GET', dl_link) as response:
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
            return

        return dl_info['url']
