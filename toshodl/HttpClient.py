# A mixin that gives the consumer a "client" attribute that's an httpx
# client object

import httpx
import asyncio

from toshodl.Printable import Printable

class HttpClient(Printable):
    client = httpx.AsyncClient()

    def __init__(self, *args, **kwargs):
        self.client = HttpClient.client
        super().__init__(*args, **kwargs)

    async def exception_retry(self, fn, exception=httpx.ConnectTimeout, tries=5, delay=5):
        for i in range(tries-1):
            try:
                rv = await fn()
            except exception as e:
                self.print(f'*** { self } Caught { e }: { i }\n')
                if delay and delay > 0:
                    await asyncio.sleep(delay)
                continue # try again

            # if we get here, fn() was successful
            return rv

