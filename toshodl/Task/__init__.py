# Base class for Tasks.  They all share a common httpx AsyncClient
#
# Child classes must implement a task_impl() function which returns either:
# None: no further action needs to be taken from the completion of this task
# Task: schedule this task to run
# list of Task: Schedule these tasks to run

import httpx
import sys
import logging
import traceback
import asyncio

logger = logging.getLogger(__name__)

class Task(object):
    client = httpx.AsyncClient()

    def __init__(self, *args, **kwargs):
        self.done = asyncio.get_event_loop().create_future()
        super().__init__(*args, **kwargs)

    async def task_impl(self):
        NotImplementedError(f'{type(self)} did not implement task_impl()')

    async def run(self):
        #rv = await self.task_impl()

        try:
            rv = await self.task_impl()
        except Exception as e:
            #print(f'***TASK EXCEPTION*** {e}')
            #exc_info = sys.exc_info()
            #logger.error(f'**** Caught { type(e) } exception in task { self }: { traceback.extract_tb(exc_info[2]) }')
            #logger.error(f'*** Caught { type(e) } exception in task { self }: { traceback.format_exc() }')
            self.print(f'*** Caught { type(e) } exception in task { self }: { traceback.format_exc() }')
            await self.flush_stdout()
            self.done.set_exception(e)
            return

        self.done.set_result(True)

        return rv

    async def timeout_retry(self, f, tries=5):
        for i in range(tries-1):
            try:
                rv = await f()
            except httpx.ConnectTimeout:
                logger.warn(f'Timeout getting { url }')
                continue
            return rv
