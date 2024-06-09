# A mixin that all the individual downloaders use.
# It establishes a framework for how the other downloaders do
# their work.  In general, tosho will refer us to a sort of landing
# page that has a link that leads to the download link for the file data
#
# This is not a runnable Task by itself.  Consuming classes must
# implement some methods:
#   * get_download_link
#   * make_download_request

import httpx
import logging
import time
import asyncio
import os.path

from toshodl.Task import Task
from toshodl.Printable import Printable

logger = logging.getLogger(__name__)

class FileDownloader(Task, Printable):
    # url is the landing-page
    # picker is the PickFileDownloadSource that generated us
    # peers is a list of the other FileDownloader Tasks for all
    #       the pieces of the file
    def __init__(self, url, filename, peers, picker, *args, **kwargs):
        self.url = url
        self.filename = filename
        self.picker = picker
        self.peers = peers
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'download_from({ self.url })'

    async def get_download_link(self):
        pass

    async def do_download_request(self):
        pass

    async def make_retriable_request(self, url):
        for retries in range(5):
            try:
                response = await self.client.get(url)
            except httpx.ConnectTimeout:
                logger.warn(f'Timeout getting { url }')
                continue
            return response
        return None
                
    # The main entrypoint
    # Given the starting URL:
    #  * get() it
    #  * call get_download_link(response) which should return the final 
    async def task_impl(self):
        self.print(f'Trying to download from { self.url }\n')
        response = await self.make_retriable_request(self.url)

        dl_url = await self.get_download_link(response)
        if dl_url is None:
            return

        await self.do_download_file(dl_url)

    async def do_download_file(self, url):
        self.print(f'Downloading {self.filename} from { url }\n')
        start_time = time.time()
        bytes_dl = 0
        total_size = 1  # cheap hack to avoid divide-by-0 in print_progress
        
        def print_progress(msg = 'In progress:'):
            kb = bytes_dl / 1024
            mb = kb / 1024
            k_per_sec = kb / (time.time() - start_time)
            pct = bytes_dl / total_size * 100
            self.print(f'{msg} {self.filename} %0.2f MB %0.2f KB/s %0.1f%%\n' % ( mb, k_per_sec, pct))

        pathname = os.path.join('working', self.filename)
        dirname = os.path.dirname(pathname)
        #with await self.make_download_request(url) as response:
        request = await self.make_download_request(url)
        try:
            response = await self.client.send(request, stream=True)
            total_size = int(response.headers['Content-Length'])

            try:
                os.makedirs(dirname)
            except FileExistsError:
                pass

            with open(pathname, 'wb') as fh:
                with ProgressTimer(start=10, interval=30, cb=print_progress) as t:
                    async for chunk in response.aiter_bytes():
                        bytes_dl += len(chunk)
                        fh.write(chunk)
        finally:
            if response:
                await response.aclose()

        print_progress(msg='Done downloading')

class ProgressTimer(object):
    def __init__(self, interval, cb, start = None):
        self.interval = interval
        self.start = start
        self.cb = cb

    def __enter__(self):
        self.task = asyncio.ensure_future(self._run())

    def __exit__(self, type, value, traceback):
        self.task.cancel()

    async def _run(self):
        if self.start is not None:
            await asyncio.sleep(self.start)
        else:
            await asyncio.sleep(self.interval)

        while True:
            self.cb()
            await asyncio.sleep(self.interval)
