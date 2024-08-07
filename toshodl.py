#!/usr/bin/env python

import asyncio
import queue

from toshodl.ToshoSearch import ToshoSearch
from toshodl import AsyncConsole
from toshodl.ToshoResolver import ToshoResolver

async def main():
    reader, writer = await AsyncConsole.init()

    tosho = ToshoSearch()

    tasks = []
    async with asyncio.TaskGroup() as tg:
        while True:
            writer.write('waiting for input: '.encode())
            line = await reader.readline()
            if not line:
                print("Done reading input!\nWaiting for all tasks to finish...")
                break
            trimmed = line.decode().strip()
            if len(trimmed) > 0:
                id = await tosho.search(trimmed)
                if id is not None:
                    writer.write(f'{trimmed} is id {id}\n'.encode())
                    resolver = ToshoResolver(id)
                    tg.create_task(resolver.run())

if __name__ == '__main__':
    asyncio.run(main())
