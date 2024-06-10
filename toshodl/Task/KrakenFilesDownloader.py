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

    async def make_initial_request(self):
        return self.client.build_request('GET', self.url)

    async def get_download_link(self, response):
        dom = BeautifulSoup(BytesIO(response.content), features='html.parser')

        # There's a form with a download button inside.  Submit the form and get
        # back a bit of JSON with a URL of the file\

        form = dom.select_one('#dl-form')
        dl_token = form.select_one('#dl-token').get('value') # hidden input
        file_hash = dom.select_one('div[data-file-hash]').get('data-file-hash')

        form_action = urljoin(self.url, form.get('action'))

        payload = f'--{self.wk_boundary}\r\nContent-Disposition: form-data; name="token"\r\n\r\n{dl_token}\r\n--{self.wk_boundary}--'
        form_response = await self.client.post(form_action,
                                headers={ 'Content-Type': f'multipart/form-data; boundary={ self.wk_boundary }',
                                          'cache-control': 'no-cache',
                                          'hash': file_hash },
                                data=payload,
                        )

        dl_info = form_response.json()
        if dl_info['status'] != 'ok':
            self.print(f"Bad status processing { self.url }: { dl_info }\n")
            return

        return dl_info['url']

    async def make_download_request(self, url):
        #return self.client.stream('GET', url)
        return self.client.build_request('GET', url)
