#!/usr/bin/env python

import asyncio
import queue

from toshodl.ToshoSearch import ToshoSearch
from toshodl import AsyncConsole
from toshodl.ToshoResolver import ToshoResolver

num_downloaders = 5

async def main():
    reader, writer = await AsyncConsole.init()

    tosho = ToshoSearch()

    tasks = []
    while True:
        writer.write('waiting for input: '.encode())
        line = await reader.readline()
        if not line:
            print("Done reading input!")
            break
        trimmed = line.decode().strip()
        if len(trimmed) > 0:
            id = await tosho.search(trimmed)
            if id is not None:
                writer.write(f'{trimmed} is id {id}\n'.encode())
                task = ToshoResolver(id)

    print("Out of the main loop")


if __name__ == '__main__':
    asyncio.run(main())
