#!/usr/bin/env python
# A simple wrapper that allows calling a specific FileDownloader given a URL

import sys
import asyncio

from toshodl import AsyncConsole
from toshodl.Task.PickFileDownloadSource import PickFileDownloadSource

async def main(source, urls):
    await AsyncConsole.init()
    picker = PickFileDownloadSource(bundle='dl-via-result', filename='dl-via-result', md5=False,
                                    links={source: urls})

    dl_task_objs = await picker.run()
    dl_tasks = [ t.run() for t in dl_task_objs ]
    await asyncio.gather(*dl_tasks)

    await picker.finalized


execname, sourcename, *pieces = sys.argv
if type(pieces) is not list:
    pieces = [ pieces ]
asyncio.run(main(sourcename, pieces))

