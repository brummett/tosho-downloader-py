# Given a tosho ID, return PickFileDownloadSource tasks for each file.  If the ID
# is for a batch, there will be one task per file in the batch

import httpx
import logging

from toshodl.Task import Task
from toshodl.Printable import Printable
from toshodl.Task.PickFileDownloadSource import PickFileDownloadSource

logger = logging.getLogger(__name__)

class ToshoResolver(Printable, Task):
    base_url = 'https://feed.animetosho.org/json'

    def __init__(self, id, *args, **kwargs):
        self.id = id
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'ToshoResolver { self.id }'

    async def query_tosho(self):
        for retries in range(5):
            try:
                response = await self.client.get(self.base_url,
                                                 params={ 'show': 'torrent', 'id': self.id })
                self.print(f'Got response { response.status_code } for id { self.id }\n')
                data = response.json()
            except httpx.ConnectTimeout:
                logger.warn(f'Timeout getting id { self.id } from tosho')
                continue

            return data
        return None

    async def task_impl(self):
        self.print(f'Trying to get { self.id } from feed API\n')

        data = await self.query_tosho()
        if data is None:
            logger.error('No response from tosho about id { self.id }')
            return

        # status can be "complete", "skipped", "processing"
        # "complete_partial" means some but not all files in a group were fetched,
        # probably as part of a manually-triggered download
        if ('status' not in data) \
        or (data['status'] not in ['complete', 'complete_partial']):
            self.print("{ data['title'] } is not yet complete: { data['status'] }\n")
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
        if data['num_files'] == 1:
            # Note that 'links' might be missing because the pieces haven't
            # been uploaded yet
            dl_tasks = PickFileDownloadSource(bundle   = data['files'][0]['filename'],
                                              filename = data['files'][0]['filename'],
                                              md5      = data['files'][0]['md5'],
                                              links    = data['files'][0].get('links', {}))

        elif data['num_files'] > 1:
            dl_tasks = [ ]
            for f in data['files']:
                dl_tasks.append( PickFileDownloadSource(bundle = data['title'],
                                                        filename = f['filename'],
                                                        md5      = f['md5'],
                                                        links    = f.get('links', {})))

        return dl_tasks
