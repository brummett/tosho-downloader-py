# A mixin to print to the terminal compatible with asyncio
#
# The "flush_stdout" decorator will force a stdout flush/drain
# after the function completes.  It only works on methods of
# classes that are Printable

import asyncio

from toshodl import AsyncConsole

class Printable(object):
    def __init__(self):
        self.stdout = AsyncConsole.stdout()

    def print(self, msg):
        self.stdout.write(msg.encode())

    def flush_stdout(self):
        return self.stdout.drain()

def flush_stdout(f):
    def wrapper(self, *args, **kwargs):
        rv = f(self, *args, **kwargs)
        asyncio.create_task(self.flush_stdout)
        return rv

    return wrapper


