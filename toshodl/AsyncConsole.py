import sys
import asyncio

cache_stdin = None
cache_stdout = None
async def init():
    global cache_stdin
    global cache_stdout

    # stdin
    loop = asyncio.get_event_loop()
    cache_stdin = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(cache_stdin)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    # stdout

    loop = asyncio.get_event_loop()
    transport, protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    #transport, protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin,
    #                                                    os.fdopen(sys.stdout.fileno(), 'wb'))
    cache_stdout = asyncio.streams.StreamWriter(transport, protocol, None, loop)

    return cache_stdin, cache_stdout

def stdin():
    return cache_stdin

def stdout():
    return cache_stdout
