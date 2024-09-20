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

    async def exception_retry(self, fn, exception=httpx.ConnectTimeout, tries=5, delay=5, name=None):
        if name is None:
            name = self.url
        for i in range(tries):
            try:
                rv = await fn()
            except exception as e:
                self.print(f'*** { self } fn { fn } Caught { type(e) } { e } attempt { i }: { name }\n')
                if delay and delay > 0:
                    await asyncio.sleep(delay)
                last_exception = e
                continue # try again

            # if we get here, fn() was successful
            return rv

        # If we get here, we ran out of retries
        self.print(f'*** ran out of retries, throwing a { type(last_exception) }: { last_exception }\n')
        raise last_exception from last_exception

