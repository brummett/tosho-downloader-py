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
    # url is where tosho told us to go
    def __init__(self, url, filename, *args, **kwargs):
        self.url = url
        self.filename = filename
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'download_from({ self.url })'

    async def save_stream_response(self, response):
        self.print(f'Trying to download from { response.url }\n')
        dirname = os.path.dirname(self.filename)
        try:
            os.makedirs(dirname)
        except FileExistsError:
            pass

        start_time = time.time()
        bytes_dl = 0
        total_size = int(response.headers['Content-Length'])

        def print_progress(msg = 'In progress:'):
            kb = bytes_dl / 1024
            mb = kb / 1024
            k_per_sec = kb / (time.time() - start_time)
            pct = bytes_dl / total_size * 100
            self.print(f'{msg} {self.filename} %0.2f MB %0.2f KB/s %0.1f%%\n' % ( mb, k_per_sec, pct))

        # We'll get a httpx.ReadTimeout if there's a download timeout
        # consider retrying/restarting either the whole request or
        # at the currently downloaded position
        with open(self.filename, 'wb') as fh:
            with ProgressTimer(start=10, interval=30, cb=print_progress) as t:
                async for chunk in response.aiter_bytes():
                    bytes_dl += len(chunk)
                    fh.write(chunk)

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
