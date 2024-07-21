# Base class for the source-specific download classes

import httpx
import time
import asyncio
import aiofiles
import os.path

from toshodl.HttpClient import HttpClient

class DownloadSourceBase(HttpClient):
    def __init__(self, url, filename, *args, **kwargs):
        self.url = url
        self.filename = filename
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'download from { self.url }'

    def download(self):
        return self.exception_retry(lambda: self.download_from_url(),
                                    exception=httpx.ReadTimeout,
                                    tries=5)

    async def save_stream_response(self, response):
        self.print(f'Trying to download from { response.url }\n')
        if response.status_code != 200:
            self.print(f"  status code { response.status_code }, exiting")
            return
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

        async with aiofiles.open(self.filename, mode='wb') as fh:
            with ProgressTimer(start=10, interval=30, cb=print_progress) as t:
                # We'll get a httpx.ReadTimeout if there's a download timeout
                # which will get caught in the exeption_retry() of download()
                async for chunk in response.aiter_bytes():
                    bytes_dl += len(chunk)
                    await fh.write(chunk)

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
