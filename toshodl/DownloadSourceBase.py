# Base class for the source-specific download classes

import httpx
import time
import asyncio
import aiofiles
import os.path

from toshodl.HttpClient import HttpClient

# raised when one source wants to give up and allow another source to try
class XTryAnotherSource(Exception):
    pass

# raised when a source encountered a retriable error
class XTryThisSourceAgain(Exception):
    pass

class DownloadSourceBase(HttpClient):
    def __init__(self, url, filename, *args, **kwargs):
        self.url = url
        self.filename = filename
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'download from { self.url }'

    async def download_from_url(self):
        raise NotImplemented(f'Class { type(self).__name__ } does not implement "download_from_url()"')

    async def download(self):
        try:
            return await self.exception_retry(self.download_from_url,
                                              exception=(httpx.TransportError, XTryThisSourceAgain),
                                              tries=5)
        except (httpx.TransportError, XTryThisSourceAgain):
            self.print(f'*** Exhausted retries downloading from { self.url }, trying another source...\n')
            raise XTryAnotherSource

    async def save_stream_response(self, response):
        self.print(f'Trying to download from { response.url }\n')
        if response.status_code != 200:
            self.print(f"  status code { response.status_code }, try another source...\n")
            raise XTryAnotherSource()
        dirname = os.path.dirname(self.filename)
        try:
            os.makedirs(dirname)
        except FileExistsError:
            pass

        start_time = prev_time = time.time()
        bytes_dl = prev_bytes = 0
        total_size = int(response.headers['Content-Length'])

        def print_progress(msg = 'In progress:', final=False):
            nonlocal prev_time
            nonlocal prev_bytes

            bytes_report = bytes_dl if final else (bytes_dl - prev_bytes)
            time_report  = start_time if final else prev_time

            kb = bytes_report / 1024
            k_per_sec = bytes_report / 1024 / (time.time() - time_report)
            mb_dl = bytes_dl / 1048576
            pct = bytes_dl / total_size * 100
            self.print(f'{msg} {self.filename} %0.2f MB %0.2f KB/s %0.1f%%\n' % ( mb_dl, k_per_sec, pct))

            prev_bytes = bytes_dl
            prev_time = time.time()

        async with aiofiles.open(self.filename, mode='wb') as fh:
            with ProgressTimer(start=10, interval=30, cb=print_progress) as t:
                # We'll get a httpx.ReadTimeout if there's a download timeout
                # which will get caught in the exeption_retry() of download()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    bytes_dl += len(chunk)
                    await fh.write(chunk)

        print_progress(msg='Done downloading', final=True)

class ProgressTimer(object):
    def __init__(self, interval, cb, start = None):
        self.interval = interval
        self.start = start
        self.cb = cb

    def __enter__(self):
        self.task = asyncio.create_task(self._run())

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

