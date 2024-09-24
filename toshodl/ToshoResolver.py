# Given a tosho ID, return PickFileDownloadSource tasks for each file.  If the ID
# is for a batch, there will be one task per file in the batch

import httpx
import asyncio

from toshodl.Printable import Printable
from toshodl.FileDownloader import FileDownloader
from toshodl.HttpClient import HttpClient

class ToshoResolver(HttpClient):
    base_url = 'https://feed.animetosho.org/json'

    def __init__(self, id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id

    def __str__(self):
        return f'ToshoResolver { self.id }'

    async def query_tosho(self):
        for retries in range(5):
            try:
                response = await self.client.get(self.base_url,
                                                 params={ 'show': 'torrent', 'id': self.id })
                self.print(f'Got response { response.status_code } for id { self.id }\n')
                data = response.json()

                if data['status'] != 'complete':
                    self.print(f"Item with id { self.id } is not complete: { data['status'] }\n")
                    return None
                else:
                    # Canonicalize the "links" values so it's always a list, perhaps of even one item
                    for f in data['files']:
                        links = f.get('links', {})
                        for k,v in links.items():
                            if type(v) is not list:
                                links[k] = [ v ]
            except httpx.ConnectTimeout:
                self.print(f'*** Timeout getting id { self.id } from tosho\n')
                continue

            return data
        return None

    async def run(self):
        self.print(f'Trying to get { self.id } from feed API\n')

        data = await self.query_tosho()
        if data is None:
            self.print('*** No response from tosho about id { self.id }\n')
            return

        # The 'files' key will be a list of hashes, each of which looks like:
        # { id: int
        #   filename: str
        #   md5: str
        #   links: {
        #       'downloader1': 'https://example.com/blahblah
        #       'downloader2:' [
        #           'https://example.org/12345',
        #           'https://example.org/9876',
        #       ]
        # }
        async with asyncio.TaskGroup() as tg:
            if data['num_files'] == 1:
                # Note that 'links' might be missing because the pieces haven't
                # been uploaded yet
                dl = FileDownloader(filename = data['files'][0]['filename'],
                                    md5      = data['files'][0]['md5'],
                                    links    = data['files'][0].get('links', {}))
                tg.create_task(dl.download())

            elif data['num_files'] > 1:
                for f in data['files']:
                    dl = FileDownloader(bundle = data['title'],
                                        filename = f['filename'],
                                        md5      = f['md5'],
                                        links    = f.get('links', {}))
                    tg.create_task(dl.download())

